package com.questforge.content.voice;

import javax.sound.sampled.AudioFormat;
import javax.sound.sampled.AudioSystem;
import javax.sound.sampled.DataLine;
import javax.sound.sampled.Mixer;
import javax.sound.sampled.TargetDataLine;

import java.util.ArrayList;
import java.util.List;

/**
 * The microphone, as a stream of fixed-size 24 kHz mono frames.
 *
 * Distinct from the jukebox's {@link com.questforge.content.jukebox.CaptureSource},
 * which reads whatever the game asks for whenever it asks and pads with silence.
 * Voice needs the opposite discipline: exact frames at an exact cadence, delivered
 * by blocking until they are ready, because 20 ms of real audio must leave the
 * machine every 20 ms or the far end hears gaps.
 *
 * Few capture devices offer 24 kHz directly, so the device is opened at whichever
 * candidate rate it does support and resampled here. Doing it this way rather than
 * demanding one rate is what keeps this working across the range of hardware people
 * actually have -- the probe on this Mac offered 16 kHz and 44.1 kHz but not 24.
 */
public final class VoiceCapture {

    /**
     * Tried in order. The native rate first so most machines skip resampling
     * entirely; then the two rates that are integer multiples or near enough that
     * the resampler has an easy job.
     */
    private static final float[] CANDIDATE_RATES = { 24000f, 48000f, 44100f, 16000f };

    private final TargetDataLine line;
    private final float deviceRate;
    private final String deviceName;

    /** Raw bytes as the device produced them, before rate conversion. */
    private byte[] raw = new byte[0];

    /** Fractional read position into the device stream, carried across frames. */
    private double resamplePos;

    /** The last sample of the previous frame, so interpolation spans the seam. */
    private short carry;
    private boolean haveCarry;

    private VoiceCapture(TargetDataLine line, float deviceRate, String deviceName) {
        this.line = line;
        this.deviceRate = deviceRate;
        this.deviceName = deviceName;
    }

    // ------------------------------------------------------------------
    // Devices
    // ------------------------------------------------------------------

    /** Every mixer that can capture at one of the candidate rates. */
    public static List<String> devices() {
        List<String> out = new ArrayList<String>();
        List<Mixer.Info> usable = usableMixers();
        for (int i = 0; i < usable.size(); i++) {
            out.add("[" + i + "] " + usable.get(i).getName());
        }
        if (out.isEmpty()) out.add("no capture devices visible to Java");
        return out;
    }

    private static List<Mixer.Info> usableMixers() {
        List<Mixer.Info> usable = new ArrayList<Mixer.Info>();
        for (Mixer.Info mi : AudioSystem.getMixerInfo()) {
            try {
                Mixer m = AudioSystem.getMixer(mi);
                for (float rate : CANDIDATE_RATES) {
                    if (m.isLineSupported(new DataLine.Info(TargetDataLine.class, format(rate)))) {
                        usable.add(mi);
                        break;
                    }
                }
            } catch (Throwable ignored) {
                // A mixer that will not answer questions is not a candidate.
            }
        }
        return usable;
    }

    private static AudioFormat format(float rate) {
        return new AudioFormat(rate, 16, 1, true, false);
    }

    /**
     * Opens a capture device.
     *
     * {@code index} below zero means "whatever the system default is", which is the
     * right behaviour for a setting nobody has touched: it follows the machine's own
     * input choice instead of pinning to a device that may not be plugged in today.
     */
    public static VoiceCapture open(int index) throws Exception {
        List<Mixer.Info> usable = usableMixers();
        if (usable.isEmpty()) throw new IllegalStateException("no capture device available");

        // An explicit choice is honoured and nothing else is tried -- silently
        // recording from a different microphone than the one that was picked would
        // be worse than failing. With no choice made, every device is fair game.
        List<Mixer.Info> attempts = new ArrayList<Mixer.Info>();
        if (index >= 0 && index < usable.size()) {
            attempts.add(usable.get(index));
        } else {
            attempts.addAll(usable);
        }

        StringBuilder failures = new StringBuilder();

        for (Mixer.Info mi : attempts) {
            for (float rate : CANDIDATE_RATES) {
                AudioFormat fmt = format(rate);
                DataLine.Info info = new DataLine.Info(TargetDataLine.class, fmt);

                try {
                    Mixer mixer = AudioSystem.getMixer(mi);
                    if (!mixer.isLineSupported(info)) continue;

                    TargetDataLine line = (TargetDataLine) mixer.getLine(info);
                    // A quarter second of slack. Enough that a scheduling hiccup on
                    // the capture thread does not overflow the device and lose
                    // audio, small enough that recovering from one does not leave a
                    // lasting delay.
                    line.open(fmt, (int) (rate * 2 / 4));
                    line.start();
                    return new VoiceCapture(line, rate, mi.getName());

                } catch (Throwable t) {
                    // isLineSupported is a promise the driver does not always keep.
                    // Windows DirectSound in particular reports formats it then
                    // refuses to open -- another application holding the device
                    // exclusively is enough to do it -- so a rate that fails here
                    // means try the next one, not give up on the device.
                    if (failures.length() > 0) failures.append("; ");
                    failures.append(mi.getName()).append('@').append((int) rate)
                            .append(": ").append(t.getClass().getSimpleName());
                }
            }
        }
        throw new IllegalStateException("no usable capture device"
                + (failures.length() > 0 ? " (" + failures + ")" : ""));
    }

    // ------------------------------------------------------------------
    // Reading
    // ------------------------------------------------------------------

    /**
     * Fills {@code frame} with exactly {@link VoiceFormat#SAMPLES_PER_FRAME} samples
     * at {@link VoiceFormat#RATE}, blocking until the microphone has produced them.
     *
     * Blocking is deliberate and is why capture runs on its own thread: it paces the
     * whole send path off the sound card's clock rather than off the game's tick,
     * so frames leave at a steady 20 ms whatever the frame rate is doing.
     */
    public boolean readFrame(short[] frame) {
        int needed = neededDeviceSamples();
        int bytes = needed * 2;
        if (raw.length < bytes) raw = new byte[bytes];

        int got = 0;
        while (got < bytes) {
            int n = line.read(raw, got, bytes - got);
            if (n <= 0) return false;              // line closed under us
            got += n;
        }
        resample(needed, frame);
        return true;
    }

    /**
     * How many device samples this frame needs.
     *
     * Rounded up against the running fractional position rather than computed fresh
     * each time, because at 44.1 kHz the true figure is 882.35 samples per frame --
     * always taking 883 would run a little fast and always 882 a little slow, and
     * either way the drift eventually becomes an audible skip.
     */
    private int neededDeviceSamples() {
        if (deviceRate == VoiceFormat.RATE) return VoiceFormat.SAMPLES_PER_FRAME;
        double ratio = deviceRate / VoiceFormat.RATE;
        double span = resamplePos + ratio * VoiceFormat.SAMPLES_PER_FRAME;
        return (int) Math.ceil(span);
    }

    /** Linear interpolation down to the wire rate. */
    private void resample(int available, short[] frame) {
        if (deviceRate == VoiceFormat.RATE) {
            for (int i = 0; i < VoiceFormat.SAMPLES_PER_FRAME; i++) {
                frame[i] = (short) ((raw[i * 2] & 0xFF) | (raw[i * 2 + 1] << 8));
            }
            if (VoiceFormat.SAMPLES_PER_FRAME > 0) {
                carry = frame[VoiceFormat.SAMPLES_PER_FRAME - 1];
                haveCarry = true;
            }
            return;
        }

        double ratio = deviceRate / VoiceFormat.RATE;
        double pos = resamplePos;

        for (int i = 0; i < VoiceFormat.SAMPLES_PER_FRAME; i++) {
            int base = (int) Math.floor(pos);
            double frac = pos - base;

            short a = sampleAt(base, available);
            short b = sampleAt(base + 1, available);
            frame[i] = (short) (a + (b - a) * frac);

            pos += ratio;
        }

        // Whatever fraction of a sample is left over starts the next frame, so the
        // two frames meet without a discontinuity.
        resamplePos = pos - available;
        if (resamplePos < 0) resamplePos = 0;
        if (available > 0) {
            carry = sampleAt(available - 1, available);
            haveCarry = true;
        }
    }

    /** Index -1 reaches back into the previous frame; past the end clamps. */
    private short sampleAt(int index, int available) {
        if (index < 0) return haveCarry ? carry : (short) 0;
        if (index >= available) index = available - 1;
        if (index < 0) return 0;
        return (short) ((raw[index * 2] & 0xFF) | (raw[index * 2 + 1] << 8));
    }

    // ------------------------------------------------------------------

    /** Loudness of a frame, 0..1, for the noise gate and the level meter. */
    public static float rms(short[] frame, int count) {
        if (count <= 0) return 0f;
        double sum = 0;
        for (int i = 0; i < count; i++) {
            double s = frame[i] / 32768.0;
            sum += s * s;
        }
        return (float) Math.sqrt(sum / count);
    }

    public String describe() {
        return deviceName + " (" + (int) deviceRate + " Hz"
                + (deviceRate == VoiceFormat.RATE ? "" : " -> " + VoiceFormat.RATE) + ")";
    }

    public void close() {
        try { line.stop(); line.close(); } catch (Throwable ignored) { }
    }
}
