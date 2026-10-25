package com.questforge.content.difficulty;

import java.lang.reflect.Field;
import java.util.Collections;
import java.util.Map;
import java.util.UUID;
import java.util.WeakHashMap;

import net.minecraft.entity.Entity;
import net.minecraft.entity.EntityList;
import net.minecraft.entity.EntityLiving;
import net.minecraft.entity.EntityLivingBase;
import net.minecraft.entity.SharedMonsterAttributes;
import net.minecraft.entity.ai.attributes.AttributeModifier;
import net.minecraft.entity.ai.attributes.IAttribute;
import net.minecraft.entity.ai.attributes.IAttributeInstance;
import net.minecraft.util.DamageSource;

import net.minecraftforge.event.entity.EntityJoinWorldEvent;
import net.minecraftforge.event.entity.living.LivingHurtEvent;
import net.minecraftforge.event.entity.living.LivingSpawnEvent;
import net.minecraftforge.event.world.WorldEvent;

import cpw.mods.fml.common.eventhandler.Event;
import cpw.mods.fml.common.eventhandler.EventPriority;
import cpw.mods.fml.common.eventhandler.SubscribeEvent;
import cpw.mods.fml.relauncher.ReflectionHelper;

import com.questforge.content.QuestForgeContent;

/**
 * The difficulty tiers' event hooks (server side; registered on the Forge bus).
 *
 * - CheckSpawn: thins natural spawns by the tier's keep share, and refuses
 *   Lycanites event spawns inside a spawn pocket.
 * - EntityJoinWorld, LOWEST (after InfernalMobs' roll): stamps a new mob with its
 *   tier, refuses a Lycanites event mob in a pocket, moves the elite odds, and
 *   (on every join, idempotently) applies health, speed and XP.
 * - LivingHurt: scales the damage a tiered mob deals (HIGH, so later reductions
 *   such as enchantments apply to the scaled hit), then at LOWEST moves the
 *   armour-ignoring share straight onto the target's health.
 *
 * With no grid every handler returns on its first line.
 */
public final class DifficultyEvents {

    static final UUID HEALTH_ID = UUID.fromString("6f1d2c43-5a1e-4c8e-9a51-7d3e0a1b2c01");
    static final UUID SPEED_ID = UUID.fromString("6f1d2c43-5a1e-4c8e-9a51-7d3e0a1b2c02");

    /** Mobs whose XP has been scaled in this object's life (experienceValue is not saved, so per object). */
    private static final Map<Entity, Boolean> xpScaled = Collections.synchronizedMap(new WeakHashMap<Entity, Boolean>());
    private static Field experienceValue;

    // ---- world lifecycle --------------------------------------------------------------

    @SubscribeEvent
    public void onWorldLoad(WorldEvent.Load event) {
        if (event.world.isRemote || event.world.provider.dimensionId != 0) return;
        Difficulty.load(event.world.getSaveHandler().getWorldDirectory());
    }

    @SubscribeEvent
    public void onWorldUnload(WorldEvent.Unload event) {
        if (event.world.isRemote || event.world.provider.dimensionId != 0) return;
        Difficulty.unload();
    }

    // ---- spawning ---------------------------------------------------------------------

    @SubscribeEvent(priority = EventPriority.HIGH)
    public void onCheckSpawn(LivingSpawnEvent.CheckSpawn event) {
        if (!Difficulty.appliesTo(event.world) || event.getResult() == Event.Result.DENY) return;
        EntityLivingBase e = event.entityLiving;
        if (!Difficulty.eligible(e) || ModHooks.isCageMob(e)) return;
        Difficulty.Where w = Difficulty.tierAt(event.world, event.x, event.y, event.z);
        if (w.pocket && Difficulty.config().suppressEventsInPockets && ModHooks.isLycanitesEventMob(e)) {
            event.setResult(Event.Result.DENY);
            if (Difficulty.debugging()) Difficulty.debug("check-spawn DENY " + name(e) + ": Lycanites event spawn in a spawn pocket");
            return;
        }
        double keep = Difficulty.config().tier(w.tier).spawnKeep;
        if (keep < 1.0 && event.world.rand.nextDouble() >= keep) {
            event.setResult(Event.Result.DENY);
            if (Difficulty.debugging()) Difficulty.debug("check-spawn DENY " + name(e) + " at " + w + ": thinned (keep " + keep + ")");
        }
    }

    @SubscribeEvent(priority = EventPriority.LOWEST)
    public void onJoin(EntityJoinWorldEvent event) {
        if (event.isCanceled() || !Difficulty.appliesTo(event.world)) return;
        Entity e = event.entity;
        if (!Difficulty.eligible(e)) return;
        EntityLiving mob = (EntityLiving) e;
        int tier = Difficulty.stampedTier(mob);
        if (tier == 0) {
            Difficulty.Where w = Difficulty.tierAt(event.world, mob.posX, mob.posY, mob.posZ);
            if (w.pocket && Difficulty.config().suppressEventsInPockets && ModHooks.isLycanitesEventMob(mob)) {
                event.setCanceled(true);
                if (Difficulty.debugging()) Difficulty.debug("join CANCEL " + name(mob) + ": Lycanites event mob in a spawn pocket " + w);
                return;
            }
            Difficulty.How how = w.how;
            tier = w.tier;
            if (ModHooks.isCageMob(mob)) {
                tier = Difficulty.config().cageTier;
                how = Difficulty.How.CAGE;
            }
            Difficulty.stamp(mob, tier, how);
            int elite = ModHooks.adjustElite(mob, Difficulty.config().tier(tier).eliteOdds, event.world.rand);
            if (Difficulty.debugging()) Difficulty.debug("stamp " + name(mob) + " at " + fmt(mob) + ": T" + tier + " (" + how.name().toLowerCase()
                    + (how == Difficulty.How.CAGE ? "" : ", place " + w) + ")"
                    + (elite > 0 ? ", promoted to elite" : elite < 0 ? ", elite removed" : ""));
        }
        applyStats(mob, Difficulty.config().tier(tier));
    }

    /** Health, speed and XP for the mob's tier; safe to repeat. */
    static void applyStats(EntityLiving mob, DifficultyConfig.Tier s) {
        float before = mob.getMaxHealth();
        if (setMultiplier(mob, SharedMonsterAttributes.maxHealth, HEALTH_ID, "qf tier health", s.health)) {
            float after = mob.getMaxHealth();
            if (before > 0 && mob.getHealth() > 0) mob.setHealth(mob.getHealth() * after / before);
        }
        setMultiplier(mob, SharedMonsterAttributes.movementSpeed, SPEED_ID, "qf tier speed", s.speed);
        if (s.xp != 1.0 && xpScaled.put(mob, Boolean.TRUE) == null) {
            try {
                if (experienceValue == null) {
                    experienceValue = ReflectionHelper.findField(EntityLiving.class, "experienceValue", "field_70728_aV");
                }
                int base = experienceValue.getInt(mob);
                double v = base * s.xp;
                int n = (int) Math.floor(v);
                if (mob.worldObj.rand.nextDouble() < v - n) n++;
                experienceValue.setInt(mob, n);
            } catch (Throwable t) {
                QuestForgeContent.log.warn("[difficulty] cannot scale experience", t);
            }
        }
    }

    /** Sets a fixed-UUID multiply-total modifier to {@code mult}; true if the attribute changed. */
    static boolean setMultiplier(EntityLivingBase mob, IAttribute attr, UUID id, String label, double mult) {
        IAttributeInstance a = mob.getEntityAttribute(attr);
        if (a == null) return false;
        AttributeModifier old = a.getModifier(id);
        double want = mult - 1.0;
        if (old == null && want == 0.0) return false;
        if (old != null && Math.abs(old.getAmount() - want) < 1e-9) return false;
        if (old != null) a.removeModifier(old);
        if (want != 0.0) a.applyModifier(new AttributeModifier(id, label, want, 2).setSaved(true));
        return true;
    }

    // ---- damage ---------------------------------------------------------------------

    @SubscribeEvent(priority = EventPriority.HIGH)
    public void onHurtScale(LivingHurtEvent event) {
        if (!Difficulty.appliesTo(event.entityLiving.worldObj)) return;
        DifficultyConfig.Tier s = attackerTier(event.source);
        if (s == null || s.damage == 1.0) return;
        float before = event.ammount;
        event.ammount = (float) (event.ammount * s.damage);
        if (Difficulty.debugging()) Difficulty.debug("hit by T" + s.tier + " " + name(event.source.getEntity()) + " on " + name(event.entityLiving)
                + ": " + before + " x" + s.damage + " = " + event.ammount);
    }

    @SubscribeEvent(priority = EventPriority.LOWEST)
    public void onHurtPierce(LivingHurtEvent event) {
        if (event.isCanceled() || !Difficulty.appliesTo(event.entityLiving.worldObj)) return;
        if (event.source.isUnblockable() || event.ammount <= 0) return;
        DifficultyConfig.Tier s = attackerTier(event.source);
        if (s == null || s.armourIgnore <= 0) return;
        EntityLivingBase target = event.entityLiving;
        float part = (float) (event.ammount * s.armourIgnore);
        event.ammount -= part;
        // Straight past armour: absorption first, then health. attackEntityFrom checks
        // for death after damageEntity returns, so a lethal share still kills properly.
        float absorb = Math.min(target.getAbsorptionAmount(), part);
        target.setAbsorptionAmount(target.getAbsorptionAmount() - absorb);
        float rest = part - absorb;
        if (rest > 0) target.setHealth(target.getHealth() - rest);
        if (Difficulty.debugging()) Difficulty.debug("hit by T" + s.tier + " " + name(event.source.getEntity()) + " on " + name(target) + ": "
                + part + " ignores armour, " + event.ammount + " left to armour");
    }

    /** The tier settings of the mob behind a damage source, or null if it has none. */
    private static DifficultyConfig.Tier attackerTier(DamageSource src) {
        Entity a = src.getEntity();
        if (!(a instanceof EntityLiving)) return null;
        int t = Difficulty.stampedTier(a);
        if (t == 0 || Difficulty.isBoss(a)) return null;
        return Difficulty.config().tier(t);
    }

    static String name(Entity e) {
        if (e == null) return "null";
        String n = EntityList.getEntityString(e);
        return n != null ? n : e.getClass().getSimpleName();
    }

    private static String fmt(Entity e) {
        return String.format("(%.0f, %.0f, %.0f)", e.posX, e.posY, e.posZ);
    }
}
