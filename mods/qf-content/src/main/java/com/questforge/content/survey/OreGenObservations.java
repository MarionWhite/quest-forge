package com.questforge.content.survey;

import java.util.Map;
import java.util.TreeMap;

import net.minecraft.block.Block;

/**
 * The exact generation parameters of every ore, gathered by watching veins be placed.
 *
 * This is the companion to the block counter, and it answers a different question.
 * Counting blocks measures the RESULT -- how much ore ends up in the ground -- which
 * is what the Transmuter pool ultimately wants, but it converges slowly for rare
 * ores because it is a noisy sample of a random process.
 *
 * This measures the CAUSE: how many veins per chunk, of what size, in what height
 * band. Those are not random, they are the arguments the generator was written with,
 * so a few hundred chunks pin them down exactly. Twenty coal veins per chunk of size
 * sixteen between y=0 and y=128 is not an estimate that gets better with more
 * sampling -- it is the parameter itself, read off the running game.
 *
 * The two instruments cross-check each other. Where both see an ore, veins-per-chunk
 * times vein size should predict the measured block density (allowing for the
 * overlap that stops a vein ever placing its full nominal count). Where they
 * disagree, something is wrong and worth knowing about.
 *
 * The limitation, stated plainly: this only sees ore placed through the standard
 * vein generator. A mod with an entirely custom generator is invisible here, which
 * is exactly why the block counter is still worth running alongside it.
 */
public class OreGenObservations {

    /** What was seen for one ore in one dimension. */
    public static class Vein {
        public long veins;
        public long totalSize;
        public int minY = Integer.MAX_VALUE;
        public int maxY = Integer.MIN_VALUE;

        /**
         * Biome name -> veins rooted in it.
         *
         * Counted at the vein's origin, the same place the vein itself is
         * attributed, so the biome shares are directly comparable to the rate.
         * An ore that only generates in one biome shows exactly one entry here,
         * which is the thing no registry will tell you.
         */
        public final Map<String, Integer> biomes = new TreeMap<String, Integer>();

        public double averageSize() {
            return veins == 0 ? 0 : (double) totalSize / veins;
        }

        void addBiome(String name, int n) {
            if (name == null) return;
            Integer had = biomes.get(name);
            biomes.put(name, Integer.valueOf((had == null ? 0 : had.intValue()) + n));
        }
    }

    /** dimension -> (blockId<<4|meta -> what was seen). */
    private static final Map<Integer, Map<Integer, Vein>> BY_DIM =
            new TreeMap<Integer, Map<Integer, Vein>>();

    /**
     * Chunks measured WHILE the vein recorder was active, per dimension.
     *
     * Its own denominator rather than the survey's cumulative chunk count, because
     * those are not the same number. A survey file can carry hundreds of thousands
     * of chunks counted before this recorder existed; dividing veins seen in this
     * run by that total understates every rate by whatever the ratio happens to be.
     * It has to be chunks-that-were-watched, and only this class knows which those
     * were.
     */
    private static final Map<Integer, Integer> WATCHED =
            new TreeMap<Integer, Integer>();

    /**
     * Veins seen in the patch being generated, held per chunk until it is known
     * whether that chunk's blocks were counted.
     *
     * This is what makes the two instruments comparable. Previously veins were
     * committed the moment they were placed, while blocks were counted later and
     * only for chunks that passed a populated check -- so the two described
     * different sets of chunks and no ratio between them meant anything. Buffering
     * by chunk and committing only the ones that were block-counted makes the
     * numerator and the denominator the same chunks by construction, with no
     * assumption about how many chunks "should" have populated.
     */
    private static final Map<Long, Map<Integer, Vein>> PENDING =
            new java.util.HashMap<Long, Map<Integer, Vein>>();

    private static boolean recording;

    private static long chunkKey(int cx, int cz) {
        return ((long) cx << 32) ^ (cz & 0xFFFFFFFFL);
    }

    /** Accepts one chunk's buffered veins into the results. */
    public static void commitChunk(int dimension, int cx, int cz) {
        Map<Integer, Vein> pending = PENDING.remove(Long.valueOf(chunkKey(cx, cz)));

        // The chunk counts towards the denominator whether or not it held ore --
        // a chunk with no veins in it is a real observation.
        WATCHED.put(Integer.valueOf(dimension), Integer.valueOf(watched(dimension) + 1));
        if (pending == null) return;

        Map<Integer, Vein> perDim = BY_DIM.get(Integer.valueOf(dimension));
        if (perDim == null) {
            perDim = new TreeMap<Integer, Vein>();
            BY_DIM.put(Integer.valueOf(dimension), perDim);
        }

        for (Map.Entry<Integer, Vein> e : pending.entrySet()) {
            Vein into = perDim.get(e.getKey());
            if (into == null) {
                into = new Vein();
                perDim.put(e.getKey(), into);
            }
            Vein from = e.getValue();
            into.veins += from.veins;
            into.totalSize += from.totalSize;
            if (from.minY < into.minY) into.minY = from.minY;
            if (from.maxY > into.maxY) into.maxY = from.maxY;
            for (Map.Entry<String, Integer> b : from.biomes.entrySet()) {
                into.addBiome(b.getKey(), b.getValue().intValue());
            }
        }
    }

    /** Drops whatever was buffered for chunks that were never counted. */
    public static void discardPending() {
        PENDING.clear();
    }

    /**
     * Only true while a survey is generating chunks.
     *
     * Checked before anything else because this is called from inside worldgen: on a
     * live server with no survey running it must be a single field read.
     */
    public static boolean isRecording() {
        return recording;
    }

    public static void setRecording(boolean value) {
        recording = value;
    }

    public static Map<Integer, Map<Integer, Vein>> byDimension() {
        return BY_DIM;
    }

    /**
     * Expected ore blocks per chunk, summed over every dimension measured.
     *
     * veins-per-chunk x vein-size is the generator's own intent, before the
     * overlap that stops a vein placing its full nominal count. That shortfall is a
     * property of the terrain rather than of the ore -- roughly uniform within a
     * dimension -- so it cancels out of the RELATIVE weights, which is all a
     * weighted pool needs. Using it rather than the block counts means rare ores
     * get an exact figure instead of a noisy one.
     */
    public static Map<Integer, Double> expectedBlocksPerChunk() {
        Map<Integer, Double> out = new java.util.HashMap<Integer, Double>();

        for (Map.Entry<Integer, Map<Integer, Vein>> dim : BY_DIM.entrySet()) {
            int chunks = watched(dim.getKey().intValue());
            if (chunks <= 0) continue;

            for (Map.Entry<Integer, Vein> e : dim.getValue().entrySet()) {
                Vein v = e.getValue();
                double perChunk = (v.totalSize / (double) chunks);
                Double running = out.get(e.getKey());
                out.put(e.getKey(), Double.valueOf(
                        (running == null ? 0.0 : running.doubleValue()) + perChunk));
            }
        }
        return out;
    }

    // ---- Persistence -----------------------------------------------------

    private static final String FILE_NAME = "qfcontent-oreveins.txt";

    private static java.io.File file;

    public static void setConfigDir(java.io.File configDir) {
        file = new java.io.File(configDir, FILE_NAME);
    }

    public static java.io.File file() {
        return file;
    }

    /** Written per dimension, so uneven sampling stays harmless. */
    public static void save() {
        if (file == null) return;

        java.io.PrintWriter out = null;
        try {
            out = new java.io.PrintWriter(file, "UTF-8");
            out.println("# QuestForge ore vein parameters.");
            out.println("# The generator's own arguments, read by hooking WorldGenMinable.");
            out.println("# Format: dimension|modid:block_name:meta = veins,totalSize,minY,maxY");
            out.println("# chunks.<dimension> is what the veins were counted over.");
            out.println();

            for (Map.Entry<Integer, Integer> e : WATCHED.entrySet()) {
                out.println("chunks." + e.getKey() + " = " + e.getValue());
            }
            out.println();

            for (Map.Entry<Integer, Map<Integer, Vein>> dim : BY_DIM.entrySet()) {
                for (Map.Entry<Integer, Vein> e : dim.getValue().entrySet()) {
                    String name = OreSurveyStore.nameOfKey(e.getKey().intValue());
                    if (name == null) continue;
                    Vein v = e.getValue();
                    out.println(dim.getKey() + "|" + name + " = " + v.veins + ","
                            + v.totalSize + "," + v.minY + "," + v.maxY);
                }
            }
        } catch (Exception e) {
            com.questforge.content.QuestForgeContent.log.error(
                    "Could not write the vein parameters to " + file, e);
        } finally {
            if (out != null) out.close();
        }

        saveBiomes();
        saveNames();
        saveDepths();
    }

    /**
     * How many blocks of each ore sit at each height.
     *
     * This is the measurement the guide is really built on. The vein file says
     * where a vein was ROOTED, which is only known for ores placed by
     * WorldGenMinable and is only two numbers besides; this says where the blocks
     * ARE, for every ore however it was generated, as a full distribution. An ore
     * whose band is nominally y 0-64 is not uniform across it, and a player wants
     * the depth worth digging at, not the range's ends.
     *
     * Written sparsely -- only heights with a non-zero count -- because most ores
     * occupy a small part of the column.
     */
    private static void saveDepths() {
        if (file == null) return;

        java.io.PrintWriter out = null;
        try {
            out = new java.io.PrintWriter(new java.io.File(file.getParentFile(),
                    "qfcontent-oredepths.txt"), "UTF-8");
            out.println("# Blocks of each ore counted at each height.");
            out.println("# Format: dimension|modid:block:meta = y:blocks,y:blocks");
            out.println("# Heights with no blocks are omitted.");
            out.println();

            for (Map.Entry<Integer, Map<Integer, int[]>> dim
                    : OreSurvey.depths().entrySet()) {
                for (Map.Entry<Integer, int[]> e : dim.getValue().entrySet()) {
                    String name = OreSurveyStore.nameOfKey(e.getKey().intValue());
                    if (name == null) continue;

                    int[] histogram = e.getValue();
                    StringBuilder sb = new StringBuilder();
                    for (int y = 0; y < histogram.length; y++) {
                        if (histogram[y] == 0) continue;
                        if (sb.length() > 0) sb.append(',');
                        sb.append(y).append(':').append(histogram[y]);
                    }
                    if (sb.length() > 0) {
                        out.println(dim.getKey() + "|" + name + " = " + sb);
                    }
                }
            }
        } catch (Exception e) {
            com.questforge.content.QuestForgeContent.log.error(
                    "Could not write the ore depth table.", e);
        } finally {
            if (out != null) out.close();
        }
    }

    /**
     * Where each ore was actually found, by biome.
     *
     * Separate from the vein file so the existing format keeps loading unchanged;
     * nothing reads this back into the game, it exists to be read by people and by
     * the guide that gets built from it.
     */
    private static void saveBiomes() {
        if (file == null) return;

        java.io.PrintWriter out = null;
        try {
            out = new java.io.PrintWriter(new java.io.File(file.getParentFile(),
                    "qfcontent-orebiomes.txt"), "UTF-8");
            out.println("# Which biomes each ore's veins were rooted in.");
            out.println("# Counted at the vein origin, so the shares match the rates");
            out.println("# in qfcontent-oreveins.txt vein for vein.");
            out.println("# Format: dimension|modid:block:meta = biome:veins;biome:veins");
            out.println();

            for (Map.Entry<Integer, Map<Integer, Vein>> dim : BY_DIM.entrySet()) {
                for (Map.Entry<Integer, Vein> e : dim.getValue().entrySet()) {
                    String name = OreSurveyStore.nameOfKey(e.getKey().intValue());
                    if (name == null || e.getValue().biomes.isEmpty()) continue;

                    StringBuilder sb = new StringBuilder();
                    for (Map.Entry<String, Integer> b : e.getValue().biomes.entrySet()) {
                        if (sb.length() > 0) sb.append(';');
                        // Biome names can contain spaces but never a semicolon or
                        // a colon in practice; strip them rather than risk it.
                        sb.append(b.getKey().replace(';', ' ').replace(':', ' '))
                          .append(':').append(b.getValue());
                    }
                    out.println(dim.getKey() + "|" + name + " = " + sb);
                }
            }
        } catch (Exception e) {
            com.questforge.content.QuestForgeContent.log.error(
                    "Could not write the ore biome table.", e);
        } finally {
            if (out != null) out.close();
        }
    }

    /**
     * registry name -> the name a player sees.
     *
     * Only the running game can do this: a block's registry name and its
     * localisation key are different strings ("minecraft:coal_ore" is localised
     * through "tile.oreCoal.name"), and metadata blocks need a per-meta lookup.
     * Dumping it once means nothing downstream has to guess.
     *
     * The ore-dictionary tags go out on the same line because they are the only
     * non-arbitrary answer to "is this actually an ore?". The vein hook fires for
     * everything WorldGenMinable places, which in this pack includes OreSpawn's
     * hundred-odd mob-spawn blocks; an "ore..." registration is the game's own
     * statement that a block is a mineable ore, so that is what the guide filters on.
     */
    private static void saveNames() {
        if (file == null) return;

        java.io.PrintWriter out = null;
        try {
            out = new java.io.PrintWriter(new java.io.File(file.getParentFile(),
                    "qfcontent-orenames.txt"), "UTF-8");
            out.println("# modid:block:meta = the name shown in game | oreDict,tags");
            out.println("# An empty tag list means the ore dictionary does not call this");
            out.println("# block an ore, whatever WorldGenMinable happened to place it as.");
            out.println();

            // Every ore the survey knows about, not just the ones the vein hook
            // watched being placed. Railcraft's poor ores and VoltzEngine's metas
            // never go through WorldGenMinable, so keying this off the vein
            // observations left exactly those ores nameless -- and they are
            // metadata blocks, whose names cannot be worked out from a registry
            // name offline. Naming is a registry lookup and needs no measurement,
            // so a survey of one chunk is enough to produce the whole table.
            java.util.Set<Integer> seen = new java.util.TreeSet<Integer>(OreSurvey.oreKeys());
            for (Map<Integer, Vein> perDim : BY_DIM.values()) seen.addAll(perDim.keySet());

            for (Integer key : seen) {
                String name = OreSurveyStore.nameOfKey(key.intValue());
                if (name == null) continue;
                out.println(name + " = " + OreSurveyStore.describe(key.intValue())
                        + " | " + oreDictTags(key.intValue()));
            }
        } catch (Exception e) {
            com.questforge.content.QuestForgeContent.log.error(
                    "Could not write the ore name table.", e);
        } finally {
            if (out != null) out.close();
        }
    }

    /**
     * Every ore-dictionary name registered for one blockId&lt;&lt;4|meta key.
     *
     * Walked the long way round -- over every registered name rather than by
     * looking the block up -- because OreDictionary offers no reverse lookup from
     * a Block, only from an ItemStack, and a metadata block's ItemStack is not
     * always the one that was registered. Wildcard registrations claim every meta.
     */
    private static String oreDictTags(int key) {
        StringBuilder sb = new StringBuilder();
        try {
            int wantId = key >> 4;
            int wantMeta = key & 15;

            for (String name : net.minecraftforge.oredict.OreDictionary.getOreNames()) {
                if (name == null) continue;

                for (net.minecraft.item.ItemStack stack
                        : net.minecraftforge.oredict.OreDictionary.getOres(name)) {
                    if (stack == null || stack.getItem() == null) continue;

                    net.minecraft.block.Block block = OreSurvey.blockOf(stack);
                    if (block == null) continue;
                    if (net.minecraft.block.Block.getIdFromBlock(block) != wantId) continue;

                    int meta = stack.getItemDamage();
                    if (meta != net.minecraftforge.oredict.OreDictionary.WILDCARD_VALUE
                            && (meta & 15) != wantMeta) continue;

                    if (sb.indexOf(name) < 0) {
                        if (sb.length() > 0) sb.append(',');
                        sb.append(name);
                    }
                    break;
                }
            }
        } catch (Throwable ignored) {
            // A name dump is never worth failing a saved survey over.
        }
        return sb.toString();
    }

    public static void load() {
        if (file == null || !file.exists()) return;

        java.io.BufferedReader in = null;
        int loaded = 0;
        try {
            in = new java.io.BufferedReader(new java.io.FileReader(file));
            clear();

            String line;
            while ((line = in.readLine()) != null) {
                line = line.trim();
                if (line.isEmpty() || line.startsWith("#") || line.indexOf('=') < 0) continue;

                String left = line.substring(0, line.indexOf('=')).trim();
                String right = line.substring(line.indexOf('=') + 1).trim();

                if (left.startsWith("chunks.")) {
                    WATCHED.put(Integer.valueOf(Integer.parseInt(left.substring(7))),
                            Integer.valueOf(Integer.parseInt(right)));
                    continue;
                }

                int bar = left.indexOf('|');
                if (bar < 0) continue;
                int dimension = Integer.parseInt(left.substring(0, bar));
                Integer key = OreSurveyStore.keyOfName(left.substring(bar + 1));
                if (key == null) continue;

                String[] parts = right.split(",");
                if (parts.length < 4) continue;

                Vein v = new Vein();
                v.veins = Long.parseLong(parts[0]);
                v.totalSize = Long.parseLong(parts[1]);
                v.minY = Integer.parseInt(parts[2]);
                v.maxY = Integer.parseInt(parts[3]);

                Map<Integer, Vein> perDim = BY_DIM.get(Integer.valueOf(dimension));
                if (perDim == null) {
                    perDim = new TreeMap<Integer, Vein>();
                    BY_DIM.put(Integer.valueOf(dimension), perDim);
                }
                perDim.put(key, v);
                loaded++;
            }

            com.questforge.content.QuestForgeContent.log.info("Loaded vein parameters: "
                    + loaded + " entries over " + WATCHED.size() + " dimension(s).");
        } catch (Exception e) {
            com.questforge.content.QuestForgeContent.log.error(
                    "Could not read the vein parameters at " + file, e);
        } finally {
            try { if (in != null) in.close(); } catch (Exception ignored) { }
        }
    }

    public static void clear() {
        BY_DIM.clear();
        WATCHED.clear();
        UNCOUNTED.clear();
        PENDING.clear();
    }

    /** Interior chunks that produced no countable result, per dimension. */
    private static final Map<Integer, Integer> UNCOUNTED = new TreeMap<Integer, Integer>();

    public static int uncounted(int dimension) {
        Integer n = UNCOUNTED.get(Integer.valueOf(dimension));
        return n == null ? 0 : n.intValue();
    }

    public static void addUnpopulated(int dimension, int chunks) {
        if (!recording || chunks <= 0) return;
        UNCOUNTED.put(Integer.valueOf(dimension),
                Integer.valueOf(uncounted(dimension) + chunks));
    }

    /** Chunks watched in one dimension: the denominator for veins per chunk. */
    public static int watched(int dimension) {
        Integer n = WATCHED.get(Integer.valueOf(dimension));
        return n == null ? 0 : n.intValue();
    }



    /**
     * Records one vein, if it started inside the area currently being measured.
     *
     * Attributing a vein to the chunk its ORIGIN falls in is what makes
     * veins-per-chunk an unbiased figure. A vein can spill across a chunk boundary,
     * but it is rooted in exactly one chunk, and the generator rooted exactly that
     * many of them there.
     */
    public static void record(Block block, int size, int meta, int x, int y, int z,
                              net.minecraft.world.World world) {
        int cx = x >> 4;
        int cz = z >> 4;
        if (!OreSurvey.isMeasuredChunk(cx, cz)) return;

        int id = Block.getIdFromBlock(block);
        if (id <= 0) return;

        Long chunk = Long.valueOf(chunkKey(cx, cz));
        Map<Integer, Vein> perChunk = PENDING.get(chunk);
        if (perChunk == null) {
            perChunk = new java.util.HashMap<Integer, Vein>();
            PENDING.put(chunk, perChunk);
        }

        Integer key = Integer.valueOf((id << 4) | (meta & 15));
        Vein seen = perChunk.get(key);
        if (seen == null) {
            seen = new Vein();
            perChunk.put(key, seen);
        }

        seen.veins++;
        seen.totalSize += size;
        if (y < seen.minY) seen.minY = y;
        if (y > seen.maxY) seen.maxY = y;
        seen.addBiome(biomeAt(world, x, z), 1);
    }

    /**
     * The biome at a vein's origin, or null if it cannot be read.
     *
     * Deliberately forgiving. This runs inside worldgen, where asking for a biome
     * can touch the chunk provider, and an ore survey is never worth risking
     * generation over -- an unknown biome is simply not counted.
     */
    private static String biomeAt(net.minecraft.world.World world, int x, int z) {
        if (world == null) return null;
        try {
            net.minecraft.world.biome.BiomeGenBase biome =
                    world.getBiomeGenForCoords(x, z);
            return biome == null ? null : biome.biomeName;
        } catch (Throwable ignored) {
            return null;
        }
    }
}
