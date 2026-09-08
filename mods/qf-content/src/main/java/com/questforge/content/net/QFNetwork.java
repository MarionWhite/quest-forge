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
                                PacketVoiceFrame.class, 9, Side.CLIENT);

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
    }

    public static void toServer(Object message) {
        if (wrapper == null) return;
        wrapper.sendToServer((cpw.mods.fml.common.network.simpleimpl.IMessage) message);
    }

    public static void toPlayer(Object message, EntityPlayerMP player) {
        if (wrapper == null || player == null) return;
        wrapper.sendTo((cpw.mods.fml.common.network.simpleimpl.IMessage) message, player);
    }
}
