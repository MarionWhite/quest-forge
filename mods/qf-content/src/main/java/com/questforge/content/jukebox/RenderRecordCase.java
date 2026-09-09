package com.questforge.content.jukebox;

import net.minecraft.client.Minecraft;
import net.minecraft.client.renderer.OpenGlHelper;
import net.minecraft.client.renderer.Tessellator;
import net.minecraft.client.renderer.tileentity.TileEntitySpecialRenderer;
import net.minecraft.item.ItemStack;
import net.minecraft.tileentity.TileEntity;
import net.minecraft.util.ResourceLocation;
import net.minecraft.world.World;
import org.lwjgl.opengl.GL11;
import org.lwjgl.opengl.GL12;

/**
 * Draws the display case.
 *
 * The frame is deliberately plain: a deep mitred moulding in one colour, with a
 * profile -- a crisp outer micro-bevel, a flat top, and a chamfer falling away to
 * the opening. Each step faces a different way, so an edge reads in four tones
 * without any texture on it at all. A wood grain lived here for a while and was
 * removed; at 1.4 of a block's 16 pixels wide, the only part of a grain sheet that
 * can be resolved is its slowest variation, which arrives as ripples rather than as
 * figure.
 *
 * The light is computed, not painted. The glass and the plaque both bounce the eye
 * off their own surface and ask what the bounced ray points at -- sky above, ground
 * below, the sun if it lines up -- so both react to where you stand, which way the
 * case faces, and the time of day. The mat carries the one thing that cannot be
 * computed here, a contact shadow, painted into its vertex colours.
 *
 * One unit is one block, and everything is laid out in sixteenths. No two visible
 * faces are allowed to share a plane -- the first version of this had a highlight
 * that did, and it both hid the record and speckled. Deliberate second passes over
 * the same surface are the one exception, and rely on the depth function being
 * GL_LEQUAL, which is set before they run.
 */
public class RenderRecordCase extends TileEntitySpecialRenderer {

    private static final float P = 1F / 16F;

    // ------------------------------------------------------------------
    // The moulding, outer edge inward
    // ------------------------------------------------------------------

    private static final float X0 = 0.5F * P, X1 = 15.5F * P;
    private static final float Y0 = 0.5F * P, Y1 = 31.5F * P;

    private static final float W_LIP = 0.14F * P;    // outer micro-bevel
    private static final float W_FLAT = 0.60F * P;   // flat top
    private static final float W_CHAM = 0.66F * P;   // chamfer into the opening
    private static final float RAIL = W_LIP + W_FLAT + W_CHAM;

    /**
     * How far the case stands off the wall. Deep on purpose: the whole point of the
     * thing is that a record is a physical object in a box, and a shallow box reads
     * as a picture of one. Everything inside is spaced against this.
     */
    private static final float FRAME_Z = 2.60F * P;    // the flat, standing proudest
    private static final float FRAME_LIP = 2.30F * P;  // where the micro-bevel starts
    private static final float FRAME_IN = 2.05F * P;   // the chamfer's inner edge

    private static final float IX0 = X0 + RAIL, IX1 = X1 - RAIL;
    private static final float IY0 = Y0 + RAIL, IY1 = Y1 - RAIL;

    // ------------------------------------------------------------------
    // The metal liner around the opening
    // ------------------------------------------------------------------

    private static final float BW_FLAT = 0.26F * P;
    private static final float BW_CHAM = 0.24F * P;
    private static final float BEZEL_W = BW_FLAT + BW_CHAM;

    private static final float BEZEL_Z = 1.92F * P;
    private static final float BEZEL_IN = 1.62F * P;

    private static final float BX0 = IX0 + BEZEL_W, BX1 = IX1 - BEZEL_W;
    private static final float BY0 = IY0 + BEZEL_W, BY1 = IY1 - BEZEL_W;

    // ------------------------------------------------------------------
    // Behind the glass
    // ------------------------------------------------------------------

    private static final float BACK_Z = 0.50F * P;
    private static final float MAT_R = 0.35F * P;      // reveal around the mat
    private static final float MAT_Z0 = 0.44F * P, MAT_Z1 = 0.80F * P;
    private static final float MX0 = BX0 + MAT_R, MX1 = BX1 - MAT_R;
    private static final float MY0 = BY0 + MAT_R, MY1 = BY1 - MAT_R;

    private static final float DISC_X0 = 3.0F * P, DISC_X1 = 13.0F * P;
    private static final float DISC_Y0 = 13.3F * P, DISC_Y1 = 23.3F * P;
    private static final float DISC_Z = 1.16F * P;

    private static final float GX0 = BX0 + 0.05F * P, GX1 = BX1 - 0.05F * P;
    private static final float GY0 = BY0 + 0.05F * P, GY1 = BY1 - 0.05F * P;
    private static final float GLASS_Z0 = 1.32F * P, GLASS_Z1 = 1.52F * P;

    // ------------------------------------------------------------------
    // The plaque, mounted on the front of the pane
    // ------------------------------------------------------------------

    private static final float PL_X0 = 3.6F * P, PL_X1 = 12.4F * P;
    private static final float PL_Y0 = 3.4F * P, PL_Y1 = 7.6F * P;

    private static final float PL_Z0 = 1.54F * P;     // sits on the glass
    private static final float PL_Z1 = 1.86F * P;     // top of the dark mount
    private static final float PL_INSET = 0.18F * P;  // reveal of mount around plate
    private static final float PL_PLATE_Z = 1.98F * P;
    private static final float PL_BEVEL = 0.24F * P;
    private static final float PL_FACE = 2.14F * P;
    private static final float PL_SCREW_Z = PL_FACE + 0.02F * P;
    private static final float PL_TEXT = PL_FACE + 0.05F * P;

    private static final float FX0 = PL_X0 + PL_INSET + PL_BEVEL;
    private static final float FX1 = PL_X1 - PL_INSET - PL_BEVEL;
    private static final float FY0 = PL_Y0 + PL_INSET + PL_BEVEL;
    private static final float FY1 = PL_Y1 - PL_INSET - PL_BEVEL;

    /** Fastener centres, inset from the face, and how big each head is drawn. */
    private static final float SCREW_IN = 0.55F * P;
    private static final float SCREW_R = 0.45F * P;

    // ------------------------------------------------------------------
    // Palettes
    // ------------------------------------------------------------------

    /**
     * One coordinated palette per pressing: frame, mat, bright metal, shadowed
     * metal, specular.
     *
     * The frame takes its colour from the record rather than being one neutral for
     * all four, because a rack of these should read as a set of different awards,
     * not the same box four times.
     *
     * The metals are pre-divided by the brushed sheet's median, so a colour here is
     * what the liner actually comes out as rather than what it starts from --
     * choosing against the raw value is how brass ends up olive.
     *
     * The specular is not white for every tier. A highlight keeps a trace of the
     * metal it came off, and that trace is most of what separates them at a glance.
     */
    private static final int[][] STYLE = {
        // frame       mat         bright      dark        specular
        { 0x3A2E20, 0x1A1712, 0xE8C05A, 0x7C6320, 0xFFF0CF },  // black: espresso + brass
        { 0x27333F, 0x151A21, 0xD8E2EE, 0x6E7885, 0xEAF3FF },  // silver: slate + steel
        { 0x54291A, 0x1C1510, 0xF2CC5E, 0x8F6E1E, 0xFFEFC4 },  // gold: mahogany + gold
        { 0x191C21, 0x121418, 0xF2F6FA, 0x9AA4AE, 0xFFFFFF },  // platinum: black + white metal
    };

    /**
     * An empty case sits in plain steel, waiting to be given a colour.
     *
     * Deliberately quieter than any of the pressings: graphite rather than a hue,
     * and a liner pulled well down from the near-white the filled ones carry. An
     * empty case with a bright liner shouts for attention it has not earned, and a
     * wall of them should read as a rack waiting to be filled rather than as four
     * finished pieces.
     */
    private static final int[] EMPTY =
        { 0x33383E, 0x14171B, 0x7C8894, 0x353C44, 0xC3CDD8 };

    /**
     * A 1-colour sheet bound in place of turning texturing off.
     *
     * glDisable(GL_TEXTURE_2D) is a fixed-function switch. A shader pack's
     * gbuffers program ignores it and samples texture2D(texture, texcoord)
     * regardless, so an "untextured" quad samples whatever sheet happens to be
     * bound, at whatever coords the vertex carries -- and vertices emitted with
     * addVertex carry none. That is why the frame, mat and backing came out pure
     * black under Vibrant while every textured part of the case still drew.
     *
     * Binding white and giving every vertex real UVs makes the sample a no-op:
     * white * vertex colour is the vertex colour, which is what the
     * fixed-function path was already producing.
     */
    private static final ResourceLocation WHITE =
            new ResourceLocation("qfcontent", "textures/misc/white.png");

    private static final ResourceLocation BRUSHED =
            new ResourceLocation("qfcontent", "textures/misc/brushed.png");
    private static final ResourceLocation BRUSHED_SPEC =
            new ResourceLocation("qfcontent", "textures/misc/brushed_spec.png");
    private static final ResourceLocation SCREW =
            new ResourceLocation("qfcontent", "textures/misc/plaque_screw.png");

    /**
     * How many times the brushed sheet repeats across a block.
     *
     * Kept near one on purpose. A sheet crammed into a narrow strip is mostly
     * minification, which throws the detail away and leaves a shimmer behind.
     */
    private static final float METAL_REPEAT = 0.9F;

    /**
     * How much darker a face is for the way it points, with no real lighting to ask.
     *
     * The four entries of a profile ring are bottom, top, left, right. A surface
     * falling away toward the centre of the frame turns its bottom length upward
     * into the light and its top length down into shadow; one rising toward the
     * centre does the opposite. Getting these the wrong way round makes a moulding
     * look pressed into the wall rather than standing off it.
     */
    private static final float[] FLAT = { 1F, 1F, 1F, 1F };
    private static final float[] FALLING = { 1.06F, 0.70F, 0.94F, 0.82F };
    private static final float[] RISING = { 0.70F, 1.06F, 0.82F, 0.94F };

    /** The same, for the vertical bands: up, down, and the two sides. */
    private static final float[] WALL_IN = { 0.95F, 0.55F, 0.72F, 0.84F };
    private static final float[] WALL_OUT = { 0.55F, 0.95F, 0.84F, 0.72F };

    private static final String[] TIER_TEXTURE =
            { "black", "silver", "gold", "platinum" };

    /** Scratch for one quad. Reused rather than allocated per face each frame. */
    private final float[] qx = new float[4];
    private final float[] qy = new float[4];
    private final float[] qz = new float[4];

    // The world the reflective surfaces are standing in, worked out once per case.
    private float camX, camY, camZ, rotC, rotS;
    private float sunY, sunZ, daylight, shade;

    /** Full lightmap coordinate: shade already carries world light. */
    private static final int FULL_BRIGHT = 0xF000F0;
    private float skyR, skyG, skyB, groundR, groundG, groundB;

    // Where the last bounce landed, and how glancing it was.
    private float hitR, hitG, hitB, hitGrazing;

    @Override
    public void renderTileEntityAt(TileEntity te, double x, double y, double z,
                                   float partial) {
        if (!(te instanceof TileEntityRecordCase)) return;
        TileEntityRecordCase display = (TileEntityRecordCase) te;

        int meta = te.getWorldObj() == null ? 0 : te.getBlockMetadata();
        int facing = BlockRecordCase.facing(meta);

        // World light applied by hand: the case is its own little lighting model, so
        // modulating colours is steadier than threading the lightmap through every
        // quad, and the floor keeps it from going pitch black.
        float light = 1F;
        if (te.getWorldObj() != null) {
            light = te.getWorldObj().getLightBrightness(te.xCoord, te.yCoord, te.zCoord);
        }
        shade = 0.38F + 0.62F * light;

        // Pin the lightmap for the whole model, and put back whatever was there.
        //
        // The comment above is the intent -- this renderer lights itself by
        // modulating colours -- but intent is not enough: a tile entity renderer
        // that never writes a lightmap coordinate does not get "no lightmap", it
        // inherits whatever the last geometry drawn left on texture unit 1. That
        // value depends on what rendered immediately before, which changes with
        // the neighbouring blocks and with view distance as chunk draw order
        // shifts. Hence a case whose brightness wandered depending on where you
        // stood and what was next to it.
        //
        // Pinned to full so the lightmap contributes nothing and `shade` alone
        // does the lighting, which is what the model was built for. Restored on
        // the way out so nothing drawn after us inherits ours -- the same class
        // of leak, pointed the other way.
        // Pinning the lightmap above sets GL *state*. That is enough for the
        // fixed-function pipeline, but a shader pack's gbuffers program reads the
        // lightmap from the per-vertex attribute, which Tessellator only writes
        // once setBrightness has been called -- until then hasBrightness is false
        // and the coordinate never reaches the vertex. Which is why the case still
        // rendered black under shaders with the pin alone in place.
        //
        // RenderTowerSpeaker and RenderSpeaker have always called setBrightness
        // after every startDrawingQuads, and neither has ever had this problem.
        // Do the same here; the pin stays for the paths that draw without the
        // Tessellator.
        float lastBrightnessX = OpenGlHelper.lastBrightnessX;
        float lastBrightnessY = OpenGlHelper.lastBrightnessY;
        OpenGlHelper.setLightmapTextureCoords(OpenGlHelper.lightmapTexUnit, 240F, 240F);

        surroundings(te, x, y, z, facing, partial);

        ItemStack record = display.getRecord();
        int[] style = record == null ? EMPTY : STYLE[ItemVinyl.tier(record)];

        int frame = style[0];
        int mat = style[1];
        int bright = style[2];
        int dark = style[3];
        int specular = style[4];
        // The backing is the mat lifted, so the reveal around the mat reads as a
        // step rather than one flat hole.
        int backing = lift(mat, 1.7F);

        GL11.glPushMatrix();
        GL11.glDisable(GL11.GL_LIGHTING);
        GL11.glTranslated(x + 0.5, y, z + 0.5);
        GL11.glRotatef(facing * 90F, 0F, 1F, 0F);
        GL11.glTranslatef(-0.5F, 0F, -0.5F);

        Tessellator t = Tessellator.instance;

        // --- everything with no material on it ---
        bind(WHITE);
        t.startDrawingQuads();
        t.setBrightness(FULL_BRIGHT);

        moulding(t, frame);

        flat(t, IX0, IY0, IX1, IY1, BACK_Z, backing, shade * 0.92F, false, 0F, false);

        // The reveal at the frame's inner edge, then the deep drop into the mat.
        wall(t, IX0, IY0, IX1, IY1, BEZEL_Z, FRAME_IN, dark, shade, true);
        wall(t, BX0, BY0, BX1, BY1, BACK_Z, BEZEL_IN, dark, shade * 0.78F, true);

        wall(t, MX0, MY0, MX1, MY1, MAT_Z0, MAT_Z1, mat, shade, false);
        drawMat(t, mat, record != null);

        plaqueBody(t, tint(dark, 0.52F), dark);
        t.draw();

        // --- the brushed metal, then its highlight ---
        bind(BRUSHED);
        t.startDrawingQuads();
        t.setBrightness(FULL_BRIGHT);
        brushedParts(t, bright, shade);
        t.draw();

        // The specular pass is additive, and a deferred pack cannot add: its
        // geometry stage writes albedo into a G-buffer, so an "additive" quad just
        // replaces what it covers. The brushed liner and the plaque plate get their
        // brightness from this pass, which is why both came out dark under Vibrant
        // while rendering as bright metal with shaders off.
        //
        // Under a pack, fold the highlight into the base colour instead: draw the
        // brushed parts once more, opaque, at a level between the base and the
        // highlight. Not the same look -- there is no view-dependent glint -- but
        // metal that reads as metal rather than as a dark hole.
        if (shadersActive()) {
            bind(BRUSHED);
            t.startDrawingQuads();
            t.setBrightness(FULL_BRIGHT);
            brushedParts(t, lift(bright, 1.35F), shade);
            t.draw();
        } else {
        bind(BRUSHED_SPEC);
        beginAdditive();
        t.startDrawingQuads();
        t.setBrightness(FULL_BRIGHT);
        // Squared rather than linear, because a highlight is reflected light: in a
        // dark room it should fall away faster than the surface under it, or it
        // survives as bright streaks on a frame that has otherwise gone to shadow.
        // The multiplier above one puts the liner back where it was in daylight --
        // the fall-off is what was wanted in the dark, not a duller metal.
        brushedParts(t, specular, shade * shade * 1.25F);
        t.draw();
        endAdditive();
        }

        if (record != null) drawDisc(record);

        // The pane goes on before the plaque's fittings, because the plaque is fixed
        // to the outside of it.
        drawGlass();

        drawScrews(bright);
        if (record != null) drawPlaque(display.plaque(), tint(dark, 0.30F));

        GL11.glEnable(GL11.GL_LIGHTING);
        GL11.glColor4f(1F, 1F, 1F, 1F);
        OpenGlHelper.setLightmapTextureCoords(
                OpenGlHelper.lightmapTexUnit, lastBrightnessX, lastBrightnessY);
        GL11.glPopMatrix();
    }

    // ------------------------------------------------------------------
    // What the reflective surfaces are looking at
    // ------------------------------------------------------------------

    /**
     * Works out where the camera is in the case's own frame, and what the sky is
     * doing, once per case rather than once per vertex.
     */
    private void surroundings(TileEntity te, double x, double y, double z,
                              int facing, float partial) {
        // The renderer is handed the tile's position relative to the viewer, so the
        // viewer relative to the tile is that negated and put back through the
        // rotation applied to the model.
        double th = facing * (Math.PI / 2);
        rotC = (float) Math.cos(th);
        rotS = (float) Math.sin(th);
        double px = -(x + 0.5), py = -y, pz = -(z + 0.5);
        camX = (float) (rotC * px - rotS * pz) + 0.5F;
        camY = (float) py;
        camZ = (float) (rotS * px + rotC * pz) + 0.5F;

        daylight = 1F;
        sunY = 1F;
        sunZ = 0F;
        World world = te.getWorldObj();
        if (world != null) {
            daylight = world.getSunBrightness(partial);
            // Vanilla swings the sun about the X axis, so it travels the Y-Z plane
            // and never has an X component. Two cases on walls at right angles
            // therefore catch it at different times of day, which is the whole point
            // of computing this rather than painting it.
            float angle = world.getCelestialAngleRadians(partial);
            sunY = (float) Math.cos(angle);
            sunZ = (float) Math.sin(angle);
        }

        // What a ray leaving a surface upward sees, and what one leaving it downward
        // sees. Not a texture: at this size a pane spans a few degrees of sky, and a
        // gradient between the two is all of it that could ever be resolved.
        skyR = 0.34F * daylight + 0.055F;
        skyG = 0.48F * daylight + 0.070F;
        skyB = 0.78F * daylight + 0.110F;
        groundR = 0.13F * daylight + 0.038F;
        groundG = 0.14F * daylight + 0.040F;
        groundB = 0.12F * daylight + 0.044F;
    }

    /**
     * Bounces the eye off a forward-facing point and records what it lands on.
     *
     * The surface normal is always straight out of the case, so the reflection is
     * the view direction with its two in-plane components flipped. Turning the
     * result back into world axes is what makes "up" mean up in the world rather
     * than up relative to whichever wall this is hanging on.
     */
    private void bounce(float vx, float vy, float vz) {
        float dx = camX - vx, dy = camY - vy, dz = camZ - vz;
        float inv = 1F / (float) Math.sqrt(dx * dx + dy * dy + dz * dz);
        float ex = dx * inv, ey = dy * inv, ez = dz * inv;

        // The angle term of Schlick's approximation, left for the caller to weight:
        // glass and steel reflect very different amounts head-on.
        float cos = ez < 0F ? 0F : ez;
        float k = 1F - cos;
        float k2 = k * k;
        hitGrazing = k2 * k2 * k;

        float rx = -ex, ry = -ey, rz = ez;
        float wx = rotC * rx + rotS * rz;
        float wy = ry;
        float wz = -rotS * rx + rotC * rz;

        float up = 0.5F + 0.5F * wy;
        hitR = groundR + (skyR - groundR) * up;
        hitG = groundG + (skyG - groundG) * up;
        hitB = groundB + (skyB - groundB) * up;

        // The sun, if the bounced ray happens to be pointing at it. Two lobes: a
        // tight core from repeated squaring -- six times is the sixty-fourth power,
        // far cheaper than a pow() per vertex -- and a broad halo around it. Real
        // reflected sunlight is never a hard-edged dot, and the halo is also what
        // makes the glint findable rather than something you have to stand in
        // exactly the right place to see.
        float d = wy * sunY + wz * sunZ;
        if (d > 0F) {
            float s = d * d; s *= s; s *= s;
            s *= s; s *= s; s *= s;
            float halo = d * d; halo *= halo; halo *= halo;
            float glint = (s * 3.2F + halo * 0.55F) * daylight;
            hitR += glint; hitG += glint; hitB += glint;
        }
    }

    // ------------------------------------------------------------------
    // The frame and the liner
    // ------------------------------------------------------------------

    /** The moulding: the back, the outer edge, and the three steps of its profile. */
    private void moulding(Tessellator t, int color) {
        // The back. It is against a wall in normal use, so it is easy to forget it
        // exists -- but a case on a wall one block thick is visible from the far
        // side, and with nothing here you look straight through it into the room.
        set(0, X0, Y0, 0F); set(1, X0, Y1, 0F);
        set(2, X1, Y1, 0F); set(3, X1, Y0, 0F);
        emit(t, color, shade * 0.42F, false, 0F, false);

        band(t, X0, Y0, X1, Y1, 0F, FRAME_LIP, color, shade, false, WALL_OUT, 0F);

        float a = X0, b = Y0, c = X1, d = Y1;
        ring(t, a, b, c, d, W_LIP, FRAME_LIP, FRAME_Z, color, shade, RISING, 0F);

        a += W_LIP; b += W_LIP; c -= W_LIP; d -= W_LIP;
        ring(t, a, b, c, d, W_FLAT, FRAME_Z, FRAME_Z, color, shade, FLAT, 0F);

        a += W_FLAT; b += W_FLAT; c -= W_FLAT; d -= W_FLAT;
        ring(t, a, b, c, d, W_CHAM, FRAME_Z, FRAME_IN, color, shade, FALLING, 0F);
    }

    /**
     * Everything brushed: the liner around the opening, and the top of the plaque.
     *
     * One method rather than two, called once for the metal and again for its
     * highlight, so the plaque is always finished in the same metal as the liner and
     * always at the same brightness.
     */
    private void brushedParts(Tessellator t, int color, float level) {
        ring(t, IX0, IY0, IX1, IY1, BW_FLAT, BEZEL_Z, BEZEL_Z, color, level,
             FLAT, METAL_REPEAT);

        float a = IX0 + BW_FLAT, b = IY0 + BW_FLAT;
        float c = IX1 - BW_FLAT, d = IY1 - BW_FLAT;
        ring(t, a, b, c, d, BW_CHAM, BEZEL_Z, BEZEL_IN, color, level,
             FALLING, METAL_REPEAT);

        // The plaque's bevel rises toward the middle, so its top length turns up
        // into the light and its bottom length turns away. That single reversal is
        // what tells the eye the plate is raised rather than sunk.
        ring(t, PL_X0 + PL_INSET, PL_Y0 + PL_INSET, PL_X1 - PL_INSET, PL_Y1 - PL_INSET,
             PL_BEVEL, PL_PLATE_Z, PL_FACE, color, level, RISING, METAL_REPEAT);

        // Turned, so the brushing runs the long way across the plate. An engraved
        // plaque is always finished along its width, never up its short side.
        flat(t, FX0, FY0, FX1, FY1, PL_FACE, color, level, true, METAL_REPEAT, true);
    }

    // ------------------------------------------------------------------
    // The plaque
    // ------------------------------------------------------------------

    /**
     * The body of the plaque: the mount it stands on and the sides of the plate.
     *
     * Only the parts with no material on them are here. The plate's bevel and face
     * are brushed like the liner, so they go down with it in the textured pass and
     * the two cannot drift out of finish with each other.
     */
    private void plaqueBody(Tessellator t, int mount, int edge) {
        box(t, PL_X0, PL_Y0, PL_Z0, PL_X1, PL_Y1, PL_Z1, mount, shade);

        float px0 = PL_X0 + PL_INSET, py0 = PL_Y0 + PL_INSET;
        float px1 = PL_X1 - PL_INSET, py1 = PL_Y1 - PL_INSET;
        box(t, px0, py0, PL_Z0 + 0.06F * P, px1, py1, PL_PLATE_Z, edge, shade);
    }

    /** The four fasteners holding the plate on. */
    private void drawScrews(int metal) {
        Minecraft.getMinecraft().getTextureManager().bindTexture(SCREW);
        smooth();
        GL11.glTexParameteri(GL11.GL_TEXTURE_2D, GL11.GL_TEXTURE_WRAP_S, GL12.GL_CLAMP_TO_EDGE);
        GL11.glTexParameteri(GL11.GL_TEXTURE_2D, GL11.GL_TEXTURE_WRAP_T, GL12.GL_CLAMP_TO_EDGE);

        GL11.glEnable(GL11.GL_BLEND);
        GL11.glBlendFunc(GL11.GL_SRC_ALPHA, GL11.GL_ONE_MINUS_SRC_ALPHA);

        // Tinted by the plate they sit on, and lit a little brighter, since a
        // machined head catches more than the flat around it.
        float k = Math.min(1F, shade * 1.12F) / 255F;
        GL11.glColor4f(((metal >> 16) & 0xFF) * k, ((metal >> 8) & 0xFF) * k,
                       (metal & 0xFF) * k, 1F);

        Tessellator t = Tessellator.instance;
        t.startDrawingQuads();
        t.setBrightness(FULL_BRIGHT);
        screw(t, FX0 + SCREW_IN, FY0 + SCREW_IN);
        screw(t, FX1 - SCREW_IN, FY0 + SCREW_IN);
        screw(t, FX0 + SCREW_IN, FY1 - SCREW_IN);
        screw(t, FX1 - SCREW_IN, FY1 - SCREW_IN);
        t.draw();

        GL11.glDisable(GL11.GL_BLEND);
        GL11.glColor4f(1F, 1F, 1F, 1F);
    }

    private void screw(Tessellator t, float cx, float cy) {
        t.setNormal(0F, 0F, 1F);
        t.addVertexWithUV(cx - SCREW_R, cy - SCREW_R, PL_SCREW_Z, 0, 1);
        t.addVertexWithUV(cx + SCREW_R, cy - SCREW_R, PL_SCREW_Z, 1, 1);
        t.addVertexWithUV(cx + SCREW_R, cy + SCREW_R, PL_SCREW_Z, 1, 0);
        t.addVertexWithUV(cx - SCREW_R, cy + SCREW_R, PL_SCREW_Z, 0, 0);
    }

    /**
     * The name, engraved. Sized to the plate rather than to a fixed scale, so a
     * one-word title is cut large and a long one shrinks to fit instead of being
     * chopped off -- which is how an engraver would actually lay it out. The room it
     * is given stops clear of the fasteners.
     */
    private void drawPlaque(String name, int engraving) {
        if (name == null || name.isEmpty()) return;

        float width = PlaqueFont.width(name);
        if (width <= 0F) return;

        float room = (PL_X1 - PL_X0) - 3.0F * P;
        float tall = (PL_Y1 - PL_Y0) - 1.7F * P;

        float scale = Math.min(room / width, tall / PlaqueFont.capHeight());

        GL11.glPushMatrix();
        GL11.glTranslatef((PL_X0 + PL_X1) / 2F - (width * scale) / 2F,
                          (PL_Y0 + PL_Y1) / 2F - (PlaqueFont.capHeight() * scale) / 2F,
                          PL_TEXT);
        GL11.glScalef(scale, scale, scale);

        PlaqueFont.draw(name, tint(engraving, shade));

        GL11.glPopMatrix();
        GL11.glColor4f(1F, 1F, 1F, 1F);
    }

    // ------------------------------------------------------------------
    // Glass
    // ------------------------------------------------------------------

    /**
     * The pane, reflecting the world it is actually standing in.
     *
     * There is no baked highlight here, because a painted streak is a picture of a
     * reflection and always looks like one: it sits in the same place whatever time
     * it is, whichever way the case faces, and wherever you stand.
     *
     * The consequences of doing it properly are the ones real glass has. Looked at
     * square on the pane is nearly invisible and the record is clean behind it. Step
     * to the side and it whitens over. Walk past and a glint of sun slides across
     * it, because the eye is at a finite distance and each point on the pane bounces
     * toward a slightly different part of the sky. It goes dark at night and dim
     * indoors.
     */
    /**
     * Whether OptiFine is running a shader pack right now.
     *
     * Looked up reflectively and re-checked each call through a cached Method,
     * because a pack can be switched from the video settings without a relaunch,
     * and because OptiFine is not on the compile classpath.
     */
    private static Boolean shadersChecked;
    private static java.lang.reflect.Method isShadersMethod;

    private static boolean shadersActive() {
        if (shadersChecked == null) {
            shadersChecked = Boolean.TRUE;
            try {
                isShadersMethod = Class.forName("Config").getMethod("isShaders");
            } catch (Throwable ignored) {
                isShadersMethod = null;   // no OptiFine: fixed-function, pane is fine
            }
        }
        if (isShadersMethod == null) {
            return false;
        }
        try {
            return Boolean.TRUE.equals(isShadersMethod.invoke(null));
        } catch (Throwable ignored) {
            return false;
        }
    }

    private void drawGlass() {
        bind(WHITE);
        GL11.glEnable(GL11.GL_BLEND);
        GL11.glDepthMask(false);

        Tessellator t = Tessellator.instance;

        // The edges of the pane, which is what gives the record its depth from a
        // three-quarter view. Ordinary blending, because an edge seen through its
        // own thickness tints what is behind it rather than adding to it.
        GL11.glBlendFunc(GL11.GL_SRC_ALPHA, GL11.GL_ONE_MINUS_SRC_ALPHA);
        t.startDrawingQuads();
        t.setBrightness(FULL_BRIGHT);
        t.setColorRGBA_F(0.66F * shade, 0.76F * shade, 0.88F * shade, 0.34F);
        edge(t, GX0, GY0, GX1, GY0);   // bottom, facing out
        edge(t, GX1, GY1, GX0, GY1);   // top
        edge(t, GX0, GY1, GX0, GY0);   // left
        edge(t, GX1, GY0, GX1, GY1);   // right
        t.draw();

        // The pane's face is skipped under a shader pack, and only under one.
        //
        // It is a translucent overlay: at a grazing angle its alpha reaches 1 by
        // design (0.22 + 0.78 * grazing, times 1.35, clamped), and a forward
        // pipeline blends that over the record correctly. A deferred pack does not
        // blend at all in the geometry pass -- it writes albedo to a G-buffer, so
        // whatever is drawn last at a pixel simply wins. The reflection colour then
        // replaced the mat, the disc and the plaque, and the case read as a black
        // rectangle with a frame around it. Measured, not guessed: skipping exactly
        // this call brought all four cases back under Sildur's Vibrant.
        //
        // The rim above still draws, so the pane keeps its edge and the case keeps
        // its depth. What is lost is the reflection, which cannot survive a pass
        // that has nowhere to blend into.
        if (shadersActive()) {
            GL11.glDepthMask(true);
            GL11.glBlendFunc(GL11.GL_SRC_ALPHA, GL11.GL_ONE_MINUS_SRC_ALPHA);
            GL11.glDisable(GL11.GL_BLEND);
            GL11.glColor4f(1F, 1F, 1F, 1F);
            return;
        }

        // The reflection adds light rather than tinting it. Glass reflects on top of
        // what it transmits; subtracting would only ever fog the record.
        GL11.glBlendFunc(GL11.GL_SRC_ALPHA, GL11.GL_ONE);
        t.startDrawingQuads();
        t.setBrightness(FULL_BRIGHT);

        // Both faces of the pane. A sheet of glass reflects off the back surface as
        // well as the front, which is why a real one shows the sun twice, slightly
        // apart, and why the doubling gets wider as you move around it. The back one
        // is weaker: what reaches it has already been through the glass twice. It
        // needs less resolution too, being a soft echo of the first.
        paneGrid(t, GLASS_Z0, 0.45F, 8, 18);
        paneGrid(t, GLASS_Z1, 1F, 12, 26);
        t.draw();

        GL11.glDepthMask(true);
        GL11.glBlendFunc(GL11.GL_SRC_ALPHA, GL11.GL_ONE_MINUS_SRC_ALPHA);
        GL11.glDisable(GL11.GL_BLEND);
        GL11.glColor4f(1F, 1F, 1F, 1F);
    }

    private void paneGrid(Tessellator t, float z, float scale, int nx, int ny) {
        for (int i = 0; i < nx; i++) {
            float x0 = GX0 + (GX1 - GX0) * i / nx;
            float x1 = GX0 + (GX1 - GX0) * (i + 1) / nx;
            for (int j = 0; j < ny; j++) {
                float y0 = GY0 + (GY1 - GY0) * j / ny;
                float y1 = GY0 + (GY1 - GY0) * (j + 1) / ny;

                pane(t, x0, y0, z, scale); pane(t, x1, y0, z, scale);
                pane(t, x1, y1, z, scale); pane(t, x0, y1, z, scale);
            }
        }
    }

    private void pane(Tessellator t, float x, float y, float z, float scale) {
        bounce(x, y, z);
        // Schlick, weighted well above glass's physical four per cent head-on. The
        // honest number is right for a window you are meant to see through and wrong
        // for one that is part of the object: at four per cent the pane simply is
        // not there until you step to the side.
        float strength = (0.22F + 0.78F * hitGrazing) * shade * 1.35F * scale;
        t.setNormal(0F, 0F, 1F);
        t.setColorRGBA_F(hitR, hitG, hitB, strength > 1F ? 1F : strength);
        t.addVertexWithUV(x, y, z, 0D, 0D);
    }

    /**
     * One edge of the pane, running from the first corner to the second along the
     * glass's thickness. Wound so it faces away from the pane's interior, which is
     * the side you can actually see it from.
     */
    private void edge(Tessellator t, float xa, float ya, float xb, float yb) {
        // Ribbon from (xa,ya) to (xb,yb) extruded along +Z, so its normal is the
        // run rotated a quarter turn in the XY plane.
        float dx = xb - xa, dy = yb - ya;
        float len = (float) Math.sqrt(dx * dx + dy * dy);
        if (len < 1.0E-6F) {
            t.setNormal(0F, 0F, 1F);
        } else {
            t.setNormal(dy / len, -dx / len, 0F);
        }
        t.addVertexWithUV(xa, ya, GLASS_Z0, 0D, 0D);
        t.addVertexWithUV(xb, yb, GLASS_Z0, 0D, 0D);
        t.addVertexWithUV(xb, yb, GLASS_Z1, 0D, 0D);
        t.addVertexWithUV(xa, ya, GLASS_Z1, 0D, 0D);
    }

    // ------------------------------------------------------------------
    // The record
    // ------------------------------------------------------------------

    /**
     * The record, from its own high-resolution art rather than the inventory icon.
     * A 16-pixel sprite blown up to most of a block is what made the first version
     * look cheap; this is the same disc drawn at 512.
     */
    private void drawDisc(ItemStack stack) {
        int tier = ItemVinyl.tier(stack);
        Minecraft.getMinecraft().getTextureManager().bindTexture(
                new ResourceLocation("qfcontent",
                        "textures/misc/record_" + TIER_TEXTURE[tier] + ".png"));

        // Grooves at 512 pixels sampled point-for-point onto a disc a few hundred
        // pixels across is exactly the case where nearest-neighbour turns fine rings
        // into moire. Averaged, they read as the sheen off vinyl.
        smooth();
        GL11.glTexParameteri(GL11.GL_TEXTURE_2D, GL11.GL_TEXTURE_WRAP_S, GL12.GL_CLAMP_TO_EDGE);
        GL11.glTexParameteri(GL11.GL_TEXTURE_2D, GL11.GL_TEXTURE_WRAP_T, GL12.GL_CLAMP_TO_EDGE);

        GL11.glEnable(GL11.GL_BLEND);
        GL11.glBlendFunc(GL11.GL_SRC_ALPHA, GL11.GL_ONE_MINUS_SRC_ALPHA);
        GL11.glColor4f(shade, shade, shade, 1F);

        Tessellator t = Tessellator.instance;
        t.startDrawingQuads();
        t.setBrightness(FULL_BRIGHT);
        t.setNormal(0F, 0F, 1F);
        t.addVertexWithUV(DISC_X0, DISC_Y0, DISC_Z, 0, 1);
        t.addVertexWithUV(DISC_X1, DISC_Y0, DISC_Z, 1, 1);
        t.addVertexWithUV(DISC_X1, DISC_Y1, DISC_Z, 1, 0);
        t.addVertexWithUV(DISC_X0, DISC_Y1, DISC_Z, 0, 0);
        t.draw();

        GL11.glDisable(GL11.GL_BLEND);
        GL11.glColor4f(1F, 1F, 1F, 1F);
    }

    // ------------------------------------------------------------------
    // Baked light
    // ------------------------------------------------------------------

    /**
     * The mat, subdivided so it can carry shading no light in this scene provides.
     *
     * Two things are painted into it. A vignette darkening toward the rabbet, which
     * is the contact shadow every recessed panel has and the cheapest way to stop
     * flat geometry reading as a diagram. And, when there is a record, the shadow it
     * casts -- offset down and to the side, so the disc sits above the mat instead of
     * being printed on it. The corners of the disc's own sprite are transparent,
     * which is exactly where that shadow shows.
     *
     * Unlike the glass and the plaque this one cannot be computed: the shadow needs
     * a light with a position, and the case has no lamp of its own.
     */
    private void drawMat(Tessellator t, int color, boolean hasRecord) {
        final int NX = 14, NY = 32;

        // The shadow is thrown down and to the side of the record; the impression an
        // empty case shows sits square, because nothing is casting it.
        float cx = (DISC_X0 + DISC_X1) / 2F + (hasRecord ? 0.10F * P : 0F);
        float cy = (DISC_Y0 + DISC_Y1) / 2F - (hasRecord ? 0.12F * P : 0F);
        float radius = (DISC_X1 - DISC_X0) / 2F;

        for (int i = 0; i < NX; i++) {
            float x0 = MX0 + (MX1 - MX0) * i / NX;
            float x1 = MX0 + (MX1 - MX0) * (i + 1) / NX;
            for (int j = 0; j < NY; j++) {
                float y0 = MY0 + (MY1 - MY0) * j / NY;
                float y1 = MY0 + (MY1 - MY0) * (j + 1) / NY;

                matVertex(t, color, x0, y0, hasRecord, cx, cy, radius);
                matVertex(t, color, x1, y0, hasRecord, cx, cy, radius);
                matVertex(t, color, x1, y1, hasRecord, cx, cy, radius);
                matVertex(t, color, x0, y1, hasRecord, cx, cy, radius);
            }
        }
    }

    private void matVertex(Tessellator t, int color, float x, float y,
                           boolean hasRecord, float cx, float cy, float radius) {
        // An empty case is nothing but this vignette, so it gets a deeper one. With
        // the record in, the disc covers most of the panel and a heavy edge would
        // only crowd it.
        float edge = Math.min(Math.min(x - MX0, MX1 - x), Math.min(y - MY0, MY1 - y));
        float a = 1F - (hasRecord ? 0.45F : 0.58F)
                     * (float) Math.exp(-edge / (0.9F * P));

        float dx = x - cx, dy = y - cy;
        float r = (float) Math.sqrt(dx * dx + dy * dy) / radius;

        if (hasRecord) {
            float k = (r - 1F) / 0.14F;
            a *= 1F - 0.40F * (float) Math.exp(-k * k);
        } else {
            // A faint impression where a record would sit. Without it an empty case
            // is one flat rectangle of nothing, and reads as unfinished rather than
            // as waiting to be filled.
            float k = (r - 1F) / 0.085F;
            a *= 1F - 0.17F * (float) Math.exp(-k * k);
        }

        t.setNormal(0F, 0F, 1F);
        t.setColorOpaque_I(tint(color, shade * a));
        t.addVertexWithUV(x, y, MAT_Z1, 0D, 0D);
    }

    // ------------------------------------------------------------------
    // Geometry
    // ------------------------------------------------------------------

    /**
     * One mitred ring: four trapezoids running between an outer rectangle and one
     * inset from it, meeting at forty-five degrees in the corners.
     *
     * Where the two z values differ the ring is a bevel rather than a flat, and each
     * of the four pieces then faces a different way -- which is the whole reason a
     * moulding reads as a moulding. Each piece stays planar because its z depends
     * only on how far in it is.
     */
    private void ring(Tessellator t, float x0, float y0, float x1, float y1,
                      float inset, float zOut, float zIn,
                      int color, float level, float[] face, float repeat) {
        float ax0 = x0 + inset, ay0 = y0 + inset;
        float ax1 = x1 - inset, ay1 = y1 - inset;
        boolean textured = repeat > 0F;

        set(0, x0, y0, zOut); set(1, x1, y0, zOut);
        set(2, ax1, ay0, zIn); set(3, ax0, ay0, zIn);
        emit(t, color, level * face[0], textured, repeat, true);

        set(0, x0, y1, zOut); set(1, ax0, ay1, zIn);
        set(2, ax1, ay1, zIn); set(3, x1, y1, zOut);
        emit(t, color, level * face[1], textured, repeat, true);

        set(0, x0, y0, zOut); set(1, ax0, ay0, zIn);
        set(2, ax0, ay1, zIn); set(3, x0, y1, zOut);
        emit(t, color, level * face[2], textured, repeat, false);

        set(0, x1, y0, zOut); set(1, x1, y1, zOut);
        set(2, ax1, ay1, zIn); set(3, ax1, ay0, zIn);
        emit(t, color, level * face[3], textured, repeat, false);
    }

    /** A vertical band around a rectangle, facing outward or in toward the centre. */
    private void wall(Tessellator t, float x0, float y0, float x1, float y1,
                      float zLow, float zHigh, int color, float level, boolean inward) {
        band(t, x0, y0, x1, y1, zLow, zHigh, color, level, inward,
             inward ? WALL_IN : WALL_OUT, 0F);
    }

    /**
     * The same band, optionally textured with the material running along its length.
     *
     * A band's texture cannot be mapped from x and y the way a front face is -- one
     * of those is constant along it -- so the length runs down the sheet and the
     * depth runs across.
     */
    private void band(Tessellator t, float x0, float y0, float x1, float y1,
                      float zLow, float zHigh, int color, float level,
                      boolean inward, float[] face, float repeat) {
        boolean textured = repeat > 0F;

        // Bottom edge, facing +y when inward.
        if (inward) { set(0, x1, y0, zLow); set(1, x0, y0, zLow);
                      set(2, x0, y0, zHigh); set(3, x1, y0, zHigh); }
        else        { set(0, x0, y0, zLow); set(1, x1, y0, zLow);
                      set(2, x1, y0, zHigh); set(3, x0, y0, zHigh); }
        emitBand(t, color, level * face[0], textured, repeat, true);

        // Top edge.
        if (inward) { set(0, x0, y1, zLow); set(1, x1, y1, zLow);
                      set(2, x1, y1, zHigh); set(3, x0, y1, zHigh); }
        else        { set(0, x1, y1, zLow); set(1, x0, y1, zLow);
                      set(2, x0, y1, zHigh); set(3, x1, y1, zHigh); }
        emitBand(t, color, level * face[1], textured, repeat, true);

        // Left edge.
        if (inward) { set(0, x0, y0, zLow); set(1, x0, y1, zLow);
                      set(2, x0, y1, zHigh); set(3, x0, y0, zHigh); }
        else        { set(0, x0, y1, zLow); set(1, x0, y0, zLow);
                      set(2, x0, y0, zHigh); set(3, x0, y1, zHigh); }
        emitBand(t, color, level * face[2], textured, repeat, false);

        // Right edge.
        if (inward) { set(0, x1, y1, zLow); set(1, x1, y0, zLow);
                      set(2, x1, y0, zHigh); set(3, x1, y1, zHigh); }
        else        { set(0, x1, y0, zLow); set(1, x1, y1, zLow);
                      set(2, x1, y1, zHigh); set(3, x1, y0, zHigh); }
        emitBand(t, color, level * face[3], textured, repeat, false);
    }

    /** A single front-facing quad, textured or not. */
    private void flat(Tessellator t, float x0, float y0, float x1, float y1, float z,
                      int color, float level, boolean textured, float repeat,
                      boolean turned) {
        set(0, x0, y0, z); set(1, x1, y0, z); set(2, x1, y1, z); set(3, x0, y1, z);
        emit(t, color, level, textured, repeat, turned);
    }

    private void set(int i, float x, float y, float z) {
        qx[i] = x; qy[i] = y; qz[i] = z;
    }

    /** Emits the scratch quad, mapping any texture from its position on the case. */
    /**
     * The outward normal of the quad currently in q[], from its own corners.
     *
     * Tessellator writes a normal per vertex only once setNormal has been called;
     * until then hasNormals is false and gl_Normal keeps whatever the previous
     * draw left. The fixed-function pipeline does not care, because this renderer
     * disables GL_LIGHTING and lights itself. A deferred shader pack very much
     * does: it reads the normal to light the fragment, gets a stale one, and the
     * case goes black. That is the Vibrant blackout.
     */
    private void quadNormal(Tessellator t) {
        float ax = qx[1] - qx[0], ay = qy[1] - qy[0], az = qz[1] - qz[0];
        float bx = qx[3] - qx[0], by = qy[3] - qy[0], bz = qz[3] - qz[0];
        float nx = ay * bz - az * by;
        float ny = az * bx - ax * bz;
        float nz = ax * by - ay * bx;
        float len = (float) Math.sqrt(nx * nx + ny * ny + nz * nz);
        if (len < 1.0E-6F) {
            // Degenerate quad -- face the viewer rather than emit a zero normal,
            // which a shader would normalise into a NaN.
            t.setNormal(0F, 0F, 1F);
        } else {
            t.setNormal(nx / len, ny / len, nz / len);
        }
    }

    private void emit(Tessellator t, int color, float level, boolean textured,
                      float repeat, boolean turned) {
        quadNormal(t);
        t.setColorOpaque_I(tint(color, level));
        for (int i = 0; i < 4; i++) {
            if (!textured) {
                t.addVertexWithUV(qx[i], qy[i], qz[i], 0D, 0D);
            } else if (turned) {
                t.addVertexWithUV(qx[i], qy[i], qz[i], qy[i] * repeat, qx[i] * repeat);
            } else {
                t.addVertexWithUV(qx[i], qy[i], qz[i], qx[i] * repeat, qy[i] * repeat);
            }
        }
    }

    /** The same, for a band, where the second axis is depth rather than position. */
    private void emitBand(Tessellator t, int color, float level, boolean textured,
                          float repeat, boolean turned) {
        quadNormal(t);
        t.setColorOpaque_I(tint(color, level));
        for (int i = 0; i < 4; i++) {
            if (!textured) {
                t.addVertexWithUV(qx[i], qy[i], qz[i], 0D, 0D);
            } else {
                float along = turned ? qx[i] : qy[i];
                t.addVertexWithUV(qx[i], qy[i], qz[i], qz[i] * repeat, along * repeat);
            }
        }
    }

    /** A shaded box. Faces are lit differently so edges read without a texture. */
    private void box(Tessellator t, float x0, float y0, float z0,
                     float x1, float y1, float z1, int color, float level) {
        flat(t, x0, y0, x1, y1, z1, color, level, false, 0F, false);
        band(t, x0, y0, x1, y1, z0, z1, color, level, false, WALL_OUT, 0F);
    }

    // ------------------------------------------------------------------
    // State
    // ------------------------------------------------------------------

    /**
     * Binds a sheet and asks for smooth filtering.
     *
     * Minecraft uploads these with nearest-neighbour sampling, which is right for
     * block art on an atlas and wrong here: a 512-pixel sheet crossing a strip a few
     * pixels wide picks one texel out of a hundred, so the scratches sparkle as you
     * walk past. Linear sampling averages them into the sheen they are meant to be.
     * The parameters live on the texture object, so setting them each frame costs
     * nothing after the first.
     */
    private void bind(ResourceLocation sheet) {
        Minecraft.getMinecraft().getTextureManager().bindTexture(sheet);
        smooth();
        GL11.glTexParameteri(GL11.GL_TEXTURE_2D, GL11.GL_TEXTURE_WRAP_S, GL11.GL_REPEAT);
        GL11.glTexParameteri(GL11.GL_TEXTURE_2D, GL11.GL_TEXTURE_WRAP_T, GL11.GL_REPEAT);
    }

    private void smooth() {
        GL11.glTexParameteri(GL11.GL_TEXTURE_2D, GL11.GL_TEXTURE_MIN_FILTER, GL11.GL_LINEAR);
        GL11.glTexParameteri(GL11.GL_TEXTURE_2D, GL11.GL_TEXTURE_MAG_FILTER, GL11.GL_LINEAR);
    }

    /**
     * Adds light rather than replacing it, over the surface just drawn.
     *
     * A highlight on metal desaturates toward the colour of the light, which no
     * amount of multiplying a tint can produce -- multiplication only ever takes
     * away. Depth writes are off and the test is GL_LEQUAL, so the second pass lands
     * exactly on the first without fighting it.
     */
    private void beginAdditive() {
        GL11.glEnable(GL11.GL_BLEND);
        GL11.glBlendFunc(GL11.GL_ONE, GL11.GL_ONE);
        GL11.glDepthFunc(GL11.GL_LEQUAL);
        GL11.glDepthMask(false);
    }

    private void endAdditive() {
        GL11.glDepthMask(true);
        GL11.glBlendFunc(GL11.GL_SRC_ALPHA, GL11.GL_ONE_MINUS_SRC_ALPHA);
        GL11.glDisable(GL11.GL_BLEND);
        GL11.glColor4f(1F, 1F, 1F, 1F);
    }

    // ------------------------------------------------------------------
    // Colour
    // ------------------------------------------------------------------

    /** Brightens a colour without shifting its hue, for the mat's surround. */
    private static int lift(int rgb, float factor) {
        int r = Math.min(255, (int) (((rgb >> 16) & 0xFF) * factor) + 6);
        int g = Math.min(255, (int) (((rgb >> 8) & 0xFF) * factor) + 6);
        int b = Math.min(255, (int) ((rgb & 0xFF) * factor) + 6);
        return (r << 16) | (g << 8) | b;
    }

    private static int tint(int rgb, float level) {
        if (level > 1F) level = 1F;
        if (level < 0F) level = 0F;
        int r = (int) (((rgb >> 16) & 0xFF) * level);
        int g = (int) (((rgb >> 8) & 0xFF) * level);
        int b = (int) ((rgb & 0xFF) * level);
        return (r << 16) | (g << 8) | b;
    }
}
