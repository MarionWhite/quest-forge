package com.questforge.content.jukebox;

import cpw.mods.fml.client.registry.ClientRegistry;
import net.minecraft.client.settings.KeyBinding;
import org.lwjgl.input.Keyboard;

/**
 * The key that opens a record's menu while the cursor is over it.
 *
 * A key rather than a click. Every mouse button in an inventory already means
 * something -- left takes a stack, right splits one, middle clones in creative,
 * and shift changes all of them -- so a record's menu had no button left that
 * would not be taking one away from something else.
 *
 * Registered as a proper binding so it shows up in Controls and can be moved if it
 * clashes with something. V is free in vanilla and clear of the keys NEI takes for
 * recipe and usage lookups, which is where an inventory-hover key is most likely
 * to collide.
 */
public final class RecordKeys {

    public static KeyBinding menu;

    private RecordKeys() { }

    public static void register() {
        menu = new KeyBinding("key.qfcontent.record_menu", Keyboard.KEY_V,
                              "key.categories.inventory");
        ClientRegistry.registerKeyBinding(menu);
    }

    /** The bound key's name, so the tooltip stays honest after a rebind. */
    public static String keyName() {
        try {
            return Keyboard.getKeyName(menu.getKeyCode());
        } catch (Throwable t) {
            return "V";
        }
    }

    public static int keyCode() {
        return menu == null ? Keyboard.KEY_V : menu.getKeyCode();
    }
}
