package com.questforge.content.net;

import cpw.mods.fml.common.network.simpleimpl.IMessage;
import cpw.mods.fml.common.network.simpleimpl.IMessageHandler;
import cpw.mods.fml.common.network.simpleimpl.MessageContext;
import io.netty.buffer.ByteBuf;
import net.minecraft.entity.player.EntityPlayerMP;
import net.minecraft.item.ItemStack;
import net.minecraft.util.ChatComponentText;
import net.minecraft.util.EnumChatFormatting;

import java.util.ArrayList;
import java.util.List;

import com.questforge.content.ModItems;
import com.questforge.content.jukebox.ItemVinyl;
import com.questforge.content.jukebox.PublicPlaylists;
import com.questforge.content.jukebox.Track;

/**
 * Erasing a record, or dropping songs from one, from the inventory screen.
 *
 * Addressed by inventory slot rather than "the held item", because this happens
 * while the inventory is open and the record may be anywhere in it. The index is
 * checked against the player's own inventory on arrival -- it arrives from a
 * client, so it is a request, not an instruction.
 */
public class PacketEditRecord implements IMessage {

    public int slot;
    public boolean erase;
    public List<Track> keep = new ArrayList<Track>();

    /** Required by the packet codec. */
    public PacketEditRecord() { }

    public PacketEditRecord(int slot, boolean erase, List<Track> keep) {
        this.slot = slot;
        this.erase = erase;
        if (keep != null) this.keep = keep;
    }

    @Override
    public void fromBytes(ByteBuf buf) {
        slot = buf.readShort();
        erase = buf.readBoolean();
        keep = erase ? new ArrayList<Track>() : TrackCodec.readTracks(buf);
    }

    @Override
    public void toBytes(ByteBuf buf) {
        buf.writeShort(slot);
        buf.writeBoolean(erase);
        if (!erase) TrackCodec.writeTracks(buf, keep);
    }

    public static class Handler implements IMessageHandler<PacketEditRecord, IMessage> {

        @Override
        public IMessage onMessage(final PacketEditRecord m, MessageContext ctx) {
            final EntityPlayerMP player = ctx.getServerHandler().playerEntity;
            if (player == null) return null;

            ServerTasks.submit(new Runnable() {
                @Override public void run() {
                    if (m.slot < 0 || m.slot >= player.inventory.getSizeInventory()) return;

                    ItemStack stack = player.inventory.getStackInSlot(m.slot);
                    if (stack == null || stack.getItem() != ModItems.record) return;
                    if (!ItemVinyl.isWritten(stack)) return;

                    if (m.erase) {
                        ItemVinyl.erase(stack);
                        say(player, "Erased the record.");
                    } else if (m.keep.isEmpty()) {
                        // Removing the last song leaves a blank rather than a
                        // record that claims a name and plays nothing.
                        ItemVinyl.erase(stack);
                        say(player, "Removed the last song; the record is blank.");
                    } else {
                        int before = ItemVinyl.trackCount(stack);
                        ItemVinyl.write(stack, ItemVinyl.name(stack), m.keep);

                        int removed = before - m.keep.size();
                        if (removed > 0) {
                            say(player, "Removed " + removed
                                    + (removed == 1 ? " song." : " songs."));
                        }
                    }
                    player.inventory.markDirty();
                }
            });
            return null;
        }

        private static void say(EntityPlayerMP p, String message) {
            p.addChatMessage(new ChatComponentText(EnumChatFormatting.AQUA + "[jukebox] "
                    + EnumChatFormatting.RESET + message));
        }
    }
}
