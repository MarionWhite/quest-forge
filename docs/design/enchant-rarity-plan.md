# Enchant rarity plan

**Status:** proposal for the owner. Nothing here is built. Written 2026-10-25 for decision
[0005](../decisions/0005-enchant-census-proposals.md) P10. Every figure comes from
[enchant-effects](../reference/enchant-effects.md) (rerunnable: `py -3.10 -I tools/balance/effects_table.py`).
**Out of scope on purpose:** drop rates, loot sources, loot placement. Rarity here is a label for
how strong the observable effect is, nothing more.

The owner's spec, from P10: every enchantment has "an observable effect proportionate to the
rarity"; "a good looking distribution across rarities (it's fine if we have to come up with some
more ideas for enchants)"; none that "break the game, make hard bosses much easier than they
should be, or otherwise ... up the flow".

## 1. The ruler

The table measures weapons by how much faster a boss dies (trusted mean over 22 uncapped bosses,
top level) and armour by damage cut against each boss's own melee (T1-T2 mean; from T3 the tier
armour already takes nothing). The bands used for the verdicts are a proposal and live at the top
of `effects_table.py`:

| Rarity | Weapon speed-up | Armour damage cut |
|---|---|---|
| Common | under 5 % | under 5 % |
| Uncommon | 5-12 % | 5-10 % |
| Rare | 12-20 % | 10-20 % |
| Epic | 20-30 % | 20-30 % |
| Legendary | 30 % and up | 30 % and up |

Context: the strongest single weapon enchantment measured is Excalibur at +42 %, which takes a
34 s Naga fight to about 14 s. The 20-30 % Epic band is "a quarter shorter", not "trivial".

**Limit of the ruler.** It measures offence and damage taken from melee. It cannot price control
and utility effects (stuns, summons, healing on kill), and the census did not measure what the
*weapon* enchantments that weaken the enemy do to the damage the wielder takes (Cripple, Sunder,
Frostbite, Daze, Suplex). Their "no observable effect" verdict below means "no offensive effect".
Until a survivability cell exists for them (section 6), do not demote or delete them on this
table alone.

## 2. Distribution today

81 registered enchantments, declared rarity (after the four P9 moves):

| Rarity | Weapon | Armour | Bow | Tool | Any | Total |
|---|---:|---:|---:|---:|---:|---:|
| Common | 3 | 2 | 0 | 3 | 0 | 8 |
| Uncommon | 5 | 2 | 0 | 5 | 0 | 12 |
| Rare | 15 | 7 | 4 | 2 | 0 | 28 |
| Epic | 10 | 5 | 2 | 5 | 1 | 23 |
| Legendary | 3 | 3 | 1 | 0 | 3 | 10 |

The shape is top-heavy: 41 % Epic or Legendary, 10 % Common, 28 Rares in the middle. Only 31 of
the 81 have a combat effect the census could rank; 50 are tools, utility or PvP-only. Of the 31:

| Verdict | Count | Which |
|---|---:|---|
| proportionate | 12 | Assassinate, Berserk, Bulwark, Colossus, Cultist, Excalibur, Executioner, Momentum, Rage, Riposte, Tank, Turtle |
| too strong for rarity | 5 | Poisonous, Roulette, Rupture, Venomous, Piercing |
| too weak | 2 | Blind, Cockroach |
| no offensive effect | 10 | Accelerant, Affliction, Alpha, Arc, Cripple, Frostbite, Killing Blow, Necromancer, Sunder, Suplex |
| harmful | 2 | Bastion, Homing |

Where the measured effect falls, by declared rarity (combat enchantments only):

| Declared \ measured | Common | Uncommon | Rare | Epic | Legendary | Negative |
|---|---:|---:|---:|---:|---:|---:|
| Uncommon | 1 | 1 | 1 | 0 | 0 | 0 |
| Rare | 6 | 1 | 5 | 2 | 1 | 0 |
| Epic | 2 | 0 | 1 | 4 | 0 | 1 |
| Legendary | 1 | 1 | 0 | 0 | 3 | 0 |

Only 5 of 15 Rares measure as Rare; six read as Common. The Rare tier is where the dead
enchantments live.

## 3. Mispriced, and what to do

Held until the re-test: Rupture, Venomous and Poisonous, because P1/P2 change how much damage they
seed (the table is from before those changes; the re-test is `ops/checkpoints/balance-retest.md`).
Their problem is T4 only: +14 to +22 % on ordinary bosses (Rare-sized) but +44 to +46 % on the
750-capped T4 bosses, where DoT damage bypasses the cap. Proposal: leave rarity alone and judge
the T4 numbers after the re-test.

| Enchant | Now | Measured | Proposal | Why |
|---|---|---:|---|---|
| Blind | Rare | +10.5 | Uncommon | Sits in the Uncommon band; or keep Rare and lift the 24 % proc |
| Cockroach | Epic | +10.3 (T1 +23, T2 +4) | Rare, or make it stronger | A once-per-60 s save is Rare-sized; does nothing from T3 where tier armour takes no damage anyway |
| Piercing (bow) | Rare | +31 | Epic | Consistent, the only strong bow enchantment; the bow instrument is noisy, so re-measure before moving |
| Poisonous | Uncommon | +13.6 | Rare | Measures as a Rare; hold for the P1 re-test |
| Roulette | Rare | +20.6 | leave | Top of Rare, inside the noise (replicate sd up to 12); P9 already moved it |
| Homing | Legendary | +6, arrows stop landing on 4 bosses | fix, then re-price | A defect (arrows steer off the target), not a price |
| Bastion | Epic | -16.6, loses fights on 8 bosses | P8 is the fix; re-measure | P8 stops golems stealing aggro; price it after the re-test |

The twelve "proportionate" ones stay, including Rage (Legendary) and Tank (Epic) as moved by P9.

## 4. No offensive effect: what they could become

Each is a design question for the owner, not a bug. "Could become" keeps the idea and gives it a
number the table can later check.

| Enchant | Why dead | Could become |
|---|---|---|
| Accelerant (Rare) | Amplifies debuffs the target already has; few bosses carry any | Your poisons and bleeds tick 25/50/75 % faster. A support piece for Rupture/Venomous. Needs the P1 re-test first |
| Affliction (Legendary armour) | 1-4 % per piece to put seven debuffs on the attacker; rarely fires | Deterministic: when hit, the attacker gets Weakness for 3 s, 5 s cooldown. Measurable as damage cut |
| Alpha (Rare) | 9 % to summon a wolf; the wolf is not a measurable share of the damage | Rarer, stronger, longer wolf that also gives you +20 % damage while it lives |
| Arc (Epic) | 35 % of the hit to up to 3 others; the census fights one boss | Right for mob packs. Keep, drop to Rare, measure in a spawner room |
| Cripple, Sunder (Rare, Uncommon) | Target deals 10-20 % less; measured on speed only | Measure survivability first (section 6); possibly already correct |
| Frostbite (Rare) | Brief Slowness; bosses are pinned or ignore it | Third hit in a row roots for 1 s. Or fold into a "control" family |
| Killing Blow (Epic) | 0.1-0.3 % to set health to 0; bosses immune by design (good) | Keep as a mob-pack thrill at Rare. Never let it touch boss health |
| Necromancer (Rare) | As Alpha | As Alpha: the minion needs a number the fight can feel |
| Suplex (Rare) | Fall damage is small and bosses fly | 1 s stun on landing; a mob tool |

## 5. Fifteen new ideas

All 1.7.10-feasible (events, potions, and the existing summon and dispatch hooks). Targets are the
band the table should measure, so each can be checked the day it is built. None touches drop rates.

| # | Name | Slot | Rarity | Mechanism | Target |
|---|---|---|---|---|---|
| 1 | Leech | weapon | Uncommon | Heal 3/6/9 % of damage dealt | survivability 5-10 % |
| 2 | Hunter's Mark | weapon | Rare | First hit marks the target for 10 s: everyone, you included, deals +8/12/16 % to it. A group enchant for the friends' server | +12-20 % per mark holder |
| 3 | Slayer | weapon | Epic | Each kill within 20 s adds +4 % damage, 5 stacks. Mob content; nothing on a lone boss | mobs +20-30 % |
| 4 | Parry | weapon | Rare | Blocking with the sword cuts the hit 25/40/55 % | DR 10-20 % while blocking |
| 5 | Brace | chest | Uncommon | Standing still 1 s: 4/7/10 % less damage | DR 5-10 % |
| 6 | Evasion | boots | Rare | 6/12/18 % to dodge a hit, 2 s cooldown | DR 10-20 % |
| 7 | Siphon | chest | Epic | When hit, heal 0.5/1/1.5 hearts, 5 s cooldown | survivability 20-30 % |
| 8 | Guardian | chest | Rare | Allies within 8 blocks take 10/15/20 % less while you stand. Group only | team DR 10-20 % |
| 9 | Second Wind | chest | Epic | Once per 5 min, below 2 hearts heal 6/9/12 hearts. A stronger Cockroach | one save per fight |
| 10 | Ward | helmet | Legendary | Negates the first hit of every fight (60 s reset) | strong vs one-shots, flat after |
| 11 | Sniper | bow | Epic | +4 % damage per block of range, to +40 % | bow +20-30 % at range |
| 12 | Volley | bow | Rare | 15/25/35 % to loose a second arrow | bow +12-20 % |
| 13 | Shatter | weapon | Rare | Ignore 15/25/35 % of the target's armour. Check first whether boss armour matters in this pack | unmeasured |
| 14 | Wrath | weapon | Epic | Each hit you take adds 4 % to your next blow, 5 stacks. Rewards risk, the opposite of Momentum's rhythm | +20-30 % at low health |
| 15 | Brand | any | Legendary | Your DoT enchantments also slow the target 15 % while they tick. Needs the P1 re-test | support |

Rough target shape for combat enchantments if the section 3 and 4 moves and the new ideas land:
Common 7, Uncommon 10, Rare 15, Epic 11, Legendary 6.

Guardrails against "breaking the game": every number above is bounded (stack caps, cooldowns, a
once-per-fight ceiling). Strength-based enchantments already dilute each other (Excalibur + Rage
is -57 points on Naga because they share Strength I), and flat adds shrink under Strength, so a
stack of one Epic and one Legendary lands near +50 %. That is why Epics must stay under 30.

## 6. What to measure before any of this is decided

1. Survivability of the weapon debuffs (Cripple, Sunder, Frostbite, Daze, Suplex, Alpha,
   Necromancer, Bastion): damage taken over a fixed 60 s fight, enchanted versus control. The only
   way to settle the "no offensive effect" ten.
2. The re-test after P1, P2, P4, P7, P8 (queued), with the table rebuilt by rerunning the script
   on the re-test jobs.
3. A better bow instrument: the bow noise runs to ±100 %, so Piercing and Homing need a longer
   window before they are re-priced.

## 7. For the owner

- Accept the bands in section 1 as the definition of "proportionate to rarity"?
- Which section 4 redesigns do you want built, which cut?
- Which section 5 ideas to prototype? Suggested first: Leech, Hunter's Mark, Parry, Brace,
  Evasion, Siphon. They fill the Uncommon and Rare gaps without touching boss bands.
