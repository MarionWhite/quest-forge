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

    public String getTrack() { return track; }

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
    }

    @Override
    public void writeToNBT(NBTTagCompound tag) {
        super.writeToNBT(tag);
        tag.setString("Track", track);
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
