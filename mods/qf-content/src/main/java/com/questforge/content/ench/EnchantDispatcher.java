package com.questforge.content.ench;

import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.List;
import java.util.Map;

import net.minecraft.enchantment.EnchantmentHelper;
import net.minecraft.item.ItemStack;

/**
 * The single place every custom enchantment effect is invoked from.
 *
 * Nothing else calls an enchantment's hooks. That is the whole point: because
 * every proc funnels through here, Multi Strike is implemented once -- as a loop
 * count -- rather than being special-cased inside eighty separate effects.
 *
 * Adding an enchantment that Multi Strike should not double is a matter of
 * returning false from isMultipliable(); no change is needed here.
 */
public class EnchantDispatcher {

    /** What kind of trigger is being dispatched. */
    public enum Trigger {
        ATTACK, DAMAGED, KILL, TICK, HARVEST, BREAK, ITEM_DESTROYED, XP_PICKUP, TARGETED, DEATH,
        ARROW_HIT, ARROW_LAND, ARROW_TICK, DROPS
    }

    /** One custom enchantment found on a stack, with its level. */
    public static class Found {
        public final QFEnchantment enchant;
        public final int level;

        Found(QFEnchantment enchant, int level) {
            this.enchant = enchant;
            this.level = level;
        }
    }

    /**
     * Every custom enchantment on a stack. Reads the stack's enchantment map once
     * rather than testing all ~80 registrations individually.
     */
    @SuppressWarnings("rawtypes")
    public static List<Found> findOn(ItemStack stack) {
        List<Found> found = new ArrayList<Found>();
        if (stack == null || !stack.isItemEnchanted()) return found;

        Map enchants = EnchantmentHelper.getEnchantments(stack);
        if (enchants == null || enchants.isEmpty()) return found;

        for (Object o : enchants.entrySet()) {
            Map.Entry e = (Map.Entry) o;
            int id = ((Number) e.getKey()).intValue();
            int level = ((Number) e.getValue()).intValue();
            QFEnchantment ench = QFEnchantments.byId(id);
            if (ench != null && level > 0) {
                found.add(new Found(ench, level));
            }
        }
        return found;
    }

    /**
     * Runs every custom enchantment on the stack for the given trigger.
     *
     * @return the resulting damage, so damage-event callers can write it back.
     */
    public static float dispatch(Trigger trigger, ProcContext ctx) {
        List<Found> found = findOn(ctx.stack);
        if (found.isEmpty()) return ctx.damage;

        // Flat adds, then multipliers, then procs. Stable, so within a phase the
        // application order still holds -- it just no longer changes the answer.
        if (found.size() > 1) Collections.sort(found, BY_PHASE);

        boolean multiStrike = hasMultiStrike(found);

        for (Found f : found) {
            // Multi Strike never doubles itself, and never doubles passives.
            int passes = (multiStrike && f.enchant.isMultipliable() && trigger != Trigger.TICK)
                    ? 2 : 1;

            for (int pass = 0; pass < passes; pass++) {
                ctx.level = f.level;
                ctx.pass = pass;

                int chance = f.enchant.getProcChance(f.level);
                if (chance < 100 && ctx.rand.nextInt(100) >= chance) continue;

                invoke(trigger, f.enchant, ctx);
            }
        }
        return ctx.damage;
    }

    private static void invoke(Trigger trigger, QFEnchantment ench, ProcContext ctx) {
        switch (trigger) {
            case ATTACK:  ench.onAttack(ctx); break;
            case DAMAGED: ench.onDamaged(ctx); break;
            case KILL:    ench.onKill(ctx); break;
            case TICK:    ench.onTick(ctx); break;
            case HARVEST:
                if (ctx instanceof HarvestContext) {
                    ench.onHarvest((HarvestContext) ctx);
                }
                break;
            case BREAK:
                if (ctx instanceof BreakContext) {
                    ench.onBreak((BreakContext) ctx);
                }
                break;
            case XP_PICKUP:
                if (ctx instanceof XpContext) {
                    ench.onXpPickup((XpContext) ctx);
                }
                break;
            case ITEM_DESTROYED:
                ench.onItemDestroyed(ctx);
                break;
            case TARGETED:
                ench.onTargeted(ctx);
                break;
            case DEATH:
                ench.onDeath(ctx);
                break;
            case DROPS:
                if (ctx instanceof DropsContext) ench.onDrops((DropsContext) ctx);
                break;
            case ARROW_HIT:
                if (ctx instanceof ArrowContext) ench.onArrowHit((ArrowContext) ctx);
                break;
            case ARROW_LAND:
                if (ctx instanceof ArrowContext) ench.onArrowLand((ArrowContext) ctx);
                break;
            case ARROW_TICK:
                if (ctx instanceof ArrowContext) ench.onArrowTick((ArrowContext) ctx);
                break;
        }
    }

    private static final Comparator<Found> BY_PHASE = new Comparator<Found>() {
        @Override
        public int compare(Found a, Found b) {
            return a.enchant.getPhase().ordinal() - b.enchant.getPhase().ordinal();
        }
    };

    private static boolean hasMultiStrike(List<Found> found) {
        if (QFEnchantments.multiStrike == null) return false;
        for (Found f : found) {
            if (f.enchant == QFEnchantments.multiStrike) return true;
        }
        return false;
    }
}
