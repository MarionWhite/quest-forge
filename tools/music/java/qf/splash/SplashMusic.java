package qf.splash;

import java.io.BufferedInputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.InputStream;
import java.io.PrintStream;

import javax.sound.sampled.AudioFormat;
import javax.sound.sampled.AudioInputStream;
import javax.sound.sampled.AudioSystem;
import javax.sound.sampled.Clip;
import javax.sound.sampled.DataLine;
import javax.sound.sampled.FloatControl;

/**
 * Java Sound for splash chant + title-menu loop.
 *
 * SplashProgress.start()  -> start()         chant + preload menu Clip
 * SplashProgress.finish() -> stop()          start menu at t=0, then fade chant
 * GuiOpenEvent            -> onGuiOpenEvent  resume on title, pause otherwise
 * MusicTicker.update()    -> onMusicTick()   keep the one clip alive; skip vanilla MENU
 *
 * One Clip, LOOP_CONTINUOUSLY. Never consult isRunning() to restart from 0 —
 * macOS Java 8 flickers that flag at the wrap and used to stack a second play
 * on the still-audible buffer. menuStarted / menuWanted are the only gates.
 *
 * Menu wav v10: [swell 5 s] + [v9 night body]. First splash→title play starts
 * at frame 0 (swell). setLoopPoints skips the swell so LOOP_CONTINUOUSLY wraps
 * the cricket bed only. Return-from-world resumes the same frame (no rewind).
 *
 * No anonymous Runnables: those compile to SplashMusic$1/$2 and a jar uf of
 * only SplashMusic.class leaves ensureMenu() throwing NoClassDefFoundError,
 * which un-skips vanilla (empty music.menu) and plays nothing.
 */
public final class SplashMusic {
    private static final Object LOCK = new Object();
    private static final float MENU_GAIN_DB = -3.0f;
    private static final float SPLASH_GAIN_DB = -6.0f;
    /** Must match menu_v10.py SWELL_SEC. Loop body starts here. */
    private static final float MENU_SWELL_SEC = 5.0f;
    /** Equal-power chant fade after the menu swell has already started. */
    private static final float CHANT_FADE_SEC = 3.0f;
    private static final String MENU_REL = "resources/assets/minecraft/sounds/music/menu.wav";
    private static final String SPLASH_REL = "resources/assets/minecraft/sounds/music/splash.wav";

    private static Clip splash;
    private static Clip menu;
    private static boolean menuStarted;
    private static boolean menuWanted;
    private static boolean vanillaSilenced;
    private static boolean menuFailLogged;

    private SplashMusic() {}

    public static void start() {
        try {
            synchronized (LOCK) {
                if (splash == null) {
                    splash = openClip(SPLASH_REL, SPLASH_GAIN_DB);
                    if (splash != null) {
                        splash.loop(Clip.LOOP_CONTINUOUSLY);
                    }
                }
            }
            /* named class, not new Runnable() — must be jar uf'd with this class */
            Thread t = new Thread(new SplashMenuPreload(), "QFMenuPreload");
            t.setDaemon(true);
            t.start();
        } catch (Throwable t) {
            /* never break splash */
        }
    }

    /** Called from SplashMenuPreload (separate .class file). */
    static void preloadMenuClip() {
        synchronized (LOCK) {
            try {
                ensureMenuClip();
            } catch (Throwable ignored) {
            }
        }
    }

    /**
     * Splash → title: start the menu swell at frame 0 (if the clip is not
     * already running), then fade the chant under it. Menu first, then fade —
     * never a hard cut, never two full-level beds.
     */
    public static void stop() {
        try {
            startMenuFromSplash();
        } catch (Throwable ignored) {
        }
        fadeAndCloseSplash();
    }

    /**
     * Called from CustomMenu MainMenuTickHandler.test(GuiOpenEvent) (ASM, before
     * CustomMenu swaps GuiMainMenu for MainMenuFix).
     */
    public static void onGuiOpenEvent(Object event) {
        try {
            Object gui = event.getClass().getField("gui").get(event);
            if (isTitleScreen(gui)) {
                ensureMenu();
            } else {
                stopMenu();
            }
        } catch (Throwable ignored) {
        }
    }

    /**
     * @return true if vanilla MusicTicker should skip this tick (we own MENU).
     */
    public static boolean onMusicTick() {
        try {
            Object screen = currentScreen();
            if (isTitleScreen(screen)) {
                try {
                    ensureMenu();
                } catch (Throwable ignored) {
                }
                return true;
            }
            if (screen == null) {
                /* splash / pre-title: do not let vanilla music.menu start */
                return true;
            }
            if (isMenuType()) {
                try {
                    ensureMenu();
                } catch (Throwable ignored) {
                }
                return true;
            }
            stopMenu();
            return false;
        } catch (Throwable ignored) {
        }
        return false;
    }

    public static void ensureMenu() {
        try {
            synchronized (LOCK) {
                if (!ensureMenuClip()) {
                    return;
                }
                if (!menuStarted) {
                    beginMenuAtZero();
                    return;
                }
                if (!menuWanted) {
                    menuWanted = true;
                    menu.loop(Clip.LOOP_CONTINUOUSLY);
                    silenceVanillaMenu();
                }
            }
        } catch (Throwable t) {
            logFail("ensureMenu", t);
        }
    }

    /**
     * Splash handoff only. Forces t=0 + swell if the clip has not started.
     * If it is already running (user somehow still on title), do not rewind.
     */
    private static void startMenuFromSplash() {
        synchronized (LOCK) {
            if (!ensureMenuClip()) {
                return;
            }
            if (menuStarted) {
                if (!menuWanted) {
                    menuWanted = true;
                    menu.loop(Clip.LOOP_CONTINUOUSLY);
                }
                silenceVanillaMenu();
                return;
            }
            beginMenuAtZero();
        }
    }

    private static void beginMenuAtZero() {
        armLoop(menu);
        try {
            menu.setFramePosition(0);
        } catch (Throwable ignored) {
        }
        menu.loop(Clip.LOOP_CONTINUOUSLY);
        menuStarted = true;
        menuWanted = true;
        silenceVanillaMenu();
    }

    private static void fadeAndCloseSplash() {
        Clip dying;
        synchronized (LOCK) {
            dying = splash;
            splash = null;
        }
        if (dying == null) {
            return;
        }
        Thread t = new Thread(new SplashChantFade(dying, SPLASH_GAIN_DB, CHANT_FADE_SEC), "QFChantFade");
        t.setDaemon(true);
        t.start();
    }

    public static void stopMenu() {
        synchronized (LOCK) {
            menuWanted = false;
            vanillaSilenced = false;
            if (menu != null) {
                try {
                    menu.stop();
                } catch (Throwable ignored) {
                }
            }
        }
    }

    private static boolean ensureMenuClip() {
        if (menu != null) {
            return true;
        }
        menu = openClip(MENU_REL, MENU_GAIN_DB);
        if (menu == null) {
            logFail("open " + MENU_REL, null);
            return false;
        }
        return true;
    }

    /**
     * Loop the night body only. Frame 0 is the one-shot swell; wrapping back
     * through it would feel like a break. If setLoopPoints fails on this JRE,
     * the clip still plays — the wrap will include the swell, which is worse
     * but not silent.
     */
    private static void armLoop(Clip c) {
        try {
            int frames = c.getFrameLength();
            if (frames <= 1) {
                return;
            }
            int swell = swellEndFrame(c);
            if (swell < 0) {
                swell = 0;
            }
            if (swell >= frames - 1) {
                swell = 0;
            }
            c.setLoopPoints(swell, frames - 1);
        } catch (Throwable ignored) {
        }
    }

    private static int swellEndFrame(Clip c) {
        float sr = 44100.0f;
        try {
            AudioFormat fmt = c.getFormat();
            if (fmt != null && fmt.getSampleRate() > 1.0f) {
                sr = fmt.getSampleRate();
            }
        } catch (Throwable ignored) {
        }
        return (int) (MENU_SWELL_SEC * sr + 0.5f);
    }

    /**
     * Kill a vanilla music.menu stream if MusicTicker already started one
     * before we owned the title (OpenAL + Java Sound = the "two instances").
     */
    private static void silenceVanillaMenu() {
        if (vanillaSilenced) {
            return;
        }
        try {
            Object mc = minecraft();
            if (mc == null) {
                return;
            }
            java.lang.reflect.Field tf = mc.getClass().getDeclaredField("ax");
            tf.setAccessible(true);
            Object ticker = tf.get(mc);
            if (ticker == null) {
                vanillaSilenced = true;
                return;
            }
            java.lang.reflect.Field cf = ticker.getClass().getDeclaredField("c");
            cf.setAccessible(true);
            Object snd = cf.get(ticker);
            if (snd != null) {
                try {
                    Object sh = null;
                    String[] methods = { "func_147118_V", "getSoundHandler" };
                    for (int i = 0; i < methods.length; i++) {
                        try {
                            sh = mc.getClass().getMethod(methods[i]).invoke(mc);
                            if (sh != null) {
                                break;
                            }
                        } catch (Throwable ignored) {
                        }
                    }
                    if (sh != null) {
                        try {
                            sh.getClass().getMethod("b", snd.getClass()).invoke(sh, snd);
                        } catch (Throwable ignored) {
                        }
                        try {
                            sh.getClass().getMethod("func_147683_b", snd.getClass()).invoke(sh, snd);
                        } catch (Throwable ignored) {
                        }
                        try {
                            sh.getClass().getMethod("stopSound", snd.getClass()).invoke(sh, snd);
                        } catch (Throwable ignored) {
                        }
                    }
                } catch (Throwable ignored) {
                }
                cf.set(ticker, null);
            }
            try {
                java.lang.reflect.Field df = ticker.getClass().getDeclaredField("d");
                df.setAccessible(true);
                df.setInt(ticker, Integer.MAX_VALUE);
            } catch (Throwable ignored) {
            }
            vanillaSilenced = true;
        } catch (Throwable ignored) {
        }
    }

    private static AudioInputStream openPcmStream(String rel) {
        try {
            File f = findWav(rel);
            InputStream raw;
            if (f != null) {
                raw = new FileInputStream(f);
            } else {
                raw = SplashMusic.class.getResourceAsStream("/" + rel.replace("resources/", ""));
                if (raw == null) {
                    return null;
                }
            }
            AudioInputStream in = AudioSystem.getAudioInputStream(new BufferedInputStream(raw));
            AudioFormat base = in.getFormat();
            AudioFormat pcm = new AudioFormat(
                    AudioFormat.Encoding.PCM_SIGNED,
                    base.getSampleRate(),
                    16,
                    base.getChannels(),
                    base.getChannels() * 2,
                    base.getSampleRate(),
                    false);
            if (!base.matches(pcm)) {
                in = AudioSystem.getAudioInputStream(pcm, in);
            }
            return in;
        } catch (Throwable t) {
            logFail("openPcmStream " + rel, t);
            return null;
        }
    }

    private static File findWav(String rel) {
        File[] roots = new File[] {
                gameDir(),
                new File("."),
                new File("minecraft")
        };
        for (int i = 0; i < roots.length; i++) {
            if (roots[i] == null) {
                continue;
            }
            File f = new File(roots[i], rel);
            if (f.isFile() && f.length() > 44) {
                return f;
            }
        }
        return null;
    }

    private static Clip openClip(String rel, float gainDb) {
        try {
            AudioInputStream in = openPcmStream(rel);
            if (in == null) {
                return null;
            }
            Clip c = AudioSystem.getClip();
            c.open(in);
            try {
                in.close();
            } catch (Throwable ignored) {
            }
            applyGain(c, gainDb);
            return c;
        } catch (Throwable t) {
            logFail("openClip " + rel, t);
            return null;
        }
    }

    private static void applyGain(DataLine line, float gainDb) {
        try {
            if (line.isControlSupported(FloatControl.Type.MASTER_GAIN)) {
                ((FloatControl) line.getControl(FloatControl.Type.MASTER_GAIN)).setValue(gainDb);
            }
        } catch (Throwable ignored) {
        }
    }

    private static void closeClip(Clip c) {
        if (c == null) {
            return;
        }
        try {
            c.stop();
            c.close();
        } catch (Throwable ignored) {
        }
    }

    private static boolean isTitleScreen(Object gui) {
        if (gui == null) {
            return false;
        }
        Class c = gui.getClass();
        while (c != null) {
            String n = c.getName();
            if (n.indexOf("MainMenuFix") >= 0 || n.indexOf("GuiMainMenu") >= 0 || "bee".equals(n)) {
                return true;
            }
            c = c.getSuperclass();
        }
        return false;
    }

    private static Object currentScreen() {
        Object mc = minecraft();
        if (mc == null) {
            return null;
        }
        String[] fields = { "n", "field_71462_r", "currentScreen" };
        for (int i = 0; i < fields.length; i++) {
            try {
                return mc.getClass().getField(fields[i]).get(mc);
            } catch (Throwable ignored) {
            }
        }
        return null;
    }

    private static boolean isMenuType() {
        try {
            Object type = currentMusicType();
            if (type == null) {
                return false;
            }
            if (type instanceof Enum && "MENU".equals(((Enum) type).name())) {
                return true;
            }
            /* notch enum constants are a,b,c...; MusicType.MENU is the first (a) */
            if (type instanceof Enum && ((Enum) type).ordinal() == 0) {
                try {
                    Object loc = type.getClass().getMethod("a").invoke(type);
                    if (loc != null && loc.toString().indexOf("music.menu") >= 0) {
                        return true;
                    }
                } catch (Throwable ignored) {
                }
            }
            try {
                Object loc = type.getClass().getMethod("a").invoke(type);
                if (loc != null && loc.toString().indexOf("music.menu") >= 0) {
                    return true;
                }
            } catch (Throwable ignored) {
            }
            try {
                Object loc = type.getClass().getMethod("func_148635_a").invoke(type);
                if (loc != null && loc.toString().indexOf("music.menu") >= 0) {
                    return true;
                }
            } catch (Throwable ignored) {
            }
        } catch (Throwable ignored) {
        }
        return false;
    }

    private static Object currentMusicType() {
        Object mc = minecraft();
        if (mc == null) {
            return null;
        }
        /* Y is getAmbientMusicType in 1.7.10 (returns bth). Do not try W — that is a boolean. */
        String[] methods = { "Y", "func_147109_W", "getAmbientMusicType" };
        for (int i = 0; i < methods.length; i++) {
            try {
                return mc.getClass().getMethod(methods[i]).invoke(mc);
            } catch (Throwable ignored) {
            }
        }
        return null;
    }

    private static Object minecraft() {
        Object mc = tryInvoke("bao", "B");
        if (mc != null) {
            return mc;
        }
        mc = tryInvoke("net.minecraft.client.Minecraft", "func_71410_x");
        if (mc != null) {
            return mc;
        }
        return tryInvoke("net.minecraft.client.Minecraft", "getMinecraft");
    }

    private static Object tryInvoke(String cls, String method) {
        try {
            return Class.forName(cls).getMethod(method).invoke(null);
        } catch (Throwable t) {
            return null;
        }
    }

    private static File gameDir() {
        Object mc = minecraft();
        if (mc != null) {
            String[] fields = { "w", "field_71412_D", "mcDataDir" };
            for (int i = 0; i < fields.length; i++) {
                try {
                    Object v = mc.getClass().getField(fields[i]).get(mc);
                    if (v instanceof File) {
                        return (File) v;
                    }
                } catch (Throwable ignored) {
                }
            }
        }
        return new File(".");
    }

    private static void logFail(String what, Throwable t) {
        if (menuFailLogged) {
            return;
        }
        menuFailLogged = true;
        try {
            PrintStream err = System.err;
            err.println("[QuestForge] SplashMusic FAILED: " + what);
            if (t != null) {
                t.printStackTrace(err);
            }
        } catch (Throwable ignored) {
        }
    }
}
