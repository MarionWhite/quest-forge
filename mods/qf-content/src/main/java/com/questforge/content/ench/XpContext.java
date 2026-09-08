package com.questforge.content.ench;

import java.util.Random;

import net.minecraft.entity.player.EntityPlayer;
import net.minecraft.item.ItemStack;
import net.minecraft.world.World;

/** A ProcContext for experience pickup, used by Mending. */
public class XpContext extends ProcContext {

    public final EntityPlayer player;
    /** Experience still unspent. Effects decrement what they consume. */
    public int xp;

    public XpContext(EntityPlayer player, ItemStack stack, World world, Random rand, int xp) {
        super(player, null, stack, world, rand, null, 0F);
        this.player = player;
        this.xp = xp;
    }
}
