package qf.menu;

import java.awt.image.BufferedImage;
import java.io.InputStream;
import java.nio.ByteBuffer;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.Random;
import javax.imageio.ImageIO;

import mainmenuserver.MainMenuFix;
import org.lwjgl.BufferUtils;
import org.lwjgl.input.Mouse;
import org.lwjgl.opengl.Display;
import org.lwjgl.opengl.GL11;

/**
 * Animated forged-iron menu buttons. The patched CustomMenu MainMenuFix.drawScreen calls
 * drawButton(this, x, y, w, h) for each visible button plate instead of drawTexturedModalRect.
 * The idle plate (texture already bound by the mod) is drawn as before; on top we animate:
 *  - heat rising through the letters (additive emissive layer with a moving vertical front)
 *  - an amber bloom
 *  - ember particles spawned from the letter pixels that drift up and fade
 * Assets live in the mod jar under /assets/custommenu/qf/<name>_{heat,glow,mask}.png.
 * Any failure disables the overlay; the plain plates keep working.
 */
public final class QFButtons {
    /**
     * CustomMenu's buttonTextures order: pairs of (hover, idle) per menu button.
     * Indices 8–9 are null (language button is skipped), so Options/Quit sit at 10–13.
     */
    private static final String[] NAMES = {"publicserver", "single", "multiplayer", "mods", null, "options", "quit"};
    private static final float HOVER_IN = 0.38f, HOVER_OUT = 0.7f;
    private static final float SPAWN_HOVER = 55f, SPAWN_IDLE = 0.35f;   // particles per second
    private static boolean disabled;
    private static int emberTex = -1;
    private static final long T0 = System.nanoTime();
    private static final Random RNG = new Random();
    private static final Map<String, Assets> ASSETS = new HashMap<String, Assets>();
    private static final Map<Long, Button> BUTTONS = new HashMap<Long, Button>();
    /** test hook: when non-null, used instead of the real mouse (gui coords) */
    static int[] debugMouse;

    private QFButtons() {}

    public static void drawButton(MainMenuFix gui, int x, int y, int w, int h, int texIndex) {
        gui.drawTexturedModalRect(x, y, w, h);
        if (disabled) return;
        try {
            overlay(gui, x, y, w, h, texIndex);
        } catch (Throwable t) {
            disabled = true;
            System.err.println("[QFButtons] animated buttons disabled: " + t);
        }
    }

    // ------------------------------------------------------------------ state
    private static final class Particle {
        float x, y, vx, vy, life, age, size, phase;
    }

    private static final class Button {
        final int x, y, w, h;
        final String name;
        float p, lastSeen, spawnAcc;
        final List<Particle> parts = new ArrayList<Particle>();
        Button(int x, int y, int w, int h, String name) { this.x = x; this.y = y; this.w = w; this.h = h; this.name = name; }
    }

    private static final class Assets {
        int heat, glow;
        float[] px, py;   // normalised spawn points inside the letters
    }

    private static float now() { return (System.nanoTime() - T0) / 1.0e9f; }

    private static long key(int x, int y, int idx) { return ((long) x << 40) ^ ((long) y << 20) ^ idx; }

    // ------------------------------------------------------------------ per-frame overlay
    private static void overlay(MainMenuFix gui, int x, int y, int w, int h, int texIndex) throws Exception {
        int slot = texIndex / 2;
        if (slot < 0 || slot >= NAMES.length || NAMES[slot] == null) return;
        float t = now();
        long k = key(x, y, texIndex);
        Button b = BUTTONS.get(k);
        if (b == null) {
            b = new Button(x, y, w, h, NAMES[slot]);
            b.lastSeen = t;
            BUTTONS.put(k, b);
            // forget plates that vanished (window resize)
            for (Iterator<Button> it = BUTTONS.values().iterator(); it.hasNext();) if (t - it.next().lastSeen > 2f) it.remove();
        }
        float dt = Math.max(0f, Math.min(0.1f, t - b.lastSeen));
        b.lastSeen = t;
        Assets a = assets(b.name);
        if (a == null) return;

        int mx, my;
        if (debugMouse != null) { mx = debugMouse[0]; my = debugMouse[1]; }
        else {
            int gw = gui.field_146294_l, gh = gui.field_146295_m;
            mx = Mouse.getX() * gw / Math.max(1, Display.getWidth());
            my = gh - Mouse.getY() * gh / Math.max(1, Display.getHeight()) - 1;
        }
        boolean hover = mx >= x && mx < x + w && my >= y && my < y + h;
        b.p += hover ? dt / HOVER_IN : -dt / HOVER_OUT;
        b.p = Math.max(0f, Math.min(1f, b.p));
        float e = b.p * b.p * (3 - 2 * b.p);

        // particles
        float rate = SPAWN_IDLE + SPAWN_HOVER * e;
        b.spawnAcc += rate * dt;
        while (b.spawnAcc >= 1f && a.px.length > 0) {
            b.spawnAcc -= 1f;
            int i = RNG.nextInt(a.px.length);
            Particle p = new Particle();
            p.x = x + a.px[i] * w; p.y = y + a.py[i] * h;
            p.vx = (RNG.nextFloat() - 0.5f) * 4f;
            p.vy = -(5f + RNG.nextFloat() * 11f) * (0.6f + 0.4f * e);
            p.life = 1.2f + RNG.nextFloat() * 1.6f;
            p.size = 1.2f + RNG.nextFloat() * 1.9f;
            p.phase = RNG.nextFloat() * 6.28f;
            b.parts.add(p);
        }
        for (Iterator<Particle> it = b.parts.iterator(); it.hasNext();) {
            Particle p = it.next();
            p.age += dt;
            if (p.age >= p.life) { it.remove(); continue; }
            p.x += (p.vx + (float) Math.sin(t * 2.3f + p.phase) * 3f) * dt;
            p.y += p.vy * dt;
            p.vy *= (1f - 0.35f * dt);
        }

        GL11.glPushAttrib(GL11.GL_ENABLE_BIT | GL11.GL_COLOR_BUFFER_BIT | GL11.GL_CURRENT_BIT | GL11.GL_TEXTURE_BIT | GL11.GL_DEPTH_BUFFER_BIT);
        GL11.glEnable(GL11.GL_TEXTURE_2D);
        GL11.glEnable(GL11.GL_BLEND);
        GL11.glDisable(GL11.GL_DEPTH_TEST);
        GL11.glDisable(GL11.GL_ALPHA_TEST);
        GL11.glBlendFunc(GL11.GL_SRC_ALPHA, GL11.GL_ONE);
        GL11.glShadeModel(GL11.GL_SMOOTH);
        if (e > 0.002f) {
            float pulse = 0.9f + 0.1f * (float) Math.sin(t * 3.1f);
            // heat: front rises from the bottom of the letters as e grows
            float aBot = clamp(e * 1.8f) * pulse, aTop = clamp((e - 0.45f) * 1.8f) * pulse;
            GL11.glBindTexture(GL11.GL_TEXTURE_2D, a.heat);
            GL11.glBegin(GL11.GL_QUADS);
            GL11.glColor4f(1f, 1f, 1f, aTop); GL11.glTexCoord2f(0, 0); GL11.glVertex2f(x, y);
            GL11.glColor4f(1f, 1f, 1f, aBot); GL11.glTexCoord2f(0, 1); GL11.glVertex2f(x, y + h);
            GL11.glColor4f(1f, 1f, 1f, aBot); GL11.glTexCoord2f(1, 1); GL11.glVertex2f(x + w, y + h);
            GL11.glColor4f(1f, 1f, 1f, aTop); GL11.glTexCoord2f(1, 0); GL11.glVertex2f(x + w, y);
            GL11.glEnd();
            // bloom
            float g = e * (0.95f + 0.3f * (float) Math.sin(t * 2.2f + 1f));
            GL11.glBindTexture(GL11.GL_TEXTURE_2D, a.glow);
            GL11.glColor4f(1f, 1f, 1f, g);
            quad(x, y, x + w, y + h);
        }
        // embers
        if (!b.parts.isEmpty()) {
            GL11.glBindTexture(GL11.GL_TEXTURE_2D, ember());
            GL11.glBegin(GL11.GL_QUADS);
            for (Particle p : b.parts) {
                float f = p.age / p.life;                       // 0 new -> 1 dead
                float al = (f < 0.15f ? f / 0.15f : 1f - (f - 0.15f) / 0.85f);
                float r = 1f, gg = 0.72f - 0.5f * f, bb = 0.30f - 0.28f * f;
                float s = p.size * (1f - 0.4f * f);
                GL11.glColor4f(r, gg, bb, al * (0.55f + 0.45f * e));
                GL11.glTexCoord2f(0, 0); GL11.glVertex2f(p.x - s, p.y - s);
                GL11.glTexCoord2f(0, 1); GL11.glVertex2f(p.x - s, p.y + s);
                GL11.glTexCoord2f(1, 1); GL11.glVertex2f(p.x + s, p.y + s);
                GL11.glTexCoord2f(1, 0); GL11.glVertex2f(p.x + s, p.y - s);
            }
            GL11.glEnd();
        }
        GL11.glPopAttrib();
    }

    private static float clamp(float v) { return v < 0 ? 0 : (v > 1 ? 1 : v); }

    private static void quad(float x0, float y0, float x1, float y1) {
        GL11.glBegin(GL11.GL_QUADS);
        GL11.glTexCoord2f(0, 0); GL11.glVertex2f(x0, y0);
        GL11.glTexCoord2f(0, 1); GL11.glVertex2f(x0, y1);
        GL11.glTexCoord2f(1, 1); GL11.glVertex2f(x1, y1);
        GL11.glTexCoord2f(1, 0); GL11.glVertex2f(x1, y0);
        GL11.glEnd();
    }

    // ------------------------------------------------------------------ assets
    private static Assets assets(String name) throws Exception {
        if (ASSETS.containsKey(name)) return ASSETS.get(name);
        Assets a = null;
        BufferedImage heat = read("/assets/custommenu/qf/" + name + "_heat.png");
        BufferedImage glow = read("/assets/custommenu/qf/" + name + "_glow.png");
        BufferedImage mask = read("/assets/custommenu/qf/" + name + "_mask.png");
        if (heat != null && glow != null && mask != null) {
            a = new Assets();
            a.heat = upload(heat);
            a.glow = upload(glow);
            int mw = mask.getWidth(), mh = mask.getHeight();
            int[] px = mask.getRGB(0, 0, mw, mh, null, 0, mw);
            List<float[]> pts = new ArrayList<float[]>();
            Random r = new Random(7);
            for (int tries = 0; tries < 60000 && pts.size() < 1500; tries++) {
                int ix = r.nextInt(mw), iy = r.nextInt(mh);
                if ((px[iy * mw + ix] & 0xFF) > 128) pts.add(new float[]{(ix + 0.5f) / mw, (iy + 0.5f) / mh});
            }
            a.px = new float[pts.size()]; a.py = new float[pts.size()];
            for (int i = 0; i < pts.size(); i++) { a.px[i] = pts.get(i)[0]; a.py[i] = pts.get(i)[1]; }
        }
        ASSETS.put(name, a);
        return a;
    }

    private static BufferedImage read(String path) throws Exception {
        InputStream in = QFButtons.class.getResourceAsStream(path);
        if (in == null) return null;
        try { return ImageIO.read(in); } finally { in.close(); }
    }

    private static int ember() {
        if (emberTex < 0) {
            int s = 32;
            ByteBuffer buf = BufferUtils.createByteBuffer(s * s * 4);
            for (int y = 0; y < s; y++) for (int x = 0; x < s; x++) {
                float dx = (x + 0.5f) / s - 0.5f, dy = (y + 0.5f) / s - 0.5f;
                float d = (float) Math.sqrt(dx * dx + dy * dy) * 2f;
                float al = clamp(1f - d); al = al * al * (3 - 2 * al);
                buf.put((byte) 255).put((byte) 255).put((byte) 255).put((byte) (al * 255));
            }
            buf.flip();
            emberTex = GL11.glGenTextures();
            GL11.glBindTexture(GL11.GL_TEXTURE_2D, emberTex);
            GL11.glTexParameteri(GL11.GL_TEXTURE_2D, GL11.GL_TEXTURE_MIN_FILTER, GL11.GL_LINEAR);
            GL11.glTexParameteri(GL11.GL_TEXTURE_2D, GL11.GL_TEXTURE_MAG_FILTER, GL11.GL_LINEAR);
            GL11.glTexParameteri(GL11.GL_TEXTURE_2D, GL11.GL_TEXTURE_WRAP_S, GL11.GL_CLAMP);
            GL11.glTexParameteri(GL11.GL_TEXTURE_2D, GL11.GL_TEXTURE_WRAP_T, GL11.GL_CLAMP);
            GL11.glTexImage2D(GL11.GL_TEXTURE_2D, 0, GL11.GL_RGBA, s, s, 0, GL11.GL_RGBA, GL11.GL_UNSIGNED_BYTE, buf);
        }
        return emberTex;
    }

    private static int upload(BufferedImage img) {
        int w = img.getWidth(), h = img.getHeight();
        int[] px = img.getRGB(0, 0, w, h, null, 0, w);
        ByteBuffer buf = BufferUtils.createByteBuffer(w * h * 4);
        for (int p : px) buf.put((byte) ((p >> 16) & 255)).put((byte) ((p >> 8) & 255)).put((byte) (p & 255)).put((byte) ((p >> 24) & 255));
        buf.flip();
        int id = GL11.glGenTextures();
        GL11.glBindTexture(GL11.GL_TEXTURE_2D, id);
        GL11.glTexParameteri(GL11.GL_TEXTURE_2D, GL11.GL_TEXTURE_MIN_FILTER, GL11.GL_LINEAR);
        GL11.glTexParameteri(GL11.GL_TEXTURE_2D, GL11.GL_TEXTURE_MAG_FILTER, GL11.GL_LINEAR);
        GL11.glTexParameteri(GL11.GL_TEXTURE_2D, GL11.GL_TEXTURE_WRAP_S, GL11.GL_CLAMP);
        GL11.glTexParameteri(GL11.GL_TEXTURE_2D, GL11.GL_TEXTURE_WRAP_T, GL11.GL_CLAMP);
        GL11.glTexImage2D(GL11.GL_TEXTURE_2D, 0, GL11.GL_RGBA, w, h, 0, GL11.GL_RGBA, GL11.GL_UNSIGNED_BYTE, buf);
        return id;
    }
}
