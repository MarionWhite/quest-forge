#!/usr/bin/env python3
"""
Read a combat-census campaign and report what each enchantment does to each boss.

A campaign is several `/qfcensus combat` runs, one per boss tier, each fought with
the weapon and armour the quest book puts in a player's hands at that stage. This
reads all of them and answers, per boss:

  * how long the fight takes with no enchantment at all (the control), and how
    much that varies between identical controls -- the instrument's own noise;
  * how much faster each enchantment kills it, from the health-band sweep, so
    enchantments that care how hurt the target is are measured across the whole
    fight rather than at full health;
  * for pairs, whether two enchantments together beat what each does alone --
    multiplicatively, because "30% faster" twice is 51%, not 60%;
  * which results are outliers: far outside their rarity tier, or synergy beyond
    noise.

Nothing here models an enchantment. Every figure is a measured time-to-kill from
the shipping code fighting the pack's own bosses at their median stats.

Usage:
    qfcampaign.py <run.tsv> [<run.tsv> ...] [--markdown out.md] [--csv out.csv]
"""
import argparse
import csv
import math
import os
import statistics
from collections import defaultdict

RARITY_ORDER = ["COMMON", "UNCOMMON", "RARE", "EPIC", "LEGENDARY"]


def num(v):
    if v is None:
        return None
    v = str(v).strip()
    if v in ("", "NaN", "+Inf", "-Inf"):
        return float("inf") if v == "+Inf" else None
    try:
        f = float(v)
    except ValueError:
        return None
    return None if math.isnan(f) else f


def read(path):
    header_lines = []
    data = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            (header_lines if line.startswith("#") else data).append(line)
    rows = list(csv.DictReader(data, delimiter="\t"))
    meta = " ".join(header_lines)
    weapon = ""
    if "Weapon: " in meta:
        weapon = meta.split("Weapon: ", 1)[1].split(". ", 1)[0].split(".\n", 1)[0].strip()
    return rows, weapon, meta


def degenerate(r):
    note = r.get("note") or ""
    return ("swings landed" in note or "pin did not hold" in note
            or "never settled" in note)


class Boss:
    def __init__(self, name, weapon, source):
        self.name = name
        self.weapon = weapon
        self.source = source
        self.target_hp = None
        self.control_ttk = []      # seconds, one per control repeat
        self.bow_ttk = []          # bow controls, a noisier instrument
        self.singles = {}          # (enchant, level) -> row
        self.bow_singles = {}      # enchant -> row
        self.pairs = {}            # frozenset({a, b}) -> row
        self.stacks = {}           # curated 3-enchant loadouts -> row
        self.defense_ctrl = []
        self.defense = {}          # enchant -> row
        self.excluded = []

    @property
    def ttk0(self):
        return Boss._stats(self.control_ttk)[0]

    @property
    def noise_pct(self):
        """Two robust standard deviations of the control repeats, as a share of their median."""
        return Boss._stats(self.control_ttk)[1]

    @staticmethod
    def _stats(ttks):
        """Median and noise (two robust sd, %) of control TTKs.

        Median and MAD rather than mean and sd: a bow control that loses two bands
        to a boss jumping out of its arc would otherwise drag the baseline and
        inflate the noise for every bow row. Never below 2%: a deterministic
        weapon repeats to the hundredth, and a 0.3% effect is not one a player
        can feel or a loot table should price.
        """
        finite = sorted(t for t in ttks if t is not None and not math.isinf(t))
        if not finite:
            return None, None
        m = statistics.median(finite)
        if len(finite) < 2:
            return m, None
        mad = statistics.median(abs(t - m) for t in finite) * 1.4826
        return m, max(2.0, 200.0 * mad / m)

    def speedup(self, row):
        """How much faster than control this row kills, in percent. 0 = no change."""
        ttk = num(row.get("ttk_est_s"))
        if ttk is None or self.ttk0 is None:
            return None
        if math.isinf(ttk):
            return -100.0
        return 100.0 * (1.0 - ttk / self.ttk0)


def collect(paths):
    bosses = {}
    for path in paths:
        rows, weapon, meta = read(path)
        for r in rows:
            target = r.get("target", "")
            key = (target, weapon)
            b = bosses.get(key)
            if b is None:
                b = bosses[key] = Boss(target, weapon, os.path.basename(path))
            if num(r.get("target_hp")):
                b.target_hp = num(r.get("target_hp"))
            if degenerate(r):
                b.excluded.append(r)
                continue
            mode, kind = r.get("mode"), r.get("kind")
            names = [p.strip().split(":")[0] for p in r["loadout"].split("+")]
            if mode == "MELEE":
                if kind == "control":
                    b.control_ttk.append(num(r.get("ttk_est_s")))
                elif kind == "isolated":
                    b.singles[(names[0], int(num(r.get("level")) or 0))] = r
                elif kind == "stacked" and len(names) == 2:
                    b.pairs[frozenset(names)] = r
                elif kind == "stacked":
                    b.stacks[r["loadout"]] = r
            elif mode == "BOW":
                if kind == "control":
                    b.bow_ttk.append(num(r.get("ttk_est_s")))
                elif kind == "isolated":
                    b.bow_singles[names[0]] = r
            elif mode == "DEFENSE":
                if kind == "control":
                    b.defense_ctrl.append(r)
                elif kind == "isolated":
                    b.defense[names[0]] = r
    return bosses


def best_level_row(boss, enchant):
    rows = [(lvl, r) for (e, lvl), r in boss.singles.items() if e == enchant]
    return max(rows)[1] if rows else None


def fmt(v, suffix="%"):
    if v is None:
        return "-"
    if math.isinf(v):
        return "never"
    return f"{v:+.1f}{suffix}"


def report(bosses, md):
    out = []
    w = out.append

    w("# Enchantment campaign\n")
    w("Each boss fought with the weapon its quest stage implies, at median stats, "
      "swept through 100/75/50/25/10% health. **Speed-up** is how much faster the "
      "boss dies than with no enchantment. A result inside the **noise** band "
      "(two standard deviations of identical controls) is not distinguishable "
      "from zero.\n")

    # ---- per-boss summary ----
    w("## Bosses\n")
    w("| Boss | Weapon | HP | Control TTK | Noise | Note |")
    w("|---|---|---:|---:|---:|---|")
    for b in sorted(bosses.values(), key=lambda b: (b.weapon, b.target_hp or 0)):
        note = ""
        if b.ttk0 is None and b.control_ttk:
            note = "**cannot be killed by this weapon** -- every control stalled"
        elif b.excluded:
            note = f"{len(b.excluded)} cell(s) excluded as degenerate"
        hp = f"{b.target_hp:,.0f}" if b.target_hp else "-"
        ttk = f"{b.ttk0:,.0f} s" if b.ttk0 else "never"
        noise = f"±{b.noise_pct:.1f}%" if b.noise_pct is not None else "-"
        w(f"| {b.name} | {b.weapon} | {hp} | {ttk} | {noise} | {note} |")
    w("")

    # ---- singles: enchant x boss matrix ----
    enchants = sorted({e for b in bosses.values() for (e, _) in b.singles})
    rarity = {}
    for b in bosses.values():
        for (e, _), r in b.singles.items():
            rarity[e] = r.get("rarity", "")
    live = [b for b in bosses.values() if b.ttk0]
    if live and enchants:
        w("## Speed-up by boss (max level)\n")
        w("Bold = beyond that boss's noise band. *Italic* = outlier for its rarity "
          "(see below).\n")
        header = "| Enchant | Rarity | " + " | ".join(
            b.name.split(".")[-1] for b in live) + " | Mean |"
        w(header)
        w("|" + "---|" * (len(live) + 3))
        means = {}
        cells = {}
        for e in enchants:
            vals = []
            row_cells = []
            for b in live:
                r = best_level_row(b, e)
                v = b.speedup(r) if r else None
                if v is not None:
                    vals.append(v)
                txt = fmt(v)
                if v is not None and b.noise_pct is not None and abs(v) > b.noise_pct:
                    txt = f"**{txt}**"
                row_cells.append(txt)
            means[e] = statistics.mean(vals) if vals else None
            cells[e] = row_cells
        # Rarity outliers: mean speed-up far from its own tier's median.
        by_tier = defaultdict(list)
        for e, m in means.items():
            if m is not None:
                by_tier[rarity.get(e, "")].append(m)
        outlier = {}
        for e, m in means.items():
            tier = by_tier.get(rarity.get(e, ""), [])
            if m is None or len(tier) < 3:
                continue
            med = statistics.median(tier)
            sd = statistics.pstdev(tier) or 1.0
            z = (m - med) / sd
            if abs(z) >= 1.5:
                outlier[e] = (z, med)
        for e in sorted(enchants, key=lambda e: -(means[e] if means[e] is not None else -1e9)):
            name = f"*{e}*" if e in outlier else e
            w(f"| {name} | {rarity.get(e, '')} | " + " | ".join(cells[e])
              + f" | {fmt(means[e])} |")
        w("")
        if outlier:
            w("### Rarity outliers\n")
            for e, (z, med) in sorted(outlier.items(), key=lambda kv: -abs(kv[1][0])):
                side = "stronger" if z > 0 else "weaker"
                w(f"- **{e}** ({rarity.get(e, '')}): mean {fmt(means[e])}, "
                  f"{abs(z):.1f} sd {side} than the {rarity.get(e, '')} median ({med:+.1f}%).")
            w("")

    # ---- curated stacks ----
    s_live = [b for b in live if b.stacks]
    if s_live:
        w("## Curated stacks\n")
        w("Loadouts a player plausibly ends up holding. A negative figure means the "
          "stack kills **slower** than no enchantment at all.\n")
        w("| Stack | " + " | ".join(b.name.split(".")[-1] for b in s_live) + " |")
        w("|---|" + "---|" * len(s_live))
        for st in sorted({k for b in s_live for k in b.stacks}):
            cells_ = []
            for b in s_live:
                r = b.stacks.get(st)
                v = b.speedup(r) if r else None
                txt = fmt(v)
                if v is not None and b.noise_pct is not None and abs(v) > b.noise_pct:
                    txt = f"**{txt}**"
                cells_.append(txt)
            w(f"| {st} | " + " | ".join(cells_) + " |")
        w("")

    # ---- pairs ----
    pair_rows = []
    for b in live:
        for pair, r in b.pairs.items():
            a, c = sorted(pair)
            ra, rc = best_level_row(b, a), best_level_row(b, c)
            ttk_ab = num(r.get("ttk_est_s"))
            if not (ra and rc and ttk_ab and b.ttk0):
                continue
            ta, tc = num(ra.get("ttk_est_s")), num(rc.get("ttk_est_s"))
            if not ta or not tc or math.isinf(ta) or math.isinf(tc) or math.isinf(ttk_ab):
                continue
            # Independent enchantments multiply: each removes its share of what
            # is left. Synergy is how far the pair beats that.
            expected = b.ttk0 * (ta / b.ttk0) * (tc / b.ttk0)
            synergy = 100.0 * (expected / ttk_ab - 1.0)
            pair_rows.append((synergy, b, a, c, b.speedup(r), expected, ttk_ab))
    if pair_rows:
        w("## Pairs: synergy beyond independence\n")
        w("Synergy = how much faster the pair kills than two independent "
          "enchantments would. Positive = they feed each other; negative = they "
          "overlap. Only results beyond the boss's noise band are listed.\n")
        w("| Pair | Boss | Pair speed-up | Synergy |")
        w("|---|---|---:|---:|")
        shown = 0
        for syn, b, a, c, sp, exp, act in sorted(pair_rows, key=lambda t: -abs(t[0])):
            if b.noise_pct is not None and abs(syn) <= b.noise_pct:
                continue
            w(f"| {a} + {c} | {b.name.split('.')[-1]} | {fmt(sp)} | **{fmt(syn)}** |")
            shown += 1
            if shown >= 60:
                break
        if shown == 0:
            w("| (none beyond noise) | | | |")
        w("")

    # ---- bow ----
    b_live = [b for b in bosses.values() if b.bow_singles and Boss._stats(b.bow_ttk)[0]]
    if b_live:
        w("## Bow speed-up by boss\n")
        w("Bow cells fight a moving boss from ten blocks and miss some arrows, so "
          "their noise band is wider; it is shown per boss.\n")
        w("| Enchant | " + " | ".join(
            f"{b.name.split('.')[-1]} (±{(Boss._stats(b.bow_ttk)[1] or 0):.0f}%)" for b in b_live) + " |")
        w("|---|" + "---|" * len(b_live))
        for e in sorted({e for b in b_live for e in b.bow_singles}):
            cells_ = []
            for b in b_live:
                r = b.bow_singles.get(e)
                m, noise = Boss._stats(b.bow_ttk)
                t = num(r.get("ttk_est_s")) if r else None
                if t is None:
                    cells_.append("-")
                    continue
                v = -100.0 if math.isinf(t) else 100.0 * (1.0 - t / m)
                txt = fmt(v)
                if noise is not None and abs(v) > noise:
                    txt = f"**{txt}**"
                cells_.append(txt)
            w(f"| {e} | " + " | ".join(cells_) + " |")
        w("")

    # ---- defence ----
    d_live = [b for b in bosses.values() if b.defense_ctrl]
    if d_live:
        w("## Armour: damage taken from each boss's real melee\n")
        w("Damage reduction versus the same armour with no custom enchantment, over "
          "sixty of the boss's own hits. A boss whose control row took nothing is one "
          "the tier's armour already makes the player immune to; no armour "
          "enchantment can show anything there.\n")
        w("| Enchant | " + " | ".join(
            f"{b.name.split('.')[-1]} ({statistics.mean(num(c.get('damage_taken')) or 0 for c in b.defense_ctrl):.0f} dmg)"
            for b in d_live) + " |")
        w("|---|" + "---|" * len(d_live))
        names = sorted({e for b in d_live for e in b.defense})
        for e in names:
            cells_ = []
            for b in d_live:
                r = b.defense.get(e)
                base = statistics.mean(num(c.get("damage_taken")) or 0 for c in b.defense_ctrl)
                if not r or base <= 0:
                    cells_.append("-" if not r else "immune")
                    continue
                v = num(r.get("damage_taken"))
                red = 100.0 * (1.0 - v / base) if v is not None else None
                txt = fmt(red)
                if red is not None and abs(red) >= 5.0:
                    txt = f"**{txt}**"
                cells_.append(txt)
            w(f"| {e} | " + " | ".join(cells_) + " |")
        w("")

    text = "\n".join(out)
    if md:
        with open(md, "w", encoding="utf-8") as fh:
            fh.write(text)
        print(f"wrote {md}")
    else:
        print(text)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("runs", nargs="+")
    ap.add_argument("--markdown")
    args = ap.parse_args()
    report(collect(args.runs), args.markdown)


if __name__ == "__main__":
    main()
