package com.questforge.content.ench;

import java.util.Random;

import net.minecraft.item.ItemStack;
import net.minecraft.nbt.NBTTagCompound;

/**
 * Reading and writing the data on an enchantment book.
 *
 * The enchantment is stored by NAME, not by numeric ID. IDs are pinned in the
 * config, but a name survives even if someone edits that config -- a book would
 * become inert rather than silently turning into a different enchantment.
 */
public class BookNBT {

    public static final String ROOT = "QFBook";

    private static final String ENCH = "ench";
    private static final String LEVEL = "lvl";
    private static final String SUCCESS = "success";
    private static final String DESTROY = "destroy";
    private static final String WARD = "ward";

    /**
     * Magic Dust can never push a book to certainty. Guaranteeing an application is
     * the Binding Scroll's job, and it should stay the rarer, more valuable answer.
     */
    public static final int DUST_CAP = 95;

    public static boolean isBook(ItemStack stack) {
        return stack != null
                && stack.hasTagCompound()
                && stack.getTagCompound().hasKey(ROOT);
    }

    /** Rolls a fresh book for this enchantment, using its rarity's ranges. */
    public static ItemStack create(ItemStack stack, QFEnchantment ench, int level, Random rand) {
        return create(stack, ench, level,
                ench.rarity.rollSuccess(rand), ench.rarity.rollDestroy(rand));
    }

    public static ItemStack create(ItemStack stack, QFEnchantment ench, int level,
            int success, int destroy) {
        NBTTagCompound tag = stack.hasTagCompound() ? stack.getTagCompound() : new NBTTagCompound();
        NBTTagCompound book = new NBTTagCompound();
        book.setString(ENCH, ench.getName());
        book.setInteger(LEVEL, level);
        book.setInteger(SUCCESS, success);
        book.setInteger(DESTROY, destroy);
        tag.setTag(ROOT, book);
        stack.setTagCompound(tag);
        return stack;
    }

    private static NBTTagCompound book(ItemStack stack) {
        return isBook(stack) ? stack.getTagCompound().getCompoundTag(ROOT) : null;
    }

    /** The enchantment this book grants, or null if it names an unknown one. */
    public static QFEnchantment getEnchant(ItemStack stack) {
        NBTTagCompound b = book(stack);
        return b == null ? null : QFEnchantments.byName(b.getString(ENCH));
    }

    public static int getLevel(ItemStack stack) {
        NBTTagCompound b = book(stack);
        return b == null ? 0 : b.getInteger(LEVEL);
    }

    public static int getSuccess(ItemStack stack) {
        NBTTagCompound b = book(stack);
        return b == null ? 0 : b.getInteger(SUCCESS);
    }

    public static int getDestroy(ItemStack stack) {
        NBTTagCompound b = book(stack);
        return b == null ? 0 : b.getInteger(DESTROY);
    }

    /** Used by Magic Dust; clamped so a book can never become a certainty. */
    public static void addSuccess(ItemStack stack, int amount, int cap) {
        NBTTagCompound b = book(stack);
        if (b == null) return;
        b.setInteger(SUCCESS, Math.min(cap, b.getInteger(SUCCESS) + amount));
    }

    /** A warded book converts one shattering into an ordinary failure. */
    public static boolean hasWard(ItemStack stack) {
        NBTTagCompound b = book(stack);
        return b != null && b.getBoolean(WARD);
    }

    public static void setWard(ItemStack stack) {
        NBTTagCompound b = book(stack);
        if (b != null) b.setBoolean(WARD, true);
    }

    /** Used by the Binding Scroll: this book will apply, whatever it was rolled at. */
    public static void setGuaranteed(ItemStack stack) {
        NBTTagCompound b = book(stack);
        if (b == null) return;
        b.setInteger(SUCCESS, 100);
        b.setInteger(DESTROY, 0);
    }
}
