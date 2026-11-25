package com.questforge.content.debug;

import java.io.File;
import java.util.ArrayList;
import java.util.List;

import net.minecraft.client.Minecraft;
import net.minecraft.item.Item;
import net.minecraft.item.ItemStack;
import net.minecraft.util.ScreenShotHelper;
import net.minecraft.util.Vec3;
import cpw.mods.fml.common.eventhandler.SubscribeEvent;
import cpw.mods.fml.common.gameevent.TickEvent;
import cpw.mods.fml.relauncher.Side;
import cpw.mods.fml.relauncher.SideOnly;

/**
 * Loads a world, places a list of items the way a player would, screenshots
 * the result and stays up -- so a renderer or a memory patch can be checked on
 * real placed blocks without anyone at the keyboard.
 *
 * Inert unless -Dqf.autoplace=<world folder> is given. AutoShot is the tool for
 * one of this mod's own blocks; this one takes any mod's items by registry
 * name, because the first use was Decocraft props (win #8 of the performance
 * plan: the lazy model patch had to be seen rendering props of every tile type
 * on first sight) and nothing in AutoShot could put a prop in the world.
 *
 * Everything that changes the world goes through the client's normal paths --
 * chat commands for teleports and difficulty, the creative inventory packet for
 * the held stack, PlayerControllerMP.onPlayerRightClick for the placement -- so
 * the integrated server does its part on its own thread. A probe that wrote
 * into the server world from the client thread once produced
 * ConcurrentModificationExceptions no real server ever sees.
 *
 *   -Dqf.autoplace=<folder under saves/>   the world; the run is inert without it
 *   -Dqf.autoplace.wait=60      ticks to sit on the title screen first (a heap
 *                               probe of the title screen needs about 600)
 *   -Dqf.autoplace.items=modid:name[:meta],...   what to place, in order
 *   -Dqf.autoplace.cols=6       items per row (rows run away from the camera)
 *   -Dqf.autoplace.spacing=3    blocks between items in a row
 *   -Dqf.autoplace.delay=200    ticks to let the scene settle before the shot
 *   -Dqf.autoplace.name=<tag>   screenshots/<tag>.png
 *   -Dqf.autoplace.quit=1       leave after the shot (default: stay up, so a
 *                               heap probe can attach -- trial.py heap)
 *
 * The player name is whatever the launch gave (trial.py: Dev); /tp needs it.
 * Items are placed on the top face of the highest block at each spot, facing
 * the same way, 3 blocks in front of the player, who is teleported beside each
 * spot first because the server ignores a placement more than 8 blocks away.
 */
@SideOnly(Side.CLIENT)
public class AutoPlace {

    private static final String WORLD = System.getProperty("qf.autoplace", "");

    private int ticks;
    private boolean launched, peaceful, positioned, shot, done;
    private int next;              // index into items
    private int step;              // 0 = teleport to the spot, 1 = place
    private List<ItemStack> items;
    private int originX, originY, originZ;

    public static boolean enabled() {
        return !WORLD.isEmpty();
    }

    private static String option(String key) {
        String v = System.getProperty(key);
        return v == null || v.trim().isEmpty() ? null : v.trim();
    }

    private static int intOption(String key, int dflt) {
        String v = option(key);
        return v == null ? dflt : Integer.parseInt(v);
    }

    /** modid:name[:meta] -> a stack, or null (logged) when no such item exists. */
    private static ItemStack parse(String spec) {
        String[] p = spec.trim().split(":");
        if (p.length < 2) {
            System.out.println("[AutoPlace] bad item spec (want modid:name[:meta]): " + spec);
            return null;
        }
        Object o = Item.itemRegistry.getObject(p[0] + ":" + p[1]);
        if (!(o instanceof Item)) {
            System.out.println("[AutoPlace] no such item: " + p[0] + ":" + p[1]);
            return null;
        }
        int meta = p.length > 2 ? Integer.parseInt(p[2]) : 0;
        return new ItemStack((Item) o, 1, meta);
    }

    private List<ItemStack> items() {
        if (items == null) {
            items = new ArrayList<ItemStack>();
            String list = option("qf.autoplace.items");
            if (list != null) {
                for (String spec : list.split(",")) {
                    ItemStack s = parse(spec);
                    if (s != null) items.add(s);
                }
            }
            System.out.println("[AutoPlace] " + items.size() + " item(s) to place");
        }
        return items;
    }

    /** Where item i goes, relative to the origin: rows away from the camera, staggered. */
    private int[] spot(int i) {
        int cols = Math.max(1, intOption("qf.autoplace.cols", 6));
        int spacing = Math.max(1, intOption("qf.autoplace.spacing", 3));
        int row = i / cols, col = i % cols;
        int x = originX - (cols - 1) * spacing / 2 + col * spacing + (row % 2 == 1 ? spacing / 2 : 0);
        int z = originZ + 8 + row * 4;
        return new int[] {x, z};
    }

    private static void chat(Minecraft mc, String command) {
        mc.thePlayer.sendChatMessage(command);
    }

    @SubscribeEvent
    @SideOnly(Side.CLIENT)
    public void onTick(TickEvent.ClientTickEvent event) {
        if (event.phase != TickEvent.Phase.END || done) {
            return;
        }
        Minecraft mc = Minecraft.getMinecraft();
        ticks++;

        if (!launched) {
            if (ticks > intOption("qf.autoplace.wait", 60) && mc.theWorld == null) {
                System.out.println("[AutoPlace] loading world: " + WORLD);
                mc.launchIntegratedServer(WORLD, WORLD, null);
                launched = true;
                ticks = 0;
            }
            return;
        }
        if (mc.theWorld == null || mc.thePlayer == null) {
            return;
        }

        // The world's own settings may be anything; a dead player places nothing.
        if (!peaceful) {
            if (ticks < 20) return;
            peaceful = true;
            chat(mc, "/difficulty 0");
            chat(mc, "/gamemode 1");
            ticks = 0;
            return;
        }

        // Stand at the origin facing +Z (yaw 0): every spot is in front of here.
        if (!positioned) {
            if (ticks < 20) return;
            positioned = true;
            originX = (int) Math.floor(mc.thePlayer.posX);
            originZ = (int) Math.floor(mc.thePlayer.posZ);
            originY = mc.theWorld.getHeightValue(originX, originZ);
            mc.thePlayer.rotationYaw = 0f;
            mc.thePlayer.rotationPitch = 8f;
            chat(mc, "/tp " + mc.thePlayer.getCommandSenderName() + " " + (originX + 0.5) + " " + originY + " " + (originZ + 0.5));
            System.out.println("[AutoPlace] origin " + originX + " " + originY + " " + originZ);
            ticks = 0;
            return;
        }

        List<ItemStack> list = items();
        if (next < list.size()) {
            if (ticks < 10) return;
            ItemStack stack = list.get(next);
            int[] s = spot(next);
            int x = s[0], z = s[1];
            if (step == 0) {
                // Beside the spot, looking the same way as from the origin.
                mc.thePlayer.rotationYaw = 0f;
                mc.thePlayer.rotationPitch = 30f;
                chat(mc, "/tp " + mc.thePlayer.getCommandSenderName() + " " + (x + 0.5) + " " + originY + " " + (z - 3 + 0.5));
                step = 1;
            } else {
                int top = mc.theWorld.getHeightValue(x, z);   // first air block above the ground
                int y = top - 1;                              // the ground block, clicked on its top face
                mc.thePlayer.inventory.mainInventory[0] = stack.copy();
                mc.thePlayer.inventory.currentItem = 0;
                mc.playerController.sendSlotPacket(stack.copy(), 36);   // creative: the server's hotbar slot 0
                boolean ok = mc.playerController.onPlayerRightClick(mc.thePlayer, mc.theWorld, stack.copy(),
                        x, y, z, 1, Vec3.createVectorHelper(x + 0.5, y + 1, z + 0.5));
                System.out.println("[AutoPlace] placed " + stack.getDisplayName() + " (" + stack.getItem().getUnlocalizedName()
                        + " meta " + stack.getItemDamage() + ") at " + x + " " + (y + 1) + " " + z + ": " + (ok ? "ok" : "REFUSED"));
                step = 0;
                next++;
            }
            ticks = 0;
            return;
        }

        if (!shot) {
            // Back to the origin for the shot, then let chunks, VBOs and lighting settle.
            if (next > 0 && step == 0 && ticks == 1) {
                mc.thePlayer.rotationYaw = 0f;
                mc.thePlayer.rotationPitch = 8f;
                chat(mc, "/tp " + mc.thePlayer.getCommandSenderName() + " " + (originX + 0.5) + " " + originY + " " + (originZ + 0.5));
                mc.thePlayer.inventory.mainInventory[0] = null;
                mc.playerController.sendSlotPacket(null, 36);
            }
            if (ticks < intOption("qf.autoplace.delay", 200)) return;
            if (mc.currentScreen != null) {
                System.out.println("[AutoPlace] dismissing " + mc.currentScreen.getClass().getSimpleName());
                mc.displayGuiScreen(null);
                ticks = intOption("qf.autoplace.delay", 200) - 20;
                return;
            }
            shot = true;
            System.out.println("[AutoPlace] FPS: " + mc.debug);
            try {
                String tag = System.getProperty("qf.autoplace.name", "autoplace");
                File dir = mc.mcDataDir;
                ScreenShotHelper.saveScreenshot(dir, tag + ".png", mc.displayWidth, mc.displayHeight, mc.getFramebuffer());
                System.out.println("[AutoPlace] wrote screenshots/" + tag + ".png at "
                        + mc.thePlayer.posX + " " + mc.thePlayer.posY + " " + mc.thePlayer.posZ);
            } catch (Throwable t) {
                System.out.println("[AutoPlace] FAILED: " + t);
                t.printStackTrace();
            }
            Runtime rt = Runtime.getRuntime();
            System.out.println("[AutoPlace] heap used " + ((rt.totalMemory() - rt.freeMemory()) >> 20) + " MB of "
                    + (rt.totalMemory() >> 20) + " MB committed (before any GC; probe with jcmd for the live set)");
            if (option("qf.autoplace.quit") != null) {
                System.out.println("[AutoPlace] done; quitting");
                mc.shutdown();
            } else {
                System.out.println("[AutoPlace] done; staying up");
            }
            done = true;
        }
    }
}
