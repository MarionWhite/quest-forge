# r14 — Difficulty layer and spawn points

The difficulty layer for the r13 continent (`r13/main.yaml`). It is a separate layer and does not
depend on the biome map. Tiers and spawn points change no terrain, so the world build is
unaffected.

- Spec: [`difficulty.yaml`](difficulty.yaml)
- Tool: `tools/world/difficulty.py`. It reads a plan dir (regions, biome, height, land, water
  and plan.json) and writes `difficulty.png` with one tier per plan pixel, `difficulty.json`
  with the shares and ratings, and a tinted preview.
- Renders:
  - `C:\qf-world\renders\r14-illustrated.png` (labelled; each spawn shows its rating)
  - `C:\qf-world\renders\r14-illustrated-clean.png`
  - `C:\qf-world\renders\r14-difficulty.png` (the tiers over the clean map, with a legend)

```
py -3.10 tools/world/plan.py render docs/design/world/r13/main.yaml PLAN --px 32
py -3.10 tools/world/difficulty.py PLAN docs/design/world/r14/difficulty.yaml --write-spawns
py -3.10 tools/world/illustrate.py PLAN r14-illustrated.png
py -3.10 tools/world/illustrate.py PLAN r14-illustrated-clean.png --no-labels
py -3.10 tools/world/difficulty.py PLAN docs/design/world/r14/difficulty.yaml \
    --map r14-illustrated-clean.png --preview r14-difficulty.png
py -3.10 tools/world/difficulty.py PLAN docs/design/world/r14/difficulty.yaml     --bake docs/design/world/r14/qf-tiers-r13.bin.gz
```

The last line bakes the tier grid the game reads; see
[`difficulty-mechanism.md`](difficulty-mechanism.md). The renders in `C:\qf-worldenders` predate
the 2026-10-25 pocket change (they still show T1).

## Tiers

There is no T1 (the author's decision of 2026-10-25). The spawn pockets are T2, and they are
small: enough for the very early game only.

| Tier | Meaning | Where |
|---|---|---|
| T2 Spawn pocket | The very early game: bearings and a starter kit | Within about 650 blocks of a spawn |
| T3 Quite difficult | The normal state of the world | Most land |
| T4 Hard | Gear and a group expected | The northern ice landmass, the northwest island, the northeast tundra, the dark woods around the corrupted core, the Maelstrom and haunted isles, the crag ring, both desert lobes, the southern volcanic isle |
| T5 Very difficult | Destinations, not places to pass through | The hot zones below |
| T6 Beyond | The way to the outskirts, the hardest content (decision 0003) | The outer sea and the edge ring of the plan |

How the layer is built:

1. **Base tier.** Each region in `regions.png` takes the tier of the zone that covers most
   of its land. Land outside every zone is T3. Region borders blend over 500 blocks.
2. **Hot zones.** Each zone pulls difficulty up to 5. The falloff is smooth, so a T4 band
   forms between a hot zone and its T3 surroundings. Noise roughens the zone edges so they
   are not perfect circles.
3. **Spawn pockets.** Each spawn is T2 within 500 blocks. From there the difficulty ramps
   from 2 to 6 over 1,200 blocks, capped by the surrounding tier, so T2 reads out to about
   650 blocks and T3 resumes there. (Until 2026-10-25 the pocket was T1 to 750 blocks and a
   T2 apron to 1,550.)
4. **Beyond.** T6 covers the sea within 2,500 blocks of the plan's edge. It also covers any
   open sea joined to that band that lies more than 4,000 blocks from land. Inner seas and
   straits keep the tier of their nearest shore.

## Hot zones (T5)

| Hot zone | Shape |
|---|---|
| Volcano island and crater rim | Circle of radius 2,400 around (-8520, -150); falloff 1,300 |
| Corrupted core of the enchanted quarter | Circle of radius 1,400 around (10500, -3200); falloff 1,100 |
| Maelstrom sea (water and isles) | Circle of radius 2,900 around (12900, 6500); falloff 1,400 |
| Ice castle and spire field | Circle of radius 1,900 around (6900, -16650); falloff 1,300 |
| Glacial caldera | Circle of radius 2,500 around (-15270, -15868); falloff 1,200 |
| High crests of the divide | Ground above y 185 between x -14,500 and 16,300; falloff 550 |
| Deep desert | Desert, Mesa and Outback more than 1,600 blocks inside the biome edge; falloff 900 |
| Tepui top | Circle of radius 1,250 around (15500, 13000); falloff 800 |
| Calving front | Circle of radius 2,400 around (13150, -20900); falloff 1,300 |

## Spawns

There are ten spawns. Each sits on flat, dry land (no sea, lake or river, low local relief) at
least 1,200 blocks from any landmark. The closest pair is 8,688 blocks apart.
`difficulty.py` checks all of this and warns on any spawn that fails.

The picker rating is the mean tier of the land within 3,000 blocks of the spawn. The labels
are: Gentle below 2.65, Hard below 2.9, Brutal below 3.08, and Deadly at 3.08 or above.

**The labels need recalibrating.** They were set when each spawn's T1/T2 pocket covered about
a quarter of the circle. With the small T2 pocket (2026-10-25) every score rose by 0.4 to 1.0,
and the old cut-offs now call eight of the ten spawns Deadly. The scores below are current;
the cut-offs are the picker's job and wait for it.

| Area | x | z | Score | Old label |
|---|---:|---:|---:|---|
| Redwood west coast | -16500 | 2500 | 2.92 | Brutal |
| Central lowlands, west of the Thousand Islands | 1400 | 5800 | 2.94 | Brutal |
| East steppe peninsula | 15900 | 2700 | 3.13 | Deadly |
| North rainforest belt (Temperate Rainforest, south of the divide) | -3200 | -2500 | 3.28 | Deadly |
| Tropical southeast lobe | 13700 | 14700 | 3.57 | Deadly |
| Southwest desert tip | -7900 | 13100 | 3.66 | Deadly |
| Northern ice landmass (Tundra, west end) | 1500 | -16400 | 3.78 | Deadly |
| Northeast tundra | 13200 | -9000 | 3.84 | Deadly |
| South desert lobe | 3200 | 14300 | 3.87 | Deadly |
| Northwest glacial-caldera island | -15300 | -11400 | 4.01 | Deadly |

The order is close to the old one: the coastal and lowland spawns are the gentlest, and the
desert, ice and caldera spawns the hardest.

## Land share per tier

| Tier | Share of land | Target |
|---|---:|---:|
| T2 | 1.3% | small: the very early game only |
| T3 | 46.8% | about 45% |
| T4 | 34.9% | about 30% |
| T5 | 17.0% | about 15% |

T6 covers only sea.

## Redwood tone

In `illustrate.py`, the BoP Redwood Forest and RWG Redwood biomes now have a muted
burgundy-brown colour (98, 70, 62) in place of the conifer green. They are still drawn with
dense tree stipple. The red-brown sits beside the neighbouring Maple Woods and Seasonal Forest
greens without becoming a bright red.

## Not decided yet

This layer is design only. In-game enforcement, meaning the JustAnotherSpawner spawn tables,
mob scaling per tier, the outskirts mechanism and the picker UI in qf-content, comes later. It
will be a **balance proposal for the author's approval** and will not be applied directly.
