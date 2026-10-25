package com.questforge.content.voice;

import cpw.mods.fml.client.registry.ClientRegistry;
import cpw.mods.fml.relauncher.Side;
import cpw.mods.fml.relauncher.SideOnly;

import net.minecraft.client.settings.KeyBinding;

import org.lwjgl.input.Keyboard;

/**
 * Push-to-talk, and the two switches worth reaching for without opening a menu.
 *
 * Tab to talk, U to mute. Not the obvious V, which the record menu already holds (see
 * {@link com.questforge.content.jukebox.RecordKeys}) along with four other mods' keys,
 * and not B and N, which were the defaults until 2026-10-25: Adventure Backpack opens
 * on B and switches its hose on N, and Transformers aims on B, so a word spoken opened
 * a backpack. Read from the pack's options.txt on that day, Tab's only other tenant is
 * vanilla's player list (held, cosmetic, and arguably informative while talking), and U
 * has none in the world: NEI's "usage" U lives inside inventories, where key input
 * events do not reach us. Every other left-hand key belongs to Legends, OreSpawn,
 * Transformers or TragicMC. Existing installs keep whatever options.txt says, so
 * tools/pack-fixes/voice_keys.py rewrites those two lines.
 *
 * Push-to-talk is read by polling the key rather than through KeyInputEvent, because
 * that event fires on the transition and we need to know whether the key is down
 * right now, every tick, for as long as it is held.
 */
@SideOnly(Side.CLIENT)
public final class VoiceKeys {

    private static final String CATEGORY = "key.categories.qfvoice";

    public static KeyBinding pushToTalk;
    public static KeyBinding muteSelf;
    public static KeyBinding deafen;

    private VoiceKeys() { }

    public static void register() {
        pushToTalk = new KeyBinding("key.qfcontent.voice_ptt", Keyboard.KEY_TAB, CATEGORY);
        muteSelf = new KeyBinding("key.qfcontent.voice_mute", Keyboard.KEY_U, CATEGORY);
        deafen = new KeyBinding("key.qfcontent.voice_deafen", Keyboard.KEY_NONE, CATEGORY);

        ClientRegistry.registerKeyBinding(pushToTalk);
        ClientRegistry.registerKeyBinding(muteSelf);
        ClientRegistry.registerKeyBinding(deafen);
    }

    /**
     * Whether the talk key is held.
     *
     * Asks LWJGL directly rather than KeyBinding.getIsKeyPressed(), which consumes a
     * queued press and would report a single true for a key held down for a whole
     * sentence.
     */
    public static boolean talkHeld() {
        if (pushToTalk == null) return false;
        int code = pushToTalk.getKeyCode();
        if (code <= 0) return false;
        try {
            return Keyboard.isKeyDown(code);
        } catch (Throwable t) {
            return false;
        }
    }

    public static String talkKeyName() {
        try {
            return Keyboard.getKeyName(pushToTalk.getKeyCode());
        } catch (Throwable t) {
            return "B";
        }
    }
}
