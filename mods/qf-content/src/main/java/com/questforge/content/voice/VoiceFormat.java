package com.questforge.content.voice;

/**
 * The numbers both ends of the voice path have to agree on.
 *
 * They live in their own class because several are load-bearing on both sides of the
 * network at once -- the server's proximity filter and the client's distance fade
 * both read {@link #MAX_RANGE}, and a mismatch there is not a small bug: too small
 * on the server and voices cut out while still audibly fading in, too large and the
 * server ships audio nobody can hear.
 */
public final class VoiceFormat {

    /**
     * 24 kHz mono.
     *
     * Above the 16 kHz that "HD voice" means, and comfortably past the 8 kHz of a
     * telephone. Speech has little worth keeping above 12 kHz, so going higher would
     * cost bandwidth for detail no one would hear over a game.
     */
    public static final int RATE = 24000;

    /** 20 ms per frame -- the usual voice frame, and short enough to keep latency low. */
    public static final int FRAME_MS = 20;

    public static final int SAMPLES_PER_FRAME = RATE * FRAME_MS / 1000;   // 480

    /** Bytes of 16-bit mono PCM in one decoded frame. */
    public static final int PCM_BYTES_PER_FRAME = SAMPLES_PER_FRAME * 2;  // 960

    /**
     * Beyond this many blocks the server does not relay at all.
     *
     * Enforced server-side on purpose. Doing the cut here rather than trusting each
     * client to ignore what it receives means a modified client cannot listen in from
     * across the map -- the audio never leaves the server.
     */
    public static final float MAX_RANGE = 40f;

    /** Inside this, a voice is at full volume and not yet directional. */
    public static final float FULL_RANGE = 6f;

    /**
     * Frames per second one player may send before the server starts dropping.
     *
     * Normal is exactly 1000 / {@link #FRAME_MS} = 50. The allowance above that
     * absorbs a client whose frames bunch up after a stall, while still capping what
     * a deliberately flooding client can cost everyone else.
     */
    public static final int MAX_FRAMES_PER_SECOND = 75;

    private VoiceFormat() { }
}
