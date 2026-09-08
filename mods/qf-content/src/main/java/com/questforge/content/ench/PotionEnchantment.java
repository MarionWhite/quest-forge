package com.questforge.content.ench;

import net.minecraft.entity.EntityLivingBase;
import net.minecraft.potion.Potion;
import net.minecraft.potion.PotionEffect;

/**
 * Base for enchantments whose whole effect is "you have this potion effect while
 * this is equipped".
 *
 * The effect is re-applied on a short cycle rather than granted once, so it drains
 * away on its own when the item is unequipped instead of needing to be tracked and
 * removed. REFRESH_TICKS is deliberately well under DURATION so there is no gap.
 */
public abstract class PotionEnchantment extends QFEnchantment {

    private static final int REFRESH_TICKS = 40;
    private static final int DURATION = 200;

    protected PotionEnchantment(int id, String name, Rarity rarity,
            EnchantCategory category, int maxLevel) {
        super(id, name, rarity, category, maxLevel);
    }

    /** The effects to apply at this level. */
    protected abstract PotionSpec[] effects(int level);

    /** Override to make the effect conditional (low health, darkness, and so on). */
    protected boolean shouldApply(ProcContext ctx) {
        return true;
    }

    @Override
    public boolean isMultipliable() {
        return false;   // passive; doubling it is meaningless
    }

    @Override
    public void onTick(ProcContext ctx) {
        if (ctx.user == null || ctx.world.isRemote) return;
        if (ctx.user.ticksExisted % REFRESH_TICKS != 0) return;
        if (!shouldApply(ctx)) return;

        EntityLivingBase user = ctx.user;
        for (PotionSpec spec : effects(ctx.level)) {
            if (spec == null) continue;
            user.addPotionEffect(new PotionEffect(spec.potion, DURATION, spec.amplifier, true));
        }
    }

    /** A potion id plus amplifier. */
    public static class PotionSpec {
        public final int potion;
        public final int amplifier;

        public PotionSpec(Potion potion, int amplifier) {
            this.potion = potion.id;
            this.amplifier = amplifier;
        }
    }
}
