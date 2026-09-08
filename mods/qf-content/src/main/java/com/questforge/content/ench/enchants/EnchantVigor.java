package com.questforge.content.ench.enchants;

import com.questforge.content.ench.EnchantCategory;
import com.questforge.content.ench.QFEnchantment;
import com.questforge.content.ench.Rarity;

/**
 * Bonus maximum health.
 *
 * Has no hooks of its own: the modifier is reconciled every tick by
 * AttributeUpkeep, because a per-item hook can add an attribute modifier but can
 * never tell when the item was taken off.
 */
public class EnchantVigor extends QFEnchantment {

    public EnchantVigor(int id) {
        super(id, "qf.vigor", Rarity.EPIC, EnchantCategory.CHESTPLATE, 3);
    }

    @Override
    public boolean isMultipliable() {
        return false;
    }
}
