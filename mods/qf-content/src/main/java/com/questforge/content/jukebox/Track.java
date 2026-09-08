package com.questforge.content.jukebox;

import java.io.File;

/**
 * One entry in the library: what a row in the browser shows and what playback needs.
 *
 * A track is either a local file or a URL in a remote catalog. The browser, the
 * block binding and the search all treat the two the same -- only {@link #open}
 * cares which it is. That is why the GUI needed no restructuring when the library
 * grew from a folder to an on-demand catalog.
 */
public class Track implements Comparable<Track> {

    /** The local file, or null for a catalog track. */
    public final File file;

    /** The audio URL for a catalog track, or null for a local file. */
    public final String url;

    /** Which catalog this came from ("archive.org"), or "" when local. */
    public final String source;

    public final String title;
    public final String artist;
    public final String album;
    public final long durationMs;

    /** Cover image URL where the catalog offers one, else null. */
    public final String artUrl;

    /** A local track, read from disk. */
    public Track(File file, String title, String artist, String album, long durationMs) {
        this(file, null, "", title, artist, album, durationMs, null,
             empty(title) ? stripExtension(file.getName()) : title);
    }

    /** A catalog track, streamed from a URL. */
    public static Track remote(String url, String source, String title,
                               String artist, String album, long durationMs) {
        return remote(url, source, title, artist, album, durationMs, null);
    }

    /** A catalog track that came with cover art. */
    public static Track remote(String url, String source, String title, String artist,
                               String album, long durationMs, String artUrl) {
        return new Track(null, url, source, title, artist, album, durationMs, artUrl,
                         empty(title) ? "Untitled" : title);
    }

    private Track(File file, String url, String source, String title, String artist,
                  String album, long durationMs, String artUrl, String resolvedTitle) {
        this.file = file;
        this.url = url;
        this.source = source == null ? "" : source;
        this.album = empty(album) ? "" : album.trim();
        this.durationMs = durationMs;
        this.artUrl = empty(artUrl) ? null : artUrl.trim();

        String name = resolvedTitle.trim();
        String by = empty(artist) ? "" : artist.trim();
        if (by.isEmpty()) {
            String[] split = splitArtist(name);
            if (split != null) { by = split[0]; name = split[1]; }
        }
        this.title = name;
        this.artist = by;
    }

    /** How an upload writes the artist into the title when there is no field for it. */
    private static final String[] ARTIST_SEPARATORS = { " -- ", " - ", " – ", " — " };

    /**
     * Recovers the artist from a title like "Marion Black - who knows".
     *
     * Half of archive.org's audio has no creator field at all and puts the name in
     * the title instead, which left those rows reading "Unknown artist" and, worse,
     * unfindable: the artist field carries the most weight in search scoring, so a
     * name sitting in the title was worth a fraction of what it should have been.
     *
     * Only ever runs when the artist is genuinely empty, so a name the catalog did
     * supply can never be overwritten by a guess. The guards are what keep it from
     * mangling titles that merely contain a dash -- a long left half is a phrase
     * rather than a name, and a numeric one is a track number.
     */
    private static String[] splitArtist(String title) {
        for (int i = 0; i < ARTIST_SEPARATORS.length; i++) {
            String separator = ARTIST_SEPARATORS[i];
            int at = title.indexOf(separator);
            if (at <= 0) continue;

            String left = title.substring(0, at).trim();
            String right = title.substring(at + separator.length()).trim();
            if (left.isEmpty() || right.isEmpty()) continue;
            if (left.length() > 40) continue;
            if (isNumber(left)) continue;

            return new String[] { left, right };
        }
        return null;
    }

    private static boolean isNumber(String s) {
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);
            if (c != '.' && (c < '0' || c > '9')) return false;
        }
        return true;
    }

    /** Rebuilt from saved data, where only the fields that were written survive. */
    public static Track saved(String key, String source, String title, String artist,
                              String album, long durationMs, String artUrl) {
        if (key != null && (key.startsWith("http://") || key.startsWith("https://"))) {
            return remote(key, source, title, artist, album, durationMs, artUrl);
        }
        File f = new File(MusicIndex.folder(), key == null ? "" : key);
        return new Track(f, null, source, title, artist, album, durationMs, artUrl,
                         empty(title) ? f.getName() : title);
    }

    /**
     * Two tracks are the same when they point at the same audio. Saved songs,
     * playlists and the queue all rely on this to avoid duplicates and to show
     * whether the track on screen is already in someone's library.
     */
    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (!(o instanceof Track)) return false;
        return key().equals(((Track) o).key());
    }

    @Override
    public int hashCode() { return key().hashCode(); }

    public boolean isRemote() { return url != null; }

    /**
     * Opens this track for playback. Streaming may block on the network, so this
     * belongs on a worker thread, never on the render thread.
     */
    public DirectAudio.PcmSource open() throws Exception {
        return open(0L);
    }

    /** Opens the track ready to play from {@code startMs}, for seeking and replay. */
    public DirectAudio.PcmSource open(long startMs) throws Exception {
        if (isRemote()) return StreamSource.open(url, label(), startMs, durationMs);
        return DirectAudio.openFile(file, startMs);
    }

    /**
     * Stable identifier used to bind a track to a jukebox block and to find it
     * again later. A filename for local tracks, the URL for catalog ones.
     */
    public String key() {
        return isRemote() ? url : file.getName();
    }

    public String label() {
        return artist.isEmpty() ? title : artist + " - " + title;
    }

    /**
     * m:ss, or h:mm:ss for the long concert and compilation uploads a catalog is
     * full of -- "180:09" reads as nonsense where "3:00:09" reads as three hours.
     * Blank when the source did not report a duration.
     */
    public String durationText() {
        if (durationMs <= 0) return "";
        long total = durationMs / 1000L;
        long h = total / 3600, m = (total % 3600) / 60, s = total % 60;
        if (h > 0) return h + ":" + String.format("%02d:%02d", m, s);
        return m + ":" + String.format("%02d", s);
    }

    public String artistText() { return artist.isEmpty() ? "Unknown artist" : artist; }

    @Override
    public int compareTo(Track o) {
        int byArtist = artist.compareToIgnoreCase(o.artist);
        if (byArtist != 0) return byArtist;
        return title.compareToIgnoreCase(o.title);
    }

    private static boolean empty(String s) { return s == null || s.trim().isEmpty(); }

    private static String stripExtension(String n) {
        int dot = n.lastIndexOf('.');
        return dot > 0 ? n.substring(0, dot) : n;
    }
}
