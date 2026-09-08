package com.questforge.content.jukebox;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.net.URLEncoder;
import java.util.ArrayList;
import java.util.List;

/**
 * On-demand search across the open music catalogs.
 *
 * This is the piece that makes the jukebox a music player rather than a file
 * browser: type an artist, get tracks, press play. Nothing is downloaded ahead of
 * time and nothing is installed -- {@link StreamSource} plays straight off the URL.
 *
 * Two sources, searched together because they hold opposite things:
 *
 *  - **Audius** -- current independent music, mostly electronic, hip-hop and
 *    remixes. One request returns described tracks, so its results land first.
 *  - **archive.org** -- live recordings, public-domain and netlabel material.
 *    Costs a request per matching item, so its results fill in behind.
 *
 * Both are keyless: every player who installs the mod can search immediately, on
 * any OS, with no account or signup. Neither is a mainstream commercial catalog,
 * and no legal keyless API is -- major-label releases are licensed, not open.
 */
public final class Catalog {

    private static final String SEARCH = "https://archive.org/advancedsearch.php";
    private static final String METADATA = "https://archive.org/metadata/";
    private static final String DOWNLOAD = "https://archive.org/download/";
    private static final String AGENT = "QuestForgeJukebox/1.0";

    /** Audius's load-balanced entry point, rather than pinning one discovery node. */
    private static final String AUDIUS = "https://discoveryprovider.audius.co";

    /** Audius asks third-party apps to identify themselves on every request. */
    private static final String APP = "questforge";

    /** Creative Commons music, much of it whole songs rather than reworkings. */
    private static final String CCMIXTER = "https://ccmixter.org";

    /** Live radio. Not on-demand, but it is where actual chart music is playing. */
    private static final String RADIO = "https://de1.api.radio-browser.info";

    /** Aggregates several openly licensed collections, Jamendo included. */
    private static final String OPENVERSE = "https://api.openverse.org";

    private static final int AUDIUS_LIMIT = 30;
    private static final int CCMIXTER_LIMIT = 20;
    private static final int RADIO_LIMIT = 12;
    private static final int OPENVERSE_LIMIT = 20;

    /** Total providers, so a search can tell "all down" from "nothing matched". */
    private static final int PROVIDERS = 5;


    /** Items per search. Each costs a metadata request, so this trades breadth for speed. */
    private static final int ITEMS = 12;

    /** Tracks taken from any single item, so one 200-track item cannot swamp the results. */
    private static final int PER_ITEM = 25;

    private static volatile Thread current;
    private static volatile String activeQuery = "";
    private static volatile String error;
    private static volatile boolean searching;

    private Catalog() { }

    /** Receives results as they arrive, on the search worker thread. */
    public interface Listener {
        void onResults(List<Track> tracks, boolean done);
    }

    public static boolean isSearching() { return searching; }
    public static String error() { return error; }

    public static String status() {
        if (searching) return "searching archive.org...";
        if (error != null) return "search failed: " + error;
        return "";
    }

    /**
     * Starts a search, cancelling any search still running. Returns immediately;
     * results arrive on the listener, growing as each item resolves.
     */
    public static void search(final String query, final Listener listener) {
        final String q = query == null ? "" : query.trim();
        activeQuery = q;
        error = null;

        Thread previous = current;
        if (previous != null) previous.interrupt();

        if (q.isEmpty()) {
            searching = false;
            listener.onResults(new ArrayList<Track>(), true);
            return;
        }

        searching = true;
        Thread t = new Thread(new Runnable() {
            @Override public void run() {
                List<Track> found = new ArrayList<Track>();
                try {
                    int failures = gather(q, q, found, listener);
                    if (!q.equals(activeQuery)) return;

                    // Typo rescue. The catalogs require every word they are given to
                    // match, so one slipped key returns nothing at all and local
                    // fuzzy ranking never gets a track to rank. Asking again with
                    // just the most distinctive word gets the right neighbourhood
                    // back, and the ranking sorts out which of it was meant.
                    String narrowed = mostDistinctive(q);
                    if (narrowed != null && !hasGoodMatch(found, q)) {
                        failures += gather(narrowed, q, found, listener);
                    }

                    if (!q.equals(activeQuery)) return;
                    // Only a total loss is worth reporting; one source answering is
                    // a working search, not a failed one.
                    if (found.isEmpty() && failures >= PROVIDERS) error = "no catalog reachable";
                    listener.onResults(rank(found, q), true);

                } catch (Throwable t2) {
                    if (q.equals(activeQuery)) {
                        error = t2.getMessage() == null ? t2.toString() : t2.getMessage();
                        listener.onResults(rank(found, q), true);
                    }
                } finally {
                    if (q.equals(activeQuery)) searching = false;
                }
            }
        }, "qf-catalog-search");
        t.setDaemon(true);
        t.setPriority(Thread.MIN_PRIORITY);
        current = t;
        t.start();
    }

    /**
     * Runs every provider once for one query string, publishing as results land.
     * Returns how many providers failed, so the caller can tell a quiet search
     * from a broken one.
     *
     * {@code rankAgainst} is what the player actually typed, which is not always
     * what was asked of the catalogs -- results from a narrowed retry still have to
     * be scored against the original words.
     */
    private static int gather(String queryText, String rankAgainst,
                              List<Track> found, Listener listener) {
        int failures = 0;

        // The single-request catalogs first, so something useful is on screen
        // almost immediately while the slow one is still working. Each is
        // isolated: one being down must not cost the others.
        for (int p = 0; p < 4; p++) {
            if (Thread.currentThread().isInterrupted()
                    || !rankAgainst.equals(activeQuery)) return failures;
            try {
                if (p == 0) audius(queryText, found);
                else if (p == 1) ccmixter(queryText, found);
                else if (p == 2) radio(queryText, found);
                else openverse(queryText, found);
            } catch (Throwable oneProviderFailed) {
                failures++;
                continue;
            }
            if (!rankAgainst.equals(activeQuery)) return failures;
            if (!found.isEmpty()) listener.onResults(rank(found, rankAgainst), false);
        }

        if (Thread.currentThread().isInterrupted()
                || !rankAgainst.equals(activeQuery)) return failures;

        // Then archive.org, one request per matching item.
        try {
            List<String[]> items = findItems(queryText);
            for (int i = 0; i < items.size(); i++) {
                if (Thread.currentThread().isInterrupted()
                        || !rankAgainst.equals(activeQuery)) return failures;
                try {
                    expand(items.get(i), found);
                } catch (Throwable perItem) {
                    // One bad item must not kill the whole search.
                    continue;
                }
                listener.onResults(rank(found, rankAgainst), false);
            }
        } catch (Throwable archiveFailed) {
            failures++;
        }
        return failures;
    }

    /**
     * Whether anything found so far actually answers what was typed.
     *
     * Deliberately about quality, not how many rows came back. Several of these
     * catalogs match loosely and will happily return a full page of tracks sharing
     * one common word, so counting results says a search succeeded when every row
     * is wrong -- which is exactly how a mistyped query looked before.
     */
    private static boolean hasGoodMatch(List<Track> found, String query) {
        String[] tokens = SearchMatch.tokenize(query);
        if (tokens.length == 0) return true;

        // Roughly: most of the words typed were genuinely found on one track.
        int bar = tokens.length * 2;
        for (int i = 0; i < found.size(); i++) {
            Track t = found.get(i);
            if (SearchMatch.score(tokens, t.title, t.artist, t.album) >= bar) return true;
        }
        return false;
    }

    /**
     * The single word most worth searching on its own, or null if there is only
     * one word anyway.
     *
     * Longest wins, because length tracks distinctiveness closely enough here --
     * an artist's name is usually longer than the "like" and "the" around it, and
     * a rare long word narrows a catalog far better than a common short one.
     */
    private static String mostDistinctive(String query) {
        String[] tokens = SearchMatch.tokenize(query);
        if (tokens.length < 2) return null;

        String best = tokens[0];
        for (String token : tokens) {
            if (token.length() > best.length()) best = token;
        }
        return best;
    }

    /**
     * Items matching the query, best-known first.
     *
     * The query targets the title and creator fields rather than the default
     * full-text search. Full text also matches reviews and radio transcripts, so a
     * plain search for an artist returns talk radio that merely mentions them.
     * Sorting by downloads puts recognisable recordings above obscure uploads.
     */
    private static List<String[]> findItems(String q) throws Exception {
        // Bare words, not a quoted phrase. Quoting demands the whole string appear
        // verbatim in one field, so "nirvana teen spirit" -- an artist plus part of
        // a song title -- matched nothing at all. Unquoted, the index matches the
        // words wherever they fall, and local ranking sorts out which hits are good.
        StringBuilder terms = new StringBuilder();
        for (String token : SearchMatch.tokenize(q)) {
            if (terms.length() > 0) terms.append(' ');
            terms.append(token);
        }
        if (terms.length() == 0) return new ArrayList<String[]>();

        String lucene = "mediatype:(audio) AND format:(VBR MP3) AND ("
                + "title:(" + terms + ") OR creator:(" + terms + "))";

        String url = SEARCH
                + "?q=" + enc(lucene)
                + "&fl[]=identifier&fl[]=title&fl[]=creator"
                + "&sort[]=downloads+desc"
                + "&rows=" + ITEMS + "&page=1&output=json";

        JsonObject root = fetchJson(url);
        JsonObject response = obj(root, "response");
        List<String[]> out = new ArrayList<String[]>();
        if (response == null) return out;

        JsonArray docs = response.getAsJsonArray("docs");
        if (docs == null) return out;

        for (int i = 0; i < docs.size(); i++) {
            JsonObject d = docs.get(i).getAsJsonObject();
            String id = str(d, "identifier");
            if (id == null) continue;
            out.add(new String[] { id, str(d, "title"), firstString(d, "creator") });
        }
        return out;
    }

    /**
     * Turns one item into playable tracks.
     *
     * An item is an album, a concert or a compilation, so the audio files inside it
     * are the actual tracks. Per-file metadata is preferred where the uploader
     * supplied it and the item's own title and creator fill the gaps.
     */
    private static void expand(String[] item, List<Track> out) throws Exception {
        String id = item[0];
        String itemTitle = item[1];
        String itemCreator = item[2];

        JsonObject root = fetchJson(METADATA + enc(id));
        JsonArray files = root.getAsJsonArray("files");
        if (files == null) return;

        JsonObject meta = obj(root, "metadata");
        if (itemCreator == null && meta != null) itemCreator = firstString(meta, "creator");
        if (itemTitle == null && meta != null) itemTitle = str(meta, "title");

        int taken = 0;
        for (int i = 0; i < files.size() && taken < PER_ITEM; i++) {
            JsonObject f = files.get(i).getAsJsonObject();

            String format = str(f, "format");
            String name = str(f, "name");
            if (name == null || format == null) continue;
            // "VBR MP3" and "128Kbps MP3" are both fine; the derived formats
            // (Ogg, FLAC, torrents, spectrograms) are not what we want to stream.
            if (!format.toLowerCase().contains("mp3")) continue;

            String title = str(f, "title");
            if (title == null) title = prettify(name);

            String artist = str(f, "artist");
            if (artist == null) artist = str(f, "creator");
            if (artist == null) artist = itemCreator;

            long ms = seconds(str(f, "length"));

            // Archive serves a thumbnail for every item from one tidy endpoint,
            // so every track in an item shares its cover.
            String art = "https://archive.org/services/img/" + enc(id);

            String url = DOWNLOAD + enc(id) + "/" + encPath(name);
            out.add(Track.remote(url, "archive.org", title, artist, itemTitle, ms, art));
            taken++;
        }
    }

    /**
     * Searches Audius, an open catalog of artist-uploaded music.
     *
     * Worth having alongside archive.org because the two hold almost opposite
     * things: archive.org is live recordings, public domain and netlabel material,
     * while Audius is current independent music -- electronic, hip-hop, remixes.
     * Between them a search for a modern artist returns something recognisable far
     * more often than either does alone.
     *
     * One request returns fully described tracks, so unlike archive.org there is no
     * per-item follow-up.
     */
    private static void audius(String query, List<Track> out) throws Exception {
        String url = AUDIUS + "/v1/tracks/search?query=" + enc(query)
                + "&app_name=" + APP + "&limit=" + AUDIUS_LIMIT;

        JsonObject root = fetchJson(url);
        JsonArray data = root.getAsJsonArray("data");
        if (data == null) return;

        for (int i = 0; i < data.size(); i++) {
            JsonElement el = data.get(i);
            if (!el.isJsonObject()) continue;
            JsonObject t = el.getAsJsonObject();

            String id = str(t, "id");
            if (id == null) continue;

            // Gated tracks need a purchase or a follow to play; the stream endpoint
            // refuses them, so listing them would only produce rows that fail.
            if (bool(t, "is_stream_gated")) continue;

            String title = str(t, "title");
            if (title == null) continue;

            String artist = null;
            JsonObject user = obj(t, "user");
            if (user != null) {
                artist = str(user, "name");
                if (artist == null) artist = str(user, "handle");
            }

            long ms = 0L;
            JsonElement dur = t.get("duration");        // whole seconds here
            if (dur != null && dur.isJsonPrimitive()) {
                try { ms = (long) (dur.getAsDouble() * 1000); } catch (Throwable ignored) { }
            }

            // Smallest square on offer: these are drawn at 16 pixels in a list.
            String art = null;
            JsonObject artwork = obj(t, "artwork");
            if (artwork != null) {
                art = str(artwork, "150x150");
                if (art == null) art = str(artwork, "480x480");
            }

            String stream = AUDIUS + "/v1/tracks/" + enc(id) + "/stream?app_name=" + APP;
            out.add(Track.remote(stream, "audius", title, artist, "", ms, art));
        }
    }

    /**
     * Searches ccMixter, a Creative Commons music community.
     *
     * Pulls its weight because its uploads are whole finished songs with proper
     * credits and durations, which balances out how remix-heavy the other
     * open catalogs are.
     */
    private static void ccmixter(String query, List<Track> out) throws Exception {
        String url = CCMIXTER + "/api/query?f=json&limit=" + CCMIXTER_LIMIT
                + "&search=" + enc(query);

        JsonArray uploads = fetchJsonArray(url);
        for (int i = 0; i < uploads.size(); i++) {
            JsonElement el = uploads.get(i);
            if (!el.isJsonObject()) continue;
            JsonObject upload = el.getAsJsonObject();

            String title = str(upload, "upload_name");
            String artist = str(upload, "user_real_name");
            if (artist == null) artist = str(upload, "user_name");

            JsonArray files = upload.getAsJsonArray("files");
            if (files == null || title == null) continue;

            // One entry per upload: the files are usually the same song in
            // several formats, and listing each would just repeat the track.
            for (int f = 0; f < files.size(); f++) {
                if (!files.get(f).isJsonObject()) continue;
                JsonObject file = files.get(f).getAsJsonObject();

                String link = str(file, "download_url");
                if (link == null) continue;

                JsonObject info = obj(file, "file_format_info");
                String mime = info == null ? null : str(info, "mime_type");
                boolean playable = "audio/mpeg".equals(mime)
                        || link.toLowerCase().endsWith(".mp3");
                if (!playable) continue;

                long ms = info == null ? 0L : seconds(str(info, "ps"));
                out.add(Track.remote(link, "ccmixter", title, artist, "", ms));
                break;
            }
        }
    }

    /**
     * Searches radio-browser, a community index of live internet radio.
     *
     * The one place in here that carries current chart music, because a station
     * is licensed to broadcast what an on-demand API cannot hand out. The trade is
     * that a station is a continuous stream: no duration, no seeking, and you join
     * wherever it happens to be.
     */
    private static void radio(String query, List<Track> out) throws Exception {
        // By name, then by tag. Name finds a station devoted to one artist; tag
        // finds the genre stations that carry current chart music, which is what a
        // search like "hip hop" is really after. Neither alone covers both.
        radioQuery("name=" + enc(query), out);
        radioQuery("tag=" + enc(query), out);
    }

    private static void radioQuery(String selector, List<Track> out) throws Exception {
        String url = RADIO + "/json/stations/search?" + selector
                + "&limit=" + RADIO_LIMIT
                + "&hidebroken=true&order=votes&reverse=true";

        JsonArray stations = fetchJsonArray(url);
        for (int i = 0; i < stations.size(); i++) {
            JsonElement el = stations.get(i);
            if (!el.isJsonObject()) continue;
            JsonObject s = el.getAsJsonObject();

            // Only mp3: there is no AAC decoder on the classpath, so an AAC
            // station would list fine and then fail the moment it was clicked.
            String codec = str(s, "codec");
            if (codec == null || !codec.toUpperCase().contains("MP3")) continue;

            String link = str(s, "url_resolved");
            if (link == null) link = str(s, "url");
            String name = str(s, "name");
            if (link == null || name == null) continue;

            // Says what it is in the column the browser already shows.
            String where = str(s, "country");
            String label = where == null ? "Live radio" : "Live radio - " + where;

            // Stations publish a logo; it stands in nicely for cover art.
            out.add(Track.remote(link.trim(), "radio", name.trim(), label, "", 0L,
                                 str(s, "favicon")));
        }
    }

    /**
     * Searches Openverse, which indexes several openly licensed collections at
     * once -- Jamendo among them.
     *
     * One request reaches catalogs that would each need their own key, which is
     * why it is worth having despite a tight anonymous allowance: 20 requests a
     * minute and 200 a day per address. When that runs out it simply fails and the
     * other sources carry the search, so it costs nothing to keep trying.
     */
    private static void openverse(String query, List<Track> out) throws Exception {
        String url = OPENVERSE + "/v1/audio/?q=" + enc(query)
                + "&page_size=" + OPENVERSE_LIMIT;

        JsonObject root = fetchJson(url);
        JsonArray results = root.getAsJsonArray("results");
        if (results == null) return;

        for (int i = 0; i < results.size(); i++) {
            JsonElement el = results.get(i);
            if (!el.isJsonObject()) continue;
            JsonObject r = el.getAsJsonObject();

            String link = str(r, "url");
            String title = str(r, "title");
            if (link == null || title == null) continue;

            String artist = str(r, "creator");

            long ms = 0L;
            JsonElement dur = r.get("duration");        // already milliseconds
            if (dur != null && dur.isJsonPrimitive()) {
                try { ms = dur.getAsLong(); } catch (Throwable ignored) { }
            }

            String provider = str(r, "provider");
            out.add(Track.remote(link, provider == null ? "openverse" : provider,
                                 title, artist, "", ms, str(r, "thumbnail")));
        }
    }

    private static boolean bool(JsonObject o, String key) {
        JsonElement e = o.get(key);
        try {
            return e != null && e.isJsonPrimitive() && e.getAsBoolean();
        } catch (Throwable t) {
            return false;
        }
    }

    /**
     * Orders results so the obvious answer is at the top.
     *
     * Archive items are ranked by downloads, which favours big compilation uploads:
     * searching an artist otherwise returns twenty tracks from one three-hour
     * "relaxing piano" mix before the actual recording by that artist. Scoring each
     * track against what was typed puts real matches first, and a stable sort keeps
     * the catalog's own ordering within each score band.
     */
    private static List<Track> rank(List<Track> found, String query) {
        final String[] tokens = SearchMatch.tokenize(query);

        // Drop repeats first. Archive items list the same recording under several
        // files, and searching radio by name and by tag returns overlapping
        // stations, so without this the list is padded with duplicates.
        List<Track> copy = new ArrayList<Track>(found.size());
        java.util.HashSet<String> seen = new java.util.HashSet<String>();
        for (int i = 0; i < found.size(); i++) {
            Track t = found.get(i);
            String fingerprint = (t.artist + " " + t.title).toLowerCase();
            if (seen.add(t.key()) && seen.add(fingerprint)) copy.add(t);
        }

        java.util.Collections.sort(copy, new java.util.Comparator<Track>() {
            @Override public int compare(Track a, Track b) {
                return score(b) - score(a);
            }
            private int score(Track t) {
                // Word-by-word relevance, so an artist and a song title typed
                // together both count and a typo still lands.
                int s = SearchMatch.score(tokens, t.title, t.artist, t.album);

                // Someone searching an artist wants that artist's songs. Open
                // catalogs are dominated by other people's reworkings of them, so
                // without this the whole first page is remixes and bootlegs.
                if (isDerivative(t.title.toLowerCase())) s -= 7;

                // Hour-long compilations are rarely what someone picked a name to hear.
                if (t.durationMs > 20L * 60_000L) s -= 3;
                // Nor are fragments; a real song is not eleven seconds long.
                if (t.durationMs > 0 && t.durationMs < 60L * 1000L) s -= 2;

                // Stations sit just below songs. Someone typing a song name wants
                // the song; someone browsing for something to put on will still
                // find them a short scroll down.
                if ("radio".equals(t.source)) s -= 2;
                return s;
            }
        });
        return copy;
    }

    /** Titles that mark someone else's rework rather than the recording itself. */
    private static final String[] DERIVATIVE_MARKERS = {
        "remix", "bootleg", "mashup", "mash up", "flip", "rework", "edit",
        "cover", "tribute", "karaoke", "instrumental", "acapella", "a capella",
        "dj set", "mixtape", "megamix", "vip mix", "refix"
    };

    private static boolean isDerivative(String lowercaseTitle) {
        for (String marker : DERIVATIVE_MARKERS) {
            if (lowercaseTitle.contains(marker)) return true;
        }
        // archive.org truncates long titles, so "(Bamboo Forest Remix)" arrives as
        // "(Bamboo Forest Rem" and matches none of the markers above.
        return lowercaseTitle.endsWith(" rem") || lowercaseTitle.endsWith(" remi");
    }

    /** Durations come as either "209.13" seconds or "3:29". */
    private static long seconds(String s) {
        if (s == null) return 0L;
        try {
            if (s.indexOf(':') >= 0) {
                String[] parts = s.split(":");
                double total = 0;
                for (String p : parts) total = total * 60 + Double.parseDouble(p.trim());
                return (long) (total * 1000);
            }
            return (long) (Double.parseDouble(s.trim()) * 1000);
        } catch (Throwable t) {
            return 0L;
        }
    }

    /** A filename made readable, for the many files that carry no title tag. */
    private static String prettify(String name) {
        int dot = name.lastIndexOf('.');
        String base = dot > 0 ? name.substring(0, dot) : name;
        base = base.replace('_', ' ').replace("--", " - ");
        return base.trim();
    }

    private static JsonObject fetchJson(String url) throws Exception {
        JsonElement parsed = fetchElement(url);
        if (!parsed.isJsonObject()) throw new IllegalStateException("unexpected response");
        return parsed.getAsJsonObject();
    }

    /** Some of these APIs answer with a bare array rather than an object. */
    private static JsonArray fetchJsonArray(String url) throws Exception {
        JsonElement parsed = fetchElement(url);
        if (!parsed.isJsonArray()) throw new IllegalStateException("unexpected response");
        return parsed.getAsJsonArray();
    }

    private static JsonElement fetchElement(String url) throws Exception {
        HttpURLConnection c = (HttpURLConnection) new URL(url).openConnection();
        c.setConnectTimeout(10000);
        c.setReadTimeout(15000);
        c.setInstanceFollowRedirects(true);
        c.setRequestProperty("User-Agent", AGENT);
        c.setRequestProperty("Accept", "application/json");
        try {
            int status = c.getResponseCode();
            if (status / 100 != 2) throw new IllegalStateException("HTTP " + status);

            BufferedReader r = new BufferedReader(
                    new InputStreamReader(c.getInputStream(), "UTF-8"));
            StringBuilder sb = new StringBuilder();
            char[] buf = new char[8192];
            int n;
            while ((n = r.read(buf)) > 0) sb.append(buf, 0, n);
            r.close();

            return new JsonParser().parse(sb.toString());
        } finally {
            c.disconnect();
        }
    }

    private static JsonObject obj(JsonObject o, String key) {
        JsonElement e = o.get(key);
        return e != null && e.isJsonObject() ? e.getAsJsonObject() : null;
    }

    private static String str(JsonObject o, String key) {
        JsonElement e = o.get(key);
        if (e == null || e.isJsonNull() || !e.isJsonPrimitive()) return null;
        String s = e.getAsString().trim();
        return s.isEmpty() ? null : s;
    }

    /** "creator" is sometimes a string and sometimes an array of them. */
    private static String firstString(JsonObject o, String key) {
        JsonElement e = o.get(key);
        if (e == null || e.isJsonNull()) return null;
        if (e.isJsonArray()) {
            JsonArray a = e.getAsJsonArray();
            if (a.size() == 0) return null;
            JsonElement first = a.get(0);
            return first.isJsonPrimitive() ? first.getAsString().trim() : null;
        }
        return e.isJsonPrimitive() ? e.getAsString().trim() : null;
    }

    private static String enc(String s) throws Exception {
        return URLEncoder.encode(s, "UTF-8").replace("+", "%20");
    }

    /** Path segments keep their slashes; only the unsafe characters are escaped. */
    private static String encPath(String s) throws Exception {
        StringBuilder sb = new StringBuilder();
        for (String part : s.split("/", -1)) {
            if (sb.length() > 0) sb.append('/');
            sb.append(enc(part));
        }
        return sb.toString();
    }
}
