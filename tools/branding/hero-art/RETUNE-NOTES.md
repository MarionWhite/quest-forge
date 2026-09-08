# Hall of Heroes reward retune (2026-09-04)

Backup: `DefaultQuests.pre-retune-20260904-161946.json`

## Fraction rule

SAU / Stark Workbench cost comes from each character's `getMaterials()`.
That list is the cost of **one piece** (same list for every slot).

- Piece quests: **30%** of each stackable ingredient (clamped 20–40%, always `<` recipe count).
- Full-set quests: **40%** of the same list.
- Count 1 unique keys (logo, gem, reactor, belt, ruby, rocket, symbiote): **skipped** (would be 100% of that ingredient).
- Count 2: reward 1 (only meaningful slice; documented 50% exception).
- If the recipe consumes **another hero suit** (Underarmor → Mark 3/7/21, Mark 2 → War Machine): divide counts by 4 first (one-piece share of a full-suit conversion), then apply 30/40%.
- Vanilla leather armor used as a mat is skipped, not treated as a suit conversion.
- Ammo (`legends:bullet`) capped at 12.
- Legendary lootbag (damage **4**): Costume Closet + Iron Man Mark 7 full set only.

## Reload

`/bq_admin default load`
