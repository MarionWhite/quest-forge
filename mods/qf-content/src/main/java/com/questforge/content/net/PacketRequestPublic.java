package com.questforge.content.net;

import cpw.mods.fml.common.network.simpleimpl.IMessage;
import cpw.mods.fml.common.network.simpleimpl.IMessageHandler;
import cpw.mods.fml.common.network.simpleimpl.MessageContext;
import io.netty.buffer.ByteBuf;
import net.minecraft.entity.player.EntityPlayerMP;

import com.questforge.content.jukebox.PublicPlaylists;

/**
 * "Send me the shared playlists." An empty id asks for the index; an id asks for
 * that one playlist's songs.
 *
 * The client asks rather than being pushed everything on join, because most
 * sessions never open the Public tab and a playlist nobody looks at should cost
 * nothing to have.
 */
public class PacketRequestPublic implements IMessage {

    public String id = "";

    /** Required by the packet codec. */
    public PacketRequestPublic() { }

    public PacketRequestPublic(String id) { this.id = id == null ? "" : id; }

    @Override
    public void fromBytes(ByteBuf buf) { id = TrackCodec.readCapped(buf, 96); }

    @Override
    public void toBytes(ByteBuf buf) { TrackCodec.writeCapped(buf, id, 96); }

    public static class Handler implements IMessageHandler<PacketRequestPublic, IMessage> {

        @Override
        public IMessage onMessage(final PacketRequestPublic m, MessageContext ctx) {
            final EntityPlayerMP player = ctx.getServerHandler().playerEntity;
            if (player == null) return null;

            ServerTasks.submit(new Runnable() {
                @Override public void run() {
                    if (m.id.isEmpty()) {
                        QFNetwork.toPlayer(
                                new PacketPublicIndex(PublicPlaylists.index()), player);
                        return;
                    }
                    PublicPlaylists.Entry e = PublicPlaylists.byId(m.id);
                    // A playlist taken down between the browse and the open is not
                    // an error; the empty reply tells the screen to say so.
                    QFNetwork.toPlayer(new PacketPublicTracks(m.id,
                            e == null ? null : e.tracks), player);
                }
            });
            return null;
        }
    }
}
