package com.questforge.content.net;

import com.questforge.content.jukebox.SpeakerRegistry;
import cpw.mods.fml.common.network.simpleimpl.IMessage;
import cpw.mods.fml.common.network.simpleimpl.IMessageHandler;
import cpw.mods.fml.common.network.simpleimpl.MessageContext;
import io.netty.buffer.ByteBuf;

import java.util.ArrayList;
import java.util.List;

/**
 * Everything one owner is playing through, resolved.
 *
 * The client cannot work this out for itself: a paired speaker is usually outside
 * its loaded chunks, so the coordinates, range and volume needed to place an OpenAL
 * source have to arrive from the server that can still see them.
 */
public class PacketDeviceList implements IMessage {

    public String owner = "";
    public boolean ownerEnabled = true;
    public List<SpeakerRegistry.Entry> devices = new ArrayList<SpeakerRegistry.Entry>();
    /** Shown to the player when something they asked for could not be done. */
    public String problem = "";

    public PacketDeviceList() { }

    public PacketDeviceList(String owner, boolean ownerEnabled,
                            List<SpeakerRegistry.Entry> devices, String problem) {
        this.owner = owner;
        this.ownerEnabled = ownerEnabled;
        this.devices = devices;
        this.problem = problem == null ? "" : problem;
    }

    @Override
    public void fromBytes(ByteBuf buf) {
        owner = SpeakerCodec.readString(buf, 64);
        ownerEnabled = buf.readBoolean();
        problem = SpeakerCodec.readString(buf, 64);
        int n = buf.readUnsignedByte();
        if (n > SpeakerCodec.MAX_DEVICES) n = SpeakerCodec.MAX_DEVICES;
        devices = new ArrayList<SpeakerRegistry.Entry>(n);
        for (int i = 0; i < n; i++) devices.add(SpeakerCodec.readEntry(buf));
    }

    @Override
    public void toBytes(ByteBuf buf) {
        SpeakerCodec.writeString(buf, owner, 64);
        buf.writeBoolean(ownerEnabled);
        SpeakerCodec.writeString(buf, problem, 64);
        int n = Math.min(devices.size(), SpeakerCodec.MAX_DEVICES);
        buf.writeByte(n);
        for (int i = 0; i < n; i++) SpeakerCodec.writeEntry(buf, devices.get(i));
    }

    public static class Handler implements IMessageHandler<PacketDeviceList, IMessage> {
        @Override
        public IMessage onMessage(final PacketDeviceList m, MessageContext ctx) {
            accept(m);
            return null;
        }

        @cpw.mods.fml.relauncher.SideOnly(cpw.mods.fml.relauncher.Side.CLIENT)
        private void accept(final PacketDeviceList m) {
            final net.minecraft.client.Minecraft mc =
                    net.minecraft.client.Minecraft.getMinecraft();
            mc.func_152344_a(new Runnable() {
                @Override public void run() {
                    com.questforge.content.jukebox.Devices.accept(
                            m.owner, m.ownerEnabled, m.devices, m.problem);
                }
            });
        }
    }
}
