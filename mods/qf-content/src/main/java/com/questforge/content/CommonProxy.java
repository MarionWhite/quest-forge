package com.questforge.content;

import cpw.mods.fml.common.event.FMLInitializationEvent;
import cpw.mods.fml.common.event.FMLPostInitializationEvent;
import cpw.mods.fml.common.event.FMLPreInitializationEvent;

/** Runs on both the client and the dedicated server. */
public class CommonProxy {

    public void preInit(FMLPreInitializationEvent event) {}

    public void init(FMLInitializationEvent event) {
        // Drains work queued by packet handlers onto the server thread.
        cpw.mods.fml.common.FMLCommonHandler.instance().bus().register(
                new com.questforge.content.net.ServerTasks());

        // Releases a player's voice send budget when they disconnect.
        cpw.mods.fml.common.FMLCommonHandler.instance().bus().register(
                new com.questforge.content.voice.VoiceServer.Lifecycle());

        // Drives the pack census, which spawns entities a few at a time against a
        // tick budget rather than all at once.
        cpw.mods.fml.common.FMLCommonHandler.instance().bus().register(
                new com.questforge.content.census.CensusTicker());
    }

    public void postInit(FMLPostInitializationEvent event) {}

    /**
     * Opens the jukebox screen. A no-op here on purpose: the GUI is a client-only
     * class, so a dedicated server must never load it. ClientProxy overrides this.
     */
    public void openJukeboxGui(double x, double y, double z) {}

    /** Opens the record cutter. Client-only for the same reason. */
    public void openRecorderGui() {}
}
