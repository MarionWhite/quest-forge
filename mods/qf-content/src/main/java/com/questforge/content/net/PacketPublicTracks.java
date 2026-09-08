package com.questforge.content.net;

import cpw.mods.fml.common.network.simpleimpl.IMessage;
import cpw.mods.fml.common.network.simpleimpl.IMessageHandler;
import cpw.mods.fml.common.network.simpleimpl.MessageContext;
import io.netty.buffer.ByteBuf;

import java.util.ArrayList;
import java.util.List;

import com.questforge.content.jukebox.PublicCache;
import com.questforge.content.jukebox.Track;

/** The songs in one shared playlist, sent when somebody opens it. */
public class PacketPublicTracks implements IMessage {

    public String id = "";
    public List<Track> tracks = new ArrayList<Track>();

    /** Required by the packet codec. */
    public PacketPublicTracks() { }

    public PacketPublicTracks(String id, List<Track> tracks) {
        this.id = id == null ? "" : id;
        if (tracks != null) this.tracks = tracks;
    }

    @Override
    public void fromBytes(ByteBuf buf) {
        id = TrackCodec.readCapped(buf, 96);
        tracks = TrackCodec.readTracks(buf);
    }

    @Override
    public void toBytes(ByteBuf buf) {
        TrackCodec.writeCapped(buf, id, 96);
        TrackCodec.writeTracks(buf, tracks);
    }

    public static class Handler implements IMessageHandler<PacketPublicTracks, IMessage> {

        @Override
        public IMessage onMessage(PacketPublicTracks m, MessageContext ctx) {
            PublicCache.setTracks(m.id, m.tracks);
            return null;
        }
    }
}
