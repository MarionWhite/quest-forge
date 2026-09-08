package com.questforge.content.ench.enchants;

import com.questforge.content.ench.EnchantCategory;
import com.questforge.content.ench.QFEnchantment;
import com.questforge.content.ench.Rarity;

/**
 * Every other custom enchantment on this item procs twice.
 *
 * Deliberately has no effect hooks of its own. EnchantDispatcher looks for it and
 * turns its presence into a loop count, which is the only reason this works
 * without every other enchantment knowing it exists.
 */
public class EnchantMultiStrike extends QFEnchantment {

    public EnchantMultiStrike(int id) {
        super(id, "qf.multistrike", Rarity.LEGENDARY, EnchantCategory.ANY, 1);
    }

    @Override
    public boolean isMultipliable() {
        return false;   // must never double itself
    }
}
