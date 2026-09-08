package com.questforge.content.jukebox;

import net.minecraft.client.gui.GuiScreen;
import net.minecraft.util.EnumChatFormatting;
import org.lwjgl.input.Keyboard;
import org.lwjgl.input.Mouse;

import java.io.File;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Comparator;
import java.util.List;

/**
 * Picks folders for the library to index.
 *
 * A browser drawn in the game rather than the operating system's own file dialog.
 * That is not a stylistic choice: opening an AWT dialog from inside the running
 * LWJGL 2 process deadlocks on macOS, because both want the one thread the platform
 * allows to own windows. Since this pack is played mostly on Windows but developed
 * here, a picker that hangs on one of the two is not worth having.
 *
 * It only ever shows folders. There is nothing to gain from picking files one at a
 * time when the indexer already walks subfolders, and a whole music collection is
 * added in a single click this way.
 */
public class GuiMusicFolders extends GuiScreen {

    private static final int PANEL   = 0xF41A2027;
    private static final int RULE    = 0xFF2A333B;
    private static final int FIELD   = 0xFF141A20;
    private static final int TEXT    = 0xFFE8ECF0;
    private static final int DIM     = 0xFF9AA6B2;
    private static final int FAINT   = 0xFF6E7A86;
    private static final int ACCENT  = 0xFFE0A34A;
    private static final int DANGER  = 0xFFC98A8A;
    private static final int GOOD    = 0xFF8FBF8F;

    private static final int ROW_H = 12;
    private static final int PAD = 10;

    private final GuiScreen parent;

    private int left, top, panelW, panelH;

    private File here;
    private List<File> folders = new ArrayList<File>();
    private int audioHere;

    private int scroll;
    private int listTop, listBottom, rows;

    /** Set after an attempt to add, so the reason a click did nothing is visible. */
    private String notice;
    private int noticeColor = DIM;

    public GuiMusicFolders(GuiScreen parent) {
        this.parent = parent;
        this.here = start();
    }

    /**
     * Opens where the music probably is: the user's home folder, or a Music folder
     * inside it when there is one.
     */
    private static File start() {
        try {
            File home = new File(System.getProperty("user.home", "."));
            File music = new File(home, "Music");
            if (music.isDirectory()) return music;
            if (home.isDirectory()) return home;
        } catch (Throwable ignored) {
            // Falls through to the game directory, which always exists.
        }
        return MusicIndex.folder();
    }

    @Override
    public void initGui() {
        Keyboard.enableRepeatEvents(true);
        panelW = Math.min(340, width - 20);
        panelH = Math.min(210, height - 20);
        left = (width - panelW) / 2;
        top = (height - panelH) / 2;
        read();
    }

    @Override
    public void onGuiClosed() {
        Keyboard.enableRepeatEvents(false);
    }

    @Override
    public boolean doesGuiPauseGame() { return false; }

    // ------------------------------------------------------------------
    // Where we are
    // ------------------------------------------------------------------

    private void read() {
        folders = new ArrayList<File>();
        audioHere = 0;
        scroll = 0;

        File[] entries = here == null ? null : here.listFiles();
        if (entries == null) {
            notice = "Cannot read that folder.";
            noticeColor = DANGER;
            return;
        }

        for (File f : entries) {
            String name = f.getName();
            // Dot folders are the operating system's business, not a music library's,
            // and on a home folder they are most of what is there.
            if (name.startsWith(".")) continue;
            if (f.isDirectory()) {
                folders.add(f);
            } else if (isAudio(name)) {
                audioHere++;
            }
        }

        java.util.Collections.sort(folders, new Comparator<File>() {
            @Override public int compare(File a, File b) {
                return a.getName().compareToIgnoreCase(b.getName());
            }
        });
    }

    private static boolean isAudio(String name) {
        String n = name.toLowerCase();
        return n.endsWith(".ogg") || n.endsWith(".mp3") || n.endsWith(".wav")
            || n.endsWith(".aiff") || n.endsWith(".aif") || n.endsWith(".au");
    }

    private void go(File dir) {
        if (dir == null || !dir.isDirectory()) return;
        here = dir;
        notice = null;
        read();
    }

    // ------------------------------------------------------------------
    // Drawing
    // ------------------------------------------------------------------

    @Override
    public void drawScreen(int mx, int my, float partial) {
        drawDefaultBackground();

        drawRect(left, top, left + panelW, top + panelH, PANEL);
        outline(left, top, left + panelW, top + panelH, RULE);

        fontRendererObj.drawString(EnumChatFormatting.BOLD + "MUSIC FOLDERS",
                                   left + PAD, top + 9, TEXT);

        String count = MusicIndex.status();
        fontRendererObj.drawString(count,
                left + panelW - PAD - fontRendererObj.getStringWidth(count), top + 9,
                MusicIndex.isIndexing() ? ACCENT : FAINT);

        int y = top + 24;
        drawRect(left + PAD, y, left + panelW - PAD, y + 1, RULE);
        y += 5;

        y = drawIndexed(mx, my, y);

        drawRect(left + PAD, y, left + panelW - PAD, y + 1, RULE);
        y += 5;

        y = drawPath(y);
        drawBrowser(mx, my, y);
        drawFooter(mx, my);

        super.drawScreen(mx, my, partial);
    }

    /** The folders already being indexed, each with a way to drop it. */
    private int drawIndexed(int mx, int my, int y) {
        fontRendererObj.drawString("Indexed", left + PAD, y, FAINT);
        y += 11;

        // The built-in folder is listed but cannot be removed: it is where the mod
        // tells people to put music, and an empty list would be a dead end.
        fontRendererObj.drawString("jukebox  " + EnumChatFormatting.DARK_GRAY
                + "(in the game folder)", left + PAD + 4, y, DIM);
        y += ROW_H;

        List<File> extras = MusicFolders.extras();
        for (int i = 0; i < extras.size(); i++) {
            File dir = extras.get(i);
            boolean gone = !dir.isDirectory();
            String label = trim(dir.getName().isEmpty()
                    ? dir.getAbsolutePath() : dir.getName(), panelW - PAD * 2 - 60);

            fontRendererObj.drawString(label, left + PAD + 4, y, gone ? DANGER : DIM);
            if (gone) {
                fontRendererObj.drawString("missing",
                        left + PAD + 8 + fontRendererObj.getStringWidth(label), y, DANGER);
            }

            int rx = left + panelW - PAD - 4 - fontRendererObj.getStringWidth("Remove");
            boolean over = mx >= rx && mx <= rx + 40 && my >= y - 1 && my < y + ROW_H - 1;
            fontRendererObj.drawString("Remove", rx, y, over ? DANGER : FAINT);
            y += ROW_H;
        }
        return y + 2;
    }

    private int drawPath(int y) {
        String path = here == null ? "" : here.getAbsolutePath();
        fontRendererObj.drawString(trim(path, panelW - PAD * 2), left + PAD, y, FAINT);
        return y + 11;
    }

    private void drawBrowser(int mx, int my, int y) {
        listTop = y;
        listBottom = top + panelH - 30;
        rows = Math.max(1, (listBottom - listTop) / ROW_H);

        drawRect(left + PAD, listTop - 2, left + panelW - PAD, listBottom, FIELD);

        int shown = 0;
        int i = scroll;

        // The way up, always first, so you are never stuck at the bottom of a tree.
        if (scroll == 0 && here != null && here.getParentFile() != null) {
            int ry = listTop + shown * ROW_H;
            boolean over = overRow(mx, my, ry);
            fontRendererObj.drawString("..", left + PAD + 6, ry + 2, over ? ACCENT : TEXT);
            shown++;
        }

        for (; i < folders.size() && shown < rows; i++, shown++) {
            int ry = listTop + shown * ROW_H;
            boolean over = overRow(mx, my, ry);
            String name = trim(folders.get(i).getName(), panelW - PAD * 2 - 16);
            fontRendererObj.drawString(name, left + PAD + 6, ry + 2, over ? ACCENT : TEXT);
        }

        if (folders.isEmpty() && shown == 0) {
            fontRendererObj.drawString("No folders here.", left + PAD + 6,
                                       listTop + 2, FAINT);
        }
    }

    private void drawFooter(int mx, int my) {
        int y = top + panelH - 24;

        String here = audioHere == 0 ? "No audio files in this folder"
                : audioHere + (audioHere == 1 ? " audio file here" : " audio files here");
        fontRendererObj.drawString(notice != null ? notice : here,
                                   left + PAD, y + 3, notice != null ? noticeColor : FAINT);

        String add = "Add this folder";
        int aw = fontRendererObj.getStringWidth(add) + 12;
        int ax = left + panelW - PAD - aw;
        boolean over = mx >= ax && mx <= ax + aw && my >= y && my <= y + 14;
        drawRect(ax, y, ax + aw, y + 14, over ? 0xFF2E3A44 : FIELD);
        outline(ax, y, ax + aw, y + 14, over ? ACCENT : RULE);
        fontRendererObj.drawString(add, ax + 6, y + 3, over ? ACCENT : TEXT);
    }

    private boolean overRow(int mx, int my, int ry) {
        return mx >= left + PAD && mx <= left + panelW - PAD
            && my >= ry && my < ry + ROW_H;
    }

    private String trim(String s, int max) {
        if (fontRendererObj.getStringWidth(s) <= max) return s;
        // Cut from the front: the end of a path says where you are, the start does
        // not.
        while (s.length() > 1 && fontRendererObj.getStringWidth("..." + s) > max) {
            s = s.substring(1);
        }
        return "..." + s;
    }

    private void outline(int x0, int y0, int x1, int y1, int color) {
        drawRect(x0, y0, x1, y0 + 1, color);
        drawRect(x0, y1 - 1, x1, y1, color);
        drawRect(x0, y0, x0 + 1, y1, color);
        drawRect(x1 - 1, y0, x1, y1, color);
    }

    // ------------------------------------------------------------------
    // Input
    // ------------------------------------------------------------------

    @Override
    protected void mouseClicked(int mx, int my, int button) {
        if (button != 0) return;

        // Remove, on one of the indexed rows.
        int y = top + 29 + 11 + ROW_H;
        List<File> extras = MusicFolders.extras();
        for (int i = 0; i < extras.size(); i++) {
            int rx = left + panelW - PAD - 4 - fontRendererObj.getStringWidth("Remove");
            if (mx >= rx && mx <= rx + 40 && my >= y - 1 && my < y + ROW_H - 1) {
                MusicFolders.remove(extras.get(i));
                notice = "Removed. Reindexing.";
                noticeColor = DIM;
                MusicIndex.rescan();
                return;
            }
            y += ROW_H;
        }

        // Add this folder.
        int fy = top + panelH - 24;
        String add = "Add this folder";
        int aw = fontRendererObj.getStringWidth(add) + 12;
        int ax = left + panelW - PAD - aw;
        if (mx >= ax && mx <= ax + aw && my >= fy && my <= fy + 14) {
            String refused = MusicFolders.add(here);
            if (refused != null) {
                notice = refused;
                noticeColor = DANGER;
            } else {
                notice = "Added. Reindexing.";
                noticeColor = GOOD;
                MusicIndex.rescan();
            }
            return;
        }

        // The browser list.
        if (my >= listTop && my < listBottom && mx >= left + PAD && mx <= left + panelW - PAD) {
            int index = (my - listTop) / ROW_H;
            boolean hasUp = scroll == 0 && here != null && here.getParentFile() != null;
            if (hasUp) {
                if (index == 0) { go(here.getParentFile()); return; }
                index--;
            }
            int target = scroll + index;
            if (target >= 0 && target < folders.size()) go(folders.get(target));
        }
    }

    @Override
    public void handleMouseInput() {
        super.handleMouseInput();
        int wheel = Mouse.getEventDWheel();
        if (wheel == 0) return;
        scroll = Math.max(0, Math.min(Math.max(0, folders.size() - rows + 1),
                                      scroll + (wheel > 0 ? -2 : 2)));
    }

    @Override
    protected void keyTyped(char c, int key) {
        if (key == Keyboard.KEY_ESCAPE) {
            mc.displayGuiScreen(parent);
            return;
        }
        if (key == Keyboard.KEY_BACK && here != null && here.getParentFile() != null) {
            go(here.getParentFile());
            return;
        }
        super.keyTyped(c, key);
    }
}
