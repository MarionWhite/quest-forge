package com.questforge.content.jukebox;

import cpw.mods.fml.relauncher.Side;
import cpw.mods.fml.relauncher.SideOnly;

import net.minecraft.client.renderer.Tessellator;
import net.minecraft.util.ResourceLocation;

import org.lwjgl.opengl.GL11;

/**
 * The jukebox's geometry: a Wurlitzer 1015 bubbler, built to the reference.
 *
 * Seven things make that cabinet recognisable, and it is worth naming them
 * because a model with six of them reads as "a jukebox" rather than as this one:
 *
 * <ol>
 *   <li>a broad arch <em>band</em> -- not tubes -- graduating red to violet,</li>
 *   <li>the chevron fin at the crown, slatted chrome pointing down,</li>
 *   <li>ring-stack capitals where the arch lands on the columns,</li>
 *   <li>rainbow tubes running the whole height below those capitals,</li>
 *   <li>a slatted selector display with coloured lamps, under the apex,</li>
 *   <li>an arch-topped window: lit title strip over gold scrollwork,</li>
 *   <li>ribbed chrome coils flanking the foot of the window.</li>
 * </ol>
 *
 * The arch is an ellipse rather than a semicircle. The real one is appreciably
 * taller than it is round, and drawing it as half a circle is most of why an
 * approximation of this cabinet looks like a wardrobe with a rainbow on it.
 *
 * <h3>Winding, and the black panel</h3>
 * Every front face here is wound the same way: bottom-left, top-left, top-right,
 * bottom-right. That is not housekeeping. Under Sildur's Vibrant the old lit
 * panel rendered pure black while the cabinet face beside it -- same sheet, same
 * brightness, same pass -- rendered fine, and the one difference between them was
 * that they were wound opposite ways. A deferred pack renders its own shadow
 * pass, and a face wound the other way is the one that survives it.
 *
 * <h3>Everything here is opaque</h3>
 * A deferred pack's geometry stage writes albedo into a G-buffer and cannot
 * blend, so the neon is not a glow laid over the cabinet: it is solid geometry.
 * Every quad carries UVs and a texture stays bound even for flat colour -- an
 * untextured quad samples whatever sheet happens to be bound at coordinates it
 * never set, and renders black. Flat colour binds {@code misc/white.png}.
 */
@SideOnly(Side.CLIENT)
public final class JukeboxModel {

    private static ResourceLocation tex(String name) {
        return new ResourceLocation("qfcontent", "textures/entity/" + name + ".png");
    }

    public static final ResourceLocation CABINET = tex("jukebox_cabinet");
    public static final ResourceLocation WINDOW = tex("jukebox_window");
    public static final ResourceLocation CHROME = tex("jukebox_chrome");
    public static final ResourceLocation ARCH = tex("jukebox_arch");
    public static final ResourceLocation TUBE_LEFT = tex("jukebox_tube_l");
    public static final ResourceLocation TUBE_RIGHT = tex("jukebox_tube_r");
    public static final ResourceLocation CAP = tex("jukebox_cap");
    public static final ResourceLocation DISPLAY = tex("jukebox_display");
    public static final ResourceLocation COIL = tex("jukebox_coil");
    public static final ResourceLocation ENV = tex("jukebox_env");
    public static final ResourceLocation FRONT = tex("jukebox_front");
    public static final ResourceLocation STRIP = tex("jukebox_strip");
    public static final ResourceLocation CHAMBER = tex("jukebox_chamber");
    public static final ResourceLocation SHOULDER = tex("jukebox_shoulder");
    public static final ResourceLocation PANEL_SIDE = tex("jukebox_panel_side");
    public static final ResourceLocation PANEL_BACK = tex("jukebox_panel_back");
    public static final ResourceLocation GLASS = tex("jukebox_glass");
    /** One per {@link ItemVinyl} tier, in the same order the item uses. */
    private static final String[] DISC_NAME = { "black", "silver", "gold", "platinum" };
    private static final ResourceLocation[] DISCS = new ResourceLocation[4];

    static {
        for (int i = 0; i < DISCS.length; i++) {
            DISCS[i] = new ResourceLocation(
                    "qfcontent", "textures/misc/record_" + DISC_NAME[i] + ".png");
        }
    }

    public static ResourceLocation disc(int tier) {
        return DISCS[tier < 0 ? 0 : tier >= DISCS.length ? 0 : tier];
    }
    public static final ResourceLocation HARDWARE = tex("jukebox_hardware");
    public static final ResourceLocation WHITE =
            new ResourceLocation("qfcontent", "textures/misc/white.png");

    /** Full daylight, both channels. What every lit part is drawn at. */
    public static final int LIT = 0xF000F0;

    // ------------------------------------------------------------------
    // Proportions, measured off the reference. Front face is -Z.
    // ------------------------------------------------------------------

    public static final float HEIGHT = 1.94F;

    private static final float X0 = 0.110F, X1 = 0.890F;   // cabinet sides
    private static final float CAB_Z = 0.240F;             // cabinet front plane
    private static final float BACK_Z = 0.865F;

    /** The plane the lit work stands on, well proud of the cabinet face. */
    private static final float FZ = 0.150F;

    private static final float BASE_TOP = 0.160F;
    private static final float TUBE_TOP = 1.050F;          // rainbow columns end
    private static final float CAP_TOP = 1.360F;           // ring stacks end
    private static final float SPRING_Y = CAP_TOP;         // the arch lands here

    /**
     * The arch, as an ellipse. Two of them, and the difference matters.
     *
     * ARCH_A/ARCH_B are the cabinet's outer silhouette -- the shoulder. The band
     * of neon runs along a second, smaller ellipse whose centreline passes
     * directly over the columns, because the band and the columns are one
     * continuous run of tube in the reference and anything else reads as a
     * mistake. Deriving the arch from the cabinet edge and the columns from their
     * own constant is exactly how they came to be a couple of centimetres apart.
     */
    private static final float ARCH_A = 0.390F;            // horizontal semi-axis
    private static final float ARCH_B = 0.520F;            // vertical semi-axis
    private static final int ARCH_STEPS = 56;

    /** Half the width of the neon band; the capitals match it. */
    private static final float ARCH_HALF = 0.065F;
    /** Centreline of the band -- and therefore where the columns stand. */
    private static final float ARCH_MID_A = 0.325F;
    private static final float ARCH_MID_B = ARCH_MID_A * (ARCH_B / ARCH_A);

    /** The two columns. */
    /** Directly under the arch band's centreline. Not a number of its own. */
    private static final float COL_X = 0.5F - ARCH_MID_A;
    private static final float COL_R = 0.050F;
    private static final float CAP_R = ARCH_HALF;
    private static final int COL_SIDES = 24;

    /** The window: arch-topped, chrome-framed. */
    private static final float WIN_X0 = 0.340F, WIN_X1 = 0.660F;
    private static final float WIN_Y0 = 0.300F, WIN_Y1 = 0.900F;
    private static final float WIN_ARCH = 0.100F;          // how far the top rounds
    private static final float STRIP_Y0 = 0.925F, STRIP_Y1 = 1.025F;

    /**
     * The mechanism well: a glazed opening with the record turning behind it.
     *
     * This is the upper half of the front, which was a slatted selector panel --
     * a lot of frontage spent on something you cannot read from two blocks away.
     * A deck you can watch is what the space is for.
     */
    /**
     * The deck bay, dropped into the body rather than up under the arch.
     *
     * A record lying flat needs real depth -- twice its radius of it -- and up
     * under the arch there was nowhere to put that: the bay could only be a
     * finger deep before it ran into the shoulder, so the disc had to stand on
     * edge like a picture. Down here the cabinet is more than half a block deep
     * and the only thing in front of the bay is the front panel, which is one
     * quad and can simply be cut around it.
     */
    private static final float WELL_X0 = 0.300F, WELL_X1 = 0.700F;
    private static final float WELL_Y0 = 1.060F, WELL_Y1 = 1.350F;
    /**
     * The well is a bezel standing proud of the cabinet, not a hole in it.
     *
     * Recessing it behind CAB_Z put the record inside solid geometry: the
     * shoulder's front cheek is a filled fan across the whole arch and the front
     * panel covers everything below it, so the mechanism was drawn correctly and
     * then buried. Cutting an opening through a fan is fiddly; standing the well
     * in front of the face costs nothing and is what the real cabinet does with
     * its glass anyway.
     */
    private static final float WELL_MOUTH = FZ;                  // front of bezel
    // Clear of the front panel, which sits at CAB_Z - 0.006. At CAB_Z - 0.005 the
    // back wall was a thousandth behind it and the well showed wood, not chamber.
    private static final float WELL_BACK = 0.520F;               // deep enough to lie flat

    /** The disc itself, and where the arm comes down on it. */
    /** The deck: where the platter sits, and how far it leans back. */
    public static final float DECK_X = 0.5F;
    public static final float DECK_Y = 1.205F;
    public static final float DECK_Z = 0.320F;
    /** Degrees from vertical. At 0 the disc faces you; at 90 it is dead flat and
     *  invisible through a vertical window. This leans it back far enough to read
     *  as lying down while still showing its face. */
    public static final float DECK_TILT = 42F;
    public static final float DISC_R = 0.128F;


    /** The chevron fin at the crown. */
    private static final float FIN_Y0 = 1.600F, FIN_Y1 = 1.842F;
    private static final float FIN_HALF = 0.046F;

    /**
     * The coils at the foot of the window.
     *
     * They splay: narrow at the top, wider at the foot, the way the stand under
     * a real cabinet's centre panel does. Vertical cylinders of forty
     * thousandths read as two fat pipes bolted on, which is exactly what they
     * looked like.
     */
    private static final float COIL_TOP_X = 0.418F;        // and mirrored
    private static final float COIL_BOT_X = 0.392F;
    private static final float COIL_Y0 = 0.318F, COIL_Y1 = 0.520F;
    private static final float COIL_R = 0.019F;

    // ------------------------------------------------------------------
    // Colour
    // ------------------------------------------------------------------

    /** The arch, left leg to right: red, orange, amber, white, pink, violet. */
    private static final float[][] ARCH_RAMP = {
            { 0.80F, 0.07F, 0.10F }, { 1.00F, 0.26F, 0.05F },
            { 1.00F, 0.50F, 0.06F }, { 1.00F, 0.76F, 0.18F },
            { 1.00F, 0.70F, 0.60F }, { 1.00F, 0.30F, 0.62F },
            { 0.90F, 0.12F, 0.55F }, { 0.58F, 0.10F, 0.62F },
    };

    /** The left tube, top to bottom. The right one is the pink counterpart. */
    private static final float[][] TUBE_L = {
            { 1.00F, 0.55F, 0.16F }, { 1.00F, 0.84F, 0.31F },
            { 0.51F, 0.90F, 0.51F }, { 0.31F, 0.84F, 0.94F },
            { 0.27F, 0.59F, 0.92F },
    };
    private static final float[][] TUBE_R = {
            { 1.00F, 0.47F, 0.78F }, { 0.96F, 0.27F, 0.65F },
            { 1.00F, 0.75F, 0.88F }, { 0.59F, 0.43F, 0.94F },
            { 0.35F, 0.71F, 0.94F },
    };

    private static final float[] CHROME_C = { 0.80F, 0.83F, 0.89F };
    private static final float[] CAP_GLOW = { 1.00F, 0.58F, 0.16F };
    private static final float[] DARK = { 0.075F, 0.068F, 0.078F };

    /** The cabinet's own colour, over the walnut sheet. Dark, but still wood. */
    private static final float[] WOOD = { 0.92F, 0.86F, 0.82F };
    private static final float[] WOOD_DEEP = { 0.66F, 0.60F, 0.57F };

    /** The lamps across the selector display. */
    private static final float[][] LAMPS = {
            { 1.00F, 0.22F, 0.18F }, { 1.00F, 0.80F, 0.20F },
            { 0.35F, 0.95F, 0.40F }, { 0.30F, 0.70F, 1.00F },
            { 1.00F, 0.45F, 0.85F }, { 1.00F, 0.92F, 0.55F },
    };

    private static final int ARCH_SIDES = 14;
    private static final float[] ASIN = new float[ARCH_SIDES + 1];
    private static final float[] ACOS = new float[ARCH_SIDES + 1];
    private static final float[] CSIN = new float[COL_SIDES + 1];
    private static final float[] CCOS = new float[COL_SIDES + 1];

    static {
        for (int i = 0; i <= ARCH_SIDES; i++) {
            double a = i * 2.0 * Math.PI / ARCH_SIDES;
            ASIN[i] = (float) Math.sin(a);
            ACOS[i] = (float) Math.cos(a);
        }
        for (int i = 0; i <= COL_SIDES; i++) {
            double a = i * 2.0 * Math.PI / COL_SIDES;
            CSIN[i] = (float) Math.sin(a);
            CCOS[i] = (float) Math.cos(a);
        }
    }

    private JukeboxModel() { }

    // ------------------------------------------------------------------
    // Primitives
    // ------------------------------------------------------------------

    private static void v(Tessellator t, float x, float y, float z, float u, float w) {
        t.addVertexWithUV(x, y, z, u, w);
    }

    private static void colour(Tessellator t, float[] c, float f) {
        t.setColorRGBA_F(c[0] * f, c[1] * f, c[2] * f, 1F);
    }

    /**
     * A front-facing quad, in the winding every front face here uses.
     *
     * Bottom-left, top-left, top-right, bottom-right. See the class note: the
     * other winding is the one a deferred pack renders black.
     */
    private static void faceZ(Tessellator t, float x0, float y0, float x1, float y1,
                              float z, float u0, float v0, float u1, float v1) {
        t.setNormal(0F, 0F, -1F);
        v(t, x0, y0, z, u0, v1);
        v(t, x0, y1, z, u0, v0);
        v(t, x1, y1, z, u1, v0);
        v(t, x1, y0, z, u1, v1);
    }

    /** A cuboid, shaded by face because these renderers draw with lighting off. */
    private static void box(Tessellator t, float[] c,
                            float x0, float y0, float z0,
                            float x1, float y1, float z1) {
        colour(t, c, 1.00F);
        t.setNormal(0F, 1F, 0F);
        v(t, x0, y1, z1, 0F, 1F); v(t, x1, y1, z1, 1F, 1F);
        v(t, x1, y1, z0, 1F, 0F); v(t, x0, y1, z0, 0F, 0F);

        colour(t, c, 0.55F);
        t.setNormal(0F, -1F, 0F);
        v(t, x0, y0, z0, 0F, 0F); v(t, x1, y0, z0, 1F, 0F);
        v(t, x1, y0, z1, 1F, 1F); v(t, x0, y0, z1, 0F, 1F);

        colour(t, c, 0.88F);
        faceZ(t, x0, y0, x1, y1, z0, 0F, 0F, 1F, 1F);

        colour(t, c, 0.74F);
        t.setNormal(0F, 0F, 1F);
        v(t, x1, y0, z1, 0F, 1F); v(t, x1, y1, z1, 0F, 0F);
        v(t, x0, y1, z1, 1F, 0F); v(t, x0, y0, z1, 1F, 1F);

        colour(t, c, 0.84F);
        t.setNormal(-1F, 0F, 0F);
        v(t, x0, y0, z1, 0F, 1F); v(t, x0, y1, z1, 0F, 0F);
        v(t, x0, y1, z0, 1F, 0F); v(t, x0, y0, z0, 1F, 1F);
        t.setNormal(1F, 0F, 0F);
        v(t, x1, y0, z0, 0F, 1F); v(t, x1, y1, z0, 0F, 0F);
        v(t, x1, y1, z1, 1F, 0F); v(t, x1, y0, z1, 1F, 1F);
    }

    /** Samples a ramp with smooth steps, clamped at both ends. */
    private static float[] ramp(float[][] stops, float f) {
        if (f <= 0F) return stops[0];
        if (f >= 1F) return stops[stops.length - 1];
        float p = f * (stops.length - 1);
        int i = (int) p;
        float k = p - i;
        k = k * k * (3F - 2F * k);
        float[] a = stops[i], b = stops[i + 1];
        return new float[] { a[0] + (b[0] - a[0]) * k,
                             a[1] + (b[1] - a[1]) * k,
                             a[2] + (b[2] - a[2]) * k };
    }

    /**
     * A vertical prism, textured round its circumference.
     *
     * U runs once around the tube with the seam at the back, so the sheet's
     * cylindrical falloff and its specular streak land on the face you actually
     * see. V runs along the length, which is where the colour ramp lives. No
     * per-facet tinting: the shading is already in the sheet, and doing it twice
     * is what makes a lit object look like painted plastic.
     */
    private static void tube(Tessellator t, float cx, float cz, float r,
                             float y0, float y1) {
        tube(t, cx, cz, r, y0, y1, 1F, 0F);
    }

    /**
     * A prism, with the sheet's V range given rather than assumed.
     *
     * Drawing a column in courses so the light can travel up it means each
     * course used to remap the whole sheet over itself -- sixteen copies of the
     * gradient stacked up the tube, which is the banding.
     */
    private static void tube(Tessellator t, float cx, float cz, float r,
                             float y0, float y1, float va, float vb) {
        tube(t, cx, cz, r, y0, y1, va, vb, -1F, -1F);
    }

    /**
     * As above, but lit from ga at the bottom to gb at the top.
     *
     * A course drawn at one brightness is a flat band, and sixteen of them
     * stacked up a column is a ladder rather than light running through glass.
     */
    private static void tube(Tessellator t, float cx, float cz, float r,
                             float y0, float y1, float va, float vb,
                             float ga, float gb) {
        for (int i = 0; i < COL_SIDES; i++) {
            float ax = cx + CCOS[i] * r, az = cz + CSIN[i] * r;
            float bx = cx + CCOS[i + 1] * r, bz = cz + CSIN[i + 1] * r;
            float u0 = seam(i), u1 = seam(i + 1);
            // The wrap point would otherwise stretch the whole sheet backwards
            // across one facet.
            if (u1 < u0) u1 += 1F;
            t.setNormal(CCOS[i], 0F, CSIN[i]);
            float sh = 0.70F + 0.30F * Math.max(0F, -CSIN[i]);
            if (ga >= 0F) { float g = ga * sh; t.setColorRGBA_F(g, g, g, 1F); }
            v(t, ax, y0, az, u0, va);
            if (gb >= 0F) { float g = gb * sh; t.setColorRGBA_F(g, g, g, 1F); }
            v(t, ax, y1, az, u0, vb);
            v(t, bx, y1, bz, u1, vb);
            if (ga >= 0F) { float g = ga * sh; t.setColorRGBA_F(g, g, g, 1F); }
            v(t, bx, y0, bz, u1, va);
        }
    }

    /** U around the tube, with 0.5 facing the viewer and the seam at the back. */
    private static float seam(int i) {
        float u = (float) i / COL_SIDES - 0.25F;
        return u - (float) Math.floor(u);
    }

    /** The capitals and the coils are the same prism with a different sheet. */
    private static void sleeve(Tessellator t, float cx, float cz, float r,
                               float y0, float y1) {
        t.setColorRGBA_F(1F, 1F, 1F, 1F);
        tube(t, cx, cz, r, y0, y1);
    }

    // ------------------------------------------------------------------
    // The passes
    // ------------------------------------------------------------------

    /**
     * The carcass: a plinth, a body with rounded corners, and a domed shoulder.
     *
     * The body was a box multiplied by {@code DARK} -- 0.075 -- which painted a
     * lacquered walnut sheet solid black and made the whole cabinet read as a
     * hole rather than as furniture. It is wood now, and it has no square
     * vertical edges: the corners are generous radii, which is most of what says
     * "cabinet" rather than "crate with a picture on the front", and it is the
     * only place the lacquer has to catch light. A highlight rolling round a
     * corner is the entire reason black can read as polished.
     */
    /**
     * The face under the arch: plain black glass.
     *
     * Drawn self-lit even though nothing behind it glows. What shows on black
     * glass is its reflection, and what it reflects is the neon arch a finger's
     * width in front of it -- lit by the room, the shader pack crushed it to
     * flat paint. The sheet is all near-black but the sheen, so it stays dark.
     */
    public static void shoulderFace(Tessellator t, int light) {
        bright(t, LIT);
        shoulder(t, true);
    }

    /**
     * The veneered panels let into the sides and back of the body.
     *
     * Each sits between the two mouldings and inside the rounded corners, a
     * whisker proud of the carcass, the way a real panel is laid onto a ground.
     * Shaded down its height from top to foot so it takes the same fall of light
     * as the burl round it, rather than sitting on it like a flat sticker.
     */
    public static void sidePanels(Tessellator t, int light) {
        bright(t, light);
        final float y0 = BASE_TOP + 0.058F, y1 = SPRING_Y - 0.062F;
        final float z0 = CAB_Z + CORNER + 0.006F, z1 = BACK_Z - CORNER - 0.006F;
        final float e = 0.0025F;
        float xl = X0 - e, xr = X1 + e;

        t.setNormal(-1F, 0F, 0F);
        shade(t, 0.80F); v(t, xl, y0, z1, 0F, 1F);
        shade(t, 1.00F); v(t, xl, y1, z1, 0F, 0F);
                          v(t, xl, y1, z0, 1F, 0F);
        shade(t, 0.80F); v(t, xl, y0, z0, 1F, 1F);

        t.setNormal(1F, 0F, 0F);
        shade(t, 0.80F); v(t, xr, y0, z0, 0F, 1F);
        shade(t, 1.00F); v(t, xr, y1, z0, 0F, 0F);
                          v(t, xr, y1, z1, 1F, 0F);
        shade(t, 0.80F); v(t, xr, y0, z1, 1F, 1F);
        t.setColorRGBA_F(1F, 1F, 1F, 1F);
    }

    public static void backPanel(Tessellator t, int light) {
        bright(t, light);
        final float y0 = BASE_TOP + 0.058F, y1 = SPRING_Y - 0.062F;
        final float x0 = X0 + CORNER + 0.006F, x1 = X1 - CORNER - 0.006F;
        final float z = BACK_Z + 0.0025F;
        t.setNormal(0F, 0F, 1F);
        shade(t, 0.66F); v(t, x1, y0, z, 0F, 1F);
        shade(t, 0.84F); v(t, x1, y1, z, 0F, 0F);
                          v(t, x0, y1, z, 1F, 0F);
        shade(t, 0.66F); v(t, x0, y0, z, 1F, 1F);
        t.setColorRGBA_F(1F, 1F, 1F, 1F);
    }

    private static void shade(Tessellator t, float f) {
        t.setColorRGBA_F(f, f, f, 1F);
    }

    public static void cabinet(Tessellator t, int light) {
        bright(t, light);
        box(t, WOOD_DEEP, X0 - 0.02F, 0F, CAB_Z - 0.03F,
            X1 + 0.02F, BASE_TOP, BACK_Z + 0.02F);
        roundedBody(t, BASE_TOP, SPRING_Y);
        shoulder(t, false);
    }

    /** How far the vertical corners are rounded off, and in how many steps. */
    private static final float CORNER = 0.085F;
    private static final int CORNER_STEPS = 6;

    /**
     * The body, as a vertical extrusion of a rounded rectangle.
     *
     * Shaded down its height as well as face to face, so light falls the way it
     * does on a real cabinet instead of each side being one flat value.
     */
    /** Blocks of cabinet per repeat of the wood sheet. */
    private static final float GRAIN = 0.80F;

    private static void roundedBody(Tessellator t, float y0, float y1) {
        float[][] ring = roundedRect(X0, CAB_Z, X1, BACK_Z, CORNER, CORNER_STEPS);
        final int n = ring.length;

        // Row boundaries land exactly on the bay, so its opening can be cut
        // without a seam running across the rest of the cabinet.
        final float[] cuts = { y0, WELL_Y0, WELL_Y1, y1 };
        final int per = 2;
        final int rows = (cuts.length - 1) * per;

        // Texture coordinates from real distance, not from facet index. Mapping
        // each row to a full 0..1 of V put six copies of the sheet up the
        // cabinet -- the banding -- and giving every facet 1/28th of U smeared
        // one narrow strip of grain across each whole flat side.
        float[] run = new float[n + 1];
        for (int i = 0; i < n; i++) {
            float[] p = ring[i], q = ring[(i + 1) % n];
            float dx = q[0] - p[0], dz = q[1] - p[1];
            run[i + 1] = run[i] + (float) Math.sqrt(dx * dx + dz * dz);
        }

        for (int r = 0; r < rows; r++) {
            int band = r / per;
            float g0 = (float) (r % per) / per, g1 = (float) (r % per + 1) / per;
            float ya = cuts[band] + (cuts[band + 1] - cuts[band]) * g0;
            float yb = cuts[band] + (cuts[band + 1] - cuts[band]) * g1;
            boolean inBay = ya >= WELL_Y0 - 1e-4F && yb <= WELL_Y1 + 1e-4F;
            float fa = fall((ya - y0) / (y1 - y0));
            float fb = fall((yb - y0) / (y1 - y0));
            float va = (ya - y0) / GRAIN, vb = (yb - y0) / GRAIN;
            for (int i = 0; i < n; i++) {
                float[] p = ring[i], q = ring[(i + 1) % n];
                float dx = q[0] - p[0], dz = q[1] - p[1];
                float len = (float) Math.sqrt(dx * dx + dz * dz);
                if (len < 1e-5F) continue;
                float nx = dz / len, nz = -dx / len;

                // The bay's mouth: skip the front facets it opens through.
                if (inBay && nz < -0.5F) {
                    float mx = (p[0] + q[0]) * 0.5F;
                    if (mx > WELL_X0 - 1e-4F && mx < WELL_X1 + 1e-4F) continue;
                }

                float side = 0.70F + 0.30F * Math.max(0F, -nz);
                float u0 = run[i] / GRAIN, u1 = run[i + 1] / GRAIN;

                t.setNormal(nx, 0F, nz);
                colour(t, WOOD, fa * side);
                v(t, p[0], ya, p[1], u0, va);
                colour(t, WOOD, fb * side);
                v(t, p[0], yb, p[1], u0, vb);
                v(t, q[0], yb, q[1], u1, vb);
                colour(t, WOOD, fa * side);
                v(t, q[0], ya, q[1], u1, va);
            }
        }

        moulding(t, ring, y0 + 0.014F, 0.030F, 1.00F);
        moulding(t, ring, y1 - 0.050F, 0.034F, 1.08F);
        // Reveals down the sides of the opening, so its cut edges are finished
        // rather than showing the cabinet's zero-thickness shell.
        reveal(t);
    }

    /** Light falling down a polished face: hot near the top, deep at the foot. */
    private static float fall(float f) {
        final float top = 1.08F, mid = 0.90F, bottom = 0.58F;
        return f > 0.5F ? mid + (top - mid) * (f - 0.5F) * 2F
                        : bottom + (mid - bottom) * f * 2F;
    }

    /** The four cut edges of the bay's mouth, given a visible thickness. */
    private static void reveal(Tessellator t) {
        float f = CAB_Z - 0.002F, b = CAB_Z + 0.055F;
        colour(t, WOOD, 0.74F);
        t.setNormal(0F, 1F, 0F);
        v(t, WELL_X0, WELL_Y0, f, 0F, 0F); v(t, WELL_X1, WELL_Y0, f, 1F, 0F);
        v(t, WELL_X1, WELL_Y0, b, 1F, 1F); v(t, WELL_X0, WELL_Y0, b, 0F, 1F);
        colour(t, WOOD, 0.52F);
        t.setNormal(0F, -1F, 0F);
        v(t, WELL_X0, WELL_Y1, b, 0F, 1F); v(t, WELL_X1, WELL_Y1, b, 1F, 1F);
        v(t, WELL_X1, WELL_Y1, f, 1F, 0F); v(t, WELL_X0, WELL_Y1, f, 0F, 0F);
        colour(t, WOOD, 0.64F);
        t.setNormal(1F, 0F, 0F);
        v(t, WELL_X0, WELL_Y0, f, 0F, 1F); v(t, WELL_X0, WELL_Y1, f, 0F, 0F);
        v(t, WELL_X0, WELL_Y1, b, 1F, 0F); v(t, WELL_X0, WELL_Y0, b, 1F, 1F);
        t.setNormal(-1F, 0F, 0F);
        v(t, WELL_X1, WELL_Y0, b, 0F, 1F); v(t, WELL_X1, WELL_Y1, b, 0F, 0F);
        v(t, WELL_X1, WELL_Y1, f, 1F, 0F); v(t, WELL_X1, WELL_Y0, f, 1F, 1F);
        t.setColorRGBA_F(1F, 1F, 1F, 1F);
    }

    /** A metal band standing slightly proud of the body, all the way round. */
    private static void moulding(Tessellator t, float[][] ring, float y,
                                 float h, float bright) {
        final int n = ring.length;
        final float out = 0.014F;
        for (int i = 0; i < n; i++) {
            float[] p = ring[i], q = ring[(i + 1) % n];
            float dx = q[0] - p[0], dz = q[1] - p[1];
            float len = (float) Math.sqrt(dx * dx + dz * dz);
            if (len < 1e-5F) continue;
            float nx = dz / len, nz = -dx / len;
            float side = 0.72F + 0.28F * Math.max(0F, -nz);
            float ax = p[0] + nx * out, az = p[1] + nz * out;
            float bx = q[0] + nx * out, bz = q[1] + nz * out;
            t.setNormal(nx, 0F, nz);
            colour(t, CHROME_C, bright * side);
            v(t, ax, y, az, 0F, 1F);
            v(t, ax, y + h, az, 0F, 0F);
            v(t, bx, y + h, bz, 1F, 0F);
            v(t, bx, y, bz, 1F, 1F);
        }
    }

    /**
     * A rounded rectangle as a ring of points, anticlockwise from the front-left.
     */
    private static float[][] roundedRect(float x0, float z0, float x1, float z1,
                                         float r, int steps) {
        java.util.List<float[]> out = new java.util.ArrayList<float[]>();
        float[][] corners = {
                { x0 + r, z0 + r, 180F }, { x1 - r, z0 + r, 270F },
                { x1 - r, z1 - r, 0F },   { x0 + r, z1 - r, 90F },
        };
        final int RUN = 10;      // pieces per straight run
        for (int c = 0; c < 4; c++) {
            float cx = corners[c][0], cz = corners[c][1], a0 = corners[c][2];
            for (int i = 0; i <= steps; i++) {
                double a = Math.toRadians(a0 + 90.0 * i / steps);
                out.add(new float[] { cx + (float) Math.cos(a) * r,
                                      cz + (float) Math.sin(a) * r });
            }
            // The straight edge to the next corner, in pieces. Without this the
            // whole front of the cabinet is a single facet, and cutting a window
            // in it means deleting the entire front.
            float[] nxt = corners[(c + 1) % 4];
            double na = Math.toRadians(nxt[2]);
            float ex = nxt[0] + (float) Math.cos(na) * r;
            float ez = nxt[1] + (float) Math.sin(na) * r;
            double la = Math.toRadians(a0 + 90.0);
            float sx = cx + (float) Math.cos(la) * r;
            float sz = cz + (float) Math.sin(la) * r;
            for (int i = 1; i < RUN; i++) {
                float f = (float) i / RUN;
                out.add(new float[] { sx + (ex - sx) * f, sz + (ez - sz) * f });
            }
        }
        return out.toArray(new float[out.size()][]);
    }

    /** The elliptical shoulder the arch is mounted on. */
    /** The dome's face sheet, mapped flat across the half ellipse. */
    private static float du(float x) { return (x - (0.5F - ARCH_A)) / (2F * ARCH_A); }
    private static float dv(float y) { return 1F - (y - SPRING_Y) / ARCH_B; }

    /** Distance along the dome's edge from its left foot to angle a. */
    private static float arcLen(float a) {
        float len = 0F;
        final int n = 48;
        float px = -ARCH_A, py = 0F;
        for (int i = 1; i <= n; i++) {
            double b = Math.PI - (Math.PI - a) * i / n;
            float x = (float) Math.cos(b) * ARCH_A, y = (float) Math.sin(b) * ARCH_B;
            len += (float) Math.hypot(x - px, y - py);
            px = x; py = y;
        }
        return len;
    }

    private static void shoulder(Tessellator t, boolean faceOnly) {
        for (int s = 0; s < ARCH_STEPS; s++) {
            float a0 = (float) Math.PI * (1F - (float) s / ARCH_STEPS);
            float a1 = (float) Math.PI * (1F - (float) (s + 1) / ARCH_STEPS);
            float x0 = 0.5F + (float) Math.cos(a0) * ARCH_A;
            float y0 = SPRING_Y + (float) Math.sin(a0) * ARCH_B;
            float x1 = 0.5F + (float) Math.cos(a1) * ARCH_A;
            float y1 = SPRING_Y + (float) Math.sin(a1) * ARCH_B;

            if (faceOnly) {
                // Planar, not polar: this is a picture seen through glass, and
                // it has to sit still behind the arch rather than wrap round it.
                // The sheet is drawn at the dome's own 3:2 shape.
                t.setColorRGBA_F(1F, 1F, 1F, 1F);
                t.setNormal(0F, 0F, -1F);
                v(t, 0.5F, SPRING_Y, CAB_Z, 0.5F, 1F);
                v(t, x0, y0, CAB_Z, du(x0), dv(y0));
                v(t, x1, y1, CAB_Z, du(x1), dv(y1));
                v(t, 0.5F, SPRING_Y, CAB_Z, 0.5F, 1F);
                continue;
            }

            // Along the curve by real distance, at the same grain as the body.
            float ua = arcLen(a0) / GRAIN;
            float ub = arcLen(a1) / GRAIN;
            float vd = (BACK_Z - CAB_Z) / GRAIN;
            colour(t, WOOD, 0.72F + 0.34F * (float) Math.sin(a0));
            t.setNormal((float) Math.cos(a0), (float) Math.sin(a0), 0F);
            v(t, x0, y0, CAB_Z, ua, vd); v(t, x1, y1, CAB_Z, ub, vd);
            v(t, x1, y1, BACK_Z, ub, 0F); v(t, x0, y0, BACK_Z, ua, 0F);

            // Flat, in blocks, the way a veneer is laid. Mapping each wedge of
            // the fan onto the same corner of the sheet stamped one triangle of
            // wood into every wedge -- which is what read as pleated paper.
            colour(t, WOOD, 0.70F);
            t.setNormal(0F, 0F, 1F);
            v(t, 0.5F, SPRING_Y, BACK_Z, 0.5F / GRAIN, SPRING_Y / GRAIN);
            v(t, x1, y1, BACK_Z, x1 / GRAIN, y1 / GRAIN);
            v(t, x0, y0, BACK_Z, x0 / GRAIN, y0 / GRAIN);
            v(t, 0.5F, SPRING_Y, BACK_Z, 0.5F / GRAIN, SPRING_Y / GRAIN);
        }
    }

    /**
     * The arch: three strands braided the whole way over.
     *
     * They used to run as concentric rings, which is tidy and dead -- the outer
     * one is always outermost, so the band reads as a printed stripe rather than
     * as cable. Braiding them means each strand's offset from the centreline
     * turns as it travels, so they cross over one another and the eye can follow
     * a single one round the arc. The offset tapers to nothing at both feet, so
     * the three converge and enter the capitals as one piece instead of arriving
     * at three different places.
     */
    public static void arch(Tessellator t, float phase, float level) {
        bright(t, LIT);
        for (int k = 0; k < STRANDS; k++) strand(t, k, phase, level);
    }

    private static final int STRANDS = 3;
    /** Turns of the braid between one foot and the other. */
    private static final float TWIST = 2.0F;
    private static final float STRAND_R = 0.0198F;
    private static final int STRAND_SIDES = 9;

    /** How far a strand rides off the centreline, tapering in at both feet. */
    private static float braid(float f) {
        float e = Math.min(f, 1F - f) / 0.14F;
        if (e > 1F) e = 1F;
        e = e * e * (3F - 2F * e);
        return ARCH_HALF * 0.54F * e;
    }

    /** A point on strand k at arc position f, in world space. */
    private static float[] strandPoint(int k, float f) {
        float a = (float) Math.PI * (1F - f);
        float[] c = onArch(a, 0F);
        float th = (float) (2.0 * Math.PI * ((double) k / STRANDS + TWIST * f));
        float br = braid(f);
        float rx = (float) Math.cos(a), ry = (float) Math.sin(a);
        float co = (float) Math.cos(th), si = (float) Math.sin(th);
        return new float[] { c[0] + rx * co * br,
                             c[1] + ry * co * br,
                             FZ + COL_R * 0.35F + si * br };
    }

    /**
     * One strand of the braid.
     *
     * The frame the ring is built in is carried along the path rather than
     * derived afresh at each step. Deriving it per segment is what shredded the
     * first braid: any perpendicular to the tangent is a valid basis, so
     * consecutive rings were rotated arbitrarily against one another and the
     * tube came out as a feather rather than a cable. Carrying one frame -- and
     * only correcting it back to perpendicular each step -- keeps the rings in
     * register the whole way over.
     */
    private static void strand(Tessellator t, int k, float phase, float level) {
        final int N = 112;
        final float OVER = 0.030F;

        float[][] p = new float[N + 1][];
        for (int i = 0; i <= N; i++) {
            p[i] = strandPoint(k, -OVER + (1F + 2F * OVER) * i / N);
        }

        float[] up = { 0F, 0F, 1F };
        float[][] prev = null;
        float prevGlow = 0F;
        for (int i = 0; i <= N; i++) {
            float[] tan = tangentAt(p, i);
            float d = up[0] * tan[0] + up[1] * tan[1] + up[2] * tan[2];
            float nx = up[0] - tan[0] * d, ny = up[1] - tan[1] * d,
                  nz = up[2] - tan[2] * d;
            float nl = (float) Math.sqrt(nx * nx + ny * ny + nz * nz);
            if (nl < 1e-4F) { nx = 0F; ny = 1F; nz = 0F; nl = 1F; }
            nx /= nl; ny /= nl; nz /= nl;
            up[0] = nx; up[1] = ny; up[2] = nz;
            float bx = tan[1] * nz - tan[2] * ny;
            float by = tan[2] * nx - tan[0] * nz;
            float bz = tan[0] * ny - tan[1] * nx;

            float[][] ring = new float[STRAND_SIDES + 1][];
            for (int j = 0; j <= STRAND_SIDES; j++) {
                double a = j * 2.0 * Math.PI / STRAND_SIDES;
                float c = (float) Math.cos(a), sn = (float) Math.sin(a);
                ring[j] = new float[] {
                        p[i][0] + (nx * c + bx * sn) * STRAND_R,
                        p[i][1] + (ny * c + by * sn) * STRAND_R,
                        p[i][2] + (nz * c + bz * sn) * STRAND_R,
                        nx * c + bx * sn, ny * c + by * sn, nz * c + bz * sn };
            }

            float f = (float) i / N;
            float glow = flow(f, phase, level);
            if (prev != null) {
                float u0 = 1F - (float) (i - 1) / N, u1 = 1F - f;
                for (int j = 0; j < STRAND_SIDES; j++) {
                    float[] a0 = prev[j], a1 = prev[j + 1];
                    float[] b0 = ring[j], b1 = ring[j + 1];
                    float v0 = (float) j / STRAND_SIDES;
                    float v1 = (float) (j + 1) / STRAND_SIDES;
                    float sh = 0.70F + 0.30F * Math.max(0F, -a0[5]);
                    t.setNormal(a0[3], a0[4], a0[5]);
                    float g = prevGlow * sh;
                    t.setColorRGBA_F(g, g, g, 1F);
                    v(t, a0[0], a0[1], a0[2], u0, v0);
                    g = glow * sh;
                    t.setColorRGBA_F(g, g, g, 1F);
                    v(t, b0[0], b0[1], b0[2], u1, v0);
                    v(t, b1[0], b1[1], b1[2], u1, v1);
                    g = prevGlow * sh;
                    t.setColorRGBA_F(g, g, g, 1F);
                    v(t, a1[0], a1[1], a1[2], u0, v1);
                }
            }
            prev = ring;
            prevGlow = glow;
        }
    }

    /**
     * Light running along the tubes.
     *
     * A single brightness for the whole run is what made the earlier version look
     * like a dimmer switch. Two travelling waves at different rates, squared to
     * sharpen them into bands, give the flow a Strimer has -- and the music rides
     * on top of that rather than replacing it, so the cabinet is alive before
     * anything is playing and hard-driven once it is.
     */
    // The speeds below must stay ones that come round to whole turns at
    // RenderJukebox.PHASE_PERIOD, or the light jumps each time the phase wraps.
    private static float flow(float f, float phase, float level) {
        double a = Math.sin((f * 3.1F - phase * 2.6F) * Math.PI * 2.0);
        double b = Math.sin((f * 1.6F + phase * 1.15F) * Math.PI * 2.0 + 1.3);
        float w = (float) (0.5 + 0.5 * (a * 0.62 + b * 0.38));
        w = w * w;
        float l = level < 0F ? 0F : level > 1F ? 1F : level;
        float g = 0.38F + 0.36F * w + l * (0.24F + 0.54F * w);
        return g > 1F ? 1F : g;
    }

    /** Unit tangent at sample i, from its neighbours. */
    private static float[] tangentAt(float[][] p, int i) {
        int a = i > 0 ? i - 1 : i, b = i < p.length - 1 ? i + 1 : i;
        float dx = p[b][0] - p[a][0], dy = p[b][1] - p[a][1], dz = p[b][2] - p[a][2];
        float l = (float) Math.sqrt(dx * dx + dy * dy + dz * dz);
        if (l < 1e-6F) return new float[] { 1F, 0F, 0F };
        return new float[] { dx / l, dy / l, dz / l };
    }



    /**
     * A point on the neon band's ellipse, offset from its centreline.
     *
     * The offset scales both axes together, so the three tubes stay concentric
     * instead of splaying apart towards the crown.
     */
    /**
     * How hard the gas is being driven, as a vertex tint.
     *
     * Neon does not sit at one brightness while a record plays through it -- the
     * whole point of a bubbler is that the cabinet moves. This rides the level of
     * the audio this jukebox is actually putting out, so it is steady when
     * nothing is on and lifts with the music when something is.
     */
    private static void live(Tessellator t, float level) {
        // A wide swing, because a narrow one is invisible: fixed-function clamps
        // colour at 1, so the only way to make the music read across a room is
        // to let the tubes sit well down when nothing is playing.
        float l = level < 0F ? 0F : level > 1F ? 1F : level;
        float g = 0.54F + 0.46F * l;
        t.setColorRGBA_F(g, g, g, 1F);
    }

    private static float[] onArch(float a, float off) {
        float scale = 1F + off / ARCH_MID_A;
        float ca = (float) Math.cos(a), sa = (float) Math.sin(a);
        return new float[] { 0.5F + ca * ARCH_MID_A * scale,
                             SPRING_Y + sa * ARCH_MID_B * scale };
    }

    /** The left column's glass. Its sheet is bound by the caller. */
    public static void tubeLeft(Tessellator t, float level, float phase) {
        bright(t, LIT);
        column(t, COL_X, level, phase);
    }

    /** A column, drawn in courses so the light can travel up it. */
    private static void column(Tessellator t, float cx, float level, float phase) {
        final int courses = 16;
        float cz = FZ + COL_R * 0.35F;
        for (int i = 0; i < courses; i++) {
            float ya = BASE_TOP + (TUBE_TOP + 0.010F - BASE_TOP) * i / courses;
            float yb = BASE_TOP + (TUBE_TOP + 0.010F - BASE_TOP) * (i + 1) / courses;
            float f = (float) i / courses;
            float ga = flow(f * 0.7F, phase, level);
            float gb = flow((float) (i + 1) / courses * 0.7F, phase, level);
            tube(t, cx, cz, COL_R, ya, yb,
                 1F - (float) i / courses, 1F - (float) (i + 1) / courses, ga, gb);
        }
    }

    public static void tubeRight(Tessellator t, float level, float phase) {
        bright(t, LIT);
        column(t, 1F - COL_X, level, phase);
    }

    /** The ring-stack capitals, where the arch lands on the columns. */
    public static void capitals(Tessellator t) {
        bright(t, LIT);
        float cz = FZ + COL_R * 0.35F;
        for (int side = 0; side < 2; side++) {
            float cx = side == 0 ? COL_X : 1F - COL_X;
            sleeve(t, cx, cz, CAP_R, TUBE_TOP - 0.020F, CAP_TOP + 0.014F);
            // Ferrules: a collar over each joint. A tube of one radius meeting a
            // casting of another leaves a step with the inside of both showing
            // through it, which is what made the joints look unfinished.
            sleeve(t, cx, cz, CAP_R * 1.10F, TUBE_TOP - 0.034F, TUBE_TOP + 0.012F);
            sleeve(t, cx, cz, CAP_R * 1.10F, CAP_TOP - 0.012F, CAP_TOP + 0.030F);
        }
    }

    /**
     * Fluted pilasters flanking the window, in place of the three coils.
     *
     * The coils were three chrome sticks leaning together at the foot of the
     * panel -- they read as scaffolding rather than as part of the cabinet. A
     * bundle of flutes running the height of the window is what the casework on
     * a machine of this age actually does, and it ties the panel to the plinth
     * instead of sitting in front of it.
     */
    public static void coils(Tessellator t) {
        bright(t, LIT);
        float y0 = BASE_TOP + 0.020F, y1 = STRIP_Y1;
        for (int side = 0; side < 2; side++) {
            float cx = side == 0 ? 0.256F : 0.744F;
            for (int i = -2; i <= 2; i++) {
                float r = i == 0 ? 0.022F : Math.abs(i) == 1 ? 0.018F : 0.012F;
                float dz = Math.abs(i) * 0.006F;      // the bundle curves away
                rod(t, cx + i * 0.026F, y0, FZ + 0.030F + dz,
                    cx + i * 0.026F, y1, FZ + 0.030F + dz, r, 1F);
            }
        }
    }

    /**
     * A cylinder between two points, textured along its length.
     *
     * Built from a basis perpendicular to the axis, so it can lean. `repeat` is
     * how many times the sheet runs along it, which is what sets the rib pitch.
     */
    private static void rod(Tessellator t, float ax, float ay, float az,
                            float bx, float by, float bz, float r, float repeat) {
        float dx = bx - ax, dy = by - ay, dz = bz - az;
        float len = (float) Math.sqrt(dx * dx + dy * dy + dz * dz);
        if (len < 1e-5F) return;
        dx /= len; dy /= len; dz /= len;

        // Any vector not parallel to the axis gives us the first perpendicular.
        float ux = 0F, uy = 0F, uz = 1F;
        if (Math.abs(dz) > 0.9F) { ux = 1F; uz = 0F; }
        float px = uy * dz - uz * dy, py = uz * dx - ux * dz, pz = ux * dy - uy * dx;
        float pl = (float) Math.sqrt(px * px + py * py + pz * pz);
        px /= pl; py /= pl; pz /= pl;
        float qx = dy * pz - dz * py, qy = dz * px - dx * pz, qz = dx * py - dy * px;

        t.setColorRGBA_F(1F, 1F, 1F, 1F);
        for (int i = 0; i < COL_SIDES; i++) {
            float c0 = CCOS[i], s0 = CSIN[i];
            float c1 = CCOS[i + 1], s1 = CSIN[i + 1];
            float n0x = px * c0 + qx * s0, n0y = py * c0 + qy * s0,
                  n0z = pz * c0 + qz * s0;
            float n1x = px * c1 + qx * s1, n1y = py * c1 + qy * s1,
                  n1z = pz * c1 + qz * s1;
            float u0 = seam(i), u1 = seam(i + 1);
            if (u1 < u0) u1 += 1F;

            t.setNormal(n0x, n0y, n0z);
            v(t, ax + n0x * r, ay + n0y * r, az + n0z * r, u0, repeat);
            v(t, bx + n0x * r, by + n0y * r, bz + n0z * r, u0, 0F);
            v(t, bx + n1x * r, by + n1y * r, bz + n1z * r, u1, 0F);
            v(t, ax + n1x * r, ay + n1y * r, az + n1z * r, u1, repeat);
        }
    }

    // ------------------------------------------------------------------
    // The trim along the top, the inlay on the back, and the stars
    // ------------------------------------------------------------------

    /**
     * A thin silver bead running round the front edge of the dome.
     *
     * It sits on the corner where the glass face turns into the curved top, so
     * it finishes that edge the way a real cabinet's chrome beading does, and it
     * dies into the ferrules at both feet. Nothing stands up off it.
     */
    public static void trim(Tessellator t) {
        bright(t, LIT);
        // Smoked rather than bright: a thin line that frames the glass, not a
        // second highlight competing with the arch.
        final float[] metal = { 0.50F, 0.52F, 0.57F };
        final float r = 0.0105F;
        final int sides = 10;
        final float cz = CAB_Z - r * 0.25F;
        for (int s2 = 0; s2 < ARCH_STEPS; s2++) {
            float a0 = (float) Math.PI * (1F - (float) s2 / ARCH_STEPS);
            float a1 = (float) Math.PI * (1F - (float) (s2 + 1) / ARCH_STEPS);
            float[] p0 = rimPoint(a0, r), p1 = rimPoint(a1, r);
            float[] o0 = rimNormal(a0), o1 = rimNormal(a1);
            for (int i = 0; i < sides; i++) {
                double t0 = i * 2.0 * Math.PI / sides, t1 = (i + 1) * 2.0 * Math.PI / sides;
                float c0 = (float) Math.cos(t0), z0 = (float) Math.sin(t0);
                float c1 = (float) Math.cos(t1), z1 = (float) Math.sin(t1);
                float shade = 0.62F + 0.38F * Math.max(0F, -z0);
                colour(t, metal, shade + 0.10F * Math.max(0F, c0 * o0[1]));
                t.setNormal(o0[0] * c0, o0[1] * c0, z0);
                v(t, p0[0] + o0[0] * c0 * r, p0[1] + o0[1] * c0 * r, cz + z0 * r,
                  (float) i / sides, 1F);
                v(t, p1[0] + o1[0] * c0 * r, p1[1] + o1[1] * c0 * r, cz + z0 * r,
                  (float) i / sides, 0F);
                v(t, p1[0] + o1[0] * c1 * r, p1[1] + o1[1] * c1 * r, cz + z1 * r,
                  (float) (i + 1) / sides, 0F);
                v(t, p0[0] + o0[0] * c1 * r, p0[1] + o0[1] * c1 * r, cz + z1 * r,
                  (float) (i + 1) / sides, 1F);
            }
        }
        t.setColorRGBA_F(1F, 1F, 1F, 1F);
    }

    /** A point on the dome's outer edge, pulled in by d. */
    private static float[] rimPoint(float a, float d) {
        float[] n = rimNormal(a);
        return new float[] { 0.5F + (float) Math.cos(a) * ARCH_A - n[0] * d,
                             SPRING_Y + (float) Math.sin(a) * ARCH_B - n[1] * d };
    }

    /** The outward normal of the dome's ellipse at angle a, in the XY plane. */
    private static float[] rimNormal(float a) {
        float nx = (float) Math.cos(a) / ARCH_A, ny = (float) Math.sin(a) / ARCH_B;
        float l = (float) Math.sqrt(nx * nx + ny * ny);
        return new float[] { nx / l, ny / l };
    }

    /**
     * Stringing on the back of the dome: a line of boxwood and one of ebony
     * following the curve, inset from the edge, as on the panels below it.
     */
    public static void backInlay(Tessellator t, int light) {
        bright(t, light);
        final float z = BACK_Z + 0.0022F;
        line(t, 0.905F, 0.888F, z, new float[] { 0.80F, 0.66F, 0.44F });
        line(t, 0.874F, 0.864F, z, new float[] { 0.07F, 0.05F, 0.04F });
        t.setColorRGBA_F(1F, 1F, 1F, 1F);
    }

    /** A band between two fractions of the dome's ellipse, on its back face. */
    private static void line(Tessellator t, float outer, float inner, float z, float[] c) {
        colour(t, c, 0.74F);
        t.setNormal(0F, 0F, 1F);
        for (int s2 = 0; s2 < ARCH_STEPS; s2++) {
            float a0 = (float) Math.PI * (1F - (float) s2 / ARCH_STEPS);
            float a1 = (float) Math.PI * (1F - (float) (s2 + 1) / ARCH_STEPS);
            float c0 = (float) Math.cos(a0), s0 = (float) Math.sin(a0);
            float c1 = (float) Math.cos(a1), s1 = (float) Math.sin(a1);
            v(t, 0.5F + c1 * ARCH_A * outer, SPRING_Y + s1 * ARCH_B * outer, z, 0F, 0F);
            v(t, 0.5F + c0 * ARCH_A * outer, SPRING_Y + s0 * ARCH_B * outer, z, 1F, 0F);
            v(t, 0.5F + c0 * ARCH_A * inner, SPRING_Y + s0 * ARCH_B * inner, z, 1F, 1F);
            v(t, 0.5F + c1 * ARCH_A * inner, SPRING_Y + s1 * ARCH_B * inner, z, 0F, 1F);
        }
    }

    /** The stars that twinkle, laid out once, in front of the nebula glass. */
    private static final int STARS = 64;
    private static final float[][] STAR = new float[STARS][];

    static {
        java.util.Random rng = new java.util.Random(0x51A75L);
        for (int i = 0; i < STARS; i++) {
            float rho = (float) Math.sqrt(rng.nextFloat());
            float th = (float) (rng.nextFloat() * Math.PI);
            // Magnitude on a power law: most faint, a handful bright.
            float mag = (float) Math.pow(rng.nextFloat(), 3.2);
            STAR[i] = new float[] {
                    0.5F + (float) Math.cos(th) * rho * 0.272F,
                    SPRING_Y + 0.030F + (float) Math.sin(th) * rho * 0.352F,
                    mag,
                    0.9F + rng.nextFloat() * 2.6F,              // rate
                    rng.nextFloat() * 6.2832F,                  // phase
                    rng.nextFloat() };                           // tint
        }
    }

    /**
     * Stars that glitter over the nebula.
     *
     * The faint field is painted into the glass and holds still; these are the
     * bright ones, drawn as geometry so each can flare on its own clock. The
     * twinkle is a sine raised to a high power, so a star sits low most of the
     * time and spikes briefly -- the glint of something seen through moving air,
     * not a light on a dimmer.
     */
    public static void stars(Tessellator t) {
        bright(t, LIT);
        final float z = CAB_Z - 0.0035F;
        double now = (System.currentTimeMillis() % 3600000L) / 1000.0;
        for (int i = 0; i < STARS; i++) {
            float[] st = STAR[i];
            float mag = st[2];
            double w = 0.5 + 0.5 * Math.sin(now * st[3] + st[4]);
            float tw = (float) Math.pow(w, 5.0);
            float b = 0.22F + 0.30F * mag + (0.55F + 0.45F * mag) * tw;
            if (b > 1F) b = 1F;
            float warm = st[5] < 0.25F ? 1F : 0.82F, cool = st[5] > 0.75F ? 1F : 0.88F;
            t.setColorRGBA_F(b * warm, b * 0.94F, b * cool, 1F);

            float core = 0.0022F + 0.0034F * mag + 0.0018F * tw;
            faceZ(t, st[0] - core, st[1] - core, st[0] + core, st[1] + core, z,
                  0F, 0F, 1F, 1F);
            // Spikes on the brighter ones, lengthening as they flare.
            if (mag > 0.18F) {
                float len = (0.006F + 0.020F * mag) * (0.35F + 0.65F * tw);
                float th = 0.00055F + 0.00045F * mag;
                faceZ(t, st[0] - len, st[1] - th, st[0] + len, st[1] + th, z - 0.0004F,
                      0F, 0F, 1F, 1F);
                faceZ(t, st[0] - th, st[1] - len, st[0] + th, st[1] + len, z - 0.0004F,
                      0F, 0F, 1F, 1F);
            }
        }
        t.setColorRGBA_F(1F, 1F, 1F, 1F);
    }

    /** A plain cuboid at the colour already set. */
    private static void boxAt(Tessellator t, float x0, float y0, float z0,
                              float x1, float y1, float z1) {
        t.setNormal(0F, 0F, -1F);
        v(t, x0, y0, z0, 0F, 1F); v(t, x0, y1, z0, 0F, 0F);
        v(t, x1, y1, z0, 1F, 0F); v(t, x1, y0, z0, 1F, 1F);
        t.setNormal(0F, 1F, 0F);
        v(t, x0, y1, z1, 0F, 1F); v(t, x1, y1, z1, 1F, 1F);
        v(t, x1, y1, z0, 1F, 0F); v(t, x0, y1, z0, 0F, 0F);
        t.setNormal(-1F, 0F, 0F);
        v(t, x0, y0, z1, 0F, 1F); v(t, x0, y1, z1, 0F, 0F);
        v(t, x0, y1, z0, 1F, 0F); v(t, x0, y0, z0, 1F, 1F);
        t.setNormal(1F, 0F, 0F);
        v(t, x1, y0, z0, 0F, 1F); v(t, x1, y1, z0, 0F, 0F);
        v(t, x1, y1, z1, 1F, 0F); v(t, x1, y0, z1, 1F, 1F);
        t.setNormal(0F, -1F, 0F);
        v(t, x0, y0, z0, 0F, 0F); v(t, x1, y0, z0, 1F, 0F);
        v(t, x1, y0, z1, 1F, 1F); v(t, x0, y0, z1, 0F, 1F);
    }

    /** The stem above the chevron, which on the reference crosses the arch. */
    public static void stem(Tessellator t) {
        bright(t, LIT);
        t.setColorRGBA_F(1F, 1F, 1F, 1F);
        faceZ(t, 0.484F, FIN_Y1, 0.516F, HEIGHT - 0.02F, FZ - 0.026F,
              0.30F, 0F, 0.62F, 1F);
    }

    /**
     * The inside of the mechanism well: back wall and four returns.
     *
     * The returns are what sell the depth. Without them the back wall is a
     * picture hung at the opening and the record has nothing to sit inside.
     */
    public static void well(Tessellator t, int light) {
        bright(t, light);
        float back = WELL_BACK;
        float mouth = WELL_MOUTH;

        t.setColorRGBA_F(1F, 1F, 1F, 1F);
        faceZ(t, WELL_X0, WELL_Y0, WELL_X1, WELL_Y1, back, 0F, 0F, 1F, 1F);

        // Top and bottom returns.
        colour(t, new float[] { 0.62F, 0.60F, 0.64F }, 1F);
        t.setNormal(0F, -1F, 0F);
        v(t, WELL_X0, WELL_Y1, mouth, 0F, 0F); v(t, WELL_X1, WELL_Y1, mouth, 1F, 0F);
        v(t, WELL_X1, WELL_Y1, back, 1F, 1F);  v(t, WELL_X0, WELL_Y1, back, 0F, 1F);
        colour(t, new float[] { 0.92F, 0.90F, 0.94F }, 1F);
        t.setNormal(0F, 1F, 0F);
        v(t, WELL_X0, WELL_Y0, back, 0F, 1F);  v(t, WELL_X1, WELL_Y0, back, 1F, 1F);
        v(t, WELL_X1, WELL_Y0, mouth, 1F, 0F); v(t, WELL_X0, WELL_Y0, mouth, 0F, 0F);

        // Side returns.
        colour(t, new float[] { 0.78F, 0.76F, 0.80F }, 1F);
        t.setNormal(1F, 0F, 0F);
        v(t, WELL_X0, WELL_Y0, mouth, 0F, 1F); v(t, WELL_X0, WELL_Y1, mouth, 0F, 0F);
        v(t, WELL_X0, WELL_Y1, back, 1F, 0F);  v(t, WELL_X0, WELL_Y0, back, 1F, 1F);
        t.setNormal(-1F, 0F, 0F);
        v(t, WELL_X1, WELL_Y0, back, 0F, 1F);  v(t, WELL_X1, WELL_Y1, back, 0F, 0F);
        v(t, WELL_X1, WELL_Y1, mouth, 1F, 0F); v(t, WELL_X1, WELL_Y0, mouth, 1F, 1F);
    }

    /**
     * The tonearm, and the spindle the record turns on.
     *
     * Comes in from the upper right and rests short of the label, which is where
     * an arm sits when it is playing rather than parked.
     */
    /**
     * The tonearm and spindle, in the deck's frame: +Z is up off the platter.
     *
     * Pivoted at the back right of the deck and reaching in over the disc, which
     * is where an arm sits while it is playing rather than parked.
     */
    public static void tonearm(Tessellator t) {
        bright(t, LIT);
        // Kept inside the bay. An arm pivoted out past the disc's own radius
        // pokes through the side of the recess once the deck is leant back.
        float lift = -0.022F;                 // clear of the record's face
        float px = DISC_R * 0.86F, py = DISC_R * 0.62F;
        rod(t, px, py, lift + 0.010F, px, py, lift - 0.014F, 0.013F, 1F);
        rod(t, px, py, lift, DISC_R * 0.22F, -DISC_R * 0.10F, lift, 0.0050F, 1F);
        rod(t, DISC_R * 0.26F, -DISC_R * 0.06F, lift,
            DISC_R * 0.18F, -DISC_R * 0.18F, lift, 0.0085F, 1F);
        rod(t, 0F, 0F, -0.004F, 0F, 0F, -0.030F, 0.008F, 1F);
    }

    /**
     * The selector display, back under the arch.
     *
     * Moving the deck down into the body left the whole head of the cabinet bare
     * wood, which is not what the reference does with that space -- it is the
     * slatted selector with its lamps, and it belongs there whether or not the
     * record is on show lower down.
     */
    public static void display(Tessellator t) {
        bright(t, LIT);
        t.setColorRGBA_F(1F, 1F, 1F, 1F);
        plate(t, 0.360F, 1.390F, 0.640F, 1.620F,
              CAB_Z - 0.030F, CAB_Z - 0.002F, new float[] { 0.40F, 0.39F, 0.43F });
    }

    /** How many columns the analyser has. */
    public static final int BARS = 80;

    /**
     * A live waveform across the selector panel.
     *
     * Each column is lit from a rainbow across the panel and stands as tall as
     * its own band is loud, so the thing reads as the music rather than as a
     * decal of some music. Drawn on the white sheet at full brightness, like the
     * rest of the lit work, so a shader pack blooms it.
     */
    public static void waveform(Tessellator t, float[] levels) {
        bright(t, LIT);
        final float base = 1.448F, top = 1.700F, foot = 1.396F;
        // The row runs out under the arch at both ends: it starts and stops on
        // the braid's centre line, which the strands always cover, so the cut
        // ends are never seen and the trace looks to carry on behind the neon.
        final float x0 = archX(base), x1 = 1F - x0;
        final float z = CAB_Z - 0.036F;
        final float pitch = (x1 - x0) / BARS;
        final float w = pitch * 0.62F;          // thin, with air between them
        final float cap = 0.006F;

        for (int i = 0; i < BARS; i++) {
            float lv = levels == null ? 0.05F : levels[i];
            if (lv < 0.022F) lv = 0.022F;       // a resting line, never nothing
            float[] c = hue((float) i / (BARS - 1));
            float bx = x0 + pitch * i + (pitch - w) * 0.5F;
            float h = (top - base) * lv;
            // And it stays inside the arch: a column near an end is cut off
            // where the arch comes down over it, the top hidden in the braid.
            float lim = Math.min(archY(bx), archY(bx + w)) - base - cap;
            if (lim <= 0.002F) continue;
            if (h > lim) h = lim;

            // The column, brightening towards its tip the way a lit bar does.
            colour(t, c, 0.72F);
            faceZ(t, bx, base, bx + w, base + h * 0.72F, z, 0F, 0F, 1F, 1F);
            colour(t, c, 1.00F);
            faceZ(t, bx, base + h * 0.72F, bx + w, base + h, z, 0F, 0F, 1F, 1F);
            // A hot cap, which is what gives the row its sparkle at distance.
            colour(t, new float[] { Math.min(1F, c[0] + 0.45F),
                                    Math.min(1F, c[1] + 0.45F),
                                    Math.min(1F, c[2] + 0.45F) }, 1F);
            faceZ(t, bx, base + h, bx + w, base + h + cap, z - 0.002F,
                  0F, 0F, 1F, 1F);

            // And its reflection in the deck below, dimmer and shorter, never
            // reaching down onto the record bay's frame.
            float rh = Math.min(h * 0.42F, base - foot);
            colour(t, c, 0.30F);
            faceZ(t, bx, base - rh, bx + w, base - 0.004F, z, 0F, 0F, 1F, 1F);
        }


        // No backing at all. A rectangle behind the columns is a window frame
        // round something that should look like it is simply there.
    }

    /** The x of the arch's centre line at height y, on the left. */
    private static float archX(float y) {
        float k = (y - SPRING_Y) / ARCH_MID_B;
        return 0.5F - ARCH_MID_A * (float) Math.sqrt(Math.max(0F, 1F - k * k));
    }

    /** The height of the arch's centre line above x. */
    private static float archY(float x) {
        float k = (x - 0.5F) / ARCH_MID_A;
        return SPRING_Y + ARCH_MID_B * (float) Math.sqrt(Math.max(0F, 1F - k * k));
    }

    /** The analyser's colours: a rainbow left to right. */
    private static float[] hue(float f) {
        float[][] stops = {
                { 1.00F, 0.16F, 0.16F }, { 1.00F, 0.62F, 0.12F },
                { 1.00F, 0.94F, 0.20F }, { 0.30F, 0.94F, 0.36F },
                { 0.20F, 0.72F, 1.00F }, { 0.58F, 0.36F, 1.00F },
                { 1.00F, 0.32F, 0.86F },
        };
        float p = f * (stops.length - 1);
        int i = (int) p;
        if (i >= stops.length - 1) return stops[stops.length - 1];
        float k = p - i;
        float[] a = stops[i], b = stops[i + 1];
        return new float[] { a[0] + (b[0] - a[0]) * k,
                             a[1] + (b[1] - a[1]) * k,
                             a[2] + (b[2] - a[2]) * k };
    }

    /** The glazing over the well: highlights only, the rest cut away. */
    public static void glass(Tessellator t) {
        bright(t, LIT);
        t.setColorRGBA_F(1F, 1F, 1F, 1F);
        faceZ(t, WELL_X0, WELL_Y0, WELL_X1, WELL_Y1, WELL_MOUTH - 0.006F,
              0F, 0F, 1F, 1F);
    }

    /** The chrome surround of the well's opening. */
    public static void wellFrame(Tessellator t) {
        bright(t, LIT);
        t.setColorRGBA_F(1F, 1F, 1F, 1F);
        float z = WELL_MOUTH - 0.010F, b = 0.026F;
        faceZ(t, WELL_X0 - b, WELL_Y0 - b, WELL_X1 + b, WELL_Y0, z, 0F, 0F, 1F, 1F);
        faceZ(t, WELL_X0 - b, WELL_Y1, WELL_X1 + b, WELL_Y1 + b, z, 0F, 0F, 1F, 1F);
        faceZ(t, WELL_X0 - b, WELL_Y0, WELL_X0, WELL_Y1, z, 0F, 0F, 1F, 1F);
        faceZ(t, WELL_X1, WELL_Y0, WELL_X1 + b, WELL_Y1, z, 0F, 0F, 1F, 1F);
    }

    /**
     * The disc, centred on the origin so the caller can tilt and spin it.
     *
     * Drawn in the XY plane: the caller leans that plane back about X to lay the
     * record down, then turns it about Z -- which after the lean is the platter's
     * own axis -- to spin it.
     */
    public static void disc(Tessellator t) {
        bright(t, LIT);
        t.setColorRGBA_F(1F, 1F, 1F, 1F);
        faceZ(t, -DISC_R, -DISC_R, DISC_R, DISC_R, 0F, 0F, 0F, 1F, 1F);
    }

    /** The platter under it, a shade wider, so the disc sits on something. */
    public static void platter(Tessellator t) {
        bright(t, LIT);
        colour(t, new float[] { 0.30F, 0.29F, 0.32F }, 1F);
        faceZ(t, -DISC_R * 1.14F, -DISC_R * 1.14F,
              DISC_R * 1.14F, DISC_R * 1.14F, 0.010F, 0F, 0F, 1F, 1F);
    }

    /**
     * The window: black glass and bevelled gold, arch-topped.
     *
     * The rounded head is a fan, and it samples the top of the sheet so the
     * scrollwork below it is not distorted by the curve.
     */
    public static void window(Tessellator t) {
        bright(t, LIT);
        t.setColorRGBA_F(1F, 1F, 1F, 1F);
        float z = CAB_Z - 0.014F;      // set back, not floating
        float headY = WIN_Y1 - WIN_ARCH;

        faceZ(t, WIN_X0, WIN_Y0, WIN_X1, headY, z, 0F, 0.06F, 1F, 1F);

        float cx = 0.5F, halfW = (WIN_X1 - WIN_X0) * 0.5F;
        final int steps = 14;
        for (int i2 = 0; i2 < steps; i2++) {
            float a0 = (float) Math.PI * (1F - (float) i2 / steps);
            float a1 = (float) Math.PI * (1F - (float) (i2 + 1) / steps);
            float x0 = cx + (float) Math.cos(a0) * halfW;
            float y0 = headY + (float) Math.sin(a0) * WIN_ARCH;
            float x1 = cx + (float) Math.cos(a1) * halfW;
            float y1 = headY + (float) Math.sin(a1) * WIN_ARCH;
            t.setNormal(0F, 0F, -1F);
            v(t, cx, headY, z, 0.5F, 0.06F);
            v(t, x0, y0, z, (x0 - WIN_X0) / (WIN_X1 - WIN_X0), 0F);
            v(t, x1, y1, z, (x1 - WIN_X0) / (WIN_X1 - WIN_X0), 0F);
            v(t, cx, headY, z, 0.5F, 0.06F);
        }
    }

    /**
     * The front panel, carrying the light the columns throw onto the cabinet.
     *
     * Drawn just proud of the carcass so it is the surface you see between and
     * around the columns, rather than the plain wood behind it.
     */
    public static void front(Tessellator t, int light) {
        bright(t, light);
        t.setColorRGBA_F(1F, 1F, 1F, 1F);
        float a = X0 + 0.012F, b = X1 - 0.012F;
        float c = BASE_TOP, d = SPRING_Y - 0.010F;
        float z = CAB_Z - 0.006F;

        // Four pieces round the deck bay. One quad across the whole front would
        // be drawn in front of the recess and hide everything in it -- which is
        // exactly what happened the first time the bay went in.
        faceZ(t, a, c, b, WELL_Y0, z, 0F, 0F, 1F, 0.45F);
        faceZ(t, a, WELL_Y1, b, d, z, 0F, 0.55F, 1F, 1F);
        faceZ(t, a, WELL_Y0, WELL_X0, WELL_Y1, z, 0F, 0.45F, 0.25F, 0.55F);
        faceZ(t, WELL_X1, WELL_Y0, b, WELL_Y1, z, 0.75F, 0.45F, 1F, 0.55F);
    }

    /**
     * Selector buttons and the coin plate.
     *
     * Both live on the strip of cabinet between the window and the right column,
     * which is where the reference puts them and the only frontage not already
     * spoken for.
     */
    public static void hardware(Tessellator t) {
        bright(t, LIT);
        t.setColorRGBA_F(1F, 1F, 1F, 1F);
        // Coin plate, beside the window. The button row moved out when the deck
        // took the space above the strip.
        faceZ(t, WIN_X1 + 0.030F, 0.560F, WIN_X1 + 0.098F, 0.700F,
              CAB_Z - 0.022F, 0.56F, 0.14F, 0.96F, 0.86F);
    }

    /**
     * A panel with sides, standing proud of a surface behind it.
     *
     * Everything on this front used to be a single quad hanging in mid-air --
     * from anywhere but dead centre you could see the texture floating off the
     * cabinet with daylight behind it. A face plus four returns costs four more
     * quads and makes it a piece of the object.
     */
    private static void plate(Tessellator t, float x0, float y0, float x1, float y1,
                              float front, float back, float[] side) {
        faceZ(t, x0, y0, x1, y1, front, 0F, 0F, 1F, 1F);
        colour(t, side, 1.00F);
        t.setNormal(0F, 1F, 0F);
        v(t, x0, y1, front, 0F, 0F); v(t, x1, y1, front, 1F, 0F);
        v(t, x1, y1, back, 1F, 1F);  v(t, x0, y1, back, 0F, 1F);
        colour(t, side, 0.62F);
        t.setNormal(0F, -1F, 0F);
        v(t, x0, y0, back, 0F, 1F);  v(t, x1, y0, back, 1F, 1F);
        v(t, x1, y0, front, 1F, 0F); v(t, x0, y0, front, 0F, 0F);
        colour(t, side, 0.80F);
        t.setNormal(-1F, 0F, 0F);
        v(t, x0, y0, front, 0F, 1F); v(t, x0, y1, front, 0F, 0F);
        v(t, x0, y1, back, 1F, 0F);  v(t, x0, y0, back, 1F, 1F);
        t.setNormal(1F, 0F, 0F);
        v(t, x1, y0, back, 0F, 1F);  v(t, x1, y1, back, 0F, 0F);
        v(t, x1, y1, front, 1F, 0F); v(t, x1, y0, front, 1F, 1F);
        t.setColorRGBA_F(1F, 1F, 1F, 1F);
    }

    /** The lit title strip inside the window's head. */
    public static void strip(Tessellator t) {
        bright(t, LIT);
        t.setColorRGBA_F(1F, 1F, 1F, 1F);
        plate(t, WIN_X0 + 0.018F, STRIP_Y0, WIN_X1 - 0.018F, STRIP_Y1,
              FZ + 0.004F, CAB_Z - 0.008F, new float[] { 0.55F, 0.45F, 0.26F });
    }

    /** Chrome: the window's frame and the band across the plinth. */
    public static void chrome(Tessellator t, int light) {
        bright(t, LIT);
        t.setColorRGBA_F(1F, 1F, 1F, 1F);
        float z = FZ + 0.020F, b = 0.024F;
        float headY = WIN_Y1 - WIN_ARCH;

        faceZ(t, WIN_X0 - b, WIN_Y0 - b, WIN_X1 + b, WIN_Y0, z, 0F, 0F, 1F, 1F);
        faceZ(t, WIN_X0 - b, WIN_Y0, WIN_X0, headY, z, 0F, 0F, 1F, 1F);
        faceZ(t, WIN_X1, WIN_Y0, WIN_X1 + b, headY, z, 0F, 0F, 1F, 1F);

        float cx = 0.5F, halfW = (WIN_X1 - WIN_X0) * 0.5F;
        final int steps = 16;
        for (int i2 = 0; i2 < steps; i2++) {
            float a0 = (float) Math.PI * (1F - (float) i2 / steps);
            float a1 = (float) Math.PI * (1F - (float) (i2 + 1) / steps);
            float c0 = (float) Math.cos(a0), s0 = (float) Math.sin(a0);
            float c1 = (float) Math.cos(a1), s1 = (float) Math.sin(a1);
            t.setNormal(0F, 0F, -1F);
            v(t, cx + c0 * halfW, headY + s0 * WIN_ARCH, z, 0F, 1F);
            v(t, cx + c0 * (halfW + b), headY + s0 * (WIN_ARCH + b), z, 0F, 0F);
            v(t, cx + c1 * (halfW + b), headY + s1 * (WIN_ARCH + b), z, 1F, 0F);
            v(t, cx + c1 * halfW, headY + s1 * WIN_ARCH, z, 1F, 1F);
        }

        faceZ(t, X0 - 0.02F, BASE_TOP - 0.052F, X1 + 0.02F, BASE_TOP - 0.014F,
              CAB_Z - 0.034F, 0F, 0F, 1F, 1F);

        // A moulding down each front corner of the body, and along its top. Real
        // cabinets are edged in metal, and from an angle it is the only thing
        // that stops the side reading as one undifferentiated panel.
        float lip = 0.022F;
        box(t, CHROME_C, X0, BASE_TOP, CAB_Z - 0.012F,
            X0 + lip, SPRING_Y, CAB_Z + 0.010F);
        box(t, CHROME_C, X1 - lip, BASE_TOP, CAB_Z - 0.012F,
            X1, SPRING_Y, CAB_Z + 0.010F);
    }

    /** GL state every pass of this model expects. Restored by {@link #end}. */
    /**
     * True while a part is being compiled into a display list.
     *
     * A list keeps whatever brightness its vertices were given, so a part
     * compiled lit by one block's light would wear that light everywhere it was
     * drawn. While compiling, parts leave brightness off the vertices entirely
     * and the renderer sets the lightmap per jukebox before calling the list;
     * all that is kept is which kind of light the part asked for.
     */
    static boolean compiling;
    /** What the part being compiled asked for: SELF_LIT, ROOM_LIT, or both. */
    static int asked;
    static final int SELF_LIT = 1, ROOM_LIT = 2;

    private static void bright(Tessellator t, int b) {
        if (compiling) {
            asked |= b == LIT ? SELF_LIT : ROOM_LIT;
            return;
        }
        t.setBrightness(b);
    }

    public static boolean begin() {
        boolean lit = GL11.glIsEnabled(GL11.GL_LIGHTING);
        if (lit) GL11.glDisable(GL11.GL_LIGHTING);
        GL11.glDisable(GL11.GL_CULL_FACE);
        GL11.glColor4f(1F, 1F, 1F, 1F);
        return lit;
    }

    public static void end(boolean lit) {
        GL11.glEnable(GL11.GL_CULL_FACE);
        if (lit) GL11.glEnable(GL11.GL_LIGHTING);
        GL11.glColor4f(1F, 1F, 1F, 1F);
    }
}
