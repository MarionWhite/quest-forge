package com.questforge.content.voice;

import org.lwjgl.BufferUtils;
import org.lwjgl.openal.AL10;

import java.nio.ByteBuffer;
import java.util.ArrayDeque;
import java.util.Deque;

/**
 * One speaker's voice, as a positioned OpenAL source.
 *
 * This is {@link com.questforge.content.jukebox.DirectAudio} made instanceable. That
 * class is static throughout -- one source, one stream, one set of smoothing state --
 * which is right for a jukebox and impossible for voice, where several people talk at
 * once. The audio path is deliberately the same one it proved out, including the two
 * findings that are easy to lose: PaulsCode cannot play buffers a mod creates, so we
 * own the OpenAL source outright; and OpenAL's distance model is switched off in
 * favour of computing gain by hand, so the position we hand it can steer direction
 * without also setting loudness.
 *
 * What is new here is the jitter buffer. A jukebox reads from a file that is always
 * ready; a voice arrives in 20 ms pieces over a network that delivers them in bursts,
 * so frames are banked before playback starts and drained at a steady rate after.
 */
final class VoiceStream {

    /** Frames of slack. More is steadier through a stutter, and later to arrive. */
    private static final int BUFFER_COUNT = 12;

    /**
     * Frames banked before a voice starts.
     *
     * 80 ms. Enough to ride out the bunching that the Minecraft connection produces
     * when a chunk load stalls the pipeline, and short enough that a conversation
     * still feels immediate -- the delay a listener perceives is this plus one client
     * tick, so around 130 ms before the network's own latency.
     */
    private static final int PREBUFFER = 4;

    /**
     * Frames after which a backlog is thrown away rather than played.
     *
     * A listener who alt-tabs stops ticking, and their queue grows for as long as
     * someone is talking. Playing all of it back afterwards would be minutes of
     * stale conversation; the newest audio is the only part worth having.
     */
    private static final int MAX_BACKLOG = 50;                 // one second

    /** Matches DirectAudio: how far past full range a voice becomes fully directional. */
    private static final float SPATIAL_RAMP = 0.45f;

    /** Kept below 1 so a speaker beside you is still heard in both ears. */
    private static final double MAX_WIDTH = 0.68;

    private static final double PAN_SMOOTHING = 0.22;
    private static final float LEVEL_SMOOTHING = 0.30f;

    private final int entityId;

    private int source;
    private int[] bufs;
    private final Deque<Integer> free = new ArrayDeque<Integer>();
    private final Deque<byte[]> jitter = new ArrayDeque<byte[]>();

    private boolean allocated;
    private boolean playing;

    /** Where the speaker was in the last frame we received. */
    private double srcX, srcY, srcZ;

    private double smoothedAzimuth;
    private float smoothedGain;
    private boolean spatialPrimed;

    private long lastFrameAt;
    private float lastLevel;

    VoiceStream(int entityId) {
        this.entityId = entityId;
    }

    int entityId() { return entityId; }

    /** True while audio is actually sounding, for the HUD's speaking indicator. */
    boolean isSpeaking() {
        return playing || !jitter.isEmpty();
    }

    float level() { return lastLevel; }

    long lastFrameAt() { return lastFrameAt; }

    // ------------------------------------------------------------------

    /** Takes a decoded frame. Called on the client thread from the tick. */
    void offer(byte[] pcm, double x, double y, double z) {
        srcX = x; srcY = y; srcZ = z;
        lastFrameAt = System.currentTimeMillis();

        jitter.addLast(pcm);
        while (jitter.size() > MAX_BACKLOG) jitter.removeFirst();
    }

    /**
     * Allocates the OpenAL source. Deferred until a voice actually has audio, so
     * players who never speak cost nothing.
     *
     * Returns false if OpenAL refuses, which is not hypothetical: the context has a
     * finite number of sources and Minecraft is already using many of them.
     */
    private boolean allocate() {
        if (allocated) return true;
        AL10.alGetError();

        source = AL10.alGenSources();
        if (AL10.alGetError() != AL10.AL_NO_ERROR) return false;

        AL10.alSourcef(source, AL10.AL_PITCH, 1.0f);
        AL10.alSourcef(source, AL10.AL_GAIN, 0f);
        AL10.alSource3f(source, AL10.AL_VELOCITY, 0f, 0f, 0f);

        // Positions are given already rotated into the listener's frame, so OpenAL
        // must not apply the listener's orientation on top of that.
        AL10.alSourcei(source, AL10.AL_SOURCE_RELATIVE, AL10.AL_TRUE);
        AL10.alSourcei(source, AL10.AL_LOOPING, AL10.AL_FALSE);

        // Attenuation is computed in updateSpatial instead. See the class comment.
        AL10.alSourcef(source, AL10.AL_ROLLOFF_FACTOR, 0f);
        AL10.alSourcef(source, AL10.AL_REFERENCE_DISTANCE, 1f);
        AL10.alSourcef(source, AL10.AL_MAX_DISTANCE, Float.MAX_VALUE);

        bufs = new int[BUFFER_COUNT];
        for (int i = 0; i < BUFFER_COUNT; i++) {
            bufs[i] = AL10.alGenBuffers();
            free.addLast(Integer.valueOf(bufs[i]));
        }
        if (AL10.alGetError() != AL10.AL_NO_ERROR) {
            dispose();
            return false;
        }

        allocated = true;
        return true;
    }

    /** Feeds OpenAL. Must run every client tick or the source underruns. */
    void tick() {
        if (jitter.isEmpty() && !playing) return;
        if (!allocate()) { jitter.clear(); return; }

        try {
            int processed = AL10.alGetSourcei(source, AL10.AL_BUFFERS_PROCESSED);
            while (processed-- > 0) {
                free.addLast(Integer.valueOf(AL10.alSourceUnqueueBuffers(source)));
            }

            // Wait for the bank to fill before the first sound, but once running,
            // play whatever is there -- pausing mid-sentence to re-bank would be far
            // more noticeable than the gap it was avoiding.
            if (!playing && jitter.size() < PREBUFFER) return;

            while (!free.isEmpty() && !jitter.isEmpty()) {
                int buffer = free.removeFirst().intValue();
                byte[] pcm = jitter.removeFirst();

                ByteBuffer bb = BufferUtils.createByteBuffer(pcm.length);
                bb.put(pcm);
                bb.flip();
                AL10.alBufferData(buffer, AL10.AL_FORMAT_MONO16, bb, VoiceFormat.RATE);
                AL10.alSourceQueueBuffers(source, buffer);
            }

            int queued = AL10.alGetSourcei(source, AL10.AL_BUFFERS_QUEUED);
            if (queued > 0) {
                if (AL10.alGetSourcei(source, AL10.AL_SOURCE_STATE) != AL10.AL_PLAYING) {
                    AL10.alSourcePlay(source);
                }
                playing = true;
            } else {
                // Nothing left to play: the speaker stopped. Not an error, and not
                // something to recover from -- the next frame starts a fresh burst.
                playing = false;
            }

            AL10.alGetError();
        } catch (Throwable t) {
            com.questforge.content.QuestForgeContent.log.warn(
                    "[voice] stream for entity " + entityId + " failed", t);
            dispose();
        }
    }

    /**
     * Places and levels the voice for where the listener is standing.
     *
     * Same treatment the jukebox gets, retuned for speech: someone next to you is
     * heard evenly in both ears the way a person in the room is, and direction fades
     * in as they walk away and you would start needing to locate them.
     */
    void updateSpatial(double lx, double ly, double lz, float yawDegrees, float masterVolume) {
        if (!allocated || !playing) return;

        double dx = srcX - lx, dy = srcY - ly, dz = srcZ - lz;
        double distance = Math.sqrt(dx * dx + dy * dy + dz * dz);

        float fall = falloff(distance);
        lastLevel = fall;

        double yaw = Math.toRadians(yawDegrees);
        double fx = -Math.sin(yaw), fz = Math.cos(yaw);        // forward
        double rx = -Math.cos(yaw), rz = -Math.sin(yaw);       // right

        double forward = dx * fx + dz * fz;
        double right = dx * rx + dz * rz;

        double azimuth = Math.atan2(right, forward);
        double width = directionality(distance) * MAX_WIDTH;
        double target = azimuth * width;
        float targetGain = Math.min(1f, masterVolume) * fall;

        if (!spatialPrimed) {
            smoothedAzimuth = target;
            smoothedGain = targetGain;
            spatialPrimed = true;
        } else {
            double delta = target - smoothedAzimuth;
            while (delta > Math.PI) delta -= 2 * Math.PI;
            while (delta < -Math.PI) delta += 2 * Math.PI;

            smoothedAzimuth += delta * PAN_SMOOTHING;
            smoothedGain += (targetGain - smoothedGain) * LEVEL_SMOOTHING;
        }

        AL10.alSourcef(source, AL10.AL_GAIN, smoothedGain);

        double horizontal = Math.sqrt(forward * forward + right * right);
        double elevation = horizontal > 0.0001 ? (dy / horizontal) * width * 0.5 : 0.0;

        AL10.alSource3f(source, AL10.AL_POSITION,
                (float) Math.sin(smoothedAzimuth),
                (float) elevation,
                (float) -Math.cos(smoothedAzimuth));
    }

    private static float falloff(double distance) {
        if (distance <= VoiceFormat.FULL_RANGE) return 1f;
        if (distance >= VoiceFormat.MAX_RANGE) return 0f;
        double t = (distance - VoiceFormat.FULL_RANGE)
                 / (VoiceFormat.MAX_RANGE - VoiceFormat.FULL_RANGE);
        double remaining = 1.0 - t;
        return (float) (remaining * remaining);
    }

    private static float directionality(double distance) {
        if (distance <= VoiceFormat.FULL_RANGE) return 0f;
        double span = (VoiceFormat.MAX_RANGE - VoiceFormat.FULL_RANGE) * SPATIAL_RAMP;
        if (span <= 0) return 1f;
        double t = (distance - VoiceFormat.FULL_RANGE) / span;
        return t >= 1.0 ? 1f : (float) t;
    }

    /** The speaker's live position, so a voice tracks them between frames. */
    void follow(double x, double y, double z) {
        srcX = x; srcY = y; srcZ = z;
    }

    void dispose() {
        jitter.clear();
        free.clear();
        playing = false;
        try {
            if (source != 0) {
                AL10.alSourceStop(source);
                AL10.alSourcei(source, AL10.AL_BUFFER, 0);     // detach before deleting
                if (bufs != null) for (int b : bufs) AL10.alDeleteBuffers(b);
                AL10.alDeleteSources(source);
            }
        } catch (Throwable ignored) {
        } finally {
            source = 0;
            bufs = null;
            allocated = false;
        }
    }
}
