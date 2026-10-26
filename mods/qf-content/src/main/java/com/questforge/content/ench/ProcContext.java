package com.questforge.content.ench;

import java.util.Random;

import net.minecraft.entity.Entity;
import net.minecraft.entity.EntityLivingBase;
import net.minecraft.item.ItemStack;
import net.minecraft.util.DamageSource;
import net.minecraft.world.World;

/**
 * Everything an enchantment effect needs, in one object.
 *
 * Effects mutate {@link #damage} rather than touching the event directly; the
 * dispatcher writes it back once at the end. That keeps enchantments unaware of
 * which event they were triggered from, which is what lets Multi Strike replay
 * them without special cases.
 */
public class ProcContext {

    /** The entity wearing/holding the enchanted item. */
    public final EntityLivingBase user;
    /** The other party. Null for effects that have no counterpart (armor ticks). */
    public final Entity target;
    /** The item carrying the enchantment. */
    public final ItemStack stack;
    public final World world;
    public final Random rand;
    /** Null outside of damage events. */
    public final DamageSource source;

    /** Level of the enchantment currently being run. Set by the dispatcher. */
    public int level;
    /** Mutable. Effects add to or scale this; the dispatcher applies it. */
    public float damage;
    /**
     * The hit as this mod received it, before any enchantment here touched it:
     * the weapon's own swing (after the target's pre-event caps and the
     * attacker's Cripple). The dispatcher sets it before the FLAT phase and
     * nothing changes it afterwards.
     *
     * The damage-over-time enchantments seed from this rather than from
     * {@link #damage} (2026-10-25, decision 0005 P2). Seeded from the boosted
     * hit, a bleed or venom inherited every multiplier that ran before it, so
     * Colossus + Rupture measured +41 points beyond independence on the Naga and
     * +33 on Mobzilla, Colossus + Venomous +46 on the Naga, Roulette + Rupture
     * +57 and Cultist + Poisonous +29 on Mobzilla. Flat adds and multipliers now
     * boost the swing only.
     */
    public float baseDamage;
    /** Set true to cancel the triggering event, where the event allows it. */
    public boolean cancelled;
    /** Which pass this is: 0 for the first, 1 for a Multi Strike replay. */
    public int pass;

    public ProcContext(EntityLivingBase user, Entity target, ItemStack stack,
            World world, Random rand, DamageSource source, float damage) {
        this.user = user;
        this.target = target;
        this.stack = stack;
        this.world = world;
        this.rand = rand;
        this.source = source;
        this.damage = damage;
    }

    /** The target as a living entity, or null if it is not one. */
    public EntityLivingBase livingTarget() {
        return target instanceof EntityLivingBase ? (EntityLivingBase) target : null;
    }

    /** True on a Multi Strike replay, for effects that want to know. */
    public boolean isReplay() {
        return pass > 0;
    }
}
