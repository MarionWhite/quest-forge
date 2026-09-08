package com.questforge.content.ench;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Random;

import net.minecraft.enchantment.EnchantmentHelper;
import net.minecraft.item.ItemStack;
import net.minecraft.util.StatCollector;

/**
 * What each consumable does when it lands on something.
 *
 * Like {@link EnchantApplication}, this decides and reports; it never removes the
 * consumable from anyone's hand. The caller does that, and only when the outcome
 * says it was actually spent.
 *
 * Three states are deliberately kept apart:
 *
 *   not applicable  -- wrong target entirely. The click falls through to vanilla,
 *                      so picking a scroll up and putting it down still works.
 *   applicable, no effect -- right target, nothing to do (already warded). The
 *                      click is ours and the player is told, but nothing is spent.
 *   applied         -- the consumable is used up.
 */
public class ConsumableUse {

    /** How much one Magic Dust is worth. */
    private static final int DUST_STEP = 5;

    public static class Outcome {
        public final String message;
        public final boolean spent;

        Outcome(String message, boolean spent) {
            this.message = message;
            this.spent = spent;
        }
    }

    private static Outcome spent(String message) {
        return new Outcome(message, true);
    }

    private static Outcome noop(String message) {
        return new Outcome(message, false);
    }

    /**
     * Whether this consumable has anything to say about this target at all.
     *
     * Split out from {@link #apply} because the client has to decide whether to
     * swallow the click before the server has rolled anything -- and it must reach
     * the same answer, or the two sides disagree about who owns the click.
     */
    public static boolean applies(int meta, ItemStack target) {
        if (target == null) return false;

        if (meta == ItemConsumable.SOLVENT) {
            return !BookNBT.isBook(target) && !customEnchantsOn(target).isEmpty();
        }
        return BookNBT.isBook(target);
    }

    /** @return null if this combination is not applicable at all. */
    public static Outcome apply(int meta, ItemStack target, Random rand) {
        if (!applies(meta, target)) return null;

        switch (meta) {
            case ItemConsumable.MAGIC_DUST:     return dust(target);
            case ItemConsumable.WARD_SCROLL:    return ward(target);
            case ItemConsumable.BINDING_SCROLL: return bind(target);
            case ItemConsumable.SOLVENT:        return dissolve(target, rand);
            default:                            return null;
        }
    }

    private static Outcome dust(ItemStack book) {
        if (BookNBT.getSuccess(book) >= BookNBT.DUST_CAP) {
            return noop("This tome will take no more dust.");
        }
        BookNBT.addSuccess(book, DUST_STEP, BookNBT.DUST_CAP);
        return spent("Success chance is now " + BookNBT.getSuccess(book) + "%.");
    }

    private static Outcome ward(ItemStack book) {
        if (BookNBT.hasWard(book)) return noop("This tome is already warded.");

        BookNBT.setWard(book);
        return spent("Warded. One shattering will be absorbed.");
    }

    private static Outcome bind(ItemStack book) {
        if (BookNBT.getSuccess(book) >= 100 && BookNBT.getDestroy(book) <= 0) {
            return noop("This tome is already bound.");
        }
        BookNBT.setGuaranteed(book);
        return spent("Bound. This tome will not fail.");
    }

    /**
     * Strips one custom enchantment, chosen at random.
     *
     * Random rather than chosen: everything else in this system is a gamble, and
     * letting a player pick would turn Solvent into a free way to move a legendary
     * onto better gear one enchantment at a time.
     */
    @SuppressWarnings("unchecked")
    private static Outcome dissolve(ItemStack target, Random rand) {
        List<Integer> ours = customEnchantsOn(target);
        if (ours.isEmpty()) return null;

        Integer chosen = ours.get(rand.nextInt(ours.size()));
        QFEnchantment removed = QFEnchantments.byId(chosen.intValue());

        Map<Integer, Integer> remaining =
                new HashMap<Integer, Integer>(EnchantmentHelper.getEnchantments(target));
        remaining.remove(chosen);
        EnchantmentHelper.setEnchantments(remaining, target);

        return spent(StatCollector.translateToLocal(removed.getName()) + " dissolves away.");
    }

    /** Only our own enchantments; vanilla and other mods' are not ours to strip. */
    @SuppressWarnings("unchecked")
    private static List<Integer> customEnchantsOn(ItemStack target) {
        List<Integer> ours = new ArrayList<Integer>();
        if (target == null || !target.isItemEnchanted()) return ours;

        Map<Integer, Integer> current = EnchantmentHelper.getEnchantments(target);
        if (current == null) return ours;

        for (Integer id : current.keySet()) {
            if (QFEnchantments.byId(id.intValue()) != null) ours.add(id);
        }
        return ours;
    }
}
