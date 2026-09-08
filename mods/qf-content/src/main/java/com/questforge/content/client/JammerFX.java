package com.questforge.content.client;

import java.nio.ByteBuffer;
import java.nio.IntBuffer;

import org.lwjgl.BufferUtils;
import org.lwjgl.opengl.GL11;
import org.lwjgl.opengl.GL12;

import net.minecraft.client.Minecraft;

import cpw.mods.fml.relauncher.Side;
import cpw.mods.fml.relauncher.SideOnly;

/**
 * Jammer's victim-side effect: the world render is genuinely downsampled.
 *
 * 1.7.10 predates shaders in vanilla, so there is no post-processing pass to hook.
 * What there is, is fixed-function OpenGL 1.1, and glCopyTexSubImage2D can read
 * the framebuffer back into a texture. That gives a three-step trick:
 *
 *   1. copy the finished world render into a full-size texture
 *   2. draw that texture into a small corner of the screen with LINEAR filtering,
 *      which makes the hardware average the pixels down for us
 *   3. copy that small region into a second texture and draw it back over the
 *      whole screen with NEAREST filtering, which blows it up blocky
 *
 * Step 2's corner is overwritten by step 3, so nothing of it survives on screen.
 *
 * This runs before the HUD is drawn, so hearts and hotbar stay readable. The
 * point is to make the victim unable to *aim*, not unable to see their health.
 */
@SideOnly(Side.CLIENT)
public class JammerFX {

    /** Written from the netty thread, read from the render thread. */
    private static volatile int factor;
    private static volatile int ticksLeft;

    private static int fullTex = -1;
    private static int smallTex = -1;
    private static int fullW, fullH, smallW, smallH;

    private static final IntBuffer VIEWPORT = BufferUtils.createIntBuffer(16);

    /**
     * A hit landed. Strength is replaced rather than added -- the server already
     * escalated it from the hit streak -- and duration is extended, not stacked,
     * so a long fight cannot leave someone jammed for minutes after it ends.
     */
    public static void apply(int newFactor, int ticks) {
        factor = newFactor;
        if (ticks > ticksLeft) ticksLeft = ticks;
    }

    public static void tick() {
        int t = ticksLeft;
        if (t > 0) ticksLeft = t - 1;
    }

    public static boolean isActive() {
        return ticksLeft > 0 && factor >= 2;
    }

    /** Forget everything on disconnect, so it cannot follow you into another world. */
    public static void clear() {
        ticksLeft = 0;
        factor = 0;
    }

    public static void render() {
        if (!isActive()) return;

        Minecraft mc = Minecraft.getMinecraft();
        if (mc == null || mc.theWorld == null) return;

        VIEWPORT.clear();
        GL11.glGetInteger(GL11.GL_VIEWPORT, VIEWPORT);
        int vx = VIEWPORT.get(0);
        int vy = VIEWPORT.get(1);
        int vw = VIEWPORT.get(2);
        int vh = VIEWPORT.get(3);
        if (vw <= 0 || vh <= 0) return;

        int f = factor;
        int sw = Math.max(1, vw / f);
        int sh = Math.max(1, vh / f);

        if (!ensureTextures(vw, vh, sw, sh)) return;

        // --- set up a plain pixel-space 2D pass -------------------------------
        GL11.glMatrixMode(GL11.GL_PROJECTION);
        GL11.glPushMatrix();
        GL11.glLoadIdentity();
        GL11.glOrtho(0.0D, vw, vh, 0.0D, -1.0D, 1.0D);   // y grows downward
        GL11.glMatrixMode(GL11.GL_MODELVIEW);
        GL11.glPushMatrix();
        GL11.glLoadIdentity();

        GL11.glDisable(GL11.GL_DEPTH_TEST);
        GL11.glDisable(GL11.GL_LIGHTING);
        GL11.glDisable(GL11.GL_BLEND);
        GL11.glDisable(GL11.GL_ALPHA_TEST);
        GL11.glEnable(GL11.GL_TEXTURE_2D);
        GL11.glColor4f(1.0F, 1.0F, 1.0F, 1.0F);

        // 1. grab the world render
        GL11.glBindTexture(GL11.GL_TEXTURE_2D, fullTex);
        GL11.glCopyTexSubImage2D(GL11.GL_TEXTURE_2D, 0, 0, 0, vx, vy, vw, vh);

        // 2. shrink it into the top-left corner; LINEAR does the averaging
        filter(GL11.GL_LINEAR);
        quad(0, 0, sw, sh);

        // 3a. read that corner back. The ortho above puts screen y=0 at the TOP,
        //     but glCopyTexSubImage2D reads in GL's bottom-left origin, so the
        //     corner we just drew sits at framebuffer y = vy + vh - sh.
        GL11.glBindTexture(GL11.GL_TEXTURE_2D, smallTex);
        GL11.glCopyTexSubImage2D(GL11.GL_TEXTURE_2D, 0, 0, 0, vx, vy + vh - sh, sw, sh);

        // 3b. and blow it back up over everything, unsmoothed
        filter(GL11.GL_NEAREST);
        quad(0, 0, vw, vh);

        // --- hand the pipeline back roughly as we found it --------------------
        GL11.glBindTexture(GL11.GL_TEXTURE_2D, 0);
        GL11.glEnable(GL11.GL_BLEND);
        GL11.glEnable(GL11.GL_ALPHA_TEST);
        GL11.glPopMatrix();
        GL11.glMatrixMode(GL11.GL_PROJECTION);
        GL11.glPopMatrix();
        GL11.glMatrixMode(GL11.GL_MODELVIEW);
    }

    /**
     * Draws the bound texture over a pixel rectangle.
     *
     * The v coordinates are inverted because a texture copied from the framebuffer
     * has v=0 at the bottom of the screen, while this projection has y=0 at the top.
     */
    private static void quad(int x0, int y0, int x1, int y1) {
        GL11.glBegin(GL11.GL_QUADS);
        GL11.glTexCoord2f(0.0F, 1.0F); GL11.glVertex2f(x0, y0);
        GL11.glTexCoord2f(0.0F, 0.0F); GL11.glVertex2f(x0, y1);
        GL11.glTexCoord2f(1.0F, 0.0F); GL11.glVertex2f(x1, y1);
        GL11.glTexCoord2f(1.0F, 1.0F); GL11.glVertex2f(x1, y0);
        GL11.glEnd();
    }

    private static void filter(int mode) {
        GL11.glTexParameteri(GL11.GL_TEXTURE_2D, GL11.GL_TEXTURE_MIN_FILTER, mode);
        GL11.glTexParameteri(GL11.GL_TEXTURE_2D, GL11.GL_TEXTURE_MAG_FILTER, mode);
    }

    /** Allocates or reallocates both scratch textures. Sizes change when the window does. */
    private static boolean ensureTextures(int vw, int vh, int sw, int sh) {
        if (fullTex == -1) fullTex = GL11.glGenTextures();
        if (smallTex == -1) smallTex = GL11.glGenTextures();
        if (fullTex == 0 || smallTex == 0) return false;

        if (fullW != vw || fullH != vh) {
            allocate(fullTex, vw, vh);
            fullW = vw;
            fullH = vh;
        }
        if (smallW != sw || smallH != sh) {
            allocate(smallTex, sw, sh);
            smallW = sw;
            smallH = sh;
        }
        return true;
    }

    private static void allocate(int tex, int w, int h) {
        GL11.glBindTexture(GL11.GL_TEXTURE_2D, tex);
        GL11.glTexImage2D(GL11.GL_TEXTURE_2D, 0, GL11.GL_RGB, w, h, 0,
                GL11.GL_RGB, GL11.GL_UNSIGNED_BYTE, (ByteBuffer) null);
        GL11.glTexParameteri(GL11.GL_TEXTURE_2D, GL11.GL_TEXTURE_WRAP_S, GL12.GL_CLAMP_TO_EDGE);
        GL11.glTexParameteri(GL11.GL_TEXTURE_2D, GL11.GL_TEXTURE_WRAP_T, GL12.GL_CLAMP_TO_EDGE);
        filter(GL11.GL_NEAREST);
    }
}
