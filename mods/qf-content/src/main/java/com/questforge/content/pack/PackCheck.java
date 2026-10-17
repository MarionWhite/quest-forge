package com.questforge.content.pack;

import java.io.File;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashSet;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

import net.minecraft.entity.player.EntityPlayerMP;
import net.minecraft.server.MinecraftServer;
import net.minecraftforge.common.config.Configuration;

import cpw.mods.fml.common.Loader;
import cpw.mods.fml.common.ModContainer;
import cpw.mods.fml.common.eventhandler.SubscribeEvent;
import cpw.mods.fml.common.gameevent.PlayerEvent;
import cpw.mods.fml.common.gameevent.TickEvent;

import com.questforge.content.QuestForgeContent;
import com.questforge.content.net.PacketPackQuery;
import com.questforge.content.net.PacketPackReport;
import com.questforge.content.net.QFNetwork;
import com.questforge.content.net.ServerTasks;

/**
 * The login check that keeps a stale client out.
 *
 * FML's handshake compares mod versions, so an old qf-content is refused there
 * (its version is per-commit now). It never compares configs, and the IDs that
 * corrupt a shared world -- potions, enchantments, biomes, dimensions, entities --
 * live in configs. So right after login the server asks, the client answers with
 * its {@link PackFingerprint} and mod list, and the server disconnects anyone whose
 * pack differs, saying which side is out of date and where to update from.
 *
 * The server decides, not the client, so the refusal is logged where the host can
 * see it and an admin's override (qfcontent.cfg, packcheck) takes effect without
 * touching any client.
 *
 * Only a dedicated server checks. In singleplayer and on LAN the client is the
 * server, so there is nothing to compare.
 */
public final class PackCheck {

    public static final String CATEGORY = "packcheck";

    // --- qfcontent.cfg, packcheck -------------------------------------------------
    static boolean enabled = true;
    static String packDate = "";
    static String updateFrom = "";
    static String expectedOverride = "";
    static Set<String> alsoAccept = new HashSet<String>();
    static boolean checkModVersions = true;
    static Set<String> ignoreMods = new HashSet<String>();

    /**
     * Never compared: the platform, not the pack. The chosen setup runs OptiFine
     * clients on Forge 1558 next to Angelica clients and the Java 25 server on
     * 1614, and the two builds interoperate. A content mismatch still shows up
     * in the config fingerprint and in every other mod's version.
     */
    static final Set<String> PLATFORM_MODS =
            new HashSet<String>(Arrays.asList("mcp", "FML", "Forge"));
    static int answerTimeoutSeconds = 60;

    // --- this side ----------------------------------------------------------------
    private static volatile PackFingerprint.Result local;
    private static volatile Map<String, String> localMods = new TreeMap<String, String>();
    private static volatile Map<String, String> localModNames = new TreeMap<String, String>();

    // --- server: who has been asked and not answered ------------------------------
    private static final Map<UUID, Long> PENDING = new ConcurrentHashMap<UUID, Long>();

    private PackCheck() {}

    public static void loadConfig(Configuration cfg) {
        cfg.setCategoryComment(CATEGORY,
                "The login pack check. A client whose ID-bearing configs (see /qfpack) or shared mod\n"
                + "versions differ from the server's is disconnected with a message saying which side\n"
                + "is out of date. Only a dedicated server checks; these settings matter there, except\n"
                + "packDate, which every side shows on its main menu and F3 screen.");
        enabled = cfg.getBoolean("enabled", CATEGORY, true,
                "Check every joining client. Turn off only in an emergency; prefer alsoAccept.");
        packDate = cfg.getString("packDate", CATEGORY, "",
                "The pack release this config folder belongs to (YYYY-MM-DD). It is not part of the\n"
                + "fingerprint; it says which side is older when fingerprints differ. Bump it with\n"
                + "`py -3.10 tools/pack_fingerprint.py --stamp` whenever an ID-bearing config changes.");
        updateFrom = cfg.getString("updateFrom", CATEGORY,
                "https://github.com/MarionWhite/quest-forge/releases",
                "Where a refused player gets the current pack. Shown in the refusal message.");
        expectedOverride = cfg.getString("expectedFingerprint", CATEGORY, "",
                "Server, emergency only: require this fingerprint from clients instead of the one\n"
                + "computed from this server's own configs. Empty = computed.");
        alsoAccept = new HashSet<String>(Arrays.asList(trimAll(cfg.getStringList("alsoAccept", CATEGORY,
                new String[0],
                "Server: further client fingerprints to let in, e.g. last release's while friends update."))));
        checkModVersions = cfg.getBoolean("checkModVersions", CATEGORY, true,
                "Server: also refuse a client whose version of a mod both sides have differs.");
        ignoreMods = new HashSet<String>(Arrays.asList(trimAll(cfg.getStringList("ignoreMods", CATEGORY,
                new String[0], "Server: mod IDs whose versions may differ between client and server."))));
        answerTimeoutSeconds = cfg.getInt("answerTimeoutSeconds", CATEGORY, 60, 5, 600,
                "Server: disconnect a client that has not answered the check after this long.");
    }

    private static String[] trimAll(String[] in) {
        List<String> out = new ArrayList<String>();
        for (String s : in) if (s != null && !s.trim().isEmpty()) out.add(s.trim());
        return out.toArray(new String[out.size()]);
    }

    /** Once every mod has loaded and written its config. */
    public static void computeLocal(File configDir) {
        local = PackFingerprint.compute(configDir);
        Map<String, String> mods = new TreeMap<String, String>();
        Map<String, String> names = new TreeMap<String, String>();
        for (ModContainer mc : Loader.instance().getActiveModList()) {
            mods.put(mc.getModId(), String.valueOf(mc.getVersion()));
            names.put(mc.getModId(), mc.getName());
        }
        localMods = mods;
        localModNames = names;
        QuestForgeContent.log.info("[packcheck] pack " + displayDate(packDate) + ", fingerprint "
                + local.fingerprint + ", " + mods.size() + " mods (digest "
                + PackFingerprint.modsDigest(mods) + ")");
    }

    public static PackFingerprint.Result local() {
        return local;
    }

    public static String fingerprint() {
        return local == null ? "?" : local.fingerprint;
    }

    public static String packDate() {
        return packDate;
    }

    public static Map<String, String> localMods() {
        return localMods;
    }

    /** What clients must send: the override if an admin set one. */
    public static String expected() {
        return expectedOverride.isEmpty() ? fingerprint() : expectedOverride;
    }

    static String displayDate(String d) {
        return (d == null || d.isEmpty()) ? "(undated)" : d;
    }

    /** The client's answer, built on whichever thread asked. */
    public static PacketPackReport buildReport() {
        PacketPackReport r = new PacketPackReport();
        PackFingerprint.Result res = local;
        r.fingerprint = res == null ? "?" : res.fingerprint;
        r.packDate = packDate;
        r.files = res == null ? new LinkedHashMap<String, String>() : res.digests;
        r.mods = localMods;
        return r;
    }

    // --- server side ----------------------------------------------------------------

    private static boolean active() {
        MinecraftServer s = MinecraftServer.getServer();
        return enabled && s != null && s.isDedicatedServer() && local != null;
    }

    /** From the netty thread: judged on the server thread. */
    public static void onReport(final EntityPlayerMP player, final PacketPackReport report) {
        ServerTasks.submit(new Runnable() {
            @Override
            public void run() {
                judge(player, report);
            }
        });
    }

    static void judge(EntityPlayerMP player, PacketPackReport r) {
        if (PENDING.remove(player.getUniqueID()) == null) return; // not asked, or already judged
        if (!active() || player.playerNetServerHandler == null) return;

        String expected = expected();
        boolean configsOk = expected.equals(r.fingerprint) || alsoAccept.contains(r.fingerprint);

        List<String> files = new ArrayList<String>();
        if (!configsOk) {
            for (Map.Entry<String, String> e : local.digests.entrySet()) {
                String theirs = r.files.get(e.getKey());
                if (theirs == null || !theirs.equals(e.getValue())) files.add(e.getKey());
            }
        }

        List<String> mods = new ArrayList<String>();
        if (checkModVersions) {
            for (Map.Entry<String, String> e : localMods.entrySet()) {
                String theirs = r.mods.get(e.getKey());
                if (theirs == null || ignoreMods.contains(e.getKey())
                        || PLATFORM_MODS.contains(e.getKey())) continue;
                if (!theirs.equals(e.getValue())) {
                    String name = localModNames.get(e.getKey());
                    mods.add((name == null ? e.getKey() : name) + " " + theirs
                            + " (server " + e.getValue() + ")");
                }
            }
        }

        String who = player.getCommandSenderName();
        if (configsOk && mods.isEmpty()) {
            QuestForgeContent.log.info("[packcheck] " + who + " OK: pack " + displayDate(r.packDate)
                    + ", fingerprint " + r.fingerprint);
            return;
        }

        String message = refusal(r, files, mods);
        QuestForgeContent.log.warn("[packcheck] refusing " + who + ": client pack "
                + displayDate(r.packDate) + " " + r.fingerprint + ", server pack "
                + displayDate(packDate) + " " + expected
                + (files.isEmpty() ? "" : "; configs differ: " + files)
                + (mods.isEmpty() ? "" : "; mods differ: " + mods));
        player.playerNetServerHandler.kickPlayerFromServer(message);
    }

    /** The disconnect screen text. Short lines: the screen wraps, but not well. */
    static String refusal(PacketPackReport r, List<String> files, List<String> mods) {
        String theirs = r.packDate == null ? "" : r.packDate;
        String ours = packDate;
        int cmp = theirs.compareTo(ours);   // ISO dates sort as strings; undated is oldest

        StringBuilder b = new StringBuilder();
        String fix;
        if (cmp < 0) {
            b.append("§cYour Quest Forge client is out of date.§r\n\n");
            fix = "Update your pack from:\n" + updateFrom;
        } else if (cmp > 0) {
            b.append("§cThis server runs an older Quest Forge pack than yours.§r\n\n");
            fix = "Ask the host to update the server,\nor install the server's pack from:\n" + updateFrom;
        } else if (!files.isEmpty()) {
            b.append("§cYour Quest Forge configs differ from the server's.§r\n\n");
            fix = "Those files must match the server's copy.\nReinstall the pack's config folder from:\n"
                    + updateFrom;
        } else {
            b.append("§cYour mods differ from the server's.§r\n\n");
            fix = "Install the server's versions from:\n" + updateFrom;
        }
        b.append("Server: pack ").append(displayDate(ours)).append(" (").append(expected()).append(")\n");
        b.append("Yours: pack ").append(displayDate(theirs)).append(" (").append(r.fingerprint).append(")\n");
        if (!files.isEmpty()) b.append("Configs: ").append(shortList(files)).append('\n');
        if (!mods.isEmpty()) b.append("Mods: ").append(shortList(mods)).append('\n');
        b.append('\n').append(fix);
        return b.toString();
    }

    private static String shortList(List<String> items) {
        int shown = Math.min(items.size(), 4);
        StringBuilder b = new StringBuilder();
        for (int i = 0; i < shown; i++) {
            if (i > 0) b.append(", ");
            b.append(items.get(i));
        }
        if (items.size() > shown) b.append(" and ").append(items.size() - shown).append(" more");
        return b.toString();
    }

    /** FML-bus events, server side. */
    public static final class Events {

        private int ticks;

        @SubscribeEvent
        public void onLogin(PlayerEvent.PlayerLoggedInEvent event) {
            if (!(event.player instanceof EntityPlayerMP) || !active()) return;
            EntityPlayerMP player = (EntityPlayerMP) event.player;
            if (player.playerNetServerHandler == null) return;     // a FakePlayer
            PENDING.put(player.getUniqueID(), System.currentTimeMillis() + answerTimeoutSeconds * 1000L);
            QFNetwork.toPlayer(new PacketPackQuery(expected(), packDate), player);
        }

        @SubscribeEvent
        public void onLogout(PlayerEvent.PlayerLoggedOutEvent event) {
            PENDING.remove(event.player.getUniqueID());
        }

        @SubscribeEvent
        public void onServerTick(TickEvent.ServerTickEvent event) {
            if (event.phase != TickEvent.Phase.END || PENDING.isEmpty() || ++ticks % 20 != 0) return;
            long now = System.currentTimeMillis();
            for (Iterator<Map.Entry<UUID, Long>> it = PENDING.entrySet().iterator(); it.hasNext(); ) {
                Map.Entry<UUID, Long> e = it.next();
                if (e.getValue() > now) continue;
                it.remove();
                EntityPlayerMP p = find(e.getKey());
                if (p == null || p.playerNetServerHandler == null) continue;
                QuestForgeContent.log.warn("[packcheck] refusing " + p.getCommandSenderName()
                        + ": no answer to the pack check in " + answerTimeoutSeconds + " s");
                p.playerNetServerHandler.kickPlayerFromServer(
                        "§cThe server could not check your Quest Forge pack.§r\n\n"
                        + "Your client did not answer in " + answerTimeoutSeconds + " s;\n"
                        + "its qf-content is probably too old.\n\n"
                        + "Server: pack " + displayDate(packDate) + " (" + expected() + ")\n\n"
                        + "Update your pack from:\n" + updateFrom);
            }
        }

        private static EntityPlayerMP find(UUID id) {
            MinecraftServer s = MinecraftServer.getServer();
            if (s == null) return null;
            for (Object o : s.getConfigurationManager().playerEntityList) {
                EntityPlayerMP p = (EntityPlayerMP) o;
                if (p.getUniqueID().equals(id)) return p;
            }
            return null;
        }
    }
}
