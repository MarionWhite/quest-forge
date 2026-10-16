package com.questforge.content.net;

import io.netty.buffer.ByteBuf;

import cpw.mods.fml.common.network.simpleimpl.IMessage;
import cpw.mods.fml.common.network.simpleimpl.IMessageHandler;
import cpw.mods.fml.common.network.simpleimpl.MessageContext;

import com.questforge.content.ench.ClickIntent;

/**
 * "The next click on this slot is me, deliberately." Sent client -> server just
 * before a drag-and-drop enchanting click. See {@link ClickIntent} for why the
 * server cannot work that out for itself.
 *
 * Handled on the netty thread on purpose: it only writes to a concurrent map, and
 * running immediately is what guarantees it lands before the click packet, which
 * the server processes on its next tick.
 */
public class PacketClickIntent implements IMessage {

    public int windowId;
    public int slotId;

    /** Required by the packet codec. */
    public PacketClickIntent() {}

    public PacketClickIntent(int windowId, int slotId) {
        this.windowId = windowId;
        this.slotId = slotId;
    }

    @Override
    public void fromBytes(ByteBuf buf) {
        windowId = buf.readInt();
        slotId = buf.readInt();
    }

    @Override
    public void toBytes(ByteBuf buf) {
        buf.writeInt(windowId);
        buf.writeInt(slotId);
    }

    public static class Handler implements IMessageHandler<PacketClickIntent, IMessage> {
        @Override
        public IMessage onMessage(PacketClickIntent message, MessageContext ctx) {
            ClickIntent.record(ctx.getServerHandler().playerEntity,
                    message.windowId, message.slotId);
            return null;
        }
    }
}
