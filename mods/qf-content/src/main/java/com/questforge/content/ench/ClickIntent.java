package com.questforge.content.ench;

import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

import net.minecraft.entity.player.EntityPlayer;

/**
 * Which inventory clicks a player's client has vouched for as deliberate.
 *
 * Drag-and-drop enchanting lives in Container.slotClick, and to the server every
 * slotClick looks the same: a stack on the cursor, a click on a slot. A person
 * dropping a book onto a sword and InventoryTweaks sorting a chest produce
 * byte-identical packets. InvTweaks sorts by picking stacks up and left-clicking
 * them onto other slots, so pressing its sort button applied every book in the
 * chest to whatever gear it happened to be shuffled onto, and every Magic Dust to
 * every book -- a cascade nobody asked for and nobody could undo.
 *
 * Timing cannot tell them apart: InvTweaks has a configurable delay between
 * clicks. What can is the client, which knows whether the mouse is actually over
 * the slot being clicked with its left button down. So the client vouches for a
 * deliberate application by sending PacketClickIntent immediately before the
 * click goes out, and the server applies a book or consumable only to a click it
 * has a matching intent for. Every other click -- sorting, shift-moving,
 * anything automated -- falls through to vanilla and simply moves the item.
 *
 * Ordering is guaranteed rather than hoped for: FML hands a custom payload to its
 * handler on the netty thread the moment it arrives, while the click packet that
 * follows it is queued for the next server tick.
 */
public final class ClickIntent {

    private ClickIntent() {}

    /** An intent older than this is stale and is ignored. */
    private static final long LIFETIME_MS = 5000L;

    private static final class Pending {
        final int windowId;
        final int slotId;
        final long at;

        Pending(int windowId, int slotId, long at) {
            this.windowId = windowId;
            this.slotId = slotId;
            this.at = at;
        }
    }

    private static final Map<UUID, Pending> PENDING = new ConcurrentHashMap<UUID, Pending>();

    /** Called from the packet handler, on the netty thread. */
    public static void record(EntityPlayer player, int windowId, int slotId) {
        if (player == null) return;
        PENDING.put(player.getUniqueID(),
                new Pending(windowId, slotId, System.currentTimeMillis()));
    }

    /**
     * True, once, if the client vouched for exactly this click. Consumed either way
     * so an intent can never be spent on a later click it was not sent for.
     */
    public static boolean consume(EntityPlayer player, int windowId, int slotId) {
        if (player == null) return false;
        Pending p = PENDING.remove(player.getUniqueID());
        if (p == null) return false;
        if (System.currentTimeMillis() - p.at > LIFETIME_MS) return false;
        return p.windowId == windowId && p.slotId == slotId;
    }
}
