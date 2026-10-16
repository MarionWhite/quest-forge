package com.questforge.content.ench;

import java.util.ArrayList;
import java.util.Iterator;
import java.util.List;

import net.minecraft.enchantment.EnchantmentHelper;
import net.minecraft.entity.item.EntityItem;
import net.minecraft.entity.player.EntityPlayer;
import net.minecraft.item.ItemStack;
import net.minecraft.nbt.NBTTagCompound;
import net.minecraft.nbt.NBTTagList;
import net.minecraft.world.World;
import net.minecraftforge.common.DimensionManager;

/**
 * The keeping half of the Soulbound enchantment.
 *
 * Three separate behaviours, per the design:
 *
 * 1. The item is pulled out of the inventory on death -- from DeathHandler, which
 *    runs ahead of GraveStones, or it would be collected into a grave and the
 *    player would end up with neither.
 * 2. It is stashed and handed back on respawn.
 * 3. If it would ever despawn as a dropped item, it returns to its owner instead.
 *
 * The stash lives in the player's persisted NBT rather than in memory. Forge
 * copies that tag onto the respawned player, and it is saved with the player
 * file, so a server restart between death and respawn no longer loses the item.
 */
public class Soulbound {

    private static final String STASH = "QFSoulbound";

    public static boolean isSoulbound(ItemStack stack) {
        QFEnchantment ench = QFEnchantments.soulbound;
        if (ench == null || stack == null) return false;
        return EnchantmentHelper.getEnchantmentLevel(ench.effectId, stack) > 0;
    }

    /**
     * Removes soulbound items from the drop list and stashes them.
     * A fallback for mods that build drops before our death handler ran.
     */
    public static void captureFrom(EntityPlayer player, List<EntityItem> drops) {
        NBTTagList stash = null;

        Iterator<EntityItem> it = drops.iterator();
        while (it.hasNext()) {
            EntityItem entityItem = it.next();
            if (entityItem == null) continue;
            ItemStack stack = entityItem.getEntityItem();
            if (!isSoulbound(stack)) continue;

            if (stash == null) stash = stashOf(player);
            stash.appendTag(stack.writeToNBT(new NBTTagCompound()));
            it.remove();
        }
    }

    /** Sweeps the inventory itself. Called from DeathHandler before GraveStones. */
    public static void captureFromInventory(EntityPlayer player) {
        NBTTagList stash = stashOf(player);
        sweep(player.inventory.mainInventory, stash);
        sweep(player.inventory.armorInventory, stash);
    }

    private static void sweep(ItemStack[] slots, NBTTagList stash) {
        for (int i = 0; i < slots.length; i++) {
            if (isSoulbound(slots[i])) {
                stash.appendTag(slots[i].writeToNBT(new NBTTagCompound()));
                slots[i] = null;
            }
        }
    }

    /** Hands everything back. Anything that will not fit is dropped at their feet. */
    public static void restoreTo(EntityPlayer player) {
        NBTTagCompound persisted = persisted(player);
        if (!persisted.hasKey(STASH)) return;

        NBTTagList stash = persisted.getTagList(STASH, 10);
        persisted.removeTag(STASH);

        for (int i = 0; i < stash.tagCount(); i++) {
            ItemStack stack = ItemStack.loadItemStackFromNBT(stash.getCompoundTagAt(i));
            if (stack == null) continue;
            if (!player.inventory.addItemStackToInventory(stack)) {
                player.entityDropItem(stack, 0.5F);
            }
        }
    }

    // ---- Keeping a dropped one alive -------------------------------------

    /**
     * Soulbound item entities currently lying in the world.
     *
     * The promise is that a soulbound item is never lost, and until now that only
     * held for the despawn timer. An item entity that burns, falls in lava or
     * drops out of the world is simply deleted, and none of those paths fire an
     * event a mod can cancel. So the entities are tracked and checked once a tick.
     *
     * Fire immunity would be tidier, but Entity.isImmuneToFire is protected and
     * Entity.invulnerable is private, so neither can be set without reflection.
     * Watching is enough: lava deals four damage a tick and an item entity has
     * five health, so there is always exactly one tick in which to act.
     */
    private static final List<EntityItem> WATCHED = new ArrayList<EntityItem>();

    /** Never grows without bound, however many items are on the floor. */
    private static final int MAX_WATCHED = 512;

    /**
     * Entity.onUpdate deletes anything below -64. Catching it at -48 leaves about
     * a second of fall to act in, and stays far enough under bedrock that an item
     * lying on the floor of a deep cave is never yanked out of the player's reach.
     */
    private static final double VOID_RESCUE_Y = -48.0D;

    /**
     * Items that entered the world while tick() was walking WATCHED. Handing an
     * item back to its owner can drop it at their feet, that drop fires
     * EntityJoinWorldEvent straight back into watch(), and adding to the list
     * mid-iteration threw a ConcurrentModificationException out of the server
     * tick. They wait here and join the list once the walk is done.
     */
    private static final List<EntityItem> PENDING = new ArrayList<EntityItem>();
    private static boolean ticking;

    /** Called for every item entity entering the world. */
    public static void watch(EntityItem entityItem) {
        if (entityItem == null || !isSoulbound(entityItem.getEntityItem())) return;
        if (WATCHED.size() + PENDING.size() >= MAX_WATCHED) return;
        for (EntityItem existing : WATCHED) {
            if (existing == entityItem) return;
        }
        for (EntityItem existing : PENDING) {
            if (existing == entityItem) return;
        }
        // Forge's own per-entity despawn timer. A soulbound item waits forever.
        entityItem.lifespan = Integer.MAX_VALUE;
        if (ticking) PENDING.add(entityItem);
        else WATCHED.add(entityItem);
    }

    /** Once a tick, per world: pull anything in danger back out of it. */
    public static void tick(World world) {
        ticking = true;
        try {
            tickWatched(world);
        } finally {
            ticking = false;
            WATCHED.addAll(PENDING);
            PENDING.clear();
        }
    }

    private static void tickWatched(World world) {
        Iterator<EntityItem> it = WATCHED.iterator();
        while (it.hasNext()) {
            EntityItem item = it.next();
            if (item == null || item.isDead || unloaded(item)) {
                it.remove();
                continue;
            }
            if (item.worldObj != world) continue;

            // handleLavaMovement only reports lava inside a shrunken box, so an item
            // resting ON a lava pool -- the usual landing -- never counted. It burned
            // to death in five ticks: Entity.moveEntity deals fire damage straight
            // from any burning block it touches and re-ignites it every tick, so
            // putting the fire out bought nothing. Found by throwing a soulbound
            // sword onto lava on a dedicated server and watching it die.
            boolean touchingFire = item.worldObj.func_147470_e(
                    item.boundingBox.contract(0.001D, 0.001D, 0.001D));
            boolean inDanger = item.isBurning() || touchingFire || item.handleLavaMovement();

            // Fire, lava and the void all mean moving the item.
            if (inDanger || item.posY < VOID_RESCUE_Y) {
                if (!returnToOwner(item)) lift(item);
            }
        }
    }

    /**
     * An item whose chunk or whole dimension has unloaded. It is never marked
     * dead, so without this it sat in WATCHED for good -- pinning its World, and
     * once 512 had piled up, leaving every new soulbound drop unprotected.
     *
     * Forgetting it loses nothing: the entity is saved with its chunk, and Forge's
     * World.addLoadedEntities fires EntityJoinWorldEvent for every entity a chunk
     * brings back, so onEntityJoin watches the reloaded copy afresh.
     */
    private static boolean unloaded(EntityItem item) {
        World world = item.worldObj;
        if (world == null) return true;
        if (DimensionManager.getWorld(world.provider.dimensionId) != world) return true;
        // Not yet placed in a chunk means it is still on its way in, not out.
        return item.addedToChunk
                && !world.getChunkProvider().chunkExists(item.chunkCoordX, item.chunkCoordZ);
    }

    /**
     * The owner, if they are alive in this world to take the item. While a player
     * sits on the death screen getPlayerEntityByName still finds the dead entity,
     * and anything handed to it is gone when they respawn -- so a dead owner counts
     * as no owner, and the item waits on the floor for the living one.
     */
    private static EntityPlayer liveOwner(EntityItem item) {
        String name = item.func_145800_j();
        if (name == null) return null;
        EntityPlayer owner = item.worldObj.getPlayerEntityByName(name);
        if (owner == null || owner.isDead || owner.getHealth() <= 0.0F) return null;
        return owner;
    }

    /** Hands the item straight back if its owner is here to take it. */
    private static boolean returnToOwner(EntityItem item) {
        EntityPlayer owner = liveOwner(item);
        if (owner == null) return false;

        ItemStack stack = item.getEntityItem();
        if (stack == null) return false;
        if (!owner.inventory.addItemStackToInventory(stack)) {
            owner.entityDropItem(stack, 0.5F);
        }
        item.setDead();
        return true;
    }

    /** No owner to hand it to: put it back on the surface, above whatever it fell into. */
    private static void lift(EntityItem item) {
        int x = net.minecraft.util.MathHelper.floor_double(item.posX);
        int z = net.minecraft.util.MathHelper.floor_double(item.posZ);
        int y = item.worldObj.getTopSolidOrLiquidBlock(x, z);
        item.setPosition(x + 0.5D, y + 1.0D, z + 0.5D);
        item.motionX = 0.0D;
        item.motionY = 0.0D;
        item.motionZ = 0.0D;
        item.extinguish();
        item.fallDistance = 0.0F;

        // Above a lava pool the item falls straight back in, and every touch costs
        // health it never regains -- so without this, lifting only postponed the
        // loss. EntityItem.health is private; its own NBT is the public way in.
        net.minecraft.nbt.NBTTagCompound tag = new net.minecraft.nbt.NBTTagCompound();
        item.writeToNBT(tag);
        tag.setShort("Health", (short) 5);
        item.readFromNBT(tag);
    }

    /**
     * An item entity is about to vanish on its despawn timer.
     *
     * @return true if we rescued it and the caller should cancel the removal.
     */
    public static boolean rescue(EntityItem entityItem) {
        if (entityItem == null) return false;
        ItemStack stack = entityItem.getEntityItem();
        if (!isSoulbound(stack)) return false;

        EntityPlayer owner = liveOwner(entityItem);
        if (owner == null) {
            // No known owner, or a dead one: refresh the despawn timer so it
            // survives regardless.
            entityItem.age = 0;
            return true;
        }

        if (!owner.inventory.addItemStackToInventory(stack)) {
            owner.entityDropItem(stack, 0.5F);
        }
        entityItem.setDead();
        return true;
    }

    // ---- The stash -------------------------------------------------------

    /** The stash list, created and attached if missing. */
    private static NBTTagList stashOf(EntityPlayer player) {
        NBTTagCompound persisted = persisted(player);
        NBTTagList stash = persisted.getTagList(STASH, 10);
        persisted.setTag(STASH, stash);   // getTagList returns a detached list when absent
        return stash;
    }

    /**
     * The persisted sub-tag, attached if missing. getCompoundTag returns a fresh,
     * detached compound when the key is absent, so it has to be set back.
     */
    private static NBTTagCompound persisted(EntityPlayer player) {
        NBTTagCompound data = player.getEntityData();
        NBTTagCompound persisted = data.getCompoundTag(EntityPlayer.PERSISTED_NBT_TAG);
        if (!data.hasKey(EntityPlayer.PERSISTED_NBT_TAG)) {
            data.setTag(EntityPlayer.PERSISTED_NBT_TAG, persisted);
        }
        return persisted;
    }
}
