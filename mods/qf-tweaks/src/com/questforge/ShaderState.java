package com.questforge;

import java.lang.reflect.Method;

/**
 * Whether a shader pack is running right now, under OptiFine or Angelica.
 *
 * Called from code patched into other mods, so it must never throw. Two
 * reflective lookups, since neither renderer is on the compile classpath:
 * OptiFine's Config.isShaders() (the E7 client) and Iris's
 * IrisApi.getInstance().isShaderPackInUse(), which Angelica ships. Re-checked
 * on every call through cached Methods, because a pack can be switched from
 * the video settings without a relaunch.
 */
public final class ShaderState {

    private static Boolean looked;
    private static Method isShaders;
    private static Object iris;
    private static Method irisInUse;

    private ShaderState() { }

    public static boolean active() {
        if (looked == null) {
            looked = Boolean.TRUE;
            try {
                isShaders = Class.forName("Config").getMethod("isShaders");
            } catch (Throwable ignored) {
                isShaders = null;      // no OptiFine
            }
            try {
                Class<?> api = Class.forName("net.irisshaders.iris.api.v0.IrisApi");
                iris = api.getMethod("getInstance").invoke(null);
                irisInUse = api.getMethod("isShaderPackInUse");
            } catch (Throwable ignored) {
                irisInUse = null;      // no Angelica
            }
        }
        boolean on = false;            // neither: plain fixed-function
        try {
            on = (isShaders != null && Boolean.TRUE.equals(isShaders.invoke(null)))
                    || (irisInUse != null && iris != null && Boolean.TRUE.equals(irisInUse.invoke(iris)));
        } catch (Throwable ignored) {
        }
        if (last == null || last != on) {
            last = on;               // one line per change; this runs every frame
            try {
                org.apache.logging.log4j.LogManager.getLogger("QuestForgeTweaks").info(
                        "[QuestForgeTweaks] shader pack {} ({}): patched mods take the {} path", on ? "ON" : "off",
                        isShaders != null ? "OptiFine" : irisInUse != null ? "Angelica/Iris" : "no shader mod",
                        on ? "shader-safe" : "normal");
            } catch (Throwable ignored) {
            }
        }
        return on;
    }

    private static Boolean last;
}
