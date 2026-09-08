package com.questforge.content.ench.enchants;

import net.minecraft.enchantment.EnchantmentHelper;
import net.minecraft.entity.Entity;
import net.minecraft.entity.EntityLivingBase;
import net.minecraft.entity.player.EntityPlayer;
import net.minecraft.item.ItemStack;
import net.minecraft.item.ItemSword;
import net.minecraft.potion.Potion;
import net.minecraft.potion.PotionEffect;
import net.minecraft.util.DamageSource;

import com.questforge.content.ench.Cooldowns;
import com.questforge.content.ench.EnchantCategory;
import com.questforge.content.ench.Mitigation;
import com.questforge.content.ench.ProcContext;
import com.questforge.content.ench.QFEnchantment;
import com.questforge.content.ench.QFEnchantments;
import com.questforge.content.ench.Rarity;

/**
 * Armor enchantments.
 *
 * An armor enchantment's hook runs once for EVERY equipped piece carrying it, so
 * each one here has to declare which model it is using:
 *
 *   slot-locked -- the category is a single slot, so it can only ever be on one
 *                  piece and the values are the whole effect.
 *   per-piece   -- the category is ARMOR and wearing more of it does more. These
 *                  are balanced for a full set, and any that set velocity or a
 *                  stat directly must be idempotent, because they will run four
 *                  times for the same hit.
 */
public class ArmorEnchants {

    /**
     * Damage reduction that grows as your health falls.
     *
     * Chestplate only, so the value is the whole effect: at 0 health it is
     * 10% per level, reaching 30% at level 3. At full health it does nothing.
     */
    public static class Bulwark extends QFEnchantment {
        private static final float PER_LEVEL = 0.10F;

        public Bulwark(int id) {
            super(id, "qf.bulwark", Rarity.RARE, EnchantCategory.CHESTPLATE, 3);
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

        @Override
        public void onDamaged(ProcContext ctx) {
            if (ctx.user == null) return;
            float max = ctx.user.getMaxHealth();
            if (max <= 0) return;

            float missing = 1.0F - (ctx.user.getHealth() / max);
            ctx.damage *= (1.0F - (PER_LEVEL * ctx.level * missing));
        }
    }

    /**
     * Chance to shrug off a negative effect when something hits you.
     *
     * Leggings only. If what it clears is Tank's permanent slowness, Tank is told
     * to leave it off for a while rather than re-applying it two seconds later --
     * that interaction is the point of running both.
     */
    public static class Cleansing extends QFEnchantment {
        public Cleansing(int id) {
            super(id, "qf.cleansing", Rarity.RARE, EnchantCategory.LEGGINGS, 3);
        }

        @Override
        public int getProcChance(int level) {
            return 10 * level;
        }

        @Override
        @SuppressWarnings("unchecked")
        public void onDamaged(ProcContext ctx) {
            if (ctx.user == null || ctx.world.isRemote) return;

            for (Object o : ctx.user.getActivePotionEffects().toArray()) {
                PotionEffect effect = (PotionEffect) o;
                Potion potion = Potion.potionTypes[effect.getPotionID()];
                if (potion == null || !potion.isBadEffect()) continue;

                ctx.user.removePotionEffect(effect.getPotionID());

                if (effect.getPotionID() == Potion.moveSlowdown.id
                        && ctx.user instanceof EntityPlayer) {
                    PotionEnchants.Tank.suppressSlowness((EntityPlayer) ctx.user);
                }
                return;   // one per hit
            }
        }
    }

    /**
     * Cuts damage from falling and explosions. Per-piece: wearing more of it
     * survives a longer drop, which is the right shape for this one.
     */
    public static class Stonehide extends QFEnchantment {
        public Stonehide(int id) {
            super(id, "qf.stonehide", Rarity.UNCOMMON, EnchantCategory.ARMOR, 3);
        }

        @Override
        public boolean isMultipliable() {
            return false;
        }

        /** Before Cockroach, so its "would this kill me" test sees this reduction. */
        @Override
        public Phase getPhase() {
            return Phase.MULTIPLIER;
        }

        @Override
        public void onDamaged(ProcContext ctx) {
            if (ctx.source == null) return;
            boolean applies = ctx.source.isExplosion() || ctx.source == DamageSource.fall;
            if (!applies) return;

            ctx.damage *= (1.0F - (0.12F * ctx.level / 4.0F));
        }
    }

    /** Shoves attackers off you. No damage, just distance. Per-piece. */
    public static class Rebound extends QFEnchantment {
        public Rebound(int id) {
            super(id, "qf.rebound", Rarity.COMMON, EnchantCategory.ARMOR, 3);
        }

        @Override
        public int getProcChance(int level) {
            // Per piece. A full set works out at roughly 8 / 16 / 23% per hit.
            return 2 * level;
        }

        @Override
        public void onDamaged(ProcContext ctx) {
            if (ctx.target == null || ctx.user == null) return;
            // Slightly harder than it was, and with more lift. The shove is only
            // worth anything if the attacker spends time getting back to you, and
            // distance comes from airtime as much as from horizontal speed -- the
            // old 0.3 of lift put them back in range before the next swing.
            knockAway(ctx.user, ctx.target, 0.75D + (0.25D * ctx.level), 0.42D);
        }
    }

    /**
     * Reflect throws attackers considerably further, and how far is decided by how
     * many pieces of it you are wearing: two blocks and one block of height per
     * piece, so a full set is eight blocks back and four in the air.
     *
     * It has to SET the attacker's velocity rather than add to it. The hook runs
     * once per equipped piece, so adding would compound to four times the intended
     * launch; assigning makes the four calls agree on one answer.
     */
    public static class Reflect extends QFEnchantment {
        private static final double BLOCKS_PER_PIECE = 2.0D;
        private static final double HEIGHT_PER_PIECE = 1.0D;

        /**
         * Horizontal distance covered per unit of launch velocity, given the
         * airtime a launch of this height produces. Derived from vanilla's 0.08
         * gravity and 0.91 air drag; approximate, and worth tuning by feel.
         */
        private static final double BLOCKS_PER_VELOCITY = 9.6D;

        public Reflect(int id) {
            super(id, "qf.reflect", Rarity.EPIC, EnchantCategory.ARMOR, 3);
        }

        @Override
        public int getProcChance(int level) {
            return 4 + (4 * level);   // 8 / 12 / 16% per piece
        }

        @Override
        public void onDamaged(ProcContext ctx) {
            if (ctx.target == null || ctx.user == null) return;

            int pieces = piecesCarrying(ctx.user, this.effectId);
            if (pieces <= 0) pieces = 1;

            double blocks = BLOCKS_PER_PIECE * pieces;
            double height = HEIGHT_PER_PIECE * pieces;

            launch(ctx.user, ctx.target,
                    blocks / BLOCKS_PER_VELOCITY,
                    Math.sqrt(2.0D * 0.08D * height));
        }
    }

    /**
     * Heavy damage reduction while you are not holding a weapon.
     *
     * Per-piece at 33% each. Four pieces compound to 1 - 0.67^4, which is 80% --
     * the figure that was agreed. The obvious 20% per piece only reaches 59%,
     * because reductions multiply rather than add.
     */
    public static class Turtle extends QFEnchantment {
        private static final float PER_PIECE = 0.33F;

        public Turtle(int id) {
            super(id, "qf.turtle", Rarity.LEGENDARY, EnchantCategory.ARMOR, 1);
        }

        @Override
        public boolean isMultipliable() {
            return false;   // 33% per piece twice is 55% per piece
        }

        /** Before Cockroach, so its "would this kill me" test sees this reduction. */
        @Override
        public Phase getPhase() {
            return Phase.MULTIPLIER;
        }

        @Override
        public void onDamaged(ProcContext ctx) {
            if (!(ctx.user instanceof EntityPlayer)) return;
            EntityPlayer player = (EntityPlayer) ctx.user;

            // "Not holding a weapon" means any weapon: swords, axes, bows, and the
            // modded guns and blades the whitelist admits. Checking only ItemSword
            // made a Turtle archer the strongest build in the mod.
            ItemStack held = player.getHeldItem();
            if (held != null && (EnchantCategory.WEAPON.accepts(held)
                    || EnchantCategory.BOW.accepts(held))) {
                return;
            }

            ctx.damage *= (1.0F - PER_PIECE);
        }

        /**
         * However good the shell, something always gets through.
         *
         * A full set multiplies incoming damage by 0.2, and on top of enchanted
         * diamond that took a forty-damage swing down to 0.22 of a health point.
         * Natural regeneration is one health every four seconds, or 0.25 a second,
         * so the wearer simply out-healed everything in the pack and could not be
         * killed at all. Turtle is meant to be very hard to kill, not impossible.
         *
         * So while Turtle is active, a hit always delivers at least a quarter of a
         * heart. Against anything swinging once a second that is 0.5 a second,
         * comfortably ahead of regeneration, and a determined boss will eventually
         * get there. It only binds on the heaviest stacks: one or two pieces never
         * reduce a real hit that far.
         */
        public static final float MINIMUM_LANDED = 0.5F;

        /** Applied once, after every piece's reduction, from the event bridge. */
        public static float floorDamage(EntityPlayer player, DamageSource source, float amount) {
            QFEnchantment turtle = QFEnchantments.turtle;
            if (turtle == null || amount <= 0.0F) return amount;

            int pieces = 0;
            for (ItemStack piece : player.inventory.armorInventory) {
                if (piece != null
                        && EnchantmentHelper.getEnchantmentLevel(turtle.effectId, piece) > 0) {
                    pieces++;
                }
            }
            if (pieces == 0) return amount;

            // Not active with a weapon in hand, so it should not floor anything either.
            ItemStack held = player.getHeldItem();
            if (held != null && (EnchantCategory.WEAPON.accepts(held)
                    || EnchantCategory.BOW.accepts(held))) {
                return amount;
            }

            // predict is linear in the amount, so one probe gives the whole factor.
            float factor = Mitigation.predict(player, source, 1.0F);
            if (factor <= 0.0F) return amount;   // armor already total; nothing to do

            // The floor must never make Turtle worse than not wearing it. In the
            // pack's best armor a hit already lands for less than a quarter heart
            // before Turtle is involved, and a flat floor would then have this
            // enchantment INCREASE the damage taken. So the floor is whichever is
            // smaller: a quarter heart, or what the hit would have done anyway.
            float withoutTurtle = amount / (float) Math.pow(1.0F - PER_PIECE, pieces);
            float ceiling = Math.min(MINIMUM_LANDED / factor, withoutTurtle);
            return Math.max(amount, ceiling);
        }
    }

    /**
     * Answers an attacker with every affliction at once.
     *
     * The chance falls as the level rises, deliberately: a full set of Affliction I
     * procs about 3.8% of the time for level I debuffs, while a full set of
     * Affliction IV procs about 1% of the time for level IV debuffs. Seven
     * simultaneous debuffs at IV is a kill, so it has to stay rare.
     *
     * The roll is done here rather than through getProcChance because the per-piece
     * chances are fractions of a percent, and getProcChance is whole percent.
     */
    public static class Affliction extends QFEnchantment {
        /**
         * Per-piece chance in ten-thousandths, by level. Each is the fourth root of
         * the intended full-set chance, since four pieces each roll independently:
         * 3.8%, 2.9%, 1.9%, 1.0%.
         */
        private static final int[] PER_PIECE = { 97, 73, 49, 25 };

        public Affliction(int id) {
            super(id, "qf.affliction", Rarity.LEGENDARY, EnchantCategory.ARMOR, 4);
        }

        @Override
        public int getProcChance(int level) {
            return 100;   // the real roll is below, at finer resolution
        }

        @Override
        public void onDamaged(ProcContext ctx) {
            if (ctx.world.isRemote) return;
            EntityLivingBase attacker = ctx.target instanceof EntityLivingBase
                    ? (EntityLivingBase) ctx.target : null;
            if (attacker == null) return;

            int index = Math.max(0, Math.min(PER_PIECE.length - 1, ctx.level - 1));
            if (ctx.rand.nextInt(10000) >= PER_PIECE[index]) return;

            int duration = 100 + (40 * ctx.level);
            int amp = ctx.level - 1;   // level 1 gives I, level 4 gives IV

            attacker.addPotionEffect(new PotionEffect(Potion.poison.id, duration, amp));
            attacker.addPotionEffect(new PotionEffect(Potion.wither.id, duration, amp));
            attacker.addPotionEffect(new PotionEffect(Potion.blindness.id, duration, 0));
            attacker.addPotionEffect(new PotionEffect(Potion.confusion.id, duration, 0));
            attacker.addPotionEffect(new PotionEffect(Potion.weakness.id, duration, amp));
            attacker.addPotionEffect(new PotionEffect(Potion.moveSlowdown.id, duration, amp));
            attacker.addPotionEffect(new PotionEffect(Potion.digSlowdown.id, duration, amp));
        }
    }

    /**
     * Depth Strider, which 1.7.10 does not have.
     *
     * Vanilla's version raises water friction and acceleration toward their land
     * values in thirds, so level 3 swims at walking pace. 1.7.10 computes both
     * inside EntityLivingBase.moveEntityWithHeading with no hook, so this closes
     * the same gap from outside by scaling the motion that came out of it -- and
     * clamps the result to land sprint speed so it lands in the same place rather
     * than overshooting into rubber-banding.
     *
     * Boots only, exactly like the enchantment it is copying.
     */
    public static class Flippers extends QFEnchantment {
        /** Sprinting is roughly twice swimming speed; level 3 closes all of it. */
        private static final double LAND_GAP = 0.96D;
        /** Land sprint speed. The result is never allowed past this. */
        private static final double MAX_SPEED = 0.22D;

        public Flippers(int id) {
            super(id, "qf.flippers", Rarity.UNCOMMON, EnchantCategory.BOOTS, 3);
        }

        @Override
        public boolean isMultipliable() {
            return false;
        }

        /**
         * The server-side tick does nothing for players on purpose. A player's
         * client owns its own movement; motion written to the server-side copy is
         * never read back, so this ran every tick and moved nobody. The client
         * applies it to the local player instead (QFClientEvents), reading the
         * boots' NBT it already holds.
         */
        @Override
        public void onTick(ProcContext ctx) {
            if (ctx.user instanceof EntityPlayer) return;
            apply(ctx.user, ctx.level);
        }

        /** Shared by the server (non-players) and the client (the local player). */
        public static void apply(EntityLivingBase user, int level) {
            if (user == null || !user.isInWater()) return;

            double speed = Math.sqrt(user.motionX * user.motionX
                    + user.motionZ * user.motionZ);
            if (speed <= 0.01D) return;   // only assists movement already underway

            double boost = 1.0D + (LAND_GAP * Math.min(3, level) / 3.0D);
            double scaled = Math.min(MAX_SPEED, speed * boost);
            double factor = scaled / speed;

            user.motionX *= factor;
            user.motionZ *= factor;
        }
    }

    /** Mobs lose interest in you. Leggings only. */
    public static class Camouflage extends QFEnchantment {
        public Camouflage(int id) {
            super(id, "qf.camouflage", Rarity.RARE, EnchantCategory.LEGGINGS, 3);
        }

        @Override
        public int getProcChance(int level) {
            return 10 * level;   // capped at 30%
        }

        @Override
        public void onTargeted(ProcContext ctx) {
            ctx.cancelled = true;   // the bridge clears the mob's target
        }
    }

    /**
     * Survive what would have killed you, at the cost of the armor piece.
     *
     * 1.7.10 has no Totem of Undying, but LivingDeathEvent is cancelable, so the
     * same effect is straightforward to build by hand. Left per-piece: a full set
     * is four saves, each one paid for with a piece of armor.
     */
    public static class Sacrifice extends QFEnchantment {
        public Sacrifice(int id) {
            super(id, "qf.sacrifice", Rarity.RARE, EnchantCategory.ARMOR, 1);
        }

        @Override
        public boolean isMultipliable() {
            return false;
        }

        @Override
        public void onDeath(ProcContext ctx) {
            if (ctx.user == null || ctx.world.isRemote) return;

            ctx.user.setHealth(ctx.user.getMaxHealth() * 0.5F);
            ctx.user.clearActivePotions();
            ctx.user.addPotionEffect(new PotionEffect(Potion.regeneration.id, 200, 1));
            ctx.user.addPotionEffect(new PotionEffect(Potion.resistance.id, 200, 1));
            ctx.user.addPotionEffect(new PotionEffect(Potion.fireResistance.id, 400, 0));

            // Consume the piece that saved you.
            if (ctx.stack != null) ctx.stack.stackSize = 0;

            ctx.cancelled = true;   // the bridge cancels the death event
        }
    }

    // ---- Shared helpers --------------------------------------------------

    /** How many equipped armor pieces carry this enchantment. Slots 1-4. */
    static int piecesCarrying(EntityLivingBase wearer, int effectId) {
        int count = 0;
        for (int slot = 1; slot <= 4; slot++) {
            ItemStack piece = wearer.getEquipmentInSlot(slot);
            if (piece != null && EnchantmentHelper.getEnchantmentLevel(effectId, piece) > 0) {
                count++;
            }
        }
        return count;
    }

    /** Adds knockback. Used by Rebound, which is happy to stack. */
    private static void knockAway(EntityLivingBase victim, Entity attacker, double strength,
            double lift) {
        double dx = attacker.posX - victim.posX;
        double dz = attacker.posZ - victim.posZ;
        double dist = Math.sqrt(dx * dx + dz * dz);
        if (dist < 0.0001D) return;

        attacker.motionX += (dx / dist) * strength;
        attacker.motionZ += (dz / dist) * strength;
        attacker.motionY += lift;
        attacker.velocityChanged = true;
    }

    /**
     * Sets knockback outright. Used by Reflect, whose hook runs once per equipped
     * piece: assigning means four calls produce one launch rather than four.
     */
    private static void launch(EntityLivingBase victim, Entity attacker,
            double horizontal, double vertical) {
        double dx = attacker.posX - victim.posX;
        double dz = attacker.posZ - victim.posZ;
        double dist = Math.sqrt(dx * dx + dz * dz);
        if (dist < 0.0001D) return;

        attacker.motionX = (dx / dist) * horizontal;
        attacker.motionZ = (dz / dist) * horizontal;
        attacker.motionY = vertical;
        attacker.fallDistance = 0F;   // the launch itself should not kill it
        attacker.velocityChanged = true;
    }
}
