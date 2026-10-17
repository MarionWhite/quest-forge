package com.questforge.content.census;

import net.minecraft.server.MinecraftServer;

import com.questforge.content.QuestForgeContent;

/**
 * Runtime half of the census tick-warp; see core.TickWarpTransformer.
 *
 * Called at the head of every MinecraftServer.tick() when -Dqf.census.tickwarp=true.
 * The outermost call runs extra, complete ticks (each a real tick() call) until
 * BUDGET_NANOS of real time is spent, then returns and lets the original body run
 * one more. The server's own loop therefore gets its tick back in under 50 ms and
 * sleeps what is left, never "falling behind".
 *
 * Game time is unchanged: every tick is one tick, and everything the census and
 * the mods it measures count in ticks -- windows, cooldowns, potion durations,
 * invulnerability frames, AI timers -- advances exactly as at normal speed. Only
 * code that reads the wall clock sees a difference; see docs/survey/combat.md.
 *
 * -Dqf.census.tickwarp.max=N caps the rate at N ticks per real second (rounded to a
 * multiple of 20 per 50 ms loop period, never below 20).
 */
public final class TickWarp {

    /** Real time spent on ticks per 50 ms loop period, leaving the loop time to sleep. */
    private static final long BUDGET_NANOS = 45_000_000L;
    private static final long REPORT_NANOS = 60_000_000_000L;

    /** Ticks a single loop period may run, including the original one; 0 = no cap. */
    private static final int PER_PERIOD = perPeriod();

    private static boolean inner;
    private static long reportedAt;
    private static long ticksSinceReport;
    private static long totalTicks;
    private static long startedAt;

    private TickWarp() {}

    private static int perPeriod() {
        String v = System.getProperty("qf.census.tickwarp.max");
        if (v == null || v.trim().isEmpty()) return 0;
        try {
            return Math.max(1, (int) Math.round(Double.parseDouble(v.trim()) / 20.0D));
        } catch (NumberFormatException e) {
            return 0;
        }
    }

    public static void beforeTick(MinecraftServer server) {
        if (inner) return;   // a tick we started ourselves
        long start = System.nanoTime();
        if (startedAt == 0L) {
            startedAt = reportedAt = start;
            QuestForgeContent.log.info("[census] tick-warp on: ticks run back to back, "
                    + (PER_PERIOD == 0 ? "uncapped" : "capped at " + (PER_PERIOD * 20) + " ticks/s")
                    + ". Game time is unchanged; wall-clock timers are not.");
        }
        int ran = 1;   // the original body, which runs after we return
        inner = true;
        try {
            while ((PER_PERIOD == 0 || ran < PER_PERIOD)
                    && server.isServerRunning()
                    && System.nanoTime() - start < BUDGET_NANOS) {
                server.tick();
                ran++;
            }
        } finally {
            inner = false;
        }
        ticksSinceReport += ran;
        totalTicks += ran;
        long now = System.nanoTime();
        if (now - reportedAt >= REPORT_NANOS) {
            double secs = (now - reportedAt) / 1e9D;
            double tps = ticksSinceReport / secs;
            QuestForgeContent.log.info(String.format("[census] tick-warp: %.0f ticks/s (%.1fx real time), "
                    + "%d ticks in %.0f s since start", tps, tps / 20.0D, totalTicks,
                    (now - startedAt) / 1e9D));
            reportedAt = now;
            ticksSinceReport = 0L;
        }
    }
}
