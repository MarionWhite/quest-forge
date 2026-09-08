package com.questforge.content.net;

import cpw.mods.fml.common.network.simpleimpl.IMessage;
import cpw.mods.fml.common.network.simpleimpl.IMessageHandler;
import cpw.mods.fml.common.network.simpleimpl.MessageContext;
import io.netty.buffer.ByteBuf;
import net.minecraft.entity.player.EntityPlayerMP;
import net.minecraft.server.MinecraftServer;
import net.minecraft.util.MathHelper;

import java.util.ArrayList;
import java.util.List;

import com.questforge.content.jukebox.PublicCache;
import com.questforge.content.jukebox.PublicPlaylists;

/**
 * What the Public tab lists: every shared playlist's name, who shared it and how
 * many songs it holds -- but not the songs.
 *
 * Splitting the index from the songs is what keeps this feature cheap. Browsing
 * costs one small packet however many playlists exist, and the songs travel only
 * for the one playlist somebody actually opens.
 */
public class PacketPublicIndex implements IMessage {

    /** Enough to browse; a server holding more than this has other problems. */
    private static final int MAX_ENTRIES = 100;

    public List<PublicPlaylists.Entry> entries = new ArrayList<PublicPlaylists.Entry>();

    /** Required by the packet codec. */
    public PacketPublicIndex() { }

    public PacketPublicIndex(List<PublicPlaylists.Entry> entries) {
        if (entries != null) this.entries = entries;
    }

    @Override
    public void fromBytes(ByteBuf buf) {
        int n = MathHelper.clamp_int(buf.readShort(), 0, MAX_ENTRIES);
        entries = new ArrayList<PublicPlaylists.Entry>(n);

        for (int i = 0; i < n; i++) {
            PublicPlaylists.Entry e = new PublicPlaylists.Entry();
            e.id = TrackCodec.readCapped(buf, 96);
            e.name = TrackCodec.readCapped(buf, PublicPlaylists.MAX_NAME);
            e.owner = TrackCodec.readCapped(buf, 32);
            e.ownerId = TrackCodec.readCapped(buf, 40);
            e.count = MathHelper.clamp_int(buf.readShort(), 0, PublicPlaylists.MAX_TRACKS);
            e.published = buf.readLong();
            if (!e.id.isEmpty() && !e.name.isEmpty()) entries.add(e);
        }
    }

    @Override
    public void toBytes(ByteBuf buf) {
        int n = Math.min(entries.size(), MAX_ENTRIES);
        buf.writeShort(n);

        for (int i = 0; i < n; i++) {
            PublicPlaylists.Entry e = entries.get(i);
            TrackCodec.writeCapped(buf, e.id, 96);
            TrackCodec.writeCapped(buf, e.name, PublicPlaylists.MAX_NAME);
            TrackCodec.writeCapped(buf, e.owner, 32);
            TrackCodec.writeCapped(buf, e.ownerId, 40);
            buf.writeShort(Math.min(e.count, PublicPlaylists.MAX_TRACKS));
            buf.writeLong(e.published);
        }
    }

    /** Pushes the fresh list to everyone, after any change to what is shared. */
    public static void broadcast() {
        MinecraftServer server = MinecraftServer.getServer();
        if (server == null) return;

        PacketPublicIndex message = new PacketPublicIndex(PublicPlaylists.index());
        try {
            @SuppressWarnings("unchecked")
            List<Object> players = server.getConfigurationManager().playerEntityList;
            for (int i = 0; i < players.size(); i++) {
                Object p = players.get(i);
                if (p instanceof EntityPlayerMP) {
                    QFNetwork.toPlayer(message, (EntityPlayerMP) p);
                }
            }
        } catch (Throwable t) {
            com.questforge.content.QuestForgeContent.log.warn(
                    "[jukebox] could not send the shared playlist index", t);
        }
    }

    public static class Handler implements IMessageHandler<PacketPublicIndex, IMessage> {

        @Override
        public IMessage onMessage(PacketPublicIndex m, MessageContext ctx) {
            // Plain data into a plain store; the screen reads it on its next frame,
            // so there is nothing here that needs the client thread.
            PublicCache.setIndex(m.entries);
            return null;
        }
    }
}
