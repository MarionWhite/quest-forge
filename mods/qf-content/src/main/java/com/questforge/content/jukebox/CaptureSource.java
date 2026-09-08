package com.questforge.content.jukebox;

import javax.sound.sampled.AudioFormat;
import javax.sound.sampled.AudioSystem;
import javax.sound.sampled.DataLine;
import javax.sound.sampled.Mixer;
import javax.sound.sampled.TargetDataLine;

import java.util.ArrayList;
import java.util.List;

/**
 * Live audio capture as a {@link DirectAudio.PcmSource}, so whatever the machine is
 * capturing comes out of a block in the world.
 *
 * This is the architecture for "play anything", proven without native code. The whole
 * capture-to-positional-audio path -- device open, PCM read, stereo downmix, buffer
 * feed, 3D placement -- is identical whether the bytes come from a microphone, a
 * loopback device, or a native helper piping system audio in later. Only the source
 * of the bytes changes.
 *
 * On machines that expose a loopback input (Windows "Stereo Mix", or a virtual audio
 * device), this already captures system audio with nothing installed and no native
 * code. Where no such device exists -- most modern Windows machines, and macOS -- the
 * native helper replaces just this class's byte source, against a contract that is
 * proven working first.
 */
public final class CaptureSource implements DirectAudio.PcmSource {

    private static final int RATE = 44100;

    private final TargetDataLine line;
    private final int channels;
    private final String name;
    private byte[] scratch = new byte[0];

    private CaptureSource(TargetDataLine line, int channels, String name) {
        this.line = line;
        this.channels = channels;
        this.name = name;
    }

    /** Every mixer on this machine that can actually capture audio. */
    public static List<String> devices() {
        List<String> out = new ArrayList<String>();
        AudioFormat fmt = new AudioFormat(RATE, 16, 2, true, false);
        DataLine.Info info = new DataLine.Info(TargetDataLine.class, fmt);
        int i = 0;
        for (Mixer.Info mi : AudioSystem.getMixerInfo()) {
            try {
                Mixer m = AudioSystem.getMixer(mi);
                if (!m.isLineSupported(info)) continue;
                String tag = looksLikeLoopback(mi) ? "  << LOOPBACK?" : "";
                out.add("[" + i + "] " + mi.getName() + tag);
            } catch (Throwable ignored) {
                // a mixer that refuses to be queried is simply not a candidate
            }
            i++;
        }
        if (out.isEmpty()) out.add("no capture devices visible to Java");
        return out;
    }

    /**
     * Names that usually indicate the device carries system output rather than a mic.
     * A hint for the operator, not something the code relies on.
     */
    private static boolean looksLikeLoopback(Mixer.Info mi) {
        String n = (mi.getName() + " " + mi.getDescription()).toLowerCase();
        return n.contains("stereo mix") || n.contains("loopback") || n.contains("what u hear")
            || n.contains("blackhole") || n.contains("soundflower") || n.contains("monitor");
    }

    /** Opens capture device by the index shown in {@link #devices()}. */
    public static CaptureSource open(int index) throws Exception {
        AudioFormat fmt = new AudioFormat(RATE, 16, 2, true, false);
        DataLine.Info info = new DataLine.Info(TargetDataLine.class, fmt);

        Mixer.Info[] all = AudioSystem.getMixerInfo();
        List<Mixer.Info> usable = new ArrayList<Mixer.Info>();
        for (Mixer.Info mi : all) {
            try {
                if (AudioSystem.getMixer(mi).isLineSupported(info)) usable.add(mi);
            } catch (Throwable ignored) { }
        }
        if (usable.isEmpty()) throw new IllegalStateException("no capture devices available");
        if (index < 0 || index >= usable.size()) {
            throw new IllegalArgumentException("device index out of range (0-" + (usable.size() - 1) + ")");
        }

        Mixer.Info chosen = usable.get(index);
        TargetDataLine line = (TargetDataLine) AudioSystem.getMixer(chosen).getLine(info);
        // A small buffer keeps latency down; the game feeds OpenAL every tick anyway.
        line.open(fmt, RATE / 5 * 4);
        line.start();
        return new CaptureSource(line, 2, chosen.getName());
    }

    @Override
    public int read(byte[] dest) {
        // Never block the game: read only what is already captured, and emit silence
        // when the device has not produced enough yet. A stalled read here would
        // freeze the client thread that drives the whole stream.
        int need = dest.length * channels;
        if (scratch.length < need) scratch = new byte[need];

        int avail = Math.min(line.available(), need);
        avail -= avail % (2 * channels);                 // whole frames only
        if (avail <= 0) {
            java.util.Arrays.fill(dest, (byte) 0);       // silence, not underrun
            return dest.length;
        }

        int n = line.read(scratch, 0, avail);
        int frames = n / (2 * channels);

        for (int f = 0; f < frames; f++) {
            int sum = 0;
            for (int c = 0; c < channels; c++) {
                int idx = (f * channels + c) * 2;
                sum += (short) ((scratch[idx] & 0xFF) | (scratch[idx + 1] << 8));
            }
            short m = (short) (sum / channels);          // OpenAL positions mono only
            dest[f * 2]     = (byte) (m & 0xFF);
            dest[f * 2 + 1] = (byte) ((m >> 8) & 0xFF);
        }
        // Pad the rest of the buffer so we always hand OpenAL a full slice.
        for (int i = frames * 2; i < dest.length; i++) dest[i] = 0;
        return dest.length;
    }

    @Override public int sampleRate() { return RATE; }

    @Override public String describe() { return "live capture: " + name; }

    public void close() {
        try { line.stop(); line.close(); } catch (Throwable ignored) { }
    }
}
