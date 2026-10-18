# Emits docs/design/world/options/a-archipelago.yaml (the centre ring of sea stacks is computed).
import math, sys

out = sys.argv[1]

import random
def rugged(pts, seed, amp=380, step=380, grow=1.12):
    rng = random.Random(seed)
    cx = sum(x for x, _ in pts) / len(pts); cz = sum(z for _, z in pts) / len(pts)
    pts = [(cx + (x - cx) * grow, cz + (z - cz) * grow) for x, z in pts]
    ph = [rng.uniform(0, 6.283) for _ in range(6)]
    out, s_ = [], 0.0
    for (x1, z1), (x2, z2) in zip(pts, pts[1:] + pts[:1]):
        Lg = math.hypot(x2 - x1, z2 - z1); nx, nz = (z2 - z1) / Lg, -(x2 - x1) / Lg
        k = max(1, int(Lg / step))
        for i in range(k):
            t = i / k; s_ += Lg / k
            off = amp * (0.6 * math.sin(s_ / 900 + ph[0]) + 0.3 * math.sin(s_ / 370 + ph[1]) + 0.25 * math.sin(s_ / 160 + ph[2]))
            out.append([round(x1 + (x2 - x1) * t + nx * off), round(z1 + (z2 - z1) * t + nz * off)])
    return out

L = []
w = L.append

w("# World option A: archipelago. No single continent: nine islands in one sea, each its own")
w("# climate and tier, rising from the starter islands (T1) through T2 and T3 to a ring of")
w("# colossal sea stacks around a central rock pillar (T4) in the middle of the map.")
w("# Render: py -3.10 tools/world/plan.py render docs/design/world/options/a-archipelago.yaml PLANDIR")
w("# Blocks, 0,0 at the centre, +x east, +z south. Biome IDs: docs/survey/biome-ids.tsv.")
w("size: 32768")
w("seed: 1701")
w("coast_warp: 800")
w("region_warp: 700")
w("blend_px: 14")
w("shore_width: 700")
w("shelf_width: 1100")
w("")
w("# The coast key holds the western island (BoP Redwood Forest, T1); the rest are islands.")
w("coast:")
for p in rugged([[-14200, -4800], [-12000, -5600], [-9800, -4600], [-8600, -2200], [-9000, 800], [-8400, 3000],
          [-10200, 4200], [-12600, 3800], [-14000, 1600], [-14600, -1800]], 1, grow=1.0):
    w(f"  - {p}")

islands = {
    "northwest, BoP Snowy Coniferous Forest (T2)": [[-12600, -12400], [-9400, -13600], [-6400, -12800], [-5000, -10400], [-5600, -8200], [-8000, -7400], [-10800, -8000], [-12400, -9800]],
    "land bridge, northwest to north": [[-5800, -10300], [-3500, -10700], [-3300, -9700], [-5600, -9300]],
    "north, BoP Alps and Tundra (T3)": [[-3800, -12000], [-600, -13200], [3200, -12600], [6200, -12800], [7800, -11000], [7200, -8600], [4200, -7600], [800, -8000], [-2200, -7800], [-3800, -9200]],
    "east-northeast, BoP Moor and Highland (T2)": [[5600, -6600], [7800, -7000], [9200, -5600], [8800, -3600], [6600, -3000], [5200, -4400]],
    "east, BoP Steppe (T1)": [[10600, -5600], [13000, -6200], [14400, -3600], [14200, -200], [14600, 2600], [12600, 3800], [10600, 2600], [10200, -1000], [11000, -3400]],
    "east-southeast, Savanna (T2)": [[4600, 4200], [7000, 3600], [8800, 5000], [8400, 7400], [6400, 8200], [4600, 7200]],
    "land bridge, savanna to desert": [[4300, 7200], [5300, 7700], [3700, 9300], [2700, 8900]],
    "southeast, BoP Mangrove and Tropics (T1)": [[9600, 8000], [12400, 7400], [14000, 9200], [13400, 12200], [10800, 13200], [9000, 11400]],
    "south, Desert and BoP Outback (T3)": [[-3600, 9200], [-400, 8600], [3400, 8800], [5200, 10200], [4400, 13000], [1000, 14200], [-2400, 13600], [-4200, 11600]],
    "southwest, BoP Tropical Rainforest (T2)": [[-12600, 6400], [-9800, 5800], [-6600, 6800], [-5600, 9200], [-6400, 12000], [-9400, 13200], [-12200, 12000], [-13400, 9200]],
}
w("")
w("islands:")
for k, (name, pts) in enumerate(islands.items()):
    w(f"  # {name}")
    w(f"  - {rugged(pts, 10 + k, amp=120 if 'bridge' in name else 380, grow=1.0 if 'bridge' in name else 1.1)}")
w("  # uncharted islets in the channels")
for x, z, r in [(-5200, -4600, 420), (5200, 1600, 360), (-1500, 6200, 380), (9600, -9800, 340), (-6200, 3400, 300), (3600, -5600, 320), (-13800, -14400, 500), (14200, 14200, 420)]:
    w(f"  - {{circle: [{x}, {z}, {r}]}}")
w("  # vanilla Mushroom Island, a small isle in the temperate channel")
w("  - {circle: [-4400, 4400, 650]}")

# Centrepiece: seven colossal sea stacks on a 2,600-block circle round a central rock pillar.
stacks = []
for i in range(7):
    a = math.radians(i * 360 / 7 + 10)
    r = 820 if i % 2 == 0 else 640
    top = 150 + (i * 23) % 50
    stacks.append((round(3000 * math.cos(a)), round(3000 * math.sin(a)), r, top, 77 if i % 2 == 0 else 250))
w("  # centrepiece: seven sea stacks round a central pillar")
for x, z, r, top, b in stacks:
    w(f"  - {{circle: [{x}, {z}, {r}]}}")
w("  - {circle: [0, 0, 700]}")

w("")
w("# Black sand on the floor of the stack ring's lagoon (WorldPainter terrain).")
w("surfaces:")
w("  - {material: black_sand, circle: [0, 0, 3000]}")
w("")
w("# Every sea stack and the pillar are sheer-walled plateaus.")
w("plateaus:")
for x, z, r, top, b in stacks:
    w(f"  - {{circle: [{x}, {z}, {r + 60}], top: {top}, wall: 45, top_relief: 8, relief: 40, biome: {b}}}")
w("  - {circle: [0, 0, 760], top: 225, wall: 40, top_relief: 10, relief: 40, biome: 250, tier: 4}")
w("")
w("# A canyon across the southern desert island, dry riverbed on its floor.")
w("canyons:")
w("  - {points: [[-2800, 10000], [-400, 10800], [2000, 11800], [3800, 12600]], width: 1000, depth: 38, meander: 300, wall_biome: 71, floor_biome: 82, tier: 3}")

w("")
w("regions:")
w("  # Centre (T4): the stacks and the pillar")
for x, z, r, top, b in stacks:
    w(f"  - {{tier: 4, biome: {b}, base: 90, relief: 60, circle: [{x}, {z}, {r + 150}]}}")
w("  - {tier: 4, biome: 250, base: 90, relief: 60, circle: [0, 0, 850]}")
w("""
  # A T3 zone in sight of every T1 spawn (360-450 blocks away)
  - {tier: 3, biomes: [[187, 2], [78, 1]], base: 78, relief: 60, circle: [-11700, -1000, 500]}
  - {tier: 3, biomes: [[251, 2], [78, 1]], base: 72, relief: 50, circle: [12300, -800, 500]}
  - {tier: 3, biome: 194, base: 64, relief: 10, circle: [12100, 10300, 500]}

  # Islets: each its own small biome
  - {tier: 2, biome: 77, base: 85, relief: 120, circle: [-5200, -4600, 520]}
  - {tier: 2, biome: 186, base: 66, relief: 10, circle: [5200, 1600, 460]}
  - {tier: 1, biome: 224, base: 66, relief: 15, circle: [-1500, 6200, 480]}
  - {tier: 2, biome: 192, base: 75, relief: 60, circle: [9600, -9800, 440]}
  - {tier: 2, biome: 197, base: 70, relief: 40, circle: [-6200, 3400, 400]}
  - {tier: 2, biome: 87, base: 68, relief: 30, circle: [3600, -5600, 420]}
  - {tier: 3, biome: 89, base: 80, relief: 60, circle: [-13800, -14400, 600]}
  - {tier: 1, biome: 75, base: 64, relief: 5, circle: [14200, 14200, 520]}

  # Small hidden biomes
  - {tier: 2, biome: 14, base: 68, relief: 30, circle: [-4400, 4400, 800]}
  - {tier: 2, biome: 185, base: 78, relief: 40, circle: [-10200, 2400, 500]}
  - {tier: 1, biome: 147, base: 72, relief: 20, circle: [13200, 1800, 500]}
  - {tier: 3, biome: 197, base: 110, relief: 50, circle: [-500, -10600, 450]}
  # Desert oases, each round a pond
  - {tier: 3, biome: 186, base: 100, relief: 8, circle: [-2000, 12500, 500]}
  - {tier: 3, biome: 186, base: 100, relief: 8, circle: [2600, 13300, 420]}

  # Seas by climate (RWG oceans), reefs and kelp on the shallow shelf
  - {biome: 211, sea: true, polygon: [[-16384, -16384], [16384, -16384], [16384, -6000], [-16384, -6000]]}
  - {biome: 210, sea: true, polygon: [[-16384, -16384], [16384, -16384], [16384, -13600], [-16384, -13600]]}
  - {biome: 212, sea: true, polygon: [[-16384, -6000], [16384, -6000], [16384, 4000], [-16384, 4000]]}
  - {biome: 213, sea: true, polygon: [[-16384, 4000], [16384, 4000], [16384, 16384], [-16384, 16384]]}
  - {biome: 75, sea: true, shallow: true, polygon: [[-16384, 6000], [16384, 6000], [16384, 16384], [-16384, 16384]]}
  - {biome: 144, sea: true, shallow: true, polygon: [[-16384, -9000], [-8000, -9000], [-8000, 6000], [-16384, 6000]]}
  - {biome: 144, sea: true, shallow: true, polygon: [[9500, -9000], [16384, -9000], [16384, 3000], [9500, 3000]]}
  # The lagoon inside the ring of stacks (after the bands, so it keeps its biome)
  - {biome: 214, sea: true, circle: [0, 0, 3900]}

  # The islands' climates. Each island's land goes to its nearest centre below.
  - {tier: 1, biomes: [[196, 3], [243, 2], [74, 1]], base: 76, relief: 70, lakes: [4, 100, 300], at: [-11500, -500]}
  - {tier: 2, biomes: [[239, 3], [66, 2], [74, 1]], base: 72, relief: 100, lakes: [8, 120, 400], at: [-8800, -10500]}
  - {tier: 3, biomes: [[60, 2], [59, 1], [89, 1]], base: 100, relief: 140, lakes: [4, 100, 300], at: [-1500, -10000]}
  - {tier: 3, biomes: [[247, 3], [61, 1], [89, 1], [192, 1]], base: 72, relief: 40, lakes: [12, 150, 500], at: [4800, -10600]}
  - {tier: 2, biomes: [[183, 2], [142, 2], [141, 1]], base: 86, relief: 70, lakes: [8, 80, 300], at: [7200, -5000]}
  - {tier: 1, biomes: [[242, 2], [193, 1], [236, 1]], base: 70, relief: 35, lakes: [3, 100, 300], at: [12400, -1000]}
  - {tier: 2, biomes: [[35, 2], [70, 1], [254, 1]], base: 72, relief: 40, lakes: [3, 80, 250], at: [6600, 5800]}
  - {tier: 1, biomes: [[246, 2], [153, 2], [195, 1]], base: 66, relief: 30, lakes: [4, 80, 250], at: [11600, 10400]}
  - {tier: 3, biomes: [[2, 3], [190, 2], [37, 1], [148, 1]], base: 100, relief: 50, at: [500, 11300]}
  - {tier: 2, biomes: [[245, 3], [62, 1], [21, 1]], base: 70, relief: 80, lakes: [6, 120, 350], at: [-9300, 9300]}

ponds:
  - {at: [-2000, 12500], r: 150, biome: 186}
  - {at: [2600, 13300], r: 130, biome: 186}

ridges:
  # Western coastal range on the redwood island
  - {points: [[-9600, -4200], [-9200, -1000], [-9000, 2400]], height: 140, width: 1200, relief: 160}
  # The spine of the northern island
  - {points: [[-3400, -10400], [-1000, -11400], [1600, -10200], [3000, -9000]], height: 215, width: 2000, relief: 220, biome: 60, biome_above: 0.55}
  # Peaks on the northwest island
  - {points: [[-11600, -11800], [-9000, -12600], [-7000, -11800]], height: 160, width: 1400, relief: 180}
  # Highland ridge on the moor island
  - {points: [[6200, -6000], [7800, -5000], [8400, -3800]], height: 125, width: 900, relief: 160}

rivers:
  # Redwood island: a forked river to the west coast
  - {points: [[-10000, -3800], [-11000, -1800], [-12600, -600], [-14600, -300]], width: 40}
  - {points: [[-9600, 200], [-10800, -900], [-12600, -600]], width: 28}
  # Tropical island: a wide winding BoP Lush River with tributaries
  - {points: [[-6400, 8600], [-8000, 9000], [-9600, 9800], [-11600, 10600], [-13600, 11000]], width: 80, meander: 350, valley: 240, biome: 150}
  - {points: [[-7000, 11600], [-7600, 10300], [-8000, 9000]], width: 32, biome: 150}
  - {points: [[-10400, 6600], [-10000, 8200], [-9600, 9800]], width: 32, biome: 150}
  - {points: [[-12000, 7400], [-11800, 9000], [-11600, 10600]], width: 28, biome: 150}
  # Frozen rivers in the north
  - {points: [[-6600, -8400], [-8200, -9800], [-9800, -11600], [-10800, -13600]], width: 32, biome: 11}
  - {points: [[-11800, -8800], [-10600, -10200], [-9800, -11600]], width: 24, biome: 11}
  - {points: [[5800, -8600], [4600, -10400], [3600, -13000]], width: 32, biome: 11}
  - {points: [[7200, -11200], [5600, -11600], [4200, -11500]], width: 24, biome: 11}
  # Steppe island
  - {points: [[11200, 2200], [12400, 600], [13200, -2000], [13600, -6000]], width: 32}
  - {points: [[14000, 1200], [12400, 600]], width: 24}
  # Desert island: a side wadi into the canyon (BoP Dry River)
  - {points: [[1200, 9200], [700, 10500], [-400, 10800]], width: 24, biome: 82, dry: true}

points:
  - {kind: spawn, tier: 1, x: -12500, z: -1500}
  - {kind: spawn, tier: 1, x: 12800, z: -1500}
  - {kind: spawn, tier: 1, x: 11600, z: 11000}
  - {kind: spawn, tier: 2, x: -9500, z: -11500}
  - {kind: spawn, tier: 2, x: -10500, z: 10500}
  - {kind: spawn, tier: 2, x: 7400, z: -4800}
""")
open(out, "w", encoding="utf-8").write("\n".join(L) + "\n")
print("wrote", out)
