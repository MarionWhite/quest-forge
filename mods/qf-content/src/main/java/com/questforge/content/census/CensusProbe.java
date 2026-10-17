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

    /** A FakePlayer that can actually be hurt, and can hold a potion effect. */
    public static class ProbePlayer extends FakePlayer {
        public ProbePlayer(WorldServer world) {
            super(world, new GameProfile(
                    UUID.nameUUIDFromBytes("qf-census-probe".getBytes()), "QFCensusProbe"));
        }

        @Override
        public boolean isEntityInvulnerable() {
            return false;
        }

        // ---- Potion effects ------------------------------------------------
        //
        // EntityPlayerMP announces every potion change to its client, and the
        // three methods below do nothing else: onNewPotionEffect sends
        // S1DPacketEntityEffect, onFinishedPotionEffect sends S1EPacketRemoveEntityEffect.
        // On a player with no connection each one is a NullPointerException.
        //
        // That matters far more than it looks. Vanilla's addPotionEffect puts the
        // effect into activePotionsMap and THEN calls onNewPotionEffect, so the
        // effect really is applied and isPotionActive really does return true --
        // and the exception then unwinds out of addPotionEffect and abandons
        // whatever the caller was doing next. Excalibur's onTick applies Strength,
        // Resistance and Speed in that order; the probe was getting Strength, the
        // throw, and neither of the other two. The rest of that tick's work --
        // AttributeUpkeep, ReachUpkeep, DemonForgedUpkeep -- was abandoned with it.
        // Every tick-driven potion enchantment was therefore being measured as a
        // fraction of itself, and the only visible symptom was a warning line.
        //
        // Overriding them to drop the packet is right rather than expedient: the
        // effect is still applied, still ticks, still expires. The only thing
        // skipped is telling a client that does not exist.

        // Skipping the packet is right. Skipping what EntityLivingBase does in
        // the same methods was not, and it went unnoticed for four runs.
        //
        // EntityPlayerMP.onNewPotionEffect sends S1DPacketEntityEffect and then
        // calls super, and EntityLivingBase's version is what runs
        // applyAttributesModifiersToEntity -- the step that turns "has Strength"
        // into "+3 attack damage". Returning early on a null connection skipped
        // both, so every potion the probe received was recorded in
        // activePotionsMap and applied to nothing.
        //
        // The symptom was Rage: firing at a measured 15.1% against a declared
        // 15%, and contributing exactly 0.0000 damage in every run. The procs
        // were real, the Strength was real, and the attribute never moved. Every
        // enchantment that works by granting a potion was being measured as
        // nothing, which is a fault in this probe and not in the pack.
        //
        // Java has no way to call a grandparent implementation, so the attribute
        // half is done here explicitly, mirroring EntityLivingBase.

        @Override
        protected void onNewPotionEffect(net.minecraft.potion.PotionEffect effect) {
            if (this.playerNetServerHandler != null) {
                super.onNewPotionEffect(effect);
                return;
            }
            applyPotionAttributes(effect, true);
        }

        @Override
        protected void onChangedPotionEffect(net.minecraft.potion.PotionEffect effect,
                boolean recalculate) {
            if (this.playerNetServerHandler != null) {
                super.onChangedPotionEffect(effect, recalculate);
                return;
            }
            // A refreshed effect is removed and re-applied, so a stronger
            // amplifier replaces the weaker modifier instead of stacking with it.
            if (recalculate) applyPotionAttributes(effect, false);
            applyPotionAttributes(effect, true);
        }

        @Override
        protected void onFinishedPotionEffect(net.minecraft.potion.PotionEffect effect) {
            if (this.playerNetServerHandler != null) {
                super.onFinishedPotionEffect(effect);
                return;
            }
            applyPotionAttributes(effect, false);
        }

        // ---- Being picked up and put down ------------------------------------
        //
        // The Alpha Yeti's melee (EntityTFYetiAlpha.attackEntityAsMob) first
        // mounts its target on its shoulders, and its ThrowRider AI throws the
        // rider off a few ticks later. That is the fight a player has with it.
        // On the probe both halves were NullPointerExceptions, because
        // EntityPlayerMP does each through its connection:
        //   mountEntity        -> super, then sendPacket(S1BPacketEntityAttach)
        //                         and setPlayerLocation;
        //   setPositionAndUpdate -> playerNetServerHandler.setPlayerLocation,
        //                         which is where a dismount puts the player down.
        //
        // The mount NPE fired after the probe was already riding, inside
        // absorbHit's catch, so it was swallowed -- and it also abandoned the
        // rest of the Yeti's attackEntityAsMob, so its swing never landed. The
        // throw, a few ticks later, came from the Yeti's own entity tick, where
        // nothing catches: "Ticking entity" crash, Forge's removeErroringEntities
        // dismounted the probe again and crashed a second time, and the server
        // stopped with exit code 0 two seconds into the first cell. The campaign
        // saw a census.log that simply ends after the first swing (2026-10-17,
        // T1 Yeti singles, twice).
        //
        // Both are done here as the connection would do them, minus the packet:
        // setPlayerLocation's only effect on the server is to place the player.

        @Override
        public void setPositionAndUpdate(double x, double y, double z) {
            if (this.playerNetServerHandler != null) {
                super.setPositionAndUpdate(x, y, z);
                return;
            }
            this.setLocationAndAngles(x, y, z, this.rotationYaw, this.rotationPitch);
        }

        @Override
        public void mountEntity(net.minecraft.entity.Entity entity) {
            if (this.playerNetServerHandler != null) {
                super.mountEntity(entity);
                return;
            }
            // EntityPlayerMP.mountEntity is EntityPlayer.mountEntity followed by
            // the two connection calls; Java cannot skip a level, so the
            // mounting runs in full and the throw from the packet that follows
            // it is the only thing dropped.
            try {
                super.mountEntity(entity);
            } catch (NullPointerException expected) {
                if (this.playerNetServerHandler != null) throw expected;
            }
        }

        /** The attribute half of a potion coming or going. */
        private void applyPotionAttributes(net.minecraft.potion.PotionEffect effect,
                boolean adding) {
            try {
                net.minecraft.potion.Potion potion =
                        net.minecraft.potion.Potion.potionTypes[effect.getPotionID()];
                if (potion == null) return;
                if (adding) {
                    potion.applyAttributesModifiersToEntity(
                            this, this.getAttributeMap(), effect.getAmplifier());
                } else {
                    potion.removeAttributesModifiersFromEntity(
                            this, this.getAttributeMap(), effect.getAmplifier());
                }
            } catch (Throwable t) {
                QuestForgeContent.log.warn("[census] potion attribute update failed: " + t);
            }
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
        // A boss that carries its target (the Alpha Yeti) may still be holding
        // the probe, or a removed one may have left the link behind. And a
        // ridden probe is ticked by the world as its mount's rider, which files
        // it in a chunk's entity list, where area attacks find it; the probe is
        // otherwise never in the world. Each cell starts unmounted and unfiled,
        // as every other boss's cells always have.
        try {
            if (probe.ridingEntity != null) probe.mountEntity(null);
            if (probe.addedToChunk && probe.worldObj != null && probe.worldObj
                    .getChunkProvider().chunkExists(probe.chunkCoordX, probe.chunkCoordZ)) {
                probe.worldObj.getChunkFromChunkCoords(probe.chunkCoordX, probe.chunkCoordZ)
                        .removeEntity(probe);
            }
            probe.addedToChunk = false;
        } catch (Throwable t) {
            QuestForgeContent.log.warn("[census] could not dismount the probe: " + t);
        }
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
     * True when something in the pack cancels AttackEntityEvent for the probe, so
     * {@code attackTargetEntityWithCurrentItem} can never land a hit.
     *
     * Set once, at the start of a run, and read for every swing so the whole
     * census uses one attack path -- a run that silently switched half way
     * through would not be comparable with itself.
     */
    private static boolean attackEventCancelled;

    public static boolean isAttackEventCancelled() {
        return attackEventCancelled;
    }

    /**
     * Swings the held weapon at a target and returns the damage it took.
     *
     * Normally this is vanilla's own {@code attackTargetEntityWithCurrentItem},
     * which is the most faithful thing available: it applies vanilla enchantment
     * modifiers, knockback, fire aspect and item wear exactly as a player's click
     * would.
     *
     * In this pack that method cannot be used. The Legends Mod
     * ({@code LegendsCommonEventHandler.onAttack}) subscribes to
     * {@code AttackEntityEvent} and cancels it for the probe, so every swing
     * returns having done nothing at all -- the census measured a full window of
     * forty swings and zero damage, and reported it as the enchantment being
     * worth -97%.
     *
     * The fallback reproduces what vanilla does after that event: base damage
     * from the wielder's attackDamage attribute plus
     * {@code getEnchantmentModifierLiving}, delivered as
     * {@code causePlayerDamage}. That still goes down the ordinary damage
     * pipeline, so {@code LivingHurtEvent} fires and every custom enchantment,
     * every armour calculation and every other mod's damage modifier applies
     * exactly as usual. What it skips is knockback, crits and item wear -- none
     * of which a stationary probe would produce anyway -- and the cancelled event
     * itself, which in this pack does nothing for a player the mod has no data
     * for.
     *
     * Which path was used is recorded in the census file header, because it is a
     * fact about the measurement rather than about the enchantments.
     */
    public static float swing(EntityPlayer probe, net.minecraft.entity.EntityLivingBase target) {
        if (probe == null || target == null) return 0F;
        float before = target.getHealth();

        if (!attackEventCancelled) {
            probe.attackTargetEntityWithCurrentItem(target);
            return Math.max(0F, before - target.getHealth());
        }

        float base = 0F;
        try {
            IAttributeInstance attr =
                    probe.getEntityAttribute(SharedMonsterAttributes.attackDamage);
            if (attr != null) base = (float) attr.getAttributeValue();
        } catch (Throwable ignored) {}

        float bonus = 0F;
        try {
            bonus = net.minecraft.enchantment.EnchantmentHelper
                    .getEnchantmentModifierLiving(probe, target);
        } catch (Throwable ignored) {}

        if (base + bonus <= 0F) return 0F;
        target.attackEntityFrom(DamageSource.causePlayerDamage(probe), base + bonus);
        return Math.max(0F, before - target.getHealth());
    }

    // ---- Making the probe experience the passage of time -------------------

    /**
     * Advances the probe by one tick, by hand, because nothing else will.
     *
     * This is the single most important method in the combat census and the
     * easiest one to leave out, so here is the whole reasoning.
     *
     * {@code FakePlayer.onUpdate()} is overridden to {@code return;}, and the
     * probe is never added to the world's entity list anyway, so
     * {@code World.updateEntity} never sees it. Three separate things therefore
     * never happen to a probe, and all three fail silently in the direction of a
     * plausible-looking number:
     *
     * <ol>
     * <li><b>{@code ticksExisted} stays 0 forever.</b> Every piece of combat
     *     memory in this mod is a comparison against it.
     *     {@code Cooldowns.isReady} asks {@code ticksExisted >= readyAt}, which
     *     at tick zero is false for all time -- Crushing Blow and Get Off Me
     *     fire exactly once each and then look like enchantments that decline to
     *     proc. {@code CombatState.recordHit} asks whether
     *     {@code now - lastTick} exceeds the window; at a frozen zero it never
     *     does, so Momentum's streak never resets and climbs past its intended
     *     cap. {@code wasHurtRecently} is true forever, so Riposte's conditional
     *     bonus becomes an unconditional one. Two of those inflate the
     *     measurement and one deflates it.</li>
     * <li><b>Potion effects never expire.</b> {@code updatePotionEffects} lives
     *     in {@code onEntityUpdate}. Strength from Rage or Excalibur is applied
     *     to the attribute map when it is added, so without ticking it is applied
     *     and then never removed -- a four-second buff measured as permanent.</li>
     * <li><b>The probe's invulnerability never lapses.</b>
     *     {@code hurtResistantTime} is decremented for players in
     *     {@code EntityPlayerMP.onUpdate}, which is the very method FakePlayer
     *     discards. A defensive measurement without it records the first hit of a
     *     fight and silently ignores every one after.</li>
     * </ol>
     *
     * The fix for (2) is to call the real {@code onEntityUpdate}, not to
     * reimplement it: FakePlayer overrides {@code onUpdate}, which is a different
     * method, so the living-entity base tick is still there and still correct.
     * (1) and (3) are single statements copied from the vanilla methods that
     * would have run them, and are commented as such.
     *
     * Finally the mod's own per-tick work is driven by posting the real
     * {@link TickEvent.PlayerTickEvent} to the bus the bridge is registered on.
     * That runs {@code EnchantEventBridge.onPlayerTick} -- the TICK dispatch,
     * AttributeUpkeep, DemonForgedUpkeep -- through the shipping code path rather
     * than a copy of it, which is the whole point of measuring in the game.
     */
    public static void pumpTick(EntityPlayer probe) {
        if (probe == null) return;

        // From World.updateEntity, which never runs for an entity that was never
        // added to the world.
        probe.ticksExisted++;

        // The living-entity base tick: potion durations, hurtTime, air, fire.
        // Safe to call directly -- FakePlayer overrides onUpdate, not this.
        try {
            probe.onEntityUpdate();
        } catch (Throwable t) {
            QuestForgeContent.log.warn("[census] probe onEntityUpdate threw: " + t);
        }

        // From EntityPlayerMP.onUpdate. onEntityUpdate deliberately skips this for
        // EntityPlayerMP (see its "&& !(this instanceof EntityPlayerMP)" guard),
        // because for a real player the server tick does it instead.
        if (probe.hurtResistantTime > 0) {
            probe.hurtResistantTime--;
        }

        // The mod's own tick work, through the real handler on the real bus.
        try {
            cpw.mods.fml.common.FMLCommonHandler.instance().bus().post(
                    new cpw.mods.fml.common.gameevent.TickEvent.PlayerTickEvent(
                            cpw.mods.fml.common.gameevent.TickEvent.Phase.END,
                            probe));
        } catch (Throwable t) {
            // With the stack trace, because without it this says only that
            // something in the mod's per-tick work does not survive a player with
            // no client attached -- which is true of a FakePlayer in ordinary play
            // too, not just of the census.
            if (tickFailures++ < MAX_LOGGED_TICK_FAILURES) {
                QuestForgeContent.log.warn("[census] probe tick event threw"
                        + (tickFailures == MAX_LOGGED_TICK_FAILURES
                                ? " (further occurrences suppressed)" : ""), t);
            }
        }
    }

    /**
     * A tick handler that throws does so every tick, and a census runs tens of
     * thousands of them. Log the first few with traces and then stop.
     */
    private static final int MAX_LOGGED_TICK_FAILURES = 5;
    private static int tickFailures;

    /**
     * Every mod listening to AttackEntityEvent, in the order they run.
     *
     * When something cancels the probe's swing, the useful output is a name, not
     * the fact of it. Forge's generated handlers report their owning class from
     * toString(), which is how a crash report names the mod responsible; this
     * asks the same list directly so a census can say who did it without anyone
     * bisecting a hundred jars by hand.
     */
    private static String attackListeners() {
        StringBuilder sb = new StringBuilder();
        try {
            net.minecraftforge.event.entity.player.AttackEntityEvent probeEvent =
                    new net.minecraftforge.event.entity.player.AttackEntityEvent(null, null);
            cpw.mods.fml.common.eventhandler.ListenerList list = probeEvent.getListenerList();

            Field busIdField = net.minecraftforge.common.MinecraftForge.EVENT_BUS
                    .getClass().getDeclaredField("busID");
            busIdField.setAccessible(true);
            int busId = busIdField.getInt(net.minecraftforge.common.MinecraftForge.EVENT_BUS);

            cpw.mods.fml.common.eventhandler.IEventListener[] listeners = list.getListeners(busId);
            for (int i = 0; i < listeners.length; i++) {
                if (i > 0) sb.append(", ");
                sb.append(String.valueOf(listeners[i]));
            }
        } catch (Throwable t) {
            sb.append("could not read the listener list: ").append(t);
        }
        return sb.toString();
    }

    /**
     * Proves {@link #pumpTick} is actually driving the mod's per-tick code.
     *
     * The test has a known answer that cannot be produced by accident: put
     * Excalibur on a sword, hold it, pump a tick, and the wielder must come out
     * with Strength on them, because Excalibur's onTick applies it. If the tick
     * dispatch is not running, the probe has no potion effects and this returns
     * a failure instead of a file of zeroes.
     *
     * Excalibur is the right probe for this because it is unconditional -- level
     * 1, 100% proc, no cooldown, no target required -- so a negative result means
     * the plumbing is broken rather than that a roll went the wrong way.
     */
    public static String calibrateTick(WorldServer world) {
        EntityPlayer probe = player(world);
        if (probe == null) return "FAILED: no probe player";

        com.questforge.content.ench.QFEnchantment excalibur =
                com.questforge.content.ench.QFEnchantments.byName("excalibur");
        if (excalibur == null) return "SKIPPED: excalibur is not registered";

        try {
            double x = world.getSpawnPoint().posX + 0.5D;
            double z = world.getSpawnPoint().posZ + 0.5D;
            double y = world.getTopSolidOrLiquidBlock((int) x, (int) z) + 1;
            reset(probe, x, y, z);

            int ticksBefore = probe.ticksExisted;

            ItemStack sword = new ItemStack(net.minecraft.init.Items.diamond_sword);
            sword.addEnchantment(excalibur, 1);
            hold(probe, sword);

            // Excalibur refreshes on a 40-tick cycle and gates on
            // "ticksExisted % 40 == 0", so the effect lands on a multiple of 40
            // rather than on the first tick. Pumping a full cycle plus one is what
            // makes the test meaningful; a single pump tests nothing and fails for
            // the wrong reason.
            boolean strength = false;
            for (int i = 0; i < 41 && !strength; i++) {
                pumpTick(probe);
                strength = probe.isPotionActive(net.minecraft.potion.Potion.damageBoost);
            }

            // All three, not just the first. Excalibur's onTick applies Strength,
            // Resistance and Speed in that order, so checking only Strength passes
            // even when the call throws immediately after applying it -- which is
            // exactly what a probe with no connection used to do. Requiring the
            // last one proves the whole hook ran.
            boolean resistance = probe.isPotionActive(net.minecraft.potion.Potion.resistance);
            boolean speed = probe.isPotionActive(net.minecraft.potion.Potion.moveSpeed);
            boolean advanced = probe.ticksExisted > ticksBefore;

            // Measured while the sword is still held and Strength is still on,
            // because both are what is being tested. Doing this after the cleanup
            // below reads the bare-handed 1.0 twice and fails for the wrong
            // reason -- which it did on the first attempt.
            double buffed = attackDamage(probe);
            probe.removePotionEffect(net.minecraft.potion.Potion.damageBoost.id);
            double plain = attackDamage(probe);

            hold(probe, null);
            try {
                probe.clearActivePotions();
            } catch (Throwable ignored) {}

            if (!advanced) {
                return "FAILED: ticksExisted did not advance; cooldowns and combat "
                        + "windows will never expire";
            }
            if (!strength) {
                return "FAILED: Excalibur's tick effect did not apply, so the TICK "
                        + "dispatch is not reaching the probe. Every tick-driven "
                        + "enchantment would measure as zero.";
            }
            if (!resistance || !speed) {
                return "FAILED: Excalibur applied Strength but not "
                        + (!resistance ? "Resistance" : "Speed")
                        + ", so its onTick threw part way through. Every tick-driven "
                        + "enchantment would be measured as a fraction of itself.";
            }

            // Having the effect is not the same as the effect doing anything.
            // Strength works by adding an attackDamage modifier, and a probe can
            // hold the potion while the attribute never moves -- which is exactly
            // what happened for four runs and measured every potion-granting
            // enchantment as zero. buffed/plain are captured above, while the
            // sword and the buff are both still on.
            if (!(buffed > plain + 0.01D)) {
                return "FAILED: the probe holds Strength but its attack damage is "
                        + CensusFile.num(plain) + " either way, so potion effects are "
                        + "not reaching the attribute. Every enchantment that works by "
                        + "granting a potion would measure as zero.";
            }
            return "OK: tick pump drives the mod's per-tick code (Excalibur applied "
                    + "Strength, Resistance and Speed; Strength moved attack damage "
                    + CensusFile.num(plain) + " -> " + CensusFile.num(buffed)
                    + "; ticksExisted advancing)";
        } catch (Throwable t) {
            return "FAILED: " + t;
        }
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

            // If the swing landed nothing, find out how far down it was stopped,
            // because the two causes need completely different fixes. Damage from
            // a player DamageSource that also lands nothing means something is
            // rejecting this attacker -- a protection mod, a PvP flag, a
            // FakePlayer check. Damage that lands here but not through the swing
            // means the attack was cancelled higher up, in AttackEntityEvent or in
            // the item's own onLeftClickEntity.
            if (swing <= 0.0F) {
                zombie.hurtResistantTime = 0;
                zombie.setHealth(zombie.getMaxHealth());
                float beforeDirect = zombie.getHealth();
                zombie.attackEntityFrom(DamageSource.causePlayerDamage(probe), 8.0F);
                float direct = beforeDirect - zombie.getHealth();
                sb.append("; direct player-source damage lands ")
                  .append(CensusFile.num(direct))
                  .append(direct > 0.0F
                          ? " (so the swing itself is being cancelled)"
                          : " (so this attacker's damage is being rejected outright)");

                // Which of the three gates in attackTargetEntityWithCurrentItem
                // stopped it. Vanilla checks them in this order, and each one
                // means a different mod is responsible, so naming the gate turns
                // "something cancels our attacks" into a search with one answer.
                sb.append("; gate: ");
                boolean cancelled = net.minecraftforge.common.MinecraftForge.EVENT_BUS.post(
                        new net.minecraftforge.event.entity.player.AttackEntityEvent(probe, zombie));
                attackEventCancelled = cancelled;
                if (cancelled) {
                    sb.append("AttackEntityEvent cancelled by a mod");
                    sb.append(" [listeners: ").append(attackListeners()).append(']');
                } else {
                    ItemStack inHand = probe.getCurrentEquippedItem();
                    boolean leftClick = inHand != null
                            && inHand.getItem().onLeftClickEntity(inHand, probe, zombie);
                    if (leftClick) {
                        sb.append("the item's onLeftClickEntity consumed the attack");
                    } else if (!zombie.canAttackWithItem()) {
                        sb.append("target.canAttackWithItem() is false");
                    } else if (zombie.hitByEntity(probe)) {
                        sb.append("target.hitByEntity() consumed the attack");
                    } else {
                        sb.append("none -- the attack should have landed");
                    }
                }
            }
            hold(probe, null);

            sb.append("; difficulty ").append(world.difficultySetting);

            if (swordAttr <= 1.01D) {
                sb.insert(0, "FAILED (weapon modifiers not applying): ");
            } else if (swing <= 0.0F && !attackEventCancelled) {
                // The probe could be hurt and the mob could be hurt, but the one
                // operation the whole offensive census is built on did nothing,
                // and for a reason we do not recognise. A calibration that passes
                // in that state is worse than no calibration.
                sb.insert(0, "FAILED (the probe's swing lands no damage): ");
            } else if (swing <= 0.0F) {
                // Recognised and handled: a mod cancels the attack event, and the
                // census will use the direct damage path instead. Still reported
                // in full, because it changes what the run means.
                sb.insert(0, "OK (using the direct attack path): ");
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
