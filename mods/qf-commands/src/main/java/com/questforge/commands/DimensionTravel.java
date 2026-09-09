package com.questforge.commands;

import net.minecraft.entity.player.EntityPlayerMP;
import net.minecraft.server.MinecraftServer;
import net.minecraft.util.ChatComponentText;
import net.minecraft.util.EnumChatFormatting;
import net.minecraft.world.WorldServer;

/**
 * A command that sends the player to one dimension.
 *
 * There is one of these per dimension the pack can reach, built from the table
 * in {@link Unlockables}. The ticket for a dimension the pack gates behind a
 * quest line is found <em>inside</em> that dimension, so it is a way back rather
 * than a way in; the reasoning for which dimensions those are is recorded in
 * {@link Unlockables} itself.
 *
 * "As if they had teleported there organically" is taken to mean: you arrive
 * standing on the ground, in the world you asked for, having changed nothing.
 * It does not mean re-running each mod's own portal ritual. Twenty-nine mods
 * have twenty-nine ways in, several of them consume items or build structures,
 * and a command that quietly performed one of those would be doing something the
 * player did not ask for.
 */
public class DimensionTravel extends Unlockable {

    public final int dimension;

    public DimensionTravel(String id, String command, int dimension, String title, String... description) {
        super(id, command, title, description);
        this.dimension = dimension;
    }

    @Override
    public String refuse(EntityPlayerMP player, String name, String[] args) {
        if (player.dimension == this.dimension) {
            return "You are already there.";
        }

        if (player.ridingEntity != null || player.riddenByEntity != null) {
            // Dimension transfer while mounted strands the mount and sometimes
            // the rider. Cheaper to refuse than to explain afterwards.
            return "Dismount first.";
        }

        MinecraftServer server = MinecraftServer.getServer();
        WorldServer destination = server == null
                ? null : server.worldServerForDimension(this.dimension);

        if (destination == null) {
            return "That dimension is not loaded on this server.";
        }

        // Some dimensions are not places you can be dropped into: Compact
        // Machines is a grid of cubes with void between them, and a boss arena
        // does not exist until its fight starts. Arriving there means falling
        // out of the world, so the trip is declined while declining is still
        // possible. findArrival tries the dimension's own entrance and spawn
        // before giving up, so this only fires for a dimension with no floor
        // anywhere -- not merely none under your feet.
        if (SafeTeleporter.findArrival(player, destination) == null) {
            return "There is nowhere to stand in " + this.title
                    + ". This command will not drop you into the void.";
        }

        return null;
    }

    @Override
    public String run(EntityPlayerMP player, String name, String[] args) {
        MinecraftServer server = MinecraftServer.getServer();
        WorldServer destination = server.worldServerForDimension(this.dimension);
        int[] arrival = SafeTeleporter.findArrival(player, destination);

        if (arrival == null) {
            // refuse() already ruled this out; the world changed under us.
            return EnumChatFormatting.YELLOW + "There is nowhere to stand in " + this.title + ".";
        }

        // Announced before the transfer, not after, purely for chat order.
        // transferPlayerToDimension posts PlayerChangedDimensionEvent
        // synchronously, so anything listening to that -- TravelTips, for one --
        // gets its line in before this method can return one, and the reminder
        // ends up above the arrival it is reminding you about.
        player.addChatMessage(new ChatComponentText(
                EnumChatFormatting.GRAY + "Arrived in " + EnumChatFormatting.WHITE + this.title));

        server.getConfigurationManager().transferPlayerToDimension(
                player, this.dimension, new SafeTeleporter(destination, arrival));

        return null;
    }
}
