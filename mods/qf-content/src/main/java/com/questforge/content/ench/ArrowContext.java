package com.questforge.content.ench;

import java.util.Random;

import net.minecraft.entity.Entity;
import net.minecraft.entity.EntityLivingBase;
import net.minecraft.entity.projectile.EntityArrow;
import net.minecraft.item.ItemStack;
import net.minecraft.world.World;

/** A ProcContext carrying the arrow in flight, plus the bow that fired it. */
public class ArrowContext extends ProcContext {

    public final EntityArrow arrow;

    public ArrowContext(EntityLivingBase shooter, Entity target, ItemStack bow,
            World world, Random rand, EntityArrow arrow, float damage) {
        super(shooter, target, bow, world, rand, null, damage);
        this.arrow = arrow;
    }
}
