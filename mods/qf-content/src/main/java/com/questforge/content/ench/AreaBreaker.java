package com.questforge.content.ench;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.LinkedList;
import java.util.List;
import java.util.Queue;
import java.util.Set;

import net.minecraft.block.Block;
import net.minecraft.entity.player.EntityPlayer;
import net.minecraft.item.ItemStack;
import net.minecraft.world.World;

/**
 * Breaking more than one block per swing, for Excavate, Timber and Tunneler.
 *
 * Two things this has to get right:
 *
 * 1. **Reentrancy.** Harvesting a block fires another BreakEvent, which would run
 *    the same enchantment again on each block we break -- an exponential blowup
 *    that locks the server. {@link #isActive()} guards against it.
 * 2. **A hard cap.** Vein-mining an ore body in a modded world can reach
 *    thousands of blocks. Every path here is bounded.
 */
public class AreaBreaker {

    private static final ThreadLocal<Boolean> ACTIVE = new ThreadLocal<Boolean>();

    /** True while we are breaking blocks ourselves; enchantments must stand down. */
    public static boolean isActive() {
        return Boolean.TRUE.equals(ACTIVE.get());
    }

    /** A block position. */
    public static class Pos {
        public final int x, y, z;

        public Pos(int x, int y, int z) {
            this.x = x;
            this.y = y;
            this.z = z;
        }

        @Override
        public boolean equals(Object o) {
            if (!(o instanceof Pos)) return false;
            Pos p = (Pos) o;
            return p.x == x && p.y == y && p.z == z;
        }

        @Override
        public int hashCode() {
            return (x * 31 + y) * 31 + z;
        }
    }

    /**
     * Connected blocks of the same type as the origin, up to {@code limit}.
     * Searches all 26 neighbours so diagonal veins are included.
     */
    public static List<Pos> flood(World world, int x, int y, int z, Block match, int limit) {
        List<Pos> found = new ArrayList<Pos>();
        Set<Pos> seen = new HashSet<Pos>();
        Queue<Pos> queue = new LinkedList<Pos>();

        Pos start = new Pos(x, y, z);
        queue.add(start);
        seen.add(start);

        while (!queue.isEmpty() && found.size() < limit) {
            Pos p = queue.poll();
            if (!(p.x == x && p.y == y && p.z == z)) found.add(p);

            for (int dx = -1; dx <= 1; dx++) {
                for (int dy = -1; dy <= 1; dy++) {
                    for (int dz = -1; dz <= 1; dz++) {
                        if (dx == 0 && dy == 0 && dz == 0) continue;
                        Pos n = new Pos(p.x + dx, p.y + dy, p.z + dz);
                        if (seen.contains(n)) continue;
                        seen.add(n);
                        if (world.getBlock(n.x, n.y, n.z) == match) queue.add(n);
                    }
                }
            }
        }
        return found;
    }

    /**
     * A flat slab centred on the origin, perpendicular to whichever axis the
     * player is most nearly facing -- so mining a wall widens the wall rather
     * than boring into it.
     */
    public static List<Pos> plane(EntityPlayer player, int x, int y, int z, int radius) {
        List<Pos> found = new ArrayList<Pos>();

        double lookX = Math.abs(player.getLookVec().xCoord);
        double lookY = Math.abs(player.getLookVec().yCoord);
        double lookZ = Math.abs(player.getLookVec().zCoord);

        for (int a = -radius; a <= radius; a++) {
            for (int b = -radius; b <= radius; b++) {
                if (a == 0 && b == 0) continue;
                if (lookY > lookX && lookY > lookZ) {
                    found.add(new Pos(x + a, y, z + b));      // looking up/down
                } else if (lookX > lookZ) {
                    found.add(new Pos(x, y + a, z + b));      // looking along X
                } else {
                    found.add(new Pos(x + a, y + b, z));      // looking along Z
                }
            }
        }
        return found;
    }

    /** Connected logs above the origin, for felling a tree. */
    public static List<Pos> tree(World world, int x, int y, int z, Block log, int limit) {
        List<Pos> found = new ArrayList<Pos>();
        Set<Pos> seen = new HashSet<Pos>();
        Queue<Pos> queue = new LinkedList<Pos>();

        Pos start = new Pos(x, y, z);
        queue.add(start);
        seen.add(start);

        while (!queue.isEmpty() && found.size() < limit) {
            Pos p = queue.poll();
            if (!(p.x == x && p.y == y && p.z == z)) found.add(p);

            for (int dx = -1; dx <= 1; dx++) {
                for (int dy = 0; dy <= 1; dy++) {          // upward only
                    for (int dz = -1; dz <= 1; dz++) {
                        if (dx == 0 && dy == 0 && dz == 0) continue;
                        Pos n = new Pos(p.x + dx, p.y + dy, p.z + dz);
                        if (seen.contains(n)) continue;
                        seen.add(n);
                        if (world.getBlock(n.x, n.y, n.z) == log) queue.add(n);
                    }
                }
            }
        }
        return found;
    }

    /**
     * Harvests the given positions as the player, respecting tool suitability and
     * consuming durability. Stops early if the tool would break.
     */
    public static void harvest(World world, EntityPlayer player, ItemStack tool, List<Pos> positions) {
        if (isActive() || world.isRemote) return;

        ACTIVE.set(Boolean.TRUE);
        try {
            for (Pos p : positions) {
                Block block = world.getBlock(p.x, p.y, p.z);
                if (block == null || block.isAir(world, p.x, p.y, p.z)) continue;
                if (block.getBlockHardness(world, p.x, p.y, p.z) < 0) continue;   // bedrock etc.
                if (!block.canHarvestBlock(player, world.getBlockMetadata(p.x, p.y, p.z))) continue;

                // Leave the player with a tool rather than silently destroying it.
                if (tool != null && tool.isItemStackDamageable()
                        && tool.getItemDamage() >= tool.getMaxDamage() - 1) {
                    break;
                }

                int meta = world.getBlockMetadata(p.x, p.y, p.z);
                block.harvestBlock(world, player, p.x, p.y, p.z, meta);
                world.setBlockToAir(p.x, p.y, p.z);

                if (tool != null) {
                    tool.damageItem(1, player);
                }
            }
        } finally {
            ACTIVE.remove();
        }
    }
}
