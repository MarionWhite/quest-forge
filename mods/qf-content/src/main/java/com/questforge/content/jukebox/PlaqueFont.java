package com.questforge.content.jukebox;

import net.minecraft.client.Minecraft;
import net.minecraft.client.renderer.Tessellator;
import net.minecraft.util.ResourceLocation;
import org.lwjgl.opengl.GL11;

/**
 * The engraving on a record case's plaque.
 *
 * Minecraft's FontRenderer can only draw Minecraft's font, and that face on a
 * brass plaque is the single detail that made the whole case look like a
 * placeholder. So the plaque has a font of its own -- Copperplate, baked to a
 * sheet, which is the face actual award plaques are engraved in.
 *
 * Glyphs sit left-aligned in fixed cells and carry their own advance widths, so
 * the text is proportionally spaced rather than the even-width grid a naive sheet
 * font produces.
 */
public final class PlaqueFont {

    private static final ResourceLocation SHEET =
            new ResourceLocation("qfcontent", "textures/misc/plaque_font.png");

    private static final int FIRST = 32;
    private static final int COLS = 16, CELL = 64;

    /** Where the baseline sits inside a cell, and how tall a capital is. */
    private static final float BASELINE = 46F;
    private static final float CAP = 33F;

    /** Advance per glyph, ascii 32 upward, in cell units. */
    private static final int[] WIDTH = {
        17, 18, 18, 31, 31, 44, 36, 13, 21, 21, 26, 31, 17, 18, 17, 16,
        31, 31, 31, 31, 31, 31, 31, 31, 31, 31, 17, 17, 31, 31, 31, 23,
        31, 34, 36, 36, 36, 34, 31, 36, 39, 18, 26, 34, 31, 41, 39, 39,
        34, 39, 36, 34, 31, 36, 34, 46, 34, 31, 31, 21, 16, 21, 31, 26,
        18, 29, 31, 29, 31, 29, 29, 31, 34, 18, 23, 29, 29, 36, 34, 31,
        29, 31, 31, 29, 26, 34, 29, 39, 29, 29, 29, 21, 13, 21, 31,
    };

    private PlaqueFont() { }

    /** Width of a string in cell units. */
    public static float width(String s) {
        if (s == null) return 0F;
        float w = 0F;
        for (int i = 0; i < s.length(); i++) w += advance(s.charAt(i));
        return w;
    }

    private static int advance(char c) {
        int index = c - FIRST;
        return index < 0 || index >= WIDTH.length ? WIDTH[0] : WIDTH[index];
    }

    /** How far above the baseline a capital reaches, so text can be centred. */
    public static float capHeight() { return CAP; }

    /**
     * Draws a string with its baseline at the origin, reading along +X and
     * upward in +Y, on the plane z = 0. The caller places and scales it.
     */
    public static void draw(String s, int color) {
        if (s == null || s.isEmpty()) return;

        Minecraft.getMinecraft().getTextureManager().bindTexture(SHEET);
        // Engraved letters drawn at a fraction of the sheet's size: sampled
        // point-for-point the serifs break up, so the edges are averaged instead.
        GL11.glTexParameteri(GL11.GL_TEXTURE_2D, GL11.GL_TEXTURE_MIN_FILTER, GL11.GL_LINEAR);
        GL11.glTexParameteri(GL11.GL_TEXTURE_2D, GL11.GL_TEXTURE_MAG_FILTER, GL11.GL_LINEAR);

        GL11.glEnable(GL11.GL_BLEND);
        GL11.glBlendFunc(GL11.GL_SRC_ALPHA, GL11.GL_ONE_MINUS_SRC_ALPHA);

        float r = ((color >> 16) & 0xFF) / 255F;
        float g = ((color >> 8) & 0xFF) / 255F;
        float b = (color & 0xFF) / 255F;
        GL11.glColor4f(r, g, b, 1F);

        // A cell reaches from the baseline up by BASELINE and down by the rest,
        // which is what leaves room for a descender.
        float top = BASELINE;
        float bottom = -(CELL - BASELINE);

        Tessellator t = Tessellator.instance;
        t.startDrawingQuads();

        float pen = 0F;
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);
            int index = c - FIRST;
            if (index < 0 || index >= WIDTH.length) index = 0;

            float u0 = (index % COLS) / (float) COLS;
            float v0 = (index / COLS) / 8F;
            float u1 = u0 + 1F / COLS;
            float v1 = v0 + 1F / 8F;

            t.addVertexWithUV(pen, bottom, 0, u0, v1);
            t.addVertexWithUV(pen + CELL, bottom, 0, u1, v1);
            t.addVertexWithUV(pen + CELL, top, 0, u1, v0);
            t.addVertexWithUV(pen, top, 0, u0, v0);

            pen += advance(c);
        }
        t.draw();

        GL11.glDisable(GL11.GL_BLEND);
        GL11.glColor4f(1F, 1F, 1F, 1F);
    }
}
