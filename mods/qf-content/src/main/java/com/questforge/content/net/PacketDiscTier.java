package com.questforge.content.net;

import io.netty.buffer.ByteBuf;
import cpw.mods.fml.common.network.simpleimpl.IMessage;
import cpw.mods.fml.common.network.simpleimpl.IMessageHandler;
import cpw.mods.fml.common.network.simpleimpl.MessageContext;
import net.minecraft.entity.player.EntityPlayerMP;
import net.minecraft.tileentity.TileEntity;
import net.minecraft.world.World;

import com.questforge.content.jukebox.TileEntityJukebox;

/**
 * "The disc showing behind this jukebox's glass is this tier."
 *
 * Sent client to server when a record is pressed or played at the block. The
 * jukebox's own right-click handling is client-side -- audio is -- so without
 * this the tier would live on one player's copy of the tile entity, look right
 * to them, and be invisible to everyone else and to the next session.
 *
 * Nothing here is trusted: the tier is clamped, and a player who is not close
 * enough to have clicked the block is ignored, the same as PacketBindTrack.
 */
public class PacketDiscTier implements IMessage {

    /** How far a player may be from a jukebox and still be changing its disc. */
    private static final double REACH_SQ = 8.0D * 8.0D;

    public int x, y, z, tier;

    /** Required by the packet codec. */
    public PacketDiscTier() { }

    public PacketDiscTier(int x, int y, int z, int tier) {
        this.x = x;
        this.y = y;
        this.z = z;
        this.tier = tier;
    }

    @Override
    public void fromBytes(ByteBuf buf) {
        x = buf.readInt();
        y = buf.readInt();
        z = buf.readInt();
        tier = buf.readByte();
    }

    @Override
    public void toBytes(ByteBuf buf) {
        buf.writeInt(x);
        buf.writeInt(y);
        buf.writeInt(z);
        buf.writeByte(tier);
    }

    public static class Handler implements IMessageHandler<PacketDiscTier, IMessage> {
        @Override
        public IMessage onMessage(final PacketDiscTier msg, MessageContext ctx) {
            final EntityPlayerMP player = ctx.getServerHandler().playerEntity;
            ServerTasks.submit(new Runnable() {
                @Override
                public void run() {
                    World world = player.worldObj;
                    if (!world.blockExists(msg.x, msg.y, msg.z)) return;
                    if (player.getDistanceSq(msg.x + 0.5D, msg.y + 0.5D,
                                             msg.z + 0.5D) > REACH_SQ) {
                        return;
                    }
                    TileEntity te = world.getTileEntity(msg.x, msg.y, msg.z);
                    if (te instanceof TileEntityJukebox) {
                        ((TileEntityJukebox) te).setDisc(msg.tier);
                    }
                }
            });
            return null;
        }
    }
}
