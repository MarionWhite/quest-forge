package com.questforge.content.voice;

import net.minecraft.client.Minecraft;
import net.minecraft.entity.Entity;
import net.minecraft.entity.player.EntityPlayer;

import cpw.mods.fml.relauncher.Side;
import cpw.mods.fml.relauncher.SideOnly;

import com.questforge.content.net.PacketVoiceFrame;

import java.util.ArrayList;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.Queue;
import java.util.concurrent.ConcurrentLinkedQueue;
import java.util.HashMap;

/**
 * Everyone currently being heard.
 *
 * Sits between the network and {@link VoiceStream}: frames land here from a netty
 * thread, and the client tick drains them, decodes, and hands them to the right
 * speaker's stream. The split exists because OpenAL must only ever be touched from
 * the thread that owns its context, which is the client thread -- the same rule the
 * jukebox follows via Playback.pump().
 */
@SideOnly(Side.CLIENT)
public final class VoicePlayback {

    /**
     * A ceiling on simultaneous voices.
     *
     * OpenAL contexts have a finite source count and Minecraft is already spending
     * most of it, so an unbounded crowd would eventually fail to allocate and the
     * failure would land on whichever sound happened to ask next -- possibly the
     * game's, not ours.
     *
     * Once this many people are talking, further speakers are ignored until one of
     * them stops. Whoever started first wins, which is arbitrary but predictable;
     * dropping the most distant instead would be fairer and would mean re-sorting
     * every frame, and eight simultaneous talkers within 40 blocks is already well
     * past the point where a conversation is intelligible anyway.
     */
    private static final int MAX_VOICES = 8;

    /** Silence after which a speaker's source is released. */
    private static final long IDLE_MS = 2000L;

    private static final Queue<PacketVoiceFrame> INBOX =
            new ConcurrentLinkedQueue<PacketVoiceFrame>();

    private static final Map<Integer, VoiceStream> STREAMS =
            new HashMap<Integer, VoiceStream>();

    /** Scratch for decoding, reused. Only ever touched on the client thread. */
    private static final byte[] SCRATCH = new byte[VoiceFormat.PCM_BYTES_PER_FRAME];

    private VoicePlayback() { }

    /** Called from the netty thread. Does no work beyond handing the frame over. */
    public static void enqueue(PacketVoiceFrame frame) {
        // Bounded so a flood, or a client that stopped ticking, cannot grow this
        // without limit. VoiceStream trims its own backlog too, but that only helps
        // once frames have been drained this far.
        if (INBOX.size() > 512) INBOX.poll();
        INBOX.add(frame);
    }

    /** Client tick. Drains the inbox, feeds every stream, retires the idle ones. */
    public static void tick() {
        Minecraft game = Minecraft.getMinecraft();

        if (game.theWorld == null) {
            // Leaving a world must not leave sources playing into a context that is
            // about to be torn down, nor carry one server's speakers into the next.
            stopAll();
            return;
        }

        drainInbox(game);
        followSpeakers(game);

        float master = VoiceSettings.volume();
        boolean deafened = VoiceSettings.isDeafened();

        Iterator<Map.Entry<Integer, VoiceStream>> it = STREAMS.entrySet().iterator();
        long now = System.currentTimeMillis();
        while (it.hasNext()) {
            VoiceStream stream = it.next().getValue();

            if (now - stream.lastFrameAt() > IDLE_MS && !stream.isSpeaking()) {
                stream.dispose();
                it.remove();
                continue;
            }

            stream.tick();
            if (game.renderViewEntity != null) {
                stream.updateSpatial(game.renderViewEntity.posX,
                                     game.renderViewEntity.posY
                                             + game.renderViewEntity.getEyeHeight(),
                                     game.renderViewEntity.posZ,
                                     game.renderViewEntity.rotationYaw,
                                     deafened ? 0f : master);
            }
        }
    }

    private static void drainInbox(Minecraft game) {
        PacketVoiceFrame packet;
        while ((packet = INBOX.poll()) != null) {
            if (VoiceSettings.isDeafened()) continue;

            String name = nameOf(game, packet.speakerId);
            if (name != null && VoiceSettings.isMuted(name)) continue;

            VoiceStream stream = STREAMS.get(Integer.valueOf(packet.speakerId));
            if (stream == null) {
                if (STREAMS.size() >= MAX_VOICES) continue;
                stream = new VoiceStream(packet.speakerId);
                STREAMS.put(Integer.valueOf(packet.speakerId), stream);
            }

            int n = VoiceCodec.decode(packet.frame, packet.frame.length, SCRATCH);
            if (n <= 0) continue;

            byte[] pcm = new byte[n];
            System.arraycopy(SCRATCH, 0, pcm, 0, n);
            stream.offer(pcm, packet.x, packet.y, packet.z);
        }
    }

    /**
     * Moves each voice to where its speaker is right now.
     *
     * Frames carry a position, but they arrive at 50 Hz and only while someone is
     * talking. Reading the entity instead means a voice keeps tracking a player who
     * is running past mid-sentence, and does not stick to the spot they were in when
     * the last frame was sent.
     */
    private static void followSpeakers(Minecraft game) {
        if (STREAMS.isEmpty() || game.theWorld == null) return;

        for (VoiceStream stream : STREAMS.values()) {
            Entity e = game.theWorld.getEntityByID(stream.entityId());
            if (e != null) {
                stream.follow(e.posX, e.posY + e.getEyeHeight(), e.posZ);
            }
            // Not found means the speaker is outside this client's entity tracking
            // range. The position from their last frame is still the best guess, so
            // it is simply left alone.
        }
    }

    private static String nameOf(Minecraft game, int entityId) {
        if (game.theWorld == null) return null;
        Entity e = game.theWorld.getEntityByID(entityId);
        return e instanceof EntityPlayer ? ((EntityPlayer) e).getCommandSenderName() : null;
    }

    /** Names of everyone currently audible, for the HUD. */
    public static List<String> speaking() {
        List<String> out = new ArrayList<String>();
        Minecraft game = Minecraft.getMinecraft();
        for (VoiceStream stream : STREAMS.values()) {
            if (!stream.isSpeaking()) continue;
            String name = nameOf(game, stream.entityId());
            out.add(name == null ? "someone nearby" : name);
        }
        return out;
    }

    public static int activeVoices() { return STREAMS.size(); }

    public static void stopAll() {
        INBOX.clear();
        for (VoiceStream stream : STREAMS.values()) stream.dispose();
        STREAMS.clear();
    }
}
