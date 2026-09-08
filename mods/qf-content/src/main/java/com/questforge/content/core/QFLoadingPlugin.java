package com.questforge.content.core;

import java.util.Map;

import cpw.mods.fml.relauncher.IFMLLoadingPlugin;

/**
 * Coremod entry point.
 *
 * Exists for exactly one reason: Forge 1.7.10 has no slot-click or mouse-input
 * event, so there is no way to detect "player dropped item A onto item B" from
 * ordinary mod code. Applying enchantment books by drag-and-drop requires
 * intercepting Container.slotClick, which requires bytecode.
 *
 * A second transformer was added later for Reach: 1.7.10 has no reach attribute,
 * so melee and mining range are hardcoded constants that also need bytecode.
 *
 * SortingIndex above 1000 so this runs after FML's deobfuscation transformer,
 * matching the convention used by the pack's existing QuestForgeTweaks coremod.
 */
@IFMLLoadingPlugin.MCVersion("1.7.10")
@IFMLLoadingPlugin.Name("QuestForgeContentCore")
@IFMLLoadingPlugin.SortingIndex(1001)
@IFMLLoadingPlugin.TransformerExclusions({ "com.questforge.content.core." })
public class QFLoadingPlugin implements IFMLLoadingPlugin {

    @Override
    public String[] getASMTransformerClass() {
        return new String[] {
                "com.questforge.content.core.ContainerTransformer",
                "com.questforge.content.core.ReachTransformer",
                "com.questforge.content.core.OreGenTransformer"
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
    public void injectData(Map<String, Object> data) {}

    @Override
    public String getAccessTransformerClass() {
        return null;
    }
}
