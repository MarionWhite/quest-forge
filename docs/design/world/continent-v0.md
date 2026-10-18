# Continent v0: first rough draft

Status: **draft for the author's review**, 2026-10-17. Source: [`continent-v0.yaml`](continent-v0.yaml).
Rendered with `tools/world/plan.py`. Principles: [`research/worlds.md`](research/worlds.md).
The author rejected the ring-sector ("pie slice") layout; v1 keeps the centre focal point and
the north-cold / south-hot climate but drops the sectors.

## Layout, by real biome

| Ring | Distance from centre | Biomes (tier) |
|---|---|---|
| Coast | 8,000 to 13,000 | BoP Redwood Forest, Cherry Blossom Grove, Prairie, Mangrove, Steppe (T1); BoP Temperate Rainforest, Snowy Coniferous Forest, Tundra (T2); **BoP Wasteland (T3), reaching the coast between Mangrove and Steppe** |
| Middle | 4,900 to 8,000 | BoP Maple Woods, Marsh, Tropical Rainforest, Outback, Highland, Frost Forest (T2); **BoP Ominous Woods, Dead Forest (T3)** |
| Mountain ring | about 4,400 | BoP Alps peaks up to y 190, broken by four passes |
| Inner | 2,200 to 4,900 | BoP Alps (north), BoP Jade Cliffs (south) (T3) |
| Centre | under 2,300 | BoP Volcano (T4) |
| Small, unlabelled on any in-game map | — | BoP Mystic Grove, Sacred Springs, Lavender Fields, Oasis; vanilla Mushroom Island; RWG Tropical Island; BoP Coral Reef and Kelp Forest at sea |

**Climate:**
- north cold: Snowy Coniferous Forest, Tundra, Frost Forest;
- west wet: Redwood Forest and Temperate Rainforest behind a coastal range;
- south warm: Prairie, Cherry Blossom Grove, Mangrove, Tropical Rainforest;
- east dry: Steppe, Outback.

## How the research shaped it

- **Difficulty rises inward (Valheim, Elden Ring).** There are seven coastal spawns: five T1 and
  two T2, in Snowy Coniferous Forest and Temperate Rainforest. The spawn picker shows each tier.
- **A dangerous zone next to the easy start (Elden Ring's Caelid).** BoP Wasteland (T3) reaches
  the coast between two T1 biomes, so players see it before they are ready for it.
- **The mountain ring is the gate and the reveal (Breath of the Wild's triangle rule).**
  Cresting a pass shows the BoP Volcano centre.
- **One hero site per region (Witcher 3, Elden Ring).** Placeholders are marked on the plan.
- **Rivers as routes.** Six rivers run from the mountain ring to the sea along biome borders.
- **Small biomes to find, not shown (Outer Wilds, Hollow Knight).** They feed the Discovery
  quest tab.
- **The sea is a threshold.** Beyond it, the RWG outskirts are the hardest content in the game
  (decision 0003).

## Open

1. Size: decided after the author tries WorldPainter (`sizing.md`).
2. The v1 layout: organic regions, a climate gradient and the centre focal point. Each
   region should blend 2–4 biomes, not one.
3. Visual quality: see [`research/rlcraft-visuals.md`](research/rlcraft-visuals.md). It needs
   a custom tree and object library placed through WorldPainter, plus seasons, foliage and
   shaders.
4. Landmarks beyond render distance: a possible qf-content "distant silhouette" renderer.
