package com.questforge.content.ench;

import java.util.Random;

import net.minecraft.block.Block;
import net.minecraft.entity.player.EntityPlayer;
import net.minecraft.item.ItemStack;
import net.minecraft.world.World;
import net.minecraftforge.event.world.BlockEvent;

/** A ProcContext for the moment a block is broken, before drops are decided. */
public class BreakContext extends ProcContext {

    public final EntityPlayer player;
    public final Block block;
    public final int blockX;
    public final int blockY;
    public final int blockZ;
    public final int meta;
    /** Kept so effects can adjust dropped experience or cancel the break. */
    public final BlockEvent.BreakEvent event;

    public BreakContext(EntityPlayer player, ItemStack tool, World world, Random rand,
            BlockEvent.BreakEvent event) {
        super(player, null, tool, world, rand, null, 0F);
        this.player = player;
        this.event = event;
        this.block = event.block;
        this.blockX = event.x;
        this.blockY = event.y;
        this.blockZ = event.z;
        this.meta = event.blockMetadata;
    }
}
