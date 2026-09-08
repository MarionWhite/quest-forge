package com.questforge.content.ench;

import java.util.HashMap;
import java.util.Map;
import java.util.Random;

import net.minecraft.enchantment.EnchantmentHelper;
import net.minecraft.item.ItemStack;

/**
 * The roll. Applying a book to an item resolves in one of four ways.
 */
public class EnchantApplication {

    public enum Result {
        /** Applied. Book consumed. */
        SUCCESS,
        /** Failed, item survived. Book consumed. */
        FAILED,
        /** Failed and the target was destroyed. Book consumed. */
        DESTROYED,
        /** Would have been destroyed, but the book's ward absorbed it. Book consumed. */
        WARDED,
        /** Nothing happened: wrong item type, or already has it at this level or higher. */
        INVALID
    }

    /**
     * Resolves a book against a target.
     *
     * The caller is responsible for consuming the book and for removing the
     * target on DESTROYED -- this decides the outcome, it does not mutate
     * inventories.
     */
    @SuppressWarnings("unchecked")
    public static Result apply(ItemStack target, ItemStack book, Random rand) {
        if (target == null || !BookNBT.isBook(book)) return Result.INVALID;

        QFEnchantment ench = BookNBT.getEnchant(book);
        if (ench == null) return Result.INVALID;

        int level = BookNBT.getLevel(book);
        if (level <= 0) return Result.INVALID;

        if (!ench.canApply(target)) return Result.INVALID;

        Map<Integer, Integer> current = EnchantmentHelper.getEnchantments(target);
        if (current == null) current = new HashMap<Integer, Integer>();

        Integer existing = current.get(Integer.valueOf(ench.effectId));
        if (existing != null && existing.intValue() >= level) return Result.INVALID;

        // Conflicts with something already on the item (e.g. Fortune V vs vanilla Fortune).
        for (Integer id : current.keySet()) {
            if (id.intValue() == ench.effectId) continue;
            net.minecraft.enchantment.Enchantment other =
                    net.minecraft.enchantment.Enchantment.enchantmentsList[id.intValue()];
            if (other != null && !ench.canApplyTogether(other)) return Result.INVALID;
        }

        if (rand.nextInt(100) < BookNBT.getSuccess(book)) {
            current.put(Integer.valueOf(ench.effectId), Integer.valueOf(level));
            EnchantmentHelper.setEnchantments(current, target);
            return Result.SUCCESS;
        }

        if (rand.nextInt(100) < BookNBT.getDestroy(book)) {
            // A Ward Scroll is spent here, not before: it only matters on the roll
            // that would actually have cost the item.
            return BookNBT.hasWard(book) ? Result.WARDED : Result.DESTROYED;
        }

        return Result.FAILED;
    }
}
