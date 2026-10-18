package com.questforge;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.lang.reflect.Field;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.IdentityHashMap;
import java.util.List;
import java.util.Map;
import java.util.Properties;
import java.util.Random;
import java.util.Set;
import java.util.TreeMap;
import java.util.WeakHashMap;

import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;

import cpw.mods.fml.common.Loader;

/**
 * Runtime half of {@link RwgPaintTransformer}: RWG's patched
 * ChunkGeneratorRealistic calls into this.
 *
 * Inside the painted rectangle (config/qftweaks-rwgpaint.cfg), a chunk is
 * decorated by the biomes stored in the chunks themselves -- the biomes
 * WorldPainter painted -- instead of by RWG's noise biome, and RWG's
 * noise-keyed snow/ice pass is replaced by vanilla's per-column one, which
 * reads the stored biome's temperature. Outside the rectangle nothing here
 * runs and RWG behaves exactly as stock.
 *
 * Safety check: a chunk that RWG itself generated inside the rectangle during
 * this server session (a hole in the export, or a rectangle that is larger
 * than the export) keeps stock RWG decoration. Painted chunks come from disk,
 * never through RWG's provideChunk.
 *
 * Compiled against no Minecraft or RWG classes (the build classpath has only
 * the obfuscated client jar), so everything is reflection on SRG names, with
 * MCP names as a fallback for a deobfuscated dev environment. All of it is
 * looked up once; on any lookup failure the hook disables itself and RWG runs
 * stock.
 */
public final class RwgPaintHook {

    private static final Logger LOG = LogManager.getLogger("QuestForgeTweaks");

    private RwgPaintHook() {
    }

    // ---- config -------------------------------------------------------------

    private static boolean configLoaded;
    private static boolean enabled;
    private static int minX = -16384, maxX = 16384, minZ = -16384, maxZ = 16384;
    private static final List<String> preferredRwg = new ArrayList<String>();

    /** RWG's own variant to use for a painted RWG base biome, when several share it. */
    private static final String DEFAULT_RWG_PREFERENCE = "RealisticBiomeDesert,RealisticBiomeTaigaPlains,"
            + "RealisticBiomeSnowHills,RealisticBiomeSavanna,RealisticBiomeHotForest,RealisticBiomeTundraPlains,"
            + "RealisticBiomeWoodHills,RealisticBiomeJungleHills,RealisticBiomeOasis,RealisticBiomePolar";

    private static synchronized void loadConfig() {
        if (configLoaded) return;
        configLoaded = true;
        File f = null;
        try {
            f = new File(Loader.instance().getConfigDir(), "qftweaks-rwgpaint.cfg");
            Properties p = new Properties();
            p.setProperty("enabled", "true");
            p.setProperty("minBlockX", "-16384");
            p.setProperty("maxBlockX", "16384");
            p.setProperty("minBlockZ", "-16384");
            p.setProperty("maxBlockZ", "16384");
            p.setProperty("rwgPreferred", DEFAULT_RWG_PREFERENCE);
            if (f.isFile()) {
                InputStream in = new FileInputStream(f);
                try {
                    p.load(in);
                } finally {
                    in.close();
                }
            } else {
                OutputStream out = new FileOutputStream(f);
                try {
                    p.store(out, " QuestForge Tweaks: decorate the painted (WorldPainter) area of an RWG world by"
                            + " its stored biomes.\n"
                            + " A chunk whose 16x16 lies inside [minBlockX,maxBlockX) x [minBlockZ,maxBlockZ) is"
                            + " decorated by\n"
                            + " the biome painted in it, and RWG's noise-keyed snow/ice pass is replaced by"
                            + " vanilla's.\n"
                            + " Outside the rectangle RWG is untouched. See docs/design/world/poc.md.\n"
                            + " rwgPreferred: which RWG variant decorates a painted RWG base biome (first match"
                            + " wins).");
                } finally {
                    out.close();
                }
            }
            enabled = Boolean.parseBoolean(p.getProperty("enabled").trim());
            minX = Integer.parseInt(p.getProperty("minBlockX").trim());
            maxX = Integer.parseInt(p.getProperty("maxBlockX").trim());
            minZ = Integer.parseInt(p.getProperty("minBlockZ").trim());
            maxZ = Integer.parseInt(p.getProperty("maxBlockZ").trim());
            for (String s : p.getProperty("rwgPreferred", "").split(",")) {
                if (s.trim().length() > 0) preferredRwg.add(s.trim());
            }
            LOG.info("[QuestForgeTweaks] RWG paint hook: {} for blocks x [{}, {}) z [{}, {}) ({})",
                    enabled ? "enabled" : "disabled", minX, maxX, minZ, maxZ, f);
        } catch (Throwable t) {
            enabled = false;
            LOG.warn("[QuestForgeTweaks] RWG paint hook: could not read " + f + "; hook disabled, RWG runs stock.",
                    t);
        }
    }

    private static boolean inRect(int blockX, int blockZ) {
        return blockX >= minX && blockX + 16 <= maxX && blockZ >= minZ && blockZ + 16 <= maxZ;
    }

    private static long key(int cx, int cz) {
        return ((long) cx << 32) ^ (cz & 0xffffffffL);
    }

    // ---- safety check: chunks RWG generated this session ----------------------

    /** Per world: chunk keys inside the rectangle that RWG's provideChunk generated. */
    private static final Map<Object, Set<Long>> generated = Collections
            .synchronizedMap(new WeakHashMap<Object, Set<Long>>());
    private static Field genWorld;

    /** Called at the top of ChunkGeneratorRealistic.provideChunk(cx, cz). */
    public static void generated(Object generator, int cx, int cz) {
        if (!configLoaded) loadConfig();
        if (!enabled || !inRect(cx << 4, cz << 4)) return;
        try {
            if (genWorld == null) {
                Field f = generator.getClass().getDeclaredField("worldObj");
                f.setAccessible(true);
                genWorld = f;
            }
            Object world = genWorld.get(generator);
            synchronized (generated) {
                Set<Long> s = generated.get(world);
                if (s == null) {
                    s = new HashSet<Long>();
                    generated.put(world, s);
                }
                s.add(key(cx, cz));
            }
        } catch (Throwable t) {
            fail("reading ChunkGeneratorRealistic.worldObj", t);
        }
    }

    private static boolean generatedThisSession(Object world, int cx, int cz) {
        synchronized (generated) {
            Set<Long> s = generated.get(world);
            return s != null && s.contains(key(cx, cz));
        }
    }

    // ---- decoration ---------------------------------------------------------

    /** Painted chunks decorated in a populate() still running; their snow pass comes later. Keyed by chunk. */
    private static final Map<Long, Object> pendingSnow = new HashMap<Long, Object>();
    private static long paintedCount;

    /**
     * Stands in front of every RealisticBiomeBase.rDecorate call in
     * ChunkGeneratorRealistic.populate. Returns false to let RWG's own call run
     * (outside the painted area). Inside it, decorates the chunk once by its
     * stored biomes and returns true for every call, so RWG's noise biomes are
     * skipped.
     */
    public static boolean decoratePainted(Object world, Random rand, int x, int z, Object perlin, Object cell,
            float river) {
        if (!configLoaded) loadConfig();
        if (!enabled || !inRect(x, z)) return false;
        int cx = x >> 4, cz = z >> 4;
        if (generatedThisSession(world, cx, cz)) return false;
        if (!lookup()) return false;
        Long k = key(cx, cz);
        if (pendingSnow.containsKey(k)) return true; // already decorated in this populate()
        pendingSnow.put(k, world);
        decorate(world, rand, x, z, perlin, cell, river);
        paintedCount++;
        if (paintedCount == 1 || paintedCount % 10000 == 0) {
            LOG.info("[QuestForgeTweaks] RWG paint hook: {} painted chunk(s) decorated by stored biome (latest {},{}).",
                    paintedCount, cx, cz);
        }
        return true;
    }

    /**
     * Wraps RWG's "snow &lt; 0.59f" test. For a painted chunk, runs vanilla's
     * stored-biome ice and snow pass and returns 1 so RWG's own pass is
     * skipped; otherwise returns RWG's value unchanged.
     */
    public static float snow(float snow, int cx, int cz) {
        if (pendingSnow.isEmpty()) return snow;
        Object world = pendingSnow.remove(key(cx, cz));
        if (world == null) return snow;
        try {
            iceAndSnow(world, cx << 4, cz << 4);
        } catch (Throwable t) {
            rethrow(t);
        }
        return 1f;
    }

    private static void decorate(Object world, Random rand, int x, int z, Object perlin, Object cell, float river) {
        try {
            // Stored biomes over the population window [x+8, x+24) x [z+8, z+24),
            // which spans the four loaded chunks population touches. 8x8 samples.
            IdentityHashMap<Object, int[]> counts = new IdentityHashMap<Object, int[]>();
            for (int i = 0; i < 8; i++) {
                for (int j = 0; j < 8; j++) {
                    Object b = getBiome.invoke(world, x + 9 + 2 * i, z + 9 + 2 * j);
                    if (b == null) continue;
                    int[] c = counts.get(b);
                    if (c == null) counts.put(b, c = new int[1]);
                    c[0]++;
                }
            }
            Object dominant = null;
            int best = -1;
            TreeMap<Integer, Object> byId = new TreeMap<Integer, Object>();
            for (Map.Entry<Object, int[]> e : counts.entrySet()) {
                byId.put(biomeID.getInt(e.getKey()), e.getKey());
                if (e.getValue()[0] > best) {
                    best = e.getValue()[0];
                    dominant = e.getKey();
                }
            }
            for (Object biome : byId.values()) {
                float strength = counts.get(biome)[0] / 64f;
                // RWG decorates every biome over 0.3 of the blend; make sure the
                // chunk's main biome always decorates, as vanilla's would.
                if (biome == dominant && strength <= 0.3f) strength = 0.31f;
                Object realistic = realisticFor(biome);
                if (realistic != null) {
                    rDecorate.invoke(realistic, world, rand, x, z, perlin, cell, strength, river);
                } else if (strength > 0.3f) {
                    decorateBiome.invoke(biome, world, rand, x, z);
                }
            }
        } catch (Throwable t) {
            rethrow(t);
        }
    }

    /** Vanilla ChunkProviderGenerate's ICE step: freeze water and lay snow by each column's stored biome. */
    private static void iceAndSnow(Object world, int x, int z) throws Exception {
        x += 8;
        z += 8;
        for (int i = 0; i < 16; i++) {
            for (int j = 0; j < 16; j++) {
                int y = (Integer) precipHeight.invoke(world, x + i, z + j);
                if ((Boolean) freezable.invoke(world, x + i, y - 1, z + j)) {
                    setBlock.invoke(world, x + i, y - 1, z + j, ice, 0, 2);
                }
                if ((Boolean) canSnow.invoke(world, x + i, y, z + j, true)) {
                    setBlock.invoke(world, x + i, y, z + j, snowLayer, 0, 2);
                }
            }
        }
    }

    // ---- biome -> RWG decorator ------------------------------------------------

    private static Map<Object, Object> realisticByBiome;

    /**
     * The RealisticBiomeBase whose base biome is the painted one: RWG's wrapper
     * for a BoP biome (its rDecorate calls the BoP decorator plus RWG's edits),
     * or one of RWG's own variants for an RWG base biome. Null for vanilla and
     * unsupported biomes, which then get their own decorate().
     */
    private static Object realisticFor(Object biome) throws Exception {
        if (realisticByBiome == null) {
            Map<Object, List<Object>> all = new IdentityHashMap<Object, List<Object>>();
            for (int i = 0; i < 256; i++) {
                Object r = rGetBiome.invoke(null, i);
                if (r == null) continue;
                String n = r.getClass().getSimpleName();
                if (n.contains("Test")) continue; // RWG's placeholder biomes
                Object base = rBaseBiome.get(r);
                if (base == null) continue;
                List<Object> l = all.get(base);
                if (l == null) all.put(base, l = new ArrayList<Object>());
                l.add(r);
            }
            Map<Object, Object> m = new IdentityHashMap<Object, Object>();
            for (Map.Entry<Object, List<Object>> e : all.entrySet()) {
                Object pick = e.getValue().get(0);
                outer: for (String pref : preferredRwg) {
                    for (Object r : e.getValue()) {
                        if (r.getClass().getSimpleName().equals(pref)) {
                            pick = r;
                            break outer;
                        }
                    }
                }
                m.put(e.getKey(), pick);
            }
            realisticByBiome = m;
        }
        return realisticByBiome.get(biome);
    }

    // ---- reflection -----------------------------------------------------------

    private static boolean looked, ok;
    private static Method getBiome, decorateBiome, rDecorate, rGetBiome;
    private static Method precipHeight, freezable, canSnow, setBlock;
    private static Field biomeID, rBaseBiome;
    private static Object ice, snowLayer;

    private static boolean lookup() {
        if (looked) return ok;
        looked = true;
        try {
            ClassLoader cl = RwgPaintHook.class.getClassLoader();
            Class<?> world = Class.forName("net.minecraft.world.World", false, cl);
            Class<?> biome = Class.forName("net.minecraft.world.biome.BiomeGenBase", false, cl);
            Class<?> block = Class.forName("net.minecraft.block.Block", false, cl);
            Class<?> blocks = Class.forName("net.minecraft.init.Blocks", true, cl);
            Class<?> realistic = Class.forName("rwg.biomes.realistic.RealisticBiomeBase", false, cl);

            getBiome = method(world, "func_72807_a", "getBiomeGenForCoords", int.class, int.class);
            decorateBiome = method(biome, "func_76728_a", "decorate", world, Random.class, int.class, int.class);
            precipHeight = method(world, "func_72874_g", "getPrecipitationHeight", int.class, int.class);
            freezable = method(world, "func_72884_u", "isBlockFreezable", int.class, int.class, int.class);
            canSnow = method(world, "func_147478_e", "func_147478_e", int.class, int.class, int.class,
                    boolean.class);
            setBlock = method(world, "func_147465_d", "setBlock", int.class, int.class, int.class, block,
                    int.class, int.class);
            biomeID = field(biome, "field_76756_M", "biomeID");
            ice = field(blocks, "field_150432_aD", "ice").get(null);
            snowLayer = field(blocks, "field_150431_aC", "snow_layer").get(null);

            for (Method m : realistic.getMethods()) {
                if (m.getName().equals("rDecorate") && m.getParameterTypes().length == 8) rDecorate = m;
            }
            if (rDecorate == null) throw new NoSuchMethodException("RealisticBiomeBase.rDecorate");
            rGetBiome = realistic.getMethod("getBiome", int.class);
            rBaseBiome = realistic.getField("baseBiome");
            ok = true;
        } catch (Throwable t) {
            fail("looking up Minecraft/RWG members", t);
        }
        return ok;
    }

    private static Method method(Class<?> c, String srg, String mcp, Class<?>... args) throws Exception {
        Method m;
        try {
            m = c.getDeclaredMethod(srg, args);
        } catch (NoSuchMethodException e) {
            m = c.getDeclaredMethod(mcp, args);
        }
        m.setAccessible(true);
        return m;
    }

    private static Field field(Class<?> c, String srg, String mcp) throws Exception {
        Field f;
        try {
            f = c.getDeclaredField(srg);
        } catch (NoSuchFieldException e) {
            f = c.getDeclaredField(mcp);
        }
        f.setAccessible(true);
        return f;
    }

    private static void fail(String what, Throwable t) {
        enabled = false;
        ok = false;
        looked = true;
        LOG.error("[QuestForgeTweaks] RWG paint hook failed " + what + "; hook disabled, RWG runs stock.", t);
    }

    /** A decorator that throws would have thrown under stock RWG too; pass it on unwrapped. */
    private static void rethrow(Throwable t) {
        if (t instanceof InvocationTargetException && t.getCause() != null) t = t.getCause();
        if (t instanceof RuntimeException) throw (RuntimeException) t;
        if (t instanceof Error) throw (Error) t;
        throw new RuntimeException(t);
    }
}
