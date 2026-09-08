package com.questforge.content.ench;

import java.util.Map;
import java.util.WeakHashMap;

import net.minecraft.entity.player.EntityPlayer;

/**
 * Tracks whether a player is currently holding right-click.
 *
 * 1.7.10 gives no "button held" signal -- PlayerInteractEvent fires once per
 * click, not continuously. So this records the tick of the last right-click and
 * treats anything within a short window as "still holding", which is close enough
 * for a click-then-swing combination and needs no client packet.
 */
public class RightClickState {

    /** How long after a right-click still counts as holding. */
    private static final int WINDOW_TICKS = 10;

    private static final Map<EntityPlayer, Integer> LAST_CLICK =
            new WeakHashMap<EntityPlayer, Integer>();

    public static void record(EntityPlayer player) {
        LAST_CLICK.put(player, Integer.valueOf(player.ticksExisted));
    }

    public static boolean isHolding(EntityPlayer player) {
        Integer tick = LAST_CLICK.get(player);
        return tick != null && (player.ticksExisted - tick.intValue()) <= WINDOW_TICKS;
    }
}
