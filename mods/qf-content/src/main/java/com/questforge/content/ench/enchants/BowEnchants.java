package com.questforge.content.ench.enchants;

import java.util.List;

import net.minecraft.entity.Entity;
import net.minecraft.entity.EntityLivingBase;
import net.minecraft.entity.player.EntityPlayer;
import net.minecraft.entity.projectile.EntityArrow;
import net.minecraft.potion.Potion;
import net.minecraft.potion.PotionEffect;
import net.minecraft.util.AxisAlignedBB;
import net.minecraft.util.Vec3;

import com.questforge.content.ench.ArrowContext;
import com.questforge.content.ench.ArrowTracker;
import com.questforge.content.ench.Cooldowns;
import com.questforge.content.ench.EnchantCategory;
import com.questforge.content.ench.Hostility;
import com.questforge.content.ench.ProcContext;
import com.questforge.content.ench.QFEnchantment;
import com.questforge.content.ench.Rarity;

/**
 * Bow enchantments.
 *
 * Arrows do not remember which bow fired them, so {@link ArrowTracker} tags each
 * arrow with the enchantments of the bow that launched it. Everything here reads
 * that tag rather than the bow.
 */
public class BowEnchants {

    /**
     * Whether a homing or ricocheting arrow should consider this entity.
     *
     * Excludes the shooter and anything tamed. Without this a guided arrow curves
     * into your own wolves, and a ricochet bounces off a mob straight into the
     * villager standing behind it.
     */
    static boolean isValidTarget(EntityLivingBase candidate, Entity shooter) {
        // Shared with Arc and Disarm: no players unless the server allows PvP,
        // nothing tamed, no CustomNPCs, none of our own summons.
        return Hostility.canTarget(candidate, shooter);
    }

    /** Ignores a fraction of the target's armor. */
    public static class Piercing extends QFEnchantment {
        public Piercing(int id) {
            super(id, "qf.piercing", Rarity.RARE, EnchantCategory.BOW, 3);
        }

        @Override
        public boolean isMultipliable() {
            return false;   // always-on multiplier
        }

        @Override
        public Phase getPhase() {
            return Phase.MULTIPLIER;
        }

        @Override
        public void onAttack(ProcContext ctx) {
            // Armor is applied after this event, so an increase here approximates
            // ignoring part of it without reaching into the armor calculation.
            ctx.damage *= 1.0F + (0.15F * ctx.level);   // x1.15 / x1.30 / x1.45
        }
    }

    /** Arrows pass through their target and keep going. */
    public static class Penetrating extends QFEnchantment {
        public Penetrating(int id) {
            super(id, "qf.penetrating", Rarity.RARE, EnchantCategory.BOW, 3);
        }

        @Override
        public void onArrowHit(ArrowContext ctx) {
            EntityArrow arrow = ctx.arrow;
            if (arrow == null || ctx.world.isRemote) return;
            if (ArrowTracker.pierceCount(arrow) >= ctx.level) return;

            ArrowTracker.incrementPierce(arrow);
            // Put it back in flight, slightly slowed, on the same heading.
            arrow.setDead();
            // Spawned slightly ahead along its own heading. Spawning it exactly where
            // the hit happened puts it inside the target's hitbox, where it can
            // immediately collide with the same entity again.
            double speed = Math.sqrt(arrow.motionX * arrow.motionX
                    + arrow.motionY * arrow.motionY
                    + arrow.motionZ * arrow.motionZ);
            double step = speed > 0.0001D ? (1.0D / speed) : 0.0D;

            EntityArrow next = new EntityArrow(ctx.world,
                    arrow.posX + (arrow.motionX * step),
                    arrow.posY + (arrow.motionY * step),
                    arrow.posZ + (arrow.motionZ * step));
            next.motionX = arrow.motionX * 0.85D;
            next.motionY = arrow.motionY * 0.85D;
            next.motionZ = arrow.motionZ * 0.85D;
            next.shootingEntity = arrow.shootingEntity;
            next.setDamage(arrow.getDamage() * 0.8D);
            ArrowTracker.copyTags(arrow, next);
            ArrowTracker.incrementPierce(next);
            ctx.world.spawnEntityInWorld(next);
        }
    }

    /** On hit, the arrow leaps to another nearby target. */
    public static class Ricochet extends QFEnchantment {
        private static final double SEARCH = 8.0D;

        public Ricochet(int id) {
            super(id, "qf.ricochet", Rarity.EPIC, EnchantCategory.BOW, 3);
        }

        @Override
        @SuppressWarnings("unchecked")
        public void onArrowHit(ArrowContext ctx) {
            EntityArrow arrow = ctx.arrow;
            if (arrow == null || ctx.world.isRemote) return;
            if (ArrowTracker.bounceCount(arrow) >= ctx.level) return;

            EntityLivingBase struck = ctx.livingTarget();
            AxisAlignedBB box = AxisAlignedBB.getBoundingBox(
                    arrow.posX - SEARCH, arrow.posY - SEARCH, arrow.posZ - SEARCH,
                    arrow.posX + SEARCH, arrow.posY + SEARCH, arrow.posZ + SEARCH);

            List<EntityLivingBase> nearby =
                    ctx.world.getEntitiesWithinAABB(EntityLivingBase.class, box);

            EntityLivingBase best = null;
            double bestDist = Double.MAX_VALUE;
            for (EntityLivingBase e : nearby) {
                if (e == struck || !isValidTarget(e, arrow.shootingEntity)) continue;
                double d = e.getDistanceSq(arrow.posX, arrow.posY, arrow.posZ);
                if (d < bestDist) {
                    bestDist = d;
                    best = e;
                }
            }
            if (best == null) return;

            EntityArrow next = new EntityArrow(ctx.world, arrow.posX, arrow.posY, arrow.posZ);
            Vec3 heading = Vec3.createVectorHelper(
                    best.posX - arrow.posX,
                    (best.posY + best.getEyeHeight()) - arrow.posY,
                    best.posZ - arrow.posZ).normalize();
            double speed = 1.2D;
            next.motionX = heading.xCoord * speed;
            next.motionY = heading.yCoord * speed;
            next.motionZ = heading.zCoord * speed;
            next.shootingEntity = arrow.shootingEntity;
            next.setDamage(arrow.getDamage() * 0.75D);
            ArrowTracker.copyTags(arrow, next);
            ArrowTracker.incrementBounce(next);
            ctx.world.spawnEntityInWorld(next);
        }
    }

    /** Slows whatever it hits. */
    public static class Bola extends QFEnchantment {
        public Bola(int id) {
            super(id, "qf.bola", Rarity.RARE, EnchantCategory.BOW, 3);
        }

        @Override
        public void onAttack(ProcContext ctx) {
            EntityLivingBase target = ctx.livingTarget();
            if (target == null || ctx.world.isRemote) return;
            target.addPotionEffect(new PotionEffect(
                    Potion.moveSlowdown.id, 80 + (40 * ctx.level), ctx.level - 1));
        }
    }

    /** Teleports you to wherever the arrow ends up. */
    public static class InstantTransmission extends QFEnchantment {
        public InstantTransmission(int id) {
            super(id, "qf.instanttransmission", Rarity.EPIC, EnchantCategory.BOW, 1);
        }

        @Override
        public boolean isMultipliable() {
            return false;
        }

        /** Short, but enough that a volley does not yank you three times over. */
        private static final int COOLDOWN = 60;   // 3 seconds

        @Override
        public void onArrowLand(ArrowContext ctx) {
            EntityArrow arrow = ctx.arrow;
            if (arrow == null || ctx.world.isRemote) return;
            Entity shooter = arrow.shootingEntity;
            if (!(shooter instanceof EntityPlayer)) return;

            EntityPlayer player = (EntityPlayer) shooter;
            if (!Cooldowns.isReady(player, "instanttransmission")) return;
            Cooldowns.start(player, "instanttransmission", COOLDOWN);

            // One block back along the arrow's own heading. The arrow's position is
            // the point it stuck in, which for a wall is inside the wall.
            double yaw = Math.toRadians(arrow.rotationYaw);
            double pitch = Math.toRadians(arrow.rotationPitch);
            double dx = -Math.sin(yaw) * Math.cos(pitch);
            double dy = -Math.sin(pitch);
            double dz = Math.cos(yaw) * Math.cos(pitch);

            player.setPositionAndUpdate(arrow.posX - dx, arrow.posY - dy + 0.5D, arrow.posZ - dz);
            player.fallDistance = 0F;
            ctx.world.playSoundAtEntity(player, "mob.endermen.portal", 1.0F, 1.0F);
        }
    }

    /** Swaps you with whatever you hit. */
    public static class SoulEntwine extends QFEnchantment {
        /** Short: swapping places is disruptive, not decisive. */
        private static final int COOLDOWN = 100;   // 5 seconds

        public SoulEntwine(int id) {
            super(id, "qf.soulentwine", Rarity.RARE, EnchantCategory.BOW, 1);
        }

        @Override
        public boolean isMultipliable() {
            return false;
        }

        @Override
        public void onAttack(ProcContext ctx) {
            EntityLivingBase target = ctx.livingTarget();
            if (target == null || ctx.world.isRemote) return;
            if (!(ctx.user instanceof EntityPlayer)) return;

            EntityPlayer player = (EntityPlayer) ctx.user;
            if (!Cooldowns.isReady(player, "soulentwine")) return;
            Cooldowns.start(player, "soulentwine", COOLDOWN);

            double px = player.posX, py = player.posY, pz = player.posZ;

            player.setPositionAndUpdate(target.posX, target.posY, target.posZ);
            target.setPositionAndUpdate(px, py, pz);
            player.fallDistance = 0F;
            ctx.world.playSoundAtEntity(player, "mob.endermen.portal", 1.0F, 1.0F);
        }
    }

    /** Arrows steer themselves toward whatever you were aiming near. */
    public static class Homing extends QFEnchantment {
        public Homing(int id) {
            super(id, "qf.homing", Rarity.LEGENDARY, EnchantCategory.BOW, 3);
        }

        @Override
        public boolean isMultipliable() {
            return false;
        }

        @Override
        @SuppressWarnings("unchecked")
        public void onArrowTick(ArrowContext ctx) {
            EntityArrow arrow = ctx.arrow;
            if (arrow == null || ctx.world.isRemote || arrow.onGround) return;

            double range = 6.0D + (3.0D * ctx.level);
            AxisAlignedBB box = AxisAlignedBB.getBoundingBox(
                    arrow.posX - range, arrow.posY - range, arrow.posZ - range,
                    arrow.posX + range, arrow.posY + range, arrow.posZ + range);

            List<EntityLivingBase> nearby =
                    ctx.world.getEntitiesWithinAABB(EntityLivingBase.class, box);

            EntityLivingBase best = null;
            double bestDist = Double.MAX_VALUE;
            for (EntityLivingBase e : nearby) {
                if (!isValidTarget(e, arrow.shootingEntity)) continue;
                double d = e.getDistanceSq(arrow.posX, arrow.posY, arrow.posZ);
                if (d < bestDist) {
                    bestDist = d;
                    best = e;
                }
            }
            if (best == null) return;

            double speed = Math.sqrt(arrow.motionX * arrow.motionX
                    + arrow.motionY * arrow.motionY
                    + arrow.motionZ * arrow.motionZ);
            if (speed < 0.1D) return;

            Vec3 toTarget = Vec3.createVectorHelper(
                    best.posX - arrow.posX,
                    (best.posY + best.getEyeHeight()) - arrow.posY,
                    best.posZ - arrow.posZ).normalize();

            // Blend heading toward the target rather than snapping, so it curves.
            double turn = 0.10D * ctx.level;
            arrow.motionX = (arrow.motionX * (1 - turn)) + (toTarget.xCoord * speed * turn);
            arrow.motionY = (arrow.motionY * (1 - turn)) + (toTarget.yCoord * speed * turn);
            arrow.motionZ = (arrow.motionZ * (1 - turn)) + (toTarget.zCoord * speed * turn);
        }
    }
}
