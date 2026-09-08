package com.questforge.content.ench.enchants;

import net.minecraft.entity.player.EntityPlayer;
import net.minecraft.potion.Potion;
import net.minecraft.potion.PotionEffect;

import com.questforge.content.ench.Cooldowns;
import com.questforge.content.ench.EnchantCategory;
import com.questforge.content.ench.Mitigation;
import com.questforge.content.ench.PotionEnchantment;
import com.questforge.content.ench.ProcContext;
import com.questforge.content.ench.Rarity;

/**
 * The enchantments whose entire effect is a permanent potion effect. Grouped in
 * one file because each is three lines; splitting them across five files would
 * add ceremony without adding clarity.
 *
 * All of these are slot-locked, which is what stops them stacking: four copies of
 * "you have Speed II" is still just Speed II, but four copies of an enchantment
 * that grants it is four chances to waste books on the same effect.
 */
public class PotionEnchants {

    /** Permanent jump boost. */
    public static class Frog extends PotionEnchantment {
        public Frog(int id) {
            super(id, "qf.frog", Rarity.RARE, EnchantCategory.BOOTS, 3);
        }

        @Override
        protected PotionSpec[] effects(int level) {
            return new PotionSpec[] { new PotionSpec(Potion.jump, level - 1) };
        }
    }

    /** Permanent speed. */
    public static class Deft extends PotionEnchantment {
        public Deft(int id) {
            super(id, "qf.deft", Rarity.EPIC, EnchantCategory.BOOTS, 2);
        }

        @Override
        protected PotionSpec[] effects(int level) {
            return new PotionSpec[] { new PotionSpec(Potion.moveSpeed, level - 1) };
        }
    }

    /** Permanent haste, on tools. */
    public static class Haste extends PotionEnchantment {
        public Haste(int id) {
            super(id, "qf.haste", Rarity.EPIC, EnchantCategory.TOOL, 3);
        }

        @Override
        protected PotionSpec[] effects(int level) {
            return new PotionSpec[] { new PotionSpec(Potion.digSpeed, level - 1) };
        }
    }

    /**
     * Trades mobility for durability: permanent slowness, permanent damage
     * reduction.
     *
     * The reduction is applied directly rather than through a Resistance effect,
     * because Resistance only comes in 20% steps -- the agreed 33% ceiling is not
     * expressible as a potion amplifier. So this reads 11% / 22% / 33%.
     *
     * The slowness half can be temporarily lifted: Cleansing removing it tells this
     * to stay off for twenty seconds rather than re-applying it on the next refresh,
     * which is what makes running Tank and Cleansing together interesting.
     */
    public static class Tank extends PotionEnchantment {
        private static final float REDUCTION_PER_LEVEL = 0.11F;

        /** How long Cleansing buys you out of the slowness. */
        private static final int RELIEF_TICKS = 400;

        /** Cooldown key. Shared by the suppressor and the check below. */
        private static final String RELIEF = "tank_slowness";

        public Tank(int id) {
            super(id, "qf.tank", Rarity.RARE, EnchantCategory.CHESTPLATE, 3);
        }

        /** Called by Cleansing when it strips this enchantment's own slowness. */
        public static void suppressSlowness(EntityPlayer player) {
            Cooldowns.start(player, RELIEF, RELIEF_TICKS);
        }

        @Override
        protected boolean shouldApply(ProcContext ctx) {
            if (!(ctx.user instanceof EntityPlayer)) return true;
            return Cooldowns.isReady((EntityPlayer) ctx.user, RELIEF);
        }

        @Override
        protected PotionSpec[] effects(int level) {
            return new PotionSpec[] { new PotionSpec(Potion.moveSlowdown, 0) };
        }

        @Override
        public boolean isMultipliable() {
            return false;   // always-on reduction; a replay would compound it
        }

        /** Before Cockroach, so its "would this kill me" test sees this reduction. */
        @Override
        public Phase getPhase() {
            return Phase.MULTIPLIER;
        }

        /** The defensive half, which the slowness relief never touches. */
        @Override
        public void onDamaged(ProcContext ctx) {
            ctx.damage *= (1.0F - (REDUCTION_PER_LEVEL * ctx.level));
        }
    }

    /**
     * The second wind you get for having survived at all.
     *
     * When something puts you on your last heart, you get a short burst of heavy
     * Resistance: long enough to run, or to take the fight back. It does not blunt
     * the hit that triggered it -- that hit is the whole point, and you are meant
     * to feel it -- and it is on a long cooldown, so it is a moment rather than a
     * permanent state.
     *
     * Whether the hit qualifies is asked of Mitigation rather than of the raw
     * event damage. LivingHurtEvent fires before armor is applied, and a boss here
     * swings for several times a player's maximum health while enchanted diamond
     * divides that by twenty-five, so the raw figure said "nearly dead" almost
     * every time it was asked.
     */
    public static class Cockroach extends com.questforge.content.ench.QFEnchantment {
        /** One heart: the hit has to leave you at or below this to count. */
        private static final float THRESHOLD = 2.0F;

        /** Resistance II / III / IV -- 40% / 60% / 80%. Never amplifier 4, which is immunity. */
        private static final int MAX_AMPLIFIER = 3;

        /** One minute. Enough that it is a moment in a fight, not a state of being. */
        private static final int COOLDOWN_TICKS = 1200;

        private static final String COOLDOWN = "cockroach";

        public Cockroach(int id) {
            super(id, "qf.cockroach", Rarity.EPIC, EnchantCategory.CHESTPLATE, 3);
        }

        @Override
        public boolean isMultipliable() {
            return false;
        }

        /** Last, so the reductions on the other pieces are already in ctx.damage. */
        @Override
        public Phase getPhase() {
            return Phase.PROC;
        }

        @Override
        public void onDamaged(ProcContext ctx) {
            if (!(ctx.user instanceof EntityPlayer) || ctx.world.isRemote) return;
            EntityPlayer player = (EntityPlayer) ctx.user;
            if (!Cooldowns.isReady(player, COOLDOWN)) return;

            float landing = Mitigation.predict(player, ctx.source, ctx.damage);
            float after = player.getHealth() - landing;

            // Has to leave you alive and on your last heart. A hit you were always
            // going to walk away from does not qualify, and neither does one that
            // kills you outright -- Resistance on a corpse helps nobody, and
            // burning the cooldown on it would be worse than not having it.
            if (after <= 0.0F || after > THRESHOLD) return;

            int amplifier = Math.min(MAX_AMPLIFIER, ctx.level);
            int duration = 80 + (20 * ctx.level);   // 5 / 6 / 7 seconds
            player.addPotionEffect(new PotionEffect(Potion.resistance.id, duration, amplifier));
            Cooldowns.start(player, COOLDOWN, COOLDOWN_TICKS);
        }
    }

    /** Regeneration, but only when nothing has hit you for a while. */
    public static class Regrowth extends PotionEnchantment {
        private static final int OUT_OF_COMBAT_TICKS = 200;   // 10 seconds

        public Regrowth(int id) {
            super(id, "qf.regrowth", Rarity.RARE, EnchantCategory.LEGGINGS, 3);
        }

        @Override
        protected boolean shouldApply(ProcContext ctx) {
            return ctx.user != null
                    && !com.questforge.content.ench.CombatState.wasHurtRecently(
                            ctx.user, OUT_OF_COMBAT_TICKS);
        }

        @Override
        protected PotionSpec[] effects(int level) {
            return new PotionSpec[] { new PotionSpec(Potion.regeneration, level - 1) };
        }
    }
}
