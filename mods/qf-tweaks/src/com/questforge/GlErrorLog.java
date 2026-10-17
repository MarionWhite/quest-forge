package com.questforge;

import java.util.HashSet;
import java.util.Set;

import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.lwjgl.opengl.GL11;

/**
 * OptiFine's shader GL error check, without the cost of reporting every error
 * every frame. Called in place of shadersmod.client.Shaders.checkGLError; see
 * GlErrorTransformer for why.
 *
 * Behaves exactly as the original towards OpenGL: one glGetError, which clears
 * the error flag, and the same return value. Only the reporting differs: each
 * distinct error at each distinct checkpoint is logged once, and after that a
 * single line a minute says how many more there were. A real new error still
 * shows up the first time it happens.
 */
public final class GlErrorLog {

    private static final Logger LOG = LogManager.getLogger("QuestForgeTweaks");

    /** Bounds the memory the "seen" set can take; checkpoint names can carry counters. */
    private static final int MAX_KEYS = 256;
    private static final long SUMMARY_NS = 60L * 1000000000L;

    private static final Set<String> SEEN = new HashSet<String>();
    private static long suppressed;
    private static long lastSummary = System.nanoTime();

    private GlErrorLog() {
    }

    /** Called from the render thread only, like the methods they replace. */
    public static int check(String location) {
        int err = GL11.glGetError();
        if (err != 0) {
            report(err, location);
        }
        return err;
    }

    /** The overload OptiFine's uniform setters use: program, then uniform name. */
    public static int check(String location, String info) {
        int err = GL11.glGetError();
        if (err != 0) {
            report(err, location + ' ' + info);
        }
        return err;
    }

    public static int check(String location, String info1, String info2) {
        int err = GL11.glGetError();
        if (err != 0) {
            report(err, location + ' ' + info1 + ' ' + info2);
        }
        return err;
    }

    private static void report(int err, String location) {
        String key = Integer.toHexString(err) + '@' + location;
        if (SEEN.size() < MAX_KEYS && SEEN.add(key)) {
            LOG.warn("[QuestForgeTweaks] GL error 0x{} at {} (shader pass). Logged once; "
                    + "repeats are counted, not printed.", Integer.toHexString(err), location);
            return;
        }
        suppressed++;
        long now = System.nanoTime();
        if (now - lastSummary >= SUMMARY_NS) {
            LOG.info("[QuestForgeTweaks] {} repeated shader GL errors in the last minute "
                    + "(not printed individually).", suppressed);
            suppressed = 0;
            lastSummary = now;
        }
    }
}
