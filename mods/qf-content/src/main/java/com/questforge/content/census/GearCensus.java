package com.questforge.content.census;

import java.io.File;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.Set;

import net.minecraft.entity.EntityLivingBase;
import net.minecraft.entity.SharedMonsterAttributes;
import net.minecraft.entity.ai.attributes.AttributeModifier;
import net.minecraft.item.Item;
import net.minecraft.item.ItemArmor;
import net.minecraft.item.ItemAxe;
import net.minecraft.item.ItemBow;
import net.minecraft.item.ItemPickaxe;
import net.minecraft.item.ItemSpade;
import net.minecraft.item.ItemStack;
import net.minecraft.item.ItemSword;
import net.minecraft.item.ItemTool;
import net.minecraft.util.DamageSource;

import net.minecraftforge.common.ISpecialArmor;

import com.google.common.collect.Multimap;

import com.questforge.content.QuestForgeContent;

/**
 * Every wearable and swingable thing in the pack, measured rather than read.
 *
 * The distinction matters. An earlier pass at this pulled armour numbers out of
 * mod jars with javap, which gets the constructor arguments right and everything
 * else wrong -- most importantly it cannot see {@link ISpecialArmor}, which
 * replaces the armour formula outright for the item that implements it. Seven
 * mods in this pack do (ProjectE's Dark and Red Matter, the Legends hero suits,
 * Witchery's vampire and hunter clothes, Battlegear knight armour, Mutant
 * Creatures' skeleton armour, Transformers), and for those the armour-point
 * number a static reader produces is not merely imprecise, it is irrelevant.
 *
 * So this asks the items themselves, in a loaded game, with the pack's own
 * configuration applied.
 *
 * Three files come out:
 *   gear         -- one row per gear stack, with whatever measurements apply
 *   specialarmor -- absorption curve for ISpecialArmor pieces, sampled across
 *                   the range of hits this pack's mobs actually deal
 *   items-other  -- everything that did NOT classify as gear, name and class
 *                   only. This one exists to be read by a human: a weapon that
 *                   deals its damage from inside hitEntity rather than through
 *                   an attribute modifier is invisible to every automated check,
 *                   and the only way to catch it is to look at the list.
 */
public final class GearCensus {

    private GearCensus() {}

    /**
     * Hit sizes to sample ISpecialArmor at. Chosen to bracket the pack: an
     * ordinary mob swing, a strong one, and the OreSpawn boss range, whose
     * damage is measured separately by {@link MobCensus} rather than assumed
     * here -- these are only sample points, so being approximately right is
     * enough.
     */
    private static final double[] PROBE_DAMAGE = { 1, 4, 10, 20, 40, 80, 175, 225, 350, 700, 1400 };

    private static final String ATTACK_DAMAGE =
            SharedMonsterAttributes.attackDamage.getAttributeUnlocalizedName();

    public static void run(File configDir, EntityLivingBase probe) {
        CensusFile gear = new CensusFile(configDir, "gear",
                "Armour and weapons: armour points, durability, absorption and attack damage.",
                new String[] {
                    "registry_name", "meta", "class", "display_name", "kind",
                    "armor_slot", "armor_points", "durability", "enchantability", "armor_material",
                    "special_armor", "attack_dmg_add", "attack_dmg_mult", "player_attack_total",
                    "tool_classes", "harvest_levels", "dig_speed", "max_stack", "damageable"
                });

        CensusFile special = new CensusFile(configDir, "specialarmor",
                "ISpecialArmor absorption, sampled across hit sizes. These items ignore armour points.",
                new String[] {
                    "registry_name", "meta", "slot", "probe_damage",
                    "absorb_ratio", "absorb_max", "priority", "armor_display", "error"
                });

        CensusFile other = new CensusFile(configDir, "items-other",
                "Items that did not classify as gear. Read this list: a weapon that deals damage "
              + "from inside hitEntity has no attribute modifier and will be sitting in here.",
                new String[] { "registry_name", "class", "display_name", "max_stack", "damageable" });

        int gearRows = 0, otherRows = 0, failed = 0;

        Iterator<?> it = Item.itemRegistry.iterator();
        while (it.hasNext()) {
            Object o = it.next();
            if (!(o instanceof Item)) continue;
            Item item = (Item) o;

            String name;
            try {
                name = String.valueOf(Item.itemRegistry.getNameForObject(item));
            } catch (Throwable t) {
                name = "?" + item.getClass().getName();
            }

            List<ItemStack> stacks = subItems(item);
            boolean anyGear = false;

            for (int i = 0; i < stacks.size(); i++) {
                ItemStack stack = stacks.get(i);
                try {
                    if (writeGearRow(gear, special, name, stack, probe)) anyGear = true;
                } catch (Throwable t) {
                    failed++;
                    QuestForgeContent.log.warn("[census] gear row failed for " + name + ": " + t);
                }
            }

            if (anyGear) {
                gearRows++;
            } else {
                otherRows++;
                other.row(name, item.getClass().getName(), displayName(stacks.isEmpty() ? null : stacks.get(0)),
                        item.getItemStackLimit(), item.isDamageable());
            }
        }

        gear.close();
        special.close();
        other.close();

        QuestForgeContent.log.info("[census] gear: " + gear.rows() + " rows over " + gearRows
                + " items, " + special.rows() + " special-armour samples, "
                + otherRows + " non-gear items, " + failed + " failures.");
    }

    /** @return true if this stack classified as gear. */
    private static boolean writeGearRow(CensusFile gear, CensusFile special,
            String name, ItemStack stack, EntityLivingBase probe) {

        Item item = stack.getItem();

        boolean isArmour = item instanceof ItemArmor;
        boolean isSpecial = item instanceof ISpecialArmor;
        boolean isSword = item instanceof ItemSword;
        boolean isBow = item instanceof ItemBow;
        boolean isTool = item instanceof ItemTool;

        Set<String> toolClasses = null;
        try {
            toolClasses = item.getToolClasses(stack);
        } catch (Throwable ignored) {}

        // Attack damage as the game computes it: the sum of the item's
        // attackDamage attribute modifiers. This is exactly what
        // EntityPlayer.attackTargetEntityWithCurrentItem reads, so a weapon whose
        // damage arrives any other way deliberately does not land here.
        double add = 0.0D, mult = 0.0D;
        boolean sawAttack = false;
        try {
            Multimap map = item.getAttributeModifiers(stack);
            if (map != null) {
                Collection<?> mods = map.get(ATTACK_DAMAGE);
                if (mods != null) {
                    for (Object m : mods) {
                        AttributeModifier am = (AttributeModifier) m;
                        sawAttack = true;
                        if (am.getOperation() == 0) add += am.getAmount();
                        else mult += am.getAmount();
                    }
                }
            }
        } catch (Throwable ignored) {}

        boolean gearish = isArmour || isSpecial || isSword || isBow || isTool || sawAttack
                || (toolClasses != null && !toolClasses.isEmpty());
        if (!gearish) return false;

        String kind = isArmour || isSpecial ? "ARMOR"
                : isSword ? "SWORD"
                : isBow ? "BOW"
                : item instanceof ItemAxe ? "AXE"
                : item instanceof ItemPickaxe ? "PICKAXE"
                : item instanceof ItemSpade ? "SHOVEL"
                : isTool ? "TOOL"
                : sawAttack ? "WEAPON_OTHER"
                : "TOOL_OTHER";

        int slot = -1, points = -1, ench = -1;
        String material = "";
        if (isArmour) {
            ItemArmor armour = (ItemArmor) item;
            slot = armour.armorType;
            points = armour.damageReduceAmount;
            try {
                ench = armour.getItemEnchantability();
            } catch (Throwable ignored) {}
            try {
                material = armour.getArmorMaterial() == null ? "" : armour.getArmorMaterial().name();
            } catch (Throwable ignored) {}
        } else {
            try {
                ench = item.getItemEnchantability();
            } catch (Throwable ignored) {}
        }

        // Base player attack damage is 1.0 (EntityPlayer.applyEntityAttributes),
        // and an operation-0 modifier adds to it.
        double playerTotal = sawAttack ? (1.0D + add) * (1.0D + mult) : 0.0D;

        String harvest = "";
        String dig = "";
        if (toolClasses != null && !toolClasses.isEmpty()) {
            StringBuilder h = new StringBuilder();
            for (String tc : toolClasses) {
                if (h.length() > 0) h.append(',');
                int lvl = -1;
                try {
                    lvl = item.getHarvestLevel(stack, tc);
                } catch (Throwable ignored) {}
                h.append(tc).append('=').append(lvl);
            }
            harvest = h.toString();
            try {
                dig = CensusFile.num(item.getDigSpeed(stack, net.minecraft.init.Blocks.stone, 0));
            } catch (Throwable ignored) {}
        }

        gear.row(name, stack.getItemDamage(), item.getClass().getName(), displayName(stack), kind,
                slot, points, item.getMaxDamage(), ench, material,
                isSpecial ? "yes" : "no",
                sawAttack ? CensusFile.num(add) : "",
                sawAttack ? CensusFile.num(mult) : "",
                sawAttack ? CensusFile.num(playerTotal) : "",
                toolClasses == null ? "" : toolClasses.toString(), harvest, dig,
                item.getItemStackLimit(), item.isDamageable());

        if (isSpecial) {
            sampleSpecialArmour(special, name, stack, probe, slot);
        }
        return true;
    }

    /**
     * Asks an ISpecialArmor piece what it will absorb, across the range of hits
     * this pack deals.
     *
     * Sampled rather than read once because the interface is free to return a
     * different ratio for a different hit size or damage type, and a piece that
     * absorbs 90% of a 4-damage hit and 2% of a 350-damage one is a completely
     * different item at the two ends. Nothing here is assumed about the shape.
     */
    private static void sampleSpecialArmour(CensusFile special, String name,
            ItemStack stack, EntityLivingBase probe, int slot) {

        ISpecialArmor armour = (ISpecialArmor) stack.getItem();
        int armourSlot = slot >= 0 ? slot : 1;

        // ApplyArmor passes the inventory index as the slot, which for a player is
        // 0 boots .. 3 helmet, the reverse of ItemArmor.armorType. Getting this
        // backwards would silently ask a helmet how it behaves as boots.
        int inventoryIndex = 3 - armourSlot;

        for (int i = 0; i < PROBE_DAMAGE.length; i++) {
            double dmg = PROBE_DAMAGE[i];
            ItemStack fresh = stack.copy();
            String err = "";
            String ratio = "", max = "", priority = "", display = "";
            try {
                ISpecialArmor.ArmorProperties p = armour.getProperties(
                        probe, fresh, DamageSource.causeMobDamage(null), dmg, inventoryIndex);
                if (p != null) {
                    ratio = CensusFile.num(p.AbsorbRatio);
                    max = String.valueOf(p.AbsorbMax);
                    priority = String.valueOf(p.Priority);
                }
            } catch (Throwable t) {
                err = t.getClass().getSimpleName() + ": " + t.getMessage();
            }
            try {
                if (probe instanceof net.minecraft.entity.player.EntityPlayer) {
                    display = String.valueOf(armour.getArmorDisplay(
                            (net.minecraft.entity.player.EntityPlayer) probe, fresh, inventoryIndex));
                }
            } catch (Throwable ignored) {}

            special.row(name, stack.getItemDamage(), armourSlot, CensusFile.num(dmg),
                    ratio, max, priority, display, err);
        }
    }

    /**
     * Every metadata variant an item exposes, so a mod that packs a whole armour
     * set into one item id is not measured as a single piece.
     *
     * Capped, because a few mods here register thousands of variants of a
     * decorative block item and none of them is gear.
     */
    private static List<ItemStack> subItems(Item item) {
        List<ItemStack> out = new ArrayList<ItemStack>();
        try {
            List<?> raw = new ArrayList<Object>();
            item.getSubItems(item, item.getCreativeTab(), (List) raw);
            for (Object o : raw) {
                if (o instanceof ItemStack) out.add((ItemStack) o);
                if (out.size() >= 64) break;
            }
        } catch (Throwable ignored) {}
        if (out.isEmpty()) {
            try {
                out.add(new ItemStack(item));
            } catch (Throwable ignored) {}
        }
        return out;
    }

    private static String displayName(ItemStack stack) {
        if (stack == null) return "";
        try {
            return stack.getDisplayName();
        } catch (Throwable t) {
            try {
                return stack.getUnlocalizedName();
            } catch (Throwable t2) {
                return "";
            }
        }
    }
}
