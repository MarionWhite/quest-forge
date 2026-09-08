package com.questforge.content.ench;

import net.minecraft.enchantment.Enchantment;
import net.minecraft.enchantment.EnumEnchantmentType;
import net.minecraft.item.ItemStack;

/**
 * Base class for every custom enchantment.
 *
 * Three things are settled here once, for all of them:
 *
 * 1. canApply is overridden so enchantments work on modded gear, not just the
 *    vanilla item classes EnumEnchantmentType knows about.
 * 2. They never appear at an enchanting table and never turn up in vanilla loot
 *    books, so they cannot dilute normal enchanting. Our own books are the only
 *    way in.
 * 3. Effects are declared as hooks rather than by registering event handlers, so
 *    every proc goes through EnchantDispatcher -- which is what makes Multi Strike
 *    possible without touching each enchantment.
 */
public abstract class QFEnchantment extends Enchantment {

    public final Rarity rarity;
    public final EnchantCategory category;
    private final int maxLevel;

    protected QFEnchantment(int id, String name, Rarity rarity, EnchantCategory category, int maxLevel) {
        // Weight is irrelevant since these never roll at a table, but must be > 0:
        // Enchantment's own random-selection helpers divide by it.
        super(id, 1, pickVanillaType(category));
        this.rarity = rarity;
        this.category = category;
        this.maxLevel = maxLevel;
        setName(name);
    }

    /**
     * The vanilla type is only a fallback for code paths that ask before calling
     * canApply. Our canApply override is the real gate.
     */
    private static EnumEnchantmentType pickVanillaType(EnchantCategory category) {
        switch (category) {
            case WEAPON:
            case SWORD:
            case AXE:        return EnumEnchantmentType.weapon;
            case BOW:        return EnumEnchantmentType.bow;
            case TOOL:
            case PICKAXE:
            case SHOVEL:
            case DIGGER:     return EnumEnchantmentType.digger;
            case ARMOR:       return EnumEnchantmentType.armor;
            case HELMET:      return EnumEnchantmentType.armor_head;
            case CHESTPLATE:  return EnumEnchantmentType.armor_torso;
            case LEGGINGS:    return EnumEnchantmentType.armor_legs;
            case BOOTS:       return EnumEnchantmentType.armor_feet;
            default:          return EnumEnchantmentType.all;
        }
    }

    @Override
    public boolean canApply(ItemStack stack) {
        return category.accepts(stack);
    }

    @Override
    public boolean canApplyAtEnchantingTable(ItemStack stack) {
        return false;
    }

    @Override
    public boolean isAllowedOnBooks() {
        return false;
    }

    @Override
    public int getMinLevel() {
        return 1;
    }

    @Override
    public int getMaxLevel() {
        return maxLevel;
    }

    /**
     * Chance in percent that this fires on a given trigger. Effects that should
     * always apply (passive stat changes) return 100.
     */
    public int getProcChance(int level) {
        return 100;
    }

    /**
     * When in a hit this enchantment's damage change is applied.
     *
     * Enchantments used to run in the order their books were applied, so the
     * same sword did different damage depending on which tome came first: a flat
     * +10 before a x1.75 is not the same as after it. The dispatcher now runs all
     * FLAT adds, then all MULTIPLIERs, then everything else, so order never matters.
     */
    public enum Phase { FLAT, MULTIPLIER, PROC }

    public Phase getPhase() {
        return Phase.PROC;
    }

    /**
     * Whether Multi Strike may run this twice.
     *
     * Passive and permanent effects must return false -- doubling "you have night
     * vision" is meaningless, and doubling a permanent attribute modifier would
     * stack it out of control.
     */
    public boolean isMultipliable() {
        return true;
    }

    // ---- Effect hooks. Override the ones that apply; all default to nothing. ----

    /** The holder hit something with this item. */
    public void onAttack(ProcContext ctx) {}

    /** The wearer was hit while this item was equipped. */
    public void onDamaged(ProcContext ctx) {}

    /** The holder killed something with this item. */
    public void onKill(ProcContext ctx) {}

    /** Runs every tick for equipped armor / held tools. Never multiplied. */
    public void onTick(ProcContext ctx) {}

    /** Drops are being decided for a block this tool broke. */
    public void onHarvest(HarvestContext ctx) {}

    /** A block is being broken with this tool, before drops are decided. */
    public void onBreak(BreakContext ctx) {}

    /** This item just ran out of durability and broke. */
    public void onItemDestroyed(ProcContext ctx) {}

    /** The holder picked up experience while carrying this item. */
    public void onXpPickup(XpContext ctx) {}

    /** A mob just chose the wearer as its target. Set ctx.cancelled to shake it off. */
    public void onTargeted(ProcContext ctx) {}

    /** The wearer is about to die. Set ctx.cancelled to prevent it. */
    public void onDeath(ProcContext ctx) {}

    /** Something the holder killed is dropping its loot. */
    public void onDrops(DropsContext ctx) {}

    /** An arrow from this bow struck something. */
    public void onArrowHit(ArrowContext ctx) {}

    /** An arrow from this bow came to rest. */
    public void onArrowLand(ArrowContext ctx) {}

    /** Runs each tick for every arrow from this bow still in flight. */
    public void onArrowTick(ArrowContext ctx) {}
}
