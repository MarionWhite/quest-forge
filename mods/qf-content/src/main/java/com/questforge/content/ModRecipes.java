package com.questforge.content;

import cpw.mods.fml.common.registry.GameRegistry;
import net.minecraft.init.Items;
import net.minecraft.item.Item;
import net.minecraft.item.ItemStack;
import net.minecraft.item.crafting.CraftingManager;
import net.minecraft.item.crafting.IRecipe;

public class ModRecipes {

    public static void register() {
        // 9 shards -> 1 block
        GameRegistry.addRecipe(
                new ItemStack(ModBlocks.forgeBlock),
                "SSS", "SSS", "SSS",
                'S', ModItems.forgeShard);

        // 1 block -> 9 shards
        GameRegistry.addShapelessRecipe(
                new ItemStack(ModItems.forgeShard, 9),
                ModBlocks.forgeBlock);

        // Something to actually obtain a shard with, so the mod is testable in survival
        GameRegistry.addShapelessRecipe(
                new ItemStack(ModItems.forgeShard, 2),
                Items.iron_ingot, Items.redstone);

        // Blank records, one per pressing. Cheap on purpose: the value is what
        // somebody cuts onto it, and handing one to a friend should not be an
        // expense. The metal only changes how it looks.
        blankRecord(0, Items.coal);
        blankRecord(1, Items.iron_ingot);
        blankRecord(2, Items.gold_ingot);
        blankRecord(3, Items.diamond);

        recordCase();
        speaker();
        tower();
        jukebox();
        logCount();
    }

    /**
     * The Quest Forge jukebox: a vanilla jukebox taught to play your own music, so it
     * costs the vanilla one (eight planks round a diamond) plus a blank record, the
     * cheapest pressing of the thing it exists to cut. Shapeless, because "a jukebox
     * and a record" is not an arrangement worth memorising. Any pressing works (the
     * metal only changes the look); vanilla's matcher ignores NBT, so a cut record is
     * taken too -- use a blank one.
     *
     * Decision 0004 (act1-04 A, 2026-10-25): quest 476 hands one out, and this recipe
     * is the second source, so a lost or second jukebox is a craft, not a quest.
     */
    private static void jukebox() {
        GameRegistry.addShapelessRecipe(
                new ItemStack(ModBlocks.jukebox),
                net.minecraft.init.Blocks.jukebox,
                new ItemStack(ModItems.record, 1,
                              net.minecraftforge.oredict.OreDictionary.WILDCARD_VALUE));
    }

    /**
     * One log line with how many recipes make this mod's items, so a headless server
     * boot proves a recipe registered without a client to open a crafting table in.
     */
    private static void logCount() {
        int ours = 0;
        for (Object o : CraftingManager.getInstance().getRecipeList()) {
            ItemStack out = ((IRecipe) o).getRecipeOutput();
            if (out == null || out.getItem() == null) continue;
            Object name = Item.itemRegistry.getNameForObject(out.getItem());
            if (name != null && String.valueOf(name).startsWith(QuestForgeContent.MODID + ":")) ours++;
        }
        QuestForgeContent.log.info("[recipes] " + ours + " recipes make " + QuestForgeContent.MODID
                + " items; the jukebox is a vanilla jukebox plus a blank record, shapeless");
    }

    /**
     * A tower speaker: a tall wooden cabinet, iron grille and drivers, and a note
     * block for the voice of it.
     *
     * Dearer than a JBL because it is the thing you build a room around, and it wants
     * to be a decision rather than something you fill a chest with.
     */
    private static void tower() {
        GameRegistry.addRecipe(
                new ItemStack(ModBlocks.towerSpeaker),
                "IWI", "INI", "IWI",
                'I', Items.iron_ingot,
                'W', new ItemStack(net.minecraft.init.Blocks.wool, 1,
                                   net.minecraftforge.oredict.OreDictionary.WILDCARD_VALUE),
                'N', net.minecraft.init.Blocks.noteblock);
    }

    /**
     * A JBL: a case, the drivers, and a redstone amplifier.
     *
     * Dearer than a record because it is the machine rather than the music, but
     * still short of a boss drop -- it is meant to be a thing you carry around, not
     * a trophy you own one of.
     */
    private static void speaker() {
        GameRegistry.addRecipe(
                new ItemStack(ModItems.speaker),
                "LWL", "NRN", "LWL",
                'L', Items.leather,
                // Any colour: the cloth ends up charcoal whatever went in, and
                // asking people to dye wool white first would be a step for nothing.
                'W', new ItemStack(net.minecraft.init.Blocks.wool, 1,
                                   net.minecraftforge.oredict.OreDictionary.WILDCARD_VALUE),
                'N', Items.iron_ingot,
                'R', Items.redstone);
    }

    /** A wall case: a wooden surround, a pane to see through, a brass plaque. */
    private static void recordCase() {
        GameRegistry.addRecipe(
                new ItemStack(ModBlocks.recordCase),
                "WGW", "WGW", "WBW",
                'W', net.minecraft.init.Blocks.planks,
                'G', net.minecraft.init.Blocks.glass_pane,
                'B', Items.gold_ingot);
    }

    /** One pressing: the metal, plus the sleeve and the groove. */
    private static void blankRecord(int meta, net.minecraft.item.Item metal) {
        GameRegistry.addShapelessRecipe(
                new ItemStack(ModItems.record, 1, meta),
                metal, Items.string, Items.redstone);
    }
}
