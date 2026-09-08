package com.questforge.content.ench;

import java.util.Random;

import net.minecraft.block.Block;
import net.minecraft.block.material.Material;
import net.minecraft.item.Item;
import net.minecraft.util.AxisAlignedBB;
import net.minecraft.world.IBlockAccess;
import net.minecraft.world.World;

/**
 * The invisible light source Torchlight leaves under the player's feet.
 *
 * 1.7.10 has no concept of a light-emitting item, so "the pickaxe glows" has to be
 * "an air block that glows follows you around". This block is air in every respect
 * that matters -- no model, no collision, replaceable by anything, drops nothing --
 * except that it emits light.
 *
 * It cleans up after itself twice over: TorchlightUpkeep removes the previous one
 * on every move, and a random tick removes any that outlived their owner, so a
 * crash or a chunk unload at the wrong moment cannot leave a permanent trail.
 */
public class BlockEnchantLight extends Block {

    /** Brightness of the dimmest level; each further level adds three. */
    private static final int BASE_LIGHT = 9;

    public BlockEnchantLight() {
        super(Material.air);
        setBlockName("qf_enchant_light");
        setLightLevel(1.0F);        // the real value comes from getLightValue below
        setTickRandomly(true);
        setBlockUnbreakable();
        disableStats();
    }

    @Override
    public int getLightValue(IBlockAccess world, int x, int y, int z) {
        return Math.min(15, BASE_LIGHT + world.getBlockMetadata(x, y, z) * 3);
    }

    @Override
    public int getRenderType() {
        return -1;                  // nothing is drawn at all
    }

    @Override
    public boolean isOpaqueCube() {
        return false;
    }

    @Override
    public boolean renderAsNormalBlock() {
        return false;
    }

    @Override
    public boolean isReplaceable(IBlockAccess world, int x, int y, int z) {
        return true;                // building through it must just work
    }

    @Override
    public boolean canCollideCheck(int meta, boolean hitIfLiquid) {
        return false;               // never gets in the way of a ray trace
    }

    @Override
    public AxisAlignedBB getCollisionBoundingBoxFromPool(World world, int x, int y, int z) {
        return null;
    }

    @Override
    public Item getItemDropped(int meta, Random rand, int fortune) {
        return null;
    }

    @Override
    public int quantityDropped(Random rand) {
        return 0;
    }

    /**
     * Orphan cleanup. Only removes itself when nobody is standing near it, so a
     * player who stops moving never sees their own light flicker out.
     */
    @Override
    public void updateTick(World world, int x, int y, int z, Random rand) {
        if (world.isRemote) return;
        if (world.getClosestPlayer(x + 0.5D, y + 0.5D, z + 0.5D, 4.0D) == null) {
            world.setBlockToAir(x, y, z);
        }
    }
}
