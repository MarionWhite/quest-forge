package com.questforge.content.jukebox;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import net.minecraft.client.Minecraft;

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
 * Saved songs and playlists, kept on disk.
 *
 * A catalog track exists only as a search result: close the screen and it is gone
 * unless something wrote it down. So enough of each track is stored to rebuild it
 * later without searching again -- its URL, what it is called, and how long it is.
 * That is what makes saving meaningful for streamed music rather than only for
 * files already on the machine.
 *
 * Written as JSON because the shape is nested, and read defensively: a library
 * that fails to parse costs someone their playlists, so anything unreadable is
 * skipped rather than allowed to abort the load.
 */
public final class Library {

    private static final String FILE = "qf-jukebox-library.json";

    private static final List<Track> saved = new ArrayList<Track>();
    private static final Map<String, List<Track>> playlists =
            new LinkedHashMap<String, List<Track>>();

    private static boolean loaded;

    private Library() { }

    private static File file() {
        File dir = new File(Minecraft.getMinecraft().mcDataDir, "config");
        if (!dir.exists()) dir.mkdirs();
        return new File(dir, FILE);
    }

    // ------------------------------------------------------------------
    // Saved songs
    // ------------------------------------------------------------------

    public static List<Track> savedTracks() {
        ensureLoaded();
        return new ArrayList<Track>(saved);
    }

    public static boolean isSaved(Track t) {
        ensureLoaded();
        return t != null && saved.contains(t);
    }

    /** Saves or unsaves, and reports which it did so the caller can say so. */
    public static boolean toggleSave(Track t) {
        ensureLoaded();
        if (t == null) return false;

        boolean nowSaved;
        if (saved.remove(t)) {
            nowSaved = false;
        } else {
            saved.add(0, t);          // newest first, like every other library
            nowSaved = true;
        }
        save();
        return nowSaved;
    }

    // ------------------------------------------------------------------
    // Playlists
    // ------------------------------------------------------------------

    public static List<String> playlistNames() {
        ensureLoaded();
        return new ArrayList<String>(playlists.keySet());
    }

    public static List<Track> playlist(String name) {
        ensureLoaded();
        List<Track> tracks = playlists.get(name);
        return tracks == null ? new ArrayList<Track>() : new ArrayList<Track>(tracks);
    }

    public static boolean hasPlaylist(String name) {
        ensureLoaded();
        return playlists.containsKey(name);
    }

    /** Creates an empty playlist. Returns false if the name is taken or blank. */
    public static boolean createPlaylist(String name) {
        ensureLoaded();
        String clean = clean(name);
        if (clean.isEmpty() || playlists.containsKey(clean)) return false;
        playlists.put(clean, new ArrayList<Track>());
        save();
        return true;
    }

    public static void deletePlaylist(String name) {
        ensureLoaded();
        if (playlists.remove(name) != null) save();
    }

    /** Adds unless it is already there, so double-clicking cannot duplicate a song. */
    public static boolean addToPlaylist(String name, Track t) {
        ensureLoaded();
        List<Track> tracks = playlists.get(name);
        if (tracks == null || t == null || tracks.contains(t)) return false;
        tracks.add(t);
        save();
        return true;
    }

    public static void removeFromPlaylist(String name, int index) {
        ensureLoaded();
        List<Track> tracks = playlists.get(name);
        if (tracks == null || index < 0 || index >= tracks.size()) return;
        tracks.remove(index);
        save();
    }

    // ------------------------------------------------------------------
    // Persistence
    // ------------------------------------------------------------------

    private static void ensureLoaded() {
        if (loaded) return;
        loaded = true;

        File f = file();
        if (!f.isFile()) return;

        FileInputStream in = null;
        try {
            in = new FileInputStream(f);
            JsonElement parsed = new JsonParser().parse(
                    new InputStreamReader(in, "UTF-8"));
            if (!parsed.isJsonObject()) return;
            JsonObject root = parsed.getAsJsonObject();

            JsonArray savedArray = root.getAsJsonArray("saved");
            if (savedArray != null) readInto(savedArray, saved);

            JsonArray lists = root.getAsJsonArray("playlists");
            if (lists != null) {
                for (int i = 0; i < lists.size(); i++) {
                    if (!lists.get(i).isJsonObject()) continue;
                    JsonObject list = lists.get(i).getAsJsonObject();

                    String name = string(list, "name");
                    if (name == null) continue;

                    List<Track> tracks = new ArrayList<Track>();
                    JsonArray array = list.getAsJsonArray("tracks");
                    if (array != null) readInto(array, tracks);
                    playlists.put(name, tracks);
                }
            }
        } catch (Throwable t) {
            com.questforge.content.QuestForgeContent.log.warn(
                    "[jukebox] could not read " + FILE + "; starting with an empty library", t);
        } finally {
            if (in != null) try { in.close(); } catch (Throwable ignored) { }
        }
    }

    /** Skips entries that will not parse rather than losing the whole file. */
    private static void readInto(JsonArray array, List<Track> out) {
        for (int i = 0; i < array.size(); i++) {
            if (!array.get(i).isJsonObject()) continue;
            try {
                JsonObject o = array.get(i).getAsJsonObject();
                String key = string(o, "key");
                if (key == null) continue;

                long duration = 0L;
                JsonElement d = o.get("duration");
                if (d != null && d.isJsonPrimitive()) duration = d.getAsLong();

                out.add(Track.saved(key,
                        or(string(o, "source"), ""),
                        or(string(o, "title"), ""),
                        or(string(o, "artist"), ""),
                        or(string(o, "album"), ""),
                        duration,
                        string(o, "art")));
            } catch (Throwable skipOne) {
                continue;
            }
        }
    }

    private static void save() {
        Writer out = null;
        try {
            JsonObject root = new JsonObject();
            root.add("saved", write(saved));

            JsonArray lists = new JsonArray();
            for (Map.Entry<String, List<Track>> e : playlists.entrySet()) {
                JsonObject list = new JsonObject();
                list.addProperty("name", e.getKey());
                list.add("tracks", write(e.getValue()));
                lists.add(list);
            }
            root.add("playlists", lists);

            out = new OutputStreamWriter(new FileOutputStream(file()), "UTF-8");
            out.write(root.toString());
        } catch (Throwable t) {
            com.questforge.content.QuestForgeContent.log.warn(
                    "[jukebox] could not save " + FILE, t);
        } finally {
            if (out != null) try { out.close(); } catch (Throwable ignored) { }
        }
    }

    private static JsonArray write(List<Track> tracks) {
        JsonArray array = new JsonArray();
        for (int i = 0; i < tracks.size(); i++) {
            Track t = tracks.get(i);
            JsonObject o = new JsonObject();
            o.addProperty("key", t.key());
            o.addProperty("source", t.source);
            o.addProperty("title", t.title);
            o.addProperty("artist", t.artist);
            o.addProperty("album", t.album);
            o.addProperty("duration", Long.valueOf(t.durationMs));
            if (t.artUrl != null) o.addProperty("art", t.artUrl);
            array.add(o);
        }
        return array;
    }

    private static String string(JsonObject o, String key) {
        JsonElement e = o.get(key);
        if (e == null || e.isJsonNull() || !e.isJsonPrimitive()) return null;
        String s = e.getAsString();
        return s.isEmpty() ? null : s;
    }

    private static String or(String value, String fallback) {
        return value == null ? fallback : value;
    }

    private static String clean(String name) {
        return name == null ? "" : name.trim();
    }
}
