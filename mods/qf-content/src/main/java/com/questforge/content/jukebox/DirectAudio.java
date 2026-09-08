package com.questforge.content.jukebox;

import org.lwjgl.BufferUtils;
import org.lwjgl.openal.AL10;

import javax.sound.sampled.AudioFormat;
import javax.sound.sampled.AudioInputStream;
import javax.sound.sampled.AudioSystem;
import java.io.File;
import java.nio.ByteBuffer;
import java.nio.IntBuffer;
import java.util.ArrayList;
import java.util.List;

/**
 * Positional audio driven straight through LWJGL's OpenAL binding.
 *
 * PaulsCode -- Minecraft's own sound library -- cannot play audio this mod creates.
 * Both rawDataStream and newStreamingSource report state=PLAYING with correct gain
 * and queued buffers, yet never advance AL_BUFFERS_PROCESSED, while Minecraft's own
 * sources render normally through the same context. So we own the whole path.
 *
 * Verified in game: buffers recycled 31 -> 71 across four seconds (exactly real
 * time), audible, directional, and fading with distance.
 *
 * Where the audio comes from is deliberately behind {@link PcmSource}. Anything that
 * can produce mono 16-bit PCM -- a decoded file today, captured system audio later --
 * plays out of a block in the world without this class changing.
 *
 * <h3>One track, several places</h3>
 * A track is decoded once and played from any number of {@link Output}s at once: the
 * jukebox or the JBL that owns the queue, plus every paired tower speaker that is
 * switched on. Each output is its own OpenAL source with its own position, range,
 * volume and tone, so a speaker across the field is quiet and directional while the
 * one beside you is not.
 *
 * They are fed in lockstep, and that is not a convenience. Sources drifting even one
 * buffer apart is a tenth of a second of delay between two speakers playing the same
 * music, which is plainly audible as an echo and, worse, combs the sound as the two
 * arrivals cancel. So a chunk is decoded once and handed to every output in the same
 * pass, and no output is fed until all of them have somewhere to put it.
 */
public final class DirectAudio {

    /** OpenAL spatialises MONO sources only. Stereo is downmixed on the way in. */
    public interface PcmSource {
        /** Fills dest with mono 16-bit LE PCM. Returns bytes written, or -1 when done. */
        int read(byte[] dest) throws Exception;
        int sampleRate();
        String describe();
    }

    private static final int BUFFERS = 8;
    private static final int BUFFER_BYTES = 8820;      // 100 ms of 44.1 kHz mono

    /** The key of the output that belongs to whoever owns the queue. */
    public static final String OWNER = "";

    /**
     * How far past an output's full-volume radius it takes to become fully
     * directional, as a fraction of the falloff zone. Reaching it well before the
     * sound gets quiet means direction arrives while there is still plenty to hear.
     */
    private static final float SPATIAL_RAMP = 0.45f;

    /**
     * How far the sound is allowed to swing off centre, as a fraction of the true
     * angle. Below 1 because a mono source placed exactly beside the listener pans
     * fully into one ear, which real rooms never do -- both ears hear a speaker to
     * your left, just unevenly. 0.68 keeps the direction obvious while both ears
     * keep working.
     */
    private static final double MAX_WIDTH = 0.68;

    public static final float MAX_VOLUME = 2.5f;

    /**
     * How much of the way to the target the pan and level move each tick.
     *
     * Spatial updates happen at the 20 Hz client tick, so a turn moves the sound
     * in 50 ms steps -- audible as the image jumping between ears, and harsher the
     * louder it is. Easing toward the target instead turns those steps into a
     * glide. Lower is smoother but lags the player's movement.
     */
    private static final double PAN_SMOOTHING = 0.22;
    private static final float LEVEL_SMOOTHING = 0.30f;

    /** Shelf corners for the tone controls, in Hz. */
    /**
     * Where the tone controls turn over.
     *
     * These were 200 Hz and 4 kHz, which are the textbook corners and which made the
     * sliders very hard to hear. A shelf does not reach its full lift at its corner
     * -- it is only half way there, by definition -- so a 200 Hz low shelf spent most
     * of its twelve decibels below 50 Hz, and a 4 kHz high shelf spent most of its
     * above 8 kHz. Those are the two bands that laptop speakers and ordinary
     * headphones reproduce worst, and 8 kHz is well past where hearing is most
     * sensitive, so almost all of the effect was being applied where it could not be
     * heard.
     *
     * Moved inward, the same twelve decibels land on the fundamentals of bass and
     * kick, and on the presence band around 3 kHz where the ear is sharpest. Measured
     * at full boost, 200 Hz goes from +6.0 to +10.1 dB and 3 kHz from +3.1 to +7.9.
     */
    private static final double BASS_HZ = 320.0, TREBLE_HZ = 2500.0;

    /** How fast a tone slider reaches its new value, per chunk. */
    private static final float TONE_GLIDE = 0.25f;

    // ------------------------------------------------------------------
    // Outputs
    // ------------------------------------------------------------------

    /**
     * One place the music comes out of.
     *
     * Everything that can differ between two speakers playing the same track lives
     * here: where it is, how far it carries, how loud, and how it is voiced.
     */
    public static final class Output {
        /** {@link #OWNER} for the jukebox or JBL, otherwise a paired device's code. */
        public final String key;

        int source;
        int[] bufs;

        /** Where the sound really is -- the block, not the point OpenAL is told. */
        double x, y, z;

        float full = 20f, max = 120f;
        float volume = 0.85f;

        /** Eased pan angle and level, carried between ticks. */
        double smoothedAzimuth;
        float smoothedGain;
        boolean primed;
        float lastFalloff;

        /** Tone targets in dB, and the eased values actually in the filters. */
        float bassDb, trebleDb;
        float bassNow, trebleNow;
        private final Shelf low = new Shelf(), high = new Shelf();

        /** Recent loudness, 0..1, for anything that wants to move to the music. */
        volatile float amplitude;

        Output(String key) { this.key = key; }
    }

    /** The outputs currently sounding. Index 0 is always the owner's. */
    private static final List<Output> outputs = new ArrayList<Output>();

    /** What the owner's output should be, kept even while nothing is playing. */
    private static double srcX, srcY, srcZ;
    private static float fullDistance = 20f;
    private static float maxDistance = 120f;
    private static float volume = 0.85f;
    private static float ownerBass, ownerTreble;

    /**
     * Whether the thing holding the queue is itself sounding.
     *
     * Switched off, the jukebox goes quiet while the speakers paired to it keep
     * playing -- which is the point of being able to put a jukebox in a cupboard and
     * hear it in the hall.
     */
    private static boolean ownerEnabled = true;

    /**
     * The paired devices that should sound alongside the owner.
     *
     * Held here rather than read from the world because a speaker 150 blocks away is
     * outside the client's loaded chunks and has no tile entity to ask. The record
     * that arrived when the device was paired carries everything the audio needs.
     */
    private static Device[] devices = new Device[0];

    /** A paired speaker, as much of one as the audio layer needs to know. */
    public static final class Device {
        public final String code;
        public final double x, y, z;
        public final float full, max, volume, bass, treble;

        public Device(String code, double x, double y, double z,
                      float full, float max, float volume, float bass, float treble) {
            this.code = code;
            this.x = x; this.y = y; this.z = z;
            this.full = full; this.max = max; this.volume = volume;
            this.bass = bass; this.treble = treble;
        }
    }

    private static boolean paused;

    /** Bytes actually played out, for the progress bar. */
    private static long bytesPlayed;

    private static boolean active;
    private static PcmSource pcm;
    private static long recycled;
    private static boolean finished;
    private static String lastError;

    /** The last chunks handed out, so a newly switched-on speaker can join in step. */
    private static final byte[][] history = new byte[BUFFERS][];
    private static final int[] historyLen = new int[BUFFERS];
    private static int historyAt;

    private DirectAudio() { }

    // ------------------------------------------------------------------
    // Starting
    // ------------------------------------------------------------------

    public static String startTone(double x, double y, double z) {
        return start(new ToneSource(330.0), x, y, z);
    }

    /** Plays any format Java can decode natively -- WAV, AIFF, AU -- downmixed to mono. */
    public static String startFile(File f, double x, double y, double z) {
        if (!f.isFile()) return "no such file: " + f.getAbsolutePath();
        try {
            return start(openFile(f), x, y, z);
        } catch (Throwable t) {
            return "could not open " + f.getName() + ": " + t;
        }
    }

    /**
     * Opens a local file as a source without starting it, so callers that decide
     * where and when to play (the block, the browser) can do the slow decode setup
     * off the render thread and start it later.
     */
    public static PcmSource openFile(File f) throws Exception {
        return openFile(f, 0L);
    }

    /**
     * Opens a local file positioned at {@code startMs}.
     *
     * The decoded stream is simply read past rather than seeked: local decoding is
     * far faster than playback, and this works for every format the SPI decoders
     * handle without needing per-format seek support.
     */
    public static PcmSource openFile(File f, long startMs) throws Exception {
        if (!f.isFile()) throw new IllegalArgumentException("no such file: " + f.getAbsolutePath());
        FileSource fs = new FileSource(f);
        if (startMs > 0) {
            long target = startMs * fs.sampleRate() / 1000L * 2L;
            byte[] scratch = new byte[16384];
            long skipped = 0;
            while (skipped < target) {
                int n = fs.read(scratch);
                if (n <= 0) break;
                skipped += n;
            }
        }
        return fs;
    }

    public static String start(PcmSource src, double x, double y, double z) {
        stop();
        AL10.alGetError();                              // clear stale error state

        pcm = src;
        srcX = x; srcY = y; srcZ = z;
        historyAt = 0;
        for (int i = 0; i < BUFFERS; i++) historyLen[i] = 0;

        // Before a single chunk is read, not after. readChunk refuses to read while
        // `finished` is set, so a track that ran to its end would leave the flag on
        // and the next one would prime zero buffers -- and with nothing queued there
        // is nothing to process, so tick can never refill it either. The track sits
        // in the queue looking queued rather than played, and the deadlock is silent.
        finished = false;
        paused = false;
        bytesPlayed = 0L;
        recycled = 0;
        lastError = null;

        String problem = openOutputs();
        if (problem != null) return problem;

        // Prime every output from the same chunks, then start them in one call so
        // they begin on the same sample rather than one frame apart.
        for (int i = 0; i < BUFFERS; i++) {
            byte[] chunk = readChunk();
            if (chunk == null) break;
            int len = lastChunkLen;
            remember(chunk, len);
            for (Output o : outputs) {
                int b = o.bufs[i];
                upload(o, b, chunk, len);
                AL10.alSourceQueueBuffers(o.source, b);
            }
        }
        int e = AL10.alGetError();
        if (e != AL10.AL_NO_ERROR) return "queueing failed: " + err(e);

        // Nothing queued means nothing will ever be processed, and a source with an
        // empty queue never recovers on its own. Say so rather than going quietly
        // silent with a track that claims to be playing.
        if (AL10.alGetSourcei(outputs.get(0).source, AL10.AL_BUFFERS_QUEUED) == 0) {
            String why = lastError == null ? "no audio came out of the decoder" : lastError;
            stop();
            return "could not start: " + why;
        }

        playAll();
        e = AL10.alGetError();
        if (e != AL10.AL_NO_ERROR) return "alSourcePlay failed: " + err(e);

        active = true;
        return "playing " + pcm.describe() + " at " + String.format("%.1f, %.1f, %.1f", x, y, z)
                + (outputs.size() > 1 ? " through " + outputs.size() + " speakers" : "");
    }

    /** Builds one OpenAL source per output. Returns an error string, or null. */
    private static String openOutputs() {
        Output owner = new Output(OWNER);
        owner.x = srcX; owner.y = srcY; owner.z = srcZ;
        owner.full = fullDistance; owner.max = maxDistance;
        owner.volume = ownerEnabled ? volume : 0f;
        owner.bassDb = owner.bassNow = ownerBass;
        owner.trebleDb = owner.trebleNow = ownerTreble;
        outputs.add(owner);

        for (Device d : devices) {
            Output o = new Output(d.code);
            o.x = d.x; o.y = d.y; o.z = d.z;
            o.full = d.full; o.max = d.max;
            o.volume = d.volume;
            o.bassDb = o.bassNow = d.bass;
            o.trebleDb = o.trebleNow = d.treble;
            outputs.add(o);
        }

        for (Output o : outputs) {
            o.source = AL10.alGenSources();
            int e = AL10.alGetError();
            if (e != AL10.AL_NO_ERROR) return "alGenSources failed: " + err(e);
            configure(o);
            o.bufs = new int[BUFFERS];
            for (int i = 0; i < BUFFERS; i++) o.bufs[i] = AL10.alGenBuffers();
        }
        return null;
    }

    private static void configure(Output o) {
        AL10.alSourcef(o.source, AL10.AL_GAIN, Math.min(1f, o.volume));
        AL10.alSourcef(o.source, AL10.AL_PITCH, 1.0f);
        AL10.alSource3f(o.source, AL10.AL_POSITION, (float) o.x, (float) o.y, (float) o.z);
        AL10.alSource3f(o.source, AL10.AL_VELOCITY, 0f, 0f, 0f);
        // Position is given in the listener's own frame, so OpenAL must not rotate
        // it again -- updateSpatial has already done that, and by angle.
        AL10.alSourcei(o.source, AL10.AL_SOURCE_RELATIVE, AL10.AL_TRUE);
        AL10.alSourcei(o.source, AL10.AL_LOOPING, AL10.AL_FALSE);   // never loop a stream

        // Rolloff zero disables OpenAL's own attenuation entirely. Distance volume
        // is applied by hand in updateSpatial, so that the position we hand OpenAL
        // can be used purely to steer direction without also changing loudness.
        AL10.alSourcef(o.source, AL10.AL_ROLLOFF_FACTOR, 0f);
        AL10.alSourcef(o.source, AL10.AL_REFERENCE_DISTANCE, 1f);
        AL10.alSourcef(o.source, AL10.AL_MAX_DISTANCE, Float.MAX_VALUE);
    }

    /** Starts every source in one call, so none of them leads the others. */
    private static void playAll() {
        if (outputs.isEmpty()) return;
        if (outputs.size() == 1) { AL10.alSourcePlay(outputs.get(0).source); return; }
        IntBuffer ids = BufferUtils.createIntBuffer(outputs.size());
        for (Output o : outputs) ids.put(o.source);
        ids.flip();
        AL10.alSourcePlay(ids);
    }

    // ------------------------------------------------------------------
    // Devices
    // ------------------------------------------------------------------

    /**
     * Sets which paired speakers should be sounding.
     *
     * When the line-up itself changes, every output is rebuilt and re-primed from the
     * same chunks and restarted together. Slipping a new source in alongside running
     * ones cannot be done in step -- it would begin up to eight buffers ahead of
     * them, which is most of a second of echo -- and switching a speaker on is a
     * deliberate, occasional act, so paying for it with one re-prime is the honest
     * trade.
     *
     * <h3>Why a settings change must not go down that path</h3>
     * That trade stops being honest the moment the same call is used to carry a
     * volume or tone change, because dragging a slider sends a fresh array every time
     * the mouse moves. Rebuilding every OpenAL source sixty times a second tears the
     * stream down and re-primes it sixty times a second, which is heard as violent
     * stuttering -- the whole track juddering while a slider is held.
     *
     * So the line-up is compared first, and if it is the same the outputs are simply
     * retuned where they stand. Nothing is lost by doing that: gain is eased toward
     * its target every tick in {@link #updateSpatial}, and the shelf coefficients
     * glide in {@link #upload}, so a running output already absorbs a change in
     * volume, position or tone smoothly. There was never anything here worth
     * restarting the audio for.
     */
    public static void setDevices(Device[] next) {
        Device[] wanted = next == null ? new Device[0] : next;

        if (active && sameLineUp(wanted)) {
            devices = wanted;
            retune();
            return;
        }

        devices = wanted;
        if (!active) return;

        boolean wasPaused = paused;
        for (Output o : outputs) closeOutput(o);
        outputs.clear();

        if (openOutputs() != null) { active = false; return; }

        // Re-prime from what the old outputs were playing, so the music carries on
        // from where it was rather than jumping.
        for (int i = 0; i < BUFFERS; i++) {
            int slot = (historyAt + i) % BUFFERS;
            if (historyLen[slot] <= 0) continue;
            for (Output o : outputs) {
                int b = o.bufs[i];
                upload(o, b, history[slot], historyLen[slot]);
                AL10.alSourceQueueBuffers(o.source, b);
            }
        }
        playAll();
        if (wasPaused) { paused = false; pause(); }
    }

    /**
     * Whether the sounding outputs are already exactly these devices, in this order.
     *
     * Identity is the code and nothing else. Two arrays that name the same speakers
     * differ only in settings, and settings are precisely what can be changed without
     * rebuilding anything.
     */
    private static boolean sameLineUp(Device[] wanted) {
        // The owner -- the jukebox or JBL itself -- is always outputs[0].
        if (outputs.size() != wanted.length + 1) return false;
        for (int i = 0; i < wanted.length; i++) {
            if (!outputs.get(i + 1).key.equals(wanted[i].code)) return false;
        }
        return true;
    }

    /** Moves the running outputs to the new settings without disturbing the stream. */
    private static void retune() {
        for (int i = 0; i < devices.length; i++) {
            Output o = outputs.get(i + 1);
            Device d = devices[i];
            o.x = d.x; o.y = d.y; o.z = d.z;
            o.full = d.full; o.max = d.max;
            o.volume = d.volume;
            // Targets only. bassNow and trebleNow are what the filters are actually
            // running on, and upload glides them toward these -- snapping them here
            // would put a step in the shelf response, and a step is a click.
            o.bassDb = d.bass;
            o.trebleDb = d.treble;
        }
    }

    public static Device[] getDevices() { return devices; }

    /**
     * Recent loudness at one output, 0..1 -- what a cone should be moving to.
     *
     * Taken from the audio actually handed to that output, after its own tone and
     * volume, so a speaker turned down or rolled off in the bass moves less than one
     * driven hard, which is what a real cone does.
     */
    public static float amplitude(String key) {
        for (Output o : outputs) if (o.key.equals(key)) return o.amplitude;
        return 0f;
    }

    // ------------------------------------------------------------------
    // Keeping it fed
    // ------------------------------------------------------------------

    /** Must run every client tick; an unfed stream underruns and stops. */
    public static void tick() {
        if (!active) return;
        try {
            // The slowest output sets the pace. Feeding a faster one ahead would put
            // it in front of the others by exactly the amount it got ahead.
            int rounds = Integer.MAX_VALUE;
            for (Output o : outputs) {
                int p = AL10.alGetSourcei(o.source, AL10.AL_BUFFERS_PROCESSED);
                if (p < rounds) rounds = p;
            }
            if (rounds == Integer.MAX_VALUE) rounds = 0;

            while (rounds-- > 0) {
                byte[] chunk = readChunk();
                int len = lastChunkLen;
                // A buffer coming back has been heard, which is what the progress
                // bar should follow -- not what has been read or queued ahead.
                bytesPlayed += BUFFER_BYTES;
                if (chunk != null) remember(chunk, len);

                for (Output o : outputs) {
                    int b = AL10.alSourceUnqueueBuffers(o.source);
                    if (chunk == null) continue;
                    upload(o, b, chunk, len);
                    AL10.alSourceQueueBuffers(o.source, b);
                }
                if (chunk != null) recycled++;
            }

            boolean anyQueued = false;
            for (Output o : outputs) {
                // While paused the source is deliberately not PLAYING, so the
                // underrun recovery below must not drag it back to life.
                if (!finished && !paused
                        && AL10.alGetSourcei(o.source, AL10.AL_SOURCE_STATE) != AL10.AL_PLAYING) {
                    AL10.alSourcePlay(o.source);        // recover from an underrun
                }
                if (AL10.alGetSourcei(o.source, AL10.AL_BUFFERS_QUEUED) > 0) anyQueued = true;
            }
            if (finished && !paused && !anyQueued) {
                stop();                                 // track ended cleanly
            }
            int e = AL10.alGetError();
            if (e != AL10.AL_NO_ERROR) lastError = err(e);
        } catch (Throwable t) {
            lastError = t.toString();
            active = false;
        }
    }

    /**
     * Positions and levels every output for where the listener is standing. Called
     * every client tick, before {@link #tick}.
     *
     * Close to a speaker the music is not placed in the world at all -- it plays
     * evenly in both ears, the way a room you are standing in does not read as
     * having a direction. Direction fades in as you walk away and the sound stops
     * filling the space, which is the point at which a listener starts locating it.
     *
     * The trick is that OpenAL is told a position that is not the speaker's. The
     * source is steered by angle: pointing straight ahead when near, so panning has
     * no direction to express, and reaching the true bearing once fully directional.
     * Loudness cannot come from that moved position, which is why rolloff is zero
     * and gain is set here instead.
     */
    public static void updateSpatial(double lx, double ly, double lz, float yawDegrees) {
        if (!active) return;

        // Into the listener's own frame. Minecraft yaw 0 faces +Z, and rises
        // clockwise, so forward and right come out as below.
        double yaw = Math.toRadians(yawDegrees);
        double fx = -Math.sin(yaw), fz = Math.cos(yaw);      // forward
        double rx = -Math.cos(yaw), rz = -Math.sin(yaw);     // right

        for (Output o : outputs) steer(o, lx, ly, lz, fx, fz, rx, rz);
    }

    private static void steer(Output o, double lx, double ly, double lz,
                              double fx, double fz, double rx, double rz) {
        double dx = o.x - lx, dy = o.y - ly, dz = o.z - lz;
        double distance = Math.sqrt(dx * dx + dy * dy + dz * dz);

        o.lastFalloff = falloff(o, distance);

        double forward = dx * fx + dz * fz;
        double right = dx * rx + dz * rz;

        // Steer by ANGLE, not by sliding the source along the line to the block.
        // Moving a source closer to the listener leaves the direction to it
        // unchanged, so panning would stay hard until the instant it snapped to
        // centre. Narrowing the angle is what actually blends the two behaviours.
        double azimuth = Math.atan2(right, forward);
        double width = directionality(o, distance) * MAX_WIDTH;
        double target = azimuth * width;
        float targetGain = Math.min(1f, o.volume) * o.lastFalloff;

        if (!o.primed) {
            o.smoothedAzimuth = target;
            o.smoothedGain = targetGain;
            o.primed = true;
        } else {
            // Shortest way round, so passing behind the listener eases through the
            // wrap instead of swinging the long way across the front.
            double delta = target - o.smoothedAzimuth;
            while (delta > Math.PI) delta -= 2 * Math.PI;
            while (delta < -Math.PI) delta += 2 * Math.PI;

            o.smoothedAzimuth += delta * PAN_SMOOTHING;
            o.smoothedGain += (targetGain - o.smoothedGain) * LEVEL_SMOOTHING;
        }

        AL10.alSourcef(o.source, AL10.AL_GAIN, o.smoothedGain);

        double horizontal = Math.sqrt(forward * forward + right * right);
        double elevation = horizontal > 0.0001 ? (dy / horizontal) * width * 0.5 : 0.0;

        // A unit vector in listener space: +X right, +Y up, -Z straight ahead.
        // AL_SOURCE_RELATIVE means OpenAL takes this as already-oriented, so the
        // listener's own rotation is not applied again on top.
        AL10.alSource3f(o.source, AL10.AL_POSITION,
                (float) Math.sin(o.smoothedAzimuth),
                (float) elevation,
                (float) -Math.cos(o.smoothedAzimuth));
    }

    /** How loud the music is for the listener, 0..1, from whichever speaker wins. */
    public static float audibleLevel() {
        if (!active) return 0f;
        float loudest = 0f;
        for (Output o : outputs) if (o.lastFalloff > loudest) loudest = o.lastFalloff;
        return loudest;
    }

    /** 1 inside the full-volume radius, easing to 0 at the outer edge. */
    private static float falloff(Output o, double distance) {
        if (distance <= o.full) return 1f;
        if (distance >= o.max) return 0f;
        double t = (distance - o.full) / (o.max - o.full);
        // Squared rather than linear: linear fades feel like they die too early,
        // because loudness is perceived closer to logarithmically than by amplitude.
        double remaining = 1.0 - t;
        return (float) (remaining * remaining);
    }

    /** 0 = centred in both ears, 1 = located at the speaker. */
    private static float directionality(Output o, double distance) {
        if (distance <= o.full) return 0f;
        double span = (o.max - o.full) * SPATIAL_RAMP;
        if (span <= 0) return 1f;
        double t = (distance - o.full) / span;
        return t >= 1.0 ? 1f : (float) t;
    }

    // ------------------------------------------------------------------
    // The owner's settings
    // ------------------------------------------------------------------

    /** Where the sound is anchored, when the block moves the listener does not. */
    public static void setPosition(double x, double y, double z) {
        srcX = x; srcY = y; srcZ = z;
        Output o = owner();
        if (o != null) { o.x = x; o.y = y; o.z = z; }
    }

    /**
     * Player volume, 0..{@link #MAX_VOLUME}.
     *
     * The gain itself is left to the next spatial update rather than written here,
     * so dragging the slider eases in through the same smoothing as everything
     * else instead of stepping.
     */
    public static void setVolume(float v) {
        volume = v < 0f ? 0f : v > MAX_VOLUME ? MAX_VOLUME : v;
        Output o = owner();
        if (o != null) o.volume = ownerEnabled ? volume : 0f;
    }

    public static float getVolume() { return volume; }

    /** Silences or restores the queue's own speaker, leaving paired ones alone. */
    public static void setOwnerEnabled(boolean on) {
        ownerEnabled = on;
        Output o = owner();
        if (o != null) o.volume = on ? volume : 0f;
    }

    public static boolean isOwnerEnabled() { return ownerEnabled; }

    public static void setGain(float g) { setVolume(g); }

    /** Applies immediately to the playing source, so range can be judged by walking. */
    public static String setRange(float full, float max) {
        fullDistance = full;
        maxDistance = Math.max(max, full + 1f);
        Output o = owner();
        if (o != null) { o.full = fullDistance; o.max = maxDistance; }
        return "range: full and non-directional within " + fullDistance
                + " blocks, fading to silence at " + maxDistance;
    }

    /** Tone for the owner's own output, in dB either side of flat. */
    public static void setTone(float bassDb, float trebleDb) {
        ownerBass = clampDb(bassDb);
        ownerTreble = clampDb(trebleDb);
        Output o = owner();
        if (o != null) { o.bassDb = ownerBass; o.trebleDb = ownerTreble; }
    }

    public static float getBass() { return ownerBass; }
    public static float getTreble() { return ownerTreble; }

    public static final float MAX_TONE_DB = 12f;

    private static float clampDb(float db) {
        return db < -MAX_TONE_DB ? -MAX_TONE_DB : db > MAX_TONE_DB ? MAX_TONE_DB : db;
    }

    private static Output owner() {
        return outputs.isEmpty() ? null : outputs.get(0);
    }

    public static float getRefDistance() { return fullDistance; }
    public static float getMaxDistance() { return maxDistance; }

    public static boolean isActive() { return active; }

    public static boolean isPaused() { return active && paused; }

    /** Holds the sources where they are; buffers stay queued so resume is seamless. */
    public static void pause() {
        if (!active || paused) return;
        paused = true;
        for (Output o : outputs) {
            try { AL10.alSourcePause(o.source); } catch (Throwable ignored) { }
        }
    }

    public static void resume() {
        if (!active || !paused) return;
        paused = false;
        playAll();
    }

    /**
     * How far into the track we are, in milliseconds.
     *
     * Counted from buffers that have finished playing, so it lags the true
     * position by at most one buffer -- a tenth of a second, invisible on a
     * progress bar and cheaper than querying OpenAL every frame.
     */
    public static long positionMs() {
        if (!active || pcm == null) return 0L;
        int rate = pcm.sampleRate();
        if (rate <= 0) return 0L;
        return (bytesPlayed / 2L) * 1000L / rate;
    }

    /** Playback position is offset when a track is opened part-way through. */
    public static void setPositionOffsetMs(long ms) {
        if (pcm == null) return;
        int rate = pcm.sampleRate();
        if (rate <= 0) return;
        bytesPlayed = ms * rate / 1000L * 2L;
    }

    public static String nowPlaying() {
        return pcm == null ? "nothing playing" : pcm.describe();
    }

    public static void stop() {
        if (!active) { closeAll(); return; }
        active = false;
        for (Output o : outputs) {
            try { AL10.alSourceStop(o.source); } catch (Throwable ignored) { }
        }
        closeAll();
    }

    private static void closeAll() {
        for (Output o : outputs) closeOutput(o);
        outputs.clear();
        try {
            if (pcm instanceof FileSource) ((FileSource) pcm).close();
            if (pcm instanceof CaptureSource) ((CaptureSource) pcm).close();
            if (pcm instanceof HelperSource) ((HelperSource) pcm).close();
        } catch (Throwable ignored) {
        } finally {
            pcm = null;
        }
    }

    private static void closeOutput(Output o) {
        try {
            if (o.source != 0) {
                AL10.alSourceStop(o.source);
                AL10.alSourcei(o.source, AL10.AL_BUFFER, 0);   // detach before deleting
                if (o.bufs != null) for (int b : o.bufs) AL10.alDeleteBuffers(b);
                AL10.alDeleteSources(o.source);
            }
        } catch (Throwable ignored) {
        } finally {
            o.bufs = null;
            o.source = 0;
        }
    }

    // ------------------------------------------------------------------
    // Moving the samples
    // ------------------------------------------------------------------

    private static byte[] chunkA = new byte[BUFFER_BYTES];
    private static byte[] work = new byte[BUFFER_BYTES];
    private static int lastChunkLen;

    /** Decodes the next chunk once, for every output to share. Null when done. */
    private static byte[] readChunk() {
        if (pcm == null || finished) return null;
        try {
            int n = pcm.read(chunkA);
            if (n <= 0) { finished = true; return null; }
            lastChunkLen = n;
            return chunkA;
        } catch (Throwable t) {
            lastError = t.toString();
            finished = true;
            return null;
        }
    }

    /** Keeps the chunk, so a speaker switched on later can join at the same place. */
    private static void remember(byte[] chunk, int len) {
        int slot = historyAt % BUFFERS;
        if (history[slot] == null || history[slot].length < len) history[slot] = new byte[len];
        System.arraycopy(chunk, 0, history[slot], 0, len);
        historyLen[slot] = len;
        historyAt = (historyAt + 1) % BUFFERS;
    }

    /**
     * Voices one output's copy of a chunk and hands it to OpenAL.
     *
     * The tone controls run here rather than on the shared chunk because each
     * speaker has its own: the same track can be thin on a small box and heavy on a
     * tower, which is the whole point of having the sliders per device. The filters
     * carry their state on the output, so a chunk boundary is not a discontinuity.
     */
    private static void upload(Output o, int buffer, byte[] chunk, int len) {
        if (work.length < len) work = new byte[len];
        System.arraycopy(chunk, 0, work, 0, len);

        // Slide the tone toward its target rather than snapping: recomputing shelf
        // coefficients between one sample and the next is a step in the filter's
        // response, and a step is a click.
        o.bassNow += (o.bassDb - o.bassNow) * TONE_GLIDE;
        o.trebleNow += (o.trebleDb - o.trebleNow) * TONE_GLIDE;

        int rate = pcm == null ? 44100 : pcm.sampleRate();
        if (Math.abs(o.bassNow) > 0.05f) {
            o.low.lowShelf(rate, BASS_HZ, o.bassNow);
            o.low.run(work, len);
        } else {
            o.low.reset();
        }
        if (Math.abs(o.trebleNow) > 0.05f) {
            o.high.highShelf(rate, TREBLE_HZ, o.trebleNow);
            o.high.run(work, len);
        } else {
            o.high.reset();
        }

        if (o.volume > 1f) amplify(work, len, o.volume);
        o.amplitude = loudness(work, len);

        ByteBuffer bb = BufferUtils.createByteBuffer(len);
        bb.put(work, 0, len);
        bb.flip();
        AL10.alBufferData(buffer, AL10.AL_FORMAT_MONO16, bb, rate);
    }

    /**
     * Boosts samples past unity with a soft knee.
     *
     * OpenAL clamps source gain at 1, so the loud half of the slider has to be
     * done here. A plain multiply would square off every peak into harsh digital
     * clipping; the cubic curve below rounds the tops instead, which reads as the
     * track getting louder rather than getting broken.
     */
    private static void amplify(byte[] data, int len, float boost) {
        for (int i = 0; i + 1 < len; i += 2) {
            int sample = (short) ((data[i] & 0xFF) | (data[i + 1] << 8));

            double x = (sample / 32768.0) * boost;
            double y;
            if (x >= 1.0) y = 1.0;
            else if (x <= -1.0) y = -1.0;
            else y = 1.5 * x - 0.5 * x * x * x;      // soft knee, unity slope at 0

            int out = (int) (y * 32767.0);
            data[i]     = (byte) (out & 0xFF);
            data[i + 1] = (byte) ((out >> 8) & 0xFF);
        }
    }

    /**
     * Root mean square of a chunk, 0..1.
     *
     * RMS rather than peak because a cone follows the energy in the music, not the
     * one loudest sample in a tenth of a second -- peak barely moves between a quiet
     * passage and a loud one once anything in the track has a transient in it.
     */
    private static float loudness(byte[] data, int len) {
        long sum = 0;
        int n = 0;
        for (int i = 0; i + 1 < len; i += 2) {
            int s = (short) ((data[i] & 0xFF) | (data[i + 1] << 8));
            sum += (long) s * s;
            n++;
        }
        if (n == 0) return 0f;
        double rms = Math.sqrt((double) sum / n) / 32768.0;
        return (float) Math.min(1.0, rms * 2.4);      // typical music sits near 0.15
    }

    /**
     * One biquad, as a shelving filter.
     *
     * The coefficients are the standard cookbook shelves. Slope is left at 1, which
     * is the gentlest that does not overshoot -- tone controls want to tilt the
     * balance, not carve a corner into it.
     */
    private static final class Shelf {
        private double b0 = 1, b1, b2, a1, a2;
        private double x1, x2, y1, y2;
        private double lastDb = Double.NaN;
        private double lastHz;

        void reset() { x1 = x2 = y1 = y2 = 0; lastDb = Double.NaN; }

        void lowShelf(int rate, double hz, double db) { shelf(rate, hz, db, true); }
        void highShelf(int rate, double hz, double db) { shelf(rate, hz, db, false); }

        private void shelf(int rate, double hz, double db, boolean low) {
            if (db == lastDb && hz == lastHz) return;
            lastDb = db; lastHz = hz;

            double A = Math.pow(10.0, db / 40.0);
            double w0 = 2 * Math.PI * hz / rate;
            double cos = Math.cos(w0);
            double alpha = Math.sin(w0) / 2.0 * Math.sqrt(2.0);
            double sq = 2.0 * Math.sqrt(A) * alpha;

            double a0;
            if (low) {
                b0 =      A * ((A + 1) - (A - 1) * cos + sq);
                b1 =  2 * A * ((A - 1) - (A + 1) * cos);
                b2 =      A * ((A + 1) - (A - 1) * cos - sq);
                a0 =          (A + 1) + (A - 1) * cos + sq;
                a1 =     -2 * ((A - 1) + (A + 1) * cos);
                a2 =          (A + 1) + (A - 1) * cos - sq;
            } else {
                b0 =      A * ((A + 1) + (A - 1) * cos + sq);
                b1 = -2 * A * ((A - 1) + (A + 1) * cos);
                b2 =      A * ((A + 1) + (A - 1) * cos - sq);
                a0 =          (A + 1) - (A - 1) * cos + sq;
                a1 =      2 * ((A - 1) - (A + 1) * cos);
                a2 =          (A + 1) - (A - 1) * cos - sq;
            }
            b0 /= a0; b1 /= a0; b2 /= a0; a1 /= a0; a2 /= a0;
        }

        void run(byte[] data, int len) {
            for (int i = 0; i + 1 < len; i += 2) {
                double x = (short) ((data[i] & 0xFF) | (data[i + 1] << 8));
                double y = b0 * x + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2;
                x2 = x1; x1 = x;
                y2 = y1; y1 = y;

                int out = (int) y;
                if (out > 32767) out = 32767;
                else if (out < -32768) out = -32768;
                data[i]     = (byte) (out & 0xFF);
                data[i + 1] = (byte) ((out >> 8) & 0xFF);
            }
        }
    }

    // ------------------------------------------------------------------
    // Sources
    // ------------------------------------------------------------------

    /** A steady tone. Useful as a known-good reference when something breaks. */
    private static final class ToneSource implements PcmSource {
        private final double freq;
        private double phase;
        ToneSource(double freq) { this.freq = freq; }

        @Override public int read(byte[] dest) {
            double inc = 2 * Math.PI * freq / 44100.0;
            for (int i = 0; i + 1 < dest.length; i += 2) {
                phase += inc;
                if (phase > 2 * Math.PI) phase -= 2 * Math.PI;
                short s = (short) (Math.sin(phase) * 9000);
                dest[i]     = (byte) (s & 0xFF);
                dest[i + 1] = (byte) ((s >> 8) & 0xFF);
            }
            return dest.length;
        }
        @Override public int sampleRate() { return 44100; }
        @Override public String describe() { return "test tone " + (int) freq + "Hz"; }
    }

    /**
     * Decodes an audio file to mono 16-bit PCM.
     *
     * Java's converters handle encoding and bit depth but not channel count, so the
     * stereo-to-mono downmix is done by hand -- and it is not optional: OpenAL will
     * not position a stereo source at all, it just plays flat in both ears.
     */
    private static final class FileSource implements PcmSource {
        private final AudioInputStream in;
        private final int rate;
        private final int channels;
        private final String name;
        private byte[] scratch = new byte[0];

        FileSource(File f) throws Exception {
            // Through AudioServices rather than AudioSystem directly: this runs on a
            // streaming thread, and the bundled mp3 and Ogg decoders are only
            // visible to a loader that can see inside the mod's own jar.
            AudioInputStream raw = AudioServices.read(f);
            AudioFormat src = raw.getFormat();
            AudioFormat want = new AudioFormat(
                    AudioFormat.Encoding.PCM_SIGNED,
                    src.getSampleRate(), 16, src.getChannels(),
                    src.getChannels() * 2, src.getSampleRate(), false);
            this.in = AudioServices.canConvert(want, src)
                    ? AudioServices.convert(want, raw) : raw;
            this.rate = (int) want.getSampleRate();
            this.channels = want.getChannels();
            this.name = f.getName();
        }

        /**
         * Reads until the buffer is full, EOF, or the decoder gives up.
         *
         * A zero-length read is NOT end of stream here. The tritonus converters
         * behind the mp3/ogg service providers return 0 while priming, which a
         * plain `n <= 0` check reads as EOF -- that is why WAV played and ogg
         * queued zero buffers with no error to show for it.
         */
        private int readFully(byte[] buf, int len) throws Exception {
            int total = 0, zeros = 0;
            while (total < len) {
                int n = in.read(buf, total, len - total);
                if (n < 0) break;                      // genuine end of stream
                if (n == 0) {
                    if (total > 0) break;              // partial buffer is fine
                    if (++zeros > 20) break;           // decoder really is done
                    Thread.sleep(2);                   // let it produce something
                    continue;
                }
                zeros = 0;
                total += n;
            }
            return total > 0 ? total : -1;
        }

        @Override public int read(byte[] dest) throws Exception {
            if (channels == 1) {
                return readFully(dest, dest.length);
            }
            // Read `channels` as many frames, then average them down to one.
            int need = dest.length * channels;
            if (scratch.length < need) scratch = new byte[need];
            int n = readFully(scratch, need);
            if (n <= 0) return -1;

            int frames = n / (2 * channels);
            for (int f = 0; f < frames; f++) {
                int sum = 0;
                for (int c = 0; c < channels; c++) {
                    int idx = (f * channels + c) * 2;
                    sum += (short) ((scratch[idx] & 0xFF) | (scratch[idx + 1] << 8));
                }
                short m = (short) (sum / channels);
                dest[f * 2]     = (byte) (m & 0xFF);
                dest[f * 2 + 1] = (byte) ((m >> 8) & 0xFF);
            }
            return frames * 2;
        }

        @Override public int sampleRate() { return rate; }
        @Override public String describe() { return name + " (" + rate + "Hz, " + channels + "ch)"; }
        void close() { try { in.close(); } catch (Throwable ignored) { } }
    }

    // ------------------------------------------------------------------

    public static String[] diag() {
        if (!active) return new String[] { "direct audio: not running"
                + (lastError == null ? "" : "   last error: " + lastError) };
        Output o = owner();
        return new String[] {
            "playing      : " + (pcm == null ? "?" : pcm.describe()),
            "outputs      : " + outputs.size() + "  (owner + " + (outputs.size() - 1) + " paired)",
            "AL id/state  : " + (o == null ? "-" : o.source + "  " + state(
                    AL10.alGetSourcei(o.source, AL10.AL_SOURCE_STATE))),
            "buffers      : " + (o == null ? "-"
                    : "queued=" + AL10.alGetSourcei(o.source, AL10.AL_BUFFERS_QUEUED)
                    + " processed=" + AL10.alGetSourcei(o.source, AL10.AL_BUFFERS_PROCESSED)),
            "RECYCLED     : " + recycled + "   <-- climbing means audio is rendering",
            "last error   : " + (lastError == null ? "none" : lastError)
        };
    }

    private static String state(int s) {
        switch (s) {
            case 4113: return "INITIAL";
            case 4114: return "PLAYING";
            case 4115: return "PAUSED";
            case 4116: return "STOPPED";
            default:   return "unknown(" + s + ")";
        }
    }

    private static String err(int e) {
        switch (e) {
            case 0xA001: return "AL_INVALID_NAME";
            case 0xA002: return "AL_INVALID_ENUM";
            case 0xA003: return "AL_INVALID_VALUE";
            case 0xA004: return "AL_INVALID_OPERATION";
            case 0xA005: return "AL_OUT_OF_MEMORY";
            default:     return "code " + e;
        }
    }
}
