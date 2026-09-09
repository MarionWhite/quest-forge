package com.questforge.commands;

import java.util.Arrays;
import java.util.List;

import net.minecraft.command.CommandBase;
import net.minecraft.command.ICommandSender;
import net.minecraft.entity.player.EntityPlayerMP;
import net.minecraft.util.ChatComponentText;
import net.minecraft.util.EnumChatFormatting;

/**
 * The command a ticket unlocks. One instance per name, so an entry that carries
 * both /home and /sethome gets one of these each, sharing an unlock.
 *
 * <h3>There is no operator exemption</h3>
 *
 * There used to be one, and it made the whole mod invisible in singleplayer:
 * ServerConfigurationManager.func_152596_g returns true for the world's owner
 * whenever cheats are on, so the host of any single-player world was silently
 * treated as an operator and every command worked from the first minute,
 * survival or not. The tickets became decorations.
 *
 * The unlock is now the only key, for everybody. An operator who wants a
 * command gives themselves its ticket -- /give works, the ticket is a normal
 * item -- which is one step, leaves a record in their unlocks, and cannot be
 * confused with the mod being broken.
 */
public class UnlockedCommand extends CommandBase {

    private final Unlockable unlockable;
    private final String name;

    public UnlockedCommand(Unlockable unlockable, String name) {
        this.unlockable = unlockable;
        this.name = name;
    }

    @Override
    public String getCommandName() {
        return this.name;
    }

    @Override
    public String getCommandUsage(ICommandSender sender) {
        return "/" + this.name;
    }

    @Override
    public int getRequiredPermissionLevel() {
        return 0;
    }

    @Override
    public boolean canCommandSenderUseCommand(ICommandSender sender) {
        return sender instanceof EntityPlayerMP;
    }

    @Override
    public void processCommand(ICommandSender sender, String[] args) {
        if (!(sender instanceof EntityPlayerMP)) {
            sender.addChatMessage(new ChatComponentText("Only a player can use this."));
            return;
        }

        EntityPlayerMP player = (EntityPlayerMP) sender;

        if (!Unlocks.has(player, this.unlockable.id)) {
            // Says how it is earned rather than just refusing, because a player
            // who types this has just seen the command exist and has no other
            // way to find out what it wants from them.
            player.addChatMessage(new ChatComponentText(EnumChatFormatting.RED
                    + "You have not earned /" + this.name + " yet."));
            player.addChatMessage(new ChatComponentText(EnumChatFormatting.GRAY
                    + "It is granted by a Lottery Ticket: " + this.unlockable.title + "."));

            if (Unlockables.sourceOf(this.unlockable) == Unlockables.Source.IN_DIMENSION) {
                player.addChatMessage(new ChatComponentText(EnumChatFormatting.GRAY
                        + "That ticket is found only inside " + this.unlockable.title
                        + " itself."));
            }
            return;
        }

        String refusal = this.unlockable.refuse(player, this.name, args);

        if (refusal != null) {
            player.addChatMessage(new ChatComponentText(EnumChatFormatting.YELLOW + refusal));
            return;
        }

        String reply = this.unlockable.run(player, this.name, args);

        if (reply != null) {
            player.addChatMessage(new ChatComponentText(reply));
        }
    }

    @Override
    @SuppressWarnings("rawtypes")
    public List getCommandAliases() {
        return Arrays.asList();
    }
}
