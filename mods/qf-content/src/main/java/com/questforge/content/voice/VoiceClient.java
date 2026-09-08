package com.questforge.content.voice;

import cpw.mods.fml.common.eventhandler.SubscribeEvent;
import cpw.mods.fml.common.gameevent.TickEvent;
import cpw.mods.fml.relauncher.Side;
import cpw.mods.fml.relauncher.SideOnly;

import net.minecraft.client.Minecraft;
import net.minecraft.util.ChatComponentText;

import com.questforge.content.net.PacketVoice;
import com.questforge.content.net.QFNetwork;

/**
 * The sending half: microphone in, frames on the wire.
 *
 * Capture runs on its own thread rather than on the client tick, and that is the
 * important decision here. {@link VoiceCapture#readFrame} blocks until the sound card
 * has produced exactly 20 ms, so the thread is paced by the audio clock -- frames
 * leave every 20 ms whether the game is rendering at 200 fps or stuttering through a
 * chunk load. Driving it from the 20 Hz client tick instead would mean sending two or
 * three frames in a burst every 50 ms, and going silent entirely during a lag spike,
 * which is exactly when a conversation most needs to keep working.
 *
 * The tick still owns everything that touches Minecraft. The capture thread reads
 * nothing but the volatile flags below.
 */
@SideOnly(Side.CLIENT)
public class VoiceClient {

    /** Set by the tick, read by the capture thread. */
    private static volatile boolean allowedToSend;

    /** Closes the microphone after this long unused, so the mic light goes out. */
    private static final long IDLE_CLOSE_MS = 60000L;

    private static volatile Thread captureThread;
    private static volatile boolean running;

    /** Live input level, for the HUD and /voice level. */
    private static volatile float inputLevel;

    /** True while frames are actually being sent. */
    private static volatile boolean transmitting;

    private static volatile String lastError;

    /**
     * Consecutive frames of digital silence from an open microphone.
     *
     * This is the diagnostic for the failure that is otherwise invisible, and it is
     * the same failure on both platforms: Windows can refuse desktop applications the
     * microphone (Privacy -> Microphone -> "Allow desktop apps to access your
     * microphone") and macOS can withhold the TCC grant, and in neither case does
     * anything throw. The line opens, reads succeed, and every sample is zero.
     *
     * Exact zero is the test rather than a low threshold, because a working
     * microphone always has some noise floor -- 480 consecutive samples of precisely
     * nothing means the operating system is synthesising the silence, not the room.
     */
    private static volatile int silentFrames;

    /** 3 seconds of it, before saying anything. */
    private static final int SILENT_FRAMES_WARN = 150;

    private static boolean warnedSilent;

    private static boolean settingsLoaded;

    // ------------------------------------------------------------------
    // Tick
    // ------------------------------------------------------------------

    @SubscribeEvent
    public void onClientTick(TickEvent.ClientTickEvent event) {
        if (event.phase != TickEvent.Phase.END) return;

        if (!settingsLoaded) {
            settingsLoaded = true;
            VoiceSettings.load();
        }

        Minecraft game = Minecraft.getMinecraft();
        handleKeys(game);

        boolean inWorld = game.theWorld != null && game.thePlayer != null;

        // A menu or the pause screen should not leave a hot microphone open behind
        // it -- the player has stepped away from the game, not muted themselves.
        boolean focused = game.currentScreen == null;

        allowedToSend = VoiceSettings.isEnabled()
                && !VoiceSettings.isMuted()
                && inWorld
                && (VoiceSettings.mode() == VoiceSettings.Mode.OPEN_MIC ? focused
                                                                        : VoiceKeys.talkHeld());

        if (inWorld && VoiceSettings.isEnabled()) {
            start();
        } else if (!inWorld) {
            stop();
        }

        VoicePlayback.tick();
    }

    private void handleKeys(Minecraft game) {
        if (VoiceKeys.muteSelf == null) return;

        // isPressed() consumes one queued press, which is what a toggle wants --
        // unlike push-to-talk, which polls the key state directly.
        while (VoiceKeys.muteSelf.isPressed()) {
            VoiceSettings.setMuted(!VoiceSettings.isMuted());
            say(game, VoiceSettings.isMuted()
                    ? "§cMicrophone muted"
                    : "§aMicrophone live");
        }
        while (VoiceKeys.deafen.isPressed()) {
            VoiceSettings.setDeafened(!VoiceSettings.isDeafened());
            if (VoiceSettings.isDeafened()) VoicePlayback.stopAll();
            say(game, VoiceSettings.isDeafened()
                    ? "§cDeafened -- you will not hear anyone"
                    : "§aListening again");
        }
    }

    private static void say(Minecraft game, String message) {
        if (game.thePlayer != null) {
            game.thePlayer.addChatMessage(new ChatComponentText("[voice] " + message));
        }
    }

    // ------------------------------------------------------------------
    // The capture thread
    // ------------------------------------------------------------------

    public static synchronized void start() {
        if (running) return;
        running = true;

        Thread t = new Thread(new Runnable() {
            @Override public void run() { captureLoop(); }
        }, "QF-Voice-Capture");
        // A daemon thread so a stuck audio device can never hold the game open on
        // the way out.
        t.setDaemon(true);
        captureThread = t;
        t.start();
    }

    public static synchronized void stop() {
        running = false;
        Thread t = captureThread;
        captureThread = null;
        if (t != null) t.interrupt();
        transmitting = false;
        inputLevel = 0f;
    }

    /**
     * Reads the microphone forever, and sends only the parts that count as speech.
     *
     * The line is drained even when nothing is being sent. That is not waste: a
     * device whose buffer is left to fill hands back seconds-old audio the moment
     * push-to-talk is pressed, and metering for the open-mic gate needs the samples
     * anyway.
     */
    private static void captureLoop() {
        VoiceCapture capture = null;
        VoiceCodec.State encoder = new VoiceCodec.State();

        short[] frame = new short[VoiceFormat.SAMPLES_PER_FRAME];
        byte[] encoded = new byte[VoiceCodec.FRAME_BYTES];

        int hangover = 0;
        long lastWanted = System.currentTimeMillis();

        try {
            while (running) {
                boolean wants = allowedToSend;
                boolean openMic = VoiceSettings.mode() == VoiceSettings.Mode.OPEN_MIC;

                // The microphone is not opened until it is first wanted, so a player
                // who never speaks never triggers the operating system's in-use
                // indicator. In open-mic mode "wanted" is simply being in the world
                // and unmuted -- the gate below decides what actually gets sent.
                if (capture == null) {
                    if (!wants) { sleep(50); continue; }
                    try {
                        capture = VoiceCapture.open(VoiceSettings.device());
                        // Reset before the first frame, or the idle timer would still
                        // be measuring from before the device was closed and would
                        // shut it again immediately.
                        lastWanted = System.currentTimeMillis();
                        lastError = null;
                        silentFrames = 0;
                        warnedSilent = false;
                        com.questforge.content.QuestForgeContent.log.info(
                                "[voice] microphone open: " + capture.describe());
                    } catch (Throwable t) {
                        lastError = String.valueOf(t.getMessage());
                        com.questforge.content.QuestForgeContent.log.warn(
                                "[voice] could not open microphone", t);
                        sleep(3000);          // do not spin on a missing device
                        continue;
                    }
                }

                if (!capture.readFrame(frame)) {
                    // The line died under us -- a device unplugged, or the default
                    // output changing. Drop it and let the next pass reopen.
                    capture.close();
                    capture = null;
                    continue;
                }

                float level = VoiceCapture.rms(frame, frame.length);
                inputLevel = level;

                if (level == 0f) {
                    if (++silentFrames == SILENT_FRAMES_WARN && !warnedSilent) {
                        warnedSilent = true;
                        com.questforge.content.QuestForgeContent.log.warn(
                                "[voice] microphone is open but delivering pure silence"
                                + " -- check the operating system's microphone"
                                + " permission for Java, or that the device is not"
                                + " muted in hardware (" + capture.describe() + ")");
                    }
                } else {
                    silentFrames = 0;
                    warnedSilent = false;
                }

                boolean send;
                if (!wants) {
                    send = false;
                    hangover = 0;
                } else if (openMic) {
                    if (level >= VoiceSettings.threshold()) {
                        hangover = VoiceSettings.hangoverFrames();
                        send = true;
                    } else {
                        // Keeps sending briefly after the level drops, so the end of
                        // a word is not clipped off by its own quietness.
                        send = hangover > 0;
                        if (hangover > 0) hangover--;
                    }
                } else {
                    send = true;                    // push-to-talk, key is held
                }

                if (send) {
                    lastWanted = System.currentTimeMillis();
                    VoiceCodec.encode(frame, frame.length, encoder, encoded);
                    // Copied because the packet outlives this loop iteration: netty
                    // may still be writing it when the next frame overwrites here.
                    byte[] copy = new byte[encoded.length];
                    System.arraycopy(encoded, 0, copy, 0, encoded.length);
                    QFNetwork.toServer(new PacketVoice(copy));
                } else if (transmitting) {
                    // Speech just ended. Reset so the next burst starts from a clean
                    // predictor rather than wherever the last word left it.
                    encoder.reset();
                }
                transmitting = send;

                if (!send && System.currentTimeMillis() - lastWanted > IDLE_CLOSE_MS) {
                    com.questforge.content.QuestForgeContent.log.info(
                            "[voice] microphone idle, releasing device");
                    capture.close();
                    capture = null;
                    sleep(200);
                }
            }
        } catch (Throwable t) {
            lastError = String.valueOf(t);
            com.questforge.content.QuestForgeContent.log.error("[voice] capture thread died", t);
        } finally {
            if (capture != null) capture.close();
            transmitting = false;
            inputLevel = 0f;
        }
    }

    private static void sleep(long ms) {
        try {
            Thread.sleep(ms);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            running = false;
        }
    }

    // ------------------------------------------------------------------

    public static float inputLevel() { return inputLevel; }

    public static boolean isTransmitting() { return transmitting; }

    public static boolean isCaptureRunning() { return running; }

    public static String lastError() { return lastError; }

    /**
     * True when an open microphone has been handing back nothing but digital
     * silence. Almost always an operating system permission, on either platform.
     */
    public static boolean micSeemsSilent() {
        return silentFrames >= SILENT_FRAMES_WARN;
    }
}
