package com.questforge.content.client;

import org.lwjgl.opengl.GL11;

import net.minecraft.block.Block;
import net.minecraft.client.Minecraft;
import net.minecraft.entity.Entity;
import net.minecraft.item.ItemBlock;
import net.minecraft.item.ItemStack;
import net.minecraft.util.MovingObjectPosition;

import cpw.mods.fml.relauncher.Side;
import cpw.mods.fml.relauncher.SideOnly;

/**
 * Shows where a two-block-tall block is about to land, before you place it.
 *
 * A jukebox is a piece of furniture you line up against a wall, and the vanilla
 * hit box tells you about the block you are pointing at, not the one you are
 * about to create. Worse, it is two blocks tall: half of what you place is
 * somewhere you were never shown. This draws that footprint -- both halves --
 * where it would actually go, and colours it by whether it would go there at all.
 *
 * Entirely client-side and entirely read-only: it raytraces the same way the
 * placement itself will and asks the block the same question, so what it draws is
 * the answer you are about to get rather than a guess at it.
 */
@SideOnly(Side.CLIENT)
public final class PlacementGhost {

    /** Off the surface, so the lines do not fight the block face they sit on. */
    private static final double PAD = 0.0035D;

    /** How tall a footprint to outline, per block that declares one. */
    private static final double JUKEBOX_HEIGHT = 2.0D;

    private PlacementGhost() { }

    public static void render(float partialTicks) {
        Minecraft mc = Minecraft.getMinecraft();
        if (mc == null || mc.theWorld == null || mc.thePlayer == null) return;

        ItemStack held = mc.thePlayer.getHeldItem();
        if (held == null || !(held.getItem() instanceof ItemBlock)) return;

        Block block = ((ItemBlock) held.getItem()).field_150939_a;
        if (block != com.questforge.content.ModBlocks.jukebox) return;

        MovingObjectPosition hit = mc.objectMouseOver;
        if (hit == null
                || hit.typeOfHit != MovingObjectPosition.MovingObjectType.BLOCK) {
            return;
        }

        // Where the block would go: one step off the face that was hit, unless
        // what was hit is something a placement replaces, like tall grass.
        int x = hit.blockX, y = hit.blockY, z = hit.blockZ;
        Block at = mc.theWorld.getBlock(x, y, z);
        if (!at.isReplaceable(mc.theWorld, x, y, z)) {
            switch (hit.sideHit) {
                case 0: y--; break;
                case 1: y++; break;
                case 2: z--; break;
                case 3: z++; break;
                case 4: x--; break;
                case 5: x++; break;
                default: return;
            }
        }

        // The same question the placement will ask, so the colour never lies.
        boolean ok = block.canPlaceBlockAt(mc.theWorld, x, y, z)
                && mc.theWorld.getBlock(x, y, z).isReplaceable(mc.theWorld, x, y, z);

        Entity view = mc.renderViewEntity;
        double camX = view.lastTickPosX + (view.posX - view.lastTickPosX) * partialTicks;
        double camY = view.lastTickPosY + (view.posY - view.lastTickPosY) * partialTicks;
        double camZ = view.lastTickPosZ + (view.posZ - view.lastTickPosZ) * partialTicks;

        double x0 = x - camX - PAD, x1 = x + 1 - camX + PAD;
        double y0 = y - camY - PAD, y1 = y + JUKEBOX_HEIGHT - camY + PAD;
        double z0 = z - camZ - PAD, z1 = z + 1 - camZ + PAD;

        GL11.glPushMatrix();
        GL11.glDisable(GL11.GL_TEXTURE_2D);
        GL11.glDisable(GL11.GL_LIGHTING);
        GL11.glEnable(GL11.GL_BLEND);
        GL11.glBlendFunc(GL11.GL_SRC_ALPHA, GL11.GL_ONE_MINUS_SRC_ALPHA);
        GL11.glDepthMask(false);

        // The outline reads through the world, so a footprint that runs into a
        // hillside is still legible where it is buried -- that is exactly the
        // case you want to see before you place.
        GL11.glDisable(GL11.GL_DEPTH_TEST);
        GL11.glLineWidth(2.0F);
        if (ok) GL11.glColor4f(0.55F, 0.95F, 1.0F, 0.85F);
        else GL11.glColor4f(1.0F, 0.35F, 0.32F, 0.85F);
        wire(x0, y0, z0, x1, y1, z1);

        // A wash inside it, faint enough to be an impression of volume rather
        // than a solid block hanging in the air.
        GL11.glEnable(GL11.GL_DEPTH_TEST);
        if (ok) GL11.glColor4f(0.55F, 0.95F, 1.0F, 0.10F);
        else GL11.glColor4f(1.0F, 0.35F, 0.32F, 0.12F);
        faces(x0, y0, z0, x1, y1, z1);

        // The seam between the two halves, so the footprint reads as two blocks.
        GL11.glDisable(GL11.GL_DEPTH_TEST);
        GL11.glLineWidth(1.0F);
        GL11.glColor4f(1F, 1F, 1F, 0.22F);
        double mid = y0 + (y1 - y0) * 0.5D;
        GL11.glBegin(GL11.GL_LINE_LOOP);
        GL11.glVertex3d(x0, mid, z0);
        GL11.glVertex3d(x1, mid, z0);
        GL11.glVertex3d(x1, mid, z1);
        GL11.glVertex3d(x0, mid, z1);
        GL11.glEnd();

        GL11.glLineWidth(1.0F);
        GL11.glDepthMask(true);
        GL11.glEnable(GL11.GL_DEPTH_TEST);
        GL11.glDisable(GL11.GL_BLEND);
        GL11.glEnable(GL11.GL_TEXTURE_2D);
        GL11.glColor4f(1F, 1F, 1F, 1F);
        GL11.glPopMatrix();
    }

    private static void wire(double x0, double y0, double z0,
                             double x1, double y1, double z1) {
        GL11.glBegin(GL11.GL_LINES);
        for (int i = 0; i < 2; i++) {
            double yy = i == 0 ? y0 : y1;
            edge(x0, yy, z0, x1, yy, z0);
            edge(x1, yy, z0, x1, yy, z1);
            edge(x1, yy, z1, x0, yy, z1);
            edge(x0, yy, z1, x0, yy, z0);
        }
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

    private static void faces(double x0, double y0, double z0,
                              double x1, double y1, double z1) {
        GL11.glBegin(GL11.GL_QUADS);
        // bottom, top
        quad(x0, y0, z0, x1, y0, z0, x1, y0, z1, x0, y0, z1);
        quad(x0, y1, z1, x1, y1, z1, x1, y1, z0, x0, y1, z0);
        // sides
        quad(x0, y0, z0, x0, y1, z0, x1, y1, z0, x1, y0, z0);
        quad(x1, y0, z1, x1, y1, z1, x0, y1, z1, x0, y0, z1);
        quad(x0, y0, z1, x0, y1, z1, x0, y1, z0, x0, y0, z0);
        quad(x1, y0, z0, x1, y1, z0, x1, y1, z1, x1, y0, z1);
        GL11.glEnd();
    }

    private static void quad(double ax, double ay, double az, double bx, double by,
                             double bz, double cx, double cy, double cz,
                             double dx, double dy, double dz) {
        GL11.glVertex3d(ax, ay, az);
        GL11.glVertex3d(bx, by, bz);
        GL11.glVertex3d(cx, cy, cz);
        GL11.glVertex3d(dx, dy, dz);
    }
}
