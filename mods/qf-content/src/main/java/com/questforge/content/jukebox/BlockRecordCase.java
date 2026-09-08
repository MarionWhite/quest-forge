package com.questforge.content.jukebox;

import net.minecraft.block.Block;
import net.minecraft.block.material.Material;
import net.minecraft.entity.EntityLivingBase;
import net.minecraft.entity.item.EntityItem;
import net.minecraft.entity.player.EntityPlayer;
import net.minecraft.item.Item;
import net.minecraft.item.ItemStack;
import net.minecraft.tileentity.TileEntity;
import net.minecraft.world.World;

import java.util.Random;

/**
 * A wall case for a record: two blocks tall, one wide, and almost no depth.
 *
 * It hangs on a wall like a picture rather than standing on the floor, so it costs
 * no room to have one -- and it is still built out of real geometry rather than a
 * flat decal, so from the side you can see the record sitting behind glass.
 *
 * The lower half owns everything: the tile entity, the record, and the plaque. The
 * upper half is scenery that hands its clicks downward, and the two are placed and
 * broken together the way a door's halves are.
 */
public class BlockRecordCase extends Block {

    /** Bit in the metadata marking the upper half. The low two bits are facing. */
    public static final int UPPER = 4;

    /**
     * Kept in step with the renderer's frame depth. If this is the shallower of the
     * two the moulding stands out past the box you can actually click on, and the
     * selection outline cuts through the middle of it.
     */
    private static final float DEPTH = 2.75F / 16F;

    public BlockRecordCase() {
        super(Material.wood);
        setHardness(1.0F);
        setResistance(3.0F);
        // Heavier than wood on purpose: it is mostly a pane of glass.
        setStepSound(Block.soundTypeGlass);
    }

    public static boolean isUpper(int meta) { return (meta & UPPER) != 0; }

    public static int facing(int meta) { return meta & 3; }

    /**
     * Facing is stored as quarter-turns from south, because that is also the angle
     * the renderer needs; keeping one number for both means the model and the
     * collision box can never disagree about which way a case is pointing.
     */
    private static int facingFromSide(int side) {
        switch (side) {
            case 3:  return 0;   // clicked a south face: the case looks south
            case 5:  return 1;   // east
            case 2:  return 2;   // north
            case 4:  return 3;   // west
            default: return 0;
        }
    }

    // ------------------------------------------------------------------
    // Shape
    // ------------------------------------------------------------------

    @Override public boolean isOpaqueCube() { return false; }
    @Override public boolean renderAsNormalBlock() { return false; }

    /** Drawn entirely by the tile entity renderer. */
    @Override public int getRenderType() { return -1; }

    @Override public boolean hasTileEntity(int meta) { return !isUpper(meta); }

    @Override
    public TileEntity createTileEntity(World world, int meta) {
        return isUpper(meta) ? null : new TileEntityRecordCase();
    }

    @Override
    public void setBlockBoundsBasedOnState(net.minecraft.world.IBlockAccess world,
                                           int x, int y, int z) {
        setBoundsFor(facing(world.getBlockMetadata(x, y, z)));
    }

    private void setBoundsFor(int facing) {
        switch (facing) {
            case 0:  setBlockBounds(0F, 0F, 0F, 1F, 1F, DEPTH); break;         // faces south
            case 1:  setBlockBounds(0F, 0F, 0F, DEPTH, 1F, 1F); break;         // faces east
            case 2:  setBlockBounds(0F, 0F, 1F - DEPTH, 1F, 1F, 1F); break;    // faces north
            default: setBlockBounds(1F - DEPTH, 0F, 0F, 1F, 1F, 1F); break;    // faces west
        }
    }

    // ------------------------------------------------------------------
    // Placing
    // ------------------------------------------------------------------

    @Override
    public boolean canPlaceBlockOnSide(World world, int x, int y, int z, int side) {
        // Walls only, and it needs one neighbour free in the vertical: half a case
        // is not a case. Which of the two it takes is settled when it is placed.
        if (side < 2) return false;
        if (!hangsDown(world, x, y, z) && !world.isAirBlock(x, y + 1, z)) return false;
        return super.canPlaceBlockAt(world, x, y, z);
    }

    @Override
    public int onBlockPlaced(World world, int x, int y, int z, int side,
                             float hitX, float hitY, float hitZ, int meta) {
        return facingFromSide(side);
    }

    /**
     * A case hangs from where you aimed rather than standing on it.
     *
     * You put a picture on a wall by deciding where its top goes, so aiming at eye
     * level should give a case whose top is at eye level -- placing upward means
     * every case ends up a block higher than the spot you picked. The exception is
     * when there is no room below, which is what happens hanging one at head height
     * off the floor, and then it grows up instead of refusing to be placed at all.
     */
    private boolean hangsDown(World world, int x, int y, int z) {
        return y >= 1 && world.isAirBlock(x, y - 1, z);
    }

    @Override
    public void onBlockPlacedBy(World world, int x, int y, int z,
                                EntityLivingBase placer, ItemStack stack) {
        int facing = facing(world.getBlockMetadata(x, y, z));

        if (hangsDown(world, x, y, z)) {
            // The tile entity has to go by hand. Changing only the metadata leaves
            // the one created here in place, and since the upper half is not
            // supposed to have one it would linger unowned -- drawing a second case
            // on top of the real one.
            world.removeTileEntity(x, y, z);
            world.setBlock(x, y, z, this, facing | UPPER, 3);
            world.setBlock(x, y - 1, z, this, facing, 3);
            return;
        }

        world.setBlock(x, y + 1, z, this, facing | UPPER, 3);
    }

    // ------------------------------------------------------------------
    // Using
    // ------------------------------------------------------------------

    @Override
    public boolean onBlockActivated(World world, int x, int y, int z, EntityPlayer player,
                                    int side, float hitX, float hitY, float hitZ) {
        int meta = world.getBlockMetadata(x, y, z);
        int baseY = isUpper(meta) ? y - 1 : y;

        TileEntity te = world.getTileEntity(x, baseY, z);
        if (!(te instanceof TileEntityRecordCase)) return true;
        if (world.isRemote) return true;

        TileEntityRecordCase caseTe = (TileEntityRecordCase) te;
        ItemStack held = player.getHeldItem();

        if (caseTe.isEmpty()) {
            if (held == null || held.getItem() != com.questforge.content.ModItems.record) {
                return true;
            }
            ItemStack one = held.copy();
            one.stackSize = 1;
            caseTe.setRecord(one);

            if (!player.capabilities.isCreativeMode && --held.stackSize <= 0) {
                player.inventory.setInventorySlotContents(
                        player.inventory.currentItem, null);
            }
            world.playSoundEffect(x + 0.5, baseY + 0.5, z + 0.5,
                                  "step.stone", 0.6F, 1.6F);
            return true;
        }

        // Taking it back out. It goes to the hand if there is room and on the floor
        // if not, rather than being destroyed by a full inventory.
        ItemStack out = caseTe.getRecord();
        caseTe.setRecord(null);
        if (!player.inventory.addItemStackToInventory(out)) {
            dropStack(world, x, baseY, z, out);
        }
        world.playSoundEffect(x + 0.5, baseY + 0.5, z + 0.5, "step.stone", 0.6F, 1.2F);
        return true;
    }

    // ------------------------------------------------------------------
    // Breaking
    // ------------------------------------------------------------------

    /**
     * Breaking the top half has to hand back a case, and by default it does not.
     *
     * Only the lower half is an item, and the path that removes its partner clears
     * it straight to air, which drops nothing -- so striking the top destroyed the
     * case outright. That was survivable while the bottom half was the one at eye
     * level; now that a case hangs from where it was aimed, the top is the half you
     * naturally hit.
     *
     * Doing it here rather than in breakBlock is what makes the creative case work:
     * this is the only one of the two that is told which player swung, and breaking
     * something in creative should not shower items.
     */
    @Override
    public void onBlockHarvested(World world, int x, int y, int z, int meta,
                                 EntityPlayer player) {
        if (isUpper(meta) && world.getBlock(x, y - 1, z) == this) {
            if (player != null && player.capabilities.isCreativeMode) {
                world.setBlockToAir(x, y - 1, z);
            } else {
                world.func_147480_a(x, y - 1, z, true);   // destroy, with drops
            }
        }
        super.onBlockHarvested(world, x, y, z, meta, player);
    }

    @Override
    public void breakBlock(World world, int x, int y, int z, Block block, int meta) {
        if (isUpper(meta)) {
            // Taking the top half takes the bottom, and the bottom is what holds
            // the record.
            if (world.getBlock(x, y - 1, z) == this) {
                dropContents(world, x, y - 1, z);
                world.setBlockToAir(x, y - 1, z);
            }
        } else {
            dropContents(world, x, y, z);
            if (world.getBlock(x, y + 1, z) == this) world.setBlockToAir(x, y + 1, z);
        }
        super.breakBlock(world, x, y, z, block, meta);
    }

    private void dropContents(World world, int x, int y, int z) {
        if (world.isRemote) return;
        TileEntity te = world.getTileEntity(x, y, z);
        if (!(te instanceof TileEntityRecordCase)) return;

        TileEntityRecordCase caseTe = (TileEntityRecordCase) te;
        if (caseTe.isEmpty()) return;

        ItemStack stack = caseTe.getRecord();
        caseTe.setRecord(null);
        dropStack(world, x, y, z, stack);
    }

    private static void dropStack(World world, int x, int y, int z, ItemStack stack) {
        if (stack == null) return;
        EntityItem item = new EntityItem(world, x + 0.5, y + 0.5, z + 0.5, stack);
        item.delayBeforeCanPickup = 10;
        world.spawnEntityInWorld(item);
    }

    /** Only the lower half is an item; otherwise one case would break into two. */
    @Override
    public Item getItemDropped(int meta, Random random, int fortune) {
        return isUpper(meta) ? null : Item.getItemFromBlock(this);
    }

    @Override
    public int damageDropped(int meta) { return 0; }

    @Override
    public Item getItem(World world, int x, int y, int z) {
        return Item.getItemFromBlock(this);
    }
}
