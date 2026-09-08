package com.questforge.content.jukebox;

import net.minecraft.item.ItemStack;
import net.minecraft.nbt.NBTTagCompound;
import net.minecraft.network.NetworkManager;
import net.minecraft.network.Packet;
import net.minecraft.network.play.server.S35PacketUpdateTileEntity;
import net.minecraft.tileentity.TileEntity;

/**
 * The record inside a display case.
 *
 * Lives on the lower half only; the upper half is scenery that routes everything
 * back down here. The whole ItemStack is kept rather than just a name and a tier,
 * because the record's songs have to survive being taken back out -- a case is
 * somewhere to put a record, not somewhere to spend one.
 */
public class TileEntityRecordCase extends TileEntity {

    private ItemStack record;

    public ItemStack getRecord() { return record; }

    public boolean isEmpty() { return record == null; }

    public void setRecord(ItemStack stack) {
        this.record = stack;
        markDirty();
        if (worldObj != null) worldObj.markBlockForUpdate(xCoord, yCoord, zCoord);
    }

    /** The name on the plaque, or empty for a blank case. */
    public String plaque() {
        if (record == null) return "";
        String name = ItemVinyl.name(record);
        return name;
    }

    @Override public boolean canUpdate() { return false; }

    @Override
    public void readFromNBT(NBTTagCompound tag) {
        super.readFromNBT(tag);
        record = tag.hasKey("Record")
                ? ItemStack.loadItemStackFromNBT(tag.getCompoundTag("Record"))
                : null;
    }

    @Override
    public void writeToNBT(NBTTagCompound tag) {
        super.writeToNBT(tag);
        if (record != null) {
            NBTTagCompound item = new NBTTagCompound();
            record.writeToNBT(item);
            tag.setTag("Record", item);
        }
    }

    // Without these the case renders empty on every client until the chunk is
    // reloaded, which for a thing whose entire job is being looked at is fatal.

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
     * The whole case, both blocks, is one thing to look at, so its render box has
     * to cover the upper half too or it blinks out when the lower block leaves the
     * frustum.
     */
    @Override
    public net.minecraft.util.AxisAlignedBB getRenderBoundingBox() {
        return net.minecraft.util.AxisAlignedBB.getBoundingBox(
                xCoord, yCoord, zCoord, xCoord + 1, yCoord + 2, zCoord + 1);
    }
}
