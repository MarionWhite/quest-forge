package com.questforge.content.ench.enchants;

import java.util.ArrayList;
import java.util.List;

import net.minecraft.block.Block;
import net.minecraft.block.BlockLog;
import net.minecraft.init.Blocks;
import net.minecraft.init.Items;
import net.minecraft.item.Item;
import net.minecraft.item.ItemStack;
import net.minecraftforge.oredict.OreDictionary;

import com.questforge.content.ench.AreaBreaker;
import com.questforge.content.ench.BreakContext;
import com.questforge.content.ench.EnchantCategory;
import com.questforge.content.ench.HarvestContext;
import com.questforge.content.ench.ProcContext;
import com.questforge.content.ench.QFEnchantment;
import com.questforge.content.ench.Rarity;
import com.questforge.content.ench.XpContext;

/** Tool enchantments. */
public class ToolEnchants {

    /** True if this block is registered as an ore by any mod. */
    static boolean isOre(Block block) {
        if (block == null) return false;
        ItemStack stack = new ItemStack(block);
        if (stack.getItem() == null) return false;
        for (int id : OreDictionary.getOreIDs(stack)) {
            String name = OreDictionary.getOreName(id);
            if (name != null && name.startsWith("ore")) return true;
        }
        return false;
    }

    /** Mines a connected vein of the same ore. */
    public static class Excavate extends QFEnchantment {
        public Excavate(int id) {
            super(id, "qf.excavate", Rarity.UNCOMMON, EnchantCategory.PICKAXE, 3);
        }

        @Override
        public boolean isMultipliable() {
            return false;   // would double-break, and the guard blocks it anyway
        }

        @Override
        public void onBreak(BreakContext ctx) {
            if (AreaBreaker.isActive() || ctx.player.isSneaking()) return;
            // Ores only. Vein-mining stone or dirt turns every swing into a
            // tunnelling charge, which is Tunneler's job, not this one's.
            if (!isOre(ctx.block)) return;

            int limit = 8 * ctx.level;   // 8 / 16 / 24
            List<AreaBreaker.Pos> vein = AreaBreaker.flood(
                    ctx.world, ctx.blockX, ctx.blockY, ctx.blockZ, ctx.block, limit);
            AreaBreaker.harvest(ctx.world, ctx.player, ctx.stack, vein);
        }
    }

    /** Fells a whole tree. */
    public static class Timber extends QFEnchantment {
        private static final int LIMIT = 128;

        public Timber(int id) {
            super(id, "qf.timber", Rarity.UNCOMMON, EnchantCategory.AXE, 1);
        }

        @Override
        public boolean isMultipliable() {
            return false;
        }

        @Override
        public void onBreak(BreakContext ctx) {
            if (AreaBreaker.isActive() || ctx.player.isSneaking()) return;
            if (!(ctx.block instanceof BlockLog)) return;

            List<AreaBreaker.Pos> logs = AreaBreaker.tree(
                    ctx.world, ctx.blockX, ctx.blockY, ctx.blockZ, ctx.block, LIMIT);
            AreaBreaker.harvest(ctx.world, ctx.player, ctx.stack, logs);
        }
    }

    /** Widens each swing into a slab. Radius grows with level. */
    public static class Tunneler extends QFEnchantment {
        public Tunneler(int id) {
            super(id, "qf.tunneler", Rarity.EPIC, EnchantCategory.PICKAXE, 3);
        }

        @Override
        public boolean isMultipliable() {
            return false;
        }

        @Override
        public void onBreak(BreakContext ctx) {
            if (AreaBreaker.isActive() || ctx.player.isSneaking()) return;

            // 3x3, 5x5, 7x7
            List<AreaBreaker.Pos> area = AreaBreaker.plane(
                    ctx.player, ctx.blockX, ctx.blockY, ctx.blockZ, ctx.level);
            AreaBreaker.harvest(ctx.world, ctx.player, ctx.stack, area);
        }
    }

    /** Chance at something useful out of otherwise worthless stone and dirt. */
    public static class Sieve extends QFEnchantment {
        public Sieve(int id) {
            super(id, "qf.sieve", Rarity.COMMON, EnchantCategory.DIGGER, 3);
        }

        @Override
        public int getProcChance(int level) {
            return 2 * level;
        }

        @Override
        public void onHarvest(HarvestContext ctx) {
            if (ctx.world.isRemote) return;
            Block b = ctx.block;
            if (b != Blocks.stone && b != Blocks.dirt && b != Blocks.gravel
                    && b != Blocks.sand && b != Blocks.cobblestone) {
                return;
            }

            // No iron nugget in 1.7.10 -- it arrived in 1.11.
            Item[] table = { Items.flint, Items.coal, Items.gold_nugget, Items.clay_ball };
            Item pick = table[ctx.rand.nextInt(table.length)];
            if (pick != null) ctx.drops.add(new ItemStack(pick, 1));
        }
    }

    /** Fortune, but for the blocks Fortune ignores. */
    public static class Bountiful extends QFEnchantment {
        public Bountiful(int id) {
            super(id, "qf.bountiful", Rarity.UNCOMMON, EnchantCategory.TOOL, 3);
        }

        @Override
        public int getProcChance(int level) {
            return 11 * level;   // 11 / 22 / 33%
        }

        @Override
        public void onHarvest(HarvestContext ctx) {
            if (ctx.world.isRemote || ctx.drops.isEmpty()) return;
            // Only blocks Fortune does not already benefit: skip anything the
            // player was already getting a fortune roll on -- vanilla's or ours.
            if (ctx.fortuneLevel > 0 || MiscEnchants.hasCustomFortune(ctx.stack)) return;

            // Never a block with a tile entity, and never a drop that carries NBT.
            // A placed backpack keeps its inventory in the item tag and a compact
            // machine keeps its room there; copying either is a duplicator.
            try {
                if (ctx.block.hasTileEntity(
                        ctx.world.getBlockMetadata(ctx.blockX, ctx.blockY, ctx.blockZ))) {
                    return;
                }
            } catch (Throwable ignored) {
                return;   // a modded block that throws here is not worth the risk
            }
            for (ItemStack drop : ctx.drops) {
                if (drop != null && drop.hasTagCompound()) return;
            }

            // One payout per position. Otherwise the loop is trivial: break a
            // block, get two, place one back, break it again.
            if (!com.questforge.content.ench.DuplicationMemory.claim(
                    ctx.world.provider.dimensionId,
                    ctx.blockX, ctx.blockY, ctx.blockZ,
                    ctx.world.getTotalWorldTime())) {
                return;
            }

            List<ItemStack> extra = new ArrayList<ItemStack>();
            for (ItemStack drop : ctx.drops) {
                if (drop != null) extra.add(drop.copy());
            }
            ctx.drops.addAll(extra);
        }
    }

    /**
     * Chance for an ore break to yield a different ore entirely.
     *
     * The replacement is drawn from a weighted distribution built at postInit from
     * whatever ores exist -- see OreDistribution. It cannot reach more than one
     * harvest tier above what was broken, so mining coal will not hand you a modded
     * endgame ore, and no mod is named anywhere.
     */
    public static class Transmuter extends QFEnchantment {
        public Transmuter(int id) {
            super(id, "qf.transmuter", Rarity.EPIC, EnchantCategory.PICKAXE, 3);
        }

        @Override
        public int getProcChance(int level) {
            return 3 * level;
        }

        @Override
        public void onHarvest(HarvestContext ctx) {
            if (ctx.world.isRemote) return;
            if (!isOre(ctx.block)) return;

            int tier = 0;
            try {
                tier = Math.max(0, ctx.block.getHarvestLevel(
                        ctx.world.getBlockMetadata(ctx.blockX, ctx.blockY, ctx.blockZ)));
            } catch (Throwable ignored) {
                // Modded block with an unusual getHarvestLevel; treat it as tier 0.
            }

            ItemStack rolled = com.questforge.content.ench.OreDistribution.roll(tier, ctx.rand);
            if (rolled != null) ctx.drops.add(rolled);
        }
    }

    /** A worn-out tool teaches you more: experience rises as durability falls. */
    public static class OldReliable extends QFEnchantment {
        public OldReliable(int id) {
            super(id, "qf.oldreliable", Rarity.UNCOMMON, EnchantCategory.TOOL, 3);
        }

        @Override
        public boolean isMultipliable() {
            return false;
        }

        @Override
        public void onBreak(BreakContext ctx) {
            ItemStack tool = ctx.stack;
            if (tool == null || !tool.isItemStackDamageable()) return;

            float worn = (float) tool.getItemDamage() / (float) tool.getMaxDamage();
            int base = ctx.event.getExpToDrop();
            if (base <= 0) return;

            ctx.event.setExpToDrop(base + Math.round(base * worn * ctx.level));
        }
    }

    /** Salvages part of a tool when it finally gives out. */
    public static class EcoFriendly extends QFEnchantment {
        public EcoFriendly(int id) {
            super(id, "qf.ecofriendly", Rarity.COMMON, EnchantCategory.TOOL, 3);
        }

        @Override
        public boolean isMultipliable() {
            return false;
        }

        @Override
        public void onItemDestroyed(ProcContext ctx) {
            if (ctx.world.isRemote || !(ctx.user instanceof net.minecraft.entity.player.EntityPlayer)) return;
            net.minecraft.entity.player.EntityPlayer player =
                    (net.minecraft.entity.player.EntityPlayer) ctx.user;

            ItemStack repair = com.questforge.content.ench.RepairMaterials.forTool(ctx.stack);
            if (repair == null) return;

            ItemStack refund = repair.copy();
            refund.stackSize = Math.min(ctx.level, 3);
            if (!player.inventory.addItemStackToInventory(refund)) {
                player.entityDropItem(refund, 0.5F);
            }
        }

    }

    /** Experience repairs your gear. 1.7.10 has no vanilla Mending. */
    public static class Mending extends QFEnchantment {
        private static final int DURABILITY_PER_XP = 2;

        public Mending(int id) {
            super(id, "qf.mending", Rarity.EPIC, EnchantCategory.ANY, 1);
        }

        @Override
        public boolean isMultipliable() {
            return false;
        }

        @Override
        public void onXpPickup(XpContext ctx) {
            ItemStack stack = ctx.stack;
            if (stack == null || ctx.xp <= 0) return;
            if (!stack.isItemStackDamageable() || stack.getItemDamage() <= 0) return;

            int repairable = Math.min(stack.getItemDamage(),
                    ctx.xp * DURABILITY_PER_XP);
            int xpSpent = (repairable + DURABILITY_PER_XP - 1) / DURABILITY_PER_XP;

            stack.setItemDamage(stack.getItemDamage() - repairable);
            ctx.xp -= xpSpent;
        }
    }
}
