package com.questforge.content.survey;

import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Random;
import java.util.Set;

import net.minecraft.block.Block;
import net.minecraft.item.ItemStack;
import net.minecraft.world.chunk.Chunk;
import net.minecraft.world.chunk.NibbleArray;
import net.minecraft.world.chunk.storage.ExtendedBlockStorage;
import net.minecraft.world.gen.ChunkProviderServer;
import net.minecraft.world.WorldServer;
import net.minecraftforge.oredict.OreDictionary;

import com.questforge.content.QuestForgeContent;

/**
 * Measures how much of each ore the world actually generates.
 *
 * The problem this solves: nothing in Minecraft can be ASKED how common an ore is.
 * The numbers exist -- vanilla places 20 veins of coal and 1 of diamond per chunk,
 * and every mod does something similar -- but they are arguments to method calls
 * inside each generator, not data attached to a block. There is no registry to
 * query, because nothing ever needed one.
 *
 * It is unqueryable but perfectly measurable, and measuring it does not need a
 * player. Chunk generation is server-side and can be driven directly:
 * ChunkProviderServer.loadChunk() runs the full pipeline including populate, which
 * is the stage that places ore. So this generates chunks itself, counts what came
 * out, and throws them away -- no camera, no movement, no rendering, no client
 * involved at all.
 *
 * Three things make it cheap enough to run on a live server:
 *
 *  - It reads the raw block-id arrays out of each chunk's storage sections rather
 *    than calling world.getBlock 65,536 times.
 *  - It works to a millisecond budget per tick rather than a fixed chunk count,
 *    so it throttles itself to whatever the pack's worldgen actually costs.
 *  - Sample points are spaced far apart, so a few hundred chunks cover many
 *    biomes rather than one.
 *
 * The result is better than any static table could be, because it reflects THIS
 * pack's configuration -- whatever CrazyCraft retuned, whatever a mod's config
 * changed -- rather than what a mod's defaults claim.
 */
public class OreSurvey {

    /**
     * How much of each 50ms tick the survey may spend generating chunks.
     *
     * This is a time budget rather than a chunk count on purpose. A fixed count
     * cannot be right for both cases: three chunks per tick is comfortable on
     * vanilla but ruinous on a heavily modded pack, where one chunk can cost
     * hundreds of milliseconds because every worldgen mod runs on it. Measuring
     * the elapsed time instead makes the survey self-throttling -- it does as
     * many chunks as fit and no more, whatever the pack costs.
     *
     * Two budgets, because the two situations are genuinely different. With players
     * online the survey is a background chore and must stay out of the way. With
     * nobody online -- a dedicated box generating a large sample unattended -- there
     * is nothing to stay out of the way OF, and throttling to 40% only makes a
     * multi-hour run into a multi-hour-and-a-half one.
     */
    private static final int BUSY_BUDGET_MS = 20;
    private static final int IDLE_BUDGET_MS = 45;

    /** Set by "/qfsurvey start <chunks> [budgetMs]"; 0 means decide automatically. */
    private static int budgetOverrideMs;

    /** Progress goes in the log this often, so a long run can be watched. */
    private static final int PROGRESS_EVERY = 2000;

    /**
     * And the file is rewritten this often. A large survey is hours of work; losing
     * it to a crash at hour three because nothing had been written would be absurd.
     */
    private static final int AUTOSAVE_EVERY = 10000;

    private static int lastProgressAt;
    private static int lastSaveAt;

    private static long budgetNanos() {
        if (budgetOverrideMs > 0) return budgetOverrideMs * 1000000L;

        int players = 0;
        try {
            players = net.minecraft.server.MinecraftServer.getServer().getCurrentPlayerCount();
        } catch (Throwable ignored) {
            // No server object yet is not a reason to fail; assume someone is on.
            players = 1;
        }
        return (players == 0 ? IDLE_BUDGET_MS : BUSY_BUDGET_MS) * 1000000L;
    }

    /**
     * Chunks between sample points. Biome regions are typically a few hundred
     * blocks, so sampling every 64th chunk (1024 blocks) lands each sample in a
     * different one instead of surveying the same forest a thousand times.
     */
    private static final int SPACING = 64;

    /** Where sampling starts, in chunks, so it never touches the spawn area. */
    private static final int ORIGIN_OFFSET = 512;

    /**
     * Chunks along one side of a generated patch.
     *
     * Chunks have to be generated in a contiguous block, because ore is not placed
     * when a chunk is generated -- it is placed when the chunk is POPULATED, and
     * Chunk.populateChunk only populates once its +1/+1 neighbours already exist.
     * Generating isolated chunks yields bare terrain with no ore in it at all.
     *
     * So each sample generates a PATCH x PATCH block and counts only the middle of
     * it. A chunk is countable only when populate has run on its whole 3x3
     * neighbourhood, since an ore vein rooted in one chunk can spill into the next.
     * In a patch of side N, populate runs over [0, N-2], so the countable interior
     * is [1, N-3] -- (N-3)^2 chunks measured for N^2 generated.
     *
     * That ratio is the survey's whole efficiency, and on a heavy pack it is the
     * difference between a useful sample and an overnight one: a chunk costs
     * ~230ms with 113 mods loaded, so wasted generation is expensive. N=10 measures
     * 49 of every 100 generated; N=24 measures 441 of 576, which is 1.6x more
     * measurement for the same work. The cost is holding N^2 chunks in memory at
     * once, and 576 is comfortable inside a 3GB heap.
     */
    private static final int PATCH = 24;

    /** Side of the countable interior; see {@link #PATCH}. */
    private static final int INTERIOR = PATCH - 3;

    private static boolean running;
    private static WorldServer world;
    private static int remaining;
    private static int completed;
    private static int index;
    private static long startedAt;

    /** Dimensions still to visit, and how many chunks to measure in each. */
    private static int[] dimQueue = new int[0];
    private static int dimCursor;
    private static int chunksPerDimension;
    private static int currentDim;

    /** Dimensions this survey loaded itself, to be unloaded again when done. */
    private static final Set<Integer> LOADED_BY_US = new HashSet<Integer>();

    /** Chunks generated, as opposed to counted. The cost of the measurement. */
    private static int generated;

    /** Which dimension is being sampled right now, for the vein recorder. */
    public static int currentDimension() {
        return currentDim;
    }

    /**
     * True when this chunk is one whose ore is actually being counted.
     *
     * The vein recorder uses the same interior as the block counter, so the two
     * instruments describe exactly the same chunks and can be compared directly.
     */
    public static boolean isMeasuredChunk(int cx, int cz) {
        int dx = cx - patchX;
        int dz = cz - patchZ;
        return dx >= 1 && dx <= INTERIOR && dz >= 1 && dz <= INTERIOR;
    }

    /** The patch being generated right now, and how far through it we are. */
    private static int patchX;
    private static int patchZ;
    private static int cursor;
    private static final Chunk[] PATCH_CHUNKS = new Chunk[PATCH * PATCH];

    /** Interior chunks that turned out not to be populated. Should stay zero. */
    private static int unpopulated;

    /** blockId << 4 | metadata, for every block registered as an ore. */
    private static final Set<Integer> ORE_KEYS = new HashSet<Integer>();

    /**
     * Observed counts, per dimension: dimensionId -> (blockId<<4|meta -> blocks).
     *
     * Per dimension rather than one global tally, because otherwise HOW LONG each
     * dimension was sampled for silently becomes its weight. Sample 40,000 overworld
     * chunks and 3,000 nether ones and every nether ore comes out thirteen times
     * too rare, for no reason but the order the survey happened to run in. Keeping
     * dimensions apart means the answer is a DENSITY -- blocks per chunk -- which is
     * a property of the world rather than of the measurement.
     */
    private static final Map<Integer, Map<Integer, Integer>> COUNTS_BY_DIM =
            new java.util.TreeMap<Integer, Map<Integer, Integer>>();

    /**
     * How many blocks of each ore were found at each height, per dimension.
     *
     * One int[256] per ore per dimension -- a few hundred kilobytes at this pack's
     * size, and the only source of depth information for the ores that do not go
     * through WorldGenMinable at all.
     */
    private static final Map<Integer, Map<Integer, int[]>> DEPTHS_BY_DIM =
            new java.util.TreeMap<Integer, Map<Integer, int[]>>();

    /** Chunks measured per dimension. The denominator for the densities above. */
    private static final Map<Integer, Integer> CHUNKS_BY_DIM =
            new java.util.TreeMap<Integer, Integer>();

    private static final Random RAND = new Random();

    // ---- Control ---------------------------------------------------------

    public static boolean isRunning() {
        return running;
    }

    public static int completed() {
        return completed;
    }

    public static int remaining() {
        return remaining;
    }

    /** Chunks generated so far, which is always more than the number measured. */
    public static int generated() {
        return generated;
    }

    public static int chunksSampled() {
        int total = 0;
        for (Integer n : CHUNKS_BY_DIM.values()) total += n.intValue();
        return total;
    }

    public static Map<Integer, Integer> chunksByDimension() {
        return CHUNKS_BY_DIM;
    }

    public static Map<Integer, Map<Integer, Integer>> countsByDimension() {
        return COUNTS_BY_DIM;
    }

    /** Raw blocks seen anywhere, as blockId<<4|meta -> count. For display only. */
    public static Map<Integer, Integer> counts() {
        Map<Integer, Integer> merged = new HashMap<Integer, Integer>();
        for (Map<Integer, Integer> perDim : COUNTS_BY_DIM.values()) {
            for (Map.Entry<Integer, Integer> e : perDim.entrySet()) {
                Integer seen = merged.get(e.getKey());
                merged.put(e.getKey(), Integer.valueOf(
                        (seen == null ? 0 : seen.intValue()) + e.getValue().intValue()));
            }
        }
        return merged;
    }

    /**
     * What the weights are actually built from: blocks per chunk, summed over every
     * dimension surveyed.
     *
     * Summing densities rather than raw counts is the whole point -- an ore that
     * averages 3 blocks per chunk in the nether contributes 3, whether the nether
     * was sampled for a thousand chunks or a hundred thousand.
     */
    public static Map<Integer, Double> densities() {
        Map<Integer, Double> out = new HashMap<Integer, Double>();

        for (Map.Entry<Integer, Map<Integer, Integer>> dim : COUNTS_BY_DIM.entrySet()) {
            Integer chunks = CHUNKS_BY_DIM.get(dim.getKey());
            if (chunks == null || chunks.intValue() <= 0) continue;

            for (Map.Entry<Integer, Integer> e : dim.getValue().entrySet()) {
                double density = e.getValue().doubleValue() / chunks.doubleValue();
                Double running = out.get(e.getKey());
                out.put(e.getKey(), Double.valueOf(
                        (running == null ? 0.0 : running.doubleValue()) + density));
            }
        }
        return out;
    }

    static void record(int dimension, int key, int amount) {
        Map<Integer, Integer> perDim = COUNTS_BY_DIM.get(Integer.valueOf(dimension));
        if (perDim == null) {
            perDim = new HashMap<Integer, Integer>();
            COUNTS_BY_DIM.put(Integer.valueOf(dimension), perDim);
        }
        Integer seen = perDim.get(Integer.valueOf(key));
        perDim.put(Integer.valueOf(key),
                Integer.valueOf((seen == null ? 0 : seen.intValue()) + amount));
    }

    static void recordChunks(int dimension, int chunks) {
        Integer seen = CHUNKS_BY_DIM.get(Integer.valueOf(dimension));
        CHUNKS_BY_DIM.put(Integer.valueOf(dimension),
                Integer.valueOf((seen == null ? 0 : seen.intValue()) + chunks));
    }

    // ---- Starting --------------------------------------------------------

    /**
     * Surveys every dimension the pack registers, one after another.
     *
     * Doing this automatically rather than a dimension at a time by hand is the
     * difference between a usable tool and a chore: this pack registers dozens of
     * dimensions, and the ores that are missing from an overworld-only survey --
     * every End ore, every nether ore -- are exactly the ones worth knowing about.
     */
    public static void startAll(int chunksEach, int budgetMs) {
        Integer[] boxed;
        try {
            boxed = net.minecraftforge.common.DimensionManager.getStaticDimensionIDs();
        } catch (Throwable t) {
            boxed = null;
        }
        if (boxed == null || boxed.length == 0) boxed = new Integer[] { Integer.valueOf(0) };

        int[] dims = new int[boxed.length];
        for (int i = 0; i < boxed.length; i++) dims[i] = boxed[i].intValue();

        // Overworld first: it is the one that matters most, so if the run is cut
        // short it is the one that got done.
        java.util.Arrays.sort(dims);
        int[] ordered = new int[dims.length];
        int at = 0;
        for (int d : dims) if (d == 0) ordered[at++] = d;
        for (int d : dims) if (d != 0) ordered[at++] = d;

        begin(ordered, chunksEach, budgetMs);
    }

    /** Surveys one dimension only. */
    public static void start(WorldServer target, int chunks, int budgetMs) {
        begin(new int[] { target.provider.dimensionId }, chunks, budgetMs);
    }

    private static void begin(int[] dims, int chunksEach, int budgetMs) {
        buildOreKeys();

        dimQueue = dims;
        dimCursor = 0;
        chunksPerDimension = chunksEach;
        budgetOverrideMs = budgetMs;
        completed = 0;
        generated = 0;
        unpopulated = 0;
        lastProgressAt = 0;
        lastSaveAt = 0;
        LOADED_BY_US.clear();
        running = true;
        OreGenObservations.setRecording(true);
        startedAt = System.currentTimeMillis();

        StringBuilder list = new StringBuilder();
        for (int d : dims) list.append(d).append(' ');

        QuestForgeContent.log.info("Ore survey started: " + chunksEach + " chunks in each of "
                + dims.length + " dimensions [" + list.toString().trim() + "], generating "
                + PATCH + "x" + PATCH + " patches and counting the middle " + INTERIOR + "x"
                + INTERIOR + ", " + ORE_KEYS.size() + " ore types known, budget "
                + (budgetMs > 0 ? budgetMs + "ms (forced)" : "automatic") + ".");

        if (!advanceDimension()) stop();
    }

    /**
     * Moves to the next dimension in the queue, loading it if the server has not.
     *
     * @return false when the queue is exhausted
     */
    private static boolean advanceDimension() {
        while (dimCursor < dimQueue.length) {
            int dim = dimQueue[dimCursor++];

            WorldServer target = null;
            try {
                boolean wasLoaded = net.minecraftforge.common.DimensionManager.getWorld(dim) != null;
                if (!wasLoaded) {
                    net.minecraftforge.common.DimensionManager.initDimension(dim);
                    LOADED_BY_US.add(Integer.valueOf(dim));
                }
                target = net.minecraftforge.common.DimensionManager.getWorld(dim);
            } catch (Throwable t) {
                QuestForgeContent.log.warn("Ore survey could not open dimension " + dim
                        + ", skipping it: " + t);
            }

            if (target == null) continue;

            world = target;
            currentDim = dim;
            remaining = chunksPerDimension;
            cursor = 0;
            java.util.Arrays.fill(PATCH_CHUNKS, null);
            index = RAND.nextInt(4096);   // a different sample line in each dimension

            QuestForgeContent.log.info("Ore survey: dimension " + dim + " ("
                    + target.provider.getDimensionName() + "), " + chunksPerDimension
                    + " chunks.");
            return true;
        }
        return false;
    }

    /** Releases a dimension the survey opened, so twenty of them do not pile up. */
    private static void releaseDimension(int dim) {
        if (!LOADED_BY_US.remove(Integer.valueOf(dim))) return;
        try {
            net.minecraftforge.common.DimensionManager.unloadWorld(dim);
        } catch (Throwable t) {
            QuestForgeContent.log.warn("Could not unload dimension " + dim + ": " + t);
        }
    }

    public static void stop() {
        if (!running) return;
        running = false;
        OreGenObservations.setRecording(false);
        world = null;

        long millis = Math.max(1L, System.currentTimeMillis() - startedAt);
        QuestForgeContent.log.info(String.format(
                "Ore survey stopped: measured %d chunks (generated %d) in %.1fs, "
                        + "%.1f measured/s. Total sampled: %d, ore types seen: %d.",
                completed, generated, millis / 1000.0, completed * 1000.0 / millis,
                chunksSampled(), counts().size()));

        if (unpopulated > 0) {
            QuestForgeContent.log.warn(unpopulated + " interior chunks were not populated. "
                    + "Ore counts are understated -- this should not happen.");
        }

        // Saving must not be able to kill the server thread; the measurement in
        // memory is still good even if the file cannot be written.
        try {
            OreSurveyStore.save();
            OreGenObservations.save();
        } catch (Throwable t) {
            QuestForgeContent.log.error("Could not save the ore survey.", t);
        }
    }

    public static void clear() {
        COUNTS_BY_DIM.clear();
        CHUNKS_BY_DIM.clear();
        DEPTHS_BY_DIM.clear();
    }

    /** The depth histograms, for the store to write out. */
    static Map<Integer, Map<Integer, int[]>> depths() {
        return DEPTHS_BY_DIM;
    }

    /** Used by the store when reloading a survey from disk. */
    static void restore(int dimension, int chunks) {
        CHUNKS_BY_DIM.put(Integer.valueOf(dimension), Integer.valueOf(chunks));
    }

    // ---- The sampler -----------------------------------------------------

    /**
     * Called once per server tick.
     *
     * Everything is inside a catch-all because this runs on the server thread:
     * an exception escaping here takes the whole server down, and a survey is a
     * convenience. If it breaks, it should switch itself off quietly.
     */
    public static void tick() {
        if (!running) return;

        try {
            if (world == null || remaining <= 0) {
                stop();
                return;
            }

            ChunkProviderServer provider = world.theChunkProviderServer;
            if (provider == null) {
                stop();
                return;
            }

            // At least one chunk per tick, so the survey always makes progress even
            // if a single chunk costs more than the entire budget.
            long deadline = System.nanoTime() + budgetNanos();
            do {
                step(provider);
            } while (remaining > 0 && System.nanoTime() < deadline);

            report();

            if (remaining <= 0) {
                // This dimension is done. On to the next, or finish.
                int finished = currentDim;
                boolean more = advanceDimension();
                releaseDimension(finished);
                if (!more) stop();
            }

        } catch (Throwable t) {
            QuestForgeContent.log.error("Ore survey failed and has been stopped.", t);
            running = false;
            OreGenObservations.setRecording(false);
            world = null;
        }
    }

    /**
     * Walks a square spiral outward, one sample point per step, spaced far enough
     * apart that consecutive samples land in different biomes.
     */
    private static int[] nextSamplePoint() {
        int n = index++;

        // Spiral in "ring" space: ring r has 8r cells.
        int r = (int) Math.floor((Math.sqrt(n + 1) - 1) / 2) + 1;
        int sideLength = 2 * r;
        int offset = n - (2 * r - 1) * (2 * r - 1);
        int side = offset / sideLength;
        int step = offset % sideLength;

        int cx, cz;
        switch (side) {
            case 0:  cx = r;             cz = -r + step + 1; break;
            case 1:  cx = r - step - 1;  cz = r;             break;
            case 2:  cx = -r;            cz = r - step - 1;  break;
            default: cx = -r + step + 1; cz = -r;            break;
        }

        return new int[] { (cx * SPACING) + ORIGIN_OFFSET, (cz * SPACING) + ORIGIN_OFFSET };
    }

    /**
     * Periodic progress to the log, and a periodic save.
     *
     * A survey large enough to be worth trusting runs for hours with nobody
     * watching, so it has to say where it has got to and it has to write down what
     * it has found so far.
     */
    private static void report() {
        if (completed - lastProgressAt >= PROGRESS_EVERY) {
            lastProgressAt = completed;

            long millis = Math.max(1L, System.currentTimeMillis() - startedAt);
            double perSecond = completed * 1000.0 / millis;
            long etaSeconds = perSecond > 0 ? (long) (remaining / perSecond) : 0;

            QuestForgeContent.log.info(String.format(
                    "Ore survey: %d measured, %d to go (%d generated, %.1f/s, ~%dm left), "
                            + "%d ore types seen.",
                    completed, remaining, generated, perSecond, etaSeconds / 60,
                    counts().size()));
        }

        if (completed - lastSaveAt >= AUTOSAVE_EVERY) {
            lastSaveAt = completed;
            try {
                OreSurveyStore.save();
                OreGenObservations.save();
            } catch (Throwable t) {
                QuestForgeContent.log.error("Ore survey autosave failed.", t);
            }
        }
    }

    /**
     * Generates exactly one chunk of the current patch.
     *
     * One chunk at a time rather than a whole patch at once, so the tick budget
     * stays meaningful: a patch is a hundred chunks and would blow any budget.
     */
    private static void step(ChunkProviderServer provider) {
        if (cursor == 0) {
            int[] point = nextSamplePoint();
            patchX = point[0];
            patchZ = point[1];
        }

        int cx = patchX + (cursor % PATCH);
        int cz = patchZ + (cursor / PATCH);

        try {
            PATCH_CHUNKS[cursor] = provider.loadChunk(cx, cz);
        } catch (Throwable t) {
            // A modded generator throwing must not take the survey -- or the tick
            // loop -- down with it.
            PATCH_CHUNKS[cursor] = null;
            QuestForgeContent.log.warn("Ore survey skipped chunk " + cx + "," + cz + ": " + t);
        }

        generated++;
        cursor++;

        if (cursor >= PATCH_CHUNKS.length) {
            harvestPatch(provider);
            cursor = 0;
        }
    }

    /** Counts the interior of a finished patch, then hands the whole thing back. */
    private static void harvestPatch(ChunkProviderServer provider) {
        int counted = 0;

        for (int dz = 1; dz <= INTERIOR; dz++) {
            for (int dx = 1; dx <= INTERIOR; dx++) {
                // Re-fetch rather than trust the reference kept at load time.
                // Populate runs LATER than the load that triggered it -- it waits on
                // the +1/+1 neighbours -- and over the seconds a patch takes, the
                // provider can hand back a different Chunk instance for the same
                // coordinates. The cached reference then still reads
                // isTerrainPopulated == false while the live chunk is fully
                // populated, so the ore in it was being thrown away: two thirds of
                // every nether patch, as it turned out.
                int cx = patchX + dx;
                int cz = patchZ + dz;

                Chunk chunk = null;
                try {
                    if (provider.chunkExists(cx, cz)) chunk = provider.provideChunk(cx, cz);
                } catch (Throwable ignored) {
                    chunk = null;
                }
                if (chunk == null) chunk = PATCH_CHUNKS[(dz * PATCH) + dx];
                if (chunk == null) continue;

                // Populate is what places ore. If this is ever false the whole
                // measurement is meaningless, so it is counted and reported rather
                // than silently producing zeros.
                if (!chunk.isTerrainPopulated) {
                    unpopulated++;
                    continue;
                }

                count(chunk);
                // Same chunk, both instruments: its buffered veins are accepted
                // exactly when its blocks are counted.
                OreGenObservations.commitChunk(currentDim, cx, cz);
                counted++;
            }
        }

        recordChunks(currentDim, counted);

        // Anything buffered for chunks that were not counted is thrown away, so the
        // vein totals and the block totals cover the same chunks by construction.
        OreGenObservations.discardPending();
        OreGenObservations.addUnpopulated(currentDim, (INTERIOR * INTERIOR) - counted);

        completed += counted;
        remaining = Math.max(0, remaining - counted);

        // Hand the patch back. unloadQueuedChunks runs on the server's own schedule
        // and will write and discard them.
        for (int i = 0; i < PATCH_CHUNKS.length; i++) {
            Chunk chunk = PATCH_CHUNKS[i];
            PATCH_CHUNKS[i] = null;
            if (chunk == null) continue;
            try {
                provider.unloadChunksIfNotNearSpawn(chunk.xPosition, chunk.zPosition);
            } catch (Throwable ignored) {
                // Nothing useful to do; the server will reclaim it eventually.
            }
        }
    }

    /**
     * Counts ore in a chunk by reading the raw block-id arrays.
     *
     * A chunk is up to sixteen 16x16x16 sections. Reading the byte arrays directly
     * is roughly two orders of magnitude cheaper than 65,536 world.getBlock calls,
     * which is what makes surveying hundreds of chunks practical inside a tick
     * budget.
     */
    private static void count(Chunk chunk) {
        ExtendedBlockStorage[] sections = chunk.getBlockStorageArray();
        if (sections == null) return;

        // Resolved once rather than per ore block found: this is the innermost loop
        // in the whole survey.
        Map<Integer, Integer> tally = COUNTS_BY_DIM.get(Integer.valueOf(currentDim));
        if (tally == null) {
            tally = new HashMap<Integer, Integer>();
            COUNTS_BY_DIM.put(Integer.valueOf(currentDim), tally);
        }

        Map<Integer, int[]> depths = DEPTHS_BY_DIM.get(Integer.valueOf(currentDim));
        if (depths == null) {
            depths = new HashMap<Integer, int[]>();
            DEPTHS_BY_DIM.put(Integer.valueOf(currentDim), depths);
        }

        for (ExtendedBlockStorage section : sections) {
            if (section == null) continue;

            byte[] lsb = section.getBlockLSBArray();
            NibbleArray msb = section.getBlockMSBArray();
            NibbleArray meta = section.getMetadataArray();
            if (lsb == null) continue;

            int sectionY = section.getYLocation();

            for (int i = 0; i < lsb.length; i++) {
                int id = lsb[i] & 255;
                if (msb != null) {
                    // The array is indexed y<<8 | z<<4 | x; unpack for the nibble read.
                    int x = i & 15;
                    int y = (i >> 8) & 15;
                    int z = (i >> 4) & 15;
                    id |= msb.get(x, y, z) << 8;
                }
                if (id == 0) continue;   // air, the overwhelming majority

                int m = 0;
                if (meta != null) {
                    int x = i & 15;
                    int y = (i >> 8) & 15;
                    int z = (i >> 4) & 15;
                    m = meta.get(x, y, z);
                }

                Integer key = Integer.valueOf((id << 4) | (m & 15));
                if (!ORE_KEYS.contains(key)) continue;

                Integer seen = tally.get(key);
                tally.put(key, Integer.valueOf(seen == null ? 1 : seen.intValue() + 1));

                // Where the block actually is, which is the question the guide
                // exists to answer. The vein hook reports where a vein was rooted,
                // but only for ores placed by WorldGenMinable -- VoltzEngine,
                // Railcraft's poor ores and HardcoreEnderExpansion have their own
                // generators and are invisible to it. Counting the blocks by
                // height covers every ore, however it got there, and describes the
                // distribution rather than just its two ends.
                int worldY = sectionY + ((i >> 8) & 15);
                if (worldY >= 0 && worldY < 256) {
                    int[] histogram = depths.get(key);
                    if (histogram == null) {
                        histogram = new int[256];
                        depths.put(key, histogram);
                    }
                    histogram[worldY]++;
                }
            }
        }
    }

    // ---- Ore identification ----------------------------------------------

    /**
     * Every block worth counting, as blockId<<4|meta.
     *
     * Done once up front so the inner loop is a hash lookup on an int rather than
     * an ore-dictionary query per block.
     *
     * The ore dictionary is the main source and the trustworthy one, but on its own
     * it is not enough. Superheroes Unlimited generates about twenty ores in the
     * Overworld and registers none of them, so an ore-dictionary-only survey
     * reports them as never generating: the vein hook watches the veins being
     * placed and then the block counter finds nothing. Anything WorldGenMinable
     * places is at least a candidate, so extra keys may be listed by registry name
     * in qfcontent-extraores.txt and are counted alongside the ore dictionary's.
     * Which of them are ores a player would care about is a judgement to make later
     * from the counts, and not one this file should be making.
     */
    static void buildOreKeys() {
        if (!ORE_KEYS.isEmpty()) return;

        addExtraOreKeys();

        for (String name : OreDictionary.getOreNames()) {
            if (name == null || !name.startsWith("ore")) continue;

            for (ItemStack stack : OreDictionary.getOres(name)) {
                if (stack == null || stack.getItem() == null) continue;

                Block block = blockOf(stack);
                if (block == null || block == net.minecraft.init.Blocks.air) continue;

                int id = Block.getIdFromBlock(block);
                if (id <= 0) continue;

                int meta = stack.getItemDamage();
                if (meta == OreDictionary.WILDCARD_VALUE) {
                    // Registered for every metadata; claim all sixteen.
                    for (int m = 0; m < 16; m++) ORE_KEYS.add(Integer.valueOf((id << 4) | m));
                } else {
                    ORE_KEYS.add(Integer.valueOf((id << 4) | (meta & 15)));
                }
            }
        }
    }

    public static int knownOreTypes() {
        return ORE_KEYS.size();
    }

    /** Every block the survey counts, for the name table to describe. */
    static Set<Integer> oreKeys() {
        return ORE_KEYS;
    }

    /**
     * Blocks named in qfcontent-extraores.txt, one "modid:block:meta" per line.
     *
     * Resolved through the same registry lookup the survey files use, so a name
     * written here is the same name that comes back out in the results. A name
     * that does not resolve is reported rather than skipped quietly: it means the
     * mod that owned it is gone, which is exactly the kind of thing that should
     * not be discovered later from a hole in the data.
     */
    private static void addExtraOreKeys() {
        java.io.File file = new java.io.File(OreSurveyStore.file().getParentFile(),
                "qfcontent-extraores.txt");
        if (!file.exists()) return;

        java.io.BufferedReader in = null;
        int added = 0, missing = 0;
        try {
            in = new java.io.BufferedReader(new java.io.FileReader(file));
            String line;
            while ((line = in.readLine()) != null) {
                line = line.trim();
                if (line.isEmpty() || line.startsWith("#")) continue;

                Integer key = OreSurveyStore.keyOfName(line);
                if (key == null) {
                    missing++;
                    continue;
                }
                if (ORE_KEYS.add(key)) added++;
            }
        } catch (Exception e) {
            QuestForgeContent.log.error("Could not read qfcontent-extraores.txt.", e);
        } finally {
            if (in != null) try { in.close(); } catch (Exception ignored) { }
        }

        QuestForgeContent.log.info("Ore survey: " + added + " extra blocks to count from "
                + "qfcontent-extraores.txt" + (missing > 0
                        ? ", " + missing + " names did not resolve to a block" : "."));
    }

    /**
     * Resolves the block an ore-dictionary entry refers to.
     *
     * Block.getBlockFromItem alone is not enough: it goes through the item-to-block
     * map, which some modded ItemBlocks are not in. Reading the ItemBlock's own
     * block field first catches those. Getting this wrong means an ore is never
     * added to ORE_KEYS and so reads as "never generates" no matter how much of it
     * the world actually contains.
     */
    static Block blockOf(ItemStack stack) {
        net.minecraft.item.Item item = stack.getItem();
        if (item instanceof net.minecraft.item.ItemBlock) {
            Block block = ((net.minecraft.item.ItemBlock) item).field_150939_a;
            if (block != null) return block;
        }
        return Block.getBlockFromItem(item);
    }

    /**
     * Every ore-dictionary entry the survey has never once seen, with the ore
     * dictionary name that registered it.
     *
     * This is the check on the measurement itself. An ore missing from the results
     * is either genuinely absent from the surveyed dimensions -- a nether ore, or a
     * block registered as an ore that no generator ever places -- or it is a bug in
     * how the survey identifies ore. The two are indistinguishable from the counts
     * alone, so the names have to be looked at.
     */
    public static java.util.List<String> missing() {
        buildOreKeys();

        Map<Integer, Integer> seenAnywhere = counts();

        java.util.TreeSet<String> lines = new java.util.TreeSet<String>();

        for (String name : OreDictionary.getOreNames()) {
            if (name == null || !name.startsWith("ore")) continue;

            for (ItemStack stack : OreDictionary.getOres(name)) {
                if (stack == null || stack.getItem() == null) continue;

                Block block = blockOf(stack);
                if (block == null || block == net.minecraft.init.Blocks.air) continue;

                int id = Block.getIdFromBlock(block);
                if (id <= 0) continue;

                int meta = stack.getItemDamage();
                if (meta == OreDictionary.WILDCARD_VALUE) {
                    // Only interesting if not one metadata of it was ever seen.
                    for (int m = 0; m < 16; m++) {
                        if (seenAnywhere.containsKey(Integer.valueOf((id << 4) | m))) {
                            block = null;
                            break;
                        }
                    }
                    if (block == null) continue;
                    meta = 0;
                } else if (seenAnywhere.containsKey(Integer.valueOf((id << 4) | (meta & 15)))) {
                    continue;
                }

                lines.add(name + "  ->  " + OreSurveyStore.registryName(block) + ":" + meta);
            }
        }

        return new java.util.ArrayList<String>(lines);
    }
}
