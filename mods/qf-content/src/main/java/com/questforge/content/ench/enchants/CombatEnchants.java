package com.questforge.content.ench.enchants;

import net.minecraft.entity.EntityLivingBase;
import net.minecraft.potion.Potion;
import net.minecraft.potion.PotionEffect;
import net.minecraft.util.DamageSource;

import com.questforge.content.ench.CombatState;
import com.questforge.content.ench.EnchantCategory;
import com.questforge.content.ench.Mitigation;
import com.questforge.content.ench.ProcContext;
import com.questforge.content.ench.QFEnchantment;
import com.questforge.content.ench.Rarity;
import com.questforge.content.ench.TickedEffects;

/** Weapon enchantments that resolve on a single hit. */
public class CombatEnchants {

    /**
     * Bonus damage proportional to the target's MAXIMUM health, so it stays
     * relevant against the huge health pools Lycanites/OreSpawn/Infernal bosses
     * have. Proc-based rather than flat, at your request, so it does not simply
     * dominate every other weapon enchantment.
     */
    public static class Colossus extends QFEnchantment {
        /** Fraction of the target's maximum health added per level. */
        private static final float PER_LEVEL = 0.025F;

        public Colossus(int id) {
            super(id, "qf.colossus", Rarity.EPIC, EnchantCategory.WEAPON, 3);
        }

        @Override
        public int getProcChance(int level) {
            return 3 + (3 * level);   // 6% / 9% / 12%
        }

        @Override
        public void onAttack(ProcContext ctx) {
            EntityLivingBase target = ctx.livingTarget();
            if (target == null) return;

            // Capped at a multiple of the hit that triggered it. Uncapped, 12% of
            // hits adding 7.5% of max health is 0.9% of max health per swing
            // whatever the weapon, which put a ~55 second ceiling on Mobzilla and
            // The King with a diamond sword. Tying the bonus to the hit keeps it a
            // bonus rather than the whole weapon.
            float bonus = target.getMaxHealth() * PER_LEVEL * ctx.level;
            float cap = Math.max(MIN_CAP, ctx.damage * CAP_MULTIPLIER);
            ctx.damage += Math.min(bonus, cap);
        }

        /** The bonus never exceeds this many times the triggering hit... */
        private static final float CAP_MULTIPLIER = 4.0F;
        /** ...but a weak weapon still gets at least this much, so it is felt. */
        private static final float MIN_CAP = 20.0F;
    }

    /** Heals you when you kill something, rather than on every hit. */
    public static class Feast extends QFEnchantment {
        public Feast(int id) {
            super(id, "qf.feast", Rarity.RARE, EnchantCategory.WEAPON, 3);
        }

        @Override
        public void onKill(ProcContext ctx) {
            if (ctx.user == null) return;
            ctx.user.heal(2.0F * ctx.level);
        }
    }

    /**
     * Poison, with damage that actually arrives.
     *
     * The potion effect is still real vanilla poison, so particles, milk, curing,
     * Cleansing and undead immunity all behave normally. The damage rides
     * alongside it, because vanilla deals poison damage from inside
     * Potion.performEffect where the target's invulnerability window swallows it
     * for as long as you keep swinging.
     */
    public static class Poisonous extends QFEnchantment {
        /**
         * Damage per second, as a fraction of the hit that applied it, per level
         * -- of the hit as it LANDED, after the target's armour. See Venomous for
         * why.
         */
        private static final float PER_LEVEL = 0.04F;

        public Poisonous(int id) {
            super(id, "qf.poisonous", Rarity.UNCOMMON, EnchantCategory.WEAPON, 3);
        }

        @Override
        public int getProcChance(int level) {
            return 10 * level;
        }

        @Override
        public void onAttack(ProcContext ctx) {
            EntityLivingBase target = ctx.livingTarget();
            if (target == null || ctx.world.isRemote) return;

            int duration = 60 + (20 * ctx.level);
            target.addPotionEffect(new PotionEffect(Potion.poison.id, duration, 0));

            // Only if it took: undead and anything else immune get nothing, and
            // we inherit whatever immunity rules the rest of the pack has added.
            if (target.isPotionActive(Potion.poison)) {
                float landed = Mitigation.predict(target, ctx.source, ctx.baseDamage);
                TickedEffects.addVenom(target, ctx.user, duration,
                        Math.max(1.0F, landed * PER_LEVEL * ctx.level));
            }
        }
    }

    /** Poisonous, but it hurts. */
    public static class Venomous extends QFEnchantment {
        public Venomous(int id) {
            super(id, "qf.venomous", Rarity.RARE, EnchantCategory.WEAPON, 3);
        }

        @Override
        public int getProcChance(int level) {
            return 8 * level;
        }

        /**
         * Damage per second, as a fraction of the hit that applied it, per level.
         *
         * The fraction is of the hit as it LANDS, read after the target's armour
         * (2026-10-25, decision 0005 P1). LivingHurtEvent fires before armour,
         * and seeding the venom from the raw hit made it 5.8% of a 750 swing on
         * bosses whose armour let 120 of that swing through: Venomous read
         * +40..50% and Poisonous (an Uncommon) +40..42% on Mobzilla, The King
         * and The Queen, more than any other enchantment there. The venom ticks
         * still bypass armour; only the seed is read after it. Old: ctx.damage x
         * 5.8% / 4%. New: the same percentages of Mitigation.predict(target,
         * hit). Against an unarmoured target the two are the same number.
         *
         * And the hit is the weapon's own, ctx.baseDamage, not ctx.damage
         * (2026-10-25, decision 0005 P2): the dispatcher runs flat adds and
         * multipliers before the procs, so a venom seeded from ctx.damage
         * inherited Colossus, Cultist and Roulette (Colossus + Venomous read +46
         * points beyond independence on the Naga, Cultist + Poisonous +29 on
         * Mobzilla). Those boosts now reach the swing only.
         */
        private static final float PER_LEVEL = 0.058F;

        @Override
        public void onAttack(ProcContext ctx) {
            EntityLivingBase target = ctx.livingTarget();
            if (target == null || ctx.world.isRemote) return;

            int duration = 100 + (40 * ctx.level);
            // Amplifier 1, so the poison -- and the venom that follows its cadence
            // -- ticks twice as often as Poisonous.
            target.addPotionEffect(new PotionEffect(Potion.poison.id, duration, 1));
            if (target.isPotionActive(Potion.poison)) {
                float landed = Mitigation.predict(target, ctx.source, ctx.baseDamage);
                TickedEffects.addVenom(target, ctx.user, duration,
                        Math.max(1.0F, landed * PER_LEVEL * ctx.level));
            }
            // Was vanilla Weakness, which is a flat -0.5 damage and therefore
            // invisible against modded weapons. This is a real 10% for 4 seconds.
            TickedEffects.addCripple(target, 0.10F, 80);
        }
    }

    /**
     * Blindness on hit.
     *
     * Worth knowing: 1.7.10 mob AI does not meaningfully use sight, so this barely
     * affects mobs. Against players it is punishing. It is effectively a PvP
     * enchantment.
     */
    public static class Blind extends QFEnchantment {
        public Blind(int id) {
            super(id, "qf.blind", Rarity.RARE, EnchantCategory.WEAPON, 3);
        }

        @Override
        public int getProcChance(int level) {
            return 8 * level;
        }

        @Override
        public void onAttack(ProcContext ctx) {
            EntityLivingBase target = ctx.livingTarget();
            if (target == null || ctx.world.isRemote) return;
            target.addPotionEffect(new PotionEffect(Potion.blindness.id, 60 + (20 * ctx.level), 0));
        }
    }

    /** Throws the target into the air, high enough that landing hurts. */
    public static class Suplex extends QFEnchantment {
        public Suplex(int id) {
            super(id, "qf.suplex", Rarity.RARE, EnchantCategory.WEAPON, 3);
        }

        @Override
        public int getProcChance(int level) {
            return 5 + (5 * level);
        }

        @Override
        public void onAttack(ProcContext ctx) {
            if (ctx.target == null) return;
            ctx.target.motionY += 0.7D + (0.15D * ctx.level);
            ctx.target.velocityChanged = true;
        }
    }

    /** Spins the target around. Disorienting for players, cosmetic for mobs. */
    public static class Daze extends QFEnchantment {
        public Daze(int id) {
            super(id, "qf.daze", Rarity.UNCOMMON, EnchantCategory.WEAPON, 3);
        }

        @Override
        public int getProcChance(int level) {
            return 10 * level;
        }

        @Override
        public void onAttack(ProcContext ctx) {
            EntityLivingBase target = ctx.livingTarget();
            if (target == null) return;
            target.rotationYaw += 180.0F;
            target.rotationYawHead += 180.0F;
            target.renderYawOffset += 180.0F;

            // A player's client owns its own rotation; changing the server copy
            // does nothing visible unless the server sends a position packet.
            // Teleport.to sends it to the same place the target already is, which
            // is how a rotation change is pushed, and skips the packet for a
            // player that has no connection to receive it.
            com.questforge.content.ench.Teleport.to(
                    target, target.posX, target.posY, target.posZ);
        }
    }

    /** Half damage or double damage, nothing in between. */
    public static class Roulette extends QFEnchantment {
        /**
         * Rare since 2026-10-25 (decision 0005 P9; was Uncommon). The census
         * measured +21% trusted mean, level with Colossus (an Epic) and above
         * every Rare but Rupture; +16% even on the 750-capped T4 bosses, since
         * it multiplies after the cap.
         */
        public Roulette(int id) {
            super(id, "qf.roulette", Rarity.RARE, EnchantCategory.WEAPON, 1);
        }

        @Override
        public boolean isMultipliable() {
            return false;   // twice would be x4 or x0.25, not "two rolls"
        }

        @Override
        public Phase getPhase() {
            return Phase.MULTIPLIER;
        }

        @Override
        public void onAttack(ProcContext ctx) {
            ctx.damage *= ctx.rand.nextBoolean() ? 2.0F : 0.5F;
        }
    }

    /** Pay in blood: hurt yourself to double the damage dealt. */
    public static class Cultist extends QFEnchantment {
        public Cultist(int id) {
            super(id, "qf.cultist", Rarity.RARE, EnchantCategory.WEAPON, 3);
        }

        @Override
        public int getProcChance(int level) {
            return 8 * level;
        }

        /**
         * The blood price: health taken from the wielder on every proc, before
         * Protection. Fixed, and independent of the level, the weapon and the
         * wielder's armour (2026-10-25, decision 0005 P7).
         */
        private static final float PRICE = 0.6F;

        @Override
        public boolean isMultipliable() {
            return false;   // a replay would double an already-doubled hit and bill for it
        }

        @Override
        public Phase getPhase() {
            return Phase.MULTIPLIER;
        }

        /**
         * The blood price's damage source. It bypasses armour (2026-10-25,
         * decision 0005 P7). Until then it was ordinary physical damage, so the
         * wielder's armour decided what Cultist cost, and the census found that
         * price falling to nothing: diamond was driven to the 1-health floor
         * within a Naga fight, fiery lost about 2 health, Ultimate and Royal lost
         * 0 and the wielder never left 20. An enchantment whose utility scales
         * with the gear has to keep a cost at every tier, so the price now
         * ignores armour points and durability. Protection (and Resistance) still
         * apply, because the source is not absolute: that is the one way armour
         * can still soften it. No armour durability is spent on it any more.
         */
        public static final DamageSource BLOOD_PRICE = new DamageSource("qf.cultist") {
        }.setDamageBypassesArmor();

        @Override
        public void onAttack(ProcContext ctx) {
            if (ctx.user == null || CombatState.isReentrant()) return;

            // The price is a fixed slice of the wielder's own health bar: not of
            // the hit (75% of the hit killed the wielder in every simulated fight,
            // because this pack's weapons swing for more than a player has health)
            // and no longer of the maximum health per level either. Old: min(75% of
            // the hit, 10% of max health x level), reduced by armour. New: 0.6
            // health a proc, armour-independent (decision 0005 P7). At 24% of
            // swings a 34-second Naga fight costs about 10 health at every tier;
            // before, about 19 in diamond and 0 in Ultimate or Royal.
            float selfDamage = PRICE;
            // A floor, not a scaling rule: the raw price never exceeds what would
            // leave one health, so Cultist alone cannot be the thing that kills you.
            selfDamage = Math.min(selfDamage, Math.max(0.0F, ctx.user.getHealth() - 1.0F));
            ctx.damage *= 2.0F;
            if (selfDamage <= 0.0F) return;

            // Damaging the wielder fires another LivingHurtEvent; the guard stops
            // that pass from triggering this enchantment again.
            CombatState.enter();
            try {
                ctx.user.attackEntityFrom(BLOOD_PRICE, selfDamage);
            } finally {
                CombatState.exit();
            }
        }
    }

    /**
     * Very rare instant kill.
     *
     * Sets health directly rather than dealing enormous damage: several bosses in
     * this pack clamp incoming damage, which would make a damage-based version
     * silently useless against exactly the targets worth using it on.
     */
    public static class KillingBlow extends QFEnchantment {
        public KillingBlow(int id) {
            super(id, "qf.killingblow", Rarity.EPIC, EnchantCategory.WEAPON, 3);
        }

        @Override
        public void onAttack(ProcContext ctx) {
            EntityLivingBase target = ctx.livingTarget();
            if (target == null) return;

            // 0.1% per level. getProcChance is integer percent, too coarse for this.
            if (ctx.rand.nextInt(1000) >= ctx.level) return;

            target.setHealth(0.0F);
            ctx.damage = Math.max(ctx.damage, 1.0F);
        }
    }

    /** Consecutive hits on the same target ramp up. Absorbs the "Ferocious" idea. */
    public static class Momentum extends QFEnchantment {
        private static final int WINDOW_TICKS = 40;
        private static final int MAX_STACKS = 8;

        /**
         * Epic since 2026-10-25 (decision 0005 P9; was Uncommon). The census
         * measured +24% trusted mean, above every Epic except Rage, and as an
         * Uncommon it dropped from vanilla chests at T0-T1, the strongest early
         * find by a wide margin. Worth 0 on the 750-capped T4 bosses.
         */
        public Momentum(int id) {
            super(id, "qf.momentum", Rarity.EPIC, EnchantCategory.WEAPON, 3);
        }

        @Override
        public boolean isMultipliable() {
            return false;   // always-on flat add; "twice" is just a bigger number
        }

        @Override
        public Phase getPhase() {
            return Phase.FLAT;
        }

        @Override
        public void onAttack(ProcContext ctx) {
            if (ctx.user == null || ctx.target == null) return;
            int stacks = CombatState.recordHit(ctx.user, ctx.target, WINDOW_TICKS);
            int capped = Math.min(stacks, MAX_STACKS);
            ctx.damage += 0.5F * ctx.level * (capped - 1);
        }
    }

    /** Hits harder just after you have been hit. */
    public static class Riposte extends QFEnchantment {
        private static final int WINDOW_TICKS = 60;

        public Riposte(int id) {
            super(id, "qf.riposte", Rarity.UNCOMMON, EnchantCategory.WEAPON, 3);
        }

        @Override
        public boolean isMultipliable() {
            return false;
        }

        @Override
        public Phase getPhase() {
            return Phase.FLAT;
        }

        @Override
        public void onAttack(ProcContext ctx) {
            if (ctx.user == null) return;
            if (!CombatState.wasHurtRecently(ctx.user, WINDOW_TICKS)) return;
            ctx.damage += 1.5F * ctx.level;
        }
    }
}
