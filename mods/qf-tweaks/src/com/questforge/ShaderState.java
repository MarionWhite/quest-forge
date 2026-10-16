package com.questforge;

import java.lang.reflect.Method;

/**
 * Whether OptiFine is running a shader pack right now.
 *
 * Called from code patched into other mods, so it must never throw. Looked up
 * reflectively -- OptiFine is not on the compile classpath -- and re-checked on
 * every call through a cached Method, because a pack can be switched from the
 * video settings without a relaunch.
 */
public final class ShaderState {

    private static Boolean looked;
    private static Method isShaders;

    private ShaderState() { }

    public static boolean active() {
        if (looked == null) {
            looked = Boolean.TRUE;
            try {
                isShaders = Class.forName("Config").getMethod("isShaders");
            } catch (Throwable ignored) {
                isShaders = null;      // no OptiFine at all: plain fixed-function
            }
        }
        if (isShaders == null) return false;
        try {
            return Boolean.TRUE.equals(isShaders.invoke(null));
        } catch (Throwable ignored) {
            return false;
        }
    }
}
