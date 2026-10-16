#!/usr/bin/env python3
"""
Read the combat census and turn it into tuning and loot decisions.

This is the analysis half of `/qfcensus combat`. It does not model anything and
it does not know any enchantment's rules -- it reads measurements that the game
produced and arranges them so a person can make three decisions:

  1. Which enchantments are mis-tuned, i.e. a long way from the rest of their
     rarity tier.
  2. Which enchantments are mis-IMPLEMENTED, i.e. firing at a rate that does not
     match their own getProcChance. That is a bug report, not a balance note, and
     it is kept in a separate section because the two get confused.
  3. What the loot weights should be, given that rarity is supposed to track
     power and currently only tracks intent.

The distinction that matters throughout: `qfsim.py` predicts what the code will
do, this reads what the code did. Where they disagree, this wins, for the same
reason ENCHANT-GROUND-TRUTH.md wins over ENCHANT-TUNING.md -- it has a
provenance and the other has a derivation.

Usage:
    qfcombat.py <census-dir-or-file> [--rarity] [--loot] [--procs] [--csv out.csv]

`census-dir-or-file` is either the directory the census wrote into (usually the
pack's config/) or the combat TSV itself.
"""
import argparse
import csv
import math
import os
import statistics
import sys
from collections import defaultdict

COMBAT = "qfcontent-census-combat.tsv"
PROCS = "qfcontent-census-combat-procs.tsv"
FAILED = "qfcontent-census-combat-failed.tsv"

RARITIES = ["COMMON", "UNCOMMON", "RARE", "EPIC", "LEGENDARY"]


# --------------------------------------------------------------------- io ----

def read_tsv(path):
    """Rows of a census file, skipping its provenance block.

    The census writes '#' comment lines before the header and one after the last
    row. Everything else is data.
    """
    if not os.path.exists(path):
        return []
    rows = []
    with open(path, encoding="utf-8") as f:
        lines = [l for l in f if not l.startswith("#")]
    if not lines:
        return []
    reader = csv.DictReader(lines, delimiter="\t")
    for row in reader:
        rows.append(row)
    return rows


def num(value):
    """A census float, or None. Empty cells and NaN both mean 'not measured'."""
    if value is None:
        return None
    value = value.strip()
    if value in ("", "NaN"):
        return None
    try:
        f = float(value)
    except ValueError:
        return None
    return None if math.isnan(f) else f


def degenerate(row):
    """True when the census flagged this cell's fight as not having happened."""
    return "swings landed" in (row.get("note") or "")


def locate(target):
    if os.path.isfile(target):
        return os.path.dirname(target) or ".", target
    return target, os.path.join(target, COMBAT)


# --------------------------------------------------------------- analysis ----

class Enchant:
    """Everything measured about one enchantment, across every target."""

    def __init__(self, name):
        self.name = name
        self.rarity = ""
        self.level = ""
        self.category = ""
        self.mode = ""
        self.rows = []

    # Marginal percentages are already normalised against a control on the same
    # target, so averaging them across targets is meaningful in a way that
    # averaging raw damage would not be.
    def _avg(self, field):
        values = [num(r[field]) for r in self.usable_rows]
        values = [v for v in values if v is not None]
        return statistics.mean(values) if values else None

    @property
    def usable_rows(self):
        """Rows whose fight actually happened.

        The census marks a cell degenerate when almost nothing it swung at
        landed, and writes the reason to the failures file -- but the row still
        goes into the main table carrying whatever numbers that broken fight
        produced. Averaging those in is how a target that cannot be hurt at all
        turns into a balance figure.

        Twilight Forest's Hydra is the case that forced this: it only takes
        damage through its separate head entities, so 49 of its 77 cells landed
        one hit or none while reporting a full window of swings.
        """
        return [r for r in self.rows if not degenerate(r)]

    @property
    def excluded(self):
        return [r for r in self.rows if degenerate(r)]

    @property
    def marginal_dps_pct(self):
        return self._avg("marginal_pct")

    @property
    def marginal_ttk_pct(self):
        return self._avg("marginal_ttk_pct")

    @property
    def mitigation_pct(self):
        return self._avg("mitigation_pct")

    @property
    def observed_proc(self):
        return self._avg("observed_proc_pct")

    @property
    def expected_proc(self):
        return self._avg("expected_proc_pct")

    @property
    def power(self):
        """The one number used for ranking.

        Offensive enchantments are ranked on marginal DPS and defensive ones on
        mitigation, because those are the quantities each was designed to move.
        They are NOT directly comparable to each other and are never mixed in a
        single ranking below -- but within a mode, this is the number.
        """
        if self.mode == "DEFENSE":
            return self.mitigation_pct
        return self.marginal_dps_pct


def collect(rows):
    """Group the isolated rows by enchantment. Controls and stacks handled apart."""
    enchants = {}
    stacked = []
    controls = []

    for row in rows:
        kind = row.get("kind", "")
        if kind == "control":
            controls.append(row)
            continue
        if kind == "stacked":
            stacked.append(row)
            continue

        name = row["loadout"].split(":")[0]
        e = enchants.get(name)
        if e is None:
            e = Enchant(name)
            e.rarity = row.get("rarity", "")
            e.level = row.get("level", "")
            e.category = row.get("category", "")
            e.mode = row.get("mode", "")
            enchants[name] = e
        e.rows.append(row)

    return enchants, stacked, controls


def by_rarity(enchants, mode):
    groups = defaultdict(list)
    for e in enchants.values():
        if e.mode != mode:
            continue
        if e.power is None:
            continue
        groups[e.rarity].append(e)
    return groups


# ---------------------------------------------------------------- reports ----

def report_ranking(enchants, mode, title):
    rows = sorted(
        [e for e in enchants.values() if e.mode == mode and e.power is not None],
        key=lambda e: e.power, reverse=True)
    if not rows:
        return

    print()
    print(title)
    print("=" * len(title))
    print()
    unit = "mitigation" if mode == "DEFENSE" else "marg.DPS"
    print(f"{'enchant':<20} {'rarity':<10} {'lvl':>3} {unit:>10} {'ttk':>8} "
          f"{'proc obs':>9} {'proc exp':>9}")
    print("-" * 74)
    for e in rows:
        note = "" if not e.excluded else f"  ({len(e.excluded)} cell(s) excluded)"
        print(f"{e.name:<20} {e.rarity:<10} {e.level:>3} "
              f"{fmt(e.power):>10} {fmt(e.marginal_ttk_pct):>8} "
              f"{fmt(e.observed_proc):>9} {fmt(e.expected_proc):>9}{note}")

    unmeasured = [e for e in enchants.values() if e.mode == mode and e.power is None]
    if unmeasured:
        print()
        print("Not measured (no control, or the cell failed). These are NOT balanced:")
        for e in sorted(unmeasured, key=lambda e: e.name):
            print(f"  {e.name}")


def fmt(value):
    return "-" if value is None else f"{value:+.1f}"


def report_rarity(enchants):
    """Is measured power actually monotonic with the rarity someone assigned?

    Rarity is currently a statement of intent. If the tiers overlap heavily then
    the loot table is distributing power at random with respect to the label on
    the box, which is the thing worth knowing before writing one.
    """
    print()
    print("Rarity coherence")
    print("================")
    print()
    print("Does power actually increase with rarity? Bands that overlap mean the")
    print("label on a book does not predict what it does.")

    for mode in ("MELEE", "BOW", "DEFENSE"):
        groups = by_rarity(enchants, mode)
        if not groups:
            continue
        print()
        print(f"  {mode}")
        previous_median = None
        previous_name = None
        for rarity in RARITIES:
            members = groups.get(rarity, [])
            if not members:
                continue
            powers = sorted(e.power for e in members)
            median = statistics.median(powers)
            flag = ""
            if previous_median is not None and median < previous_median:
                flag = f"  <-- weaker than {previous_name}"
            print(f"    {rarity:<10} n={len(members):<3} "
                  f"median {median:+7.1f}  range {powers[0]:+.1f}..{powers[-1]:+.1f}{flag}")
            previous_median, previous_name = median, rarity

        # Outliers: an enchantment far outside its own tier is either mis-tuned
        # or mis-labelled, and both are decisions to make before loot weights.
        print()
        for rarity in RARITIES:
            members = groups.get(rarity, [])
            if len(members) < 3:
                continue
            powers = [e.power for e in members]
            median = statistics.median(powers)
            spread = statistics.pstdev(powers) or 1.0
            for e in sorted(members, key=lambda e: e.power, reverse=True):
                z = (e.power - median) / spread
                if abs(z) >= 2.0:
                    direction = "above" if z > 0 else "below"
                    print(f"    outlier: {e.name} is {abs(z):.1f} sd {direction} "
                          f"the {rarity} median ({e.power:+.1f} vs {median:+.1f})")


def report_procs(procs_rows):
    """Where the code does not do what getProcChance says it does."""
    print()
    print("Proc rate check")
    print("===============")
    print()
    print("Observed rate vs the enchantment's own getProcChance. A gap here is a")
    print("bug in the enchantment; tuning the effect will not fix it. Rows with")
    print("few rolls are noise, so a minimum sample is enforced.")
    print()

    interesting = []
    for row in procs_rows:
        rolls = num(row["rolls"]) or 0
        observed = num(row["observed_pct"])
        expected = num(row["expected_pct"])
        if rolls < 30 or observed is None or expected is None:
            continue
        # Binomial standard error on the expected rate, in percentage points.
        p = expected / 100.0
        se = 100.0 * math.sqrt(max(p * (1 - p), 1e-9) / rolls)
        deviation = observed - expected
        if abs(deviation) > max(3.0 * se, 2.0):
            interesting.append((abs(deviation / max(se, 1e-9)), row, observed,
                                expected, deviation, rolls))

    if not interesting:
        print("  Every enchantment with a usable sample fired within noise of its")
        print("  declared rate. Nothing to report.")
        return

    interesting.sort(reverse=True, key=lambda t: t[0])
    print(f"{'enchant':<20} {'trigger':<12} {'rolls':>7} {'observed':>9} "
          f"{'expected':>9} {'gap':>8}")
    print("-" * 70)
    for sigma, row, observed, expected, deviation, rolls in interesting:
        print(f"{row['enchant']:<20} {row['trigger']:<12} {int(rolls):>7} "
              f"{observed:>8.1f}% {expected:>8.1f}% {deviation:>+7.1f}")


def report_stacks(stacked, enchants):
    """Does a combination do more than its parts?

    This is the question the loot table is really an answer to. Nobody ends up
    holding one enchantment; they end up holding five, and if those five multiply
    rather than add then the tier weights are the only lever left.
    """
    if not stacked:
        return
    print()
    print("Stacked loadouts")
    print("================")
    print()
    print("Measured combination vs the sum of its parts measured alone. A large")
    print("positive excess means these enchantments multiply, and the loot table")
    print("has to make the combination rare rather than each piece rare.")
    print()
    print(f"{'loadout':<44} {'measured':>9} {'sum parts':>10} {'excess':>8}")
    print("-" * 74)

    seen = {}
    for row in stacked:
        measured = num(row["marginal_pct"])
        if measured is None:
            continue
        parts = [p.strip().split(":")[0] for p in row["loadout"].split("+")]
        total = 0.0
        complete = True
        for part in parts:
            e = enchants.get(part)
            if e is None or e.marginal_dps_pct is None:
                complete = False
                break
            total += e.marginal_dps_pct
        if not complete:
            continue
        label = row["loadout"]
        seen.setdefault(label, []).append((measured, total))

    for label, samples in sorted(seen.items()):
        measured = statistics.mean(s[0] for s in samples)
        total = statistics.mean(s[1] for s in samples)
        print(f"{label:<44} {measured:>+8.1f}% {total:>+9.1f}% {measured - total:>+7.1f}")


def report_loot(enchants):
    """A loot weighting derived from measured power rather than from intent.

    The proposal is deliberately simple and deliberately not applied
    automatically: rank within mode, split into five bands of equal population,
    and weight so that expected power per book is flat. Whether that is the right
    curve for this pack is a design question, and the point of printing it is to
    argue with it.
    """
    print()
    print("Loot weighting, derived from measured power")
    print("===========================================")
    print()
    print("Ranks each enchantment within its mode and bands it by measured power,")
    print("rather than by the rarity currently written in the source. Where the")
    print("two disagree, the 'now' and 'measured' columns differ -- those are the")
    print("books whose colour is lying to the player.")
    print()

    for mode in ("MELEE", "BOW", "DEFENSE"):
        ranked = sorted(
            [e for e in enchants.values() if e.mode == mode and e.power is not None],
            key=lambda e: e.power, reverse=True)
        if len(ranked) < 5:
            continue

        print(f"  {mode}")
        print(f"    {'enchant':<20} {'now':<10} {'measured':<10} {'power':>8} {'weight':>7}")
        print("    " + "-" * 60)

        # Five equal-population bands, strongest first.
        band_size = max(1, len(ranked) // len(RARITIES))
        # Chest weights currently in EnchantLoot.CHEST_WEIGHT, kept so the
        # proposal is expressed in the units the code already uses.
        weights = {"LEGENDARY": 1, "EPIC": 2, "RARE": 4, "UNCOMMON": 8, "COMMON": 12}

        for i, e in enumerate(ranked):
            band_index = min(i // band_size, len(RARITIES) - 1)
            measured_rarity = list(reversed(RARITIES))[band_index]
            mismatch = "" if measured_rarity == e.rarity else "  <-- mismatch"
            print(f"    {e.name:<20} {e.rarity:<10} {measured_rarity:<10} "
                  f"{e.power:>+7.1f} {weights[measured_rarity]:>7}{mismatch}")
        print()


def report_failures(failed_rows):
    if not failed_rows:
        return
    print()
    print("Cells that failed")
    print("=================")
    print()
    print("An enchantment here has no measurement at all. It is not balanced,")
    print("whatever any document says about it.")
    print()
    for row in failed_rows:
        print(f"  {row.get('loadout',''):<30} {row.get('target',''):<20} "
              f"{row.get('stage','')}: {row.get('error','')}")


def write_csv(path, enchants):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["enchant", "mode", "rarity", "level", "category",
                    "power", "marginal_dps_pct", "marginal_ttk_pct",
                    "mitigation_pct", "observed_proc_pct", "expected_proc_pct"])
        for e in sorted(enchants.values(), key=lambda e: e.name):
            w.writerow([e.name, e.mode, e.rarity, e.level, e.category,
                        e.power, e.marginal_dps_pct, e.marginal_ttk_pct,
                        e.mitigation_pct, e.observed_proc, e.expected_proc])
    print(f"\nWrote {path}")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("target", help="census directory, or the combat TSV itself")
    ap.add_argument("--rarity", action="store_true", help="rarity coherence only")
    ap.add_argument("--loot", action="store_true", help="loot weighting only")
    ap.add_argument("--procs", action="store_true", help="proc rate check only")
    ap.add_argument("--csv", help="also write a flat CSV of the per-enchant table")
    ap.add_argument("--only", action="append", default=None, dest="only",
                    help="only use cells fought against this target (repeatable). "
                         "Prefer a target that cannot die inside the window: a "
                         "mob that dies mid-cell makes damage depend on how many "
                         "spawns were chewed through and what health each rolled, "
                         "which is the largest source of noise in the whole census.")
    args = ap.parse_args()

    directory, combat_path = locate(args.target)
    rows = read_tsv(combat_path)
    if not rows:
        sys.exit(f"No combat census found at {combat_path}. Run /qfcensus combat first.")

    if args.only:
        wanted = set(t.lower() for t in args.only)
        before = len(rows)
        rows = [r for r in rows if (r.get("target") or "").lower() in wanted]
        if not rows:
            sys.exit("no rows for target(s) %s" % ", ".join(sorted(wanted)))
        print(f"Restricted to {', '.join(sorted(wanted))}: "
              f"{len(rows)} of {before} rows")

    enchants, stacked, controls = collect(rows)
    procs_rows = read_tsv(os.path.join(directory, PROCS))
    failed_rows = read_tsv(os.path.join(directory, FAILED))

    print(f"Combat census: {len(rows)} rows, {len(enchants)} enchantments, "
          f"{len(controls)} controls, {len(stacked)} stacked loadouts")
    print(f"Source: {combat_path}")

    everything = not (args.rarity or args.loot or args.procs)

    if everything:
        report_ranking(enchants, "MELEE", "Melee, by marginal DPS over control")
        report_ranking(enchants, "BOW", "Bows, by marginal DPS over control")
        report_ranking(enchants, "DEFENSE", "Armour, by damage mitigated")
    if everything or args.procs:
        report_procs(procs_rows)
    if everything or args.rarity:
        report_rarity(enchants)
    if everything:
        report_stacks(stacked, enchants)
    if everything or args.loot:
        report_loot(enchants)
    if everything:
        report_failures(failed_rows)

    if args.csv:
        write_csv(args.csv, enchants)


if __name__ == "__main__":
    main()
