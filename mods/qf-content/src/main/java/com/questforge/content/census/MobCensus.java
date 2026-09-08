package com.questforge.content.census;

import java.io.File;
import java.lang.reflect.Constructor;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Iterator;
import java.util.List;
import java.util.Map;

import net.minecraft.entity.Entity;
import net.minecraft.entity.EntityList;
import net.minecraft.entity.EntityLiving;
import net.minecraft.entity.EntityLivingBase;
import net.minecraft.entity.IRangedAttackMob;
import net.minecraft.entity.SharedMonsterAttributes;
import net.minecraft.entity.ai.attributes.IAttributeInstance;
import net.minecraft.entity.player.EntityPlayer;
import net.minecraft.util.AxisAlignedBB;
import net.minecraft.util.DamageSource;
import net.minecraft.world.WorldServer;

import com.questforge.content.QuestForgeContent;

/**
 * Every living thing the pack registers, spawned and then hit.
 *
 * Why spawn rather than read: half of this pack's mob stats do not exist until
 * the mob is in a world. MobProperties rewrites health and damage from JSON on
 * EntityJoinWorldEvent, Lycanites and TragicMC read their own configs, InfernalMobs
 * re-rolls a mob into something several times stronger, and several bosses keep
 * their real damage in a private field that the attribute system never sees.
 * Constructing an entity and reading its attribute map therefore measures the
 * mob the mod author wrote, not the mob this pack actually fights.
 *
 * Why hit it rather than read its attributes: a mob that clamps incoming damage
 * makes every damage-multiplying enchantment worth exactly nothing, and there is
 * no attribute or flag that says so -- it is an override of attackEntityFrom.
 * Reading 700-odd overrides across 43 mods is not a plan. Hitting each mob with a
 * known number and measuring what its health bar actually lost is one line of
 * arithmetic and cannot be wrong.
 *
 * Symmetrically, a mob's outgoing damage is measured by having it hit a probe,
 * because attackEntityAsMob is free to ignore the attackDamage attribute, and in
 * this pack's bosses it generally does.
 *
 * Runs to a millisecond budget per tick, like the ore survey, because spawning
 * several hundred entities in one tick would trip the watchdog.
 */
public final class MobCensus {

    private MobCensus() {}

    /**
     * Absolute hit sizes for the damage-taken probe. Every one of these is
     * discarded if it is not comfortably below the mob's own health -- see
     * {@link #probePoints}.
     */
    private static final float[] ABSOLUTE_HITS = { 1, 2, 5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000 };

    /** Hit sizes as a fraction of the mob's own health, so big mobs get probed at their own scale. */
    private static final float[] RELATIVE_HITS = { 0.02F, 0.10F, 0.30F, 0.60F, 0.90F };

    /** How many times to ask a mob to attack, since many roll a random component. */
    private static final int ATTACK_SAMPLES = 8;

    /**
     * How many times to spawn each entity.
     *
     * Not redundancy -- this pack randomises mob stats per spawn. MobProperties
     * gives The King a maxHealth modifier of "2.0~5.0", which is a uniform roll
     * applied on every spawn, so its health is a range from three to six times
     * base rather than a number. One spawn would report one draw from that
     * distribution as though it were the answer.
     */
    private static final int SPAWN_SAMPLES = 5;

    private static final long BUDGET_NANOS = 30L * 1000000L;

    // --- run state ---------------------------------------------------------

    private static boolean running;
    private static List<String> queue;
    private static int index;
    private static File configDir;
    private static WorldServer world;
    private static CensusFile out;
    private static CensusFile failures;
    private static int measured, failed;

    /** The entity spawned last tick, waiting to be measured this tick. */
    private static Entity pending;
    private static String pendingName;

    /** Which repeat of the current entity we are on, and what the repeats have said so far. */
    private static String currentName;
    private static int sampleIndex;
    private static final List<Float> sampleHealth = new ArrayList<Float>();
    private static final List<Double> sampleAttackAttr = new ArrayList<Double>();
    private static final List<Float> sampleDealt = new ArrayList<Float>();
    /** Why the attack probe produced nothing, if it produced nothing. */
    private static String attackError;

    private static double px, py, pz;

    public static boolean isRunning() {
        return running;
    }

    public static String status() {
        if (!running) return "not running";
        return "mob census: " + index + "/" + queue.size() + " (" + measured + " measured, "
                + failed + " failed)";
    }

    public static void start(WorldServer target, File dir) {
        if (running) return;

        world = target;
        configDir = dir;
        index = 0;
        measured = 0;
        failed = 0;
        pending = null;

        queue = new ArrayList<String>();
        for (Object key : EntityList.stringToClassMapping.keySet()) {
            queue.add(String.valueOf(key));
        }
        Collections.sort(queue);

        // Somewhere solid and out of the way. Spawning several hundred mobs on
        // top of a player's base would be a rude way to take a measurement.
        px = target.getSpawnPoint().posX + 0.5D;
        pz = target.getSpawnPoint().posZ + 0.5D;
        py = target.getTopSolidOrLiquidBlock((int) px, (int) pz) + 1;

        out = new CensusFile(dir, "mobs",
                "Every registered living entity, spawned " + SPAWN_SAMPLES + " times so the pack's own "
              + "scaling applies and its randomness is visible, then hit with known damage and asked "
              + "to hit back. Damage dealt is what an UNARMOURED player loses, at this world's "
              + "difficulty, which is recorded in the calibration line in the log.",
                new String[] {
                    "entity_name", "class", "mod", "spawns",
                    "health_min", "health_med", "health_max",
                    "armor_points", "attack_attr_min", "attack_attr_max",
                    "knockback_resist", "move_speed", "follow_range",
                    "creature_attribute", "undead", "is_ranged", "width", "height", "xp_value",
                    "dmg_taken_curve", "dmg_taken_nomit", "mitigation_verdict", "armor_effect",
                    "immune_to", "dealt_min", "dealt_mean", "dealt_max", "dealt_samples",
                    "overrides_attack", "attack_error"
                });

        failures = new CensusFile(dir, "mobs-failed",
                "Entities that could not be spawned or measured, and why. Read this: an unmeasured "
              + "boss is a hole in the balance model, not an absence of one.",
                new String[] { "entity_name", "class", "stage", "error" });

        running = true;
        QuestForgeContent.log.info("[census] mob census started over " + queue.size() + " registered entities.");
    }

    public static void stop() {
        if (!running) return;
        discard();
        if (out != null) out.close();
        if (failures != null) failures.close();
        QuestForgeContent.log.info("[census] mob census finished: " + measured + " measured, "
                + failed + " failed. -> " + (out == null ? "?" : out.file().getName()));
        running = false;
        queue = null;
        world = null;
    }

    /** Called once per server tick. */
    public static void tick() {
        if (!running) return;

        long deadline = System.nanoTime() + BUDGET_NANOS;

        // Anything spawned last tick has now had a full tick of the world acting
        // on it, which is when MobProperties and the rest have applied.
        if (pending != null) {
            boolean last = sampleIndex >= SPAWN_SAMPLES;
            measure(pending, pendingName, last);
            discard();
            if (last) currentName = null;
        }

        while (System.nanoTime() < deadline && pending == null) {
            if (currentName == null) {
                if (index >= queue.size()) break;
                currentName = queue.get(index++);
                sampleIndex = 0;
                sampleHealth.clear();
                sampleAttackAttr.clear();
                sampleDealt.clear();
                attackError = null;
            }
            sampleIndex++;
            if (!spawn(currentName)) {
                // Not living, abstract, or would not construct. Recorded by
                // spawn() where it matters; move on rather than retrying it
                // SPAWN_SAMPLES times.
                currentName = null;
            }
        }

        if (index >= queue.size() && pending == null && currentName == null) {
            stop();
        }
    }

    // --- one entity --------------------------------------------------------

    /** @return true if an entity is now pending measurement. */
    private static boolean spawn(String name) {
        Class<?> cls = (Class<?>) EntityList.stringToClassMapping.get(name);
        if (cls == null) return false;

        // Only living things: the registry is full of arrows, boats and hooks.
        if (!EntityLivingBase.class.isAssignableFrom(cls)) return false;
        if (java.lang.reflect.Modifier.isAbstract(cls.getModifiers())) {
            if (sampleIndex <= 1) failures.row(name, cls.getName(), "instantiate", "abstract class");
            return false;
        }

        Entity e;
        try {
            Constructor<?> ctor = cls.getConstructor(net.minecraft.world.World.class);
            ctor.setAccessible(true);
            e = (Entity) ctor.newInstance(world);
        } catch (Throwable t) {
            if (sampleIndex <= 1) {
                failed++;
                failures.row(name, cls.getName(), "instantiate", describe(t));
            }
            return false;
        }

        try {
            e.setPosition(px, py, pz);
            // Spawning is what fires EntityJoinWorldEvent, which is where this
            // pack does most of its rewriting of mob stats.
            world.spawnEntityInWorld(e);
        } catch (Throwable t) {
            if (sampleIndex <= 1) {
                failed++;
                failures.row(name, cls.getName(), "spawn", describe(t));
            }
            try { e.setDead(); } catch (Throwable ignored) {}
            return false;
        }

        pending = e;
        pendingName = name;
        return true;
    }

    private static void measure(Entity raw, String name, boolean last) {
        if (!(raw instanceof EntityLivingBase)) return;
        EntityLivingBase mob = (EntityLivingBase) raw;
        String cls = mob.getClass().getName();

        try {
            float maxHealth = mob.getMaxHealth();
            sampleHealth.add(Float.valueOf(maxHealth));
            sampleAttackAttr.add(Double.valueOf(attribute(mob, SharedMonsterAttributes.attackDamage)));

            // Sampled on every spawn, because a mob whose damage is rolled at
            // construction varies between spawns as well as between swings.
            collectDamageDealt(mob);

            if (!last) return;

            int armour = safeArmour(mob);
            double knockback = attribute(mob, SharedMonsterAttributes.knockbackResistance);
            double speed = attribute(mob, SharedMonsterAttributes.movementSpeed);
            double follow = attribute(mob, SharedMonsterAttributes.followRange);

            float[] points = probePoints(maxHealth);
            EntityPlayer probe = CensusProbe.player(world);
            DamageSource playerHit = probe != null
                    ? DamageSource.causePlayerDamage(probe) : DamageSource.generic;

            String curve = curve(mob, playerHit, points, maxHealth);
            String nomit = curve(mob, DamageSource.generic, points, maxHealth);
            String verdict = verdict(mob, playerHit, points, maxHealth);
            String armourEffect = armourEffect(mob, playerHit, points, maxHealth);
            String immune = immunities(mob, maxHealth);

            out.row(name, cls, modOf(cls), sampleHealth.size(),
                    CensusFile.num(min(sampleHealth)), CensusFile.num(median(sampleHealth)),
                    CensusFile.num(max(sampleHealth)),
                    armour,
                    CensusFile.num(dmin(sampleAttackAttr)), CensusFile.num(dmax(sampleAttackAttr)),
                    CensusFile.num(knockback), CensusFile.num(speed), CensusFile.num(follow),
                    creatureAttribute(mob), mob.isEntityUndead(),
                    mob instanceof IRangedAttackMob,
                    CensusFile.num(mob.width), CensusFile.num(mob.height), xpValue(mob),
                    curve, nomit, verdict, armourEffect, immune,
                    sampleDealt.isEmpty() ? "" : CensusFile.num(min(sampleDealt)),
                    sampleDealt.isEmpty() ? "" : CensusFile.num(mean(sampleDealt)),
                    sampleDealt.isEmpty() ? "" : CensusFile.num(max(sampleDealt)),
                    sampleDealt.size(),
                    overridesAttack(mob),
                    attackError == null ? "" : attackError);
            measured++;
        } catch (Throwable t) {
            if (last) {
                failed++;
                failures.row(name, cls, "measure", describe(t));
            }
        }
    }

    /**
     * Hit sizes to probe this particular mob with.
     *
     * Everything is held below 90% of the mob's own health, and that constraint
     * is the entire point. Health cannot go below zero, so a 10,000-damage hit on
     * a 20-health zombie removes 20 -- and an earlier version of this file read
     * that as "this mob caps incoming damage at 20" and reported a damage cap for
     * every ordinary mob in the game. A cap is only distinguishable from an empty
     * health bar while the health bar still has room in it.
     */
    private static float[] probePoints(float maxHealth) {
        java.util.TreeSet<Float> set = new java.util.TreeSet<Float>();
        float ceiling = maxHealth * 0.9F;

        for (int i = 0; i < ABSOLUTE_HITS.length; i++) {
            if (ABSOLUTE_HITS[i] <= ceiling) set.add(Float.valueOf(ABSOLUTE_HITS[i]));
        }
        for (int i = 0; i < RELATIVE_HITS.length; i++) {
            float v = maxHealth * RELATIVE_HITS[i];
            if (v >= 0.05F) set.add(Float.valueOf(v));
        }
        if (set.isEmpty()) set.add(Float.valueOf(Math.max(0.05F, maxHealth * 0.5F)));

        float[] out = new float[set.size()];
        int i = 0;
        for (Float f : set) out[i++] = f.floatValue();
        return out;
    }

    private static String curve(EntityLivingBase mob, DamageSource src, float[] points, float maxHealth) {
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < points.length; i++) {
            float taken = applyOneHit(mob, src, points[i], maxHealth);
            if (sb.length() > 0) sb.append(' ');
            sb.append(CensusFile.num(points[i])).append(':').append(CensusFile.num(taken));
        }
        return sb.toString();
    }

    /**
     * A one-line reading of the curve. The curve itself stays in its own column,
     * because this is an interpretation and that is a measurement.
     */
    private static String verdict(EntityLivingBase mob, DamageSource src, float[] points, float maxHealth) {
        if (points.length == 0) return "unknown";
        float top = points[points.length - 1];
        float takenTop = applyOneHit(mob, src, top, maxHealth);
        if (Float.isNaN(takenTop)) return "unknown";
        if (takenTop <= 0.001F) return "immune";

        if (points.length >= 2) {
            float second = points[points.length - 2];
            float takenSecond = applyOneHit(mob, src, second, maxHealth);
            boolean plateau = Math.abs(takenTop - takenSecond) <= 0.02F * Math.max(takenTop, takenSecond);
            if (plateau && top >= second * 1.3F) {
                return "capped@" + CensusFile.num(takenTop);
            }
        }
        double ratio = takenTop / top;
        if (ratio >= 0.98D) return "linear";
        return "scaled x" + CensusFile.num(ratio);
    }

    /**
     * How much of a hit this mob's armour and resistances remove, measured by
     * comparing an ordinary player hit against one that bypasses armour.
     *
     * DamageSource.generic carries setDamageBypassesArmor, which is easy to miss
     * and makes it the wrong source for asking what a sword does -- but exactly
     * the right one for isolating what armour was contributing.
     */
    private static String armourEffect(EntityLivingBase mob, DamageSource playerHit,
            float[] points, float maxHealth) {
        if (points.length == 0) return "";
        float top = points[points.length - 1];
        float withArmour = applyOneHit(mob, playerHit, top, maxHealth);
        float without = applyOneHit(mob, DamageSource.generic, top, maxHealth);
        if (Float.isNaN(withArmour) || Float.isNaN(without) || without <= 0.001F) return "";
        return CensusFile.num(1.0D - (withArmour / without));
    }

    /** Whether this class implements its own attack, or inherits the do-nothing base. */
    private static String overridesAttack(EntityLivingBase mob) {
        try {
            Method m = mob.getClass().getMethod("attackEntityAsMob", Entity.class);
            return String.valueOf(!m.getDeclaringClass().equals(EntityLivingBase.class));
        } catch (Throwable t) {
            return "false";
        }
    }

    /**
     * One clean hit: full health, no invulnerability carried over from the last
     * probe, and the health difference read straight off the entity.
     */
    private static float applyOneHit(EntityLivingBase mob, DamageSource src, float amount, float maxHealth) {
        try {
            revive(mob, maxHealth);
            float before = mob.getHealth();
            mob.attackEntityFrom(src, amount);
            float after = mob.getHealth();
            if (mob.isDead || after < 0.0F) after = 0.0F;
            return before - after;
        } catch (Throwable t) {
            return Float.NaN;
        }
    }

    /**
     * Puts a mob back to full between probes.
     *
     * hurtResistantTime is the reason this is not just setHealth: vanilla ignores
     * a hit that arrives within ten ticks of a bigger one, so a naive sweep would
     * measure the first hit correctly and then silently record zero for every
     * hit after it.
     */
    private static void revive(EntityLivingBase mob, float maxHealth) {
        mob.isDead = false;
        mob.deathTime = 0;
        mob.hurtResistantTime = 0;
        mob.hurtTime = 0;
        mob.setHealth(maxHealth);
        mob.setPosition(px, py, pz);
        mob.motionX = mob.motionY = mob.motionZ = 0.0D;
        mob.fallDistance = 0.0F;
        try {
            mob.clearActivePotions();
        } catch (Throwable ignored) {}
    }

    /** Which damage types this mob ignores outright. */
    private static String immunities(EntityLivingBase mob, float maxHealth) {
        StringBuilder sb = new StringBuilder();
        checkImmune(sb, mob, maxHealth, "fire", DamageSource.inFire);
        checkImmune(sb, mob, maxHealth, "lava", DamageSource.lava);
        checkImmune(sb, mob, maxHealth, "drown", DamageSource.drown);
        checkImmune(sb, mob, maxHealth, "explosion", DamageSource.setExplosionSource(null));
        checkImmune(sb, mob, maxHealth, "magic", DamageSource.magic);
        checkImmune(sb, mob, maxHealth, "wither", DamageSource.wither);
        checkImmune(sb, mob, maxHealth, "fall", DamageSource.fall);
        checkImmune(sb, mob, maxHealth, "cactus", DamageSource.cactus);
        return sb.toString();
    }

    private static void checkImmune(StringBuilder sb, EntityLivingBase mob, float maxHealth,
            String label, DamageSource src) {
        float taken;
        try {
            taken = applyOneHit(mob, src, 40.0F, maxHealth);
        } catch (Throwable t) {
            return;
        }
        if (taken <= 0.001F) {
            if (sb.length() > 0) sb.append(',');
            sb.append(label);
        }
    }

    /**
     * What the mob hits for, measured by asking it to hit something.
     *
     * The probe is given an enormous health pool and no armour, so the number
     * recorded is the raw swing before any mitigation -- which is the number a
     * balance model needs, since mitigation is the part that varies by what the
     * player is wearing.
     *
     * Samples accumulate across every spawn of this entity, so both kinds of
     * variance are captured: the roll inside a single swing, and the roll that
     * happened when the mob was constructed.
     */
    private static void collectDamageDealt(EntityLivingBase mob) {
        Method attack;
        try {
            attack = mob.getClass().getMethod("attackEntityAsMob", Entity.class);
        } catch (Throwable t) {
            return;
        }

        EntityPlayer probe = CensusProbe.player(world);
        if (probe == null) return;

        for (int i = 0; i < ATTACK_SAMPLES; i++) {
            try {
                CensusProbe.reset(probe, px + 1.0D, py, pz);
                if (mob instanceof EntityLiving) {
                    ((EntityLiving) mob).setAttackTarget(probe);
                }
                mob.setPosition(px, py, pz);
                float before = probe.getHealth();
                attack.invoke(mob, probe);
                float after = probe.getHealth();
                float dealt = before - after;
                if (dealt < 0.0F) continue;
                sampleDealt.add(Float.valueOf(dealt));
            } catch (Throwable t) {
                // A mob whose attack needs state we have not set up does not
                // contribute a sample. The reason is kept: "no samples" with no
                // explanation is indistinguishable from "deals no damage", and
                // those two mean very different things for balance.
                if (attackError == null) attackError = describe(t);
            }
        }

        CensusProbe.cleanup(probe);
    }

    // --- small statistics over the repeated spawns -------------------------

    private static float min(List<Float> xs) {
        float m = Float.MAX_VALUE;
        for (int i = 0; i < xs.size(); i++) m = Math.min(m, xs.get(i).floatValue());
        return xs.isEmpty() ? Float.NaN : m;
    }

    private static float max(List<Float> xs) {
        float m = -Float.MAX_VALUE;
        for (int i = 0; i < xs.size(); i++) m = Math.max(m, xs.get(i).floatValue());
        return xs.isEmpty() ? Float.NaN : m;
    }

    private static float mean(List<Float> xs) {
        if (xs.isEmpty()) return Float.NaN;
        double t = 0.0D;
        for (int i = 0; i < xs.size(); i++) t += xs.get(i).floatValue();
        return (float) (t / xs.size());
    }

    /**
     * The median rather than the mean, because a randomised stat wants a typical
     * value and a mean is pulled around by the tail of a wide roll.
     */
    private static float median(List<Float> xs) {
        if (xs.isEmpty()) return Float.NaN;
        List<Float> copy = new ArrayList<Float>(xs);
        Collections.sort(copy);
        int n = copy.size();
        return n % 2 == 1 ? copy.get(n / 2).floatValue()
                : (copy.get(n / 2 - 1).floatValue() + copy.get(n / 2).floatValue()) / 2.0F;
    }

    private static double dmin(List<Double> xs) {
        double m = Double.MAX_VALUE;
        for (int i = 0; i < xs.size(); i++) {
            double v = xs.get(i).doubleValue();
            if (!Double.isNaN(v)) m = Math.min(m, v);
        }
        return m == Double.MAX_VALUE ? Double.NaN : m;
    }

    private static double dmax(List<Double> xs) {
        double m = -Double.MAX_VALUE;
        for (int i = 0; i < xs.size(); i++) {
            double v = xs.get(i).doubleValue();
            if (!Double.isNaN(v)) m = Math.max(m, v);
        }
        return m == -Double.MAX_VALUE ? Double.NaN : m;
    }

    // --- helpers -----------------------------------------------------------

    private static void discard() {
        if (pending != null) {
            try { pending.setDead(); } catch (Throwable ignored) {}
            try { world.removeEntity(pending); } catch (Throwable ignored) {}
            pending = null;
            pendingName = null;
        }
        sweep();
    }

    /**
     * Removes anything the probe brought with it.
     *
     * Several bosses here spawn an escort on their first tick, and a few spawn one
     * every time they are hit. Left alone, a census would end with a few thousand
     * minions standing on the world spawn.
     */
    private static void sweep() {
        if (world == null) return;
        try {
            AxisAlignedBB box = AxisAlignedBB.getBoundingBox(
                    px - 24, py - 24, pz - 24, px + 24, py + 24, pz + 24);
            List<?> found = world.getEntitiesWithinAABB(EntityLivingBase.class, box);
            for (Object o : found) {
                Entity e = (Entity) o;
                if (e instanceof EntityPlayer) continue;
                e.setDead();
                world.removeEntity(e);
            }
        } catch (Throwable ignored) {}
    }

    private static double attribute(EntityLivingBase mob, net.minecraft.entity.ai.attributes.IAttribute attr) {
        try {
            IAttributeInstance inst = mob.getEntityAttribute(attr);
            return inst == null ? Double.NaN : inst.getAttributeValue();
        } catch (Throwable t) {
            return Double.NaN;
        }
    }

    private static int safeArmour(EntityLivingBase mob) {
        try {
            return mob.getTotalArmorValue();
        } catch (Throwable t) {
            return -1;
        }
    }

    private static String creatureAttribute(EntityLivingBase mob) {
        try {
            return String.valueOf(mob.getCreatureAttribute());
        } catch (Throwable t) {
            return "";
        }
    }

    private static String xpValue(EntityLivingBase mob) {
        try {
            Field f = EntityLiving.class.getDeclaredField("experienceValue");
            f.setAccessible(true);
            return String.valueOf(f.getInt(mob));
        } catch (Throwable t) {
            return "";
        }
    }

    /** The mod that owns a class, taken from its package. Good enough to group by. */
    private static String modOf(String className) {
        if (className.startsWith("net.minecraft.")) return "minecraft";
        int dot = className.indexOf('.');
        if (dot < 0) return "?";
        int second = className.indexOf('.', dot + 1);
        return second < 0 ? className.substring(0, dot) : className.substring(0, second);
    }

    private static String describe(Throwable t) {
        Throwable root = t;
        while (root.getCause() != null && root.getCause() != root) root = root.getCause();
        String msg = root.getMessage();
        return root.getClass().getSimpleName() + (msg == null ? "" : ": " + msg);
    }
}
