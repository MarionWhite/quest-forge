package com.questforge.content.jukebox;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import net.minecraft.server.MinecraftServer;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.InputStreamReader;
import java.io.OutputStreamWriter;
import java.io.Writer;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Playlists shared with everyone on the server. Server side only.
 *
 * This is the one part of the jukebox where one player's typing reaches every other
 * player's machine, so it is written as though the client were hostile, because a
 * client is only ever software running on somebody else's computer. Names are
 * clipped, track keys go through the same host check that guards a bound track, and
 * everything is bounded -- per playlist, per player, and overall -- so no amount of
 * publishing can grow the save file or a packet without limit.
 *
 * Local files are refused outright. A path on your machine means nothing on mine,
 * so a shared playlist of them would be a list of songs nobody else can play.
 */
public final class PublicPlaylists {

    /**
     * Bounds, chosen so a whole playlist still fits in one packet. Minecraft's
     * custom payload tops out at 32767 bytes; the worst case here, every field at
     * its cap, lands around 29KB.
     */
    public static final int MAX_TRACKS = 40;
    public static final int MAX_NAME = 40;
    private static final int MAX_PER_PLAYER = 20;
    private static final int MAX_TOTAL = 200;

    private static final String FILE = "qf-jukebox-public.json";

    /** Insertion-ordered, so the browse list is stable between openings. */
    private static final Map<String, Entry> entries = new LinkedHashMap<String, Entry>();
    private static boolean loaded;

    private PublicPlaylists() { }

    /** One shared playlist. {@code tracks} is empty in an index listing. */
    public static final class Entry {
        public String id;
        public String name;
        public String owner;
        public String ownerId;
        public long published;
        public List<Track> tracks = new ArrayList<Track>();

        public int count;

        public Entry() { }

        /** The listing form: everything but the songs. */
        public Entry summary() {
            Entry e = new Entry();
            e.id = id;
            e.name = name;
            e.owner = owner;
            e.ownerId = ownerId;
            e.published = published;
            e.count = tracks.size();
            return e;
        }
    }

    /**
     * The id is owner and name together, which makes republishing the same playlist
     * an update rather than a second copy. A UUID never contains '|', and names have
     * theirs stripped, so the split is unambiguous.
     */
    private static String idOf(String ownerId, String name) {
        return ownerId + "|" + name;
    }

    // ------------------------------------------------------------------
    // Publishing
    // ------------------------------------------------------------------

    /**
     * Shares a playlist, replacing any earlier version of it. Returns what to tell
     * the player, which is never silent: a publish that quietly dropped half the
     * songs would look like the feature was broken.
     */
    public static synchronized String publish(String ownerId, String ownerName,
                                              String rawName, List<Track> rawTracks) {
        ensureLoaded();

        String name = cleanName(rawName);
        if (name.isEmpty()) return "That playlist needs a name before it can be shared.";

        List<Track> tracks = new ArrayList<Track>();
        int dropped = 0;
        for (int i = 0; i < rawTracks.size(); i++) {
            Track t = rawTracks.get(i);
            if (t == null) { dropped++; continue; }

            // The same host check a bound track goes through, for the same reason:
            // these URLs are fetched by every client that opens the playlist.
            String key = com.questforge.content.net.PacketBindTrack.sanitize(t.key());
            if (key.isEmpty() || !(key.startsWith("http://") || key.startsWith("https://"))) {
                dropped++;
                continue;
            }
            if (tracks.size() >= MAX_TRACKS) { dropped++; continue; }

            tracks.add(Track.remote(key, clip(t.source, 32), clip(t.title, 80),
                                    clip(t.artist, 60), clip(t.album, 60),
                                    t.durationMs < 0 ? 0L : t.durationMs,
                                    t.artUrl == null ? null : clip(t.artUrl, 200)));
        }

        if (tracks.isEmpty()) {
            return "Nothing in \"" + name + "\" can be shared -- shared playlists "
                 + "hold streamed tracks, not files on your own machine.";
        }

        String id = idOf(ownerId, name);
        boolean replacing = entries.containsKey(id);

        if (!replacing) {
            if (countFor(ownerId) >= MAX_PER_PLAYER) {
                return "You have already shared " + MAX_PER_PLAYER + " playlists.";
            }
            if (entries.size() >= MAX_TOTAL) {
                return "The server is holding as many shared playlists as it can.";
            }
        }

        Entry e = new Entry();
        e.id = id;
        e.name = name;
        e.owner = clip(ownerName, 32);
        e.ownerId = ownerId;
        e.published = System.currentTimeMillis();
        e.tracks = tracks;
        entries.put(id, e);
        save();

        String verb = replacing ? "Updated" : "Shared";
        if (dropped > 0) {
            return verb + " \"" + name + "\" with " + tracks.size()
                 + " songs; " + dropped + " could not be shared.";
        }
        return verb + " \"" + name + "\" with " + tracks.size() + " songs.";
    }

    /** Takes a playlist back down. Only its owner, or an operator, may do it. */
    public static synchronized String unpublish(String ownerId, String rawName,
                                                boolean operator) {
        ensureLoaded();
        String name = cleanName(rawName);

        Entry mine = entries.get(idOf(ownerId, name));
        if (mine != null) {
            entries.remove(mine.id);
            save();
            return "\"" + name + "\" is no longer shared.";
        }
        if (operator) {
            // An operator removing someone else's, by name.
            for (Entry e : new ArrayList<Entry>(entries.values())) {
                if (e.name.equals(name)) {
                    entries.remove(e.id);
                    save();
                    return "Removed \"" + name + "\" (shared by " + e.owner + ").";
                }
            }
        }
        return "\"" + name + "\" was not shared.";
    }

    // ------------------------------------------------------------------
    // Reading
    // ------------------------------------------------------------------

    /** Names and counts, without the songs -- what the Public tab lists. */
    public static synchronized List<Entry> index() {
        ensureLoaded();
        List<Entry> out = new ArrayList<Entry>(entries.size());
        for (Entry e : entries.values()) out.add(e.summary());
        return out;
    }

    public static synchronized Entry byId(String id) {
        ensureLoaded();
        return id == null ? null : entries.get(id);
    }

    private static int countFor(String ownerId) {
        int n = 0;
        for (Entry e : entries.values()) {
            if (e.ownerId.equals(ownerId)) n++;
        }
        return n;
    }

    /** Names are shown to everyone, so they lose control characters and '|'. */
    private static String cleanName(String raw) {
        if (raw == null) return "";
        StringBuilder b = new StringBuilder();
        for (int i = 0; i < raw.length() && b.length() < MAX_NAME; i++) {
            char c = raw.charAt(i);
            if (c == '|' || c == '§' || c < ' ') continue;
            b.append(c);
        }
        return b.toString().trim();
    }

    private static String clip(String s, int max) {
        if (s == null) return "";
        s = s.replace('§', ' ').trim();
        return s.length() <= max ? s : s.substring(0, max);
    }

    // ------------------------------------------------------------------
    // Persistence
    // ------------------------------------------------------------------

    /**
     * Kept beside the world rather than in config, so shared playlists belong to
     * the world they were shared in and travel with a backup of it.
     */
    private static File file() {
        MinecraftServer server = MinecraftServer.getServer();
        File dir = null;
        try {
            if (server != null && server.getEntityWorld() != null) {
                dir = server.getEntityWorld().getSaveHandler().getWorldDirectory();
            }
        } catch (Throwable ignored) {
            // Fall through to the server folder.
        }
        if (dir == null) dir = server == null ? new File(".") : server.getFile(".");
        if (!dir.exists()) dir.mkdirs();
        return new File(dir, FILE);
    }

    /** Dropped on world unload so a second world does not inherit the first's. */
    public static synchronized void reset() {
        entries.clear();
        loaded = false;
    }

    private static void ensureLoaded() {
        if (loaded) return;
        loaded = true;

        File f = file();
        if (!f.isFile()) return;

        FileInputStream in = null;
        try {
            in = new FileInputStream(f);
            JsonElement parsed = new JsonParser().parse(new InputStreamReader(in, "UTF-8"));
            if (!parsed.isJsonObject()) return;

            JsonArray lists = parsed.getAsJsonObject().getAsJsonArray("shared");
            if (lists == null) return;

            for (int i = 0; i < lists.size() && entries.size() < MAX_TOTAL; i++) {
                if (!lists.get(i).isJsonObject()) continue;
                try {
                    JsonObject o = lists.get(i).getAsJsonObject();
                    Entry e = new Entry();
                    e.name = cleanName(string(o, "name"));
                    e.owner = clip(string(o, "owner"), 32);
                    e.ownerId = string(o, "ownerId");
                    if (e.name.isEmpty() || e.ownerId == null) continue;

                    JsonElement when = o.get("published");
                    e.published = when != null && when.isJsonPrimitive() ? when.getAsLong() : 0L;
                    e.id = idOf(e.ownerId, e.name);

                    JsonArray tracks = o.getAsJsonArray("tracks");
                    if (tracks != null) readTracks(tracks, e.tracks);
                    if (e.tracks.isEmpty()) continue;

                    entries.put(e.id, e);
                } catch (Throwable skipOne) {
                    continue;
                }
            }
        } catch (Throwable t) {
            com.questforge.content.QuestForgeContent.log.warn(
                    "[jukebox] could not read " + FILE + "; no shared playlists this session", t);
        } finally {
            if (in != null) try { in.close(); } catch (Throwable ignored) { }
        }
    }

    /**
     * Read back through the same checks that were applied on the way in. The file
     * sits in a world folder that could have come from anywhere, so trusting it
     * would only move the problem from the packet to the disk.
     */
    private static void readTracks(JsonArray array, List<Track> out) {
        for (int i = 0; i < array.size() && out.size() < MAX_TRACKS; i++) {
            if (!array.get(i).isJsonObject()) continue;
            JsonObject o = array.get(i).getAsJsonObject();

            String key = com.questforge.content.net.PacketBindTrack.sanitize(string(o, "key"));
            if (key.isEmpty() || !(key.startsWith("http://") || key.startsWith("https://"))) continue;

            JsonElement d = o.get("duration");
            long duration = d != null && d.isJsonPrimitive() ? d.getAsLong() : 0L;

            out.add(Track.remote(key, clip(string(o, "source"), 32),
                                 clip(string(o, "title"), 80),
                                 clip(string(o, "artist"), 60),
                                 clip(string(o, "album"), 60),
                                 duration < 0 ? 0L : duration,
                                 clip(string(o, "art"), 200)));
        }
    }

    private static void save() {
        Writer out = null;
        try {
            JsonArray lists = new JsonArray();
            for (Entry e : entries.values()) {
                JsonObject o = new JsonObject();
                o.addProperty("name", e.name);
                o.addProperty("owner", e.owner);
                o.addProperty("ownerId", e.ownerId);
                o.addProperty("published", Long.valueOf(e.published));

                JsonArray tracks = new JsonArray();
                for (int i = 0; i < e.tracks.size(); i++) {
                    Track t = e.tracks.get(i);
                    JsonObject j = new JsonObject();
                    j.addProperty("key", t.key());
                    j.addProperty("source", t.source);
                    j.addProperty("title", t.title);
                    j.addProperty("artist", t.artist);
                    j.addProperty("album", t.album);
                    j.addProperty("duration", Long.valueOf(t.durationMs));
                    if (t.artUrl != null) j.addProperty("art", t.artUrl);
                    tracks.add(j);
                }
                o.add("tracks", tracks);
                lists.add(o);
            }

            JsonObject root = new JsonObject();
            root.add("shared", lists);

            out = new OutputStreamWriter(new FileOutputStream(file()), "UTF-8");
            out.write(root.toString());
        } catch (Throwable t) {
            com.questforge.content.QuestForgeContent.log.warn(
                    "[jukebox] could not save " + FILE, t);
        } finally {
            if (out != null) try { out.close(); } catch (Throwable ignored) { }
        }
    }

    private static String string(JsonObject o, String key) {
        JsonElement e = o.get(key);
        if (e == null || e.isJsonNull() || !e.isJsonPrimitive()) return null;
        String s = e.getAsString();
        return s.isEmpty() ? null : s;
    }
}
