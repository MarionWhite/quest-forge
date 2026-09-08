package com.questforge.content.ench.enchants;

import java.util.List;

import net.minecraft.block.Block;
import net.minecraft.enchantment.Enchantment;
import net.minecraft.entity.EntityLivingBase;
import net.minecraft.entity.item.EntityItem;
import net.minecraft.entity.monster.EntityCreeper;
import net.minecraft.entity.monster.EntitySkeleton;
import net.minecraft.entity.monster.EntityZombie;
import net.minecraft.entity.player.EntityPlayer;
import net.minecraft.init.Blocks;
import net.minecraft.init.Items;
import net.minecraft.item.ItemStack;

import net.minecraft.enchantment.EnchantmentHelper;

import com.questforge.content.ench.DropsContext;
import com.questforge.content.ench.EnchantCategory;
import com.questforge.content.ench.HarvestContext;
import com.questforge.content.ench.ProcContext;
import com.questforge.content.ench.QFEnchantment;
import com.questforge.content.ench.QFEnchantments;
import com.questforge.content.ench.Rarity;

/** Enchantments that did not fit neatly into the weapon/tool/armor files. */
public class MiscEnchants {

    /** Chance at the target's head. Only mobs vanilla has a skull for. */
    public static class Decapitate extends QFEnchantment {
        public Decapitate(int id) {
            super(id, "qf.decapitate", Rarity.COMMON, EnchantCategory.WEAPON, 3);
        }

        @Override
        public int getProcChance(int level) {
            return Math.min(40, 15 * level);   // 15 / 30 / 40%
        }

        @Override
        public void onDrops(DropsContext ctx) {
            if (ctx.world.isRemote || ctx.victim == null) return;

            int meta = skullMeta(ctx.victim);
            if (meta < 0) return;

            ItemStack skull = new ItemStack(Items.skull, 1, meta);
            ctx.drops.add(new EntityItem(ctx.world,
                    ctx.victim.posX, ctx.victim.posY + 0.5D, ctx.victim.posZ, skull));
        }

        /** Vanilla skull damage values. -1 for mobs with no head item. */
        private static int skullMeta(EntityLivingBase victim) {
            if (victim instanceof EntitySkeleton) {
                return ((EntitySkeleton) victim).getSkeletonType() == 1 ? 1 : 0;
            }
            if (victim instanceof EntityZombie) return 2;
            if (victim instanceof EntityPlayer) return 3;
            if (victim instanceof EntityCreeper) return 4;
            return -1;
        }
    }

    /**
     * Stronger Fortune, mutually exclusive with the vanilla one.
     *
     * canApplyTogether keeps vanilla Fortune off an item that already has this;
     * the book application step handles replacing an existing vanilla Fortune.
     */
    public static class FortuneV extends QFEnchantment {
        public FortuneV(int id) {
            super(id, "qf.fortune_v", Rarity.RARE, EnchantCategory.PICKAXE, 1);
        }

        @Override
        public boolean canApplyTogether(Enchantment other) {
            if (other == Enchantment.fortune || other == Enchantment.silkTouch) return false;
            if (isCustomFortune(other)) return false;
            return super.canApplyTogether(other);
        }

        @Override
        public void onHarvest(HarvestContext ctx) {
            duplicate(ctx, 5);
        }
    }

    /** As FortuneV, but more so. */
    public static class FortuneX extends QFEnchantment {
        public FortuneX(int id) {
            super(id, "qf.fortune_x", Rarity.EPIC, EnchantCategory.PICKAXE, 1);
        }

        @Override
        public boolean canApplyTogether(Enchantment other) {
            if (other == Enchantment.fortune || other == Enchantment.silkTouch) return false;
            if (isCustomFortune(other)) return false;
            return super.canApplyTogether(other);
        }

        @Override
        public void onHarvest(HarvestContext ctx) {
            duplicate(ctx, 10);
        }
    }

    /**
     * Doubles what vanilla Fortune is doing.
     *
     * It used to read Fortune V and Fortune X as well, and then duplicate a drop
     * list those had already expanded: the two multiplied, and Fortune X with Bold
     * averaged thirty ores per block. The three are now mutually exclusive, so a
     * pickaxe carries vanilla Fortune plus Bold, or Fortune V, or Fortune X.
     */
    public static class Bold extends QFEnchantment {
        public Bold(int id) {
            super(id, "qf.bold", Rarity.EPIC, EnchantCategory.PICKAXE, 1);
        }

        @Override
        public boolean canApplyTogether(Enchantment other) {
            if (isCustomFortune(other)) return false;
            return super.canApplyTogether(other);
        }

        @Override
        public void onHarvest(HarvestContext ctx) {
            if (ctx.world.isRemote || ctx.drops.isEmpty()) return;
            if (ctx.fortuneLevel <= 0) return;
            duplicate(ctx, ctx.fortuneLevel);
        }
    }

    /** Fortune V, Fortune X and Bold: one of these per tool, never two. */
    static boolean isCustomFortune(Enchantment other) {
        return other != null && (other == QFEnchantments.fortuneV
                || other == QFEnchantments.fortuneX || other == QFEnchantments.bold);
    }

    /** True if the tool carries Fortune V, Fortune X or Bold. Read by Bountiful. */
    public static boolean hasCustomFortune(net.minecraft.item.ItemStack tool) {
        if (tool == null) return false;
        for (QFEnchantment e : new QFEnchantment[] {
                QFEnchantments.fortuneV, QFEnchantments.fortuneX, QFEnchantments.bold }) {
            if (e != null && EnchantmentHelper.getEnchantmentLevel(e.effectId, tool) > 0) return true;
        }
        return false;
    }

    /**
     * Adds extra copies of the drops, weighted by an effective fortune level.
     * Only ores are boosted; duplicating cobblestone would be pointless and
     * duplicating a mod's machine block would be an exploit.
     */
    private static void duplicate(HarvestContext ctx, int fortuneLevel) {
        if (ctx.world.isRemote || ctx.drops.isEmpty()) return;
        if (!isOre(ctx.block)) return;

        int bonus = ctx.rand.nextInt(Math.max(1, fortuneLevel));
        if (bonus <= 0) return;

        List<ItemStack> extra = new java.util.ArrayList<ItemStack>();
        for (ItemStack drop : ctx.drops) {
            if (drop == null) continue;
            for (int i = 0; i < bonus; i++) extra.add(drop.copy());
        }
        ctx.drops.addAll(extra);
    }

    private static boolean isOre(Block block) {
        if (block == null) return false;
        ItemStack stack = new ItemStack(block);
        if (stack.getItem() == null) return false;
        for (int id : net.minecraftforge.oredict.OreDictionary.getOreIDs(stack)) {
            if (net.minecraftforge.oredict.OreDictionary.getOreName(id).startsWith("ore")) {
                return true;
            }
        }
        return false;
    }

    /** Freezes water you walk over. 1.7.10 has no Frost Walker. */
    public static class Frostpath extends QFEnchantment {
        /** How long laid ice lasts before it thaws: 20 seconds. */
        private static final int THAW_TICKS = 400;

        public Frostpath(int id) {
            super(id, "qf.frostpath", Rarity.RARE, EnchantCategory.BOOTS, 3);
        }

        @Override
        public boolean isMultipliable() {
            return false;
        }

        @Override
        public void onTick(ProcContext ctx) {
            EntityLivingBase user = ctx.user;
            if (user == null || ctx.world.isRemote || !user.onGround) return;
            if (user.ticksExisted % 5 != 0) return;

            int radius = ctx.level;
            int y = (int) Math.floor(user.posY) - 1;

            for (int dx = -radius; dx <= radius; dx++) {
                for (int dz = -radius; dz <= radius; dz++) {
                    int x = (int) Math.floor(user.posX) + dx;
                    int z = (int) Math.floor(user.posZ) + dz;

                    Block block = ctx.world.getBlock(x, y, z);
                    if (block != Blocks.water && block != Blocks.flowing_water) continue;
                    // Only still, source-level water, so we do not dam rivers.
                    if (ctx.world.getBlockMetadata(x, y, z) != 0) continue;

                    ctx.world.setBlock(x, y, z, Blocks.ice);
                    // ...and it thaws again, like Frost Walker's. Left permanent,
                    // a walk along the shore paved the ocean and broke other
                    // players' water sources.
                    com.questforge.content.ench.TickedEffects.addIce(
                            ctx.world, x, y, z, THAW_TICKS);
                }
            }
        }
    }
}
