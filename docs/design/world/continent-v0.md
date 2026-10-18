# Continent v0: first rough draft

Status: **draft for the author's review**, 2026-10-17. Source: [`continent-v0.yaml`](continent-v0.yaml).
Rendered with `tools/world/plan.py`. Principles: [`research/worlds.md`](research/worlds.md).

## The idea in one sentence

A continent broken from the outside in: gentle coasts where players land, wilder lands
inward, a mountain crown with four passes, and at the centre **the Wound**, where the sky
broke. The Acts of the Chronicle (`docs/design/questline-audit.md` 4.1) follow the walk inland.

## Layout

| Ring | Distance from centre | Tier | Regions |
|---|---|---|---|
| Coast | 8,000 to 13,000 blocks | T1–T2 | Redwood Coast, Lantern Coast, Sunfields, Mangrove Delta, Windward Steppe (T1); Rainward, Frostharbor Fjords, Tundra Reach (T2); **Ashen Reach (T3)** |
| Middle | 4,900 to 8,000 | T2–T3 | Maple Highlands, Great Marsh, Jungle Basin, Red Canyons, Heather Highlands, Frostwood (T2); **Ominous Woods, Deadwood (T3)** |
| Crown Range | about 4,400 | — | A ring of peaks up to y 190, broken by Shade, Frost, Ember and Marsh passes |
| Inner | 2,200 to 4,900 | T3 | Glacier Spine (north), Jade Terraces (south) |
| The Wound | under 2,300 | T4 | A volcanic caldera; the Spire is the hero site |
| Hidden | — | — | Mystic Hollow, Sacred Springs, Lavender Sea, Canyon Oasis, Mushroom Isle, Sunken Isles; reef and kelp seas |

**Climate makes geographic sense:**
- the north is cold, with fjords and tundra;
- the west is wet: redwoods and rainforest behind a coastal range;
- the south is warm: prairie, cherry groves, mangroves and jungle;
- the east is dry: steppe and red canyons.

## How the research shaped it

- **Difficulty radiates inward (Valheim, Elden Ring).** All seven spawns are on the coast.
  Five are T1; Frostharbor and Rainward are T2 for players who want a harder start. The
  spawn picker shows the tier.
- **A Caelid next to the cradle.** The Ashen Reach (T3 wasteland) reaches the coast between
  two T1 regions, Mangrove Delta and Windward. Players see the danger before it bites, and
  it is a visible "not yet" from day one.
- **The Crown Range is the gate and the reveal (Breath of the Wild's triangle rule).** You
  cross a pass and the Wound opens below you, with the Spire at its heart. Four passes give
  four first sightings.
- **One theme and one hero site per region (Witcher 3, Elden Ring).** Examples: the Elder
  Redwood, Lantern Shrine, the Colosseum, Ash Crater, the Drowned Abbey and Canyon Arch.
  Each region also gets its own Lycanites family, planned for the spawn tables.
- **Rivers are roads.** Six rivers run from the Crown Range to the sea along region borders.
  They are natural routes and dividers, and points of interest cluster along them.
- **Things to find, not just see (Outer Wilds, Hollow Knight).** The hidden places are small
  biomes no map label gives away, fed by the Discovery quest tab.
- **The sea is a threshold.** The procedural RWG outskirts beyond it are uncurated.
  Making them the hardest frontier (Valheim) is an open question below.

## Not settled; for the author

1. **Scale.** 32,768 blocks is about 1,000 km²: roughly 13× Elden Ring and 50× Wynncraft.
   Five friends will see a fraction of it. The draft concentrates hand-made content along the
   rivers and passes and leaves wilderness between them. A 24k world would roughly double the
   density. (see `sizing.md`)
2. **The layout is still schematic.** The regions are ring sectors, and the next pass should
   break that symmetry.
3. **The frontier's difficulty.** Hardest of all (Valheim), or ordinary pack spawns?
4. **Landmarks past the render distance.** Friends at 5–8 chunks see only 80–128 blocks.
   One option is a qf-content "distant silhouette" renderer for the Spire and the hero sites
   (research principle 1).
5. **Names and fiction:** all placeholders.
