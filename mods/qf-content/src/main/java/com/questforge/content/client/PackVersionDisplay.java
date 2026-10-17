package com.questforge.content.client;

import java.lang.reflect.Field;

import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.FontRenderer;
import net.minecraft.client.gui.GuiDisconnected;
import net.minecraft.client.gui.GuiMainMenu;
import net.minecraft.util.IChatComponent;
import net.minecraftforge.client.event.GuiOpenEvent;
import net.minecraftforge.client.event.GuiScreenEvent;
import net.minecraftforge.client.event.RenderGameOverlayEvent;

import cpw.mods.fml.common.eventhandler.SubscribeEvent;
import cpw.mods.fml.relauncher.Side;
import cpw.mods.fml.relauncher.SideOnly;

import com.questforge.content.QuestForgeContent;
import com.questforge.content.pack.PackCheck;

/**
 * Says which pack this client runs: one small line in the main menu's top-right
 * corner, and one on the F3 screen. It is what a refused player reads out to the
 * host, and what the host compares with {@code /qfpack}.
 *
 * Also writes the text of any disconnect screen to the log, since a refusal
 * otherwise exists only on screen and "send me latest.log" is how friends report
 * problems.
 */
@SideOnly(Side.CLIENT)
public class PackVersionDisplay {

    static String line() {
        return "Quest Forge pack " + displayDate() + " - " + PackCheck.fingerprint();
    }

    private static String displayDate() {
        String d = PackCheck.packDate();
        return (d == null || d.isEmpty()) ? "(undated)" : d;
    }

    /** CustomMenu's screen extends GuiMainMenu, so this covers the branded menu too. */
    @SubscribeEvent
    public void onDrawScreen(GuiScreenEvent.DrawScreenEvent.Post event) {
        if (!(event.gui instanceof GuiMainMenu)) return;
        FontRenderer font = Minecraft.getMinecraft().fontRenderer;
        String text = line();
        font.drawStringWithShadow(text, event.gui.width - font.getStringWidth(text) - 2, 2, 0x9a9a9a);
    }

    @SubscribeEvent
    public void onDebugText(RenderGameOverlayEvent.Text event) {
        if (!Minecraft.getMinecraft().gameSettings.showDebugInfo) return;
        event.left.add("");
        event.left.add(line());
    }

    @SubscribeEvent
    public void onGuiOpen(GuiOpenEvent event) {
        if (!(event.gui instanceof GuiDisconnected)) return;
        try {
            for (Field f : GuiDisconnected.class.getDeclaredFields()) {
                if (!IChatComponent.class.isAssignableFrom(f.getType())) continue;
                f.setAccessible(true);
                Object v = f.get(event.gui);
                if (v != null) {
                    QuestForgeContent.log.info("[packcheck] disconnect screen: "
                            + ((IChatComponent) v).getUnformattedText().replace("\n", " | "));
                }
            }
        } catch (Throwable t) {
            // Diagnostics only.
        }
    }
}
