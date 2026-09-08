import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpHandler;
import com.sun.net.httpserver.HttpServer;

import javax.net.ssl.SSLSocket;
import javax.net.ssl.SSLSocketFactory;
import javax.net.ssl.SSLSession;
import javax.net.ssl.HttpsURLConnection;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.InetAddress;
import java.net.InetSocketAddress;
import java.net.URL;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.attribute.PosixFilePermission;
import java.nio.file.attribute.PosixFilePermissions;
import java.security.MessageDigest;
import java.security.SecureRandom;
import java.security.cert.X509Certificate;
import java.util.ArrayList;
import java.util.Base64;
import java.util.Collections;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Properties;
import java.util.Set;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.TimeUnit;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * De-risking spike for the QuestForge Spotify jukebox mod.
 *
 * Answers three questions, in order, before any mod code gets written:
 *   1. Can the pack's JVM (Oracle 8u162, Jan 2018) even open a TLS connection to
 *      Spotify? TLS 1.2 only became the client default in 8u161, and that JVM's
 *      cacerts trust store is eight years stale.
 *   2. Does the OAuth browser handoff work from macOS without touching AWT?
 *   3. Do the player endpoints actually respond -- devices, play, volume?
 *
 * Deliberately zero-dependency: everything here is JDK 8 stdlib, so it compiles
 * and runs under the exact JVM the pack uses. JSON is scraped with regex, which
 * is fine for a spike and gets replaced by Gson (already on the 1.7.10 classpath)
 * in the real mod.
 *
 *   javac SpotifySpike.java && java SpotifySpike [tls|auth|play|all]
 */
public class SpotifySpike {

    private static final String REDIRECT_URI = "http://127.0.0.1:8888/callback";
    private static final int    CALLBACK_PORT = 8888;
    private static final String SCOPES = "user-read-playback-state user-modify-playback-state";

    private static final Path CONF_DIR = Paths.get(System.getProperty("user.home"), ".config", "qf-spotify");
    private static final Path TOKENS   = CONF_DIR.resolve("tokens.properties");
    private static final Path CLIENT   = CONF_DIR.resolve("client_id");

    /** What stage 3 searches for to get something real to play. Override with argv[1]. */
    private static String query = "year:2020";

    public static void main(String[] args) {
        String stage = args.length > 0 ? args[0] : "all";
        if (args.length > 1) query = args[1];
        banner();
        try {
            boolean tlsOk = stageTls();
            if ("tls".equals(stage)) { verdict(tlsOk); return; }
            if (!tlsOk) {
                System.out.println();
                System.out.println("STOPPING: TLS failed, so nothing above this layer can work.");
                System.out.println("See the remediation notes printed above.");
                verdict(false);
                return;
            }

            String token = stageAuth();
            if (token == null) { verdict(false); return; }
            if ("auth".equals(stage)) { verdict(true); return; }

            boolean playOk = stagePlay(token);
            verdict(playOk);
        } catch (Exception e) {
            System.out.println();
            System.out.println("!! UNCAUGHT: " + e.getClass().getName() + ": " + e.getMessage());
            e.printStackTrace(System.out);
            verdict(false);
        }
    }

    private static void banner() {
        System.out.println("======================================================================");
        System.out.println(" QuestForge Spotify jukebox -- feasibility spike");
        System.out.println("======================================================================");
        System.out.println("  java.version : " + System.getProperty("java.version"));
        System.out.println("  java.vendor  : " + System.getProperty("java.vendor"));
        System.out.println("  os.arch      : " + System.getProperty("os.arch"));
        System.out.println("  java.home    : " + System.getProperty("java.home"));
        System.out.println();
    }

    private static void verdict(boolean ok) {
        System.out.println();
        System.out.println("======================================================================");
        System.out.println(ok ? " SPIKE PASSED" : " SPIKE FAILED");
        System.out.println("======================================================================");
        if (!ok) System.exit(1);
    }

    // ------------------------------------------------------------------
    // Stage 1 -- TLS reachability from this exact JVM
    // ------------------------------------------------------------------

    private static boolean stageTls() {
        System.out.println("[1/3] TLS handshake against Spotify hosts");
        System.out.println("----------------------------------------------------------------------");

        boolean all = true;
        all &= probe("accounts.spotify.com");
        all &= probe("api.spotify.com");

        if (all) {
            // A real HTTPS request, not just a handshake -- proves the URLConnection
            // stack (not only raw sockets) trusts the chain. 401 is the expected
            // answer from an unauthenticated /me and counts as success.
            try {
                Response r = request("GET", "https://api.spotify.com/v1/me", null, null, null);
                System.out.println("  HTTPS GET /v1/me -> HTTP " + r.status + "  (401 expected, means the stack works)");
                if (r.status != 401 && r.status != 403) {
                    System.out.println("  ?? unexpected status; body: " + trim(r.body, 200));
                }
            } catch (Exception e) {
                System.out.println("  !! HttpsURLConnection failed even though the raw handshake worked:");
                System.out.println("     " + e.getClass().getSimpleName() + ": " + e.getMessage());
                all = false;
            }
        }

        if (!all) {
            System.out.println();
            System.out.println("  REMEDIATION, in order of preference:");
            System.out.println("   a) Add to the pack's JVM args:  -Dhttps.protocols=TLSv1.2 "
                             + "-Djdk.tls.client.protocols=TLSv1.2");
            System.out.println("   b) If it is a trust failure (SunCertPathBuilderException), copy a modern");
            System.out.println("      cacerts over 8u162's:");
            System.out.println("        cp /Library/Java/JavaVirtualMachines/zulu-8.jdk/Contents/Home/jre/lib/security/cacerts \\");
            System.out.println("           <8u162>/jre/lib/security/cacerts");
            System.out.println("   c) Ship our own truststore in the mod and point an SSLContext at it,");
            System.out.println("      so the user's JVM is left untouched. Most work, most robust.");
        }
        System.out.println();
        return all;
    }

    private static boolean probe(String host) {
        System.out.println("  " + host);
        SSLSocketFactory f = (SSLSocketFactory) SSLSocketFactory.getDefault();
        SSLSocket s = null;
        try {
            s = (SSLSocket) f.createSocket();
            s.connect(new InetSocketAddress(host, 443), 10000);
            s.setSoTimeout(10000);
            System.out.println("    enabled  : " + String.join(", ", s.getEnabledProtocols()));
            s.startHandshake();

            SSLSession sess = s.getSession();
            System.out.println("    negotiated: " + sess.getProtocol() + " / " + sess.getCipherSuite());

            java.security.cert.Certificate[] chain = sess.getPeerCertificates();
            X509Certificate leaf = (X509Certificate) chain[0];
            X509Certificate top  = (X509Certificate) chain[chain.length - 1];
            System.out.println("    leaf     : " + shortDn(leaf.getSubjectX500Principal().getName()));
            System.out.println("    anchor   : " + shortDn(top.getIssuerX500Principal().getName())
                             + "   (this root must be in cacerts)");
            System.out.println("    OK");
            return true;
        } catch (Exception e) {
            System.out.println("    !! FAILED: " + e.getClass().getSimpleName() + ": " + e.getMessage());
            Throwable c = e.getCause();
            while (c != null) {
                System.out.println("       caused by: " + c.getClass().getSimpleName() + ": " + c.getMessage());
                c = c.getCause();
            }
            return false;
        } finally {
            if (s != null) try { s.close(); } catch (IOException ignored) { }
        }
    }

    private static String shortDn(String dn) {
        Matcher m = Pattern.compile("CN=([^,]+)").matcher(dn);
        if (m.find()) return m.group(1);
        m = Pattern.compile("O=([^,]+)").matcher(dn);
        return m.find() ? m.group(1) : dn;
    }

    // ------------------------------------------------------------------
    // Stage 2 -- PKCE OAuth with a loopback listener
    // ------------------------------------------------------------------

    private static String stageAuth() throws Exception {
        System.out.println("[2/3] OAuth (PKCE, no client secret)");
        System.out.println("----------------------------------------------------------------------");

        String clientId = clientId();
        if (clientId == null) return null;
        System.out.println("  client_id : " + clientId.substring(0, Math.min(8, clientId.length())) + "...");

        String refresh = loadProp("refresh_token");
        if (refresh != null) {
            System.out.println("  cached refresh_token found -- skipping the browser");
            String tok = refreshToken(clientId, refresh);
            if (tok != null) { System.out.println("  refreshed OK"); System.out.println(); return tok; }
            System.out.println("  refresh failed, falling back to a full browser login");
        }

        // PKCE: verifier is a high-entropy random string, challenge is its SHA-256.
        // Only the challenge crosses the network on the way out, so intercepting
        // the redirect is not enough to steal the code exchange.
        String verifier  = b64url(random(64));
        String challenge = b64url(MessageDigest.getInstance("SHA-256")
                                  .digest(verifier.getBytes(StandardCharsets.US_ASCII)));
        String state     = b64url(random(16));

        CompletableFuture<Map<String, String>> callback = new CompletableFuture<>();
        HttpServer server = HttpServer.create(
                new InetSocketAddress(InetAddress.getByName("127.0.0.1"), CALLBACK_PORT), 0);
        server.createContext("/callback", new CallbackHandler(callback));
        server.setExecutor(null);
        server.start();
        System.out.println("  listening on " + REDIRECT_URI);

        String authUrl = "https://accounts.spotify.com/authorize"
                + "?client_id="            + enc(clientId)
                + "&response_type=code"
                + "&redirect_uri="         + enc(REDIRECT_URI)
                + "&code_challenge_method=S256"
                + "&code_challenge="       + enc(challenge)
                + "&state="                + enc(state)
                + "&scope="                + enc(SCOPES);

        // macOS `open` rather than java.awt.Desktop -- AWT from inside the LWJGL2
        // game process on a Mac is exactly the kind of thing that deadlocks, and
        // this same call has to work from the mod later.
        System.out.println("  opening browser...");
        boolean opened = false;
        try {
            Process p = Runtime.getRuntime().exec(new String[] { "open", authUrl });
            opened = p.waitFor(10, TimeUnit.SECONDS) && p.exitValue() == 0;
        } catch (Exception e) {
            System.out.println("  `open` failed: " + e.getMessage());
        }
        if (!opened) {
            System.out.println("  !! could not launch a browser. Paste this URL manually:");
            System.out.println();
            System.out.println("  " + authUrl);
            System.out.println();
        }

        Map<String, String> params;
        try {
            System.out.println("  waiting for the redirect (2 min timeout)...");
            params = callback.get(120, TimeUnit.SECONDS);
        } catch (Exception e) {
            System.out.println("  !! no callback received: " + e.getClass().getSimpleName());
            return null;
        } finally {
            server.stop(0);
        }

        if (params.containsKey("error")) {
            System.out.println("  !! Spotify returned error=" + params.get("error"));
            return null;
        }
        if (!state.equals(params.get("state"))) {
            System.out.println("  !! state mismatch -- possible CSRF, aborting");
            return null;
        }
        String code = params.get("code");
        System.out.println("  got authorization code");

        Map<String, String> form = new LinkedHashMap<>();
        form.put("grant_type",    "authorization_code");
        form.put("code",          code);
        form.put("redirect_uri",  REDIRECT_URI);
        form.put("client_id",     clientId);
        form.put("code_verifier", verifier);

        Response r = request("POST", "https://accounts.spotify.com/api/token",
                             null, "application/x-www-form-urlencoded", formBody(form));
        if (r.status != 200) {
            System.out.println("  !! token exchange -> HTTP " + r.status + ": " + trim(r.body, 400));
            return null;
        }

        String access  = json(r.body, "access_token");
        String refresh2 = json(r.body, "refresh_token");
        System.out.println("  token exchange OK, expires_in=" + json(r.body, "expires_in") + "s");
        System.out.println("  granted scopes: " + json(r.body, "scope"));

        if (refresh2 != null) saveProp("refresh_token", refresh2);
        System.out.println();
        return access;
    }

    private static String refreshToken(String clientId, String refresh) throws Exception {
        Map<String, String> form = new LinkedHashMap<>();
        form.put("grant_type",    "refresh_token");
        form.put("refresh_token", refresh);
        form.put("client_id",     clientId);
        Response r = request("POST", "https://accounts.spotify.com/api/token",
                             null, "application/x-www-form-urlencoded", formBody(form));
        if (r.status != 200) {
            System.out.println("  refresh -> HTTP " + r.status + ": " + trim(r.body, 200));
            return null;
        }
        // Spotify may or may not rotate the refresh token; keep the old one if not.
        String rotated = json(r.body, "refresh_token");
        if (rotated != null) saveProp("refresh_token", rotated);
        return json(r.body, "access_token");
    }

    private static final class CallbackHandler implements HttpHandler {
        private final CompletableFuture<Map<String, String>> future;
        CallbackHandler(CompletableFuture<Map<String, String>> f) { this.future = f; }

        @Override public void handle(HttpExchange x) throws IOException {
            Map<String, String> q = parseQuery(x.getRequestURI().getRawQuery());
            boolean ok = q.containsKey("code");
            String html = "<!doctype html><meta charset=utf-8>"
                    + "<title>QuestForge</title>"
                    + "<body style=\"font:16px -apple-system,sans-serif;text-align:center;padding:80px;"
                    + "background:#121212;color:#eee\">"
                    + "<h2 style=\"color:" + (ok ? "#1db954" : "#e22134") + "\">"
                    + (ok ? "Linked." : "Authorization failed.") + "</h2>"
                    + "<p>You can close this tab and go back to the terminal.</p>";
            byte[] out = html.getBytes(StandardCharsets.UTF_8);
            x.getResponseHeaders().add("Content-Type", "text/html; charset=utf-8");
            x.sendResponseHeaders(ok ? 200 : 400, out.length);
            try (OutputStream os = x.getResponseBody()) { os.write(out); }
            future.complete(q);
        }
    }

    // ------------------------------------------------------------------
    // Stage 3 -- the player endpoints that the jukebox will actually use
    // ------------------------------------------------------------------

    private static boolean stagePlay(String token) throws Exception {
        System.out.println("[3/3] Player endpoints");
        System.out.println("----------------------------------------------------------------------");

        Response dev = request("GET", "https://api.spotify.com/v1/me/player/devices", token, null, null);
        if (dev.status != 200) {
            System.out.println("  !! /me/player/devices -> HTTP " + dev.status + ": " + trim(dev.body, 300));
            return false;
        }

        List<String> devices = jsonObjects(dev.body, "devices");
        if (devices.isEmpty()) {
            System.out.println("  !! no devices visible.");
            System.out.println("     Open the Spotify desktop app and play something for a second so it");
            System.out.println("     registers as a Connect device, then re-run.");
            return false;
        }

        System.out.println("  devices:");
        String targetId = null, targetName = null;
        Integer originalVolume = null;
        for (String d : devices) {
            String id     = topField(d, "id");
            String name   = topField(d, "name");
            String type   = topField(d, "type");
            boolean act   = "true".equals(topField(d, "is_active"));
            String vol    = topField(d, "volume_percent");
            System.out.println("    " + (act ? "* " : "  ") + name + "  [" + type + "]"
                             + (vol != null && !"null".equals(vol) ? "  vol=" + vol + "%" : ""));
            // Prefer whichever device is already active; otherwise take the first.
            if (targetId == null || act) {
                targetId = id;
                targetName = name;
                originalVolume = (vol != null && vol.matches("\\d+")) ? Integer.parseInt(vol) : null;
            }
        }
        System.out.println("  target: " + targetName);

        // Search needs no user scope, and guarantees we have something real to play
        // rather than depending on whatever happens to be queued.
        Response se = request("GET", "https://api.spotify.com/v1/search?q="
                + enc(query) + "&type=track&limit=1", token, null, null);
        String trackUri = null, trackName = null;
        if (se.status != 200) {
            System.out.println("  search -> HTTP " + se.status + ": " + trim(se.body, 200));
        } else {
            List<String> items = jsonObjects(se.body, "items");
            if (items.isEmpty()) {
                System.out.println("  search returned no tracks for \"" + query + "\"");
            } else {
                String item = items.get(0);
                trackUri  = topField(item, "uri");
                trackName = topField(item, "name");

                String artists = topField(item, "artists");
                if (artists != null) {
                    List<String> as = objectsIn(artists, 0);
                    if (!as.isEmpty()) trackName += " — " + topField(as.get(0), "name");
                }

                // The whole point of the last failure: never hand a non-track URI
                // to /me/player/play.
                if (trackUri != null && !trackUri.startsWith("spotify:track:")) {
                    System.out.println("  !! parsed a non-track uri (" + trackUri + "), ignoring it");
                    trackUri = null;
                }
            }
        }

        String body = trackUri != null
                ? "{\"uris\":[\"" + trackUri + "\"]}"
                : null;                                  // null body == plain resume
        System.out.println("  play -> " + (trackName != null ? trackName : "(resume current queue)"));

        Response play = request("PUT", "https://api.spotify.com/v1/me/player/play?device_id=" + enc(targetId),
                                token, "application/json", body == null ? null : body.getBytes(StandardCharsets.UTF_8));
        System.out.println("  PUT /me/player/play -> HTTP " + play.status
                         + (play.status == 204 ? "  (204 = success)" : ""));
        if (play.status == 403) {
            System.out.println("  !! 403 usually means the account is not Premium, or the device");
            System.out.println("     refused the command. Body: " + trim(play.body, 300));
            return false;
        }
        if (play.status != 204 && play.status != 202) {
            System.out.println("  !! " + trim(play.body, 300));
            return false;
        }

        Thread.sleep(1500);
        Response now = request("GET", "https://api.spotify.com/v1/me/player/currently-playing", token, null, null);
        if (now.status == 200) {
            // The track sits under "item"; reading "name" off the envelope would
            // pick up a nested album/artist name instead.
            String item = topField(now.body, "item");
            String name = item == null ? null : topField(item, "name");
            System.out.println("  now playing: " + (name == null ? "(unknown)" : name)
                             + "   is_playing=" + topField(now.body, "is_playing"));
        } else if (now.status == 204) {
            System.out.println("  currently-playing -> 204 (nothing playing)");
        } else {
            System.out.println("  currently-playing -> HTTP " + now.status);
        }

        // The volume endpoint is what makes proximity fade possible. If this 403s,
        // the walk-away-and-it-fades feature is dead and the design changes.
        System.out.println();
        System.out.println("  volume control (proximity-fade feasibility):");
        Response v1 = request("PUT", "https://api.spotify.com/v1/me/player/volume?volume_percent=40&device_id="
                              + enc(targetId), token, null, null);
        System.out.println("    set 40%  -> HTTP " + v1.status);
        boolean volumeOk = v1.status == 204;
        if (!volumeOk) System.out.println("    !! " + trim(v1.body, 300));
        if (originalVolume != null && volumeOk) {
            Thread.sleep(1200);
            Response v2 = request("PUT", "https://api.spotify.com/v1/me/player/volume?volume_percent="
                    + originalVolume + "&device_id=" + enc(targetId), token, null, null);
            System.out.println("    restored " + originalVolume + "% -> HTTP " + v2.status);
        }

        Response pause = request("PUT", "https://api.spotify.com/v1/me/player/pause?device_id=" + enc(targetId),
                                 token, null, null);
        System.out.println("  PUT /me/player/pause -> HTTP " + pause.status);

        System.out.println();
        System.out.println("  SUMMARY");
        System.out.println("    devices listed  : yes (" + devices.size() + ")");
        System.out.println("    playback start  : yes");
        System.out.println("    volume control  : " + (volumeOk ? "yes -- proximity fade is viable"
                                                                : "NO -- drop the proximity-fade feature"));
        return true;
    }

    // ------------------------------------------------------------------
    // HTTP
    // ------------------------------------------------------------------

    private static final class Response {
        final int status; final String body;
        Response(int s, String b) { status = s; body = b; }
    }

    private static Response request(String method, String url, String bearer,
                                    String contentType, byte[] body) throws IOException {
        HttpURLConnection c = (HttpURLConnection) new URL(url).openConnection();
        if (c instanceof HttpsURLConnection) {
            // Nothing to configure yet, but this is where a bundled truststore
            // would get attached if stage 1 shows we need one.
        }
        c.setRequestMethod(method);
        c.setConnectTimeout(10000);
        c.setReadTimeout(15000);
        c.setInstanceFollowRedirects(false);
        c.setRequestProperty("Accept", "application/json");
        c.setRequestProperty("User-Agent", "QuestForgeJukebox/spike");
        if (bearer != null)      c.setRequestProperty("Authorization", "Bearer " + bearer);
        if (contentType != null) c.setRequestProperty("Content-Type", contentType);

        if (body != null) {
            c.setDoOutput(true);
            c.setFixedLengthStreamingMode(body.length);
            try (OutputStream os = c.getOutputStream()) { os.write(body); }
        } else if ("PUT".equals(method) || "POST".equals(method)) {
            // Spotify's PUT endpoints are happy with an empty body, but the JDK
            // will not send Content-Length: 0 unless we ask for it.
            c.setDoOutput(true);
            c.setFixedLengthStreamingMode(0);
            try (OutputStream os = c.getOutputStream()) { os.write(new byte[0]); }
        }

        int status = c.getResponseCode();
        InputStream in = status >= 400 ? c.getErrorStream() : c.getInputStream();
        String text = in == null ? "" : readAll(in);
        c.disconnect();
        return new Response(status, text);
    }

    private static String readAll(InputStream in) throws IOException {
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        byte[] buf = new byte[8192];
        int n;
        while ((n = in.read(buf)) > 0) out.write(buf, 0, n);
        in.close();
        return new String(out.toByteArray(), StandardCharsets.UTF_8);
    }

    private static byte[] formBody(Map<String, String> form) {
        StringBuilder sb = new StringBuilder();
        for (Map.Entry<String, String> e : form.entrySet()) {
            if (sb.length() > 0) sb.append('&');
            sb.append(enc(e.getKey())).append('=').append(enc(e.getValue()));
        }
        return sb.toString().getBytes(StandardCharsets.UTF_8);
    }

    // ------------------------------------------------------------------
    // Tiny helpers -- regex JSON is spike-only, Gson replaces this in the mod
    // ------------------------------------------------------------------

    /** Extracts a string-valued field. */
    private static String json(String body, String key) {
        Matcher m = Pattern.compile("\"" + Pattern.quote(key) + "\"\\s*:\\s*\"((?:[^\"\\\\]|\\\\.)*)\"")
                           .matcher(body);
        return m.find() ? m.group(1).replace("\\/", "/") : null;
    }

    /**
     * Extracts a field that sits at the TOP level of one JSON object, ignoring
     * identically-named keys inside nested objects and arrays.
     *
     * This distinction is not academic: a Spotify track object embeds
     * album.artists[0] -- with its own "uri" and "name" -- before its own fields,
     * so a naive first-match regex hands back the artist and the play endpoint
     * rejects it with "Unsupported uri kind: artist".
     */
    private static String topField(String obj, String key) {
        int depth = 0, p = 0, n = obj.length();
        while (p < n) {
            char ch = obj.charAt(p);
            if (ch == '"') {
                int[] str = readString(obj, p);
                String name = unescape(obj.substring(p + 1, str[0]));
                p = str[1];
                if (depth != 1) continue;

                int q = skipWs(obj, p);
                if (q >= n || obj.charAt(q) != ':' || !name.equals(key)) continue;

                q = skipWs(obj, q + 1);
                if (q >= n) return null;
                if (obj.charAt(q) == '"') {
                    int[] val = readString(obj, q);
                    return unescape(obj.substring(q + 1, val[0]));
                }
                if (obj.charAt(q) == '{' || obj.charAt(q) == '[') {
                    int end = matchBracket(obj, q);
                    return end < 0 ? null : obj.substring(q, end + 1);
                }
                int e = q;
                while (e < n && "-+.eE0123456789truefalsnl".indexOf(obj.charAt(e)) >= 0) e++;
                return obj.substring(q, e).trim();
            }
            if (ch == '{' || ch == '[') depth++;
            else if (ch == '}' || ch == ']') depth--;
            p++;
        }
        return null;
    }

    /** Given index of an opening quote, returns {closingQuoteIndex, indexAfter}. */
    private static int[] readString(String s, int p) {
        boolean esc = false;
        for (int i = p + 1; i < s.length(); i++) {
            char c = s.charAt(i);
            if (esc) { esc = false; continue; }
            if (c == '\\') { esc = true; continue; }
            if (c == '"') return new int[] { i, i + 1 };
        }
        return new int[] { s.length(), s.length() };
    }

    /** Given index of '{' or '[', returns the index of its match, or -1. */
    private static int matchBracket(String s, int p) {
        int depth = 0;
        for (int i = p; i < s.length(); i++) {
            char c = s.charAt(i);
            if (c == '"') { i = readString(s, i)[0]; continue; }
            if (c == '{' || c == '[') depth++;
            else if (c == '}' || c == ']') { if (--depth == 0) return i; }
        }
        return -1;
    }

    private static int skipWs(String s, int p) {
        while (p < s.length() && Character.isWhitespace(s.charAt(p))) p++;
        return p;
    }

    private static String unescape(String s) {
        if (s.indexOf('\\') < 0) return s;
        StringBuilder sb = new StringBuilder(s.length());
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);
            if (c != '\\' || i + 1 >= s.length()) { sb.append(c); continue; }
            char e = s.charAt(++i);
            switch (e) {
                case 'n': sb.append('\n'); break;
                case 't': sb.append('\t'); break;
                case 'r': sb.append('\r'); break;
                case 'b': sb.append('\b'); break;
                case 'f': sb.append('\f'); break;
                case 'u':
                    if (i + 4 < s.length()) {
                        sb.append((char) Integer.parseInt(s.substring(i + 1, i + 5), 16));
                        i += 4;
                    }
                    break;
                default: sb.append(e);
            }
        }
        return sb.toString();
    }

    /** Splits the objects out of a named JSON array, respecting nesting and strings. */
    private static List<String> jsonObjects(String s, String arrayKey) {
        int i = s.indexOf("\"" + arrayKey + "\"");
        if (i < 0) return Collections.emptyList();
        i = s.indexOf('[', i);
        if (i < 0) return Collections.emptyList();
        return objectsIn(s, i);
    }

    /** Splits the objects out of a JSON array whose '[' is at index i. */
    private static List<String> objectsIn(String s, int i) {
        List<String> out = new ArrayList<>();
        int depth = 0, start = -1;
        boolean inStr = false, esc = false;
        for (int p = i; p < s.length(); p++) {
            char ch = s.charAt(p);
            if (inStr) {
                if (esc) esc = false;
                else if (ch == '\\') esc = true;
                else if (ch == '"') inStr = false;
                continue;
            }
            if (ch == '"') { inStr = true; continue; }
            if (ch == '{') { if (depth == 0) start = p; depth++; }
            else if (ch == '}') {
                depth--;
                if (depth == 0 && start >= 0) { out.add(s.substring(start, p + 1)); start = -1; }
            } else if (ch == ']' && depth == 0) break;
        }
        return out;
    }

    private static Map<String, String> parseQuery(String q) {
        Map<String, String> m = new HashMap<>();
        if (q == null) return m;
        for (String pair : q.split("&")) {
            int eq = pair.indexOf('=');
            if (eq < 0) continue;
            try {
                m.put(java.net.URLDecoder.decode(pair.substring(0, eq), "UTF-8"),
                      java.net.URLDecoder.decode(pair.substring(eq + 1), "UTF-8"));
            } catch (Exception ignored) { }
        }
        return m;
    }

    private static String enc(String s) {
        try { return URLEncoder.encode(s, "UTF-8"); }
        catch (Exception e) { throw new RuntimeException(e); }
    }

    private static byte[] random(int n) {
        byte[] b = new byte[n];
        new SecureRandom().nextBytes(b);
        return b;
    }

    private static String b64url(byte[] b) {
        return Base64.getUrlEncoder().withoutPadding().encodeToString(b);
    }

    private static String trim(String s, int n) {
        if (s == null) return "";
        s = s.replaceAll("\\s+", " ").trim();
        return s.length() <= n ? s : s.substring(0, n) + "...";
    }

    // ------------------------------------------------------------------
    // Config -- client id in, refresh token out
    // ------------------------------------------------------------------

    private static String clientId() throws IOException {
        String env = System.getenv("SPOTIFY_CLIENT_ID");
        if (env != null && !env.trim().isEmpty()) return env.trim();
        if (Files.exists(CLIENT)) {
            String s = new String(Files.readAllBytes(CLIENT), StandardCharsets.UTF_8).trim();
            if (!s.isEmpty()) return s;
        }
        System.out.println("  !! No client id.");
        System.out.println();
        System.out.println("  One-time setup:");
        System.out.println("    1. https://developer.spotify.com/dashboard -> Create app");
        System.out.println("    2. Redirect URI must be EXACTLY:  " + REDIRECT_URI);
        System.out.println("       (loopback IP only -- Spotify rejects http://localhost)");
        System.out.println("    3. Under APIs used, tick 'Web API'");
        System.out.println("    4. Copy the Client ID, then:");
        System.out.println("         mkdir -p " + CONF_DIR);
        System.out.println("         echo YOUR_CLIENT_ID > " + CLIENT);
        System.out.println();
        System.out.println("  No client secret needed -- PKCE does not use one, which is why the");
        System.out.println("  mod jar stays safe to hand to anyone.");
        return null;
    }

    private static String loadProp(String key) {
        if (!Files.exists(TOKENS)) return null;
        Properties p = new Properties();
        try (InputStream in = Files.newInputStream(TOKENS)) { p.load(in); }
        catch (IOException e) { return null; }
        return p.getProperty(key);
    }

    private static void saveProp(String key, String value) {
        try {
            Files.createDirectories(CONF_DIR);
            Properties p = new Properties();
            if (Files.exists(TOKENS)) {
                try (InputStream in = Files.newInputStream(TOKENS)) { p.load(in); }
            }
            p.setProperty(key, value);
            try (OutputStream out = Files.newOutputStream(TOKENS)) {
                p.store(out, "QuestForge Spotify -- refresh token. Treat as a credential.");
            }
            // A refresh token is a long-lived credential; do not leave it world-readable.
            Set<PosixFilePermission> perms = PosixFilePermissions.fromString("rw-------");
            Files.setPosixFilePermissions(TOKENS, perms);
        } catch (IOException e) {
            System.out.println("  (warning: could not persist token: " + e.getMessage() + ")");
        }
    }
}
