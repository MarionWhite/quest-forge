package com.questforge.content.ench.enchants;

import java.util.List;

import net.minecraft.entity.EntityLiving;
import net.minecraft.entity.EntityLivingBase;
import net.minecraft.entity.item.EntityItem;
import net.minecraft.entity.monster.EntityIronGolem;
import net.minecraft.entity.monster.EntitySkeleton;
import net.minecraft.entity.monster.EntityZombie;
import net.minecraft.entity.passive.EntityWolf;
import net.minecraft.entity.player.EntityPlayer;
import net.minecraft.item.ItemStack;
import net.minecraft.potion.Potion;
import net.minecraft.potion.PotionEffect;
import net.minecraft.util.AxisAlignedBB;
import net.minecraft.util.DamageSource;

import com.questforge.content.ench.CombatState;
import com.questforge.content.ench.EnchantCategory;
import com.questforge.content.ench.Hostility;
import com.questforge.content.ench.ProcContext;
import com.questforge.content.ench.QFEnchantment;
import com.questforge.content.ench.Rarity;
import com.questforge.content.ench.TickedEffects;

/** The second half of the weapon set. */
public class WeaponEnchants2 {

    /** Stacking bleed that keeps hurting after the hit. */
    public static class Rupture extends QFEnchantment {
        public Rupture(int id) {
            super(id, "qf.rupture", Rarity.RARE, EnchantCategory.WEAPON, 3);
        }

        @Override
        public int getProcChance(int level) {
            return 15 + (10 * level);
        }

        /** Each stack bleeds for this fraction of the hit that applied it, per second. */
        private static final float PER_STACK_OF_HIT = 0.04F;
        /** ...and never less than this, so a fist still draws blood. */
        private static final float PER_STACK_FLOOR = 0.5F;

        @Override
        public void onAttack(ProcContext ctx) {
            EntityLivingBase target = ctx.livingTarget();
            if (target == null || ctx.world.isRemote) return;
            // 5 / 6 / 7 seconds. Bleed ignores armor entirely, so the window has to
            // stay short or a single application out-damages everything else here.
            // The per-stack damage scales with the hit: a flat half-heart was
            // invisible against this pack's health pools.
            float perStack = Math.max(PER_STACK_FLOOR, ctx.damage * PER_STACK_OF_HIT);
            TickedEffects.addBleed(target, ctx.user, 80 + (20 * ctx.level), ctx.level + 1, perStack);
        }
    }

    /** Damage leaps to nearby enemies. */
    public static class Arc extends QFEnchantment {
        private static final double RANGE = 5.0D;

        public Arc(int id) {
            super(id, "qf.arc", Rarity.EPIC, EnchantCategory.WEAPON, 3);
        }

        @Override
        public int getProcChance(int level) {
            return 10 + (5 * level);
        }

        @Override
        @SuppressWarnings("unchecked")
        public void onAttack(ProcContext ctx) {
            EntityLivingBase struck = ctx.livingTarget();
            if (struck == null || ctx.world.isRemote || ctx.user == null) return;

            AxisAlignedBB box = struck.boundingBox.expand(RANGE, RANGE / 2, RANGE);
            List<EntityLivingBase> nearby =
                    ctx.world.getEntitiesWithinAABB(EntityLivingBase.class, box);

            float chained = ctx.damage * 0.35F;
            int hits = 0;
            // The chained hits name the wielder as their source, which would make
            // each one look like a fresh swing to the event bridge. The guard
            // keeps them from re-rolling every on-hit enchantment.
            CombatState.enter();
            try {
                for (EntityLivingBase e : nearby) {
                    if (e == struck) continue;
                    if (!Hostility.canTarget(e, ctx.user)) continue;
                    if (hits++ >= ctx.level) break;
                    e.attackEntityFrom(DamageSource.causeIndirectMagicDamage(ctx.user, ctx.user), chained);
                }
            } finally {
                CombatState.exit();
            }
        }
    }

    /**
     * Knocks the weapon out of whatever you hit.
     *
     * Works on players as well as mobs, but at half the chance: losing your sword
     * mid-fight matters far more to someone who chose it than to a zombie that
     * spawned holding one.
     */
    public static class Disarm extends QFEnchantment {
        public Disarm(int id) {
            super(id, "qf.disarm", Rarity.UNCOMMON, EnchantCategory.WEAPON, 3);
        }

        @Override
        public int getProcChance(int level) {
            return 4 * level;   // 4 / 8 / 12% on mobs; halved below for players
        }

        @Override
        public void onAttack(ProcContext ctx) {
            if (ctx.world.isRemote) return;

            if (ctx.target instanceof EntityPlayer) {
                if (!Hostility.pvpAllowed()) return;
                // The dispatcher has already rolled at the mob rate, so one further
                // coin flip is exactly half of it: 2 / 4 / 6%.
                if (ctx.rand.nextBoolean()) return;
                disarmPlayer(ctx, (EntityPlayer) ctx.target);
                return;
            }

            if (!(ctx.target instanceof EntityLiving)) return;
            // A CustomNPC that respawns holding its weapon would be a weapon
            // printer; tamed animals and our own summons are not fair game either.
            if (Hostility.isProtectedBystander((EntityLiving) ctx.target)) return;

            EntityLiving mob = (EntityLiving) ctx.target;
            ItemStack held = mob.getEquipmentInSlot(0);
            if (held == null) return;

            mob.setCurrentItemOrArmor(0, null);
            drop(ctx, mob.posX, mob.posY + 0.5D, mob.posZ, held);
        }

        /** Empties the player's selected hotbar slot onto the floor. */
        private static void disarmPlayer(ProcContext ctx, EntityPlayer victim) {
            int slot = victim.inventory.currentItem;
            ItemStack held = victim.inventory.mainInventory[slot];
            if (held == null) return;

            victim.inventory.mainInventory[slot] = null;
            victim.inventory.markDirty();
            drop(ctx, victim.posX, victim.posY + 0.5D, victim.posZ, held);
        }

        private static void drop(ProcContext ctx, double x, double y, double z, ItemStack stack) {
            EntityItem dropped = new EntityItem(ctx.world, x, y, z, stack);
            // Long enough that they cannot simply walk back over it mid-swing.
            dropped.delayBeforeCanPickup = 20;
            ctx.world.spawnEntityInWorld(dropped);
        }
    }

    /** Extra damage against something that has not noticed you. */
    public static class Assassinate extends QFEnchantment {
        public Assassinate(int id) {
            super(id, "qf.assassinate", Rarity.RARE, EnchantCategory.WEAPON, 3);
        }

        @Override
        public boolean isMultipliable() {
            return false;   // conditional multiplier; a replay would square it
        }

        @Override
        public Phase getPhase() {
            return Phase.MULTIPLIER;
        }

        @Override
        public void onAttack(ProcContext ctx) {
            if (!(ctx.target instanceof EntityLiving) || ctx.user == null) return;

            // The target must genuinely not have noticed you. Sneaking used to
            // count on its own, which made this a permanent damage multiplier for
            // anyone willing to walk around crouched.
            EntityLiving mob = (EntityLiving) ctx.target;
            if (mob.getAttackTarget() == ctx.user) return;

            ctx.damage *= 1.0F + (0.25F * ctx.level);
        }
    }

    /** Leaves the target easier to hurt for a few seconds. */
    public static class Sunder extends QFEnchantment {
        public Sunder(int id) {
            super(id, "qf.sunder", Rarity.UNCOMMON, EnchantCategory.WEAPON, 3);
        }

        @Override
        public int getProcChance(int level) {
            return 10 * level;
        }

        @Override
        public void onAttack(ProcContext ctx) {
            EntityLivingBase target = ctx.livingTarget();
            if (target == null || ctx.world.isRemote) return;
            // 1.7.10 has no armor attribute to strip, so this approximates it with
            // a damage debuff plus a mining slowdown.
            // Vanilla Weakness is a flat -0.5 damage per level, which is nothing
            // against this pack's weapons, so the damage half goes through our own
            // percentage-based cripple instead.
            int duration = 60 + (20 * ctx.level);
            // Deliberately below Cripple's 20% ceiling: Sunder is an Uncommon whose
            // damage cut is a side effect, and it should not out-debuff the Rare
            // whose whole purpose that is.
            TickedEffects.addCripple(target, 0.05F * ctx.level, duration);   // 5/10/15%
            target.addPotionEffect(new PotionEffect(Potion.digSlowdown.id, duration, ctx.level - 1));
        }
    }

    /**
     * A burst of strength.
     *
     * Originally specced as a swing-speed buff, which 1.7.10 cannot express: there
     * is no attack-speed attribute and no swing cooldown. Strength delivers the
     * same "you are suddenly dangerous" feel with a mechanic that exists.
     */
    public static class Rage extends QFEnchantment {
        public Rage(int id) {
            super(id, "qf.rage", Rarity.EPIC, EnchantCategory.WEAPON, 3);
        }

        @Override
        public int getProcChance(int level) {
            return 5 * level;
        }

        @Override
        public void onAttack(ProcContext ctx) {
            if (ctx.user == null || ctx.world.isRemote) return;
            // Fixed at Strength I. In 1.7.10 Strength is MULTIPLICATIVE --
            // 1.3 x (amplifier + 1) applied to the total -- so I is already x2.3
            // damage and III would be x4.9. The level buys duration, not strength.
            ctx.user.addPotionEffect(new PotionEffect(
                    Potion.damageBoost.id, 40 + (40 * ctx.level), 0));
        }
    }

    /**
     * The target hits softer for a while. No slow -- this is purely a damage
     * debuff.
     *
     * Vanilla Weakness cannot express this: in 1.7.10 it is a flat -0.5 damage per
     * level, which against a modded weapon swinging for twenty-five is a rounding
     * error. So the reduction is tracked in TickedEffects and applied as a
     * percentage in the event bridge, where the crippled entity's own attacks pass
     * through.
     */
    public static class Cripple extends QFEnchantment {
        /** Fraction of the target's outgoing damage removed. Tops out at 20%. */
        private static final float PER_LEVEL = 0.05F;

        public Cripple(int id) {
            super(id, "qf.cripple", Rarity.RARE, EnchantCategory.WEAPON, 3);
        }

        @Override
        public int getProcChance(int level) {
            return 10 * level;
        }

        @Override
        public void onAttack(ProcContext ctx) {
            EntityLivingBase target = ctx.livingTarget();
            if (target == null || ctx.world.isRemote) return;

            int duration = 80 + (40 * ctx.level);   // 6 / 8 / 10 seconds
            TickedEffects.addCripple(target, PER_LEVEL * (ctx.level + 1), duration);   // 10/15/20%
        }
    }

    /**
     * Makes every affliction already on the target worse.
     *
     * The proc chance is flat across levels; what the level buys is a higher
     * ceiling. Each level raises the cap by two, so level 1 can drive an effect to
     * IV, level 2 to VI and level 3 to VIII -- and nothing can be walked past that
     * by hitting the same target all afternoon.
     */
    public static class Accelerant extends QFEnchantment {
        private static final int PROC = 12;

        public Accelerant(int id) {
            super(id, "qf.accelerant", Rarity.RARE, EnchantCategory.WEAPON, 3);
        }

        @Override
        public int getProcChance(int level) {
            return PROC;
        }

        /** Amplifier ceiling: 3, 5, 7 -- displayed in game as IV, VI, VIII. */
        private static int ceiling(int level) {
            return (2 * level) + 1;
        }

        /**
         * Wither stops at IV whatever the level. Wither ticks every 40 >> amplifier
         * ticks: IV is 4 damage a second, V is 10, and VI and above tick every game
         * tick for 20 armor-bypassing damage a second, which is a death sentence
         * for anything. Poison has the same curve but stops at half a heart and
         * cannot touch undead, so it keeps the full ceiling.
         */
        private static final int WITHER_CEILING = 3;

        private static int ceilingFor(Potion potion, int level) {
            int cap = ceiling(level);
            return potion == Potion.wither ? Math.min(cap, WITHER_CEILING) : cap;
        }

        @Override
        @SuppressWarnings("unchecked")
        public void onAttack(ProcContext ctx) {
            EntityLivingBase target = ctx.livingTarget();
            if (target == null || ctx.world.isRemote) return;

            for (Object o : target.getActivePotionEffects().toArray()) {
                PotionEffect effect = (PotionEffect) o;
                Potion potion = Potion.potionTypes[effect.getPotionID()];
                if (potion == null || !potion.isBadEffect()) continue;

                int cap = ceilingFor(potion, ctx.level);
                int amplifier = Math.min(cap, effect.getAmplifier() + ctx.level);
                if (amplifier <= effect.getAmplifier()
                        && effect.getAmplifier() >= cap) {
                    // Already at this level's ceiling: extend it, but do not
                    // pointlessly re-apply the same strength every hit.
                    amplifier = effect.getAmplifier();
                }

                target.addPotionEffect(new PotionEffect(
                        effect.getPotionID(),
                        effect.getDuration() + (40 * ctx.level),
                        amplifier));
            }
        }
    }

    /** Killing something leaves you briefly hardier. */
    public static class Lich extends QFEnchantment {
        /** Absorption. 1.7.10 exposes no named constant for it. */
        private static final int ABSORPTION = 22;

        public Lich(int id) {
            super(id, "qf.lich", Rarity.EPIC, EnchantCategory.WEAPON, 3);
        }

        @Override
        public void onKill(ProcContext ctx) {
            if (ctx.user == null || ctx.world.isRemote) return;
            if (Potion.potionTypes[ABSORPTION] == null) return;
            ctx.user.addPotionEffect(new PotionEffect(
                    ABSORPTION, 300 + (100 * ctx.level), ctx.level - 1));
        }
    }

    /** The chase item: permanently buffed, and hits harder. */
    public static class Excalibur extends QFEnchantment {
        public Excalibur(int id) {
            super(id, "qf.excalibur", Rarity.LEGENDARY, EnchantCategory.WEAPON, 1);
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
        public void onTick(ProcContext ctx) {
            if (ctx.user == null || ctx.world.isRemote) return;
            if (ctx.user.ticksExisted % 40 != 0) return;
            ctx.user.addPotionEffect(new PotionEffect(Potion.damageBoost.id, 200, 0, true));
            ctx.user.addPotionEffect(new PotionEffect(Potion.resistance.id, 200, 0, true));
            ctx.user.addPotionEffect(new PotionEffect(Potion.moveSpeed.id, 200, 0, true));
        }

        @Override
        public void onAttack(ProcContext ctx) {
            ctx.damage += 4.0F;
        }
    }

    /** The item simply does not wear out. */
    public static class DemonForged extends QFEnchantment {
        public DemonForged(int id) {
            super(id, "qf.demonforged", Rarity.LEGENDARY, EnchantCategory.ANY, 1);
        }

        @Override
        public boolean isMultipliable() {
            return false;
        }

        @Override
        public void onTick(ProcContext ctx) {
            // 1.7.10 honours the vanilla Unbreakable tag (ItemStack line 230), so
            // setting it is enough -- no need to intercept durability loss.
            // DemonForgedUpkeep owns both writing it and taking it back off if the
            // enchantment is ever removed.
            com.questforge.content.ench.DemonForgedUpkeep.mark(ctx.stack);
        }
    }

    // ---- Summons ---------------------------------------------------------

    /** Shared behaviour for the three "call for help" enchantments. */
    private abstract static class SummonEnchant extends QFEnchantment {
        SummonEnchant(int id, String name, Rarity rarity, int maxLevel) {
            super(id, name, rarity, EnchantCategory.WEAPON, maxLevel);
        }

        protected abstract EntityLiving create(ProcContext ctx);

        @Override
        public int getProcChance(int level) {
            return 3 * level;
        }

        @Override
        public void onAttack(ProcContext ctx) {
            if (ctx.world.isRemote || ctx.user == null) return;

            EntityLiving ally = create(ctx);
            if (ally == null) return;

            ally.setPosition(ctx.user.posX + ctx.rand.nextDouble() * 2 - 1,
                    ctx.user.posY,
                    ctx.user.posZ + ctx.rand.nextDouble() * 2 - 1);

            EntityLivingBase target = ctx.livingTarget();
            if (target != null) ally.setAttackTarget(target);

            // Registered BEFORE it joins the world: the join event treats a tagged
            // summon that nobody is tracking as an orphan from a previous session.
            TickedEffects.addSummon(ally, ctx.user, target, 400 + (200 * ctx.level));
            ctx.world.spawnEntityInWorld(ally);
            ctx.world.playSoundAtEntity(ally, "mob.endermen.portal", 0.8F, 0.8F);
        }
    }

    /** Calls up the restless dead. */
    public static class Necromancer extends SummonEnchant {
        public Necromancer(int id) {
            super(id, "qf.necromancer", Rarity.RARE, 3);
        }

        @Override
        protected EntityLiving create(ProcContext ctx) {
            return ctx.rand.nextBoolean()
                    ? new EntityZombie(ctx.world)
                    : new EntitySkeleton(ctx.world);
        }
    }

    /** Calls the pack. */
    public static class Alpha extends SummonEnchant {
        public Alpha(int id) {
            super(id, "qf.alpha", Rarity.RARE, 3);
        }

        @Override
        protected EntityLiving create(ProcContext ctx) {
            EntityWolf wolf = new EntityWolf(ctx.world);
            if (ctx.user instanceof EntityPlayer) {
                wolf.setTamed(true);
                wolf.func_152115_b(ctx.user.getUniqueID().toString());
            }
            return wolf;
        }
    }

    /** Calls something considerably heavier. */
    public static class Bastion extends SummonEnchant {
        public Bastion(int id) {
            super(id, "qf.bastion", Rarity.EPIC, 3);
        }

        @Override
        protected EntityLiving create(ProcContext ctx) {
            EntityIronGolem golem = new EntityIronGolem(ctx.world);
            // Player-created, so it never picks a fight with a bystander on its own.
            // It still hits players, because TickedEffects assigns its target
            // outright each tick rather than leaving it to golem AI -- which only
            // ever selects IMob and would otherwise ignore a player entirely.
            golem.setPlayerCreated(true);
            return golem;
        }
    }

}
