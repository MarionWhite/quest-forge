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
    private boolean peaceful;
    private boolean held;
    private boolean timeSet;
    private boolean orbited;
    private int subjectX, subjectY, subjectZ;

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

    /** The block -Dqf.autoshot.place asked for, or the Tower Speaker. */
    private static net.minecraft.block.Block blockNamed(String name) {
        if ("jukebox".equals(name)) return com.questforge.content.ModBlocks.jukebox;
        if ("record_case".equals(name)) return com.questforge.content.ModBlocks.recordCase;
        return com.questforge.content.ModBlocks.towerSpeaker;
    }

    /**
     * -Dqf.autoshot.clear=<radius> opens the space around the subject.
     *
     * A world is photographed wherever the player last stood, and the first clean
     * daylight shot of the jukebox still had three leaf blocks between the camera
     * and the block. Everything above the floor inside the radius goes, the
     * subject and the ground it stands on excepted; the camera sits well inside
     * it, so this clears the line of sight as well as the backdrop.
     */
    private static void clearAround(net.minecraft.world.WorldServer w,
                                    int x, int y, int z, net.minecraft.block.Block subject) {
        int r = Integer.getInteger("qf.autoshot.clear", 0);
        if (r <= 0) return;
        int cleared = 0;
        for (int dx = -r; dx <= r; dx++) {
            for (int dz = -r; dz <= r; dz++) {
                for (int dy = 0; dy <= r; dy++) {
                    int bx = x + dx, by = y + dy, bz = z + dz;
                    net.minecraft.block.Block b = w.getBlock(bx, by, bz);
                    if (b == subject || b == net.minecraft.init.Blocks.air) continue;
                    w.setBlockToAir(bx, by, bz);
                    cleared++;
                }
            }
        }
        System.out.println("[AutoShot] cleared " + cleared + " blocks within " + r);
    }

    /** Finishes placing a block the way a player's click would. */
    private static void place(net.minecraft.world.WorldServer w,
                              int x, int y, int z, net.minecraft.block.Block block) {
        try {
            java.util.List<?> players = w.playerEntities;
            if (players.isEmpty()) return;
            net.minecraft.entity.EntityLivingBase placer =
                    (net.minecraft.entity.EntityLivingBase) players.get(0);
            block.onBlockPlacedBy(w, x, y, z, placer, new ItemStack(block));
        } catch (Throwable t) {
            System.out.println("[AutoShot] onBlockPlacedBy failed: " + t);
        }
    }

    /**
     * A property that was passed but left empty counts as absent.
     *
     * A launcher that fills its arguments from environment variables writes
     * -Dqf.autoshot.hold= when the variable is unset, and getProperty then returns
     * "" rather than null. Every option here used to treat that as "yes", which is
     * how a capture came back with the player holding a tower speaker nobody had
     * asked for.
     */
    private static String option(String key) {
        String v = System.getProperty(key);
        return v == null || v.trim().isEmpty() ? null : v.trim();
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

        // Peaceful, the moment there is a world to set it on -- before the delay
        // below, not after it. A run stands still for the better part of a minute
        // in whatever difficulty the world was saved at, and a capture that comes
        // back as the death screen has cost a launch and proved nothing: the first
        // cleared shot of the jukebox read "Developer was slain by Zombie".
        if (!peaceful && mc.getIntegratedServer() != null) {
            peaceful = true;
            try {
                mc.getIntegratedServer().func_147139_a(
                        net.minecraft.world.EnumDifficulty.PEACEFUL);
                System.out.println("[AutoShot] difficulty set to peaceful");
            } catch (Throwable t) {
                System.out.println("[AutoShot] peaceful failed: " + t);
            }
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
        // -Dqf.autoshot.place=<block> drops one of the mod's blocks just in front
        // of the player, on the server so it actually exists, to photograph
        // something that needs a block in the world. Anything unrecognised -- the
        // old =1 included -- gets the Tower Speaker this option started out as.
        String place = option("qf.autoshot.place");
        if (place != null && !placed) {
            placed = true;
            try {
                net.minecraft.server.MinecraftServer server = mc.getIntegratedServer();
                if (server != null) {
                    net.minecraft.world.WorldServer w = server.worldServerForDimension(0);
                    double yaw = Math.toRadians(mc.thePlayer.rotationYaw);
                    int bx = (int) Math.floor(mc.thePlayer.posX - Math.sin(yaw) * 2.5D);
                    int bz = (int) Math.floor(mc.thePlayer.posZ + Math.cos(yaw) * 2.5D);
                    int by = (int) Math.floor(mc.thePlayer.posY);
                    net.minecraft.block.Block block = blockNamed(place);
                    w.setBlock(bx, by, bz, block, 0, 3);
                    // The call real placement makes. Without it a block that turns
                    // to face whoever put it down is photographed facing north --
                    // which looks like broken art rather than a shot that skipped
                    // half of placing the block.
                    subjectX = bx; subjectY = by; subjectZ = bz;
                    place(w, bx, by, bz, block);
                    System.out.println("[AutoShot] placed " + block.getUnlocalizedName()
                            + " at " + bx + " " + by + " " + bz
                            + " meta " + w.getBlockMetadata(bx, by, bz));
                    clearAround(w, bx, by, bz, block);

                    // -Dqf.autoshot.extra=<n> puts n more beside it, in a row, so
                    // the cost of a roomful can be measured rather than guessed.
                    String extra = option("qf.autoshot.extra");
                    if (extra != null) {
                        int n = Integer.parseInt(extra.trim());
                        for (int i = 1; i <= n; i++) {
                            int dx = ((i + 1) / 2) * 2 * (i % 2 == 0 ? 1 : -1);
                            w.setBlock(bx + dx, by, bz, block, 0, 3);
                            place(w, bx + dx, by, bz, block);
                        }
                        System.out.println("[AutoShot] placed " + n + " more");
                    }

                    // -Dqf.autoshot.disc=<tier> sets the disc showing behind a
                    // jukebox's glass, so the tiers can be photographed without
                    // a person standing there feeding it records.
                    String tier = option("qf.autoshot.disc");
                    if (tier != null) {
                        net.minecraft.tileentity.TileEntity te =
                                w.getTileEntity(bx, by, bz);
                        if (te instanceof com.questforge.content.jukebox.TileEntityJukebox) {
                            ((com.questforge.content.jukebox.TileEntityJukebox) te)
                                    .setDisc(Integer.parseInt(tier));
                            System.out.println("[AutoShot] disc tier " + tier);
                        }
                    }
                }
            } catch (Throwable t) {
                System.out.println("[AutoShot] place failed: " + t);
            }
            ticks = 0;
            return;
        }

        // -Dqf.autoshot.hold=<block> puts that block in the hotbar and selects it,
        // without placing anything. It exists to photograph what a mod draws while
        // you are *about* to place something -- the placement ghost has no other
        // way of appearing in an unattended capture, because it is a function of
        // what is in your hand and where you are looking.
        String hold = option("qf.autoshot.hold");
        if (hold != null && !held) {
            held = true;
            try {
                ItemStack stack = new ItemStack(blockNamed(hold));
                net.minecraft.server.MinecraftServer server = mc.getIntegratedServer();
                if (server != null) {
                    java.util.List<?> players =
                            server.getConfigurationManager().playerEntityList;
                    for (Object o : players) {
                        net.minecraft.entity.player.EntityPlayerMP mp =
                                (net.minecraft.entity.player.EntityPlayerMP) o;
                        mp.inventory.mainInventory[0] = stack.copy();
                        mp.inventory.currentItem = 0;
                        mp.inventory.markDirty();
                    }
                }
                mc.thePlayer.inventory.mainInventory[0] = stack.copy();
                mc.thePlayer.inventory.currentItem = 0;
                System.out.println("[AutoShot] holding " + stack.getDisplayName());
            } catch (Throwable t) {
                System.out.println("[AutoShot] hold failed: " + t);
            }
            ticks = 0;
            return;
        }

        // -Dqf.autoshot.orbit=<degrees> walks the camera round the block it just
        // placed and turns it to look back. A block that faces whoever places it
        // is otherwise photographed head-on every single time, which is exactly
        // the angle at which a flat surface pretending to be round still looks
        // round -- so the one view that would catch the cheat never got taken.
        String orbit = option("qf.autoshot.orbit");
        if (orbit != null && !orbited && placed) {
            orbited = true;
            try {
                double deg = Double.parseDouble(orbit);
                double rad = Math.toRadians(deg);
                // Aim at the middle of a two-block-tall subject, not its foot.
                double cx = subjectX + 0.5, cy = subjectY + 1.0, cz = subjectZ + 0.5;
                double dx = mc.thePlayer.posX - cx, dz = mc.thePlayer.posZ - cz;
                // Far enough back to frame a two-block subject. The placement
                // distance is two and a half blocks, which puts the camera inside
                // the cabinet's own height and crops the top off every shot.
                double dist = Math.sqrt(dx * dx + dz * dz);
                String far = option("qf.autoshot.back");
                dist = far != null ? Double.parseDouble(far) : Math.max(dist, 4.2D);
                double base = Math.atan2(dz, dx);
                double nx = cx + Math.cos(base + rad) * dist;
                double nz = cz + Math.sin(base + rad) * dist;

                // Minecraft's look vector is (-sin(yaw)cos(pitch), -sin(pitch),
                // cos(yaw)cos(pitch)): yaw 0 faces +Z and grows towards -X, and
                // pitch is positive looking DOWN. Writing the angle down the way
                // it reads on paper aims the camera at the floor, which is what
                // the first version of this did.
                double tx = cx - nx, tz = cz - nz;
                float yaw = (float) Math.toDegrees(Math.atan2(-tx, tz));
                // The client player's posY is already eye height in 1.7.10 --
                // adding the eye offset again aimed every orbit shot at the floor.
                double eye = mc.thePlayer.posY;
                float pitch = (float) -Math.toDegrees(Math.atan2(cy - eye, dist));

                mc.thePlayer.setPositionAndRotation(nx, mc.thePlayer.posY, nz,
                                                    yaw, pitch);
                net.minecraft.server.MinecraftServer server = mc.getIntegratedServer();
                if (server != null) {
                    java.util.List<?> players =
                            server.getConfigurationManager().playerEntityList;
                    for (Object o : players) {
                        ((net.minecraft.entity.player.EntityPlayerMP) o)
                                .playerNetServerHandler.setPlayerLocation(
                                        nx, mc.thePlayer.posY, nz, yaw, pitch);
                    }
                }
                System.out.println("[AutoShot] orbited " + deg + " deg to "
                        + nx + " " + nz + " yaw " + yaw + " pitch " + pitch);
            } catch (Throwable t) {
                System.out.println("[AutoShot] orbit failed: " + t);
            }
            ticks = 0;
            return;
        }

        // -Dqf.autoshot.time=<ticks> sets the time of day and stops the weather,
        // 6000 being noon. A world is usually saved wherever somebody left it,
        // and a block photographed at midnight in the rain says nothing about its
        // artwork -- the first shot of this jukebox was four dark red pixels.
        String time = option("qf.autoshot.time");
        if (time != null && !timeSet) {
            timeSet = true;
            try {
                net.minecraft.server.MinecraftServer server = mc.getIntegratedServer();
                if (server != null) {
                    net.minecraft.world.WorldServer w = server.worldServerForDimension(0);
                    w.setWorldTime(Long.parseLong(time.trim()));
                    w.getWorldInfo().setRaining(false);
                    w.getWorldInfo().setThundering(false);
                    System.out.println("[AutoShot] world time set to " + w.getWorldTime());
                }
            } catch (Throwable t) {
                System.out.println("[AutoShot] time failed: " + t);
            }
            // The client learns the time from the next sync packet, so give the
            // same settling delay again rather than capturing into dusk.
            ticks = 0;
            return;
        }

        // -Dqf.autoshot.unequip=1 strips the chest slot instead, to get the
        // control shot: the same world, same position, same shader, armour off.
        if (option("qf.autoshot.unequip") != null
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
        String armor = option("qf.autoshot.armor");
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

        // Anything covering the world goes first. Singleplayer pauses itself the
        // moment the window loses focus, and an unattended run loses focus to
        // whatever else the machine is doing -- so without this the capture is a
        // photograph of the pause menu, which is how one of these runs came back
        // showing "Game menu" instead of the block it was sent to look at. The
        // plate option is the exception: there the GUI is the subject.
        if (option("qf.autoshot.plate") == null && mc.currentScreen != null) {
            System.out.println("[AutoShot] dismissing "
                    + mc.currentScreen.getClass().getSimpleName());
            mc.displayGuiScreen(null);
            ticks = 0;
            return;
        }

        shot = true;
        // The frame rate at the moment of the shot, for measuring a scene.
        System.out.println("[AutoShot] FPS: " + mc.debug);
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
