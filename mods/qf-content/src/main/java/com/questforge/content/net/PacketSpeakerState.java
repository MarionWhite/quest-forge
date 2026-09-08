package com.questforge.content.net;

import com.questforge.content.jukebox.SpeakerRegistry;
import cpw.mods.fml.common.network.simpleimpl.IMessage;
import cpw.mods.fml.common.network.simpleimpl.IMessageHandler;
import cpw.mods.fml.common.network.simpleimpl.MessageContext;
import io.netty.buffer.ByteBuf;

/** One speaker's record, after the server has changed it. */
public class PacketSpeakerState implements IMessage {

    public SpeakerRegistry.Entry entry = new SpeakerRegistry.Entry();

    public PacketSpeakerState() { }

    public PacketSpeakerState(SpeakerRegistry.Entry entry) { this.entry = entry; }

    @Override public void fromBytes(ByteBuf buf) { entry = SpeakerCodec.readEntry(buf); }
    @Override public void toBytes(ByteBuf buf) { SpeakerCodec.writeEntry(buf, entry); }

    public static class Handler implements IMessageHandler<PacketSpeakerState, IMessage> {
        @Override
        public IMessage onMessage(final PacketSpeakerState m, MessageContext ctx) {
            if (m.entry == null || m.entry.code.isEmpty()) return null;
            apply(m);
            return null;
        }

        @cpw.mods.fml.relauncher.SideOnly(cpw.mods.fml.relauncher.Side.CLIENT)
        private void apply(final PacketSpeakerState m) {
            final net.minecraft.client.Minecraft mc =
                    net.minecraft.client.Minecraft.getMinecraft();
            mc.func_152344_a(new Runnable() {
                @Override public void run() {
                    com.questforge.content.jukebox.Devices.update(m.entry);
                }
            });
        }
    }
}
