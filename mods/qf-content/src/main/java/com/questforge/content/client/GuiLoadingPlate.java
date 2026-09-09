package com.questforge.content.client;

import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.FontRenderer;
import net.minecraft.client.gui.GuiDownloadTerrain;
import net.minecraft.client.network.NetHandlerPlayClient;
import net.minecraft.client.renderer.Tessellator;
import net.minecraft.util.ResourceLocation;

import org.lwjgl.opengl.GL11;

import cpw.mods.fml.relauncher.Side;
import cpw.mods.fml.relauncher.SideOnly;

/**
 * The "downloading terrain" screen, with the destination's plate behind it.
 *
 * Extends GuiDownloadTerrain rather than replacing it. That screen is not just a
 * picture: it sends a keep-alive every twenty ticks from updateScreen, and it is
 * dismissed from outside by the net handler once the player spawns. Subclassing
 * inherits both, so only the drawing changes and nothing about the handshake
 * does. drawScreen is overridden without calling super precisely because super
 * is what paints the dirt background over everything.
 */
@SideOnly(Side.CLIENT)
public class GuiLoadingPlate extends GuiDownloadTerrain {

    private final ResourceLocation plate;
    private final String title;

    public GuiLoadingPlate(NetHandlerPlayClient netHandler, ResourceLocation plate, String title) {
        super(netHandler);
        this.plate = plate;
        this.title = title;
    }

    @Override
    public void drawScreen(int mouseX, int mouseY, float partialTicks) {
        Minecraft mc = Minecraft.getMinecraft();

        drawCover(mc);
        drawVignette();
        drawCaption(mc);
    }

    /**
     * Draws the plate scaled to cover the window, cropping the overflow.
     *
     * Letterboxing a 16:9 still onto a window of some other shape would put bars
     * against the frame's own dark edges and read as a bug. Covering crops
     * instead, and the plates were graded with their top eighth and bottom
     * quarter darkened for exactly this -- there is nothing near the edges that
     * cannot be lost.
     */
    private void drawCover(Minecraft mc) {
        int w = this.width;
        int h = this.height;

        float scale = Math.max(w / 16F, h / 9F);
        float drawW = 16F * scale;
        float drawH = 9F * scale;
        float x = (w - drawW) / 2F;
        float y = (h - drawH) / 2F;

        GL11.glDisable(GL11.GL_LIGHTING);
        GL11.glDisable(GL11.GL_FOG);
        GL11.glEnable(GL11.GL_TEXTURE_2D);
        GL11.glColor4f(1F, 1F, 1F, 1F);
        mc.getTextureManager().bindTexture(this.plate);

        Tessellator t = Tessellator.instance;
        t.startDrawingQuads();
        t.addVertexWithUV(x, y + drawH, 0D, 0D, 1D);
        t.addVertexWithUV(x + drawW, y + drawH, 0D, 1D, 1D);
        t.addVertexWithUV(x + drawW, y, 0D, 1D, 0D);
        t.addVertexWithUV(x, y, 0D, 0D, 0D);
        t.draw();
    }

    /** A dark band at the bottom, so the caption sits on something. */
    private void drawVignette() {
        int band = Math.max(48, this.height / 6);
        drawGradientRect(0, this.height - band, this.width, this.height, 0x00000000, 0xB0000000);
    }

    private void drawCaption(Minecraft mc) {
        FontRenderer font = mc.fontRenderer;
        int baseline = this.height - 28;

        if (this.title != null) {
            drawCenteredString(font, this.title, this.width / 2, baseline, 0xFFFFFF);
        }

        // Vanilla's own wording, kept so the screen still says what it is doing.
        drawCenteredString(font, net.minecraft.client.resources.I18n.format("multiplayer.downloadingTerrain"),
                this.width / 2, baseline + 12, 0xA0A0A0);
    }
}
