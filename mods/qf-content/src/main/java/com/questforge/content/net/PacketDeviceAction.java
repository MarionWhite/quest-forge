package com.questforge.content.net;

import com.questforge.content.jukebox.BlockJukebox;
import com.questforge.content.jukebox.ItemSpeaker;
import com.questforge.content.jukebox.SpeakerRegistry;
import cpw.mods.fml.common.network.simpleimpl.IMessage;
import cpw.mods.fml.common.network.simpleimpl.IMessageHandler;
import cpw.mods.fml.common.network.simpleimpl.MessageContext;
import io.netty.buffer.ByteBuf;
import net.minecraft.entity.player.EntityPlayerMP;
import net.minecraft.item.ItemStack;
import net.minecraft.world.World;

import java.util.List;

/**
 * Pairing, unpairing and switching devices on and off, from the owner's end.
 *
 * <h3>What the server will not take on trust</h3>
 * The client says which owner it is acting as, and that claim is the whole security
 * boundary: unchecked, anyone could pair their own speaker to somebody else's
 * jukebox, or silence one across the map. So the owner is re-derived here and
 * verified against the player -- a jukebox has to actually be a jukebox, in this
 * dimension, within reach; a JBL has to be the one in the player's hand. The code
 * they send is only ever looked up, never trusted to describe anything.
 */
public class PacketDeviceAction implements IMessage {

    public static final int PAIR = 0, UNPAIR = 1, TOGGLE = 2, REFRESH = 3, OPEN = 4;

    /** How far a player may be from their own jukebox while using its screen. */
    private static final double REACH = 24.0;

    /** Owner is a block if this is true, otherwise the JBL named by {@link #id}. */
    public boolean block;
    public int x, y, z;
    public String id = "";

    public int action;
    /** The device being acted on; empty means the owner's own speaker. */
    public String code = "";

    public PacketDeviceAction() { }

    public static PacketDeviceAction forBlock(int x, int y, int z, int action, String code) {
        PacketDeviceAction p = new PacketDeviceAction();
        p.block = true; p.x = x; p.y = y; p.z = z;
        p.action = action; p.code = code == null ? "" : code;
        return p;
    }

    public static PacketDeviceAction forItem(String id, int action, String code) {
        PacketDeviceAction p = new PacketDeviceAction();
        p.block = false; p.id = id == null ? "" : id;
        p.action = action; p.code = code == null ? "" : code;
        return p;
    }

    @Override
    public void fromBytes(ByteBuf buf) {
        block = buf.readBoolean();
        x = buf.readInt(); y = buf.readInt(); z = buf.readInt();
        id = SpeakerCodec.readString(buf, 48);
        action = buf.readByte();
        code = SpeakerRegistry.normalise(SpeakerCodec.readString(buf, SpeakerCodec.MAX_CODE));
    }

    @Override
    public void toBytes(ByteBuf buf) {
        buf.writeBoolean(block);
        buf.writeInt(x); buf.writeInt(y); buf.writeInt(z);
        SpeakerCodec.writeString(buf, id, 48);
        buf.writeByte(action);
        SpeakerCodec.writeString(buf, code, SpeakerCodec.MAX_CODE);
    }

    public static class Handler implements IMessageHandler<PacketDeviceAction, IMessage> {

        @Override
        public IMessage onMessage(PacketDeviceAction m, MessageContext ctx) {
            EntityPlayerMP player = ctx.getServerHandler().playerEntity;
            if (player == null) return null;
            World world = player.worldObj;

            SpeakerRegistry reg = SpeakerRegistry.get(world);
            if (reg == null) return null;

            String owner = verifyOwner(m, player, world);
            if (owner == null) return null;

            String problem = null;
            switch (m.action) {
                case PAIR:    problem = pair(reg, m, owner, player); break;
                case UNPAIR:  unpair(reg, m, owner); break;
                case TOGGLE:  toggle(reg, m, owner); break;
                case REFRESH: break;
                case OPEN:
                    // Answers with the speaker's screen rather than the device list.
                    openRemotely(reg, m, owner, player);
                    return null;
                default: return null;
            }

            QFNetwork.toPlayer(new PacketDeviceList(owner, reg.ownerEnabled(owner),
                                                   reg.pairedWith(owner), problem), player);
            return null;
        }

        /**
         * Turns the client's claim into an owner key, or null if it does not hold up.
         */
        private String verifyOwner(PacketDeviceAction m, EntityPlayerMP player, World world) {
            if (m.block) {
                if (!world.blockExists(m.x, m.y, m.z)) return null;
                if (!(world.getBlock(m.x, m.y, m.z) instanceof BlockJukebox)) return null;
                double dx = m.x + 0.5 - player.posX;
                double dy = m.y + 0.5 - player.posY;
                double dz = m.z + 0.5 - player.posZ;
                if (dx * dx + dy * dy + dz * dz > REACH * REACH) return null;
                return SpeakerRegistry.blockOwner(player.dimension, m.x, m.y, m.z);
            }
            // A JBL is only yours while you are holding it, which is also the only
            // time it can play -- so the same rule covers both.
            ItemStack held = player.getHeldItem();
            if (held == null || !(held.getItem() instanceof ItemSpeaker)) return null;
            String actual = ItemSpeaker.id(held);
            if (actual.isEmpty() || !actual.equals(m.id)) return null;
            return SpeakerRegistry.itemOwner(actual);
        }

        private String pair(SpeakerRegistry reg, PacketDeviceAction m, String owner,
                            EntityPlayerMP player) {
            SpeakerRegistry.Entry e = reg.find(m.code);
            if (e == null) return "No speaker has that code";
            if (owner.equals(e.pairedTo)) return "Already connected";
            if (!e.pairedTo.isEmpty()) return "That speaker is paired to something else";
            if (e.dim != player.dimension) return "That speaker is in another dimension";

            List<SpeakerRegistry.Entry> already = reg.pairedWith(owner);
            if (already.size() >= SpeakerCodec.MAX_DEVICES) return "Too many devices";

            double dx = e.x + 0.5 - anchorX(m, player);
            double dy = e.y + 0.5 - anchorY(m, player);
            double dz = e.z + 0.5 - anchorZ(m, player);
            double range = SpeakerRegistry.PAIR_RANGE;
            if (dx * dx + dy * dy + dz * dz > range * range) return "Out of range";

            e.pairedTo = owner;
            e.enabled = true;
            reg.put(e);
            return null;
        }

        // Distance is measured from the jukebox for a block, and from the player for
        // a JBL -- which is the same thing, since the JBL is in their hand.
        private double anchorX(PacketDeviceAction m, EntityPlayerMP p) {
            return m.block ? m.x + 0.5 : p.posX;
        }
        private double anchorY(PacketDeviceAction m, EntityPlayerMP p) {
            return m.block ? m.y + 0.5 : p.posY;
        }
        private double anchorZ(PacketDeviceAction m, EntityPlayerMP p) {
            return m.block ? m.z + 0.5 : p.posZ;
        }

        /**
         * Opens one paired speaker's own screen, from the owner's list.
         *
         * Only a speaker that already answers to this owner, which is the same rule
         * that lets the owner unpair or silence it. Verifying it here as well as in
         * PacketSpeakerEdit is not redundant: this is what decides whether the
         * player is shown the speaker's settings at all, and a screen that opened
         * for a speaker the player had no claim on would be a leak even if every
         * edit it then tried was refused.
         */
        private void openRemotely(SpeakerRegistry reg, PacketDeviceAction m,
                                  String owner, EntityPlayerMP player) {
            SpeakerRegistry.Entry e = reg.find(m.code);
            if (e == null || !owner.equals(e.pairedTo)) return;
            QFNetwork.toPlayer(new PacketOpenTowerSpeaker(e.x, e.y, e.z, e, true), player);
        }

        private void unpair(SpeakerRegistry reg, PacketDeviceAction m, String owner) {
            SpeakerRegistry.Entry e = reg.find(m.code);
            // Only the owner it actually answers to may let it go.
            if (e == null || !owner.equals(e.pairedTo)) return;
            e.pairedTo = "";
            reg.put(e);
        }

        private void toggle(SpeakerRegistry reg, PacketDeviceAction m, String owner) {
            if (m.code.isEmpty()) {
                reg.setOwnerEnabled(owner, !reg.ownerEnabled(owner));
                return;
            }
            SpeakerRegistry.Entry e = reg.find(m.code);
            if (e == null || !owner.equals(e.pairedTo)) return;
            e.enabled = !e.enabled;
            reg.put(e);
        }
    }
}
