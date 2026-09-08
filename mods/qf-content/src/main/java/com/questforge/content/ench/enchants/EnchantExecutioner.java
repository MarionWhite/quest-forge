package com.questforge.content.ench.enchants;

import net.minecraft.entity.EntityLivingBase;

import com.questforge.content.ench.EnchantCategory;
import com.questforge.content.ench.ProcContext;
import com.questforge.content.ench.QFEnchantment;
import com.questforge.content.ench.Rarity;

/**
 * Damage scales with how much health the target has already lost.
 * At full health it does nothing; on a nearly-dead target it is a large bonus.
 *
 * The bonus is a PERCENTAGE of the hit, not a flat addition. This pack's weapons
 * span from a wooden sword's 4 damage to modded weapons in the thirties, and a
 * flat "+15" would be decisive on the former and irrelevant on the latter. A
 * multiplier means the enchantment is worth the same to whatever you put it on.
 */
public class EnchantExecutioner extends QFEnchantment {

    /** Extra damage fraction at 0% target health, per level. */
    private static final float PER_LEVEL = 0.25F;

    public EnchantExecutioner(int id) {
        super(id, "qf.executioner", Rarity.RARE, EnchantCategory.WEAPON, 3);
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
        EntityLivingBase target = ctx.livingTarget();
        if (target == null) return;

        float max = target.getMaxHealth();
        if (max <= 0) return;

        float missingFraction = 1.0F - (target.getHealth() / max);
        ctx.damage *= 1.0F + (PER_LEVEL * ctx.level * missingFraction);
    }
}
