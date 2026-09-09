package com.questforge.content.client;

import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.FontRenderer;
import net.minecraft.client.gui.GuiDownloadTerrain;
import net.minecraft.client.network.NetHandlerPlayClient;
import net.minecraft.client.gui.ScaledResolution;
import net.minecraft.client.renderer.Tessellator;
import net.minecraft.client.renderer.texture.SimpleTexture;
import net.minecraft.client.renderer.texture.TextureManager;
import net.minecraft.util.ResourceLocation;

import org.lwjgl.opengl.GL11;
import org.lwjgl.opengl.GL12;

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

    /** Set when this screen's art could not be loaded; see drawCover. */
    private boolean coverUnavailable;

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
     * Draws the plate at the display's real resolution, not the GUI's.
     *
     * GuiScreen.width and height are in GUI units, not pixels. At the default
     * "Auto" gui scale a 2560x1440 display reports width=640, so drawing the
     * plate against those numbers rasterises it at 640x360 and lets the GUI
     * projection blow it up fourfold. Shipping a 2560 source made no difference
     * whatsoever, because the resampling happened before the texture was ever
     * sampled -- which is how a full-resolution image ends up looking like a
     * thumbnail.
     *
     * So the GUI scale is undone for this one quad: scale the matrix by its
     * reciprocal and draw across mc.displayWidth by mc.displayHeight, which are
     * actual pixels. Captions are left in GUI space, where being scaled is the
     * point.
     *
     * Filtering is set to LINEAR for the same reason RenderRecordCase does it.
     * Minecraft's default is NEAREST, which is right for pixel art and wrong for
     * a photograph -- at any scale but exactly 1:1 it turns gradients into
     * stair-steps.
     */
    private void drawCover(Minecraft mc) {
        ScaledResolution res = new ScaledResolution(mc, mc.displayWidth, mc.displayHeight);
        int factor = Math.max(1, res.getScaleFactor());

        int pw = mc.displayWidth;
        int ph = mc.displayHeight;

        float scale = Math.max(pw / 16F, ph / 9F);
        float drawW = 16F * scale;
        float drawH = 9F * scale;
        float x = (pw - drawW) / 2F;
        float y = (ph - drawH) / 2F;

        GL11.glDisable(GL11.GL_LIGHTING);
        GL11.glDisable(GL11.GL_FOG);
        GL11.glEnable(GL11.GL_TEXTURE_2D);
        GL11.glColor4f(1F, 1F, 1F, 1F);

        // bindTexture hides failure: a plate that misses once is remembered as
        // the missing-texture checkerboard and never retried, so a single
        // transient miss -- a resource reload racing a dimension change, which
        // shader packs cause -- leaves that dimension's art broken until the
        // game restarts. Load it explicitly instead, and on failure drop the
        // placeholder so the next dimension change gets a clean attempt.
        // Meanwhile draw no cover at all, which reads as a plain loading
        // screen rather than as a corrupted one.
        if (this.coverUnavailable) {
            return;
        }

        TextureManager textures = mc.getTextureManager();

        if (textures.getTexture(this.plate) == null
                && !textures.loadTexture(this.plate, new SimpleTexture(this.plate))) {
            textures.deleteTexture(this.plate);
            this.coverUnavailable = true;
            return;
        }

        textures.bindTexture(this.plate);

        GL11.glTexParameteri(GL11.GL_TEXTURE_2D, GL11.GL_TEXTURE_MIN_FILTER, GL11.GL_LINEAR);
        GL11.glTexParameteri(GL11.GL_TEXTURE_2D, GL11.GL_TEXTURE_MAG_FILTER, GL11.GL_LINEAR);
        // The plate is drawn edge to edge, so sampling must not wrap round and
        // fetch the opposite side along the seam.
        GL11.glTexParameteri(GL11.GL_TEXTURE_2D, GL11.GL_TEXTURE_WRAP_S, GL12.GL_CLAMP_TO_EDGE);
        GL11.glTexParameteri(GL11.GL_TEXTURE_2D, GL11.GL_TEXTURE_WRAP_T, GL12.GL_CLAMP_TO_EDGE);

        GL11.glPushMatrix();
        GL11.glScalef(1F / factor, 1F / factor, 1F);

        Tessellator t = Tessellator.instance;
        t.startDrawingQuads();
        t.addVertexWithUV(x, y + drawH, 0D, 0D, 1D);
        t.addVertexWithUV(x + drawW, y + drawH, 0D, 1D, 1D);
        t.addVertexWithUV(x + drawW, y, 0D, 1D, 0D);
        t.addVertexWithUV(x, y, 0D, 0D, 0D);
        t.draw();

        GL11.glPopMatrix();
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
