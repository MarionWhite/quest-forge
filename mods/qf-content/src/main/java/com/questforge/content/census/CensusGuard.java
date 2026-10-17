package com.questforge.content.census;

import cpw.mods.fml.common.eventhandler.EventPriority;
import cpw.mods.fml.common.eventhandler.SubscribeEvent;

import net.minecraftforge.common.MinecraftForge;
import net.minecraftforge.event.entity.living.LivingAttackEvent;

/**
 * Keeps the probe's health where the combat census put it: cancels any attack on
 * the probe that is not the census's own scheduled hit. See
 * CombatCensus.blocksAttack. Inert outside a running combat census.
 */
public final class CensusGuard {

    private static boolean registered;

    private CensusGuard() {}

    static void register() {
        if (registered) return;
        registered = true;
        MinecraftForge.EVENT_BUS.register(new CensusGuard());
    }

    @SubscribeEvent(priority = EventPriority.HIGHEST)
    public void onLivingAttack(LivingAttackEvent event) {
        if (CombatCensus.blocksAttack(event.entityLiving, event.source)) event.setCanceled(true);
    }
}
