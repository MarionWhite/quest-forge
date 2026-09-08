package com.questforge.content.voice;

import cpw.mods.fml.client.registry.ClientRegistry;
import cpw.mods.fml.relauncher.Side;
import cpw.mods.fml.relauncher.SideOnly;

import net.minecraft.client.settings.KeyBinding;

import org.lwjgl.input.Keyboard;

/**
 * Push-to-talk, and the two switches worth reaching for without opening a menu.
 *
 * B and N rather than the more obvious V, which the record menu already holds -- see
 * {@link com.questforge.content.jukebox.RecordKeys}. Both are free in vanilla 1.7.10
 * and neither collides with NEI's lookup keys.
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
        pushToTalk = new KeyBinding("key.qfcontent.voice_ptt", Keyboard.KEY_B, CATEGORY);
        muteSelf = new KeyBinding("key.qfcontent.voice_mute", Keyboard.KEY_N, CATEGORY);
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
