package com.questforge.content.ench;

import java.util.Random;

import net.minecraft.entity.player.EntityPlayer;
import net.minecraft.item.ItemStack;
import net.minecraftforge.event.entity.living.LivingDeathEvent;

import cpw.mods.fml.common.eventhandler.EventPriority;
import cpw.mods.fml.common.eventhandler.SubscribeEvent;

/**
 * The two things that must happen before any other mod reacts to a player dying.
 *
 * GraveStones handles LivingDeathEvent at HIGHEST priority from its preInit and
 * moves every inventory slot into a grave before returning. Every mod's preInit
 * runs before any init, so a handler registered from init -- where the rest of
 * the bridge lives -- can never get ahead of it at the same priority. This class
 * is registered from preInit, and the mod declares itself "before:gravestonemod",
 * which is what puts it first in the HIGHEST bucket.
 *
 * Order within this handler matters too: Sacrifice decides whether the death
 * happens at all, and only then does Soulbound pull items aside. A death that was
 * vetoed leaves the inventory exactly as it was.
 */
public class DeathHandler {

    private final Random rand = new Random();

    @SubscribeEvent(priority = EventPriority.HIGHEST)
    public void onPlayerDeath(LivingDeathEvent event) {
        if (!(event.entityLiving instanceof EntityPlayer)) return;
        if (event.entityLiving.worldObj.isRemote || event.isCanceled()) return;

        EntityPlayer player = (EntityPlayer) event.entityLiving;

        if (sacrificeVeto(player, event)) {
            event.setCanceled(true);
            return;
        }

        // With keepInventory on nothing is going anywhere, and stashing would only
        // add a window in which a restart could lose the item.
        if (player.worldObj.getGameRules().getGameRuleBooleanValue("keepInventory")) return;

        Soulbound.captureFromInventory(player);
    }

    /** @return true if a Sacrifice piece absorbed the death. */
    private boolean sacrificeVeto(EntityPlayer player, LivingDeathEvent event) {
        ItemStack[] armor = player.inventory.armorInventory;
        for (int slot = 0; slot < armor.length; slot++) {
            ItemStack piece = armor[slot];
            if (piece == null) continue;

            ProcContext ctx = new ProcContext(player, null, piece,
                    player.worldObj, rand, event.source, 0F);
            EnchantDispatcher.dispatch(EnchantDispatcher.Trigger.DEATH, ctx);

            if (ctx.cancelled) {
                // The piece that saved you is gone. Clearing the slot here rather
                // than leaving a zero-count stack: vanilla only nulls a spent armor
                // stack on the next hit that damages armor, and until then the ghost
                // still renders, still counts as equipped, and can fire again.
                if (piece.stackSize <= 0) {
                    armor[slot] = null;
                    player.inventory.markDirty();
                }
                return true;
            }
        }
        return false;
    }
}
