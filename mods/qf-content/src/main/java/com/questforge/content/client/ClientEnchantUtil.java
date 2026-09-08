package com.questforge.content.client;

import net.minecraft.client.Minecraft;
import net.minecraft.enchantment.EnchantmentHelper;
import net.minecraft.item.ItemStack;

import com.questforge.content.ench.QFEnchantment;

import cpw.mods.fml.relauncher.Side;
import cpw.mods.fml.relauncher.SideOnly;

/**
 * Lets client-side effects read the player's own enchantments.
 *
 * This is why Tracker, Prospector and Reach need no packets at all: a client
 * already holds the full NBT of its own player's inventory, enchantment tags
 * included. The server only has to be told about an effect when it happens to
 * somebody else -- which is Jammer, and Jammer alone.
 */
@SideOnly(Side.CLIENT)
public class ClientEnchantUtil {

    /** Level of the given enchantment on whatever the local player is holding. */
    public static int heldLevel(QFEnchantment ench) {
        if (ench == null) return 0;

        Minecraft mc = Minecraft.getMinecraft();
        if (mc == null || mc.thePlayer == null) return 0;

        ItemStack held = mc.thePlayer.getHeldItem();
        if (held == null) return 0;

        return EnchantmentHelper.getEnchantmentLevel(ench.effectId, held);
    }
}
