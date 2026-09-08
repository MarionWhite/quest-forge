package com.questforge.content.jukebox;

import cpw.mods.fml.relauncher.Side;
import cpw.mods.fml.relauncher.SideOnly;

import net.minecraft.client.Minecraft;
import net.minecraft.client.renderer.Tessellator;
import net.minecraft.client.renderer.tileentity.TileEntitySpecialRenderer;
import net.minecraft.tileentity.TileEntity;
import net.minecraft.util.ResourceLocation;

import org.lwjgl.opengl.GL11;

/**
 * The tower speaker.
 *
 * <h3>Why the grille is a real sheet</h3>
 * Perforated steel is not a picture of holes; it is a sheet with holes in it, and the
 * whole difference is being able to see past it. So the mesh is drawn as an
 * alpha-tested quad with genuinely transparent perforations, and the drivers are
 * modelled a tenth of a block behind it. Walking past the cabinet slides the cones
 * against the holes, and that parallax is what tells the eye there is a box here
 * rather than a photograph of one.
 *
 * The sheet is drawn twice, a hair apart, so at a grazing angle you see the thickness
 * of the metal instead of a zero-width cut. The two passes sit at different depths on
 * purpose -- they are not a multipass at one plane, and nothing here shares a plane
 * with anything else.
 *
 * <h3>The cones move</h3>
 * {@link DirectAudio#amplitude} is the running loudness of the audio actually handed
 * to this speaker's own output, so the woofer follows what this cabinet is playing --
 * not what some other speaker is, and not at all when it is switched off.
 */
@SideOnly(Side.CLIENT)
public class RenderTowerSpeaker extends TileEntitySpecialRenderer {

    private static final ResourceLocation CABINET =
            new ResourceLocation("qfcontent", "textures/entity/tower_cabinet.png");
    private static final ResourceLocation GRILLE =
            new ResourceLocation("qfcontent", "textures/entity/tower_grille.png");
    private static final ResourceLocation CONE =
            new ResourceLocation("qfcontent", "textures/entity/tower_cone.png");

    /** Sides on a driver. Enough that the rim reads as round at arm's length. */
    private static final int SEGMENTS = 32;

    private static final float IN = 0.07F;          // cabinet inset from the block
    private static final float FRONT = IN;          // front face plane
    private static final float BACK = 1F - IN;
    private static final float TOP = 2.0F;

    /**
     * The baffle the drivers mount in, and the cavity behind it.
     *
     * The baffle has real holes cut in it, one per driver, which is the whole point:
     * drawn as a single unbroken quad it sits between the viewer and the cones and
     * hides them completely, which is exactly what went wrong the first time. A
     * driver is a hole in a panel with a cone set back in it, and it has to be built
     * that way or the depth is not there to see.
     *
     * The cavity walls run past the baffle to the inside of the back panel, so if a
     * hole and its driver ever disagree at the edges the gap shows dark box rather
     * than daylight through the model.
     */
    private static final float INNER_Z = BACK - 0.03F;
    private static final float BAFFLE_Z = FRONT + 0.105F;
    private static final float MESH_Z0 = FRONT + 0.012F;
    private static final float MESH_Z1 = FRONT + 0.024F;
    private static final float OPEN_X0 = 0.135F, OPEN_X1 = 0.865F;
    private static final float OPEN_Y0 = 0.115F, OPEN_Y1 = 1.885F;

    /** Drivers: centre height and radius. Woofer, midrange, tweeter. */
    private static final float[][] DRIVERS = {
            { 0.520F, 0.300F },
            { 1.230F, 0.185F },
            { 1.640F, 0.098F },
    };

    /** How far a cone can travel at full tilt. Small: real ones barely move. */
    private static final float THROW = 0.028F;

    /** Light in model space, from above and in front. */
    private static final float LX = -0.36F, LY = 0.74F, LZ = -0.57F;

    private final float[] sin = new float[SEGMENTS + 1];
    private final float[] cos = new float[SEGMENTS + 1];

    public RenderTowerSpeaker() {
        for (int i = 0; i <= SEGMENTS; i++) {
            double a = Math.PI * 2.0 * i / SEGMENTS;
            sin[i] = (float) Math.sin(a);
            cos[i] = (float) Math.cos(a);
        }
    }

    @Override
    public void renderTileEntityAt(TileEntity te, double x, double y, double z, float partial) {
        if (!(te instanceof TileEntityTowerSpeaker)) return;
        TileEntityTowerSpeaker speaker = (TileEntityTowerSpeaker) te;

        int meta = te.getWorldObj() == null ? 0
                : te.getWorldObj().getBlockMetadata(te.xCoord, te.yCoord, te.zCoord);
        int look = BlockTowerSpeaker.facing(meta);

        int light = te.getWorldObj() == null ? 0xF000F0
                : te.getWorldObj().getLightBrightnessForSkyBlocks(
                        te.xCoord, te.yCoord + 1, te.zCoord, 0);

        float drive = DirectAudio.amplitude(speaker.code());

        GL11.glPushMatrix();
        GL11.glTranslated(x, y, z);
        // Turn the cabinet to face the way it was placed, about its own middle.
        GL11.glTranslatef(0.5F, 0F, 0.5F);
        GL11.glRotatef(-look * 90F, 0F, 1F, 0F);
        GL11.glTranslatef(-0.5F, 0F, -0.5F);

        boolean lit = GL11.glIsEnabled(GL11.GL_LIGHTING);
        if (lit) GL11.glDisable(GL11.GL_LIGHTING);

        // A TESR draws with back-face culling on, unlike the entity pass the JBL is
        // drawn in, and a quad wound the wrong way there is not a dim face -- it is
        // no face at all, which is what left two sides of the cabinet see-through.
        // The shape is a closed opaque box, so the far faces are behind the near
        // ones and the depth test settles them; turning culling off costs a little
        // fill and removes a whole class of bug that cannot be seen to be absent.
        boolean culled = GL11.glIsEnabled(GL11.GL_CULL_FACE);
        if (culled) GL11.glDisable(GL11.GL_CULL_FACE);

        GL11.glColor4f(1F, 1F, 1F, 1F);

        Tessellator t = Tessellator.instance;

        bindTexture(CABINET);
        t.startDrawingQuads();
        t.setBrightness(light);
        cabinet(t);
        t.draw();

        bindTexture(CONE);
        t.startDrawingQuads();
        t.setBrightness(light);
        for (int i = 0; i < DRIVERS.length; i++) {
            // The tweeter barely moves; the woofer does most of the work, which is
            // also true of the music, so excursion is scaled by driver size.
            float travel = drive * THROW * (i == 0 ? 1.0F : i == 1 ? 0.55F : 0.18F);
            driver(t, DRIVERS[i][0], DRIVERS[i][1], travel);
        }
        t.draw();

        grille(t, light);

        if (culled) GL11.glEnable(GL11.GL_CULL_FACE);
        if (lit) GL11.glEnable(GL11.GL_LIGHTING);
        GL11.glPopMatrix();
    }

    // ------------------------------------------------------------------

    /**
     * The box, and the cavity cut into its front.
     *
     * The front face is drawn as a frame -- four quads around the opening -- rather
     * than a full panel with something laid over it, so what is behind the grille is
     * genuinely open. The walls of the cavity run all the way to the inside of the
     * back panel, which is what gives the drivers a dark volume to stand in instead
     * of a surface to be flattened against.
     */
    private void cabinet(Tessellator t) {
        float s;

        // Sides
        s = shade(-1F, 0F, 0F);
        quad(t, s, IN, 0F, FRONT, IN, TOP, FRONT, IN, TOP, BACK, IN, 0F, BACK);
        s = shade(1F, 0F, 0F);
        quad(t, s, 1F - IN, 0F, BACK, 1F - IN, TOP, BACK, 1F - IN, TOP, FRONT, 1F - IN, 0F, FRONT);

        // Back and top
        s = shade(0F, 0F, 1F);
        quad(t, s, 1F - IN, 0F, BACK, 1F - IN, TOP, BACK, IN, TOP, BACK, IN, 0F, BACK);
        s = shade(0F, 1F, 0F);
        quad(t, s, IN, TOP, FRONT, 1F - IN, TOP, FRONT, 1F - IN, TOP, BACK, IN, TOP, BACK);
        s = shade(0F, -1F, 0F);
        quad(t, s, IN, 0F, BACK, 1F - IN, 0F, BACK, 1F - IN, 0F, FRONT, IN, 0F, FRONT);

        // The front face, as a frame around the opening.
        s = shade(0F, 0F, -1F);
        quad(t, s, IN, 0F, FRONT, IN, OPEN_Y0, FRONT, 1F - IN, OPEN_Y0, FRONT, 1F - IN, 0F, FRONT);
        quad(t, s, IN, OPEN_Y1, FRONT, IN, TOP, FRONT, 1F - IN, TOP, FRONT, 1F - IN, OPEN_Y1, FRONT);
        quad(t, s, IN, OPEN_Y0, FRONT, OPEN_X0, OPEN_Y0, FRONT, OPEN_X0, OPEN_Y1, FRONT, IN, OPEN_Y1, FRONT);
        quad(t, s, OPEN_X1, OPEN_Y0, FRONT, 1F - IN, OPEN_Y0, FRONT, 1F - IN, OPEN_Y1, FRONT, OPEN_X1, OPEN_Y1, FRONT);

        // The cavity: four walls running back to the inside of the box.
        s = shade(0F, 0F, -0.4F);
        quad(t, s, OPEN_X0, OPEN_Y0, FRONT, OPEN_X0, OPEN_Y1, FRONT, OPEN_X0, OPEN_Y1, INNER_Z, OPEN_X0, OPEN_Y0, INNER_Z);
        quad(t, s, OPEN_X1, OPEN_Y0, INNER_Z, OPEN_X1, OPEN_Y1, INNER_Z, OPEN_X1, OPEN_Y1, FRONT, OPEN_X1, OPEN_Y0, FRONT);
        quad(t, s, OPEN_X0, OPEN_Y1, FRONT, OPEN_X1, OPEN_Y1, FRONT, OPEN_X1, OPEN_Y1, INNER_Z, OPEN_X0, OPEN_Y1, INNER_Z);
        quad(t, s, OPEN_X0, OPEN_Y0, INNER_Z, OPEN_X1, OPEN_Y0, INNER_Z, OPEN_X1, OPEN_Y0, FRONT, OPEN_X0, OPEN_Y0, FRONT);

        // The inside of the back panel, far enough away to read as depth rather
        // than as a lid on the drivers.
        s = shade(0F, 0F, -1F) * 0.30F;
        quad(t, s, OPEN_X0, OPEN_Y0, INNER_Z, OPEN_X0, OPEN_Y1, INNER_Z,
                   OPEN_X1, OPEN_Y1, INNER_Z, OPEN_X1, OPEN_Y0, INNER_Z);

        baffle(t);
    }

    /**
     * The baffle, as a panel with a hole cut for each driver.
     *
     * Built in horizontal bands. The three drivers share a centre line and their
     * height ranges do not overlap, so any given band meets at most one hole and is
     * either one quad clean across or two -- left of the hole and right of it. Where
     * a band crosses a circle its half-width is taken at whichever of its two edges
     * is further from the driver's centre, so the panel laps very slightly over the
     * basket rim: an overlap hides a sliver of metal, whereas the opposite error
     * would open a ragged seam onto the dark inside of the box.
     */
    private void baffle(Tessellator t) {
        float s = shade(0F, 0F, -1F) * 0.80F;
        float y = OPEN_Y0;

        for (int d = 0; d < DRIVERS.length; d++) {
            float cy = DRIVERS[d][0], r = DRIVERS[d][1];
            float low = cy - r, high = cy + r;
            if (low > y) band(t, s, y, low);

            int rows = SEGMENTS / 2;
            for (int i = 0; i < rows; i++) {
                float y0 = low + 2F * r * i / rows;
                float y1 = low + 2F * r * (i + 1) / rows;
                float far = Math.abs(y0 - cy) > Math.abs(y1 - cy) ? y0 : y1;
                float dy = far - cy;
                float dx = (float) Math.sqrt(Math.max(0F, r * r - dy * dy));
                quad(t, s, OPEN_X0, y0, BAFFLE_Z, OPEN_X0, y1, BAFFLE_Z,
                           0.5F - dx, y1, BAFFLE_Z, 0.5F - dx, y0, BAFFLE_Z);
                quad(t, s, 0.5F + dx, y0, BAFFLE_Z, 0.5F + dx, y1, BAFFLE_Z,
                           OPEN_X1, y1, BAFFLE_Z, OPEN_X1, y0, BAFFLE_Z);
            }
            y = high;
        }

        if (OPEN_Y1 > y) band(t, s, y, OPEN_Y1);
    }

    /** One unbroken course of baffle, right across the opening. */
    private void band(Tessellator t, float s, float y0, float y1) {
        quad(t, s, OPEN_X0, y0, BAFFLE_Z, OPEN_X0, y1, BAFFLE_Z,
                   OPEN_X1, y1, BAFFLE_Z, OPEN_X1, y0, BAFFLE_Z);
    }

    /**
     * One driver: a surround at the baffle, and a cone dished back behind it.
     *
     * The cone is a real cone -- the apex genuinely sits deeper than the rim -- which
     * a flat disc textured to look like one does not survive being walked past. Its
     * depth is scaled by the driver rather than fixed, because one depth for all
     * three would leave the woofer a saucer and the tweeter a well.
     *
     * Excursion moves the cone and the inner edge of the surround together while the
     * mounting flange stays put, so the surround stretches the way rubber does. The
     * travel is toward the grille: a cone that pumped away from the listener would be
     * moving the wrong way.
     */
    private void driver(Tessellator t, float cy, float radius, float travel) {
        float cx = 0.5F;
        float depth = 0.045F + radius * 0.34F;

        float flangeZ = BAFFLE_Z;                      // fixed, gripped by the baffle
        float lipZ = BAFFLE_Z + 0.022F - travel;       // inner edge of the surround
        float apexZ = lipZ + depth;                    // the dust cap, deepest point

        float lipR = radius * 0.90F;

        // The surround: a short roll from the flange in to the cone's edge.
        for (int i = 0; i < SEGMENTS; i++) {
            int j = i + 1;
            float s0 = shade(sin[i], cos[i], -0.55F) * 0.72F;
            float s1 = shade(sin[j], cos[j], -0.55F) * 0.72F;
            float ue0 = 0.5F + sin[i] * 0.5F, ve0 = 0.5F - cos[i] * 0.5F;
            float ue1 = 0.5F + sin[j] * 0.5F, ve1 = 0.5F - cos[j] * 0.5F;
            float ui0 = 0.5F + sin[i] * 0.45F, vi0 = 0.5F - cos[i] * 0.45F;
            float ui1 = 0.5F + sin[j] * 0.45F, vi1 = 0.5F - cos[j] * 0.45F;
            vertex(t, s0, cx + sin[i] * radius, cy + cos[i] * radius, flangeZ, ue0, ve0);
            vertex(t, s1, cx + sin[j] * radius, cy + cos[j] * radius, flangeZ, ue1, ve1);
            vertex(t, s1, cx + sin[j] * lipR, cy + cos[j] * lipR, lipZ, ui1, vi1);
            vertex(t, s0, cx + sin[i] * lipR, cy + cos[i] * lipR, lipZ, ui0, vi0);
        }

        // The cone, as a fan from the dust cap out to the surround. Shaded off the
        // cone's own slope, so the dish catches the light around its circumference
        // instead of reading as one flat colour.
        for (int i = 0; i < SEGMENTS; i++) {
            int j = i + 1;
            float s0 = shade(sin[i] * depth, cos[i] * depth, -lipR);
            float s1 = shade(sin[j] * depth, cos[j] * depth, -lipR);
            float u0 = 0.5F + sin[i] * 0.45F, v0 = 0.5F - cos[i] * 0.45F;
            float u1 = 0.5F + sin[j] * 0.45F, v1 = 0.5F - cos[j] * 0.45F;
            float mid = (s0 + s1) * 0.5F;
            vertex(t, mid, cx, cy, apexZ, 0.5F, 0.5F);
            vertex(t, s0, cx + sin[i] * lipR, cy + cos[i] * lipR, lipZ, u0, v0);
            vertex(t, s1, cx + sin[j] * lipR, cy + cos[j] * lipR, lipZ, u1, v1);
            vertex(t, mid, cx, cy, apexZ, 0.5F, 0.5F);
        }
    }

    /**
     * The perforated sheet, twice.
     *
     * Alpha testing rather than blending: a blended grille would need sorting against
     * the drivers behind it, and at this hole count the edges are a pixel wide
     * anyway. The threshold is set high enough that a half-covered edge texel falls
     * on the metal side, which keeps the holes crisp instead of haloed.
     */
    private void grille(Tessellator t, int light) {
        bindTexture(GRILLE);

        boolean wasAlpha = GL11.glIsEnabled(GL11.GL_ALPHA_TEST);
        GL11.glEnable(GL11.GL_ALPHA_TEST);
        GL11.glAlphaFunc(GL11.GL_GREATER, 0.5F);

        // The sheet is 512 wide by 1024 tall, so a v unit is twice as many texels as
        // a u unit. Scaling both by the same number is what squashed the holes to
        // half height and turned the perforation into a weave; the 0.5 puts a texel
        // the same size on both axes, which is what makes the holes round and the
        // stagger read as punched metal.
        float u0 = 0F, u1 = (OPEN_X1 - OPEN_X0);
        float v0 = 0F, v1 = (OPEN_Y1 - OPEN_Y0) * 0.5F;

        t.startDrawingQuads();
        t.setBrightness(light);

        float front = shade(0F, 0F, -1F);
        sheet(t, front, MESH_Z0, u0, v0, u1, v1);
        // The back face of the same sheet, a hair deeper, so the metal has thickness
        // when you look along it rather than being a cut with no material.
        sheet(t, front * 0.55F, MESH_Z1, u0, v0, u1, v1);

        t.draw();

        GL11.glAlphaFunc(GL11.GL_GREATER, 0.1F);
        if (!wasAlpha) GL11.glDisable(GL11.GL_ALPHA_TEST);
    }

    private void sheet(Tessellator t, float s, float z, float u0, float v0, float u1, float v1) {
        vertex(t, s, OPEN_X0, OPEN_Y0, z, u0, v1);
        vertex(t, s, OPEN_X0, OPEN_Y1, z, u0, v0);
        vertex(t, s, OPEN_X1, OPEN_Y1, z, u1, v0);
        vertex(t, s, OPEN_X1, OPEN_Y0, z, u1, v1);
    }

    // ------------------------------------------------------------------

    private void quad(Tessellator t, float s,
                      float ax, float ay, float az, float bx, float by, float bz,
                      float cx, float cy, float cz, float dx, float dy, float dz) {
        // Cabinet panels take their texture from where they are, so the flake does
        // not swim when a face is a different size from its neighbour.
        vertex(t, s, ax, ay, az, ax + az, ay);
        vertex(t, s, bx, by, bz, bx + bz, by);
        vertex(t, s, cx, cy, cz, cx + cz, cy);
        vertex(t, s, dx, dy, dz, dx + dz, dy);
    }

    private float shade(float nx, float ny, float nz) {
        float len = (float) Math.sqrt(nx * nx + ny * ny + nz * nz);
        if (len < 1.0E-5F) return 1F;
        float d = (nx * LX + ny * LY + nz * LZ) / len;
        return 0.54F + 0.46F * (d < 0F ? 0F : d);
    }

    private void vertex(Tessellator t, float s, float x, float y, float z, float u, float v) {
        t.setColorOpaque_F(s, s, s);
        t.addVertexWithUV(x, y, z, u, v);
    }
}
