package com.questforge.content.ench;

import net.minecraft.enchantment.EnchantmentHelper;
import net.minecraft.entity.player.EntityPlayer;
import net.minecraft.item.ItemStack;
import net.minecraft.nbt.NBTTagCompound;

/**
 * Takes Demon Forged's indestructibility back off again.
 *
 * Demon Forged works by setting the vanilla "Unbreakable" tag, which 1.7.10
 * honours (ItemStack line 230). But a tag is permanent and an enchantment is not:
 * strip Demon Forged with Solvent, or lose it any other way, and without this the
 * item stays indestructible forever.
 *
 * The enchantment's own hook cannot undo it, because hooks only run for
 * enchantments that are still ON the item. So the sweep has to live outside.
 *
 * A second marker tag is written alongside, so this only ever clears Unbreakable
 * from items WE made unbreakable -- another mod's genuinely unbreakable item is
 * left alone.
 */
public class DemonForgedUpkeep {

    private static final String VANILLA = "Unbreakable";
    private static final String MARKER = "QFDemonForged";

    /** Called by the enchantment while it is present. */
    public static void mark(ItemStack stack) {
        if (stack == null) return;
        if (!stack.hasTagCompound()) stack.setTagCompound(new NBTTagCompound());

        NBTTagCompound tag = stack.getTagCompound();
        if (!tag.getBoolean(VANILLA)) tag.setBoolean(VANILLA, true);
        if (!tag.getBoolean(MARKER)) tag.setBoolean(MARKER, true);
    }

    /** Sweeps held item and armor, clearing the tag where the enchantment has gone. */
    public static void update(EntityPlayer player) {
        check(player.getHeldItem());
        for (ItemStack piece : player.inventory.armorInventory) {
            check(piece);
        }
    }

    private static void check(ItemStack stack) {
        if (stack == null || !stack.hasTagCompound()) return;

        NBTTagCompound tag = stack.getTagCompound();
        if (!tag.getBoolean(MARKER)) return;   // not ours; leave it alone

        QFEnchantment ench = QFEnchantments.demonForged;
        if (ench != null && EnchantmentHelper.getEnchantmentLevel(ench.effectId, stack) > 0) {
            return;   // still enchanted, still unbreakable
        }

        tag.removeTag(VANILLA);
        tag.removeTag(MARKER);
    }
}
