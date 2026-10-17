package com.questforge.content.net;

import java.util.LinkedHashMap;
import java.util.Map;

import io.netty.buffer.ByteBuf;

import cpw.mods.fml.common.network.ByteBufUtils;
import cpw.mods.fml.common.network.simpleimpl.IMessage;
import cpw.mods.fml.common.network.simpleimpl.IMessageHandler;
import cpw.mods.fml.common.network.simpleimpl.MessageContext;

import com.questforge.content.pack.PackCheck;

/**
 * Client -> server: the answer to {@link PacketPackQuery}. The client's pack
 * fingerprint and date, each fingerprinted config's digest (so a refusal can name
 * the files), and its mod list with versions. About 6 KB for the full pack, well
 * inside a custom payload's 32 KB.
 */
public class PacketPackReport implements IMessage {

    public String fingerprint = "";
    public String packDate = "";
    public Map<String, String> files = new LinkedHashMap<String, String>();
    public Map<String, String> mods = new LinkedHashMap<String, String>();

    /** Required by the packet codec. */
    public PacketPackReport() {}

    @Override
    public void fromBytes(ByteBuf buf) {
        fingerprint = ByteBufUtils.readUTF8String(buf);
        packDate = ByteBufUtils.readUTF8String(buf);
        files = readMap(buf);
        mods = readMap(buf);
    }

    @Override
    public void toBytes(ByteBuf buf) {
        ByteBufUtils.writeUTF8String(buf, fingerprint);
        ByteBufUtils.writeUTF8String(buf, packDate == null ? "" : packDate);
        writeMap(buf, files);
        writeMap(buf, mods);
    }

    private static Map<String, String> readMap(ByteBuf buf) {
        int n = ByteBufUtils.readVarInt(buf, 3);
        // A hostile count must not allocate a giant map before the reads fail.
        Map<String, String> m = new LinkedHashMap<String, String>(Math.min(n, 512));
        for (int i = 0; i < n; i++) {
            m.put(ByteBufUtils.readUTF8String(buf), ByteBufUtils.readUTF8String(buf));
        }
        return m;
    }

    private static void writeMap(ByteBuf buf, Map<String, String> m) {
        ByteBufUtils.writeVarInt(buf, m.size(), 3);
        for (Map.Entry<String, String> e : m.entrySet()) {
            ByteBufUtils.writeUTF8String(buf, e.getKey());
            ByteBufUtils.writeUTF8String(buf, String.valueOf(e.getValue()));
        }
    }

    public static class Handler implements IMessageHandler<PacketPackReport, IMessage> {
        @Override
        public IMessage onMessage(PacketPackReport message, MessageContext ctx) {
            PackCheck.onReport(ctx.getServerHandler().playerEntity, message);
            return null;
        }
    }
}
