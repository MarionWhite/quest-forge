import com.questforge.content.voice.VoiceCodec;
import com.questforge.content.voice.VoiceFormat;

/**
 * Proves the ADPCM tables and the frame seeding actually work, offline.
 *
 * This exists because a wrong constant in either table does not fail loudly. The
 * codec still encodes, still decodes, still produces sound -- it just makes everyone
 * sound slightly broken, and the only way to notice is to have two people on a server
 * and a suspicion. Measuring the round trip here turns that into a number.
 *
 * Three things are checked, and the third is the one worth having:
 *
 *   1. a decoded signal tracks the original -- catches a wrong step table
 *   2. quiet audio survives -- catches a step index that runs away, which sounds fine
 *      on loud speech and turns whispers into noise
 *   3. dropping a frame costs exactly that frame. This is the property the header
 *      seed exists for, and the one that silently disappears if someone later
 *      "optimises" the seed away because the stream sounds fine without it.
 */
public class VoiceCodecCheck {

    private static int failures;

    public static void main(String[] args) {
        System.out.println("Voice codec: " + VoiceFormat.RATE + " Hz, "
                + VoiceCodec.FRAME_BYTES + " bytes per " + VoiceFormat.FRAME_MS + " ms frame ("
                + (VoiceCodec.FRAME_BYTES * 1000 / VoiceFormat.FRAME_MS) + " B/s per speaker)");
        System.out.println();

        checkRoundTrip("speech-like (300-3400 Hz)", speechLike(1.0f), 18.0);
        checkRoundTrip("loud speech", speechLike(0.8f), 18.0);
        checkRoundTrip("quiet speech", speechLike(0.05f), 12.0);
        checkRoundTrip("silence", new short[VoiceFormat.SAMPLES_PER_FRAME * 20], 0.0);
        checkFrameLoss();

        System.out.println();
        if (failures > 0) {
            System.out.println(failures + " CHECK(S) FAILED");
            System.exit(1);
        }
        System.out.println("all voice codec checks passed");
    }

    /**
     * A stand-in for a voice: several harmonics inside the telephone band, with an
     * envelope so the codec has to track something that starts and stops rather than
     * a steady tone it can settle on.
     */
    private static short[] speechLike(float amplitude) {
        int n = VoiceFormat.SAMPLES_PER_FRAME * 20;
        short[] out = new short[n];
        for (int i = 0; i < n; i++) {
            double t = (double) i / VoiceFormat.RATE;
            double v = 0.60 * Math.sin(2 * Math.PI * 220 * t)
                     + 0.25 * Math.sin(2 * Math.PI * 880 * t)
                     + 0.10 * Math.sin(2 * Math.PI * 2400 * t)
                     + 0.05 * Math.sin(2 * Math.PI * 3300 * t);
            double envelope = 0.5 * (1 - Math.cos(2 * Math.PI * t * 3));
            out[i] = (short) (v * envelope * amplitude * 30000);
        }
        return out;
    }

    private static void checkRoundTrip(String label, short[] original, double minSnrDb) {
        short[] decoded = roundTrip(original, -1);

        double signal = 0, noise = 0;
        for (int i = 0; i < original.length; i++) {
            double s = original[i];
            double e = s - decoded[i];
            signal += s * s;
            noise += e * e;
        }

        if (signal == 0) {
            // Silence in must be silence out. A codec that idles into a DC offset or
            // a faint whine passes every SNR test and is unusable on an open mic.
            int worst = 0;
            for (short s : decoded) worst = Math.max(worst, Math.abs(s));
            report(label, worst <= 4, "peak output " + worst + " (want <= 4)");
            return;
        }

        double snr = 10 * Math.log10(signal / Math.max(noise, 1e-9));
        report(label, snr >= minSnrDb,
                String.format("SNR %.1f dB (want >= %.1f)", Double.valueOf(snr),
                        Double.valueOf(minSnrDb)));
    }

    /**
     * Encodes, throws one frame away, and confirms the damage stops there.
     *
     * The frames after the gap are compared against a clean run of the same input.
     * They must match exactly: each frame reseeds the decoder from its own header, so
     * a lost frame cannot leave the predictor somewhere wrong.
     */
    private static void checkFrameLoss() {
        short[] original = speechLike(0.8f);
        short[] clean = roundTrip(original, -1);
        short[] lossy = roundTrip(original, 5);

        int perFrame = VoiceFormat.SAMPLES_PER_FRAME;
        int resumeAt = 6 * perFrame;

        int mismatches = 0;
        for (int i = resumeAt; i < clean.length; i++) {
            if (clean[i] != lossy[i]) mismatches++;
        }
        report("frame loss recovery", mismatches == 0,
                mismatches == 0
                    ? "frames after a drop are bit-identical to a clean stream"
                    : mismatches + " samples differ after the dropped frame -- the "
                      + "decoder is carrying state across frames");
    }

    /** {@code dropFrame} below zero drops nothing. */
    private static short[] roundTrip(short[] input, int dropFrame) {
        VoiceCodec.State encoder = new VoiceCodec.State();
        int perFrame = VoiceFormat.SAMPLES_PER_FRAME;

        short[] out = new short[input.length];
        short[] frame = new short[perFrame];
        byte[] encoded = new byte[VoiceCodec.FRAME_BYTES];
        byte[] pcm = new byte[VoiceFormat.PCM_BYTES_PER_FRAME];

        int frameIndex = 0;
        for (int offset = 0; offset + perFrame <= input.length; offset += perFrame, frameIndex++) {
            System.arraycopy(input, offset, frame, 0, perFrame);
            VoiceCodec.encode(frame, perFrame, encoder, encoded);

            if (frameIndex == dropFrame) continue;      // never reaches the decoder

            int n = VoiceCodec.decode(encoded, encoded.length, pcm);
            for (int i = 0; i * 2 + 1 < n && offset + i < out.length; i++) {
                out[offset + i] = (short) ((pcm[i * 2] & 0xFF) | (pcm[i * 2 + 1] << 8));
            }
        }
        return out;
    }

    private static void report(String label, boolean ok, String detail) {
        System.out.println((ok ? "  PASS  " : "  FAIL  ") + pad(label) + detail);
        if (!ok) failures++;
    }

    private static String pad(String s) {
        StringBuilder sb = new StringBuilder(s);
        while (sb.length() < 28) sb.append(' ');
        return sb.toString();
    }
}
