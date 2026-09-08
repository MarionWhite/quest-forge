package com.questforge.content.ench;

import java.util.HashMap;
import java.util.Map;
import java.util.WeakHashMap;

import net.minecraft.entity.EntityLivingBase;

/** Per-entity, per-ability cooldowns for the activated enchantments. */
public class Cooldowns {

    private static final Map<EntityLivingBase, Map<String, Integer>> READY_AT =
            new WeakHashMap<EntityLivingBase, Map<String, Integer>>();

    public static boolean isReady(EntityLivingBase entity, String ability) {
        Map<String, Integer> byAbility = READY_AT.get(entity);
        if (byAbility == null) return true;
        Integer ready = byAbility.get(ability);
        return ready == null || entity.ticksExisted >= ready.intValue();
    }

    public static void start(EntityLivingBase entity, String ability, int ticks) {
        Map<String, Integer> byAbility = READY_AT.get(entity);
        if (byAbility == null) {
            byAbility = new HashMap<String, Integer>();
            READY_AT.put(entity, byAbility);
        }
        byAbility.put(ability, Integer.valueOf(entity.ticksExisted + ticks));
    }

    /** Seconds remaining, for player feedback. */
    public static int secondsLeft(EntityLivingBase entity, String ability) {
        Map<String, Integer> byAbility = READY_AT.get(entity);
        if (byAbility == null) return 0;
        Integer ready = byAbility.get(ability);
        if (ready == null) return 0;
        int ticks = ready.intValue() - entity.ticksExisted;
        return ticks <= 0 ? 0 : (ticks / 20) + 1;
    }
}
