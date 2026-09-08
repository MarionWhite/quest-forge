package com.questforge.content.net;

import cpw.mods.fml.common.eventhandler.SubscribeEvent;
import cpw.mods.fml.common.gameevent.TickEvent;

import java.util.Queue;
import java.util.concurrent.ConcurrentLinkedQueue;

/**
 * Runs work on the server thread.
 *
 * Packet handlers execute on a netty thread, so touching world state from one races
 * the tick. 1.7.10 has no built-in scheduler for this -- MinecraftServer only gained
 * addScheduledTask in 1.8 -- and the common workaround of just mutating the world
 * from the handler anyway is a genuine race, not merely a theoretical one:
 * markBlockForUpdate walks the world's pending-update list while the tick is doing
 * the same.
 *
 * So we queue, and drain once per server tick.
 */
public class ServerTasks {

    private static final Queue<Runnable> QUEUE = new ConcurrentLinkedQueue<Runnable>();

    /** Safe to call from any thread. */
    public static void submit(Runnable task) {
        if (task != null) QUEUE.add(task);
    }

    @SubscribeEvent
    public void onServerTick(TickEvent.ServerTickEvent event) {
        if (event.phase != TickEvent.Phase.END) return;

        // Bounded per tick so a flood of packets cannot stall the server.
        for (int i = 0; i < 64; i++) {
            Runnable task = QUEUE.poll();
            if (task == null) break;
            try {
                task.run();
            } catch (Throwable t) {
                com.questforge.content.QuestForgeContent.log.error(
                        "[net] queued server task failed", t);
            }
        }
    }
}
