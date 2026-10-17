package com.questforge.content.jukebox;

import net.minecraft.block.Block;
import net.minecraft.block.material.Material;
import net.minecraft.entity.EntityLivingBase;
import net.minecraft.entity.player.EntityPlayer;
import net.minecraft.item.ItemStack;
import net.minecraft.tileentity.TileEntity;
import net.minecraft.util.ChatComponentText;
import net.minecraft.util.EnumChatFormatting;
import net.minecraft.util.MathHelper;
import net.minecraft.world.World;


/**
 * The jukebox. Right-click to start or stop; the music plays from the block's
 * position in the world, not from the player.
 *
 * Audio is client-side only -- each player hears it on their own machine through
 * their own speakers -- so every sound call here is guarded on world.isRemote. The
 * tile entity holds only which track the block is bound to.
 *
 * <h3>Shape</h3>
 * A bubbler is a piece of furniture, not a cube: one block wide, two tall, drawn
 * entirely by {@link RenderJukebox}. The tile entity lives on the lower half and
 * the upper half is deliberately stateless, so there is never a question about
 * which of the two is the jukebox -- the same arrangement the record case and the
 * tower speaker use.
 *
 * Metadata is the low two bits of facing plus {@link #UPPER}. The tile entity does
 * not read it and the block drops as meta 0, so one picked up and put back down
 * turns to whoever placed it and loses nothing else.
 */
public class BlockJukebox extends Block {

    /** Set on the upper half's metadata; the low two bits are the facing. */
    public static final int UPPER = 4;

    /** How far in from the block's edge the cabinet stands. */
    private static final float INSET = 0.09F;

    public BlockJukebox() {
        super(Material.wood);
        setBlockBounds(INSET, 0F, INSET, 1F - INSET, 1F, 1F - INSET);
        // Glass, chrome and neon standing in a room: it should not carve a
        // lightless column out of the world the way a solid block does.
        setLightOpacity(0);
    }

    public static boolean isUpper(int meta) { return (meta & UPPER) != 0; }

    public static int facing(int meta) { return meta & 3; }

    /** The lower half of the pair at these coordinates. */
    public static int baseY(World world, int x, int y, int z) {
        return isUpper(world.getBlockMetadata(x, y, z)) ? y - 1 : y;
    }

    // ------------------------------------------------------------------
    // Shape
    // ------------------------------------------------------------------

    @Override public boolean isOpaqueCube() { return false; }
    @Override public boolean renderAsNormalBlock() { return false; }

    /** Drawn entirely by its renderer; there is no block model at all. */
    @Override public int getRenderType() { return -1; }

    @Override public boolean hasTileEntity(int meta) { return !isUpper(meta); }

    @Override public TileEntity createTileEntity(World world, int meta) {
        return isUpper(meta) ? null : new TileEntityJukebox();
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

    @Override
    public void onBlockPlacedBy(World world, int x, int y, int z,
                                EntityLivingBase placer, ItemStack stack) {
        // Turned to face whoever put it down, so the arch looks back at them.
        int look = MathHelper.floor_double(placer.rotationYaw * 4.0F / 360.0F + 0.5D) & 3;
        world.setBlockMetadataWithNotify(x, y, z, look, 2);
        world.setBlock(x, y + 1, z, this, look | UPPER, 3);
    }

    /**
     * Taking either half takes the other.
     *
     * Done here rather than in breakBlock because this is the only one of the two
     * told which player swung, and breaking something in creative should not
     * shower items -- the same reasoning as the record case and the tower speaker.
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

    /** Only the lower half is an item; the upper is scenery. */
    @Override
    public net.minecraft.item.Item getItemDropped(int meta, java.util.Random rand,
                                                  int fortune) {
        return isUpper(meta) ? null : net.minecraft.item.Item.getItemFromBlock(this);
    }

    @Override
    public net.minecraft.item.Item getItem(World world, int x, int y, int z) {
        return net.minecraft.item.Item.getItemFromBlock(this);
    }

    @Override
    public boolean onBlockActivated(World world, int x, int y, int z, EntityPlayer player,
                                    int side, float hitX, float hitY, float hitZ) {
        // The server owns the block; the client owns the sound. Returning true on
        // the server still consumes the click so no item gets placed.
        if (!world.isRemote) return true;

        // Clicking the arch is clicking the jukebox. Everything below works off
        // the lower half, which is the one that owns the tile entity.
        y = baseY(world, x, y, z);

        // A record in hand takes over the click: the jukebox is the cutting lathe
        // as well as the deck, so pressing and playing back both happen at one.
        net.minecraft.item.ItemStack held = player.getHeldItem();
        if (held != null && held.getItem() == com.questforge.content.ModItems.record) {
            // The disc you put in is the disc you see turning behind the glass.
            com.questforge.content.net.QFNetwork.toServer(
                    new com.questforge.content.net.PacketDiscTier(
                            x, y, z, ItemVinyl.tier(held)));
            useRecord(player, held);
            return true;
        }

        // Sneak-click is the quick control: start the next track, or stop what is
        // playing, without opening anything. A plain click opens the player.
        if (player.isSneaking()) {
            if (DirectAudio.isActive() || Playback.loading() != null) {
                Playback.stop();
                say(player, "stopped");
                return true;
            }
            MusicIndex.ensureBuilt();
            Track track = pickTrack(world, x, y, z);
            if (track == null) {
                if (MusicIndex.isIndexing()) {
                    say(player, "Still reading your library (" + MusicIndex.status() + ")");
                } else {
                    say(player, EnumChatFormatting.YELLOW + "Nothing bound to this jukebox.");
                    say(player, "Right-click it to search for music.");
                }
                return true;
            }
            // The lower half's centre. Not mid-cabinet, tempting as that is: this
            // same triple is floored into block coordinates by the screen and by
            // PacketBindTrack, so raising it by a block would address the arch --
            // which owns no tile entity -- and the audio height is imperceptible.
            Playback.play(track, x + 0.5, y + 0.5, z + 0.5);
            say(player, EnumChatFormatting.GREEN + "♪ " + track.title
                    + EnumChatFormatting.GRAY + "  " + track.artistText());
            return true;
        }

        // Through the proxy: GuiJukebox is client-only and must not be loaded on a
        // dedicated server, even though this branch already cannot run there.
        com.questforge.content.QuestForgeContent.proxy.openJukeboxGui(
                x + 0.5, y + 0.5, z + 0.5);
        return true;
    }

    /**
     * A blank record opens the cutter; a pressed one gets copied into the library.
     *
     * Playing one back needs no packet at all. The contents are already in the
     * item's NBT and the item is already in this client's hand, so saving it is a
     * local read into a local library -- and the record survives, which is what
     * makes it worth handing to somebody.
     */
    private void useRecord(EntityPlayer player, net.minecraft.item.ItemStack disc) {
        if (!ItemVinyl.isWritten(disc)) {
            com.questforge.content.QuestForgeContent.proxy.openRecorderGui();
            return;
        }

        java.util.List<Track> tracks = ItemVinyl.tracks(disc);
        if (tracks.isEmpty()) {
            say(player, EnumChatFormatting.YELLOW + "That record came out blank.");
            return;
        }

        String name = ItemVinyl.name(disc);
        if (name.isEmpty()) name = "Record";

        // Someone else's record must not merge into a playlist you already have.
        String target = name;
        for (int i = 2; Library.hasPlaylist(target) && i < 100; i++) {
            target = name + " " + i;
        }
        if (!Library.createPlaylist(target)) {
            say(player, EnumChatFormatting.YELLOW + "Could not make room for that record.");
            return;
        }

        int added = 0;
        for (int i = 0; i < tracks.size(); i++) {
            if (Library.addToPlaylist(target, tracks.get(i))) added++;
        }
        say(player, EnumChatFormatting.GREEN + "Saved \"" + target + "\""
                + EnumChatFormatting.GRAY + "  " + added
                + (added == 1 ? " song" : " songs"));
    }

    /** The bound track if this block holds one, otherwise the next in the library. */
    private Track pickTrack(World world, int x, int y, int z) {
        TileEntity te = world.getTileEntity(x, y, z);
        if (te instanceof TileEntityJukebox) {
            Track bound = MusicIndex.byKey(((TileEntityJukebox) te).getTrack());
            if (bound != null) return bound;
        }
        return MusicIndex.next();
    }

    @Override
    public void breakBlock(World world, int x, int y, int z, Block block, int meta) {
        // Whichever half goes, the other follows it.
        if (isUpper(meta)) {
            if (world.getBlock(x, y - 1, z) == this) world.setBlockToAir(x, y - 1, z);
        } else {
            if (world.getBlock(x, y + 1, z) == this) world.setBlockToAir(x, y + 1, z);

            // Music does not come from a block that no longer exists -- but it is
            // put down rather than thrown away, so the play button at the next
            // jukebox carries on from the same second. Only the lower half is ever
            // the source, which is the half that holds the tile entity.
            if (world.isRemote && JukeboxTicker.isSourceAt(x + 0.5, y + 0.5, z + 0.5)) {
                Playback.suspend();
            }
        }
        super.breakBlock(world, x, y, z, block, meta);
    }

    private static void say(EntityPlayer p, String msg) {
        p.addChatMessage(new ChatComponentText(EnumChatFormatting.AQUA + "[jukebox] "
                + EnumChatFormatting.RESET + msg));
    }
}
