package com.questforge.content.census;

import cpw.mods.fml.common.eventhandler.SubscribeEvent;
import cpw.mods.fml.common.gameevent.TickEvent;

import com.questforge.content.QuestForgeContent;

/**
 * Drives the mob census.
 *
 * Separate from the census itself so that a crash in a measurement cannot take
 * the server tick with it: an entity from a 115-mod pack can throw from places
 * that have nothing to do with us, and the right outcome is a recorded failure
 * and a continued run, not a dead world.
 */
public class CensusTicker {

    @SubscribeEvent
    public void onServerTick(TickEvent.ServerTickEvent event) {
        if (event.phase != TickEvent.Phase.END) return;
        if (!MobCensus.isRunning()) return;
        try {
            MobCensus.tick();
        } catch (Throwable t) {
            QuestForgeContent.log.error("[census] mob census tick failed; stopping", t);
            try {
                MobCensus.stop();
            } catch (Throwable ignored) {}
        }
    }
}
