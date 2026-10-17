package com.questforge.content.client;

import java.lang.reflect.Method;

import cpw.mods.fml.relauncher.Side;
import cpw.mods.fml.relauncher.SideOnly;

/**
 * Whether a shader pack is running right now, under OptiFine or under Angelica.
 *
 * Two renderers need this and for opposite reasons. The record case takes a
 * shader-safe path when a pack is on, because a deferred pack cannot blend its
 * glass pane. The jukebox takes an <em>extra</em> path when a pack is off,
 * because fixed-function texture generation gives its chrome a real moving
 * reflection and a shader pack ignores {@code glTexGen} entirely.
 *
 * Two lookups, both reflective because neither renderer is a compile
 * dependency: OptiFine's {@code Config.isShaders()} (the E7 client) and
 * Iris's {@code IrisApi.getInstance().isShaderPackInUse()}, which Angelica
 * ships (the Angelica client). Only one of them exists in any one game.
 * Re-checked on every call through cached Methods, because a pack can be
 * switched from the video settings without a relaunch.
 */
@SideOnly(Side.CLIENT)
public final class Shaders {

    private static Boolean looked;
    private static Method isShaders;
    private static Object iris;
    private static Method irisInUse;

    private Shaders() { }

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
                irisInUse = null;      // no Angelica/Iris
            }
        }
        boolean on = false;        // neither: plain fixed-function
        try {
            on = (isShaders != null && Boolean.TRUE.equals(isShaders.invoke(null)))
                    || (irisInUse != null && iris != null && Boolean.TRUE.equals(irisInUse.invoke(iris)));
        } catch (Throwable ignored) {
        }
        if (last == null || last != on) {
            // One line per change, so a log shows which path the record case and
            // jukebox took (this is called every frame they draw).
            last = on;
            cpw.mods.fml.common.FMLLog.info("[QuestForge] shader pack %s (%s): record case and jukebox take the %s path",
                    on ? "ON" : "off", isShaders != null ? "OptiFine" : irisInUse != null ? "Angelica/Iris" : "no shader mod",
                    on ? "shader-safe" : "fixed-function");
        }
        return on;
    }

    private static Boolean last;
}
