package com.questforge.content.client;

import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

import org.lwjgl.opengl.GL11;

import net.minecraft.block.Block;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.FontRenderer;
import net.minecraft.init.Blocks;
import net.minecraft.item.Item;
import net.minecraft.item.ItemStack;
import net.minecraft.util.EnumChatFormatting;
import net.minecraft.world.World;
import net.minecraftforge.oredict.OreDictionary;

import com.questforge.content.ench.QFEnchantments;

import cpw.mods.fml.relauncher.Side;
import cpw.mods.fml.relauncher.SideOnly;

/**
 * Prospector: a quiet readout of what is worth digging for nearby.
 *
 * The scan is client-side. A client has the block data for every chunk it has
 * loaded, so asking the server would be a packet round trip for information the
 * client is already holding.
 *
 * "Ore" is decided by the ore dictionary rather than a hardcoded list, which is
 * the only approach that works in a 113-mod pack -- every modded ore that
 * registers itself properly is found for free, and the result is cached per
 * block+metadata so the dictionary lookup happens once per ore type, not once per
 * block scanned.
 */
@SideOnly(Side.CLIENT)
public class ProspectorHUD {

    /** Two seconds between sweeps: often enough to feel live, rare enough to be free. */
    private static final int SCAN_INTERVAL = 40;

    private static final int VERTICAL_RANGE = 8;
    private static final int MAX_LINES = 6;

    private static final List<String> LINES = new ArrayList<String>();
    private static final Map<Integer, String> ORE_NAME_CACHE = new HashMap<Integer, String>();

    /** Blocks that make up most of the world and are definitely not ore. */
    private static final Set<Block> IGNORED = new HashSet<Block>();
    static {
        Collections.addAll(IGNORED,
                Blocks.air, Blocks.stone, Blocks.dirt, Blocks.grass, Blocks.gravel,
                Blocks.sand, Blocks.sandstone, Blocks.bedrock, Blocks.water,
                Blocks.flowing_water, Blocks.lava, Blocks.flowing_lava, Blocks.netherrack,
                Blocks.end_stone, Blocks.cobblestone, Blocks.leaves, Blocks.leaves2,
                Blocks.log, Blocks.log2, Blocks.tallgrass, Blocks.snow, Blocks.ice);
    }

    private static int cooldown;

    public static void tick() {
        if (--cooldown > 0) return;
        cooldown = SCAN_INTERVAL;

        int level = ClientEnchantUtil.heldLevel(QFEnchantments.prospector);
        if (level <= 0) {
            LINES.clear();
            return;
        }

        Minecraft mc = Minecraft.getMinecraft();
        if (mc == null || mc.theWorld == null || mc.thePlayer == null) {
            LINES.clear();
            return;
        }

        scan(mc.theWorld, 8 + 4 * level,
                (int) Math.floor(mc.thePlayer.posX),
                (int) Math.floor(mc.thePlayer.posY),
                (int) Math.floor(mc.thePlayer.posZ));
    }

    private static void scan(World world, int radius, int cx, int cy, int cz) {
        Map<String, Integer> tally = new HashMap<String, Integer>();

        int minY = Math.max(0, cy - VERTICAL_RANGE);
        int maxY = Math.min(255, cy + VERTICAL_RANGE);

        for (int x = cx - radius; x <= cx + radius; x++) {
            for (int z = cz - radius; z <= cz + radius; z++) {
                for (int y = minY; y <= maxY; y++) {
                    Block block = world.getBlock(x, y, z);
                    if (block == null || IGNORED.contains(block)) continue;

                    String name = oreName(block, world.getBlockMetadata(x, y, z));
                    if (name == null) continue;

                    Integer existing = tally.get(name);
                    tally.put(name, Integer.valueOf(existing == null ? 1 : existing.intValue() + 1));
                }
            }
        }

        rebuildLines(tally);
    }

    private static void rebuildLines(Map<String, Integer> tally) {
        LINES.clear();
        if (tally.isEmpty()) return;

        List<Map.Entry<String, Integer>> sorted =
                new ArrayList<Map.Entry<String, Integer>>(tally.entrySet());
        Collections.sort(sorted, new Comparator<Map.Entry<String, Integer>>() {
            @Override
            public int compare(Map.Entry<String, Integer> a, Map.Entry<String, Integer> b) {
                return b.getValue().intValue() - a.getValue().intValue();
            }
        });

        for (int i = 0; i < sorted.size() && i < MAX_LINES; i++) {
            Map.Entry<String, Integer> e = sorted.get(i);
            LINES.add(String.valueOf(e.getValue()) + EnumChatFormatting.DARK_GRAY + " x "
                    + EnumChatFormatting.GRAY + e.getKey());
        }
    }

    /**
     * The display name if this block+meta is an ore, or null if it is not.
     * Cached both ways -- a null result is remembered too, since the common case
     * is being asked about the same non-ore thousands of times.
     */
    private static String oreName(Block block, int meta) {
        Integer key = Integer.valueOf((Block.getIdFromBlock(block) << 4) | (meta & 15));

        if (ORE_NAME_CACHE.containsKey(key)) return ORE_NAME_CACHE.get(key);

        String name = null;
        try {
            if (Item.getItemFromBlock(block) != null) {
                ItemStack stack = new ItemStack(block, 1, meta);
                for (int id : OreDictionary.getOreIDs(stack)) {
                    String entry = OreDictionary.getOreName(id);
                    if (entry != null && entry.startsWith("ore")) {
                        name = stack.getDisplayName();
                        break;
                    }
                }
            }
        } catch (Throwable t) {
            // A badly behaved modded block can throw from getDisplayName. Treat it
            // as "not ore" and never ask again rather than killing the scan.
            name = null;
        }

        ORE_NAME_CACHE.put(key, name);
        return name;
    }

    public static void render() {
        if (LINES.isEmpty()) return;

        Minecraft mc = Minecraft.getMinecraft();
        if (mc == null || mc.gameSettings.showDebugInfo) return;

        FontRenderer font = mc.fontRenderer;
        if (font == null) return;

        GL11.glPushMatrix();
        GL11.glEnable(GL11.GL_BLEND);
        // Three quarter size and unshadowed: present but never competing with the HUD.
        GL11.glScalef(0.75F, 0.75F, 1.0F);

        int y = 4;
        font.drawString(EnumChatFormatting.DARK_AQUA + "Prospector", 4, y, 0xFFFFFF);
        y += 11;

        for (int i = 0; i < LINES.size(); i++) {
            font.drawString(LINES.get(i), 6, y, 0xFFFFFF);
            y += 10;
        }

        GL11.glDisable(GL11.GL_BLEND);
        GL11.glColor4f(1.0F, 1.0F, 1.0F, 1.0F);
        GL11.glPopMatrix();
    }
}
