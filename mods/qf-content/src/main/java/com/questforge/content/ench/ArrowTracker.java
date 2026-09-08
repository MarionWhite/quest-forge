package com.questforge.content.ench;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.WeakHashMap;

import net.minecraft.entity.projectile.EntityArrow;
import net.minecraft.item.ItemStack;

/**
 * Remembers which bow fired which arrow.
 *
 * An EntityArrow keeps no reference to the bow, so without this a bow enchantment
 * has nothing to read once the arrow is in flight. Tagged at spawn, read on tick
 * and on hit.
 *
 * WeakHashMap so a collected arrow takes its entry with it; nothing here survives
 * a save, which is fine because an arrow in flight across a reload is not worth
 * the bookkeeping.
 */
public class ArrowTracker {

    private static final Map<EntityArrow, ItemStack> BOWS =
            new WeakHashMap<EntityArrow, ItemStack>();

    /** [0] = times pierced, [1] = times bounced. Bounds Penetrating and Ricochet. */
    private static final Map<EntityArrow, int[]> COUNTERS =
            new WeakHashMap<EntityArrow, int[]>();

    public static void track(EntityArrow arrow, ItemStack bow) {
        if (arrow == null || bow == null) return;
        BOWS.put(arrow, bow.copy());
    }

    /** The bow that fired this arrow, or null if we were not watching. */
    public static ItemStack bowFor(EntityArrow arrow) {
        return arrow == null ? null : BOWS.get(arrow);
    }

    public static boolean isTracked(EntityArrow arrow) {
        return arrow != null && BOWS.containsKey(arrow);
    }

    public static void forget(EntityArrow arrow) {
        BOWS.remove(arrow);
        COUNTERS.remove(arrow);
    }

    /** Snapshot of currently tracked arrows, safe to iterate while modifying. */
    public static List<EntityArrow> tracked() {
        return new ArrayList<EntityArrow>(BOWS.keySet());
    }

    private static int[] counters(EntityArrow arrow) {
        int[] c = COUNTERS.get(arrow);
        if (c == null) {
            c = new int[2];
            COUNTERS.put(arrow, c);
        }
        return c;
    }

    public static int pierceCount(EntityArrow arrow) {
        return counters(arrow)[0];
    }

    public static void incrementPierce(EntityArrow arrow) {
        counters(arrow)[0]++;
    }

    public static int bounceCount(EntityArrow arrow) {
        return counters(arrow)[1];
    }

    public static void incrementBounce(EntityArrow arrow) {
        counters(arrow)[1]++;
    }

    /** Carries the bow and the counters onto a follow-up arrow. */
    public static void copyTags(EntityArrow from, EntityArrow to) {
        ItemStack bow = BOWS.get(from);
        if (bow != null) BOWS.put(to, bow);

        int[] c = COUNTERS.get(from);
        if (c != null) COUNTERS.put(to, new int[] { c[0], c[1] });
    }
}
