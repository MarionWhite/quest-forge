package com.questforge;

/**
 * Reentrancy flag for Morph's first-person hand override.
 *
 * Morph 0.9.3 EventHandler.onRenderHand cancels RenderHandEvent and then
 * calls EntityRenderer.renderHand / func_78476_b so it can swap in the
 * morph arm. OptiFine E7 ReflectorForge.renderFirstPersonHand posts that
 * same event again, so Morph re-enters itself until the client freezes
 * (stack overflow / InvocationTargetException, often no crash-report).
 *
 * The bytecode / ASM patch calls shouldSkip() at the top of onRenderHand.
 * A nested call returns immediately WITHOUT canceling, so OptiFine's
 * inner renderHand actually draws the swapped morph arm, then leave()
 * runs on the way out.
 *
 * Also shipped inside Morph-Beta-0.9.3-QF-OPTIFINE.jar so the work-folder
 * jar is self-contained and does not require a rebuilt QuestForgeTweaks.
 */
public final class MorphHandGuard {

    public static boolean rendering;

    private MorphHandGuard() {}

    public static boolean shouldSkip() {
        return rendering;
    }

    public static void enter() {
        rendering = true;
    }

    public static void leave() {
        rendering = false;
    }
}
