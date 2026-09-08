package com.questforge.content.ench;

import java.util.ArrayList;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.WeakHashMap;

import net.minecraft.entity.EntityCreature;
import net.minecraft.entity.EntityLiving;
import net.minecraft.entity.EntityLivingBase;
import net.minecraft.util.DamageSource;
import net.minecraft.world.World;

/**
 * Effects that need to keep happening after the hit that caused them: bleed from
 * Rupture, the damage debuff from Cripple, and the temporary allies summoned by
 * Necromancer / Alpha / Bastion.
 *
 * Driven once per world tick from the event bridge. Everything here is bounded
 * and self-expiring; nothing survives a save.
 */
public class TickedEffects {

    private static final List<Bleed> BLEEDS = new ArrayList<Bleed>();
    private static final List<Summon> SUMMONS = new ArrayList<Summon>();

    /** Damage every this many ticks. */
    private static final int BLEED_INTERVAL = 20;

    private static class Bleed {
        EntityLivingBase victim;
        EntityLivingBase source;
        int stacks;
        int ticksLeft;
        int nextTick;
        /** Damage per stack per interval; the strongest application wins. */
        float perStack;
    }

    /** Marks an entity we summoned, so it can be recognised after a reload. */
    private static final String SUMMON_TAG = "QFSummon";

    /** Ice laid by Frostpath, waiting to thaw. */
    private static class Ice {
        World world;
        int x, y, z;
        int ticksLeft;
    }

    private static final List<Ice> ICE = new ArrayList<Ice>();
    private static final int MAX_ICE = 4096;

    /**
     * A summoned ally, its owner, and what it was told to fight.
     *
     * The owner matters: a summoned zombie or iron golem runs ordinary vanilla AI,
     * which re-picks the nearest player as a target every few seconds. Without
     * re-asserting this every tick, your own summons turn on you within seconds of
     * arriving.
     */
    private static class Summon {
        EntityLivingBase entity;
        EntityLivingBase owner;
        EntityLivingBase target;
        int ticksLeft;
    }

    /** How much a crippled entity's outgoing damage is cut, and until when. */
    private static class Cripple {
        float reduction;
        int ticksLeft;
    }

    private static final Map<EntityLivingBase, Cripple> CRIPPLES =
            new WeakHashMap<EntityLivingBase, Cripple>();

    // ---- Landing a tick at all -------------------------------------------

    /**
     * Applies one tick of damage over time, past the target's invulnerability.
     *
     * Vanilla gives an entity twenty ticks of invulnerability after any hit and
     * remembers how big that hit was; for the next ten ticks nothing smaller can
     * land at all. A weapon swing is worth tens of damage and a tick of bleed is
     * worth a few, so for as long as the wielder kept attacking, every tick of
     * every damage-over-time effect in this mod was discarded. Measured before
     * this existed: a hundred and forty-eight bleed ticks blocked, none landed,
     * across a hundred and fifty seconds.
     *
     * Zeroing the timer for the duration of the call is the least invasive way
     * through. The damage still goes down the normal pipeline, so LivingHurtEvent
     * fires, armor and resistance apply as the source dictates, and a kill runs
     * proper death handling with drops and experience.
     *
     * Two consequences of forcing the uninterrupted path have to be undone.
     * Vanilla would leave the timer at twenty, which would swallow the wielder's
     * next swing, so it is put back. And vanilla applies knockback on that path,
     * which on a once-a-second tick would shove the target around for the whole
     * duration, so the target's motion is restored afterwards.
     */
    public static void hurtThroughInvulnerability(EntityLivingBase victim,
            DamageSource source, float amount) {
        if (victim == null || amount <= 0.0F) return;

        int savedInvulnerability = victim.hurtResistantTime;
        double mx = victim.motionX;
        double my = victim.motionY;
        double mz = victim.motionZ;

        // The guard stops the bridge treating this as a fresh weapon swing.
        CombatState.enter();
        try {
            victim.hurtResistantTime = 0;
            victim.attackEntityFrom(source, amount);
        } finally {
            CombatState.exit();
            victim.hurtResistantTime = savedInvulnerability;
            victim.motionX = mx;
            victim.motionY = my;
            victim.motionZ = mz;
        }
    }

    // ---- Bleed -----------------------------------------------------------

    /** Adds or refreshes bleed on a target. Stacks are capped. */
    public static void addBleed(EntityLivingBase victim, EntityLivingBase source,
            int durationTicks, int maxStacks, float perStack) {
        for (Bleed b : BLEEDS) {
            if (b.victim == victim) {
                b.stacks = Math.min(maxStacks, b.stacks + 1);
                b.ticksLeft = Math.max(b.ticksLeft, durationTicks);
                b.perStack = Math.max(b.perStack, perStack);
                b.source = source;
                return;
            }
        }
        Bleed b = new Bleed();
        b.victim = victim;
        b.source = source;
        b.stacks = 1;
        b.ticksLeft = durationTicks;
        b.nextTick = BLEED_INTERVAL;
        b.perStack = perStack;
        BLEEDS.add(b);
    }

    // ---- Venom -----------------------------------------------------------

    /**
     * The damage half of Poisonous and Venomous.
     *
     * Vanilla poison deals its damage from inside Potion.performEffect, which we
     * cannot reach, so it loses every tick to the invulnerability rule exactly as
     * bleed did. This runs alongside the real poison effect rather than replacing
     * it: the target is still genuinely poisoned, so the particles, milk, curing,
     * Cleansing and undead immunity all behave as they always did, and this
     * delivers the damage that the enchantment was supposed to be doing.
     *
     * It follows the live poison amplifier rather than a fixed schedule, so
     * Accelerant raising the amplifier speeds this up too, and it expires the
     * moment the poison does.
     */
    private static class Venom {
        EntityLivingBase victim;
        EntityLivingBase source;
        int ticksLeft;
        int nextTick;
        /** Damage per SECOND, not per tick. See addVenom. */
        float perSecond;
    }

    private static final List<Venom> VENOMS = new ArrayList<Venom>();

    /**
     * Only call this once the poison effect has actually taken hold.
     *
     * The rate is per second and the per-tick amount is derived from whatever
     * cadence the poison is running at, so the throughput is the same at every
     * amplifier. That matters because Accelerant pushes poison as high as
     * amplifier VIII, where vanilla's cadence collapses to one tick: carrying a
     * fixed per-tick figure into that made Poisonous plus Accelerant worth 2.36x
     * a bare weapon, more than the strongest Epic in the mod, from an Uncommon
     * and a Rare. Vanilla gets away with the same collapse because its tick is
     * one damage and cannot kill.
     *
     * Accelerant still earns its place here through the longer duration it adds,
     * and through every other debuff it amplifies.
     */
    public static void addVenom(EntityLivingBase victim, EntityLivingBase source,
            int durationTicks, float damagePerSecond) {
        for (Venom v : VENOMS) {
            if (v.victim == victim) {
                v.ticksLeft = Math.max(v.ticksLeft, durationTicks);
                v.perSecond = Math.max(v.perSecond, damagePerSecond);
                v.source = source;
                return;
            }
        }
        Venom v = new Venom();
        v.victim = victim;
        v.source = source;
        v.ticksLeft = durationTicks;
        v.nextTick = venomInterval(victim);
        v.perSecond = damagePerSecond;
        VENOMS.add(v);
    }

    /** Vanilla's own poison cadence, read from whatever amplifier is on there now. */
    private static int venomInterval(EntityLivingBase victim) {
        net.minecraft.potion.PotionEffect poison =
                victim.getActivePotionEffect(net.minecraft.potion.Potion.poison);
        int amplifier = poison == null ? 0 : poison.getAmplifier();
        int interval = 25 >> Math.min(4, Math.max(0, amplifier));
        return interval < 1 ? 1 : interval;
    }

    private static void tickVenoms(World world) {
        Iterator<Venom> it = VENOMS.iterator();
        while (it.hasNext()) {
            Venom v = it.next();
            if (v.victim == null || v.victim.isDead) {
                it.remove();
                continue;
            }
            if (v.victim.worldObj != world) continue;

            // The poison itself is the authority: cured, expired or resisted, we stop.
            if (!v.victim.isPotionActive(net.minecraft.potion.Potion.poison)) {
                it.remove();
                continue;
            }

            v.ticksLeft--;
            if (--v.nextTick <= 0) {
                int interval = venomInterval(v.victim);
                v.nextTick = interval;
                // Magic, so armor does not blunt it, credited to the wielder.
                // Unlike vanilla poison this can finish a target: an offensive
                // enchantment that cannot land the last blow is not offensive.
                // The amount is the rate spread over this interval, so a faster
                // cadence delivers the same damage in smaller pieces.
                hurtThroughInvulnerability(v.victim,
                        DamageSource.causeIndirectMagicDamage(v.source, v.source),
                        v.perSecond * interval / 20.0F);
            }
            if (v.ticksLeft <= 0) it.remove();
        }
    }

    // ---- Frostpath ice ---------------------------------------------------

    /** Remembers ice we laid so it can thaw again; Frost Walker melts its own. */
    public static void addIce(World world, int x, int y, int z, int ticks) {
        if (ICE.size() >= MAX_ICE) return;   // never grows without bound
        Ice ice = new Ice();
        ice.world = world;
        ice.x = x;
        ice.y = y;
        ice.z = z;
        ice.ticksLeft = ticks;
        ICE.add(ice);
    }

    // ---- Summon identity -------------------------------------------------

    public static boolean isSummon(EntityLivingBase entity) {
        return entity != null && entity.getEntityData().getBoolean(SUMMON_TAG);
    }

    /**
     * A tagged summon nobody is tracking: it came back from disk after a restart
     * and has neither an expiry nor a leash any more.
     */
    public static boolean isOrphanedSummon(EntityLivingBase entity) {
        if (!isSummon(entity)) return false;
        for (Summon s : SUMMONS) {
            if (s.entity == entity) return false;
        }
        return true;
    }

    // ---- Cripple ---------------------------------------------------------

    /**
     * Cuts an entity's outgoing damage by a fraction for a while.
     *
     * 1.7.10's Weakness is a flat -0.5 damage per level, which against this pack's
     * weapons is a rounding error, so this is tracked ourselves and applied in the
     * event bridge instead.
     */
    public static void addCripple(EntityLivingBase victim, float reduction, int durationTicks) {
        Cripple c = CRIPPLES.get(victim);
        if (c == null) {
            c = new Cripple();
            CRIPPLES.put(victim, c);
        }
        // A stronger or longer application always wins; a weaker one never
        // downgrades what is already there.
        c.reduction = Math.max(c.reduction, reduction);
        c.ticksLeft = Math.max(c.ticksLeft, durationTicks);
    }

    /** How much of this attacker's damage survives. 1.0 when not crippled. */
    public static float damageMultiplier(EntityLivingBase attacker) {
        if (attacker == null) return 1.0F;
        Cripple c = CRIPPLES.get(attacker);
        if (c == null || c.ticksLeft <= 0) return 1.0F;
        return Math.max(0.0F, 1.0F - c.reduction);
    }

    // ---- Summons ---------------------------------------------------------

    /**
     * Registers a summoned ally: removed when its time is up, and kept pointed at
     * the enemy rather than at whoever summoned it.
     */
    public static void addSummon(EntityLivingBase entity, EntityLivingBase owner,
            EntityLivingBase target, int ticksLeft) {
        entity.getEntityData().setBoolean(SUMMON_TAG, true);
        Summon s = new Summon();
        s.entity = entity;
        s.owner = owner;
        s.target = target;
        s.ticksLeft = ticksLeft;
        SUMMONS.add(s);
    }

    // ---- Driving ---------------------------------------------------------

    public static void tick(World world) {
        tickBleeds(world);
        tickVenoms(world);
        tickCripples();
        tickSummons(world);
        tickIce(world);
    }

    private static void tickIce(World world) {
        Iterator<Ice> it = ICE.iterator();
        while (it.hasNext()) {
            Ice ice = it.next();
            if (ice.world != world) continue;
            if (--ice.ticksLeft > 0) continue;
            // Only ice, and only back to still water: if a player has since built
            // on the spot, or it was already broken, leave it be.
            if (world.getBlock(ice.x, ice.y, ice.z) == net.minecraft.init.Blocks.ice) {
                world.setBlock(ice.x, ice.y, ice.z, net.minecraft.init.Blocks.water, 0, 3);
            }
            it.remove();
        }
    }

    private static void tickBleeds(World world) {
        Iterator<Bleed> it = BLEEDS.iterator();
        while (it.hasNext()) {
            Bleed b = it.next();
            if (b.victim == null || b.victim.isDead || b.victim.worldObj != world) {
                if (b.victim == null || b.victim.isDead) it.remove();
                continue;
            }

            b.ticksLeft--;
            if (--b.nextTick <= 0) {
                b.nextTick = BLEED_INTERVAL;
                // Bypasses armor: bleeding does not care what you are wearing.
                // The damage names the wielder as its source so kills credit them.
                hurtThroughInvulnerability(b.victim,
                        DamageSource.causeThornsDamage(b.source).setDamageBypassesArmor(),
                        b.perStack * b.stacks);
            }
            if (b.ticksLeft <= 0) it.remove();
        }
    }

    private static void tickCripples() {
        Iterator<Map.Entry<EntityLivingBase, Cripple>> it = CRIPPLES.entrySet().iterator();
        while (it.hasNext()) {
            Cripple c = it.next().getValue();
            if (--c.ticksLeft <= 0) it.remove();
        }
    }

    private static void tickSummons(World world) {
        Iterator<Summon> it = SUMMONS.iterator();
        while (it.hasNext()) {
            Summon s = it.next();
            if (s.entity == null || s.entity.isDead) {
                it.remove();
                continue;
            }
            if (s.entity.worldObj != world) continue;

            keepPointedAtTheEnemy(s);

            if (--s.ticksLeft <= 0) {
                s.entity.worldObj.playSoundAtEntity(s.entity, "mob.endermen.portal", 0.6F, 1.4F);
                s.entity.setDead();
                it.remove();
            }
        }
    }

    /**
     * Re-asserts the summon's target every tick.
     *
     * Vanilla AI is doing its own thing underneath -- a zombie's
     * EntityAINearestAttackableTarget will happily pick the summoner, and an iron
     * golem will drop a player target on its own. Overriding it here is what makes
     * a summoned mob an ally rather than one more thing attacking you.
     */
    private static void keepPointedAtTheEnemy(Summon s) {
        if (!(s.entity instanceof EntityLiving)) return;
        EntityLiving mob = (EntityLiving) s.entity;

        EntityLivingBase current = mob.getAttackTarget();

        // Never the summoner, never a tamed animal, an NPC or another summon.
        // Other players are deliberately left in: a golem turning on a friend
        // mid-fight is an accepted risk of calling one.
        if (current == s.owner || Hostility.isProtectedBystander(current)) current = null;

        if (current == null || !current.isEntityAlive()) {
            if (s.target != null && s.target.isEntityAlive()) {
                mob.setAttackTarget(s.target);
                if (mob instanceof EntityCreature) {
                    ((EntityCreature) mob).setTarget(s.target);
                }
            } else {
                mob.setAttackTarget(null);
                s.target = null;
            }
        }
    }
}
