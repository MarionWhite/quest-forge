package com.questforge.content.survey;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileReader;
import java.io.PrintWriter;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.List;
import java.util.Map;

import net.minecraft.block.Block;
import net.minecraft.item.ItemStack;

import cpw.mods.fml.common.registry.GameRegistry;

import com.questforge.content.QuestForgeContent;

/**
 * Persists the ore survey between sessions.
 *
 * Written as plain text keyed on REGISTRY NAME rather than numeric block id, for
 * the same reason enchantment books store names: block ids are assigned per
 * install and shift when mods are added or removed, so a numeric file would
 * silently start describing different ores.
 *
 * The file is meant to be readable and editable -- a survey is a measurement, and
 * you should be able to look at it and disagree with it.
 */
public class OreSurveyStore {

    private static final String FILE_NAME = "qfcontent-oresurvey.txt";

    private static File file;

    public static void setConfigDir(File configDir) {
        file = new File(configDir, FILE_NAME);
    }

    public static File file() {
        return file;
    }

    public static void save() {
        if (file == null) return;

        PrintWriter out = null;
        try {
            out = new PrintWriter(file, "UTF-8");
            out.println("# QuestForge ore survey.");
            out.println("# Measured by generating chunks server-side and counting what came out.");
            out.println("# Format: dimension|modid:block_name:metadata = blocks observed");
            out.println("# chunks.<dimension> is how many chunks that dimension was measured");
            out.println("# over, which is what turns counts into a density. Sampling one");
            out.println("# dimension longer than another therefore cannot skew the result.");
            out.println("# Delete this file to discard the measurement and start again.");
            out.println();

            for (Map.Entry<Integer, Integer> e : OreSurvey.chunksByDimension().entrySet()) {
                out.println("chunks." + e.getKey() + " = " + e.getValue());
            }
            out.println();

            for (Map.Entry<Integer, Map<Integer, Integer>> dim
                    : OreSurvey.countsByDimension().entrySet()) {
                for (String line : sortedLines(dim.getKey().intValue(), dim.getValue())) {
                    out.println(line);
                }
                out.println();
            }

        } catch (Exception e) {
            QuestForgeContent.log.error("Could not write the ore survey to " + file, e);
        } finally {
            if (out != null) out.close();
        }
    }

    /**
     * Most abundant ore first.
     *
     * Deliberately a named, package-private class rather than an anonymous one.
     * Anonymous classes -- and private nested classes, which javac reaches
     * through a synthetic accessor class -- produce an extra OreSurveyStore$N
     * that failed to load under Forge's LaunchClassLoader on the dedicated
     * server, taking the server down with it. Nothing synthetic, nothing to
     * fail to load.
     */
    static final class ByCountDescending
            implements Comparator<Map.Entry<Integer, Integer>> {
        @Override
        public int compare(Map.Entry<Integer, Integer> a, Map.Entry<Integer, Integer> b) {
            return Integer.compare(b.getValue().intValue(), a.getValue().intValue());
        }
    }

    private static final Comparator<Map.Entry<Integer, Integer>> BY_COUNT =
            new ByCountDescending();

    /**
     * Everything measured so far, most abundant first.
     *
     * Both the file and the /qfsurvey show output want exactly this, so it lives
     * in one place rather than being two copies of the same sort.
     */
    public static List<Map.Entry<Integer, Integer>> ranked() {
        List<Map.Entry<Integer, Integer>> entries =
                new ArrayList<Map.Entry<Integer, Integer>>(OreSurvey.counts().entrySet());
        Collections.sort(entries, BY_COUNT);
        return entries;
    }

    /** Highest count first, so each dimension's block reads as a ranking. */
    private static List<String> sortedLines(int dimension, Map<Integer, Integer> counts) {
        List<Map.Entry<Integer, Integer>> entries =
                new ArrayList<Map.Entry<Integer, Integer>>(counts.entrySet());
        Collections.sort(entries, BY_COUNT);

        List<String> lines = new ArrayList<String>();
        for (Map.Entry<Integer, Integer> e : entries) {
            String name = nameOf(e.getKey().intValue());
            if (name != null) lines.add(dimension + "|" + name + " = " + e.getValue());
        }
        return lines;
    }

    static String nameOfKey(int key) {
        return nameOf(key);
    }

    static Integer keyOfName(String name) {
        return keyOf(name);
    }

    private static String nameOf(int key) {
        Block block = Block.getBlockById(key >> 4);
        if (block == null) return null;

        String name = registryName(block);
        return name == null ? null : name + ":" + (key & 15);
    }

    /** "modid:block_name", or null if the block is not registered. */
    static String registryName(Block block) {
        GameRegistry.UniqueIdentifier id =
                GameRegistry.findUniqueIdentifierFor(net.minecraft.item.Item.getItemFromBlock(block));
        if (id == null) id = GameRegistry.findUniqueIdentifierFor(block);
        return id == null ? null : id.modId + ":" + id.name;
    }

    /** Reloads a previous survey, if one exists. Safe to call when none does. */
    public static void load() {
        if (file == null || !file.exists()) return;

        BufferedReader in = null;
        int loaded = 0;
        try {
            in = new BufferedReader(new FileReader(file));
            OreSurvey.clear();

            String line;
            while ((line = in.readLine()) != null) {
                line = line.trim();
                if (line.isEmpty() || line.startsWith("#")) continue;

                int eq = line.indexOf('=');
                if (eq < 0) continue;

                String left = line.substring(0, eq).trim();
                String right = line.substring(eq + 1).trim();

                if (left.startsWith("chunks.")) {
                    OreSurvey.restore(parse(left.substring("chunks.".length())), parse(right));
                    continue;
                }
                if ("chunks_sampled".equals(left)) {
                    // A file written before the survey knew about dimensions. All of
                    // it was measured in the overworld, so that is where it belongs.
                    OreSurvey.restore(0, parse(right));
                    continue;
                }

                int dimension = 0;
                String name = left;
                int bar = left.indexOf('|');
                if (bar >= 0) {
                    dimension = parse(left.substring(0, bar));
                    name = left.substring(bar + 1);
                }

                Integer key = keyOf(name);
                if (key == null) continue;

                OreSurvey.record(dimension, key.intValue(), parse(right));
                loaded++;
            }

            QuestForgeContent.log.info("Loaded ore survey: " + loaded + " entries over "
                    + OreSurvey.chunksSampled() + " chunks in "
                    + OreSurvey.chunksByDimension().size() + " dimension(s).");

        } catch (Exception e) {
            QuestForgeContent.log.error("Could not read the ore survey at " + file, e);
        } finally {
            try { if (in != null) in.close(); } catch (Exception ignored) { }
        }
    }

    /** "modid:block_name:meta" back to blockId<<4|meta, or null if not installed now. */
    private static Integer keyOf(String name) {
        int lastColon = name.lastIndexOf(':');
        if (lastColon < 0) return null;

        String blockName = name.substring(0, lastColon);
        int meta = parse(name.substring(lastColon + 1));

        int firstColon = blockName.indexOf(':');
        if (firstColon < 0) return null;

        Block block = GameRegistry.findBlock(blockName.substring(0, firstColon),
                blockName.substring(firstColon + 1));
        if (block == null) return null;   // that mod is no longer installed

        int id = Block.getIdFromBlock(block);
        if (id <= 0) return null;

        return Integer.valueOf((id << 4) | (meta & 15));
    }

    private static int parse(String s) {
        try {
            return Integer.parseInt(s.trim());
        } catch (NumberFormatException e) {
            return 0;
        }
    }

    /** Convenience for the command, so it need not know about ItemStacks. */
    public static String describe(int key) {
        Block block = Block.getBlockById(key >> 4);
        if (block == null) return "unknown";
        try {
            return new ItemStack(block, 1, key & 15).getDisplayName();
        } catch (Throwable t) {
            return block.getUnlocalizedName();
        }
    }
}
