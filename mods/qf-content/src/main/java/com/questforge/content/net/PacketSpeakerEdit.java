package com.questforge.content.net;

import com.questforge.content.jukebox.SpeakerRegistry;
import com.questforge.content.jukebox.TileEntityTowerSpeaker;
import cpw.mods.fml.common.network.simpleimpl.IMessage;
import cpw.mods.fml.common.network.simpleimpl.IMessageHandler;
import cpw.mods.fml.common.network.simpleimpl.MessageContext;
import io.netty.buffer.ByteBuf;
import net.minecraft.entity.player.EntityPlayerMP;
import net.minecraft.tileentity.TileEntity;
import net.minecraft.world.World;

/**
 * A change made at the speaker itself: its name, how far it carries, how loud, how
 * it is voiced, or that it should stop answering to anything.
 *
 * One packet rather than five because the checks are the same for all of them, and a
 * check written once is a check that cannot be forgotten on the fifth copy.
 */
public class PacketSpeakerEdit implements IMessage {

    public static final int RENAME = 0, RANGE = 1, VOLUME = 2, TONE = 3, UNPAIR = 4;

    /** A speaker cannot be edited from further than this. */
    private static final double REACH = 24.0;

    public String code = "";
    public int action;
    public String name = "";
    public int range;
    public float volume, bass, treble;

    public PacketSpeakerEdit() { }

    public PacketSpeakerEdit(String code, int action) {
        this.code = code; this.action = action;
    }

    @Override
    public void fromBytes(ByteBuf buf) {
        code = SpeakerRegistry.normalise(SpeakerCodec.readString(buf, SpeakerCodec.MAX_CODE));
        action = buf.readByte();
        name = SpeakerCodec.readString(buf, SpeakerCodec.MAX_NAME);
        range = buf.readByte();
        volume = buf.readFloat();
        bass = buf.readFloat();
        treble = buf.readFloat();
    }

    @Override
    public void toBytes(ByteBuf buf) {
        SpeakerCodec.writeString(buf, code, SpeakerCodec.MAX_CODE);
        buf.writeByte(action);
        SpeakerCodec.writeString(buf, name, SpeakerCodec.MAX_NAME);
        buf.writeByte(range);
        buf.writeFloat(volume);
        buf.writeFloat(bass);
        buf.writeFloat(treble);
    }

    public static class Handler implements IMessageHandler<PacketSpeakerEdit, IMessage> {

        @Override
        public IMessage onMessage(PacketSpeakerEdit m, MessageContext ctx) {
            EntityPlayerMP player = ctx.getServerHandler().playerEntity;
            if (player == null) return null;
            World world = player.worldObj;

            SpeakerRegistry reg = SpeakerRegistry.get(world);
            if (reg == null) return null;
            SpeakerRegistry.Entry e = reg.find(m.code);
            if (e == null) return null;

            // A speaker may be edited two ways, and without one of them a client
            // could rename or silence any speaker on the server whose code it had
            // seen. Either you are standing at the speaker, or you are working the
            // owner it is already paired to -- which means standing at that jukebox
            // or holding that JBL, and means the speaker has already agreed to
            // answer to you. The owner is read from the speaker's own record here,
            // never from the packet, so the client cannot nominate who to check it
            // against; see OwnerAccess.
            if (!atTheSpeaker(e, player) && !OwnerAccess.controls(player, e.pairedTo)) {
                return null;
            }

            switch (m.action) {
                case RENAME:
                    e.name = SpeakerCodec.cleanName(m.name);
                    nameTheBlock(world, e);
                    break;
                case RANGE:  e.range = SpeakerCodec.clampRange(m.range); break;
                case VOLUME: e.volume = SpeakerCodec.clampVolume(m.volume); break;
                case TONE:
                    e.bass = SpeakerCodec.clampTone(m.bass);
                    e.treble = SpeakerCodec.clampTone(m.treble);
                    break;
                case UNPAIR: e.pairedTo = ""; break;
                default: return null;
            }
            reg.put(e);

            QFNetwork.toPlayer(new PacketSpeakerState(e), player);
            return null;
        }

        /** Standing close enough to the speaker to be working it by hand. */
        private boolean atTheSpeaker(SpeakerRegistry.Entry e, EntityPlayerMP player) {
            if (e.dim != player.dimension) return false;
            double dx = e.x + 0.5 - player.posX;
            double dy = e.y + 0.5 - player.posY;
            double dz = e.z + 0.5 - player.posZ;
            return dx * dx + dy * dy + dz * dz <= REACH * REACH;
        }

        /** Keeps the block's own copy of the name in step, for the renderer. */
        private void nameTheBlock(World world, SpeakerRegistry.Entry e) {
            if (!world.blockExists(e.x, e.y, e.z)) return;
            TileEntity te = world.getTileEntity(e.x, e.y, e.z);
            if (te instanceof TileEntityTowerSpeaker) {
                ((TileEntityTowerSpeaker) te).setName(e.name);
            }
        }
    }
}
