package com.questforge.content.jukebox;

import net.minecraft.client.Minecraft;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.util.Properties;

/**
 * Remembers the jukebox's volume and range between sessions.
 *
 * Volume is the kind of setting someone adjusts once to suit their speakers, so
 * having it reset on every launch would be a small, repeated annoyance. Range is
 * kept alongside it because it is tuned the same way -- by walking around until it
 * feels right -- and that judgement should not have to be redone either.
 */
public final class JukeboxSettings {

    private static final String FILE = "qf-jukebox.properties";

    /**
     * Ducking has to change Minecraft's own music level, because that is the only
     * value the sound engine actually reads. That value is saved in options.txt,
     * so a crash while the music is ducked would leave the player's music silent
     * with no clue why. Writing the original here first means the next launch can
     * hand it back.
     */
    private static final String STASH_KEY = "duckedMusicLevel";

    /**
     * Bumped whenever the default range is retuned. A saved file from before the
     * change keeps its volume and loop settings but takes the new range, so a
     * tuning fix is not permanently masked by whatever was on disk.
     */
    private static final int RANGE_TUNING = 2;

    private static boolean loaded;

    private JukeboxSettings() { }

    private static File file() {
        File dir = new File(Minecraft.getMinecraft().mcDataDir, "config");
        if (!dir.exists()) dir.mkdirs();
        return new File(dir, FILE);
    }

    /** Applies saved settings. Safe to call repeatedly; only the first does work. */
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

            String v = p.getProperty("volume");
            if (v != null) DirectAudio.setVolume(Float.parseFloat(v));

            // Range is skipped when the file predates the current tuning, so a
            // retuned default actually reaches players who already have a saved
            // file -- otherwise the old numbers would silently win forever.
            int version = 0;
            try {
                version = Integer.parseInt(p.getProperty("version", "0"));
            } catch (NumberFormatException ignored) {
                // Treated as the oldest version, which is what we want.
            }

            if (version >= RANGE_TUNING) {
                String full = p.getProperty("fullDistance");
                String max = p.getProperty("maxDistance");
                if (full != null && max != null) {
                    DirectAudio.setRange(Float.parseFloat(full), Float.parseFloat(max));
                }
            }

            String loop = p.getProperty("loop");
            if (loop != null) Playback.setLooping(Boolean.parseBoolean(loop));
        } catch (Throwable t) {
            // A corrupt settings file must never stop the jukebox working; the
            // defaults are perfectly usable.
            com.questforge.content.QuestForgeContent.log.warn(
                    "[jukebox] could not read " + FILE + ", using defaults", t);
        } finally {
            close(in);
        }
    }

    /**
     * The music level to give back after a crash, or null if we exited cleanly.
     * Read once at startup, before anything has had a chance to duck.
     */
    public static Float stashedMusicLevel() {
        File f = file();
        if (!f.isFile()) return null;

        FileInputStream in = null;
        try {
            Properties p = new Properties();
            in = new FileInputStream(f);
            p.load(in);
            String v = p.getProperty(STASH_KEY);
            return v == null ? null : Float.valueOf(Float.parseFloat(v));
        } catch (Throwable t) {
            return null;
        } finally {
            close(in);
        }
    }

    /** Recorded before the music is ducked, cleared once it has been restored. */
    public static void stashMusicLevel(Float level) {
        write(level);
    }

    public static void clearMusicStash() {
        write(null);
    }

    public static void save() {
        write(stashedMusicLevel());
    }

    private static void write(Float stash) {
        FileOutputStream out = null;
        try {
            Properties p = new Properties();
            p.setProperty("volume", String.valueOf(DirectAudio.getVolume()));
            p.setProperty("fullDistance", String.valueOf(DirectAudio.getRefDistance()));
            p.setProperty("maxDistance", String.valueOf(DirectAudio.getMaxDistance()));
            p.setProperty("loop", String.valueOf(Playback.isLooping()));
            p.setProperty("version", String.valueOf(RANGE_TUNING));
            if (stash != null) p.setProperty(STASH_KEY, String.valueOf(stash.floatValue()));

            out = new FileOutputStream(file());
            p.store(out, "QuestForge jukebox settings");
        } catch (Throwable t) {
            com.questforge.content.QuestForgeContent.log.warn(
                    "[jukebox] could not save " + FILE, t);
        } finally {
            close(out);
        }
    }

    private static void close(java.io.Closeable c) {
        if (c != null) try { c.close(); } catch (Throwable ignored) { }
    }
}
