package com.questforge.content.jukebox;

import net.minecraft.block.Block;
import net.minecraft.block.BlockContainer;
import net.minecraft.block.material.Material;
import net.minecraft.entity.EntityLivingBase;
import net.minecraft.entity.player.EntityPlayer;
import net.minecraft.entity.player.EntityPlayerMP;
import net.minecraft.item.Item;
import net.minecraft.item.ItemStack;
import net.minecraft.tileentity.TileEntity;
import net.minecraft.util.MathHelper;
import net.minecraft.world.World;

/**
 * A tower speaker: two blocks of cabinet that a jukebox can play through.
 *
 * Built the way the record case is -- one block that owns everything and a second
 * that is only there so the thing is two blocks tall. The tile entity lives on the
 * lower half, and the upper half is deliberately empty of state, so there is never a
 * question about which of the two is the speaker.
 *
 * It is narrower than a full block on purpose. A cabinet that filled its block would
 * meet its neighbours edge to edge and read as terrain; leaving a margin lets the
 * floor show underneath and around it, which is what makes it look like an object
 * standing in a room rather than part of the building.
 */
public class BlockTowerSpeaker extends BlockContainer {

    /** Set on the upper half's metadata; the low two bits are the facing. */
    public static final int UPPER = 4;

    /** How far in from the block's edge the cabinet stands. */
    private static final float INSET = 0.07F;

    public BlockTowerSpeaker() {
        super(Material.wood);
        setHardness(2.0F);
        setResistance(6.0F);
        setStepSound(soundTypeWood);
        setBlockName("tower_speaker");
        // Drawn by a TESR in the world, but the item form still needs a face.
        setBlockTextureName(com.questforge.content.QuestForgeContent.MODID + ":tower_speaker");
        setCreativeTab(com.questforge.content.ModCreativeTab.INSTANCE);
        setBlockBounds(INSET, 0F, INSET, 1F - INSET, 1F, 1F - INSET);
    }

    public static boolean isUpper(int meta) { return (meta & UPPER) != 0; }

    public static int facing(int meta) { return meta & 3; }

    // ------------------------------------------------------------------
    // Shape
    // ------------------------------------------------------------------

    @Override public boolean isOpaqueCube() { return false; }
    @Override public boolean renderAsNormalBlock() { return false; }

    /** Drawn entirely by its renderer; there is no block model at all. */
    @Override public int getRenderType() { return -1; }

    @Override public boolean hasTileEntity(int meta) { return !isUpper(meta); }

    @Override
    public TileEntity createNewTileEntity(World world, int meta) {
        return isUpper(meta) ? null : new TileEntityTowerSpeaker();
    }

    @Override
    public void setBlockBoundsBasedOnState(net.minecraft.world.IBlockAccess world,
                                           int x, int y, int z) {
        setBlockBounds(INSET, 0F, INSET, 1F - INSET, 1F, 1F - INSET);
    }

    @Override
    public boolean canPlaceBlockAt(World world, int x, int y, int z) {
        // Two blocks tall, so it needs two blocks of room and a world tall enough
        // to hold the second one.
        return y < world.getHeight() - 1
                && world.getBlock(x, y + 1, z).isReplaceable(world, x, y + 1, z)
                && super.canPlaceBlockAt(world, x, y, z);
    }

    // ------------------------------------------------------------------
    // Placing and breaking
    // ------------------------------------------------------------------

    @Override
    public void onBlockPlacedBy(World world, int x, int y, int z,
                                EntityLivingBase placer, ItemStack stack) {
        // Facing the player, so the grille looks at whoever put it down.
        int look = MathHelper.floor_double(placer.rotationYaw * 4.0F / 360.0F + 0.5D) & 3;
        world.setBlockMetadataWithNotify(x, y, z, look, 2);
        world.setBlock(x, y + 1, z, this, look | UPPER, 3);
    }

    /**
     * Taking either half takes the other.
     *
     * Done here rather than in breakBlock because this is the only one of the two
     * told which player swung, and breaking something in creative should not shower
     * items -- the same reasoning as the record case.
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
            if (world.getBlock(x, y - 1, z) == this) {
                forget(world, x, y - 1, z);
                world.setBlockToAir(x, y - 1, z);
            }
        } else {
            forget(world, x, y, z);
            if (world.getBlock(x, y + 1, z) == this) world.setBlockToAir(x, y + 1, z);
        }
        super.breakBlock(world, x, y, z, block, meta);
    }

    /**
     * Drops the speaker out of the registry, which also unpairs it.
     *
     * The code itself is not released -- {@link SpeakerRegistry} keeps every code it
     * has ever issued -- so a jukebox still holding this one finds nothing rather
     * than finding somebody else's new speaker.
     */
    private void forget(World world, int x, int y, int z) {
        if (world.isRemote) return;
        TileEntity te = world.getTileEntity(x, y, z);
        if (!(te instanceof TileEntityTowerSpeaker)) return;
        SpeakerRegistry reg = SpeakerRegistry.get(world);
        if (reg != null) reg.remove(((TileEntityTowerSpeaker) te).code());
    }

    /** Only the lower half is an item; the upper is scenery. */
    @Override
    public Item getItemDropped(int meta, java.util.Random rand, int fortune) {
        return isUpper(meta) ? null : Item.getItemFromBlock(this);
    }

    @Override
    public Item getItem(World world, int x, int y, int z) {
        return Item.getItemFromBlock(this);
    }

    // ------------------------------------------------------------------
    // Using
    // ------------------------------------------------------------------

    @Override
    public boolean onBlockActivated(World world, int x, int y, int z, EntityPlayer player,
                                    int side, float hitX, float hitY, float hitZ) {
        int meta = world.getBlockMetadata(x, y, z);
        int baseY = isUpper(meta) ? y - 1 : y;

        // The screen is opened from the server, the same way the JBL's is: the code
        // is issued here, and a client that opened its own screen first would have
        // to guess at one that does not exist yet.
        if (world.isRemote) return true;

        TileEntity te = world.getTileEntity(x, baseY, z);
        if (!(te instanceof TileEntityTowerSpeaker)) return true;

        TileEntityTowerSpeaker speaker = (TileEntityTowerSpeaker) te;
        SpeakerRegistry.Entry e = speaker.register(player);
        if (e == null) return true;

        com.questforge.content.net.QFNetwork.toPlayer(
                new com.questforge.content.net.PacketOpenTowerSpeaker(x, baseY, z, e),
                (EntityPlayerMP) player);
        return true;
    }
}
