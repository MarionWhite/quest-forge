#!/usr/bin/env python3
"""
Build the enchant effects table from the combat-census campaign.

This is the table decision 0005 (P10) asks for: one row per enchantment and
level, and one per measured pair, saying what the enchantment does in a real
fight -- how much faster the boss dies, on which bosses, how many seconds that
is, how much less damage the wielder takes -- and a verdict on whether that
effect is proportionate to the rarity the registry declares.

Nothing here models an enchantment. Every figure is read from the census TSVs
that `run_campaign.py` leaves in the campaign directory (one folder per job,
`T<n>-<boss>-<phase>`), and every number is paired against that job's own
controls, as `qfcampaign.py` does. The shared primitives (TSV reader, health-band
integration, the degenerate-cell rule, the control noise band) are imported from
qfcampaign so there is one definition of each.

Rerunnable. Point it at the campaign directory and at any directory of re-test
jobs; a job folder in a later root replaces the same-named job from an earlier
one, so the targeted re-runs after P1/P2/P7/P8 slot in without touching the
original campaign:

    py -3.10 -I tools/balance/effects_table.py
    py -3.10 -I tools/balance/effects_table.py C:\\qfs\\campaign C:\\qfs\\campaign-retest

Declared rarity is read from the qf-content registry source (the `super(id,
"qf.<name>", Rarity.<R>, ...)` lines), so the P9 moves change the verdicts the
moment they are committed. The rarity the census jar carried is kept alongside.

Outputs docs/reference/enchant-effects.md and enchant-effects.json.
"""
import argparse
import datetime
import json
import math
import os
import re
import statistics
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import qfcampaign as camp  # noqa: E402  (read, num, phase_ttk, phase_end, degenerate, Boss._stats)

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
DEFAULT_CAMPAIGN = r"C:\qfs\campaign"
DEFAULT_REGISTRY = os.path.join(REPO, "mods", "qf-content", "src", "main", "java", "com",
                                "questforge", "content", "ench", "enchants")
DEFAULT_MD = os.path.join(REPO, "docs", "reference", "enchant-effects.md")
DEFAULT_JSON = os.path.join(REPO, "docs", "reference", "enchant-effects.json")

RARITIES = ["COMMON", "UNCOMMON", "RARE", "EPIC", "LEGENDARY"]
TIERS = ["T1", "T2", "T3", "T4"]

# ---------------------------------------------------------------------------
# Policy: which bosses the census can be trusted on, and why.
# Mirrors enchantment-combat-results.md §1 and §7. Edit here when a re-run
# changes a boss's standing; nothing else in the file knows a boss by name.
# ---------------------------------------------------------------------------
BOSS_POLICY = {
    # status: trusted (default) | excluded | shown | capped | apart | defence-only
    "TragicMC.Apis": dict(status="excluded", why="controls biased: placebos +34% (results §7.1)"),
    "witchery.leonard": dict(status="excluded", why="last-10% band noise ±34% (results §7.2)"),
    "witchery.lordoftorment": dict(status="shown", cap="5 raw before its event",
                                   why="controls biased −14%; TTK runs to 50% only (results §7.3)"),
    "TragicMC.Kitsune": dict(status="defence-only", why="immune to weapons by design"),
    "Mobzilla": dict(status="capped", cap="750/hit"),
    "The_King": dict(status="capped", cap="750/hit"),
    "The_Queen": dict(status="capped", cap="750/hit"),
    "demonmobs.rahovart": dict(status="apart", cap="25/hit", why="Lycanites damageMax; T3 and T4 jobs identical"),
    "legends.Godzilla": dict(status="apart", why="uncapped T4; dies in 8 s to the Royal sword"),
    "witchery.babayaga": dict(cap="15/hit"),
    "TwilightForest.Twilight_Lich": dict(note="shields held down"),
    "TragicMC.Enyvil": dict(note="struck at the eye"),
}
# Armour cells that cannot be read (results §5).
DEFENCE_EXCLUDED = {
    "TragicMC.Enyvil": "defence controls vary ±32 damage",
    "witchery.death": "its hits ignore armour: 172 damage whatever the enchantment",
}
# Wielder-health cells that are drift, not measurement (results §7.4).
WOUNDED_INVALID = {"witchery.death": "probe driven to 1 HP in every cell, controls included"}

# Ten enchantments with no mechanism against a boss in the census. Their spread
# on each boss is the instrument's real noise; the threshold used for every
# significance mark is max(control band, 2 sd of the placebos).
PLACEBOS = ["tracker", "rally", "daze", "decapitate", "demonforged", "soulbound",
            "timber", "trade", "jammer", "getoffme"]

# One boss per tier for the "seconds saved" columns. Mobzilla is capped and is
# shown as the T4 reference because that is the T4 the pack has.
REFERENCE = [("T1", "TwilightForest.Naga"), ("T2", "WitherBoss"), ("T3", "Mantis"), ("T4", "Mobzilla")]

# ---------------------------------------------------------------------------
# Verdict bands: the speed-up (weapons, trusted mean at top level) or damage
# reduction (armour, T1-T2 mean) that each declared rarity should buy. These are
# the proposal in docs/design/enchant-rarity-plan.md; change them there and here.
# ---------------------------------------------------------------------------
BANDS = {
    "weapon": {"COMMON": (None, 5), "UNCOMMON": (5, 12), "RARE": (12, 20),
               "EPIC": (20, 30), "LEGENDARY": (30, None)},
    "armour": {"COMMON": (None, 5), "UNCOMMON": (5, 10), "RARE": (10, 20),
               "EPIC": (20, 30), "LEGENDARY": (30, None)},
}
NO_EFFECT_MAX = 5.0        # |effect| at or below this, with few significant bosses, is "no observable effect"
NO_EFFECT_SIG_FRAC = 0.25  # ... "few" = significant on under a quarter of the trusted bosses
T4_OUTLIER_MARGIN = 10.0   # T4-capped mean this far above the band's ceiling is flagged

V_PROP = "proportionate"
V_STRONG = "too strong for rarity"
V_WEAK = "too weak"
V_NONE = "no observable effect"
V_UNTEST = "untestable by this census (utility/PvP)"
V_HARM = "harmful: loses fights"
V_UNMEASURED = "not measured"

# Enchantments the census has no cell for. The reason is printed next to the
# verdict so the reader knows what would be needed to measure it.
UNTESTABLE = {
    # tools
    "magnetize": "tool: drops to inventory", "haste": "tool: dig speed", "excavate": "tool: vein mining",
    "timber": "tool: tree felling", "tunneler": "tool: area mining", "sieve": "tool: bonus drops",
    "bountiful": "tool: drop doubling", "transmuter": "tool: bonus ore", "oldreliable": "tool: XP",
    "ecofriendly": "tool: refund on break", "fortune_v": "tool: Fortune", "fortune_x": "tool: Fortune",
    "bold": "tool: doubles Fortune", "prospector": "tool: ore HUD", "torchlight": "tool: light",
    # gear upkeep
    "mending": "durability from XP", "demonforged": "unbreakable", "soulbound": "survives death",
    # PvP-only or player-only effects
    "trade": "players only", "jammer": "players only (screen effect)", "polarize": "attacker's gear (PvP)",
    "tracker": "client outline", "rally": "flourish; music unimplemented",
    # needs a player input or event the probe never produces
    "crushingblow": "needs the wielder sneaking", "getoffme": "needs right-click held",
    "feast": "heals on kill; banded cells never kill", "lich": "absorption on kill; banded cells never kill",
    "sacrifice": "fires on a lethal hit; the census holds the wielder alive",
    "decapitate": "head drop on kill", "disarm": "bosses hold no item",
    "daze": "spins the target; cosmetic on mobs", "reach": "range; the probe stands in range",
    # movement and utility armour
    "flippers": "swim speed", "frog": "jump", "deft": "speed", "frostpath": "freezes water",
    "nightsight": "night vision", "camouflage": "stops a mob acquiring you; the census assigns the target",
    "stonehide": "falls and explosions only", "cleansing": "strips a debuff; the census strips DoTs after each hit",
    "regrowth": "out-of-combat regen; see hits survived", "vigor": "+max health; see hits survived",
    "rebound": "knockback on the attacker; the census pins the target", "reflect": "knockback on the attacker",
    # bows the census fires but whose effect is positional
    "instanttransmission": "teleport to the arrow", "soulentwine": "swap positions",
    "penetrating": "passes through targets (3 pinned targets)",
    "ricochet": "second arrow to another target", "bola": "slowness; the target is pinned",
}

# What each enchantment does, in one line, from enchantment-ground-truth.md and
# enchantment-tuning.md. Shown next to the numbers so the table reads on its own.
EFFECTS = {
    "accelerant": "12%: every debuff on the target +L amplifier (cap IV/VI/VIII), +2 s/level; wither capped at IV",
    "affliction": "per piece ~1-4%: 7 debuffs on the attacker",
    "alpha": "3/6/9%: summons a tamed wolf for 30/40/50 s",
    "arc": "15/20/25%: 35% of the hit to up to L others within 5 blocks",
    "assassinate": "x1.25/1.50/1.75 while the target is not targeting you",
    "bastion": "3/6/9%: summons an iron golem for 30/40/50 s, aimed at the target",
    "berserk": "your damage x(1 + 0.9 x your missing health) at III; nothing at full health",
    "blind": "8/16/24%: Blindness 4/5/6 s",
    "bola": "arrow: Slowness I-III 6/8/10 s",
    "bold": "doubles vanilla Fortune",
    "bountiful": "11/22/33%: doubles drops when the tool has no Fortune",
    "bulwark": "chest: x(1 - 0.10 x L x your missing-health fraction)",
    "camouflage": "legs 10/20/30%: a mob that targets you forgets you",
    "cleansing": "legs 10/20/30%: strips one debuff when hit",
    "cockroach": "chest: Resistance L+1 for 5/6/7 s after a hit leaves you at <=1 heart; 60 s cooldown",
    "colossus": "6/9/12%: +2.5% x L of the target's max health, capped at 4x the hit",
    "cripple": "10/20/30%: target deals 10/15/20% less for 6/8/10 s",
    "crushingblow": "sneaking, 10 s cooldown: x1.6/2.2/2.8",
    "cultist": "8/16/24%: x2 damage; you pay 10% max health per level as physical damage",
    "daze": "10/20/30%: spins the target 180 degrees",
    "decapitate": "15/30/40%: vanilla head drop",
    "deft": "boots: Speed I/II",
    "demonforged": "unbreakable",
    "disarm": "4/8/12%: knocks the held item out",
    "ecofriendly": "refund on break",
    "excalibur": "+4 flat; while held Strength I (x2.3), Resistance I, Speed I",
    "excavate": "vein mining 8/16/24",
    "executioner": "x(1 + 0.25 x L x target's missing health), up to x1.75",
    "feast": "heal 1/2/3 hearts on kill",
    "flippers": "swim speed",
    "fortune_v": "Fortune V",
    "fortune_x": "Fortune X",
    "frog": "boots: Jump Boost I-III",
    "frostbite": "20/30/40%: Slowness I-III 1.5/2.0/2.5 s",
    "frostpath": "boots: freezes water underfoot",
    "getoffme": "right-click held, 10 min cooldown: launch",
    "haste": "Haste I-III",
    "homing": "arrows steer to the nearest target within 9/12/15 blocks",
    "instanttransmission": "teleport to the arrow, 3 s cooldown",
    "jammer": "players: downsamples their screen",
    "killingblow": "0.1/0.2/0.3%: sets target health to 0",
    "lich": "Absorption I-III for 20/25/30 s on kill",
    "magnetize": "drops to inventory",
    "mending": "2 durability per XP",
    "momentum": "+0.5 x L per consecutive hit, 8 stacks, 2 s window: up to +3.5/7/10.5 flat",
    "multistrike": "every proc enchantment on the item rolls twice",
    "necromancer": "3/6/9%: summons a zombie or skeleton for 30/40/50 s",
    "nightsight": "helmet: night vision in the dark",
    "oldreliable": "XP x(1 + wear x L)",
    "penetrating": "arrow passes through up to L targets",
    "piercing": "arrow x1.15/1.30/1.45",
    "poisonous": "10/20/30%: Poison I 4/5/6 s with venom 4% x L of the hit per second",
    "polarize": "0.01%/level/piece: wipes the attacker's enchantments",
    "prospector": "ore HUD",
    "rage": "5/10/15%: Strength I (x2.3) for 4/6/8 s",
    "rally": "flourish on the opening blow",
    "reach": "+1 block range per level",
    "rebound": "per piece 2/4/6%: shoves the attacker back",
    "reflect": "per piece 8/12/16%: launches the attacker",
    "regrowth": "legs: Regeneration I-III after 10 s out of combat",
    "ricochet": "second arrow to the nearest target within 8 blocks",
    "riposte": "+1.5 x L flat while hurt in the last 3 s",
    "roulette": "every hit x2 or x0.5 (EV x1.25)",
    "rupture": "25/35/45%: bleed 4% of the hit per stack per second, L+1 stacks, 5/6/7 s, ignores armour",
    "sacrifice": "per piece: survive a lethal hit at half health; destroys the piece",
    "sieve": "2/4/6%: bonus drop from stone and dirt",
    "soulbound": "kept through death",
    "soulentwine": "arrow: swap positions with the target",
    "stonehide": "per piece 3% x L: falls and explosions only",
    "sunder": "10/20/30%: target deals 5/10/15% less + Mining Fatigue, 4/5/6 s",
    "suplex": "10/15/20%: throws the target up (fall damage)",
    "tank": "chest: 11/22/33% less damage taken, permanent Slowness I",
    "timber": "fells the tree",
    "torchlight": "light at head height",
    "tracker": "outlines living things through walls",
    "trade": "2/4/6%: swaps held items (players only)",
    "transmuter": "3/6/9%: a second ore on ore break",
    "tunneler": "3x3 / 5x5 / 7x7 mining",
    "turtle": "per piece x0.67 while holding no weapon: 80% for a set",
    "venomous": "8/16/24%: Poison II 7/9/11 s with venom 5.8% x L of the hit per second, target -10% damage",
    "vigor": "chest: +4 max health per level",
}


# ---------------------------------------------------------------------------
# Registry: declared rarity, category and max level from the Java source.
# ---------------------------------------------------------------------------
SUPER_RE = re.compile(
    r'super\(\s*id\s*,\s*"qf\.([a-z_]+)"\s*,\s*(?:Rarity\.)?([A-Z]+)\s*,'
    r'(?:\s*(?:EnchantCategory\.)?([A-Z_]+)\s*,)?\s*(\d+)\s*\)')

GROUP_OF = {
    "WEAPON": "weapon", "SWORD": "weapon", "BOW": "bow",
    "ARMOR": "armour", "HELMET": "armour", "CHESTPLATE": "armour", "LEGGINGS": "armour", "BOOTS": "armour",
    "TOOL": "tool", "PICKAXE": "tool", "DIGGER": "tool", "SHOVEL": "tool", "AXE": "tool",
    "ANY": "any",
}


def read_registry(path):
    reg = {}
    if not os.path.isdir(path):
        return reg
    for fn in sorted(os.listdir(path)):
        if not fn.endswith(".java"):
            continue
        with open(os.path.join(path, fn), encoding="utf-8") as fh:
            for m in SUPER_RE.finditer(fh.read()):
                name, rarity, cat, lvl = m.group(1), m.group(2), m.group(3), int(m.group(4))
                cat = cat or "WEAPON"   # the SummonEnchant constructor fixes the category
                reg[name] = dict(rarity=rarity, category=cat, group=GROUP_OF.get(cat, "other"),
                                 max_level=lvl, source=fn)
    return reg


# ---------------------------------------------------------------------------
# Campaign jobs
# ---------------------------------------------------------------------------
JOB_RE = re.compile(r"^(T\d)-(.+)-(singles|pairs|levels|hp[0-9.]+)$")


class Job:
    def __init__(self, name, path, tier, boss, phase):
        self.name, self.path, self.tier, self.boss, self.phase = name, path, tier, boss, phase
        self.rows, self.procs, self.weapon, self.options = [], [], "", ""
        self.seconds = None
        self.excluded = 0
        self.hp = 1.0
        self.ctrl = {}   # mode -> (median ttk, noise %, n) ; DEFENSE -> (mean damage taken, hits survived, probe hp, n)

    def load(self):
        p = os.path.join(self.path, "qfcontent-census-combat.tsv")
        rows, weapon, meta = camp.read(p)
        self.weapon = weapon
        m = re.search(r"Options: (.*?)\. Weapon:", meta)
        self.options = m.group(1) if m else ""
        m = re.search(r"\bhp=([0-9.]+)", self.options)
        self.hp = float(m.group(1)) if m else 1.0
        end = camp.phase_end(self.boss)
        kept = []
        for r in rows:
            if end is not None:
                t = camp.phase_ttk(r, end)
                if t is not None:
                    r["ttk_est_s"] = "+Inf" if math.isinf(t) else str(t)
            if camp.degenerate(r):
                self.excluded += 1
                continue
            kept.append(r)
        self.rows = kept
        fj = os.path.join(self.path, "finished.json")
        if os.path.exists(fj):
            with open(fj, encoding="utf-8") as fh:
                self.seconds = json.load(fh).get("seconds")
        pp = os.path.join(self.path, "qfcontent-census-combat-procs.tsv")
        if os.path.exists(pp):
            self.procs, _, _ = camp.read(pp)
        # Controls per mode.
        by_mode = defaultdict(list)
        for r in self.rows:
            if r.get("kind") == "control":
                by_mode[r["mode"]].append(r)
        for mode, rs in by_mode.items():
            if mode == "DEFENSE":
                taken = [camp.num(r.get("damage_taken")) or 0.0 for r in rs]
                surv = [camp.num(r.get("hits_survived")) or 0.0 for r in rs]
                hpmin = [camp.num(r.get("probe_hp_min")) for r in rs if camp.num(r.get("probe_hp_min")) is not None]
                self.ctrl[mode] = (statistics.mean(taken), statistics.mean(surv),
                                   statistics.mean(hpmin) if hpmin else None, len(rs))
            else:
                ttks = [camp.num(r.get("ttk_est_s")) for r in rs]
                med, noise = camp.Boss._stats(ttks)
                self.ctrl[mode] = (med, noise, len(rs))

    def target_hp(self):
        for r in self.rows:
            v = camp.num(r.get("target_hp"))
            if v:
                return v
        return None

    def speedup(self, row, mode="MELEE"):
        c = self.ctrl.get(mode)
        if not c or c[0] is None:
            return None
        ttk = camp.num(row.get("ttk_est_s"))
        if ttk is None:
            return None
        if math.isinf(ttk):
            return -100.0
        return 100.0 * (1.0 - ttk / c[0])


def load_jobs(roots):
    jobs, notes = {}, []
    for root in roots:
        if not os.path.isdir(root):
            notes.append(f"root not found: {root}")
            continue
        for d in sorted(os.listdir(root)):
            m = JOB_RE.match(d)
            path = os.path.join(root, d)
            if not m or not os.path.isdir(path):
                continue
            if not os.path.exists(os.path.join(path, "qfcontent-census-combat.tsv")):
                notes.append(f"{d}: no combat TSV, skipped")
                continue
            fj = os.path.join(path, "finished.json")
            if os.path.exists(fj):
                with open(fj, encoding="utf-8") as fh:
                    fin = json.load(fh)
                if not fin.get("finished", True):
                    notes.append(f"{d}: finished.json says not finished, skipped")
                    continue
            job = Job(d, path, m.group(1), m.group(2), m.group(3))
            job.load()
            if d in jobs:
                notes.append(f"{d}: replaced by the copy in {root}")
            jobs[d] = job
    return jobs, notes


def names_of(loadout):
    return [p.strip().split(":")[0] for p in loadout.split("+")]


def level_of(row):
    v = camp.num(row.get("level"))
    return int(v) if v else None


def mean(xs):
    xs = [x for x in xs if x is not None]
    return statistics.mean(xs) if xs else None


def sd(xs):
    xs = [x for x in xs if x is not None]
    return statistics.stdev(xs) if len(xs) > 1 else None


def f1(v, sign=True, suffix=""):
    if v is None:
        return "–"
    if isinstance(v, float) and math.isinf(v):
        return "never"
    return (f"{v:+.1f}" if sign else f"{v:.1f}") + suffix


def f0(v, sign=True):
    if v is None:
        return "–"
    if isinstance(v, float) and math.isinf(v):
        return "never"
    return f"{v:+.0f}" if sign else f"{v:.0f}"


def short(boss):
    return boss.split(".")[-1].replace("_", " ")


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------
def base_verdict(v):
    """Verdict without its ' (T4 only)' qualifier."""
    return v[:-len(" (T4 only)")] if v.endswith(" (T4 only)") else v


class Analysis:
    def __init__(self, jobs, registry):
        self.jobs = jobs
        self.registry = registry
        self.bosses = {}          # boss -> info dict
        self.singles = defaultdict(dict)    # boss -> (ench, lvl) -> speed-up (singles job, melee)
        self.single_ttk = defaultdict(dict)  # boss -> ench -> (ttk0, ttk) top level
        self.probe_hp = defaultdict(dict)   # boss -> ench -> probe_hp_min (melee singles), '(control)' -> mean
        self.bow = defaultdict(dict)        # boss -> ench -> speed-up vs bow controls
        self.defence = defaultdict(dict)    # boss -> ench -> dict
        self.defence_levels = defaultdict(lambda: defaultdict(dict))  # boss -> ench -> lvl -> DR
        self.levels = defaultdict(lambda: defaultdict(dict))          # boss -> ench -> lvl -> speed-up
        self.replicates = defaultdict(lambda: defaultdict(list))      # boss -> ench -> [speed-ups]
        self.pairs = defaultdict(dict)      # boss -> frozenset -> dict
        self.stacks = defaultdict(dict)     # boss -> loadout -> speed-up (singles job)
        self.wounded = defaultdict(lambda: defaultdict(dict))  # boss -> hp -> loadout -> speed-up
        self.procs = defaultdict(lambda: defaultdict(lambda: [0, 0, None]))  # ench -> trigger -> [rolls, fires, expected]
        self.deep = set()

    # -- collection -----------------------------------------------------
    def collect(self):
        for name, job in sorted(self.jobs.items()):
            if job.phase == "singles":
                self._singles(job)
            elif job.phase == "levels":
                self.deep.add(job.boss)
                self._levels(job)
            elif job.phase == "pairs":
                self.deep.add(job.boss)
                self._pairs(job)
            elif job.phase.startswith("hp"):
                self._wounded(job)
            if job.phase == "singles":
                for r in job.procs:
                    e, t = r.get("enchant"), r.get("trigger")
                    if not e or not t:
                        continue
                    cell = self.procs[e][t]
                    cell[0] += int(camp.num(r.get("rolls")) or 0)
                    cell[1] += int(camp.num(r.get("fires")) or 0)
                    cell[2] = camp.num(r.get("expected_pct"))
        self._thresholds()

    def _boss_info(self, job):
        b = self.bosses.get(job.boss)
        if b is None:
            pol = BOSS_POLICY.get(job.boss, {})
            b = self.bosses[job.boss] = dict(
                boss=job.boss, short=short(job.boss), tier=job.tier, hp=job.target_hp(),
                weapon=job.weapon, status=pol.get("status", "trusted"), cap=pol.get("cap"),
                why=pol.get("why") or pol.get("note"), control_ttk=None, band=None,
                placebo_median=None, placebo_sd=None, threshold=None, bow_ttk=None, bow_band=None,
                defence_control=None, defence_hits=None, defence_probe_hp=None, defence_measured=False, jobs=[])
        b["jobs"].append(job.name)
        if job.boss == "demonmobs.rahovart" and job.tier == "T4":
            b["tier"] = "T3/T4"
        return b

    def _singles(self, job):
        b = self._boss_info(job)
        if job.boss == "demonmobs.rahovart" and job.tier == "T4":
            return   # identical to the T3 job (25/hit cap); the T3 job is the one shown
        c = job.ctrl.get("MELEE")
        if c and c[0] is not None:
            b["control_ttk"], b["band"] = c[0], c[1]
        cb = job.ctrl.get("BOW")
        if cb and cb[0] is not None:
            b["bow_ttk"], b["bow_band"] = cb[0], cb[1]
        cd = job.ctrl.get("DEFENSE")
        if cd:
            b["defence_control"], b["defence_hits"], b["defence_probe_hp"] = cd[0], cd[1], cd[2]
            b["defence_measured"] = cd[0] > 0
        ctrl_hp = [camp.num(r.get("probe_hp_min")) for r in job.rows
                   if r.get("kind") == "control" and r.get("mode") == "MELEE"]
        self.probe_hp[job.boss]["(control)"] = mean(ctrl_hp)
        for r in job.rows:
            kind, mode = r.get("kind"), r.get("mode")
            names = names_of(r["loadout"])
            if mode == "MELEE" and kind == "isolated":
                e, lvl = names[0], level_of(r)
                v = job.speedup(r)
                self.singles[job.boss][(e, lvl)] = v
                self.single_ttk[job.boss][e] = (c[0] if c else None, camp.num(r.get("ttk_est_s")))
                self.probe_hp[job.boss][e] = camp.num(r.get("probe_hp_min"))
                self.replicates[job.boss][e].append(v)
            elif mode == "MELEE" and kind == "stacked":
                self.stacks[job.boss][r["loadout"]] = job.speedup(r)
            elif mode == "BOW" and kind == "isolated":
                self.bow[job.boss][names[0]] = job.speedup(r, "BOW")
            elif mode == "DEFENSE" and kind == "isolated":
                self._defence_row(job, r, names[0], level_of(r), top=True)

    def _defence_row(self, job, r, e, lvl, top):
        cd = job.ctrl.get("DEFENSE")
        if not cd:
            return
        base, base_hits, base_hp = cd[0], cd[1], cd[2]
        taken = camp.num(r.get("damage_taken"))
        surv = camp.num(r.get("hits_survived"))
        hpmin = camp.num(r.get("probe_hp_min"))
        dr = 100.0 * (1.0 - taken / base) if (base and base > 0 and taken is not None) else None
        if top:
            self.defence[job.boss][e] = dict(
                dr=dr, taken=taken, base=base,
                hits_delta=(surv - base_hits) if (surv is not None and base_hits is not None) else None,
                probe_hp_min=hpmin, probe_hp_control=base_hp, level=lvl)
        else:
            self.defence_levels[job.boss][e][lvl] = dr

    def _levels(self, job):
        self._boss_info(job)
        for r in job.rows:
            kind, mode = r.get("kind"), r.get("mode")
            if kind != "isolated":
                continue
            e, lvl = names_of(r["loadout"])[0], level_of(r)
            if mode == "MELEE":
                v = job.speedup(r)
                self.levels[job.boss][e][lvl] = v
                reg = self.registry.get(e)
                if reg and lvl == reg["max_level"]:
                    self.replicates[job.boss][e].append(v)
            elif mode == "DEFENSE":
                self._defence_row(job, r, e, lvl, top=False)

    def _pairs(self, job):
        self._boss_info(job)
        for r in job.rows:
            if r.get("mode") != "MELEE":
                continue
            names = names_of(r["loadout"])
            if r.get("kind") == "isolated":
                self.replicates[job.boss][names[0]].append(job.speedup(r))
        c = job.ctrl.get("MELEE")
        for r in job.rows:
            if r.get("mode") != "MELEE" or r.get("kind") != "stacked":
                continue
            names = names_of(r["loadout"])
            if len(names) != 2:
                continue
            self.pairs[job.boss][frozenset(names)] = dict(
                loadout=r["loadout"], speedup=job.speedup(r), ttk=camp.num(r.get("ttk_est_s")),
                ttk0=c[0] if c else None, noise=c[1] if c else None)

    def _wounded(self, job):
        self._boss_info(job)
        for r in job.rows:
            if r.get("mode") != "MELEE" or r.get("kind") == "control":
                continue
            self.wounded[job.boss][job.hp][r["loadout"]] = job.speedup(r)

    def _thresholds(self):
        for boss, b in self.bosses.items():
            vals = []
            for p in PLACEBOS:
                v = self.single(boss, p)
                if v is not None and not math.isinf(v):
                    vals.append(v)
            if len(vals) >= 3:
                b["placebo_median"] = statistics.median(vals)
                b["placebo_sd"] = statistics.pstdev(vals)
            if b["band"] is None and not vals:
                continue
            b["threshold"] = max(b["band"] or 0.0, 2.0 * (b["placebo_sd"] or 0.0))

    # -- derived -----------------------------------------------------------
    def trusted_bosses(self):
        return [k for k, b in self.bosses.items() if b["status"] == "trusted" and b["control_ttk"]]

    def tier_bosses(self, tier):
        return [k for k in self.trusted_bosses() if self.bosses[k]["tier"] == tier]

    def capped_bosses(self):
        return [k for k, b in self.bosses.items() if b["status"] == "capped" and b["control_ttk"]]

    def sig(self, boss, v):
        t = self.bosses[boss].get("threshold")
        return v is not None and t is not None and abs(v) > t

    def top_level(self, e):
        reg = self.registry.get(e)
        if reg:
            return reg["max_level"]
        lv = [l for b in self.singles.values() for (n, l) in b if n == e and l]
        return max(lv) if lv else None

    def single(self, boss, e, lvl=None):
        lvl = lvl or self.top_level(e)
        v = self.singles[boss].get((e, lvl))
        if v is None:
            for (n, l), vv in self.singles[boss].items():
                if n == e:
                    v = vv
        return v

    def enchant_rows(self):
        names = set(self.registry)
        for b in self.singles.values():
            names.update(n for (n, _) in b)
        for b in self.defence.values():
            names.update(b)
        for b in self.bow.values():
            names.update(b)
        return [self.enchant_row(e) for e in sorted(names)]

    def enchant_row(self, e):
        reg = self.registry.get(e, {})
        group = reg.get("group") or self._guess_group(e)
        census_rarity = self._census_rarity(e)
        row = dict(name=e, category=reg.get("category"), group=group,
                   rarity=reg.get("rarity") or census_rarity, census_rarity=census_rarity,
                   max_level=reg.get("max_level") or self.top_level(e), effect=EFFECTS.get(e, ""),
                   retiered=(reg.get("rarity") is not None and census_rarity is not None
                             and reg.get("rarity") != census_rarity))
        trusted = self.trusted_bosses()
        per_boss = {b: self.single(b, e) for b in self.bosses if self.bosses[b]["control_ttk"]}
        row["per_boss"] = {b: dict(speedup=v, sig=self.sig(b, v), tier=self.bosses[b]["tier"],
                                   status=self.bosses[b]["status"])
                           for b, v in per_boss.items() if v is not None}
        tv = [per_boss[b] for b in trusted if per_boss.get(b) is not None]
        row["trusted_mean"] = mean(tv)
        row["trusted_sd"] = sd(tv)
        row["trusted_n"] = len(tv)

        def sig_pos(b):
            return per_boss.get(b) is not None and self.sig(b, per_boss[b]) and per_boss[b] > 0

        def sig_neg(b):
            return per_boss.get(b) is not None and self.sig(b, per_boss[b]) and per_boss[b] < 0

        row["sig_pos"] = sum(1 for b in trusted if sig_pos(b))
        row["sig_neg"] = sum(1 for b in trusted if sig_neg(b))
        row["sig_on"] = sorted(short(b) for b in trusted if sig_pos(b))
        row["sig_loss_on"] = sorted(short(b) for b in self.bosses
                                    if sig_neg(b) and self.bosses[b]["status"] != "excluded")
        row["tier_mean"] = {t: mean([per_boss[b] for b in self.tier_bosses(t) if per_boss.get(b) is not None]) for t in TIERS}
        row["tier_n"] = {t: len([b for b in self.tier_bosses(t) if per_boss.get(b) is not None]) for t in TIERS}
        row["tier_sig"] = {t: sum(1 for b in self.tier_bosses(t) if sig_pos(b)) for t in TIERS}
        row["t4_capped_mean"] = mean([per_boss[b] for b in self.capped_bosses() if per_boss.get(b) is not None])
        row["t4_capped_sig"] = sum(1 for b in self.capped_bosses() if sig_pos(b))
        row["rahovart"] = per_boss.get("demonmobs.rahovart")
        row["godzilla"] = per_boss.get("legends.Godzilla")
        row["replicate_sd"] = {short(b): sd(self.replicates[b][e]) for b in sorted(self.deep)
                               if len(self.replicates[b][e]) > 1}
        refs = {}
        for tier, b in REFERENCE:
            tt = self.single_ttk.get(b, {}).get(e)
            if tt and tt[0]:
                ttk0, ttk = tt
                dead = ttk is None or math.isinf(ttk)
                refs[b] = dict(tier=tier, control_s=ttk0, with_s=None if dead else ttk,
                               saved_s=None if dead else ttk0 - ttk,
                               speedup=per_boss.get(b), capped=self.bosses[b]["status"] == "capped")
        row["reference"] = refs
        row["levels"] = {short(b): {lvl: v for lvl, v in sorted(self.levels[b][e].items())}
                         for b in sorted(self.deep) if self.levels[b].get(e)}
        w = {}
        for b in sorted(self.wounded):
            if b in WOUNDED_INVALID:
                continue
            for hp, cells in self.wounded[b].items():
                for lo, v in cells.items():
                    if names_of(lo) == [e]:
                        w.setdefault(short(b), {})[hp] = v
        row["wounded"] = w
        cost = {}
        for tier, b in REFERENCE:
            ph = self.probe_hp.get(b, {})
            if e in ph and ph.get("(control)") is not None and ph[e] is not None and abs(ph[e] - ph["(control)"]) > 0.05:
                cost[b] = dict(control=ph["(control)"], with_enchant=ph[e])
        row["probe_hp_min"] = cost
        # bow
        bt = [self.bow[b][e] for b in trusted if e in self.bow.get(b, {})]
        bow_sig = [b for b in trusted if e in self.bow.get(b, {}) and self.bosses[b].get("bow_band") is not None
                   and self.bow[b][e] is not None and self.bow[b][e] > max(self.bosses[b]["bow_band"], self.bosses[b].get("threshold") or 0)]
        row["bow_mean"] = mean([v for v in bt if v is not None and v > -100.0])
        row["bow_never_on"] = sorted(short(b) for b in self.bosses if e in self.bow.get(b, {}) and self.bow[b][e] == -100.0)
        row["bow_sig_n"] = len(bow_sig)
        row["bow_n"] = len(bt)
        row["bow_per_boss"] = {short(b): self.bow[b][e] for b in self.bosses if e in self.bow.get(b, {})}
        # armour
        dm = [b for b in self.bosses if self.bosses[b]["defence_measured"] and b not in DEFENCE_EXCLUDED]
        drs = {b: self.defence[b][e]["dr"] for b in dm if e in self.defence.get(b, {}) and self.defence[b][e]["dr"] is not None}
        row["dr_per_boss"] = {short(b): v for b, v in drs.items()}
        row["dr_mean"] = mean(list(drs.values()))
        row["dr_tier_mean"] = {t: mean([v for b, v in drs.items() if self.bosses[b]["tier"] == t]) for t in ("T1", "T2")}
        row["dr_n"] = len(drs)
        row["dr_ge5"] = sum(1 for v in drs.values() if v >= 5.0)
        row["dr_le_minus5"] = sum(1 for v in drs.values() if v <= -5.0)
        best = max(drs.items(), key=lambda kv: kv[1]) if drs else None
        row["dr_best"] = dict(boss=short(best[0]), dr=best[1]) if best else None
        hd = [self.defence[b][e]["hits_delta"] for b in dm if e in self.defence.get(b, {}) and self.defence[b][e]["hits_delta"] is not None]
        row["hits_survived_delta"] = mean(hd)
        hp_left = [(self.defence[b][e]["probe_hp_min"] or 0) - (self.defence[b][e]["probe_hp_control"] or 0)
                   for b in dm if e in self.defence.get(b, {}) and self.defence[b][e]["probe_hp_min"] is not None
                   and self.defence[b][e]["probe_hp_control"] is not None]
        row["hp_left_delta"] = mean(hp_left)
        row["immune_from"] = sorted({self.bosses[b]["tier"] for b in self.bosses
                                     if self.bosses[b].get("defence_control") == 0.0 and e in self.defence.get(b, {})})
        row["dr_levels"] = {short(b): {lvl: v for lvl, v in sorted(self.defence_levels[b][e].items())}
                            for b in sorted(self.deep) if self.defence_levels[b].get(e)}
        row["procs"] = self._proc_summary(e, group)
        row["pairs"] = []
        row["verdict"], row["verdict_why"], row["effect_measure"] = self.verdict(row)
        return row

    def _guess_group(self, e):
        if any(e in self.defence.get(b, {}) for b in self.defence):
            return "armour"
        if any(e in self.bow.get(b, {}) for b in self.bow):
            return "bow"
        return "weapon"

    def _census_rarity(self, e):
        for job in self.jobs.values():
            for r in job.rows:
                if r.get("kind") == "isolated" and names_of(r["loadout"]) == [e] and r.get("rarity"):
                    return r["rarity"]
        return None

    def _proc_summary(self, e, group):
        trig = {"weapon": "ATTACK", "armour": "DAMAGED", "bow": "ARROW_HIT"}.get(group)
        cells = self.procs.get(e, {})
        if not cells:
            return None
        if trig not in cells or cells[trig][2] is None or cells[trig][2] >= 100.0:
            cand = [(t, c) for t, c in cells.items() if c[2] is not None and c[2] < 100.0 and c[0]]
            if not cand:
                return None
            trig, _ = max(cand, key=lambda tc: tc[1][0])
        rolls, fires, exp = cells[trig]
        if not rolls or exp is None or exp >= 100.0:
            return None
        obs = 100.0 * fires / rolls
        se = math.sqrt(max(exp * (100.0 - exp) / rolls, 1e-9))
        return dict(trigger=trig, rolls=rolls, fires=fires, observed_pct=obs, declared_pct=exp,
                    z=(obs - exp) / se, mismatch=abs(obs - exp) > max(2.0, 3.0 * se))

    # -- verdict -----------------------------------------------------------
    def verdict(self, row):
        e, group, rarity = row["name"], row["group"], row["rarity"]
        if e in UNTESTABLE:
            return V_UNTEST, UNTESTABLE[e], None
        if group in ("tool", "any", "other"):
            return V_UNTEST, "not a combat enchantment", None
        if rarity not in BANDS["weapon"]:
            return V_UNMEASURED, "no declared rarity", None
        if group == "armour":
            m = row["dr_mean"]
            if m is None:
                return V_UNMEASURED, "no armour cell could read it", None
            n = row["dr_n"] or 1
            measure = f"{m:+.1f}% less damage taken (T1-T2 mean over {n} bosses, >=5% on {row['dr_ge5']})"
            if abs(m) <= NO_EFFECT_MAX and row["dr_ge5"] / n < NO_EFFECT_SIG_FRAC:
                return V_NONE, measure, m
            return self._band_verdict(m, BANDS["armour"][rarity], measure, None)
        if group == "bow":
            m = row["bow_mean"]
            if m is None or row["bow_n"] == 0:
                return V_UNMEASURED, "no bow cell", None
            measure = f"{m:+.1f}% bow speed-up (noisy instrument, significant on {row['bow_sig_n']}/{row['bow_n']})"
            if row["bow_never_on"]:
                # One or two "never" cells are bow-instrument misses (Piercing, Penetrating also show them);
                # four or more, or any with a negative mean, is the Homing pattern the census flagged.
                measure += f"; arrows never land on {', '.join(row['bow_never_on'])}"
                if len(row["bow_never_on"]) >= 4 or m < 0:
                    return V_HARM, measure, m
            if abs(m) <= NO_EFFECT_MAX or row["bow_sig_n"] / max(row["bow_n"], 1) < NO_EFFECT_SIG_FRAC:
                return V_NONE, measure, m
            return self._band_verdict(m, BANDS["weapon"][rarity], measure, None)
        m = row["trusted_mean"]
        if m is None:
            return V_UNMEASURED, "no melee cell on a trusted boss", None
        n = row["trusted_n"] or 1
        measure = f"{m:+.1f}% speed-up (trusted mean, {n} bosses, significant on {row['sig_pos']})"
        if e == "berserk":
            w = [cells.get(0.5) for cells in row["wounded"].values()]
            w25 = [cells.get(0.25) for cells in row["wounded"].values()]
            if any(v is not None for v in w):
                m = mean(w)
                measure = (f"0 at full health; {m:+.1f}% at half health, {mean(w25):+.1f}% at a quarter "
                           f"(mean over {len([v for v in w if v is not None])} bosses)")
                return self._band_verdict(m, BANDS["weapon"][rarity], measure, None)
        if e == "multistrike":
            ms = self.multistrike_contribution()
            if ms:
                m = mean(list(ms.values()))
                measure = f"alone 0; adds {m:+.1f} points to Colossus + Executioner (mean over {len(ms)} deep bosses)"
                return self._band_verdict(m, BANDS["weapon"][rarity], measure, None)
        if m < -NO_EFFECT_MAX and row["sig_neg"] >= 3:
            return V_HARM, measure + f"; significant loss on {row['sig_neg']} bosses", m
        if abs(m) <= NO_EFFECT_MAX and row["sig_pos"] / n < NO_EFFECT_SIG_FRAC:
            return V_NONE, measure, m
        return self._band_verdict(m, BANDS["weapon"][rarity], measure, row["t4_capped_mean"])

    def _band_verdict(self, m, band, measure, t4):
        lo, hi = band
        if lo is not None and m < lo:
            v = V_WEAK
        elif hi is not None and m > hi:
            v = V_STRONG
        else:
            v = V_PROP
        if t4 is not None and hi is not None and t4 > hi + T4_OUTLIER_MARGIN:
            measure += f"; T4 capped bosses {t4:+.0f}% (above the band)"
            if v != V_STRONG:
                v = V_STRONG + " (T4 only)"
        return v, measure, m

    def multistrike_contribution(self):
        out = {}
        for b in sorted(self.deep):
            pair = self.pairs[b].get(frozenset(["colossus", "executioner"]))
            stack = None
            for lo, v in self.stacks.get(b, {}).items():
                if set(names_of(lo)) == {"multistrike", "colossus", "executioner"}:
                    stack = v
            if pair and pair.get("speedup") is not None and stack is not None:
                out[short(b)] = stack - pair["speedup"]
        return out

    # -- pairs -------------------------------------------------------------
    def pair_rows(self):
        rows = {}
        for b in sorted(self.deep):
            for key, cell in self.pairs[b].items():
                a, c = sorted(key)
                ra, rc = self.replicates[b].get(a, []), self.replicates[b].get(c, [])
                if not ra or not rc or cell["speedup"] is None or cell["ttk0"] is None:
                    continue
                # Independence multiplies TTK ratios: each enchantment removes its share of what is left.
                ratio_a = mean([1.0 - v / 100.0 for v in ra if v is not None])
                ratio_c = mean([1.0 - v / 100.0 for v in rc if v is not None])
                ratio_pair = 1.0 - cell["speedup"] / 100.0
                if ratio_pair <= 0 or ratio_a is None or ratio_c is None:
                    continue
                expected = ratio_a * ratio_c
                synergy = 100.0 * (expected / ratio_pair - 1.0)
                sda, sdc = sd(ra) or 0.0, sd(rc) or 0.0
                noise = cell.get("noise") or 2.0
                band = 2.0 * math.sqrt(sda ** 2 + sdc ** 2 + (noise / 2.0) ** 2)
                r = rows.setdefault((a, c), dict(a=a, b=c, per_boss={}))
                r["per_boss"][short(b)] = dict(speedup=cell["speedup"], synergy=synergy, band=band,
                                               sig=abs(synergy) > band, expected_speedup=100.0 * (1 - expected),
                                               ttk_s=cell["ttk"], ttk0_s=cell["ttk0"])
        for r in rows.values():
            sigs = [(k, v) for k, v in r["per_boss"].items() if v["sig"]]
            pos = [k for k, v in sigs if v["synergy"] > 0]
            neg = [k for k, v in sigs if v["synergy"] < 0]
            if len(pos) >= 2 and not neg:
                r["call"] = "synergy"
            elif len(neg) >= 2 and not pos:
                r["call"] = "anti-synergy"
            elif len(pos) == 1 and not neg:
                r["call"] = "probable synergy (one boss)"
            elif len(neg) == 1 and not pos:
                r["call"] = "probable anti-synergy (one boss)"
            elif pos and neg:
                r["call"] = "boss-dependent"
            else:
                r["call"] = "independent"
            r["mean_synergy"] = mean([v["synergy"] for v in r["per_boss"].values()])
            r["mean_speedup"] = mean([v["speedup"] for v in r["per_boss"].values()])
        return sorted(rows.values(), key=lambda r: -(abs(r["mean_synergy"]) if r["mean_synergy"] is not None else 0))

    def stack_rows(self):
        names = sorted({lo for b in self.stacks for lo in self.stacks[b]})
        out = []
        for lo in names:
            per = {b: self.stacks[b][lo] for b in self.stacks if lo in self.stacks[b]}
            tv = [per[b] for b in self.trusted_bosses() if per.get(b) is not None]
            out.append(dict(loadout=lo, trusted_mean=mean(tv), trusted_n=len(tv),
                            t4_capped_mean=mean([per[b] for b in self.capped_bosses() if per.get(b) is not None]),
                            per_boss={short(b): v for b, v in per.items()},
                            wounded={short(b): {hp: cells[lo] for hp, cells in self.wounded[b].items() if lo in cells}
                                     for b in sorted(self.wounded) if b not in WOUNDED_INVALID}))
        return out

    def histogram(self, rows):
        groups = ["weapon", "armour", "bow", "tool", "any"]
        by_rc = {r: {g: 0 for g in groups} for r in RARITIES}
        by_rv = {r: defaultdict(int) for r in RARITIES}
        measured = {r: defaultdict(int) for r in RARITIES}
        for row in rows:
            r = row["rarity"]
            if r not in by_rc:
                continue
            by_rc[r][row["group"] if row["group"] in groups else "any"] += 1
            by_rv[r][base_verdict(row["verdict"])] += 1
            m = row.get("effect_measure")
            if m is not None and row["verdict"] not in (V_UNTEST, V_UNMEASURED):
                band_set = BANDS["armour"] if row["group"] == "armour" else BANDS["weapon"]
                cls = None
                for rr, (lo, hi) in band_set.items():
                    if (lo is None or m >= lo) and (hi is None or m < hi):
                        cls = rr
                if m < -NO_EFFECT_MAX:
                    cls = "NEGATIVE"
                measured[r][cls or "?"] += 1
        return dict(by_rarity_category=by_rc,
                    by_rarity_verdict={r: dict(v) for r, v in by_rv.items()},
                    measured_class_by_declared={r: dict(v) for r, v in measured.items()})


# ---------------------------------------------------------------------------
# Markdown
# ---------------------------------------------------------------------------
def table(w, header, rows, align=None):
    w("| " + " | ".join(header) + " |")
    if align is None:
        align = ["---"] + ["---:"] * (len(header) - 1)
    w("|" + "|".join(align) + "|")
    for r in rows:
        w("| " + " | ".join(str(x) for x in r) + " |")
    w("")


def _bands_text(b):
    parts = []
    for r in RARITIES:
        lo, hi = b[r]
        if lo is None:
            parts.append(f"{r.title()} < {hi}")
        elif hi is None:
            parts.append(f"{r.title()} ≥ {lo}")
        else:
            parts.append(f"{r.title()} {lo}–{hi}")
    return ", ".join(parts) + " points"


def _flag(r):
    return r["verdict"] in (V_STRONG, V_WEAK, V_HARM) or r["verdict"].startswith(V_STRONG)


def _name(r):
    return f"**{r['name']}**" if _flag(r) else r["name"]


def _rar(r):
    t = (r["rarity"] or "–").title()
    if r.get("retiered"):
        t += f" (was {r['census_rarity'].title()})"
    return t


def _bold(txt, cond):
    return f"**{txt}**" if cond else txt


def _tier(v, nsig):
    if v is None:
        return "–"
    return f"{v:+.0f} ({nsig})" if nsig else f"{v:+.0f}"


def _verdict_cell(r):
    v = r["verdict"]
    if v == V_UNTEST:
        return f"{v} — {r['verdict_why']}"
    return f"**{v}**" if _flag(r) else v


def md_report(an, rows, pairs, stacks, hist, args, job_notes):
    out = []
    w = out.append
    today = datetime.date.today().isoformat()
    trusted = an.trusted_bosses()
    deep = sorted(an.deep, key=lambda b: an.bosses[b]["tier"])
    w("# Enchant effects table")
    w("")
    w(f"Generated {today} by `tools/balance/effects_table.py` from {len(an.jobs)} census jobs in "
      + ", ".join(f"`{r}`" for r in args.roots) + ". **Do not edit by hand: rerun the tool.** "
      "Every number is a measurement from the running pack, paired against the same weapon and armour "
      "with no custom enchantment ([method](enchantment-combat-results.md#1-method)). This is the table "
      "decision [0005](../decisions/0005-enchant-census-proposals.md) P10 asks for; what to do about it "
      "is in [enchant-rarity-plan](../design/enchant-rarity-plan.md). Machine-readable copy: "
      "[`enchant-effects.json`](enchant-effects.json).")
    w("")
    w("**Contents.** [How to read it](#how-to-read-it) · [Rarity distribution](#rarity-distribution) · "
      "[Bosses](#the-bosses) · [Weapons](#weapon-enchantments) · [Armour](#armour-enchantments) · "
      "[Bows](#bow-enchantments) · [Utility, tools and PvP](#utility-tool-and-pvp-enchantments) · "
      "[Pairs](#pairs) · [Stacks](#curated-stacks) · [Data notes](#data-notes) · "
      "[Appendix: every boss](#appendix-speed-up-by-boss)")
    w("")
    w("## How to read it")
    w("")
    w("- **Speed-up** = 1 − (time to kill with the enchantment ÷ time to kill without). +50% means the boss dies in half the time. "
      "**Seconds saved** is the same thing in seconds on one reference boss per tier.")
    w(f"- **Trusted mean** averages the top level over the {len(trusted)} bosses whose controls are unbiased and uncapped (see [Bosses](#the-bosses)). "
      "The 750-per-hit T4 bosses, Rahovart (25/hit) and Godzilla are shown in their own columns, not averaged: a cap measures the boss, not the enchantment.")
    w("- **Significant** (bold, and the counts in brackets) means outside that boss's threshold, which is the larger of its control noise band "
      "and two standard deviations of ten placebo enchantments with no boss-fight mechanism. Proc luck is wider than that on the deterministic T3/T4 bosses: "
      "the **replicate sd** column is the spread of the same cell over its three runs, where it exists.")
    w("- **Damage reduction** (armour) is damage taken over sixty of the boss's own melee hits against the same armour with no enchantment. "
      "From T3 the tier armour already takes nothing from any boss, so every armour enchantment is 0 there; the means are T1–T2.")
    w("- **Proc** is the observed firing rate on the enchantment's own trigger over every singles job, against the declared rate. A mismatch is a code question, not a balance one.")
    w("- **Verdict** compares the measured effect with the band its *declared* rarity should buy "
      f"(registry source as of this run): weapons {_bands_text(BANDS['weapon'])}; armour {_bands_text(BANDS['armour'])}. "
      f"|effect| ≤ {NO_EFFECT_MAX:.0f} points and significant on under a quarter of the bosses reads **no observable effect**. "
      "Enchantments the census has no cell for are **untestable** and priced on utility. These bands are a proposal; they live at the top of the script.")
    retiered = [r for r in rows if r.get("retiered")]
    if retiered:
        w("- **Re-tiered since the census** (registry rarity differs from the rarity the census jar carried): "
          + ", ".join(f"{r['name']} {r['census_rarity'].title()} → {r['rarity'].title()}" for r in retiered) + ".")
    w("")
    # ---- histogram ----
    w("## Rarity distribution")
    w("")
    w("Declared rarity (registry today) by category:")
    w("")
    groups = ["weapon", "armour", "bow", "tool", "any"]
    table(w, ["Rarity"] + [g.title() for g in groups] + ["Total"],
          [[r.title()] + [hist["by_rarity_category"][r][g] for g in groups] + [sum(hist["by_rarity_category"][r].values())] for r in RARITIES]
          + [["**All**"] + [sum(hist["by_rarity_category"][r][g] for r in RARITIES) for g in groups]
             + [sum(sum(hist["by_rarity_category"][r].values()) for r in RARITIES)]])
    w("Declared rarity by verdict:")
    w("")
    verdicts = [V_PROP, V_STRONG, V_WEAK, V_NONE, V_HARM, V_UNTEST, V_UNMEASURED]
    table(w, ["Rarity"] + verdicts,
          [[r.title()] + [hist["by_rarity_verdict"][r].get(v, 0) for v in verdicts] for r in RARITIES])
    w("Where the measured effect lands (rows: declared rarity; columns: the band the measurement falls in; "
      "combat enchantments with a measurable effect only, Berserk read at half health, Multi Strike as its stack contribution):")
    w("")
    cols = RARITIES + ["NEGATIVE"]
    table(w, ["Declared \\ measured"] + [c.title() for c in cols],
          [[r.title()] + [hist["measured_class_by_declared"][r].get(c, 0) for c in cols] for r in RARITIES])
    # ---- bosses ----
    w("## The bosses")
    w("")
    brow = []
    for b in sorted(an.bosses.values(), key=lambda b: (b["tier"], b["hp"] or 0)):
        st = b["status"]
        note = b.get("why") or ""
        if b.get("cap"):
            note = (f"cap {b['cap']}; " + note) if note else f"cap {b['cap']}"
        brow.append([b["tier"], b["short"], f"{b['hp']:,.0f}" if b["hp"] else "–",
                     f"{b['control_ttk']:.1f} s" if b["control_ttk"] else "–",
                     f"±{b['band']:.1f}%" if b["band"] is not None else "–",
                     f1(b["placebo_median"]) if b["placebo_median"] is not None else "–",
                     f"±{b['threshold']:.1f}%" if b["threshold"] is not None else "–",
                     f"{b['defence_control']:.0f}" if b.get("defence_control") is not None else "–",
                     ("**" + st + "**" if st != "trusted" else st) + (f": {note}" if note else "")])
    table(w, ["Tier", "Boss", "HP", "Control TTK", "Control band", "Placebo median", "Threshold", "Control dmg / 60 hits", "Status"], brow,
          ["---", "---", "---:", "---:", "---:", "---:", "---:", "---:", "---"])
    # ---- weapons ----
    weapons = [r for r in rows if r["group"] == "weapon" and r["verdict"] != V_UNTEST]
    weapons.sort(key=lambda r: -(r["trusted_mean"] if r["trusted_mean"] is not None else -999))
    w("## Weapon enchantments")
    w("")
    w("Top level, melee. Brackets: bosses significant in that group (− for a significant loss). Sorted by trusted mean.")
    w("")
    wr = []
    for r in weapons:
        tm = r["tier_mean"]
        wr.append([_name(r), _rar(r), r["max_level"] or "–", r["effect"],
                   _bold(f1(r["trusted_mean"]), True) + (f" ± {r['trusted_sd']:.0f}" if r["trusted_sd"] else "")
                   + f" ({r['sig_pos']}" + (f", {r['sig_neg']}−" if r["sig_neg"] else "") + f"/{r['trusted_n']})",
                   _tier(tm["T1"], r["tier_sig"]["T1"]), _tier(tm["T2"], r["tier_sig"]["T2"]),
                   _tier(tm["T3"], r["tier_sig"]["T3"]), _tier(r["t4_capped_mean"], r["t4_capped_sig"]),
                   f0(r["rahovart"]), f0(r["godzilla"]), _verdict_cell(r)])
    table(w, ["Enchant", "Rarity", "Lvl", "Effect", "Trusted mean (sig)", "T1", "T2", "T3", "T4 capped", "Rahovart", "Godzilla", "Verdict"], wr,
          ["---", "---", "---:", "---", "---:", "---:", "---:", "---:", "---:", "---:", "---:", "---"])
    w("### Seconds saved, levels and procs")
    w("")
    w("Reference bosses: " + ", ".join(
        f"{t} {short(b)} ({an.bosses[b]['control_ttk']:.1f} s unenchanted" + (", capped" if an.bosses[b]["status"] == "capped" else "") + ")"
        for t, b in REFERENCE if b in an.bosses and an.bosses[b]["control_ttk"]) + ". "
      "A cell reads *TTK with* → *seconds saved*. Levels are speed-up at I / II / III on the deep boss of that tier (levels job, one cell each: ±10 for proc enchantments).")
    w("")
    wr = []
    for r in weapons:
        refs = []
        for t, b in REFERENCE:
            x = r["reference"].get(b)
            refs.append(f"{x['with_s']:.0f} s → {x['saved_s']:+.0f} s" if x and x["with_s"] is not None else ("never" if x else "–"))
        lv = []
        for bname in ("Naga", "Mantis", "Mobzilla"):
            l = r["levels"].get(bname)
            lv.append(" / ".join(f0(l.get(i)) for i in (1, 2, 3)) if l else "–")
        p = r["procs"]
        ptxt = "–" if not p else (f"{p['observed_pct']:.1f} / {p['declared_pct']:.0f}% {p['trigger']}" + (" **≠**" if p["mismatch"] else ""))
        rep = ", ".join(f"{k} ±{v:.0f}" for k, v in r["replicate_sd"].items() if v is not None) or "–"
        wr.append([_name(r)] + refs + lv + [ptxt, rep])
    table(w, ["Enchant", "Naga (T1)", "Wither (T2)", "Mantis (T3)", "Mobzilla (T4, capped)", "Levels Naga", "Levels Mantis", "Levels Mobzilla", "Proc obs / declared", "Replicate sd"], wr,
          ["---"] + ["---:"] * 9)
    w("### Conditional and costed")
    w("")
    cond = []
    for r in weapons:
        for b, cells in r["wounded"].items():
            cond.append([r["name"], b, "wielder at 50% / 25% health", f"{f0(cells.get(0.5))} / {f0(cells.get(0.25))}"])
        for b, c in r["probe_hp_min"].items():
            cond.append([r["name"], short(b), "wielder's lowest health in the fight (control → with)", f"{c['control']:.1f} → {c['with_enchant']:.1f} of 20"])
    for b, v in an.multistrike_contribution().items():
        cond.append(["multistrike", b, "added to Colossus + Executioner (stack − pair)", f0(v)])
    if cond:
        table(w, ["Enchant", "Boss", "Measure", "Value"], cond, ["---", "---", "---", "---:"])
    # ---- armour ----
    armour = [r for r in rows if r["group"] == "armour"]
    armour.sort(key=lambda r: -(r["dr_mean"] if r["dr_mean"] is not None else -999))
    w("## Armour enchantments")
    w("")
    w("Damage reduction against each boss's own melee, top level, over sixty hits. "
      f"Left out: {'; '.join(f'{short(k)} ({v})' for k, v in DEFENCE_EXCLUDED.items())}. "
      "**Hits survived** and **HP left** are the wielder's gain against the control in the same cell (the probe is held alive, so a 60-hit cell mostly ends near zero health; read the sign). "
      "Vigor and Regrowth read as negative reduction because a lethal hit only counts the health that was left: use hits survived for those two.")
    w("")
    ar = []
    for r in armour:
        lv = r["dr_levels"].get("Naga") or {}
        ar.append([_name(r), _rar(r), r["max_level"] or "–", r["effect"],
                   _bold(f1(r["dr_tier_mean"]["T1"]), (r["dr_tier_mean"]["T1"] or 0) >= 5),
                   _bold(f1(r["dr_tier_mean"]["T2"]), (r["dr_tier_mean"]["T2"] or 0) >= 5),
                   _bold(f1(r["dr_mean"]), (r["dr_mean"] or 0) >= 5),
                   f"{r['dr_best']['dr']:+.0f} ({r['dr_best']['boss']})" if r["dr_best"] else "–",
                   f"{r['dr_ge5']}/{r['dr_n']}" + (f" ({r['dr_le_minus5']}−)" if r["dr_le_minus5"] else ""),
                   f1(r["hits_survived_delta"]), f1(r["hp_left_delta"]),
                   " / ".join(f0(lv.get(i), sign=False) for i in sorted(lv)) if lv else "–",
                   _verdict_cell(r)])
    table(w, ["Enchant", "Rarity", "Lvl", "Effect", "DR T1", "DR T2", "DR mean", "Best", "≥5% on", "Hits survived", "HP left", "Levels (Naga DR)", "Verdict"], ar,
          ["---", "---", "---:", "---", "---:", "---:", "---:", "---:", "---:", "---:", "---:", "---:", "---"])
    # ---- bows ----
    bows = [r for r in rows if r["group"] == "bow"]
    bows.sort(key=lambda r: -(r["bow_mean"] if r["bow_mean"] is not None else -999))
    w("## Bow enchantments")
    w("")
    w("Bow cells fire a full-draw arrow every 20 ticks at a boss ten blocks away and miss some; the bow noise band is wide (±2% to over ±100% per boss), so only a consistent result means anything.")
    w("")
    br = [[_name(r), _rar(r), r["max_level"] or "–", r["effect"], f1(r["bow_mean"]), f"{r['bow_sig_n']}/{r['bow_n']}",
           ", ".join(r["bow_never_on"]) or "–", _verdict_cell(r)] for r in bows]
    table(w, ["Enchant", "Rarity", "Lvl", "Effect", "Trusted mean", "Sig. on", "Arrows never land on", "Verdict"], br,
          ["---", "---", "---:", "---", "---:", "---:", "---", "---"])
    # ---- utility ----
    util = [r for r in rows if r["verdict"] == V_UNTEST and r["group"] in ("weapon", "tool", "any", "other")]
    util.sort(key=lambda r: (RARITIES.index(r["rarity"]) if r["rarity"] in RARITIES else 9, r["name"]))
    w("## Utility, tool and PvP enchantments")
    w("")
    w("No boss cell can exercise these. Their census rows are the placebo set's noise (trusted mean shown for completeness); price them on what they do, not on this table.")
    w("")
    ur = [[r["name"], _rar(r), r["group"], r["effect"], f1(r["trusted_mean"]) if r["trusted_mean"] is not None else "–", r["verdict_why"]] for r in util]
    table(w, ["Enchant", "Rarity", "Group", "Effect", "Census reads", "Why untestable"], ur, ["---", "---", "---", "---", "---:", "---"])
    # ---- pairs ----
    w("## Pairs")
    w("")
    w("All pairs of the author's 14-enchantment set on one boss per damage model (" + ", ".join(f"{an.bosses[b]['tier']} {short(b)}" for b in deep) + "). "
      "**Synergy** = expected TTK under independence ÷ the pair's TTK, minus one; independence multiplies (two +30% enchantments are +51% together). "
      "Each single's ratio is the mean of its replicate runs; the band is two sd of both replicate spreads plus the control noise. "
      "A pair is **called** when significant on at least two bosses with the same sign; one boss is *probable*. "
      "Lord of Torment's controls are biased, so no call should rest on it alone.")
    w("")
    pr = []
    for p in pairs:
        cells = []
        for b in deep:
            x = p["per_boss"].get(short(b))
            cells.append(_bold(f0(x["synergy"]), x["sig"]) + f" (±{x['band']:.0f})" if x else "–")
        pr.append([f"{p['a']} + {p['b']}", f0(p["mean_speedup"])] + cells + [p["call"] if p["call"] == "independent" else "**" + p["call"] + "**"])
    table(w, ["Pair", "Mean speed-up"] + [short(b) for b in deep] + ["Call"], pr, ["---", "---:"] + ["---:"] * len(deep) + ["---"])
    # ---- stacks ----
    w("## Curated stacks")
    w("")
    sr = []
    for s in stacks:
        wtxt = "; ".join(f"{b} {f0(c.get(0.5))} / {f0(c.get(0.25))}" for b, c in s["wounded"].items() if c) or "–"
        sr.append([s["loadout"], f1(s["trusted_mean"]) + f" ({s['trusted_n']})", f1(s["t4_capped_mean"]), wtxt])
    table(w, ["Stack", "Trusted mean", "T4 capped", "Wielder at 50% / 25% health"], sr, ["---", "---:", "---:", "---"])
    # ---- notes ----
    w("## Data notes")
    w("")
    exc = [(j.name, j.excluded) for j in an.jobs.values() if j.excluded]
    if exc:
        w("- Degenerate cells excluded (pin did not hold / removed alive): " + ", ".join(f"{n} ({c})" for n, c in exc) + ".")
    thrown = defaultdict(set)
    for j in an.jobs.values():
        for r in j.rows:
            if "threw" in (r.get("note") or ""):
                thrown[r["loadout"]].add(short(j.boss))
    for lo, bs in thrown.items():
        w(f"- `{lo}` threw an exception on {', '.join(sorted(bs))}: those cells measure nothing (note text in the TSV).")
    pm = [r for r in rows if r["procs"] and r["procs"]["mismatch"]]
    if pm:
        w("- Proc-rate mismatches on the enchantment's own trigger: " + ", ".join(
            f"{r['name']} {r['procs']['observed_pct']:.1f}% vs {r['procs']['declared_pct']:.0f}% ({r['procs']['trigger']}, {r['procs']['rolls']} rolls)" for r in pm) + ".")
    for n in job_notes:
        w(f"- {n}")
    w(f"- Jobs read: {len(an.jobs)}. Deep bosses (levels, pairs, wounded): " + ", ".join(short(b) for b in deep) + ".")
    w("- Rahovart appears under T3 and T4 with identical numbers (25/hit cap); the T3 job is the one shown.")
    w("")
    # ---- appendix ----
    w("## Appendix: speed-up by boss")
    w("")
    w("Top level, melee, singles job. Bold = beyond that boss's threshold. ✗ = excluded from every mean; ⚠ = shown, not averaged.")
    w("")
    for tier in TIERS:
        bl = [b for b in an.bosses if an.bosses[b]["tier"].startswith(tier) and an.bosses[b]["control_ttk"]]
        if tier == "T4":
            bl = [b for b in bl if b != "demonmobs.rahovart"]
        bl.sort(key=lambda b: (b == "demonmobs.rahovart", an.bosses[b]["hp"] or 0))
        if not bl:
            continue
        w(f"#### {tier}")
        w("")
        hdr = ["Enchant"] + [short(b) + (" ✗" if an.bosses[b]["status"] == "excluded" else " ⚠" if an.bosses[b]["status"] == "shown" else "")
                             + f" ±{an.bosses[b]['threshold']:.0f}" for b in bl]
        ar = []
        for r in weapons + util:
            cells = []
            for b in bl:
                x = r["per_boss"].get(b)
                cells.append(_bold(f0(x["speedup"]), x["sig"]) if x else "–")
            ar.append([r["name"]] + cells)
        table(w, hdr, ar, ["---"] + ["---:"] * len(bl))
    return "\n".join(out)


# ---------------------------------------------------------------------------
def _jsonable(o):
    if isinstance(o, frozenset):
        return sorted(o)
    if isinstance(o, float) and (math.isinf(o) or math.isnan(o)):
        return None
    raise TypeError(type(o))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("roots", nargs="*", default=[DEFAULT_CAMPAIGN],
                    help="campaign directories; a job folder in a later root replaces the same-named job from an earlier one")
    ap.add_argument("--registry", default=DEFAULT_REGISTRY, help="qf-content enchants source folder (declared rarity)")
    ap.add_argument("--md", default=DEFAULT_MD)
    ap.add_argument("--json", default=DEFAULT_JSON)
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    registry = read_registry(args.registry)
    jobs, job_notes = load_jobs(args.roots)
    if not jobs:
        sys.exit("no census jobs found under " + ", ".join(args.roots))
    an = Analysis(jobs, registry)
    an.collect()
    rows = an.enchant_rows()
    pairs = an.pair_rows()
    for p in pairs:
        for r in rows:
            if r["name"] in (p["a"], p["b"]):
                r["pairs"].append(dict(with_=(p["b"] if r["name"] == p["a"] else p["a"]), call=p["call"],
                                       mean_synergy=p["mean_synergy"]))
    stacks = an.stack_rows()
    hist = an.histogram(rows)

    md = md_report(an, rows, pairs, stacks, hist, args, job_notes)
    os.makedirs(os.path.dirname(os.path.abspath(args.md)), exist_ok=True)
    with open(args.md, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(md)
    doc = dict(
        generated=datetime.datetime.now().isoformat(timespec="seconds"),
        roots=args.roots, registry=args.registry,
        jobs=[dict(name=j.name, tier=j.tier, boss=j.boss, phase=j.phase, weapon=j.weapon, options=j.options,
                   seconds=j.seconds, cells=len(j.rows), excluded=j.excluded) for j in an.jobs.values()],
        policy=dict(bosses=BOSS_POLICY, defence_excluded=DEFENCE_EXCLUDED, wounded_invalid=sorted(WOUNDED_INVALID),
                    placebos=PLACEBOS, reference=REFERENCE, bands=BANDS, no_effect_max=NO_EFFECT_MAX,
                    no_effect_sig_frac=NO_EFFECT_SIG_FRAC, t4_outlier_margin=T4_OUTLIER_MARGIN),
        bosses=an.bosses, enchants=rows, pairs=pairs, stacks=stacks, histogram=hist, notes=job_notes)
    with open(args.json, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False, default=_jsonable)
    if not args.quiet:
        print(f"{len(an.jobs)} jobs, {len(an.bosses)} bosses ({len(an.trusted_bosses())} trusted), {len(rows)} enchantments, {len(pairs)} pairs")
        for v in (V_PROP, V_STRONG, V_WEAK, V_NONE, V_HARM, V_UNTEST, V_UNMEASURED):
            n = [r["name"] for r in rows if base_verdict(r["verdict"]) == v]
            print(f"  {v}: {len(n)}" + (f" — {', '.join(n)}" if n and v != V_UNTEST else ""))
        print(f"wrote {args.md}\nwrote {args.json}")


if __name__ == "__main__":
    main()
