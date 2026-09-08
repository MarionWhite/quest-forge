package com.questforge.content;

import cpw.mods.fml.common.registry.GameRegistry;
import net.minecraft.block.Block;
import net.minecraft.block.material.Material;
import net.minecraft.item.ItemBlock;

public class ModBlocks {

    public static Block forgeBlock;

    /** Torchlight's invisible light source. Deliberately has no item form. */
    public static Block enchantLight;

    /** Plays the player's own music, positionally, from where it sits in the world. */
    public static Block jukebox;

    /** A wall case for a record: two tall, one wide, and barely any depth. */
    public static Block recordCase;
    public static Block towerSpeaker;

    public static void register() {
        forgeBlock = new BlockForge(Material.iron)
                .setBlockName("forge_block")
                .setBlockTextureName(QuestForgeContent.MODID + ":forge_block")
                .setHardness(5.0F)
                .setResistance(10.0F)
                .setStepSound(Block.soundTypePiston)
                .setCreativeTab(ModCreativeTab.INSTANCE);

        GameRegistry.registerBlock(forgeBlock, ItemBlock.class, "forge_block");

        // No ItemBlock: nobody should ever hold one of these, and no creative tab
        // entry for the same reason. It exists only to be placed by TorchlightUpkeep.
        enchantLight = new com.questforge.content.ench.BlockEnchantLight();
        GameRegistry.registerBlock(enchantLight, null, "enchant_light");

        // Borrows vanilla's jukebox texture, so there is no missing-texture checker
        // until this block gets art of its own.
        jukebox = new com.questforge.content.jukebox.BlockJukebox()
                .setBlockName("qf_jukebox")
                .setBlockTextureName("jukebox_side")
                .setHardness(2.0F)
                .setStepSound(Block.soundTypeWood)
                .setCreativeTab(ModCreativeTab.INSTANCE);

        GameRegistry.registerBlock(jukebox, ItemBlock.class, "qf_jukebox");
        GameRegistry.registerTileEntity(
                com.questforge.content.jukebox.TileEntityJukebox.class, "qf_jukebox");

        // Render type -1 means nothing draws it in the world but the tile entity
        // renderer -- and it also means the item form falls back to a flat sprite,
        // which is what this texture is for.
        recordCase = new com.questforge.content.jukebox.BlockRecordCase()
                .setBlockName("record_case")
                .setBlockTextureName(QuestForgeContent.MODID + ":record_case")
                .setCreativeTab(ModCreativeTab.INSTANCE);

        GameRegistry.registerBlock(recordCase, ItemBlock.class, "record_case");
        GameRegistry.registerTileEntity(
                com.questforge.content.jukebox.TileEntityRecordCase.class, "qf_record_case");

        towerSpeaker = new com.questforge.content.jukebox.BlockTowerSpeaker();
        GameRegistry.registerBlock(towerSpeaker, ItemBlock.class, "tower_speaker");
        GameRegistry.registerTileEntity(
                com.questforge.content.jukebox.TileEntityTowerSpeaker.class, "qf_tower_speaker");
    }
}
