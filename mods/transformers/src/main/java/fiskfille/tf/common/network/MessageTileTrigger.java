package fiskfille.tf.common.network;

import io.netty.buffer.ByteBuf;
import net.minecraft.entity.player.EntityPlayer;
import net.minecraft.item.ItemStack;
import net.minecraft.tileentity.TileEntity;
import net.minecraft.world.World;
import net.minecraftforge.common.DimensionManager;
import cpw.mods.fml.common.network.simpleimpl.IMessage;
import cpw.mods.fml.common.network.simpleimpl.IMessageHandler;
import cpw.mods.fml.common.network.simpleimpl.MessageContext;
import fiskfille.tf.TransformersMod;
import fiskfille.tf.common.item.ItemCSD;
import fiskfille.tf.common.item.ItemCSD.DimensionalCoords;
import fiskfille.tf.common.item.TFItems;
import fiskfille.tf.common.network.base.TFNetworkManager;

public class MessageTileTrigger implements IMessage
{
    private DimensionalCoords coordinates;
    private int id;
    private int action;
    private int playerDimension;

    public MessageTileTrigger()
    {

    }

    public MessageTileTrigger(DimensionalCoords coords, EntityPlayer player, int action)
    {
        this.coordinates = coords;
        this.action = action;

        if (player != null)
        {
            id = player.getEntityId();
            playerDimension = player.worldObj.provider.dimensionId;
        }
    }

    @Override
    public void fromBytes(ByteBuf buf)
    {
        id = buf.readInt();
        action = buf.readInt();
        playerDimension = buf.readInt();
        coordinates = new DimensionalCoords().fromBytes(buf);
    }

    @Override
    public void toBytes(ByteBuf buf)
    {
        buf.writeInt(id);
        buf.writeInt(action);
        buf.writeInt(playerDimension);
        coordinates.toBytes(buf);
    }

    public static class Handler implements IMessageHandler<MessageTileTrigger, IMessage>
    {
        // Reach plus the size of the largest multi-block, so clicks on a far part of one still count
        private static final double MAX_DISTANCE_SQ = 10 * 10;

        @Override
        public IMessage onMessage(MessageTileTrigger message, MessageContext ctx)
        {
            DimensionalCoords coords = message.coordinates;

            if (ctx.side.isClient())
            {
                EntityPlayer clientPlayer = TransformersMod.proxy.getPlayer();

                if (clientPlayer == null || clientPlayer.worldObj == null)
                {
                    return null;
                }

                World world = clientPlayer.worldObj;

                if (world.provider.dimensionId != coords.dimension)
                {
                    return null;
                }

                EntityPlayer player = null;

                // The triggering player may be in another dimension (ground bridge remote); the tile still updates
                if (world.provider.dimensionId == message.playerDimension && world.getEntityByID(message.id) instanceof EntityPlayer)
                {
                    player = (EntityPlayer) world.getEntityByID(message.id);
                }

                TileEntity tile = world.getTileEntity(coords.posX, coords.posY, coords.posZ);

                if (tile instanceof ITileDataCallback)
                {
                    ((ITileDataCallback) tile).receive(player, message.action);
                }
            }
            else
            {
                // Only the sender can trigger, and only tiles it could actually be using:
                // the entity id and dimensions in the message are not trusted.
                EntityPlayer player = ctx.getServerHandler().playerEntity;

                if (player == null)
                {
                    return null;
                }

                World world = getTargetWorld(player, coords);

                if (world == null)
                {
                    return null;
                }

                TileEntity tile = world.getTileEntity(coords.posX, coords.posY, coords.posZ);

                if (tile instanceof ITileDataCallback)
                {
                    ((ITileDataCallback) tile).receive(player, message.action);
                    TFNetworkManager.networkWrapper.sendToDimension(new MessageTileTrigger(coords, player, message.action), coords.dimension);
                }
            }

            return null;
        }

        /**
         * The world in which the given player may act on the tile at coords, or null if
         * it may not. Shared with other client-to-tile packets.
         */
        static World getTargetWorld(EntityPlayer player, DimensionalCoords coords)
        {
            ItemStack heldItem = player.getHeldItem();

            if (heldItem != null && heldItem.getItem() == TFItems.groundBridgeRemote && coords.equals(ItemCSD.getCoords(heldItem)))
            {
                // The remote drives its linked panel from any distance or dimension, but only
                // if that dimension is already loaded: a packet must never hot-load one.
                return DimensionManager.getWorld(coords.dimension);
            }

            if (player.worldObj.provider.dimensionId != coords.dimension || player.getDistanceSq(coords.posX + 0.5, coords.posY + 0.5, coords.posZ + 0.5) > MAX_DISTANCE_SQ)
            {
                return null;
            }

            return player.worldObj;
        }
    }

    public static interface ITileDataCallback
    {
        /**
         * Called when a tile gets triggered
         * 
         * @param player The player who triggered it, or null if none exists
         * @param action The trigger type
         */
        void receive(EntityPlayer player, int action);
    }
}
