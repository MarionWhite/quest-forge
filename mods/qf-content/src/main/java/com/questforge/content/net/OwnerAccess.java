package com.questforge.content.net;

import com.questforge.content.jukebox.BlockJukebox;
import com.questforge.content.jukebox.ItemSpeaker;
import com.questforge.content.jukebox.SpeakerRegistry;

import net.minecraft.entity.player.EntityPlayerMP;
import net.minecraft.item.ItemStack;
import net.minecraft.world.World;

/**
 * Whether a player is, at this moment, at the controls of a given owner.
 *
 * <h3>Why this exists</h3>
 * A speaker used to be editable only by someone standing next to it, and that single
 * rule was the whole of its security: a client could not rename or silence a speaker
 * across the map because it could not reach one. Opening a speaker's screen from the
 * jukebox breaks that rule by design -- the entire point is to tune a speaker that is
 * a hundred blocks away -- so the rule has to be replaced rather than dropped.
 *
 * What replaces it is the pairing. A speaker may be operated remotely by whoever is
 * currently working the thing it is paired to, and by nobody else. That is a real
 * claim rather than a weaker one: to reach a speaker this way you must already be
 * standing at its jukebox, or holding its JBL, and the speaker must already have
 * agreed to answer to that owner.
 *
 * <h3>What is checked, and what is never trusted</h3>
 * The owner key handed in here comes from the speaker's own registry entry on the
 * server -- never from the packet. A client cannot name the owner it would like to be
 * verified against; it can only ask about a speaker, and the server looks up who that
 * speaker actually answers to. So the worst a forged packet can do is ask a question
 * about a speaker it has no relationship with, and get told no.
 *
 * The two owner forms are checked the way they are earned: a jukebox has to still be
 * a jukebox, in this dimension, within arm's reach; a JBL has to be the one in the
 * player's hand, which is also the only time it can play.
 */
public final class OwnerAccess {

    /** How far a player may be from their own jukebox while working its screen. */
    public static final double REACH = 24.0;

    private OwnerAccess() { }

    public static boolean controls(EntityPlayerMP player, String owner) {
        if (player == null || owner == null || owner.isEmpty()) return false;
        if (owner.startsWith("S:")) return holdingThatSpeaker(player, owner);
        if (owner.startsWith("B:")) return standingAtThatJukebox(player, owner);
        return false;
    }

    private static boolean holdingThatSpeaker(EntityPlayerMP player, String owner) {
        ItemStack held = player.getHeldItem();
        if (held == null || !(held.getItem() instanceof ItemSpeaker)) return false;
        String id = ItemSpeaker.id(held);
        // Rebuilt through itemOwner rather than compared by substring, so the two
        // ends cannot drift apart if the key format is ever changed.
        return !id.isEmpty() && owner.equals(SpeakerRegistry.itemOwner(id));
    }

    private static boolean standingAtThatJukebox(EntityPlayerMP player, String owner) {
        String[] part = owner.split(":");
        if (part.length != 5) return false;

        final int dim, x, y, z;
        try {
            dim = Integer.parseInt(part[1]);
            x = Integer.parseInt(part[2]);
            y = Integer.parseInt(part[3]);
            z = Integer.parseInt(part[4]);
        } catch (NumberFormatException malformed) {
            return false;
        }

        if (dim != player.dimension) return false;

        World world = player.worldObj;
        // blockExists first: asking for a block in an unloaded chunk would load it,
        // and a packet handler is not a good reason to pull chunks off the disk.
        if (!world.blockExists(x, y, z)) return false;
        if (!(world.getBlock(x, y, z) instanceof BlockJukebox)) return false;

        double dx = x + 0.5 - player.posX;
        double dy = y + 0.5 - player.posY;
        double dz = z + 0.5 - player.posZ;
        return dx * dx + dy * dy + dz * dz <= REACH * REACH;
    }
}
