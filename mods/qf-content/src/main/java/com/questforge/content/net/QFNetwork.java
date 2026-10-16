package com.questforge.content.net;

import net.minecraft.entity.player.EntityPlayerMP;

import cpw.mods.fml.common.network.NetworkRegistry;
import cpw.mods.fml.common.network.simpleimpl.SimpleNetworkWrapper;
import cpw.mods.fml.relauncher.Side;

/**
 * The mod's packet channel.
 *
 * Only one enchantment genuinely needs the network: Jammer, which has to reach
 * into a *different* player's client. Everything else that looked like it needed
 * a packet -- Tracker's outlines, Prospector's readout, Reach's range -- turned
 * out not to, because a client already has its own player's inventory NBT and its
 * own loaded chunks. Those are handled entirely client-side.
 */
public class QFNetwork {

    /** Channel names are capped at 20 characters. */
    public static final String CHANNEL = "qfcontent";

    public static SimpleNetworkWrapper wrapper;

    public static void register() {
        wrapper = NetworkRegistry.INSTANCE.newSimpleChannel(CHANNEL);

        // Server -> client only. Registered on both sides so the discriminator
        // numbering matches; the handler itself only ever runs on a client.
        wrapper.registerMessage(PacketJammer.Handler.class, PacketJammer.class, 0, Side.CLIENT);

        // Client -> server: which track a jukebox holds. The audio never travels,
        // only the choice, so the block remembers its own music.
        wrapper.registerMessage(PacketBindTrack.Handler.class, PacketBindTrack.class, 1, Side.SERVER);

        // Shared playlists. The client asks and publishes; the server answers, and
        // pushes a fresh index to everyone whenever what is shared changes.
        wrapper.registerMessage(PacketPublishPlaylist.Handler.class,
                                PacketPublishPlaylist.class, 2, Side.SERVER);
        wrapper.registerMessage(PacketRequestPublic.Handler.class,
                                PacketRequestPublic.class, 3, Side.SERVER);
        wrapper.registerMessage(PacketPublicIndex.Handler.class,
                                PacketPublicIndex.class, 4, Side.CLIENT);
        wrapper.registerMessage(PacketPublicTracks.Handler.class,
                                PacketPublicTracks.class, 5, Side.CLIENT);

        // Records. The client composes and edits; only the server may write the
        // item's NBT and have it stick.
        wrapper.registerMessage(PacketWriteRecord.Handler.class,
                                PacketWriteRecord.class, 6, Side.SERVER);
        wrapper.registerMessage(PacketEditRecord.Handler.class,
                                PacketEditRecord.class, 7, Side.SERVER);

        // Proximity voice. Up to 50 of each per second per speaker, which is far
        // more traffic than everything above put together -- see PacketVoice for
        // why these are handled on the netty thread rather than queued to the tick.
        wrapper.registerMessage(PacketVoice.Handler.class, PacketVoice.class, 8, Side.SERVER);
        wrapper.registerMessage(PacketVoiceFrame.Handler.class,
                                PacketVoiceFrame.class, VOICE_FRAME_ID, Side.CLIENT);

        // Opening a portable speaker's screen. The server answers the right-click,
        // because only it can stamp the speaker's id and have that stick.
        // The tower speakers: opening one, editing it, and the device lists that
        // say which of them a jukebox or JBL is playing through.
        wrapper.registerMessage(PacketOpenTowerSpeaker.Handler.class,
                PacketOpenTowerSpeaker.class, 11, Side.CLIENT);
        wrapper.registerMessage(PacketSpeakerEdit.Handler.class,
                PacketSpeakerEdit.class, 12, Side.SERVER);
        wrapper.registerMessage(PacketSpeakerState.Handler.class,
                PacketSpeakerState.class, 13, Side.CLIENT);
        wrapper.registerMessage(PacketDeviceAction.Handler.class,
                PacketDeviceAction.class, 14, Side.SERVER);
        wrapper.registerMessage(PacketDeviceList.Handler.class,
                PacketDeviceList.class, 15, Side.CLIENT);

        wrapper.registerMessage(PacketOpenSpeaker.Handler.class,
                                PacketOpenSpeaker.class, 10, Side.CLIENT);
        // "This drag-and-drop enchanting click is deliberate." Without it the
        // server cannot tell a person from InventoryTweaks' sort; see ClickIntent.
        wrapper.registerMessage(PacketClickIntent.Handler.class,
                                PacketClickIntent.class, 17, Side.SERVER);
    }

    public static void toServer(Object message) {
        if (wrapper == null) return;
        wrapper.sendToServer((cpw.mods.fml.common.network.simpleimpl.IMessage) message);
    }

    public static void toPlayer(Object message, EntityPlayerMP player) {
        if (wrapper == null || player == null) return;
        wrapper.sendTo((cpw.mods.fml.common.network.simpleimpl.IMessage) message, player);
    }

    /** PacketVoiceFrame's discriminator, shared with toPlayerAnyThread's encoding. */
    public static final int VOICE_FRAME_ID = 9;

    /**
     * toPlayer for a thread that is not the server thread -- voice, which is relayed
     * straight from the netty thread that received it.
     *
     * SimpleNetworkWrapper is not safe to call off the main thread: every send goes
     * through one shared FMLEmbeddedChannel, setting its target attributes and then
     * writing, so two threads sending at once can deliver a packet to the wrong
     * player or corrupt the pipeline. getPacketFrom is no way out, since it runs
     * the same shared channel. So this encodes the message by hand, exactly as
     * FMLIndexedMessageToMessageCodec would -- discriminator byte, then toBytes --
     * into a plain custom-payload packet, and hands it to the player's own
     * NetworkManager, which queues onto its netty event loop from any thread.
     */
    public static void toPlayerAnyThread(cpw.mods.fml.common.network.simpleimpl.IMessage message,
                                         int discriminator, EntityPlayerMP player) {
        if (message == null || player == null) return;
        // A FakePlayer has no connection to send on.
        net.minecraft.network.NetHandlerPlayServer conn = player.playerNetServerHandler;
        if (conn == null) return;

        io.netty.buffer.ByteBuf buf = io.netty.buffer.Unpooled.buffer();
        buf.writeByte(discriminator);
        message.toBytes(buf);
        byte[] payload = new byte[buf.readableBytes()];
        buf.readBytes(payload);

        conn.sendPacket(new net.minecraft.network.play.server.S3FPacketCustomPayload(
                CHANNEL, payload));
    }
}
