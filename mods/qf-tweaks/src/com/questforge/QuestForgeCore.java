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
        // Not a transformer, but loaded from code patched into GraveStones;
        // there is nothing in it any transformer needs to touch.
        "com.questforge.ShaderState"
})
public class QuestForgeCore implements IFMLLoadingPlugin {

    @Override
    public String[] getASMTransformerClass() {
        return new String[] {
                "com.questforge.PanelButtonQuestTransformer",
                "com.questforge.MusicTickerTransformer",
                "com.questforge.GraveBeamTransformer",
                "com.questforge.GraveBaublesTransformer"
        };
    }

    @Override
    public String getModContainerClass() {
        return null;
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
