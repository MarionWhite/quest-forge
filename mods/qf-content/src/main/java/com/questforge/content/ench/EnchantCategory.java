package com.questforge.content.ench;

import java.util.HashSet;
import java.util.Set;

import net.minecraft.item.Item;
import net.minecraft.item.ItemArmor;
import net.minecraft.item.ItemAxe;
import net.minecraft.item.ItemBow;
import net.minecraft.item.ItemPickaxe;
import net.minecraft.item.ItemSpade;
import net.minecraft.item.ItemStack;
import net.minecraft.item.ItemSword;
import net.minecraft.item.ItemTool;

import cpw.mods.fml.common.registry.GameRegistry;

/**
 * What an enchantment will accept.
 *
 * This is the whole answer to "works on modded items too". Enchantment.canApply
 * normally delegates to EnumEnchantmentType.canEnchantItem, which only knows about
 * vanilla item classes. Overriding it with this lets us accept anything.
 *
 * Two identification strategies are used together, because neither is sufficient
 * on its own in a 113-mod pack:
 *
 *   instanceof   catches everything built on the vanilla classes, which is most
 *                modded gear.
 *   tool classes catches tools that extend ItemTool directly and declare
 *                themselves through Forge's getToolClasses instead -- common for
 *                multi-tools and for mods with their own tool hierarchy.
 *
 * Armor slots come from ItemArmor.armorType (0 helmet, 1 chestplate, 2 leggings,
 * 3 boots), which modded armor sets correctly because vanilla rendering depends
 * on it.
 *
 * The config whitelist and blacklist remain the final word for gear that fits
 * neither route -- Battlegear, ICBM and MCHeli weapons are the likely holdouts.
 */
public enum EnchantCategory {

    // --- Broad buckets, for enchantments that genuinely go anywhere ---------

    /** Swords and axes -- anything a player would swing. */
    WEAPON,
    /** Bows and other ranged weapons. */
    BOW,
    /** Pickaxes, shovels, axes -- anything that breaks blocks. */
    TOOL,
    /** Any armor piece. */
    ARMOR,
    /** Anything enchantable at all. */
    ANY,

    // --- Precise buckets ---------------------------------------------------

    /** Swords only. Excludes axes, unlike WEAPON. */
    SWORD,
    /** Axes, whether they are being used as a tool or a weapon. */
    AXE,
    PICKAXE,
    SHOVEL,
    /** Pickaxes and shovels: the two things you dig with, but not axes. */
    DIGGER,

    HELMET,
    CHESTPLATE,
    LEGGINGS,
    BOOTS;

    /** Registry names ("modid:item_name") force-added to this category via config. */
    private final Set<String> whitelist = new HashSet<String>();
    /** Registry names force-removed from this category via config. */
    private final Set<String> blacklist = new HashSet<String>();

    public void whitelist(String registryName) {
        whitelist.add(registryName);
    }

    public void blacklist(String registryName) {
        blacklist.add(registryName);
    }

    public boolean accepts(ItemStack stack) {
        if (stack == null || stack.getItem() == null) return false;
        Item item = stack.getItem();

        String name = nameOf(item);
        if (name != null) {
            if (blacklist.contains(name)) return false;
            if (whitelist.contains(name)) return true;
        }

        switch (this) {
            case WEAPON:
                return item instanceof ItemSword || isAxe(item, stack);
            case BOW:
                return item instanceof ItemBow;
            case TOOL:
                return item instanceof ItemTool || item instanceof ItemPickaxe
                        || item instanceof ItemSpade || item instanceof ItemAxe
                        || hasToolClass(item, stack, "pickaxe")
                        || hasToolClass(item, stack, "shovel")
                        || hasToolClass(item, stack, "axe");
            case ARMOR:
                return item instanceof ItemArmor;
            case ANY:
                return item instanceof ItemSword || item instanceof ItemTool
                        || item instanceof ItemArmor || item instanceof ItemBow;

            case SWORD:
                return item instanceof ItemSword;
            case AXE:
                return isAxe(item, stack);
            case PICKAXE:
                return isPickaxe(item, stack);
            case SHOVEL:
                return isShovel(item, stack);
            case DIGGER:
                return isPickaxe(item, stack) || isShovel(item, stack);

            case HELMET:
                return isArmorSlot(item, 0);
            case CHESTPLATE:
                return isArmorSlot(item, 1);
            case LEGGINGS:
                return isArmorSlot(item, 2);
            case BOOTS:
                return isArmorSlot(item, 3);

            default:
                return false;
        }
    }

    /** A human-readable description, used in the book tooltip. */
    public String describe() {
        switch (this) {
            case WEAPON:     return "swords and axes";
            case BOW:        return "bows";
            case TOOL:       return "tools";
            case ARMOR:      return "armor";
            case ANY:        return "any gear";
            case SWORD:      return "swords";
            case AXE:        return "axes";
            case PICKAXE:    return "pickaxes";
            case SHOVEL:     return "shovels";
            case DIGGER:     return "pickaxes and shovels";
            case HELMET:     return "helmets";
            case CHESTPLATE: return "chestplates";
            case LEGGINGS:   return "leggings";
            case BOOTS:      return "boots";
            default:         return name().toLowerCase();
        }
    }

    private static boolean isPickaxe(Item item, ItemStack stack) {
        return item instanceof ItemPickaxe || hasToolClass(item, stack, "pickaxe");
    }

    private static boolean isShovel(Item item, ItemStack stack) {
        return item instanceof ItemSpade || hasToolClass(item, stack, "shovel");
    }

    private static boolean isAxe(Item item, ItemStack stack) {
        return item instanceof ItemAxe || hasToolClass(item, stack, "axe");
    }

    private static boolean isArmorSlot(Item item, int slot) {
        return item instanceof ItemArmor && ((ItemArmor) item).armorType == slot;
    }

    /**
     * Forge's own answer to "what is this tool for". A tool that extends ItemTool
     * directly is invisible to instanceof but still declares itself here.
     */
    private static boolean hasToolClass(Item item, ItemStack stack, String toolClass) {
        try {
            Set<String> classes = item.getToolClasses(stack);
            return classes != null && classes.contains(toolClass);
        } catch (Throwable t) {
            // A modded item can throw from getToolClasses. Fall back to instanceof,
            // which the caller has already tried.
            return false;
        }
    }

    private static String nameOf(Item item) {
        GameRegistry.UniqueIdentifier id = GameRegistry.findUniqueIdentifierFor(item);
        return id == null ? null : id.modId + ":" + id.name;
    }
}
