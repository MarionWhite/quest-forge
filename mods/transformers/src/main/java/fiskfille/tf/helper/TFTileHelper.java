package fiskfille.tf.helper;

import java.util.Map;

import net.minecraft.tileentity.TileEntity;

import com.google.common.collect.Maps;

import fiskfille.tf.common.data.tile.TileData;
import fiskfille.tf.common.item.ItemCSD.DimensionalCoords;
import fiskfille.tf.common.tileentity.IMultiTile;

public class TFTileHelper
{
    private static Map<DimensionalCoords, TileData> tileData = Maps.newHashMap();

    public static TileData getTileData(DimensionalCoords coords)
    {
        return tileData.get(coords);
    }

    public static Map<DimensionalCoords, TileData> getTileData()
    {
        return tileData;
    }

    public static void clearTileData()
    {
        for (Map.Entry<DimensionalCoords, TileData> e : tileData.entrySet())
        {
            e.getValue().kill();
        }
    }

    public static void putServerData(TileData data)
    {
        putServerData(data.getCoords(), data);
    }

    public static void putServerData(DimensionalCoords coords, TileData data)
    {
        if (data == null)
        {
            tileData.remove(coords);
            return;
        }

        tileData.put(coords, data);
    }

    public static int[] getTileBaseOffsets(TileEntity tile, int metadata)
    {
        if (tile instanceof IMultiTile)
        {
            return ((IMultiTile) tile).getBaseOffsets(metadata);
        }

        return new int[] {0, 0, 0};
    }

    /**
     * Returns the base tile of a multi-block, or null if there is none. The tile
     * found at the base offset is only returned if it is of the same class as
     * the given tile: a broken or replaced multi-block can leave some other tile
     * there, and the old unchecked (T) cast surfaced that as a
     * ClassCastException in whichever caller first touched it.
     */
    public static <T extends TileEntity> T getTileBase(T tile)
    {
        if (tile == null)
        {
            return null;
        }

        int[] offsets = getTileBaseOffsets(tile, tile.getBlockMetadata());

        if (offsets[0] != 0 || offsets[1] != 0 || offsets[2] != 0)
        {
            if (tile.getWorldObj() == null)
            {
                return null;
            }

            TileEntity base = tile.getWorldObj().getTileEntity(tile.xCoord + offsets[0], tile.yCoord + offsets[1], tile.zCoord + offsets[2]);
            return tile.getClass().isInstance(base) ? (T) base : null;
        }

        return tile;
    }
}
