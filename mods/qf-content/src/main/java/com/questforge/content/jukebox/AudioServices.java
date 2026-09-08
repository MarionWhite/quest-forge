package com.questforge.content.jukebox;

import cpw.mods.fml.common.FMLLog;

import javax.sound.sampled.AudioFormat;
import javax.sound.sampled.AudioInputStream;
import javax.sound.sampled.AudioSystem;
import javax.sound.sampled.UnsupportedAudioFileException;
import javax.sound.sampled.spi.AudioFileReader;
import javax.sound.sampled.spi.FormatConversionProvider;
import java.io.File;
import java.io.IOException;
import java.io.InputStream;
import java.util.Iterator;
import java.util.ServiceLoader;

/**
 * Reaches the bundled mp3 and Ogg decoders from whatever thread is asking.
 *
 * Java 8 decodes only WAV, AIFF and AU on its own. The mod ships JavaZOOM's mp3 and
 * Vorbis providers inside its own jar, and AudioSystem is supposed to find them by
 * itself -- it looks up implementations through ServiceLoader, which reads the
 * META-INF/services files off the classpath.
 *
 * The catch is which classpath. ServiceLoader.load(Class) scans the calling thread's
 * CONTEXT class loader, and in a packed instance a mod jar is not on the system
 * classpath at all: Forge loads it through LaunchClassLoader. Minecraft's own thread
 * has that set as its context loader, and a thread inherits its creator's, so the
 * decoders are usually found -- but "usually" is doing real work in that sentence.
 * Any thread that came from a pool, or from anything Forge did not start, carries a
 * loader that cannot see inside this jar, and the failure is a plain
 * UnsupportedAudioFileException with nothing to say it was a lookup problem.
 *
 * In a dev workspace none of this can go wrong, because there the decoders sit on the
 * system classpath where every loader can reach them. That asymmetry is exactly what
 * makes this worth pinning down rather than testing: the bug cannot reproduce here,
 * and only shows up in the pack.
 *
 * So every call goes through this class, which points the context loader at the one
 * that loaded this file -- the same jar the decoders are in -- and puts it back
 * afterwards.
 */
public final class AudioServices {

    private AudioServices() { }

    // ------------------------------------------------------------------
    // The wrapped calls
    // ------------------------------------------------------------------

    public static AudioInputStream read(File file)
            throws UnsupportedAudioFileException, IOException {
        ClassLoader previous = borrow();
        try {
            return AudioSystem.getAudioInputStream(file);
        } finally {
            giveBack(previous);
        }
    }

    public static AudioInputStream read(InputStream stream)
            throws UnsupportedAudioFileException, IOException {
        ClassLoader previous = borrow();
        try {
            return AudioSystem.getAudioInputStream(stream);
        } finally {
            giveBack(previous);
        }
    }

    public static boolean canConvert(AudioFormat target, AudioFormat source) {
        ClassLoader previous = borrow();
        try {
            return AudioSystem.isConversionSupported(target, source);
        } finally {
            giveBack(previous);
        }
    }

    public static AudioInputStream convert(AudioFormat target, AudioInputStream source) {
        ClassLoader previous = borrow();
        try {
            return AudioSystem.getAudioInputStream(target, source);
        } finally {
            giveBack(previous);
        }
    }

    // ------------------------------------------------------------------
    // Diagnosis
    // ------------------------------------------------------------------

    /**
     * Logs which decoders are actually reachable, once, at startup.
     *
     * Worth a line in the log because the alternative way to discover that the
     * shading went wrong is a player reporting that some of their music does not
     * play. Four providers is a working install; two means the service files were
     * overwritten instead of merged during packaging, and none means the libraries
     * did not make it into the jar at all.
     */
    public static void report() {
        ClassLoader previous = borrow();
        try {
            int readers = count(ServiceLoader.load(AudioFileReader.class).iterator());
            int converters = count(ServiceLoader.load(FormatConversionProvider.class).iterator());

            FMLLog.info("[QuestForge] Audio decoders: %d file readers, %d converters",
                        readers, converters);

            for (AudioFileReader reader : ServiceLoader.load(AudioFileReader.class)) {
                String name = reader.getClass().getName();
                if (name.startsWith("javazoom")) {
                    FMLLog.info("[QuestForge]   %s", name);
                }
            }

            if (readers < 4) {
                FMLLog.warning("[QuestForge] Expected at least four audio file readers "
                        + "(Java's own three, plus mp3 and Ogg). Some formats will not "
                        + "play -- the bundled decoders are missing or their "
                        + "META-INF/services entries were overwritten rather than "
                        + "merged when this jar was built.");
            }
        } catch (Throwable t) {
            FMLLog.warning("[QuestForge] Could not enumerate audio decoders: %s", t);
        } finally {
            giveBack(previous);
        }
    }

    private static int count(Iterator<?> it) {
        int n = 0;
        while (it.hasNext()) { it.next(); n++; }
        return n;
    }

    // ------------------------------------------------------------------
    // The swap
    // ------------------------------------------------------------------

    /**
     * Points the context loader at this jar and hands back what was there.
     *
     * Returns null when nothing needs restoring, which also covers the case where a
     * security manager refuses the change -- there is none in Minecraft, but a
     * failure here should degrade to "look-up might miss" rather than to a crash in
     * the middle of starting a track.
     */
    private static ClassLoader borrow() {
        try {
            Thread thread = Thread.currentThread();
            ClassLoader mine = AudioServices.class.getClassLoader();
            ClassLoader previous = thread.getContextClassLoader();
            if (previous == mine) return null;
            thread.setContextClassLoader(mine);
            return previous == null ? ClassLoader.getSystemClassLoader() : previous;
        } catch (Throwable t) {
            return null;
        }
    }

    private static void giveBack(ClassLoader previous) {
        if (previous == null) return;
        try {
            Thread.currentThread().setContextClassLoader(previous);
        } catch (Throwable ignored) {
            // Nothing useful to do: the stream has already been opened.
        }
    }
}
