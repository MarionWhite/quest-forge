package com.questforge.content.ench;

import java.util.List;

import net.minecraft.client.renderer.texture.IIconRegister;
import net.minecraft.creativetab.CreativeTabs;
import net.minecraft.entity.player.EntityPlayer;
import net.minecraft.item.Item;
import net.minecraft.item.ItemStack;
import net.minecraft.util.ChatComponentText;
import net.minecraft.util.EnumChatFormatting;
import net.minecraft.util.IIcon;
import net.minecraft.world.World;

import com.questforge.content.ModCreativeTab;

import cpw.mods.fml.relauncher.Side;
import cpw.mods.fml.relauncher.SideOnly;

/**
 * A sealed tome. Right-click to open it into a random book of its rarity.
 *
 * This exists because both of the ways a player is meant to get books hand out a
 * *fixed* ItemStack: chest generation in 1.7.10 copies a template stack, and
 * BetterQuesting rewards are stored stacks. Neither can roll NBT at the moment it
 * is given out, so a book placed that way would be the same book every time.
 *
 * A sealed tome has no NBT to fix. It is one stackable item per rarity, safe to
 * drop into any loot table or quest reward, and the roll happens in the player's
 * hand -- which also makes opening one an event rather than an inventory update.
 */
public class ItemSealedTome extends Item {

    private static final String[] ICONS = {
        "book_normal", "book_normal", "book_writable", "book_written", "book_enchanted"
    };

    @SideOnly(Side.CLIENT)
    private IIcon[] icons;

    public ItemSealedTome() {
        setUnlocalizedName("qf_sealed_tome");
        setCreativeTab(ModCreativeTab.INSTANCE);
        setHasSubtypes(true);
        setMaxDamage(0);
    }

    private static Rarity rarityOf(ItemStack stack) {
        int meta = stack.getItemDamage();
        Rarity[] all = Rarity.values();
        return (meta < 0 || meta >= all.length) ? Rarity.COMMON : all[meta];
    }

    @Override
    public String getItemStackDisplayName(ItemStack stack) {
        Rarity rarity = rarityOf(stack);
        return rarity.colour + "Sealed Tome" + EnumChatFormatting.GRAY
                + " (" + rarity.displayName() + EnumChatFormatting.GRAY + ")";
    }

    @Override
    @SuppressWarnings({ "unchecked", "rawtypes" })
    @SideOnly(Side.CLIENT)
    public void addInformation(ItemStack stack, EntityPlayer player, List list, boolean advanced) {
        Rarity rarity = rarityOf(stack);
        list.add(EnumChatFormatting.GRAY + "Right-click to open.");
        list.add(EnumChatFormatting.DARK_GRAY + "Contains one "
                + rarity.displayName() + EnumChatFormatting.DARK_GRAY + " enchantment.");
    }

    @Override
    public ItemStack onItemRightClick(ItemStack stack, World world, EntityPlayer player) {
        if (world.isRemote) return stack;

        ItemStack book = EnchantLoot.rollBook(rarityOf(stack), world.rand);
        if (book == null) {
            player.addChatMessage(new ChatComponentText(EnumChatFormatting.RED
                    + "The tome is empty. No enchantments of that rarity are registered."));
            return stack;
        }

        stack.stackSize--;

        if (!player.inventory.addItemStackToInventory(book)) {
            player.entityDropItem(book, 0.5F);
        }
        player.inventory.markDirty();

        world.playSoundAtEntity(player, "random.levelup", 0.6F, 1.4F);
        player.addChatMessage(new ChatComponentText(EnumChatFormatting.GRAY + "The seal breaks: "
                + book.getDisplayName()));

        return stack.stackSize <= 0 ? null : stack;
    }

    @Override
    @SuppressWarnings({ "unchecked", "rawtypes" })
    @SideOnly(Side.CLIENT)
    public void getSubItems(Item item, CreativeTabs tab, List list) {
        for (int meta = 0; meta < Rarity.values().length; meta++) {
            list.add(new ItemStack(item, 1, meta));
        }
    }

    @Override
    @SideOnly(Side.CLIENT)
    public void registerIcons(IIconRegister register) {
        icons = new IIcon[ICONS.length];
        for (int i = 0; i < ICONS.length; i++) {
            icons[i] = register.registerIcon(ICONS[i]);
        }
    }

    @Override
    @SideOnly(Side.CLIENT)
    public IIcon getIconFromDamage(int meta) {
        return icons[(meta < 0 || meta >= icons.length) ? 0 : meta];
    }
}
