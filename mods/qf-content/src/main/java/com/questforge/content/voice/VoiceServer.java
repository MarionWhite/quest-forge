package com.questforge.content.voice;

import net.minecraft.entity.player.EntityPlayerMP;
import net.minecraft.server.MinecraftServer;

import com.questforge.content.net.PacketVoiceFrame;
import com.questforge.content.net.QFNetwork;

import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

/**
 * The proximity filter: decides who is close enough to hear whom.
 *
 * This is the whole reason the audio goes through the server rather than
 * peer-to-peer. A client is never sent voice from outside
 * {@link VoiceFormat#MAX_RANGE}, so listening in from across the map is not a
 * question of a client choosing to behave -- the audio simply is not there. It also
 * means a busy area costs bandwidth in proportion to who can actually hear, rather
 * than broadcasting everything to everyone.
 *
 * Every method here runs on a netty thread. See {@link
 * com.questforge.content.net.PacketVoice.Handler} for why that is deliberate.
 */
public final class VoiceServer {

    /** Per-speaker send budget, so one client cannot flood the server. */
    private static final Map<UUID, Budget> BUDGETS = new ConcurrentHashMap<UUID, Budget>();

    private VoiceServer() { }

    private static final class Budget {
        long windowStart;
        int frames;
        long lastWarned;
    }

    public static void relay(EntityPlayerMP speaker, byte[] frame) {
        if (!allow(speaker)) return;

        MinecraftServer server = MinecraftServer.getServer();
        if (server == null || server.getConfigurationManager() == null) return;

        @SuppressWarnings("unchecked")
        List<EntityPlayerMP> everyone =
                (List<EntityPlayerMP>) server.getConfigurationManager().playerEntityList;
        if (everyone == null) return;

        double sx = speaker.posX;
        // Ears, not feet. Placing a voice at the player's origin puts it at ankle
        // height, which is audibly wrong when someone is standing next to you.
        double sy = speaker.posY + speaker.getEyeHeight();
        double sz = speaker.posZ;

        int speakerId = speaker.getEntityId();
        int speakerDim = speaker.dimension;
        double rangeSq = VoiceFormat.MAX_RANGE * VoiceFormat.MAX_RANGE;

        PacketVoiceFrame out = new PacketVoiceFrame(speakerId, sx, sy, sz, frame);

        // Indexed rather than for-each: the list is the live player list and another
        // thread joining or leaving a player mid-iteration would otherwise throw
        // ConcurrentModificationException and kill this frame for everyone.
        for (int i = 0; i < everyone.size(); i++) {
            EntityPlayerMP listener;
            try {
                listener = everyone.get(i);
            } catch (IndexOutOfBoundsException e) {
                break;                                  // list shrank under us
            }
            if (listener == null || listener == speaker) continue;
            if (listener.dimension != speakerDim) continue;

            double dx = listener.posX - sx;
            double dy = listener.posY + listener.getEyeHeight() - sy;
            double dz = listener.posZ - sz;
            if (dx * dx + dy * dy + dz * dz > rangeSq) continue;

            QFNetwork.toPlayer(out, listener);
        }
    }

    /**
     * True if this speaker is inside their frame budget.
     *
     * A well-behaved client sends exactly {@link VoiceFormat#FRAME_MS} apart. This
     * exists for the one that does not: without it a modified client could hand every
     * player in range an unbounded stream and cost the server their bandwidth.
     */
    private static boolean allow(EntityPlayerMP speaker) {
        UUID id = speaker.getUniqueID();
        Budget b = BUDGETS.get(id);
        if (b == null) {
            b = new Budget();
            Budget existing = BUDGETS.putIfAbsent(id, b);
            if (existing != null) b = existing;
        }

        long now = System.currentTimeMillis();
        synchronized (b) {
            if (now - b.windowStart >= 1000L) {
                b.windowStart = now;
                b.frames = 0;
            }
            if (++b.frames > VoiceFormat.MAX_FRAMES_PER_SECOND) {
                // Logged at most once a minute per player: the whole point is that
                // this fires many times a second, and a log line per dropped frame
                // would be a worse denial of service than the flood.
                if (now - b.lastWarned > 60000L) {
                    b.lastWarned = now;
                    com.questforge.content.QuestForgeContent.log.warn(
                            "[voice] dropping frames from " + speaker.getCommandSenderName()
                            + ": over " + VoiceFormat.MAX_FRAMES_PER_SECOND + " per second");
                }
                return false;
            }
        }
        return true;
    }

    public static void reset() {
        BUDGETS.clear();
    }

    /**
     * Drops a player's send budget when they leave.
     *
     * Without this the map keeps one small entry per player who has ever spoken,
     * for as long as the server is up. Trivial on a friend server, but it is the
     * kind of thing that is free to get right now and annoying to find later.
     */
    public static class Lifecycle {
        @cpw.mods.fml.common.eventhandler.SubscribeEvent
        public void onLogout(cpw.mods.fml.common.gameevent.PlayerEvent.PlayerLoggedOutEvent e) {
            if (e.player != null) BUDGETS.remove(e.player.getUniqueID());
        }
    }
}
