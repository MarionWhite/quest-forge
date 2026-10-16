#!/usr/bin/env python3
"""
Turn the combat census runs into a rarity and loot proposal.

`qfcombat.py` reports one run. This reads several -- each measuring a different
situation -- and answers the question the loot table actually needs answered:

    given everything we now know an enchantment can do, what tier does it
    belong in and how often should it drop?

Why more than one run. An enchantment's worth is not a single number, because
its condition is not always met:

  * against a boss that cannot die, sustained damage is what matters and
    anything keyed to finishing a target does nothing;
  * against a target that dies, burst converts into kill throughput, and a
    capped effect that looked useless against the boss can dominate;
  * a wielder at full health never triggers Berserk, Riposte, Bulwark,
    Cockroach or Sacrifice, all of which key off being hurt;
  * armour mitigation is a ratio and reads the same at any incoming magnitude,
    while survivability only resolves when hits are hard enough to kill.

So each run measures one situation, and an enchantment is rated on its
**ceiling** -- the best it managed anywhere. That is deliberately the
pessimistic reading for balance purposes: a loot table has to be safe for the
case where the enchantment is at its strongest, not for its average.

Usage:
    qfshipping.py <run.tsv> [<run.tsv> ...]
"""
import argparse
import csv
import math
import os
import statistics
from collections import defaultdict

RARITIES = ["COMMON", "UNCOMMON", "RARE", "EPIC", "LEGENDARY"]

# Enchantments that cannot move the quantity a given mode measures. Their spread
# is the instrument's error bar, and every figure is corrected against their
# mean. Keeping this list honest is what separates a result from a coincidence.
NULL_SET = {
    "MELEE": {"accelerant", "tracker", "demonforged", "soulbound", "rally",
              "reach", "decapitate", "jammer"},
    "DEFENSE": {"nightsight", "flippers", "frostpath", "camouflage", "frog", "deft"},
    "BOW": set(),
}
FIELD = {"MELEE": "marginal_pct", "BOW": "marginal_pct", "DEFENSE": "mitigation_pct"}

# Enchantments whose designed effect is not damage dealt or damage stopped. A
# combat census cannot price these and should not pretend to: measuring zero
# means the instrument is wrong, not that the enchantment is. They are listed
# separately so nobody reads "COMMON" off a table and demotes Soulbound.
UTILITY = {
    "soulbound", "reach", "tracker", "timber", "mending", "demonforged",
    "rally", "trade", "disarm", "daze", "suplex", "getoffme", "magnetize",
    "torchlight", "prospector", "nightsight", "flippers", "frog", "deft",
    "camouflage", "cleansing", "frostpath", "polarize", "jammer",
    "instanttransmission", "soulentwine", "bola",
}


def num(row, field):
    v = (row.get(field) or "").strip()
    if v in ("", "NaN"):
        return None
    try:
        f = float(v)
    except ValueError:
        return None
    return None if math.isnan(f) else f


def read(path):
    with open(path, encoding="utf-8") as fh:
        lines = [l for l in fh if not l.startswith("#")]
    rows = list(csv.DictReader(lines, delimiter="\t"))
    wounded = False
    with open(path, encoding="utf-8") as fh:
        wounded = "WOUNDED RUN" in fh.read(4000)
    return rows, wounded


def usable(row):
    return "swings landed" not in (row.get("note") or "")


class Measured:
    """One enchantment, and the best it managed in any situation tested."""

    def __init__(self, name):
        self.name = name
        self.rarity = ""
        self.mode = ""
        # scenario label -> corrected value
        self.scores = {}

    @property
    def ceiling(self):
        return max(self.scores.values()) if self.scores else None

    @property
    def best_scenario(self):
        if not self.scores:
            return ""
        return max(self.scores.items(), key=lambda kv: kv[1])[0]


def collect(paths):
    found = {}
    for path in paths:
        rows, wounded = read(path)
        label_suffix = " (wounded)" if wounded else ""
        # Group by (mode, target) -- each is one situation.
        groups = defaultdict(list)
        for r in rows:
            if r.get("kind") != "isolated" or not usable(r):
                continue
            groups[(r["mode"], r["target"])].append(r)

        for (mode, target), rs in groups.items():
            field = FIELD.get(mode)
            if field is None:
                continue
            nulls = [num(r, field) for r in rs
                     if r["loadout"].split(":")[0] in NULL_SET.get(mode, set())]
            nulls = [n for n in nulls if n is not None]
            if len(nulls) >= 2:
                base = statistics.mean(nulls)
                band = 2 * statistics.pstdev(nulls)
            else:
                base, band = 0.0, 0.0
            scenario = f"{mode.lower()} vs {target.split('.')[-1]}{label_suffix}"

            for r in rs:
                v = num(r, field)
                if v is None:
                    continue
                corrected = v - base
                # Below the error bar is zero, not a small number.
                if abs(corrected) <= band:
                    corrected = 0.0
                name = r["loadout"].split(":")[0]
                m = found.get(name)
                if m is None:
                    m = Measured(name)
                    m.rarity = r.get("rarity", "")
                    m.mode = mode
                    found[name] = m
                prev = m.scores.get(scenario)
                if prev is None or corrected > prev:
                    m.scores[scenario] = corrected
    return found


def band_for(ceiling, mode):
    """Which tier a measured ceiling earns.

    Thresholds are set from the measured spread rather than from theory: the
    strongest thing in the pack lands near +70%, so the tiers divide that range.
    Offensive and defensive numbers are not comparable, so each mode gets its
    own scale, and both are anchored on "does nothing measurable" = COMMON.
    """
    if ceiling is None:
        return None
    if ceiling <= 0:
        return "COMMON"
    if mode == "DEFENSE":
        cuts = [(50, "LEGENDARY"), (30, "EPIC"), (15, "RARE"), (5, "UNCOMMON")]
    else:
        cuts = [(55, "LEGENDARY"), (35, "EPIC"), (18, "RARE"), (8, "UNCOMMON")]
    for threshold, tier in cuts:
        if ceiling >= threshold:
            return tier
    return "COMMON"


# Weights already in EnchantLoot.CHEST_WEIGHT, so the proposal is expressed in
# the units the code uses.
WEIGHT = {"LEGENDARY": 1, "EPIC": 2, "RARE": 4, "UNCOMMON": 8, "COMMON": 12}


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("runs", nargs="+", help="combat census TSVs, one per run")
    args = ap.parse_args()

    for p in args.runs:
        if not os.path.exists(p):
            raise SystemExit("no such run: %s" % p)

    found = collect(args.runs)
    print(f"Read {len(args.runs)} run(s); {len(found)} enchantments measured\n")

    for mode, title in (("MELEE", "WEAPONS"), ("BOW", "BOWS"), ("DEFENSE", "ARMOUR")):
        rows = [m for m in found.values() if m.mode == mode and m.ceiling is not None]
        if not rows:
            continue
        rows.sort(key=lambda m: m.ceiling, reverse=True)
        print(title)
        print("=" * len(title))
        print(f"{'enchant':<20}{'now':<11}{'measured':<11}{'ceiling':>8}  {'weight':>6}  best case")
        print("-" * 96)
        for m in rows:
            if m.name in UTILITY:
                continue
            proposed = band_for(m.ceiling, mode)
            flag = "" if proposed == m.rarity else "  <-- move"
            if m.ceiling > 0:
                best = m.best_scenario
            elif m.ceiling < 0:
                best = "ACTIVELY HARMFUL"
            else:
                best = "nothing measurable"
            print(f"{m.name:<20}{m.rarity:<11}{proposed:<11}{m.ceiling:>+7.1f}  "
                  f"{WEIGHT[proposed]:>6}  {best}{flag}")
        print()

    # A roster that does nothing is the single biggest shipping risk: those are
    # the books a player finds, identifies, and feels cheated by.
    dead = sorted(m.name for m in found.values()
                  if m.ceiling is not None and m.ceiling <= 0
                  and m.name not in UTILITY)
    utility = sorted(m.name for m in found.values() if m.name in UTILITY)
    if utility:
        print("Utility and mobility -- not priceable from combat")
        print("=" * 49)
        print("Their designed effect is not damage dealt or damage stopped, so a combat")
        print("census is the wrong instrument and a zero here says nothing about them.")
        print("Price these on what they do, not on this table.")
        print()
        print("  " + ", ".join(utility))
        print()

    if dead:
        print("Combat enchantments that measured no effect")
        print("=" * 43)
        print("These are meant to deal damage or stop it, and in every situation tested")
        print("they did neither. Each is either mis-tuned, gated behind a condition no")
        print("run has reproduced, or broken -- and a player who finds one at EPIC will")
        print("not be able to tell which. This list is the shipping risk.")
        print()
        for name in dead:
            m = found[name]
            print(f"  {name:<16}{m.rarity:<11}{m.mode.lower()}")


if __name__ == "__main__":
    main()
