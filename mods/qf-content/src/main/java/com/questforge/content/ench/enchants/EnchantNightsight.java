package com.questforge.content.ench.enchants;

import net.minecraft.entity.player.EntityPlayer;
import net.minecraft.potion.Potion;
import net.minecraft.potion.PotionEffect;

import com.questforge.content.ench.EnchantCategory;
import com.questforge.content.ench.ProcContext;
import com.questforge.content.ench.QFEnchantment;
import com.questforge.content.ench.Rarity;

/**
 * Night vision while it is dark enough to matter.
 *
 * The effect is refreshed on a short timer rather than applied once, so it fades
 * out on its own when you step into daylight instead of needing to be removed.
 */
public class EnchantNightsight extends QFEnchantment {

    /** Light level at or below which this kicks in. */
    private static final int DARK_ENOUGH = 8;

    public EnchantNightsight(int id) {
        super(id, "qf.nightsight", Rarity.COMMON, EnchantCategory.HELMET, 1);
    }

    @Override
    public boolean isMultipliable() {
        return false;   // passive
    }

    @Override
    public void onTick(ProcContext ctx) {
        if (!(ctx.user instanceof EntityPlayer) || ctx.world.isRemote) return;
        EntityPlayer player = (EntityPlayer) ctx.user;

        // Only re-apply occasionally; this runs every tick.
        if (player.ticksExisted % 40 != 0) return;

        int light = ctx.world.getBlockLightValue(
                (int) Math.floor(player.posX),
                (int) Math.floor(player.posY),
                (int) Math.floor(player.posZ));

        if (light <= DARK_ENOUGH) {
            // 220 ticks against a 40-tick refresh: comfortably overlapping, and
            // short enough that it expires quickly once you leave the dark.
            player.addPotionEffect(new PotionEffect(Potion.nightVision.id, 220, 0, true));
        }
    }
}
