package com.questforge.content.net;

import io.netty.buffer.ByteBuf;

import cpw.mods.fml.common.network.simpleimpl.IMessage;
import cpw.mods.fml.common.network.simpleimpl.IMessageHandler;
import cpw.mods.fml.common.network.simpleimpl.MessageContext;
import cpw.mods.fml.relauncher.Side;
import cpw.mods.fml.relauncher.SideOnly;

/**
 * "Your screen is now worse." Sent to the victim of a Jammer hit.
 *
 * The attacker's server-side proc decides the strength and duration; the victim's
 * client only obeys. Nothing here is trusted input in a security sense -- a
 * malicious server could already do far worse -- but both fields are clamped on
 * arrival anyway so a corrupt packet cannot divide by zero or hang the renderer.
 */
public class PacketJammer implements IMessage {

    /** Downsample factor: 2 = half resolution, 16 = extremely blocky. */
    public int factor;

    /** How many ticks it lasts. */
    public int ticks;

    /** Required by the packet codec. */
    public PacketJammer() {}

    public PacketJammer(int factor, int ticks) {
        this.factor = factor;
        this.ticks = ticks;
    }

    @Override
    public void fromBytes(ByteBuf buf) {
        factor = buf.readInt();
        ticks = buf.readInt();
    }

    @Override
    public void toBytes(ByteBuf buf) {
        buf.writeInt(factor);
        buf.writeInt(ticks);
    }

    public static class Handler implements IMessageHandler<PacketJammer, IMessage> {

        @Override
        @SideOnly(Side.CLIENT)
        public IMessage onMessage(PacketJammer message, MessageContext ctx) {
            if (ctx.side != Side.CLIENT) return null;

            int factor = Math.max(2, Math.min(24, message.factor));
            int ticks = Math.max(0, Math.min(1200, message.ticks));

            // Runs on the netty thread. The renderer only ever reads these two
            // volatile ints, so there is nothing to schedule onto the client
            // thread -- a value landing a frame early is invisible.
            com.questforge.content.client.JammerFX.apply(factor, ticks);
            return null;
        }
    }
}
