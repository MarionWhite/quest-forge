package com.questforge.content.jukebox;

import java.util.concurrent.atomic.AtomicReference;

/**
 * Starts, stops and steers the current track.
 *
 * Two constraints meet here. Opening a stream talks to the network and can take
 * seconds, so it must not happen on the client thread -- a click that freezes the
 * game for three seconds is worse than one that does nothing. But OpenAL calls
 * belong on the thread that owns the context, so the source cannot simply be
 * started from the worker either.
 *
 * So loading happens on a worker and the finished source is handed to
 * {@link JukeboxTicker}, which starts it on the next client tick. Seeking and
 * replaying reuse that same path: both are just "open this track at this position",
 * which is why dragging the progress bar cannot stall the game either.
 */
public final class Playback {

    /** A source that has finished loading and is waiting for the client thread. */
    private static final AtomicReference<Pending> ready = new AtomicReference<Pending>();

    private static volatile Track loading;
    private static volatile Track playing;
    private static volatile String error;
    private static volatile long generation;
    private static volatile boolean looping;

    /** Where the current track is anchored, so replay and seek can restart it. */
    private static volatile double px, py, pz;

    /** Position a pending open was asked to start at. */
    private static volatile long seekTargetMs;

    /**
     * A track whose jukebox went away mid-song, and how far into it that happened.
     *
     * Breaking the block someone is listening through should not simply throw the
     * song away; the music belongs to the listener, not to the block. So it is put
     * down rather than discarded, and the play button at any jukebox picks it back
     * up exactly where it stopped.
     */
    private static volatile Track suspended;
    private static volatile long suspendedMs;

    private Playback() { }

    private static final class Pending {
        final DirectAudio.PcmSource source;
        final Track track;
        final double x, y, z;
        final long gen, startMs;

        Pending(DirectAudio.PcmSource source, Track track,
                double x, double y, double z, long gen, long startMs) {
            this.source = source; this.track = track;
            this.x = x; this.y = y; this.z = z;
            this.gen = gen; this.startMs = startMs;
        }
    }

    public static Track loading() { return loading; }
    public static Track playing() { return playing; }
    public static String error() { return error; }

    public static boolean isLooping() { return looping; }
    public static void setLooping(boolean on) { looping = on; }
    public static void toggleLooping() { looping = !looping; }

    /**
     * Where playback is, in milliseconds. While a seek is loading this reports the
     * target rather than the old position, so the bar stays where it was dragged
     * instead of snapping back for a second.
     */
    public static long positionMs() {
        if (loading != null) return seekTargetMs;
        if (suspended != null) return suspendedMs;
        return DirectAudio.positionMs();
    }

    /** Length of the current track, or 0 when the catalog did not report one. */
    public static long durationMs() {
        Track t = playing != null ? playing : loading != null ? loading : suspended;
        return t == null ? 0L : t.durationMs;
    }

    public static boolean hasSuspended() { return suspended != null; }

    public static Track suspendedTrack() { return suspended; }

    /**
     * Stops the audio but keeps the track and the position, for when the block
     * carrying it is broken.
     */
    public static void suspend() {
        Track t = playing != null ? playing : loading;
        long at = DirectAudio.positionMs();
        stop();
        if (t == null) return;

        suspended = t;
        suspendedMs = at;
    }

    /** Picks a suspended track back up, here. */
    public static boolean resumeSuspended(double x, double y, double z) {
        Track t = suspended;
        if (t == null) return false;

        long at = suspendedMs;
        suspended = null;
        px = x; py = y; pz = z;
        open(t, at);
        return true;
    }

    /** Throws away a suspended track, when the player clears rather than resumes. */
    public static void forget() { suspended = null; suspendedMs = 0L; }

    /** What to show in the now-playing bar, whatever state we are in. */
    public static String status() {
        Track l = loading;
        if (l != null) return "Loading " + l.title + "...";
        if (error != null) return error;
        Track p = playing;
        if (p != null && DirectAudio.isActive()) {
            return (DirectAudio.isPaused() ? "[paused] " : "") + p.label();
        }
        Track s = suspended;
        if (s != null) return "[paused] " + s.label();
        return "";
    }

    /** Begins playing a track at a world position. Returns immediately. */
    public static void play(Track track, double x, double y, double z) {
        px = x; py = y; pz = z;
        open(track, 0L);
    }

    /** Jumps to a position in the current track. */
    public static void seek(long ms) {
        Track t = playing != null ? playing : loading;
        if (t == null) return;
        if (ms < 0) ms = 0;
        long duration = t.durationMs;
        // Seeking to the very end would just stop; leave a moment of music.
        if (duration > 0 && ms > duration - 1000) ms = Math.max(0, duration - 1000);
        open(t, ms);
    }

    /** Restarts the current track from the beginning. */
    public static void replay() {
        Track t = playing != null ? playing : loading;
        if (t != null) open(t, 0L);
    }

    public static void togglePause() {
        if (!DirectAudio.isActive()) return;
        if (DirectAudio.isPaused()) DirectAudio.resume();
        else DirectAudio.pause();
    }

    /**
     * Loads a track on a worker and hands it to the client thread when ready.
     * A second call supersedes the first, so dragging the progress bar or clicking
     * through a list does not pile up half-finished streams.
     */
    private static void open(final Track track, final long startMs) {
        if (track == null) return;

        final long gen = ++generation;
        final double x = px, y = py, z = pz;
        loading = track;
        seekTargetMs = startMs;
        error = null;
        // Anything newly started replaces whatever was waiting to be picked up.
        suspended = null;

        Thread t = new Thread(new Runnable() {
            @Override public void run() {
                try {
                    DirectAudio.PcmSource src = track.open(startMs);
                    // A newer request arrived while this one was loading; drop it
                    // rather than interrupting whatever the player chose instead.
                    if (gen != generation) {
                        close(src);
                        return;
                    }
                    Pending superseded =
                            ready.getAndSet(new Pending(src, track, x, y, z, gen, startMs));
                    if (superseded != null) close(superseded.source);
                } catch (Throwable e) {
                    if (gen != generation) return;
                    String msg = e.getMessage() == null ? e.toString() : e.getMessage();
                    error = "Could not play " + track.title + ": " + msg;
                    loading = null;
                    com.questforge.content.QuestForgeContent.log.warn(
                            "[jukebox] failed to open " + track.key(), e);
                }
            }
        }, "qf-jukebox-load");
        t.setDaemon(true);
        t.start();
    }

    /**
     * Called from the client tick. Starts anything that finished loading, on the
     * thread that owns the OpenAL context.
     */
    static void pump() {
        Pending p = ready.getAndSet(null);
        if (p == null) return;

        if (p.gen != generation) { close(p.source); return; }

        String result = DirectAudio.start(p.source, p.x, p.y, p.z);
        loading = null;
        if (DirectAudio.isActive()) {
            // Where the source actually began, which is not always what was asked
            // for -- a server that ignores range requests restarts from the top,
            // and trusting the request there is what desynced the progress bar.
            long began = p.startMs;
            if (p.source instanceof StreamSource) {
                began = ((StreamSource) p.source).startedAtMs();
            }
            DirectAudio.setPositionOffsetMs(began);
            playing = p.track;
            error = null;
            JukeboxTicker.setSource(p.x, p.y, p.z);
        } else {
            playing = null;
            error = result;
            close(p.source);
        }
    }

    public static void stop() {
        generation++;
        loading = null;
        playing = null;
        error = null;
        Pending p = ready.getAndSet(null);
        if (p != null) close(p.source);
        DirectAudio.stop();
        JukeboxTicker.clearSource();
    }

    /**
     * Called when audio ends on its own. With loop on, the same track starts
     * again; otherwise the now-playing bar clears.
     */
    static void finished() {
        Track ended = playing;
        loading = null;
        playing = null;

        // Loop repeats the one track and never advances -- that is what the button
        // says it does. Otherwise the queue decides, and simply stops if empty.
        if (looping && ended != null) {
            open(ended, 0L);
            return;
        }
        Queue.advanceOnFinish(px, py, pz);
    }

    /**
     * Moves the anchor without disturbing what is playing.
     *
     * For a speaker being carried: the queue reads this when it starts the next
     * track, so without it the following song would begin wherever the last one was
     * started from and the music would be left behind on the ground.
     */
    public static void moveTo(double x, double y, double z) {
        px = x; py = y; pz = z;
    }

    /** Where the jukebox that owns playback is, for the queue to start the next one. */
    public static double blockX() { return px; }
    public static double blockY() { return py; }
    public static double blockZ() { return pz; }

    private static void close(DirectAudio.PcmSource src) {
        if (src instanceof StreamSource) ((StreamSource) src).close();
    }
}
