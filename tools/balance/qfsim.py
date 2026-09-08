#!/usr/bin/env python3
"""
QuestForge custom-enchant balance simulation.

Replicates EnchantDispatcher/EnchantEventBridge semantics as written in the
mod source (proc rolls, NBT-order iteration, Multi Strike replay, Rupture bleed
re-dispatch, Arc chaining) on top of the vanilla 1.7.10 damage pipeline
(i-frames, armor, Strength x2.3, potion tick rates) and the pack's actual
targets (MobProperties multipliers, OreSpawn config health, Lycanites caps).
"""
import random, math, statistics, json, sys
from collections import defaultdict, Counter

rng = random.Random(12345)
TUNED = "--tuned" in sys.argv   # simulate the 2026-09-06 changes instead of the original code

# ---------------------------------------------------------------- targets ----
# (name, base_hp, armor_pts, attack, hp_mult_range, dmg_mult_range, undead, cap, defense, group)
# hp_mult = MobProperties op1 additive multiplier: hp * (1 + U(a,b))
TARGETS = {
    "Zombie":            dict(hp=20,   armor=2,  atk=3,   mp=(3,9),  dmp=(0.5,2), undead=True,  cap=None, defense=0),
    "Creeper":           dict(hp=20,   armor=0,  atk=0,   mp=(3,9),  dmp=(0.5,2), undead=False, cap=None, defense=0),
    "Mutant Zombie":     dict(hp=150,  armor=0,  atk=12,  mp=(3,9),  dmp=(0.5,2), undead=True,  cap=None, defense=0),
    "TF Naga":           dict(hp=120,  armor=0,  atk=6,   mp=(3,9),  dmp=(0.5,2), undead=False, cap=None, defense=0),
    "TF Hydra":          dict(hp=360,  armor=0,  atk=12,  mp=(3,9),  dmp=(0.5,2), undead=False, cap=None, defense=0),
    "Ender Dragon":      dict(hp=200,  armor=0,  atk=10,  mp=(3,9),  dmp=(0.5,2), undead=False, cap=None, defense=0),
    "Wither":            dict(hp=300,  armor=4,  atk=8,   mp=(3,9),  dmp=(0.5,2), undead=True,  cap=None, defense=0),
    "Witchery Death":    dict(hp=1000, armor=0,  atk=7,   mp=(3,9),  dmp=(0.5,2), undead=True,  cap=None, defense=0),
    "OreSpawn Kraken":   dict(hp=1000, armor=0,  atk=15,  mp=(2,5),  dmp=(0,0),   undead=False, cap=None, defense=0),
    "OreSpawn Mobzilla": dict(hp=4000, armor=0,  atk=25,  mp=(2,5),  dmp=(0,0),   undead=False, cap=None, defense=0),
    "OreSpawn The King": dict(hp=7000, armor=0,  atk=40,  mp=(2,5),  dmp=(0,0),   undead=False, cap=None, defense=0),
    "Lycanites Rahovart":dict(hp=5000, armor=0,  atk=18,  mp=(3,9),  dmp=(0.5,2), undead=False, cap=25,   defense=2),
    "TragicMC boss(1k)": dict(hp=1000, armor=0,  atk=15,  mp=(2,5),  dmp=(0,0),   undead=False, cap=25,   defense=0),
}

# weapon attack-damage attribute totals (vanilla base 1 + weapon modifier)
WEAPONS = {"Diamond sword": 8, "TragicMC Tragic": 26, "OreSpawn Ultimate": 37,
           "OreSpawn Attitude": 83, "Big Bertha": 497, "Royal Guardian": 747}

# ---------------------------------------------------------------- enchants ---
# proc chances exactly as in code
def proc(name, lvl):
    return {
        "executioner": 100, "berserk": 100, "roulette": 100, "momentum": 100, "riposte": 100,
        "assassinate": 100, "excalibur": 100, "killingblow": 100, "crushingblow": 100,
        "colossus": 3 + 3*lvl, "cultist": 8*lvl, "rupture": 15 + 10*lvl, "arc": 10 + 5*lvl,
        "poisonous": 10*lvl, "venomous": 8*lvl, "rage": 5*lvl, "sunder": 10*lvl, "cripple": 10*lvl,
        "accelerant": 12, "necromancer": 3*lvl, "bastion": 3*lvl, "alpha": 3*lvl, "frostbite": 10+10*lvl,
        "feast": 100, "lich": 100, "multistrike": 100,
    }[name]

NOT_MULTIPLIABLE = {"excalibur", "crushingblow", "multistrike"}
TUNED_NOT_MULTIPLIABLE = NOT_MULTIPLIABLE | {"executioner","berserk","assassinate","roulette","momentum","riposte","cultist"}
PHASE = {"momentum":0,"riposte":0,"excalibur":0,"executioner":1,"berserk":1,"assassinate":1,"roulette":1,"crushingblow":1,"cultist":1}

class Target:
    def __init__(self, spec, mp_roll=None):
        m = rng.uniform(*spec["mp"]) if mp_roll is None else mp_roll
        self.max_hp = spec["hp"] * (1 + m)
        self.hp = self.max_hp
        self.armor = spec["armor"]; self.undead = spec["undead"]
        self.cap = spec["cap"]; self.defense = spec["defense"]
        d = rng.uniform(*spec["dmp"])
        self.atk = spec["atk"] * (1 + d)
        self.hurt_res = 0; self.last_dmg = 0.0
        self.potions = {}          # id -> [duration, amp]
        self.bleed = None          # [stacks, ticksLeft, nextTick, perStack]
        self.venom = None          # [perTick, ticksLeft]
        self.cripple = None        # [reduction, ticksLeft]
        self.targeting = False
        self.dead = False
        self.absorb = 0.0

class Player:
    def __init__(self, weapon, hp=20.0, armor=20, prot=0, strength=False, resist=False, immortal=False):
        self.weapon = weapon; self.max_hp = hp; self.hp = hp
        self.immortal = immortal
        self.armor = armor; self.prot = prot
        self.strength_ticks = 10**9 if strength else 0
        self.resist = resist
        self.hurt_res = 0; self.last_dmg = 0.0
        self.last_hurt_tick = -10**9
        self.absorb = 0.0
        self.dead = False
        self.streak_target = None; self.streak = 0; self.streak_tick = -10**9
        self.cooldowns = {}

# ------------------------------------------------------------- damage core ---
def vanilla_attack(ent, amount, tick, bypass_armor=False, cap=True):
    """EntityLivingBase.attackEntityFrom + damageEntity. Returns (event_fired, applied)."""
    if ent.dead: return (False, 0.0)
    if ent.hurt_res > 10:
        if amount <= ent.last_dmg: return (False, 0.0)
        amt = amount - ent.last_dmg
        ent.last_dmg = amount
    else:
        ent.last_dmg = amount
        ent.hurt_res = 20
        amt = amount
    return (True, amt)

def finish_damage(ent, amt, bypass_armor=False):
    """post-LivingHurtEvent part of damageEntity."""
    if amt <= 0: return 0.0
    if isinstance(ent, Target):
        if ent.defense: amt = max(0.0, amt - ent.defense)      # Lycanites getDamageAfterDefense (approx)
        if ent.cap: amt = min(amt, ent.cap)                    # damageMax / TragicMC bossDamageCap
        if not bypass_armor: amt = amt * (25 - ent.armor) / 25.0
    else:
        if not bypass_armor:
            amt *= (25 - ent.armor) / 25.0
            if ent.prot: amt *= (25 - min(20, 4 * ent.prot)) / 25.0   # Prot IV set ~ x0.2 cap
        if ent.resist: amt *= 0.8
    a = min(ent.absorb, amt); ent.absorb -= a; amt -= a
    ent.hp -= amt
    if ent.hp <= 0:
        if getattr(ent, "immortal", False): ent.hp = 1.0
        else: ent.dead = True
    return amt

# ---------------------------------------------------------------- dispatch ---
class Sim:
    def __init__(self, player, target, enchants, order="applied", swing=10, crowd=0,
                 bleed_redispatch=True, target_hits_every=40, sneaking=True):
        self.p = player; self.t = target
        self.ench = list(enchants)          # [(name, lvl)] in NBT order
        self.swing = swing; self.crowd = crowd
        self.bleed_redispatch = bleed_redispatch
        self.target_hits_every = target_hits_every
        self.sneaking = sneaking
        self.tick = 0
        self.stats = Counter()
        self.crowd_hp = [target.max_hp * 0.1] * crowd   # bystanders (small)
        self.crowd_iframe = [0] * crowd
        self.first_hit_done = False

    def has(self, n): return any(e == n for e, _ in self.ench)
    def ms(self): return self.has("multistrike")

    def strength_mult(self):
        return 2.3 if self.p.strength_ticks > 0 else 1.0

    def dispatch_attack(self, dmg, victim, depth=0):
        """EnchantDispatcher.dispatch(ATTACK). Returns final damage."""
        p = self.p
        multi = self.ms()
        order = sorted(self.ench, key=lambda e: PHASE.get(e[0], 2)) if TUNED else self.ench
        nm = TUNED_NOT_MULTIPLIABLE if TUNED else NOT_MULTIPLIABLE
        for name, lvl in order:
            if name == "multistrike": continue
            passes = 2 if (multi and name not in nm) else 1
            for ps in range(passes):
                c = proc(name, lvl)
                if c < 100 and rng.randrange(100) >= c: continue
                self.stats["proc:" + name] += 1
                dmg = self.effect(name, lvl, dmg, victim, ps, depth)
                if victim.dead: break
        return dmg

    def effect(self, name, lvl, dmg, v, ps, depth):
        p = self.p
        if name == "executioner":
            miss = 1 - v.hp / v.max_hp; return dmg * (1 + 0.25 * lvl * miss)
        if name == "berserk":
            miss = 1 - p.hp / p.max_hp; return dmg * (1 + 0.30 * lvl * miss)
        if name == "colossus":
            bonus = v.max_hp * 0.025 * lvl
            if TUNED: bonus = min(bonus, max(20.0, dmg * 4.0))
            return dmg + bonus
        if name == "roulette":
            return dmg * (2.0 if rng.random() < 0.5 else 0.5)
        if name == "assassinate":
            if not v.targeting: return dmg * (1 + 0.25 * lvl)
            return dmg
        if name == "excalibur":
            return dmg + 4.0
        if name == "momentum":
            if ps > 0 and not TUNED: stacks = 8
            else:
                if p.streak_target is not v or (self.tick - p.streak_tick) > 40: p.streak = 0
                p.streak_target = v; p.streak += 1; p.streak_tick = self.tick; stacks = p.streak
            return dmg + 0.5 * lvl * (min(stacks, 8) - 1)
        if name == "riposte":
            return dmg + 1.5 * lvl if (self.tick - p.last_hurt_tick) <= 60 else dmg
        if name == "killingblow":
            if rng.randrange(1000) < lvl:
                v.hp = 0; v.dead = True; self.stats["killingblow_kills"] += 1
                return max(dmg, 1.0)
            return dmg
        if name == "cultist":
            self_dmg = dmg * 0.75
            if TUNED: self_dmg = min(self_dmg, p.max_hp * 0.10 * lvl, max(0.0, p.hp - 1.0))
            fired, amt = vanilla_attack(p, self_dmg, self.tick)
            if fired:
                before = p.hp
                if TUNED:
                    # physical, not magic: armour and protection apply in full
                    amt = finish_damage(p, amt)
                else:
                    if p.resist: amt *= 0.8
                    p.hp -= amt
                    if p.hp <= 0:
                        if p.immortal: p.hp = 1.0
                        else: p.dead = True
                p.last_hurt_tick = self.tick
                self.stats["cultist_self_dmg"] += amt
                if before - amt <= 0:
                    self.stats["cultist_deaths"] += 1
                    if not p.immortal: self.stats["player_deaths"] += 1
            return dmg * 2.0
        if name == "crushingblow":
            if not self.sneaking: return dmg
            if p.cooldowns.get("cb", -10**9) > self.tick: return dmg
            p.cooldowns["cb"] = self.tick + 200
            return dmg * (1 + 0.6 * lvl)
        if name == "rage":
            p.strength_ticks = max(p.strength_ticks, 40 + 40 * lvl); return dmg
        if name == "rupture":
            per = max(0.5, dmg * 0.04) if TUNED else 0.5
            if v.bleed: v.bleed[0] = min(lvl + 1, v.bleed[0] + 1); v.bleed[1] = max(v.bleed[1], 80 + 20 * lvl); v.bleed[3] = max(v.bleed[3], per)
            else: v.bleed = [1, 80 + 20 * lvl, 20, per]
            return dmg
        if name == "poisonous":
            if not v.undead:
                self.add_potion(v, "poison", 60 + 20 * lvl, 0)
                if TUNED: self.add_venom(v, max(0.8, dmg * 0.04 * lvl), 60 + 20 * lvl)
            return dmg
        if name == "venomous":
            if not v.undead:
                self.add_potion(v, "poison", 100 + 40 * lvl, 1)
                if TUNED: self.add_venom(v, max(0.8, dmg * 0.058 * lvl), 100 + 40 * lvl)
            self.add_cripple(v, 0.10, 80); return dmg
        if name == "sunder":
            self.add_cripple(v, 0.05 * lvl, 60 + 20 * lvl); return dmg
        if name == "cripple":
            self.add_cripple(v, 0.05 * (lvl + 1), 80 + 40 * lvl); return dmg
        if name == "accelerant":
            cap = 2 * lvl + 1
            for pid, eff in list(v.potions.items()):
                amp = min(cap, eff[1] + lvl)
                if amp <= eff[1] and eff[1] >= cap: amp = eff[1]
                v.potions[pid] = [eff[0] + 40 * lvl, amp]
            return dmg
        if name == "arc":
            if depth > 50: return dmg
            chained = dmg * 0.35; hits = 0
            for i in range(self.crowd):
                if hits >= lvl: break
                if self.crowd_iframe[i] > 10: continue       # i-frames block re-entry
                hits += 1; self.crowd_iframe[i] = 20
                self.stats["arc_chain_hits"] += 1
                # chained hit re-dispatches ATTACK on the bystander (bridge has no reentrancy guard)
                if not TUNED: self.dispatch_attack(chained, DummyVictim(self.crowd_hp[i]), depth + 1)
            return dmg
        if name in ("necromancer", "bastion", "alpha"):
            self.stats["summons"] += 1; return dmg
        if name == "frostbite":
            return dmg
        return dmg

    def add_potion(self, v, pid, dur, amp):
        cur = v.potions.get(pid)
        if cur is None or amp > cur[1] or (amp == cur[1] and dur > cur[0]): v.potions[pid] = [dur, amp]

    def add_venom(self, v, per_second, dur):
        """Rate per second; the per-tick slice is derived from the live cadence."""
        cur = getattr(v, "venom", None)
        if cur: v.venom = [max(cur[0], per_second), max(cur[1], dur)]
        else: v.venom = [per_second, dur]

    def add_cripple(self, v, red, dur):
        if v.cripple: v.cripple = [max(v.cripple[0], red), max(v.cripple[1], dur)]
        else: v.cripple = [red, dur]

    # ------------------------------------------------------------ swing ------
    def player_swing(self):
        p, t = self.p, self.t
        base = p.weapon * self.strength_mult()
        fired, amt = vanilla_attack(t, base, self.tick)
        self.stats["swings"] += 1
        if not fired: self.stats["swings_blocked_iframe"] += 1; return
        self.stats["hits"] += 1
        amt = self.dispatch_attack(amt, t)
        if t.dead and t.hp <= 0 and self.stats.get("killingblow_kills"):
            pass
        done = finish_damage(t, amt)
        self.stats["dmg_dealt"] += done
        t.targeting = True
        if t.dead: self.on_kill()

    def on_kill(self):
        for name, lvl in self.ench:
            if name == "feast": self.p.hp = min(self.p.max_hp, self.p.hp + 2 * lvl)
            if name == "lich": self.p.absorb = max(self.p.absorb, 4 * lvl)

    def target_attack(self):
        p, t = self.p, self.t
        dmg = t.atk
        if t.cripple: dmg *= max(0.0, 1 - t.cripple[0])
        fired, amt = vanilla_attack(p, dmg, self.tick)
        if not fired: return
        p.last_hurt_tick = self.tick
        done = finish_damage(p, amt)
        self.stats["dmg_taken"] += done
        if p.dead: self.stats["player_deaths"] += 1

    def bleed_tick(self):
        t = self.t
        b = t.bleed
        if not b: return
        b[1] -= 1; b[2] -= 1
        if b[2] <= 0:
            b[2] = 20
            if TUNED:
                # hurtThroughInvulnerability: the timer is zeroed for the call and
                # restored, so the tick always lands and the next swing is untouched
                self.stats["bleed_ticks_landed"] += 1
                done = finish_damage(t, b[3] * b[0], bypass_armor=True)
                self.stats["dmg_dealt"] += done; self.stats["bleed_dmg"] += done
                if t.dead: self.on_kill()
            else:
                fired, amt = vanilla_attack(t, b[3] * b[0], self.tick)
                if fired:
                    self.stats["bleed_ticks_landed"] += 1
                    if self.bleed_redispatch:
                        self.stats["bleed_redispatches"] += 1
                        amt = self.dispatch_attack(amt, t)
                    done = finish_damage(t, amt, bypass_armor=True)
                    self.stats["dmg_dealt"] += done; self.stats["bleed_dmg"] += done
                    if t.dead: self.on_kill()
                else:
                    self.stats["bleed_ticks_iframed"] += 1
        if b[1] <= 0: t.bleed = None

    def potion_tick(self):
        t = self.t
        for pid in list(t.potions):
            dur, amp = t.potions[pid]
            if pid == "poison":
                k = 25 >> amp
                if k <= 0: k = 1
                if dur % k == 0:
                    venom = getattr(t, "venom", None)
                    if TUNED and venom and venom[1] > 0:
                        # our own tick: lands whatever the wielder is doing, and
                        # unlike vanilla poison it is allowed to finish the target
                        d = finish_damage(t, venom[0] * k / 20.0, bypass_armor=True)
                        self.stats["poison_dmg"] += d
                        self.stats["dmg_dealt"] += d
                        self.stats["venom_ticks_landed"] += 1
                        if t.dead: self.on_kill()
                    if t.hp > 1.0 and not t.dead:
                        fired, amt = vanilla_attack(t, 1.0, self.tick)
                        if fired:
                            d = finish_damage(t, amt, bypass_armor=True)
                            if t.hp < 1.0: t.hp = 1.0; t.dead = False
                            self.stats["poison_dmg"] += d
                            self.stats["dmg_dealt"] += d
                        else:
                            self.stats["poison_ticks_iframed"] += 1
            if pid == "wither":
                k = 40 >> amp
                if k <= 0 or dur % k == 0:
                    fired, amt = vanilla_attack(t, 1.0, self.tick)
                    if fired:
                        d = finish_damage(t, amt, bypass_armor=True)
                        self.stats["wither_dmg"] += d; self.stats["dmg_dealt"] += d
                        if t.dead: self.on_kill()
            if pid == "poison":
                venom = getattr(t, "venom", None)
                if venom: venom[1] -= 1
            dur -= 1
            if dur <= 0: del t.potions[pid]
            else: t.potions[pid][0] = dur

    def run(self, max_ticks=20 * 1200, player_stops_at=None):
        p, t = self.p, self.t
        while self.tick < max_ticks and not t.dead and not p.dead:
            self.tick += 1
            if t.hurt_res > 0: t.hurt_res -= 1
            if p.hurt_res > 0: p.hurt_res -= 1
            for i in range(self.crowd):
                if self.crowd_iframe[i] > 0: self.crowd_iframe[i] -= 1
            if p.strength_ticks > 0 and p.strength_ticks < 10**8: p.strength_ticks -= 1
            if t.cripple:
                t.cripple[1] -= 1
                if t.cripple[1] <= 0: t.cripple = None
            attacking = player_stops_at is None or self.tick < player_stops_at
            if attacking and self.tick % self.swing == 0: self.player_swing()
            if t.dead: break
            if self.target_hits_every and self.tick % self.target_hits_every == 0: self.target_attack()
            self.bleed_tick()
            self.potion_tick()
        self.stats["ticks"] = self.tick
        self.stats["killed"] = 1 if t.dead else 0
        return self.stats

class DummyVictim:
    """A bystander for Arc chains: only needs the fields effects read."""
    def __init__(self, hp):
        self.hp = hp; self.max_hp = hp; self.dead = False; self.undead = False
        self.potions = {}; self.bleed = None; self.venom = None
        self.cripple = None; self.targeting = True

# --------------------------------------------------------------- scenarios ---
def run_many(n, make_sim):
    agg = defaultdict(list)
    for _ in range(n):
        s = make_sim(); st = s.run()
        for k, v in st.items(): agg[k].append(v)
    out = {}
    for k, v in agg.items():
        out[k] = statistics.mean(v)
    out["ttk_s"] = statistics.mean([x / 20.0 for x in agg["ticks"]])
    out["ttk_med_s"] = statistics.median([x / 20.0 for x in agg["ticks"]])
    out["kill_rate"] = statistics.mean(agg["killed"])
    out["dps"] = statistics.mean([d / max(1, x) * 20.0 for d, x in zip(agg["dmg_dealt"], agg["ticks"])])
    return out

def baseline_ttk(target_spec, weapon, n=200, **kw):
    return run_many(n, lambda: Sim(Player(weapon, immortal=True), Target(target_spec), [], **kw))

def report_section(title):
    print("\n" + "=" * 100); print(title); print("=" * 100)

# =============================================================================
if __name__ == "__main__":
    N = 300
    results = {}

    # ---- 1. Single-enchant value: TTK reduction vs baseline, per target ----
    report_section("1. SINGLE ENCHANT (level 3, or max) -- time-to-kill in seconds, 2 swings/s, diamond sword (8) and Ultimate (37); wielder immortal, hit by the target every 2 s")
    singles = [("executioner",3),("berserk",3),("colossus",3),("roulette",1),("momentum",3),("riposte",3),
               ("assassinate",3),("excalibur",1),("killingblow",3),("cultist",3),("rupture",3),("rage",3),
               ("crushingblow",3),("venomous",3),("poisonous",3),("feast",3)]
    for wname in ["Diamond sword", "OreSpawn Ultimate"]:
        W = WEAPONS[wname]
        print(f"\n--- weapon: {wname} (attack {W}) ---")
        hdr = f"{'target':<20}{'typ.HP':>8}{'base':>8}" + "".join(f"{n[:9]:>11}" for n,_ in singles)
        print(hdr)
        for tname, spec in TARGETS.items():
            base = baseline_ttk(spec, W, n=40)
            typ = spec["hp"] * (1 + sum(spec["mp"]) / 2)
            row = f"{tname:<20}{typ:>8.0f}{base['ttk_s']:>8.1f}"
            for ename, lvl in singles:
                strength = ename == "excalibur"
                r = run_many(40, lambda: Sim(Player(W, strength=strength, immortal=True), Target(spec), [(ename, lvl)]))
                cell = "inf" if r["kill_rate"] < 0.5 else f"{r['ttk_s']:.1f}"
                if 0.5 <= r["kill_rate"] < 1: cell += "*"
                if ename == "cultist" and r.get("cultist_deaths", 0) > 0: cell = f"{cell}†{r['cultist_deaths']:.1f}"
                row += f"{cell:>11}"
            print(row)
            results.setdefault("singles", {}).setdefault(wname, {})[tname] = base["ttk_s"]
    print("  inf = not killed within 20 minutes in most runs; * = some runs timed out;  †N = times a 20-HP wielder would have died to Cultist during the kill")

    # ---- 2. Cultist lethality by weapon ----
    report_section("2. CULTIST -- chance the wielder dies to their own weapon (20 HP, diamond armor + Prot IV, vs Zombie)")
    for wname, W in WEAPONS.items():
        for ms in (False, True):
            ench = [("cultist", 3)] + ([("multistrike", 1)] if ms else [])
            r = run_many(200, lambda: Sim(Player(W, prot=4), Target(TARGETS["Zombie"]), ench))
            print(f"  {wname:<18} attack {W:>4}  MS={'Y' if ms else 'N'}   wielder died in {r.get('player_deaths',0)*100:5.1f}% of fights   "
                  f"avg self-damage per fight {r.get('cultist_self_dmg',0):6.1f}")

    # ---- 3. Stacking / kitchen-sink sword, order dependence ----
    report_section("3. STACKED WEAPON -- every always-on damage enchant, effect of NBT order and Multi Strike (vs Mobzilla, Ultimate 37)")
    flat = [("momentum",3),("riposte",3),("excalibur",1)]
    mult = [("executioner",3),("berserk",3),("assassinate",3),("roulette",1),("crushingblow",3)]
    procs = [("colossus",3),("killingblow",3),("rupture",3),("rage",3),("arc",3),("cultist",3)]
    combos = {
        "flat-first (M,R,E then multipliers)": flat + mult,
        "mult-first (multipliers then M,R,E)": mult + flat,
        "flat-first + Multi Strike": flat + mult + [("multistrike",1)],
        "all 14 (no MS)": flat + mult + procs,
        "all 14 + Multi Strike": flat + mult + procs + [("multistrike",1)],
        "all 14 + MS, wielder at 10% HP (Berserk)": flat + mult + procs + [("multistrike",1)],
    }
    spec = TARGETS["OreSpawn Mobzilla"]
    base = baseline_ttk(spec, 37, n=100)
    print(f"  baseline Ultimate vs Mobzilla: TTK {base['ttk_s']:.1f}s  DPS {base['dps']:.1f}")
    for label, ench in combos.items():
        def mk(ench=ench, label=label):
            pl = Player(37, strength=True, hp=20.0, immortal=True)
            if "10% HP" in label: pl.hp = 2.0
            return Sim(pl, Target(spec), ench, target_hits_every=0 if "10%" in label else 40)
        r = run_many(100, mk)
        print(f"  {label:<44} TTK {r['ttk_s']:7.1f}s  DPS {r['dps']:8.1f}   procs/hit: colossus {r.get('proc:colossus',0)/max(1,r['hits']):.2f} "
              f"KB kills {r.get('killingblow_kills',0)*100:.0f}%  cultist-deaths/fight {r.get('cultist_deaths',0):.1f}")
        results.setdefault("stacked", {})[label] = r["ttk_s"]

    # ---- 4. Rupture re-dispatch: hands-free proc engine ----
    report_section("4. RUPTURE BLEED RE-DISPATCH -- player hits for 5 s then walks away; what the bleed keeps doing (vs Mobzilla)")
    for label, ench in {
        "Rupture III alone": [("rupture",3)],
        "Rupture III + Colossus III": [("rupture",3),("colossus",3)],
        "Rupture III + Colossus III + Multi Strike": [("rupture",3),("colossus",3),("multistrike",1)],
        "Rupture III + Killing Blow III": [("rupture",3),("killingblow",3)],
        "Rupture III + Necromancer III": [("rupture",3),("necromancer",3)],
    }.items():
        for redis in (True, False):
            def mk(ench=ench, redis=redis):
                return Sim(Player(37), Target(spec), ench, bleed_redispatch=redis, target_hits_every=0)
            agg = defaultdict(list)
            for _ in range(100):
                s = mk(); st = s.run(max_ticks=20*600, player_stops_at=100)
                for k, v in st.items(): agg[k].append(v)
            dead = statistics.mean(agg["killed"]); tt = statistics.mean([x/20 for x in agg["ticks"]])
            print(f"  {label:<44} redispatch={'as coded' if redis else 'guarded '}  bleed ticks landed {statistics.mean(agg['bleed_ticks_landed']):6.1f}  "
                  f"bleed dmg {statistics.mean(agg['bleed_dmg']):8.1f}  colossus procs {statistics.mean(agg.get('proc:colossus',[0])):6.1f}  "
                  f"summons {statistics.mean(agg.get('summons',[0])):5.1f}  killed {dead*100:3.0f}% (t={tt:.0f}s)")

    # ---- 5. Arc in a crowd ----
    report_section("5. ARC IN A CROWD -- chained hits per swing and extra full proc rolls they generate (Arc III, crowd of 12)")
    for label, ench in {"Arc III": [("arc",3)], "Arc III + Multi Strike": [("arc",3),("multistrike",1)],
                        "Arc III + Colossus III + Killing Blow III + MS": [("arc",3),("colossus",3),("killingblow",3),("multistrike",1)]}.items():
        r = run_many(100, lambda ench=ench: Sim(Player(37), Target(TARGETS["Zombie"]), ench, crowd=12))
        print(f"  {label:<48} chain hits per swing {r.get('arc_chain_hits',0)/max(1,r['swings']):.2f}   "
              f"colossus procs per swing {r.get('proc:colossus',0)/max(1,r['swings']):.2f}   KB rolls/swing {r.get('proc:killingblow',0)/max(1,r['swings']):.2f}")

    # ---- 6. Killing Blow: expected time on capped bosses ----
    report_section("6. KILLING BLOW vs damage-capped / huge bosses -- expected hits and seconds at 2 hits/s")
    for lvl in (1,2,3):
        for ms in (False, True):
            rolls = 2 if ms else 1
            p_hit = 1 - (1 - lvl/1000) ** rolls
            print(f"  KB {lvl} MS={'Y' if ms else 'N'}: {p_hit*100:.2f}% per hit -> expected {1/p_hit:.0f} hits = {1/p_hit/2:.0f}s ; with Rupture idle bleed adding 1 roll/s -> {1/p_hit/3:.0f}s")
    for tname in ("Lycanites Rahovart", "OreSpawn The King", "TragicMC boss(1k)"):
        t = Target(TARGETS[tname], mp_roll=sum(TARGETS[tname]["mp"])/2)
        per_hit = min(t.cap or 1e9, 37 * (25 - t.armor) / 25 - t.defense)
        print(f"  {tname:<20} typical HP {t.max_hp:8.0f}  best-case per-hit with Ultimate {per_hit:5.1f} -> {t.max_hp/per_hit/2:6.0f}s of perfect swinging; KB III ~ {1000/3/2:.0f}s")

    # ---- 7. Defense ----
    report_section("7. DEFENCE -- damage multiplier on an incoming melee hit (after vanilla diamond+Prot IV = x0.04 already applied)")
    def qf_def(turtle, tank, bulwark_missing, cockroach, ms, resist):
        m = 1.0
        dbl = ms and not TUNED             # tuned: Turtle/Bulwark/Stonehide no longer multipliable
        if turtle: m *= (0.67 ** (8 if dbl else 4))
        if tank: m *= (1 - 0.33) ** (1)     # Tank not multipliable
        if bulwark_missing is not None: m *= (1 - 0.30 * bulwark_missing) ** (2 if dbl else 1)
        if cockroach: m *= 0.2
        if resist: m *= 0.8
        return m
    rows = [("nothing", dict(turtle=0,tank=0,bulwark_missing=None,cockroach=0,ms=0,resist=0)),
            ("Tank III", dict(turtle=0,tank=1,bulwark_missing=None,cockroach=0,ms=0,resist=0)),
            ("Turtle x4 (not holding a weapon)", dict(turtle=1,tank=0,bulwark_missing=None,cockroach=0,ms=0,resist=0)),
            ("Turtle x4 + Tank III + Bulwark III @ half HP", dict(turtle=1,tank=1,bulwark_missing=0.5,cockroach=0,ms=0,resist=0)),
            ("...+ Excalibur Resistance I", dict(turtle=1,tank=1,bulwark_missing=0.5,cockroach=0,ms=0,resist=1)),
            ("...+ Cockroach III (<=1 heart)", dict(turtle=1,tank=1,bulwark_missing=0.9,cockroach=1,ms=0,resist=1)),
            ("Turtle x4 with Multi Strike on each piece", dict(turtle=1,tank=0,bulwark_missing=None,cockroach=0,ms=1,resist=0)),
            ("everything + Multi Strike on each piece", dict(turtle=1,tank=1,bulwark_missing=0.9,cockroach=1,ms=1,resist=1))]
    for label, kw in rows:
        m = qf_def(**kw)
        for hit in (20, 40, 100):
            pass
        print(f"  {label:<48} x{m:6.4f}  -> a 40-dmg King hit lands {40*0.04*m:6.3f} (diamond+ProtIV) or {40*m:6.2f} (naked); "
              f"20-HP player survives {20/(40*0.04*m) if m>0 else 0:6.0f} hits")

    # ---- 8. Mining yields ----
    report_section("8. MINING -- expected drops per ore block and per Excavate III swing (24-block vein), diamond ore = 8192 EMC")
    def yields():
        out = {}
        out["vanilla Fortune III"] = 2.2
        out["Fortune V"] = 1 + 2.0
        out["Fortune X"] = 1 + 4.5
        if TUNED:
            out["vanilla Fortune III + Bold"] = 2.2 * 2
            out["Fortune X + Bold (now mutually exclusive)"] = float("nan")
            out["Fortune X + Bountiful III (Bountiful now yields)"] = 5.5
            out["Fortune X + Transmuter III"] = 5.5 + 0.09
            return out
        out["Fortune X + Bold"] = 5.5 * 5.5
        out["Fortune X + Bold + Bountiful III"] = 5.5 * 5.5 * 1.33
        out["Fortune X + Bold + Bountiful III + Transmuter III"] = 5.5 * 5.5 * 1.33 + 0.09
        return out
    for k, v in yields().items():
        print(f"  {k:<48} {v:6.2f} per block   {v*24:8.1f} per Excavate III swing   {v*24*8192/1e6:6.2f}M EMC per swing on diamond")

    # ---- 9. Book economy ----
    report_section("9. BOOK ECONOMY -- per rarity, from the ranges in Rarity.java")
    R = {"Common":(75,90,0,5),"Uncommon":(65,80,5,12),"Rare":(50,70,12,22),"Epic":(35,55,22,35),"Legendary":(20,40,35,50)}
    POOL = {"Common":7,"Uncommon":15,"Rare":28,"Epic":22,"Legendary":9}
    for name,(s0,s1,d0,d1) in R.items():
        s = (s0+s1)/2/100; d = (d0+d1)/2/100
        p_destroy = (1-s)*d
        books_per_success = 1/s
        items_lost_per_success = p_destroy/s
        s_dust = min(0.95, s + 0.05*10)   # ten dust
        print(f"  {name:<10} success {s*100:4.0f}%  item destroyed per attempt {p_destroy*100:4.1f}%  books per success {books_per_success:4.1f}  "
              f"items shattered per success {items_lost_per_success:4.2f}  | with 10 dust: success {s_dust*100:3.0f}%, shattered/success {(1-s_dust)*d/s_dust:4.2f} "
              f"| pool {POOL[name]} enchants -> P(specific enchant per tome) {100/POOL[name]:4.1f}%  P(level 3) 11%")
    # expected tomes to land a *specific* enchant at its max level on one item, no consumables
    print("\n  Tomes of that rarity needed to land ONE specific enchant at max level on one item (uniform pick, level roll 1/3 per step, then the success roll):")
    for label, rar, maxl in [("Multi Strike", "Legendary", 1), ("Turtle (per armor piece)", "Legendary", 1), ("Excalibur", "Legendary", 1),
                             ("Affliction IV", "Legendary", 4), ("Fortune X", "Epic", 1), ("Colossus III", "Epic", 3), ("Killing Blow III", "Epic", 3),
                             ("Executioner III", "Rare", 3), ("Rupture III", "Rare", 3), ("Momentum III", "Uncommon", 3), ("Magnetize", "Common", 1)]:
        s0,s1,d0,d1 = R[rar]; s=(s0+s1)/2/100; d=(d0+d1)/2/100
        books_needed = POOL[rar] * (3 ** (maxl - 1))
        tomes = books_needed / s
        shattered = tomes * (1 - s) * d
        print(f"    {label:<26} {rar:<10} ~{tomes:5.0f} tomes, ~{shattered:4.1f} items shattered on the way")

    # ---- 10. Loot ----
    report_section("10. LOOT -- tome share of vanilla chest rolls (vanilla + Forge book weights only; other mods add more items, so these are upper bounds)")
    VAN = {"dungeon":(119+1, 8), "mineshaft":(79+1, 5), "stronghold corridor":(89+1, 3), "stronghold crossing":(61+1, 3),
           "stronghold library":(42+2, 3), "blacksmith":(90, 6), "desert pyramid":(72+1, 4.5), "jungle pyramid":(72+1, 4.5)}
    TOME_W = 27; CONS_W = 18; LEG_W = 1
    for chest,(w, rolls) in VAN.items():
        cons = CONS_W if chest in ("dungeon","mineshaft","stronghold corridor","blacksmith") else 0
        tot = w + TOME_W + cons
        print(f"  {chest:<20} tome per roll {TOME_W/tot*100:5.1f}%  tomes per chest {rolls*TOME_W/tot:4.2f}  Legendary tomes per chest {rolls*LEG_W/tot*100:4.1f}%  "
              f"consumables per chest {rolls*cons/tot:4.2f}")

    json.dump(results, open(sys.argv[1] if len(sys.argv) > 1 else "/dev/null", "w"), indent=1)
