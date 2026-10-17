package com.questforge;

import javax.script.ScriptEngineManager;

import org.apache.logging.log4j.LogManager;

/**
 * Called from Lucky Block's patched ExpressionParser; see LuckyScriptTransformer.
 */
public final class LuckyScriptFix {

    /** Whether a bootstrap-only ScriptEngineManager finds JavaScript; null = not checked yet. */
    private static volatile Boolean bootstrapHasJs;

    private LuckyScriptFix() {
    }

    /**
     * Returns the loader Lucky Block asked for, unless it asked for null (the
     * bootstrap loader) and the bootstrap loader has no JavaScript engine. Then
     * it returns the loader that sees the game's class path, where lwjgl3ify's
     * Nashorn lives. On Java 8 the bootstrap loader always has Nashorn, so this
     * returns null and nothing changes.
     */
    public static ClassLoader loader(ClassLoader given) {
        if (given != null) {
            return given;
        }
        Boolean has = bootstrapHasJs;
        if (has == null) {
            try {
                has = new ScriptEngineManager(null).getEngineByName("JavaScript") != null;
            } catch (Throwable t) {
                has = Boolean.FALSE;
            }
            bootstrapHasJs = has;
            LogManager.getLogger("QuestForgeTweaks").info(has
                    ? "[QuestForgeTweaks] Lucky Block: the JDK has a JavaScript engine; using it unchanged."
                    : "[QuestForgeTweaks] Lucky Block: the JDK has no JavaScript engine; using the game class loader's.");
        }
        if (has) {
            return null;
        }
        ClassLoader own = LuckyScriptFix.class.getClassLoader();
        return own != null ? own : ClassLoader.getSystemClassLoader();
    }
}
