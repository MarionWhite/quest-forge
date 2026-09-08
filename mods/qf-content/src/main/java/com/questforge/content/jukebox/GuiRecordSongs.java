package com.questforge.content.jukebox;

import net.minecraft.client.gui.GuiScreen;
import net.minecraft.client.gui.ScaledResolution;
import net.minecraft.util.EnumChatFormatting;
import org.lwjgl.input.Keyboard;
import org.lwjgl.input.Mouse;
import org.lwjgl.opengl.GL11;

import java.util.ArrayList;
import java.util.List;

/**
 * What is on a record, with the option to take songs off it.
 *
 * Unticking marks a song rather than deleting it on the spot, and nothing is sent
 * until Save. A checkbox that destroyed something the instant it was clicked would
 * be a delete button wearing a checkbox's clothes, and there is no undo on a
 * record.
 */
public class GuiRecordSongs extends GuiScreen {

    private static final int ACCENT      = 0xFFE0A34A;
    private static final int PANEL       = 0xF2101418;
    private static final int PANEL_EDGE  = 0xFF2B3238;
    private static final int RULE        = 0xFF232A30;
    private static final int TEXT        = 0xFFE8ECF0;
    private static final int TEXT_DIM    = 0xFF8A96A2;
    private static final int TEXT_FAINT  = 0xFF5A6672;
    private static final int HOVER       = 0x14FFFFFF;
    private static final int DANGER      = 0xFFB87878;

    private static final int ROW_H = 22;
    private static final int PAD = 10;
    private static final int FOOTER_H = 30;

    private final int slotIndex;
    private final String label;
    private final List<Track> tracks;
    private final boolean[] keep;

    private float scroll, scrollTarget;
    private int left, top, panelW, panelH, listTop, listH, visibleRows;
    private int saveX, saveY, saveW, saveH = 16;

    public GuiRecordSongs(int slotIndex, String label, List<Track> tracks) {
        this.slotIndex = slotIndex;
        this.label = label == null || label.isEmpty() ? "Record" : label;
        this.tracks = tracks == null ? new ArrayList<Track>() : tracks;
        this.keep = new boolean[this.tracks.size()];
        for (int i = 0; i < keep.length; i++) keep[i] = true;
    }

    @Override public boolean doesGuiPauseGame() { return false; }

    @Override
    public void initGui() {
        panelW = Math.min(width - 40, 400);
        panelH = Math.min(height - 40, 260);
        left = (width - panelW) / 2;
        top = (height - panelH) / 2;

        listTop = top + 34;
        listH = panelH - FOOTER_H - (listTop - top) - 6;
        visibleRows = Math.max(1, listH / ROW_H);

        saveW = 96;
        saveX = left + panelW - PAD - saveW;
        saveY = top + panelH - FOOTER_H + 6;
    }

    private int kept() {
        int n = 0;
        for (int i = 0; i < keep.length; i++) if (keep[i]) n++;
        return n;
    }

    private boolean changed() { return kept() != tracks.size(); }

    private void save() {
        if (!changed()) { mc.displayGuiScreen(null); return; }

        List<Track> remaining = new ArrayList<Track>();
        for (int i = 0; i < tracks.size(); i++) if (keep[i]) remaining.add(tracks.get(i));

        com.questforge.content.net.QFNetwork.toServer(
                new com.questforge.content.net.PacketEditRecord(slotIndex, false, remaining));
        mc.displayGuiScreen(null);
    }

    @Override
    protected void keyTyped(char c, int key) {
        // Escape leaves the record as it was; only Save commits.
        if (key == Keyboard.KEY_ESCAPE) { mc.displayGuiScreen(null); return; }
        if (key == Keyboard.KEY_RETURN) { save(); return; }
        super.keyTyped(c, key);
    }

    @Override
    protected void mouseClicked(int mx, int my, int button) {
        if (mx >= saveX && mx <= saveX + saveW && my >= saveY && my <= saveY + saveH) {
            save();
            return;
        }

        if (my >= listTop && my < listTop + listH
                && mx >= left + PAD && mx <= left + panelW - PAD) {
            int index = (int) ((my - listTop + scroll * ROW_H) / ROW_H);
            if (index < 0 || index >= tracks.size()) return;
            keep[index] = !keep[index];
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
        int max = Math.max(0, tracks.size() - visibleRows);
        if (scrollTarget > max) scrollTarget = max;
        if (scrollTarget < 0) scrollTarget = 0;
    }

    @Override
    public void drawScreen(int mx, int my, float partial) {
        clampScroll();
        scroll += (scrollTarget - scroll) * 0.35f;
        if (Math.abs(scrollTarget - scroll) < 0.01f) scroll = scrollTarget;

        drawDefaultBackground();
        drawRect(left, top, left + panelW, top + panelH, PANEL);
        outline(left, top, left + panelW, top + panelH, PANEL_EDGE);

        fontRendererObj.drawString(EnumChatFormatting.BOLD + label.toUpperCase(),
                                   left + PAD, top + 10, TEXT);

        String tally = kept() + " of " + tracks.size();
        fontRendererObj.drawString(tally,
                left + panelW - PAD - fontRendererObj.getStringWidth(tally), top + 10,
                changed() ? ACCENT : TEXT_FAINT);
        drawRect(left + PAD, top + 24, left + panelW - PAD, top + 25, RULE);

        drawList(mx, my);
        drawFooter(mx, my);

        super.drawScreen(mx, my, partial);
    }

    private void drawList(int mx, int my) {
        if (tracks.isEmpty()) {
            fontRendererObj.drawString("This record is blank.",
                                       left + PAD + 2, listTop + 8, TEXT_FAINT);
            return;
        }

        beginClip(left + PAD, listTop, panelW - PAD * 2, listH);

        int first = (int) Math.floor(scroll);
        int offset = (int) ((scroll - first) * ROW_H);

        for (int i = 0; i <= visibleRows; i++) {
            int index = first + i;
            if (index < 0 || index >= tracks.size()) continue;

            int ry = listTop + i * ROW_H - offset;
            boolean hover = mx >= left + PAD && mx <= left + panelW - PAD
                         && my >= ry && my < ry + ROW_H
                         && my >= listTop && my < listTop + listH;
            if (hover) drawRect(left + PAD, ry, left + panelW - PAD, ry + ROW_H, HOVER);

            Track t = tracks.get(index);
            boolean on = keep[index];

            drawCheck(left + PAD + 4, ry + ROW_H / 2 - 4, on);

            int textX = left + PAD + 18;
            int width = panelW - (textX - left) - 24;
            fontRendererObj.drawString(trim(t.title, width), textX, ry + 2,
                                       on ? TEXT : DANGER);
            fontRendererObj.drawString(trim(t.artistText(), width), textX, ry + 11,
                                       on ? TEXT_DIM : TEXT_FAINT);
        }
        endClip();

        if (tracks.size() > visibleRows) {
            int trackX = left + panelW - PAD + 2;
            int barHeight = Math.max(12, listH * visibleRows / tracks.size());
            int max = tracks.size() - visibleRows;
            int y = listTop + (int) ((listH - barHeight) * (scroll / Math.max(1, max)));

            drawRect(trackX, listTop, trackX + 2, listTop + listH, 0x18FFFFFF);
            drawRect(trackX, y, trackX + 2, y + barHeight, 0x66FFFFFF);
        }
    }

    private void drawCheck(int x, int y, boolean on) {
        outline(x, y, x + 9, y + 9, on ? ACCENT : TEXT_FAINT);
        if (!on) return;
        drawRect(x + 2, y + 4, x + 4, y + 6, ACCENT);
        drawRect(x + 4, y + 3, x + 7, y + 5, ACCENT);
    }

    private void drawFooter(int mx, int my) {
        int y0 = top + panelH - FOOTER_H;
        drawRect(left + PAD, y0, left + panelW - PAD, y0 + 1, RULE);

        int removed = tracks.size() - kept();
        fontRendererObj.drawString(
                removed == 0 ? "untick a song to take it off"
                             : "removing " + removed + (removed == 1 ? " song" : " songs"),
                left + PAD, saveY + 4, removed == 0 ? TEXT_FAINT : DANGER);

        boolean hover = mx >= saveX && mx <= saveX + saveW
                     && my >= saveY && my <= saveY + saveH;

        drawRect(saveX, saveY, saveX + saveW, saveY + saveH,
                 hover ? 0xFF2A3A32 : 0xFF1D2429);
        outline(saveX, saveY, saveX + saveW, saveY + saveH,
                changed() ? (hover ? ACCENT : 0xFF3E4952) : RULE);

        String action = changed() ? "Save changes" : "Done";
        fontRendererObj.drawString(action,
                saveX + (saveW - fontRendererObj.getStringWidth(action)) / 2, saveY + 4,
                hover ? ACCENT : TEXT);
    }

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
