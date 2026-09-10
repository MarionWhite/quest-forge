package com.questforge.commands;

import java.util.List;

import net.minecraft.client.renderer.texture.IIconRegister;
import net.minecraft.creativetab.CreativeTabs;
import net.minecraft.entity.player.EntityPlayer;
import net.minecraft.entity.player.EntityPlayerMP;
import net.minecraft.item.Item;
import net.minecraft.item.ItemStack;
import net.minecraft.util.EnumChatFormatting;
import net.minecraft.world.World;

import cpw.mods.fml.relauncher.Side;
import cpw.mods.fml.relauncher.SideOnly;

/**
 * A lottery ticket. Using it grants one command, permanently.
 *
 * One item with a damage value per entry in {@link Unlockables}, rather than one
 * item class each: the sprite is the same ticket every time, the behaviour is
 * identical, and thirty registered items would be thirty things to keep in step
 * for no gain. The damage value is the registry index.
 *
 * The tooltip is long on purpose. This is a rare drop whose whole value is a
 * command the player has never seen, so the item has to teach it: what to type,
 * what it does, what it will not do, and where the ticket came from. A player
 * who reads it should not need to ask anyone anything.
 */
public class ItemTicket extends Item {

    public ItemTicket() {
        setHasSubtypes(true);
        setMaxDamage(0);
        setMaxStackSize(16);
        setUnlocalizedName("qfcommands.ticket");
        setTextureName("qfcommands:lottery_ticket");
        setCreativeTab(CreativeTabs.tabMisc);
    }

    private static Unlockable of(ItemStack stack) {
        return Unlockables.byIndex(stack.getItemDamage());
    }

    @Override
    public String getItemStackDisplayName(ItemStack stack) {
        Unlockable u = of(stack);
        return u == null
                ? "Lottery Ticket"
                : EnumChatFormatting.GOLD + "Lottery Ticket: " + EnumChatFormatting.YELLOW + u.title;
    }

    @Override
    @SuppressWarnings({ "unchecked", "rawtypes" })
    @SideOnly(Side.CLIENT)
    public void addInformation(ItemStack stack, EntityPlayer player, List lines, boolean advanced) {
        Unlockable u = of(stack);

        if (u == null) {
            lines.add(EnumChatFormatting.RED + "This ticket is for a command that no longer exists.");
            return;
        }

        StringBuilder names = new StringBuilder();

        for (String c : u.commands) {
            names.append(names.length() == 0 ? "" : EnumChatFormatting.DARK_GRAY + "  and  "
                    + EnumChatFormatting.GREEN).append("/").append(c);
        }

        lines.add(EnumChatFormatting.GREEN + names.toString());
        lines.add("");

        for (String line : u.description) {
            lines.add(line.isEmpty() ? "" : EnumChatFormatting.GRAY + line);
        }

        lines.add("");

        if (Unlocks.has(player, u.id)) {
            lines.add(EnumChatFormatting.DARK_GRAY + "You already have this command.");
            lines.add(EnumChatFormatting.DARK_GRAY + "Using this ticket would waste it.");
        } else {
            lines.add(EnumChatFormatting.AQUA + "Right-click to redeem.");
            lines.add(EnumChatFormatting.DARK_GRAY + "One ticket, one player, permanent.");
            lines.add(EnumChatFormatting.DARK_GRAY + "Type " + EnumChatFormatting.WHITE + "/commands"
                    + EnumChatFormatting.DARK_GRAY + " to see everything you have earned.");
        }
    }

    @Override
    public ItemStack onItemRightClick(ItemStack stack, World world, EntityPlayer player) {
        if (world.isRemote) {
            return stack;
        }

        Unlockable u = of(stack);

        if (u == null) {
            return stack;
        }

        // Belt to the creative tab's braces. These tickets are not offered
        // anywhere, but a damage value can still be typed into /give, and
        // spending one would buy a command that does nothing but refuse.
        if (Unlockables.sourceOf(u) == Unlockables.Source.NONE) {
            player.addChatMessage(new net.minecraft.util.ChatComponentText(
                    EnumChatFormatting.YELLOW + "There is no ticket for " + u.title + "."));
            player.addChatMessage(new net.minecraft.util.ChatComponentText(
                    EnumChatFormatting.GRAY + "It has nowhere to arrive, so /" + u.command()
                            + " is left to operators."));
            return stack;
        }

        // Refusing to be consumed is deliberate. A duplicate ticket is worth
        // trading or keeping; silently eating it for nothing is not a fair
        // outcome for something this rare.
        if (!Unlocks.grant(player, u.id)) {
            player.addChatMessage(new net.minecraft.util.ChatComponentText(
                    EnumChatFormatting.YELLOW + "You already have /" + u.command()
                            + ". The ticket is untouched."));
            return stack;
        }

        stack.stackSize--;

        player.addChatMessage(new net.minecraft.util.ChatComponentText(
                EnumChatFormatting.GOLD + "Unlocked " + EnumChatFormatting.GREEN + "/" + u.command()
                        + EnumChatFormatting.GOLD + " -- " + EnumChatFormatting.WHITE + u.title));

        for (String line : u.description) {
            if (!line.isEmpty()) {
                player.addChatMessage(new net.minecraft.util.ChatComponentText(
                        EnumChatFormatting.GRAY + line));
            }
        }

        // The first dimension ticket also teaches the way back, whichever
        // dimension it was for. Redeeming a ticket to Torment and discovering
        // afterwards that nothing brings you home is a trap, not a reward, and
        // the player has no way to see it coming. grant() returns false once
        // they already have it, so this fires exactly once -- and not at all if
        // the ticket they just used was the Overworld's own.
        Unlockable home = Unlockables.wayHome();

        if (u instanceof DimensionTravel && home != null && Unlocks.grant(player, home.id)) {
            player.addChatMessage(new net.minecraft.util.ChatComponentText(""));
            player.addChatMessage(new net.minecraft.util.ChatComponentText(
                    EnumChatFormatting.GOLD + "Also unlocked " + EnumChatFormatting.GREEN + "/"
                            + home.command() + EnumChatFormatting.GOLD + " -- the way back."));
            player.addChatMessage(new net.minecraft.util.ChatComponentText(
                    EnumChatFormatting.GRAY
                            + "Your first journey comes with a way home, so no ticket"));
            player.addChatMessage(new net.minecraft.util.ChatComponentText(
                    EnumChatFormatting.GRAY + "can strand you somewhere you cannot leave."));
        }

        // Never null, even at stackSize 0. ItemInWorldManager.tryUseItem writes
        // whatever comes back straight into the held slot and then reads
        // .stackSize off it -- in creative it assigns to it first -- so a null
        // return is an immediate NPE on the server thread and takes the world
        // down with it. Vanilla's own consumables all decrement and return the
        // same stack; emptying the slot is tryUseItem's job, not ours.
        return stack;
    }

    /**
     * Every ticket that exists -- which is not every command.
     *
     * A Source.NONE entry has no ticket at all: its dimension has nowhere to
     * arrive, so the command only ever refuses, and offering the ticket here
     * meant it could still be picked up and spent on nothing. The index is the
     * damage value, so skipping an entry leaves every other ticket where it
     * was rather than shifting them along.
     */
    @Override
    @SuppressWarnings({ "unchecked", "rawtypes" })
    @SideOnly(Side.CLIENT)
    public void getSubItems(Item item, CreativeTabs tab, List out) {
        for (int i = 0; i < Unlockables.count(); i++) {
            Unlockable u = Unlockables.byIndex(i);

            if (u != null && Unlockables.sourceOf(u) != Unlockables.Source.NONE) {
                out.add(new ItemStack(item, 1, i));
            }
        }
    }

    @Override
    @SideOnly(Side.CLIENT)
    public void registerIcons(IIconRegister register) {
        this.itemIcon = register.registerIcon(getIconString());
    }
}
