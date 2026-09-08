package com.questforge.content.ench;

import java.util.Map;
import java.util.WeakHashMap;

import net.minecraft.entity.Entity;
import net.minecraft.entity.EntityLivingBase;

/**
 * Short-lived per-entity combat memory, for enchantments that care about what
 * happened a moment ago (consecutive hits, recent damage taken).
 *
 * WeakHashMap keyed on the entity so state disappears when the entity is
 * collected. Nothing here needs to survive a save.
 */
public class CombatState {

    /** Consecutive-hit tracking, for Momentum. */
    private static final Map<EntityLivingBase, Streak> STREAKS =
            new WeakHashMap<EntityLivingBase, Streak>();

    /** Tick at which this entity last took damage, for Riposte. */
    private static final Map<EntityLivingBase, Integer> LAST_HURT =
            new WeakHashMap<EntityLivingBase, Integer>();

    /**
     * Depth of our own damage calls currently on the stack. A counter rather
     * than a flag, because an effect can fire inside another effect's damage
     * (Cultist inside an Arc chain) and the inner exit must not clear the outer.
     */
    private static final ThreadLocal<int[]> REENTRANT = new ThreadLocal<int[]>() {
        @Override
        protected int[] initialValue() {
            return new int[1];
        }
    };

    private static class Streak {
        Entity target;
        int count;
        int lastTick;
    }

    /**
     * Records a hit and returns how many consecutive hits have landed on this same
     * target. Switching targets, or pausing longer than {@code windowTicks},
     * resets it to 1.
     */
    public static int recordHit(EntityLivingBase attacker, Entity target, int windowTicks) {
        Streak s = STREAKS.get(attacker);
        int now = attacker.ticksExisted;

        if (s == null) {
            s = new Streak();
            STREAKS.put(attacker, s);
        }

        if (s.target != target || (now - s.lastTick) > windowTicks) {
            s.count = 0;
        }

        s.target = target;
        s.count++;
        s.lastTick = now;
        return s.count;
    }

    public static void recordHurt(EntityLivingBase entity) {
        LAST_HURT.put(entity, Integer.valueOf(entity.ticksExisted));
    }

    /** True if this entity took damage within the last {@code windowTicks}. */
    public static boolean wasHurtRecently(EntityLivingBase entity, int windowTicks) {
        Integer tick = LAST_HURT.get(entity);
        return tick != null && (entity.ticksExisted - tick.intValue()) <= windowTicks;
    }

    // --- Reentrancy -------------------------------------------------------
    // Cultist damages its wielder, Rupture's bleed and Arc's chains damage other
    // entities, and every one of those fires another LivingHurtEvent that names
    // the wielder as the attacker. While any of them is on the stack the bridge
    // must not treat the resulting event as a new swing.

    public static boolean isReentrant() {
        return REENTRANT.get()[0] > 0;
    }

    public static void enter() {
        REENTRANT.get()[0]++;
    }

    public static void exit() {
        int[] depth = REENTRANT.get();
        if (depth[0] > 0) depth[0]--;
    }
}
