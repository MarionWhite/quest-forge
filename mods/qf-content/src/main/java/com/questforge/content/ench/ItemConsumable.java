package com.questforge.content.ench;

import java.util.List;

import net.minecraft.client.renderer.texture.IIconRegister;
import net.minecraft.creativetab.CreativeTabs;
import net.minecraft.entity.player.EntityPlayer;
import net.minecraft.item.Item;
import net.minecraft.item.ItemStack;
import net.minecraft.util.EnumChatFormatting;
import net.minecraft.util.IIcon;

import com.questforge.content.ModCreativeTab;

import cpw.mods.fml.relauncher.Side;
import cpw.mods.fml.relauncher.SideOnly;

/**
 * The four things that bend the odds. All are used the same way the books are:
 * pick one up and drop it on what it should affect.
 *
 * One item with four metadata values rather than four registered items, so that
 * loot tables, quest rewards and recipes all deal with a single registry name.
 */
public class ItemConsumable extends Item {

    public static final int MAGIC_DUST = 0;
    public static final int WARD_SCROLL = 1;
    public static final int BINDING_SCROLL = 2;
    public static final int SOLVENT = 3;

    public static final int COUNT = 4;

    private static final String[] NAMES = {
        "magic_dust", "ward_scroll", "binding_scroll", "solvent"
    };

    /** Placeholder art, borrowed from vanilla until there is real art. */
    private static final String[] ICONS = {
        "glowstone_dust", "paper", "book_normal", "potion_bottle_drinkable"
    };

    private static final String[] TOOLTIPS = {
        "Drop on a tome to raise its success chance by 5%.",
        "Drop on a tome. One shattering will be absorbed.",
        "Drop on a tome. It will not fail.",
        "Drop on an enchanted item to dissolve one custom enchantment."
    };

    @SideOnly(Side.CLIENT)
    private IIcon[] icons;

    public ItemConsumable() {
        setUnlocalizedName("qf_consumable");
        setCreativeTab(ModCreativeTab.INSTANCE);
        setHasSubtypes(true);
        setMaxDamage(0);
    }

    @Override
    public String getUnlocalizedName(ItemStack stack) {
        return "item.qf_" + NAMES[clamp(stack.getItemDamage())];
    }

    @Override
    @SuppressWarnings({ "unchecked", "rawtypes" })
    @SideOnly(Side.CLIENT)
    public void addInformation(ItemStack stack, EntityPlayer player, List list, boolean advanced) {
        list.add(EnumChatFormatting.GRAY + TOOLTIPS[clamp(stack.getItemDamage())]);
    }

    @Override
    @SuppressWarnings({ "unchecked", "rawtypes" })
    @SideOnly(Side.CLIENT)
    public void getSubItems(Item item, CreativeTabs tab, List list) {
        for (int meta = 0; meta < COUNT; meta++) {
            list.add(new ItemStack(item, 1, meta));
        }
    }

    @Override
    @SideOnly(Side.CLIENT)
    public void registerIcons(IIconRegister register) {
        icons = new IIcon[COUNT];
        for (int meta = 0; meta < COUNT; meta++) {
            icons[meta] = register.registerIcon(ICONS[meta]);
        }
    }

    @Override
    @SideOnly(Side.CLIENT)
    public IIcon getIconFromDamage(int meta) {
        return icons[clamp(meta)];
    }

    /** Metadata arrives from NBT and from commands, so it is never trusted raw. */
    private static int clamp(int meta) {
        return (meta < 0 || meta >= COUNT) ? 0 : meta;
    }
}
