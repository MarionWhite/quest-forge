package com.questforge.content.ench;

import java.util.Map;
import java.util.WeakHashMap;

import net.minecraft.block.Block;
import net.minecraft.enchantment.EnchantmentHelper;
import net.minecraft.entity.player.EntityPlayer;
import net.minecraft.init.Blocks;
import net.minecraft.item.ItemStack;
import net.minecraft.world.World;

import com.questforge.content.ModBlocks;

/**
 * Keeps exactly one invisible light block under each Torchlight user.
 *
 * The light is placed at head height rather than at the feet: it spreads further
 * that way, and it is far less likely to land inside the block the player is
 * standing on.
 *
 * Only ever touches a block that is air or one of ours, so it can never overwrite
 * anything a player built or a mod placed.
 */
public class TorchlightUpkeep {

    /** Where a player's current light is, and which world it is in. */
    private static class Light {
        final int dim, x, y, z;

        Light(int dim, int x, int y, int z) {
            this.dim = dim;
            this.x = x;
            this.y = y;
            this.z = z;
        }

        boolean at(int dim, int x, int y, int z) {
            return this.dim == dim && this.x == x && this.y == y && this.z == z;
        }
    }

    private static final Map<EntityPlayer, Light> ACTIVE = new WeakHashMap<EntityPlayer, Light>();

    /** Called from the player tick, server side only. */
    public static void tick(EntityPlayer player) {
        World world = player.worldObj;
        if (world == null || world.isRemote) return;

        int level = levelOn(player.getHeldItem());
        if (level <= 0) {
            clear(player);
            return;
        }

        int dim = world.provider.dimensionId;
        int x = (int) Math.floor(player.posX);
        int y = (int) Math.floor(player.posY + player.getEyeHeight());
        int z = (int) Math.floor(player.posZ);

        Light current = ACTIVE.get(player);
        if (current != null && current.at(dim, x, y, z)
                && world.getBlock(x, y, z) == ModBlocks.enchantLight) {
            return;   // already lit, nothing to do
        }

        removeLight(world, current, dim);

        Block existing = world.getBlock(x, y, z);
        if (existing != Blocks.air && existing != ModBlocks.enchantLight) {
            // Standing with our head inside something solid. Skip this tick rather
            // than destroy whatever it is; the next step will usually free us.
            ACTIVE.remove(player);
            return;
        }

        world.setBlock(x, y, z, ModBlocks.enchantLight, Math.min(3, level) - 1, 3);
        ACTIVE.put(player, new Light(dim, x, y, z));
    }

    /** Called when a player logs out or dies, so nothing is left behind. */
    public static void clear(EntityPlayer player) {
        Light light = ACTIVE.remove(player);
        if (light == null || player.worldObj == null) return;
        removeLight(player.worldObj, light, player.worldObj.provider.dimensionId);
    }

    /**
     * Removes a previously placed light, but only if we are in the world it was
     * placed in -- otherwise the coordinates would refer to somewhere else entirely.
     * A light stranded by a dimension change is picked up by the block's own random
     * tick instead.
     */
    private static void removeLight(World world, Light light, int currentDim) {
        if (light == null || light.dim != currentDim) return;
        if (world.getBlock(light.x, light.y, light.z) == ModBlocks.enchantLight) {
            world.setBlockToAir(light.x, light.y, light.z);
        }
    }

    private static int levelOn(ItemStack stack) {
        QFEnchantment ench = QFEnchantments.torchlight;
        if (ench == null || stack == null) return 0;
        return EnchantmentHelper.getEnchantmentLevel(ench.effectId, stack);
    }
}
