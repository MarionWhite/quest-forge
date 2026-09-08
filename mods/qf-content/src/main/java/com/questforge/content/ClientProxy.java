package com.questforge.content;

import cpw.mods.fml.common.FMLCommonHandler;
import cpw.mods.fml.common.event.FMLInitializationEvent;
import net.minecraftforge.common.MinecraftForge;

import com.questforge.content.client.QFClientEvents;

/** Client-only setup: renderers, models, key bindings. */
public class ClientProxy extends CommonProxy {

    @Override
    public void init(FMLInitializationEvent event) {
        super.init(event);

        // Rendering and the HUD are on the Forge bus; client ticks are on FML's.
        // One handler object serves both, mirroring EnchantEventBridge.
        QFClientEvents handler = new QFClientEvents();
        MinecraftForge.EVENT_BUS.register(handler);
        FMLCommonHandler.instance().bus().register(handler);

        // Jukebox audio test harness. Client-side only, so it registers through
        // ClientCommandHandler and needs no packets or integrated server.
        net.minecraftforge.client.ClientCommandHandler.instance.registerCommand(
                new com.questforge.content.jukebox.CommandJukebox());

        // Keeps the jukebox's OpenAL stream fed. Not optional: an unfed streaming
        // source underruns and goes silent within a fraction of a second.
        FMLCommonHandler.instance().bus().register(
                new com.questforge.content.jukebox.JukeboxTicker());

        // The right-click menu on a record in the inventory. On the Forge bus
        // rather than the FML one: it listens to GUI events, which are posted
        // there.
        net.minecraftforge.common.MinecraftForge.EVENT_BUS.register(
                new com.questforge.content.jukebox.InventoryRecordMenu());

        // The key that opens a record's menu while the cursor is over it.
        com.questforge.content.jukebox.RecordKeys.register();

        // The JBL on a player's shoulder. It draws off RenderPlayerEvent.Specials,
        // which is the hook capes and armour overlays use, so it inherits the
        // player's transform and needs no entity of its own.
        com.questforge.content.jukebox.RenderSpeaker speaker =
                new com.questforge.content.jukebox.RenderSpeaker();
        MinecraftForge.EVENT_BUS.register(speaker);

        // First person has no biped model to hang it off, and 1.7.10 has no
        // RenderHandEvent, so the same geometry is drawn through an item renderer --
        // the one hook that runs in place of the flat sprite in your hand.
        net.minecraftforge.client.MinecraftForgeClient.registerItemRenderer(
                com.questforge.content.ModItems.speaker,
                new com.questforge.content.jukebox.SpeakerItemRenderer(speaker));

        // Volume and range are restored before anything can play, so the first
        // track of a session is at the level the player left it.
        com.questforge.content.jukebox.JukeboxSettings.load();

        // Proximity voice. The keys register here so they show up in Controls and
        // can be rebound; the microphone itself stays closed until someone first
        // tries to speak, so a player who never uses it never has a live mic.
        com.questforge.content.voice.VoiceKeys.register();
        com.questforge.content.voice.VoiceSettings.load();

        // Capture and playback ride the client tick, alongside the jukebox's.
        FMLCommonHandler.instance().bus().register(
                new com.questforge.content.voice.VoiceClient());
        // The readout goes on the Forge bus, which is where overlay events post.
        MinecraftForge.EVENT_BUS.register(
                new com.questforge.content.voice.VoiceHud());

        net.minecraftforge.client.ClientCommandHandler.instance.registerCommand(
                new com.questforge.content.voice.CommandVoice());
    }

    @Override
    public void postInit(cpw.mods.fml.common.event.FMLPostInitializationEvent event) {
        super.postInit(event);
        // The case is drawn entirely here; its block has no world renderer at all.
        cpw.mods.fml.client.registry.ClientRegistry.bindTileEntitySpecialRenderer(
                com.questforge.content.jukebox.TileEntityRecordCase.class,
                new com.questforge.content.jukebox.RenderRecordCase());

        cpw.mods.fml.client.registry.ClientRegistry.bindTileEntitySpecialRenderer(
                com.questforge.content.jukebox.TileEntityTowerSpeaker.class,
                new com.questforge.content.jukebox.RenderTowerSpeaker());

        // Says in the log which audio formats this build can actually play. The one
        // way this breaks is at packaging time, and it breaks silently.
        com.questforge.content.jukebox.AudioServices.report();
    }

    @Override
    public void openJukeboxGui(double x, double y, double z) {
        // Hands the queue back from whichever speaker was holding it, so a wall
        // jukebox opens on its own list rather than on whatever was in your hand.
        com.questforge.content.jukebox.Speakers.openBlock();
        net.minecraft.client.Minecraft.getMinecraft().displayGuiScreen(
                new com.questforge.content.jukebox.GuiJukebox(x, y, z));
    }

    @Override
    public void openRecorderGui() {
        net.minecraft.client.Minecraft.getMinecraft().displayGuiScreen(
                new com.questforge.content.jukebox.GuiRecorder());
    }
}
