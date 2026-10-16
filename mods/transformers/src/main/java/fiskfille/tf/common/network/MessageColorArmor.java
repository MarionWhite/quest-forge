package fiskfille.tf.common.network;

import fiskfille.tf.TransformersMod;
import fiskfille.tf.common.network.base.TFNetworkManager;
import fiskfille.tf.common.item.ItemCSD.DimensionalCoords;
import fiskfille.tf.common.tileentity.TileEntityDisplayStation;
import io.netty.buffer.ByteBuf;
import net.minecraft.entity.player.EntityPlayer;
import net.minecraft.tileentity.TileEntity;
import net.minecraft.world.World;
import cpw.mods.fml.common.network.simpleimpl.IMessage;
import cpw.mods.fml.common.network.simpleimpl.IMessageHandler;
import cpw.mods.fml.common.network.simpleimpl.MessageContext;

public class MessageColorArmor implements IMessage
{
    private int x;
    private int y;
    private int z;
    private int primaryColor;
    private int secondaryColor;

    public MessageColorArmor()
    {

    }

    public MessageColorArmor(int x, int y, int z, int primaryColor, int secondaryColor)
    {
        this.x = x;
        this.y = y;
        this.z = z;
        this.primaryColor = primaryColor;
        this.secondaryColor = secondaryColor;
    }

    @Override
    public void fromBytes(ByteBuf buf)
    {
        x = buf.readInt();
        y = buf.readInt();
        z = buf.readInt();
        primaryColor = buf.readInt();
        secondaryColor = buf.readInt();
    }

    @Override
    public void toBytes(ByteBuf buf)
    {
        buf.writeInt(x);
        buf.writeInt(y);
        buf.writeInt(z);
        buf.writeInt(primaryColor);
        buf.writeInt(secondaryColor);
    }

    public static class Handler implements IMessageHandler<MessageColorArmor, IMessage>
    {
        @Override
        public IMessage onMessage(MessageColorArmor message, MessageContext ctx)
        {
            EntityPlayer player = ctx.side.isClient() ? TransformersMod.proxy.getPlayer() : ctx.getServerHandler().playerEntity;

            if (player == null || player.worldObj == null)
            {
                return null;
            }

            World world = player.worldObj;

            if (ctx.side.isServer())
            {
                world = MessageTileTrigger.Handler.getTargetWorld(player, new DimensionalCoords(message.x, message.y, message.z, world.provider.dimensionId));

                if (world == null)
                {
                    return null;
                }
            }

            TileEntity tile = world.getTileEntity(message.x, message.y, message.z);

            if (tile instanceof TileEntityDisplayStation)
            {
                if (((TileEntityDisplayStation) tile).setColor(message.primaryColor, message.secondaryColor))
                {
                    world.markBlockForUpdate(message.x, message.y, message.z);

                    if (ctx.side.isServer())
                    {
                        TFNetworkManager.networkWrapper.sendToDimension(new MessageColorArmor(message.x, message.y, message.z, message.primaryColor, message.secondaryColor), world.provider.dimensionId);
                    }
                }
            }

            return null;
        }
    }
}
