package fiskfille.tf.common.network;

import io.netty.buffer.ByteBuf;

import java.util.Collections;
import java.util.Comparator;
import java.util.List;
import java.util.Map;

import net.minecraft.entity.player.EntityPlayer;
import net.minecraft.world.WorldProvider;
import net.minecraft.world.WorldServer;
import net.minecraftforge.common.DimensionManager;

import com.google.common.collect.Lists;
import com.google.common.collect.Maps;

import cpw.mods.fml.common.network.ByteBufUtils;
import cpw.mods.fml.common.network.simpleimpl.IMessage;
import cpw.mods.fml.common.network.simpleimpl.IMessageHandler;
import cpw.mods.fml.common.network.simpleimpl.MessageContext;
import fiskfille.tf.TransformersAPI;
import fiskfille.tf.TransformersMod;
import fiskfille.tf.common.data.TFData;
import fiskfille.tf.common.transformer.base.Transformer;
import fiskfille.tf.config.TFConfig;
import fiskfille.tf.helper.TFDimensionHelper;

public class MessagePlayerJoin extends MessageSyncBase
{
    private Map<Transformer, Boolean> canTransform;
    private Map<Integer, String> dimensionNames = Maps.newHashMap();
    private Integer[] dimensionIDs;

    public MessagePlayerJoin()
    {
    }

    public MessagePlayerJoin(EntityPlayer player)
    {
        super(player);
        canTransform = TFConfig.canTransform;

        if (canTransform.isEmpty() || !canTransform.keySet().containsAll(TransformersAPI.getTransformers()))
        {
            for (Transformer transformer : TransformersAPI.getTransformers())
            {
                if (!canTransform.containsKey(transformer))
                {
                    canTransform.put(transformer, true);
                }
            }
        }

        Integer[] ids = DimensionManager.getIDs();
        dimensionNames = TFDimensionHelper.dimensionNames;

        for (int i = 0; i < ids.length; ++i)
        {
            int id = ids[i];
            // Only the name is wanted. worldServerForDimension loads any
            // dimension that isn't, so this used to load every dimension in the
            // pack on every login; a bare provider names it without a world.
            WorldServer world = DimensionManager.getWorld(id);

            try
            {
                WorldProvider provider = world != null ? world.provider : DimensionManager.createProviderFor(id);

                if (provider != null)
                {
                    dimensionNames.put(id, provider.getDimensionName());
                }
            }
            catch (Exception e)
            {
                // A provider that needs its world to name itself; skip it.
            }
        }

        List<Integer> list = Lists.newArrayList();

        for (int i = 0; i < ids.length; ++i)
        {
            int id = ids[i];

            if (DimensionManager.shouldLoadSpawn(id))
            {
                list.add(id);
            }
        }

        Collections.sort(list, new Comparator<Integer>()
        {
            @Override
            public int compare(Integer arg0, Integer arg1)
            {
                return Double.valueOf(arg0).compareTo(Double.valueOf(arg1));
            }
        });

        TFDimensionHelper.dimensionIDs = dimensionIDs = list.toArray(new Integer[list.size()]);
    }

    @Override
    public void fromBytes(ByteBuf buf)
    {
        super.fromBytes(buf);
        canTransform = Maps.newHashMap();

        for (Transformer transformer : TransformersAPI.getTransformers())
        {
            canTransform.put(transformer, buf.readBoolean());
        }

        int length = buf.readInt();

        for (int i = 0; i < length; ++i)
        {
            dimensionNames.put(buf.readInt(), ByteBufUtils.readUTF8String(buf));
        }

        dimensionIDs = new Integer[buf.readInt()];

        for (int i = 0; i < dimensionIDs.length; ++i)
        {
            dimensionIDs[i] = buf.readInt();
        }
    }

    @Override
    public void toBytes(ByteBuf buf)
    {
        super.toBytes(buf);

        // fromBytes reads these in TransformersAPI.getTransformers() order, so write them in
        // that order too; iterating the HashMap scrambled which flag belonged to which transformer
        for (Transformer transformer : TransformersAPI.getTransformers())
        {
            Boolean flag = canTransform.get(transformer);
            buf.writeBoolean(flag == null || flag);
        }

        buf.writeInt(dimensionNames.size());

        for (Map.Entry<Integer, String> e : dimensionNames.entrySet())
        {
            buf.writeInt(e.getKey());
            ByteBufUtils.writeUTF8String(buf, e.getValue());
        }

        buf.writeInt(dimensionIDs.length);

        for (int i = 0; i < dimensionIDs.length; ++i)
        {
            buf.writeInt(dimensionIDs[i]);
        }
    }

    public static class Handler implements IMessageHandler<MessagePlayerJoin, IMessage>
    {
        @Override
        public IMessage onMessage(MessagePlayerJoin message, MessageContext ctx)
        {
            if (ctx.side.isClient())
            {
                EntityPlayer player = TransformersMod.proxy.getPlayer();

                for (Map.Entry<TFData, Object> e : message.playerData.entrySet())
                {
                    e.getKey().setWithoutNotify(player, e.getValue());
                }

                if (message.canTransform != null)
                {
                    TFConfig.canTransform = message.canTransform;
                }

                TFDimensionHelper.dimensionNames = message.dimensionNames;
                TFDimensionHelper.dimensionIDs = message.dimensionIDs;
            }

            return null;
        }
    }
}
