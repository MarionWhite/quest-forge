package com.questforge.content.jukebox;

import net.minecraft.client.gui.GuiScreen;
import net.minecraft.client.gui.GuiTextField;
import net.minecraft.client.gui.ScaledResolution;
import net.minecraft.util.EnumChatFormatting;
import org.lwjgl.input.Keyboard;
import org.lwjgl.input.Mouse;
import org.lwjgl.opengl.GL11;

import java.util.ArrayList;
import java.util.List;

/**
 * Pressing a record: pick from what you already have, name it, cut it.
 *
 * Deliberately narrower than the jukebox screen. This one is not for finding
 * music -- it draws only on your own playlists and saved songs, because a record
 * is made out of things you have already decided you like. That is what keeps it
 * to three short lists instead of a second search interface.
 */
public class GuiRecorder extends GuiScreen {

    private static final int ACCENT      = 0xFFE0A34A;
    private static final int ACCENT_SOFT = 0x33E0A34A;
    private static final int PANEL       = 0xF2101418;
    private static final int PANEL_EDGE  = 0xFF2B3238;
    private static final int FIELD       = 0xFF171C21;
    private static final int RULE        = 0xFF232A30;
    private static final int TEXT        = 0xFFE8ECF0;
    private static final int TEXT_DIM    = 0xFF8A96A2;
    private static final int TEXT_FAINT  = 0xFF5A6672;
    private static final int HOVER       = 0x14FFFFFF;

    private static final int ROW_H = 22;
    private static final int PAD = 10;
    private static final int FOOTER_H = 30;

    private static final int TAB_PLAYLISTS = 0, TAB_SAVED = 1, TAB_SIDE = 2;
    private static final String[] TAB_NAMES = { "Playlists", "Saved songs", "The record" };

    /** What is going onto the record, in the order it was chosen. */
    private final List<Track> chosen = new ArrayList<Track>();

    private GuiTextField nameField;
    private int tab = TAB_PLAYLISTS;

    private float scroll, scrollTarget;
    private int left, top, panelW, panelH, listTop, listH, visibleRows;
    private int caretTimer;

    private int[] tabX = new int[TAB_NAMES.length];
    private int[] tabW = new int[TAB_NAMES.length];
    private int tabY, tabH = 15;

    private int cutX, cutY, cutW, cutH = 16;

    private String toast;
    private long toastUntil;

    @Override public boolean doesGuiPauseGame() { return false; }

    @Override
    public void initGui() {
        Keyboard.enableRepeatEvents(true);

        panelW = Math.min(width - 40, 420);
        panelH = Math.min(height - 40, 280);
        left = (width - panelW) / 2;
        top = (height - panelH) / 2;

        nameField = new GuiTextField(fontRendererObj, left + PAD, top + 24,
                                     panelW - PAD * 2, 14);
        nameField.setMaxStringLength(PublicPlaylists.MAX_NAME);
        nameField.setFocused(true);

        tabY = top + 48;
        int x = left + PAD;
        for (int i = 0; i < TAB_NAMES.length; i++) {
            tabW[i] = fontRendererObj.getStringWidth(TAB_NAMES[i]) + 14;
            tabX[i] = x;
            x += tabW[i] + 4;
        }

        listTop = top + 70;
        listH = panelH - FOOTER_H - (listTop - top) - 6;
        visibleRows = Math.max(1, listH / ROW_H);

        cutW = 92;
        cutX = left + panelW - PAD - cutW;
        cutY = top + panelH - FOOTER_H + 6;
    }

    @Override public void onGuiClosed() { Keyboard.enableRepeatEvents(false); }

    @Override public void updateScreen() { super.updateScreen(); caretTimer++; }

    // ------------------------------------------------------------------
    // Contents
    // ------------------------------------------------------------------

    private int rowCount() {
        if (tab == TAB_PLAYLISTS) return Library.playlistNames().size();
        if (tab == TAB_SAVED) return Library.savedTracks().size();
        return chosen.size();
    }

    private boolean full() { return chosen.size() >= PublicPlaylists.MAX_TRACKS; }

    /** True when every song in a playlist is already on the record. */
    private boolean allChosen(List<Track> tracks) {
        if (tracks.isEmpty()) return false;
        for (int i = 0; i < tracks.size(); i++) {
            if (!chosen.contains(tracks.get(i))) return false;
        }
        return true;
    }

    private void toggleTrack(Track t) {
        if (chosen.remove(t)) return;
        if (full()) { say("A record holds " + PublicPlaylists.MAX_TRACKS + " songs"); return; }
        chosen.add(t);
    }

    private void togglePlaylist(String name) {
        List<Track> tracks = Library.playlist(name);
        if (tracks.isEmpty()) { say("\"" + name + "\" is empty"); return; }

        if (allChosen(tracks)) {
            chosen.removeAll(tracks);
            say("Removed " + name);
            return;
        }

        int added = 0;
        for (int i = 0; i < tracks.size(); i++) {
            Track t = tracks.get(i);
            if (chosen.contains(t)) continue;
            if (full()) break;
            chosen.add(t);
            added++;
        }
        say(added == 0 ? "Already on the record" : "Added " + added + " from " + name);
    }

    private void cut() {
        if (chosen.isEmpty()) { say("Pick some songs first"); return; }

        String label = nameField.getText().trim();
        if (label.isEmpty()) label = "Untitled";

        // The server writes the NBT; this only asks. The chat line it sends back
        // is what confirms the record was really pressed.
        com.questforge.content.net.QFNetwork.toServer(
                new com.questforge.content.net.PacketWriteRecord(label, chosen));
        mc.displayGuiScreen(null);
    }

    // ------------------------------------------------------------------
    // Input
    // ------------------------------------------------------------------

    @Override
    protected void keyTyped(char c, int key) {
        if (key == Keyboard.KEY_ESCAPE) { mc.displayGuiScreen(null); return; }
        if (key == Keyboard.KEY_RETURN) { cut(); return; }
        if (key == Keyboard.KEY_TAB) {
            tab = (tab + 1) % TAB_NAMES.length;
            scroll = scrollTarget = 0;
            return;
        }
        if (nameField.textboxKeyTyped(c, key)) return;
        super.keyTyped(c, key);
    }

    @Override
    protected void mouseClicked(int mx, int my, int button) {
        nameField.mouseClicked(mx, my, button);

        for (int i = 0; i < TAB_NAMES.length; i++) {
            if (mx >= tabX[i] && mx <= tabX[i] + tabW[i] && my >= tabY && my <= tabY + tabH) {
                tab = i;
                scroll = scrollTarget = 0;
                return;
            }
        }

        if (mx >= cutX && mx <= cutX + cutW && my >= cutY && my <= cutY + cutH) {
            cut();
            return;
        }

        if (my >= listTop && my < listTop + listH
                && mx >= left + PAD && mx <= left + panelW - PAD) {
            int index = (int) ((my - listTop + scroll * ROW_H) / ROW_H);
            if (index < 0 || index >= rowCount()) return;

            if (tab == TAB_PLAYLISTS) {
                togglePlaylist(Library.playlistNames().get(index));
            } else if (tab == TAB_SAVED) {
                toggleTrack(Library.savedTracks().get(index));
            } else {
                chosen.remove(index);
            }
        }
    }

    @Override
    public void handleMouseInput() {
        super.handleMouseInput();
        int wheel = Mouse.getEventDWheel();
        if (wheel == 0) return;
        scrollTarget += wheel > 0 ? -3 : 3;
        clampScroll();
    }

    private void clampScroll() {
        int max = Math.max(0, rowCount() - visibleRows);
        if (scrollTarget > max) scrollTarget = max;
        if (scrollTarget < 0) scrollTarget = 0;
    }

    // ------------------------------------------------------------------
    // Drawing
    // ------------------------------------------------------------------

    @Override
    public void drawScreen(int mx, int my, float partial) {
        clampScroll();
        scroll += (scrollTarget - scroll) * 0.35f;
        if (Math.abs(scrollTarget - scroll) < 0.01f) scroll = scrollTarget;

        drawDefaultBackground();
        drawRect(left, top, left + panelW, top + panelH, PANEL);
        outline(left, top, left + panelW, top + panelH, PANEL_EDGE);

        fontRendererObj.drawString(EnumChatFormatting.BOLD + "CUT A RECORD",
                                   left + PAD, top + 10, TEXT);

        String tally = chosen.size() + " / " + PublicPlaylists.MAX_TRACKS;
        fontRendererObj.drawString(tally,
                left + panelW - PAD - fontRendererObj.getStringWidth(tally), top + 10,
                full() ? ACCENT : TEXT_FAINT);

        drawNameField();
        drawTabs(mx, my);
        drawList(mx, my);
        drawFooter(mx, my);
        drawToast();

        super.drawScreen(mx, my, partial);
    }

    private void drawNameField() {
        int x = left + PAD, y = top + 22, w = panelW - PAD * 2, h = 18;
        drawRect(x, y, x + w, y + h, FIELD);
        outline(x, y, x + w, y + h, nameField.isFocused() ? 0xFF3E4952 : RULE);

        String text = nameField.getText();
        if (text.isEmpty()) {
            fontRendererObj.drawString("name this record", x + 6, y + 5, TEXT_FAINT);
        } else {
            fontRendererObj.drawString(trim(text, w - 12), x + 6, y + 5, TEXT);
        }

        if (nameField.isFocused() && (caretTimer / 6) % 2 == 0) {
            int caretX = x + 6 + fontRendererObj.getStringWidth(text);
            drawRect(caretX, y + 4, caretX + 1, y + h - 4, ACCENT);
        }
    }

    private void drawTabs(int mx, int my) {
        for (int i = 0; i < TAB_NAMES.length; i++) {
            boolean active = i == tab;
            boolean hover = mx >= tabX[i] && mx <= tabX[i] + tabW[i]
                         && my >= tabY && my <= tabY + tabH;

            if (active) drawRect(tabX[i], tabY, tabX[i] + tabW[i], tabY + tabH, ACCENT_SOFT);
            else if (hover) drawRect(tabX[i], tabY, tabX[i] + tabW[i], tabY + tabH, HOVER);

            String name = TAB_NAMES[i];
            if (i == TAB_SIDE && !chosen.isEmpty()) name = name + "  " + chosen.size();

            int tx = tabX[i] + (tabW[i] - fontRendererObj.getStringWidth(TAB_NAMES[i])) / 2;
            fontRendererObj.drawString(name, tx, tabY + 4, active ? ACCENT : TEXT_DIM);
            if (active) drawRect(tabX[i], tabY + tabH - 1, tabX[i] + tabW[i], tabY + tabH, ACCENT);
        }
        drawRect(left + PAD, tabY + tabH, left + panelW - PAD, tabY + tabH + 1, RULE);
    }

    private void drawList(int mx, int my) {
        int count = rowCount();
        if (count == 0) {
            fontRendererObj.drawString(emptyMessage(), left + PAD + 2, listTop + 8, TEXT_FAINT);
            return;
        }

        beginClip(left + PAD, listTop, panelW - PAD * 2, listH);

        int first = (int) Math.floor(scroll);
        int offset = (int) ((scroll - first) * ROW_H);

        List<String> names = tab == TAB_PLAYLISTS ? Library.playlistNames() : null;
        List<Track> saved = tab == TAB_SAVED ? Library.savedTracks() : null;

        for (int i = 0; i <= visibleRows; i++) {
            int index = first + i;
            if (index < 0 || index >= count) continue;

            int ry = listTop + i * ROW_H - offset;
            boolean hover = mx >= left + PAD && mx <= left + panelW - PAD
                         && my >= ry && my < ry + ROW_H
                         && my >= listTop && my < listTop + listH;
            if (hover) drawRect(left + PAD, ry, left + panelW - PAD, ry + ROW_H, HOVER);

            if (tab == TAB_PLAYLISTS) {
                String name = names.get(index);
                List<Track> tracks = Library.playlist(name);
                drawCheck(left + PAD + 4, ry + ROW_H / 2 - 4, allChosen(tracks));

                int n = tracks.size();
                String size = n + (n == 1 ? " song" : " songs");
                int sw = fontRendererObj.getStringWidth(size);
                fontRendererObj.drawString(size, left + panelW - PAD - 6 - sw, ry + 7, TEXT_FAINT);
                fontRendererObj.drawString(trim(name, panelW - 90), left + PAD + 18, ry + 7, TEXT);

            } else if (tab == TAB_SAVED) {
                Track t = saved.get(index);
                drawCheck(left + PAD + 4, ry + ROW_H / 2 - 4, chosen.contains(t));
                drawTrack(t, left + PAD + 18, ry);

            } else {
                // The running order is the record, so it is numbered.
                String number = (index + 1) + ".";
                fontRendererObj.drawString(number, left + PAD + 4, ry + 7, TEXT_FAINT);
                drawTrack(chosen.get(index), left + PAD + 20, ry);

                if (hover) {
                    String remove = "remove";
                    fontRendererObj.drawString(remove,
                            left + panelW - PAD - 6 - fontRendererObj.getStringWidth(remove),
                            ry + 7, 0xFFB87878);
                }
            }
        }
        endClip();

        drawScrollbar(count);
    }

    private void drawTrack(Track t, int x, int ry) {
        int width = panelW - (x - left) - 60;
        fontRendererObj.drawString(trim(t.title, width), x, ry + 2, TEXT);
        fontRendererObj.drawString(trim(t.artistText(), width), x, ry + 11, TEXT_DIM);
    }

    private void drawCheck(int x, int y, boolean on) {
        outline(x, y, x + 9, y + 9, on ? ACCENT : TEXT_DIM);
        if (!on) return;
        drawRect(x + 2, y + 4, x + 4, y + 6, ACCENT);
        drawRect(x + 4, y + 3, x + 7, y + 5, ACCENT);
    }

    private void drawScrollbar(int count) {
        if (count <= visibleRows) return;
        int trackX = left + panelW - PAD + 2;
        int barHeight = Math.max(12, listH * visibleRows / count);
        int max = count - visibleRows;
        int y = listTop + (int) ((listH - barHeight) * (scroll / Math.max(1, max)));

        drawRect(trackX, listTop, trackX + 2, listTop + listH, 0x18FFFFFF);
        drawRect(trackX, y, trackX + 2, y + barHeight, 0x66FFFFFF);
    }

    private String emptyMessage() {
        if (tab == TAB_PLAYLISTS) return "No playlists yet. Make one in the jukebox.";
        if (tab == TAB_SAVED) return "Nothing saved yet. Use the dots on any song.";
        return "Nothing on the record. Pick from the other two tabs.";
    }

    private void drawFooter(int mx, int my) {
        int y0 = top + panelH - FOOTER_H;
        drawRect(left + PAD, y0, left + panelW - PAD, y0 + 1, RULE);

        fontRendererObj.drawString(
                chosen.isEmpty() ? "pick songs, name it, then cut it"
                                 : "cuts onto the record in your hand",
                left + PAD, cutY + 4, TEXT_FAINT);

        boolean ready = !chosen.isEmpty();
        boolean hover = mx >= cutX && mx <= cutX + cutW
                     && my >= cutY && my <= cutY + cutH;

        drawRect(cutX, cutY, cutX + cutW, cutY + cutH,
                 ready && hover ? 0xFF2A3A32 : 0xFF1D2429);
        outline(cutX, cutY, cutX + cutW, cutY + cutH,
                ready ? (hover ? ACCENT : 0xFF3E4952) : RULE);

        String label = "Cut record";
        fontRendererObj.drawString(label,
                cutX + (cutW - fontRendererObj.getStringWidth(label)) / 2, cutY + 4,
                ready ? (hover ? ACCENT : TEXT) : TEXT_FAINT);
    }

    private void say(String message) {
        toast = message;
        toastUntil = System.currentTimeMillis() + 2200L;
    }

    private void drawToast() {
        if (toast == null || System.currentTimeMillis() > toastUntil) return;
        int w = fontRendererObj.getStringWidth(toast) + 16;
        int x = left + (panelW - w) / 2;
        int y = top + panelH - FOOTER_H - 18;

        drawRect(x, y, x + w, y + 14, 0xE81A2027);
        outline(x, y, x + w, y + 14, 0xFF3E4952);
        fontRendererObj.drawString(toast, x + 8, y + 3, ACCENT);
    }

    // ------------------------------------------------------------------
    // Helpers
    // ------------------------------------------------------------------

    private void beginClip(int x, int y, int w, int h) {
        ScaledResolution sr = new ScaledResolution(mc, mc.displayWidth, mc.displayHeight);
        int factor = sr.getScaleFactor();
        GL11.glEnable(GL11.GL_SCISSOR_TEST);
        GL11.glScissor(x * factor, (sr.getScaledHeight() - (y + h)) * factor,
                       w * factor, h * factor);
    }

    private void endClip() { GL11.glDisable(GL11.GL_SCISSOR_TEST); }

    private void outline(int x1, int y1, int x2, int y2, int c) {
        drawRect(x1, y1, x2, y1 + 1, c);
        drawRect(x1, y2 - 1, x2, y2, c);
        drawRect(x1, y1, x1 + 1, y2, c);
        drawRect(x2 - 1, y1, x2, y2, c);
    }

    private String trim(String s, int maxPx) {
        if (s == null || maxPx <= 0) return "";
        if (fontRendererObj.getStringWidth(s) <= maxPx) return s;
        while (s.length() > 1 && fontRendererObj.getStringWidth(s + "...") > maxPx) {
            s = s.substring(0, s.length() - 1);
        }
        return s + "...";
    }
}
