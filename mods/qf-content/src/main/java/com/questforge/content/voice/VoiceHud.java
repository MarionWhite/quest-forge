package com.questforge.content.voice;

import cpw.mods.fml.common.eventhandler.SubscribeEvent;
import cpw.mods.fml.relauncher.Side;
import cpw.mods.fml.relauncher.SideOnly;

import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.FontRenderer;
import net.minecraft.client.gui.ScaledResolution;
import net.minecraftforge.client.event.RenderGameOverlayEvent;

import java.util.List;

/**
 * A small readout of who can hear you and who you can hear.
 *
 * Worth the screen space for one reason: without it there is no way to tell an open
 * microphone from a broken one. A player who cannot see whether they are transmitting
 * has to ask someone else every time, and a hot microphone they have forgotten about
 * is worse than no voice chat at all.
 *
 * Drawn top-left under the Prospector readout rather than centre-screen, and only
 * when something is actually happening.
 */
@SideOnly(Side.CLIENT)
public class VoiceHud {

    private static final int X = 4;
    private static final int Y = 4;

    @SubscribeEvent
    public void onOverlay(RenderGameOverlayEvent.Post event) {
        if (event.type != RenderGameOverlayEvent.ElementType.TEXT) return;
        if (!VoiceSettings.isEnabled()) return;

        Minecraft game = Minecraft.getMinecraft();
        if (game.thePlayer == null) return;
        if (game.gameSettings.showDebugInfo) return;      // F3 has the screen

        FontRenderer font = game.fontRenderer;
        if (font == null) return;

        // Anchored bottom-left: the top of the screen already has Prospector, and a
        // status line that moves depending on what else is showing is hard to glance at.
        ScaledResolution res = new ScaledResolution(
                game, game.displayWidth, game.displayHeight);
        int y = res.getScaledHeight() - 32;

        List<String> talking = VoicePlayback.speaking();
        for (int i = talking.size() - 1; i >= 0; i--) {
            // Plain ASCII: Minecraft's 1.7.10 font sheet has no glyph for most of
            // the arrows and bullets that would look better here, and a missing
            // glyph draws as a blank box.
            font.drawStringWithShadow("§7> §f" + talking.get(i), X, y, 0xFFFFFF);
            y -= 10;
        }

        String mic = micLine();
        if (mic != null) font.drawStringWithShadow(mic, X, y, 0xFFFFFF);
    }

    /**
     * The microphone's own state, or null when there is nothing worth saying.
     *
     * Push-to-talk stays silent while idle on purpose -- the key not being held is
     * the normal case and does not need announcing. Open mic always shows something,
     * because "my microphone is live and I forgot" is the failure this exists to
     * prevent.
     */
    private static String micLine() {
        if (VoiceSettings.isDeafened()) return "§c[x] deafened";
        if (VoiceSettings.isMuted())    return "§c[x] mic muted";

        if (VoiceClient.isTransmitting()) {
            return "§a[*] speaking";
        }
        if (VoiceSettings.mode() == VoiceSettings.Mode.OPEN_MIC) {
            return "§8[ ] open mic";
        }
        return null;
    }
}
