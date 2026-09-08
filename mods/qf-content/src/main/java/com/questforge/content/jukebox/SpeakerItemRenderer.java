package com.questforge.content.jukebox;

import cpw.mods.fml.relauncher.Side;
import cpw.mods.fml.relauncher.SideOnly;

import net.minecraft.client.Minecraft;
import net.minecraft.client.entity.AbstractClientPlayer;
import net.minecraft.client.renderer.entity.RenderManager;
import net.minecraft.client.renderer.entity.RenderPlayer;
import net.minecraft.item.ItemStack;
import net.minecraftforge.client.IItemRenderer;

import org.lwjgl.opengl.GL11;

/**
 * What you see of your own JBL, in first person.
 *
 * The third-person speaker rides the biped model, which does not exist in first
 * person -- there is only a hand, and by default that hand holds a flat sprite of
 * the item. So this replaces the sprite with the two things you would actually see
 * of a speaker on your own right shoulder: the near end of the speaker itself,
 * jutting forward past your cheek, and your arm coming up to it.
 *
 * <h3>Getting somewhere you can reason about</h3>
 * 1.7.10 has no RenderHandEvent -- that arrived in 1.8 -- so the only way in is an
 * IItemRenderer for EQUIPPED_FIRST_PERSON. By the time one is called, the matrix has
 * been through {@code ItemRenderer.renderItemInFirstPerson} (anchor, swing, and a
 * scale of 0.4) and then {@code ForgeHooksClient.renderEquippedItem}. Placing
 * anything by trial and error inside that is guesswork, so the first thing this does
 * is unwind the two parts of it that are constant -- Forge's half-block offset and
 * the item scale and yaw -- which lands us back at the hand's anchor with
 * camera-aligned axes and one unit to the block. Every number below is then a plain
 * measurement in front of the player's eye: +x right, +y up, -z forward.
 *
 * Asking for the EQUIPPED_BLOCK helper is what keeps that unwind short: it is the
 * branch where Forge applies a single translate rather than its own scale-and-rotate
 * pose for flat items.
 */
@SideOnly(Side.CLIENT)
public class SpeakerItemRenderer implements IItemRenderer {

    /** Undoes ItemRenderer's 0.4 item scale, back to one unit per block. */
    private static final float UNSCALE = 2.5F;

    /** The speaker's middle, measured from the hand's anchor. */
    private static final float SP_X = -0.02F, SP_Y = 0.14F, SP_Z = 0.42F;
    /** Turned in toward the eye a little, the way it sits on a shoulder. */
    private static final float SP_YAW = -9.0F, SP_ROLL = -6.0F;

    /** The arm's shoulder, from the same anchor. It rises into view from below. */
    private static final float ARM_X = -0.03F, ARM_Y = -0.62F, ARM_Z = 0.16F;
    /** Leaned back and inward so the hand finishes under the speaker. */
    private static final float ARM_PITCH = 14.0F, ARM_ROLL = -9.0F;

    private final RenderSpeaker speaker;

    public SpeakerItemRenderer(RenderSpeaker speaker) {
        this.speaker = speaker;
    }

    // ------------------------------------------------------------------

    @Override
    public boolean handleRenderType(ItemStack item, ItemRenderType type) {
        // Third person already draws the real speaker off the biped model, and the
        // inventory wants the icon, so this owns the first-person view alone.
        return type == ItemRenderType.EQUIPPED_FIRST_PERSON;
    }

    @Override
    public boolean shouldUseRenderHelper(ItemRenderType type, ItemStack item,
                                         ItemRendererHelper helper) {
        // The short branch: one translate, which is trivial to undo. The other
        // branch poses the item like a flat sprite, which is what we are replacing.
        return helper == ItemRendererHelper.EQUIPPED_BLOCK;
    }

    @Override
    public void renderItem(ItemRenderType type, ItemStack item, Object... data) {
        Minecraft game = Minecraft.getMinecraft();
        if (game.thePlayer == null || game.theWorld == null) return;

        AbstractClientPlayer player = game.thePlayer;
        int light = player.getBrightnessForRender(0F);

        GL11.glPushMatrix();

        // Back out of the item pose: Forge's half block, then the 0.4 scale and the
        // 45 degree yaw the hand anchor carries. What is left is the anchor itself.
        GL11.glTranslatef(0.5F, 0.5F, 0.5F);
        GL11.glScalef(UNSCALE, UNSCALE, UNSCALE);
        GL11.glRotatef(-45.0F, 0.0F, 1.0F, 0.0F);

        arm(game, player);
        speaker(light);

        GL11.glPopMatrix();
        GL11.glColor4f(1F, 1F, 1F, 1F);
    }

    // ------------------------------------------------------------------

    private void speaker(int light) {
        GL11.glPushMatrix();
        GL11.glTranslatef(SP_X, SP_Y, SP_Z);
        GL11.glRotatef(SP_YAW, 0.0F, 1.0F, 0.0F);
        GL11.glRotatef(SP_ROLL, 0.0F, 0.0F, 1.0F);
        // The lathe is built in the biped's frame, where y counts downward.
        GL11.glScalef(1.0F, -1.0F, 1.0F);
        // That flip reverses winding, and unlike the entity pass culling is on here.
        boolean culled = GL11.glIsEnabled(GL11.GL_CULL_FACE);
        if (culled) GL11.glDisable(GL11.GL_CULL_FACE);

        speaker.draw(light);

        if (culled) GL11.glEnable(GL11.GL_CULL_FACE);
        GL11.glPopMatrix();
    }

    /**
     * Your own arm, rising from below the view.
     *
     * The biped arm grows along +y from its shoulder, and in the biped's frame +y is
     * down. Here it is not flipped, so the arm grows upward out of frame-bottom with
     * the hand at the top -- which is exactly a raised arm, and keeps the winding
     * and the skin the right way round without a mirror.
     */
    private void arm(Minecraft game, AbstractClientPlayer player) {
        Object render = RenderManager.instance.getEntityRenderObject(player);
        if (!(render instanceof RenderPlayer)) return;
        RenderPlayer renderer = (RenderPlayer) render;
        // Third person may not have run yet this session, so the jointed arm may
        // not be installed. Either part draws the same straight arm here.
        SpeakerArm.install(renderer);

        GL11.glPushMatrix();
        GL11.glTranslatef(ARM_X, ARM_Y, ARM_Z);
        GL11.glRotatef(ARM_PITCH, 1.0F, 0.0F, 0.0F);
        GL11.glRotatef(ARM_ROLL, 0.0F, 0.0F, 1.0F);

        game.getTextureManager().bindTexture(player.getLocationSkin());
        GL11.glColor4f(1F, 1F, 1F, 1F);

        // Straight: the joint's carry pose is aimed at a body that is not being
        // drawn, and the angles that read from outside read as a broken elbow from
        // behind your own eyes.
        renderer.modelBipedMain.bipedRightArm.rotateAngleX = 0F;
        renderer.modelBipedMain.bipedRightArm.rotateAngleY = 0F;
        renderer.modelBipedMain.bipedRightArm.rotateAngleZ = 0F;
        renderer.modelBipedMain.bipedRightArm.render(0.0625F);

        GL11.glPopMatrix();
    }
}
