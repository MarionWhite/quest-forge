package com.questforge.content.ench;

import java.util.Map;
import java.util.WeakHashMap;

import net.minecraft.block.Block;
import net.minecraft.enchantment.EnchantmentHelper;
import net.minecraft.entity.player.EntityPlayer;
import net.minecraft.init.Blocks;
import net.minecraft.item.ItemStack;
import net.minecraft.world.EnumSkyBlock;
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
 *
 * WHAT IT COSTS, AND WHY IT MOVES AS LITTLE AS IT DOES. Each move is two
 * relights -- the old spot going dark, the new one lighting up -- and lighting is
 * baked into chunk geometry in 1.7.10, so every client in range rebuilds every
 * render section the light reaches: up to 27 per relight, and far dearer under
 * shaders. Moving at every block boundary did that four or five times a second
 * while sprinting, which was a visible stutter for everyone nearby. So:
 *  - the light only moves once it is MOVE_DISTANCE blocks behind, which a
 *    light of 9-15 hides completely;
 *  - it is not placed at all where daylight already outshines it;
 *  - the new light goes in before the old one comes out, so the darkening pass
 *    stops at the new light instead of spreading through the whole area;
 *  - neither change notifies neighbours. The block is air to everything but
 *    the light engine, so there is nothing for a neighbour to react to.
 */
public class TorchlightUpkeep {

    /** How far (in any one axis) the player may get from the light before it follows. */
    static final int MOVE_DISTANCE = 2;

    /** Send to clients, but skip neighbour updates. See the class comment. */
    private static final int FLAGS = 2;

    /** Where a player's current light is, and which world it is in. */
    private static class Light {
        final int dim, x, y, z;

        Light(int dim, int x, int y, int z) {
            this.dim = dim;
            this.x = x;
            this.y = y;
            this.z = z;
        }

        /** Same world, and no further than MOVE_DISTANCE away on any axis. */
        boolean near(int dim, int x, int y, int z) {
            return this.dim == dim && Math.abs(this.x - x) < MOVE_DISTANCE
                    && Math.abs(this.y - y) < MOVE_DISTANCE
                    && Math.abs(this.z - z) < MOVE_DISTANCE;
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
        if (current != null && current.near(dim, x, y, z)
                && world.getBlock(current.x, current.y, current.z) == ModBlocks.enchantLight) {
            return;   // still close enough to light the player
        }

        int meta = Math.min(3, level) - 1;
        if (outshoneBySky(world, x, y, z, BlockEnchantLight.lightFor(meta))) {
            removeLight(world, current, dim);
            ACTIVE.remove(player);
            return;
        }

        Block existing = world.getBlock(x, y, z);
        if (existing != Blocks.air && existing != ModBlocks.enchantLight) {
            // Standing with our head inside something solid. Leave the old light
            // where it is rather than destroy whatever this is; the next step will
            // usually free us.
            return;
        }

        // New before old: see the class comment.
        world.setBlock(x, y, z, ModBlocks.enchantLight, meta, FLAGS);
        removeLight(world, current, dim);
        ACTIVE.put(player, new Light(dim, x, y, z));
    }

    /**
     * True when the sky alone lights this spot at least as brightly as the
     * enchantment would, so placing a light would cost a relight and show nothing.
     * Sky light is read without the block light, which our own light would
     * otherwise feed back into.
     */
    private static boolean outshoneBySky(World world, int x, int y, int z, int light) {
        if (world.provider.hasNoSky) return false;
        int sky = world.getSavedLightValue(EnumSkyBlock.Sky, x, y, z) - world.skylightSubtracted;
        return sky >= light;
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
            world.setBlock(light.x, light.y, light.z, Blocks.air, 0, FLAGS);
        }
    }

    private static int levelOn(ItemStack stack) {
        QFEnchantment ench = QFEnchantments.torchlight;
        if (ench == null || stack == null) return 0;
        return EnchantmentHelper.getEnchantmentLevel(ench.effectId, stack);
    }
}
