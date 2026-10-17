package com.questforge.content.net;

import io.netty.buffer.ByteBuf;

import cpw.mods.fml.common.network.ByteBufUtils;
import cpw.mods.fml.common.network.simpleimpl.IMessage;
import cpw.mods.fml.common.network.simpleimpl.IMessageHandler;
import cpw.mods.fml.common.network.simpleimpl.MessageContext;

import com.questforge.content.QuestForgeContent;
import com.questforge.content.pack.PackCheck;

/**
 * Server -> client, right after login: "what pack are you running?" Carries the
 * server's own fingerprint and date only for the client's log; the server makes
 * the decision when the answer, {@link PacketPackReport}, comes back.
 *
 * Answered on the netty thread by returning the report: it reads nothing but
 * values computed at load time.
 */
public class PacketPackQuery implements IMessage {

    public String fingerprint = "";
    public String packDate = "";

    /** Required by the packet codec. */
    public PacketPackQuery() {}

    public PacketPackQuery(String fingerprint, String packDate) {
        this.fingerprint = fingerprint;
        this.packDate = packDate;
    }

    @Override
    public void fromBytes(ByteBuf buf) {
        fingerprint = ByteBufUtils.readUTF8String(buf);
        packDate = ByteBufUtils.readUTF8String(buf);
    }

    @Override
    public void toBytes(ByteBuf buf) {
        ByteBufUtils.writeUTF8String(buf, fingerprint);
        ByteBufUtils.writeUTF8String(buf, packDate);
    }

    public static class Handler implements IMessageHandler<PacketPackQuery, IMessage> {
        @Override
        public IMessage onMessage(PacketPackQuery message, MessageContext ctx) {
            QuestForgeContent.log.info("[packcheck] server pack " + message.packDate + " ("
                    + message.fingerprint + "), ours " + PackCheck.packDate() + " ("
                    + PackCheck.fingerprint() + ")");
            return PackCheck.buildReport();
        }
    }
}
