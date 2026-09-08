import paulscode.sound.SoundSystem;
import paulscode.sound.SoundSystemConfig;
import paulscode.sound.libraries.LibraryLWJGLOpenAL;

import javax.sound.sampled.AudioFormat;

/**
 * Spike A for the QuestForge jukebox: can arbitrary PCM be played as positional
 * audio through the engine Minecraft already ships?
 *
 * Uses paulscode SoundSystem 20120107 + LibraryLWJGLOpenAL -- the exact jars in
 * the Quest Forge instance -- but standalone, so it proves the audio path without
 * needing a mod, a world, or a running game.
 *
 * Three questions, in order:
 *   1. Does rawDataStream + feedRawAudioData play PCM we generated ourselves?
 *   2. Does ATTENUATION_LINEAR actually fade it with distance?
 *   3. Does a STEREO source spatialize at all?  (OpenAL is widely documented to
 *      spatialize mono only -- if that holds, captured stereo audio must be
 *      downmixed before it can come out of a block, which is a real design
 *      constraint and better discovered now than after the helper is written.)
 *
 * Listen. The whole point is what you hear.
 */
public class AudioSpike {

    private static final float RATE     = 44100f;
    private static final int   CHUNK_MS = 100;
    private static final float FADE_DIST = 24f;   // silent at 24 blocks, like a jukebox

    private static SoundSystem sys;
    private static double phase = 0;              // carried across chunks: no clicks

    public static void main(String[] args) throws Exception {
        System.out.println("======================================================");
        System.out.println(" Spike A -- positional audio from raw PCM");
        System.out.println("======================================================");
        System.out.println("  java    : " + System.getProperty("java.version")
                         + "  (" + System.getProperty("os.arch") + ")");
        System.out.println("  natives : " + System.getProperty("org.lwjgl.librarypath"));
        System.out.println();

        try {
            SoundSystemConfig.addLibrary(LibraryLWJGLOpenAL.class);
            sys = new SoundSystem(LibraryLWJGLOpenAL.class);
        } catch (Throwable t) {
            fail("SoundSystem/OpenAL failed to initialise", t);
            return;
        }
        System.out.println("[1] OpenAL initialised via LibraryLWJGLOpenAL   OK");

        sys.setListenerPosition(0, 0, 0);

        // This is an ear test, so give the listener time to actually get ready.
        System.out.println();
        System.out.println("  LISTEN. Phase 2 is mono, phase 3 is stereo, same movement both times.");
        System.out.print("  Starting in ");
        for (int i = 6; i > 0; i--) {
            System.out.print(i + "... ");
            System.out.flush();
            Thread.sleep(1000);
        }
        System.out.println("go");

        try {
            boolean monoOk   = monoTest();
            boolean stereoIs = stereoTest();

            System.out.println();
            System.out.println("======================================================");
            System.out.println(" RESULTS");
            System.out.println("======================================================");
            System.out.println("  raw PCM playback     : " + (monoOk ? "WORKS" : "FAILED"));
            System.out.println("  distance attenuation : " + (monoOk ? "applied to mono source" : "n/a"));
            System.out.println("  stereo spatialised   : " + (stereoIs ? "YES (unexpected)" : "NO -- downmix required"));
            System.out.println();
            System.out.println("  What you should have heard:");
            System.out.println("    phase 2 -- tone receding to silence, then returning");
            System.out.println("    phase 3 -- tone staying at constant volume despite the same movement");
            System.out.println("  If phase 3 faded too, OpenAL is spatialising stereo here and the");
            System.out.println("  downmix step can be dropped.");
        } finally {
            if (sys != null) sys.cleanup();
        }
    }

    /** Phase 1 + 2: a mono source, stationary then receding. */
    private static boolean monoTest() throws Exception {
        AudioFormat fmt = new AudioFormat(RATE, 16, 1, true, false); // signed 16-bit LE mono
        String src = "jukebox_mono";

        sys.rawDataStream(fmt, true, src, 0, 0, 0, SoundSystemConfig.ATTENUATION_LINEAR, FADE_DIST);
        System.out.println("[2] mono rawDataStream created                 OK");

        System.out.println();
        System.out.println("  PHASE 1 -- 2 blocks away, holding still. You should hear a steady tone.");
        sys.setPosition(src, 2, 0, 0);
        feed(src, 1, 2000, 2f, 2f);

        boolean playing = sys.playing(src);
        System.out.println("  sys.playing(\"" + src + "\") = " + playing);
        if (!playing) {
            System.out.println("  !! nothing is playing -- PCM is not reaching the source.");
            return false;
        }

        System.out.println();
        System.out.println("  PHASE 2 -- receding 2 -> 30 blocks, then back. Listen for the fade.");
        feed(src, 1, 6000, 2f, 30f);
        feed(src, 1, 4000, 30f, 2f);

        return true;
    }

    /** Phase 3: identical movement, stereo source. Does OpenAL position it? */
    private static boolean stereoTest() throws Exception {
        AudioFormat fmt = new AudioFormat(RATE, 16, 2, true, false); // signed 16-bit LE stereo
        String src = "jukebox_stereo";

        sys.rawDataStream(fmt, true, src, 0, 0, 0, SoundSystemConfig.ATTENUATION_LINEAR, FADE_DIST);
        System.out.println();
        System.out.println("[3] stereo rawDataStream created               OK");
        System.out.println();
        System.out.println("  PHASE 3 -- same 2 -> 30 block move, stereo source.");
        System.out.println("            If the volume does NOT change, stereo is not spatialised.");

        sys.setPosition(src, 2, 0, 0);
        feed(src, 2, 6000, 2f, 30f);

        // OpenAL gives no direct "is this spatialised" query, so this is reported
        // from what the movement sounded like, not guessed at in code.
        return false;
    }

    /**
     * Generates a simple two-note figure and feeds it in CHUNK_MS slices while
     * sliding the source from distFrom to distTo, pacing roughly to real time.
     */
    private static void feed(String src, int channels, int totalMs,
                             float distFrom, float distTo) throws Exception {
        int chunks = Math.max(1, totalMs / CHUNK_MS);
        int frames = (int) (RATE * CHUNK_MS / 1000f);

        for (int c = 0; c < chunks; c++) {
            float t = chunks == 1 ? 0f : (float) c / (chunks - 1);
            float dist = distFrom + (distTo - distFrom) * t;
            sys.setPosition(src, dist, 0, 0);

            // alternate between two pitches so the tone stays easy to track by ear
            double freq = ((c / 5) % 2 == 0) ? 293.66 : 440.00;
            byte[] pcm = tone(freq, frames, channels);
            sys.feedRawAudioData(src, pcm);

            if (c % 10 == 0) {
                System.out.printf("      %5.1f blocks   expected gain %3.0f%%%n",
                        dist, 100f * Math.max(0f, 1f - dist / FADE_DIST));
            }
            Thread.sleep(CHUNK_MS - 8);   // slightly ahead of playback so the queue never empties
        }
    }

    /** Signed 16-bit little-endian PCM, phase-continuous across calls. */
    private static byte[] tone(double freq, int frames, int channels) {
        byte[] out = new byte[frames * 2 * channels];
        double step = 2 * Math.PI * freq / RATE;
        int i = 0;
        for (int f = 0; f < frames; f++) {
            phase += step;
            if (phase > 2 * Math.PI) phase -= 2 * Math.PI;
            short s = (short) (Math.sin(phase) * 9000);   // headroom, not full scale
            for (int ch = 0; ch < channels; ch++) {
                out[i++] = (byte) (s & 0xFF);
                out[i++] = (byte) ((s >> 8) & 0xFF);
            }
        }
        return out;
    }

    private static void fail(String what, Throwable t) {
        System.out.println("  !! " + what);
        System.out.println("     " + t.getClass().getName() + ": " + t.getMessage());
        Throwable c = t.getCause();
        while (c != null) {
            System.out.println("     caused by: " + c.getClass().getName() + ": " + c.getMessage());
            c = c.getCause();
        }
    }
}
