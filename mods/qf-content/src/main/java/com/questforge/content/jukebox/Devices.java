package com.questforge.content.jukebox;

import cpw.mods.fml.relauncher.Side;
import cpw.mods.fml.relauncher.SideOnly;

import java.util.ArrayList;
import java.util.List;

/**
 * What the client believes is currently plugged in.
 *
 * The server owns the pairings; this is the copy the audio layer plays from and the
 * screens draw. It is deliberately a cache and not a source of truth -- everything
 * that changes it either arrived from the server or was asked of the server first --
 * because the alternative is a client that can hear speakers it is not paired with.
 *
 * The device list belongs to whichever thing owns the queue right now, so it changes
 * when you put down a jukebox's screen and pick up a JBL, exactly as the queue does.
 */
@SideOnly(Side.CLIENT)
public final class Devices {

    /**
     * The tower speaker's range table.
     *
     * The first four match the jukebox and the JBL. The last two are the reason a
     * tower exists: something that can fill a build, rather than a room. Stadium was
     * taken off the small speakers when these arrived -- a portable that carries a
     * third of a kilometre made the towers pointless.
     */
    public static final String[] RANGE_NAMES =
            { "Booth", "Room", "Hall", "Block", "Stadium", "Festival" };
    public static final float[] RANGE_FULL = { 6f, 12f, 20f, 36f, 64f, 100f };
    public static final float[] RANGE_MAX  = { 40f, 70f, 120f, 200f, 320f, 500f };

    /** How long a refusal from the server stays on screen. */
    private static final long PROBLEM_MS = 5000L;

    private static String owner = "";
    private static boolean ownerEnabled = true;
    private static List<SpeakerRegistry.Entry> list =
            new ArrayList<SpeakerRegistry.Entry>();

    private static String problem = "";
    private static long problemAt;

    private Devices() { }

    // ------------------------------------------------------------------
    // From the server
    // ------------------------------------------------------------------

    public static void accept(String owner, boolean ownerEnabled,
                              List<SpeakerRegistry.Entry> devices, String problem) {
        Devices.owner = owner == null ? "" : owner;
        Devices.ownerEnabled = ownerEnabled;
        Devices.list = devices == null ? new ArrayList<SpeakerRegistry.Entry>() : devices;
        if (problem != null && !problem.isEmpty()) {
            Devices.problem = problem;
            problemAt = System.currentTimeMillis();
        } else {
            Devices.problem = "";
        }
        push();
    }

    /** One speaker's settings changed at the speaker itself. */
    public static void update(SpeakerRegistry.Entry e) {
        atSpeaker(e);
        for (int i = 0; i < list.size(); i++) {
            if (list.get(i).code.equals(e.code)) {
                // A speaker that has just been unpaired from us stops being ours.
                if (!owner.equals(e.pairedTo)) list.remove(i);
                else list.set(i, e);
                push();
                return;
            }
        }
        if (owner.equals(e.pairedTo)) { list.add(e); push(); }
    }

    /** Keeps an open speaker screen in step with what the server just agreed to. */
    private static void atSpeaker(SpeakerRegistry.Entry e) {
        net.minecraft.client.gui.GuiScreen open =
                net.minecraft.client.Minecraft.getMinecraft().currentScreen;
        if (open instanceof GuiTowerSpeaker) ((GuiTowerSpeaker) open).refresh(e);
    }

    public static void clear() {
        owner = "";
        list = new ArrayList<SpeakerRegistry.Entry>();
        ownerEnabled = true;
        DirectAudio.setDevices(new DirectAudio.Device[0]);
        DirectAudio.setOwnerEnabled(true);
    }

    // ------------------------------------------------------------------
    // Reading
    // ------------------------------------------------------------------

    public static List<SpeakerRegistry.Entry> list() { return list; }

    public static boolean ownerEnabled() { return ownerEnabled; }

    public static String owner() { return owner; }

    /** A refusal worth showing, or empty once it has had its moment. */
    public static String problem() {
        if (problem.isEmpty()) return "";
        if (System.currentTimeMillis() - problemAt > PROBLEM_MS) problem = "";
        return problem;
    }

    // ------------------------------------------------------------------
    // Asking
    // ------------------------------------------------------------------

    /** Sends an action for whichever owner's screen is open. */
    public static void act(int action, String code) {
        String speaker = Speakers.active();
        if (speaker != null) {
            com.questforge.content.net.QFNetwork.toServer(
                    com.questforge.content.net.PacketDeviceAction.forItem(speaker, action, code));
            return;
        }
        net.minecraft.client.gui.GuiScreen open =
                net.minecraft.client.Minecraft.getMinecraft().currentScreen;
        if (open instanceof GuiJukebox) {
            GuiJukebox gui = (GuiJukebox) open;
            com.questforge.content.net.QFNetwork.toServer(
                    com.questforge.content.net.PacketDeviceAction.forBlock(
                            gui.blockX(), gui.blockY(), gui.blockZ(), action, code));
        }
    }

    public static void refresh() {
        act(com.questforge.content.net.PacketDeviceAction.REFRESH, "");
    }

    // ------------------------------------------------------------------
    // To the audio layer
    // ------------------------------------------------------------------

    /**
     * Hands the audio layer the speakers that should be sounding.
     *
     * Only the ones switched on are passed: a disabled speaker is not a silent
     * source, it is not a source at all, so it costs no OpenAL handle and cannot
     * hold the lockstep feed back.
     */
    private static void push() {
        List<DirectAudio.Device> out = new ArrayList<DirectAudio.Device>();
        for (SpeakerRegistry.Entry e : list) {
            if (!e.enabled) continue;
            int r = e.range < 0 ? 0 : e.range >= RANGE_FULL.length ? RANGE_FULL.length - 1 : e.range;
            out.add(new DirectAudio.Device(e.code, e.x + 0.5, e.y + 1.0, e.z + 0.5,
                                           RANGE_FULL[r], RANGE_MAX[r],
                                           e.volume, e.bass, e.treble));
        }
        DirectAudio.setDevices(out.toArray(new DirectAudio.Device[out.size()]));
        DirectAudio.setOwnerEnabled(ownerEnabled);
    }
}
