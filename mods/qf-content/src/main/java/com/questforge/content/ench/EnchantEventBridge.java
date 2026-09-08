package com.questforge.content.ench;

import java.util.Random;

import net.minecraft.entity.Entity;
import net.minecraft.entity.EntityLiving;
import net.minecraft.entity.EntityLivingBase;
import net.minecraft.entity.player.EntityPlayer;
import net.minecraft.entity.projectile.EntityArrow;
import net.minecraft.item.ItemStack;
import net.minecraftforge.event.entity.EntityJoinWorldEvent;
import net.minecraftforge.event.entity.living.LivingDeathEvent;
import net.minecraftforge.event.entity.living.LivingDropsEvent;
import net.minecraftforge.event.entity.living.LivingHurtEvent;
import net.minecraftforge.event.entity.living.LivingSetAttackTargetEvent;
import net.minecraft.entity.item.EntityItem;
import net.minecraftforge.event.entity.item.ItemExpireEvent;
import net.minecraftforge.event.entity.player.PlayerDestroyItemEvent;
import net.minecraftforge.event.entity.player.PlayerDropsEvent;
import net.minecraftforge.event.entity.player.PlayerInteractEvent;
import net.minecraftforge.event.entity.player.PlayerPickupXpEvent;
import net.minecraftforge.event.world.BlockEvent;

import cpw.mods.fml.common.eventhandler.EventPriority;
import com.questforge.content.ench.enchants.ArmorEnchants;

import cpw.mods.fml.common.eventhandler.SubscribeEvent;
import cpw.mods.fml.common.gameevent.PlayerEvent;
import cpw.mods.fml.common.gameevent.TickEvent;

/**
 * Turns Forge events into dispatcher calls. This is the only class that knows
 * which Forge event corresponds to which trigger; enchantments never see events.
 */
public class EnchantEventBridge {

    private final Random rand = new Random();

    // ---- Combat -----------------------------------------------------------

    @SubscribeEvent
    public void onLivingHurt(LivingHurtEvent event) {
        if (event.entityLiving == null || event.entityLiving.worldObj.isRemote) return;

        // Riposte and Regrowth both key off "was this entity hurt recently".
        CombatState.recordHurt(event.entityLiving);

        Entity attacker = event.source.getEntity();

        // Cripple, and Sunder's damage half. Applied to the raw hit before any
        // enchantment sees it, so it reduces the attack itself rather than fighting
        // with whatever the attacker's own enchantments add on top.
        if (attacker instanceof EntityLivingBase) {
            event.ammount *= TickedEffects.damageMultiplier((EntityLivingBase) attacker);
        }

        // An arrow we are tracking: the enchantments live on the bow that fired it,
        // not on whatever the shooter happens to be holding now.
        Entity direct = event.source.getSourceOfDamage();
        if (direct instanceof EntityArrow && ArrowTracker.isTracked((EntityArrow) direct)) {
            EntityArrow arrow = (EntityArrow) direct;
            EntityLivingBase shooter = arrow.shootingEntity instanceof EntityLivingBase
                    ? (EntityLivingBase) arrow.shootingEntity : null;

            ArrowContext actx = new ArrowContext(shooter, event.entityLiving,
                    ArrowTracker.bowFor(arrow), event.entityLiving.worldObj, rand,
                    arrow, event.ammount);
            event.ammount = EnchantDispatcher.dispatch(EnchantDispatcher.Trigger.ATTACK, actx);
            EnchantDispatcher.dispatch(EnchantDispatcher.Trigger.ARROW_HIT, actx);

            applyArmour(event, attacker);
            return;   // do not also run the melee path
        }

        // The attacker's weapon -- unless this hit IS one of our own effects.
        // Rupture's bleed and Arc's chains carry the wielder as their damage entity,
        // so without this guard every bleed tick and every chained hit would count
        // as a fresh swing and re-roll every on-hit enchantment.
        if (attacker instanceof EntityLivingBase && !CombatState.isReentrant()) {
            EntityLivingBase living = (EntityLivingBase) attacker;
            ItemStack weapon = living.getHeldItem();
            if (weapon != null) {
                ProcContext ctx = new ProcContext(living, event.entityLiving, weapon,
                        living.worldObj, rand, event.source, event.ammount);
                // Note the Forge typo: the field really is "ammount".
                event.ammount = EnchantDispatcher.dispatch(EnchantDispatcher.Trigger.ATTACK, ctx);
            }
        }

        applyArmour(event, attacker);
    }

    /** Runs the victim's armor enchantments. Shared by the melee and arrow paths. */
    private void applyArmour(LivingHurtEvent event, Entity attacker) {
        if (event.entityLiving instanceof EntityPlayer) {
            EntityPlayer victim = (EntityPlayer) event.entityLiving;
            for (ItemStack piece : victim.inventory.armorInventory) {
                if (piece == null) continue;
                ProcContext ctx = new ProcContext(victim, attacker, piece,
                        victim.worldObj, rand, event.source, event.ammount);
                event.ammount = EnchantDispatcher.dispatch(EnchantDispatcher.Trigger.DAMAGED, ctx);
            }

            // After every piece has had its say: a Turtle set is meant to be very
            // hard to kill, not unkillable, so something always gets through.
            event.ammount = ArmorEnchants.Turtle.floorDamage(victim, event.source, event.ammount);
        }

        if (event.ammount < 0F) event.ammount = 0F;
    }

    // Sacrifice's veto and Soulbound's inventory sweep live in DeathHandler, which
    // is registered from preInit so it can run ahead of GraveStones.

    @SubscribeEvent
    public void onTargeted(LivingSetAttackTargetEvent event) {
        if (!(event.target instanceof EntityPlayer)) return;
        if (!(event.entityLiving instanceof EntityLiving)) return;
        if (event.entityLiving.worldObj.isRemote) return;

        EntityPlayer player = (EntityPlayer) event.target;
        for (ItemStack piece : player.inventory.armorInventory) {
            if (piece == null) continue;
            ProcContext ctx = new ProcContext(player, event.entityLiving, piece,
                    player.worldObj, rand, null, 0F);
            EnchantDispatcher.dispatch(EnchantDispatcher.Trigger.TARGETED, ctx);
            if (ctx.cancelled) {
                ((EntityLiving) event.entityLiving).setAttackTarget(null);
                return;
            }
        }
    }

    @SubscribeEvent
    public void onLivingDeath(LivingDeathEvent event) {
        if (event.entityLiving == null || event.entityLiving.worldObj.isRemote) return;

        Entity killer = event.source.getEntity();
        if (!(killer instanceof EntityLivingBase)) return;

        EntityLivingBase living = (EntityLivingBase) killer;
        ItemStack weapon = living.getHeldItem();
        if (weapon == null) return;

        ProcContext ctx = new ProcContext(living, event.entityLiving, weapon,
                living.worldObj, rand, event.source, 0F);
        EnchantDispatcher.dispatch(EnchantDispatcher.Trigger.KILL, ctx);
    }

    // ---- Mining -----------------------------------------------------------

    @SubscribeEvent
    public void onHarvestDrops(BlockEvent.HarvestDropsEvent event) {
        if (event.harvester == null || event.world.isRemote) return;

        ItemStack tool = event.harvester.getHeldItem();
        if (tool == null) return;

        HarvestContext ctx = new HarvestContext(event.harvester, tool, event.world, rand,
                event.block, event.x, event.y, event.z, event.fortuneLevel, event.drops);
        EnchantDispatcher.dispatch(EnchantDispatcher.Trigger.HARVEST, ctx);
    }

    @SubscribeEvent
    public void onBlockBreak(BlockEvent.BreakEvent event) {
        if (event.getPlayer() == null || event.world.isRemote) return;
        // Our own area-breaking fires this event for every block it breaks.
        if (AreaBreaker.isActive()) return;

        ItemStack tool = event.getPlayer().getHeldItem();
        if (tool == null) return;

        BreakContext ctx = new BreakContext(event.getPlayer(), tool, event.world, rand, event);
        EnchantDispatcher.dispatch(EnchantDispatcher.Trigger.BREAK, ctx);
    }

    @SubscribeEvent
    public void onXpPickup(PlayerPickupXpEvent event) {
        if (event.entityPlayer == null || event.entityPlayer.worldObj.isRemote) return;
        if (event.orb == null) return;

        EntityPlayer player = event.entityPlayer;
        int remaining = event.orb.xpValue;

        // Offer the orb to armor first, then the held item.
        for (ItemStack piece : player.inventory.armorInventory) {
            if (piece == null || remaining <= 0) continue;
            remaining = spendXp(player, piece, remaining);
        }
        ItemStack held = player.getHeldItem();
        if (held != null && remaining > 0) {
            remaining = spendXp(player, held, remaining);
        }

        event.orb.xpValue = remaining;
    }

    private int spendXp(EntityPlayer player, ItemStack stack, int xp) {
        XpContext ctx = new XpContext(player, stack, player.worldObj, rand, xp);
        EnchantDispatcher.dispatch(EnchantDispatcher.Trigger.XP_PICKUP, ctx);
        return ctx.xp;
    }

    @SubscribeEvent
    public void onItemDestroyed(PlayerDestroyItemEvent event) {
        if (event.entityPlayer == null || event.entityPlayer.worldObj.isRemote) return;
        if (event.original == null) return;

        ProcContext ctx = new ProcContext(event.entityPlayer, null, event.original,
                event.entityPlayer.worldObj, rand, null, 0F);
        EnchantDispatcher.dispatch(EnchantDispatcher.Trigger.ITEM_DESTROYED, ctx);
    }

    @SubscribeEvent
    public void onLivingDrops(LivingDropsEvent event) {
        if (event.entityLiving == null || event.entityLiving.worldObj.isRemote) return;
        if (event.source == null) return;

        Entity killer = event.source.getEntity();
        if (!(killer instanceof EntityLivingBase)) return;

        EntityLivingBase living = (EntityLivingBase) killer;
        ItemStack weapon = living.getHeldItem();
        if (weapon == null) return;

        DropsContext ctx = new DropsContext(living, event.entityLiving, weapon,
                living.worldObj, rand, event.source, event.drops, event.lootingLevel);
        EnchantDispatcher.dispatch(EnchantDispatcher.Trigger.DROPS, ctx);
    }

    // ---- Soulbound --------------------------------------------------------

    /**
     * HIGHEST priority so soulbound items leave the drop list before Gravestones
     * (or any other death-handling mod) collects it. Getting this order wrong
     * means the item ends up in a grave AND is removed from the player.
     */
    @SubscribeEvent(priority = EventPriority.HIGHEST)
    public void onPlayerDrops(PlayerDropsEvent event) {
        if (event.entityPlayer == null || event.entityPlayer.worldObj.isRemote) return;
        Soulbound.captureFrom(event.entityPlayer, event.drops);
    }

    @SubscribeEvent
    public void onPlayerClone(PlayerEvent.PlayerRespawnEvent event) {
        if (event.player == null || event.player.worldObj.isRemote) return;
        Soulbound.restoreTo(event.player);
    }

    /** A soulbound item that would despawn goes home instead. */
    @SubscribeEvent
    public void onItemExpire(ItemExpireEvent event) {
        EntityItem item = event.entityItem;
        if (item == null || item.worldObj.isRemote) return;
        if (Soulbound.rescue(item)) event.setCanceled(true);
    }

    // ---- Activated abilities ---------------------------------------------

    /** Feeds RightClickState, which Get Off Me reads. */
    @SubscribeEvent
    public void onPlayerInteract(PlayerInteractEvent event) {
        if (event.entityPlayer == null) return;
        if (event.action == PlayerInteractEvent.Action.RIGHT_CLICK_AIR
                || event.action == PlayerInteractEvent.Action.RIGHT_CLICK_BLOCK) {
            RightClickState.record(event.entityPlayer);
        }
    }

    // ---- Arrows -----------------------------------------------------------

    /**
     * Tag a new arrow with the bow that fired it. Done at spawn because it is the
     * only moment the bow is reliably still in the shooter's hand.
     */
    @SubscribeEvent
    public void onEntityJoin(EntityJoinWorldEvent event) {
        if (event.world.isRemote) return;

        // A summon loaded from disk -- the server restarted while it was alive --
        // has lost both its expiry and its leash. Remove it rather than leave a
        // MobProperties-buffed hostile wandering about with no owner.
        if (event.entity instanceof EntityLivingBase
                && TickedEffects.isOrphanedSummon((EntityLivingBase) event.entity)) {
            event.entity.setDead();
            event.setCanceled(true);
            return;
        }

        // A soulbound item on the floor is watched from the moment it appears, so
        // fire, lava and the void can be answered before they delete it.
        if (event.entity instanceof EntityItem) {
            Soulbound.watch((EntityItem) event.entity);
            return;
        }

        if (!(event.entity instanceof EntityArrow)) return;

        EntityArrow arrow = (EntityArrow) event.entity;
        if (ArrowTracker.isTracked(arrow)) return;   // a follow-up arrow we spawned
        if (!(arrow.shootingEntity instanceof EntityLivingBase)) return;

        ItemStack bow = ((EntityLivingBase) arrow.shootingEntity).getHeldItem();
        if (bow == null || EnchantDispatcher.findOn(bow).isEmpty()) return;

        ArrowTracker.track(arrow, bow);
    }

    /**
     * Drives Homing and detects landing. Iterates only arrows we tagged, so the
     * cost is proportional to enchanted arrows in flight rather than to all
     * entities.
     */
    @SubscribeEvent
    public void onWorldTick(TickEvent.WorldTickEvent event) {
        if (event.phase != TickEvent.Phase.END || event.world.isRemote) return;

        // Bleed damage and summon expiry.
        TickedEffects.tick(event.world);

        // Soulbound items lying in fire, lava or the void, none of which fire an
        // event that could be cancelled.
        Soulbound.tick(event.world);

        for (EntityArrow arrow : ArrowTracker.tracked()) {
            if (arrow == null || arrow.isDead) {
                ArrowTracker.forget(arrow);
                continue;
            }
            if (arrow.worldObj != event.world) continue;

            ItemStack bow = ArrowTracker.bowFor(arrow);
            if (bow == null) continue;

            EntityLivingBase shooter = arrow.shootingEntity instanceof EntityLivingBase
                    ? (EntityLivingBase) arrow.shootingEntity : null;
            ArrowContext ctx = new ArrowContext(shooter, null, bow,
                    event.world, rand, arrow, 0F);

            if (arrow.onGround) {
                EnchantDispatcher.dispatch(EnchantDispatcher.Trigger.ARROW_LAND, ctx);
                ArrowTracker.forget(arrow);
            } else {
                EnchantDispatcher.dispatch(EnchantDispatcher.Trigger.ARROW_TICK, ctx);
            }
        }
    }

    /** Drives the ore survey, which generates and counts chunks without a player. */
    @SubscribeEvent
    public void onServerTick(TickEvent.ServerTickEvent event) {
        if (event.phase != TickEvent.Phase.END) return;
        com.questforge.content.survey.OreSurvey.tick();
    }

    // ---- Passive ticks ----------------------------------------------------

    @SubscribeEvent
    public void onPlayerTick(TickEvent.PlayerTickEvent event) {
        if (event.phase != TickEvent.Phase.END) return;
        if (event.player == null || event.player.worldObj.isRemote) return;

        EntityPlayer player = event.player;

        for (ItemStack piece : player.inventory.armorInventory) {
            if (piece == null) continue;
            tick(player, piece);
        }

        ItemStack held = player.getHeldItem();
        if (held != null) tick(player, held);

        // Attribute-driven enchantments cannot be handled by the per-item hook,
        // which never learns when an item was removed. Reconcile them here.
        AttributeUpkeep.update(player);

        // Reach's block half. The entity half is in ReachTransformer; see the note
        // on ReachUpkeep for why the two are done differently.
        ReachUpkeep.update(player);

        // Demon Forged writes a permanent NBT tag, so something has to notice when
        // the enchantment granting it is gone.
        DemonForgedUpkeep.update(player);

        // Torchlight moves a block, which is far too expensive to do every tick and
        // entirely unnecessary: a player cannot cross a block boundary in under four.
        if (player.ticksExisted % 5 == 0) {
            TorchlightUpkeep.tick(player);
        }
    }

    /** Nobody should leave a light behind them when they log out. */
    @SubscribeEvent
    public void onPlayerLoggedOut(cpw.mods.fml.common.gameevent.PlayerEvent.PlayerLoggedOutEvent event) {
        if (event.player != null) TorchlightUpkeep.clear(event.player);
    }

    private void tick(EntityPlayer player, ItemStack stack) {
        ProcContext ctx = new ProcContext(player, null, stack,
                player.worldObj, rand, null, 0F);
        EnchantDispatcher.dispatch(EnchantDispatcher.Trigger.TICK, ctx);
    }
}
