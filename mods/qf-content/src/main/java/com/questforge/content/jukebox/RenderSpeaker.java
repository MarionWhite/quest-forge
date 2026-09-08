package com.questforge.content.jukebox;

import cpw.mods.fml.common.eventhandler.SubscribeEvent;
import cpw.mods.fml.relauncher.Side;
import cpw.mods.fml.relauncher.SideOnly;

import net.minecraft.client.Minecraft;
import net.minecraft.client.renderer.Tessellator;
import net.minecraft.entity.player.EntityPlayer;
import net.minecraft.item.ItemStack;
import net.minecraft.util.ResourceLocation;
import net.minecraftforge.client.event.RenderPlayerEvent;

import org.lwjgl.opengl.GL11;

/**
 * The JBL, riding on the player's right shoulder.
 *
 * It is drawn rather than modelled: a lathe turns a profile -- cloth barrel, rubber
 * bumper, rounded shoulder, end disc -- into rings, and the rings into bands. That
 * buys a silhouette with no visible facets at 48 segments, which is the whole point
 * of a "high resolution" speaker; a box model would read as a brick no matter how
 * good the texture on it was.
 *
 * Three sheets are bound in turn, so the cloth, the rubber and the driver each get a
 * full-resolution texture of their own instead of sharing one atlas. That costs two
 * extra binds per player per frame, which at the number of players this pack will
 * ever hold is not worth folding an atlas around.
 *
 * <h3>The space this draws in</h3>
 * Specials.Post fires inside the biped model's own frame, so this works in model
 * coordinates: <b>+y is down, -z is forward, -x is the player's right</b>, and one
 * unit is one block once {@code postRender(0.0625F)} has been through. Culling is
 * already off for the whole entity render, which is why winding is not fussed over
 * below.
 */
@SideOnly(Side.CLIENT)
public class RenderSpeaker {

    private static final ResourceLocation SLEEVE =
            new ResourceLocation("qfcontent", "textures/entity/jbl_sleeve.png");
    private static final ResourceLocation SHELL =
            new ResourceLocation("qfcontent", "textures/entity/jbl_shell.png");
    private static final ResourceLocation CAP =
            new ResourceLocation("qfcontent", "textures/entity/jbl_cap.png");

    /** Sides around the barrel. Enough that the outline reads as a curve. */
    private static final int SEGMENTS = 48;

    private static final float R = 0.214F;      // the cloth barrel
    private static final float BUMP = 0.226F;   // the rubber bumper, proud of it
    private static final float CLOTH_Z = 0.309F;
    private static final float END_Z = 0.486F;
    private static final float DISC_R = 0.189F;

    /**
     * Where it sits: over the right shoulder, resting on it, and set back so that
     * the length in front of the shoulder is shell rather than cloth. That is what
     * gives the hand somewhere to grip that is not on top of the lettering.
     */
    private static final float AT_X = -0.345F;
    private static final float AT_Y = -0.185F;
    private static final float AT_Z = 0.050F;

    /**
     * The end shell's profile, from the cloth out to the face. Each entry is
     * {z, radius}; the step at the start is the bumper's lip, and the last three
     * roll the corner over so the end does not finish on a hard edge.
     */
    private static final float[][] PROFILE = {
            { CLOTH_Z,  R      },
            { 0.318F,   BUMP   },
            { 0.416F,   BUMP   },
            { 0.456F,   0.217F },
            { 0.478F,   0.202F },
            { END_Z,    DISC_R },
    };

    /** Light in model space: from above and a little in front. */
    private static final float LX = -0.34F, LY = -0.82F, LZ = -0.46F;

    private final float[] sin = new float[SEGMENTS + 1];
    private final float[] cos = new float[SEGMENTS + 1];
    private final float[] u = new float[SEGMENTS + 1];

    public RenderSpeaker() {
        for (int i = 0; i <= SEGMENTS; i++) {
            double a = Math.PI * 2.0 * i / SEGMENTS;
            sin[i] = (float) Math.sin(a);
            cos[i] = (float) Math.cos(a);
            // u = 0.5 points outboard, which puts the wordmark on the side people
            // see and the wrap seam against the player's neck where nobody looks.
            u[i] = 0.5F + (float) ((a + Math.PI / 2.0) / (Math.PI * 2.0));
        }
    }

    // ------------------------------------------------------------------
    // The hook
    // ------------------------------------------------------------------

    /**
     * Raises the arm before the body draws.
     *
     * The holder is set here and cleared in Post so the pose cannot leak into the
     * first-person hand, which draws the same model part outside any player render.
     */
    @SubscribeEvent
    public void onRenderPlayerPre(RenderPlayerEvent.Pre event) {
        SpeakerArm.carrying(null);
        if (!carrying(event.entityPlayer)) return;
        SpeakerArm.install(event.renderer);
        SpeakerArm.carrying(event.entityPlayer);
    }

    @SubscribeEvent
    public void onRenderPlayerPost(RenderPlayerEvent.Post event) {
        SpeakerArm.carrying(null);
    }

    /**
     * Drops the flat sprite from the hand. The speaker itself is the item now, and
     * a second one hanging off a raised fist reads as a bug.
     */
    @SubscribeEvent
    public void onRenderSpecialsPre(RenderPlayerEvent.Specials.Pre event) {
        if (carrying(event.entityPlayer)) event.renderItem = false;
    }

    private static boolean carrying(EntityPlayer player) {
        if (player == null) return false;
        ItemStack held = player.getHeldItem();
        return held != null && held.getItem() instanceof ItemSpeaker;
    }

    @SubscribeEvent
    public void onRenderSpecials(RenderPlayerEvent.Specials.Post event) {
        EntityPlayer player = event.entityPlayer;
        if (!carrying(player)) return;

        GL11.glPushMatrix();
        // Into the body's frame, so the speaker leans with the torso rather than
        // hanging in the air beside a player who is turning.
        event.renderer.modelBipedMain.bipedBody.postRender(0.0625F);

        GL11.glTranslatef(AT_X, AT_Y, AT_Z);
        // A little off square in both directions: dead parallel to the shoulders
        // reads as a prop bolted on, and the shoulder itself slopes outward.
        GL11.glRotatef(-7.0F, 0.0F, 1.0F, 0.0F);
        GL11.glRotatef(-6.0F, 0.0F, 0.0F, 1.0F);

        draw(player.getBrightnessForRender(event.partialRenderTick));

        GL11.glPopMatrix();
    }

    // ------------------------------------------------------------------
    // The speaker
    // ------------------------------------------------------------------

    /** The speaker at the origin, axis along z, in blocks. Public for first person. */
    public void draw(int light) {
        Minecraft game = Minecraft.getMinecraft();
        Tessellator t = Tessellator.instance;

        boolean lit = GL11.glIsEnabled(GL11.GL_LIGHTING);
        // Shading here is per-vertex and computed from the lathe's own normals; the
        // fixed-function lights would fight it, and Tessellator sends no normals of
        // its own anyway, so leaving them on would flat-light the whole barrel.
        if (lit) GL11.glDisable(GL11.GL_LIGHTING);
        GL11.glColor4f(1F, 1F, 1F, 1F);

        game.getTextureManager().bindTexture(SLEEVE);
        t.startDrawingQuads();
        t.setBrightness(light);
        barrel(t, -CLOTH_Z, R, CLOTH_Z, R, 0F, 1F);
        t.draw();

        game.getTextureManager().bindTexture(SHELL);
        t.startDrawingQuads();
        t.setBrightness(light);
        for (int end = 0; end < 2; end++) {
            float side = end == 0 ? 1F : -1F;
            float v = 0F;
            for (int i = 0; i + 1 < PROFILE.length; i++) {
                float z0 = PROFILE[i][0] * side, r0 = PROFILE[i][1];
                float z1 = PROFILE[i + 1][0] * side, r1 = PROFILE[i + 1][1];
                // v by arc length, so the pebbling keeps its scale around the roll
                // instead of stretching over the long straight section.
                float dz = PROFILE[i + 1][0] - PROFILE[i][0];
                float dr = r1 - r0;
                float v1 = v + (float) Math.sqrt(dz * dz + dr * dr) * 6.0F;
                barrel(t, z0, r0, z1, r1, v, v1);
                v = v1;
            }
        }
        bar(t);
        t.draw();

        game.getTextureManager().bindTexture(CAP);
        t.startDrawingQuads();
        t.setBrightness(light);
        disc(t, END_Z, 1F);
        disc(t, -END_Z, -1F);
        t.draw();

        if (lit) GL11.glEnable(GL11.GL_LIGHTING);
    }

    /**
     * One band of the lathe, between two rings of the profile.
     *
     * The normal is the profile's own: perpendicular to the segment in the (r, z)
     * plane, swung round by the segment angle. Getting that right is what makes the
     * rolled corners read as rolled rather than as a stack of cylinders.
     */
    private void barrel(Tessellator t, float z0, float r0, float z1, float r1,
                        float v0, float v1) {
        float dz = z1 - z0, dr = r1 - r0;
        float len = (float) Math.sqrt(dz * dz + dr * dr);
        if (len < 1.0E-6F) return;
        // Outward in the plane: (dz, -dr) rotated to point away from the axis.
        float nr = dz / len, nz = -dr / len;

        for (int i = 0; i < SEGMENTS; i++) {
            int j = i + 1;
            float sA = shade(sin[i] * nr, -cos[i] * nr, nz);
            float sB = shade(sin[j] * nr, -cos[j] * nr, nz);

            vertex(t, sA, sin[i] * r0, -cos[i] * r0, z0, u[i], v0);
            vertex(t, sB, sin[j] * r0, -cos[j] * r0, z0, u[j], v0);
            vertex(t, sB, sin[j] * r1, -cos[j] * r1, z1, u[j], v1);
            vertex(t, sA, sin[i] * r1, -cos[i] * r1, z1, u[i], v1);
        }
    }

    /** The end face, as a fan of quads sharing the centre. */
    private void disc(Tessellator t, float z, float facing) {
        float s = shade(0F, 0F, facing);
        for (int i = 0; i < SEGMENTS; i++) {
            int j = i + 1;
            float u0 = 0.5F + sin[i] * 0.5F, v0 = 0.5F - cos[i] * 0.5F;
            float u1 = 0.5F + sin[j] * 0.5F, v1 = 0.5F - cos[j] * 0.5F;

            vertex(t, s, 0F, 0F, z, 0.5F, 0.5F);
            vertex(t, s, sin[i] * DISC_R, -cos[i] * DISC_R, z, u0, v0);
            vertex(t, s, sin[j] * DISC_R, -cos[j] * DISC_R, z, u1, v1);
            // A fan needs three corners; the fourth doubles the last, which the
            // quad tessellator is happy with and which costs nothing.
            vertex(t, s, sin[j] * DISC_R, -cos[j] * DISC_R, z, u1, v1);
        }
    }

    /**
     * The control bar along the top: a raised rubber strip with walls, the one piece
     * of hardware that is visible from above while it is on a shoulder.
     */
    private void bar(Tessellator t) {
        final int span = 5;                 // segments either side of top dead centre
        final float lift = 0.015F;
        final float z0 = -0.170F, z1 = 0.170F;

        int from = SEGMENTS - span;
        for (int k = 0; k < span * 2; k++) {
            int i = (from + k) % SEGMENTS, j = (from + k + 1) % SEGMENTS;
            float r = R + lift;
            float sA = shade(sin[i], -cos[i], 0F);
            float sB = shade(sin[j], -cos[j], 0F);
            float va = 0.10F + k * 0.06F, vb = va + 0.06F;

            vertex(t, sA, sin[i] * r, -cos[i] * r, z0, 0.20F, va);
            vertex(t, sB, sin[j] * r, -cos[j] * r, z0, 0.20F, vb);
            vertex(t, sB, sin[j] * r, -cos[j] * r, z1, 0.62F, vb);
            vertex(t, sA, sin[i] * r, -cos[i] * r, z1, 0.62F, va);
        }

        // The two ends of the strip, so it has thickness rather than being a decal.
        for (int e = 0; e < 2; e++) {
            float z = e == 0 ? z0 : z1;
            float s = shade(0F, 0F, e == 0 ? -1F : 1F);
            for (int k = 0; k < span * 2; k++) {
                int i = (from + k) % SEGMENTS, j = (from + k + 1) % SEGMENTS;
                vertex(t, s, sin[i] * R, -cos[i] * R, z, 0.72F, 0.10F);
                vertex(t, s, sin[j] * R, -cos[j] * R, z, 0.72F, 0.16F);
                vertex(t, s, sin[j] * (R + lift), -cos[j] * (R + lift), z, 0.80F, 0.16F);
                vertex(t, s, sin[i] * (R + lift), -cos[i] * (R + lift), z, 0.80F, 0.10F);
            }
        }
    }

    // ------------------------------------------------------------------

    /** Lambert against a fixed key, on a floor bright enough to keep detail. */
    private float shade(float nx, float ny, float nz) {
        float d = nx * LX + ny * LY + nz * LZ;
        return 0.52F + 0.48F * (d < 0F ? 0F : d);
    }

    private void vertex(Tessellator t, float shade, float x, float y, float z,
                        float u, float v) {
        t.setColorOpaque_F(shade, shade, shade);
        t.addVertexWithUV(x, y, z, u, v);
    }
}
