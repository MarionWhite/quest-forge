# Enchantment ground truth

Every number here was read out of the source on 2026-09-07 and is cited to the
file and line it came from. Nothing in this file is derived, simulated or
remembered.

It exists because `ENCHANT-TUNING.md` is a mixture of two very different kinds of
claim — descriptions of what the code does, and conclusions from a simulation —
and the second kind is not currently trusted. This file is only the first kind.

**How to use it:** if a number here disagrees with `ENCHANT-TUNING.md`, this file
wins, because it has a line number. If it disagrees with the game, the game wins
and this file is wrong.

Status: weapons, armour and the framework are fully transcribed. Bows, tools and
the client enchantments have their headline constants only — marked *partial*.

---

## Framework

| Fact | Value | Source |
|---|---|---|
| Rarity success roll | COMMON 75–90, UNCOMMON 65–80, RARE 50–70, EPIC 35–55, LEGENDARY 20–40 | `Rarity.java:14-18` |
| Rarity destroy roll | COMMON 0–5, UNCOMMON 5–12, RARE 12–22, EPIC 22–35, LEGENDARY 35–50 | `Rarity.java:14-18` |
| Default proc chance | 100% | `QFEnchantment.java:89-91` |
| Dispatch order | FLAT → MULTIPLIER → PROC, stable sort | `EnchantDispatcher.java:76`, `QFEnchantment.java:101` |
| Multi Strike | 2 passes for anything with `isMultipliable()`, never on TICK | `EnchantDispatcher.java:82-83` |
| Proc roll | `rand.nextInt(100) >= chance` → skip; re-rolled per pass | `EnchantDispatcher.java:90` |

Two vanilla facts the balance rests on, both verified against decompiled source
and then **confirmed by measurement** in the control census:

- Player base attack damage is **1.0**; a weapon adds an operation-0 attribute
  modifier on top. A diamond sword's modifier is `4.0F + material damage` = 7.0,
  so it swings for **8.0**, not 7. (`EntityPlayer.java:181`, `ItemSword.java:28`;
  measured 8.0, landing 7.36 on a 2-armour zombie = 8 × (25−2)/25.)
- Mob damage to a player is **difficulty-scaled**: Easy `amount/2 + 1`, Normal
  unchanged, Hard `amount × 3/2` (`EntityPlayer.java` `attackEntityFrom`).
  Measured: zombie deals 3.0 on Normal, 2.5 on Easy. **The pack runs Normal**
  (`options.txt` `difficulty:2`).

---

## Two places ENCHANT-TUNING.md is wrong

These are not judgement calls, they are arithmetic:

| Enchant | ENCHANT-TUNING.md says | Code does | Source |
|---|---|---|---|
| **Sunder** | cuts damage 8 / 16 / 24% | `0.05F * level` = **5 / 10 / 15%** | `WeaponEnchants2.java:217` |
| **Cripple** | cuts damage 20 / 30 / 40% | `0.05F * (level+1)` = **10 / 15 / 20%** | `WeaponEnchants2.java:279` |

In both cases the code's own inline comment agrees with the code, so the doc rows
are stale rather than the code being wrong. Durations in both rows are correct.

---

## Weapons

Proc chance is per hit. "Mult" = counted by Multi Strike.

| Enchant | Rarity | Lvl | Proc | Effect | Phase | Mult | Source |
|---|---|---|---|---|---|---|---|
| Colossus | EPIC | 3 | `3+3L` = 6/9/12% | `+0.025 × L × target maxHealth`, capped at `max(20, hit × 4)` | PROC | yes | `CombatEnchants.java:26,34,47-55` |
| Feast | RARE | 3 | on kill | heal `2.0 × L` | PROC | yes | `CombatEnchants.java:67` |
| Poisonous | UNCOMMON | 3 | `10L` = 10/20/30% | Poison I for `60+20L` ticks (4/5/6 s); venom `max(1.0, hit × 0.04 × L)` per second | PROC | yes | `CombatEnchants.java:82,90,98-105` |
| Venomous | RARE | 3 | `8L` = 8/16/24% | Poison **II** for `100+40L` ticks (7/9/11 s); venom `max(1.0, hit × 0.058 × L)`/s; cripple 10% for 80 ticks | PROC | yes | `CombatEnchants.java:118,122,129-139` |
| Blind | RARE | 3 | `8L` | Blindness `60+20L` ticks (4/5/6 s) | PROC | yes | `CombatEnchants.java:157,164` |
| Suplex | RARE | 3 | `5+5L` = 10/15/20% | `motionY += 0.7 + 0.15L` (0.85/1.00/1.15) | PROC | yes | `CombatEnchants.java:176,182` |
| Daze | UNCOMMON | 3 | `10L` | target yaw +180° | PROC | yes | `CombatEnchants.java:195,202` |
| Roulette | UNCOMMON | 1 | always | `×2.0` or `×0.5`, even odds (EV ×1.25) | MULTIPLIER | **no** | `CombatEnchants.java:227,232,237` |
| Cultist | RARE | 3 | `8L` = 8/16/24% | `×2.0` damage; self-damage `min(hit × 0.75, maxHealth × 0.10 × L)`, never below 1 HP, via custom physical source `qf.cultist` | MULTIPLIER | **no** | `CombatEnchants.java:249,253,271,285-297` |
| Killing Blow | EPIC | 3 | `nextInt(1000) < L` = 0.1/0.2/0.3% | `setHealth(0)`, then floors the hit at 1.0 so `onDeath(source)` still credits the player | PROC | yes | `CombatEnchants.java:322-325` |
| Momentum | UNCOMMON | 3 | always | `+0.5 × L × (stacks−1)`, 8 stacks max, 40-tick window → +3.5/7.0/10.5 | FLAT | **no** | `CombatEnchants.java:331-332,353` |
| Riposte | UNCOMMON | 3 | always, if hurt in 60 ticks | `+1.5 × L` | FLAT | **no** | `CombatEnchants.java:359,379` |
| Rupture | RARE | 3 | `15+10L` = 25/35/45% | bleed `max(0.5, hit × 0.04)` per stack per second, `80+20L` ticks (5/6/7 s), `L+1` stacks, ignores armour | PROC | yes | `WeaponEnchants2.java:38,42-44,54-55` |
| Arc | EPIC | 3 | `10+5L` = 15/20/25% | `hit × 0.35` to up to `L` others within 5 blocks, as indirect magic | PROC | yes | `WeaponEnchants2.java:61,69,82,92-93` |
| Disarm | UNCOMMON | 3 | `4L` = 4/8/12%; players half | drops held item, 20-tick pickup delay | PROC | yes | `WeaponEnchants2.java:115,126,158` |
| Assassinate | RARE | 3 | always, if target is not targeting you | `×(1 + 0.25L)` = 1.25/1.50/1.75 | MULTIPLIER | **no** | `WeaponEnchants2.java:171,176,187-189` |
| **Sunder** | UNCOMMON | 3 | `10L` | cripple **`0.05 × L`** = 5/10/15% + Mining Fatigue, `60+20L` ticks | PROC | yes | `WeaponEnchants2.java:201,213-218` |
| Rage | EPIC | 3 | `5L` = 5/10/15% | Strength **I** for `40+40L` ticks (4/6/8 s) | PROC | yes | `WeaponEnchants2.java:236,245-246` |
| **Cripple** | RARE | 3 | `10L` | cripple **`0.05 × (L+1)`** = 10/15/20%, `80+40L` ticks (6/8/10 s) | PROC | yes | `WeaponEnchants2.java:262,269,278-279` |
| Accelerant | RARE | 3 | flat 12% | every bad effect: amplifier `+L` capped at `2L+1` (IV/VI/VIII), duration `+40L`; **wither capped at 3 (IV)** | PROC | yes | `WeaponEnchants2.java:292,305,315,334,344` |
| Lich | EPIC | 3 | on kill | Absorption `L` for `300+100L` ticks (20/25/30 s) | PROC | yes | `WeaponEnchants2.java:353,363-364` |
| Excalibur | LEGENDARY | 1 | always | `+4.0` flat; while held, Strength I + Resistance I + Speed I refreshed every 40 ticks | FLAT | **no** | `WeaponEnchants2.java:380,388-390,395` |
| Demon Forged | LEGENDARY | 1 | passive | sets vanilla `Unbreakable` | PROC | **no** | `WeaponEnchants2.java:416` |
| Necromancer | RARE | 3 | `3L` = 3/6/9% | zombie or skeleton, `400+200L` ticks (30/40/50 s) | PROC | yes | `WeaponEnchants2.java:431,451,465-467` |
| Alpha | RARE | 3 | `3L` | wolf, tamed to you, same duration | PROC | yes | `WeaponEnchants2.java:431,479-483` |
| Bastion | EPIC | 3 | `3L` | iron golem, player-created, same duration | PROC | yes | `WeaponEnchants2.java:431,496-501` |
| Trade | RARE | 3 | `2L` = 2/4/6% | swaps held slots, players only | PROC | yes | `PvpEnchants.java:77` |
| Crushing Blow | EPIC | 3 | sneaking, 200-tick cooldown | `×(1 + 0.6L)` = 1.6/2.2/2.8 | PROC | **no** | `AbilityEnchants.java:27,35,54` |
| Get Off Me | EPIC | 3 | right-click, **12000-tick (10 min)** cooldown | launch | PROC | **no** | `AbilityEnchants.java:70,78` |
| Rally | COMMON | 1 | opener, 200-tick cooldown | flourish (music still unimplemented) | PROC | **no** | `AbilityEnchants.java:120,123,128` |

---

## Armour

Per-piece enchantments run their hook **once per equipped piece carrying them**,
so the full-set figure is the compounded one.

| Enchant | Rarity | Lvl | Slot | Proc | Effect | Full set | Source |
|---|---|---|---|---|---|---|---|
| Bulwark | RARE | 3 | chestplate | always | `×(1 − 0.10 × L × missingHealthFraction)` | up to 10/20/30% at 0 HP | `ArmorEnchants.java:43,66-67` |
| Cleansing | RARE | 3 | leggings | `10L` | strips one bad effect; suppresses Tank's slowness for 400 ticks | — | `ArmorEnchants.java:85,98-103` |
| Stonehide | UNCOMMON | 3 | **per piece** | always | `×(1 − 0.12 × L / 4)` = 3% per piece per level, falls and explosions only | L3 ×0.91⁴ = **31.4%** | `ArmorEnchants.java:132-135` |
| Rebound | COMMON | 3 | **per piece** | `2L` per piece | knockback `0.75 + 0.25L` with 0.42 lift | 7.8/15.0/**21.7%** per hit | `ArmorEnchants.java:148,158` |
| Reflect | EPIC | 3 | **per piece** | `4+4L` = 8/12/16% per piece | *sets* velocity: 2 blocks back and 1 up per piece worn | 8 blocks / 4 up | `ArmorEnchants.java:172-180,188,198-203` |
| Turtle | LEGENDARY | 1 | **per piece** | while holding no weapon or bow | `×0.67` per piece | ×0.67⁴ = **80%**; floor of 0.5 damage, capped at the un-Turtled hit | `ArmorEnchants.java:215,241-246,264,296-298` |
| Affliction | LEGENDARY | **4** | **per piece** | 0.97/0.73/0.49/0.25% per piece | 7 debuffs at amplifier `L−1`, `100+40L` ticks | 3.8/2.9/1.9/**1.0%** | `ArmorEnchants.java:319,338-349` |
| Flippers | UNCOMMON | 3 | boots | passive | speed `×(1 + 0.96 × min(3,L)/3)`, hard-capped at 0.22 | — | `ArmorEnchants.java:367-369,401-402` |
| Camouflage | RARE | 3 | leggings | `10L` | cancels a mob acquiring you | — | `ArmorEnchants.java:418,423` |
| Sacrifice | RARE | 1 | **per piece** | on lethal damage | survive at 50% health, Regen II + Resist II 200 ticks, Fire Res 400; destroys the piece | 4 saves | `ArmorEnchants.java:448-455` |
| Tank | RARE | 3 | chestplate | always | `×(1 − 0.11 × L)` = 11/22/33%, plus permanent Slowness I | — | `PotionEnchants.java:74,116` |
| Cockroach | EPIC | 3 | chestplate | hit leaving you alive at ≤ 2.0 HP, 1200-tick (60 s) cooldown | Resistance `L+1` capped at amplifier 3, does not blunt the triggering hit | — | `PotionEnchants.java:137,140,143,166-180` |
| Regrowth | RARE | 3 | leggings | 200 ticks out of combat | Regeneration I–III | — | `PotionEnchants.java:186` |
| Frog / Deft | RARE / EPIC | 3 / 2 | boots | passive | Jump Boost I–III / Speed I–II | — | `PotionEnchants.java:28,40` |
| Polarize | LEGENDARY | 3 | **per piece** | see source | wipes attacker's enchantments | — | `PvpEnchants.java:30` |
| Nightsight, Vigor, Soulbound | — | — | — | — | see `EnchantNightsight/Vigor/Soulbound.java` | — | *partial* |

---

## Bows and tools — *partial*

Headline constants only; the rest is not yet transcribed.

| Enchant | Rarity | Lvl | Effect | Source |
|---|---|---|---|---|
| Piercing | RARE | 3 | `×(1 + 0.15L)` = 1.15/1.30/1.45 | `BowEnchants.java:65` |
| Ricochet | EPIC | 3 | search radius 8.0 | `BowEnchants.java:109` |
| Instant Transmission | EPIC | 1 | 60-tick (3 s) cooldown | `BowEnchants.java:186` |
| Soul Entwine | RARE | 1 | 100-tick (5 s) cooldown | `BowEnchants.java:216` |
| Bola / Penetrating / Homing | RARE / RARE / LEGENDARY | 3 | not yet transcribed | `BowEnchants.java:160,70,247` |
| Haste | EPIC | 3 | Haste I–III | `PotionEnchants.java:52` |

---

## Numbers in the code that are modelled rather than measured

These are the ones most likely to be wrong, because nothing has ever checked them
against the game:

- `Reflect.BLOCKS_PER_VELOCITY = 9.6` — the comment says "Derived from vanilla's
  0.08 gravity and 0.91 air drag; approximate, and worth tuning by feel"
  (`ArmorEnchants.java:176-180`). Every "throws them N blocks" claim rests on it.
- Suplex's "4.5 / 6.3 / 8.3 blocks" in ENCHANT-TUNING.md is not in the code at
  all; the code sets a vertical velocity and the block figure was computed
  somewhere else.
- `Flippers.LAND_GAP = 0.96` and `MAX_SPEED = 0.22` as "land sprint speed".

All three are measurable in-game and none has been measured.
