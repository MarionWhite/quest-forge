"""Survival by armour set against the pack's real bosses.

Every number here comes from a config file or the decompiled source, not from
memory:
  armour reductions, durability, built-in Protection/Unbreaking  OreSpawn.cfg
  boss attack damage                                             OreSpawn.cfg
  boss health multiplier (x3-x6, no damage multiplier)           MobProperties/
  the armour arithmetic                                          forge_armor.py
  Protection modifier floor((6+l*l)/3*0.75), capped at 20        EnchantmentProtection
  natural regeneration 1 HP / 80 ticks at food >= 18             FoodStats.onUpdate
"""
import json, random, forge_armor as fa

OS = json.load(open("orespawn_armour.json"))

# name -> (reductions [h,c,l,b], durability factor, built-in prot, built-in unbreaking)
SETS = {n: (v["red"], v["dur"], v["prot"], v["unb"]) for n, v in OS.items()}
SETS.update({
    "vanilla leather":        ([1, 3, 2, 1], 5,  0, 0),
    "vanilla iron":           ([2, 6, 5, 2], 15, 0, 0),
    "vanilla diamond":        ([3, 8, 6, 3], 33, 0, 0),
    "Railcraft steel":        ([2, 6, 5, 2], 25, 0, 0),
    "Railcraft void fortress":([4, 8, 7, 4], 18, 0, 0),
    "TragicMC tungsten":      ([3, 6, 4, 2], 22, 0, 0),
    "TragicMC dark":          ([3, 7, 5, 3], 18, 0, 0),
    "TragicMC overlord":      ([5, 8, 7, 4], 35, 0, 0),
})

BOSSES = [("OreSpawn Kraken", 40), ("OreSpawn Mobzilla", 175),
          ("OreSpawn The Queen", 225), ("OreSpawn The King", 350)]


def prot_modifier(level, pieces=4):
    if level <= 0: return 0
    return min(20, pieces * int((6 + level * level) / 3.0 * 0.75))


def survive(red, dur, prot, unb, raw, max_s=1800, rng=None, regen=True):
    """Hits taken before death, at one landing hit a second (the i-frame ceiling
    for a constant-damage attacker). Returns (seconds, hit the first piece broke)."""
    rng = rng or random
    pieces = [fa.Piece(red[t], fa.MAX_DAMAGE_ARRAY[t] * dur, unb) for t in range(4)]
    hp = 20.0
    first_break = None
    for s in range(max_s):
        landed = max(0.0, fa.apply_armor(pieces, raw, rng))
        # applyPotionDamageCalculations: protection, capped at 20 of 25
        live = sum(1 for p in pieces if not p.broken)
        k = prot_modifier(prot, live)
        if k: landed = landed * (25 - k) / 25.0
        hp -= landed
        if regen: hp = min(20.0, hp + 0.25)      # 1 HP per 80 ticks, fed
        if first_break is None and any(p.broken for p in pieces):
            first_break = s + 1
        if hp <= 0:
            return s + 1, first_break
    return max_s, first_break


def table(prot_override=None, unb_override=None, label=""):
    print(f"\n  Seconds survived at one landing hit a second{label}. 1800 = 30 min cap.")
    hdr = f"  {'armour set':<26}{'pts':>4}{'dur':>6}{'prot':>5}{'unb':>4}"
    for b, _ in BOSSES: hdr += f"{b.split()[-1]:>12}"
    print(hdr); print("  " + "-" * (len(hdr) - 2))
    rows = sorted(SETS.items(), key=lambda kv: sum(kv[1][0]))
    for name, (red, dur, prot, unb) in rows:
        p = prot if prot_override is None else max(prot, prot_override)
        u = unb if unb_override is None else max(unb, unb_override)
        row = f"  {name:<26}{sum(red):>4}{dur:>6}{p:>5}{u:>4}"
        for _, raw in BOSSES:
            rng = random.Random(hash((name, raw)) & 0xffff)
            secs = [survive(red, dur, p, u, raw, rng=rng)[0] for _ in range(15)]
            secs.sort(); m = secs[len(secs) // 2]
            row += f"{(str(m) if m < 1800 else '>1800'):>12}"
        print(row)


if __name__ == "__main__":
    print("=" * 96)
    print("  ARMOUR SETS vs THE PACK'S BOSSES -- built-in enchantments only, as the set drops")
    print("=" * 96)
    table()
    print("\n" + "=" * 96)
    print("  THE SAME SETS, PLAYER-ENCHANTED to Protection IV / Unbreaking III")
    print("=" * 96)
    table(prot_override=4, unb_override=3, label=", Prot IV / Unbreaking III")
