package com.questforge;

import java.util.Map;

import cpw.mods.fml.relauncher.IFMLLoadingPlugin;

/**
 * Forge coremod entry point for QuestForgeTweaks.
 *
 * Registers a single class transformer that makes BetterQuesting's quest
 * buttons clickable even when the quest is LOCKED, so players can read a
 * quest's description ahead of time. Completion gating is untouched and
 * still enforced server-side.
 *
 * SortingIndex is above 1000 so this runs after FML's deobfuscation
 * transformer. BetterQuesting ships unobfuscated, but ordering after the
 * standard transformers is the safe default.
 */
@IFMLLoadingPlugin.MCVersion("1.7.10")
@IFMLLoadingPlugin.Name("QuestForgeTweaks")
@IFMLLoadingPlugin.SortingIndex(1001)
@IFMLLoadingPlugin.TransformerExclusions({
        // One entry per class, never the package. Exclusions are prefix
        // matches over every transformer in the game -- FML's @SideOnly
        // stripper included -- and "com.questforge." also swallowed
        // qf-content and qf-commands, which are ordinary mods that need that
        // stripping on a dedicated server. Each name also covers its own
        // inner classes (the $SafeClassWriters). A class added to this jar
        // needs adding here too.
        "com.questforge.QuestForgeCore",
        "com.questforge.PanelButtonQuestTransformer",
        "com.questforge.MusicTickerTransformer",
        "com.questforge.GraveBeamTransformer",
        "com.questforge.GraveBaublesTransformer",
        "com.questforge.GlErrorTransformer",
        "com.questforge.ChunkCleanTransformer",
        "com.questforge.MorphOptifineTransformer",
        "com.questforge.MmmScanTransformer",
        "com.questforge.LuckyScriptTransformer",
        // Not transformers, but loaded from code patched into GraveStones and
        // OptiFine; there is nothing in them any transformer needs to touch.
        "com.questforge.ShaderState",
        "com.questforge.GlErrorLog",
        // Called from Morph's patched classes.
        "com.questforge.MorphFix",
        // Called from LittleMaidMob's patched model scan.
        "com.questforge.MmmScanGuard",
        // Called from Lucky Block's patched ExpressionParser.
        "com.questforge.LuckyScriptFix"
})
public class QuestForgeCore implements IFMLLoadingPlugin {

    @Override
    public String[] getASMTransformerClass() {
        return new String[] {
                "com.questforge.PanelButtonQuestTransformer",
                "com.questforge.MusicTickerTransformer",
                "com.questforge.GraveBeamTransformer",
                "com.questforge.GraveBaublesTransformer",
                "com.questforge.GlErrorTransformer",
                "com.questforge.ChunkCleanTransformer",
                "com.questforge.MorphOptifineTransformer",
                "com.questforge.MmmScanTransformer",
                "com.questforge.LuckyScriptTransformer"
        };
    }

    @Override
    public String getModContainerClass() {
        // A mod entry with a real version, so packs can be compared; see the class.
        return "com.questforge.QuestForgeTweaksContainer";
    }

    @Override
    public String getSetupClass() {
        return null;
    }

    @Override
    public void injectData(Map<String, Object> data) {
        // nothing needed
    }

    @Override
    public String getAccessTransformerClass() {
        return null;
    }
}
