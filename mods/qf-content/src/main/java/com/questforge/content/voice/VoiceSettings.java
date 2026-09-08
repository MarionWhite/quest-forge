package com.questforge.content.voice;

import net.minecraft.client.Minecraft;

import cpw.mods.fml.relauncher.Side;
import cpw.mods.fml.relauncher.SideOnly;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.util.Collections;
import java.util.HashSet;
import java.util.Properties;
import java.util.Set;
import java.util.TreeSet;

/**
 * Voice preferences, kept between sessions.
 *
 * Follows the shape of {@link com.questforge.content.jukebox.JukeboxSettings}: a
 * properties file in config/, written on change, and tolerant of a corrupt one
 * because defaults that work are better than a mod that will not start.
 *
 * The mute list is here rather than server-side deliberately. Not wanting to hear
 * someone is the listener's business, it should survive a server restart, and it
 * should not require an operator.
 */
@SideOnly(Side.CLIENT)
public final class VoiceSettings {

    private static final String FILE = "qf-voice.properties";

    /** How the microphone decides to open. */
    public enum Mode { PUSH_TO_TALK, OPEN_MIC }

    /**
     * Push-to-talk by default, on purpose.
     *
     * Open mic is the friendlier setting once someone has chosen it, but it should
     * never be what happens to a player who installed the pack and does not yet know
     * the mod is there. A hot microphone nobody opted into is a bad surprise.
     */
    private static Mode mode = Mode.PUSH_TO_TALK;

    private static boolean enabled = true;

    /** Own microphone off. */
    private static boolean muted;

    /** Everyone else off. */
    private static boolean deafened;

    private static float volume = 1.0f;

    /**
     * Loudness at which open mic starts transmitting, as RMS of a frame.
     *
     * Low, because RMS over 20 ms of ordinary speech sits well under a tenth of full
     * scale even when someone is talking normally. Tuned by watching /voice level.
     */
    private static float threshold = 0.020f;

    /** Below-threshold frames still sent after speech stops. 15 frames = 300 ms. */
    private static int hangoverFrames = 15;

    /** Index into VoiceCapture.devices(); below zero means the system default. */
    private static int device = -1;

    private static final Set<String> MUTED_PLAYERS = new HashSet<String>();

    private static boolean loaded;

    private VoiceSettings() { }

    private static File file() {
        File dir = new File(Minecraft.getMinecraft().mcDataDir, "config");
        if (!dir.exists()) dir.mkdirs();
        return new File(dir, FILE);
    }

    public static void load() {
        if (loaded) return;
        loaded = true;

        File f = file();
        if (!f.isFile()) return;

        FileInputStream in = null;
        try {
            Properties p = new Properties();
            in = new FileInputStream(f);
            p.load(in);

            String m = p.getProperty("mode");
            if (m != null) {
                mode = "open".equalsIgnoreCase(m) ? Mode.OPEN_MIC : Mode.PUSH_TO_TALK;
            }
            enabled = Boolean.parseBoolean(p.getProperty("enabled", "true"));
            volume = clamp(parseFloat(p.getProperty("volume"), volume), 0f, 2f);
            threshold = clamp(parseFloat(p.getProperty("threshold"), threshold), 0f, 1f);
            device = (int) parseFloat(p.getProperty("device"), device);
            hangoverFrames = (int) clamp(
                    parseFloat(p.getProperty("hangoverFrames"), hangoverFrames), 0f, 200f);

            String muted = p.getProperty("muted", "");
            MUTED_PLAYERS.clear();
            for (String name : muted.split(",")) {
                String trimmed = name.trim();
                if (trimmed.length() > 0) MUTED_PLAYERS.add(trimmed.toLowerCase());
            }
        } catch (Throwable t) {
            com.questforge.content.QuestForgeContent.log.warn(
                    "[voice] could not read " + FILE + ", using defaults", t);
        } finally {
            close(in);
        }
    }

    public static void save() {
        FileOutputStream out = null;
        try {
            Properties p = new Properties();
            p.setProperty("mode", mode == Mode.OPEN_MIC ? "open" : "ptt");
            p.setProperty("enabled", String.valueOf(enabled));
            p.setProperty("volume", String.valueOf(volume));
            p.setProperty("threshold", String.valueOf(threshold));
            p.setProperty("device", String.valueOf(device));
            p.setProperty("hangoverFrames", String.valueOf(hangoverFrames));

            StringBuilder sb = new StringBuilder();
            for (String name : new TreeSet<String>(MUTED_PLAYERS)) {
                if (sb.length() > 0) sb.append(',');
                sb.append(name);
            }
            p.setProperty("muted", sb.toString());

            out = new FileOutputStream(file());
            p.store(out, "QuestForge proximity voice settings");
        } catch (Throwable t) {
            com.questforge.content.QuestForgeContent.log.warn(
                    "[voice] could not save " + FILE, t);
        } finally {
            close(out);
        }
    }

    // ------------------------------------------------------------------

    public static Mode mode() { return mode; }

    public static void setMode(Mode m) { mode = m; save(); }

    public static boolean isEnabled() { return enabled; }

    public static void setEnabled(boolean b) { enabled = b; save(); }

    public static boolean isMuted() { return muted; }

    /** Not saved: a self-mute is for the moment, not for every future session. */
    public static void setMuted(boolean b) { muted = b; }

    public static boolean isDeafened() { return deafened; }

    public static void setDeafened(boolean b) { deafened = b; }

    public static float volume() { return volume; }

    public static void setVolume(float v) { volume = clamp(v, 0f, 2f); save(); }

    public static float threshold() { return threshold; }

    public static void setThreshold(float t) { threshold = clamp(t, 0f, 1f); save(); }

    public static int hangoverFrames() { return hangoverFrames; }

    public static int device() { return device; }

    public static void setDevice(int d) { device = d; save(); }

    public static boolean isMuted(String playerName) {
        return playerName != null && MUTED_PLAYERS.contains(playerName.toLowerCase());
    }

    /** Returns true if the player is muted after the call. */
    public static boolean toggleMuted(String playerName) {
        String key = playerName.toLowerCase();
        boolean nowMuted;
        if (MUTED_PLAYERS.contains(key)) {
            MUTED_PLAYERS.remove(key);
            nowMuted = false;
        } else {
            MUTED_PLAYERS.add(key);
            nowMuted = true;
        }
        save();
        return nowMuted;
    }

    public static Set<String> mutedPlayers() {
        return Collections.unmodifiableSet(MUTED_PLAYERS);
    }

    // ------------------------------------------------------------------

    private static float parseFloat(String s, float fallback) {
        if (s == null) return fallback;
        try {
            return Float.parseFloat(s);
        } catch (NumberFormatException e) {
            return fallback;
        }
    }

    private static float clamp(float v, float lo, float hi) {
        return v < lo ? lo : v > hi ? hi : v;
    }

    private static void close(java.io.Closeable c) {
        if (c != null) try { c.close(); } catch (Throwable ignored) { }
    }
}
