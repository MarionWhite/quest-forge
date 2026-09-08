package com.questforge.content.ench.enchants;

import java.util.Iterator;

import net.minecraft.item.ItemStack;

import com.questforge.content.ench.EnchantCategory;
import com.questforge.content.ench.HarvestContext;
import com.questforge.content.ench.QFEnchantment;
import com.questforge.content.ench.Rarity;

/**
 * Mined drops go straight into your inventory instead of onto the floor.
 * Anything that will not fit falls normally.
 */
public class EnchantMagnetize extends QFEnchantment {

    public EnchantMagnetize(int id) {
        super(id, "qf.magnetize", Rarity.COMMON, EnchantCategory.TOOL, 1);
    }

    @Override
    public boolean isMultipliable() {
        return false;   // doubling item collection would duplicate drops
    }

    @Override
    public void onHarvest(HarvestContext ctx) {
        if (ctx.player == null || ctx.world.isRemote) return;

        Iterator<ItemStack> it = ctx.drops.iterator();
        while (it.hasNext()) {
            ItemStack drop = it.next();
            if (drop == null) continue;
            if (ctx.player.inventory.addItemStackToInventory(drop)) {
                it.remove();   // fully collected; do not also drop it
            }
        }
    }
}
