package com.questforge.content.net;

import cpw.mods.fml.common.network.simpleimpl.IMessage;
import cpw.mods.fml.common.network.simpleimpl.IMessageHandler;
import cpw.mods.fml.common.network.simpleimpl.MessageContext;
import io.netty.buffer.ByteBuf;
import net.minecraft.entity.player.EntityPlayerMP;
import net.minecraft.item.ItemStack;
import net.minecraft.util.ChatComponentText;
import net.minecraft.util.EnumChatFormatting;

import java.util.ArrayList;
import java.util.List;

import com.questforge.content.ModItems;
import com.questforge.content.jukebox.ItemVinyl;
import com.questforge.content.jukebox.PublicPlaylists;
import com.questforge.content.jukebox.Track;

/**
 * "Press these songs onto the record I am holding."
 *
 * The client composes the list but cannot write it: item NBT edited client-side is
 * overwritten by the next sync, so a record pressed that way would read blank the
 * moment anyone looked at it properly. The server writes it, having checked the
 * player really is holding a blank one.
 */
public class PacketWriteRecord implements IMessage {

    public String name = "";
    public List<Track> tracks = new ArrayList<Track>();

    /** Required by the packet codec. */
    public PacketWriteRecord() { }

    public PacketWriteRecord(String name, List<Track> tracks) {
        this.name = name == null ? "" : name;
        if (tracks != null) this.tracks = tracks;
    }

    @Override
    public void fromBytes(ByteBuf buf) {
        name = TrackCodec.readCapped(buf, PublicPlaylists.MAX_NAME);
        tracks = TrackCodec.readTracks(buf);
    }

    @Override
    public void toBytes(ByteBuf buf) {
        TrackCodec.writeCapped(buf, name, PublicPlaylists.MAX_NAME);
        TrackCodec.writeTracks(buf, tracks);
    }

    public static class Handler implements IMessageHandler<PacketWriteRecord, IMessage> {

        @Override
        public IMessage onMessage(final PacketWriteRecord m, MessageContext ctx) {
            final EntityPlayerMP player = ctx.getServerHandler().playerEntity;
            if (player == null) return null;

            ServerTasks.submit(new Runnable() {
                @Override public void run() {
                    ItemStack held = player.getHeldItem();
                    if (held == null || held.getItem() != ModItems.record) {
                        say(player, "You are not holding a record.");
                        return;
                    }
                    // Pressing over a record that already holds something would
                    // destroy whatever somebody put on it.
                    if (ItemVinyl.isWritten(held)) {
                        say(player, "That record already has something on it.");
                        return;
                    }
                    if (m.tracks.isEmpty()) {
                        say(player, "Nothing to press.");
                        return;
                    }

                    ItemVinyl.write(held, m.name, m.tracks);
                    player.inventory.markDirty();

                    say(player, EnumChatFormatting.GREEN + "Pressed "
                            + m.tracks.size() + " songs onto \"" + m.name + "\".");
                }
            });
            return null;
        }

        private static void say(EntityPlayerMP p, String message) {
            p.addChatMessage(new ChatComponentText(EnumChatFormatting.AQUA + "[jukebox] "
                    + EnumChatFormatting.RESET + message));
        }
    }
}
