package com.questforge.content.ench.enchants;

import net.minecraft.entity.EntityLivingBase;
import net.minecraft.potion.Potion;
import net.minecraft.potion.PotionEffect;

import com.questforge.content.ench.EnchantCategory;
import com.questforge.content.ench.ProcContext;
import com.questforge.content.ench.QFEnchantment;
import com.questforge.content.ench.Rarity;

/**
 * Chance to chill the target, slowing it. The first enchantment with a proc
 * chance below 100, so it also exercises the dispatcher's roll.
 */
public class EnchantFrostbite extends QFEnchantment {

    public EnchantFrostbite(int id) {
        super(id, "qf.frostbite", Rarity.RARE, EnchantCategory.WEAPON, 3);
    }

    @Override
    public int getProcChance(int level) {
        return 10 + (10 * level);   // 20% / 30% / 40%
    }

    @Override
    public void onAttack(ProcContext ctx) {
        EntityLivingBase target = ctx.livingTarget();
        if (target == null || ctx.world.isRemote) return;

        // Deliberately brief. Slowness III is -45% movement, and at a 40% proc rate
        // a long duration would mean permanently slowed rather than occasionally
        // chilled -- the difference between a debuff and a lockdown.
        int duration = 20 + (10 * ctx.level);   // 1.5 / 2.0 / 2.5 seconds
        target.addPotionEffect(new PotionEffect(Potion.moveSlowdown.id, duration, ctx.level - 1));
    }
}
