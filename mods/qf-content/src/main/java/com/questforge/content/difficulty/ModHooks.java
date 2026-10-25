package com.questforge.content.difficulty;

import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.util.Random;

import net.minecraft.entity.Entity;
import net.minecraft.entity.EntityLivingBase;
import net.minecraftforge.common.config.ConfigCategory;
import net.minecraftforge.common.config.Configuration;
import net.minecraftforge.common.config.Property;

import com.questforge.content.QuestForgeContent;

/**
 * The three other mods the tiers talk to, by reflection, so qf-content needs none
 * of them to load. Every entry point is checked against the pack's jars:
 *
 * - InfernalMobs (1.7.10): only its public API. InfernalMobsCore.processEntitySpawn
 *   is the roll its own EntityJoinWorldEvent handler makes (1 in eliteRarity,
 *   respecting its class lists); getIsRareEntity reads the result. Demoting an elite
 *   right after the roll is removeEntFromElites plus removing its NBT tag
 *   (getNBTTag): the modifier writes nothing else until its first update tick.
 *   eliteRarity is read from its public Configuration.
 * - Lycanites Mobs 1.13.0.5: its SpawnTypeBase.spawnMobs sets the public fields
 *   EntityCreatureBase.spawnedFromType (before Forge's CheckSpawn) and, for a mob
 *   event, spawnEventType = event name (before spawnEntityInWorld). Event spawners
 *   may ignore a CheckSpawn DENY (SpawnTypeBase.forceSpawning), so the join event
 *   is where an event mob is reliably refused. isBoss() marks its bosses.
 * - Soul Shards: The Old Ways: TileEntityCage sets getEntityData().setBoolean("SSTOW",
 *   true) on every mob it makes, before spawnEntityInWorld.
 */
final class ModHooks {

    private ModHooks() {}

    // ---- InfernalMobs ---------------------------------------------------------------
    private static boolean imChecked;
    private static Object imCore;
    private static Method imProcess, imIsRare, imRemove, imTag;
    private static int imRarity = 15;

    private static boolean im() {
        if (imChecked) return imCore != null;
        imChecked = true;
        try {
            Class<?> core = Class.forName("atomicstryker.infernalmobs.common.InfernalMobsCore");
            Object inst = core.getMethod("instance").invoke(null);
            imProcess = core.getMethod("processEntitySpawn", EntityLivingBase.class);
            imIsRare = core.getMethod("getIsRareEntity", EntityLivingBase.class);
            imRemove = core.getMethod("removeEntFromElites", EntityLivingBase.class);
            imTag = core.getMethod("getNBTTag");
            Object cfg = core.getField("config").get(inst);
            if (cfg instanceof Configuration) {
                ConfigCategory cat = ((Configuration) cfg).getCategory("general");
                Property p = cat != null ? cat.get("eliteRarity") : null;
                if (p != null) imRarity = Math.max(1, p.getInt(15));
            }
            imCore = inst;
            QuestForgeContent.log.info("[difficulty] InfernalMobs found; elite odds by tier active (eliteRarity "
                    + imRarity + ")");
        } catch (ClassNotFoundException e) {
            // Not in this pack/trial: elite odds are simply not adjusted.
        } catch (Throwable t) {
            QuestForgeContent.log.warn("[difficulty] InfernalMobs present but its API differs; elite odds by tier off", t);
            imCore = null;
        }
        return imCore != null;
    }

    static boolean isElite(EntityLivingBase e) {
        if (!im()) return false;
        try {
            return (Boolean) imIsRare.invoke(null, e);
        } catch (Throwable t) {
            return false;
        }
    }

    /**
     * Moves a fresh spawn's elite chance from InfernalMobs' 1/R to mult/R (capped at
     * 1), after InfernalMobs' own roll. Lower: demote an elite with probability
     * 1 - mult. Higher: further independent rolls through InfernalMobs' own
     * processEntitySpawn, k full ones plus one taken with probability f, chosen so
     * the total chance comes out exact. Returns +1 promoted, -1 demoted, 0 neither.
     */
    static int adjustElite(EntityLivingBase e, double mult, Random rand) {
        if (mult == 1.0 || !im()) return 0;
        try {
            boolean rare = (Boolean) imIsRare.invoke(null, e);
            if (mult < 1.0) {
                if (!rare || rand.nextDouble() < mult) return 0;
                imRemove.invoke(null, e);
                e.getEntityData().removeTag((String) imTag.invoke(imCore));
                return -1;
            }
            if (rare) return 0;
            double p0 = 1.0 / imRarity;
            double target = Math.min(1.0, mult * p0);
            if (p0 >= 1.0) return 0;
            // P(still normal) we need, given the first roll already missed.
            double stay = (1.0 - target) / (1.0 - p0);
            double q = 1.0 - p0;
            int k = stay <= 0 ? 200 : (int) Math.min(200, Math.floor(Math.log(stay) / Math.log(q)));
            double f = Math.max(0, Math.min(1, (1.0 - stay / Math.pow(q, k)) / p0));
            int calls = k + (rand.nextDouble() < f ? 1 : 0);
            for (int i = 0; i < calls; i++) {
                imProcess.invoke(imCore, e);
                if ((Boolean) imIsRare.invoke(null, e)) return 1;
            }
        } catch (Throwable t) {
            QuestForgeContent.log.warn("[difficulty] InfernalMobs call failed; elite odds by tier off", t);
            imCore = null;
        }
        return 0;
    }

    /** Makes a fresh elite a normal mob again (a probe wants a clean attacker). */
    static void stripElite(EntityLivingBase e) {
        if (!isElite(e)) return;
        try {
            imRemove.invoke(null, e);
            e.getEntityData().removeTag((String) imTag.invoke(imCore));
        } catch (Throwable ignored) {
        }
    }

    // ---- Lycanites Mobs -------------------------------------------------------------
    private static boolean lyChecked;
    private static Class<?> lyCreature;
    private static Field lyEventType, lyFromType, lyTypeEvent;
    private static Method lyIsBoss;

    private static boolean ly() {
        if (lyChecked) return lyCreature != null;
        lyChecked = true;
        try {
            Class<?> c = Class.forName("lycanite.lycanitesmobs.api.entity.EntityCreatureBase");
            Class<?> spawnType = Class.forName("lycanite.lycanitesmobs.api.spawning.SpawnTypeBase");
            lyEventType = c.getField("spawnEventType");
            lyFromType = c.getField("spawnedFromType");
            lyTypeEvent = spawnType.getField("mobEvent");
            lyIsBoss = c.getMethod("isBoss");
            lyCreature = c;
            QuestForgeContent.log.info("[difficulty] Lycanites Mobs found; event spawns can be refused in spawn pockets");
        } catch (ClassNotFoundException e) {
            // Not loaded.
        } catch (Throwable t) {
            QuestForgeContent.log.warn("[difficulty] Lycanites present but its fields differ; event suppression off", t);
            lyCreature = null;
        }
        return lyCreature != null;
    }

    /** True for a mob a Lycanites mob event is spawning (or spawned). */
    static boolean isLycanitesEventMob(Entity e) {
        if (!ly() || !lyCreature.isInstance(e)) return false;
        try {
            Object name = lyEventType.get(e);
            if (name instanceof String && !((String) name).isEmpty()) return true;
            Object from = lyFromType.get(e);
            return from != null && lyTypeEvent.get(from) != null;
        } catch (Throwable t) {
            return false;
        }
    }

    /** The event name a test can stamp on a mob, exactly as Lycanites does. */
    static boolean markLycanitesEventMob(Entity e, String event) {
        if (!ly() || !lyCreature.isInstance(e)) return false;
        try {
            lyEventType.set(e, event);
            return true;
        } catch (Throwable t) {
            return false;
        }
    }

    static boolean isLycanitesBoss(Entity e) {
        if (!ly() || !lyCreature.isInstance(e)) return false;
        try {
            return (Boolean) lyIsBoss.invoke(e);
        } catch (Throwable t) {
            return false;
        }
    }

    // ---- Soul Shards ----------------------------------------------------------------
    static final String SOUL_SHARDS_TAG = "SSTOW";

    /** True for a mob a Soul Shards cage made. */
    static boolean isCageMob(Entity e) {
        return e.getEntityData().getBoolean(SOUL_SHARDS_TAG);
    }
}
