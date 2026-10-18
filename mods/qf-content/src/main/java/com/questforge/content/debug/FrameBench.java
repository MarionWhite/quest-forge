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

    public FrameBench() {
        scenes = System.getProperty("qf.bench.scenes", "static,fly,torch").split(",");
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
            quiet = n == 0 ? quiet + 1 : 0;
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
                if ((quiet >= 3 && ticks > 100) || ticks > SETTLE_MAX) {
                    log(scene() + ": settled after " + ticks + " ticks; measuring");
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
                if (ticks >= (mv != null ? mv.ticks : MEASURE_TICKS)) {
                    summarise(mc);
                    if (mv != null || scene().equals("torch")) {
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

    private void nextScene(final Minecraft mc) {
        sceneIdx++;
        if (sceneIdx >= scenes.length) {
            finish(mc);
            return;
        }
        stage = Stage.SETUP;
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
        String name = "bench-" + System.getProperty("qf.bench.tag", "bench") + "-" + what + ".png";
        try {
            net.minecraft.util.ScreenShotHelper.saveScreenshot(mc.mcDataDir, name,
                    mc.displayWidth, mc.displayHeight, mc.getFramebuffer());
            report.add("  screenshot screenshots/" + name);
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
                && (views.containsKey(scene()) || scene().equals("gallery"));
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
            report.add(String.format("%-7s no frames recorded", scene()));
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
        log(line);
        report.add(line);
        report.add("  wall " + System.currentTimeMillis());
        // A picture of the static view, so a setting that buys frames can be
        // judged on what it costs to look at, not just what it costs to draw.
        if (scene().equals("static")) {
            String name = "bench-" + System.getProperty("qf.bench.tag", "bench") + ".png";
            try {
                net.minecraft.util.ScreenShotHelper.saveScreenshot(mc.mcDataDir, name,
                        mc.displayWidth, mc.displayHeight, mc.getFramebuffer());
                report.add("  screenshot screenshots/" + name);
            } catch (Throwable t) {
                log("screenshot failed: " + t);
            }
        }
        if (tally != null) {
            for (String t : tally.top(12)) {
                log(t);
                report.add(t);
            }
        }
    }

    private void finish(Minecraft mc) {
        stage = Stage.DONE;
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
}
