package com.questforge.content.jukebox;

import net.minecraft.entity.player.EntityPlayer;
import net.minecraft.nbt.NBTTagCompound;
import net.minecraft.network.NetworkManager;
import net.minecraft.network.Packet;
import net.minecraft.network.play.server.S35PacketUpdateTileEntity;
import net.minecraft.tileentity.TileEntity;
import net.minecraft.util.AxisAlignedBB;

/**
 * The lower half of a tower speaker. The upper half is scenery.
 *
 * Almost nothing lives here. A speaker's name, range, volume, tone and pairing are
 * all held by {@link SpeakerRegistry}, because a jukebox has to be able to read them
 * while this block sits in an unloaded chunk 150 blocks away. What the block keeps is
 * the one thing that identifies which registry entry is its own -- and a copy of the
 * name, so the renderer can letter the cabinet without a round trip.
 */
public class TileEntityTowerSpeaker extends TileEntity {

    private String code = "";

    /** Mirrored from the registry purely so the renderer can draw it. */
    private String name = "Speaker";

    public String code() { return code; }
    public String speakerName() { return name; }

    public void setCode(String code) {
        this.code = code == null ? "" : code;
        markDirty();
    }

    /** Kept in step by the server whenever the registry entry is renamed. */
    public void setName(String name) {
        this.name = name == null || name.isEmpty() ? "Speaker" : name;
        markDirty();
        if (worldObj != null && !worldObj.isRemote) {
            worldObj.markBlockForUpdate(xCoord, yCoord, zCoord);
        }
    }

    /** The registry entry for this speaker, or null if it has none yet. */
    public SpeakerRegistry.Entry entry() {
        SpeakerRegistry reg = SpeakerRegistry.get(worldObj);
        return reg == null ? null : reg.find(code);
    }

    /**
     * Gives the speaker a code the first time it is needed, and files it.
     *
     * Deferred to first use rather than done on placement so that a stack of
     * speakers placed and immediately mined again does not burn codes that can never
     * be issued twice.
     */
    public SpeakerRegistry.Entry register(EntityPlayer by) {
        SpeakerRegistry reg = SpeakerRegistry.get(worldObj);
        if (reg == null) return null;

        SpeakerRegistry.Entry e = reg.find(code);
        if (e != null) return e;

        e = new SpeakerRegistry.Entry();
        e.code = reg.issue();
        e.dim = worldObj.provider.dimensionId;
        e.x = xCoord; e.y = yCoord; e.z = zCoord;
        e.name = name;
        reg.put(e);
        setCode(e.code);
        worldObj.markBlockForUpdate(xCoord, yCoord, zCoord);
        return e;
    }

    @Override
    public void readFromNBT(NBTTagCompound tag) {
        super.readFromNBT(tag);
        code = tag.getString("Code");
        name = tag.hasKey("Name") ? tag.getString("Name") : "Speaker";
    }

    @Override
    public void writeToNBT(NBTTagCompound tag) {
        super.writeToNBT(tag);
        tag.setString("Code", code);
        tag.setString("Name", name);
    }

    // Without these the cabinet renders nameless on every client until the chunk is
    // reloaded, and the renderer cannot find its own amplitude without the code.

    @Override
    public Packet getDescriptionPacket() {
        NBTTagCompound tag = new NBTTagCompound();
        writeToNBT(tag);
        return new S35PacketUpdateTileEntity(xCoord, yCoord, zCoord, 0, tag);
    }

    @Override
    public void onDataPacket(NetworkManager net, S35PacketUpdateTileEntity pkt) {
        readFromNBT(pkt.func_148857_g());
    }

    /**
     * The whole tower, both blocks, is one thing to look at, so its render box has
     * to cover the upper half too or it blinks out when the lower block leaves the
     * frustum.
     */
    @Override
    public AxisAlignedBB getRenderBoundingBox() {
        return AxisAlignedBB.getBoundingBox(xCoord, yCoord, zCoord,
                                            xCoord + 1, yCoord + 2, zCoord + 1);
    }
}
