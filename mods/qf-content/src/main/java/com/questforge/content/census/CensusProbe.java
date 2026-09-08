package com.questforge.content.census;

import java.lang.reflect.Field;
import java.util.UUID;

import com.mojang.authlib.GameProfile;

import net.minecraft.entity.SharedMonsterAttributes;
import net.minecraft.entity.ai.attributes.IAttributeInstance;
import net.minecraft.entity.monster.EntityZombie;
import net.minecraft.entity.player.EntityPlayer;
import net.minecraft.item.ItemStack;
import net.minecraft.util.DamageSource;
import net.minecraft.world.WorldServer;

import net.minecraftforge.common.util.FakePlayer;

import com.questforge.content.QuestForgeContent;

/**
 * The player that everything in the census gets measured against.
 *
 * Forge's own {@link FakePlayer} cannot be used as-is, and the reason is worth
 * writing down because it would have gone unnoticed:
 * {@code FakePlayer.isEntityInvulnerable()} returns true. Every mob asked to
 * attack one deals exactly zero, and a census built on it produces a full file of
 * neatly formatted zeroes that look like measurements. So this subclasses it and
 * turns that off.
 *
 * There is a second trap in the same path. {@code EntityPlayerMP.attackEntityFrom}
 * refuses damage while {@code field_147101_bU} -- the post-respawn grace timer --
 * is above zero, and a freshly constructed EntityPlayerMP has it set. It is reset
 * on every probe below.
 *
 * And a third, which is not a bug but a fact the whole balance model depends on:
 * {@code DamageSource.causeMobDamage} is difficulty-scaled. On Easy a mob's swing
 * arrives as {@code amount / 2 + 1}, on Hard as {@code amount * 3 / 2}. A mob
 * damage figure without a difficulty attached to it is not a number. The
 * difficulty in force is recorded with every run.
 */
public final class CensusProbe {

    private CensusProbe() {}

    /** Large enough that nothing in this pack can kill the probe in one swing. */
    private static final double PROBE_HEALTH = 1000000.0D;

    private static ProbePlayer instance;

    /** A FakePlayer that can actually be hurt. */
    public static class ProbePlayer extends FakePlayer {
        public ProbePlayer(WorldServer world) {
            super(world, new GameProfile(
                    UUID.nameUUIDFromBytes("qf-census-probe".getBytes()), "QFCensusProbe"));
        }

        @Override
        public boolean isEntityInvulnerable() {
            return false;
        }
    }

    public static EntityPlayer player(WorldServer world) {
        try {
            if (instance == null || instance.worldObj != world) {
                instance = new ProbePlayer(world);
                IAttributeInstance health = instance.getEntityAttribute(SharedMonsterAttributes.maxHealth);
                if (health != null) health.setBaseValue(PROBE_HEALTH);
            }
            return instance;
        } catch (Throwable t) {
            QuestForgeContent.log.error("[census] could not build the probe player", t);
            return null;
        }
    }

    /**
     * Puts the probe back to a known state: full health, no armour, no
     * invulnerability of any kind, standing where it is told.
     */
    public static void reset(EntityPlayer probe, double x, double y, double z) {
        if (probe == null) return;
        probe.isDead = false;
        probe.deathTime = 0;
        probe.hurtResistantTime = 0;
        probe.hurtTime = 0;
        probe.fallDistance = 0.0F;
        probe.capabilities.disableDamage = false;
        probe.setHealth((float) PROBE_HEALTH);
        probe.setPosition(x, y, z);
        probe.motionX = probe.motionY = probe.motionZ = 0.0D;
        try {
            probe.clearActivePotions();
        } catch (Throwable ignored) {}
        for (int i = 0; i < probe.inventory.armorInventory.length; i++) {
            probe.inventory.armorInventory[i] = null;
        }
        clearRespawnGrace(probe);
    }

    /** Puts armour on the probe. Index 0 is boots, 3 is helmet, matching the inventory. */
    public static void wear(EntityPlayer probe, ItemStack[] armour) {
        if (probe == null) return;
        for (int i = 0; i < probe.inventory.armorInventory.length; i++) {
            probe.inventory.armorInventory[i] =
                    armour != null && i < armour.length && armour[i] != null ? armour[i].copy() : null;
        }
    }

    /** The weapon whose attribute modifiers are currently applied to the probe. */
    private static ItemStack held;

    /**
     * Puts a weapon in the probe's hand -- and, crucially, applies its attribute
     * modifiers by hand.
     *
     * A held item's damage does not come from the item at swing time. It comes
     * from the wielder's attackDamage attribute, and equipment modifiers are
     * folded into that attribute inside {@code EntityLivingBase.onUpdate}, which
     * FakePlayer overrides to do nothing. So a probe that simply holds a sword
     * swings for the bare-handed 1.0 and every weapon in the pack measures
     * identically. Applying the modifiers explicitly is what makes the weapon
     * real.
     */
    public static void hold(EntityPlayer probe, ItemStack weapon) {
        if (probe == null) return;
        try {
            if (held != null) {
                probe.getAttributeMap().removeAttributeModifiers(held.getAttributeModifiers());
            }
            held = null;
            probe.inventory.mainInventory[probe.inventory.currentItem] = null;

            if (weapon != null) {
                ItemStack copy = weapon.copy();
                probe.inventory.mainInventory[probe.inventory.currentItem] = copy;
                probe.getAttributeMap().applyAttributeModifiers(copy.getAttributeModifiers());
                held = copy;
            }
        } catch (Throwable t) {
            QuestForgeContent.log.warn("[census] could not equip probe weapon: " + t);
        }
    }

    /** What the probe would swing for right now, as the game computes it. */
    public static double attackDamage(EntityPlayer probe) {
        if (probe == null) return Double.NaN;
        try {
            IAttributeInstance a = probe.getEntityAttribute(SharedMonsterAttributes.attackDamage);
            return a == null ? Double.NaN : a.getAttributeValue();
        } catch (Throwable t) {
            return Double.NaN;
        }
    }

    public static void cleanup(EntityPlayer probe) {
        if (probe == null) return;
        reset(probe, probe.posX, probe.posY, probe.posZ);
    }

    /**
     * EntityPlayerMP refuses all damage while its post-respawn grace timer is
     * running, and a constructed one starts with it set. Without this every
     * measurement in the census is zero.
     */
    private static void clearRespawnGrace(EntityPlayer probe) {
        try {
            Field f = net.minecraft.entity.player.EntityPlayerMP.class
                    .getDeclaredField("field_147101_bU");
            f.setAccessible(true);
            f.setInt(probe, 0);
        } catch (Throwable ignored) {
            // Named differently in some mappings; the reset below is the fallback.
        }
    }

    /**
     * A sanity check with a known answer, run before the census is trusted.
     *
     * A vanilla zombie on Normal deals 3 damage and has 20 health. If the probe
     * reports anything else, the probe is broken and every number the census
     * produces is worthless -- which is exactly the failure this is here to catch,
     * because a broken probe fails silently and produces well-formed output.
     */
    public static String calibrate(WorldServer world) {
        StringBuilder sb = new StringBuilder();
        EntityZombie zombie = null;
        try {
            EntityPlayer probe = player(world);
            if (probe == null) return "FAILED: no probe player";

            double x = world.getSpawnPoint().posX + 0.5D;
            double z = world.getSpawnPoint().posZ + 0.5D;
            double y = world.getTopSolidOrLiquidBlock((int) x, (int) z) + 1;

            zombie = new EntityZombie(world);
            zombie.setPosition(x, y, z);
            world.spawnEntityInWorld(zombie);

            float health = zombie.getMaxHealth();
            sb.append("zombie max health ").append(CensusFile.num(health));
            sb.append(" (vanilla 20)");

            // Damage taken.
            zombie.hurtResistantTime = 0;
            float before = zombie.getHealth();
            zombie.attackEntityFrom(DamageSource.generic, 5.0F);
            float taken = before - zombie.getHealth();
            sb.append("; takes ").append(CensusFile.num(taken)).append(" from a raw 5 (vanilla 5)");

            // Damage dealt.
            reset(probe, x + 1.0D, y, z);
            float pBefore = probe.getHealth();
            zombie.attackEntityAsMob(probe);
            float dealt = pBefore - probe.getHealth();
            sb.append("; deals ").append(CensusFile.num(dealt))
              .append(" to an unarmoured player (vanilla 3 on Normal, 2.5 on Easy, 4.5 on Hard)");

            // The weapon half of the pipeline, which has its own silent failure:
            // if the held item's attribute modifiers are not applied, every
            // weapon in the pack measures as a bare fist and nothing says so.
            reset(probe, x + 1.0D, y, z);
            hold(probe, new ItemStack(net.minecraft.init.Items.diamond_sword));
            double swordAttr = attackDamage(probe);
            sb.append("; diamond sword attribute ").append(CensusFile.num(swordAttr))
              .append(" (1.0 base + 7.0 modifier = 8.0; a 1.0 here means modifiers are not applying)");

            zombie.hurtResistantTime = 0;
            zombie.setHealth(zombie.getMaxHealth());
            float zBefore = zombie.getHealth();
            probe.attackTargetEntityWithCurrentItem(zombie);
            float swing = zBefore - zombie.getHealth();
            sb.append("; diamond sword swing lands ").append(CensusFile.num(swing))
              .append(" on a zombie (2 armour points)");
            hold(probe, null);

            sb.append("; difficulty ").append(world.difficultySetting);

            if (swordAttr <= 1.01D) {
                sb.insert(0, "FAILED (weapon modifiers not applying): ");
            } else if (dealt <= 0.0F) {
                sb.insert(0, "FAILED (probe takes no damage): ");
            } else if (taken <= 0.0F) {
                sb.insert(0, "FAILED (mob takes no damage): ");
            } else {
                sb.insert(0, "OK: ");
            }
        } catch (Throwable t) {
            return "FAILED: " + t;
        } finally {
            if (zombie != null) {
                try {
                    zombie.setDead();
                    world.removeEntity(zombie);
                } catch (Throwable ignored) {}
            }
        }
        return sb.toString();
    }
}
