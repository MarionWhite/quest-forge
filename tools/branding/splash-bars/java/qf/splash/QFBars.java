package qf.splash;

import java.awt.image.BufferedImage;
import java.io.File;
import java.nio.ByteBuffer;
import javax.imageio.ImageIO;

import net.minecraft.launchwrapper.Launch;
import org.lwjgl.BufferUtils;
import org.lwjgl.opengl.GL11;

/**
 * Quest Forge textured splash bars. The patched Forge SplashProgress$3.drawBar calls:
 *   beginBar(2,2,1)                    instead of the first GL11.glScalef  (bar origin, before the title text)
 *   drawBox(this, 400, 20)             border  (bar origin translated by 0,20)
 *   drawBox(this, 398, 18)             background (translated by a further 1,1)
 *   drawBox(this, fill, 18)            fill
 * Textures are read from <gameDir>/resources/assets/minecraft/textures/gui/title/splash/.
 * Any failure falls back to Forge's plain coloured boxes, so the splash can never die because of this class.
 */
public final class QFBars {
    private static final String DIR = "resources/assets/minecraft/textures/gui/title/splash";
    private static final float CAP = 30f, PAD = 5f;
    private static final float TITLE_SCALE = 2.6f, TITLE_LIFT = -5f;   // title text: bigger, nudged up           // trough overhang beyond the 400x20 border box
    private static boolean tried, ok;
    private static int texTrough, texRim, texMagma, texHead, texPlaque;
    private static int phase;                                   // 0 border, 1 background, 2 fill
    private static float fullW = 398f;
    private static final long T0 = System.nanoTime();

    private QFBars() {}

    public static void beginBar(float sx, float sy, float sz) {
        try {
            if (ready()) {
                GL11.glTranslatef(0f, TITLE_LIFT, 0f);
                GL11.glScalef(TITLE_SCALE, TITLE_SCALE, 1f);
                return;
            }
        } catch (Throwable t) {
            ok = false;
        }
        GL11.glScalef(sx, sy, sz);
    }

    public static void drawBox(Object self, int w, int h) {
        try {
            if (ready()) {
                if (phase == 0 && h == 20) { drawTrough(w, h); phase = 1; return; }
                if (phase == 1 && h == 18) { fullW = w; phase = 2; return; }
                if (phase == 2 && h == 18) { drawFill(w, h); phase = 0; return; }
                phase = 0;
            }
        } catch (Throwable t) {
            ok = false;
        }
        plainBox(w, h);
    }

    // ------------------------------------------------------------------ drawing
    private static float seconds() {
        return (System.nanoTime() - T0) / 1.0e9f;
    }

    private static void push() {
        GL11.glPushAttrib(GL11.GL_ENABLE_BIT | GL11.GL_COLOR_BUFFER_BIT | GL11.GL_CURRENT_BIT | GL11.GL_TEXTURE_BIT);
        GL11.glEnable(GL11.GL_TEXTURE_2D);
        GL11.glEnable(GL11.GL_BLEND);
        GL11.glBlendFunc(GL11.GL_SRC_ALPHA, GL11.GL_ONE_MINUS_SRC_ALPHA);
        GL11.glColor4f(1f, 1f, 1f, 1f);
    }

    private static void pop() {
        GL11.glPopAttrib();
    }

    private static void quad(float x0, float y0, float x1, float y1, float u0, float v0, float u1, float v1) {
        GL11.glBegin(GL11.GL_QUADS);
        GL11.glTexCoord2f(u0, v0); GL11.glVertex2f(x0, y0);
        GL11.glTexCoord2f(u0, v1); GL11.glVertex2f(x0, y1);
        GL11.glTexCoord2f(u1, v1); GL11.glVertex2f(x1, y1);
        GL11.glTexCoord2f(u1, v0); GL11.glVertex2f(x1, y0);
        GL11.glEnd();
    }

    private static void drawPlaque() {
        push();
        GL11.glBindTexture(GL11.GL_TEXTURE_2D, texPlaque);
        quad(-CAP, -14f, 400f + CAP, 46f, 0, 0, 1, 1);
        pop();
    }

    private static void drawTrough(int w, int h) {
        push();
        GL11.glBindTexture(GL11.GL_TEXTURE_2D, texTrough);
        quad(-CAP, -PAD, w + CAP, h + PAD, 0, 0, 1, 1);
        pop();
    }

    private static void drawFill(int w, int h) {
        push();
        float t = seconds();
        if (w > 0) {
            float fw = fullW;
            float fill = w;
            boolean complete = fill >= fw - 1f;
            float scroll = -t * 0.045f;                       // slow flow to the right
            float pulse = 0.92f + 0.08f * (float) Math.sin(t * 2.1);
            GL11.glBindTexture(GL11.GL_TEXTURE_2D, texMagma);
            magmaShape(fill, h, fw, scroll, complete, pulse, pulse, pulse, 1f);
            // second, fainter layer drifting the other way for depth
            GL11.glBlendFunc(GL11.GL_SRC_ALPHA, GL11.GL_ONE);
            magmaShape(fill, h, fw, -scroll * 0.6f + 0.37f, complete, 1f, 0.55f, 0.15f,
                    0.12f + 0.06f * (float) Math.sin(t * 3.7));
            if (!complete) {
                glowTongue(fill, h, 0.62f + 0.22f * (float) Math.sin(t * 5.0));
            }
            GL11.glBlendFunc(GL11.GL_SRC_ALPHA, GL11.GL_ONE_MINUS_SRC_ALPHA);
            GL11.glColor4f(1f, 1f, 1f, 1f);
        }
        // rim overlay hides the square corners of the fill inside the rounded channel
        GL11.glBindTexture(GL11.GL_TEXTURE_2D, texRim);
        quad(-1f - CAP, -1f - PAD, -1f + 400f + CAP, -1f + 20f + PAD, 0, 0, 1, 1);
        pop();
    }

    /**
     * Magma body plus a floor-hugging tongue. Bottom edge stays flush with the channel
     * floor (y = h); the top surface is a quarter-ellipse that curves down to meet that
     * floor at the tip. Not a vertically symmetric cap.
     */
    private static void magmaShape(float fill, float h, float fw, float u0, boolean complete,
                                  float r, float g, float b, float a) {
        GL11.glColor4f(r, g, b, a);
        if (complete || fill <= 1f) {
            quad(0, 0, fill, h, u0, 0, u0 + fill / fw, 1);
            return;
        }
        float nose = tongueNose(fill, h);
        float body = fill - nose;
        if (body > 0.35f) {
            quad(0, 0, body, h, u0, 0, u0 + body / fw, 1);
        }
        int segs = 16;
        GL11.glBegin(GL11.GL_TRIANGLE_STRIP);
        for (int i = 0; i <= segs; i++) {
            float s = i / (float) segs;       // 0 at body join, 1 at tip
            // quarter-ellipse: stays near full height, then the top drops to the floor
            float drop = tongueDrop(s);
            float x = body + nose * s;
            float top = h * drop;             // 0 → h (curves down)
            float bot = h;                    // stays on the channel floor
            float fade = s < 0.88f ? 1f : (1f - s) / 0.12f;
            GL11.glColor4f(r, g, b, a * (0.55f + 0.45f * fade));
            float u = u0 + x / fw;
            GL11.glTexCoord2f(u, top / h); GL11.glVertex2f(x, top);
            GL11.glTexCoord2f(u, 1f); GL11.glVertex2f(x, bot);
        }
        GL11.glEnd();
        GL11.glColor4f(r, g, b, a);
    }

    private static float tongueNose(float fill, float h) {
        return Math.min(fill, Math.max(h * 2.1f, 20f));
    }

    /** Quarter-ellipse 0→1: top stays high, then drops to the floor at the tip. */
    private static float tongueDrop(float s) {
        return 1f - (float) Math.sqrt(Math.max(0f, 1f - s * s));
    }

    /**
     * Additive highlight warped onto the same tongue: bright core at the floor tip,
     * halo following the top-curves-down edge. Not a centered circular sprite.
     */
    private static void glowTongue(float fill, float h, float a) {
        float nose = tongueNose(fill, h);
        float body = fill - nose;
        GL11.glBindTexture(GL11.GL_TEXTURE_2D, texHead);
        int segs = 16;
        // Wedge: same floor + top curve as the magma, head.png centre pinned at the tip
        GL11.glBegin(GL11.GL_TRIANGLE_STRIP);
        for (int i = 0; i <= segs; i++) {
            float s = i / (float) segs;
            float x = body + nose * s;
            float top = h * tongueDrop(s);
            float u = 0.12f + 0.38f * s;          // 0.12 at body (dim rim) → 0.50 at tip (hot centre)
            float along = 0.20f + 0.80f * s * s;  // brighter toward the tip
            GL11.glColor4f(1f, 0.85f, 0.45f, a * along);
            GL11.glTexCoord2f(u, 0.28f); GL11.glVertex2f(x, top - h * 0.08f);
            GL11.glColor4f(1f, 0.55f, 0.18f, a * along * 0.35f);
            GL11.glTexCoord2f(u, 0.72f); GL11.glVertex2f(x, h);
        }
        GL11.glEnd();
        // Thin lip along the upper curve so the highlight reads as riding the slope
        GL11.glBegin(GL11.GL_TRIANGLE_STRIP);
        for (int i = 0; i <= segs; i++) {
            float s = i / (float) segs;
            float x = body + nose * s;
            float top = h * tongueDrop(s);
            float u = 0.20f + 0.30f * s;
            float along = 0.15f + 0.85f * s;
            float band = Math.max(1.2f, (h - top) * 0.22f + h * 0.10f);
            GL11.glColor4f(1f, 0.92f, 0.55f, a * along * 0.85f);
            GL11.glTexCoord2f(u, 0.40f); GL11.glVertex2f(x, top - h * 0.06f);
            GL11.glColor4f(1f, 0.6f, 0.2f, a * along * 0.15f);
            GL11.glTexCoord2f(u, 0.60f); GL11.glVertex2f(x, Math.min(h, top + band));
        }
        GL11.glEnd();
    }

    private static void plainBox(int w, int h) {
        GL11.glBegin(GL11.GL_QUADS);
        GL11.glVertex2f(0, 0);
        GL11.glVertex2f(0, h);
        GL11.glVertex2f(w, h);
        GL11.glVertex2f(w, 0);
        GL11.glEnd();
    }

    // ------------------------------------------------------------------ textures
    private static boolean ready() {
        if (!tried) {
            tried = true;
            try {
                File home = Launch.minecraftHome != null ? Launch.minecraftHome : new File(".");
                File dir = new File(home, DIR);
                texTrough = load(new File(dir, "trough.png"), false);
                texRim = load(new File(dir, "rim.png"), false);
                texMagma = load(new File(dir, "magma.png"), true);
                texHead = load(new File(dir, "head.png"), false);
                texPlaque = load(new File(dir, "plaque.png"), false);
                ok = true;
            } catch (Throwable t) {
                ok = false;
                System.err.println("[QFBars] textured splash bars disabled: " + t);
            }
        }
        return ok;
    }

    private static int load(File f, boolean repeatS) throws Exception {
        BufferedImage img = ImageIO.read(f);
        if (img == null) throw new IllegalStateException("cannot decode " + f);
        int w = img.getWidth(), h = img.getHeight();
        int[] px = img.getRGB(0, 0, w, h, null, 0, w);
        ByteBuffer buf = BufferUtils.createByteBuffer(w * h * 4);
        for (int i = 0; i < px.length; i++) {
            int p = px[i];
            buf.put((byte) ((p >> 16) & 0xFF)).put((byte) ((p >> 8) & 0xFF)).put((byte) (p & 0xFF)).put((byte) ((p >> 24) & 0xFF));
        }
        buf.flip();
        int id = GL11.glGenTextures();
        GL11.glBindTexture(GL11.GL_TEXTURE_2D, id);
        GL11.glTexParameteri(GL11.GL_TEXTURE_2D, GL11.GL_TEXTURE_MIN_FILTER, GL11.GL_LINEAR);
        GL11.glTexParameteri(GL11.GL_TEXTURE_2D, GL11.GL_TEXTURE_MAG_FILTER, GL11.GL_LINEAR);
        GL11.glTexParameteri(GL11.GL_TEXTURE_2D, GL11.GL_TEXTURE_WRAP_S, repeatS ? GL11.GL_REPEAT : GL11.GL_CLAMP);
        GL11.glTexParameteri(GL11.GL_TEXTURE_2D, GL11.GL_TEXTURE_WRAP_T, GL11.GL_CLAMP);
        GL11.glTexImage2D(GL11.GL_TEXTURE_2D, 0, GL11.GL_RGBA, w, h, 0, GL11.GL_RGBA, GL11.GL_UNSIGNED_BYTE, buf);
        int err = GL11.glGetError();
        if (err != 0) throw new IllegalStateException("glTexImage2D error " + err + " for " + f.getName());
        return id;
    }
}
