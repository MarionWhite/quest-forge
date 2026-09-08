package com.questforge.content;

import net.minecraft.creativetab.CreativeTabs;
import net.minecraft.item.Item;

/** The creative-inventory tab everything in this mod appears under. */
public class ModCreativeTab extends CreativeTabs {

    public static final ModCreativeTab INSTANCE = new ModCreativeTab();

    private ModCreativeTab() {
        super(QuestForgeContent.MODID);
    }

    @Override
    public Item getTabIconItem() {
        return ModItems.forgeShard;
    }
}
