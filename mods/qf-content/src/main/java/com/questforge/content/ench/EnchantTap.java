package com.questforge.content.ench;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * A counter the dispatcher reports to, so a census can see inside a fight.
 *
 * The combat census needs to answer two questions the damage totals cannot:
 * <b>how often did this enchantment actually fire</b>, and <b>how much of the
 * hit was its doing</b>. Both are only knowable at the moment of dispatch, so the
 * dispatcher reports them here and everything else stays out of it.
 *
 * <h3>Why this is not simply an event</h3>
 *
 * Posting an event per proc would put a bus dispatch inside the innermost loop of
 * every hit in the game, for the benefit of a measurement that runs for an hour
 * and never again. Instead this is two static calls that return on a boolean the
 * JIT will hoist. When the census is not running the cost is a field read.
 *
 * <h3>What "attributed damage" does and does not include</h3>
 *
 * {@link #attribute} records the change an enchantment made to {@code ctx.damage}
 * -- the hit being dealt right now. That is the whole story for Executioner or
 * Colossus, and only part of it for Rupture, Arc or Venomous, whose damage
 * arrives later or lands on somebody else. Those show up in the fight's total
 * damage but not in this column, and the two must not be added together. The
 * census writes them as separate columns for exactly that reason.
 *
 * Not thread-safe, and deliberately so: it is driven from the server thread by a
 * command that only an operator can run.
 */
public final class EnchantTap {

    private EnchantTap() {}

    /**
     * Checked before every record. Kept as a plain static boolean rather than
     * a null check on the map so the disabled path is as close to free as Java
     * allows.
     */
    private static boolean enabled;

    /** Keyed "enchantname/TRIGGER", which is the grain the census reports at. */
    private static final Map<String, Counts> COUNTS = new HashMap<String, Counts>();

    /**
     * The same counters, accumulated across the whole run.
     *
     * The census resets the per-cell counters between measurements so each row
     * reports its own cell, but the proc-rate report is a statement about an
     * enchantment rather than about one cell and needs every roll it ever made.
     * Without this, resetting per cell left the final report describing only the
     * last cell that ran.
     */
    private static final Map<String, Counts> TOTALS = new HashMap<String, Counts>();

    /** One enchantment's behaviour under one trigger. */
    public static class Counts {
        public final String enchant;
        public final String trigger;
        /** Times the dispatcher considered it: the denominator of the proc rate. */
        public long rolls;
        /** Times it actually ran. */
        public long fires;
        /** Sum of the change it made to the hit it fired on. */
        public double attributedDamage;
        /** Largest single change it made, which is where outliers show up. */
        public double largestSingle;
        /** Times it ran as a Multi Strike replay rather than a first pass. */
        public long replays;

        Counts(String enchant, String trigger) {
            this.enchant = enchant;
            this.trigger = trigger;
        }

        /** Observed proc rate in percent, or NaN if it was never considered. */
        public double observedPercent() {
            return rolls == 0 ? Double.NaN : (100.0D * fires) / rolls;
        }
    }

    // ---- Control ----------------------------------------------------------

    public static void start() {
        COUNTS.clear();
        TOTALS.clear();
        enabled = true;
    }

    public static void stop() {
        enabled = false;
    }

    public static boolean isEnabled() {
        return enabled;
    }

    /**
     * Folds the current cell's counters into the run totals and zeroes them.
     * Called between cells, so a row reports its own cell while
     * {@link #totals()} still sees the whole run.
     */
    public static void reset() {
        for (Counts c : COUNTS.values()) {
            Counts total = TOTALS.get(c.enchant + "/" + c.trigger);
            if (total == null) {
                total = new Counts(c.enchant, c.trigger);
                TOTALS.put(c.enchant + "/" + c.trigger, total);
            }
            total.rolls += c.rolls;
            total.fires += c.fires;
            total.replays += c.replays;
            total.attributedDamage += c.attributedDamage;
            if (Math.abs(c.largestSingle) > Math.abs(total.largestSingle)) {
                total.largestSingle = c.largestSingle;
            }
        }
        COUNTS.clear();
    }

    /** Every counter recorded since the last reset: this cell only. */
    public static List<Counts> snapshot() {
        return new ArrayList<Counts>(COUNTS.values());
    }

    /** Every counter for the whole run, including the cell in progress. */
    public static List<Counts> totals() {
        Map<String, Counts> merged = new HashMap<String, Counts>();
        for (Counts c : TOTALS.values()) {
            Counts copy = new Counts(c.enchant, c.trigger);
            copy.rolls = c.rolls;
            copy.fires = c.fires;
            copy.replays = c.replays;
            copy.attributedDamage = c.attributedDamage;
            copy.largestSingle = c.largestSingle;
            merged.put(c.enchant + "/" + c.trigger, copy);
        }
        for (Counts c : COUNTS.values()) {
            Counts total = merged.get(c.enchant + "/" + c.trigger);
            if (total == null) {
                total = new Counts(c.enchant, c.trigger);
                merged.put(c.enchant + "/" + c.trigger, total);
            }
            total.rolls += c.rolls;
            total.fires += c.fires;
            total.replays += c.replays;
            total.attributedDamage += c.attributedDamage;
            if (Math.abs(c.largestSingle) > Math.abs(total.largestSingle)) {
                total.largestSingle = c.largestSingle;
            }
        }
        return new ArrayList<Counts>(merged.values());
    }

    /** One enchantment's counter under one trigger, or null if it never came up. */
    public static Counts get(String enchant, String trigger) {
        return COUNTS.get(enchant + "/" + trigger);
    }

    /** Totals across every trigger for one enchantment. */
    public static Counts total(String enchant) {
        Counts sum = new Counts(enchant, "*");
        for (Counts c : COUNTS.values()) {
            if (!c.enchant.equals(enchant)) continue;
            sum.rolls += c.rolls;
            sum.fires += c.fires;
            sum.replays += c.replays;
            sum.attributedDamage += c.attributedDamage;
            if (c.largestSingle > sum.largestSingle) sum.largestSingle = c.largestSingle;
        }
        return sum;
    }

    // ---- Recording, called from the dispatcher ----------------------------

    /**
     * One proc roll and its outcome.
     *
     * Called for every considered enchantment whether or not it fired, because a
     * proc rate without its denominator is not a measurement.
     */
    public static void rolled(QFEnchantment ench, Object trigger, boolean fired, int pass) {
        if (!enabled || ench == null) return;
        Counts c = counts(ench, trigger);
        c.rolls++;
        if (fired) {
            c.fires++;
            if (pass > 0) c.replays++;
        }
    }

    /** How much an enchantment just changed the hit it fired on. */
    public static void attribute(QFEnchantment ench, Object trigger, float delta) {
        if (!enabled || ench == null || delta == 0F) return;
        Counts c = counts(ench, trigger);
        c.attributedDamage += delta;
        double magnitude = Math.abs(delta);
        if (magnitude > Math.abs(c.largestSingle)) c.largestSingle = delta;
    }

    private static Counts counts(QFEnchantment ench, Object trigger) {
        String name = ench.displayKey();
        String trig = String.valueOf(trigger);
        String key = name + "/" + trig;
        Counts c = COUNTS.get(key);
        if (c == null) {
            c = new Counts(name, trig);
            COUNTS.put(key, c);
        }
        return c;
    }
}
