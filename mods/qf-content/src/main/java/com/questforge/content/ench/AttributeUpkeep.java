package com.questforge.content.ench;

import java.util.UUID;

import net.minecraft.entity.SharedMonsterAttributes;
import net.minecraft.entity.ai.attributes.AttributeModifier;
import net.minecraft.entity.ai.attributes.IAttributeInstance;
import net.minecraft.entity.player.EntityPlayer;
import net.minecraft.item.ItemStack;
import net.minecraft.nbt.NBTTagCompound;

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

    /**
     * The player's health as of the last tick, kept while Vigor is worn.
     *
     * The modifier is not saved, so a player loading in has a maximum of twenty
     * when their saved health is read, and anything above twenty is clamped off
     * before the first tick puts the modifier back. This remembers the real figure
     * so it can be restored once the maximum is back.
     *
     * Chosen over saving the modifier itself, which would also fix it: a saved
     * modifier on the vanilla max-health attribute outlives this mod, so removing
     * QuestForgeContent from the pack would leave every Vigor wearer with bonus
     * hearts and nothing to take them away. A stray ForgeData float does no harm.
     * Kept outside the persisted tag on purpose: a death should not carry it over.
     */
    private static final String VIGOR_HEALTH = "QFVigorHealth";

    public static void update(EntityPlayer player) {
        int vigor = totalLevel(player, QFEnchantments.vigor);

        IAttributeInstance maxHealth = player.getEntityAttribute(SharedMonsterAttributes.maxHealth);
        boolean wasApplied = maxHealth != null && maxHealth.getModifier(VIGOR_ID) != null;

        applyModifier(player, SharedMonsterAttributes.maxHealth, VIGOR_ID, VIGOR_NAME,
                vigor * VIGOR_PER_LEVEL);

        NBTTagCompound data = player.getEntityData();
        if (vigor > 0) {
            // The modifier has only just gone back on -- a login, or a fresh
            // EntityPlayerMP -- so put back what the clamp took. Only ever upward,
            // and never for a player already dead.
            if (!wasApplied && data.hasKey(VIGOR_HEALTH)) {
                float saved = data.getFloat(VIGOR_HEALTH);
                if (player.getHealth() > 0.0F && saved > player.getHealth()) {
                    player.setHealth(Math.min(saved, player.getMaxHealth()));
                }
            }
        }

        // Never leave the player above their (possibly just lowered) maximum.
        if (player.getHealth() > player.getMaxHealth()) {
            player.setHealth(player.getMaxHealth());
        }

        if (vigor > 0) {
            data.setFloat(VIGOR_HEALTH, player.getHealth());
        } else if (data.hasKey(VIGOR_HEALTH)) {
            // Taken off: a stale figure must not refill someone who puts it back on.
            data.removeTag(VIGOR_HEALTH);
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
