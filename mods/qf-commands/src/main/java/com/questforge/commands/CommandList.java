package com.questforge.commands;

import net.minecraft.command.CommandBase;
import net.minecraft.command.ICommandSender;
import net.minecraft.entity.player.EntityPlayerMP;
import net.minecraft.util.ChatComponentText;
import net.minecraft.util.EnumChatFormatting;

/** /commands -- what this player has earned, and what is still out there. */
public class CommandList extends CommandBase {

    @Override
    public String getCommandName() {
        return "commands";
    }

    @Override
    public String getCommandUsage(ICommandSender sender) {
        return "/commands";
    }

    @Override
    public int getRequiredPermissionLevel() {
        return 0;
    }

    @Override
    public void processCommand(ICommandSender sender, String[] args) {
        if (!(sender instanceof EntityPlayerMP)) {
            return;
        }

        EntityPlayerMP player = (EntityPlayerMP) sender;
        int owned = 0;

        player.addChatMessage(new ChatComponentText(
                EnumChatFormatting.GOLD + "--- Commands you have earned ---"));

        for (Unlockable u : Unlockables.all()) {
            if (Unlocks.has(player, u.id)) {
                owned++;
                player.addChatMessage(new ChatComponentText(
                        EnumChatFormatting.GREEN + "/" + u.command()
                                + EnumChatFormatting.DARK_GRAY + "  " + u.title));
            }
        }

        if (owned == 0) {
            player.addChatMessage(new ChatComponentText(
                    EnumChatFormatting.GRAY + "None yet. They come from lottery tickets."));
        }

        player.addChatMessage(new ChatComponentText(EnumChatFormatting.DARK_GRAY
                + String.valueOf(owned) + " of " + Unlockables.count() + " found."));
    }
}
