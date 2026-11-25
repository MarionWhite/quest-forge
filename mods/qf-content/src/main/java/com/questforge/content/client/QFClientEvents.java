package com.questforge.content.client;

import net.minecraft.util.EnumChatFormatting;
import net.minecraft.util.StatCollector;
import net.minecraftforge.client.event.RenderGameOverlayEvent;
import net.minecraftforge.client.event.RenderWorldLastEvent;
import net.minecraftforge.event.entity.player.ItemTooltipEvent;

import com.questforge.content.ench.EnchantDispatcher;
import com.questforge.content.ench.ItemEnchantBook;

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

    /**
     * One line per custom enchantment on the item that has something a player
     * has to know (QFEnchantment.tooltipNote): Rage's "does nothing while
     * Excalibur is held", and Excalibur's mirror of it (decision 0005 P4). The
     * book gets the same line from ItemEnchantBook.addInformation; this is for
     * the gear it was applied to, which vanilla only labels with the name.
     */
    @SubscribeEvent
    @SuppressWarnings("unchecked")
    public void onItemTooltip(ItemTooltipEvent event) {
        if (event.itemStack == null || event.toolTip == null) return;
        if (event.itemStack.getItem() instanceof ItemEnchantBook) return;
        for (EnchantDispatcher.Found f : EnchantDispatcher.findOn(event.itemStack)) {
            String note = f.enchant.tooltipNote();
            if (note == null) continue;
            event.toolTip.add(EnumChatFormatting.DARK_GRAY
                    + StatCollector.translateToLocal(f.enchant.getName()) + ": "
                    + StatCollector.translateToLocal(note));
        }
    }

    /** Outlines drawn after the world, so they sit in world space. */
    @SubscribeEvent
    public void onRenderWorldLast(RenderWorldLastEvent event) {
        TrackerFX.render(event.partialTicks);
        PlacementGhost.render(event.partialTicks);
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
