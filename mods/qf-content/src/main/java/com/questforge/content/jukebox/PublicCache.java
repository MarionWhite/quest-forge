package com.questforge.content.jukebox;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * What this client knows about the server's shared playlists.
 *
 * A cache, not a source: the server holds the real list and everything here is a
 * copy that arrived in a packet. The screen reads it every frame, and packets land
 * on the network thread, so the two collections are concurrent and are replaced
 * wholesale rather than edited in place.
 *
 * Nothing here is trusted for playback beyond what already passed the host rules
 * on the way in -- this only decides what a list looks like.
 */
public final class PublicCache {

    /** Do not ask the server again more often than this while browsing. */
    private static final long REFRESH_MS = 15000L;

    private static volatile List<PublicPlaylists.Entry> index =
            new ArrayList<PublicPlaylists.Entry>();

    private static final Map<String, List<Track>> tracks =
            new ConcurrentHashMap<String, List<Track>>();

    /** Ids asked for and not yet answered, so a list does not ask on every frame. */
    private static final Map<String, Boolean> pending =
            new ConcurrentHashMap<String, Boolean>();

    private static volatile long lastIndexRequest;
    private static volatile boolean everAnswered;

    private PublicCache() { }

    public static List<PublicPlaylists.Entry> index() { return index; }

    /** True once the server has replied at least once, so "empty" can be trusted. */
    public static boolean ready() { return everAnswered; }

    public static void setIndex(List<PublicPlaylists.Entry> fresh) {
        index = fresh == null ? new ArrayList<PublicPlaylists.Entry>() : fresh;
        everAnswered = true;
        // Anything already open may have changed underneath; let it be fetched again.
        tracks.clear();
        pending.clear();
    }

    public static void setTracks(String id, List<Track> list) {
        if (id == null) return;
        tracks.put(id, list == null ? new ArrayList<Track>() : list);
        pending.remove(id);
    }

    /** The songs in a shared playlist, or null while they are still on their way. */
    public static List<Track> tracks(String id) {
        if (id == null) return null;
        List<Track> known = tracks.get(id);
        if (known != null) return known;

        if (pending.putIfAbsent(id, Boolean.TRUE) == null) {
            com.questforge.content.net.QFNetwork.toServer(
                    new com.questforge.content.net.PacketRequestPublic(id));
        }
        return null;
    }

    /** Asks for the index, at most once every {@link #REFRESH_MS}. */
    public static void refresh(boolean force) {
        long now = System.currentTimeMillis();
        if (!force && everAnswered && now - lastIndexRequest < REFRESH_MS) return;

        lastIndexRequest = now;
        com.questforge.content.net.QFNetwork.toServer(
                new com.questforge.content.net.PacketRequestPublic(""));
    }

    /** Whether this player has already shared a playlist under this name. */
    public static boolean isSharedByMe(String myId, String name) {
        if (myId == null || name == null) return false;
        List<PublicPlaylists.Entry> current = index;
        for (int i = 0; i < current.size(); i++) {
            PublicPlaylists.Entry e = current.get(i);
            if (myId.equals(e.ownerId) && name.equals(e.name)) return true;
        }
        return false;
    }

    public static PublicPlaylists.Entry byId(String id) {
        List<PublicPlaylists.Entry> current = index;
        for (int i = 0; i < current.size(); i++) {
            if (current.get(i).id.equals(id)) return current.get(i);
        }
        return null;
    }

    /** Dropped when leaving a world; the next server has its own playlists. */
    public static void clear() {
        index = new ArrayList<PublicPlaylists.Entry>();
        tracks.clear();
        pending.clear();
        everAnswered = false;
        lastIndexRequest = 0L;
    }
}
