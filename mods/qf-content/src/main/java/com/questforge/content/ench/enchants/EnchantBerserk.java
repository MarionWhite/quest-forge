package com.questforge.content.ench.enchants;

import com.questforge.content.ench.EnchantCategory;
import com.questforge.content.ench.ProcContext;
import com.questforge.content.ench.QFEnchantment;
import com.questforge.content.ench.Rarity;

/**
 * The mirror of Executioner: your damage rises as your own health falls.
 * Rewards fighting hurt, which is exactly the wrong instinct, which is the point.
 */
public class EnchantBerserk extends QFEnchantment {

    /** Extra damage fraction when at zero health, per level. */
    private static final float PER_LEVEL = 0.30F;

    public EnchantBerserk(int id) {
        super(id, "qf.berserk", Rarity.EPIC, EnchantCategory.WEAPON, 3);
    }

    @Override
    public boolean isMultipliable() {
        return false;   // always-on multiplier: a replay would square it
    }

    @Override
    public Phase getPhase() {
        return Phase.MULTIPLIER;
    }

    @Override
    public void onAttack(ProcContext ctx) {
        if (ctx.user == null) return;

        float max = ctx.user.getMaxHealth();
        if (max <= 0) return;

        float missingFraction = 1.0F - (ctx.user.getHealth() / max);
        // A fraction of the hit rather than a flat addition, for the same reason
        // Executioner is: this pack's weapons run from 4 damage to well over 30.
        ctx.damage *= 1.0F + (PER_LEVEL * ctx.level * missingFraction);
    }
}
