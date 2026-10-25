package com.questforge.content.debug;

import java.io.File;
import java.io.FileWriter;
import java.io.PrintWriter;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.GuiSelectWorld;
import net.minecraft.entity.player.EntityPlayerMP;
import net.minecraft.init.Blocks;
import net.minecraft.init.Items;
import net.minecraft.item.ItemStack;
import net.minecraft.server.MinecraftServer;
import net.minecraft.world.EnumDifficulty;
import net.minecraft.world.WorldServer;
import net.minecraft.world.WorldSettings;
import cpw.mods.fml.common.eventhandler.SubscribeEvent;
import cpw.mods.fml.common.gameevent.TickEvent;
import cpw.mods.fml.relauncher.Side;
import cpw.mods.fml.relauncher.SideOnly;

import com.questforge.content.ench.QFEnchantments;

/**
 * Flies a fixed route through a fixed world and records every frame, so two
 * settings can be compared by numbers instead of by feel.
 *
 * Entirely inert unless -Dqf.bench=1 is given; the first world in the save list
 * is loaded. -Dqf.bench.tag=<name> names the result file (bench/<tag>.txt in
 * the game directory). -Dqf.bench.scenes=static,fly,torch picks the scenes.
 * -Dqf.bench.torch=0 runs the torch scene holding a plain pickaxe, as its
 * control.
 *
 * The scenes:
 *   static -- noon, standing still, looking over terrain: the steady cost of
 *             the world and the shader, with nothing being rebuilt.
 *   fly    -- noon, flying in a straight line at 10 blocks/s: chunks arriving
 *             and being built, which is where frame spikes come from.
 *   torch  -- midnight, sprinting through a sealed tunnel holding a
 *             Torchlight III pickaxe (or a plain one): the cost of the
 *             light following the player.
 *   torch_wall -- midnight, standing still in a sealed mineshaft-style tunnel
 *             lit only by torches placed on its walls (no held light, no HUD):
 *             the shader review's block-light scene. Shot like a view scene.
 *
 * Why frame times and not FPS: an average hides exactly the thing people
 * complain about. Each scene reports mean FPS, the median and 99th-percentile
 * frame time, the "1% low" (mean FPS of the slowest 1% of frames), the worst
 * frame, how many frames took over 33 ms, and the chunk updates the game
 * itself counted.
 *
 * View scenes (shader review, docs/design/shaders/review-loop.md):
 * -Dqf.bench.views=<file> defines still-camera scenes by name, one per line:
 *   name  x  y|auto  z  yaw  pitch  worldTime  [measureTicks]
 * Any name in qf.bench.scenes that is not a built-in scene is looked up there.
 * A view hides the GUI (F1), so frames carry no HUD; it is measured standing
 * still, then shot twice on consecutive ticks AFTER measuring (bench-TAG-NAME.png
 * and bench-TAG-NAME-b.png): the pair gives check_frames.py its temporal-noise
 * test, and no screenshot hitch lands inside a measured window. worldTime picks
 * the moon phase too: 18000 is a full moon, 114000 (day 4) a new moon.
 * -Dqf.bench.reload=scene,scene calls Iris.reload() (the F9 key) before those scenes.
 *
 * Batch mode (tools/renderq, 2026-10-25): -Dqf.bench.jobs=<file> renders many jobs -- each a
 * tag, shaders on or off and a shader option file -- in ONE boot, instead of one boot per
 * option set. The file, written by tools/renderq/batch.py:
 *   target <path>                          the pack's option file (shaderpacks/QuestForge.txt)
 *   boot on|off                            whether the client booted with shaders on
 *   job <tag> on|off <warmTicks> <measureTicks> <opts|->
 *                                          opts is copied onto target before the job's frames;
 *                                          measureTicks > 0 overrides the scene's own (a
 *                                          screenshot-only job measures 20 ticks, not 200)
 *   rps <tag> <name>|<name>|...            the job's resource packs (options.txt order: the
 *                                          last wins); changed in game with shaders off
 *   step <tag> <scene>                     one measured scene of one job, in the order given
 * Before a step whose job differs from the live state, the option file is rewritten and
 * Iris.reload() (or Iris.toggleShaders) runs; that step then settles for at least warmTicks
 * more, so no measured frame belongs to the rebuilt pipeline's first seconds. Each finished
 * step appends its block to bench/<tag>.part (a crash keeps the steps done); at the end
 * every job gets bench/<tag>.txt in the same format as a single run. bench/_progress.txt is
 * rewritten at every stage change, for the runner's stall watchdog.
 */
@SideOnly(Side.CLIENT)
public class FrameBench {

    private static final boolean ON = System.getProperty("qf.bench") != null;

    public static boolean enabled() {
        return ON;
    }

    // Route. The test world is pregenerated 640 blocks round 0,0, so all of
    // this is finished terrain and the server never generates during a scene.
    private static final int TUNNEL_Y = 14, TUNNEL_Z = 120, TUNNEL_X0 = -70, TUNNEL_LEN = 140;
    private static final double FLY_Y = 120, FLY_Z = 200, FLY_X0 = -300, FLY_SPEED = 0.5;
    private static final double SPRINT = 0.28;          // blocks/tick, vanilla sprint
    private static final int MEASURE_TICKS = 400;       // 20 s per scene
    private static final int SETTLE_MAX = 900;          // 45 s to finish building chunks
    private static final int BATCH_QUIET_UPDATES = 25;  // chunk updates/s that count as settled (batch)

    private enum Stage { TITLE, SELECTING, LOADING, SETUP, SETTLE, MEASURE, SHOOT, DONE }

    /** A still-camera scene from the qf.bench.views file. */
    private static final class View {
        String name;
        double x, y, z;     // y NaN: stand on the top block
        float yaw, pitch;
        long time;
        int ticks;
    }

    private final java.util.Map<String, View> views = loadViews();

    private static java.util.Map<String, View> loadViews() {
        java.util.Map<String, View> out = new java.util.HashMap<String, View>();
        String path = System.getProperty("qf.bench.views");
        if (path == null) return out;
        try {
            for (String line : java.nio.file.Files.readAllLines(new File(path).toPath(),
                    java.nio.charset.StandardCharsets.UTF_8)) {
                line = line.trim();
                if (line.isEmpty() || line.startsWith("#")) continue;
                String[] f = line.split("\\s+");
                View v = new View();
                v.name = f[0];
                v.x = Double.parseDouble(f[1]);
                v.y = f[2].equals("auto") ? Double.NaN : Double.parseDouble(f[2]);
                v.z = Double.parseDouble(f[3]);
                v.yaw = Float.parseFloat(f[4]);
                v.pitch = Float.parseFloat(f[5]);
                v.time = Long.parseLong(f[6]);
                v.ticks = f.length > 7 ? Integer.parseInt(f[7]) : 200;
                out.put(v.name, v);
            }
        } catch (Exception e) {
            log("views: cannot read " + path + ": " + e);
        }
        log("views: " + out.keySet());
        return out;
    }

    private Stage stage = Stage.TITLE;
    private int ticks, quiet, sceneIdx = -1;
    private String[] scenes;
    private long lastFrame;
    private final List<Long> frames = new ArrayList<Long>();
    private int chunkUpdates;
    private String lastDebug = "";
    private final List<String> report = new ArrayList<String>();

    /** One job of a batch (-Dqf.bench.jobs): a tag, shaders on/off, an option file to apply. */
    private static final class Job {
        String tag;
        boolean shaders;
        int warm, measure;
        String opts;          // null: leave the option file as it is
        List<String> rps;     // null: leave the resource packs as they are
        final List<String> report = new ArrayList<String>();
    }

    private final java.util.Map<String, Job> jobs = new java.util.LinkedHashMap<String, Job>();
    private Job[] stepJob;            // per step; null in a single run
    private String optsTarget;
    private Job live;                 // the job whose state the pipeline has now
    private boolean liveShaders;      // shaders on at boot? (config/shaders.properties)
    private List<String> liveRps;     // resource packs now active (null: as booted)
    private int warmTicks;            // settle at least this long (set after a reload)
    private final long batchStart = System.currentTimeMillis();

    public FrameBench() {
        String jf = System.getProperty("qf.bench.jobs");
        if (jf != null) {
            loadJobs(jf);
        } else {
            scenes = System.getProperty("qf.bench.scenes", "static,fly,torch").split(",");
        }
    }

    private void loadJobs(String path) {
        List<String> sc = new ArrayList<String>();
        List<Job> sj = new ArrayList<Job>();
        try {
            for (String line : java.nio.file.Files.readAllLines(new File(path).toPath(),
                    java.nio.charset.StandardCharsets.UTF_8)) {
                line = line.trim();
                if (line.isEmpty() || line.startsWith("#")) continue;
                String[] f = line.split("\\s+", 6);
                if (f[0].equals("target")) {
                    optsTarget = line.substring(6).trim();
                } else if (f[0].equals("boot")) {
                    liveShaders = f[1].equals("on");
                } else if (f[0].equals("job")) {
                    Job j = new Job();
                    j.tag = f[1];
                    j.shaders = f[2].equals("on");
                    j.warm = Integer.parseInt(f[3]);
                    j.measure = Integer.parseInt(f[4]);
                    j.opts = f.length > 5 && !f[5].equals("-") ? f[5] : null;
                    jobs.put(j.tag, j);
                } else if (f[0].equals("rps")) {
                    Job j = jobs.get(f[1]);
                    if (j != null) {
                        String rest = line.substring(3).trim();
                        rest = rest.substring(f[1].length()).trim();   // names may hold spaces
                        j.rps = rest.isEmpty() ? new ArrayList<String>() : Arrays.asList(rest.split("\\|"));
                    }
                } else if (f[0].equals("step")) {
                    Job j = jobs.get(f[1]);
                    if (j == null) {
                        log("jobs: step for unknown job " + f[1]);
                        continue;
                    }
                    sj.add(j);
                    sc.add(f[2]);
                }
            }
        } catch (Exception e) {
            log("jobs: cannot read " + path + ": " + e);
        }
        scenes = sc.toArray(new String[0]);
        stepJob = sj.toArray(new Job[0]);
        log("jobs: " + jobs.size() + " jobs, " + scenes.length + " steps, boot shaders "
                + (liveShaders ? "on" : "off"));
    }

    private String tag() {
        if (stepJob != null && sceneIdx >= 0 && sceneIdx < stepJob.length) return stepJob[sceneIdx].tag;
        return System.getProperty("qf.bench.tag", "bench");
    }

    private List<String> rep() {
        if (stepJob != null && sceneIdx >= 0 && sceneIdx < stepJob.length) return stepJob[sceneIdx].report;
        return report;
    }

    /** bench/_progress.txt: what the batch is doing now, for the runner's watchdog and ETA. */
    private void progress(Minecraft mc, String what) {
        try {
            File dir = new File(mc.mcDataDir, "bench");
            dir.mkdirs();
            File tmp = new File(dir, "_progress.tmp");
            PrintWriter out = new PrintWriter(new FileWriter(tmp));
            out.println("at " + System.currentTimeMillis());
            out.println("step " + (sceneIdx + 1) + " " + (scenes == null ? 0 : scenes.length));
            out.println("tag " + tag());
            out.println("scene " + (sceneIdx >= 0 && scenes != null && sceneIdx < scenes.length ? scene() : "-"));
            out.println("stage " + what);
            out.println("elapsed " + (System.currentTimeMillis() - batchStart));
            out.close();
            File dst = new File(dir, "_progress.txt");
            dst.delete();
            tmp.renameTo(dst);
        } catch (Throwable t) {
            log("progress: " + t);
        }
    }

    /**
     * Brings the pipeline to job j's state: its option file, shaders on or off. Iris.reload()
     * re-reads shaderpacks/<pack>.txt and rebuilds the pipeline (the F9 key);
     * Iris.toggleShaders turns the pack on or off (the K key). Returns false if nothing changed.
     */
    private boolean apply(Job j) {
        if (live == j) return false;
        boolean optsChange = j.opts != null && (live == null || !j.opts.equals(live.opts));
        long t0 = System.nanoTime();
        String did = "nothing to rebuild";
        try {
            if (j.rps != null && !j.rps.equals(liveRps == null ? Minecraft.getMinecraft().gameSettings.resourcePacks : liveRps)) {
                did = setResourcePacks(j.rps) + "; ";
            }
            if (optsChange && optsTarget != null) {
                File dst = new File(optsTarget);
                byte[] b = java.nio.file.Files.readAllBytes(new File(j.opts).toPath());
                dst.delete();
                java.nio.file.Files.write(dst.toPath(), b);
            }
            Class<?> iris = Class.forName("net.coderbot.iris.Iris");
            if (j.shaders != liveShaders) {
                iris.getMethod("toggleShaders", Minecraft.class, boolean.class)
                        .invoke(null, Minecraft.getMinecraft(), j.shaders);
                did = (did.startsWith("nothing") ? "" : did) + "toggleShaders(" + j.shaders + ")";
            } else if (j.shaders && optsChange) {
                iris.getMethod("reload").invoke(null);
                did = (did.startsWith("nothing") ? "" : did) + "reload()";
            }
            liveShaders = j.shaders;
        } catch (Throwable t) {
            log("job " + j.tag + ": apply failed: " + t);
            t.printStackTrace();
        }
        log(String.format("job %s: %s in %.0f ms", j.tag, did, (System.nanoTime() - t0) / 1e6));
        live = j;
        return !did.equals("nothing to rebuild");
    }

    /**
     * What the resource pack screen's Done button does (GuiScreenResourcePacks), with the shader
     * pipeline off for the reload: Angelica rebuilding a live pipeline across a resource reload is
     * what crashes it at boot. Names are file names in resourcepacks/, bottom first.
     */
    private String setResourcePacks(List<String> names) throws Exception {
        Minecraft mc = Minecraft.getMinecraft();
        if (liveShaders) {
            Class.forName("net.coderbot.iris.Iris").getMethod("toggleShaders", Minecraft.class, boolean.class)
                    .invoke(null, mc, false);
            liveShaders = false;
        }
        net.minecraft.client.resources.ResourcePackRepository repo = mc.getResourcePackRepository();
        repo.updateRepositoryEntriesAll();
        List<Object> entries = new ArrayList<Object>();
        for (String n : names) {
            for (Object o : repo.getRepositoryEntriesAll()) {
                if (((net.minecraft.client.resources.ResourcePackRepository.Entry) o).getResourcePackName().equals(n)) {
                    entries.add(o);
                }
            }
        }
        if (entries.size() != names.size()) log("resource packs: found " + entries.size() + " of " + names);
        repo.func_148527_a(entries);
        mc.gameSettings.resourcePacks.clear();
        mc.gameSettings.resourcePacks.addAll(names);
        mc.refreshResources();
        liveRps = new ArrayList<String>(names);
        return "resource packs " + names;
    }

    /** A finished step's lines, appended to bench/<tag>.part so a crash keeps them. */
    private void savePart(Minecraft mc, List<String> lines) {
        if (stepJob == null) return;
        try {
            File dir = new File(mc.mcDataDir, "bench");
            dir.mkdirs();
            PrintWriter out = new PrintWriter(new FileWriter(new File(dir, tag() + ".part"), true));
            for (String l : lines) out.println(l);
            out.close();
        } catch (Throwable t) {
            log("part: " + t);
        }
    }

    private static void log(String s) {
        System.out.println("[FrameBench] " + s);
    }

    /** Frame boundaries. START of one render tick to START of the next is one frame. */
    @SubscribeEvent
    public void onRender(TickEvent.RenderTickEvent event) {
        if (event.phase != TickEvent.Phase.START) return;
        long now = System.nanoTime();
        if (stage == Stage.MEASURE && lastFrame != 0) frames.add(now - lastFrame);
        lastFrame = now;
    }

    @SubscribeEvent
    public void onTick(TickEvent.ClientTickEvent event) {
        if (event.phase != TickEvent.Phase.END || stage == Stage.DONE) return;
        Minecraft mc = Minecraft.getMinecraft();
        ticks++;

        // Singleplayer pauses when the window loses focus, and an unattended run
        // always has lost focus. A paused game renders the menu, not the scene.
        mc.gameSettings.pauseOnLostFocus = false;
        if (stage.ordinal() >= Stage.SETUP.ordinal() && mc.currentScreen != null) {
            mc.displayGuiScreen(null);
        }

        // "123 fps, 45 chunk updates" -- refreshed once a second.
        if (!mc.debug.equals(lastDebug)) {
            lastDebug = mc.debug;
            int n = parseChunkUpdates(lastDebug);
            if (stage == Stage.MEASURE) chunkUpdates += n;
            // Batch mode settles on "no more than a trickle": a world with flowing water or lava
            // never reports 0 for long (r007's qh measured 1-22 updates/s standing still), so the
            // single-run rule hit the 45 s SETTLE_MAX on most scenes; after a reload or teleport the
            // rebuild runs at hundreds a second. Single runs keep the old rule.
            quiet = n <= (stepJob != null ? BATCH_QUIET_UPDATES : 0) ? quiet + 1 : 0;
        }

        switch (stage) {
            case TITLE:
                // Not launchIntegratedServer: with CustomMenu installed that starts
                // the server but leaves the client on the title screen. The world
                // list's own click path logs in properly.
                if (ticks > 100 && mc.theWorld == null) {
                    mc.displayGuiScreen(new GuiSelectWorld(mc.currentScreen));
                    stage = Stage.SELECTING;
                    ticks = 0;
                }
                return;
            case SELECTING:
                if (ticks > 20 && mc.currentScreen instanceof GuiSelectWorld) {
                    log("loading world 0");
                    ((GuiSelectWorld) mc.currentScreen).func_146615_e(0);
                    stage = Stage.LOADING;
                    ticks = 0;
                }
                return;
            case LOADING:
                if (mc.theWorld != null && mc.thePlayer != null && mc.getIntegratedServer() != null
                        && ticks > 200) {
                    nextScene(mc);
                }
                return;
            case SETUP:
                if (setupDone) {
                    setupDone = false;
                    stage = Stage.SETTLE;
                    ticks = 0;
                    quiet = 0;
                }
                return;
            case SETTLE:
                hold(mc);
                // Built when the game has reported no chunk updates for three
                // seconds running, or after SETTLE_MAX regardless.
                if ((quiet >= 3 && ticks > Math.max(100, warmTicks)) || ticks > SETTLE_MAX + warmTicks) {
                    log(scene() + ": settled after " + ticks + " ticks; measuring");
                    progress(mc, "measure");
                    if (tally == null || tally.world != mc.theWorld) {
                        tally = new UpdateTally(mc.theWorld);
                        mc.theWorld.addWorldAccess(tally);
                    }
                    tally.clear();
                    frames.clear();
                    chunkUpdates = 0;
                    lastFrame = 0;
                    stage = Stage.MEASURE;
                    ticks = 0;
                }
                return;
            case MEASURE:
                move(mc);
                View mv = views.get(scene());
                int want = mv != null ? mv.ticks : MEASURE_TICKS;
                if (stepJob != null && stepJob[sceneIdx].measure > 0 && !scene().equals("gallery")) {
                    want = stepJob[sceneIdx].measure;
                }
                if (ticks >= want) {
                    summarise(mc);
                    if (mv != null || scene().equals("torch") || scene().equals("torch_wall")) {
                        stage = Stage.SHOOT;
                        ticks = 0;
                    } else {
                        nextScene(mc);
                    }
                }
                return;
            case SHOOT:
                // After measuring, so the screenshot hitch is never a measured frame.
                hold(mc);
                if (ticks == 2) shot(mc, scene());
                if (ticks == 3) shot(mc, scene() + "-b");
                if (ticks >= 4) nextScene(mc);
                return;
            default:
        }
    }

    private String scene() {
        return scenes[sceneIdx].trim();
    }

    private int stepMark;

    private void nextScene(final Minecraft mc) {
        if (stepJob != null && sceneIdx >= 0 && sceneIdx < scenes.length) {
            List<String> r = rep();
            savePart(mc, new ArrayList<String>(r.subList(stepMark, r.size())));
        }
        sceneIdx++;
        if (sceneIdx >= scenes.length) {
            finish(mc);
            return;
        }
        stage = Stage.SETUP;
        warmTicks = 0;
        if (stepJob != null) {
            stepMark = rep().size();
            if (apply(stepJob[sceneIdx])) warmTicks = stepJob[sceneIdx].warm;
        }
        progress(mc, "settle");
        // Everything a scene changes in the world -- time, blocks, the player's
        // position and inventory -- belongs to the integrated server, which runs
        // on its own thread. Doing it from this (client) thread races the server
        // tick: an earlier version did, and crashed it twice with
        // ConcurrentModificationExceptions (once in ChickenChunks, once in the
        // entity tracker) that were the harness's fault, not the pack's.
        final String sc = scene();
        // -Dqf.bench.reload=a,b: Iris.reload() before those scenes -- what F9 does -- so a
        // run proves a shader pack survives a live reload (Angelica rebuilds the pipeline).
        if (Arrays.asList(System.getProperty("qf.bench.reload", "").split(",")).contains(sc)) {
            try {
                Class.forName("net.coderbot.iris.Iris").getMethod("reload").invoke(null);
                log("reload: Iris.reload() before " + sc);
            } catch (Throwable t) {
                log("reload failed: " + t);
            }
        }
        serverTasks.add(new Runnable() {
            public void run() {
                try {
                    setUp(mc, sc);
                } catch (Throwable t) {
                    log(sc + " setup failed: " + t);
                    t.printStackTrace();
                }
                setupDone = true;
            }
        });
    }

    private final java.util.concurrent.ConcurrentLinkedQueue<Runnable> serverTasks =
            new java.util.concurrent.ConcurrentLinkedQueue<Runnable>();
    private volatile boolean setupDone;

    /** Runs queued scene changes on the server thread, between server ticks. */
    @SubscribeEvent
    public void onServerTick(TickEvent.ServerTickEvent event) {
        if (event.phase != TickEvent.Phase.END) return;
        Runnable r;
        while ((r = serverTasks.poll()) != null) r.run();
    }

    private static EntityPlayerMP serverPlayer(Minecraft mc) {
        MinecraftServer server = mc.getIntegratedServer();
        return (EntityPlayerMP) server.getConfigurationManager().playerEntityList.get(0);
    }

    private void setUp(Minecraft mc, String scene) {
        MinecraftServer server = mc.getIntegratedServer();
        WorldServer w = server.worldServerForDimension(0);
        EntityPlayerMP mp = serverPlayer(mc);

        server.func_147139_a(EnumDifficulty.PEACEFUL);
        w.getGameRules().setOrCreateGameRule("doDaylightCycle", "false");
        w.getGameRules().setOrCreateGameRule("doMobSpawning", "false");
        w.getWorldInfo().setRaining(false);
        w.getWorldInfo().setThundering(false);
        // Creative: the server accepts a position it did not simulate, and nothing
        // dies of falling mid-run.
        mp.setGameType(WorldSettings.GameType.CREATIVE);

        if (scene.equals("torch")) {
            w.setWorldTime(18000);
            carveTunnel(w);
            boolean lit = !"0".equals(System.getProperty("qf.bench.torch", "1"));
            ItemStack pick = new ItemStack(Items.diamond_pickaxe);
            if (lit) pick.addEnchantment(QFEnchantments.torchlight, 3);
            mp.inventory.mainInventory[0] = pick;
            mp.inventory.currentItem = 0;
            mp.inventory.markDirty();
            log("torch: holding " + (lit ? "Torchlight III" : "plain") + " diamond pickaxe");
            place(mc, TUNNEL_X0 + 0.5, TUNNEL_Y, TUNNEL_Z + 0.5, -90F, 0F, false);
        } else if (scene.equals("torch_wall")) {
            w.setWorldTime(18000);
            buildTorchHall(w);
            place(mc, TH_X0 + 1.5, TH_Y, TH_Z + 0.5, -90F, 6F, false);
        } else if (scene.equals("gallery")) {
            w.setWorldTime(Long.getLong("qf.bench.time", 10000L));
            buildGallery(w);
            place(mc, galleryCx, GALLERY_Y + 0.5, GALLERY_Z + 11.0, 180F, 4F, true);
        } else if (views.containsKey(scene)) {
            View v = views.get(scene);
            w.setWorldTime(v.time);
            double y = Double.isNaN(v.y)
                    ? w.getTopSolidOrLiquidBlock((int) Math.floor(v.x), (int) Math.floor(v.z)) + 1.0 : v.y;
            place(mc, v.x, y, v.z, v.yaw, v.pitch, true);
        } else if (scene.equals("fly")) {
            w.setWorldTime(6000);
            place(mc, FLY_X0, FLY_Y, FLY_Z, -90F, 20F, true);
        } else {
            w.setWorldTime(6000);
            int y = w.getTopSolidOrLiquidBlock(0, 0) + 2;
            place(mc, 0.5, y, 0.5, -90F, 15F, true);
        }
        mp.inventory.mainInventory[0] = scene.equals("torch") ? mp.inventory.mainInventory[0] : null;
        log(scene + ": set up");
    }

    /**
     * A sealed 3x3 tunnel: stone all round, air inside. Sealing it keeps a cave's
     * water or lava from flowing in and makes the light the only light.
     */
    private static void carveTunnel(WorldServer w) {
        for (int x = TUNNEL_X0 - 3; x <= TUNNEL_X0 + TUNNEL_LEN + 3; x++) {
            for (int dz = -2; dz <= 2; dz++) {
                for (int dy = -1; dy <= 3; dy++) {
                    boolean inside = x >= TUNNEL_X0 && x <= TUNNEL_X0 + TUNNEL_LEN
                            && Math.abs(dz) <= 1 && dy >= 0 && dy <= 2;
                    w.setBlock(x, TUNNEL_Y + dy, TUNNEL_Z + dz,
                            inside ? Blocks.air : Blocks.stone, 0, 2);
                }
            }
        }
    }

    // The torch hall: 5 wide, 4 high, 40 long, along +x. Oak frames (fence posts and a plank
    // beam) every 6 blocks, a torch on alternate posts, cobblestone floor with a plank walk,
    // and the surfaces warm light turns neon first (look bible 3): a chest, planks, a gold block.
    private static final int TH_X0 = -70, TH_Y = 14, TH_Z = 150, TH_LEN = 40;

    private static void buildTorchHall(WorldServer w) {
        for (int x = TH_X0 - 2; x <= TH_X0 + TH_LEN + 2; x++) {
            for (int dz = -4; dz <= 4; dz++) {
                for (int dy = -2; dy <= 5; dy++) {
                    boolean inside = x >= TH_X0 && x <= TH_X0 + TH_LEN && Math.abs(dz) <= 2 && dy >= 0 && dy <= 3;
                    net.minecraft.block.Block b = inside ? Blocks.air
                            : (dy == -1 && Math.abs(dz) <= 2 ? (dz == 0 ? Blocks.planks : Blocks.cobblestone) : Blocks.stone);
                    w.setBlock(x, TH_Y + dy, TH_Z + dz, b, 0, 2);
                }
            }
        }
        int frame = 0;
        for (int x = TH_X0 + 4; x <= TH_X0 + TH_LEN - 2; x += 6, frame++) {
            for (int dy = 0; dy <= 2; dy++) {
                w.setBlock(x, TH_Y + dy, TH_Z - 2, Blocks.fence, 0, 2);
                w.setBlock(x, TH_Y + dy, TH_Z + 2, Blocks.fence, 0, 2);
            }
            for (int dz = -2; dz <= 2; dz++) w.setBlock(x, TH_Y + 3, TH_Z + dz, Blocks.planks, 0, 2);
            // A wall torch beside the post, on the side the camera sees (meta 3 points south,
            // off the north wall; 4 points north, off the south wall). Alternating sides.
            boolean north = frame % 2 == 0;
            w.setBlock(x - 1, TH_Y + 2, north ? TH_Z - 2 : TH_Z + 2, Blocks.torch, north ? 3 : 4, 3);
        }
        w.setBlock(TH_X0 + 7, TH_Y, TH_Z + 2, Blocks.chest, 2, 2);
        w.setBlock(TH_X0 + 8, TH_Y, TH_Z + 2, Blocks.planks, 0, 2);
        w.setBlock(TH_X0 + 8, TH_Y + 1, TH_Z + 2, Blocks.planks, 0, 2);
        w.setBlock(TH_X0 + 13, TH_Y, TH_Z - 2, Blocks.gold_block, 0, 2);
        w.setBlock(TH_X0 + 14, TH_Y, TH_Z - 2, Blocks.log, 0, 2);
    }

    // The gallery: a wall of blocks on a floating platform, so a texture pack or
    // shader can be judged on modded blocks next to their vanilla counterparts.
    // -Dqf.bench.gallery=<file>: one block per line as modid:name or
    // modid:name@meta; a line "--" starts the next row up. Columns are two apart
    // so the afternoon sun (from -X) rakes across every face the camera sees.
    private static final int GALLERY_X = 100, GALLERY_Y = 110, GALLERY_Z = 100;
    private double galleryCx = GALLERY_X;
    private int galleryRows, galleryCols;

    private void buildGallery(WorldServer w) {
        List<List<String>> rows = new ArrayList<List<String>>();
        rows.add(new ArrayList<String>());
        try {
            for (String line : java.nio.file.Files.readAllLines(
                    new File(System.getProperty("qf.bench.gallery")).toPath(),
                    java.nio.charset.StandardCharsets.UTF_8)) {
                line = line.trim();
                if (line.isEmpty() || line.startsWith("#")) continue;
                if (line.equals("--")) rows.add(new ArrayList<String>());
                else rows.get(rows.size() - 1).add(line);
            }
        } catch (Exception e) {
            log("gallery: cannot read list: " + e);
        }
        int cols = 0;
        for (List<String> r : rows) cols = Math.max(cols, r.size());
        galleryRows = rows.size();
        galleryCols = cols;
        galleryCx = GALLERY_X + (cols - 1) + 0.5;

        // Clear the air and lay a floor, larger than the wall, under the camera too.
        for (int x = GALLERY_X - 4; x <= GALLERY_X + 2 * cols + 2; x++) {
            for (int z = GALLERY_Z - 3; z <= GALLERY_Z + 14; z++) {
                w.setBlock(x, GALLERY_Y - 1, z, Blocks.grass, 0, 2);
                for (int y = GALLERY_Y; y <= GALLERY_Y + galleryRows + 4; y++) {
                    w.setBlock(x, y, z, Blocks.air, 0, 2);
                }
            }
        }
        int placed = 0;
        for (int r = 0; r < rows.size(); r++) {
            for (int c = 0; c < rows.get(r).size(); c++) {
                String spec = rows.get(r).get(c);
                int meta = 0;
                int at = spec.indexOf('@');
                if (at > 0) {
                    meta = Integer.parseInt(spec.substring(at + 1));
                    spec = spec.substring(0, at);
                }
                net.minecraft.block.Block b = net.minecraft.block.Block.getBlockFromName(spec);
                if (b == null || b == Blocks.air) {
                    log("gallery: no block " + spec);
                    continue;
                }
                w.setBlock(GALLERY_X + 2 * c, GALLERY_Y + r, GALLERY_Z, b, meta, 2);
                placed++;
            }
        }
        log("gallery: placed " + placed + " blocks in " + galleryRows + " rows");
    }

    /** Wide shot, then a close one on the middle of the wall, during the gallery scene. */
    private void galleryShots(Minecraft mc) {
        if (ticks == 20) shot(mc, "wide");
        if (ticks == 30) {
            px = galleryCx;
            pz = GALLERY_Z + 4.5;
            py = GALLERY_Y + galleryRows / 2.0 - 1.0;
            pitch = 0F;
        }
        if (ticks == 160) shot(mc, "close");
    }

    private void shot(Minecraft mc, String what) {
        String name = "bench-" + tag() + "-" + what + ".png";
        try {
            net.minecraft.util.ScreenShotHelper.saveScreenshot(mc.mcDataDir, name,
                    mc.displayWidth, mc.displayHeight, mc.getFramebuffer());
            rep().add("  screenshot screenshots/" + name);
        } catch (Throwable t) {
            log("screenshot failed: " + t);
        }
    }

    private double px, py, pz;
    private float yaw, pitch;
    private boolean flying;

    private void place(Minecraft mc, double x, double y, double z, float yaw, float pitch,
                       boolean fly) {
        // Server thread (from setUp). The client player is pinned by hold(),
        // which the client tick calls every tick while the scene settles.
        px = x; py = y; pz = z; this.yaw = yaw; this.pitch = pitch; flying = fly;
        serverPlayer(mc).playerNetServerHandler.setPlayerLocation(x, y, z, yaw, pitch);
    }

    /** Pins the player where the scene put them, so settling happens in place. */
    private void hold(Minecraft mc) {
        if (mc.thePlayer == null) return;
        // F1 for view scenes: review frames carry no HUD for the critic to mistake for the world.
        mc.gameSettings.hideGUI = sceneIdx >= 0 && sceneIdx < scenes.length
                && (views.containsKey(scene()) || scene().equals("gallery") || scene().equals("torch_wall"));
        mc.thePlayer.capabilities.isFlying = flying;
        mc.thePlayer.motionX = mc.thePlayer.motionY = mc.thePlayer.motionZ = 0;
        mc.thePlayer.setPositionAndRotation(px, py + mc.thePlayer.yOffset, pz, yaw, pitch);
        mc.thePlayer.rotationYawHead = yaw;
    }

    private void move(Minecraft mc) {
        String s = scene();
        if (s.equals("fly")) px += FLY_SPEED;
        else if (s.equals("torch")) px += SPRINT;
        else if (s.equals("gallery")) galleryShots(mc);
        hold(mc);
    }

    /**
     * Who keeps asking for chunks to be rebuilt. A world that has finished loading
     * and is not changing should rebuild nothing; this one rebuilt ~36 chunks a
     * second standing still. Counts every render-update request by the block at
     * that spot and keeps the first call stack per block, which says whether it
     * came off the network (a server-side change) or from client code.
     */
    private static final class UpdateTally implements net.minecraft.world.IWorldAccess {
        final net.minecraft.world.World world;
        final java.util.Map<String, int[]> counts = new java.util.HashMap<String, int[]>();
        final java.util.Map<String, String> firstStack = new java.util.HashMap<String, String>();
        int ranges;

        UpdateTally(net.minecraft.world.World world) {
            this.world = world;
        }

        private void hit(String kind, int x, int y, int z) {
            net.minecraft.block.Block b = world.getBlock(x, y, z);
            String key = kind + " " + net.minecraft.block.Block.blockRegistry.getNameForObject(b);
            int[] c = counts.get(key);
            if (c == null) {
                counts.put(key, c = new int[1]);
                StringBuilder sb = new StringBuilder();
                StackTraceElement[] st = new Throwable().getStackTrace();
                for (int i = 2; i < Math.min(st.length, 14); i++) sb.append("\n      at ").append(st[i]);
                firstStack.put(key, sb.toString());
            }
            c[0]++;
        }

        void clear() {
            counts.clear();
            firstStack.clear();
            ranges = 0;
        }

        List<String> top(int n) {
            List<java.util.Map.Entry<String, int[]>> es =
                    new ArrayList<java.util.Map.Entry<String, int[]>>(counts.entrySet());
            java.util.Collections.sort(es, new java.util.Comparator<java.util.Map.Entry<String, int[]>>() {
                public int compare(java.util.Map.Entry<String, int[]> a, java.util.Map.Entry<String, int[]> b) {
                    return b.getValue()[0] - a.getValue()[0];
                }
            });
            List<String> out = new ArrayList<String>();
            out.add("  range updates " + ranges);
            for (int i = 0; i < Math.min(n, es.size()); i++) {
                String k = es.get(i).getKey();
                out.add(String.format("  %6d  %s", es.get(i).getValue()[0], k));
                if (i < 5) out.add("    first call:" + firstStack.get(k));
            }
            return out;
        }

        @Override public void markBlockForUpdate(int x, int y, int z) { hit("block", x, y, z); }
        @Override public void markBlockForRenderUpdate(int x, int y, int z) { hit("render", x, y, z); }
        @Override public void markBlockRangeForRenderUpdate(int a, int b, int c, int d, int e, int f) { ranges++; }
        @Override public void playSound(String s, double x, double y, double z, float v, float p) { }
        @Override public void playSoundToNearExcept(net.minecraft.entity.player.EntityPlayer pl, String s,
                double x, double y, double z, float v, float p) { }
        @Override public void spawnParticle(String s, double x, double y, double z, double a, double b, double c) { }
        @Override public void onEntityCreate(net.minecraft.entity.Entity e) { }
        @Override public void onEntityDestroy(net.minecraft.entity.Entity e) { }
        @Override public void playRecord(String s, int x, int y, int z) { }
        @Override public void broadcastSound(int a, int x, int y, int z, int b) { }
        @Override public void playAuxSFX(net.minecraft.entity.player.EntityPlayer p, int a, int x, int y, int z, int b) { }
        @Override public void destroyBlockPartially(int a, int x, int y, int z, int b) { }
        @Override public void onStaticEntitiesChanged() { }
    }

    private UpdateTally tally;

    private static int parseChunkUpdates(String debug) {
        try {
            String[] parts = debug.split(",");
            return Integer.parseInt(parts[1].trim().split(" ")[0]);
        } catch (Exception e) {
            return 0;
        }
    }

    private void summarise(Minecraft mc) {
        int n = frames.size();
        if (n == 0) {
            rep().add(String.format("%-7s no frames recorded", scene()));
            return;
        }
        long[] ns = new long[n];
        long total = 0;
        for (int i = 0; i < n; i++) {
            ns[i] = frames.get(i);
            total += ns[i];
        }
        Arrays.sort(ns);
        double meanFps = n / (total / 1e9);
        int worst1 = Math.max(1, n / 100);
        long slowSum = 0;
        for (int i = n - worst1; i < n; i++) slowSum += ns[i];
        double low1 = worst1 / (slowSum / 1e9);
        int over33 = 0;
        for (long v : ns) if (v > 33_000_000L) over33++;
        String line = String.format(
                "%-7s frames %5d  mean %6.1f fps  p50 %6.2f ms  p99 %6.2f ms  1%%low %6.1f fps"
                        + "  worst %7.1f ms  >33ms %4d  chunkUpdates %5d",
                scene(), n, meanFps, ns[n / 2] / 1e6, ns[(int) (n * 0.99)] / 1e6, low1,
                ns[n - 1] / 1e6, over33, chunkUpdates);
        log((stepJob != null ? tag() + " " : "") + line);
        rep().add(line);
        rep().add("  wall " + System.currentTimeMillis());
        // A picture of the static view, so a setting that buys frames can be
        // judged on what it costs to look at, not just what it costs to draw.
        if (scene().equals("static")) {
            String name = "bench-" + tag() + ".png";
            try {
                net.minecraft.util.ScreenShotHelper.saveScreenshot(mc.mcDataDir, name,
                        mc.displayWidth, mc.displayHeight, mc.getFramebuffer());
                rep().add("  screenshot screenshots/" + name);
            } catch (Throwable t) {
                log("screenshot failed: " + t);
            }
        }
        if (tally != null) {
            for (String t : tally.top(12)) {
                log(t);
                rep().add(t);
            }
        }
    }

    private void finish(Minecraft mc) {
        stage = Stage.DONE;
        progress(mc, "done");
        if (stepJob != null) {
            for (Job j : jobs.values()) writeResult(mc, j.tag, j.report);
            mc.shutdown();
            return;
        }
        String tag = System.getProperty("qf.bench.tag", "bench");
        try {
            File dir = new File(mc.mcDataDir, "bench");
            dir.mkdirs();
            PrintWriter out = new PrintWriter(new FileWriter(new File(dir, tag + ".txt")));
            out.println("tag " + tag + "  display " + mc.displayWidth + "x" + mc.displayHeight);
            for (String r : report) out.println(r);
            out.close();
            log("wrote bench/" + tag + ".txt");
        } catch (Throwable t) {
            log("could not write results: " + t);
        }
        mc.shutdown();
    }

    private void writeResult(Minecraft mc, String tag, List<String> lines) {
        try {
            File dir = new File(mc.mcDataDir, "bench");
            dir.mkdirs();
            PrintWriter out = new PrintWriter(new FileWriter(new File(dir, tag + ".txt")));
            out.println("tag " + tag + "  display " + mc.displayWidth + "x" + mc.displayHeight);
            for (String r : lines) out.println(r);
            out.close();
            new File(dir, tag + ".part").delete();
            log("wrote bench/" + tag + ".txt");
        } catch (Throwable t) {
            log("could not write results for " + tag + ": " + t);
        }
    }
}
