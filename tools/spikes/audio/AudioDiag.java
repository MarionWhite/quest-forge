import paulscode.sound.SoundSystem;
import paulscode.sound.SoundSystemConfig;
import paulscode.sound.libraries.LibraryLWJGLOpenAL;

import javax.sound.sampled.AudioFormat;

/**
 * Diagnostic follow-up to AudioSpike, which produced a tone that never changed
 * volume -- meaning distance attenuation was not being applied to a rawDataStream
 * source at all, for mono or stereo.
 *
 * Three checks, each judged by ear and each isolating a different failure:
 *
 *   1. setVolume  -- does the source respond to ANY control? If this fails, the
 *      source name is wrong or commands are not reaching it, and nothing else
 *      about the result means anything.
 *   2. panning    -- hard left vs hard right. Tests whether OpenAL is doing any
 *      spatialisation whatsoever, independent of distance maths.
 *   3. distance   -- retried with setAttenuation() and setDistOrRoll() called
 *      EXPLICITLY after creation, which the first spike never did; it only passed
 *      them as rawDataStream arguments.
 *
 * If 1 passes and 2 fails, the source is non-spatial and the jukebox must compute
 * distance itself and drive setVolume -- workable, but no stereo image.
 * If 1 and 2 pass and 3 fails, the attenuation model is the problem, not the source.
 */
public class AudioDiag {

    private static final float RATE     = 44100f;
    private static final int   CHUNK_MS = 100;
    private static final float FADE_DIST = 24f;

    private static SoundSystem sys;
    private static double phase = 0;

    public static void main(String[] args) throws Exception {
        System.out.println("=========================================================");
        System.out.println(" Audio diagnostic -- why did nothing attenuate?");
        System.out.println("=========================================================");
        System.out.println();

        SoundSystemConfig.addLibrary(LibraryLWJGLOpenAL.class);
        sys = new SoundSystem(LibraryLWJGLOpenAL.class);
        sys.setListenerPosition(0, 0, 0);

        AudioFormat mono = new AudioFormat(RATE, 16, 1, true, false);
        String src = "diag";
        sys.rawDataStream(mono, true, src, 0, 0, 0, SoundSystemConfig.ATTENUATION_LINEAR, FADE_DIST);

        // CONFIRMED BY EAR: the attenuation arguments passed to rawDataStream above
        // are ignored. Without these two explicit calls the source plays at constant
        // volume no matter where it is. This is the whole reason the first spike
        // appeared to show "no attenuation, even for mono".
        sys.setAttenuation(src, SoundSystemConfig.ATTENUATION_LINEAR);
        sys.setDistOrRoll(src, FADE_DIST);

        countdown();

        // ---- TEST A : is OpenAL spatialising at all?  BOTH EARS REQUIRED. ----
        banner("TEST A", "panning: LEFT <-> RIGHT",
                          "Does the tone move between your ears?");
        sys.setVolume(src, 1.0f);
        say("  hard LEFT");   run(src, 2000, t -> pos(src, -6f));
        say("  hard RIGHT");  run(src, 2000, t -> pos(src,  6f));
        say("  hard LEFT");   run(src, 2000, t -> pos(src, -6f));
        say("  hard RIGHT");  run(src, 2000, t -> pos(src,  6f));
        pause();

        // ---- TEST B : confirm the distance fade, now that we know why it works ----
        banner("TEST B", "distance: 1 -> 30 blocks and back",
                          "Does it fade away and return?");
        run(src, 5000, t -> pos(src, 1f + 29f * t));
        run(src, 5000, t -> pos(src, 30f - 29f * t));

        // ---- TEST C : does a circling source track around your head? ----
        banner("TEST C", "orbit: circling you at 5 blocks",
                          "Does it travel around your head?");
        run(src, 8000, t -> {
            double a = 2 * Math.PI * t * 2;   // two full laps
            sys.setPosition(src, (float) (Math.sin(a) * 5), 0, (float) (-Math.cos(a) * 5));
        });

        System.out.println();
        System.out.println("=========================================================");
        System.out.println(" Report which of the three you actually heard change.");
        System.out.println("=========================================================");
        sys.cleanup();
    }

    private static void pos(String src, float x) {
        sys.setPosition(src, x, 0, 0);
    }

    /** Feeds audio for totalMs, calling move(progress 0..1) once per chunk. */
    private static void run(String src, int totalMs, java.util.function.Consumer<Float> move)
            throws Exception {
        int chunks = Math.max(1, totalMs / CHUNK_MS);
        int frames = (int) (RATE * CHUNK_MS / 1000f);
        for (int c = 0; c < chunks; c++) {
            if (move != null) move.accept(chunks == 1 ? 0f : (float) c / (chunks - 1));
            sys.feedRawAudioData(src, tone(330.0, frames));
            Thread.sleep(CHUNK_MS - 8);
        }
    }

    private static byte[] tone(double freq, int frames) {
        byte[] out = new byte[frames * 2];
        double step = 2 * Math.PI * freq / RATE;
        int i = 0;
        for (int f = 0; f < frames; f++) {
            phase += step;
            if (phase > 2 * Math.PI) phase -= 2 * Math.PI;
            short s = (short) (Math.sin(phase) * 9000);
            out[i++] = (byte) (s & 0xFF);
            out[i++] = (byte) ((s >> 8) & 0xFF);
        }
        return out;
    }

    private static void banner(String n, String what, String question) {
        System.out.println();
        System.out.println("---------------------------------------------------------");
        System.out.println(" " + n + " -- " + what);
        System.out.println("          " + question);
        System.out.println("---------------------------------------------------------");
    }

    private static void say(String s) { System.out.println(s); }

    private static void pause() throws Exception {
        System.out.println("  ...");
        Thread.sleep(1200);
    }

    private static void countdown() throws Exception {
        System.out.print("  Listening starts in ");
        for (int i = 5; i > 0; i--) { System.out.print(i + "... "); System.out.flush(); Thread.sleep(1000); }
        System.out.println("go");
    }
}
