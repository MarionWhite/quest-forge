package com.questforge.content.jukebox;

import javax.sound.sampled.AudioFormat;
import javax.sound.sampled.AudioInputStream;
import javax.sound.sampled.AudioSystem;
import java.io.BufferedInputStream;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;

/**
 * Audio streamed over HTTP, as a {@link DirectAudio.PcmSource}.
 *
 * This is what makes the jukebox an on-demand player rather than a folder browser:
 * give it the URL of a track in a catalog and it plays, without downloading first.
 *
 * The network is the reason this looks different from {@link DirectAudio}'s file
 * source. A stalled socket read must never reach the game thread, so decoding runs
 * on a worker that fills a ring buffer, and {@code read} only ever drains what has
 * already arrived. When the buffer runs dry the jukebox gets silence for a moment
 * instead of the client freezing.
 *
 * Decoding is the same machinery local files use -- the mp3 and ogg service
 * providers register with AudioSystem, so a remote mp3 needs no special handling.
 */
public final class StreamSource implements DirectAudio.PcmSource {

    /** Four seconds of slack. Network jitter is far lumpier than a local disk. */
    private static final int RING_BYTES = 44100 * 2 * 4;

    /** Do not start playing until this much has arrived, or it stutters immediately. */
    private static final int PREBUFFER_BYTES = 44100 * 2 / 2;   // ~0.5 s

    private final String label;
    private final int rate;
    private final AudioInputStream in;
    private final HttpURLConnection connection;
    private final int channels;

    /** Where playback really began, which is 0 when a seek could not be honoured. */
    private final long startedAtMs;

    private final byte[] ring = new byte[RING_BYTES];
    private final Object lock = new Object();
    private int writePos, readPos, available;

    private volatile boolean alive = true;
    private volatile boolean ended;
    private volatile String lastError;
    private volatile long totalDecoded;
    private volatile long starved;

    private StreamSource(HttpURLConnection connection, AudioInputStream in,
                         int rate, int channels, String label, long startedAtMs) {
        this.connection = connection;
        this.in = in;
        this.rate = rate;
        this.channels = channels;
        this.label = label;
        this.startedAtMs = startedAtMs;

        Thread pump = new Thread(new Pump(), "qf-stream-decode");
        pump.setDaemon(true);
        pump.start();
    }

    /**
     * Opens a URL and prepares it for playback. Blocks until enough audio has
     * buffered to start cleanly -- this runs on a click, never in the audio path.
     */
    public static StreamSource open(String url, String label) throws Exception {
        return open(url, label, 0L, 0L);
    }

    /**
     * Opens a stream, optionally part-way through.
     *
     * Seeking is done by byte offset, because these are plain HTTP files with no
     * seek protocol of their own: the position is converted to a byte range using
     * the track's overall length. That is exact for constant-bitrate audio and
     * approximate for variable-bitrate, so a seek can land slightly off where the
     * bar was dragged. Landing mid-frame is fine -- the mp3 decoder resynchronises
     * on the next frame header.
     */
    public static StreamSource open(String url, String label,
                                    long startMs, long durationMs) throws Exception {
        long offset = 0L;
        if (startMs > 0 && durationMs > 0) {
            long total = totalLength(url);
            if (total > 0) {
                offset = (long) (total * (startMs / (double) durationMs));
                if (offset >= total) offset = Math.max(0, total - 1);
            }
        }

        HttpURLConnection c = (HttpURLConnection) new URL(url).openConnection();
        c.setConnectTimeout(10000);
        c.setReadTimeout(20000);
        c.setInstanceFollowRedirects(true);
        c.setRequestProperty("User-Agent", "QuestForgeJukebox/1.0");
        c.setRequestProperty("Accept", "*/*");
        if (offset > 0) c.setRequestProperty("Range", "bytes=" + offset + "-");

        int status = c.getResponseCode();
        if (status / 100 != 2) {
            c.disconnect();
            throw new IllegalStateException("HTTP " + status + " from " + url);
        }

        // 206 means the seek took. A 200 to a range request means the server
        // ignored it and is sending the file from the top -- so playback really
        // is starting at zero, and saying otherwise is what put the progress bar
        // out of step with the audio.
        long actualStart = (offset > 0 && status == 206) ? startMs : 0L;

        // AudioSystem sniffs the format by reading and rewinding, so the stream has
        // to support mark/reset; a raw socket stream does not.
        InputStream raw = new BufferedInputStream(c.getInputStream(), 1 << 16);
        AudioInputStream decoded;
        try {
            decoded = AudioServices.read(raw);
        } catch (Exception e) {
            c.disconnect();
            throw new IllegalStateException("unsupported audio format: " + e.getMessage());
        }

        AudioFormat src = decoded.getFormat();
        AudioFormat want = new AudioFormat(
                AudioFormat.Encoding.PCM_SIGNED,
                src.getSampleRate() > 0 ? src.getSampleRate() : 44100f,
                16, src.getChannels(), src.getChannels() * 2,
                src.getSampleRate() > 0 ? src.getSampleRate() : 44100f, false);

        // Without a conversion the stream is still MPEG frames. Handing those to
        // OpenAL as if they were samples produces loud noise, not a quiet failure,
        // so refuse rather than fall through to "play it anyway".
        AudioInputStream pcm;
        if (AudioServices.canConvert(want, src)) {
            pcm = AudioServices.convert(want, decoded);
        } else if (isPcm(src)) {
            pcm = decoded;
        } else {
            c.disconnect();
            throw new IllegalStateException("no decoder for " + src.getEncoding()
                    + " (is the mp3/ogg support jar missing?)");
        }

        StreamSource s = new StreamSource(c, pcm, (int) want.getSampleRate(),
                want.getChannels(), label, actualStart);

        // Wait briefly for the pre-buffer so playback does not start on empty.
        long deadline = System.currentTimeMillis() + 8000;
        while (System.currentTimeMillis() < deadline) {
            synchronized (s.lock) {
                if (s.available >= PREBUFFER_BYTES || s.ended || !s.alive) break;
            }
            Thread.sleep(25);
        }
        if (s.lastError != null && s.totalDecoded == 0) {
            s.close();
            throw new IllegalStateException(s.lastError);
        }
        return s;
    }

    /**
     * The file's size in bytes, or -1 if the server will not say.
     *
     * Asks for the first two bytes and reads the total out of the Content-Range
     * reply ("bytes 0-1/7612845"). A HEAD would be the obvious way to do this and
     * is what this used to do, but Audius answers HEAD on its stream endpoint with
     * 403 after redirecting -- so seeking silently failed there and the track
     * restarted while the progress bar jumped. A ranged GET works on both catalogs.
     */
    private static long totalLength(String url) {
        HttpURLConnection c = null;
        try {
            c = (HttpURLConnection) new URL(url).openConnection();
            c.setConnectTimeout(8000);
            c.setReadTimeout(8000);
            c.setInstanceFollowRedirects(true);
            c.setRequestProperty("User-Agent", "QuestForgeJukebox/1.0");
            c.setRequestProperty("Range", "bytes=0-1");

            int status = c.getResponseCode();
            if (status == 206) {
                String range = c.getHeaderField("Content-Range");
                if (range != null) {
                    int slash = range.lastIndexOf('/');
                    if (slash >= 0) {
                        String total = range.substring(slash + 1).trim();
                        if (!"*".equals(total)) return Long.parseLong(total);
                    }
                }
                return -1L;
            }
            // 200 means the range was ignored, so this server cannot seek at all.
            return -1L;
        } catch (Throwable t) {
            return -1L;
        } finally {
            if (c != null) try { c.disconnect(); } catch (Throwable ignored) { }
        }
    }

    /** True when the stream already carries raw samples we can queue as-is. */
    private static boolean isPcm(AudioFormat f) {
        return (AudioFormat.Encoding.PCM_SIGNED.equals(f.getEncoding())
                || AudioFormat.Encoding.PCM_UNSIGNED.equals(f.getEncoding()))
                && f.getSampleSizeInBits() == 16;
    }

    /** Decodes ahead of playback, downmixing to mono on the way in. */
    private final class Pump implements Runnable {
        @Override public void run() {
            byte[] buf = new byte[16384];
            byte[] mono = new byte[16384];
            try {
                while (alive) {
                    int n = readFully(buf);
                    if (n <= 0) { ended = true; break; }

                    int bytes;
                    if (channels == 1) {
                        System.arraycopy(buf, 0, mono, 0, n);
                        bytes = n;
                    } else {
                        // OpenAL positions mono only; a stereo source has no place
                        // in the world at all, it just plays flat in both ears.
                        int frames = n / (2 * channels);
                        for (int f = 0; f < frames; f++) {
                            int sum = 0;
                            for (int ch = 0; ch < channels; ch++) {
                                int idx = (f * channels + ch) * 2;
                                sum += (short) ((buf[idx] & 0xFF) | (buf[idx + 1] << 8));
                            }
                            short m = (short) (sum / channels);
                            mono[f * 2]     = (byte) (m & 0xFF);
                            mono[f * 2 + 1] = (byte) ((m >> 8) & 0xFF);
                        }
                        bytes = frames * 2;
                    }

                    push(mono, bytes);
                    totalDecoded += bytes;
                }
            } catch (Throwable t) {
                lastError = t.toString();
            } finally {
                ended = true;
            }
        }

        /**
         * A zero-length read is not end of stream: the tritonus converters behind
         * the mp3/ogg providers return 0 while priming, and over a network they do
         * it more often than from disk.
         */
        private int readFully(byte[] dest) throws Exception {
            int total = 0, zeros = 0;
            while (total < dest.length) {
                int n = in.read(dest, total, dest.length - total);
                if (n < 0) break;
                if (n == 0) {
                    if (total > 0) break;
                    if (++zeros > 40) break;
                    Thread.sleep(5);
                    continue;
                }
                zeros = 0;
                total += n;

                // Do not run far ahead of playback; the ring is the buffer.
                synchronized (lock) {
                    while (available > RING_BYTES - 32768 && alive) {
                        lock.wait(50);
                    }
                }
            }
            return total > 0 ? total : -1;
        }
    }

    private void push(byte[] data, int len) {
        synchronized (lock) {
            for (int i = 0; i < len; i++) {
                ring[writePos] = data[i];
                writePos = (writePos + 1) % RING_BYTES;
                if (available < RING_BYTES) available++;
                else readPos = (readPos + 1) % RING_BYTES;
            }
            lock.notifyAll();
        }
    }

    @Override
    public int read(byte[] dest) {
        synchronized (lock) {
            int n = Math.min(available, dest.length);
            n -= n % 2;
            for (int i = 0; i < n; i++) {
                dest[i] = ring[readPos];
                readPos = (readPos + 1) % RING_BYTES;
            }
            available -= n;
            if (n < dest.length) {
                if (ended && available == 0) return n > 0 ? n : -1;   // track finished
                starved++;
                for (int i = n; i < dest.length; i++) dest[i] = 0;     // brief silence
            }
            lock.notifyAll();
            return dest.length;
        }
    }

    /**
     * The position this stream actually began at. Not necessarily the position
     * that was asked for: a server that refuses range requests starts from the
     * top, and the progress bar has to follow the audio rather than the request.
     */
    public long startedAtMs() { return startedAtMs; }

    @Override public int sampleRate() { return rate; }

    @Override public String describe() { return label; }

    public String[] status() {
        synchronized (lock) {
            return new String[] {
                "streaming    : " + label,
                "buffered     : " + (available * 100 / RING_BYTES) + "%  ("
                        + available + " / " + RING_BYTES + ")",
                "decoded      : " + totalDecoded + " bytes"
                        + (starved > 0 ? "   underruns=" + starved : ""),
                "state        : " + (ended ? "stream ended" : "receiving"),
                "last error   : " + (lastError == null ? "none" : lastError)
            };
        }
    }

    public void close() {
        alive = false;
        synchronized (lock) { lock.notifyAll(); }
        try { in.close(); } catch (Throwable ignored) { }
        try { connection.disconnect(); } catch (Throwable ignored) { }
    }
}
