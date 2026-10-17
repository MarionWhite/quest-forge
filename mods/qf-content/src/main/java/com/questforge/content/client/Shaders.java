package com.questforge.content.client;

import java.lang.reflect.Method;

import cpw.mods.fml.relauncher.Side;
import cpw.mods.fml.relauncher.SideOnly;

/**
 * Whether OptiFine is running a shader pack right now.
 *
 * Two renderers need this and for opposite reasons. The record case takes a
 * shader-safe path when a pack is on, because a deferred pack cannot blend its
 * glass pane. The jukebox takes an <em>extra</em> path when a pack is off,
 * because fixed-function texture generation gives its chrome a real moving
 * reflection and a shader pack ignores {@code glTexGen} entirely.
 *
 * Looked up reflectively -- OptiFine is not on the compile classpath -- and
 * re-checked on every call through a cached Method, because a pack can be
 * switched from the video settings without a relaunch.
 */
@SideOnly(Side.CLIENT)
public final class Shaders {

    private static Boolean looked;
    private static Method isShaders;

    private Shaders() { }

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
