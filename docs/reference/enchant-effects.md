# Enchant effects table

Generated 2026-10-25 by `tools/balance/effects_table.py` from 48 census jobs in `C:\qfs\campaign`. **Do not edit by hand: rerun the tool.** Every number is a measurement from the running pack, paired against the same weapon and armour with no custom enchantment ([method](enchantment-combat-results.md#1-method)). This is the table decision [0005](../decisions/0005-enchant-census-proposals.md) P10 asks for; what to do about it is in [enchant-rarity-plan](../design/enchant-rarity-plan.md). Machine-readable copy: [`enchant-effects.json`](enchant-effects.json).

**Contents.** [How to read it](#how-to-read-it) · [Rarity distribution](#rarity-distribution) · [Bosses](#the-bosses) · [Weapons](#weapon-enchantments) · [Armour](#armour-enchantments) · [Bows](#bow-enchantments) · [Utility, tools and PvP](#utility-tool-and-pvp-enchantments) · [Pairs](#pairs) · [Stacks](#curated-stacks) · [Data notes](#data-notes) · [Appendix: every boss](#appendix-speed-up-by-boss)

## How to read it

- **Speed-up** = 1 − (time to kill with the enchantment ÷ time to kill without). +50% means the boss dies in half the time. **Seconds saved** is the same thing in seconds on one reference boss per tier.
- **Trusted mean** averages the top level over the 22 bosses whose controls are unbiased and uncapped (see [Bosses](#the-bosses)). The 750-per-hit T4 bosses, Rahovart (25/hit) and Godzilla are shown in their own columns, not averaged: a cap measures the boss, not the enchantment.
- **Significant** (bold, and the counts in brackets) means outside that boss's threshold, which is the larger of its control noise band and two standard deviations of ten placebo enchantments with no boss-fight mechanism. Proc luck is wider than that on the deterministic T3/T4 bosses: the **replicate sd** column is the spread of the same cell over its three runs, where it exists.
- **Damage reduction** (armour) is damage taken over sixty of the boss's own melee hits against the same armour with no enchantment. From T3 the tier armour already takes nothing from any boss, so every armour enchantment is 0 there; the means are T1–T2.
- **Proc** is the observed firing rate on the enchantment's own trigger over every singles job, against the declared rate. A mismatch is a code question, not a balance one.
- **Verdict** compares the measured effect with the band its *declared* rarity should buy (registry source as of this run): weapons Common < 5, Uncommon 5–12, Rare 12–20, Epic 20–30, Legendary ≥ 30 points; armour Common < 5, Uncommon 5–10, Rare 10–20, Epic 20–30, Legendary ≥ 30 points. |effect| ≤ 5 points and significant on under a quarter of the bosses reads **no observable effect**. Enchantments the census has no cell for are **untestable** and priced on utility. These bands are a proposal; they live at the top of the script.
- **Re-tiered since the census** (registry rarity differs from the rarity the census jar carried): momentum Uncommon → Epic, rage Epic → Legendary, roulette Uncommon → Rare, tank Rare → Epic.

## Rarity distribution

Declared rarity (registry today) by category:

| Rarity | Weapon | Armour | Bow | Tool | Any | Total |
|---|---:|---:|---:|---:|---:|---:|
| Common | 3 | 2 | 0 | 3 | 0 | 8 |
| Uncommon | 5 | 2 | 0 | 5 | 0 | 12 |
| Rare | 15 | 7 | 4 | 2 | 0 | 28 |
| Epic | 10 | 5 | 2 | 5 | 1 | 23 |
| Legendary | 3 | 3 | 1 | 0 | 3 | 10 |
| **All** | 36 | 19 | 7 | 15 | 4 | 81 |

Declared rarity by verdict:

| Rarity | proportionate | too strong for rarity | too weak | no observable effect | harmful: loses fights | untestable by this census (utility/PvP) | not measured |
|---|---:|---:|---:|---:|---:|---:|---:|
| Common | 0 | 0 | 0 | 0 | 0 | 8 | 0 |
| Uncommon | 1 | 1 | 0 | 1 | 0 | 9 | 0 |
| Rare | 4 | 4 | 1 | 6 | 0 | 13 | 0 |
| Epic | 4 | 0 | 1 | 2 | 1 | 15 | 0 |
| Legendary | 3 | 0 | 0 | 1 | 1 | 5 | 0 |

Where the measured effect lands (rows: declared rarity; columns: the band the measurement falls in; combat enchantments with a measurable effect only, Berserk read at half health, Multi Strike as its stack contribution):

| Declared \ measured | Common | Uncommon | Rare | Epic | Legendary | Negative |
|---|---:|---:|---:|---:|---:|---:|
| Common | 0 | 0 | 0 | 0 | 0 | 0 |
| Uncommon | 1 | 1 | 1 | 0 | 0 | 0 |
| Rare | 6 | 1 | 5 | 2 | 1 | 0 |
| Epic | 2 | 0 | 1 | 4 | 0 | 1 |
| Legendary | 1 | 1 | 0 | 0 | 3 | 0 |

## The bosses

| Tier | Boss | HP | Control TTK | Control band | Placebo median | Threshold | Control dmg / 60 hits | Status |
|---|---|---:|---:|---:|---:|---:|---:|---|
| T1 | Knight Phantom | 290 | 13.1 s | ±8.7% | +1.0 | ±8.7% | 232 | trusted |
| T1 | Twilight Lich | 717 | 18.6 s | ±5.5% | +2.2 | ±8.6% | 100 | trusted: shields held down |
| T1 | Minoshroom | 857 | 21.5 s | ±2.7% | +0.3 | ±8.3% | 286 | trusted |
| T1 | Yeti Boss | 1,284 | 34.3 s | ±5.9% | +3.8 | ±8.0% | 22 | trusted |
| T1 | Naga | 1,338 | 34.0 s | ±7.5% | +0.1 | ±10.1% | 120 | trusted |
| T1 | Tower Boss | 1,659 | 97.1 s | ±8.2% | -0.9 | ±8.2% | 0 | trusted |
| T1 | Snow Queen | 1,665 | 42.6 s | ±2.4% | +3.8 | ±9.3% | 134 | trusted |
| T2 | Kitsune | 383 | – | – | – | – | 12 | **defence-only**: immune to weapons by design |
| T2 | Polaris | 580 | 11.6 s | ±3.5% | +0.7 | ±8.9% | 10 | trusted |
| T2 | Apis | 808 | 48.7 s | ±7.4% | +33.7 | ±47.4% | 29 | **excluded**: controls biased: placebos +34% (results §7.1) |
| T2 | DeathReaper | 1,134 | 14.8 s | ±4.1% | +0.7 | ±12.9% | 61 | trusted |
| T2 | TimeController | 1,689 | 57.5 s | ±3.4% | -1.1 | ±5.5% | 174 | trusted |
| T2 | Enyvil | 1,797 | 20.6 s | ±12.2% | +0.6 | ±12.2% | 67 | trusted: struck at the eye |
| T2 | WitherBoss | 2,284 | 25.8 s | ±6.3% | +1.0 | ±8.1% | 10 | trusted |
| T2 | hornedHuntsman | 2,488 | 40.0 s | ±12.4% | -0.2 | ±12.4% | 42 | trusted |
| T2 | EnderDemon | 2,899 | 132.4 s | ±7.5% | +3.7 | ±7.5% | 0 | trusted |
| T2 | babayaga | 3,271 | 52.2 s | ±3.8% | -0.8 | ±9.1% | 8 | trusted: cap 15/hit |
| T2 | lordoftorment | 3,853 | 71.3 s | ±4.9% | -13.9 | ±17.5% | 42 | **shown**: cap 5 raw before its event; controls biased −14%; TTK runs to 50% only (results §7.3) |
| T2 | leonard | 4,070 | 156.8 s | ±33.6% | +33.9 | ±33.6% | 42 | **excluded**: last-10% band noise ±34% (results §7.2) |
| T2 | monking | 5,414 | 50.8 s | ±8.8% | -2.4 | ±8.8% | 66 | trusted |
| T2 | death | 6,321 | 85.5 s | ±2.2% | +2.9 | ±5.9% | 172 | trusted |
| T3 | Mantis | 598 | 12.2 s | ±2.0% | +0.0 | ±2.0% | 0 | trusted |
| T3 | Mothra | 709 | 12.7 s | ±2.0% | +0.0 | ±2.0% | 0 | trusted |
| T3 | Basilisk | 850 | 77.4 s | ±2.0% | +0.0 | ±2.0% | 0 | trusted |
| T3 | Emperor Scorpion | 1,558 | 283.8 s | ±2.0% | +0.0 | ±2.0% | 0 | trusted |
| T3 | The Kraken | 3,913 | 237.5 s | ±2.0% | +0.0 | ±2.0% | 0 | trusted |
| T3/T4 | rahovart | 42,249 | 845.0 s | ±2.0% | +0.0 | ±2.0% | 0 | **apart**: cap 25/hit; Lycanites damageMax; T3 and T4 jobs identical |
| T4 | Godzilla | 10,000 | 8.3 s | ±2.0% | +0.0 | ±2.0% | 0 | **apart**: uncapped T4; dies in 8 s to the Royal sword |
| T4 | Mobzilla | 16,175 | 134.8 s | ±2.0% | +0.0 | ±2.0% | 0 | **capped**: cap 750/hit |
| T4 | The Queen | 28,834 | 240.3 s | ±2.0% | +0.0 | ±2.0% | 0 | **capped**: cap 750/hit |
| T4 | The King | 35,346 | 294.6 s | ±2.0% | +0.0 | ±2.0% | 0 | **capped**: cap 750/hit |

## Weapon enchantments

Top level, melee. Brackets: bosses significant in that group (− for a significant loss). Sorted by trusted mean.

| Enchant | Rarity | Lvl | Effect | Trusted mean (sig) | T1 | T2 | T3 | T4 capped | Rahovart | Godzilla | Verdict |
|---|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---|
| excalibur | Legendary | 1 | +4 flat; while held Strength I (x2.3), Resistance I, Speed I | **+42.1** ± 21 (21/22) | +55 (7) | +25 (9) | +58 (5) | +1 | +14 | +55 | proportionate |
| rage | Legendary (was Epic) | 3 | 5/10/15%: Strength I (x2.3) for 4/6/8 s | **+32.0** ± 22 (18/22) | +51 (7) | +16 (6) | +39 (5) | -0 | +0 | +51 | proportionate |
| momentum | Epic (was Uncommon) | 3 | +0.5 x L per consecutive hit, 8 stacks, 2 s window: up to +3.5/7/10.5 flat | **+25.1** ± 12 (22/22) | +37 (7) | +20 (10) | +18 (5) | +1 | +28 | +1 | proportionate |
| **rupture** | Rare | 3 | 25/35/45%: bleed 4% of the hit per stack per second, L+1 stacks, 5/6/7 s, ignores armour | **+21.9** ± 17 (20, 1−/22) | +25 (7) | +19 (8) | +24 (5) | +44 (3) | +1 | +8 | **too strong for rarity** |
| colossus | Epic | 3 | 6/9/12%: +2.5% x L of the target's max health, capped at 4x the hit | **+21.8** ± 10 (21/22) | +26 (7) | +21 (9) | +17 (5) | +29 (3) | -2 | +7 | proportionate |
| **roulette** | Rare (was Uncommon) | 1 | every hit x2 or x0.5 (EV x1.25) | **+20.6** ± 7 (20/22) | +22 (7) | +19 (8) | +22 (5) | +16 (2) | +6 | +18 | **too strong for rarity** |
| executioner | Rare | 3 | x(1 + 0.25 x L x target's missing health), up to x1.75 | **+19.4** ± 4 (22/22) | +21 (7) | +18 (10) | +20 (5) | +20 (3) | +20 | +20 | proportionate |
| assassinate | Rare | 3 | x1.25/1.50/1.75 while the target is not targeting you | **+18.7** ± 21 (12/22) | +26 (5) | +10 (2) | +27 (5) | +2 (3) | +3 | +43 | proportionate |
| **venomous** | Rare | 3 | 8/16/24%: Poison II 7/9/11 s with venom 5.8% x L of the hit per second, target -10% damage | **+17.8** ± 16 (15, 1−/22) | +20 (6) | +11 (4) | +27 (5) | +46 (3) | +2 | +9 | **too strong for rarity (T4 only)** |
| cultist | Rare | 3 | 8/16/24%: x2 damage; you pay 10% max health per level as physical damage | **+17.5** ± 5 (22/22) | +19 (7) | +17 (10) | +17 (5) | +18 (3) | +23 | +16 | proportionate |
| **poisonous** | Uncommon | 3 | 10/20/30%: Poison I 4/5/6 s with venom 4% x L of the hit per second | **+13.6** ± 12 (15/22) | +16 (6) | +9 (4) | +19 (5) | +41 (3) | +2 | +6 | **too strong for rarity** |
| **blind** | Rare | 3 | 8/16/24%: Blindness 4/5/6 s | **+10.5** ± 5 (14/22) | +15 (6) | +7 (3) | +10 (5) | +10 (3) | +12 | +12 | **too weak** |
| riposte | Uncommon | 3 | +1.5 x L flat while hurt in the last 3 s | **+7.1** ± 8 (11, 1−/22) | +13 (5) | +2 (1) | +9 (5) | +1 | +0 | +0 | proportionate |
| berserk | Epic | 3 | your damage x(1 + 0.9 x your missing health) at III; nothing at full health | **+3.0** ± 7 (2/22) | +4 (1) | +4 (1) | +0 | -0 | +0 | +0 | proportionate |
| killingblow | Epic | 3 | 0.1/0.2/0.3%: sets target health to 0 | **+2.6** ± 5 (2/22) | +2 | +3 (1) | +3 (1) | -0 | +0 | +0 | no observable effect |
| cripple | Rare | 3 | 10/20/30%: target deals 10/15/20% less for 6/8/10 s | **+1.1** ± 4 (0/22) | +1 | +2 | +0 | +0 | +0 | +0 | no observable effect |
| necromancer | Rare | 3 | 3/6/9%: summons a zombie or skeleton for 30/40/50 s | **+0.6** ± 3 (0/22) | +2 | +0 | -0 | +0 | +0 | +0 | no observable effect |
| accelerant | Rare | 3 | 12%: every debuff on the target +L amplifier (cap IV/VI/VIII), +2 s/level; wither capped at IV | **+0.4** ± 6 (3, 1−/22) | +2 (2) | -0 (1) | -0 | -0 | +0 | +0 | no observable effect |
| sunder | Uncommon | 3 | 10/20/30%: target deals 5/10/15% less + Mining Fatigue, 4/5/6 s | **+0.3** ± 5 (1, 1−/22) | +2 (1) | -1 | +0 | -0 | +0 | +0 | no observable effect |
| frostbite | Rare | 3 | 20/30/40%: Slowness I-III 1.5/2.0/2.5 s | **+0.3** ± 5 (1, 1−/22) | +1 (1) | -0 | -0 | -0 | +0 | +0 | no observable effect |
| suplex | Rare | 3 | 10/15/20%: throws the target up (fall damage) | **-0.1** ± 5 (1, 2−/22) | +1 | -1 (1) | +0 | +0 | +0 | +0 | no observable effect |
| alpha | Rare | 3 | 3/6/9%: summons a tamed wolf for 30/40/50 s | **-0.3** ± 4 (0/22) | +2 | -2 | -0 | -0 | +0 | +0 | no observable effect |
| arc | Epic | 3 | 15/20/25%: 35% of the hit to up to L others within 5 blocks | **-1.2** ± 6 (2, 2−/22) | +4 (2) | -6 | +0 | -0 | +0 | +0 | no observable effect |
| **bastion** | Epic | 3 | 3/6/9%: summons an iron golem for 30/40/50 s, aimed at the target | **-16.6** ± 35 (2, 8−/22) | +3 (2) | -37 | -3 | -3 | +0 | +0 | **harmful: loses fights** |

### Seconds saved, levels and procs

Reference bosses: T1 Naga (34.0 s unenchanted), T2 WitherBoss (25.8 s unenchanted), T3 Mantis (12.2 s unenchanted), T4 Mobzilla (134.8 s unenchanted, capped). A cell reads *TTK with* → *seconds saved*. Levels are speed-up at I / II / III on the deep boss of that tier (levels job, one cell each: ±10 for proc enchantments).

| Enchant | Naga (T1) | Wither (T2) | Mantis (T3) | Mobzilla (T4, capped) | Levels Naga | Levels Mantis | Levels Mobzilla | Proc obs / declared | Replicate sd |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| excalibur | 14 s → +20 s | 11 s → +15 s | 5 s → +7 s | 134 s → +1 s | +60 / – / – | +58 / – / – | +1 / – / – | – | Mantis ±0, Mobzilla ±0, Naga ±2, lordoftorment ±7 |
| rage | 15 s → +19 s | 12 s → +14 s | 6 s → +6 s | 135 s → -0 s | -7 / +52 / +57 | +4 / +48 / +42 | +0 / +0 / +0 | 14.4 / 15% ATTACK | Mantis ±7, Mobzilla ±0, Naga ±1, lordoftorment ±9 |
| momentum | 23 s → +11 s | 21 s → +5 s | 10 s → +2 s | 133 s → +2 s | +17 / +30 / +33 | +7 / +14 / +19 | +0 / +1 / +1 | – | Mantis ±0, Mobzilla ±0, Naga ±1, lordoftorment ±6 |
| **rupture** | 27 s → +7 s | 19 s → +7 s | 11 s → +1 s | 81 s → +54 s | +14 / +19 / +26 | +5 / +7 / +11 | +17 / +29 / +47 | 45.2 / 45% ATTACK | Mantis ±0, Mobzilla ±5, Naga ±4, lordoftorment ±9 |
| colossus | 24 s → +10 s | 20 s → +6 s | 11 s → +1 s | 108 s → +27 s | -1 / +35 / +35 | +1 / +7 / +10 | +5 / +6 / +22 | 11.6 / 12% ATTACK | Mantis ±3, Mobzilla ±6, Naga ±5, lordoftorment ±17 |
| **roulette** | 27 s → +7 s | 24 s → +2 s | 9 s → +3 s | 136 s → -1 s | +12 / – / – | +17 / – / – | +23 / – / – | – | Mantis ±11, Mobzilla ±12, Naga ±4, lordoftorment ±5 |
| executioner | 26 s → +8 s | 21 s → +4 s | 10 s → +2 s | 108 s → +27 s | +9 / +15 / +27 | +8 / +15 / +20 | +8 / +15 / +20 | – | Mantis ±0, Mobzilla ±0, Naga ±2, lordoftorment ±10 |
| assassinate | 21 s → +13 s | 26 s → -1 s | 7 s → +5 s | 132 s → +3 s | +23 / +35 / +40 | +20 / +33 / +43 | +1 / +5 / +5 | – | Mantis ±0, Mobzilla ±1, Naga ±1, lordoftorment ±8 |
| **venomous** | 26 s → +8 s | 25 s → +1 s | 11 s → +1 s | 71 s → +63 s | +7 / +13 / +21 | +3 / +7 / +11 | +17 / +37 / +52 | 23.8 / 24% ATTACK | Mantis ±1, Mobzilla ±2, Naga ±2, lordoftorment ±9 |
| cultist | 30 s → +4 s | 23 s → +3 s | 10 s → +2 s | 115 s → +20 s | +8 / +15 / +18 | +2 / +11 / +23 | +1 / +13 / +16 | 24.1 / 24% ATTACK | Mantis ±5, Mobzilla ±1, Naga ±6, lordoftorment ±4 |
| **poisonous** | 30 s → +4 s | 25 s → +1 s | 11 s → +1 s | 81 s → +54 s | +6 / +11 / +19 | +2 / +5 / +8 | +8 / +29 / +36 | 29.4 / 30% ATTACK | Mantis ±1, Mobzilla ±2, Naga ±4, lordoftorment ±5 |
| **blind** | 28 s → +6 s | 26 s → +0 s | 11 s → +2 s | 124 s → +11 s | +7 / +14 / +14 | +8 / +11 / +12 | +4 / +8 / +12 | 23.3 / 24% ATTACK | Mantis ±0, Mobzilla ±2, Naga ±5, lordoftorment ±2 |
| riposte | 28 s → +6 s | 24 s → +2 s | 11 s → +1 s | 134 s → +1 s | +9 / +16 / +20 | +3 / +7 / +10 | +0 / +0 / +1 | – | Mantis ±0, Mobzilla ±0, Naga ±1, lordoftorment ±6 |
| berserk | 32 s → +2 s | 27 s → -1 s | 12 s → +0 s | 135 s → -0 s | +3 / +6 / +5 | -0 / -0 / -0 | +0 / +0 / +0 | – | Mantis ±0, Mobzilla ±0, Naga ±2, lordoftorment ±10 |
| killingblow | 33 s → +1 s | 24 s → +2 s | 10 s → +2 s | 135 s → -0 s | -4 / +1 / +1 | -0 / +0 / -0 | -0 / +0 / +0 | – | Mantis ±11, Mobzilla ±0, Naga ±1, lordoftorment ±2 |
| cripple | 34 s → -0 s | 24 s → +2 s | 12 s → +0 s | 135 s → +0 s | +8 / +7 / +7 | -0 / -0 / +0 | +0 / +0 / +0 | 28.0 / 30% ATTACK | Mantis ±0, Mobzilla ±0, Naga ±5, lordoftorment ±8 |
| necromancer | 32 s → +2 s | 26 s → +0 s | 12 s → -0 s | 135 s → +0 s | +3 / +1 / +6 | -0 / +0 / +0 | -0 / +0 / +0 | 10.5 / 9% ATTACK | Mantis ±0, Mobzilla ±0, Naga ±1, lordoftorment ±5 |
| accelerant | 36 s → -2 s | 28 s → -2 s | 12 s → +0 s | 135 s → -0 s | -3 / +6 / +1 | -0 / +0 / -0 | -0 / -0 / -0 | 12.0 / 12% ATTACK | Mantis ±0, Mobzilla ±0, Naga ±4, lordoftorment ±15 |
| sunder | 33 s → +1 s | 25 s → +1 s | 12 s → +0 s | 135 s → +0 s | +2 / +3 / +1 | -0 / -0 / -0 | +0 / +0 / -0 | 29.0 / 30% ATTACK | Mantis ±0, Mobzilla ±0, Naga ±1, lordoftorment ±8 |
| frostbite | 36 s → -2 s | 27 s → -1 s | 12 s → +0 s | 135 s → +0 s | +3 / +5 / -12 | +0 / +0 / -0 | +0 / -0 / +0 | 38.4 / 40% ATTACK | Mantis ±0, Mobzilla ±0, Naga ±5, lordoftorment ±3 |
| suplex | 37 s → -3 s | 29 s → -4 s | 12 s → +0 s | 135 s → +0 s | -4 / +4 / +0 | +0 / -0 / -0 | -0 / +0 / -0 | 20.0 / 20% ATTACK | Mantis ±0, Mobzilla ±0, Naga ±5, lordoftorment ±7 |
| alpha | 37 s → -3 s | 27 s → -1 s | 12 s → +0 s | 135 s → +0 s | +6 / +3 / -0 | -0 / -0 / +0 | -0 / +0 / +0 | 9.4 / 9% ATTACK | Mantis ±0, Mobzilla ±0, Naga ±7, lordoftorment ±13 |
| arc | 31 s → +3 s | 28 s → -2 s | 12 s → +0 s | 135 s → -0 s | +5 / -2 / +2 | +0 / +0 / -0 | +0 / +0 / +0 | 25.3 / 25% ATTACK | Mantis ±0, Mobzilla ±0, Naga ±4, lordoftorment ±4 |
| **bastion** | 35 s → -1 s | 27 s → -2 s | 14 s → -1 s | 135 s → +0 s | +0 / +3 / +10 | -10 / -7 / -12 | -0 / +0 / +0 | 9.3 / 9% ATTACK | Mantis ±0, Mobzilla ±0, Naga ±10 |

### Conditional and costed

| Enchant | Boss | Measure | Value |
|---|---|---|---:|
| cultist | Mantis | wielder at 50% / 25% health | +19 / +22 |
| cultist | Mobzilla | wielder at 50% / 25% health | +12 / +14 |
| cultist | Naga | wielder at 50% / 25% health | +8 / +23 |
| cultist | lordoftorment | wielder at 50% / 25% health | +15 / +18 |
| cultist | Naga | wielder's lowest health in the fight (control → with) | 20.0 → 1.8 of 20 |
| cultist | WitherBoss | wielder's lowest health in the fight (control → with) | 20.0 → 18.3 of 20 |
| berserk | Mantis | wielder at 50% / 25% health | +31 / +40 |
| berserk | Mobzilla | wielder at 50% / 25% health | +31 / +40 |
| berserk | Naga | wielder at 50% / 25% health | +27 / +41 |
| berserk | lordoftorment | wielder at 50% / 25% health | +29 / +42 |
| multistrike | Mantis | added to Colossus + Executioner (stack − pair) | +13 |
| multistrike | Mobzilla | added to Colossus + Executioner (stack − pair) | +8 |
| multistrike | Naga | added to Colossus + Executioner (stack − pair) | +5 |
| multistrike | lordoftorment | added to Colossus + Executioner (stack − pair) | +6 |

## Armour enchantments

Damage reduction against each boss's own melee, top level, over sixty hits. Left out: Enyvil (defence controls vary ±32 damage); death (its hits ignore armour: 172 damage whatever the enchantment). **Hits survived** and **HP left** are the wielder's gain against the control in the same cell (the probe is held alive, so a 60-hit cell mostly ends near zero health; read the sign). Vigor and Regrowth read as negative reduction because a lethal hit only counts the health that was left: use hits survived for those two.

| Enchant | Rarity | Lvl | Effect | DR T1 | DR T2 | DR mean | Best | ≥5% on | Hits survived | HP left | Levels (Naga DR) | Verdict |
|---|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| turtle | Legendary | 1 | per piece x0.67 while holding no weapon: 80% for a set | **+61.9** | **+15.0** | **+31.5** | +76 (Snow Queen) | 12/17 | +2.7 | -0.1 | 74 | proportionate |
| tank | Epic (was Rare) | 3 | chest: 11/22/33% less damage taken, permanent Slowness I | **+30.9** | **+28.6** | **+29.4** | +38 (leonard) | 17/17 | +1.2 | +1.3 | 8 / 17 / 28 | proportionate |
| **cockroach** | Epic | 3 | chest: Resistance L+1 for 5/6/7 s after a hit leaves you at <=1 heart; 60 s cooldown | **+22.8** | +3.6 | **+10.3** | +40 (Snow Queen) | 9/17 | +0.8 | -0.1 | 0 / 7 / 26 | **too weak** |
| bulwark | Rare | 3 | chest: x(1 - 0.10 x L x your missing-health fraction) | **+13.2** | **+8.4** | **+10.1** | +27 (DeathReaper) | 14/17 | +0.5 | +0.1 | 0 / 0 / 8 | proportionate |
| affliction | Legendary | 4 | per piece ~1-4%: 7 debuffs on the attacker | +3.5 | +2.9 | +3.1 | +19 (DeathReaper) | 4/17 | +0.0 | -0.1 | 0 / 0 / 0 / 0 | no observable effect |
| frostpath | Rare | 3 | boots: freezes water underfoot | +1.4 | +3.4 | +2.7 | +15 (DeathReaper) | 4/17 | +0.2 | +0.2 | 0 / 0 / 0 | untestable by this census (utility/PvP) — freezes water |
| sacrifice | Rare | 1 | per piece: survive a lethal hit at half health; destroys the piece | +2.1 | +3.0 | +2.7 | +21 (DeathReaper) | 3/17 | +0.2 | +0.3 | 0 | untestable by this census (utility/PvP) — fires on a lethal hit; the census holds the wielder alive |
| cleansing | Rare | 3 | legs 10/20/30%: strips one debuff when hit | -0.1 | +1.4 | +0.9 | +22 (Kitsune) | 3/17 (2−) | -2.0 | +0.2 | 0 / 0 / 0 | untestable by this census (utility/PvP) — strips a debuff; the census strips DoTs after each hit |
| camouflage | Rare | 3 | legs 10/20/30%: a mob that targets you forgets you | +1.5 | +0.0 | +0.6 | +6 (TimeController) | 2/17 | +0.1 | +0.2 | 0 / 0 / 0 | untestable by this census (utility/PvP) — stops a mob acquiring you; the census assigns the target |
| nightsight | Common | 1 | helmet: night vision in the dark | +0.9 | +0.3 | +0.5 | +7 (TimeController) | 1/17 | +0.1 | -0.1 | 0 | untestable by this census (utility/PvP) — night vision |
| flippers | Uncommon | 3 | swim speed | +0.6 | +0.4 | +0.5 | +21 (DeathReaper) | 1/17 (1−) | +0.0 | +0.1 | 0 / 0 / 0 | untestable by this census (utility/PvP) — swim speed |
| stonehide | Uncommon | 3 | per piece 3% x L: falls and explosions only | +1.7 | -1.8 | -0.5 | +8 (TimeController) | 2/17 (1−) | +0.0 | +0.2 | 0 / 0 / 0 | untestable by this census (utility/PvP) — falls and explosions only |
| polarize | Legendary | 3 | 0.01%/level/piece: wipes the attacker's enchantments | +0.6 | -1.2 | -0.5 | +3 (Kitsune) | 0/17 (2−) | -0.1 | -0.4 | 0 / 0 / 0 | untestable by this census (utility/PvP) — attacker's gear (PvP) |
| reflect | Epic | 3 | per piece 8/12/16%: launches the attacker | -0.8 | -0.7 | -0.7 | +5 (lordoftorment) | 0/17 (1−) | -0.0 | +0.3 | 0 / 0 / 0 | untestable by this census (utility/PvP) — knockback on the attacker |
| rebound | Common | 3 | per piece 2/4/6%: shoves the attacker back | +0.9 | -2.6 | -1.3 | +22 (DeathReaper) | 1/17 (2−) | -0.1 | +0.0 | 0 / 0 / 0 | untestable by this census (utility/PvP) — knockback on the attacker; the census pins the target |
| frog | Rare | 3 | boots: Jump Boost I-III | -1.2 | -1.6 | -1.5 | +3 (lordoftorment) | 0/17 (1−) | -0.2 | +0.3 | 0 / 0 / 0 | untestable by this census (utility/PvP) — jump |
| deft | Epic | 2 | boots: Speed I/II | -0.4 | -2.8 | -2.0 | +4 (hornedHuntsman) | 0/17 (1−) | -0.2 | -0.0 | 0 / 0 | untestable by this census (utility/PvP) — speed |
| regrowth | Rare | 3 | legs: Regeneration I-III after 10 s out of combat | -3.2 | -9.1 | -7.0 | +1 (Snow Queen) | 0/17 (9−) | +1.0 | +0.7 | -2 / -2 / -10 | untestable by this census (utility/PvP) — out-of-combat regen; see hits survived |
| vigor | Epic | 3 | chest: +4 max health per level | -2.7 | -25.1 | -17.2 | +2 (Knight Phantom) | 0/17 (9−) | +1.2 | +4.0 | -9 / -8 / -7 | untestable by this census (utility/PvP) — +max health; see hits survived |

## Bow enchantments

Bow cells fire a full-draw arrow every 20 ticks at a boss ten blocks away and miss some; the bow noise band is wide (±2% to over ±100% per boss), so only a consistent result means anything.

| Enchant | Rarity | Lvl | Effect | Trusted mean | Sig. on | Arrows never land on | Verdict |
|---|---|---:|---|---:|---:|---|---|
| **piercing** | Rare | 3 | arrow x1.15/1.30/1.45 | +31.1 | 13/22 | Snow Queen | **too strong for rarity** |
| penetrating | Rare | 3 | arrow passes through up to L targets | +12.1 | 5/22 | Snow Queen, TimeController | untestable by this census (utility/PvP) — passes through targets (3 pinned targets) |
| bola | Rare | 3 | arrow: Slowness I-III 6/8/10 s | +8.3 | 2/22 | Snow Queen, TimeController | untestable by this census (utility/PvP) — slowness; the target is pinned |
| **homing** | Legendary | 3 | arrows steer to the nearest target within 9/12/15 blocks | +6.2 | 2/22 | Emperor Scorpion, Mobzilla, Twilight Lich, babayaga | **harmful: loses fights** |
| soulentwine | Rare | 1 | arrow: swap positions with the target | +4.7 | 2/22 | Apis, Snow Queen, TimeController | untestable by this census (utility/PvP) — swap positions |
| instanttransmission | Epic | 1 | teleport to the arrow, 3 s cooldown | +3.7 | 2/22 | Snow Queen, babayaga | untestable by this census (utility/PvP) — teleport to the arrow |
| ricochet | Epic | 3 | second arrow to the nearest target within 8 blocks | +3.5 | 1/22 | Naga, Twilight Lich, babayaga | untestable by this census (utility/PvP) — second arrow to another target |

## Utility, tool and PvP enchantments

No boss cell can exercise these. Their census rows are the placebo set's noise (trusted mean shown for completeness); price them on what they do, not on this table.

| Enchant | Rarity | Group | Effect | Census reads | Why untestable |
|---|---|---|---|---:|---|
| decapitate | Common | weapon | 15/30/40%: vanilla head drop | -0.1 | head drop on kill |
| ecofriendly | Common | tool | refund on break | – | tool: refund on break |
| magnetize | Common | tool | drops to inventory | – | tool: drops to inventory |
| rally | Common | weapon | flourish on the opening blow | +0.8 | flourish; music unimplemented |
| sieve | Common | tool | 2/4/6%: bonus drop from stone and dirt | – | tool: bonus drops |
| tracker | Common | weapon | outlines living things through walls | -0.4 | client outline |
| bountiful | Uncommon | tool | 11/22/33%: doubles drops when the tool has no Fortune | – | tool: drop doubling |
| daze | Uncommon | weapon | 10/20/30%: spins the target 180 degrees | +0.5 | spins the target; cosmetic on mobs |
| disarm | Uncommon | weapon | 4/8/12%: knocks the held item out | +0.9 | bosses hold no item |
| excavate | Uncommon | tool | vein mining 8/16/24 | – | tool: vein mining |
| oldreliable | Uncommon | tool | XP x(1 + wear x L) | – | tool: XP |
| timber | Uncommon | tool | fells the tree | +0.8 | tool: tree felling |
| torchlight | Uncommon | tool | light at head height | – | tool: light |
| feast | Rare | weapon | heal 1/2/3 hearts on kill | +1.0 | heals on kill; banded cells never kill |
| fortune_v | Rare | tool | Fortune V | – | tool: Fortune |
| prospector | Rare | tool | ore HUD | – | tool: ore HUD |
| trade | Rare | weapon | 2/4/6%: swaps held items (players only) | +0.5 | players only |
| bold | Epic | tool | doubles vanilla Fortune | – | tool: doubles Fortune |
| crushingblow | Epic | weapon | sneaking, 10 s cooldown: x1.6/2.2/2.8 | +0.8 | needs the wielder sneaking |
| fortune_x | Epic | tool | Fortune X | – | tool: Fortune |
| getoffme | Epic | weapon | right-click held, 10 min cooldown: launch | +1.9 | needs right-click held |
| haste | Epic | tool | Haste I-III | – | tool: dig speed |
| lich | Epic | weapon | Absorption I-III for 20/25/30 s on kill | +0.1 | absorption on kill; banded cells never kill |
| mending | Epic | any | 2 durability per XP | +0.1 | durability from XP |
| reach | Epic | weapon | +1 block range per level | +0.3 | range; the probe stands in range |
| transmuter | Epic | tool | 3/6/9%: a second ore on ore break | – | tool: bonus ore |
| tunneler | Epic | tool | 3x3 / 5x5 / 7x7 mining | – | tool: area mining |
| demonforged | Legendary | any | unbreakable | +0.3 | unbreakable |
| jammer | Legendary | weapon | players: downsamples their screen | +1.8 | players only (screen effect) |
| multistrike | Legendary | any | every proc enchantment on the item rolls twice | +0.2 | not a combat enchantment |
| soulbound | Legendary | any | kept through death | +0.8 | survives death |

## Pairs

All pairs of the author's 14-enchantment set on one boss per damage model (T1 Naga, T2 lordoftorment, T3 Mantis, T4 Mobzilla). **Synergy** = expected TTK under independence ÷ the pair's TTK, minus one; independence multiplies (two +30% enchantments are +51% together). Each single's ratio is the mean of its replicate runs; the band is two sd of both replicate spreads plus the control noise. A pair is **called** when significant on at least two bosses with the same sign; one boss is *probable*. Lord of Torment's controls are biased, so no call should rest on it alone.

| Pair | Mean speed-up | Naga | lordoftorment | Mantis | Mobzilla | Call |
|---|---:|---:|---:|---:|---:|---|
| blind + colossus | +41 | **+26** (±16) | **+108** (±36) | -0 (±6) | +3 (±14) | **synergy** |
| assassinate + blind | +47 | +5 (±13) | **+92** (±18) | **-2** (±2) | **+40** (±6) | **boss-dependent** |
| excalibur + rage | +33 | **-57** (±9) | +2 (±24) | **-43** (±14) | +0 (±2) | **anti-synergy** |
| colossus + rupture | +46 | **+41** (±15) | +15 (±40) | **+7** (±6) | **+33** (±16) | **synergy** |
| colossus + venomous | +49 | **+46** (±13) | **+57** (±40) | +5 (±6) | **-14** (±14) | **boss-dependent** |
| rage + roulette | +46 | **+22** (±12) | +18 (±21) | **+42** (±26) | +6 (±24) | **synergy** |
| poisonous + venomous | +24 | **-13** (±12) | -17 (±22) | **-8** (±3) | **-41** (±7) | **anti-synergy** |
| roulette + rupture | +39 | +3 (±14) | -13 (±22) | +13 (±22) | **+57** (±26) | **probable synergy (one boss)** |
| blind + roulette | +33 | +4 (±15) | **+34** (±13) | +9 (±22) | +1 (±25) | **probable synergy (one boss)** |
| colossus + poisonous | +40 | **+27** (±15) | +27 (±37) | +3 (±6) | -9 (±14) | **probable synergy (one boss)** |
| colossus + momentum | +37 | -9 (±13) | **+67** (±37) | **-9** (±6) | -8 (±13) | **boss-dependent** |
| assassinate + rage | +38 | +6 (±9) | +12 (±25) | **+21** (±14) | +1 (±3) | **probable synergy (one boss)** |
| assassinate + rupture | +43 | +5 (±11) | +15 (±25) | -0 (±2) | **+16** (±10) | **probable synergy (one boss)** |
| excalibur + momentum | +45 | **-18** (±10) | -1 (±20) | **-13** (±2) | -0 (±2) | **anti-synergy** |
| colossus + excalibur | +51 | **-21** (±13) | **+54** (±38) | **-9** (±6) | +7 (±13) | **boss-dependent** |
| rupture + venomous | +36 | **-12** (±11) | +13 (±27) | **-3** (±3) | **-29** (±11) | **anti-synergy** |
| berserk + roulette | +21 | -7 (±12) | -1 (±23) | +14 (±22) | +24 (±24) | independent |
| assassinate + poisonous | +41 | +10 (±12) | +6 (±20) | +0 (±2) | **+14** (±6) | **probable synergy (one boss)** |
| blind + rupture | +34 | -2 (±14) | **+22** (±20) | -1 (±2) | **+12** (±11) | **synergy** |
| executioner + venomous | +34 | -9 (±10) | +6 (±28) | -0 (±3) | **-25** (±5) | **probable anti-synergy (one boss)** |
| assassinate + riposte | +34 | +3 (±9) | +17 (±21) | +0 (±2) | **+8** (±3) | **probable synergy (one boss)** |
| berserk + cultist | +23 | -2 (±15) | +20 (±23) | +10 (±11) | -3 (±4) | independent |
| berserk + colossus | +22 | -5 (±13) | +36 (±40) | -0 (±6) | -5 (±13) | independent |
| cultist + riposte | +32 | +4 (±15) | +7 (±16) | +8 (±11) | **+6** (±4) | **probable synergy (one boss)** |
| colossus + cultist | +37 | -4 (±17) | +21 (±36) | +4 (±12) | +3 (±13) | independent |
| riposte + venomous | +31 | -1 (±9) | +2 (±23) | -1 (±3) | **-24** (±5) | **probable anti-synergy (one boss)** |
| rage + venomous | +48 | -7 (±9) | +16 (±26) | +13 (±14) | +0 (±5) | independent |
| rage + rupture | +45 | **-20** (±11) | +23 (±26) | **+18** (±14) | +2 (±10) | **boss-dependent** |
| executioner + poisonous | +29 | -6 (±13) | +2 (±24) | +1 (±2) | **-19** (±5) | **probable anti-synergy (one boss)** |
| colossus + roulette | +25 | **-25** (±15) | +18 (±37) | +6 (±23) | -22 (±27) | **probable anti-synergy (one boss)** |
| cultist + rupture | +38 | -5 (±16) | -3 (±21) | **+12** (±11) | **+16** (±10) | **synergy** |
| assassinate + excalibur | +47 | +4 (±9) | +18 (±23) | **-7** (±2) | **+5** (±3) | **boss-dependent** |
| colossus + executioner | +34 | **-18** (±14) | **+49** (±41) | **-10** (±6) | -0 (±13) | **boss-dependent** |
| blind + rage | +29 | -9 (±13) | +9 (±20) | **-22** (±14) | +2 (±5) | **probable anti-synergy (one boss)** |
| colossus + riposte | +30 | +5 (±13) | +18 (±37) | +1 (±6) | -4 (±13) | independent |
| assassinate + momentum | +41 | +5 (±9) | +10 (±21) | +0 (±2) | +3 (±3) | independent |
| berserk + rage | +26 | **-18** (±9) | +19 (±27) | **+17** (±14) | -0 (±2) | **boss-dependent** |
| momentum + rage | +39 | **-25** (±9) | +5 (±22) | +3 (±14) | +0 (±2) | **probable anti-synergy (one boss)** |
| poisonous + rage | +37 | **-23** (±12) | +4 (±22) | +6 (±14) | -4 (±5) | **probable anti-synergy (one boss)** |
| assassinate + berserk | +24 | -4 (±10) | +22 (±26) | +0 (±2) | -1 (±3) | independent |
| cultist + poisonous | +34 | -9 (±17) | +1 (±16) | -4 (±11) | **+29** (±6) | **probable synergy (one boss)** |
| berserk + rupture | +24 | -4 (±12) | +20 (±27) | +0 (±2) | +1 (±10) | independent |
| poisonous + roulette | +34 | +10 (±14) | -10 (±16) | +9 (±22) | +7 (±25) | independent |
| executioner + rage | +35 | **-15** (±10) | +12 (±28) | -13 (±14) | -0 (±2) | **probable anti-synergy (one boss)** |
| assassinate + cultist | +37 | +7 (±15) | +5 (±19) | +0 (±11) | +4 (±5) | independent |
| rage + riposte | +30 | **-33** (±9) | +20 (±22) | -2 (±14) | -0 (±2) | **probable anti-synergy (one boss)** |
| poisonous + rupture | +33 | -8 (±14) | +14 (±22) | -0 (±2) | **-20** (±11) | **probable anti-synergy (one boss)** |
| assassinate + colossus | +37 | -7 (±13) | +29 (±39) | -4 (±6) | -5 (±13) | independent |
| momentum + poisonous | +36 | +5 (±12) | -5 (±18) | +1 (±2) | **-14** (±5) | **probable anti-synergy (one boss)** |
| excalibur + rupture | +52 | -5 (±12) | +22 (±24) | +0 (±2) | -5 (±10) | independent |
| cultist + rage | +38 | +2 (±14) | -7 (±21) | +11 (±18) | **+7** (±4) | **probable synergy (one boss)** |
| executioner + rupture | +37 | -8 (±12) | +11 (±28) | +0 (±2) | +9 (±10) | independent |
| blind + venomous | +35 | -10 (±13) | **+21** (±20) | +1 (±3) | +1 (±7) | **probable synergy (one boss)** |
| cultist + excalibur | +44 | -2 (±15) | -9 (±18) | +1 (±11) | -2 (±4) | independent |
| riposte + rupture | +33 | -9 (±11) | +14 (±23) | +0 (±2) | +7 (±10) | independent |
| blind + executioner | +24 | -13 (±13) | +5 (±22) | +0 (±2) | -4 (±5) | independent |
| blind + excalibur | +44 | -4 (±13) | +16 (±17) | -2 (±2) | +2 (±5) | independent |
| berserk + venomous | +24 | -7 (±10) | +11 (±28) | -1 (±3) | **-15** (±5) | **probable anti-synergy (one boss)** |
| momentum + roulette | +36 | +10 (±12) | +10 (±17) | -4 (±22) | -4 (±24) | independent |
| riposte + roulette | +23 | -3 (±12) | -3 (±17) | -2 (±22) | -3 (±24) | independent |
| blind + momentum | +33 | -2 (±13) | +12 (±15) | -0 (±2) | +0 (±5) | independent |
| berserk + poisonous | +17 | -10 (±13) | +10 (±24) | -1 (±2) | **-9** (±5) | **probable anti-synergy (one boss)** |
| cultist + venomous | +39 | +12 (±15) | -18 (±21) | -1 (±11) | **+16** (±6) | **probable synergy (one boss)** |
| executioner + riposte | +29 | -9 (±10) | +19 (±25) | -0 (±2) | +0 (±2) | independent |
| blind + cultist | +25 | -14 (±17) | **-13** (±12) | +4 (±11) | **+14** (±6) | **boss-dependent** |
| excalibur + riposte | +41 | **-15** (±9) | +13 (±20) | **-6** (±2) | +0 (±2) | **anti-synergy** |
| berserk + executioner | +19 | -8 (±10) | +16 (±29) | +0 (±2) | -0 (±2) | independent |
| assassinate + roulette | +35 | +5 (±12) | +3 (±20) | -1 (±22) | +0 (±24) | independent |
| excalibur + roulette | +43 | -1 (±12) | -16 (±19) | +7 (±22) | +3 (±24) | independent |
| assassinate + executioner | +31 | -1 (±10) | -9 (±27) | -1 (±2) | **+5** (±3) | **probable synergy (one boss)** |
| colossus + rage | +38 | **-24** (±13) | +34 (±40) | +3 (±15) | -6 (±13) | **probable anti-synergy (one boss)** |
| blind + poisonous | +26 | -1 (±15) | -2 (±14) | +1 (±2) | -4 (±7) | independent |
| berserk + momentum | +24 | -5 (±10) | +11 (±24) | +0 (±2) | -0 (±2) | independent |
| cultist + executioner | +32 | -6 (±15) | -1 (±24) | -2 (±11) | +3 (±4) | independent |
| momentum + riposte | +30 | -6 (±9) | +2 (±18) | -2 (±2) | -0 (±2) | independent |
| poisonous + riposte | +29 | -3 (±12) | **+20** (±17) | +1 (±2) | **-12** (±5) | **boss-dependent** |
| blind + riposte | +22 | -6 (±13) | +10 (±15) | +0 (±2) | +1 (±5) | independent |
| assassinate + venomous | +43 | +0 (±9) | +5 (±25) | -0 (±3) | -1 (±6) | independent |
| executioner + momentum | +37 | -7 (±10) | +4 (±25) | -0 (±2) | -0 (±2) | independent |
| excalibur + poisonous | +48 | +2 (±13) | -0 (±20) | +1 (±2) | **-6** (±5) | **probable anti-synergy (one boss)** |
| momentum + rupture | +41 | -5 (±11) | +8 (±23) | +0 (±2) | -1 (±10) | independent |
| excalibur + venomous | +54 | -3 (±10) | +6 (±24) | +1 (±3) | **-7** (±5) | **probable anti-synergy (one boss)** |
| momentum + venomous | +44 | -9 (±9) | +4 (±23) | -1 (±3) | +4 (±5) | independent |
| cultist + momentum | +36 | -0 (±15) | -0 (±16) | +2 (±11) | **-4** (±4) | **probable anti-synergy (one boss)** |
| excalibur + executioner | +46 | -8 (±10) | +12 (±26) | **-6** (±2) | +0 (±2) | **probable anti-synergy (one boss)** |
| berserk + blind | +11 | -10 (±13) | +9 (±22) | +1 (±2) | +2 (±5) | independent |
| cultist + roulette | +30 | **+19** (±16) | **-19** (±15) | +2 (±24) | -4 (±24) | **boss-dependent** |
| berserk + excalibur | +35 | **-11** (±10) | +11 (±25) | -1 (±2) | +0 (±2) | **probable anti-synergy (one boss)** |
| roulette + venomous | +37 | -0 (±12) | -14 (±22) | +6 (±22) | +9 (±25) | independent |
| berserk + riposte | +11 | **-12** (±10) | +11 (±24) | +0 (±2) | -0 (±2) | **probable anti-synergy (one boss)** |
| executioner + roulette | +30 | -2 (±12) | -19 (±24) | +5 (±22) | +16 (±24) | independent |

## Curated stacks

| Stack | Trusted mean | T4 capped | Wielder at 50% / 25% health |
|---|---:|---:|---|
| arc:3 + rupture:3 + feast:3 | +20.7 (22) | +42.2 | Mantis +11 / +11; Mobzilla +38 / +42; Naga +18 / +23; lordoftorment +14 / +21 |
| cultist:3 + berserk:3 + riposte:3 | +33.7 (22) | +22.0 | Mantis +52 / +55; Mobzilla +45 / +48; Naga +62 / +62; lordoftorment +61 / +69 |
| excalibur:1 + multistrike:1 | +43.6 (22) | +0.5 | Mantis +58 / +58; Mobzilla +1 / +0; Naga +59 / +60; lordoftorment +14 / +31 |
| momentum:3 + assassinate:3 + rage:3 | +52.8 (22) | +3.7 | Mantis +71 / +74; Mobzilla +3 / +11; Naga +79 / +77; lordoftorment +41 / +44 |
| multistrike:1 + colossus:3 + executioner:3 | +46.7 (22) | +48.7 | Mantis +32 / +36; Mobzilla +36 / +36; Naga +58 / +56; lordoftorment +50 / +36 |
| multistrike:1 + rupture:3 + accelerant:3 | +23.2 (22) | +46.8 | Mantis +11 / +11; Mobzilla +48 / +47; Naga +22 / +21; lordoftorment +26 / +21 |
| venomous:3 + poisonous:3 + accelerant:3 | +17.2 (22) | +50.9 | Mantis +12 / +12; Mobzilla +48 / +52; Naga +20 / +17; lordoftorment +16 / +20 |

## Data notes

- Degenerate cells excluded (pin did not hold / removed alive): T2-witchery.lordoftorment-levels (21), T2-witchery.lordoftorment-singles (12).
- `cleansing:3` threw an exception on Basilisk, DeathReaper, Emperor Scorpion, Kitsune, Polaris: those cells measure nothing (note text in the TSV).
- Jobs read: 48. Deep bosses (levels, pairs, wounded): Naga, lordoftorment, Mantis, Mobzilla.
- Rahovart appears under T3 and T4 with identical numbers (25/hit cap); the T3 job is the one shown.

## Appendix: speed-up by boss

Top level, melee, singles job. Bold = beyond that boss's threshold. ✗ = excluded from every mean; ⚠ = shown, not averaged.

#### T1

| Enchant | Knight Phantom ±9 | Twilight Lich ±9 | Minoshroom ±8 | Yeti Boss ±8 | Naga ±10 | Tower Boss ±8 | Snow Queen ±9 |
|---|---:|---:|---:|---:|---:|---:|---:|
| excalibur | **+59** | **+62** | **+61** | **+25** | **+58** | **+63** | **+59** |
| rage | **+37** | **+42** | **+56** | **+58** | **+55** | **+50** | **+57** |
| momentum | **+33** | **+34** | **+33** | **+36** | **+31** | **+59** | **+33** |
| rupture | **+36** | **+31** | **+21** | **+22** | **+19** | **+27** | **+17** |
| colossus | **+14** | **+26** | **+18** | **+30** | **+28** | **+28** | **+39** |
| roulette | **+27** | **+23** | **+13** | **+26** | **+20** | **+19** | **+26** |
| executioner | **+23** | **+24** | **+13** | **+24** | **+22** | **+11** | **+28** |
| assassinate | **+42** | **+42** | +3 | **+9** | **+39** | **+39** | +4 |
| venomous | **+33** | +4 | **+18** | **+26** | **+24** | **+17** | **+20** |
| cultist | **+13** | **+20** | **+19** | **+24** | **+12** | **+17** | **+24** |
| poisonous | **+25** | -2 | **+25** | **+23** | **+12** | **+14** | **+16** |
| blind | **+16** | +8 | **+11** | **+22** | **+19** | **+17** | **+12** |
| riposte | **+20** | **+9** | **+18** | **+21** | **+19** | -2 | +6 |
| berserk | +0 | +1 | **+9** | +4 | +7 | +5 | -2 |
| killingblow | +1 | +8 | +3 | +5 | +2 | -4 | +0 |
| cripple | +6 | +3 | -4 | +7 | -1 | -6 | -2 |
| necromancer | +1 | +0 | +3 | +5 | +5 | -7 | +5 |
| accelerant | **+12** | **+10** | -1 | -0 | -5 | -4 | -0 |
| sunder | -5 | **+13** | -5 | +5 | +2 | -1 | +5 |
| frostbite | -1 | +5 | +4 | **+14** | -5 | -7 | -2 |
| suplex | +2 | +3 | +2 | +7 | -7 | -3 | +5 |
| alpha | +7 | +6 | -0 | +2 | -10 | +3 | +6 |
| arc | +1 | **+10** | +4 | **+9** | +8 | -8 | +7 |
| bastion | -4 | +6 | **+9** | +5 | -4 | -3 | **+12** |
| decapitate | +1 | +0 | -0 | +6 | -7 | +4 | +4 |
| ecofriendly | – | – | – | – | – | – | – |
| magnetize | – | – | – | – | – | – | – |
| rally | -0 | +2 | +5 | +0 | -0 | -3 | -2 |
| sieve | – | – | – | – | – | – | – |
| tracker | -4 | +8 | **-9** | -2 | +1 | -7 | +3 |
| bountiful | – | – | – | – | – | – | – |
| daze | -1 | -1 | -1 | +0 | -2 | -7 | +9 |
| disarm | +0 | +4 | +6 | +6 | +4 | +1 | +4 |
| excavate | – | – | – | – | – | – | – |
| oldreliable | – | – | – | – | – | – | – |
| timber | +2 | -2 | +3 | +1 | +7 | -6 | +9 |
| torchlight | – | – | – | – | – | – | – |
| feast | +3 | +5 | -7 | +4 | +1 | -1 | +0 |
| fortune_v | – | – | – | – | – | – | – |
| prospector | – | – | – | – | – | – | – |
| trade | +7 | +3 | -3 | **+9** | +8 | +2 | +5 |
| bold | – | – | – | – | – | – | – |
| crushingblow | +5 | +8 | +3 | +7 | +4 | -3 | -0 |
| fortune_x | – | – | – | – | – | – | – |
| getoffme | +1 | **+10** | +1 | +3 | -1 | +1 | **+13** |
| haste | – | – | – | – | – | – | – |
| lich | -4 | +3 | -0 | **+9** | +1 | **-10** | -6 |
| mending | +2 | +3 | +4 | +5 | +4 | -1 | -2 |
| reach | +2 | +2 | -2 | **+10** | +4 | -1 | +2 |
| transmuter | – | – | – | – | – | – | – |
| tunneler | – | – | – | – | – | – | – |
| demonforged | +1 | -1 | +3 | +5 | -4 | +0 | +1 |
| jammer | +2 | +3 | -1 | **+10** | +9 | -2 | -3 |
| multistrike | +4 | +2 | -0 | +2 | +6 | -5 | **+12** |
| soulbound | +2 | **+9** | +5 | **+8** | +3 | +3 | +3 |

#### T2

| Enchant | Polaris ±9 | Apis ✗ ±47 | DeathReaper ±13 | TimeController ±5 | Enyvil ±12 | WitherBoss ±8 | hornedHuntsman ±12 | EnderDemon ±7 | babayaga ±9 | lordoftorment ⚠ ±18 | leonard ✗ ±34 | monking ±9 | death ±6 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| excalibur | **+18** | **+56** | **+15** | **+21** | **+20** | **+58** | +7 | **+29** | **+10** | **+18** | **+40** | **+57** | **+14** |
| rage | +7 | +46 | **+13** | **+13** | **+15** | **+53** | -5 | **+8** | -0 | +2 | +6 | **+51** | -1 |
| momentum | **+12** | **+63** | **+17** | **+13** | **+14** | **+20** | **+22** | **+50** | **+21** | **+34** | **+53** | **+10** | **+22** |
| rupture | **+47** | **+56** | **+33** | **+42** | +4 | **+27** | **+26** | **+13** | **-32** | +13 | +19 | **+11** | **+18** |
| colossus | +5 | +22 | **+23** | **+19** | **+17** | **+24** | **+14** | **+18** | **+33** | +3 | **+63** | **+41** | **+17** |
| roulette | **+27** | **+54** | **+24** | **+27** | +9 | +7 | **+23** | **+22** | **+10** | **+28** | +17 | **+24** | **+18** |
| executioner | **+26** | +16 | **+20** | **+15** | **+20** | **+17** | **+15** | **+20** | **+15** | -5 | +30 | **+12** | **+19** |
| assassinate | +3 | +42 | +5 | +0 | -5 | -2 | +4 | **+49** | -2 | -4 | +4 | +3 | **+43** |
| venomous | **+45** | +27 | +8 | -1 | -4 | +4 | **+31** | **+22** | -6 | +9 | +33 | **+22** | **-7** |
| cultist | **+19** | +9 | **+17** | **+19** | **+14** | **+12** | **+20** | **+24** | **+24** | **+28** | +16 | **+13** | **+6** |
| poisonous | **+37** | +12 | +4 | -2 | +1 | +3 | **+18** | **+13** | +4 | **+19** | +16 | **+10** | +3 |
| blind | +3 | **+49** | **+14** | +5 | +5 | +1 | +7 | **+16** | +6 | +5 | **+52** | +7 | **+10** |
| riposte | +7 | +46 | -6 | **+8** | -0 | +6 | +8 | **-8** | +6 | +10 | **+56** | +5 | -2 |
| berserk | +5 | +46 | +0 | +3 | +10 | -4 | +7 | +1 | -6 | **-18** | +13 | -6 | **+30** |
| killingblow | +4 | +44 | **+16** | -5 | -4 | +7 | +1 | +4 | +2 | -7 | -6 | +3 | -3 |
| cripple | +2 | -5 | -1 | +2 | +8 | +6 | +6 | +3 | -6 | -16 | +20 | -1 | +3 |
| necromancer | -5 | -16 | -4 | +3 | +5 | +0 | -2 | +3 | +2 | -10 | +29 | -1 | +1 |
| accelerant | -5 | +42 | +9 | -1 | +0 | **-9** | +6 | -5 | -6 | **-18** | **+40** | -2 | **+10** |
| sunder | +1 | +47 | -1 | -1 | -6 | +3 | +3 | +3 | **-11** | -3 | **+43** | +4 | -2 |
| frostbite | -0 | +44 | +0 | -3 | +4 | -5 | +4 | +2 | +1 | -13 | +26 | +2 | **-8** |
| suplex | +1 | +42 | -0 | -0 | -3 | **-14** | -1 | **+8** | +2 | -10 | +29 | **-9** | +5 |
| alpha | +1 | +44 | +3 | -1 | -10 | -4 | -3 | -0 | -5 | -15 | **+43** | -3 | +1 |
| arc | -3 | **+48** | -10 | -2 | -8 | **-9** | -2 | -6 | **-13** | -12 | +29 | -2 | -2 |
| bastion | -6 | +33 | **-93** | **-11** | +2 | -7 | **-77** | +1 | **-120** | -12 | **+43** | **-39** | **-19** |
| decapitate | -0 | -9 | +0 | +0 | -0 | -7 | -3 | +2 | -6 | **-18** | +7 | -2 | **+6** |
| ecofriendly | – | – | – | – | – | – | – | – | – | – | – | – | – |
| magnetize | – | – | – | – | – | – | – | – | – | – | – | – | – |
| rally | +3 | -7 | -12 | +5 | -1 | +2 | +7 | +7 | -3 | **-23** | **+41** | +3 | +4 |
| sieve | – | – | – | – | – | – | – | – | – | – | – | – | – |
| tracker | -0 | +43 | +5 | +1 | +3 | -4 | -2 | +4 | +3 | -10 | **+37** | -8 | +0 |
| bountiful | – | – | – | – | – | – | – | – | – | – | – | – | – |
| daze | +1 | -5 | +1 | -2 | -1 | +0 | +4 | +4 | +2 | -4 | +31 | -2 | **+7** |
| disarm | -1 | -4 | +3 | **-11** | +7 | +5 | +3 | **-8** | +3 | -12 | +11 | -3 | -1 |
| excavate | – | – | – | – | – | – | – | – | – | – | – | – | – |
| oldreliable | – | – | – | – | – | – | – | – | – | – | – | – | – |
| timber | -2 | +46 | +0 | **-6** | +5 | -2 | -6 | +1 | +4 | -8 | **+43** | +5 | +4 |
| torchlight | – | – | – | – | – | – | – | – | – | – | – | – | – |
| feast | +3 | -6 | +5 | **+6** | -1 | +2 | +4 | +5 | -5 | -3 | +12 | -5 | +2 |
| fortune_v | – | – | – | – | – | – | – | – | – | – | – | – | – |
| prospector | – | – | – | – | – | – | – | – | – | – | – | – | – |
| trade | -8 | +25 | **-15** | +2 | -5 | +5 | -3 | **+14** | -7 | -15 | +20 | +0 | -1 |
| bold | – | – | – | – | – | – | – | – | – | – | – | – | – |
| crushingblow | +1 | -1 | -0 | -3 | +6 | -3 | -0 | **+9** | -8 | -15 | -2 | -6 | -2 |
| fortune_x | – | – | – | – | – | – | – | – | – | – | – | – | – |
| getoffme | -5 | +45 | +1 | -1 | +3 | +5 | +5 | +3 | +3 | **-18** | **+40** | -2 | +3 |
| haste | – | – | – | – | – | – | – | – | – | – | – | – | – |
| lich | +2 | +46 | +5 | -3 | +8 | -3 | +3 | +3 | -1 | -14 | +4 | -6 | +1 |
| mending | +7 | **+47** | -1 | -0 | +1 | -5 | +1 | +4 | -7 | -15 | +32 | -7 | **-6** |
| reach | -6 | +1 | -4 | -2 | -0 | -2 | +3 | **+10** | -3 | **-19** | +21 | -1 | -5 |
| transmuter | – | – | – | – | – | – | – | – | – | – | – | – | – |
| tunneler | – | – | – | – | – | – | – | – | – | – | – | – | – |
| demonforged | +2 | -3 | +4 | -1 | +6 | +2 | +0 | +2 | -9 | **-35** | +0 | -4 | -2 |
| jammer | **+9** | +42 | +2 | -1 | +1 | +2 | +6 | +4 | +2 | -13 | **+42** | -3 | -1 |
| multistrike | -2 | -7 | +2 | **-6** | +0 | -4 | -1 | -2 | +5 | -3 | +10 | -5 | -3 |
| soulbound | +3 | +43 | -5 | -3 | -0 | -6 | -1 | +4 | -5 | -7 | +1 | -7 | +3 |

#### T3

| Enchant | Mantis ±2 | Mothra ±2 | Basilisk ±2 | Emperor Scorpion ±2 | The Kraken ±2 | rahovart ±2 |
|---|---:|---:|---:|---:|---:|---:|
| excalibur | **+58** | **+58** | **+58** | **+58** | **+58** | **+14** |
| rage | **+51** | **+42** | **+27** | **+36** | **+37** | +0 |
| momentum | **+19** | **+19** | **+18** | **+18** | **+18** | **+28** |
| rupture | **+11** | **+10** | **+28** | **+46** | **+24** | +1 |
| colossus | **+9** | **+15** | **+15** | **+14** | **+34** | **-2** |
| roulette | **+24** | **+16** | **+12** | **+30** | **+27** | **+6** |
| executioner | **+20** | **+20** | **+21** | **+21** | **+21** | **+20** |
| assassinate | **+43** | **+43** | **+2** | **+2** | **+43** | **+3** |
| venomous | **+12** | **+11** | **+38** | **+56** | **+19** | +2 |
| cultist | **+15** | **+18** | **+14** | **+25** | **+15** | **+23** |
| poisonous | **+7** | **+8** | **+28** | **+37** | **+14** | +2 |
| blind | **+13** | **+11** | **+6** | **+10** | **+11** | **+12** |
| riposte | **+10** | **+9** | **+10** | **+10** | **+5** | +0 |
| berserk | +0 | +0 | +0 | +0 | +0 | +0 |
| killingblow | **+15** | +0 | +0 | +0 | +0 | +0 |
| cripple | +0 | +0 | +0 | +0 | +0 | +0 |
| necromancer | -0 | +0 | +0 | +0 | +0 | +0 |
| accelerant | +0 | +0 | -0 | +0 | +0 | +0 |
| sunder | +0 | +0 | +0 | +0 | +0 | +0 |
| frostbite | +0 | +0 | +0 | -1 | +0 | +0 |
| suplex | +0 | +0 | +0 | +0 | +0 | +0 |
| alpha | +0 | +0 | -0 | +0 | +0 | +0 |
| arc | +0 | +0 | +0 | +0 | +0 | +0 |
| bastion | **-12** | +0 | -0 | **-5** | +0 | +0 |
| decapitate | -0 | +0 | +0 | +0 | +0 | +0 |
| ecofriendly | – | – | – | – | – | – |
| magnetize | – | – | – | – | – | – |
| rally | +0 | +0 | +0 | +0 | +0 | +0 |
| sieve | – | – | – | – | – | – |
| tracker | -0 | +0 | -0 | +0 | +0 | +0 |
| bountiful | – | – | – | – | – | – |
| daze | +0 | +0 | -0 | +0 | +0 | +0 |
| disarm | +0 | +0 | -0 | +0 | +0 | +0 |
| excavate | – | – | – | – | – | – |
| oldreliable | – | – | – | – | – | – |
| timber | +0 | +0 | +0 | +0 | +0 | +0 |
| torchlight | – | – | – | – | – | – |
| feast | +0 | +0 | -0 | +0 | +0 | +0 |
| fortune_v | – | – | – | – | – | – |
| prospector | – | – | – | – | – | – |
| trade | -0 | +0 | +0 | +0 | +0 | +0 |
| bold | – | – | – | – | – | – |
| crushingblow | +0 | +0 | +0 | +0 | +0 | +0 |
| fortune_x | – | – | – | – | – | – |
| getoffme | +0 | +0 | +0 | +0 | +0 | +0 |
| haste | – | – | – | – | – | – |
| lich | +0 | +0 | -0 | +0 | +0 | +0 |
| mending | +0 | +0 | -0 | +0 | +0 | +0 |
| reach | +0 | +0 | +0 | -1 | +0 | +0 |
| transmuter | – | – | – | – | – | – |
| tunneler | – | – | – | – | – | – |
| demonforged | +0 | +0 | -0 | +0 | +0 | +0 |
| jammer | +0 | +0 | +0 | +0 | +0 | +0 |
| multistrike | +0 | +0 | +0 | -1 | +0 | +0 |
| soulbound | +0 | +0 | -0 | +0 | +0 | +0 |

#### T4

| Enchant | Godzilla ±2 | Mobzilla ±2 | The Queen ±2 | The King ±2 |
|---|---:|---:|---:|---:|
| excalibur | **+55** | +1 | +1 | +0 |
| rage | **+51** | -0 | -0 | -0 |
| momentum | +1 | +1 | +1 | +1 |
| rupture | **+8** | **+40** | **+48** | **+46** |
| colossus | **+7** | **+20** | **+32** | **+34** |
| roulette | **+18** | -1 | **+21** | **+28** |
| executioner | **+20** | **+20** | **+20** | **+20** |
| assassinate | **+43** | **+2** | **+2** | **+2** |
| venomous | **+9** | **+47** | **+50** | **+40** |
| cultist | **+16** | **+15** | **+12** | **+28** |
| poisonous | **+6** | **+40** | **+40** | **+42** |
| blind | **+12** | **+8** | **+12** | **+11** |
| riposte | +0 | +1 | +1 | +1 |
| berserk | +0 | -0 | -0 | +0 |
| killingblow | +0 | -0 | -0 | -0 |
| cripple | +0 | +0 | +0 | +0 |
| necromancer | +0 | +0 | +0 | +0 |
| accelerant | +0 | -0 | +0 | -0 |
| sunder | +0 | +0 | -0 | -0 |
| frostbite | +0 | +0 | -0 | -0 |
| suplex | +0 | +0 | +0 | +0 |
| alpha | +0 | +0 | +0 | -0 |
| arc | +0 | -0 | +0 | -0 |
| bastion | +0 | +0 | **-5** | **-6** |
| decapitate | +0 | -0 | +0 | -0 |
| ecofriendly | – | – | – | – |
| magnetize | – | – | – | – |
| rally | +0 | +0 | +0 | +0 |
| sieve | – | – | – | – |
| tracker | +0 | +0 | +0 | +0 |
| bountiful | – | – | – | – |
| daze | +0 | +0 | +0 | +0 |
| disarm | +0 | +0 | +0 | +0 |
| excavate | – | – | – | – |
| oldreliable | – | – | – | – |
| timber | +0 | +0 | +0 | +0 |
| torchlight | – | – | – | – |
| feast | +0 | +0 | +0 | +0 |
| fortune_v | – | – | – | – |
| prospector | – | – | – | – |
| trade | +0 | +0 | +0 | +0 |
| bold | – | – | – | – |
| crushingblow | +0 | -0 | +0 | -0 |
| fortune_x | – | – | – | – |
| getoffme | +0 | -0 | +0 | +0 |
| haste | – | – | – | – |
| lich | +0 | +0 | +0 | -0 |
| mending | +0 | +0 | +0 | -0 |
| reach | +0 | +0 | -0 | +0 |
| transmuter | – | – | – | – |
| tunneler | – | – | – | – |
| demonforged | +0 | +0 | +0 | +0 |
| jammer | +0 | -0 | +0 | +0 |
| multistrike | +0 | +0 | +0 | -0 |
| soulbound | +0 | +0 | +0 | -0 |
