package com.questforge.content.client;

import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.GuiDownloadTerrain;
import net.minecraft.client.network.NetHandlerPlayClient;
import net.minecraft.util.ResourceLocation;
import net.minecraftforge.client.event.GuiOpenEvent;

import cpw.mods.fml.common.eventhandler.SubscribeEvent;
import cpw.mods.fml.relauncher.Side;
import cpw.mods.fml.relauncher.SideOnly;

/**
 * Swaps the terrain-download screen for one showing the destination.
 *
 * The client opens GuiDownloadTerrain on join and on every dimension change,
 * and by then the player entity already carries the dimension it is going TO --
 * the respawn packet sets it before the screen appears -- so the plate can be
 * chosen at the moment the screen opens rather than guessed at afterwards.
 *
 * A dimension with no plate is left alone and gets the vanilla screen. That is
 * the overworld every time, and any dimension a future mod adds.
 */
@SideOnly(Side.CLIENT)
public class LoadingPlateHandler {

    @SubscribeEvent
    public void onGuiOpen(GuiOpenEvent event) {
        if (!(event.gui instanceof GuiDownloadTerrain) || event.gui instanceof GuiLoadingPlate) {
            return;
        }

        Minecraft mc = Minecraft.getMinecraft();

        if (mc.thePlayer == null) {
            return;
        }

        int dimension = mc.thePlayer.dimension;
        ResourceLocation plate = LoadingPlates.texture(dimension);

        if (plate == null) {
            return;
        }

        NetHandlerPlayClient handler = mc.getNetHandler();

        if (handler == null) {
            return;
        }

        // Never let artwork stop a dimension change. If anything here throws, the
        // vanilla screen is already in event.gui and the journey continues.
        try {
            event.gui = new GuiLoadingPlate(handler, plate, LoadingPlates.name(dimension));
        } catch (Throwable t) {
            System.out.println("[QuestForgeContent] loading plate for dim " + dimension
                    + " failed, using the vanilla screen: " + t);
        }
    }
}
