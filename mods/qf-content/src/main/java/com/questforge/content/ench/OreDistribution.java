package com.questforge.content.ench;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Random;

import net.minecraft.block.Block;
import net.minecraft.item.Item;
import net.minecraft.item.ItemBlock;
import net.minecraft.item.ItemStack;
import net.minecraftforge.oredict.OreDictionary;

/**
 * A weighted pool of every ore in the game, for Transmuter.
 *
 * Weights come from one of two places, in order of preference:
 *
 * 1. **A measurement.** OreSurvey generates chunks server-side and counts the
 *    blocks that actually came out. That is the real answer -- it reflects this
 *    pack's own configuration, including anything a mod or the pack author
 *    retuned, rather than what a mod's defaults claim. Placed blocks, not vein
 *    attempts: a generator that runs in a world it cannot convert leaves nothing
 *    behind, and the pool must not pay out for that.
 *
 * 2. **Harvest tier**, until a survey exists. There is no cross-mod ore rarity
 *    API in 1.7.10: generation counts are arguments to method calls inside each
 *    mod's generator, not data attached to a block, so nothing can be asked. The
 *    closest queryable proxy is Forge's harvest level plus block hardness, which
 *    every mod sets correctly because mining depends on both. It is a proxy for
 *    TIER rather than rarity -- iron and coal share a tier and differ threefold in
 *    abundance -- which is exactly why the survey is worth running.
 *
 * Either way the pool is built from whatever the ore dictionary contains at
 * postInit. No mod is named anywhere; adding or removing one changes the pool by
 * itself.
 */
public class OreDistribution {

    /** One ore, its tier, and how likely it is to come up. */
    private static class Entry {
        final ItemStack stack;
        final int harvestLevel;
        final int weight;

        Entry(ItemStack stack, int harvestLevel, int weight) {
            this.stack = stack;
            this.harvestLevel = harvestLevel;
            this.weight = weight;
        }
    }

    private static final List<Entry> POOL = new ArrayList<Entry>();

    /**
     * How far above the broken ore's tier a transmute may reach.
     *
     * One, deliberately: breaking coal should occasionally hand you iron, and
     * should never hand you a modded endgame ore. Without this, the pool being
     * flat meant a coal vein could produce anything in the game.
     */
    private static final int TIER_HEADROOM = 1;

    /**
     * Minimum chunks in a survey before its numbers are trusted over the heuristic.
     * Diamond is one vein per chunk in vanilla, so a handful of chunks can miss an
     * ore entirely; a few hundred cannot.
     */
    private static final int MIN_SAMPLE = 200;

    private static boolean measured;

    /**
     * Ores the survey never saw a single block of: ore that arrives some way other
     * than world generation, and ore whose generator runs everywhere but places
     * nothing because the world it runs in is not made of stone.
     *
     * They get a floor weight rather than being dropped: they exist and are
     * obtainable, so Transmuter producing one occasionally is right. Giving them a
     * generator's stated output would not be.
     */
    private static final double NEVER_SEEN_WEIGHT = 0.02;

    /** Built once at postInit, when every mod has registered its ores. */
    public static void build() {
        POOL.clear();

        // Blocks that were actually placed, and nothing else.
        //
        // The vein recorder reads the generator's own arguments, which is a more
        // precise number for a rarer thing -- but it counts ATTEMPTS. WorldGenMinable
        // converts a target block, almost always stone, so in a world that is not
        // built of stone the generator runs its full loop and places nothing. The
        // 2026-09 survey caught 36 ore/dimension pairs like that, one of them 105,840
        // coal vein attempts that left zero coal in the ground. Weighting the pool by
        // attempts would hand out ore that cannot be mined anywhere.
        //
        // Vein parameters are still read; they are just no longer a source of weight.
        Map<Integer, Double> survey = com.questforge.content.survey.OreSurvey.densities();

        measured = com.questforge.content.survey.OreSurvey.chunksSampled() >= MIN_SAMPLE
                && !survey.isEmpty();

        for (String name : OreDictionary.getOreNames()) {
            if (name == null || !name.startsWith("ore")) continue;

            for (ItemStack stack : OreDictionary.getOres(name)) {
                Entry entry = describe(stack, survey);
                if (entry != null) POOL.add(entry);
            }
        }

        com.questforge.content.QuestForgeContent.log.info("Transmuter pool: " + POOL.size()
                + " ores, weighted by "
                + (measured
                    ? ("blocks counted over "
                       + com.questforge.content.survey.OreSurvey.chunksSampled() + " chunks")
                    : "harvest tier (no survey yet -- run /qfsurvey start)")
                + ".");
    }

    /** True when the weights come from measurement rather than the fallback. */
    public static boolean isMeasured() {
        return measured;
    }

    private static Entry describe(ItemStack stack, Map<Integer, Double> survey) {
        if (stack == null || stack.getItem() == null) return null;

        Block block = blockOf(stack);
        if (block == null) return null;

        int harvestLevel;
        float hardness;
        try {
            harvestLevel = Math.max(0, block.getHarvestLevel(stack.getItemDamage()));
            hardness = block.getBlockHardness(null, 0, 0, 0);
        } catch (Throwable t) {
            // Plenty of modded blocks read world state in these. If one throws,
            // treat it as an ordinary mid-tier ore rather than dropping it.
            harvestLevel = 1;
            hardness = 3.0F;
        }
        if (hardness < 0 || Float.isNaN(hardness)) hardness = 3.0F;

        int weight;
        if (measured) {
            // Blocks per chunk, summed over every dimension surveyed. A density
            // rather than a raw count, so how long each dimension happened to be
            // sampled for cannot skew the pool.
            int key = (Block.getIdFromBlock(block) << 4) | (stack.getItemDamage() & 15);
            Double density = survey.get(Integer.valueOf(key));

            // The floor is a floor, not just the never-seen case: an ore the survey
            // saw one block of in five thousand chunks would otherwise rank below one
            // it never saw at all.
            double perChunk = Math.max(NEVER_SEEN_WEIGHT,
                    density == null ? 0.0 : density.doubleValue());
            weight = (int) Math.max(1, Math.round(perChunk * 100.0));
        } else {
            // Fallback until a survey exists. Harvest level dominates because it is
            // the signal mods set deliberately; hardness only breaks ties.
            weight = Math.max(1, 240 / (1 + (harvestLevel * 5) + (int) hardness));
        }

        return new Entry(stack, harvestLevel, weight);
    }

    private static Block blockOf(ItemStack stack) {
        Item item = stack.getItem();
        if (item instanceof ItemBlock) return ((ItemBlock) item).field_150939_a;
        return Block.getBlockFromItem(item);
    }

    /**
     * Picks an ore no more than one tier above the one that was broken.
     *
     * @param brokenHarvestLevel the harvest level of the block the player mined
     * @return a copy ready to add to the drops, or null if the pool is empty
     */
    public static ItemStack roll(int brokenHarvestLevel, Random rand) {
        if (POOL.isEmpty()) return null;

        int ceiling = brokenHarvestLevel + TIER_HEADROOM;

        int total = 0;
        for (int i = 0; i < POOL.size(); i++) {
            Entry e = POOL.get(i);
            if (e.harvestLevel <= ceiling) total += e.weight;
        }
        if (total <= 0) return null;

        int pick = rand.nextInt(total);
        for (int i = 0; i < POOL.size(); i++) {
            Entry e = POOL.get(i);
            if (e.harvestLevel > ceiling) continue;
            pick -= e.weight;
            if (pick < 0) return e.stack.copy();
        }
        return null;
    }

    public static int size() {
        return POOL.size();
    }
}
