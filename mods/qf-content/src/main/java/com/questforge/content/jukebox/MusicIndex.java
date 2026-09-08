package com.questforge.content.jukebox;

import net.minecraft.client.Minecraft;

import javax.sound.sampled.AudioFileFormat;
import javax.sound.sampled.AudioSystem;
import java.io.File;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;

/**
 * The searchable library.
 *
 * Two things make this different from just listing a folder, and both matter the
 * moment the library stops being small:
 *
 *  - Reading tags means opening and parsing every file. At a few thousand tracks
 *    that is seconds of work, so it happens on a worker thread and the browser
 *    stays responsive while it runs, showing progress.
 *  - Search runs against a prebuilt lowercase haystack per track rather than
 *    re-deriving strings on every keystroke, so typing stays smooth on a big list.
 *
 * Search is synchronous here because a local list is instant. When results start
 * coming from a network catalog, only {@link #search} needs to become asynchronous;
 * the browser already treats its result list as something that arrives and changes.
 */
public final class MusicIndex {

    private static final String[] EXTS = { ".ogg", ".mp3", ".wav", ".aiff", ".aif", ".au" };

    private static volatile List<Track> tracks = new ArrayList<Track>();
    private static volatile boolean indexing;
    private static volatile int scanned;
    private static volatile int total;
    private static volatile Thread worker;

    private MusicIndex() { }

    /** <game dir>/jukebox, created on first use so it is obvious where music goes. */
    public static File folder() {
        File dir = new File(Minecraft.getMinecraft().mcDataDir, "jukebox");
        if (!dir.exists()) dir.mkdirs();
        return dir;
    }

    public static List<Track> all() { return tracks; }
    public static boolean isIndexing() { return indexing; }
    public static int scanned() { return scanned; }
    public static int total() { return total; }

    public static String status() {
        if (indexing) return "indexing " + scanned + " / " + total;
        return tracks.size() + " track" + (tracks.size() == 1 ? "" : "s");
    }

    /** Kicks off a background rescan. Cheap to call; ignored while one is running. */
    public static void rescan() {
        if (indexing) return;
        indexing = true;
        scanned = 0;
        total = 0;

        worker = new Thread(new Runnable() {
            @Override public void run() {
                try {
                    build();
                } catch (Throwable t) {
                    com.questforge.content.QuestForgeContent.log.error("[jukebox] index failed", t);
                } finally {
                    indexing = false;
                }
            }
        }, "qf-jukebox-index");
        worker.setDaemon(true);
        worker.setPriority(Thread.MIN_PRIORITY);   // never compete with the render thread
        worker.start();
    }

    /** Builds the index if it has never been built. */
    public static void ensureBuilt() {
        if (tracks.isEmpty() && !indexing) rescan();
    }

    private static void build() {
        List<File> files = new ArrayList<File>();
        // Seeded with every root's own path so a folder cannot walk into another
        // that is already being scanned, and so the same file is never listed twice
        // when two roots overlap through a symlink.
        java.util.Set<String> seen = new java.util.HashSet<String>();
        for (File root : MusicFolders.roots()) {
            collect(root, files, seen, 0);
        }
        total = files.size();

        List<Track> found = new ArrayList<Track>(files.size());
        for (File f : files) {
            found.add(read(f));
            scanned++;
            // Publish progressively so a large library becomes usable while it loads
            // rather than staying empty until the very end.
            if ((scanned & 31) == 0) {
                List<Track> snapshot = new ArrayList<Track>(found);
                Collections.sort(snapshot);
                tracks = snapshot;
            }
        }
        Collections.sort(found);
        tracks = found;
    }

    /** Subfolders are included, so people can organise by artist or album. */
    private static void collect(File dir, List<File> out,
                                java.util.Set<String> seen, int depth) {
        if (depth > 6) return;                      // guard against symlink loops
        if (!seen.add(canonical(dir))) return;      // and against revisiting a folder

        File[] entries = dir.listFiles();
        if (entries == null) return;                // unreadable: skip it quietly
        for (File f : entries) {
            if (f.isDirectory()) {
                collect(f, out, seen, depth + 1);
                continue;
            }
            String n = f.getName().toLowerCase();
            for (String ext : EXTS) {
                if (n.endsWith(ext)) { out.add(f); break; }
            }
        }
    }

    private static String canonical(File f) {
        try {
            return f.getCanonicalPath();
        } catch (Throwable t) {
            return f.getAbsolutePath();
        }
    }

    /**
     * Reads tags where the decoder exposes them. mp3spi and vorbisspi surface
     * author/title/album/duration through AudioFileFormat properties; WAV carries
     * none, so those fall back to the filename.
     */
    private static Track read(File f) {
        String title = null, artist = null, album = null;
        long durationMs = 0L;
        try {
            AudioFileFormat aff = AudioSystem.getAudioFileFormat(f);
            Map<String, Object> p = aff.properties();
            if (p != null) {
                title = str(p.get("title"));
                artist = str(p.get("author"));
                album = str(p.get("album"));
                Object dur = p.get("duration");     // microseconds
                if (dur instanceof Number) durationMs = ((Number) dur).longValue() / 1000L;
            }
            if (durationMs <= 0 && aff.getFrameLength() > 0
                    && aff.getFormat().getFrameRate() > 0) {
                durationMs = (long) (aff.getFrameLength() / aff.getFormat().getFrameRate() * 1000.0);
            }
        } catch (Throwable ignored) {
            // Unreadable or unsupported: still list it, named by its file.
        }
        return new Track(f, title, artist, album, durationMs);
    }

    private static String str(Object o) { return o == null ? null : String.valueOf(o); }

    /**
     * Word-by-word match across title, artist and album, best first.
     *
     * Shares its matching with the catalog so the local folder behaves the same
     * way: word order does not matter, an artist and a song title can be typed
     * together, and a typo still finds the track.
     */
    public static List<Track> search(String query) {
        List<Track> src = tracks;
        final String[] tokens = SearchMatch.tokenize(query);
        if (tokens.length == 0) return src;

        List<Track> hits = new ArrayList<Track>();
        for (int i = 0; i < src.size(); i++) {
            Track t = src.get(i);
            if (SearchMatch.matchesAll(tokens, t.title, t.artist, t.album)) hits.add(t);
        }

        Collections.sort(hits, new java.util.Comparator<Track>() {
            @Override public int compare(Track a, Track b) {
                return SearchMatch.score(tokens, b.title, b.artist, b.album)
                     - SearchMatch.score(tokens, a.title, a.artist, a.album);
            }
        });
        return hits;
    }

    private static int cursor;

    /** Next track in the library, wrapping. Null when there is nothing indexed. */
    public static Track next() {
        List<Track> src = tracks;
        if (src.isEmpty()) return null;
        Track t = src.get(Math.abs(cursor) % src.size());
        cursor = (cursor + 1) % Math.max(1, src.size());
        return t;
    }

    /**
     * Finds a track by its key, for a jukebox restoring what it was bound to.
     *
     * A catalog key is the audio URL itself, so a bound remote track survives a
     * restart without needing the search that found it to be repeated -- the block
     * remembers enough to play again on its own.
     */
    public static Track byKey(String key) {
        if (key == null || key.isEmpty()) return null;

        if (key.startsWith("http://") || key.startsWith("https://")) {
            return Track.remote(key, sourceOf(key), nameFromUrl(key), "", "", 0L);
        }

        List<Track> src = tracks;
        for (int i = 0; i < src.size(); i++) {
            Track t = src.get(i);
            if (!t.isRemote() && t.file.getName().equals(key)) return t;
        }
        return null;
    }

    /** Which catalog a stored URL came from, for the row's label. */
    private static String sourceOf(String url) {
        if (url.contains("audius.co")) return "audius";
        if (url.contains("ccmixter.org")) return "ccmixter";
        if (url.contains("archive.org")) return "archive.org";
        // Everything else bound to a jukebox is a radio station.
        return "radio";
    }

    /**
     * A readable name for a track restored from a bound URL.
     *
     * Audius URLs end in an opaque id rather than a filename, so there is nothing
     * to prettify -- the block shows a placeholder until the track is played and
     * the stream itself supplies a better label.
     */
    private static String nameFromUrl(String url) {
        String n = url;

        int query = n.indexOf('?');
        if (query >= 0) n = n.substring(0, query);

        // ".../tracks/<id>/stream" carries no name worth showing.
        if (n.endsWith("/stream")) return "Saved track";

        int slash = n.lastIndexOf('/');
        if (slash >= 0) n = n.substring(slash + 1);
        int dot = n.lastIndexOf('.');
        if (dot > 0) n = n.substring(0, dot);
        try {
            n = java.net.URLDecoder.decode(n, "UTF-8");
        } catch (Throwable ignored) {
            // Keep the escaped form rather than losing the name entirely.
        }
        n = n.replace('_', ' ').replace("--", " - ").trim();
        return n.isEmpty() ? "Saved track" : n;
    }
}
