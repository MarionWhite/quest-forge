package com.questforge.content.jukebox;

import net.minecraft.nbt.NBTTagCompound;
import net.minecraft.tileentity.TileEntity;

/**
 * Server-side state for one jukebox: which track it is bound to.
 *
 * The audio itself is never here. Sound is client-side, so each player hears the
 * block through their own machine; this only remembers what the block should play,
 * so it survives a save and so a GUI has something to write to later.
 */
public class TileEntityJukebox extends TileEntity {

    /** Track filename within the jukebox folder. Empty means "whatever is next". */
    private String track = "";

    /**
     * Which disc shows behind the glass: an {@link ItemVinyl} tier.
     *
     * Visual only -- it changes nothing about what plays. It is here rather than
     * on the client because the jukebox's right-click handling is client-side, so
     * a tier kept there would look right to the player who set it and be invisible
     * to everyone else and to the next session.
     */
    private int disc = 0;

    public String getTrack() { return track; }

    public int getDisc() { return disc; }

    public void setDisc(int tier) {
        this.disc = tier < 0 ? 0 : tier > 3 ? 3 : tier;
        markDirty();
        if (worldObj != null) {
            worldObj.markBlockForUpdate(xCoord, yCoord, zCoord);
        }
    }

    public void setTrack(String t) {
        this.track = t == null ? "" : t;
        markDirty();
        if (worldObj != null) {
            worldObj.markBlockForUpdate(xCoord, yCoord, zCoord);
        }
    }

    @Override
    public void readFromNBT(NBTTagCompound tag) {
        super.readFromNBT(tag);
        track = tag.getString("Track");
        disc = tag.getInteger("Disc");
    }

    @Override
    public void writeToNBT(NBTTagCompound tag) {
        super.writeToNBT(tag);
        tag.setString("Track", track);
        tag.setInteger("Disc", disc);
    }

    /**
     * The box the renderer is culled against.
     *
     * A tile entity is culled on its own block's cube by default, and this one
     * is a block wide and two tall with an arch on the front -- so at a steep
     * enough angle the lower block leaves the view frustum, the cabinet stops
     * being drawn, and the whole jukebox vanishes while it is plainly still on
     * screen. The box has to cover everything the model actually reaches.
     */
    @Override
    public net.minecraft.util.AxisAlignedBB getRenderBoundingBox() {
        return net.minecraft.util.AxisAlignedBB.getBoundingBox(
                xCoord - 0.5D, yCoord, zCoord - 0.5D,
                xCoord + 1.5D, yCoord + 2.5D, zCoord + 1.5D);
    }

    /** Jukeboxes are rare and cheap to tick past; no update logic needed yet. */
    @Override
    public boolean canUpdate() { return false; }

    // Without these two, the bound track lives only on the server and every client
    // sees an empty jukebox until it reloads the chunk.

    @Override
    public net.minecraft.network.Packet getDescriptionPacket() {
        NBTTagCompound tag = new NBTTagCompound();
        writeToNBT(tag);
        return new net.minecraft.network.play.server.S35PacketUpdateTileEntity(
                xCoord, yCoord, zCoord, 0, tag);
    }

    @Override
    public void onDataPacket(net.minecraft.network.NetworkManager net,
                             net.minecraft.network.play.server.S35PacketUpdateTileEntity pkt) {
        readFromNBT(pkt.func_148857_g());
    }
}
