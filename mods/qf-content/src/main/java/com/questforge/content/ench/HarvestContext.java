package com.questforge.content.ench;

import java.util.List;
import java.util.Random;

import net.minecraft.block.Block;
import net.minecraft.entity.player.EntityPlayer;
import net.minecraft.item.ItemStack;
import net.minecraft.world.World;

/** A ProcContext for block-breaking effects, carrying the drop list. */
public class HarvestContext extends ProcContext {

    public final EntityPlayer player;
    public final Block block;
    public final int blockX;
    public final int blockY;
    public final int blockZ;
    public final int fortuneLevel;
    /** Mutable: effects may add to or remove from this. */
    public final List<ItemStack> drops;

    public HarvestContext(EntityPlayer player, ItemStack tool, World world, Random rand,
            Block block, int x, int y, int z, int fortuneLevel, List<ItemStack> drops) {
        super(player, null, tool, world, rand, null, 0F);
        this.player = player;
        this.block = block;
        this.blockX = x;
        this.blockY = y;
        this.blockZ = z;
        this.fortuneLevel = fortuneLevel;
        this.drops = drops;
    }
}
