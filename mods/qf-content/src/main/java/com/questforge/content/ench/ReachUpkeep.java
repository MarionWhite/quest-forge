package com.questforge.content.ench;

import net.minecraft.entity.player.EntityPlayer;
import net.minecraft.entity.player.EntityPlayerMP;

/**
 * Server-side block reach for the Reach enchantment.
 *
 * Reach turned out to need two different mechanisms, because Forge already solved
 * half of it. Block breaking and placing are checked against
 * ItemInWorldManager.getBlockReachDistance(), which Forge made settable -- so that
 * half is an ordinary API call from the player tick, no bytecode involved.
 *
 * Attacking an entity is still checked against a hardcoded 36.0D in
 * NetHandlerPlayServer with no way in, so that half stays in ReachTransformer.
 *
 * The value is written every tick rather than on equip: there is no reliable
 * "player changed held item" event in 1.7.10, and a stale reach value would either
 * leave the enchantment on after it was removed or off after it was added.
 */
public class ReachUpkeep {

    /** Forge's default for a survival player. Restored whenever Reach is not held. */
    private static final double VANILLA = 5.0D;

    public static void update(EntityPlayer player) {
        if (!(player instanceof EntityPlayerMP)) return;

        EntityPlayerMP mp = (EntityPlayerMP) player;
        if (mp.theItemInWorldManager == null) return;

        int level = QFReachHooks.levelOn(mp.getHeldItem());
        double wanted = (level <= 0) ? VANILLA : VANILLA + level;

        if (mp.theItemInWorldManager.getBlockReachDistance() != wanted) {
            mp.theItemInWorldManager.setBlockReachDistance(wanted);
        }
    }
}
