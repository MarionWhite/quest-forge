package com.questforge.content.net;

import com.questforge.content.jukebox.SpeakerRegistry;
import cpw.mods.fml.common.network.simpleimpl.IMessage;
import cpw.mods.fml.common.network.simpleimpl.IMessageHandler;
import cpw.mods.fml.common.network.simpleimpl.MessageContext;
import io.netty.buffer.ByteBuf;

/**
 * Opens a tower speaker's screen, carrying the speaker's own record.
 *
 * The trip through the server exists for the same reason the JBL's does: a freshly
 * placed speaker has no code until one is issued, only the server may issue one, and
 * a client opening its own screen first would have nothing to show.
 */
public class PacketOpenTowerSpeaker implements IMessage {

    public int x, y, z;
    public SpeakerRegistry.Entry entry = new SpeakerRegistry.Entry();

    /**
     * True when the screen was opened from a jukebox's device list rather than by
     * right-clicking the speaker. It changes nothing about what may be done -- the
     * server decides that -- only where closing the screen goes back to.
     */
    public boolean remote;

    public PacketOpenTowerSpeaker() { }

    public PacketOpenTowerSpeaker(int x, int y, int z, SpeakerRegistry.Entry entry) {
        this(x, y, z, entry, false);
    }

    public PacketOpenTowerSpeaker(int x, int y, int z, SpeakerRegistry.Entry entry,
                                  boolean remote) {
        this.x = x; this.y = y; this.z = z;
        this.entry = entry;
        this.remote = remote;
    }

    @Override
    public void fromBytes(ByteBuf buf) {
        x = buf.readInt(); y = buf.readInt(); z = buf.readInt();
        entry = SpeakerCodec.readEntry(buf);
        remote = buf.readBoolean();
    }

    @Override
    public void toBytes(ByteBuf buf) {
        buf.writeInt(x); buf.writeInt(y); buf.writeInt(z);
        SpeakerCodec.writeEntry(buf, entry);
        buf.writeBoolean(remote);
    }

    public static class Handler
            implements IMessageHandler<PacketOpenTowerSpeaker, IMessage> {

        @Override
        public IMessage onMessage(PacketOpenTowerSpeaker message, MessageContext ctx) {
            if (message.entry == null || message.entry.code.isEmpty()) return null;
            open(message);
            return null;
        }

        @cpw.mods.fml.relauncher.SideOnly(cpw.mods.fml.relauncher.Side.CLIENT)
        private void open(final PacketOpenTowerSpeaker message) {
            final net.minecraft.client.Minecraft mc =
                    net.minecraft.client.Minecraft.getMinecraft();
            // Onto the client thread: a packet arrives on a netty thread, and opening
            // a screen from there races the renderer.
            mc.func_152344_a(new Runnable() {
                @Override public void run() {
                    mc.displayGuiScreen(
                            new com.questforge.content.jukebox.GuiTowerSpeaker(
                                    message.x, message.y, message.z, message.entry));
                }
            });
        }
    }
}
