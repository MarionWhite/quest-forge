package com.questforge.content.ench;

import java.util.List;
import java.util.Random;

import net.minecraft.entity.EntityLivingBase;
import net.minecraft.entity.item.EntityItem;
import net.minecraft.item.ItemStack;
import net.minecraft.util.DamageSource;
import net.minecraft.world.World;

/** A ProcContext for something dying and dropping its loot. */
public class DropsContext extends ProcContext {

    /** The entity that died. */
    public final EntityLivingBase victim;
    public final int lootingLevel;
    /** Mutable: effects may add to this. */
    public final List<EntityItem> drops;

    public DropsContext(EntityLivingBase killer, EntityLivingBase victim, ItemStack weapon,
            World world, Random rand, DamageSource source,
            List<EntityItem> drops, int lootingLevel) {
        super(killer, victim, weapon, world, rand, source, 0F);
        this.victim = victim;
        this.drops = drops;
        this.lootingLevel = lootingLevel;
    }
}
