package com.questforge.content;

import java.io.File;
import java.io.PrintWriter;
import java.util.ArrayList;
import java.util.List;

import net.minecraft.enchantment.Enchantment;

/**
 * Dumps every enchantment registered by every mod, plus the free ID ranges.
 *
 * 1.7.10 has exactly 256 enchantment ID slots shared by vanilla and all mods, and
 * the Enchantment constructor throws IllegalArgumentException on a duplicate ID --
 * a hard crash at load, not a warning. In a 113-mod pack you cannot pick IDs by
 * guessing, so run this once and read the report before choosing.
 *
 * Writes config/qfcontent-enchantments.txt on every start. Cheap; delete the
 * postInit call once the IDs are settled.
 */
public class EnchantmentAudit {

    public static void write(File configDir) {
        File out = new File(configDir, "qfcontent-enchantments.txt");
        PrintWriter w = null;
        try {
            w = new PrintWriter(out, "UTF-8");

            Enchantment[] list = Enchantment.enchantmentsList;
            int used = 0;

            w.println("Enchantment registry audit");
            w.println("Total ID slots: " + list.length);
            w.println();
            w.println("id   name                      type            weight maxLvl class");
            w.println("---- ------------------------- --------------- ------ ------ -----");

            for (int i = 0; i < list.length; i++) {
                Enchantment e = list[i];
                if (e == null) continue;
                used++;
                w.printf("%-4d %-25s %-15s %-6d %-6d %s%n",
                        i,
                        safe(e.getName()),
                        e.type == null ? "?" : e.type.toString(),
                        e.getWeight(),
                        e.getMaxLevel(),
                        e.getClass().getName());
            }

            w.println();
            w.println("Used: " + used + " / " + list.length + "   Free: " + (list.length - used));
            w.println();
            w.println("Free ID ranges:");
            for (String range : freeRanges(list)) {
                w.println("  " + range);
            }

            QuestForgeContent.log.info("Enchantment audit written to " + out.getAbsolutePath()
                    + " (" + used + " of " + list.length + " IDs used)");
        } catch (Exception ex) {
            QuestForgeContent.log.error("Could not write enchantment audit", ex);
        } finally {
            if (w != null) w.close();
        }
    }

    private static List<String> freeRanges(Enchantment[] list) {
        List<String> ranges = new ArrayList<String>();
        int start = -1;
        for (int i = 0; i <= list.length; i++) {
            boolean free = i < list.length && list[i] == null;
            if (free && start == -1) {
                start = i;
            } else if (!free && start != -1) {
                int end = i - 1;
                ranges.add(start == end
                        ? String.valueOf(start)
                        : start + "-" + end + "  (" + (end - start + 1) + " slots)");
                start = -1;
            }
        }
        return ranges;
    }

    private static String safe(String s) {
        return s == null ? "?" : s;
    }
}
