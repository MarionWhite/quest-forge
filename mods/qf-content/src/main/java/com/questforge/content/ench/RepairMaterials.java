package com.questforge.content.ench;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import net.minecraft.init.Items;
import net.minecraft.item.Item;
import net.minecraft.item.ItemStack;
import net.minecraftforge.oredict.OreDictionary;

/**
 * Works out what repairs a given tool, for Eco-Friendly.
 *
 * The obvious approach -- read the vanilla ToolMaterial enum -- only works for
 * gear built on one of the five vanilla materials, which in a 113-mod pack is a
 * small minority. So this asks the item itself instead, through Forge's
 * {@code Item.getIsRepairable(ItemStack, ItemStack)}, which every modded tool
 * implements because the anvil depends on it.
 *
 * The candidate list comes from the ore dictionary: every ingot, gem and nugget
 * any mod registered, plus a few vanilla staples that are not in the dictionary.
 * That means a mod's own custom material is found without knowing anything about
 * that mod.
 *
 * The answer is cached per Item, so the scan happens once per tool type rather
 * than once per broken tool.
 */
public class RepairMaterials {

    private static final Map<Item, ItemStack> CACHE = new HashMap<Item, ItemStack>();
    private static List<ItemStack> candidates;

    /** The material that repairs this tool, or null if nothing recognised does. */
    public static ItemStack forTool(ItemStack tool) {
        if (tool == null || tool.getItem() == null) return null;

        Item item = tool.getItem();
        if (CACHE.containsKey(item)) {
            ItemStack cached = CACHE.get(item);
            return cached == null ? null : cached.copy();
        }

        ItemStack found = search(tool);
        CACHE.put(item, found);
        return found == null ? null : found.copy();
    }

    private static ItemStack search(ItemStack tool) {
        for (ItemStack candidate : candidates()) {
            try {
                if (tool.getItem().getIsRepairable(tool, candidate)) {
                    return candidate;
                }
            } catch (Throwable t) {
                // A modded item that throws from getIsRepairable is not a reason to
                // give up on the rest of the list.
            }
        }
        return null;
    }

    /** Every plausible repair material, gathered once. */
    private static List<ItemStack> candidates() {
        if (candidates != null) return candidates;

        candidates = new ArrayList<ItemStack>();

        for (String name : OreDictionary.getOreNames()) {
            if (name == null) continue;
            if (!name.startsWith("ingot") && !name.startsWith("gem")
                    && !name.startsWith("nugget") && !name.startsWith("plate")) {
                continue;
            }
            for (ItemStack stack : OreDictionary.getOres(name)) {
                if (stack != null && stack.getItem() != null) candidates.add(stack);
            }
        }

        // Vanilla materials that are not ore-dictionary entries.
        addVanilla(Items.leather);
        addVanilla(Items.stick);
        addVanilla(Items.flint);
        addVanilla(Item.getItemFromBlock(net.minecraft.init.Blocks.planks));
        addVanilla(Item.getItemFromBlock(net.minecraft.init.Blocks.cobblestone));

        return candidates;
    }

    private static void addVanilla(Item item) {
        if (item != null) candidates.add(new ItemStack(item, 1, 0));
    }
}
