package com.questforge.content.ench.enchants;

import java.util.HashMap;

import net.minecraft.enchantment.EnchantmentHelper;
import net.minecraft.entity.player.EntityPlayer;
import net.minecraft.item.ItemStack;
import net.minecraft.util.ChatComponentText;
import net.minecraft.util.EnumChatFormatting;

import com.questforge.content.ench.EnchantCategory;
import com.questforge.content.ench.ProcContext;
import com.questforge.content.ench.QFEnchantment;
import com.questforge.content.ench.Rarity;

/**
 * Enchantments that only mean anything against another player.
 *
 * They are harmless against mobs rather than disabled, so nothing breaks in
 * single-player -- they simply never find a valid target.
 */
public class PvpEnchants {

    /**
     * A vanishingly small chance to strip every enchantment off an attacker's
     * gear -- custom and vanilla alike.
     */
    public static class Polarize extends QFEnchantment {
        public Polarize(int id) {
            super(id, "qf.polarize", Rarity.LEGENDARY, EnchantCategory.ARMOR, 3);
        }

        @Override
        @SuppressWarnings("unchecked")
        public void onDamaged(ProcContext ctx) {
            if (ctx.world.isRemote) return;
            if (!(ctx.target instanceof EntityPlayer)) return;

            // 0.01% per level, per hit, per armor piece. Stacks, as specified.
            if (ctx.rand.nextInt(10000) >= ctx.level) return;

            EntityPlayer victim = (EntityPlayer) ctx.target;
            int stripped = 0;

            for (ItemStack piece : victim.inventory.armorInventory) {
                if (strip(piece)) stripped++;
            }
            ItemStack held = victim.getHeldItem();
            if (strip(held)) stripped++;

            if (stripped > 0) {
                victim.addChatMessage(new ChatComponentText(
                        EnumChatFormatting.DARK_RED + "Your equipment has been stripped bare."));
                if (ctx.user instanceof EntityPlayer) {
                    ((EntityPlayer) ctx.user).addChatMessage(new ChatComponentText(
                            EnumChatFormatting.GOLD + "Polarize discharges."));
                }
            }
        }

        private static boolean strip(ItemStack stack) {
            if (stack == null || !stack.isItemEnchanted()) return false;
            EnchantmentHelper.setEnchantments(
                    new HashMap<Integer, Integer>(), stack);
            return true;
        }
    }

    /** Chance to swap held items with whoever you hit. */
    public static class Trade extends QFEnchantment {
        public Trade(int id) {
            super(id, "qf.trade", Rarity.RARE, EnchantCategory.WEAPON, 3);
        }

        @Override
        public int getProcChance(int level) {
            return 2 * level;
        }

        @Override
        public void onAttack(ProcContext ctx) {
            if (ctx.world.isRemote) return;
            if (!(ctx.target instanceof EntityPlayer) || !(ctx.user instanceof EntityPlayer)) return;

            EntityPlayer attacker = (EntityPlayer) ctx.user;
            EntityPlayer victim = (EntityPlayer) ctx.target;

            int aSlot = attacker.inventory.currentItem;
            int vSlot = victim.inventory.currentItem;

            ItemStack mine = attacker.inventory.mainInventory[aSlot];
            ItemStack theirs = victim.inventory.mainInventory[vSlot];

            attacker.inventory.mainInventory[aSlot] = theirs;
            victim.inventory.mainInventory[vSlot] = mine;

            attacker.inventory.markDirty();
            victim.inventory.markDirty();

            victim.addChatMessage(new ChatComponentText(
                    EnumChatFormatting.LIGHT_PURPLE + "Something changed hands."));
        }
    }
}
