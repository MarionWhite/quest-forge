package com.questforge.content.pack;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.charset.Charset;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * A short hash of the pack's ID-bearing configs: what a client and a server must
 * agree on before they can share a world.
 *
 * Potion, enchantment, biome, entity and dimension IDs live in mod configs, and
 * FML's handshake never compares configs. A client with last month's witchery.cfg
 * joins fine and then reads every TragicMC potion the server sends as a Witchery
 * one. The file list is {@code qfcontent-packcheck.txt}, shipped in this jar so
 * both sides read the same one.
 *
 * Only ID entries count, not whole files. Comments, layout, CRLF vs LF, key order
 * and every non-ID setting are ignored, and so is any section with "client" in
 * its name, so a friend's tweaked HUD option or a file a mod reflowed on save
 * never refuses anyone. The bytes are read as Latin-1 (one byte, one char), so no
 * charset decoder on any OS can disagree about a malformed byte.
 *
 * KEEP IN STEP WITH tools/pack_fingerprint.py, which computes the same value from
 * pack/config without booting the game. {@code /qfpack} prints this side's value;
 * the script's output on the same folder must be identical.
 */
public final class PackFingerprint {

    /** Bumped whenever the algorithm changes, so old and new can never collide. */
    static final String VERSION_TAG = "qfpack-1";

    private static final Charset LATIN1 = Charset.forName("ISO-8859-1");

    private static final Pattern NEWLINE = Pattern.compile("\r\n|\r|\n");
    private static final Pattern ENTRY =
            Pattern.compile("^(?:[A-Za-z]:)?(?:\"([^\"]*)\"|([^=]+?))\\s*=(.*)$");
    private static final Pattern COLON = Pattern.compile("^([^:=]+):([A-Za-z]):(.*)$");
    private static final Pattern INT = Pattern.compile("^-?\\d+$");
    private static final Pattern ID_TOKEN = Pattern.compile(
            "(?<![A-Za-z])[Ii][Dd][Ss]?(?![a-z])|(?<=[a-z0-9])(?:ID|Id)[Ss]?(?![a-z])");
    private static final Pattern KIND = Pattern.compile(
            "(?i)potion|biome|enchant|dimension|villager|profession|provider");

    /** The outcome for one config folder. */
    public static final class Result {
        /** 12 hex characters. */
        public final String fingerprint;
        /** Config path (relative, forward slashes) to a 16-hex digest or "missing". */
        public final Map<String, String> digests;

        Result(String fingerprint, Map<String, String> digests) {
            this.fingerprint = fingerprint;
            this.digests = digests;
        }
    }

    private PackFingerprint() {}

    public static Result compute(File configDir) {
        Map<String, String> digests = new LinkedHashMap<String, String>();
        StringBuilder body = new StringBuilder(VERSION_TAG).append('\n');
        for (String rel : fileList()) {
            String digest = fileDigest(new File(configDir, rel.replace('/', File.separatorChar)));
            digests.put(rel, digest);
            body.append(rel).append('\t').append(digest).append('\n');
        }
        return new Result(sha256(body.toString()).substring(0, 12), digests);
    }

    /** The fingerprinted configs, in list order. Lines starting with '-' are reviewed-out. */
    public static List<String> fileList() {
        List<String> files = new ArrayList<String>();
        InputStream in = PackFingerprint.class.getResourceAsStream("/qfcontent-packcheck.txt");
        if (in == null) return files;
        try {
            BufferedReader r = new BufferedReader(new InputStreamReader(in, "UTF-8"));
            String line;
            while ((line = r.readLine()) != null) {
                String t = line.trim();
                if (t.isEmpty() || t.startsWith("#") || t.startsWith("-")) continue;
                files.add(t);
            }
            r.close();
        } catch (IOException e) {
            // An unreadable list hashes as an empty one; both sides would see it.
        }
        return files;
    }

    static String fileDigest(File f) {
        if (!f.isFile()) return "missing";
        byte[] raw;
        try {
            raw = readAll(f);
        } catch (IOException e) {
            return "unreadable";
        }
        StringBuilder canon = new StringBuilder();
        for (String e : entries(raw)) canon.append(e).append('\n');
        return sha256(canon.toString()).substring(0, 16);
    }

    /** The ID-bearing entries of one config file, as "section/path|key=value", sorted. */
    public static List<String> entries(byte[] raw) {
        String text = new String(raw, LATIN1);
        if (text.startsWith("ï»¿")) text = text.substring(3); // UTF-8 BOM
        List<String> out = new ArrayList<String>();
        List<String> stack = new ArrayList<String>();
        boolean inList = false;
        for (String line : NEWLINE.split(text)) {
            String t = line.trim();
            if (inList) {
                if (t.endsWith(">")) inList = false;
                continue;
            }
            if (t.isEmpty() || t.startsWith("#") || t.startsWith("//")) continue;
            if (t.endsWith("<")) {          // S:list < ... >: lists never hold IDs here
                inList = true;
                continue;
            }
            if (t.equals("}")) {
                if (!stack.isEmpty()) stack.remove(stack.size() - 1);
                continue;
            }
            if (t.endsWith("{") && t.indexOf('=') < 0) {
                String name = t.substring(0, t.length() - 1).trim();
                if (name.length() >= 2 && name.charAt(0) == '"' && name.charAt(name.length() - 1) == '"') {
                    name = name.substring(1, name.length() - 1);
                }
                stack.add(name);
                continue;
            }
            String key;
            String value;
            Matcher m = ENTRY.matcher(t);
            if (m.matches()) {
                key = m.group(1) != null ? m.group(1) : m.group(2);
                value = m.group(3);
            } else {
                m = COLON.matcher(t);
                if (!m.matches()) continue;
                key = m.group(1);
                value = m.group(3);
            }
            key = key.trim();
            value = value.trim();
            if (!INT.matcher(value).matches()) continue;
            String path = join(stack);
            if (path.toLowerCase(Locale.ROOT).contains("client")) continue;
            if (ID_TOKEN.matcher(key).find() || KIND.matcher(key).find() || KIND.matcher(path).find()) {
                out.add(path + "|" + key + "=" + value);
            }
        }
        Collections.sort(out);
        return out;
    }

    /** sha256 of "id=version\n" for each mod, sorted: a one-glance check of a mod list. */
    public static String modsDigest(Map<String, String> mods) {
        List<String> lines = new ArrayList<String>();
        for (Map.Entry<String, String> e : mods.entrySet()) lines.add(e.getKey() + "=" + e.getValue());
        Collections.sort(lines);
        StringBuilder b = new StringBuilder();
        for (String l : lines) b.append(l).append('\n');
        return sha256(b.toString()).substring(0, 12);
    }

    private static String join(List<String> parts) {
        StringBuilder b = new StringBuilder();
        for (int i = 0; i < parts.size(); i++) {
            if (i > 0) b.append('/');
            b.append(parts.get(i));
        }
        return b.toString();
    }

    private static byte[] readAll(File f) throws IOException {
        FileInputStream in = new FileInputStream(f);
        try {
            byte[] buf = new byte[(int) f.length()];
            int off = 0;
            while (off < buf.length) {
                int n = in.read(buf, off, buf.length - off);
                if (n < 0) break;
                off += n;
            }
            if (off == buf.length) return buf;
            byte[] cut = new byte[off];
            System.arraycopy(buf, 0, cut, 0, off);
            return cut;
        } finally {
            in.close();
        }
    }

    static String sha256(String s) {
        try {
            byte[] d = MessageDigest.getInstance("SHA-256").digest(s.getBytes(LATIN1));
            StringBuilder hex = new StringBuilder();
            for (byte b : d) hex.append(String.format("%02x", b & 0xff));
            return hex.toString();
        } catch (Exception e) {
            throw new RuntimeException(e);
        }
    }
}
