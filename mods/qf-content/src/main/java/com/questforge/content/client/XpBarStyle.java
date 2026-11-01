package com.questforge.content.client;

import java.io.InputStream;
import java.util.Properties;

import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.FontRenderer;
import net.minecraft.client.gui.Gui;
import net.minecraft.client.resources.IResourceManager;
import net.minecraft.client.resources.IResourceManagerReloadListener;
import net.minecraft.entity.boss.BossStatus;
import net.minecraft.util.EnumChatFormatting;
import net.minecraft.util.ResourceLocation;
import net.minecraftforge.client.event.RenderGameOverlayEvent;

import org.lwjgl.opengl.GL11;

import cpw.mods.fml.common.eventhandler.SubscribeEvent;

/**
 * The XP level number in the resource pack's colours. Vanilla draws it in a fixed lime (0x80FF20) that no texture can
 * change, and MCPatcher's {@code text.xpbar} (Custom Colors) does not reach it in this pack: Angelica applies text
 * colours only through its extended-HD font mixin, which it skips when CoFHCore is loaded.
 *
 * <p>Reads the same key a pack author already knows, from {@code assets/minecraft/mcpatcher/color.properties}:
 * <pre>
 *   text.xpbar=E8C98A           the number's colour (hex RGB)
 *   qf.xpbar.outline=1A120A     the four-way outline under it (default black, as vanilla)
 *   qf.xpbar.plate=0,100,24,11  optional: a sprite from gui/icons.png (u,v,w,h) drawn centred behind the number
 *   text.boss=F4E8CC            the boss name's colour (vanilla white)
 *   qf.boss.outline=120C06      an eight-way outline round the boss name, so it reads over a bright sky
 *   qf.boss.frame=0,120,200,15  optional: a sprite from gui/icons.png drawn centred on the boss bar (a frame round it)
 * </pre>
 * With none of these keys in any pack nothing here draws, and the HUD is vanilla. Client only; no server part.
 *
 * <p>It redraws after Forge's own number (RenderGameOverlayEvent.Post, EXPERIENCE), at the same position with the same
 * font, so every lime glyph pixel is covered; a plate is drawn first and the outline and number again over it.
 */
public class XpBarStyle implements IResourceManagerReloadListener {

    private static final ResourceLocation PROPS = new ResourceLocation("minecraft", "mcpatcher/color.properties");
    private static final ResourceLocation ICONS = Gui.icons;

    private int color = -1;
    private int outline = 0;
    private int[] plate;
    private int bossColor = -1;
    private int bossOutline = -1;
    private int[] bossFrame;
    private boolean bossDrawn;

    @Override
    public void onResourceManagerReload(IResourceManager rm) {
        color = -1;
        outline = 0;
        plate = null;
        bossColor = -1;
        bossOutline = -1;
        bossFrame = null;
        try (InputStream in = rm.getResource(PROPS).getInputStream()) {
            Properties p = new Properties();
            p.load(in);
            color = hex(p.getProperty("text.xpbar"), -1);
            outline = hex(p.getProperty("qf.xpbar.outline"), 0);
            String s = p.getProperty("qf.xpbar.plate");
            if (s != null) {
                String[] f = s.trim().split("\\s*,\\s*");
                if (f.length == 4) {
                    plate = new int[4];
                    for (int i = 0; i < 4; i++) plate[i] = Integer.parseInt(f[i]);
                }
            }
        } catch (Exception e) {
            // no pack sets it (the normal case) or it is malformed: vanilla
            color = -1;
            plate = null;
        }
    }

    private static int hex(String s, int dflt) {
        if (s == null) return dflt;
        s = s.trim();
        if (s.startsWith("#")) s = s.substring(1);
        return s.isEmpty() ? dflt : Integer.parseInt(s, 16) & 0xFFFFFF;
    }

    @SubscribeEvent
    public void pre(RenderGameOverlayEvent.Pre e) {
        // vanilla counts statusBarTime down while it draws, so decide here whether it draws this frame
        if (e.type == RenderGameOverlayEvent.ElementType.BOSSHEALTH)
            bossDrawn = BossStatus.bossName != null && BossStatus.statusBarTime > 0;
    }

    @SubscribeEvent
    public void post(RenderGameOverlayEvent.Post e) {
        if (e.type == RenderGameOverlayEvent.ElementType.BOSSHEALTH) {
            boss(e);
            return;
        }
        if (e.type != RenderGameOverlayEvent.ElementType.EXPERIENCE || color < 0) return;
        Minecraft mc = Minecraft.getMinecraft();
        if (mc.thePlayer == null || mc.playerController == null || mc.ingameGUI == null
                || !mc.playerController.gameIsSurvivalOrAdventure() || mc.thePlayer.experienceLevel <= 0) return;
        FontRenderer fr = mc.fontRenderer;
        String t = String.valueOf(mc.thePlayer.experienceLevel);
        int w = e.resolution.getScaledWidth();
        int h = e.resolution.getScaledHeight();
        int x = (w - fr.getStringWidth(t)) / 2;     // GuiIngameForge.renderExperience's own placement
        int y = h - 31 - 4;
        if (plate != null) {
            mc.getTextureManager().bindTexture(ICONS);
            GL11.glColor4f(1F, 1F, 1F, 1F);
            GL11.glEnable(GL11.GL_BLEND);
            GL11.glBlendFunc(GL11.GL_SRC_ALPHA, GL11.GL_ONE_MINUS_SRC_ALPHA);
            mc.ingameGUI.drawTexturedModalRect(w / 2 - plate[2] / 2, y + 4 - plate[3] / 2, plate[0], plate[1], plate[2], plate[3]);
        }
        fr.drawString(t, x + 1, y, outline);
        fr.drawString(t, x - 1, y, outline);
        fr.drawString(t, x, y + 1, outline);
        fr.drawString(t, x, y - 1, outline);
        fr.drawString(t, x, y, color);
        GL11.glColor4f(1F, 1F, 1F, 1F);
        mc.getTextureManager().bindTexture(ICONS);
    }

    /**
     * Over vanilla's boss bar (GuiIngame.renderBossHealth: a 182 x 5 bar at y 12, the name centred at y 2 in white with
     * a shadow): the pack's frame sprite centred on the bar, then the name again in the pack's colour inside a dark
     * eight-way outline, which covers vanilla's white glyphs and their shadow.
     */
    private void boss(RenderGameOverlayEvent.Post e) {
        if (!bossDrawn || (bossOutline < 0 && bossColor < 0 && bossFrame == null)) return;
        String name = BossStatus.bossName;
        if (name == null) return;
        Minecraft mc = Minecraft.getMinecraft();
        FontRenderer fr = mc.fontRenderer;
        int w = e.resolution.getScaledWidth();
        if (bossFrame != null) {
            mc.getTextureManager().bindTexture(ICONS);
            GL11.glColor4f(1F, 1F, 1F, 1F);
            GL11.glEnable(GL11.GL_BLEND);
            GL11.glBlendFunc(GL11.GL_SRC_ALPHA, GL11.GL_ONE_MINUS_SRC_ALPHA);
            mc.ingameGUI.drawTexturedModalRect(w / 2 - bossFrame[2] / 2, 12 + (5 - bossFrame[3]) / 2,
                    bossFrame[0], bossFrame[1], bossFrame[2], bossFrame[3]);
        }
        String bare = EnumChatFormatting.getTextWithoutFormattingCodes(name);
        int x = w / 2 - fr.getStringWidth(name) / 2;
        int y = 2;
        if (bossOutline >= 0) {
            for (int dy = -1; dy <= 1; dy++)
                for (int dx = -1; dx <= 1; dx++)
                    if (dx != 0 || dy != 0) fr.drawString(bare, x + dx, y + dy, bossOutline);
        }
        fr.drawString(bossColor >= 0 ? bare : name, x, y, bossColor >= 0 ? bossColor : 0xFFFFFF);
        GL11.glColor4f(1F, 1F, 1F, 1F);
        mc.getTextureManager().bindTexture(ICONS);
    }
}
