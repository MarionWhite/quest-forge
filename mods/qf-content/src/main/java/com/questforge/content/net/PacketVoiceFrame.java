package com.questforge.content.net;

import io.netty.buffer.ByteBuf;

import cpw.mods.fml.common.network.simpleimpl.IMessage;
import cpw.mods.fml.common.network.simpleimpl.IMessageHandler;
import cpw.mods.fml.common.network.simpleimpl.MessageContext;
import cpw.mods.fml.relauncher.Side;
import cpw.mods.fml.relauncher.SideOnly;

import com.questforge.content.voice.VoiceCodec;

/**
 * One frame of somebody else's voice, arriving at a listener.
 *
 * The speaker's entity id and position are both sent. That looks redundant -- the
 * client could look the entity up -- but each covers a case the other does not: the
 * id lets playback follow a player smoothly between frames at render rate, while the
 * position still places the voice correctly for the moment when a speaker is at the
 * edge of the relay range and their entity has not been tracked to this client yet.
 */
public class PacketVoiceFrame implements IMessage {

    public int speakerId;
    public float x, y, z;
    public byte[] frame;

    /** Required by the packet codec. */
    public PacketVoiceFrame() {}

    public PacketVoiceFrame(int speakerId, double x, double y, double z, byte[] frame) {
        this.speakerId = speakerId;
        this.x = (float) x;
        this.y = (float) y;
        this.z = (float) z;
        this.frame = frame;
    }

    @Override
    public void fromBytes(ByteBuf buf) {
        speakerId = buf.readInt();
        x = buf.readFloat();
        y = buf.readFloat();
        z = buf.readFloat();
        int len = buf.readUnsignedShort();
        if (len != VoiceCodec.FRAME_BYTES || buf.readableBytes() < len) {
            frame = null;
            return;
        }
        frame = new byte[len];
        buf.readBytes(frame);
    }

    @Override
    public void toBytes(ByteBuf buf) {
        buf.writeInt(speakerId);
        buf.writeFloat(x);
        buf.writeFloat(y);
        buf.writeFloat(z);
        buf.writeShort(frame.length);
        buf.writeBytes(frame);
    }

    public static class Handler implements IMessageHandler<PacketVoiceFrame, IMessage> {

        @Override
        @SideOnly(Side.CLIENT)
        public IMessage onMessage(PacketVoiceFrame message, MessageContext ctx) {
            if (ctx.side != Side.CLIENT) return null;
            if (message.frame == null) return null;

            // Only queued here. Decoding is cheap but OpenAL is not thread-safe to
            // touch from netty, so the client tick picks these up and does the work
            // on the thread that owns the audio context.
            com.questforge.content.voice.VoicePlayback.enqueue(message);
            return null;
        }
    }
}
