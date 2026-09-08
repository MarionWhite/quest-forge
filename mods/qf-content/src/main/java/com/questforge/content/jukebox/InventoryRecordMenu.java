package com.questforge.content.jukebox;

import cpw.mods.fml.common.eventhandler.SubscribeEvent;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.inventory.GuiInventory;
import net.minecraftforge.client.event.GuiOpenEvent;

/**
 * Puts {@link GuiInventoryRecords} in place of the ordinary inventory screen.
 *
 * Only when the screen is exactly vanilla's. Another mod that has already
 * substituted its own inventory is left alone -- taking it over would silently
 * undo whatever that mod adds, to add a menu that only matters when a record is
 * being held.
 */
public class InventoryRecordMenu {

    @SubscribeEvent
    public void onGuiOpen(GuiOpenEvent event) {
        if (event.gui == null) return;
        if (event.gui.getClass() != GuiInventory.class) return;

        Minecraft mc = Minecraft.getMinecraft();
        if (mc.thePlayer == null) return;

        event.gui = new GuiInventoryRecords(mc.thePlayer);
    }
}
