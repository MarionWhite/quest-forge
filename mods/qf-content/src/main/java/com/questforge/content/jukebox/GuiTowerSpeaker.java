package com.questforge.content.jukebox;

import cpw.mods.fml.relauncher.Side;
import cpw.mods.fml.relauncher.SideOnly;

import net.minecraft.client.gui.GuiScreen;
import net.minecraft.client.gui.GuiTextField;
import net.minecraft.util.EnumChatFormatting;

import org.lwjgl.input.Keyboard;

/**
 * The screen on a tower speaker.
 *
 * It has two faces, because a speaker has two lives. Unpaired, the only thing worth
 * showing is its code and a way to get that code to a jukebox -- everything else is
 * settings for a thing that is not doing anything yet. Paired, the code stops
 * mattering and what you want is the tuning: how far it carries, how loud, how it is
 * voiced, and how to let it go.
 */
@SideOnly(Side.CLIENT)
public class GuiTowerSpeaker extends GuiScreen {

    private static final int ACCENT      = 0xFFE0A34A;
    private static final int PANEL       = 0xF2101418;
    private static final int PANEL_EDGE  = 0xFF2B3238;
    private static final int FIELD       = 0xFF171C21;
    private static final int RULE        = 0xFF232A30;
    private static final int TEXT        = 0xFFE8ECF0;
    private static final int TEXT_DIM    = 0xFF8A96A2;
    private static final int TEXT_FAINT  = 0xFF5A6672;
    private static final int GOOD        = 0xFF8FD08A;
    private static final int BAD         = 0xFFD08A8A;

    private static final int PAD = 14;

    private final int bx, by, bz;
    private SpeakerRegistry.Entry entry;

    /** Where closing goes back to, when this was opened from a device list. */
    private final net.minecraft.client.gui.GuiScreen back;

    /** The range menu, open or shut. */
    private boolean rangeOpen;
    private static final int RANGE_MENU_W = 112;
    private static final int RANGE_ROW_H = 12;

    private GuiTextField nameField;

    private int left, top, panelW, panelH;

    private int backX, backY, backW, backH;
    private int copyX, copyY, copyW, copyH;
    private int rangeX, rangeY, rangeW, rangeH;
    private int unpairX, unpairY, unpairW, unpairH;

    /** Slider tracks: volume, bass, treble. */
    private final int[] slX = new int[3], slY = new int[3], slW = new int[3];
    private static final int SLIDER_H = 10;
    private int dragging = -1;

    private String note = "";
    private long noteAt;

    public GuiTowerSpeaker(int x, int y, int z, SpeakerRegistry.Entry entry) {
        this(x, y, z, entry, null);
    }

    public GuiTowerSpeaker(int x, int y, int z, SpeakerRegistry.Entry entry,
                           net.minecraft.client.gui.GuiScreen back) {
        this.bx = x; this.by = y; this.bz = z;
        this.entry = entry;
        this.back = back;
    }

    private boolean paired() { return entry != null && !entry.pairedTo.isEmpty(); }

    @Override public boolean doesGuiPauseGame() { return false; }

    // ------------------------------------------------------------------

    @Override
    public void initGui() {
        Keyboard.enableRepeatEvents(true);

        panelW = Math.min(width - 40, 300);
        panelH = paired() ? 210 : 128;
        left = (width - panelW) / 2;
        top = (height - panelH) / 2;

        nameField = new GuiTextField(fontRendererObj,
                left + PAD + 2, top + 44, panelW - PAD * 2 - 4, 14);
        nameField.setMaxStringLength(
                com.questforge.content.net.SpeakerCodec.MAX_NAME);
        nameField.setText(entry == null ? "Speaker" : entry.name);
        nameField.setEnableBackgroundDrawing(false);

        layout();
    }

    private void layout() {
        backW = 13; backH = 13;
        backX = left + PAD; backY = top + 7;

        int row = top + 78;

        copyW = 46; copyH = 14;
        copyX = left + panelW - PAD - copyW;
        copyY = row;

        row += 30;
        if (paired()) {
            rangeW = 92; rangeH = 14;
            rangeX = left + panelW - PAD - rangeW;
            rangeY = row;
            row += 22;

            for (int i = 0; i < 3; i++) {
                slX[i] = left + PAD + 54;
                slY[i] = row + i * 18;
                slW[i] = panelW - PAD * 2 - 54 - 34;
            }
            row += 3 * 18 + 6;

            unpairW = 74; unpairH = 15;
            unpairX = left + panelW - PAD - unpairW;
            unpairY = row;
        }
    }

    /** Rebuilds when the server tells us the speaker's state changed. */
    public void refresh(SpeakerRegistry.Entry e) {
        if (e == null || entry == null || !e.code.equals(entry.code)) return;
        boolean was = paired();
        entry = e;
        if (was != paired()) initGui();
        else layout();
    }

    // ------------------------------------------------------------------

    @Override
    public void drawScreen(int mx, int my, float partial) {
        drawDefaultBackground();
        drawRect(left, top, left + panelW, top + panelH, PANEL);
        outline(left, top, left + panelW, top + panelH, PANEL_EDGE);

        int titleX = left + PAD;
        if (back != null) {
            // Only drawn when there is somewhere to go. A back arrow on a screen you
            // reached by walking up to the speaker would point nowhere.
            boolean overBack = hit(mx, my, backX, backY, backW, backH);
            drawRect(backX, backY, backX + backW, backY + backH,
                     overBack ? 0xFF2A343D : FIELD);
            outline(backX, backY, backX + backW, backY + backH,
                    overBack ? 0xFF3E4952 : RULE);

            // Drawn as a triangle rather than written: the arrow characters are not
            // in the game's font and would come out blank.
            int ax = backX + 4, ay = backY + 6;
            int tint = overBack ? TEXT : TEXT_DIM;
            for (int i = 0; i < 4; i++) {
                drawRect(ax + i, ay - i, ax + i + 1, ay + i + 1, tint);
            }
            titleX = backX + backW + 6;
        }

        fontRendererObj.drawString(EnumChatFormatting.BOLD + "SPEAKER",
                                   titleX, top + 10, TEXT);

        String state = paired() ? "CONNECTED" : "NOT CONNECTED";
        int w = fontRendererObj.getStringWidth(state);
        fontRendererObj.drawString(state, left + panelW - PAD - w, top + 10,
                                   paired() ? GOOD : TEXT_FAINT);

        drawRect(left + PAD, top + 24, left + panelW - PAD, top + 25, RULE);

        // Name
        fontRendererObj.drawString("Name", left + PAD, top + 32, TEXT_FAINT);
        drawRect(left + PAD, top + 41, left + panelW - PAD, top + 41 + 18, FIELD);
        outline(left + PAD, top + 41, left + panelW - PAD, top + 41 + 18,
                nameField.isFocused() ? 0xFF3E4952 : RULE);
        nameField.drawTextBox();

        // Code
        fontRendererObj.drawString("Frequency", left + PAD, top + 68, TEXT_FAINT);
        String code = entry == null ? "--------" : entry.code;
        fontRendererObj.drawString(EnumChatFormatting.BOLD + code,
                                   left + PAD, top + 79, ACCENT);

        boolean overCopy = hit(mx, my, copyX, copyY, copyW, copyH);
        drawRect(copyX, copyY, copyX + copyW, copyY + copyH, overCopy ? 0xFF2A343D : FIELD);
        outline(copyX, copyY, copyX + copyW, copyY + copyH, overCopy ? 0xFF3E4952 : RULE);
        centred("Copy", copyX, copyX + copyW, copyY + 3, TEXT);

        if (!paired()) {
            fontRendererObj.drawSplitString(
                    "Paste this into a jukebox or JBL, under Devices, to connect.",
                    left + PAD, top + 100, panelW - PAD * 2, TEXT_FAINT);
        } else {
            drawTuning(mx, my);
        }

        drawNote();
        drawRangeMenu(mx, my);
        super.drawScreen(mx, my, partial);
    }

    private void drawTuning(int mx, int my) {
        fontRendererObj.drawString("Range", left + PAD, rangeY + 3, TEXT_DIM);

        boolean hot = rangeOpen || hit(mx, my, rangeX, rangeY, rangeW, rangeH);
        drawRect(rangeX, rangeY, rangeX + rangeW, rangeY + rangeH, hot ? 0xFF2A343D : FIELD);
        outline(rangeX, rangeY, rangeX + rangeW, rangeY + rangeH, hot ? 0xFF3E4952 : RULE);

        int r = clampRange(entry.range);
        fontRendererObj.drawString(Devices.RANGE_NAMES[r], rangeX + 6, rangeY + 3,
                                   hot ? TEXT : TEXT_DIM);

        // The same caret the jukebox uses, so the control reads as something that
        // opens rather than a readout that happens to change when poked.
        int cx = rangeX + rangeW - 9, cy = rangeY + 5;
        for (int i = 0; i < 3; i++) {
            drawRect(cx - 2 + i, cy + i, cx + 3 - i, cy + i + 1, hot ? TEXT : TEXT_DIM);
        }

        slider(0, "Volume", entry.volume / DirectAudio.MAX_VOLUME,
               Math.round(entry.volume * 100) + "%");
        slider(1, "Bass", (entry.bass + 12f) / 24f, db(entry.bass));
        slider(2, "Treble", (entry.treble + 12f) / 24f, db(entry.treble));

        boolean overUnpair = hit(mx, my, unpairX, unpairY, unpairW, unpairH);
        drawRect(unpairX, unpairY, unpairX + unpairW, unpairY + unpairH,
                 overUnpair ? 0xFF3A2A2A : FIELD);
        outline(unpairX, unpairY, unpairX + unpairW, unpairY + unpairH,
                overUnpair ? BAD : RULE);
        centred("Disconnect", unpairX, unpairX + unpairW, unpairY + 4,
                overUnpair ? BAD : TEXT_DIM);
    }

    /**
     * The range list.
     *
     * It drops downward rather than up, unlike the jukebox's. The jukebox's control
     * sits near the bottom of its panel and has nowhere below to go; this one is high
     * on a taller panel, where opening upward would cover the name field and the code
     * -- the two things you might be reading while you choose.
     */
    private void drawRangeMenu(int mx, int my) {
        if (!rangeOpen) return;

        int x0 = rangeX + rangeW - RANGE_MENU_W;
        int y = rangeMenuY();
        int h = Devices.RANGE_NAMES.length * RANGE_ROW_H + 4;

        drawRect(x0, y, x0 + RANGE_MENU_W, y + h, 0xF81A2027);
        outline(x0, y, x0 + RANGE_MENU_W, y + h, 0xFF3E4952);

        int current = clampRange(entry.range);
        for (int i = 0; i < Devices.RANGE_NAMES.length; i++) {
            int iy = y + 2 + i * RANGE_ROW_H;
            boolean hover = mx >= x0 && mx <= x0 + RANGE_MENU_W
                         && my >= iy && my < iy + RANGE_ROW_H;
            if (hover) drawRect(x0 + 1, iy, x0 + RANGE_MENU_W - 1, iy + RANGE_ROW_H, 0x40E0A34A);

            fontRendererObj.drawString(Devices.RANGE_NAMES[i], x0 + 6, iy + 2,
                    i == current ? ACCENT : hover ? TEXT : TEXT_DIM);

            String blocks = (int) Devices.RANGE_FULL[i] + " blocks";
            fontRendererObj.drawString(blocks,
                    x0 + RANGE_MENU_W - 6 - fontRendererObj.getStringWidth(blocks),
                    iy + 2, i == current ? ACCENT : TEXT_FAINT);
        }
    }

    private int rangeMenuY() { return rangeY + rangeH + 2; }

    /** Which entry the mouse is over, or -1. */
    private int rangeMenuHit(int mx, int my) {
        if (!rangeOpen) return -1;
        int x0 = rangeX + rangeW - RANGE_MENU_W;
        if (mx < x0 || mx > x0 + RANGE_MENU_W) return -1;
        int i = (my - rangeMenuY() - 2) / RANGE_ROW_H;
        return i >= 0 && i < Devices.RANGE_NAMES.length ? i : -1;
    }

    private void chooseRange(int index) {
        rangeOpen = false;
        if (index < 0 || index >= Devices.RANGE_NAMES.length) return;
        entry.range = index;
        com.questforge.content.net.PacketSpeakerEdit p =
                new com.questforge.content.net.PacketSpeakerEdit(
                        entry.code, com.questforge.content.net.PacketSpeakerEdit.RANGE);
        p.range = index;
        com.questforge.content.net.QFNetwork.toServer(p);
        say(Devices.RANGE_NAMES[index] + "  ·  full volume within "
                + (int) Devices.RANGE_FULL[index] + " blocks");
    }

    private void slider(int i, String label, float t, String value) {
        fontRendererObj.drawString(label, left + PAD, slY[i] + 1, TEXT_DIM);

        int y = slY[i] + 3;
        drawRect(slX[i], y, slX[i] + slW[i], y + 2, RULE);
        int knob = slX[i] + Math.round(clamp01(t) * slW[i]);
        drawRect(slX[i], y, knob, y + 2, ACCENT);
        drawRect(knob - 2, y - 3, knob + 2, y + 5, ACCENT);

        fontRendererObj.drawString(value, slX[i] + slW[i] + 6, slY[i] + 1, TEXT_FAINT);
    }

    private static String db(float v) {
        int n = Math.round(v);
        return (n > 0 ? "+" : "") + n + "dB";
    }

    private void drawNote() {
        String shown = note;
        if (!shown.isEmpty() && System.currentTimeMillis() - noteAt > 3000L) {
            note = "";
            shown = "";
        }
        String problem = Devices.problem();
        if (!problem.isEmpty()) shown = problem;
        if (shown.isEmpty()) return;
        int w = fontRendererObj.getStringWidth(shown);
        fontRendererObj.drawString(shown, left + (panelW - w) / 2, top + panelH + 6, TEXT_DIM);
    }

    // ------------------------------------------------------------------

    @Override
    protected void mouseClicked(int mx, int my, int button) {
        // While the menu is open it takes the click, whatever it lands on: picking
        // an entry, or anywhere else to dismiss it. Letting a click fall through to
        // whatever the menu was covering would act on a control the player could
        // not see.
        if (rangeOpen) {
            int pick = rangeMenuHit(mx, my);
            if (pick >= 0) chooseRange(pick);
            else rangeOpen = false;
            return;
        }

        super.mouseClicked(mx, my, button);
        nameField.mouseClicked(mx, my, button);

        if (back != null && hit(mx, my, backX, backY, backW, backH)) {
            goBack();
            return;
        }

        if (hit(mx, my, copyX, copyY, copyW, copyH)) {
            setClipboardString(entry == null ? "" : entry.code);
            say("Copied");
            return;
        }
        if (!paired()) return;

        if (hit(mx, my, rangeX, rangeY, rangeW, rangeH)) {
            rangeOpen = true;
            return;
        }
        for (int i = 0; i < 3; i++) {
            if (my >= slY[i] - 2 && my <= slY[i] + SLIDER_H
                    && mx >= slX[i] - 3 && mx <= slX[i] + slW[i] + 3) {
                dragging = i;
                dragTo(i, mx);
                return;
            }
        }
        if (hit(mx, my, unpairX, unpairY, unpairW, unpairH)) {
            com.questforge.content.net.QFNetwork.toServer(
                    new com.questforge.content.net.PacketSpeakerEdit(
                            entry.code, com.questforge.content.net.PacketSpeakerEdit.UNPAIR));
            say("Disconnected");
        }
    }

    @Override
    protected void mouseClickMove(int mx, int my, int button, long held) {
        if (dragging >= 0) dragTo(dragging, mx);
    }

    @Override
    protected void mouseMovedOrUp(int mx, int my, int state) {
        super.mouseMovedOrUp(mx, my, state);
        if (state != -1 && dragging >= 0) {
            sendTuning(dragging);
            dragging = -1;
        }
    }

    private void dragTo(int i, int mx) {
        float t = clamp01((mx - slX[i]) / (float) Math.max(1, slW[i]));
        if (i == 0) {
            entry.volume = t * DirectAudio.MAX_VOLUME;
        } else if (i == 1) {
            entry.bass = t * 24f - 12f;
        } else {
            entry.treble = t * 24f - 12f;
        }
        // Locally first, so dragging a slider is heard while it is dragged rather
        // than after the server has agreed with it.
        Devices.update(entry);
    }

    /** Sent on release rather than per pixel: a drag is one decision, not sixty. */
    private void sendTuning(int i) {
        com.questforge.content.net.PacketSpeakerEdit p =
                new com.questforge.content.net.PacketSpeakerEdit(entry.code,
                        i == 0 ? com.questforge.content.net.PacketSpeakerEdit.VOLUME
                               : com.questforge.content.net.PacketSpeakerEdit.TONE);
        p.volume = entry.volume;
        p.bass = entry.bass;
        p.treble = entry.treble;
        com.questforge.content.net.QFNetwork.toServer(p);
    }

    @Override
    protected void keyTyped(char ch, int key) {
        if (rangeOpen && key == Keyboard.KEY_ESCAPE) { rangeOpen = false; return; }
        if (key == Keyboard.KEY_ESCAPE && back != null && !nameField.isFocused()) {
            goBack();
            return;
        }
        if (nameField.isFocused()) {
            if (key == Keyboard.KEY_RETURN || key == Keyboard.KEY_NUMPADENTER) {
                commitName();
                nameField.setFocused(false);
                return;
            }
            if (key == Keyboard.KEY_ESCAPE) {
                nameField.setFocused(false);
                return;
            }
            nameField.textboxKeyTyped(ch, key);
            return;
        }
        super.keyTyped(ch, key);
    }

    private void commitName() {
        if (entry == null) return;
        String name = com.questforge.content.net.SpeakerCodec.cleanName(nameField.getText());
        if (name.equals(entry.name)) return;
        entry.name = name;
        nameField.setText(name);
        com.questforge.content.net.PacketSpeakerEdit p =
                new com.questforge.content.net.PacketSpeakerEdit(
                        entry.code, com.questforge.content.net.PacketSpeakerEdit.RENAME);
        p.name = name;
        com.questforge.content.net.QFNetwork.toServer(p);
        say("Renamed");
    }

    @Override
    public void onGuiClosed() {
        // A name typed and then walked away from is still a name that was typed.
        commitName();
        Keyboard.enableRepeatEvents(false);
    }

    @Override
    public void updateScreen() {
        nameField.updateCursorCounter();
    }

    // ------------------------------------------------------------------

    /**
     * Returns to the list this speaker was opened from.
     *
     * The screen object itself is handed back rather than a fresh one, so the jukebox
     * comes up on the tab and scroll position it was left on -- going to a speaker
     * and back should cost you your place no more than opening a drawer does.
     */
    private void goBack() {
        commitName();
        mc.displayGuiScreen(back);
    }

    private void say(String msg) { note = msg; noteAt = System.currentTimeMillis(); }

    private static int clampRange(int i) {
        return i < 0 ? 0 : i >= Devices.RANGE_NAMES.length ? Devices.RANGE_NAMES.length - 1 : i;
    }

    private static float clamp01(float v) { return v < 0f ? 0f : v > 1f ? 1f : v; }

    private static boolean hit(int mx, int my, int x, int y, int w, int h) {
        return w > 0 && mx >= x && mx <= x + w && my >= y && my <= y + h;
    }

    private void centred(String s, int x0, int x1, int y, int colour) {
        int w = fontRendererObj.getStringWidth(s);
        fontRendererObj.drawString(s, x0 + (x1 - x0 - w) / 2, y, colour);
    }

    private void outline(int x0, int y0, int x1, int y1, int colour) {
        drawRect(x0, y0, x1, y0 + 1, colour);
        drawRect(x0, y1 - 1, x1, y1, colour);
        drawRect(x0, y0, x0 + 1, y1, colour);
        drawRect(x1 - 1, y0, x1, y1, colour);
    }
}
