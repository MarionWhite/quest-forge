package com.questforge.content.jukebox;

import cpw.mods.fml.relauncher.Side;
import cpw.mods.fml.relauncher.SideOnly;

import net.minecraft.client.model.ModelBiped;
import net.minecraft.client.model.ModelRenderer;
import net.minecraft.client.renderer.entity.RenderPlayer;
import net.minecraft.entity.player.EntityPlayer;
import net.minecraft.item.ItemStack;

/**
 * The right arm, with an elbow, raised to carry the JBL.
 *
 * <h3>Why this is a model part and not an event</h3>
 * The pose has to be applied after {@code ModelBiped.setRotationAngles}, which
 * recomputes every arm angle from scratch each frame, and before the arm draws.
 * Forge fires nothing between those two -- {@code RenderPlayerEvent.Pre} lands
 * before the first and {@code Specials} after the second -- so anything written
 * from an event handler is either overwritten or too late. The one seam is
 * {@link ModelRenderer#render}, which is called at draw time and can be
 * overridden. So the arm itself carries the pose.
 *
 * <h3>Why it has an elbow</h3>
 * A vanilla arm is one box on one joint, and that cannot hold this speaker: the
 * shoulder sits inside the barrel's footprint, so every angle that brings the hand
 * onto the speaker drags the forearm straight through it, and every angle that
 * clears the speaker leaves the hand waving in the air beside it. The arm is
 * therefore split at the elbow into the same two halves the skin already draws --
 * upper at texture (40,16), lower at (40,22), six units each -- so that unposed it
 * is pixel-for-pixel the arm it replaced, and posed it can fold.
 *
 * The angles below are not eyeballed. They come from a search over both joints for
 * a pose that lands the hand just off the barrel's skin while keeping the centre
 * line of both segments outside its radius for their whole length, which is the
 * difference between a hand resting on a speaker and a hand buried in one.
 */
@SideOnly(Side.CLIENT)
public class SpeakerArm extends ModelRenderer {

    /** Upper arm: up, forward and out, clearing the barrel on the outboard side. */
    private static final float UPPER_X = -2.356F, UPPER_Z = -0.698F;
    /** Forearm, relative to it: over onto the rubber end shell, forward of the cloth. */
    private static final float FORE_X = -0.436F, FORE_Z = -0.262F;
    /** How much of the walk swing survives, so a carried speaker is not frozen. */
    private static final float LIVELINESS = 0.15F;

    /** Whose arm is being drawn. Set for the length of one player's render. */
    private static EntityPlayer holder;

    private final ModelRenderer forearm;

    private SpeakerArm(ModelBiped owner, float expand) {
        super(owner, 40, 16);
        // The vanilla right arm, cut in half at the elbow: same pivot, same boxes,
        // same corners of the skin.
        addBox(-3.0F, -2.0F, -2.0F, 4, 6, 4, expand);
        setRotationPoint(-5.0F, 2.0F, 0.0F);

        forearm = new ModelRenderer(owner, 40, 22);
        forearm.addBox(-3.0F, 0.0F, -2.0F, 4, 6, 4, expand);
        forearm.setRotationPoint(0.0F, 4.0F, 0.0F);
        addChild(forearm);
    }

    // ------------------------------------------------------------------
    // Installing
    // ------------------------------------------------------------------

    /**
     * Puts the jointed arm on the renderer's three biped models, so armour follows
     * the skin instead of leaving a straight steel sleeve beside a bent arm.
     */
    public static void install(RenderPlayer renderer) {
        if (renderer == null) return;
        swap(renderer.modelBipedMain, 0.0F);
        swap(renderer.modelArmorChestplate, 1.0F);
        swap(renderer.modelArmor, 0.5F);
    }

    private static void swap(ModelBiped model, float expand) {
        if (model == null || model.bipedRightArm instanceof SpeakerArm) return;
        // The replaced part would otherwise linger in boxList, where anything
        // walking the model's parts would still find it.
        model.boxList.remove(model.bipedRightArm);
        model.bipedRightArm = new SpeakerArm(model, expand);
    }

    /** Called either side of a player's render, so the pose cannot leak. */
    public static void carrying(EntityPlayer player) { holder = player; }

    // ------------------------------------------------------------------
    // Posing
    // ------------------------------------------------------------------

    private void pose() {
        boolean carry = false;
        if (holder != null) {
            ItemStack held = holder.getHeldItem();
            carry = held != null && held.getItem() instanceof ItemSpeaker;
        }

        if (!carry) {
            // Straight again, and indistinguishable from the part this replaced.
            forearm.rotateAngleX = forearm.rotateAngleY = forearm.rotateAngleZ = 0.0F;
            return;
        }

        rotateAngleX = UPPER_X + rotateAngleX * LIVELINESS;
        rotateAngleY = 0.0F;
        rotateAngleZ = UPPER_Z;

        forearm.rotateAngleX = FORE_X;
        forearm.rotateAngleY = 0.0F;
        forearm.rotateAngleZ = FORE_Z;
    }

    @Override
    public void render(float scale) {
        pose();
        super.render(scale);
    }

    @Override
    public void postRender(float scale) {
        pose();
        super.postRender(scale);
    }
}
