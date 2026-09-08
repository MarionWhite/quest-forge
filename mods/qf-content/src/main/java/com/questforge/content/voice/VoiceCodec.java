package com.questforge.content.voice;

/**
 * IMA ADPCM, 4 bits per sample.
 *
 * Chosen over the obvious alternatives for a specific reason each. Raw 16-bit PCM
 * at {@link VoiceFormat#RATE} is 48 KB/s per speaker, which is a lot to push through
 * the Minecraft connection for no quality the transport can actually deliver. Mu-law
 * is a byte per sample -- half of raw, but audibly telephone-grade. Opus would be
 * better than both and is available as a pure-Java port, but the jukebox's mp3spi and
 * vorbisspi are declared in build.gradle.kts and are *not* in the built jar, so
 * shading is an unsolved problem in this build and adding a dependency would mean
 * solving it first.
 *
 * ADPCM is 12 KB/s, needs no dependency at all, and at 24 kHz sits well above the
 * 16 kHz "HD voice" bar. Its real weakness is that the predictor is stateful, so a
 * lost frame corrupts everything after it -- which is exactly why each frame carries
 * its own predictor seed below, and why voice rides the ordered, reliable Minecraft
 * connection rather than a side UDP socket.
 *
 * Tables are the standard IMA/DVI ones; the step table has 89 entries and the index
 * table 16. Both are transcribed rather than derived -- a single wrong constant here
 * does not fail loudly, it just makes everyone sound slightly broken.
 */
public final class VoiceCodec {

    private static final int[] INDEX_TABLE = {
        -1, -1, -1, -1, 2, 4, 6, 8,
        -1, -1, -1, -1, 2, 4, 6, 8
    };

    private static final int[] STEP_TABLE = {
            7,     8,     9,    10,    11,    12,    13,    14,    16,    17,
           19,    21,    23,    25,    28,    31,    34,    37,    41,    45,
           50,    55,    60,    66,    73,    80,    88,    97,   107,   118,
          130,   143,   157,   173,   190,   209,   230,   253,   279,   307,
          337,   371,   408,   449,   494,   544,   598,   658,   724,   796,
          876,   963,  1060,  1166,  1282,  1411,  1552,  1707,  1878,  2066,
         2272,  2499,  2749,  3024,  3327,  3660,  4026,  4428,  4871,  5358,
         5894,  6484,  7132,  7845,  8630,  9493, 10442, 11487, 12635, 13899,
        15289, 16818, 18500, 20350, 22385, 24623, 27086, 29794, 32767
    };

    /**
     * Bytes of ADPCM for one frame, plus the three-byte seed.
     *
     * The seed is what makes a frame survive the one ahead of it going missing: the
     * encoder writes the predictor state it is *about* to encode from, so a decoder
     * that missed everything before it still starts from the right place. Three bytes
     * per 240 is a rounding error against getting a permanent buzz after one drop.
     */
    public static final int HEADER_BYTES = 3;
    public static final int PACKED_BYTES = VoiceFormat.SAMPLES_PER_FRAME / 2;
    public static final int FRAME_BYTES = HEADER_BYTES + PACKED_BYTES;

    private VoiceCodec() { }

    /** Running predictor state. One per direction, per speaker. */
    public static final class State {
        int predictor;
        int index;

        public void reset() { predictor = 0; index = 0; }
    }

    /**
     * Encodes exactly {@link VoiceFormat#SAMPLES_PER_FRAME} samples into {@code out}.
     * {@code state} is carried across calls, so consecutive frames join seamlessly.
     */
    public static void encode(short[] pcm, int count, State state, byte[] out) {
        // Seed first: this is the state the decoder must start from, not the one we
        // finish with.
        out[0] = (byte) (state.predictor & 0xFF);
        out[1] = (byte) ((state.predictor >> 8) & 0xFF);
        out[2] = (byte) state.index;

        int predictor = state.predictor;
        int index = state.index;
        int w = HEADER_BYTES;
        int pending = 0;          // the low nibble, waiting for its partner
        boolean havePending = false;

        for (int i = 0; i < count; i++) {
            int step = STEP_TABLE[index];
            int diff = pcm[i] - predictor;

            int nibble = 0;
            if (diff < 0) { nibble = 8; diff = -diff; }

            int vpdiff = step >> 3;
            if (diff >= step)        { nibble |= 4; diff -= step;        vpdiff += step; }
            if (diff >= (step >> 1)) { nibble |= 2; diff -= step >> 1;   vpdiff += step >> 1; }
            if (diff >= (step >> 2)) { nibble |= 1;                      vpdiff += step >> 2; }

            predictor += (nibble & 8) != 0 ? -vpdiff : vpdiff;
            if (predictor > 32767) predictor = 32767;
            else if (predictor < -32768) predictor = -32768;

            index += INDEX_TABLE[nibble];
            if (index < 0) index = 0;
            else if (index > 88) index = 88;

            if (havePending) {
                out[w++] = (byte) ((nibble << 4) | pending);
                havePending = false;
            } else {
                pending = nibble;
                havePending = true;
            }
        }
        // An odd sample count would leave half a byte; pad rather than drop it, so
        // the frame length stays predictable.
        if (havePending) out[w++] = (byte) pending;

        state.predictor = predictor;
        state.index = index;
    }

    /**
     * Decodes one frame into 16-bit little-endian PCM.
     *
     * The frame's own seed is used rather than whatever this decoder ended on, so a
     * gap in the stream costs exactly the missing audio and nothing after it.
     * Returns bytes written.
     */
    public static int decode(byte[] in, int length, byte[] outPcm) {
        if (length < HEADER_BYTES) return 0;

        int predictor = (short) ((in[0] & 0xFF) | (in[1] << 8));
        int index = in[2] & 0xFF;
        if (index > 88) index = 88;

        int w = 0;
        for (int r = HEADER_BYTES; r < length; r++) {
            int packed = in[r] & 0xFF;

            for (int half = 0; half < 2; half++) {
                int nibble = half == 0 ? (packed & 0x0F) : (packed >> 4);

                int step = STEP_TABLE[index];
                int vpdiff = step >> 3;
                if ((nibble & 4) != 0) vpdiff += step;
                if ((nibble & 2) != 0) vpdiff += step >> 1;
                if ((nibble & 1) != 0) vpdiff += step >> 2;

                predictor += (nibble & 8) != 0 ? -vpdiff : vpdiff;
                if (predictor > 32767) predictor = 32767;
                else if (predictor < -32768) predictor = -32768;

                index += INDEX_TABLE[nibble];
                if (index < 0) index = 0;
                else if (index > 88) index = 88;

                if (w + 1 < outPcm.length) {
                    outPcm[w++] = (byte) (predictor & 0xFF);
                    outPcm[w++] = (byte) ((predictor >> 8) & 0xFF);
                }
            }
        }
        return w;
    }
}
