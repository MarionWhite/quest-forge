package com.questforge.commands.vault;

import net.minecraft.entity.player.EntityPlayer;
import net.minecraft.inventory.InventoryBasic;
import net.minecraft.item.ItemStack;
import net.minecraft.nbt.NBTTagCompound;
import net.minecraft.nbt.NBTTagList;

/**
 * A player's private vault: 54 slots, theirs alone, nowhere in the world.
 *
 * Deliberately NOT an ender chest. The ender inventory is a single shared
 * container per player that half a dozen mods in this pack already read, write,
 * link to and upgrade -- putting a second door onto it would mean this command
 * quietly fights EnderStorage and Ender Utilities over the same slots. This has
 * its own storage and cannot collide with any of them.
 *
 * Stored in the persistent half of the player's NBT for the same reason the
 * unlocks are: it follows the player through death and dimension changes, and a
 * world copied without knowing about this mod does not lose anyone's things.
 */
public class VaultInventory extends InventoryBasic {

    public static final int ROWS = 6;
    public static final int COLUMNS = 9;
    public static final int SIZE = ROWS * COLUMNS;

    private static final String ROOT = "QFCommands";
    private static final String TAG = "Vault";

    private final EntityPlayer owner;

    /** Suppresses writing back the contents we are in the middle of reading. */
    private boolean loading;

    public VaultInventory(EntityPlayer owner) {
        super("Personal Vault", false, SIZE);
        this.owner = owner;
        load();
    }

    private NBTTagCompound persisted() {
        NBTTagCompound data = this.owner.getEntityData();
        NBTTagCompound persist = data.getCompoundTag(EntityPlayer.PERSISTED_NBT_TAG);
        data.setTag(EntityPlayer.PERSISTED_NBT_TAG, persist);
        NBTTagCompound mine = persist.getCompoundTag(ROOT);
        persist.setTag(ROOT, mine);
        return mine;
    }

    private void load() {
        this.loading = true;

        try {
            NBTTagList list = persisted().getTagList(TAG, 10);   // 10 == compound

            for (int i = 0; i < list.tagCount(); i++) {
                NBTTagCompound entry = list.getCompoundTagAt(i);
                int slot = entry.getByte("Slot") & 255;

                if (slot < SIZE) {
                    setInventorySlotContents(slot, ItemStack.loadItemStackFromNBT(entry));
                }
            }
        } finally {
            this.loading = false;
        }
    }

    /**
     * Saves on every change, which is cheaper than it sounds.
     *
     * {@link #save} only rewrites a tag on the player's in-memory NBT -- the
     * disk write happens when the player is saved, on the server's own
     * schedule, whatever we do here. Saving only when the screen closed left a
     * window where logging out or crashing with the vault open lost everything
     * in it, which is not a trade worth making for an allocation.
     */
    @Override
    public void markDirty() {
        super.markDirty();

        if (!this.loading) {
            save();
        }
    }

    /** Writes the vault back onto the player. */
    public void save() {
        NBTTagList list = new NBTTagList();

        for (int slot = 0; slot < SIZE; slot++) {
            ItemStack stack = getStackInSlot(slot);

            if (stack == null) {
                continue;
            }

            NBTTagCompound entry = new NBTTagCompound();
            entry.setByte("Slot", (byte) slot);
            stack.writeToNBT(entry);
            list.appendTag(entry);
        }

        persisted().setTag(TAG, list);
    }

    @Override
    public boolean isUseableByPlayer(EntityPlayer player) {
        return player == this.owner;
    }
}
