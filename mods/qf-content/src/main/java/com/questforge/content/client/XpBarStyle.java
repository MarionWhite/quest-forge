package com.questforge.content.client;

import java.io.InputStream;
import java.util.Properties;

import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.FontRenderer;
import net.minecraft.client.gui.Gui;
import net.minecraft.client.renderer.Tessellator;
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
 * Bar mode (round 16): with {@code qf.boss.sheet} set, the pack replaces vanilla's 182 x 5 boss bar with its own,
 * drawn from that sheet (u, v, w, h in GUI px of a 256-unit sheet, as icons.png; the image may be 2x):
 * <pre>
 *   qf.boss.sheet=textures/gui/qf_bossbar.png   the sheet (minecraft domain); turns bar mode on
 *   qf.boss.top=11                  the bar's top row on screen (GUI px)
 *   qf.boss.back=u,v,w,h            the bar with its channel empty; centred on the screen
 *   qf.boss.fill=u,v,w,h,dx,dy      the full fill, drawn at back + (dx, dy) and cut to the boss's health (from the left)
 *   qf.boss.tip=u,v,w,h,dy          optional: centred on the fill's leading edge, top at back + dy
 *   qf.boss.over=u,v,w,h            optional: drawn over all of it at the back's corner (rails, emblem, ticks)
 *   qf.boss.pct=RRGGBB,OUTLINE,dx,dy,L|C|R   optional: the health in percent, anchored at back + (dx, dy)
 *   qf.boss.namey=2                 the name's top row (the name keeps text.boss / qf.boss.outline)
 *   qf.boss.fade=20                 optional: ticks to fade in when a bar appears
 * </pre>
 * Vanilla's bar is then cancelled (Pre), so this counts {@code BossStatus.statusBarTime} down the way vanilla does.
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
    // bar mode
    private ResourceLocation sheet;
    private int top = 12, nameY = 2, fadeTicks;
    private int[] back, fill, tip, over;
    private int pctColor = -1, pctOutline = -1, pctDx, pctDy;
    private char pctAlign = 'R';
    private long shownAt = -1;

    @Override
    public void onResourceManagerReload(IResourceManager rm) {
        color = -1;
        outline = 0;
        plate = null;
        bossColor = -1;
        bossOutline = -1;
        bossFrame = null;
        sheet = null;
        back = fill = tip = over = null;
        pctColor = pctOutline = -1;
        try (InputStream in = rm.getResource(PROPS).getInputStream()) {
            Properties p = new Properties();
            p.load(in);
            color = hex(p.getProperty("text.xpbar"), -1);
            outline = hex(p.getProperty("qf.xpbar.outline"), 0);
            plate = rect(p.getProperty("qf.xpbar.plate"));
            bossColor = hex(p.getProperty("text.boss"), -1);
            bossOutline = hex(p.getProperty("qf.boss.outline"), -1);
            bossFrame = rect(p.getProperty("qf.boss.frame"));
            String sh = p.getProperty("qf.boss.sheet");
            if (sh != null && !sh.trim().isEmpty()) {
                back = ints(p.getProperty("qf.boss.back"), 4);
                fill = ints(p.getProperty("qf.boss.fill"), 6);
                if (back != null && fill != null) {
                    sheet = new ResourceLocation("minecraft", sh.trim());
                    tip = ints(p.getProperty("qf.boss.tip"), 5);
                    over = ints(p.getProperty("qf.boss.over"), 4);
                    top = num(p.getProperty("qf.boss.top"), 12);
                    nameY = num(p.getProperty("qf.boss.namey"), 2);
                    fadeTicks = num(p.getProperty("qf.boss.fade"), 0);
                    String pc = p.getProperty("qf.boss.pct");
                    if (pc != null) {
                        String[] f = pc.trim().split("\\s*,\\s*");
                        if (f.length >= 4) {
                            pctColor = hex(f[0], -1);
                            pctOutline = f[1].equalsIgnoreCase("none") ? -1 : hex(f[1], -1);
                            pctDx = Integer.parseInt(f[2]);
                            pctDy = Integer.parseInt(f[3]);
                            pctAlign = f.length > 4 && !f[4].isEmpty() ? Character.toUpperCase(f[4].charAt(0)) : 'R';
                        }
                    }
                }
            }
        } catch (Exception e) {
            // no pack sets it (the normal case) or it is malformed: vanilla
            color = -1;
            plate = null;
            bossColor = -1;
            bossOutline = -1;
            bossFrame = null;
            sheet = null;
            pctColor = -1;
        }
    }

    private static int[] ints(String s, int n) {
        if (s == null) return null;
        String[] f = s.trim().split("\\s*,\\s*");
        if (f.length != n) return null;
        int[] r = new int[n];
        for (int i = 0; i < n; i++) r[i] = Integer.parseInt(f[i]);
        return r;
    }

    private static int num(String s, int dflt) {
        return s == null || s.trim().isEmpty() ? dflt : Integer.parseInt(s.trim());
    }

    private static int[] rect(String s) {
        if (s == null) return null;
        String[] f = s.trim().split("\\s*,\\s*");
        if (f.length != 4) return null;
        int[] r = new int[4];
        for (int i = 0; i < 4; i++) r[i] = Integer.parseInt(f[i]);
        return r;
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
        if (e.type != RenderGameOverlayEvent.ElementType.BOSSHEALTH) return;
        bossDrawn = BossStatus.bossName != null && BossStatus.statusBarTime > 0;
        if (sheet == null) return;
        e.setCanceled(true);                    // ours replaces vanilla's bar, so Post never fires: draw here
        if (!bossDrawn) {
            shownAt = -1;
            return;
        }
        --BossStatus.statusBarTime;             // what vanilla's renderBossHealth does each frame it draws
        bar(e);
    }

    /** Bar mode: back, fill cut to the health, tip, over, percent, then the outlined name. */
    private void bar(RenderGameOverlayEvent.Pre e) {
        Minecraft mc = Minecraft.getMinecraft();
        FontRenderer fr = mc.fontRenderer;
        int w = e.resolution.getScaledWidth();
        long now = Minecraft.getSystemTime();
        if (shownAt < 0) shownAt = now;
        float a = fadeTicks > 0 ? Math.min(1F, (now - shownAt) / (fadeTicks * 50F)) : 1F;
        if (a <= 0.02F) return;
        float hp = Math.max(0F, Math.min(1F, BossStatus.healthScale));
        int x0 = w / 2 - back[2] / 2;
        int y0 = top;
        GL11.glEnable(GL11.GL_BLEND);
        GL11.glBlendFunc(GL11.GL_SRC_ALPHA, GL11.GL_ONE_MINUS_SRC_ALPHA);
        GL11.glColor4f(1F, 1F, 1F, a);
        mc.getTextureManager().bindTexture(sheet);
        quad(x0, y0, back[0], back[1], back[2], back[3]);
        float fw = fill[2] * hp;
        if (fw > 0F) quad(x0 + fill[4], y0 + fill[5], fill[0], fill[1], fw, fill[3]);
        if (tip != null && hp > 0F) {
            float tx = x0 + fill[4] + fw - tip[2] / 2F;
            quad(Math.round(tx), y0 + tip[4], tip[0], tip[1], tip[2], tip[3]);
        }
        if (over != null) quad(x0, y0, over[0], over[1], over[2], over[3]);
        int alpha = Math.max(4, Math.round(a * 255F)) << 24;
        if (pctColor >= 0) {
            String t = (int) Math.ceil(hp * 100F - 0.001F) + "%";
            int tw = fr.getStringWidth(t);
            int tx = x0 + pctDx - (pctAlign == 'R' ? tw : pctAlign == 'C' ? tw / 2 : 0);
            int ty = y0 + pctDy;
            if (pctOutline >= 0) outlined(fr, t, tx, ty, pctOutline | alpha, false);
            fr.drawString(t, tx, ty, pctColor | alpha);
        }
        String name = BossStatus.bossName;
        String bare = EnumChatFormatting.getTextWithoutFormattingCodes(name);
        int nx = w / 2 - fr.getStringWidth(bare) / 2;
        if (bossOutline >= 0) outlined(fr, bare, nx, nameY, bossOutline | alpha, true);
        fr.drawString(bossColor >= 0 ? bare : name, nx, nameY, (bossColor >= 0 ? bossColor : 0xFFFFFF) | alpha);
        GL11.glColor4f(1F, 1F, 1F, 1F);
        mc.getTextureManager().bindTexture(ICONS);
        GL11.glDisable(GL11.GL_BLEND);              // as GuiIngameForge.renderBossHealth leaves it
    }

    private static void outlined(FontRenderer fr, String t, int x, int y, int c, boolean eight) {
        for (int dy = -1; dy <= 1; dy++)
            for (int dx = -1; dx <= 1; dx++)
                if ((dx != 0 || dy != 0) && (eight || dx == 0 || dy == 0)) fr.drawString(t, x + dx, y + dy, c);
    }

    /** A sheet sprite (u, v in 256-unit GUI px) at (x, y); w may be fractional (the fill). */
    private static void quad(float x, float y, float u, float v, float w, float h) {
        float k = 1F / 256F;
        Tessellator t = Tessellator.instance;
        t.startDrawingQuads();
        t.addVertexWithUV(x, y + h, 0, u * k, (v + h) * k);
        t.addVertexWithUV(x + w, y + h, 0, (u + w) * k, (v + h) * k);
        t.addVertexWithUV(x + w, y, 0, (u + w) * k, v * k);
        t.addVertexWithUV(x, y, 0, u * k, v * k);
        t.draw();
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
