package com.questforge.content.net;

import cpw.mods.fml.common.network.simpleimpl.IMessage;
import cpw.mods.fml.common.network.simpleimpl.IMessageHandler;
import cpw.mods.fml.common.network.simpleimpl.MessageContext;
import io.netty.buffer.ByteBuf;
import net.minecraft.entity.player.EntityPlayerMP;
import net.minecraft.util.ChatComponentText;
import net.minecraft.util.EnumChatFormatting;

import java.util.ArrayList;
import java.util.List;

import com.questforge.content.jukebox.PublicPlaylists;
import com.questforge.content.jukebox.Track;

/**
 * "Share this playlist" -- or, with {@code share} false, "stop sharing it".
 *
 * Sent when the player ticks the Public box on one of their own playlists. The
 * whole playlist travels because the server is what other people read it from; the
 * client keeps its own copy either way, so unsharing never costs anyone their
 * songs.
 */
public class PacketPublishPlaylist implements IMessage {

    public boolean share;
    public String name = "";
    public List<Track> tracks = new ArrayList<Track>();

    /** Required by the packet codec. */
    public PacketPublishPlaylist() { }

    public PacketPublishPlaylist(boolean share, String name, List<Track> tracks) {
        this.share = share;
        this.name = name == null ? "" : name;
        if (tracks != null) this.tracks = tracks;
    }

    @Override
    public void fromBytes(ByteBuf buf) {
        share = buf.readBoolean();
        name = TrackCodec.readCapped(buf, PublicPlaylists.MAX_NAME);
        tracks = share ? TrackCodec.readTracks(buf) : new ArrayList<Track>();
    }

    @Override
    public void toBytes(ByteBuf buf) {
        buf.writeBoolean(share);
        TrackCodec.writeCapped(buf, name, PublicPlaylists.MAX_NAME);
        if (share) TrackCodec.writeTracks(buf, tracks);
    }

    public static class Handler
            implements IMessageHandler<PacketPublishPlaylist, IMessage> {

        @Override
        public IMessage onMessage(final PacketPublishPlaylist m, MessageContext ctx) {
            final EntityPlayerMP player = ctx.getServerHandler().playerEntity;
            if (player == null) return null;

            // Runs on the netty thread. The store is synchronized and writes a file,
            // so it goes on the server thread with everything else that touches the
            // save folder.
            ServerTasks.submit(new Runnable() {
                @Override public void run() {
                    String id = player.getUniqueID().toString();
                    String result = m.share
                            ? PublicPlaylists.publish(id, player.getCommandSenderName(),
                                                      m.name, m.tracks)
                            : PublicPlaylists.unpublish(id, m.name, isOperator(player));

                    player.addChatMessage(new ChatComponentText(
                            EnumChatFormatting.AQUA + "[jukebox] "
                            + EnumChatFormatting.RESET + result));

                    // Everyone's Public tab is now out of date, including the
                    // publisher's own.
                    PacketPublicIndex.broadcast();
                }
            });
            return null;
        }

        private static boolean isOperator(EntityPlayerMP player) {
            try {
                return net.minecraft.server.MinecraftServer.getServer()
                        .getConfigurationManager()
                        .func_152596_g(player.getGameProfile());
            } catch (Throwable t) {
                return false;
            }
        }
    }
}
