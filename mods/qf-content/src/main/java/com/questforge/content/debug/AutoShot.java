package com.questforge.content.debug;

import java.io.File;

import net.minecraft.client.Minecraft;
import net.minecraft.item.Item;
import net.minecraft.item.ItemArmor;
import net.minecraft.item.ItemStack;
import net.minecraft.util.ScreenShotHelper;
import cpw.mods.fml.common.gameevent.TickEvent;
import cpw.mods.fml.common.eventhandler.SubscribeEvent;
import cpw.mods.fml.relauncher.Side;
import cpw.mods.fml.relauncher.SideOnly;

/**
 * Loads a world, screenshots it, and quits -- so a render bug can be measured
 * instead of described.
 *
 * Entirely inert unless -Dqf.autoshot=<world folder> is on the command line, so
 * it costs a normal launch one string lookup per tick and nothing else.
 *
 * Why this exists: the record case renders correctly under one shader pack and
 * black under another, and every round of "change something, ask, wait" spent a
 * person's attention to answer a question a screenshot answers exactly. This
 * turns that loop into something that runs unattended.
 *
 * -Dqf.autoshot.name=<tag> names the file, so one run per diagnostic can be told
 * from another. -Dqf.autoshot.delay=<ticks> waits longer before capturing if the
 * chunks around the subject have not finished drawing.
 */
@SideOnly(Side.CLIENT)
public class AutoShot {

    private static final String WORLD = System.getProperty("qf.autoshot", "");

    private int ticks;
    private boolean launched;
    private boolean shot;
    private boolean equipped;
    private boolean placed;

    /**
     * Matches a class or any of its superclasses by simple name.
     *
     * ItemTransformerArmor is abstract -- every real chestplate is a subclass with
     * its own name -- so matching getClass().getName() alone silently found
     * nothing, and a run that looked like a verification was actually wearing
     * whatever the previous run had left on.
     */
    /** Puts a stack in the integrated server player's chest slot, so it sticks. */
    private static void equipServerSide(Minecraft mc, ItemStack stack) {
        try {
            net.minecraft.server.MinecraftServer server = mc.getIntegratedServer();
            if (server == null) {
                return;
            }
            java.util.List<?> players = server.getConfigurationManager().playerEntityList;
            for (Object o : players) {
                net.minecraft.entity.player.EntityPlayerMP mp =
                        (net.minecraft.entity.player.EntityPlayerMP) o;
                mp.inventory.armorInventory[2] = stack == null ? null : stack.copy();
                mp.inventory.markDirty();
            }
        } catch (Throwable t) {
            System.out.println("[AutoShot] server-side equip failed: " + t);
        }
    }

    private static boolean matches(Class<?> c, String needle) {
        for (Class<?> k = c; k != null; k = k.getSuperclass()) {
            if (k.getName().contains(needle)) {
                return true;
            }
        }
        return false;
    }

    public static boolean enabled() {
        return !WORLD.isEmpty();
    }

    @SubscribeEvent
    @SideOnly(Side.CLIENT)
    public void onTick(TickEvent.ClientTickEvent event) {
        if (event.phase != TickEvent.Phase.END || shot) {
            return;
        }
        Minecraft mc = Minecraft.getMinecraft();
        ticks++;

        // Give the title screen a moment to finish building before loading a world
        // out from under it.
        if (!launched) {
            if (ticks > 60 && mc.theWorld == null) {
                System.out.println("[AutoShot] loading world: " + WORLD);
                mc.launchIntegratedServer(WORLD, WORLD, null);
                launched = true;
                ticks = 0;
            }
            return;
        }

        // The world is up, but terrain, the shader's framebuffers and the tile
        // entity renderers all need frames to settle. Capturing too early gets a
        // grey void and proves nothing.
        int delay = Integer.getInteger("qf.autoshot.delay", 200);
        if (mc.theWorld == null || mc.thePlayer == null || ticks < delay) {
            return;
        }

        // -Dqf.autoshot.armor=<substring> puts the first chestplate whose class
        // name contains that substring into the chest slot before capturing, so a
        // bug that only appears while wearing armour can be photographed without a
        // person standing there to equip it.
        // -Dqf.autoshot.place=1 drops a Tower Speaker just in front of the player,
        // on the server so it actually exists, to photograph a renderer that needs
        // a block in the world.
        if (System.getProperty("qf.autoshot.place") != null && !placed) {
            placed = true;
            try {
                net.minecraft.server.MinecraftServer server = mc.getIntegratedServer();
                if (server != null) {
                    net.minecraft.world.WorldServer w = server.worldServerForDimension(0);
                    double yaw = Math.toRadians(mc.thePlayer.rotationYaw);
                    int bx = (int) Math.floor(mc.thePlayer.posX - Math.sin(yaw) * 2.5D);
                    int bz = (int) Math.floor(mc.thePlayer.posZ + Math.cos(yaw) * 2.5D);
                    int by = (int) Math.floor(mc.thePlayer.posY);
                    w.setBlock(bx, by, bz, com.questforge.content.ModBlocks.towerSpeaker, 0, 3);
                    System.out.println("[AutoShot] placed towerSpeaker at "
                            + bx + " " + by + " " + bz);
                }
            } catch (Throwable t) {
                System.out.println("[AutoShot] place failed: " + t);
            }
            ticks = 0;
            return;
        }

        // -Dqf.autoshot.unequip=1 strips the chest slot instead, to get the
        // control shot: the same world, same position, same shader, armour off.
        if (System.getProperty("qf.autoshot.unequip") != null
                && mc.thePlayer.inventory.armorInventory[2] != null) {
            System.out.println("[AutoShot] unequipped "
                    + mc.thePlayer.inventory.armorInventory[2].getItem().getClass().getName());
            equipServerSide(mc, null);
            mc.thePlayer.inventory.armorInventory[2] = null;
            ticks = 0;
            return;
        }

        // Force-replaces whatever is worn, so a vanilla chestplate can be swapped
        // in as a control against the mod's own.
        String armor = System.getProperty("qf.autoshot.armor");
        if (armor != null && !equipped) {
            for (Object o : Item.itemRegistry) {
                if (!(o instanceof ItemArmor)) {
                    continue;
                }
                ItemArmor ia = (ItemArmor) o;
                if (ia.armorType == 1 && matches(ia.getClass(), armor)) {
                    // Set it on the SERVER's player, not just the client's. The
                    // integrated server owns the inventory and syncs it back, so a
                    // client-only assignment is silently undone within a tick --
                    // which is exactly how a run reported an empty chest slot after
                    // claiming to have equipped something.
                    equipServerSide(mc, new ItemStack(ia));
                    mc.thePlayer.inventory.armorInventory[2] = new ItemStack(ia);
                    System.out.println("[AutoShot] equipped " + ia.getClass().getName()
                            + " (" + ia.getUnlocalizedName() + ")");
                    equipped = true;
                    ticks = 0;   // let a few frames render with it on
                    return;
                }
            }
            System.out.println("[AutoShot] no chestplate matching: " + armor);
            equipped = true;
        }

        shot = true;
        try {
            String tag = System.getProperty("qf.autoshot.name", "autoshot");
            File dir = mc.mcDataDir;
            ScreenShotHelper.saveScreenshot(dir, tag + ".png",
                    mc.displayWidth, mc.displayHeight, mc.getFramebuffer());
            // State the capture, do not infer it. A hotbar icon is not worn armour,
            // and reading one for the other invalidated a verification run.
            ItemStack chest = mc.thePlayer.inventory.armorInventory[2];
            String worn = chest == null ? "NOTHING"
                    : chest.getItem().getClass().getName() + " (" + chest.getDisplayName() + ")";
            System.out.println("[AutoShot] CHEST SLOT: " + worn);
            System.out.println("[AutoShot] wrote screenshots/" + tag + ".png at "
                    + mc.thePlayer.posX + " " + mc.thePlayer.posY + " " + mc.thePlayer.posZ);
        } catch (Throwable t) {
            System.out.println("[AutoShot] FAILED: " + t);
            t.printStackTrace();
        }

        // Leave, so a run is one command that terminates rather than a window
        // someone has to close.
        mc.shutdown();
    }
}
