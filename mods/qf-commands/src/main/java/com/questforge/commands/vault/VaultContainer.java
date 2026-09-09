package com.questforge.commands.vault;

import net.minecraft.entity.player.EntityPlayer;
import net.minecraft.inventory.Container;
import net.minecraft.inventory.Slot;
import net.minecraft.item.ItemStack;

/** Slot layout for the vault: six rows over the player's inventory. */
public class VaultContainer extends Container {

    private final VaultInventory vault;

    public VaultContainer(EntityPlayer player, VaultInventory vault) {
        this.vault = vault;

        for (int row = 0; row < VaultInventory.ROWS; row++) {
            for (int col = 0; col < VaultInventory.COLUMNS; col++) {
                addSlotToContainer(new Slot(vault,
                        col + row * VaultInventory.COLUMNS, 8 + col * 18, 18 + row * 18));
            }
        }

        int top = 18 + VaultInventory.ROWS * 18 + 13;

        for (int row = 0; row < 3; row++) {
            for (int col = 0; col < 9; col++) {
                addSlotToContainer(new Slot(player.inventory,
                        col + row * 9 + 9, 8 + col * 18, top + row * 18));
            }
        }

        for (int col = 0; col < 9; col++) {
            addSlotToContainer(new Slot(player.inventory, col, 8 + col * 18, top + 58));
        }
    }

    @Override
    public boolean canInteractWith(EntityPlayer player) {
        return this.vault.isUseableByPlayer(player);
    }

    @Override
    public ItemStack transferStackInSlot(EntityPlayer player, int index) {
        Slot slot = (Slot) this.inventorySlots.get(index);

        if (slot == null || !slot.getHasStack()) {
            return null;
        }

        ItemStack stack = slot.getStack();
        ItemStack copy = stack.copy();
        int vaultEnd = VaultInventory.SIZE;

        // Shift-click moves between the vault and the player, never within one.
        boolean moved = index < vaultEnd
                ? mergeItemStack(stack, vaultEnd, this.inventorySlots.size(), true)
                : mergeItemStack(stack, 0, vaultEnd, false);

        if (!moved) {
            return null;
        }

        if (stack.stackSize == 0) {
            slot.putStack(null);
        } else {
            slot.onSlotChanged();
        }

        return copy;
    }

    @Override
    public void onContainerClosed(EntityPlayer player) {
        super.onContainerClosed(player);

        // Belt and braces: markDirty already saves each change, but the drag
        // and double-click paths reach the inventory in ways that have been
        // known to skip it.
        if (!player.worldObj.isRemote) {
            this.vault.save();
        }
    }
}
