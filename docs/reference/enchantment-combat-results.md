# Enchantment combat results (campaign v2, 2026-10-17)

What each combat enchantment is worth against the pack's own bosses, measured in the
running game. This is the definitive offensive and defensive record. It supersedes
the offensive figures in [`enchantment-tuning.md`](enchantment-tuning.md), which
describe what the code was written to do, and every number taken from the v1
singles campaign. v1 is invalid: see [Method](#1-method).

Nothing in this document changes the game. Section 6 holds **proposals only**. Each
one needs the author's yes or no before anyone touches code or configs.

Source data: `C:\qfs\campaign\` (48 jobs, driver log `driver-v2b.log`), jar
`1.1.0+20261017.0a2cec6b`. Analysis: `tools/balance/qfcampaign.py` plus the checks
described below. How the census works: [`../survey/combat.md`](../survey/combat.md).
What was fixed before this run, and why: [`../survey/census-anomalies-2026-10-17.md`](../survey/census-anomalies-2026-10-17.md).

**Contents.** [1. Method](#1-method) · [2. Per-enchant results](#2-per-enchant-results) ·
[3. Pairs](#3-pairs) · [4. Levels and wounded wielder](#4-level-scaling-and-the-wounded-wielder) ·
[5. Armour](#5-armour-enchants-damage-reduction-per-boss) · [6. Balance proposals](#6-what-it-means-for-balance-proposals-only) ·
[7. Caveats](#7-data-quality-caveats-and-what-still-looks-wrong) · [Appendix: full matrix](#appendix-speed-up-by-boss-every-enchant)

---

## Headlines

- **Excalibur (+43%) and Rage (+33%) are the two strongest weapon enchantments**,
  because both grant Strength I, which multiplies damage by 2.3 in 1.7.10. They do
  not stack with each other: the pair loses 43–57 points against independence.
  Against the three T4 bosses that cap each hit at 750, both are worth **0**.
- **The damage-over-time enchantments are now the best T4 enchantments.** Since fix
  7a, Rupture, Venomous and Poisonous kill Mobzilla, The King and The Queen 40–48%
  faster. That is more than anything else does there, and it comes from a Rare, a
  Rare and an Uncommon. v1 measured them at −1% to −171%.
- **Declared rarity still does not track power.** Momentum (Uncommon, +24%) beats
  every Epic except Rage, and Roulette (Uncommon, +21%) matches Colossus (Epic). Four of the five Legendaries
  do nothing in a boss fight.
- **Armour enchantments stop mattering at T3.** Ultimate and Royal armour already
  make the wielder immune to the melee of all 10 T3/T4 bosses. Tank (+29%) and
  Turtle (+32%) are the only armour enchantments worth having at T1–T2.
- **Rahovart takes 845 s with either the T3 or the T4 weapon.** Its 25-per-hit cap
  makes the weapon upgrade worthless there, and only post-cap additions help.
- **Three bosses' offensive columns are not usable**: Apis, Leonard and Lord of
  Torment (see §7). Death's wielder-health cells are invalid as well.

---

## 1. Method

**A cell** is one loadout (one enchantment at its top level, a pair, or a curated
stack) fighting one boss for 400 ticks per health band. The boss is pinned to the
median health and attack of 15 settled spawns, and swept through 100/75/50/25/10%
health. `ttk_est_s` integrates the five bands' damage per second into a full-fight
time to kill. The wielder swings every 10 ticks with the weapon and armour the quest
book has handed out by that boss (T1 diamond sword and armour; T2 The Titan with
fiery armour; T3 Ultimate sword and armour; T4 Royal Guardian sword and armour).
**Speed-up** = 1 − cell TTK / control TTK. +50% means the boss dies in half the time.
Every cell is paired with controls (the same weapon with no custom enchantment):
five per singles job, three per pairs, levels and wounded job.

**The noise band.** qfcampaign's band is two robust standard deviations of the
controls, with a 2% floor. This campaign adds a second, independent check, the
**placebo enchantments**: ten that have no mechanism against a boss in the census
(Tracker, Rally, Daze, Decapitate, Demon Forged, Soulbound, Timber, Trade, Jammer,
Get Off Me). Their spread is the instrument's real cell-to-cell noise. On six bosses
it is wider than the control band (Minoshroom ±2.7% → ±8.3%, Snow Queen, DeathReaper,
Polaris, Baba Yaga, Death). On three bosses the placebos are offset from zero, which
means the controls are biased (Apis +34%, Leonard +34%, Lord of Torment −14%).
**Every significance mark in this document uses max(control band, placebo 2 sd)**,
and those three bosses are left out of every mean. Thresholds per boss are in the
table below. A result is significant when it lies outside that band.

The band does not cover **proc luck**. Against a deterministic OreSpawn weapon the
controls repeat to the hundredth, so the band sits on its 2% floor. A proc
enchantment's own randomness is larger than that. The four deep bosses measured
every pair-set enchantment three times (in the singles, levels and pairs jobs), so
the spread between those runs gives proc luck directly. The median replicate sd is
2.4% on Naga, 6.0% on Lord of Torment, 0.1% on Mantis and 0.0% on Mobzilla. For the
coin-flip enchantments it is far wider: Roulette 13–14%, Rage 12.5% (Mantis) and
Colossus up to 20% (Lord of Torment). The pair analysis (§3) uses these replicate
spreads.

**Tick-warp validation.** All 48 jobs ran with `-Dqf.census.tickwarp=true`, which
runs ticks back to back. A job took 70–660 s instead of about 4,110 s, and the whole
campaign took 95 minutes (18:56–20:31). Every census window counts ticks, and an
audit of every boss found no wall-clock timers. Validation on T1 Naga compared the
normal-speed job with four warp runs: 1 of 41 cells fell outside 2 sd, and the median
cell TTK was identical. In v2 itself, the three independent runs of each
deep-boss enchantment agree to 0.1% on Mantis and Mobzilla.

**Fixes since v1** (jar `0a2cec6b`). Census fixes 1–6 change only the instrument.
Fixes 7a and 7b are user-approved gameplay changes.

| # | Fix | Effect on the data |
|---|---|---|
| 1 | A target removed while alive no longer counts as a kill | Lord of Torment's 50/25/10% bands read "cannot be measured" instead of instant kills |
| 2 | The probe has a closed connection | The EnderDemon no longer NPEs and gets deleted by Forge: control 1.3 s → 132 s |
| 3 | `CensusGuard` cancels the boss AI's hits on the probe (new `probe_hp_min` and `ai_hits_blocked` columns) | DeathReaper placebos +30% → +1%. Berserk at full health now reads about 0 instead of +19..+49% |
| 4 | Apis's reflection held down | Control noise ±92% → ±7%, but see §7: Apis is still not usable |
| 5 | Enyvil struck at `part=enyvilEye`, and `onSpawnWithEgg` called | Enyvil "never" → 21 s |
| 6 | Kitsune defence-only | Kitsune is immune to weapons by design (`kitsunakumaFireballExempt=true`) |
| 7a | DoT ticks get past OreSpawn's private `hurt_timer` | Rupture on Mobzilla −140% → +40%, The King −171% → +46%, The Queen −121% → +48% |
| 7b | A hit the target has zeroed keeps no on-hit enchantment | Flat adds no longer leak through Kitsune's immunity |

The reference opponents were re-sampled for v2, and their health differs from v1 by
up to 34% (Horned Huntsman 3,321 → 2,488). **Compare speed-ups, not TTKs, across
versions.**

**Partial bosses.**
- **Kitsune is defence-only.** It takes damage only from its own reflected
  fireballs, so no weapon enchantment can act on it.
- **Lord of Torment's TTK runs only to 50% health.** There it takes the fight to the
  Torment dimension and `setDead()`s. qfcampaign integrates bands 1–2 only
  (`PHASE_END`). Its pre-event 5-raw cap also lets flat adds dominate. On top of
  that, its controls are biased this run (placebos −14%), so it is shown but not
  averaged.
- **Mobzilla's 750/hit cap** sits before armour, and the Royal sword swings for 751.
  Anything that raises the raw hit (Strength from Excalibur and Rage, flat adds such
  as Momentum and Riposte) is discarded. Multipliers applied after the cap
  (Executioner, Cultist, Colossus, Berserk) and DoT still work. **The King and The
  Queen show the identical signature**: 120.0 damage after armour on every first
  swing whether the raw hit is 751 or 1,727, and Excalibur at exactly +0.5%. The
  census anomaly doc names only Mobzilla, but in this data all three are capped.
- **Rahovart's 25/hit cap** (Lycanites `damageMax`) is applied in its armour step.
  The T3 and T4 jobs produce identical TTKs (845.0 s): 42,249 HP ÷ 25 at two swings
  a second. Strength and pre-cap multipliers read 0. Only additions after the cap
  move it (Executioner +20%, Cultist +23%, Momentum +28%, Excalibur's +4 flat +14%).

### The bosses

| Tier | Boss | HP | Control TTK | Control band | Placebo median | **Threshold used** | Status |
|---|---|---:|---:|---:|---:|---:|---|
| T1 | Knight Phantom | 290 | 13.1 s | ±8.7% | +1.0% | ±8.7% | ok |
| T1 | Twilight Lich | 717 | 18.6 s | ±5.5% | +2.2% | ±8.6% | ok, shields held down |
| T1 | Minoshroom | 857 | 21.5 s | ±2.7% | +0.3% | ±8.3% | ok |
| T1 | Yeti | 1,284 | 34.3 s | ±5.9% | +3.8% | ±8.0% | ok |
| T1 | Naga | 1,338 | 34.0 s | ±7.5% | +0.1% | ±10.1% | ok (deep boss) |
| T1 | Tower Boss | 1,659 | 97.1 s | ±8.2% | −0.9% | ±8.2% | ok |
| T1 | Snow Queen | 1,665 | 42.6 s | ±2.4% | +3.8% | ±9.3% | ok |
| T2 | Kitsune | 383 | — | — | — | — | defence only |
| T2 | Polaris | 580 | 11.6 s | ±3.5% | +0.7% | ±8.9% | ok |
| T2 | Apis | 808 | 48.7 s | ±7.4% | **+33.7%** | ±47% | **excluded**, see §7 |
| T2 | DeathReaper | 1,134 | 14.8 s | ±4.1% | +0.7% | ±12.9% | ok |
| T2 | TimeController | 1,689 | 57.5 s | ±3.4% | −1.1% | ±5.5% | ok |
| T2 | Enyvil | 1,797 | 20.6 s | ±12.2% | +0.6% | ±12.2% | ok, eye only |
| T2 | Wither | 2,284 | 25.8 s | ±6.3% | +1.0% | ±8.1% | ok |
| T2 | Horned Huntsman | 2,488 | 40.0 s | ±12.4% | −0.2% | ±12.4% | ok |
| T2 | EnderDemon | 2,899 | 132.4 s | ±7.5% | +3.7% | ±7.5% | ok |
| T2 | Baba Yaga | 3,271 | 52.2 s | ±3.8% | −0.8% | ±9.1% | ok, 15/hit cap |
| T2 | Lord of Torment | 3,853 | 71.3 s (to 50%) | ±4.9% | **−13.9%** | ±17.5% | **shown, not averaged** |
| T2 | Leonard | 4,070 | 156.8 s | ±33.6% | **+33.9%** | ±33.6% | **excluded**, see §7 |
| T2 | Monking | 5,414 | 50.8 s | ±8.8% | −2.4% | ±8.8% | ok |
| T2 | Death | 6,321 | 85.5 s | ±2.2% | +2.9% | ±5.9% | ok, except wielder-health cells (§7) |
| T3 | Mantis | 598 | 12.2 s | ±2.0% | 0.0% | ±2.0% | ok (deep boss) |
| T3 | Mothra | 709 | 12.7 s | ±2.0% | 0.0% | ±2.0% | ok |
| T3 | Basilisk | 850 | 77.4 s | ±2.0% | 0.0% | ±2.0% | ok, 30-tick hurt gate |
| T3 | Emperor Scorpion | 1,558 | 283.8 s | ±2.0% | 0.0% | ±2.0% | ok, 30-tick hurt gate |
| T3 | Kraken | 3,913 | 237.5 s | ±2.0% | 0.0% | ±2.0% | ok, 30-tick hurt gate |
| T3/T4 | Rahovart | 42,249 | 845.0 s | ±2.0% | 0.0% | ±2.0% | 25/hit cap, shown apart |
| T4 | Godzilla (Legends) | 10,000 | 8.3 s | ±2.0% | 0.0% | ±2.0% | ok, uncapped |
| T4 | Mobzilla | 16,175 | 134.8 s | ±2.0% | 0.0% | ±2.0% | 750/hit cap (deep boss) |
| T4 | The Queen | 28,834 | 240.3 s | ±2.0% | 0.0% | ±2.0% | 750/hit cap |
| T4 | The King | 35,346 | 294.6 s | ±2.0% | 0.0% | ±2.0% | 750/hit cap |

The **trusted mean** used below covers 23 bosses: all seven T1 bosses, ten T2
bosses (not Kitsune, Apis, Leonard or Lord of Torment), five T3 bosses (not
Rahovart) and Godzilla. The capped bosses are reported in their own columns, not
averaged in, because the caps measure the boss rather than the enchantment.

---

## 2. Per-enchant results

Mean speed-up per tier group, top level, melee. The number in brackets is how many
of that group's bosses show a significant gain (and, with −, a significant loss).
**z** is the distance from the median of the enchantment's own declared rarity in
standard deviations, computed over the trusted mean. **Bold z ≥ 2** is a rarity
outlier. The full per-boss matrix is in the [appendix](#appendix-speed-up-by-boss-every-enchant).

| Enchant | Rarity | Lvl | T1 (7) | T2 (10) | T3 (5) | T4 capped (3) | Rahovart | Godzilla | **Trusted mean** | z | Sig. on |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| excalibur | Legendary | 1 | +55 (7) | +25 (9) | +58 (5) | +1 (0) | **+14** | **+55** | **+42.7** | **+2.5** | 22/23 |
| rage | Epic | 3 | +51 (7) | +16 (6) | +39 (5) | −0 (0) | +0 | **+51** | **+32.8** | **+2.6** | 19/23 |
| momentum | Uncommon | 3 | +37 (7) | +20 (10) | +18 (5) | +1 (0) | **+28** | +1 | **+24.0** | **+2.2** | 22/23 |
| rupture | Rare | 3 | +25 (7) | +19 (8, 1−) | +24 (5) | **+44 (3)** | +1 | **+8** | **+21.2** | **+2.3** | 21/23 |
| colossus | Epic | 3 | +26 (7) | +21 (9) | +17 (5) | +29 (3) | −2 | **+7** | +21.2 | +1.7 | 22/23 |
| roulette | Uncommon | 1 | +22 (7) | +19 (8) | +22 (5) | +16 (2) | +6 | **+18** | +20.5 | +1.8 | 21/23 |
| assassinate | Rare | 3 | +26 (5) | +10 (2) | +27 (5) | +2 (3) | +3 | **+43** | +19.8 | **+2.1** | 13/23 |
| executioner | Rare | 3 | +21 (7) | +18 (10) | +20 (5) | +20 (3) | **+20** | **+20** | +19.4 | **+2.1** | 23/23 |
| cultist | Rare | 3 | +19 (7) | +17 (10) | +17 (5) | +18 (3) | **+23** | **+16** | +17.4 | +1.9 | 23/23 |
| venomous | Rare | 3 | +20 (6) | +11 (4, 1−) | +27 (5) | **+46 (3)** | +2 | **+9** | +17.4 | +1.9 | 16/23 |
| poisonous | Uncommon | 3 | +16 (6) | +9 (4) | +19 (5) | **+41 (3)** | +2 | **+6** | +13.3 | +1.0 | 16/23 |
| blind | Rare | 3 | +15 (6) | +7 (3) | +10 (5) | +10 (3) | **+12** | **+12** | +10.6 | +1.1 | 15/23 |
| riposte | Uncommon | 3 | +13 (5) | +2 (1, 1−) | +9 (5) | +1 (0) | +0 | +0 | +6.8 | +0.3 | 11/23 |
| berserk | Epic | 3 | +4 (1) | +4 (1) | +0 | −0 | +0 | +0 | +2.8 | +0.2 | 2/23 |
| killingblow | Epic | 3 | +2 | +3 (1) | +3 (1) | −0 | +0 | +0 | +2.5 | +0.1 | 2/23 |
| getoffme | Epic | 3 | +4 (2) | +1 | +0 | −0 | +0 | +0 | +1.8 | +0.1 | 2/23 |
| jammer | Legendary | 3 | +3 (1) | +2 (1) | +0 | −0 | +0 | +0 | +1.8 | +0.1 | 2/23 |
| cripple | Rare | 3 | +1 | +2 | +0 | +0 | +0 | +0 | +1.1 | +0.0 | 0/23 |
| feast | Rare | 3 | +1 | +2 (1) | −0 | +0 | +0 | +0 | +1.0 | −0.0 | 1/23 |
| disarm | Uncommon | 3 | +4 | −0 (2−) | −0 | +0 | +0 | +0 | +0.9 | −0.3 | 0/23 |
| soulbound | Legendary | 1 | +5 (2) | −2 | −0 | −0 | +0 | +0 | +0.8 | +0.0 | 2/23 |
| crushingblow | Epic | 3 | +3 | −1 (1) | +0 | −0 | +0 | +0 | +0.8 | +0.0 | 1/23 |
| timber | Uncommon | 1 | +2 | +0 (1−) | +0 | +0 | +0 | +0 | +0.8 | −0.3 | 0/23 |
| rally | Common | 1 | +0 | +1 | +0 | +0 | +0 | +0 | +0.7 | +1.7 | 0/23 |
| necromancer | Rare | 3 | +2 | +0 | −0 | +0 | +0 | +0 | +0.6 | −0.0 | 0/23 |
| trade | Rare | 3 | +4 (1) | −2 (1, 1−) | −0 | +0 | +0 | +0 | +0.5 | −0.1 | 2/23 |
| daze | Uncommon | 3 | −1 | +1 (1) | −0 | +0 | +0 | +0 | +0.5 | −0.4 | 1/23 |
| accelerant | Rare | 3 | +2 (2) | −0 (1, 1−) | −0 | −0 | +0 | +0 | +0.3 | −0.1 | 3/23 |
| sunder | Uncommon | 3 | +2 (1) | −1 (1−) | +0 | −0 | +0 | +0 | +0.3 | −0.4 | 1/23 |
| reach | Epic | 3 | +3 (1) | −1 (1) | −0 | −0 | +0 | +0 | +0.3 | −0.0 | 2/23 |
| frostbite | Rare | 3 | +1 (1) | −0 (1−) | −0 | −0 | +0 | +0 | +0.3 | −0.1 | 1/23 |
| demonforged | Legendary | 1 | +1 | +0 | −0 | +0 | +0 | +0 | +0.3 | −0.0 | 0/23 |
| multistrike | Legendary | 1 | +3 (1) | −2 (1−) | −0 | −0 | +0 | +0 | +0.2 | −0.0 | 1/23 |
| lich | Epic | 3 | −1 (1, 1−) | +1 | −0 | −0 | +0 | +0 | +0.1 | −0.1 | 1/23 |
| mending | Epic | 1 | +2 | −1 (1−) | −0 | −0 | +0 | +0 | +0.1 | −0.1 | 0/23 |
| suplex | Rare | 3 | +1 | −1 (1, 2−) | +0 | +0 | +0 | +0 | −0.1 | −0.1 | 1/23 |
| decapitate | Common | 3 | +1 | −1 (1) | −0 | −0 | +0 | +0 | −0.1 | +0.0 | 1/23 |
| alpha | Rare | 3 | +2 | −2 | −0 | −0 | +0 | +0 | −0.3 | −0.2 | 0/23 |
| tracker | Common | 3 | −2 (1−) | +0 | −0 | +0 | +0 | +0 | −0.4 | −0.6 | 0/23 |
| arc | Epic | 3 | +4 (2) | −6 (2−) | +0 | −0 | +0 | +0 | −1.2 | −0.2 | 2/23 |
| bastion | Epic | 3 | +3 (2) | **−37 (6−)** | −3 (2−) | −3 (2−) | +0 | +0 | **−15.9** | −1.4 | 2/23 |

Rarity medians (trusted mean, all melee enchantments of that rarity): Common −0.1%
(n=3), Uncommon +3.9% (8), Rare +1.0% (14), Epic +0.8% (11), Legendary +0.8% (5).
Each tier is mostly utility enchantments that have no boss-fight effect, so the
medians sit near zero. A z above 2 therefore means "a real damage enchantment"
more than "an outlier within damage enchantments". The ranking itself is the more
useful reading.

**Rarity outliers (z ≥ 2):** Excalibur (Legendary, +2.5), Rage (Epic, +2.6),
Rupture (Rare, +2.3), Momentum (Uncommon, +2.2), Assassinate and Executioner (Rare,
+2.1). Cultist and Venomous (+1.9), Roulette (+1.8) and Colossus (+1.7) are close
behind. Against the declared ladder, Momentum (Uncommon) beats every Epic except
Rage, Rupture (Rare) ties Colossus (Epic), Roulette (Uncommon) and four more Rares
sit within 4 points of Colossus, and every Legendary except Excalibur measures
about zero.

What the per-tier columns show:
- **T1 is where everything works.** The diamond sword goes through KillerPacman's
  ×1–4 WeaponScaler, and no T1 boss caps hits.
- **T2 is flatter.** TragicMC's `bossDamageCap=25` (TragicMC.cfg) is the likely
  reason Strength enchantments are worth only +7–22% on DeathReaper, Enyvil,
  Polaris and TimeController, against +51–58% on the Wither and Monking. This was
  not traced. Baba Yaga caps at 15 per hit.
- **T3 is deterministic.** OreSpawn weapons skip WeaponScaler, so Excalibur is
  exactly ×2.3976 per hit (+58.3%) on every uncapped T3 boss.
- **T4 is cap-bound.** Against Mobzilla, The King and The Queen only post-cap
  multipliers and DoT register (see §6, P5). Godzilla (Legends) is uncapped and
  dies in 8.3 s to the Royal sword with no enchantment at all.
- **Bastion loses fights.** It costs 37% at T2 (Baba Yaga −120%, DeathReaper −93%,
  Horned Huntsman −77%, Monking −39%) because the iron golem's hits take the boss's
  i-frames from the player's much larger multiplied hits (anomaly doc §4b). This is
  real gameplay.
- **Multi Strike adds nothing measurable** to Excalibur (+1.4 points mean over the
  curated `excalibur + multistrike` stack). Excalibur is a passive and is not
  doubled. Most of Multi Strike's value would come from doubling Colossus or Rupture.

**Curated stacks** (trusted mean; T4 capped mean in brackets):
Momentum+Assassinate+Rage +53.6% (+4); Multi Strike+Colossus+Executioner +46.2% (+49);
Excalibur+Multi Strike +44.1% (+1); Cultist+Berserk+Riposte +33.1% (+22); Multi
Strike+Rupture+Accelerant +22.6% (+47); Arc+Rupture+Feast +20.2% (+42);
Venomous+Poisonous+Accelerant +16.8% (+51).

**Bow** (singles, bow controls; noise per boss is wide, ±2% to ±139%). Piercing is
the only bow enchantment that is consistently significant: +23% to +46% on 17 of 24
bosses (Apis excluded). Homing reads −100% ("never") on Basilisk, Emperor Scorpion, Mobzilla, the
Lich and Baba Yaga. Its arrows stop landing, which is worth a separate look. The
rest are within bow noise.

---

## 3. Pairs

All 91 pairs of the author's 14-enchantment set: Excalibur, Rage, Momentum,
Colossus, Executioner, Assassinate, Roulette, Cultist, Blind, Riposte, Berserk,
Poisonous, Rupture and Venomous. They were fought against one boss per damage model:
Naga (T1, linear), Lord of Torment (T2, 5-raw cap), Mantis (T3) and Mobzilla (T4,
750 cap).

**Synergy** = expected TTK under independence ÷ the pair's TTK, minus 1. The
expected TTK assumes multiplication (two "30% faster" enchantments together are 51%
faster, not 60%). Each single's ratio is the mean of its three replicate runs
(singles, levels and pairs job). The band is 2 sd from the replicate spreads of both
singles and the pair cell. A pair is **called** only when it is significant on at
least two bosses, all with the same sign. A single-boss result is listed as
"probable" only when a mechanism explains it. Lord of Torment's pairs control is
slow (77.6 s against 71.3 s in singles), which shifts all its synergies up by about
+10, so the call rule never rests on it alone.

### Synergies beyond independence

| Pair | Naga | Lord of Torment | Mantis | Mobzilla | Mechanism |
|---|---:|---:|---:|---:|---|
| **Colossus + Rupture** | **+41** (±17) | +15 (±48) | +7 (±8) | **+33** (±20) | Dispatch runs flat adds, then multipliers, then procs (`EnchantDispatcher`, `BY_PHASE`). A DoT's strength is a share of `ctx.damage`, so a Colossus-boosted hit seeds a bleed up to 5× bigger |
| **Colossus + Venomous** | **+46** (±17) | **+57** (±48) | +5 (±8) | −14 (±19) | The same seeding |
| Colossus + Poisonous | **+27** (±17) | +27 (±47) | +3 (±8) | −9 (±18) | The same seeding (probable: one boss) |
| Cultist + Poisonous / Venomous / Rupture | −9 / +12 / −5 | +1 / −18 / −3 | −4 / −1 / +12 | **+29 / +16** / +16 | Cultist's ×2 also runs before the DoT procs. Clear only on Mobzilla, where DoT is most of the damage (probable) |
| Roulette + Rupture | +3 | −13 | +13 | **+57** (±33) | The same seeding on a ×2 roll (probable: Mobzilla only) |
| **Assassinate + Blind** | +5 (±14) | **+92** (±23) | −2 (±3) | **+40** (±6) | Not traced. Assassinate pays only while the target is not targeting the wielder. Blindness apparently makes Witchery's and OreSpawn's AI lose its target. Naga and Mantis show nothing |
| **Blind + Colossus** | **+26** (±17) | **+108** (±47) | −0 (±8) | +3 (±18) | Not traced. Mantis (deterministic) shows nothing, so treat it as boss-specific |
| **Rage + Roulette** | **+22** (±13) | +18 (±23) | **+42** (±33) | +6 (±32) | Not traced. Both are proc-luck enchantments with wide replicate spreads. Weak |

### Anti-synergies

| Pair | Naga | Lord of Torment | Mantis | Mobzilla | Mechanism |
|---|---:|---:|---:|---:|---|
| **Excalibur + Rage** | **−57** (±13) | +2 (±23) | **−43** (±29) | +0 (±3) | Both grant Strength I, and potion effects do not stack. Rage adds nothing while Excalibur is held. Lord of Torment and Mobzilla cap away Strength anyway |
| **Excalibur + Momentum** | **−18** (±13) | −1 | **−13** (±3) | −0 | Momentum's flat add is not multiplied by Strength, so its share of a 2.3× hit shrinks. Additive, not multiplicative |
| Excalibur + Riposte | **−15** (±13) | +13 | **−6** (±3) | +0 | The same: a flat add diluted by Strength |
| Rage + Momentum / Riposte / Poisonous / Executioner | **−25 / −33 / −23 / −15** | +5 / +20 / +4 / +12 | +3 / −2 / +6 / −13 | 0 | The same dilution of flat adds under Rage's Strength. Naga only, so probable |
| **Poisonous + Venomous** | −13 (±13) | −17 (±27) | **−8** (±3) | **−41** (±11) | The same potion (Poison I and II). The stronger effect replaces the weaker, so the venom riders overlap |
| **Rupture + Venomous** | −12 | +13 | **−3** (±3) | **−29** (±19) | Two DoTs on one target. Overlap or a shared tick, not traced |
| Executioner / Riposte / Momentum / Berserk + Venomous or Poisonous on Mobzilla | | | | **−14 to −25** (±9–10) | Not explained: on Mobzilla, DoT gains do not add to other enchantments' gains. Mobzilla only |

Earlier docs claimed that **Momentum + Assassinate saturate (−57 points)**. That came
from v1. In v2 they are independent: +5, +10, 0 and +3.

---

## 4. Level scaling and the wounded wielder

### Levels I / II / III (speed-up %, * = beyond threshold)

| Enchant | Naga (±10) | Lord of Torment (±18) | Mantis (±2) | Mobzilla (±2) | Reading |
|---|---|---|---|---|---|
| executioner | +9 / +15* / +27* | −1 / −2 / +7 | +8* / +15* / +20* | +8* / +15* / +20* | Linear and deterministic: about +7 points per level |
| assassinate | +23* / +35* / +40* | −5 / −5 / −11 | +20* / +33* / +43* | +1 / +5* / +5* | Linear where the opener applies |
| momentum | +17* / +30* / +33* | +21* / +29* / +44* | +7* / +14* / +19* | +0 / +1 / +1 | Linear. Nothing past the 750 cap |
| rage | −7 / **+52\*** / +57* | −14 / +5 / −13 | +4* / **+48\*** / +42* | 0 / 0 / 0 | **A cliff: level I is worth about 0, level II nearly everything.** See §7 |
| colossus | −1 / **+35\*** / +35* | +28* / +9 / +6 | +1 / +7* / +10* | +5* / +6* / +22* | Proc-luck dominated. Replicates differ by up to 31 points |
| cultist | +8 / +15* / +18* | −1 / +12 / +21* | +2* / +11* / +23* | +1 / +13* / +16* | Roughly linear |
| riposte | +9 / +16* / +20* | +6 / +17 / +18* | +3* / +7* / +10* | 0 / 0 / +1 | Linear. Nothing past the 750 cap |
| blind | +7 / +14* / +14* | −2 / +10 / +9 | +8* / +11* / +12* | +4* / +8* / +12* | Flattens after II |
| rupture | +14* / +19* / +26* | −3 / +15 / −0 | +5* / +7* / +11* | **+17\* / +29\* / +47\*** | Steepest at T4 |
| venomous | +7 / +13* / +21* | +1 / +15 / +23* | +3* / +7* / +11* | **+17\* / +37\* / +52\*** | Steepest at T4 |
| poisonous | +6 / +11* / +19* | −1 / +11 / +13 | +2* / +5* / +8* | **+8\* / +29\* / +36\*** | Steepest at T4 |
| bastion | +0 / +3 / +10 | +3 | −10* / −7* / −12* | 0 | A loss at T3 |
| tank (armour) | 8 / 17 / 28% DR | 3 / 17 / 35% DR | immune | immune | Linear |
| cockroach (armour) | 0 / 7 / 26% DR | about 0 | immune | immune | Pays only at III |

The Berserk, Feast, Lich, Mending and utility rows are flat within noise at every
level. That is expected, since nothing in a full-health banded cell triggers them.

### The wounded wielder (Berserk and Cultist at 100/50/25% health)

Berserk is the one enchantment whose value depends on the wielder's own health. At
full health it correctly reads about 0 now that the probe's health is held. v1's
+19..+49% came from probe drift.

| Loadout | Health | Naga | Lord of Torment | Mantis | Mobzilla | Design (×1 + 0.9 × missing) |
|---|---:|---:|---:|---:|---:|---:|
| berserk III | 100% | +7 / +5 | −18 / −6 (biased) | +0 | −0 | 0% |
| berserk III | 50% | **+27** | **+29** | **+31** | **+31** | +31% |
| berserk III | 25% | **+41** | **+42** | **+40** | **+40** | +40% |
| cultist III | 100 / 50 / 25% | +12–18 / +8 / +23 | +21–28 / +15 / +18 | +15–23 / +19 / +22 | +15 / +12 / +14 | flat (proc ×2) |
| cultist + berserk + riposte | 100% | +41 / +49 | +39 / +21 | +29 / +25 | +21 / +14 | |
| cultist + berserk + riposte | 50% | **+62** | **+61** | **+52** | **+45** | |
| cultist + berserk + riposte | 25% | **+62** | **+69** | **+55** | **+48** | |

Berserk matches its design to within a point on all four bosses, Mobzilla included
(it is a post-cap multiplier). Cultist does not depend on the wielder's health. What
it costs does depend on armour (`probe_hp_min`, Cultist cells): **diamond (T1) —
the wielder is driven to the 1-HP floor within a Naga fight. Fiery (T2) — about
2 HP lost. Ultimate and Royal (T3/T4) — nothing at all.** See P7. The 25%-health
control on Lord of Torment is noisy (±28%).

---

## 5. Armour enchants: damage reduction per boss

Each boss's real melee, 60 hits per cell, against the tier's armour. Reduction is
against the same armour with no custom enchantment. **No T3 or T4 boss lands any
damage** on Ultimate or Royal armour (all 10, Rahovart and Godzilla included), and
neither do Tower Boss or EnderDemon (which have no melee). So every armour
enchantment is worth exactly 0 from T3 on. Enyvil (control ±32 dmg) and Death (its
hits ignore armour: 172 damage whatever the enchantment, Turtle included) are left
out of the means.

| Enchant | Rarity | Lvl | T1 mean (6) | T2 mean (11) | Mean (17) | Best | ≥5% on | Hits survived vs control |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| turtle | Legendary | 1 | **+62** | +15 | **+31.5** | +76 (Snow Queen) | 12/17 | +2.7 |
| tank | Rare | 3 | **+31** | **+29** | **+29.4** | +38 (Leonard) | 17/17 | +1.2 |
| cockroach | Epic | 3 | +23 | +4 | +10.3 | +40 (Snow Queen) | 9/17 | +0.8 |
| bulwark | Rare | 3 | +13 | +8 | +10.1 | +27 (DeathReaper) | 14/17 | +0.5 |
| affliction | Legendary | 4 | +3 | +3 | +3.1 | +19 | 4/17 | 0.0 |
| frostpath | Rare | 3 | +1 | +3 | +2.7 | +15 | 4/17 | +0.2 |
| sacrifice | Rare | 1 | +2 | +3 | +2.7 | +21 | 3/17 | +0.2 |
| cleansing | Rare | 3 | −0 | +1 | +0.9 | +22 (Kitsune) | 3/17 (2−) | −2.0 |
| camouflage | Rare | 3 | +2 | +0 | +0.6 | +6 | 2/17 | +0.1 |
| nightsight | Common | 1 | +1 | +0 | +0.5 | +7 | 1/17 | +0.1 |
| flippers | Uncommon | 3 | +1 | +0 | +0.5 | +21 | 1/17 | 0.0 |
| stonehide | Uncommon | 3 | +2 | −2 | −0.5 | +8 | 2/17 | 0.0 |
| polarize | Legendary | 3 | +1 | −1 | −0.5 | +3 | 0/17 | −0.1 |
| reflect | Epic | 3 | −1 | −1 | −0.7 | +5 | 0/17 | 0.0 |
| rebound | Common | 3 | +1 | −3 | −1.3 | +22 | 1/17 | −0.1 |
| frog | Rare | 3 | −1 | −2 | −1.5 | +3 | 0/17 | −0.2 |
| deft | Epic | 2 | −0 | −3 | −2.0 | +4 | 0/17 | −0.2 |
| regrowth | Rare | 3 | −3 | −9 | −7.0* | +1 | 0/17 | **+1.0** |
| vigor | Epic | 3 | −3 | −25 | −17.2* | +2 | 0/17 | **+1.2** |

\* **Not more damage taken.** `damage_taken` is health actually lost, and a lethal
hit counts only the health that was left. Vigor and Regrowth give the wielder more
health to lose, so the figure rises even though the wielder survives more hits. For
these two, read the hits-survived column.

Per boss (≥5% bold). Bosses that do not reach the wielder are omitted.

| Enchant | Knight Phantom | Minoshroom | Naga | Snow Queen | Lich | Yeti | Apis | DeathReaper | Kitsune | Polaris | TimeController | Wither | Monking | Baba Yaga | Huntsman | Leonard | Lord of Torment |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| control dmg / 60 hits | 232 | 286 | 120 | 134 | 100 | 22 | 29 | 61 | 12 | 10 | 174 | 10 | 66 | 8 | 42 | 42 | 42 |
| turtle | **+76** | **+75** | **+74** | **+76** | **+70** | +0 | **+5** | **+21** | −1 | +0 | **+73** | +0 | **+25** | +0 | **+13** | **+10** | **+17** |
| tank | **+30** | **+34** | **+28** | **+31** | **+29** | **+33** | **+14** | **+31** | **+32** | **+32** | **+15** | **+33** | **+24** | **+33** | **+32** | **+38** | **+30** |
| bulwark | **+17** | **+9** | **+8** | **+17** | **+13** | **+14** | +4 | **+27** | **+11** | **+6** | **+5** | **+7** | **+6** | **+5** | +1 | +4 | **+18** |
| cockroach | **+6** | **+30** | **+26** | **+40** | **+24** | **+10** | −1 | −2 | −1 | +0 | **+12** | +0 | +0 | +0 | **+14** | +1 | **+15** |
| affliction | +2 | +2 | +0 | **+7** | +0 | **+10** | −1 | **+19** | −0 | −1 | −3 | +0 | +0 | **+9** | +4 | +2 | +4 |
| frostpath | +2 | **+7** | +0 | +0 | +0 | +0 | −1 | **+15** | −1 | −0 | +1 | +0 | +0 | +0 | **+11** | +0 | **+11** |
| sacrifice | +3 | **+9** | +0 | +0 | +0 | +0 | −1 | **+21** | −1 | −1 | **+12** | +0 | +0 | +0 | +3 | +0 | −0 |
| cleansing | +2 | −2 | +0 | +0 | +0 | +0 | −1 | **+6** | **+22** | **+12** | **−17** | +0 | +0 | +0 | **−5** | −4 | +3 |
| flippers | +3 | +0 | +0 | +0 | +0 | +0 | −1 | **+21** | −1 | −1 | **−9** | +0 | +0 | +0 | −2 | −1 | −0 |
| rebound | +3 | +2 | +0 | +0 | +0 | +0 | −1 | **+22** | −0 | +1 | **−37** | +0 | +0 | +0 | **−9** | −3 | −1 |
| stonehide | +3 | **+7** | +0 | +0 | +0 | +0 | −1 | **−30** | −0 | +0 | **+8** | +0 | +0 | +0 | +1 | +2 | +0 |

DeathReaper and TimeController swing ±20–37 for enchantments with no plausible
effect (Flippers, Rebound, Stonehide). Their own melee is a noisy instrument.
Lord of Torment's armour cells also disagree between its singles and levels jobs
(Bulwark +18 vs +3, Cockroach +15 vs −2), so treat its column as ±15.

---

## 6. What it means for balance (proposals only)

None of these is applied. Each needs the author's explicit yes or no. The guiding
rule is the author's own: fix the outlier at its source, and never inflate the rest
of the ladder to match. Gear and weapon balance were waiting on this census, which
is now done.

### P1. Damage-over-time is seeded from the pre-armour hit. After fix 7a, that makes it the T4 meta. **Decision needed.**

*Evidence.* Fix 7a turned Rupture on Mobzilla from −140% into **+40%** (The King
+46%, The Queen +48%). Venomous gives +40–50% and Poisonous (an Uncommon) +40–42%
on the same three bosses. No other enchantment comes close there: the next best is
Colossus at +29%. On the gated T3 bosses DoT went from 0..−53% to +15..+56%.
Levels I→III on Mobzilla: Rupture +17/+29/+47, Venomous +17/+37/+52. The reason is
that `perStack = max(0.5, ctx.damage × 4%)` reads `ctx.damage` in `LivingHurtEvent`,
which is **after the boss's 750 cap but before armour**. Mobzilla's armour turns
the 750 hit into 120, so the melee lands 16% of its raw value, while the bleed lands
its full 4%-of-750 per stack per second through armour. Four stacks deal about
120/s, which roughly doubles the wielder's sustained damage.

*Suggestion.* Seed Rupture, Venomous and Poisonous from the damage that actually
lands after armour, rather than from the pre-armour hit. Old: `ctx.damage ×
4% / 5.8% / 4%` per level per second, from the pre-armour hit. New: the same
percentages of the hit's post-armour damage. Bypassing armour on each tick stays.

*Expected effect.* On Mobzilla, The King and The Queen the DoTs drop from +40–50%
to roughly +10–15% (the armour factor is 120/750). Against unarmoured T1–T2 bosses
there is little change. They would still be the only T4 option alongside the
post-cap multipliers. *Alternative (no code change):* keep the strength and price it
instead, by re-tiering Rupture and Venomous Rare → Epic and Poisonous Uncommon →
Rare (see P9).

### P2. DoTs inherit every damage multiplier that runs before them. **Decision needed.**

*Evidence.* `EnchantDispatcher` runs flat adds, then multipliers, then procs, so the
DoT procs read a `ctx.damage` that already includes Colossus, Cultist and Roulette.
Colossus+Rupture is +41 points beyond independence on Naga and +33 on Mobzilla.
Colossus+Venomous is +46 on Naga. Cultist+Poisonous and Roulette+Rupture are +29
and +57 on Mobzilla.

*Suggestion.* Seed DoTs from the hit before this mod's own multipliers (store
`ctx.baseDamage` before the FLAT phase). Old: seeded from the fully boosted hit.
New: seeded from the weapon's own hit.

*Expected effect.* Those synergies collapse to about independence (Colossus+Rupture
on Naga about +44% instead of +62%), and the single-enchant figures barely move.
Combined with P1, DoT becomes a steady +10–25% tool at every tier.

### P3. Excalibur: the strongest enchantment, worth nothing at T4. **Decision needed.**

*Evidence.* The trusted mean is **+42.7%**, significant on 22 of 23 bosses, 2.5 sd
above the Legendary median. It is +58.3% on every uncapped T3 boss, from the
multiplicative Strength I (×2.3). It is +0.5% on Mobzilla, The King and The Queen,
and +14% on Rahovart (its +4 flat lands after the 25 cap). It cancels Rage (−43 to
−57 points, P4). The tuning doc says it was "left deliberately enormous".

*Suggestion, option A (no change):* keep it as the pack's trophy weapon
enchantment. Excalibur is then strongest at T1–T3 and irrelevant at T4, which
matters for where it drops (P10). *Option B:* replace the permanent Strength I with
a ×1.5 multiplier in the multiplier phase. Old: permanent Strength I (×2.3), +4
flat, Resistance I and Speed I. New: ×1.5, +4 flat, Resistance I and Speed I.
Expected: about +33% on uncapped bosses instead of +58%. It would stack with Rage,
and it would still be 0 on the 750-capped bosses only if applied before the cap. As
a `LivingHurtEvent` multiplier it lands after the cap, so it would start working at
T4 (+33%).

### P4. Rage: Epic, +33%. Level I is worth about nothing, and it does not stack with Excalibur. **Investigate first.**

*Evidence.* Mean +32.8% (z +2.6). By level: Naga −7 / +52 / +57, Mantis +4 / +48 /
+42. Level I fires at its 5% rate (Mantis: 47 of 883 rolls), yet on the
deterministic Mantis its band damage stays exactly at control (49.2 dps) through
four of five bands. At about 33% expected uptime it should read roughly +30%. That
looks like a bug or a census interaction, not a balance fact (§7). It is 0 against
every capped boss.

*Suggestion.* Find out why Rage I does not show before retuning. If the cliff is
real, flatten it. Old: proc 5/10/15%, Strength I for 4/6/8 s. New: proc 10/12/15%,
Strength I for 4/6/8 s. Expected: level I about +25%, level III unchanged. Separately,
make the Excalibur clash visible: a tooltip line "does nothing while Excalibur is
held". That is not a balance change.

### P5. The 750/hit cap on Mobzilla, The King and The Queen. **Recommend no change, but confirm.**

*Evidence.* The Royal sword's 751 raw is already over the cap, so every T4 weapon
upgrade, Strength source or pre-cap flat add is wasted on those three bosses
(Excalibur, Rage, Momentum and Riposte all about 0). The enchantments that work are
Executioner +20, Colossus +20–34, Cultist +12–28, Roulette +0–28, Blind +8–12,
Berserk when wounded +31/+40, and DoT +40–50. Without enchantments the fights take
135 s, 240 s and 295 s.

*Suggestion.* Keep the caps. They make T4 a different puzzle rather than a bigger
number, which fits the pack vision of leaps in power without a fast plateau. Raising
them would mostly hand power back to Excalibur and Rage, the two existing outliers.
If the author wants weapon damage to keep mattering at T4, the lever would be a
qf-tweaks transformer on OreSpawn's cap (750 → 1,500). Expected effect: Excalibur
about +56% and Rage about +50% on all three bosses.

### P6. Rahovart: 845 s for any weapon. **Decision needed.**

*Evidence.* The 25/hit `damageMax` is hard-coded in the Lycanites class. The T3
Ultimate sword and the T4 Royal sword produce identical 845.0 s fights: 42,249 HP,
that is 1,690 hits. MobProperties (`config/MobProperties/demonmobs/rahovart.json`)
gives it a ×4–×10 max-health boost (`"3.0~9.0"`, operator 1) on top of Lycanites'
base health.

*Suggestion.* Shorten the fight at its source, the health boost, rather than the
cap. Old: `"value": "3.0~9.0"`. New: `"0.5~2.0"`. No code change is needed.

*Expected effect.* Median health about 42,000 → about 13,500, and TTK 845 s → about
270 s with no enchantment (about 215 s with Executioner). Upgrading the weapon still
does nothing there. That is acceptable for a boss that is meant to be ground down.

### P7. Cultist's price disappears at T3. **Decision needed.**

*Evidence.* Cultist is +17.4% at every tier, its highest on Rahovart (+23%). Its
self-damage is "ordinary physical damage — armor applies in full". `probe_hp_min`
shows the price falling with armour. Diamond: driven to the 1-HP floor within a Naga
fight. Fiery: about 2 HP. Ultimate and Royal: 0 HP, with the wielder staying at 20.0.

*Suggestion.* Make the price armour-independent. Old: 10% of max health per level,
as physical damage that armour reduces. New: a fixed 0.6 health per proc that
bypasses armour (Protection still applies), and still never below 1 health.

*Expected effect.* Over a 34 s Naga fight the T1 cost falls from about 19 HP to
about 11 HP. At T3/T4 it rises from 0 to the same 11 HP. The damage figure is
unchanged.

### P8. Bastion costs damage at T2. **Decision needed (design).**

*Evidence.* Trusted mean −15.9%, and −37% across T2: Baba Yaga −120%, DeathReaper
−93%, Horned Huntsman −77%, Monking −39%. Golem hits take the boss's i-frames from
the player's larger multiplied hits (anomaly doc §4b). This is real gameplay.

*Suggestion.* The options from the anomaly doc, in order of how much they change:
(a) golems ignore the wielder's current target while the wielder has hit it within
the last 20 ticks, so they fight adds; (b) give Bastion a tanking role (the golem
taunts) instead of damage; (c) keep it and document it as an add-clearing
enchantment. Expected effect of (a): Bastion becomes about 0% on bosses and keeps
its value against groups.

### P9. Re-tier by measured value: the input `progression-audit.md` §5 asked for. **Decision needed.**

`progression-audit.md` §5 built its placement from v1 claims that v2 does not
support: "Excalibur measures RARE", "Bulwark and Cockroach measure LEGENDARY",
"Berserk to Legendary" and "Momentum + Assassinate saturate". The measured bands
below come from the trusted mean, with the T4 picture noted, because §5 puts
Legendary drops behind T4 kills.

| Measured class | Enchantments (trusted mean; T4 capped) | Declared | Suggested |
|---|---|---|---|
| ≥ +30% | Excalibur (+43; +1), Rage (+33; 0) | Legendary, Epic | Excalibur stays **Legendary**. Rage **Epic → Legendary**, or P4 |
| +20 to +30% | Momentum (+24; +1), Rupture (+21; **+44**), Colossus (+21; +29), Roulette (+21; +16) | Uncommon, Rare, Epic, Uncommon | Momentum **Uncommon → Epic**. Rupture **Rare → Epic** (unless P1). Colossus stays Epic. Roulette **Uncommon → Rare** |
| +15 to +20% | Assassinate (+20; +2), Executioner (+19; +20), Cultist (+17; +18), Venomous (+17; **+46**) | all Rare | Stay **Rare**. Venomous → Epic unless P1. Cultist → Epic if P7 is declined (it is free at T3+) |
| +5 to +15% | Poisonous (+13; **+41**), Blind (+11; +10), Riposte (+7; +1) | Uncommon, Rare, Uncommon | Poisonous **Uncommon → Rare** unless P1. Blind stays Rare. Riposte stays Uncommon |
| Conditional | Berserk (0 at full health, **+31 at 50%, +40 at 25%**) | Epic | Stays **Epic**. v1's "Legendary" came from probe drift |
| about 0 against bosses | Killing Blow, Get Off Me, Jammer, Multi Strike, Soulbound, Demon Forged, Feast, Lich, Mending, Cripple, Sunder, Frostbite, Accelerant, Arc, Reach, Necromancer, Alpha, Trade, utility | various | Price these on utility or PvP value. The census cannot rank them |
| Negative | Bastion (−16; T2 −37) | Epic | See P8 |
| Armour ≥ +25% DR at T1–T2 | Turtle (+32; T1 +62), Tank (+29) | Legendary, Rare | Turtle stays Legendary. Tank **Rare → Epic** |
| Armour about +10% | Cockroach (+10; Epic), Bulwark (+10; Rare) | | Stay. **Not** Legendary, as §5 claimed |
| Armour about 0 | the other 15 armour enchantments | | Utility-priced |

### P10. Loot placement on the ladder (input to `progression-audit.md` §5)

The census shows where on the ladder each enchantment pays, and that should decide
which step's loot it comes from:

- **Armour enchantments only pay at T1–T2.** From T3 the tier armour is already
  immune to every boss's melee. §5's plan to hand out Legendary armour (Turtle)
  from T4 boss kills would deliver it where it is worth 0. Place armour enchantments
  in T1–T2 sources: Twilight chests, TF boss quests, TragicMC and Witchery boss
  drops.
- **Excalibur, Rage, Momentum, Riposte and Assassinate peak at T1–T3 and are dead
  against the T4 capped bosses.** As T4 rewards they only make the earlier tiers
  trivial in retrospect. Put Excalibur and Rage in T3 sources (OreSpawn mid-boss
  drops at a low chance), not behind Mobzilla, The King and The Queen. Momentum
  as an Uncommon drops from vanilla chests at T0–T1, making it the strongest
  early-game find by a wide margin. That is the strongest argument for P9's
  Momentum → Epic.
- **Executioner, Cultist and Colossus are flat across all tiers, T4 caps included.**
  They are the right "keeps growing" rewards for T4 kills.
- **The DoTs grow with tier** (T1 +16..+25, T2 +9..+19, T4 capped +41..+46). If P1 is
  declined they are the natural T4 rewards. If P1 is accepted they are mid-tier.
- **Spread rewards so one step does not hand out a pair that clashes**
  (Excalibur + Rage, Poisonous + Venomous). Momentum and Assassinate do not clash
  (§3).

### P11. Godzilla (Legends) dies in 8 s at T4. **Flag only.**

With 10,000 HP and no cap, the Royal sword lands about 600 per swing. If it is meant
as a T4 gate it is not one. Its placement on the ladder is a questline matter, not
an enchantment one.

---

## 7. Data-quality caveats, and what still looks wrong

1. **Apis is still invalid despite fix 4.** Every cell runs in one of two regimes:
   about 16 dps (the controls, and Cripple, Daze, Feast, Multi Strike and the rest)
   or about 30 dps (Timber, Tracker, Sunder and other placebos at +42–48%). The
   controls show 393–661 blocked AI hits and the fast cells 0–84, so a hidden boss
   state (aggression or stance) differs between control and treatment cells. A real
   Apis fight is about twice the vulnerable-phase TTK anyway. **Re-run needed** once
   that state is held.
2. **Leonard's TTK is set by its last 10% of health.** Bands 1–4 are steady at about
   60 dps. Band 5 swings between 3.6 and 25 dps, which gives ±34% control noise and
   +34% placebos. A report-side fix like Lord of Torment's (integrate bands 1–4)
   would rescue it. No re-run is needed for that.
3. **Lord of Torment's controls are biased low** in the singles job (placebos −14%)
   and its noise is ±18%. Its control TTK differs across jobs: 71.3, 73.3 and
   77.6 s. Flat adds pass its pre-event 5-raw cap (Momentum +34–44%), which is a
   design question first raised in the anomaly doc §1a.
4. **Death still drives the probe to 1 HP in every cell**, controls included
   (`probe_hp_min` 1.0, only 18–30 AI hits blocked). Its non-melee damage gets past
   `CensusGuard`. Berserk +30%, Cultist and Riposte on Death are therefore drift.
   Every other cell in the campaign held the probe's health.
5. **Proc luck is wider than the noise band** on deterministic bosses (§1). Roulette
   on Mobzilla read −1, +13 and +23 in three runs. Treat single cells of Roulette,
   Rage and Colossus on T3/T4 as ±15 points.
6. **Rage I reads about 0 although it fires at its 5% rate** (§6 P4). The Strength
   from a Rage I proc barely shows in band damage. That has not been explained.
7. **King and Queen are capped like Mobzilla.** This is not in the anomaly doc, but
   the first-swing logs show it (120.0 dealt for raw 751 or 1,727).
8. **The `qfcontent-census-combat.tsv` header says defensive cells take "a fixed
   8.0000 raw per hit"**, but the campaign ran with the boss's own melee
   (`options.incoming = 0`). The data is right and the header text is wrong.
9. **Vigor and Regrowth read as negative reduction** because `damage_taken` is capped
   by remaining health (§5). That is a reporting artefact, not a balance fact.
10. **Enyvil's defence controls vary ±32 damage**, so its Reflect +99% and Rebound
    +96% are unverified.
11. **Unexplained synergies:** Assassinate + Blind (Lord of Torment +92, Mobzilla
    +40), Blind + Colossus (Lord of Torment +108, Naga +26), and the negative
    synergy between DoT and every other enchantment on Mobzilla. The Colossus/DoT
    synergy is explained (P2).
12. **Homing arrows read "never"** on five bosses (bow section).
13. **TragicMC's `bossDamageCap=25`** probably flattens Strength on TragicMC bosses
    (§2). This was not traced.
14. **The report tool.** `qfcampaign.py` keys bosses by target and weapon, so
    passing the singles, levels and wounded TSVs together merges their controls and
    overwrites the full-health cells with wounded ones. Run it per phase, as this
    document does. Its outlier rule is 1.5 sd, while this document uses 2.0. Neither
    is changed here.
15. **v1 is invalid** and must not be mixed with v2: removed-alive kills, drift,
    Apis phase lottery, no Enyvil, the DoT gate, and a different reference opponent
    for every boss. Its numbers are kept in `C:\qfs\campaign\archive-v1-singles-20261017\`
    for comparison only.

**Re-run list** (none blocks the conclusions above): Apis (after holding its state),
Leonard (report fix only), Lord of Torment singles (controls), and Death's
wielder-health cells (after guarding its non-melee damage).

---

## Appendix: speed-up by boss, every enchant

Top level, melee, singles job. **Bold** = beyond that boss's threshold (header ±).
✗ = excluded (control bias; numbers not interpretable). ⚠ = shown, not averaged.
Rahovart appears under both T3 and T4 (identical: 25/hit cap).

#### T1

| Enchant | Knight Phantom ±9 | Minoshroom ±8 | Naga ±10 | Snow Queen ±9 | Tower Boss ±8 | Twilight Lich ±9 | Yeti Boss ±8 |
|---|---:|---:|---:|---:|---:|---:|---:|
| excalibur | **+59** | **+61** | **+58** | **+59** | **+63** | **+62** | **+25** |
| rage | **+37** | **+56** | **+55** | **+57** | **+50** | **+42** | **+58** |
| momentum | **+33** | **+33** | **+31** | **+33** | **+59** | **+34** | **+36** |
| rupture | **+36** | **+21** | **+19** | **+17** | **+27** | **+31** | **+22** |
| colossus | **+14** | **+18** | **+28** | **+39** | **+28** | **+26** | **+30** |
| roulette | **+27** | **+13** | **+20** | **+26** | **+19** | **+23** | **+26** |
| assassinate | **+42** | +3 | **+39** | +4 | **+39** | **+42** | **+9** |
| executioner | **+23** | **+13** | **+22** | **+28** | **+11** | **+24** | **+24** |
| cultist | **+13** | **+19** | **+12** | **+24** | **+17** | **+20** | **+24** |
| venomous | **+33** | **+18** | **+24** | **+20** | **+17** | +4 | **+26** |
| poisonous | **+25** | **+25** | **+12** | **+16** | **+14** | -2 | **+23** |
| blind | **+16** | **+11** | **+19** | **+12** | **+17** | +8 | **+22** |
| riposte | **+20** | **+18** | **+19** | +6 | -2 | **+9** | **+21** |
| berserk | +0 | **+9** | +7 | -2 | +5 | +1 | +4 |
| killingblow | +1 | +3 | +2 | +0 | -4 | +8 | +5 |
| getoffme | +1 | +1 | -1 | **+13** | +1 | **+10** | +3 |
| jammer | +2 | -1 | +9 | -3 | -2 | +3 | **+10** |
| cripple | +6 | -4 | -1 | -2 | -6 | +3 | +7 |
| feast | +3 | -7 | +1 | +0 | -1 | +5 | +4 |
| disarm | +0 | +6 | +4 | +4 | +1 | +4 | +6 |
| soulbound | +2 | +5 | +3 | +3 | +3 | **+9** | **+8** |
| crushingblow | +5 | +3 | +4 | -0 | -3 | +8 | +7 |
| timber | +2 | +3 | +7 | +9 | -6 | -2 | +1 |
| rally | -0 | +5 | -0 | -2 | -3 | +2 | +0 |
| necromancer | +1 | +3 | +5 | +5 | -7 | +0 | +5 |
| trade | +7 | -3 | +8 | +5 | +2 | +3 | **+9** |
| daze | -1 | -1 | -2 | +9 | -7 | -1 | +0 |
| accelerant | **+12** | -1 | -5 | -0 | -4 | **+10** | -0 |
| sunder | -5 | -5 | +2 | +5 | -1 | **+13** | +5 |
| reach | +2 | -2 | +4 | +2 | -1 | +2 | **+10** |
| frostbite | -1 | +4 | -5 | -2 | -7 | +5 | **+14** |
| demonforged | +1 | +3 | -4 | +1 | +0 | -1 | +5 |
| multistrike | +4 | -0 | +6 | **+12** | -5 | +2 | +2 |
| lich | -4 | -0 | +1 | -6 | **-10** | +3 | **+9** |
| mending | +2 | +4 | +4 | -2 | -1 | +3 | +5 |
| suplex | +2 | +2 | -7 | +5 | -3 | +3 | +7 |
| decapitate | +1 | -0 | -7 | +4 | +4 | +0 | +6 |
| alpha | +7 | -0 | -10 | +6 | +3 | +6 | +2 |
| tracker | -4 | **-9** | +1 | +3 | -7 | +8 | -2 |
| arc | +1 | +4 | +8 | +7 | -8 | **+10** | **+9** |
| bastion | -4 | **+9** | -4 | **+12** | -3 | +6 | +5 |

#### T2

| Enchant | EnderDemon ±7 | Apis ✗ ±47 | DeathReaper ±13 | Enyvil ±12 | Polaris ±9 | TimeController ±5 | WitherBoss ±8 | monking ±9 | babayaga ±9 | death ±6 | hornedHuntsman ±12 | leonard ✗ ±34 | lordoftorment ⚠ ±18 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| excalibur | **+29** | +56 | **+15** | **+20** | **+18** | **+21** | **+58** | **+57** | **+10** | **+14** | +7 | +40 | **+18** |
| rage | **+8** | +46 | **+13** | **+15** | +7 | **+13** | **+53** | **+51** | -0 | -1 | -5 | +6 | +2 |
| momentum | **+50** | +63 | **+17** | **+14** | **+12** | **+13** | **+20** | **+10** | **+21** | **+22** | **+22** | +53 | **+34** |
| rupture | **+13** | +56 | **+33** | +4 | **+47** | **+42** | **+27** | **+11** | **-32** | **+18** | **+26** | +19 | +13 |
| colossus | **+18** | +22 | **+23** | **+17** | +5 | **+19** | **+24** | **+41** | **+33** | **+17** | **+14** | +63 | +3 |
| roulette | **+22** | +54 | **+24** | +9 | **+27** | **+27** | +7 | **+24** | **+10** | **+18** | **+23** | +17 | **+28** |
| assassinate | **+49** | +42 | +5 | -5 | +3 | +0 | -2 | +3 | -2 | **+43** | +4 | +4 | -4 |
| executioner | **+20** | +16 | **+20** | **+20** | **+26** | **+15** | **+17** | **+12** | **+15** | **+19** | **+15** | +30 | -5 |
| cultist | **+24** | +9 | **+17** | **+14** | **+19** | **+19** | **+12** | **+13** | **+24** | **+6** | **+20** | +16 | **+28** |
| venomous | **+22** | +27 | +8 | -4 | **+45** | -1 | +4 | **+22** | -6 | **-7** | **+31** | +33 | +9 |
| poisonous | **+13** | +12 | +4 | +1 | **+37** | -2 | +3 | **+10** | +4 | +3 | **+18** | +16 | **+19** |
| blind | **+16** | +49 | **+14** | +5 | +3 | +5 | +1 | +7 | +6 | **+10** | +7 | +52 | +5 |
| riposte | **-8** | +46 | -6 | -0 | +7 | **+8** | +6 | +5 | +6 | -2 | +8 | +56 | +10 |
| berserk | +1 | +46 | +0 | +10 | +5 | +3 | -4 | -6 | -6 | **+30** | +7 | +13 | **-18** |
| killingblow | +4 | +44 | **+16** | -4 | +4 | -5 | +7 | +3 | +2 | -3 | +1 | -6 | -7 |
| getoffme | +3 | +45 | +1 | +3 | -5 | -1 | +5 | -2 | +3 | +3 | +5 | +40 | **-18** |
| jammer | +4 | +42 | +2 | +1 | **+9** | -1 | +2 | -3 | +2 | -1 | +6 | +42 | -13 |
| cripple | +3 | -5 | -1 | +8 | +2 | +2 | +6 | -1 | -6 | +3 | +6 | +20 | -16 |
| feast | +5 | -6 | +5 | -1 | +3 | **+6** | +2 | -5 | -5 | +2 | +4 | +12 | -3 |
| disarm | **-8** | -4 | +3 | +7 | -1 | **-11** | +5 | -3 | +3 | -1 | +3 | +11 | -12 |
| soulbound | +4 | +43 | -5 | -0 | +3 | -3 | -6 | -7 | -5 | +3 | -1 | +1 | -7 |
| crushingblow | **+9** | -1 | -0 | +6 | +1 | -3 | -3 | -6 | -8 | -2 | -0 | -2 | -15 |
| timber | +1 | +46 | +0 | +5 | -2 | **-6** | -2 | +5 | +4 | +4 | -6 | +43 | -8 |
| rally | +7 | -7 | -12 | -1 | +3 | +5 | +2 | +3 | -3 | +4 | +7 | +41 | **-23** |
| necromancer | +3 | -16 | -4 | +5 | -5 | +3 | +0 | -1 | +2 | +1 | -2 | +29 | -10 |
| trade | **+14** | +25 | **-15** | -5 | -8 | +2 | +5 | +0 | -7 | -1 | -3 | +20 | -15 |
| daze | +4 | -5 | +1 | -1 | +1 | -2 | +0 | -2 | +2 | **+7** | +4 | +31 | -4 |
| accelerant | -5 | +42 | +9 | +0 | -5 | -1 | **-9** | -2 | -6 | **+10** | +6 | +40 | **-18** |
| sunder | +3 | +47 | -1 | -6 | +1 | -1 | +3 | +4 | **-11** | -2 | +3 | +43 | -3 |
| reach | **+10** | +1 | -4 | -0 | -6 | -2 | -2 | -1 | -3 | -5 | +3 | +21 | **-19** |
| frostbite | +2 | +44 | +0 | +4 | -0 | -3 | -5 | +2 | +1 | **-8** | +4 | +26 | -13 |
| demonforged | +2 | -3 | +4 | +6 | +2 | -1 | +2 | -4 | -9 | -2 | +0 | +0 | **-35** |
| multistrike | -2 | -7 | +2 | +0 | -2 | **-6** | -4 | -5 | +5 | -3 | -1 | +10 | -3 |
| lich | +3 | +46 | +5 | +8 | +2 | -3 | -3 | -6 | -1 | +1 | +3 | +4 | -14 |
| mending | +4 | +47 | -1 | +1 | +7 | -0 | -5 | -7 | -7 | **-6** | +1 | +32 | -15 |
| suplex | **+8** | +42 | -0 | -3 | +1 | -0 | **-14** | **-9** | +2 | +5 | -1 | +29 | -10 |
| decapitate | +2 | -9 | +0 | -0 | -0 | +0 | -7 | -2 | -6 | **+6** | -3 | +7 | **-18** |
| alpha | -0 | +44 | +3 | -10 | +1 | -1 | -4 | -3 | -5 | +1 | -3 | +43 | -15 |
| tracker | +4 | +43 | +5 | +3 | -0 | +1 | -4 | -8 | +3 | +0 | -2 | +37 | -10 |
| arc | -6 | +48 | -10 | -8 | -3 | -2 | **-9** | -2 | **-13** | -2 | -2 | +29 | -12 |
| bastion | +1 | +33 | **-93** | +2 | -6 | **-11** | -7 | **-39** | **-120** | **-19** | **-77** | +43 | -12 |

#### T3

| Enchant | Basilisk ±2 | Emperor Scorpion ±2 | Mantis ±2 | Mothra ±2 | The Kraken ±2 | rahovart ±2 |
|---|---:|---:|---:|---:|---:|---:|
| excalibur | **+58** | **+58** | **+58** | **+58** | **+58** | **+14** |
| rage | **+27** | **+36** | **+51** | **+42** | **+37** | +0 |
| momentum | **+18** | **+18** | **+19** | **+19** | **+18** | **+28** |
| rupture | **+28** | **+46** | **+11** | **+10** | **+24** | +1 |
| colossus | **+15** | **+14** | **+9** | **+15** | **+34** | **-2** |
| roulette | **+12** | **+30** | **+24** | **+16** | **+27** | **+6** |
| assassinate | **+2** | **+2** | **+43** | **+43** | **+43** | **+3** |
| executioner | **+21** | **+21** | **+20** | **+20** | **+21** | **+20** |
| cultist | **+14** | **+25** | **+15** | **+18** | **+15** | **+23** |
| venomous | **+38** | **+56** | **+12** | **+11** | **+19** | +2 |
| poisonous | **+28** | **+37** | **+7** | **+8** | **+14** | +2 |
| blind | **+6** | **+10** | **+13** | **+11** | **+11** | **+12** |
| riposte | **+10** | **+10** | **+10** | **+9** | **+5** | +0 |
| berserk | +0 | +0 | +0 | +0 | +0 | +0 |
| killingblow | +0 | +0 | **+15** | +0 | +0 | +0 |
| getoffme | +0 | +0 | +0 | +0 | +0 | +0 |
| jammer | +0 | +0 | +0 | +0 | +0 | +0 |
| cripple | +0 | +0 | +0 | +0 | +0 | +0 |
| feast | -0 | +0 | +0 | +0 | +0 | +0 |
| disarm | -0 | +0 | +0 | +0 | +0 | +0 |
| soulbound | -0 | +0 | +0 | +0 | +0 | +0 |
| crushingblow | +0 | +0 | +0 | +0 | +0 | +0 |
| timber | +0 | +0 | +0 | +0 | +0 | +0 |
| rally | +0 | +0 | +0 | +0 | +0 | +0 |
| necromancer | +0 | +0 | -0 | +0 | +0 | +0 |
| trade | +0 | +0 | -0 | +0 | +0 | +0 |
| daze | -0 | +0 | +0 | +0 | +0 | +0 |
| accelerant | -0 | +0 | +0 | +0 | +0 | +0 |
| sunder | +0 | +0 | +0 | +0 | +0 | +0 |
| reach | +0 | -1 | +0 | +0 | +0 | +0 |
| frostbite | +0 | -1 | +0 | +0 | +0 | +0 |
| demonforged | -0 | +0 | +0 | +0 | +0 | +0 |
| multistrike | +0 | -1 | +0 | +0 | +0 | +0 |
| lich | -0 | +0 | +0 | +0 | +0 | +0 |
| mending | -0 | +0 | +0 | +0 | +0 | +0 |
| suplex | +0 | +0 | +0 | +0 | +0 | +0 |
| decapitate | +0 | +0 | -0 | +0 | +0 | +0 |
| alpha | -0 | +0 | +0 | +0 | +0 | +0 |
| tracker | -0 | +0 | -0 | +0 | +0 | +0 |
| arc | +0 | +0 | +0 | +0 | +0 | +0 |
| bastion | -0 | **-5** | **-12** | +0 | +0 | +0 |

#### T4

| Enchant | Mobzilla ±2 | The King ±2 | The Queen ±2 | rahovart ±2 | Godzilla ±2 |
|---|---:|---:|---:|---:|---:|
| excalibur | +1 | +0 | +1 | **+14** | **+55** |
| rage | -0 | -0 | -0 | +0 | **+51** |
| momentum | +1 | +1 | +1 | **+28** | +1 |
| rupture | **+40** | **+46** | **+48** | +0 | **+8** |
| colossus | **+20** | **+34** | **+32** | -2 | **+7** |
| roulette | -1 | **+28** | **+21** | **+31** | **+18** |
| assassinate | **+2** | **+2** | **+2** | +1 | **+43** |
| executioner | **+20** | **+20** | **+20** | **+20** | **+20** |
| cultist | **+15** | **+28** | **+12** | **+19** | **+16** |
| venomous | **+47** | **+40** | **+50** | +2 | **+9** |
| poisonous | **+40** | **+42** | **+40** | **+2** | **+6** |
| blind | **+8** | **+11** | **+12** | **+12** | **+12** |
| riposte | +1 | +1 | +1 | +0 | +0 |
| berserk | -0 | +0 | -0 | +0 | +0 |
| killingblow | -0 | -0 | -0 | +1 | +0 |
| getoffme | -0 | +0 | +0 | +0 | +0 |
| jammer | -0 | +0 | +0 | +0 | +0 |
| cripple | +0 | +0 | +0 | +0 | +0 |
| feast | +0 | +0 | +0 | +0 | +0 |
| disarm | +0 | +0 | +0 | +0 | +0 |
| soulbound | +0 | -0 | +0 | +0 | +0 |
| crushingblow | -0 | -0 | +0 | +0 | +0 |
| timber | +0 | +0 | +0 | +0 | +0 |
| rally | +0 | +0 | +0 | +0 | +0 |
| necromancer | +0 | +0 | +0 | +0 | +0 |
| trade | +0 | +0 | +0 | +0 | +0 |
| daze | +0 | +0 | +0 | +0 | +0 |
| accelerant | -0 | -0 | +0 | +0 | +0 |
| sunder | +0 | -0 | -0 | +0 | +0 |
| reach | +0 | +0 | -0 | +0 | +0 |
| frostbite | +0 | -0 | -0 | +0 | +0 |
| demonforged | +0 | +0 | +0 | +0 | +0 |
| multistrike | +0 | -0 | +0 | +0 | +0 |
| lich | +0 | -0 | +0 | +0 | +0 |
| mending | +0 | -0 | +0 | +0 | +0 |
| suplex | +0 | +0 | +0 | +0 | +0 |
| decapitate | -0 | -0 | +0 | +0 | +0 |
| alpha | +0 | -0 | +0 | +0 | +0 |
| tracker | +0 | +0 | +0 | +0 | +0 |
| arc | -0 | -0 | +0 | +0 | +0 |
| bastion | +0 | **-6** | **-5** | +0 | +0 |

