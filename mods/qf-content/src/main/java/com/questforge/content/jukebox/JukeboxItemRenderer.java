package com.questforge.content.jukebox;

import cpw.mods.fml.relauncher.Side;
import cpw.mods.fml.relauncher.SideOnly;

import net.minecraft.client.Minecraft;
import net.minecraft.client.renderer.Tessellator;
import net.minecraft.item.ItemStack;
import net.minecraft.util.ResourceLocation;
import net.minecraftforge.client.IItemRenderer;

import org.lwjgl.opengl.GL11;

/**
 * The jukebox as an item: in the creative tab, on the ground, and in your hand.
 *
 * The block's render type is -1, which means nothing draws it but its tile entity
 * renderer -- and an item has no tile entity, so without this the thing you carry
 * would be a flat sprite of a block that is anything but flat. Drawing the real
 * model is also what makes the creative tab honest about what you are about to
 * place: two blocks of cabinet, not one.
 *
 * The model is 1 x 2 x 1, so every case here is the same two decisions -- shrink
 * it to fit whatever space this render type gets, and stand it on the floor of
 * that space rather than in the middle of it.
 *
 * Except in a slot. There the cabinet would be 48 pixels tall, and its braid
 * and analyser shimmer at that size, so the slot shows a picture of the model
 * instead: rendered once at 1024 pixels by the debug IconBake and filtered
 * down, which keeps every detail the model has and none of the crawl.
 */
@SideOnly(Side.CLIENT)
public class JukeboxItemRenderer implements IItemRenderer {

    private static final ResourceLocation ICON =
            new ResourceLocation("qfcontent", "textures/items/jukebox_icon.png");

    @Override
    public boolean handleRenderType(ItemStack item, ItemRenderType type) {
        return type == ItemRenderType.INVENTORY
                || type == ItemRenderType.ENTITY
                || type == ItemRenderType.EQUIPPED
                || type == ItemRenderType.EQUIPPED_FIRST_PERSON;
    }

    @Override
    public boolean shouldUseRenderHelper(ItemRenderType type, ItemStack item,
                                         ItemRendererHelper helper) {
        // BLOCK_3D puts the inventory slot into the isometric block pose, which is
        // the one the rest of the tab is drawn in; the two ENTITY helpers give a
        // dropped stack its spin and bob.
        if (type == ItemRenderType.INVENTORY) return false;
        return helper == ItemRendererHelper.ENTITY_ROTATION
                || helper == ItemRendererHelper.ENTITY_BOBBING
                || helper == ItemRendererHelper.EQUIPPED_BLOCK;
    }

    @Override
    public void renderItem(ItemRenderType type, ItemStack item, Object... data) {
        if (type == ItemRenderType.INVENTORY) {
            icon();
            return;
        }
        GL11.glPushMatrix();

        switch (type) {

            case ENTITY:
                // A dropped stack is drawn about its own centre.
                GL11.glScalef(0.44F, 0.44F, 0.44F);
                GL11.glTranslatef(-0.5F, -0.9F, -0.5F);
                break;

            case EQUIPPED:
            case EQUIPPED_FIRST_PERSON:
                GL11.glScalef(0.42F, 0.42F, 0.42F);
                GL11.glTranslatef(0.4F, 0F, 0.4F);
                GL11.glRotatef(20F, 0F, 1F, 0F);
                break;

            default:
                break;
        }

        // Lit as though it were standing in daylight: an item is not in the world,
        // so there is no block here whose light level would mean anything.
        RenderJukebox.draw(JukeboxModel.LIT, RenderJukebox.phase(), 0F, 0);

        GL11.glPopMatrix();
    }

    /** The baked picture, over the 16 x 16 slot. */
    private static void icon() {
        Minecraft.getMinecraft().getTextureManager().bindTexture(ICON);
        // Filtered, not nearest: the sheet is larger than the slot, and nearest
        // sampling would throw away most of what the bake was for.
        GL11.glTexParameteri(GL11.GL_TEXTURE_2D, GL11.GL_TEXTURE_MIN_FILTER, GL11.GL_LINEAR);
        GL11.glTexParameteri(GL11.GL_TEXTURE_2D, GL11.GL_TEXTURE_MAG_FILTER, GL11.GL_LINEAR);
        boolean lit = GL11.glIsEnabled(GL11.GL_LIGHTING);
        GL11.glDisable(GL11.GL_LIGHTING);
        GL11.glEnable(GL11.GL_BLEND);
        GL11.glBlendFunc(GL11.GL_SRC_ALPHA, GL11.GL_ONE_MINUS_SRC_ALPHA);
        GL11.glColor4f(1F, 1F, 1F, 1F);
        Tessellator t = Tessellator.instance;
        t.startDrawingQuads();
        t.addVertexWithUV(0, 16, 0, 0, 1);
        t.addVertexWithUV(16, 16, 0, 1, 1);
        t.addVertexWithUV(16, 0, 0, 1, 0);
        t.addVertexWithUV(0, 0, 0, 0, 0);
        t.draw();
        GL11.glDisable(GL11.GL_BLEND);
        if (lit) GL11.glEnable(GL11.GL_LIGHTING);
    }
}
