package com.questforge.content.ench;

import java.util.List;
import java.util.Random;

import net.minecraft.creativetab.CreativeTabs;
import net.minecraft.entity.player.EntityPlayer;
import net.minecraft.item.Item;
import net.minecraft.item.ItemStack;
import net.minecraft.util.EnumChatFormatting;
import net.minecraft.util.StatCollector;

import com.questforge.content.ModCreativeTab;
import com.questforge.content.QuestForgeContent;

import cpw.mods.fml.relauncher.Side;
import cpw.mods.fml.relauncher.SideOnly;

/**
 * An enchantment book. Drag it onto an item to apply it.
 *
 * Success and destroy chances are rolled into each book when it is created, from
 * the ranges its rarity allows -- so two books of the same enchantment are not
 * interchangeable, and a good roll is a real find.
 */
public class ItemEnchantBook extends Item {

    public ItemEnchantBook() {
        setUnlocalizedName("enchant_book");
        setTextureName("minecraft:book_enchanted");   // placeholder art
        setCreativeTab(ModCreativeTab.INSTANCE);
        setMaxStackSize(1);                            // each carries its own rolls
        setHasSubtypes(true);
    }

    @Override
    public String getItemStackDisplayName(ItemStack stack) {
        QFEnchantment ench = BookNBT.getEnchant(stack);
        if (ench == null) return EnumChatFormatting.OBFUSCATED + "Ruined Tome";

        int level = BookNBT.getLevel(stack);
        String name = StatCollector.translateToLocal(ench.getName());
        return ench.rarity.colour + name + (level > 1 ? " " + roman(level) : "");
    }

    @Override
    @SuppressWarnings({ "unchecked", "rawtypes" })
    @SideOnly(Side.CLIENT)
    public void addInformation(ItemStack stack, EntityPlayer player, List list, boolean advanced) {
        QFEnchantment ench = BookNBT.getEnchant(stack);
        if (ench == null) {
            list.add(EnumChatFormatting.RED + "This book names an enchantment that no longer exists.");
            return;
        }

        list.add(ench.rarity.displayName());
        list.add(EnumChatFormatting.GRAY + "Applies to: " + ench.category.describe());
        list.add("");

        int success = BookNBT.getSuccess(stack);
        int destroy = BookNBT.getDestroy(stack);

        list.add(colourForSuccess(success) + "Success: " + success + "%");
        list.add(colourForDestroy(destroy) + "Destroy: " + destroy + "%");
        if (BookNBT.hasWard(stack)) {
            list.add(EnumChatFormatting.LIGHT_PURPLE + "Warded");
        }
        list.add("");
        list.add(EnumChatFormatting.DARK_GRAY + "Drag onto an item to apply.");
    }

    /**
     * One book per enchantment in creative, at max level and guaranteed.
     *
     * Creative books are a testing tool, not a sample of the real thing: rolling
     * odds into them would mean the only way to try an enchantment out is to gamble
     * for it. The rolled ranges belong to books that come from loot, which is where
     * the RNG lives.
     */
    @Override
    @SuppressWarnings({ "unchecked", "rawtypes" })
    @SideOnly(Side.CLIENT)
    public void getSubItems(Item item, CreativeTabs tab, List list) {
        for (QFEnchantment ench : QFEnchantments.all()) {
            if (ench == null) continue;
            ItemStack stack = new ItemStack(item, 1, 0);
            BookNBT.create(stack, ench, ench.getMaxLevel(), 100, 0);
            list.add(stack);
        }
    }

    /** Convenience for loot and quest rewards. */
    public static ItemStack roll(QFEnchantment ench, int level, Random rand) {
        ItemStack stack = new ItemStack(QuestForgeContent.enchantBook, 1, 0);
        return BookNBT.create(stack, ench, level, rand);
    }

    private static EnumChatFormatting colourForSuccess(int pct) {
        if (pct >= 75) return EnumChatFormatting.GREEN;
        if (pct >= 50) return EnumChatFormatting.YELLOW;
        return EnumChatFormatting.RED;
    }

    private static EnumChatFormatting colourForDestroy(int pct) {
        if (pct <= 5) return EnumChatFormatting.GREEN;
        if (pct <= 20) return EnumChatFormatting.YELLOW;
        return EnumChatFormatting.RED;
    }

    private static String roman(int n) {
        switch (n) {
            case 1: return "I";
            case 2: return "II";
            case 3: return "III";
            case 4: return "IV";
            case 5: return "V";
            default: return String.valueOf(n);
        }
    }
}
