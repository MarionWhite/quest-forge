package com.questforge.content.jukebox;

import net.minecraft.client.gui.inventory.GuiInventory;
import net.minecraft.client.renderer.RenderHelper;
import net.minecraft.entity.player.EntityPlayer;
import net.minecraft.inventory.Slot;
import net.minecraft.item.ItemStack;
import org.lwjgl.input.Keyboard;
import org.lwjgl.input.Mouse;
import org.lwjgl.opengl.GL11;

import java.util.ArrayList;
import java.util.List;

/**
 * The inventory screen, with a right-click menu on records.
 *
 * This is the inventory rather than an overlay on it because Forge 10.13 has no
 * event for mouse input inside a GUI -- only for drawing. Substituting the screen
 * is the one hook that reaches the click, and as a subclass it also gets at the
 * layout fields it needs to know which slot the cursor is over, with no reflection
 * into names that change between the workspace and the built jar.
 *
 * The menu stays up until something is chosen or the next click lands elsewhere. A
 * record holds a whole playlist, and a tooltip long enough to show one would cover
 * the screen, so the songs live here instead.
 */
public class GuiInventoryRecords extends GuiInventory {

    private static final int PANEL     = 0xF81A2027;
    private static final int EDGE      = 0xFF3E4952;
    private static final int ACCENT    = 0xFFE0A34A;
    private static final int ACCENT_BG = 0x33E0A34A;
    private static final int TEXT      = 0xFFE8ECF0;
    private static final int SUBTLE    = 0xFF8A96A2;
    private static final int DANGER    = 0xFFB87878;
    private static final int DANGER_HI = 0xFFE08A8A;

    private static final int ROW_H = 12;

    private static final String VIEW = "View songs";
    private static final String ERASE = "Erase record";

    private boolean open;
    private int slotIndex = -1;
    private String title = "";
    private final List<String> items = new ArrayList<String>();
    private int menuX, menuY, menuW, menuH;

    public GuiInventoryRecords(EntityPlayer player) { super(player); }

    // ------------------------------------------------------------------
    // Input
    // ------------------------------------------------------------------

    @Override
    protected void mouseClicked(int mx, int my, int button) {
        if (open) {
            // Modal while it is up: the click that dismisses it must not also land
            // on whatever is underneath.
            int hit = hit(mx, my);
            if (hit >= 0) run(items.get(hit));
            close();
            return;
        }
        super.mouseClicked(mx, my, button);
    }

    @Override
    protected void mouseMovedOrUp(int mx, int my, int state) {
        // Swallow the release that belongs to the click which opened the menu, so
        // the inventory does not pick up a drag we never started.
        if (open) return;
        super.mouseMovedOrUp(mx, my, state);
    }

    @Override
    protected void keyTyped(char c, int key) {
        if (open) {
            // The same key closes it again, so it toggles rather than trapping you.
            if (key == Keyboard.KEY_ESCAPE || key == RecordKeys.keyCode()) {
                close();
                return;
            }
            super.keyTyped(c, key);
            return;
        }

        if (key == RecordKeys.keyCode()) {
            int mx = mouseX(), my = mouseY();
            Slot slot = slotAt(mx, my);
            if (slot != null && slot.getHasStack()) {
                ItemStack stack = slot.getStack();
                if (stack.getItem() == com.questforge.content.ModItems.record
                        && ItemVinyl.isWritten(stack)
                        && slot.inventory == mc.thePlayer.inventory) {
                    openFor(slot, stack, mx, my);
                    return;
                }
            }
        }
        super.keyTyped(c, key);
    }

    // The key arrives without a cursor position, so it is read straight from the
    // mouse and put into the same scaled coordinates the slots are laid out in.

    private int mouseX() {
        return Mouse.getX() * width / mc.displayWidth;
    }

    private int mouseY() {
        return height - Mouse.getY() * height / mc.displayHeight - 1;
    }

    /**
     * The slot under the cursor, found the way GuiContainer finds it. Its own
     * version is private, but the layout fields it uses are not.
     */
    private Slot slotAt(int mx, int my) {
        List<?> slots = inventorySlots.inventorySlots;
        for (int i = 0; i < slots.size(); i++) {
            Slot slot = (Slot) slots.get(i);
            int sx = guiLeft + slot.xDisplayPosition;
            int sy = guiTop + slot.yDisplayPosition;
            if (mx >= sx - 1 && mx < sx + 17 && my >= sy - 1 && my < sy + 17) return slot;
        }
        return null;
    }

    private void openFor(Slot slot, ItemStack stack, int mx, int my) {
        open = true;
        slotIndex = slot.getSlotIndex();

        String label = ItemVinyl.name(stack);
        int n = ItemVinyl.trackCount(stack);
        title = (label.isEmpty() ? "Record" : label) + "  ·  " + n
                + (n == 1 ? " song" : " songs");

        items.clear();
        items.add(VIEW);
        items.add(ERASE);

        menuW = fontRendererObj.getStringWidth(title) + 14;
        for (int i = 0; i < items.size(); i++) {
            menuW = Math.max(menuW, fontRendererObj.getStringWidth(items.get(i)) + 20);
        }
        menuH = ROW_H + 3 + items.size() * ROW_H + 4;

        menuX = Math.max(2, Math.min(mx + 2, width - menuW - 2));
        menuY = Math.max(2, Math.min(my + 2, height - menuH - 2));
    }

    private void close() {
        open = false;
        slotIndex = -1;
        items.clear();
    }

    private int hit(int mx, int my) {
        if (mx < menuX || mx > menuX + menuW) return -1;
        int top = menuY + ROW_H + 3;
        int index = (my - top) / ROW_H;
        return index >= 0 && index < items.size() ? index : -1;
    }

    private ItemStack record() {
        if (slotIndex < 0) return null;
        try {
            ItemStack stack = mc.thePlayer.inventory.getStackInSlot(slotIndex);
            return stack != null && stack.getItem() == com.questforge.content.ModItems.record
                    ? stack : null;
        } catch (Throwable t) {
            return null;
        }
    }

    private void run(String action) {
        ItemStack stack = record();
        if (stack == null) return;

        if (action.equals(ERASE)) {
            com.questforge.content.net.QFNetwork.toServer(
                    new com.questforge.content.net.PacketEditRecord(slotIndex, true, null));
        } else if (action.equals(VIEW)) {
            mc.displayGuiScreen(new GuiRecordSongs(slotIndex, ItemVinyl.name(stack),
                                                   ItemVinyl.tracks(stack)));
        }
    }

    // ------------------------------------------------------------------
    // Drawing
    // ------------------------------------------------------------------

    @Override
    public void drawScreen(int mx, int my, float partial) {
        super.drawScreen(mx, my, partial);
        if (!open) return;
        if (record() == null) { close(); return; }

        // Drawn after the inventory's own tooltips, and above them, so the menu is
        // never half-covered by a label for the item it is about.
        RenderHelper.disableStandardItemLighting();
        GL11.glDisable(GL11.GL_LIGHTING);
        GL11.glDisable(GL11.GL_DEPTH_TEST);
        zLevel = 500F;

        drawRect(menuX, menuY, menuX + menuW, menuY + menuH, PANEL);
        drawRect(menuX, menuY, menuX + menuW, menuY + 1, EDGE);
        drawRect(menuX, menuY + menuH - 1, menuX + menuW, menuY + menuH, EDGE);
        drawRect(menuX, menuY, menuX + 1, menuY + menuH, EDGE);
        drawRect(menuX + menuW - 1, menuY, menuX + menuW, menuY + menuH, EDGE);

        fontRendererObj.drawString(title, menuX + 6, menuY + 4, SUBTLE);
        drawRect(menuX + 4, menuY + ROW_H + 1, menuX + menuW - 4, menuY + ROW_H + 2, EDGE);

        int hovered = hit(mx, my);
        for (int i = 0; i < items.size(); i++) {
            int ry = menuY + ROW_H + 3 + i * ROW_H;
            boolean on = i == hovered;
            if (on) drawRect(menuX + 1, ry, menuX + menuW - 1, ry + ROW_H, ACCENT_BG);

            boolean destructive = items.get(i).equals(ERASE);
            int color = destructive ? (on ? DANGER_HI : DANGER) : (on ? ACCENT : TEXT);
            fontRendererObj.drawString(items.get(i), menuX + 8, ry + 2, color);
        }

        zLevel = 0F;
        GL11.glEnable(GL11.GL_DEPTH_TEST);
        GL11.glEnable(GL11.GL_LIGHTING);
    }
}
