package com.questforge.commands;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import net.minecraft.command.CommandBase;
import net.minecraft.entity.player.EntityPlayerMP;
import net.minecraft.server.MinecraftServer;
import net.minecraft.util.ChatComponentText;
import net.minecraft.util.EnumChatFormatting;
import net.minecraft.util.MathHelper;
import net.minecraft.world.WorldServer;

/**
 * /tpa and /tpaccept: ask to teleport to a friend, and let them say yes.
 *
 * The one social command the pack hands out. Without it a group of friends in a
 * 49,000-block world drifts apart within an evening, because non-ops otherwise
 * have no way to reach each other but walking (server-readiness, section 6).
 *
 * <h3>Only the asker moves, and only when told yes</h3>
 *
 * Nobody can pull another player to them. The asker arrives where the other
 * stands, after that player types /tpaccept, and a request that is not answered
 * expires in {@link #EXPIRES_SECONDS}. That keeps the command harmless under
 * the PvP rule the owner chose (friendly fire is part of the game): it cannot
 * drag anyone into a fight, and whoever says yes sees who is coming.
 *
 * <h3>The ticket is the asker's</h3>
 *
 * Both words share one unlock, like /home and /sethome, but only /tpa checks
 * it. /tpaccept is free to everyone: a ticket that let you ask but let nobody
 * answer would be worthless until a second ticket turned up in the right
 * hands, and the natural first use is one friend holding a ticket and joining
 * one who does not. {@link #needsUnlock} is where that is said.
 *
 * <h3>Dimensions</h3>
 *
 * Crosses them the way /home does: the exact spot is known, so the landing
 * search is skipped and {@link SafeTeleporter} is used only for what it refuses
 * to do, which is dig a portal on arrival.
 */
public class TpaAccess extends Unlockable {

    /** How long a request stays open. */
    public static final int EXPIRES_SECONDS = 60;

    /**
     * Open requests, keyed by the player who was asked. One open request per
     * target: a newer one replaces an older one, and the replaced asker is told.
     * Kept on the server only; a server restart forgets them, which is right.
     */
    private static final Map<UUID, Request> PENDING = new HashMap<UUID, Request>();

    private static final class Request {
        final UUID from;
        final String fromName;
        final long expiresAt;

        Request(EntityPlayerMP from) {
            this.from = from.getUniqueID();
            this.fromName = from.getCommandSenderName();
            this.expiresAt = System.currentTimeMillis() + EXPIRES_SECONDS * 1000L;
        }

        boolean expired() {
            return System.currentTimeMillis() > this.expiresAt;
        }
    }

    public TpaAccess() {
        super("tpa", new String[] { "tpa", "tpaccept" }, "Teleport Request",
                "Two commands, one ticket.",
                "",
                EnumChatFormatting.WHITE + "/tpa <player>" + EnumChatFormatting.GRAY
                        + " asks to teleport to a friend.",
                EnumChatFormatting.WHITE + "/tpaccept" + EnumChatFormatting.GRAY
                        + " is their answer, and needs no ticket:",
                "anyone can accept, so your ticket is enough for",
                "the two of you.",
                "",
                "You arrive where they stand, from anywhere, including",
                "from another dimension. A request expires after " + EXPIRES_SECONDS,
                "seconds; asking again replaces it. Nothing is consumed.",
                "",
                "Only the asker ever moves. Nobody can pull you to them",
                "with this; they can only come to you, and only when",
                "you say yes.",
                "",
                "A rare find in world loot.");
    }

    /** /tpaccept is an answer, not a privilege; see the class comment. */
    @Override
    public boolean needsUnlock(String name) {
        return !"tpaccept".equals(name);
    }

    /** Forgets every open request; called when a server starts. */
    public static void reset() {
        PENDING.clear();
    }

    @Override
    public String refuse(EntityPlayerMP player, String name, String[] args) {
        return "tpaccept".equals(name) ? refuseAccept(player) : refuseAsk(player, args);
    }

    private static String refuseAsk(EntityPlayerMP player, String[] args) {
        if (args.length != 1) {
            return "Usage: /tpa <player>";
        }

        EntityPlayerMP target = byName(args[0]);

        if (target == null) {
            return "No player called " + args[0] + " is online.";
        }

        if (target == player) {
            return "You are already there.";
        }

        if (player.ridingEntity != null || player.riddenByEntity != null) {
            // The same refusal as every other trip here: a mounted transfer
            // strands the mount and sometimes the rider.
            return "Dismount first.";
        }

        return null;
    }

    private static String refuseAccept(EntityPlayerMP player) {
        Request req = PENDING.get(player.getUniqueID());

        if (req == null) {
            return "Nobody has asked to teleport to you.";
        }

        if (req.expired()) {
            PENDING.remove(player.getUniqueID());
            return req.fromName + "'s request has expired. They can ask again.";
        }

        EntityPlayerMP from = byUUID(req.from);

        if (from == null) {
            PENDING.remove(player.getUniqueID());
            return req.fromName + " is no longer online.";
        }

        if (from.ridingEntity != null || from.riddenByEntity != null) {
            return req.fromName + " is riding something and has to dismount first.";
        }

        MinecraftServer server = MinecraftServer.getServer();

        if (server == null || server.worldServerForDimension(player.dimension) == null) {
            return "The dimension you are in is not loaded on this server.";
        }

        return null;
    }

    @Override
    public String run(EntityPlayerMP player, String name, String[] args) {
        return "tpaccept".equals(name) ? accept(player) : ask(player, args);
    }

    private static String ask(EntityPlayerMP player, String[] args) {
        EntityPlayerMP target = byName(args[0]);

        if (target == null) {
            // refuse() saw them a moment ago; they logged out in between.
            return EnumChatFormatting.YELLOW + "No player called " + args[0] + " is online.";
        }

        Request old = PENDING.put(target.getUniqueID(), new Request(player));

        target.addChatMessage(new ChatComponentText(EnumChatFormatting.GOLD
                + player.getCommandSenderName() + EnumChatFormatting.GRAY
                + " wants to teleport to you."));
        target.addChatMessage(new ChatComponentText(EnumChatFormatting.GRAY + "Type "
                + EnumChatFormatting.GREEN + "/tpaccept" + EnumChatFormatting.GRAY + " within "
                + EXPIRES_SECONDS + " seconds to let them. Ignore it to say no."));

        if (old != null && !old.expired() && !old.from.equals(player.getUniqueID())) {
            EntityPlayerMP replaced = byUUID(old.from);

            if (replaced != null) {
                replaced.addChatMessage(new ChatComponentText(EnumChatFormatting.GRAY
                        + "Your request to " + target.getCommandSenderName()
                        + " was replaced by " + player.getCommandSenderName() + "'s."));
            }
        }

        return EnumChatFormatting.GRAY + "Asked " + EnumChatFormatting.WHITE
                + target.getCommandSenderName() + EnumChatFormatting.GRAY
                + ". The request expires in " + EXPIRES_SECONDS + " seconds.";
    }

    private static String accept(EntityPlayerMP player) {
        Request req = PENDING.remove(player.getUniqueID());

        if (req == null) {
            return EnumChatFormatting.YELLOW + "Nobody has asked to teleport to you.";
        }

        EntityPlayerMP from = byUUID(req.from);

        if (from == null) {
            // refuse() ruled this out; the asker logged out in between.
            return EnumChatFormatting.YELLOW + req.fromName + " is no longer online.";
        }

        teleport(from, player);

        from.addChatMessage(new ChatComponentText(EnumChatFormatting.GRAY
                + player.getCommandSenderName() + " said yes."));

        return EnumChatFormatting.GRAY + from.getCommandSenderName() + " is here.";
    }

    /** Puts `who` where `to` stands, crossing dimensions the way /home does. */
    private static void teleport(EntityPlayerMP who, EntityPlayerMP to) {
        double x = to.posX;
        double y = to.posY;
        double z = to.posZ;

        if (who.dimension != to.dimension) {
            WorldServer destination = MinecraftServer.getServer().worldServerForDimension(to.dimension);

            new SafeTeleporter(destination, new int[] {
                MathHelper.floor_double(x),
                MathHelper.floor_double(y),
                MathHelper.floor_double(z) }).transfer(who, to.dimension);
        }

        who.playerNetServerHandler.setPlayerLocation(x, y, z, to.rotationYaw, to.rotationPitch);
        who.fallDistance = 0F;
    }

    private static EntityPlayerMP byName(String name) {
        MinecraftServer server = MinecraftServer.getServer();
        return server == null ? null : server.getConfigurationManager().func_152612_a(name);
    }

    private static EntityPlayerMP byUUID(UUID id) {
        MinecraftServer server = MinecraftServer.getServer();

        if (server == null) {
            return null;
        }

        for (Object o : server.getConfigurationManager().playerEntityList) {
            EntityPlayerMP p = (EntityPlayerMP) o;

            if (id.equals(p.getUniqueID())) {
                return p;
            }
        }

        return null;
    }

    @Override
    @SuppressWarnings("rawtypes")
    public List tabComplete(EntityPlayerMP player, String name, String[] args) {
        if ("tpa".equals(name) && args.length == 1) {
            return CommandBase.getListOfStringsMatchingLastWord(args,
                    MinecraftServer.getServer().getAllUsernames());
        }

        return null;
    }
}
