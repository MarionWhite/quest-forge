package com.questforge.content.ench;

import java.util.ArrayList;
import java.util.EnumMap;
import java.util.List;
import java.util.Map;
import java.util.Random;

import net.minecraft.item.ItemStack;
import net.minecraft.util.WeightedRandomChestContent;
import net.minecraftforge.common.ChestGenHooks;

import com.questforge.content.ModItems;

/**
 * Where books come from.
 *
 * The pool is built once, after every mod has registered, and grouped by rarity so
 * a Legendary tome can only ever open into a Legendary enchantment.
 *
 * Chest generation in 1.7.10 takes a fixed ItemStack -- there is no hook for
 * "generate this item's NBT at placement time" -- which is exactly why sealed tomes
 * exist. The chest gets a plain, stackable, NBT-free tome; the roll happens when a
 * player opens it. That also makes tomes trivial to hand out as BetterQuesting
 * rewards, which have the same fixed-ItemStack limitation.
 */
public class EnchantLoot {

    private static final Map<Rarity, List<QFEnchantment>> BY_RARITY =
            new EnumMap<Rarity, List<QFEnchantment>>(Rarity.class);

    /**
     * Relative chance of a tome of each rarity turning up in a chest. Legendary is
     * deliberately close to never: the user's word on Multi Strike was "I will make
     * sure it is rare as fuck", and that applies to the whole top tier.
     */
    private static final int[] CHEST_WEIGHT = { 12, 8, 4, 2, 1 };

    public static void build() {
        BY_RARITY.clear();
        for (Rarity rarity : Rarity.values()) {
            BY_RARITY.put(rarity, new ArrayList<QFEnchantment>());
        }

        for (QFEnchantment ench : QFEnchantments.all()) {
            if (ench != null) BY_RARITY.get(ench.rarity).add(ench);
        }
    }

    /** All enchantments of one rarity. Never null; may be empty. */
    public static List<QFEnchantment> of(Rarity rarity) {
        List<QFEnchantment> list = BY_RARITY.get(rarity);
        return list == null ? new ArrayList<QFEnchantment>() : list;
    }

    /**
     * A fully rolled book of the given rarity, or null if nothing is registered at
     * that rarity (which can happen if the config disabled things).
     */
    public static ItemStack rollBook(Rarity rarity, Random rand) {
        List<QFEnchantment> pool = of(rarity);
        if (pool.isEmpty()) return null;

        QFEnchantment ench = pool.get(rand.nextInt(pool.size()));

        // Weighted toward the low end: a level 3 book should feel like a find.
        int max = ench.getMaxLevel();
        int level = 1;
        for (int i = 1; i < max; i++) {
            if (rand.nextInt(3) == 0) level++;
        }

        return ItemEnchantBook.roll(ench, level, rand);
    }

    /** Adds sealed tomes and consumables to vanilla chest generation. */
    public static void registerChestLoot() {
        addTomes(ChestGenHooks.DUNGEON_CHEST, 1, 1);
        addTomes(ChestGenHooks.MINESHAFT_CORRIDOR, 1, 1);
        addTomes(ChestGenHooks.PYRAMID_DESERT_CHEST, 1, 1);
        addTomes(ChestGenHooks.PYRAMID_JUNGLE_CHEST, 1, 1);
        addTomes(ChestGenHooks.STRONGHOLD_CORRIDOR, 1, 1);
        addTomes(ChestGenHooks.STRONGHOLD_CROSSING, 1, 1);
        addTomes(ChestGenHooks.STRONGHOLD_LIBRARY, 1, 2);
        addTomes(ChestGenHooks.VILLAGE_BLACKSMITH, 1, 1);

        addConsumables(ChestGenHooks.DUNGEON_CHEST);
        addConsumables(ChestGenHooks.MINESHAFT_CORRIDOR);
        addConsumables(ChestGenHooks.STRONGHOLD_CORRIDOR);
        addConsumables(ChestGenHooks.VILLAGE_BLACKSMITH);
    }

    private static void addTomes(String category, int min, int max) {
        for (Rarity rarity : Rarity.values()) {
            if (of(rarity).isEmpty()) continue;

            ChestGenHooks.addItem(category, new WeightedRandomChestContent(
                    new ItemStack(ModItems.sealedTome, 1, rarity.ordinal()),
                    min, max, CHEST_WEIGHT[rarity.ordinal()]));
        }
    }

    private static void addConsumables(String category) {
        // Dust is the workhorse and should be common; the two scrolls are the
        // preparation that makes a bad book worth risking, so they stay scarce.
        add(category, ItemConsumable.MAGIC_DUST, 1, 3, 10);
        add(category, ItemConsumable.WARD_SCROLL, 1, 1, 3);
        add(category, ItemConsumable.BINDING_SCROLL, 1, 1, 1);
        add(category, ItemConsumable.SOLVENT, 1, 1, 4);
    }

    private static void add(String category, int meta, int min, int max, int weight) {
        ChestGenHooks.addItem(category, new WeightedRandomChestContent(
                new ItemStack(ModItems.consumable, 1, meta), min, max, weight));
    }
}
