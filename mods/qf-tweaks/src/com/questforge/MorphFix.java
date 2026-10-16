package com.questforge;

import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;

import org.lwjgl.opengl.GL11;

/**
 * Runtime half of {@link MorphOptifineTransformer}; Morph's patched classes call
 * into this. Client-only: nothing here is reached on a dedicated server.
 */
public final class MorphFix {

    private MorphFix() {
    }

    // ---- 1. kill-acquire crash -------------------------------------------------

    private static Method deleteDisplayLists;
    private static boolean lookedUp;

    /**
     * Stands in for GLAllocation.deleteDisplayLists(id). Vanilla's version is
     * glDeleteLists(id, map.remove(id)), which throws NullPointerException when
     * the list did not come from GLAllocation -- and under OptiFine E7 the model
     * lists Morph deletes often did not. Keep vanilla's behaviour when it works,
     * and otherwise delete the single list ModelRenderer compiles.
     */
    public static void deleteDisplayList(int id) {
        try {
            if (!lookedUp) {
                lookedUp = true;
                Class<?> c = Class.forName("net.minecraft.client.renderer.GLAllocation", false,
                        MorphFix.class.getClassLoader());
                deleteDisplayLists = c.getMethod("func_74523_b", int.class);
            }
            if (deleteDisplayLists != null) {
                deleteDisplayLists.invoke(null, id);
                return;
            }
        } catch (InvocationTargetException e) {
            // The NullPointerException this exists for; fall through.
        } catch (Throwable t) {
            deleteDisplayLists = null;
        }
        if (id > 0) {
            GL11.glDeleteLists(id, 1);
        }
    }

    // ---- 2. morph-in freeze ----------------------------------------------------

    private static boolean inHand;

    /**
     * True when Morph's hand handler may run. False while Morph is already inside
     * its own call to EntityRenderer.renderHand: OptiFine posts RenderHandEvent
     * from inside renderHand, so without this the handler re-enters itself until
     * the stack overflows -- every frame, which is the freeze.
     */
    public static boolean enterHand() {
        if (inHand) {
            return false;
        }
        inHand = true;
        return true;
    }

    public static void exitHand() {
        inHand = false;
    }
}
