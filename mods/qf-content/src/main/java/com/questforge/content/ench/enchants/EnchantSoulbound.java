package com.questforge.content.ench.enchants;

import com.questforge.content.ench.EnchantCategory;
import com.questforge.content.ench.QFEnchantment;
import com.questforge.content.ench.Rarity;

/**
 * The item comes back to you, whatever happens to it.
 *
 * Has no hooks: all three behaviours (kept through death, excluded from the
 * Gravestones pool, rescued from despawning) are driven from the event bridge by
 * com.questforge.content.ench.Soulbound, because they need event priorities and
 * player-respawn events rather than per-item procs.
 */
public class EnchantSoulbound extends QFEnchantment {

    public EnchantSoulbound(int id) {
        super(id, "qf.soulbound", Rarity.LEGENDARY, EnchantCategory.ANY, 1);
    }

    @Override
    public boolean isMultipliable() {
        return false;
    }
}
