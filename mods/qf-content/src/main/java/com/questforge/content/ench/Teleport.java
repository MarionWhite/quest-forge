package com.questforge.content.ench;

import net.minecraft.entity.Entity;
import net.minecraft.entity.player.EntityPlayerMP;

/**
 * Moving an entity somewhere else, without crashing the server.
 *
 * {@code EntityPlayerMP.setPositionAndUpdate} is a one-line method that does
 * nothing but dereference {@code playerNetServerHandler}
 * (EntityPlayerMP.java:1020). That field is <b>null on a FakePlayer</b>, which
 * has no connection to send a position packet down. Every mod that runs an
 * automated bow, a turret or a block-breaker does so as a FakePlayer, and this
 * pack has several; so does the combat census.
 *
 * Calling it unguarded therefore turns "a fake player landed a hit with a Soul
 * Entwine bow" into a NullPointerException inside {@code LivingHurtEvent}, which
 * surfaces as {@code ReportedException: Ticking entity} and takes the server
 * down. That is exactly how this was found -- the first full combat census run
 * crashed on it after fifty-six cells.
 *
 * The guard already existed in one place ({@code CombatEnchants.Daze}); this is
 * that check, made shared, so the next enchantment that moves something cannot
 * quietly reintroduce the crash.
 */
public final class Teleport {

    private Teleport() {}

    /**
     * Puts an entity at a position and, for a real player, tells its client.
     *
     * A player with no network handler is still moved server-side, so the effect
     * happens; only the packet is skipped, because there is nobody to send it to.
     */
    public static void to(Entity entity, double x, double y, double z) {
        if (entity == null) return;

        if (entity instanceof EntityPlayerMP) {
            EntityPlayerMP player = (EntityPlayerMP) entity;
            if (player.playerNetServerHandler != null) {
                player.playerNetServerHandler.setPlayerLocation(
                        x, y, z, player.rotationYaw, player.rotationPitch);
                return;
            }
            // A FakePlayer, or a player mid-login. Move it directly.
            player.setPosition(x, y, z);
            return;
        }

        entity.setPosition(x, y, z);
    }
}
