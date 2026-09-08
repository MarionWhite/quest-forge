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
@IFMLLoadingPlugin.TransformerExclusions({ "com.questforge." })
public class QuestForgeCore implements IFMLLoadingPlugin {

    @Override
    public String[] getASMTransformerClass() {
        return new String[] {
                "com.questforge.PanelButtonQuestTransformer",
                "com.questforge.MusicTickerTransformer"
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
