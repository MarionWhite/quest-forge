# 0005 — The enchant census proposals P1–P10

**Date:** 2026-10-25
**Status:** accepted with conditions (Decisions sheet 1, cards bal-p1 … bal-p10; issue #10;
`answers/s001.json`). Source: [enchantment-combat-results](../reference/enchantment-combat-results.md) §6.

## Decisions

| | Decision | Exactly what changes |
|---|---|---|
| P1 | **Yes** | Rupture, Venomous and Poisonous seed their per-stack damage from the post-armour hit, same percentages (4 / 5.8 / 4 % per level per second). |
| P2 | **Yes** | DoTs seed from the weapon's own hit, before this mod's flat and multiplier phases (`baseDamage` stored before FLAT). |
| P3 | **No change** | Excalibur stays the trophy (permanent Strength I, +4, Resistance I, Speed I). |
| P4 | **Yes** | The proposed proc change is withdrawn (Rage stays 5/10/15 %); a tooltip line "does nothing while Excalibur is held" is added. |
| P5 | **Keep** | The 750-per-hit caps on Mobzilla, The King and The Queen stay. |
| P6 | **Yes, this one change** | `config/MobProperties/demonmobs/rahovart.json` max-health boost `"3.0~9.0"` → `"0.5~2.0"`. |
| P7 | **Yes** | Cultist's price becomes a fixed 0.6 health per proc that bypasses armour (Protection applies), never below 1 health. |
| P8 | **Yes (a)** | Bastion's golems ignore the wielder's current target for 20 ticks after the wielder hits it. |
| P9 | **Yes, the table** | Unconditional moves: Rage Epic → Legendary, Momentum Uncommon → Epic, Roulette Uncommon → Rare, Tank Rare → Epic. The conditional moves do not happen (P1 and P7 were accepted). |
| P10 | **Later** | Not decided; replaced by the programme below. |

## The author's conditions (verbatim where it matters)

- P1: "Even if we make this change, everything still needs to be retested after to assure
  balance." → every code change above is followed by a targeted census re-run before it is
  installed anywhere.
- P6: "take into consideration how long other fights are averaging … research modern modpacks
  that do a good job of balancing fight duration … **Check back in before making any other
  changes in this capacity.**" → P6 is the only fight-length change; a fight-duration study
  (our census TTKs by tier, and what well-balanced modern packs aim for) comes back as a
  proposal.
- P7: "It should always have a cost because its utility scales with the gear, but we need to
  make sure we get this right."
- P8: "take a look at how others do this enchant because this is a thing that exists on like
  factions servers."
- P9: rarity may follow measured strength, but **drop rates and sources will change a lot
  later**; do not reason about drop rates when setting rarity.
- P10: the author wants, before any loot placement: "a full comprehensive table showing what
  sort of effect each enchantment/combination is having in tests (how much it increases
  survivability, how much damage it adds, which fights they show up in, tangible amounts of
  time that they shorten the fight by, etc.)"; every enchantment with "an observable effect
  proportionate to the rarity"; "a good looking distribution across rarities (it's fine if we
  have to come up with some more ideas for enchants)"; none that "break the game, make hard
  bosses much easier than they should be, or otherwise … up the flow". "I want this pack to
  be fun, and I want it to have a good lifespan."

## Consequences

1. Code: P1, P2, P4 (tooltip), P7, P8 in qf-content; P9's four rarity moves in the registry;
   P6 in `pack/config`. Built, then re-measured on the affected bosses with the census
   harness before `trial.py install`.
2. The **enchant effects table** the author described, generated from census data, becomes a
   reference document and, later, a site page; rarity distribution and new-enchant ideas are
   proposed from it.
3. The fight-duration study and the Bastion comparison come back on Decisions sheet 2.
4. No loot-placement work (P10, progression audit §5) until the author has the table.
