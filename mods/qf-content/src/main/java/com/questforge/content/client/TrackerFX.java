package com.questforge.content.client;

import java.util.List;

import org.lwjgl.opengl.GL11;

import net.minecraft.client.Minecraft;
import net.minecraft.entity.Entity;
import net.minecraft.entity.EntityLiving;
import net.minecraft.entity.EntityLivingBase;
import net.minecraft.entity.monster.IMob;
import net.minecraft.entity.player.EntityPlayer;
import net.minecraft.util.AxisAlignedBB;

import com.questforge.content.ench.QFEnchantments;

import cpw.mods.fml.relauncher.Side;
import cpw.mods.fml.relauncher.SideOnly;

/**
 * Tracker: living things nearby are outlined through walls.
 *
 * 1.7.10 has no glowing effect -- that arrived in 1.9 -- so the outline is drawn
 * by hand as a wireframe box with the depth test off, which is what makes it show
 * through terrain.
 *
 * Entirely client-side. The client already has every entity in its loaded chunks,
 * and it can read its own held item, so nothing needs to cross the network.
 */
@SideOnly(Side.CLIENT)
public class TrackerFX {

    /** Blocks of range per level. */
    private static final double RANGE_PER_LEVEL = 16.0D;

    /** Grown slightly so the outline sits just off the model rather than z-fighting it. */
    private static final double PADDING = 0.06D;

    public static void render(float partialTicks) {
        int level = ClientEnchantUtil.heldLevel(QFEnchantments.tracker);
        if (level <= 0) return;

        Minecraft mc = Minecraft.getMinecraft();
        if (mc == null || mc.theWorld == null || mc.renderViewEntity == null) return;

        Entity view = mc.renderViewEntity;
        double camX = view.lastTickPosX + (view.posX - view.lastTickPosX) * partialTicks;
        double camY = view.lastTickPosY + (view.posY - view.lastTickPosY) * partialTicks;
        double camZ = view.lastTickPosZ + (view.posZ - view.lastTickPosZ) * partialTicks;

        double range = RANGE_PER_LEVEL * level;
        double rangeSq = range * range;

        GL11.glPushMatrix();
        GL11.glDisable(GL11.GL_TEXTURE_2D);
        GL11.glDisable(GL11.GL_DEPTH_TEST);
        GL11.glDisable(GL11.GL_LIGHTING);
        GL11.glEnable(GL11.GL_BLEND);
        GL11.glBlendFunc(GL11.GL_SRC_ALPHA, GL11.GL_ONE_MINUS_SRC_ALPHA);
        GL11.glDepthMask(false);
        GL11.glLineWidth(1.6F);

        @SuppressWarnings("unchecked")
        List<Entity> entities = mc.theWorld.loadedEntityList;

        for (int i = 0; i < entities.size(); i++) {
            Entity entity = entities.get(i);
            if (!(entity instanceof EntityLivingBase) || entity == mc.thePlayer) continue;

            double dx = entity.posX - camX;
            double dy = entity.posY - camY;
            double dz = entity.posZ - camZ;
            if (dx * dx + dy * dy + dz * dz > rangeSq) continue;

            // Interpolate the box too, or fast-moving mobs trail their outline.
            double ex = entity.lastTickPosX + (entity.posX - entity.lastTickPosX) * partialTicks;
            double ey = entity.lastTickPosY + (entity.posY - entity.lastTickPosY) * partialTicks;
            double ez = entity.lastTickPosZ + (entity.posZ - entity.lastTickPosZ) * partialTicks;

            AxisAlignedBB box = entity.boundingBox;
            double w = (box.maxX - box.minX) / 2.0D + PADDING;
            double h = (box.maxY - box.minY);
            double yOffset = box.minY - entity.posY;

            colourFor(entity);
            drawBox(ex - camX - w, ey - camY + yOffset - PADDING, ez - camZ - w,
                    ex - camX + w, ey - camY + yOffset + h + PADDING, ez - camZ + w);
        }

        GL11.glLineWidth(1.0F);
        GL11.glDepthMask(true);
        GL11.glDisable(GL11.GL_BLEND);
        GL11.glEnable(GL11.GL_DEPTH_TEST);
        GL11.glEnable(GL11.GL_TEXTURE_2D);
        GL11.glColor4f(1.0F, 1.0F, 1.0F, 1.0F);
        GL11.glPopMatrix();
    }

    /** Red for anything that wants to kill you, blue for people, green for the rest. */
    private static void colourFor(Entity entity) {
        if (entity instanceof EntityPlayer) {
            GL11.glColor4f(0.45F, 0.70F, 1.0F, 0.85F);
        } else if (entity instanceof IMob) {
            GL11.glColor4f(1.0F, 0.30F, 0.30F, 0.80F);
        } else if (entity instanceof EntityLiving) {
            GL11.glColor4f(0.45F, 1.0F, 0.55F, 0.65F);
        } else {
            GL11.glColor4f(1.0F, 1.0F, 1.0F, 0.60F);
        }
    }

    private static void drawBox(double x0, double y0, double z0,
                                double x1, double y1, double z1) {
        GL11.glBegin(GL11.GL_LINES);
        // bottom
        edge(x0, y0, z0, x1, y0, z0);
        edge(x1, y0, z0, x1, y0, z1);
        edge(x1, y0, z1, x0, y0, z1);
        edge(x0, y0, z1, x0, y0, z0);
        // top
        edge(x0, y1, z0, x1, y1, z0);
        edge(x1, y1, z0, x1, y1, z1);
        edge(x1, y1, z1, x0, y1, z1);
        edge(x0, y1, z1, x0, y1, z0);
        // uprights
        edge(x0, y0, z0, x0, y1, z0);
        edge(x1, y0, z0, x1, y1, z0);
        edge(x1, y0, z1, x1, y1, z1);
        edge(x0, y0, z1, x0, y1, z1);
        GL11.glEnd();
    }

    private static void edge(double x0, double y0, double z0,
                             double x1, double y1, double z1) {
        GL11.glVertex3d(x0, y0, z0);
        GL11.glVertex3d(x1, y1, z1);
    }
}
