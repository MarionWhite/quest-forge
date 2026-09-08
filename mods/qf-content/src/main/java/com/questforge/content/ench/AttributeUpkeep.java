package com.questforge.content.ench;

import java.util.UUID;

import net.minecraft.entity.SharedMonsterAttributes;
import net.minecraft.entity.ai.attributes.AttributeModifier;
import net.minecraft.entity.ai.attributes.IAttributeInstance;
import net.minecraft.entity.player.EntityPlayer;
import net.minecraft.item.ItemStack;

/**
 * Keeps attribute modifiers in step with what the player is actually wearing.
 *
 * Attribute-based enchantments cannot be driven from the per-item tick hook: that
 * hook only runs while the item is equipped, so it can add a modifier but never
 * learns when to take it away. This recomputes the desired value from scratch each
 * tick and reconciles, which handles unequipping, dying and level changes with no
 * special cases.
 */
public class AttributeUpkeep {

    private static final UUID VIGOR_ID = UUID.fromString("6f2a1c40-8b3d-4d3a-9c1e-2f8b7a4d5e10");
    private static final String VIGOR_NAME = "qf.vigor";

    /** Extra half-hearts per level of Vigor. */
    private static final double VIGOR_PER_LEVEL = 4.0D;

    public static void update(EntityPlayer player) {
        int vigor = totalLevel(player, QFEnchantments.vigor);
        applyModifier(player, SharedMonsterAttributes.maxHealth, VIGOR_ID, VIGOR_NAME,
                vigor * VIGOR_PER_LEVEL);

        // Never leave the player above their (possibly just lowered) maximum.
        if (player.getHealth() > player.getMaxHealth()) {
            player.setHealth(player.getMaxHealth());
        }
    }

    /** Summed level across all four armor slots. */
    private static int totalLevel(EntityPlayer player, QFEnchantment ench) {
        if (ench == null) return 0;
        int total = 0;
        for (ItemStack piece : player.inventory.armorInventory) {
            if (piece == null) continue;
            total += net.minecraft.enchantment.EnchantmentHelper
                    .getEnchantmentLevel(ench.effectId, piece);
        }
        return total;
    }

    private static void applyModifier(EntityPlayer player,
            net.minecraft.entity.ai.attributes.IAttribute attribute,
            UUID id, String name, double amount) {

        IAttributeInstance instance = player.getEntityAttribute(attribute);
        if (instance == null) return;

        AttributeModifier existing = instance.getModifier(id);

        if (amount == 0.0D) {
            if (existing != null) instance.removeModifier(existing);
            return;
        }
        if (existing != null && existing.getAmount() == amount) return;

        if (existing != null) instance.removeModifier(existing);
        // Operation 0 = flat addition. Not saved: it is recomputed every tick.
        instance.applyModifier(new AttributeModifier(id, name, amount, 0).setSaved(false));
    }
}
