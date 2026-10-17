package com.questforge.content.debug;

import java.awt.image.BufferedImage;
import java.io.File;
import java.nio.ByteBuffer;

import javax.imageio.ImageIO;

import net.minecraft.client.Minecraft;
import net.minecraft.client.renderer.OpenGlHelper;
import net.minecraft.client.shader.Framebuffer;

import org.lwjgl.BufferUtils;
import org.lwjgl.opengl.GL11;

import com.questforge.content.jukebox.JukeboxModel;
import com.questforge.content.jukebox.RenderJukebox;

import cpw.mods.fml.common.gameevent.TickEvent;
import cpw.mods.fml.common.eventhandler.SubscribeEvent;
import cpw.mods.fml.relauncher.Side;
import cpw.mods.fml.relauncher.SideOnly;

/**
 * Renders the jukebox model once, off screen, to a transparent PNG.
 *
 * The inventory icon is that picture scaled down. Drawing the live model into a
 * slot gives a 48-pixel cabinet whose braid and analyser shimmer from one frame
 * to the next; a 1024-pixel render filtered down once is the same model, held
 * still and clean. -Dqf.iconbake=<file> asks for it; it runs once a world is
 * up, so the lightmap and every sheet exist, and the game carries on after.
 */
@SideOnly(Side.CLIENT)
public class IconBake {

    private static final String OUT = System.getProperty("qf.iconbake", "");
    private static final int SIZE = 1024;

    private boolean done;
    private int ticks;

    public static boolean enabled() {
        return !OUT.isEmpty();
    }

    @SubscribeEvent
    public void onRender(TickEvent.RenderTickEvent event) {
        if (done || event.phase != TickEvent.Phase.END) return;
        Minecraft mc = Minecraft.getMinecraft();
        if (mc.theWorld == null || ++ticks < 120) return;
        done = true;
        try {
            bake(mc, event.renderTickTime);
            System.out.println("[IconBake] wrote " + OUT);
        } catch (Throwable t) {
            System.out.println("[IconBake] FAILED: " + t);
            t.printStackTrace();
        }
    }

    private static void bake(Minecraft mc, float partial) throws Exception {
        Framebuffer fb = new Framebuffer(SIZE, SIZE, true);
        fb.setFramebufferColor(0F, 0F, 0F, 0F);
        fb.framebufferClear();
        fb.bindFramebuffer(true);

        GL11.glMatrixMode(GL11.GL_PROJECTION);
        GL11.glPushMatrix();
        GL11.glLoadIdentity();
        GL11.glOrtho(-1.05, 1.05, -1.05, 1.05, -10, 10);
        GL11.glMatrixMode(GL11.GL_MODELVIEW);
        GL11.glPushMatrix();
        GL11.glLoadIdentity();

        // A product shot: a little from above and off to the right, so the
        // wood of one side shows and the cabinet reads as a solid, not a card.
        GL11.glRotatef(10F, 1F, 0F, 0F);
        GL11.glRotatef(-24F, 0F, 1F, 0F);
        GL11.glTranslatef(0F, -0.95F, 0F);
        // The front faces -Z in model space; turn it to the camera.
        GL11.glRotatef(180F, 0F, 1F, 0F);
        GL11.glTranslatef(-0.5F, 0F, -0.5F);

        GL11.glEnable(GL11.GL_DEPTH_TEST);
        GL11.glDepthMask(true);
        GL11.glDisable(GL11.GL_BLEND);
        GL11.glEnable(GL11.GL_ALPHA_TEST);
        GL11.glAlphaFunc(GL11.GL_GREATER, 0.1F);
        GL11.glEnable(GL11.GL_TEXTURE_2D);
        mc.entityRenderer.enableLightmap(partial);
        OpenGlHelper.setLightmapTextureCoords(OpenGlHelper.lightmapTexUnit, 240F, 240F);

        // The analyser mid-song, so the icon shows what the thing is for.
        float[] bars = new float[JukeboxModel.BARS];
        for (int i = 0; i < bars.length; i++) {
            double f = (double) i / (bars.length - 1);
            bars[i] = (float) (0.28 + 0.36 * Math.pow(Math.sin(f * Math.PI), 0.8)
                    * (0.62 + 0.38 * Math.sin(f * 23.0) * Math.cos(f * 9.0)));
        }
        RenderJukebox.pose(bars, 0.65F);
        RenderJukebox.draw(JukeboxModel.LIT, 3.4F, 0F, 0);

        mc.entityRenderer.disableLightmap(partial);

        ByteBuffer px = BufferUtils.createByteBuffer(SIZE * SIZE * 4);
        GL11.glReadPixels(0, 0, SIZE, SIZE, GL11.GL_RGBA, GL11.GL_UNSIGNED_BYTE, px);

        GL11.glMatrixMode(GL11.GL_PROJECTION);
        GL11.glPopMatrix();
        GL11.glMatrixMode(GL11.GL_MODELVIEW);
        GL11.glPopMatrix();
        fb.unbindFramebuffer();
        fb.deleteFramebuffer();
        mc.getFramebuffer().bindFramebuffer(true);

        BufferedImage img = new BufferedImage(SIZE, SIZE, BufferedImage.TYPE_INT_ARGB);
        for (int y = 0; y < SIZE; y++) {
            for (int x = 0; x < SIZE; x++) {
                int i = ((SIZE - 1 - y) * SIZE + x) * 4;
                int r = px.get(i) & 0xFF, g = px.get(i + 1) & 0xFF;
                int b = px.get(i + 2) & 0xFF, a = px.get(i + 3) & 0xFF;
                img.setRGB(x, y, (a << 24) | (r << 16) | (g << 8) | b);
            }
        }
        File out = new File(OUT);
        out.getAbsoluteFile().getParentFile().mkdirs();
        ImageIO.write(img, "png", out);
    }
}
