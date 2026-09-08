package com.questforge.content.net;

import cpw.mods.fml.common.network.simpleimpl.IMessage;
import cpw.mods.fml.common.network.simpleimpl.IMessageHandler;
import cpw.mods.fml.common.network.simpleimpl.MessageContext;
import io.netty.buffer.ByteBuf;

/**
 * Opens a JBL's screen on the client that right-clicked it.
 *
 * The trip to the server exists to settle the speaker's identity. A newly made
 * speaker has no id until one is stamped into its NBT, only the server may do that
 * and have it stick, and the client would otherwise have to wait for the stack to
 * sync back before it knew which queue to load -- so the first click on a new
 * speaker would open the wrong one, or nothing at all. Sending the id along with the
 * instruction to open removes the guess entirely.
 */
public class PacketOpenSpeaker implements IMessage {

    /** A UUID in its usual dashed form. */
    private static final int MAX_ID = 48;

    public String id = "";

    /** Required by the packet codec. */
    public PacketOpenSpeaker() { }

    public PacketOpenSpeaker(String id) {
        this.id = id == null ? "" : id;
    }

    @Override
    public void fromBytes(ByteBuf buf) {
        int length = buf.readUnsignedByte();
        if (length > MAX_ID) length = MAX_ID;
        byte[] raw = new byte[length];
        buf.readBytes(raw);
        try {
            id = new String(raw, "UTF-8");
        } catch (Exception e) {
            id = "";
        }
    }

    @Override
    public void toBytes(ByteBuf buf) {
        byte[] raw;
        try {
            raw = id.getBytes("UTF-8");
        } catch (Exception e) {
            raw = new byte[0];
        }
        int length = Math.min(raw.length, MAX_ID);
        buf.writeByte(length);
        buf.writeBytes(raw, 0, length);
    }

    public static class Handler
            implements IMessageHandler<PacketOpenSpeaker, IMessage> {

        @Override
        public IMessage onMessage(PacketOpenSpeaker message, MessageContext ctx) {
            if (message.id == null || message.id.isEmpty()) return null;
            open(message.id);
            return null;
        }

        @cpw.mods.fml.relauncher.SideOnly(cpw.mods.fml.relauncher.Side.CLIENT)
        private void open(final String id) {
            final net.minecraft.client.Minecraft mc =
                    net.minecraft.client.Minecraft.getMinecraft();
            // Onto the client thread: a packet arrives on a netty thread, and
            // opening a screen from there races the renderer.
            mc.func_152344_a(new Runnable() {
                @Override public void run() {
                    com.questforge.content.jukebox.Speakers.open(id);
                    mc.displayGuiScreen(
                            new com.questforge.content.jukebox.GuiJukebox(id));
                }
            });
        }
    }
}
