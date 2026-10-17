package qf.splash;

import java.awt.image.BufferedImage;
import java.io.File;
import java.io.InputStream;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.nio.ByteBuffer;

import javax.imageio.ImageIO;
import javax.sound.sampled.Clip;

import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.lwjgl.BufferUtils;
import org.lwjgl.opengl.Display;
import org.lwjgl.opengl.GL11;

/**
 * Runtime half of com.questforge.SplashTransformer: the few things the old
 * hand-patched Forge jar did inline, reached here by reflection so the
 * transformer only ever adds INVOKESTATIC calls (no new fields, no branches).
 *
 *   pulse(texture)   head of SplashProgress$Texture.bind: the corner emblem breathes
 *   fontColor()      the colour argument of the splash's two drawString calls
 *   open(location)   SplashFontRenderer.getResourceInputStream: glyph widths are
 *                    measured from the same resources/ font the splash draws
 *   frame()          before each Display.update of the splash thread
 *   finishing()      head of SplashProgress.finish
 *
 * frame() and finishing() only log, unless -Dqf.splash.shots=DIR is set; then
 * frame() also saves the splash's back buffer to DIR every
 * -Dqf.splash.shotEvery milliseconds (default 5000), so the loading screen can
 * be compared between the OptiFine and the Angelica client without relying on
 * a desktop capture. Every method swallows its own errors: the splash must
 * never die because of this class.
 */
public final class QFSplash {

    private static final Logger LOG = LogManager.getLogger("QuestForgeTweaks");
    private static final String SP = "cpw.mods.fml.client.SplashProgress";
    private static final long T0 = System.nanoTime();

    private static final String SHOTS = System.getProperty("qf.splash.shots");
    private static final long SHOT_EVERY_MS = Long.getLong("qf.splash.shotEvery", 5000L);

    private static Field forgeTexture, fontColor;
    private static Method open;
    private static boolean reflected, reflectFailed;
    private static int frames;
    private static long nextShotMs;
    private static int shots;

    private QFSplash() {}

    // ------------------------------------------------------------- patched calls

    public static void pulse(Object texture) {
        try {
            if (texture != null && reflect() && texture == forgeTexture.get(null)) {
                float v = (float) Math.sin(System.currentTimeMillis() * 0.0025132741228718345D) * 0.225F + 0.775F;
                GL11.glColor4f(v, v, v, 1.0F);
            }
        } catch (Throwable ignored) {
        }
    }

    public static int fontColor() {
        try {
            if (reflect()) return fontColor.getInt(null);
        } catch (Throwable ignored) {
        }
        return 0;
    }

    public static InputStream open(Object location) throws java.io.IOException {
        try {
            if (reflect()) return (InputStream) open.invoke(null, location);
        } catch (java.lang.reflect.InvocationTargetException e) {
            Throwable c = e.getCause();
            if (c instanceof java.io.IOException) throw (java.io.IOException) c;
        } catch (Throwable ignored) {
        }
        throw new java.io.FileNotFoundException(String.valueOf(location));
    }

    public static synchronized void frame() {
        try {
            frames++;
            long ms = (System.nanoTime() - T0) / 1000000L;
            if (frames == 1) {
                LOG.info("[QFSplash] first splash frame at {} ms: {}x{}, textured bars {}, {}",
                        ms, Display.getWidth(), Display.getHeight(),
                        QFBarsState.ready() ? "on" : "OFF (plain Forge boxes)", music());
                nextShotMs = ms;
            }
            if (SHOTS != null && ms >= nextShotMs) {
                nextShotMs = ms + SHOT_EVERY_MS;
                shoot(ms);
            }
        } catch (Throwable ignored) {
        }
    }

    public static void finishing() {
        try {
            long ms = (System.nanoTime() - T0) / 1000000L;
            LOG.info("[QFSplash] splash finishing after {} ms and {} frames; {}", ms, frames, music());
            Thread t = new Thread(new MusicReport(4000L), "QFSplashMusicReport");
            t.setDaemon(true);
            t.start();
        } catch (Throwable ignored) {
        }
    }

    // ----------------------------------------------------------------- reporting

    /** The splash chant and menu clips, as SplashMusic holds them right now. */
    static String music() {
        try {
            Class<?> sm = Class.forName("qf.splash.SplashMusic");
            return "chant " + clip(sm, "splash") + ", menu " + clip(sm, "menu");
        } catch (Throwable t) {
            return "SplashMusic not loaded (" + t + ")";
        }
    }

    private static String clip(Class<?> sm, String field) {
        try {
            Field f = sm.getDeclaredField(field);
            f.setAccessible(true);
            Object o = f.get(null);
            if (!(o instanceof Clip)) return "none";
            Clip c = (Clip) o;
            float rate = c.getFormat().getFrameRate();
            return String.format("%s at %.1fs of %.1fs", c.isRunning() ? "PLAYING" : "stopped",
                    c.getLongFramePosition() / rate, c.getFrameLength() / rate);
        } catch (Throwable t) {
            return "? (" + t.getClass().getSimpleName() + ")";
        }
    }

    /** Logs the music once more after the hand-off, when the chant fade is done. */
    static final class MusicReport implements Runnable {
        private final long delay;

        MusicReport(long delay) {
            this.delay = delay;
        }

        public void run() {
            try {
                Thread.sleep(delay);
                LOG.info("[QFSplash] {} ms after the splash: {}", delay, music());
            } catch (Throwable ignored) {
            }
        }
    }

    private static void shoot(long ms) {
        int w = Display.getWidth(), h = Display.getHeight();
        if (w <= 0 || h <= 0) return;
        ByteBuffer buf = BufferUtils.createByteBuffer(w * h * 4);
        GL11.glReadBuffer(GL11.GL_BACK);
        GL11.glReadPixels(0, 0, w, h, GL11.GL_RGBA, GL11.GL_UNSIGNED_BYTE, buf);
        Thread t = new Thread(new Shot(buf, w, h, new File(SHOTS,
                String.format("splash-%02d-%05dms.png", ++shots, ms))), "QFSplashShot");
        t.setDaemon(true);
        t.start();
    }

    static final class Shot implements Runnable {
        private final ByteBuffer buf;
        private final int w, h;
        private final File out;

        Shot(ByteBuffer buf, int w, int h, File out) {
            this.buf = buf;
            this.w = w;
            this.h = h;
            this.out = out;
        }

        public void run() {
            try {
                BufferedImage img = new BufferedImage(w, h, BufferedImage.TYPE_INT_RGB);
                for (int y = 0; y < h; y++) {
                    for (int x = 0; x < w; x++) {
                        int i = ((h - 1 - y) * w + x) * 4;
                        int r = buf.get(i) & 0xFF, g = buf.get(i + 1) & 0xFF, b = buf.get(i + 2) & 0xFF;
                        img.setRGB(x, y, (r << 16) | (g << 8) | b);
                    }
                }
                out.getParentFile().mkdirs();
                ImageIO.write(img, "png", out);
                LOG.info("[QFSplash] saved {} ({})", out.getName(), music());
            } catch (Throwable t) {
                LOG.warn("[QFSplash] could not save " + out, t);
            }
        }
    }

    // ---------------------------------------------------------------- reflection

    private static boolean reflect() {
        if (reflected) return !reflectFailed;
        reflected = true;
        try {
            Class<?> sp = Class.forName(SP, false, QFSplash.class.getClassLoader());
            forgeTexture = sp.getDeclaredField("forgeTexture");
            forgeTexture.setAccessible(true);
            fontColor = sp.getDeclaredField("fontColor");
            fontColor.setAccessible(true);
            for (Method m : sp.getDeclaredMethods()) {
                if ("open".equals(m.getName()) && m.getParameterTypes().length == 1) {
                    open = m;
                }
            }
            if (open == null) throw new NoSuchMethodException(SP + ".open");
            open.setAccessible(true);
        } catch (Throwable t) {
            reflectFailed = true;
            LOG.warn("[QFSplash] cannot reach SplashProgress internals; emblem pulse, font colour "
                    + "and HD font widths fall back to Forge's", t);
        }
        return !reflectFailed;
    }

    /** QFBars keeps its texture state private; ask it the same way it asks itself. */
    static final class QFBarsState {
        static boolean ready() {
            try {
                Method m = QFBars.class.getDeclaredMethod("ready");
                m.setAccessible(true);
                return Boolean.TRUE.equals(m.invoke(null));
            } catch (Throwable t) {
                return false;
            }
        }
    }
}
