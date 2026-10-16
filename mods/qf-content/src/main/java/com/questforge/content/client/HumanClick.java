package com.questforge.content.client;

import org.lwjgl.input.Mouse;

import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.inventory.GuiContainer;
import net.minecraft.inventory.Container;
import net.minecraft.inventory.Slot;

import cpw.mods.fml.relauncher.ReflectionHelper;

/**
 * Whether a slot click on this client came from the person at the keyboard.
 *
 * Client-only -- it touches LWJGL and the open screen -- and reached through
 * ClientProxy so a dedicated server never loads it.
 *
 * Two conditions, both of which an automated click fails:
 *
 *  - the left mouse button is physically down. A sort triggered by a key, a GUI
 *    button release or a middle-click has no left button held;
 *  - the clicked slot is the one under the mouse. InventoryTweaks walks through
 *    slots the cursor is nowhere near.
 *
 * Either one alone has a hole; together they describe a hand on a mouse.
 */
public final class HumanClick {

    private HumanClick() {}

    public static boolean isDeliberate(Container container, int slotId) {
        try {
            if (!Mouse.isButtonDown(0)) return false;

            Minecraft mc = Minecraft.getMinecraft();
            if (!(mc.currentScreen instanceof GuiContainer)) return false;
            GuiContainer gui = (GuiContainer) mc.currentScreen;
            if (gui.inventorySlots != container) return false;

            // GuiContainer.theSlot: the slot the mouse is hovering, as the screen
            // itself computed it for this frame.
            Slot hovered = ReflectionHelper.getPrivateValue(
                    GuiContainer.class, gui, "theSlot", "field_147006_u");
            return hovered != null && hovered.slotNumber == slotId;
        } catch (Throwable t) {
            // Unknown means no: the cost is that one application falls back to a
            // plain item swap, which the player can simply repeat.
            return false;
        }
    }
}
