package com.questforge.content.census;

import java.io.File;
import java.io.PrintWriter;

import com.questforge.content.QuestForgeContent;

/**
 * A tab-separated census output file.
 *
 * Tab-separated rather than the aligned plain text the ore survey uses, because
 * these files are inputs to analysis rather than things to read directly: a mob
 * census in this pack runs to hundreds of rows and thirty columns. Tabs survive
 * display names containing spaces, commas and section signs, all of which modded
 * items have.
 *
 * Every file opens with a provenance block. The point of this whole exercise is
 * that a number can be traced back to where it came from, so a file that has been
 * copied out of the config directory still says which pack, which measurement and
 * which day produced it.
 */
public class CensusFile {

    private final PrintWriter out;
    private final File target;
    private int rows;

    public CensusFile(File configDir, String name, String description, String[] columns) {
        File f = new File(configDir, "qfcontent-census-" + name + ".tsv");
        PrintWriter w = null;
        try {
            w = new PrintWriter(f, "UTF-8");
            w.println("# QuestForge pack census: " + name);
            w.println("# " + description);
            w.println("#");
            w.println("# Measured inside the running game, not read out of jars. Every value here");
            w.println("# came from calling the pack's own code on the pack's own objects.");
            w.println("# Written " + new java.util.Date());
            w.println("# Minecraft " + net.minecraft.server.MinecraftServer.getServer().getMinecraftVersion()
                    + ", " + cpw.mods.fml.common.Loader.instance().getActiveModList().size() + " mods loaded");
            w.println("#");
            w.println(join(columns));
        } catch (Exception e) {
            QuestForgeContent.log.error("[census] could not open " + f, e);
        }
        this.out = w;
        this.target = f;
    }

    /** One row. Fields are converted with String.valueOf and stripped of tabs and newlines. */
    public void row(Object... fields) {
        if (out == null) return;
        String[] s = new String[fields.length];
        for (int i = 0; i < fields.length; i++) {
            s[i] = clean(fields[i]);
        }
        out.println(join(s));
        rows++;
    }

    public File file() {
        return target;
    }

    public int rows() {
        return rows;
    }

    public void close() {
        if (out == null) return;
        out.println("# " + rows + " rows");
        out.close();
    }

    private static String clean(Object o) {
        if (o == null) return "";
        String s = String.valueOf(o);
        // A tab or a newline inside a field would silently shift every later column.
        s = s.replace('\t', ' ').replace('\n', ' ').replace('\r', ' ');
        return s;
    }

    private static String join(String[] parts) {
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < parts.length; i++) {
            if (i > 0) sb.append('\t');
            sb.append(parts[i]);
        }
        return sb.toString();
    }

    /** Formats a float without locale surprises and without trailing noise. */
    public static String num(double v) {
        if (Double.isNaN(v)) return "NaN";
        if (Double.isInfinite(v)) return v > 0 ? "+Inf" : "-Inf";
        return String.format(java.util.Locale.ROOT, "%.4f", v);
    }
}
