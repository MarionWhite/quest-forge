package com.questforge.content;

import cpw.mods.fml.common.registry.GameRegistry;
import net.minecraft.item.Item;

public class ModItems {

    public static Item forgeShard;

    /** Magic Dust, Ward Scroll, Binding Scroll and Solvent, as metadata 0-3. */
    public static Item consumable;

    /** One per rarity, as metadata 0-4. Opens into a random book of that rarity. */
    public static Item sealedTome;

    /** A playlist you can hold: cut at a jukebox, played back at any other. */
    public static Item record;
    public static Item speaker;

    public static void register() {
        forgeShard = new Item()
                .setUnlocalizedName("forge_shard")
                .setTextureName(QuestForgeContent.MODID + ":forge_shard")
                .setCreativeTab(ModCreativeTab.INSTANCE);

        // The registry name is what shows up in /give and in CraftTweaker scripts
        // as qfcontent:forge_shard -- keep it stable once a world has used it.
        GameRegistry.registerItem(forgeShard, "forge_shard");

        consumable = new com.questforge.content.ench.ItemConsumable();
        GameRegistry.registerItem(consumable, "consumable");

        sealedTome = new com.questforge.content.ench.ItemSealedTome();
        GameRegistry.registerItem(sealedTome, "sealed_tome");

        record = new com.questforge.content.jukebox.ItemVinyl();
        GameRegistry.registerItem(record, "record");

        speaker = new com.questforge.content.jukebox.ItemSpeaker();
        GameRegistry.registerItem(speaker, "jbl");
    }
}
