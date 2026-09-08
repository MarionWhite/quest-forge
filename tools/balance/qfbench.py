#!/usr/bin/env python3
"""
QuestForge benchmark suites, on top of qfsim.

Three things qfsim did not cover:

  A. What Cultist actually costs now that its price is physical damage, by armor
     tier -- the whole point of the change.
  B. Combinations of offensive enchantments against benchmark bosses, so the loot
     tables can be written knowing what an accumulating player ends up with.
  C. Defensive loadouts simulated rather than multiplied out on paper: incoming
     hits, i-frames, armor durability lost to Sacrifice, knockback uptime,
     regeneration.

All of this runs under the tuned (post-2026-09-06) rules.
"""
import itertools, random, statistics, sys
from collections import defaultdict

import forge_armor
import qfsim
qfsim.TUNED = True                      # everything here benchmarks the shipped rules
from qfsim import (Sim, Player, Target, TARGETS, WEAPONS, vanilla_attack,
                   finish_damage, report_section)

rng = random.Random(20260907)
qfsim.rng = random.Random(99)

# ---------------------------------------------------------------------------
# Benchmark bosses. Chosen to span the three shapes that matter here: a mid-game
# wall, a pure health sponge, and a boss that caps incoming damage per hit.
# ---------------------------------------------------------------------------
BENCH = [
    ("TF Hydra",           "mid-game wall, no damage cap"),
    ("OreSpawn Mobzilla",  "health sponge, no damage cap"),
    ("Lycanites Rahovart", "hard 25/hit cap plus 2 flat defense"),
]

# Offensive weapon enchantments: (key, level, rarity). Rarities read from source.
OFFENSE = [
    ("executioner",  3, "Rare"),
    ("berserk",      3, "Epic"),
    ("colossus",     3, "Epic"),
    ("roulette",     1, "Uncommon"),
    ("momentum",     3, "Uncommon"),
    ("riposte",      3, "Uncommon"),
    ("assassinate",  3, "Rare"),
    ("excalibur",    1, "Legendary"),
    ("killingblow",  3, "Epic"),
    ("cultist",      3, "Rare"),
    ("rupture",      3, "Rare"),
    ("rage",         3, "Epic"),
    ("crushingblow", 3, "Epic"),
    ("venomous",     3, "Rare"),
    ("poisonous",    3, "Uncommon"),
    ("feast",        3, "Rare"),
    ("sunder",       3, "Uncommon"),
    ("cripple",      3, "Rare"),
    ("multistrike",  1, "Legendary"),
]
BY_KEY = {k: (k, l, r) for k, l, r in OFFENSE}

WINDOW = 20 * 150          # 150 seconds: long enough for streaks and bleeds to matter
RUNS = 60                  # Monte Carlo runs per (combo, boss)


def dps_of(combo, target_name, weapon, runs=RUNS, hp=20.0, armor=20, prot=4):
    """Sustained damage per second over a fixed window, wielder immortal.

    Immortal so the measurement is of the weapon, not of whether the player
    happened to die; Cultist deaths are counted separately.
    """
    spec = TARGETS[target_name]
    ench = [(k, BY_KEY[k][1]) for k in combo]
    dps, killed, ttk, cult = [], [], [], []
    for _ in range(runs):
        p = Player(weapon, hp=hp, armor=armor, prot=prot, immortal=True)
        s = Sim(p, Target(spec), ench, target_hits_every=40)
        st = s.run(max_ticks=WINDOW)
        secs = st["ticks"] / 20.0
        dps.append(st["dmg_dealt"] / max(secs, 0.05))
        killed.append(st["killed"])
        if st["killed"]:
            ttk.append(secs)
        cult.append(st.get("cultist_deaths", 0))
    return {
        "dps": statistics.mean(dps),
        "kill_rate": statistics.mean(killed),
        "ttk": statistics.mean(ttk) if ttk else None,
        "cultist_deaths": statistics.mean(cult),
    }


# ===========================================================================
# A. Cultist by armor tier
# ===========================================================================
ARMOR_TIERS = [
    ("naked",              0,  0),
    ("leather",            7,  0),
    ("iron",              15,  0),
    ("diamond",           20,  0),
    ("diamond + Prot IV", 20,  4),
]


def cultist_fight(pts, prot, weapon, level=3, mob_dps_interval=40, mob_raw=25.0,
                  ticks=20 * 300, seed=None):
    """One realistic fight with Cultist: the wielder is mortal and regenerates.

    Written out here rather than reusing Sim because Sim's player has no
    regeneration, and an immortal player simply floors at one health, at which
    point Cultist's own safety clamp stops charging anything at all.
    """
    r = random.Random(seed)
    hp = max_hp = 20.0
    hurt_res, last_dmg = 0, 0.0
    self_total, mob_total, procs, blocked = 0.0, 0.0, 0, 0
    chance = 8 * level
    factor = (25 - pts) / 25.0 * ((25 - min(20, 5 * prot)) / 25.0 if prot else 1.0)
    death_tick = None

    for tick in range(1, ticks + 1):
        if hurt_res > 0:
            hurt_res -= 1
        if tick % 80 == 0 and hp < max_hp:
            hp = min(max_hp, hp + 1.0)

        def take(raw):
            """vanilla attackEntityFrom + armour, on the local state."""
            nonlocal hp, hurt_res, last_dmg
            if hurt_res > 10:
                if raw <= last_dmg:
                    return None
                amt = raw - last_dmg
                last_dmg = raw
            else:
                last_dmg = raw
                hurt_res = 20
                amt = raw
            landed = amt * factor
            hp -= landed
            return landed

        if tick % 10 == 0 and r.randrange(100) < chance:          # a swing that procs
            raw = min(weapon * 0.75, max_hp * 0.10 * level, max(0.0, hp - 1.0))
            if raw > 0:
                procs += 1
                landed = take(raw)
                if landed is None:
                    blocked += 1
                else:
                    self_total += landed
        if mob_dps_interval and tick % mob_dps_interval == 0:
            landed = take(mob_raw)
            if landed is not None:
                mob_total += landed
        if hp <= 0:
            death_tick = tick
            break

    return {"self": self_total, "mob": mob_total, "procs": procs, "blocked": blocked,
            "died": 1 if death_tick else 0,
            "survived_s": (death_tick or ticks) / 20.0}


def section_cultist():
    report_section("A. CULTIST, NOW THAT THE PRICE IS PHYSICAL -- the whole point of the change is "
                   "that armor now stands between you and the bill")
    print("  A1. What one proc costs, at full health, Cultist III (6.0 raw = 10% of max health per level)\n")
    print(f"  {'armor':<20}{'pts':>5}{'prot':>6}{'vanilla mult':>14}{'health lost per proc':>23}"
          f"{'procs to half health':>23}")
    for label, pts, prot in ARMOR_TIERS:
        mult = (25 - pts) / 25.0 * ((25 - min(20, 5 * prot)) / 25.0 if prot else 1.0)
        per = 6.0 * mult
        print(f"  {label:<20}{pts:>5}{prot:>6}{mult:>14.3f}{per:>23.2f}{10.0 / per:>23.0f}")

    print("\n  A2. A 5-minute fight, wielder mortal and regenerating, Mobzilla hitting back every 2 s.")
    print("      'self' is health lost to Cultist, 'mob' health lost to the boss.\n")
    print(f"  {'armor':<20}{'self-dmg':>10}{'mob-dmg':>10}{'self share':>12}"
          f"{'procs':>8}{'i-framed':>10}{'died':>7}{'survived':>10}")
    for label, pts, prot in ARMOR_TIERS:
        agg = defaultdict(list)
        for i in range(120):
            st = cultist_fight(pts, prot, WEAPONS["OreSpawn Ultimate"], seed=1000 + i)
            for k, v in st.items():
                agg[k].append(v)
        m = {k: statistics.mean(v) for k, v in agg.items()}
        share = m["self"] / max(m["self"] + m["mob"], 1e-9) * 100
        print(f"  {label:<20}{m['self']:>10.1f}{m['mob']:>10.1f}{share:>11.0f}%"
              f"{m['procs']:>8.0f}{m['blocked']:>10.0f}{m['died'] * 100:>6.0f}%{m['survived_s']:>9.0f}s")
    print("\n  Same enchantment, same weapon: unarmoured it is most of the damage you take, in")
    print("  enchanted diamond it is a rounding error. Note the i-framed column -- a proc that")
    print("  lands inside the invulnerability window of the boss hit you just took is free.")


# ===========================================================================
# B. Offensive combinations
# ===========================================================================
def section_offense(quick=False):
    report_section("B1. OFFENSIVE SINGLES -- sustained DPS multiplier over unenchanted, "
                   "OreSpawn Ultimate (37), 150 s window")
    weapon = WEAPONS["OreSpawn Ultimate"]

    base = {}
    for name, _ in BENCH:
        base[name] = dps_of((), name, weapon, runs=80)["dps"]

    hdr = f"  {'enchant':<16}{'rarity':<11}"
    for name, _ in BENCH:
        hdr += f"{name[:17]:>19}"
    print(hdr)
    print(f"  {'(baseline DPS)':<16}{'':<11}" + "".join(f"{base[n]:>19.1f}" for n, _ in BENCH))

    singles = {}
    for key, lvl, rar in OFFENSE:
        row = f"  {key:<16}{rar:<11}"
        singles[key] = {}
        for name, _ in BENCH:
            r = dps_of((key,), name, weapon)
            m = r["dps"] / base[name]
            singles[key][name] = m
            row += f"{m:>18.2f}x"
        print(row)

    report_section("B1b. WHAT THE DPS COLUMN MISSES -- the enchantments that read as 1.00x above "
                   "are not all doing nothing. vs OreSpawn Mobzilla, 150 s, Ultimate")
    boss0 = "OreSpawn Mobzilla"
    print(f"  {'enchant':<16}{'dps':>7}{'kills':>8}{'dmg taken':>12}{'bleed land':>12}"
          f"{'bleed lost':>12}{'poison':>9}   what it is actually for")
    notes = {
        "killingblow": "instant kill roll; invisible to DPS, decisive on a health sponge",
        "rupture":     "bleed; ticks now land past the target's invulnerability window",
        "venomous":    "venom plus a damage debuff; one of the few things a damage cap cannot stop",
        "poisonous":   "venom rides the real poison effect; undead are still immune",
        "sunder":      "cuts the TARGET's damage: defensive, not offensive",
        "cripple":     "cuts the TARGET's damage: defensive, not offensive",
        "feast":       "heals you on a kill; nothing during a single boss fight",
        "assassinate": "opener only: one hit in three hundred once the boss has aggro",
        "multistrike": "doubles other procs; worth exactly nothing on its own",
    }
    for key in ["killingblow", "rupture", "venomous", "poisonous", "sunder", "cripple",
                "feast", "assassinate", "multistrike"]:
        agg = defaultdict(list)
        for _ in range(60):
            p = Player(weapon, hp=20.0, armor=20, prot=4, immortal=True)
            sm = Sim(p, Target(TARGETS[boss0]), [(key, BY_KEY[key][1])], target_hits_every=40)
            st = sm.run(max_ticks=WINDOW)
            for k, v in st.items():
                agg[k].append(v)
        m = {k: statistics.mean(v) for k, v in agg.items()}
        secs = m["ticks"] / 20.0
        print(f"  {key:<16}{m['dmg_dealt'] / secs:>7.1f}{m.get('killingblow_kills', 0):>8.2f}"
              f"{m.get('dmg_taken', 0):>12.1f}{m.get('bleed_ticks_landed', 0):>12.1f}"
              f"{m.get('bleed_ticks_iframed', 0):>12.1f}{m.get('poison_dmg', 0):>9.1f}   {notes[key]}")

    # ---- pairs: is the pair worth more than the two parts multiplied? --------
    report_section("B2. PAIRWISE SYNERGY -- pairs whose combined multiplier beats the product of "
                   "the two singles (vs OreSpawn Mobzilla). Superlinear pairs are what makes a "
                   "loot pool dangerous, because accumulation compounds")
    boss = "OreSpawn Mobzilla"
    keys = [k for k, _, _ in OFFENSE]
    pairs = []
    for a, b in itertools.combinations(keys, 2):
        r = dps_of((a, b), boss, weapon)
        actual = r["dps"] / base[boss]
        expect = singles[a][boss] * singles[b][boss]
        pairs.append((actual / expect, actual, expect, a, b, r["cultist_deaths"]))
    pairs.sort(reverse=True)
    print(f"  {'pair':<32}{'expected':>11}{'actual':>10}{'synergy':>10}")
    for ratio, actual, expect, a, b, _cd in pairs[:12]:
        print(f"  {a + ' + ' + b:<32}{expect:>10.2f}x{actual:>9.2f}x{ratio:>9.2f}x")
    print("  ... worst (anti-synergy, the pair is worth less than its parts):")
    for ratio, actual, expect, a, b, _cd in pairs[-5:]:
        print(f"  {a + ' + ' + b:<32}{expect:>10.2f}x{actual:>9.2f}x{ratio:>9.2f}x")

    # ---- accumulation: what does k random offensive enchants get you? -------
    report_section("B3. ACCUMULATION -- a player who has collected k random offensive enchants. "
                   "Random subsets, DPS multiplier over unenchanted, vs each benchmark boss")
    trials = 80 if not quick else 15
    for name, note in BENCH:
        print(f"\n  --- {name} ({note}) ---")
        print(f"  {'k':>2}{'median':>10}{'p90':>9}{'max':>9}   {'worst-case combo at this size':<52}")
        for k in (1, 2, 3, 4, 5, 6, 8):
            seen, mults, best = set(), [], (0, None)
            for _ in range(trials):
                combo = tuple(sorted(rng.sample(keys, k)))
                if combo in seen:
                    continue
                seen.add(combo)
                m = dps_of(combo, name, weapon, runs=25)["dps"] / base[name]
                mults.append(m)
                if m > best[0]:
                    best = (m, combo)
            mults.sort()
            p90 = mults[min(len(mults) - 1, int(0.9 * len(mults)))]
            label = " + ".join(best[1]) if best[1] else ""
            print(f"  {k:>2}{statistics.median(mults):>9.2f}x{p90:>8.2f}x{best[0]:>8.2f}x   {label[:52]:<52}")

    # ---- the ceiling --------------------------------------------------------
    report_section("B4. THE CEILING -- everything at once, and the same without the pieces "
                   "a loot table could hold back")
    everything = tuple(keys)
    no_ms = tuple(k for k in keys if k != "multistrike")
    no_top = tuple(k for k in keys if k not in ("multistrike", "colossus", "excalibur", "crushingblow"))
    for label, combo in (("every offensive enchant", everything),
                         ("without Multi Strike", no_ms),
                         ("without Multi Strike, Colossus, Excalibur, Crushing Blow", no_top)):
        print(f"\n  {label}")
        for name, _ in BENCH:
            r = dps_of(combo, name, weapon, runs=60)
            ttk = f"{r['ttk']:.0f}s" if r["ttk"] else "not killed in 150s"
            print(f"    {name:<22}{r['dps'] / base[name]:>7.1f}x baseline   "
                  f"kill rate {r['kill_rate'] * 100:>3.0f}%   ttk {ttk}")


# ===========================================================================
# C. Defensive loadouts, simulated
# ===========================================================================
TURTLE_FLOOR = 0.5      # ArmorEnchants.Turtle.MINIMUM_LANDED

# ItemArmor.ArmorMaterial.getDurability multipliers, indexed by armour TYPE
# (0 helmet, 1 chest, 2 legs, 3 boots) -- not by inventory slot.
ARMOUR_TYPE = {"helmet": 0, "chest": 1, "legs": 2, "boots": 3}

DIAMOND_POINTS = {"helmet": 3, "chest": 8, "legs": 6, "boots": 3}
SLOTS = ("boots", "legs", "chest", "helmet")     # dispatch order: armorInventory 0..3


class Piece(forge_armor.Piece):
    """A worn armour stack. The armour arithmetic lives in forge_armor, which is
    a line-for-line transcription of Forge's ISpecialArmor; this only adds the
    slot, the Protection level and the QF enchantments riding on the piece."""

    def __init__(self, slot, points, prot, ench, durability_factor=33, unbreaking=0):
        forge_armor.Piece.__init__(
            self, points,
            forge_armor.MAX_DAMAGE_ARRAY[ARMOUR_TYPE[slot]] * durability_factor,
            unbreaking)
        self.slot = slot
        self.points = points
        self.prot = prot
        self.ench = dict(ench)      # name -> level


class Defender:
    """A player wearing four armor pieces, being hit."""

    def __init__(self, pieces, sheathed=True, vigor=0, base_hp=20.0):
        self.pieces = pieces
        self.sheathed = sheathed
        self.max_hp = base_hp + 4.0 * vigor
        self.hp = self.max_hp
        self.hurt_res = 0
        self.last_dmg = 0.0
        self.last_hurt_tick = -10 ** 9
        self.dead = False
        self.absorb = 0.0
        self.potions = {}           # name -> [ticks, amp]
        self.dist = 2.0             # blocks from the attacker
        self.saves_used = 0
        self.cockroach_ready = -10 ** 9
        self.rng = random

    def live(self):
        return [p for p in self.pieces if not p.broken]

    def armor_points(self):
        return sum(p.points for p in self.live())

    def prot_modifier(self):
        """EnchantmentHelper.getEnchantmentModifierDamage, then the cap in
        applyPotionDamageCalculations.

        The summed level is NOT the modifier. 1.7.10 rolls it:
            return (k + 1 >> 1) + rand.nextInt((k >> 1) + 1)
        so four pieces of Protection IV (k = 20) give a modifier uniformly in
        10..20, i.e. a reduction between 60% and 20%, averaging 40% -- not the
        flat 80% a naive reading of the cap suggests. This file used the flat
        reading until it was checked against the real method.
        """
        total = 0
        for p in self.live():
            if p.prot:
                total += int((6 + p.prot * p.prot) / 3.0 * 0.75)
        total = min(25, total)                       # cap inside getEnchantmentModifierDamage
        rolled = ((total + 1) >> 1) + random.randint(0, total >> 1)
        return min(20, rolled)                       # cap inside applyPotionDamageCalculations

    def level_of(self, name):
        """Total level across worn pieces (per-piece enchants stack)."""
        return sum(p.ench.get(name, 0) for p in self.live())

    def pieces_with(self, name):
        return [p for p in self.live() if name in p.ench]


def defend_hit(d, raw, tick, stats, source="melee"):
    """One incoming hit, through the whole chain. Returns damage that landed."""
    fired, amt = vanilla_attack(d, raw, tick)
    if not fired:
        stats["hits_iframed"] += 1
        return 0.0
    stats["hits_landed"] += 1

    # --- QF onDamaged, MULTIPLIER phase: the always-on reductions -------------
    tank = d.level_of("tank")
    if tank:
        amt *= (1.0 - 0.11 * min(3, tank))
    bul = d.level_of("bulwark")
    if bul:
        missing = 1.0 - (d.hp / d.max_hp)
        amt *= (1.0 - 0.10 * min(3, bul) * missing)
    if d.sheathed:
        for _ in d.pieces_with("turtle"):
            amt *= (1.0 - 0.33)
    if source in ("blast", "fall"):
        for p in d.pieces_with("stonehide"):
            amt *= (1.0 - 0.12 * p.ench["stonehide"] / 4.0)

    # --- QF onDamaged, PROC phase -------------------------------------------
    # Cockroach no longer blunts the hit; it answers it. Handled after the
    # damage lands, below.

    # Knockback effects buy time rather than reducing the hit.
    for p in d.pieces_with("rebound"):
        if rng.randrange(100) < 2 * p.ench["rebound"]:
            d.dist = max(d.dist, 2.0 + 4.0)
            stats["rebound_procs"] += 1
            break
    reflect_pieces = d.pieces_with("reflect")
    for p in reflect_pieces:
        if rng.randrange(100) < 4 + 4 * p.ench["reflect"]:
            d.dist = max(d.dist, 2.0 + 2.0 * len(reflect_pieces))
            stats["reflect_procs"] += 1
            break

    # --- vanilla mitigation --------------------------------------------------
    after_armour = forge_armour(d, amt, spend=True)
    factor = vanilla_factor(d)
    landed = after_armour * factor
    # Turtle guarantees a minimum landed hit, so a shell can always be cracked --
    # but never more than the hit would have done without Turtle at all.
    turtle_pieces = len(d.pieces_with("turtle"))
    if d.sheathed and turtle_pieces and landed > 0.0:
        without = landed / (0.67 ** turtle_pieces)
        landed = max(landed, min(TURTLE_FLOOR, without))
    a = min(d.absorb, landed)
    d.absorb -= a
    landed -= a
    d.hp -= landed
    d.last_hurt_tick = tick
    stats["dmg_taken"] += landed

    # Armor durability: vanilla damages armor on every non-bypassing hit.
    stats["armor_wear"] += raw / 4.0

    # Cockroach: a hit that leaves you alive on your last heart buys a short
    # burst of heavy Resistance, then goes on a one-minute cooldown.
    cock = d.level_of("cockroach")
    if cock and 0.0 < d.hp <= 2.0 and tick >= d.cockroach_ready:
        level = min(3, cock)
        d.potions["resistance"] = [80 + 20 * level, min(3, level)]
        d.cockroach_ready = tick + 1200
        stats["cockroach_procs"] += 1

    if d.hp <= 0:
        sacs = d.pieces_with("sacrifice")
        if sacs:
            piece = sacs[0]
            piece.broken = True
            d.saves_used += 1
            d.hp = d.max_hp * 0.5
            d.potions = {"regeneration": [200, 1], "resistance": [200, 1]}
            stats["sacrifice_saves"] += 1
        else:
            d.dead = True
    return landed


def forge_armour(d, raw, spend=True, unblockable=False):
    """The player's armour step: Forge's ApplyArmor, transcribed in forge_armor.py.

    Vanilla's (25 - points)/25 is NOT the player's path -- Forge patches
    EntityPlayer.damageEntity to call ApplyArmor instead. Below 25 points the two
    agree exactly, which is why the difference went unnoticed; at and above 25
    they do not. ApplyArmor caps each piece's absorption by its REMAINING
    DURABILITY and spends that durability as it goes, which is what stops a
    25-point set from being permanently invulnerable.
    """
    pieces = list(d.pieces)
    return forge_armor.apply_armor(pieces, raw, d.rng, spend=spend,
                                   unblockable=unblockable)


def vanilla_factor(d):
    """Read-only multiplier for the potion/protection steps only."""
    f = 1.0
    res = d.potions.get("resistance")
    if res:
        f *= (25 - 5 * (res[1] + 1)) / 25.0
    k = d.prot_modifier()
    if k:
        f *= (25 - k) / 25.0
    return f


def tick_defender(d, tick, stats):
    if d.hurt_res > 0:
        d.hurt_res -= 1
    # regeneration
    regen = d.potions.get("regeneration")
    if regen:
        period = max(1, 50 >> regen[1])
        if tick % period == 0:
            d.hp = min(d.max_hp, d.hp + 1.0)
            stats["healed"] += 1
    else:
        regrowth = d.level_of("regrowth")
        if regrowth and (tick - d.last_hurt_tick) > 200:
            period = max(1, 50 >> (min(3, regrowth) - 1))
            if tick % period == 0:
                d.hp = min(d.max_hp, d.hp + 1.0)
                stats["healed"] += 1
        elif tick % 80 == 0:                      # natural regeneration, well fed
            d.hp = min(d.max_hp, d.hp + 1.0)
    for name in list(d.potions):
        d.potions[name][0] -= 1
        if d.potions[name][0] <= 0:
            del d.potions[name]


def survive(loadout, raw_hit, interval, sheathed=True, mob_speed=4.3,
            max_ticks=20 * 600, source="melee", points=None, durability=33):
    """How long a loadout lasts under a fixed incoming attack. Returns stats."""
    d = Defender(build_pieces(loadout, points, durability), sheathed=sheathed,
                 vigor=loadout.get("vigor", 0))

    stats = defaultdict(float)
    tick = 0
    next_attack = interval
    while tick < max_ticks and not d.dead:
        tick += 1
        tick_defender(d, tick, stats)
        # attacker walks back in if it was thrown
        if d.dist > 2.0:
            d.dist = max(2.0, d.dist - mob_speed / 20.0)
            stats["ticks_out_of_reach"] += 1
        if tick >= next_attack:
            if d.dist <= 2.01:
                defend_hit(d, raw_hit, tick, stats, source=source)
                next_attack = tick + interval
            else:
                next_attack = tick + 1        # waiting to get back into reach
    stats["survived_s"] = tick / 20.0
    stats["died"] = 1 if d.dead else 0
    stats["saves"] = d.saves_used
    return stats


def run_survive(loadout, raw_hit, interval, runs=40, **kw):
    agg = defaultdict(list)
    for _ in range(runs):
        st = survive(loadout, raw_hit, interval, **kw)
        for k, v in st.items():
            agg[k].append(v)
    return {k: statistics.mean(v) for k, v in agg.items()}


def split_points(total):
    """Spread an armour total across the four slots in vanilla's proportions."""
    share = {"helmet": 3 / 20.0, "chest": 8 / 20.0, "legs": 6 / 20.0, "boots": 3 / 20.0}
    out, used = {}, 0
    for slot in ("helmet", "chest", "legs"):
        out[slot] = int(round(total * share[slot]))
        used += out[slot]
    out["boots"] = total - used
    return out


def build_pieces(loadout, points=None, durability=33):
    pieces = []
    pts = points or DIAMOND_POINTS
    for slot in SLOTS:
        ench = dict(loadout.get("all", {}))
        ench.update(loadout.get(slot, {}))
        pieces.append(Piece(slot, pts[slot], loadout.get("prot", 4), ench, durability))
    return pieces


def per_hit(loadout, raw, sheathed=True, at_health=None, points=None, durability=33):
    """Damage that reaches the health bar from one hit, on a fresh wearer."""
    d = Defender(build_pieces(loadout, points, durability), sheathed=sheathed, vigor=loadout.get("vigor", 0))
    if at_health is not None:
        d.hp = at_health
    return defend_hit(d, raw, 100, defaultdict(float))


DEF_LOADOUTS = [
    ("bare diamond, Prot IV",              {}),
    ("+ Vigor III",                        {"vigor": 3, "chest": {"vigor": 3}}),
    ("+ Tank III",                         {"chest": {"tank": 3}}),
    ("+ Bulwark III",                      {"chest": {"bulwark": 3}}),
    ("+ Cockroach III",                    {"chest": {"cockroach": 3}}),
    ("+ Stonehide III (all)",              {"all": {"stonehide": 3}}),
    ("+ Sacrifice (all four)",             {"all": {"sacrifice": 1}}),
    ("+ Rebound III (all)",                {"all": {"rebound": 3}}),
    ("+ Reflect III (all)",                {"all": {"reflect": 3}}),
    ("+ Regrowth III",                     {"legs": {"regrowth": 3}}),
    ("+ Turtle (all four)",                {"all": {"turtle": 1}}),
    ("chest stack: Tank+Bulwark+Cockroach+Vigor",
     {"vigor": 3, "chest": {"tank": 3, "bulwark": 3, "cockroach": 3, "vigor": 3}}),
    ("everything except Turtle",
     {"vigor": 3, "all": {"stonehide": 3, "sacrifice": 1, "rebound": 3, "reflect": 3},
      "chest": {"tank": 3, "bulwark": 3, "cockroach": 3, "vigor": 3}, "legs": {"regrowth": 3}}),
    ("everything, Turtle included",
     {"vigor": 3, "all": {"stonehide": 3, "sacrifice": 1, "rebound": 3, "reflect": 3, "turtle": 1},
      "chest": {"tank": 3, "bulwark": 3, "cockroach": 3, "vigor": 3}, "legs": {"regrowth": 3}}),
]

# Damage figures are the mobs' real ones. OreSpawn's come from the mob block of
# OreSpawn.cfg (TheKing_attack=350, Mobzilla_attack=175, Kraken_attack=40);
# MobProperties scales these bosses' HEALTH by 3-6x and does not touch their
# damage. An earlier version of this file called 40 "The King" -- that is the
# Kraken's number, and it understated the King by nearly nine times.
ATTACKERS = [
    ("Mutant Zombie (24/hit, 1s)",       24, 20),
    ("OreSpawn Kraken (40/hit, 1s)",     40, 20),
    ("OreSpawn Mobzilla (175/hit, 1s)", 175, 20),
    ("OreSpawn The King (350/hit, 1s)", 350, 20),
    ("swarm (8/hit, every 0.25s)",        8,  5),
    # Without a blast row Stonehide reads as doing nothing, which is only true of melee.
    ("creeper blast (49/hit, every 3s)", 49, 60),
]
BLAST_LABEL = "creeper blast (49/hit, every 3s)"


def section_defense():
    report_section("C1. DEFENSIVE LOADOUTS -- seconds survived under sustained attack, full diamond "
                   "+ Prot IV underneath, weapon sheathed (so Turtle is live). 10 min cap")
    for label, raw, interval in ATTACKERS:
        print(f"\n  --- attacker: {label} ---")
        print(f"  {'loadout':<44}{'survived':>11}{'hits':>7}{'saves':>7}{'died':>7}")
        src = "blast" if label == BLAST_LABEL else "melee"
        for name, loadout in DEF_LOADOUTS:
            r = run_survive(loadout, raw, interval, runs=120, source=src)
            secs = r["survived_s"]
            shown = f"{secs:.0f}s" if r["died"] > 0.5 else f">{secs:.0f}s"
            print(f"  {name:<44}{shown:>11}{r['hits_landed']:>7.0f}"
                  f"{r['saves']:>7.1f}{r['died'] * 100:>6.0f}%")

    report_section("C2. THE TURTLE QUESTION -- Turtle only works with the weapon put away, so the "
                   "real question is what drawing it costs. Damage taken from one 175-damage Mobzilla "
                   "swing, sheathed against armed")
    print(f"  {'loadout':<44}{'sheathed':>11}{'armed':>10}{'cost of drawing':>18}")
    for name, loadout in DEF_LOADOUTS:
        if "turtle" not in str(loadout):
            continue
        a = per_hit(loadout, 175.0, sheathed=True)
        b = per_hit(loadout, 175.0, sheathed=False)
        print(f"  {name:<44}{a:>11.3f}{b:>10.3f}{b / max(a, 1e-9):>17.1f}x")
    print("\n  Turtle is worth about five times your survivability and costs you the ability to")
    print("  swing. It is a stance, not a passive -- which is the right shape for a Legendary.")

    report_section("C3. PER-HIT MITIGATION -- what fraction of a 175-damage Mobzilla swing reaches the "
                   "health bar, and the effective health pool that implies")
    print(f"  {'loadout':<44}{'per hit':>10}{'of raw':>9}{'effective HP':>15}")
    for name, loadout in DEF_LOADOUTS:
        pieces = []
        for slot in SLOTS:
            ench = dict(loadout.get("all", {}))
            ench.update(loadout.get(slot, {}))
            pieces.append(Piece(slot, DIAMOND_POINTS[slot], loadout.get("prot", 4), ench))
        d = Defender(pieces, sheathed=True, vigor=loadout.get("vigor", 0))
        stats = defaultdict(float)
        landed = defend_hit(d, 175.0, 100, stats)
        pool = d.max_hp * (1 + len(d.pieces_with("sacrifice")) * 0.5)
        hits = pool / max(landed, 1e-6)
        print(f"  {name:<44}{landed:>10.3f}{landed / 175.0 * 100:>8.1f}%{hits:>12.0f} hits")

    report_section("C4. KNOCKBACK AS MITIGATION -- how much attack uptime Reflect and Rebound "
                   "actually remove, by how fast the attacker returns")
    loadout = {"all": {"reflect": 3, "rebound": 3}}
    print(f"  {'attacker return speed':<30}{'uptime removed':>17}{'survival vs bare':>19}")
    bare = run_survive({}, 40, 20, runs=120)["survived_s"]
    for speed, label in ((2.0, "slow (2.0 blocks/s)"), (4.3, "walking (4.3 blocks/s)"),
                         (5.6, "sprinting (5.6 blocks/s)"), (10.0, "flying boss (10 blocks/s)")):
        r = run_survive(loadout, 40, 20, runs=30, mob_speed=speed)
        removed = r["ticks_out_of_reach"] / max(r["survived_s"] * 20.0, 1)
        print(f"  {label:<30}{removed * 100:>16.0f}%{r['survived_s'] / max(bare, 0.05):>18.1f}x")


def section_regen_threshold():
    report_section("C5. THE LINE BETWEEN TOUGH AND UNKILLABLE -- natural regeneration is 1 health "
                   "every 4 seconds, so 0.25 health per second of incoming damage is the threshold. "
                   "Below it, that attacker can never kill you")
    print(f"  {'loadout':<44}{'40/hit 1s':>13}{'175/hit 1s':>13}{'8/hit 0.25s':>13}")
    for name, loadout in DEF_LOADOUTS:
        cells = ""
        for raw, interval in ((40, 20), (175, 20), (8, 5)):
            landed = per_hit(loadout, float(raw))
            # at a 5-tick interval the invulnerability window eats every other hit
            rate = landed / (interval / 20.0) * (0.5 if interval < 10 else 1.0)
            cells += f"{rate:>12.2f}{'*' if rate < 0.25 else ' '}"
        print(f"  {name:<44}{cells}")
    print("\n  * would mark incoming damage below the regeneration floor -- an attacker that can")
    print("  never kill you. Nothing on this table earns one any more. On the corrected armour")
    print("  model even Turtle plus the whole defensive stack takes 0.50 a second from a Kraken")
    print("  and 0.95 from Mobzilla, both above the floor. The earlier pass put several loadouts")
    print("  under it, which was an artefact of using the wrong armour formula and of calling a")
    print("  40-damage hit The King.")



# ===========================================================================
# D. The pack's actual gear
#
# Every figure above assumes vanilla diamond and a diamond-tier weapon, which
# almost nobody in this pack is wearing by the time they meet the bosses being
# benchmarked. Armour totals read out of the mod jars with javap (EnumHelper
# takes its numbers as bytecode constants) and out of OreSpawn.cfg, which is
# config-driven. Weapon damage from OreSpawn.cfg.
# ===========================================================================

# (label, total armour points, tier)
# (label, per-piece reduction [helmet, chest, legs, boots], durability factor,
#  built-in Protection level, built-in Unbreaking level, tier)
# OreSpawn rows come from the orespawnarmor block of OreSpawn.cfg; the rest from
# javap on EnumHelper.addArmorMaterial. Durability and the built-in enchantments
# matter as much as the point total, because Forge's ApplyArmor caps each piece's
# absorption at its REMAINING DURABILITY -- see forge_armor.py.
ARMOUR_TIERS = [
    ("vanilla leather",         [1, 3, 2, 1],   5,  0, 0, "early"),
    ("OreSpawn peacock",        [2, 5, 4, 2],  40,  0, 0, "early"),
    ("vanilla iron",            [2, 6, 5, 2],  15,  0, 0, "early"),
    ("Railcraft steel",         [2, 6, 5, 2],  25,  0, 0, "mid"),
    ("TragicMC tungsten",       [3, 6, 4, 2],  22,  0, 0, "mid"),
    ("OreSpawn lava eel",       [2, 7, 5, 2],  40,  3, 0, "mid"),
    ("TragicMC dark",           [3, 7, 5, 3],  18,  0, 0, "mid"),
    ("OreSpawn emerald",        [3, 8, 6, 3],  60,  0, 0, "mid"),
    ("vanilla diamond",         [3, 8, 6, 3],  33,  0, 0, "mid"),
    ("OreSpawn amethyst",       [4, 8, 7, 3], 100,  0, 0, "mid"),
    ("OreSpawn tiger's eye",    [4, 8, 7, 4],  80,  0, 0, "high"),
    ("Railcraft void fortress", [4, 8, 7, 4],  18,  0, 0, "high"),
    ("TragicMC overlord",       [5, 8, 7, 4],  35,  0, 0, "high"),
    ("OreSpawn experience",     [5, 9, 7, 4],  70,  2, 0, "high"),
    ("OreSpawn ruby",           [4, 9, 8, 4],  90,  0, 0, "high"),
    ("OreSpawn ultimate",       [6, 12, 10, 6], 200, 5, 0, "extreme"),
    ("OreSpawn mobzilla",       [7, 13, 11, 7], 1000, 10, 5, "extreme"),
    ("OreSpawn queen",          [9, 16, 14, 9], 1500, 0, 0, "extreme"),
    ("OreSpawn royal",          [8, 14, 12, 8], 2000, 10, 5, "extreme"),
]

# (label, attack damage). From the OreSpawn.cfg mob block. MobProperties gives
# these bosses a x3-x6 HEALTH modifier and no damage modifier, so these stand.
BOSS_HITS = [("Kraken", 40), ("Mobzilla", 175), ("The Queen", 225), ("The King", 350)]

# (label, attack damage, tier)
WEAPON_TIERS = [
    ("vanilla diamond sword",  8,   "early"),
    ("OreSpawn ruby",          16,  "mid"),
    ("TragicMC tragic",        26,  "mid"),
    ("OreSpawn ultimate",      36,  "high"),
    ("OreSpawn battle axe",    46,  "high"),
    ("OreSpawn chainsaw",      56,  "high"),
    ("OreSpawn attitude",      82,  "high"),
    ("Big Bertha",             496, "extreme"),
    ("OreSpawn royal guardian", 746, "extreme"),
]

FULL_DEF = {"vigor": 3,
            "all": {"stonehide": 3, "sacrifice": 1, "rebound": 3, "reflect": 3},
            "chest": {"tank": 3, "bulwark": 3, "cockroach": 3, "vigor": 3},
            "legs": {"regrowth": 3}}
FULL_DEF_TURTLE = dict(FULL_DEF)
FULL_DEF_TURTLE["all"] = dict(FULL_DEF["all"]); FULL_DEF_TURTLE["all"]["turtle"] = 1


def section_gear():
    report_section("D1. OFFENSIVE ENCHANTS ACROSS THE PACK'S WEAPON TIERS -- DPS multiplier over "
                   "the same weapon unenchanted, vs OreSpawn Mobzilla. Does an enchantment keep "
                   "its value as the weapon grows?")
    picks = [("rage", 3), ("colossus", 3), ("executioner", 3), ("rupture", 3), ("cultist", 3)]
    hdr = f"  {'weapon':<26}{'tier':<9}{'atk':>5}{'base dps':>10}"
    for k, _ in picks:
        hdr += f"{k[:10]:>11}"
    hdr += f"{'all 19':>9}"
    print(hdr)
    for label, atk, tier in WEAPON_TIERS:
        base = dps_of((), "OreSpawn Mobzilla", atk, runs=40)["dps"]
        row = f"  {label:<26}{tier:<9}{atk:>5}{base:>10.1f}"
        for k, lvl in picks:
            r = dps_of((k,), "OreSpawn Mobzilla", atk, runs=40)
            row += f"{r['dps'] / base:>10.2f}x"
        allr = dps_of(tuple(k for k, _, _ in OFFENSE), "OreSpawn Mobzilla", atk, runs=30)
        row += f"{allr['dps'] / base:>8.1f}x"
        print(row)
    print("\n  Colossus is the only one whose value falls as the weapon grows -- its bonus is")
    print("  capped at four times the triggering hit, so a bigger hit raises the cap it is")
    print("  already below. Everything else is a multiplier and holds its value exactly.")

    report_section("D2. WHAT ONE BOSS SWING ACTUALLY COSTS -- damage reaching the health bar "
                   "from a single hit on a FRESH set, built-in enchantments only. A player has "
                   "20 HP")
    hdr = f"  {'armour set':<26}{'pts':>4}{'dur':>6}{'prot':>5}"
    for name, raw in BOSS_HITS:
        hdr += f"{name + ' ' + str(raw):>16}"
    print(hdr)
    print("  " + "-" * (len(hdr) - 2))
    for label, red, dur, prot, unb, tier in ARMOUR_TIERS:
        row = f"  {label:<26}{sum(red):>4}{dur:>6}{prot:>5}"
        for _, raw in BOSS_HITS:
            landed = gear_per_hit(red, dur, prot, unb, raw)
            mark = " KO" if landed >= 20.0 else ""
            row += f"{f'{landed:.1f}{mark}':>16}"
        print(row)
    print("\n  Forge's ApplyArmor caps each piece's absorption at its remaining durability, and")
    print("  damage is scaled by 25 inside that check -- so a piece can absorb at most")
    print("  (remaining durability / 25) damage from any ONE hit, however many armour points it")
    print("  carries. That is why the point total stops predicting anything as the hits get big:")
    print("  a full vanilla diamond set holds 1819 durability, which is 72.8 damage of absorption,")
    print("  against a swing of 350. Nothing in this pack is immune to The King.")

    report_section("D3. HOW LONG A FIGHT LASTS -- seconds survived at one landing hit a second "
                   "(the invulnerability-frame ceiling for a constant attacker), with natural "
                   "regeneration at 0.25 HP/s. 1800 = the 30 minute cap")
    hdr = f"  {'armour set':<26}{'pts':>4}{'dur':>6}{'prot':>5}{'unb':>4}"
    for name, _ in BOSS_HITS:
        hdr += f"{name:>12}"
    print(hdr)
    print("  " + "-" * (len(hdr) - 2))
    for label, red, dur, prot, unb, tier in ARMOUR_TIERS:
        row = f"  {label:<26}{sum(red):>4}{dur:>6}{prot:>5}{unb:>4}"
        for _, raw in BOSS_HITS:
            secs = gear_survive(red, dur, prot, unb, raw)
            row += f"{(str(secs) if secs < 1800 else '>1800'):>12}"
        print(row)
    print("\n  Everything below OreSpawn ultimate is killed by a single swing from The King, the")
    print("  Queen or Mobzilla, regardless of armour points. The four extreme sets survive")
    print("  because of durability, not points: Queen has the most points in the pack (48) and")
    print("  still dies faster than Royal (42), which has twice the durability, Protection X and")
    print("  Unbreaking V built in.")


def gear_prot_modifier(level, pieces=4, rng=None):
    """The summed level, then the ROLL in getEnchantmentModifierDamage, then the
    cap in applyPotionDamageCalculations. See Defender.prot_modifier."""
    if level <= 0:
        return 0
    total = min(25, pieces * int((6 + level * level) / 3.0 * 0.75))
    rolled = ((total + 1) >> 1) + (rng or random).randint(0, total >> 1)
    return min(20, rolled)


def gear_per_hit(red, dur, prot, unb, raw):
    pieces = [forge_armor.Piece(red[t], forge_armor.MAX_DAMAGE_ARRAY[t] * dur, unb)
              for t in range(4)]
    landed = max(0.0, forge_armor.apply_armor(pieces, raw, spend=False))
    k = gear_prot_modifier(prot)
    return landed * (25 - k) / 25.0 if k else landed


def gear_survive(red, dur, prot, unb, raw, trials=15, cap=1800):
    out = []
    for t in range(trials):
        rng = random.Random(hash((tuple(red), dur, raw, t)) & 0xffff)
        pieces = [forge_armor.Piece(red[i], forge_armor.MAX_DAMAGE_ARRAY[i] * dur, unb)
                  for i in range(4)]
        hp = 20.0
        secs = cap
        for s in range(cap):
            landed = max(0.0, forge_armor.apply_armor(pieces, raw, rng))
            k = gear_prot_modifier(prot, sum(1 for p in pieces if not p.broken), rng)
            if k:
                landed = landed * (25 - k) / 25.0
            hp = min(20.0, hp - landed + 0.25)      # FoodStats: 1 HP per 80 ticks
            if hp <= 0:
                secs = s + 1
                break
        out.append(secs)
    out.sort()
    return out[len(out) // 2]


if __name__ == "__main__":
    quick = "--quick" in sys.argv
    section_cultist()
    section_offense(quick=quick)
    section_defense()
    section_regen_threshold()
    section_gear()
    print()
