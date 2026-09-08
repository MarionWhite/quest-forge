package com.questforge.content.ench;

import net.minecraft.entity.Entity;
import net.minecraft.entity.EntityLivingBase;
import net.minecraft.entity.passive.EntityTameable;
import net.minecraft.entity.player.EntityPlayer;
import net.minecraft.server.MinecraftServer;

/**
 * One answer to "may this enchantment turn on that entity", shared by every
 * effect that picks its own targets rather than reacting to what the player hit.
 *
 * Used by Arc, Homing, Ricochet and Disarm. Summons deliberately use only the
 * weaker {@link #isProtectedBystander} half: a golem turning on a friend
 * mid-boss-fight is an accepted risk, so summons may target players, but they
 * still leave tamed animals, NPCs and other summons alone.
 *
 * CustomNPCs is detected by class name so there is no compile dependency; if the
 * mod is absent the check is simply never true.
 */
public class Hostility {

    private static Class<?> npcClass;
    private static boolean npcSearched;

    /** Neither the attacker, nor a player when PvP is off, nor anything protected. */
    public static boolean canTarget(EntityLivingBase candidate, Entity attacker) {
        if (candidate == null || !candidate.isEntityAlive()) return false;
        if (candidate == attacker) return false;
        if (candidate instanceof EntityPlayer && !pvpAllowed()) return false;
        return !isProtectedBystander(candidate);
    }

    /** Tamed animals, CustomNPCs and our own summons: never a valid target. */
    public static boolean isProtectedBystander(EntityLivingBase candidate) {
        if (candidate == null) return true;
        if (candidate instanceof EntityTameable && ((EntityTameable) candidate).isTamed()) return true;
        if (isNpc(candidate)) return true;
        return TickedEffects.isSummon(candidate);
    }

    public static boolean pvpAllowed() {
        MinecraftServer server = MinecraftServer.getServer();
        return server == null || server.isPVPEnabled();
    }

    public static boolean isNpc(Entity entity) {
        if (!npcSearched) {
            npcSearched = true;
            try {
                npcClass = Class.forName("noppes.npcs.entity.EntityNPCInterface");
            } catch (Throwable t) {
                npcClass = null;
            }
        }
        return npcClass != null && npcClass.isInstance(entity);
    }
}
