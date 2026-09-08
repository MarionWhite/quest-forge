package com.questforge.content.jukebox;

import net.minecraft.client.Minecraft;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileReader;
import java.io.PrintWriter;
import java.util.ArrayList;
import java.util.List;

/**
 * The folders the library is built from.
 *
 * The jukebox folder inside the game directory is always one of them. This adds the
 * others, so a music collection that already exists somewhere on the disk can be
 * played without being moved or copied into the pack -- which for anyone with a real
 * library would mean duplicating tens of gigabytes.
 *
 * Pointing at folders rather than importing files is also what keeps this change
 * small. A local track is identified everywhere else in the mod by its FILE NAME, not
 * its path -- that is what gets stored in a record, sent in a packet, and looked up
 * again when a jukebox restores what it was bound to. So an indexed file works
 * exactly the same wherever it physically lives, and nothing downstream had to know
 * this feature exists.
 *
 * The one consequence of that is worth stating: two files with the same name in
 * different folders are the same track as far as the rest of the mod is concerned,
 * and a jukebox rebinding to that name gets whichever was indexed first.
 *
 * The list is a plain text file so it can be fixed by hand if a folder moves.
 */
public final class MusicFolders {

    private static final String FILE = "qf-jukebox-folders.txt";

    /** Enough for a music drive and a few loose folders; a guard, not a design. */
    public static final int MAX = 8;

    private static List<File> extra;

    private MusicFolders() { }

    private static File file() {
        File dir = new File(Minecraft.getMinecraft().mcDataDir, "config");
        if (!dir.exists()) dir.mkdirs();
        return new File(dir, FILE);
    }

    // ------------------------------------------------------------------
    // Reading
    // ------------------------------------------------------------------

    /** Every folder to scan: the built-in one first, then whatever was added. */
    public static List<File> roots() {
        List<File> all = new ArrayList<File>();
        all.add(MusicIndex.folder());
        all.addAll(extras());
        return all;
    }

    public static List<File> extras() {
        if (extra == null) load();
        return new ArrayList<File>(extra);
    }

    private static synchronized void load() {
        List<File> found = new ArrayList<File>();
        File f = file();
        if (f.isFile()) {
            BufferedReader in = null;
            try {
                in = new BufferedReader(new FileReader(f));
                String line;
                while ((line = in.readLine()) != null) {
                    line = line.trim();
                    if (line.isEmpty() || line.startsWith("#")) continue;
                    File dir = new File(line);
                    // Kept even when missing would be tempting, but a folder on an
                    // unplugged drive that silently disappears from the list is worse
                    // than one that stays and simply indexes nothing.
                    if (found.size() < MAX) found.add(dir);
                }
            } catch (Throwable t) {
                com.questforge.content.QuestForgeContent.log.warn(
                        "[jukebox] could not read music folders", t);
            } finally {
                close(in);
            }
        }
        extra = found;
    }

    private static synchronized void save() {
        PrintWriter out = null;
        try {
            out = new PrintWriter(file(), "UTF-8");
            out.println("# Folders the jukebox indexes, one per line, in addition to");
            out.println("# the jukebox folder in this game directory.");
            for (File dir : extra) out.println(dir.getAbsolutePath());
        } catch (Throwable t) {
            com.questforge.content.QuestForgeContent.log.warn(
                    "[jukebox] could not save music folders", t);
        } finally {
            if (out != null) out.close();
        }
    }

    // ------------------------------------------------------------------
    // Changing
    // ------------------------------------------------------------------

    /**
     * Adds a folder. Returns why not, or null on success.
     *
     * The refusals are all about not making the index worse: scanning a folder twice
     * lists every track in it twice, and handing this the root of a disk would send
     * the indexer through the whole filesystem.
     */
    public static synchronized String add(File dir) {
        if (extra == null) load();

        if (dir == null || !dir.isDirectory()) return "That is not a folder.";
        if (dir.getParentFile() == null) return "Pick a folder inside the drive, not the drive itself.";
        if (extra.size() >= MAX) return "That is as many folders as it will hold.";

        String path = canonical(dir);
        for (File existing : roots()) {
            String other = canonical(existing);
            if (path.equals(other)) return "That folder is already in the list.";
            if (path.startsWith(other + File.separator)) {
                return "Already covered by " + existing.getName() + ".";
            }
            if (other.startsWith(path + File.separator)) {
                return "That folder contains " + existing.getName() + ", already in the list.";
            }
        }

        extra.add(dir);
        save();
        return null;
    }

    public static synchronized void remove(File dir) {
        if (extra == null) load();
        String path = canonical(dir);
        for (int i = 0; i < extra.size(); i++) {
            if (canonical(extra.get(i)).equals(path)) {
                extra.remove(i);
                save();
                return;
            }
        }
    }

    /**
     * Resolved through any symlinks, so two names for one folder are recognised as
     * the same folder -- which is the case the containment checks above would
     * otherwise miss entirely.
     */
    private static String canonical(File f) {
        try {
            return f.getCanonicalPath();
        } catch (Throwable t) {
            return f.getAbsolutePath();
        }
    }

    private static void close(java.io.Closeable c) {
        if (c == null) return;
        try { c.close(); } catch (Throwable ignored) { }
    }
}
