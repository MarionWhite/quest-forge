package com.questforge.content.client;

import net.minecraftforge.client.event.RenderGameOverlayEvent;
import net.minecraftforge.client.event.RenderWorldLastEvent;

import cpw.mods.fml.common.eventhandler.SubscribeEvent;
import cpw.mods.fml.common.gameevent.TickEvent;
import cpw.mods.fml.common.network.FMLNetworkEvent;
import cpw.mods.fml.relauncher.Side;
import cpw.mods.fml.relauncher.SideOnly;

/**
 * The single client-side event handler, mirroring what EnchantEventBridge does on
 * the common side: nothing else in the client package touches Forge events.
 */
@SideOnly(Side.CLIENT)
public class QFClientEvents {

    @SubscribeEvent
    public void onClientTick(TickEvent.ClientTickEvent event) {
        if (event.phase != TickEvent.Phase.END) return;
        JammerFX.tick();
        ProspectorHUD.tick();
        flippers();
    }

    /**
     * Flippers for the local player. Movement is client-owned, so the swim boost
     * has to be applied here; the server tick only handles non-players.
     */
    private static void flippers() {
        net.minecraft.client.Minecraft mc = net.minecraft.client.Minecraft.getMinecraft();
        if (mc == null || mc.thePlayer == null) return;
        com.questforge.content.ench.QFEnchantment ench = com.questforge.content.ench.QFEnchantments.flippers;
        if (ench == null) return;

        net.minecraft.item.ItemStack boots = mc.thePlayer.inventory.armorInventory[0];
        if (boots == null) return;
        int level = net.minecraft.enchantment.EnchantmentHelper.getEnchantmentLevel(ench.effectId, boots);
        if (level <= 0) return;

        com.questforge.content.ench.enchants.ArmorEnchants.Flippers.apply(mc.thePlayer, level);
    }

    /** Tracker's outlines, drawn after the world so they sit in world space. */
    @SubscribeEvent
    public void onRenderWorldLast(RenderWorldLastEvent event) {
        TrackerFX.render(event.partialTicks);
    }

    /**
     * Jammer runs at Pre(ALL): the world is finished, the HUD is not yet drawn.
     * That is deliberate -- the victim loses their aim, not their health bar.
     */
    @SubscribeEvent
    public void onOverlayPre(RenderGameOverlayEvent.Pre event) {
        if (event.type != RenderGameOverlayEvent.ElementType.ALL) return;
        JammerFX.render();
    }

    @SubscribeEvent
    public void onOverlayPost(RenderGameOverlayEvent.Post event) {
        if (event.type != RenderGameOverlayEvent.ElementType.TEXT) return;
        ProspectorHUD.render();
    }

    /** A jam must not follow you into the next world you join. */
    @SubscribeEvent
    public void onDisconnect(FMLNetworkEvent.ClientDisconnectionFromServerEvent event) {
        JammerFX.clear();
    }
}
