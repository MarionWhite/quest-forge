package fiskfille.tf.common.network;

import io.netty.buffer.ByteBuf;
import cpw.mods.fml.common.network.ByteBufUtils;
import cpw.mods.fml.common.network.simpleimpl.IMessage;
import cpw.mods.fml.common.network.simpleimpl.IMessageHandler;
import cpw.mods.fml.common.network.simpleimpl.MessageContext;
import fiskfille.tf.common.data.tile.TileData;
import fiskfille.tf.common.item.ItemCSD.DimensionalCoords;
import fiskfille.tf.helper.TFTileHelper;

public class MessageSetTileData implements IMessage
{
    private TileData tileData;
    private DimensionalCoords tileCoords;

    public MessageSetTileData()
    {

    }

    public MessageSetTileData(DimensionalCoords coords, TileData data)
    {
        tileData = data;
        tileCoords = coords;
    }

    public MessageSetTileData(TileData data)
    {
        this(data.getCoords(), data);
    }

    @Override
    public void fromBytes(ByteBuf buf)
    {
        if (buf.readBoolean())
        {
            try
            {
                // Load without initializing and check the type first, so a crafted name
                // can't make the receiver initialize or construct an arbitrary class
                Class<?> clazz = Class.forName(ByteBufUtils.readUTF8String(buf), false, MessageSetTileData.class.getClassLoader());

                if (TileData.class.isAssignableFrom(clazz))
                {
                    tileData = (TileData) clazz.newInstance();
                    tileData.fromBytes(buf);
                }
            }
            catch (Exception e)
            {
                e.printStackTrace();
            }
        }
        else
        {
            tileCoords = new DimensionalCoords().fromBytes(buf);
        }
    }

    @Override
    public void toBytes(ByteBuf buf)
    {
        buf.writeBoolean(tileData != null);

        if (tileData == null)
        {
            tileCoords.toBytes(buf);
        }
        else
        {
            ByteBufUtils.writeUTF8String(buf, tileData.getClass().getCanonicalName());
            tileData.toBytes(buf);
        }
    }

    public static class Handler implements IMessageHandler<MessageSetTileData, IMessage>
    {
        @Override
        public IMessage onMessage(MessageSetTileData message, MessageContext ctx)
        {
            // Tile data only flows server -> client; clients must not be able to inject it
            if (ctx.side.isServer())
            {
                return null;
            }

            TileData data = message.tileData;
            DimensionalCoords coords = data != null ? data.getCoords() : message.tileCoords;

            if (coords != null)
            {
                TFTileHelper.putServerData(coords, data);
            }

            return null;
        }
    }
}
