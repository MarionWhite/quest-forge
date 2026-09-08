package com.questforge.content.jukebox;

import java.io.DataInputStream;
import java.io.File;
import java.io.InputStream;
import java.util.ArrayList;
import java.util.List;

/**
 * Audio from a native capture helper, as a {@link DirectAudio.PcmSource}.
 *
 * The helper is a small platform-specific program that captures what the machine is
 * playing and writes mono 16-bit PCM to stdout. This class runs it, reads the
 * stream, and hands it to OpenAL -- so whatever Spotify (or anything else) is
 * playing comes out of a block in the world.
 *
 * Wire format, deliberately trivial so every platform's helper is easy to write:
 *   "QFPCM1", Int32LE sample rate, Int32LE channel count (always 1),
 *   then continuous Int16LE samples until the pipe closes.
 *
 * A subprocess rather than JNI on purpose: a crash in native capture code loaded
 * into the JVM takes Minecraft down with it, whereas a dead subprocess just stops
 * the music and gets reported.
 */
public final class HelperSource implements DirectAudio.PcmSource {

    /** Two seconds of slack, so a scheduling hiccup does not become a dropout. */
    private static final int RING_BYTES = 44100 * 2 * 2;

    private final Process process;
    private final int rate;
    private final String label;

    private final byte[] ring = new byte[RING_BYTES];
    private final Object lock = new Object();
    private int writePos, readPos, available;

    private volatile boolean alive = true;
    private volatile String lastError;
    private volatile long totalRead;
    private volatile long dropped;

    private HelperSource(Process process, int rate, String label) {
        this.process = process;
        this.rate = rate;
        this.label = label;

        Thread reader = new Thread(new Reader(), "qf-helper-reader");
        reader.setDaemon(true);
        reader.start();

        Thread errs = new Thread(new ErrorDrain(), "qf-helper-stderr");
        errs.setDaemon(true);
        errs.start();
    }

    // ------------------------------------------------------------------

    /** Where the helper lives for this platform, or null if none is bundled. */
    public static File helperBinary() {
        String os = System.getProperty("os.name", "").toLowerCase();
        String name = os.contains("win") ? "qfcapture.exe" : "qfcapture";
        String platform = os.contains("win") ? "windows" : os.contains("mac") ? "macos" : "linux";

        // Dev layout first, then next to the game directory for a real install.
        List<File> candidates = new ArrayList<File>();
        candidates.add(new File("tools/capture/" + platform + "/" + name));
        candidates.add(new File(System.getProperty("user.home")
                + "/Desktop/QuestForge-Mods/tools/capture/" + platform + "/" + name));
        candidates.add(new File(net.minecraft.client.Minecraft.getMinecraft().mcDataDir,
                "qfcapture/" + name));

        for (File f : candidates) {
            if (f.isFile()) return f;
        }
        return null;
    }

    /**
     * Launches the helper and reads its header. Blocks briefly -- only until the
     * header arrives -- which is acceptable because it happens on a click, not in
     * the audio path.
     */
    public static HelperSource start(String... extraArgs) throws Exception {
        File bin = helperBinary();
        if (bin == null) throw new IllegalStateException("no capture helper for this platform");
        if (!bin.canExecute() && !bin.setExecutable(true)) {
            throw new IllegalStateException("helper is not executable: " + bin);
        }

        List<String> cmd = new ArrayList<String>();
        cmd.add(bin.getAbsolutePath());
        for (String a : extraArgs) cmd.add(a);

        ProcessBuilder pb = new ProcessBuilder(cmd);
        pb.redirectErrorStream(false);              // stderr is status, not audio
        Process p = pb.start();

        DataInputStream in = new DataInputStream(p.getInputStream());
        byte[] magic = new byte[6];
        in.readFully(magic);
        if (!"QFPCM1".equals(new String(magic, "US-ASCII"))) {
            p.destroy();
            throw new IllegalStateException("helper sent a bad header");
        }
        int rate = Integer.reverseBytes(in.readInt());
        int channels = Integer.reverseBytes(in.readInt());
        if (rate < 8000 || rate > 192000 || channels != 1) {
            p.destroy();
            throw new IllegalStateException("helper sent an unusable format: "
                    + rate + " Hz, " + channels + " ch");
        }

        return new HelperSource(p, rate, bin.getName() + " @ " + rate + " Hz");
    }

    // ------------------------------------------------------------------

    /** Pulls from the pipe continuously so the helper never blocks on a full buffer. */
    private final class Reader implements Runnable {
        @Override public void run() {
            InputStream in = process.getInputStream();
            byte[] buf = new byte[8192];
            try {
                while (alive) {
                    int n = in.read(buf);
                    if (n < 0) break;
                    push(buf, n);
                    totalRead += n;
                }
            } catch (Throwable t) {
                lastError = t.toString();
            } finally {
                alive = false;
            }
        }
    }

    /** The helper's status messages, surfaced instead of silently discarded. */
    private final class ErrorDrain implements Runnable {
        @Override public void run() {
            try {
                java.io.BufferedReader r = new java.io.BufferedReader(
                        new java.io.InputStreamReader(process.getErrorStream(), "UTF-8"));
                String line;
                while ((line = r.readLine()) != null) {
                    com.questforge.content.QuestForgeContent.log.info("[capture] " + line);
                    lastError = line;
                }
            } catch (Throwable ignored) {
            }
        }
    }

    private void push(byte[] data, int len) {
        synchronized (lock) {
            for (int i = 0; i < len; i++) {
                ring[writePos] = data[i];
                writePos = (writePos + 1) % RING_BYTES;
                if (available < RING_BYTES) {
                    available++;
                } else {
                    // Full: overwrite the oldest. Dropping the past keeps latency
                    // bounded, which matters far more than completeness for live audio.
                    readPos = (readPos + 1) % RING_BYTES;
                    dropped++;
                }
            }
        }
    }

    // ------------------------------------------------------------------

    @Override
    public int read(byte[] dest) {
        // Never block the client thread: hand back silence when the helper has not
        // produced enough yet, rather than stalling the whole game.
        synchronized (lock) {
            int n = Math.min(available, dest.length);
            n -= n % 2;                                  // whole samples only
            for (int i = 0; i < n; i++) {
                dest[i] = ring[readPos];
                readPos = (readPos + 1) % RING_BYTES;
            }
            available -= n;
            for (int i = n; i < dest.length; i++) dest[i] = 0;
        }
        return dest.length;
    }

    @Override public int sampleRate() { return rate; }

    @Override public String describe() { return "capture: " + label; }

    public boolean isAlive() { return alive && process.isAlive(); }

    public String[] status() {
        return new String[] {
            "helper       : " + label + (isAlive() ? "  running" : "  STOPPED"),
            "bytes read   : " + totalRead + (dropped > 0 ? "   dropped=" + dropped : ""),
            "buffered     : " + available + " / " + RING_BYTES,
            "last message : " + (lastError == null ? "none" : lastError)
        };
    }

    public void close() {
        alive = false;
        try { process.destroy(); } catch (Throwable ignored) { }
    }
}
