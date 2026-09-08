package com.questforge.content.jukebox;

import net.minecraft.block.Block;
import net.minecraft.block.material.Material;
import net.minecraft.entity.player.EntityPlayer;
import net.minecraft.tileentity.TileEntity;
import net.minecraft.util.ChatComponentText;
import net.minecraft.util.EnumChatFormatting;
import net.minecraft.world.World;


/**
 * The jukebox. Right-click to start or stop; the music plays from the block's
 * position in the world, not from the player.
 *
 * Audio is client-side only -- each player hears it on their own machine through
 * their own speakers -- so every sound call here is guarded on world.isRemote. The
 * tile entity holds only which track the block is bound to.
 */
public class BlockJukebox extends Block {

    public BlockJukebox() {
        super(Material.wood);
    }

    @Override public boolean hasTileEntity(int meta) { return true; }

    @Override public TileEntity createTileEntity(World world, int meta) {
        return new TileEntityJukebox();
    }

    @Override
    public boolean onBlockActivated(World world, int x, int y, int z, EntityPlayer player,
                                    int side, float hitX, float hitY, float hitZ) {
        // The server owns the block; the client owns the sound. Returning true on
        // the server still consumes the click so no item gets placed.
        if (!world.isRemote) return true;

        // A record in hand takes over the click: the jukebox is the cutting lathe
        // as well as the deck, so pressing and playing back both happen at one.
        net.minecraft.item.ItemStack held = player.getHeldItem();
        if (held != null && held.getItem() == com.questforge.content.ModItems.record) {
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
            // Centre of the block, so it sounds like it comes from the box itself.
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
        // Music does not come from a block that no longer exists -- but it is put
        // down rather than thrown away, so the play button at the next jukebox
        // carries on from the same second.
        if (world.isRemote && JukeboxTicker.isSourceAt(x + 0.5, y + 0.5, z + 0.5)) {
            Playback.suspend();
        }
        super.breakBlock(world, x, y, z, block, meta);
    }

    private static void say(EntityPlayer p, String msg) {
        p.addChatMessage(new ChatComponentText(EnumChatFormatting.AQUA + "[jukebox] "
                + EnumChatFormatting.RESET + msg));
    }
}
