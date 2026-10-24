"""r12 frozen: main.yaml plus four contained FROZEN WONDERS set pieces in the north.

Loads main.yaml and only appends entries (new regions are prepended so they win their
small area). Nothing already in main.yaml is edited, removed or reordered.
  1. Spire field   - a cluster of narrow ice spikes west of the Ice castle (Ice Plains Spikes)
  2. Calving front - a glacier tongue down the eastern lobe to a sheer ice cliff at the sea,
                     with tabular iceberg islets in a frozen-ocean field offshore
  3. Frozen falls  - a glacier shelf on the western lobe holding a hanging lake that spills
                     over the rim into a lower frozen lake
  4. Aurora point  - a high, bare tundra headland on the small middle cape, peak at its tip
Run: py -3.10 frozen-gen.py  (writes frozen.yaml next to this script)
"""
import copy
import math
import os
import random

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
spec = yaml.safe_load(open(os.path.join(HERE, "main.yaml"), encoding="utf-8"))
orig = copy.deepcopy(spec)
rng = random.Random(1217)

ICE_SPIKES, GLACIER, FROZEN_OCEAN, FROZEN_RIVER, ICE_PLAINS, TUNDRA, ICE_MTN = 140, 89, 10, 11, 12, 247, 13

new_regions, ponds, plateaus, ridges, islands, rivers, points = [], [], [], [], [], [], []


def circle_poly(x, z, r, n=24):
    return [[round(x + r * math.cos(2 * math.pi * i / n)), round(z + r * math.sin(2 * math.pi * i / n))] for i in range(n)]


# 1. Spire field: ~22 needle spikes, 50-75 blocks above the plain, west/north-west of the castle.
sx, sz = 6450, -16750
for _ in range(400):
    if len([r for r in ridges if r.get("_spike")]) >= 28:
        break
    a, d = rng.uniform(0, 2 * math.pi), 1150 * math.sqrt(rng.random())
    x, z = sx + d * math.cos(a), sz + d * math.sin(a) * 0.8
    if math.hypot(x - 7520, z + 16298) < 800:           # keep clear of the castle's frost forest
        continue
    if any(math.hypot(x - r["points"][0][0], z - r["points"][0][1]) < 260 for r in ridges):
        continue
    ridges.append({"_spike": True, "points": [[round(x), round(z)], [round(x) + 1, round(z) + 1]],
                   "height": rng.randint(125, 152), "width": rng.randint(170, 260),
                   "relief": 120, "peak_spacing": 300, "biome": ICE_SPIKES, "biome_above": 0.0})
for r in ridges:
    r.pop("_spike")
ponds.append({"at": [sx - 150, sz + 150], "r": 170, "biome": ICE_SPIKES})   # a frozen tarn among the spires
points.append({"name": "Spire field", "kind": "landmark", "x": sx - 150, "z": sz - 250})

# 2. Calving front: glacier tongue from the eastern lobe's neck to its north tip.
tongue = [[12300, -17900], [12700, -18900], [13050, -19700], [13150, -20350]]
hs = [128, 112, 98]
for (a, b), hh in zip(zip(tongue, tongue[1:]), hs):
    ridges.append({"points": [a, b], "height": hh, "width": 1100, "relief": 18, "peak_spacing": 2600,
                   "biome": GLACIER, "biome_above": 0.15})
# the ice body itself: a lane of glacier biome, low relief, flaring at the snout
lane = [[11900, -17900], [12700, -18000], [13200, -18900], [13500, -19700], [13650, -20550],
        [12700, -20550], [12600, -19800], [12250, -18950]]
new_regions.append({"biome": GLACIER, "base": 80, "relief": 12, "exact": True, "polygon": lane})
# the snout: a sheer ice cliff where it meets the sea
plateaus.append({"circle": [13150, -20200, 450], "top": 92, "wall": 20, "top_relief": 4, "relief": 10,
                 "biome": GLACIER})
# iceberg field offshore: tabular ice islets, packed close to the front and thinning out
bergs = []
for _ in range(600):
    if len(bergs) >= 22:
        break
    a = rng.uniform(math.radians(-165), math.radians(-15))       # the sea north of the snout
    d = rng.uniform(450, 2300)
    x, z = 13150 + d * math.cos(a), -20450 + d * math.sin(a)
    r = rng.uniform(70, 190) * (1.15 - 0.4 * (d - 450) / 1850)
    if z > -20700:
        continue
    if any(math.hypot(x - bx, z - bz) < br + r + 140 for bx, bz, br in bergs):
        continue
    bergs.append((round(x), round(z), round(r)))
for x, z, r in bergs:
    islands.append({"circle": [x, z, r]})
    plateaus.append({"circle": [x, z, r + 40], "top": 70 + int(r / 25), "wall": 8, "top_relief": 2,
                     "relief": 6, "biome": GLACIER})
field = circle_poly(13150, -21400, 2100)
new_regions.append({"biome": GLACIER, "base": 66, "relief": 6, "exact": True,
                    "polygon": [[x, min(z, -20650)] for x, z in field]})
new_regions.append({"biome": FROZEN_OCEAN, "sea": True, "polygon": circle_poly(13150, -21300, 2300)})
points.append({"name": "Calving front", "kind": "landmark", "x": 13150, "z": -20450})

# 3. Frozen falls: a glacier shelf with a hanging lake spilling over its rim to a lower lake.
fx, fz = 4700, -19350
plateaus.append({"circle": [fx, fz, 850], "top": 130, "wall": 36, "top_relief": 5, "relief": 15,
                 "biome": GLACIER})
new_regions.append({"biome": ICE_PLAINS, "base": 70, "relief": 15, "exact": True,
                    "polygon": circle_poly(fx + 400, fz + 400, 1300)})
ponds.append({"at": [fx - 50, fz - 100], "r": 290, "depth": 10, "biome": ICE_PLAINS, "rot": 0.3, "aspect": 1.3})
ponds.append({"at": [fx + 950, fz + 1100], "r": 300, "depth": 12, "biome": ICE_PLAINS, "rot": 0.8, "aspect": 1.4})
rivers.append({"points": [[fx + 100, fz + 80], [fx + 400, fz + 400], [fx + 650, fz + 650], [fx + 900, fz + 1000]],
               "width": 26, "meander": 60, "valley": 60, "biome": FROZEN_RIVER})
points.append({"name": "Frozen falls", "kind": "landmark", "x": fx + 600, "z": fz + 600})

# 4. Aurora point: the small middle cape raised into a bare, high tundra headland.
ax, az = 9150, -19500
plateaus.append({"circle": [ax, az, 900], "top": 104, "wall": 45, "top_relief": 8, "relief": 25})
ridges.append({"points": [[ax - 250, az + 150], [ax - 249, az + 151]], "height": 168, "width": 600,
               "relief": 60, "peak_spacing": 2600, "biome": ICE_MTN, "biome_above": 0.3})
new_regions.append({"biome": TUNDRA, "base": 90, "relief": 25, "exact": True, "polygon": circle_poly(ax, az, 1100)})
points.append({"name": "Aurora point", "kind": "landmark", "x": ax - 250, "z": az + 150})

# Append only. New regions go first so they win their small area.
spec["regions"] = new_regions + spec["regions"]
for key, items in (("ponds", ponds), ("plateaus", plateaus), ("ridges", ridges), ("islands", islands),
                   ("rivers", rivers), ("points", points)):
    spec.setdefault(key, [])
    spec[key] = spec[key] + items

# Guard: every original entry is still there, unchanged and in order.
for k, v in orig.items():
    if k == "regions":
        assert spec[k][len(new_regions):] == v, k
    elif isinstance(v, list):
        assert spec[k][:len(v)] == v, k
    else:
        assert spec[k] == v, k

out = os.path.join(HERE, "frozen.yaml")
with open(out, "w", encoding="utf-8") as f:
    f.write("# r12 frozen: generated by frozen-gen.py from main.yaml (append-only FROZEN WONDERS set pieces)\n")
    yaml.safe_dump(spec, f, sort_keys=False, default_flow_style=None, width=120)
print(f"{out}: +{len(new_regions)} regions, +{len(ridges)} ridges, +{len(plateaus)} plateaus, "
      f"+{len(islands)} islets, +{len(ponds)} ponds, +{len(rivers)} rivers, +{len(points)} points")
