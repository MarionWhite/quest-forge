package com.questforge.content.net;

import io.netty.buffer.ByteBuf;

import cpw.mods.fml.common.network.simpleimpl.IMessage;
import cpw.mods.fml.common.network.simpleimpl.IMessageHandler;
import cpw.mods.fml.common.network.simpleimpl.MessageContext;

import net.minecraft.entity.player.EntityPlayerMP;

import com.questforge.content.voice.VoiceCodec;
import com.questforge.content.voice.VoiceServer;

/**
 * One 20 ms frame of a player's voice, on its way up to the server.
 *
 * Carries no position: where the speaker is, is the server's business, and a client
 * that could name its own coordinates could put its voice anywhere.
 */
public class PacketVoice implements IMessage {

    public byte[] frame;

    /** Required by the packet codec. */
    public PacketVoice() {}

    public PacketVoice(byte[] frame) {
        this.frame = frame;
    }

    @Override
    public void fromBytes(ByteBuf buf) {
        int len = buf.readUnsignedShort();
        // A frame is a fixed size, so anything else is a corrupt or hostile packet
        // and there is nothing to salvage by reading it.
        if (len != VoiceCodec.FRAME_BYTES || buf.readableBytes() < len) {
            frame = null;
            return;
        }
        frame = new byte[len];
        buf.readBytes(frame);
    }

    @Override
    public void toBytes(ByteBuf buf) {
        buf.writeShort(frame.length);
        buf.writeBytes(frame);
    }

    public static class Handler implements IMessageHandler<PacketVoice, IMessage> {

        /**
         * Relays on the netty thread rather than queueing onto the server tick.
         *
         * This deliberately breaks the convention {@link ServerTasks} sets, and the
         * reason is arithmetic: that queue drains 64 tasks per tick, so 1280 a
         * second, while voice alone is 50 frames a second per speaker. Three people
         * talking would spend a quarter of the entire budget, and any real burst
         * would start dropping other mods' work as well as the audio.
         *
         * It is safe here in a way it would not be for world changes: this reads
         * player positions, which are plain fields, and writes nothing at all.
         * A position read a tick stale simply places a voice where its speaker was
         * 50 ms ago, which is well inside what the client's own smoothing absorbs.
         */
        @Override
        public IMessage onMessage(PacketVoice message, MessageContext ctx) {
            if (ctx.side != cpw.mods.fml.relauncher.Side.SERVER) return null;
            if (message.frame == null) return null;

            EntityPlayerMP speaker = ctx.getServerHandler().playerEntity;
            if (speaker == null) return null;

            VoiceServer.relay(speaker, message.frame);
            return null;
        }
    }
}
