package com.questforge.content.ench;

import java.util.Random;

import net.minecraft.entity.player.EntityPlayer;
import net.minecraft.entity.player.EntityPlayerMP;
import net.minecraft.inventory.Container;
import net.minecraft.inventory.Slot;
import net.minecraft.item.ItemStack;
import net.minecraft.util.ChatComponentText;
import net.minecraft.util.EnumChatFormatting;

/**
 * Called from bytecode injected into Container.slotClick by ContainerTransformer.
 *
 * Returning true means "we handled this click"; the injected code then returns
 * from slotClick without running vanilla's swap.
 */
public class QFHooks {

    private static final Random RAND = new Random();

    /**
     * @return true if this click was an enchantment book application.
     */
    public static boolean onSlotClick(Container container, int slotId, int button,
            int mode, EntityPlayer player) {
        try {
            // Plain left-click only. Shift-click, drag-paint and number keys stay vanilla.
            if (mode != 0 || button != 0) return false;
            if (slotId < 0 || player == null || container == null) return false;

            ItemStack cursor = player.inventory.getItemStack();
            if (cursor == null) return false;

            Slot slot = container.getSlot(slotId);
            if (slot == null) return false;

            ItemStack target = slot.getStack();
            if (target == null) return false;

            if (BookNBT.isBook(cursor)) {
                QFEnchantment ench = BookNBT.getEnchant(cursor);
                if (ench == null || !ench.canApply(target)) return false;

                // From here we own the click on both sides. The client does nothing
                // and waits for the server's slot update, which avoids showing a
                // swap that is about to be corrected.
                if (player.worldObj.isRemote) return true;

                resolve(container, player, slot, target, cursor);
                return true;
            }

            if (cursor.getItem() instanceof ItemConsumable) {
                return useConsumable(container, player, slot, target, cursor);
            }

            return false;

        } catch (Throwable t) {
            // A crash here would break every inventory click in the game.
            System.err.println("[QuestForgeContent] error in slot-click hook: " + t);
            t.printStackTrace();
            return false;
        }
    }

    /**
     * Magic Dust, Ward Scroll, Binding Scroll, Solvent.
     *
     * @return true if the click belongs to us.
     */
    private static boolean useConsumable(Container container, EntityPlayer player,
            Slot slot, ItemStack target, ItemStack cursor) {

        int meta = cursor.getItemDamage();
        if (!ConsumableUse.applies(meta, target)) return false;

        // Both sides agree the click is ours; only the server decides what happened.
        if (player.worldObj.isRemote) return true;

        ConsumableUse.Outcome outcome = ConsumableUse.apply(meta, target, RAND);
        if (outcome == null) return false;

        if (outcome.spent) {
            cursor.stackSize--;
            if (cursor.stackSize <= 0) player.inventory.setItemStack(null);
            say(player, EnumChatFormatting.AQUA, outcome.message);
        } else {
            say(player, EnumChatFormatting.GRAY, outcome.message);
        }

        slot.putStack(target);
        slot.onSlotChanged();
        container.detectAndSendChanges();
        if (player instanceof EntityPlayerMP) {
            ((EntityPlayerMP) player).updateHeldItem();
        }
        return true;
    }

    private static void resolve(Container container, EntityPlayer player, Slot slot,
            ItemStack target, ItemStack book) {

        EnchantApplication.Result result = EnchantApplication.apply(target, book, RAND);
        if (result == EnchantApplication.Result.INVALID) {
            // Leave the click alone entirely rather than silently eating the book.
            return;
        }

        // The book is consumed on any resolved outcome.
        book.stackSize--;
        if (book.stackSize <= 0) {
            player.inventory.setItemStack(null);
        }

        switch (result) {
            case SUCCESS:
                slot.putStack(target);
                say(player, EnumChatFormatting.GREEN, "The enchantment takes hold.");
                break;
            case FAILED:
                slot.putStack(target);
                say(player, EnumChatFormatting.YELLOW, "The enchantment fails, but the item holds.");
                break;
            case DESTROYED:
                slot.putStack(null);
                say(player, EnumChatFormatting.RED, "The enchantment fails and the item shatters.");
                break;
            case WARDED:
                slot.putStack(target);
                say(player, EnumChatFormatting.LIGHT_PURPLE,
                        "The ward burns away and takes the shattering with it.");
                break;
            default:
                break;
        }

        slot.onSlotChanged();
        container.detectAndSendChanges();
        if (player instanceof EntityPlayerMP) {
            ((EntityPlayerMP) player).updateHeldItem();
        }
    }

    private static void say(EntityPlayer player, EnumChatFormatting colour, String message) {
        player.addChatMessage(new ChatComponentText(colour + message));
    }
}
