"""r12 coast: main.yaml plus four contained coast-and-sea set pieces. Append-only.

Loads main.yaml and only appends islands, plateaus and points; its new regions are prepended so
they win their small areas. Nothing already in main.yaml is edited, removed or reordered.

  1. Sea stacks and arch, off the redwood shore below the west spawn (-18280, -2280).
  2. Lighthouse headland: the existing west-pointing cape at (-21000, -3700), raised to a
     heath-topped cliff.
  3. Wreck cove: the sheltered bay behind that cape; reef rocks across its mouth, wrecks inside.
  4. Tidal lagoon: a sand spit off the south coast below the Xeric spawn (-7702, 15522),
     with salt marsh along the inner shore and marsh islets.

Run: py -3.10 coast-gen.py   (writes coast.yaml next to it)
"""
import copy
import math
import os

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
base = yaml.safe_load(open(os.path.join(HERE, "main.yaml")))
d = copy.deepcopy(base)

REDWOOD, CRAG, HEATH, STONE_BEACH, BEACH = 196, 77, 141, 25, 16
DEAD_FOREST, MARSH, WETLAND, SCRUB = 78, 159, 252, 198

new_regions, new_islands, new_plateaus, new_points = [], [], [], []


def circle_poly(x, z, r, k=20):
    return [[int(x + r * math.cos(2 * math.pi * i / k)), int(z + r * math.sin(2 * math.pi * i / k))] for i in range(k)]


def band(points, width):
    """A polyline thickened to a closed polygon of the given width (blocks)."""
    left, right = [], []
    for i, (x, z) in enumerate(points):
        a = points[max(0, i - 1)]
        b = points[min(len(points) - 1, i + 1)]
        dx, dz = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dz) or 1
        nx, nz = -dz / L * width / 2, dx / L * width / 2
        taper = 0.55 if i in (0, len(points) - 1) else 1.0
        left.append([int(x + nx * taper), int(z + nz * taper)])
        right.append([int(x - nx * taper), int(z - nz * taper)])
    return left + right[::-1]


# --- 1. Sea stacks and arch ---------------------------------------------------------------
# (x, z, r, top, biome on top). Kept 700-1000 blocks off the coast so no plateau touches land.
stacks = [
    (-19300, -1500, 170, 118, REDWOOD),
    (-18900, -1050, 135, 104, CRAG),
    (-19650, -700, 115, 90, CRAG),
    (-18050, 300, 200, 128, REDWOOD),    # the great stack
    (-17700, 750, 125, 100, CRAG),
    (-18850, -50, 110, 94, CRAG),
]
for x, z, r, top, b in stacks:
    new_islands.append({"circle": [x, z, r]})
    new_plateaus.append({"circle": [x, z, int(r * 1.6)], "top": top, "wall": 24, "top_relief": 4,
                         "relief": 25, "biome": b})
# The arch: two stacks joined by a high rock bridge (carve the opening in WorldPainter).
a1, a2 = (-18520, -720, 150), (-18200, -360, 140)
new_islands += [{"circle": list(a1)}, {"circle": list(a2)}, {"polygon": band([a1[:2], a2[:2]], 220)}]
new_plateaus.append({"polygon": band([a1[:2], a2[:2]], 560), "top": 98, "wall": 22, "top_relief": 3,
                     "relief": 20, "biome": CRAG})
new_points.append({"name": "Sea arch", "kind": "landmark", "x": -18360, "z": -540})

# --- 2. Lighthouse headland -----------------------------------------------------------------
# The cape already there; the plateau only lifts land inside it, so the coast is unchanged.
new_plateaus.append({"polygon": [[-21750, -4550], [-20520, -4550], [-20430, -3700], [-20560, -2650],
                                 [-21750, -2650]],
                     "top": 104, "wall": 40, "top_relief": 6, "relief": 30, "biome": HEATH})
new_points.append({"name": "Lighthouse", "kind": "landmark", "x": -21120, "z": -3650})

# --- 3. Wreck cove --------------------------------------------------------------------------
# The bay between the cape and the shore; low reef rocks half-close its south mouth.
new_regions.append({"exact": True, "biomes": [[DEAD_FOREST, 2], [STONE_BEACH, 1]], "base": 68,
                    "relief": 18, "patch": 500,
                    "polygon": [[-20420, -5000], [-19300, -5000], [-19250, -2950], [-20420, -2950]]})
for x, z, r in [(-20330, -2700, 130), (-20020, -2520, 110), (-19760, -2700, 125), (-20600, -2450, 110)]:
    new_islands.append({"circle": [x, z, r]})
    new_plateaus.append({"circle": [x, z, int(r * 1.5)], "top": 70, "wall": 14, "top_relief": 2,
                         "relief": 15, "biome": STONE_BEACH})
new_points.append({"name": "Wreck cove", "kind": "landmark", "x": -20050, "z": -3300})
for x, z in [(-20180, -2600), (-20100, -4450)]:
    new_points.append({"name": "Wreck", "kind": "landmark", "x": x, "z": z})

# --- 4. Tidal lagoon behind a sand spit ------------------------------------------------------
spit = [[-8950, 16990], [-8550, 16950], [-8100, 16860], [-7600, 16780], [-7100, 16700], [-6600, 16560]]
new_islands.append({"polygon": band(spit, 240)})
new_regions.append({"exact": True, "biomes": [[BEACH, 3], [SCRUB, 1]], "base": 65, "relief": 3,
                    "patch": 450, "polygon": band(spit, 700)})
islets = [(-7950, 16420, 140), (-7300, 16380, 160), (-6800, 16320, 120)]
for x, z, r in islets:
    new_islands.append({"circle": [x, z, r]})
new_regions.append({"exact": True, "biomes": [[MARSH, 2], [WETLAND, 1]], "base": 63, "relief": 4,
                    "patch": 500,
                    "polygon": [[-8600, 15750], [-6350, 15700], [-6300, 16480], [-8600, 16520]]})
new_points.append({"name": "Tidal lagoon", "kind": "landmark", "x": -7450, "z": 16200})

# --- assemble: prepend regions, append everything else -------------------------------------
d["regions"] = new_regions + d["regions"]
d["islands"] = d["islands"] + new_islands
d["plateaus"] = d["plateaus"] + new_plateaus
d["points"] = d["points"] + new_points

# Guard: everything from main.yaml is still there, unchanged and in order.
assert d["regions"][len(new_regions):] == base["regions"]
for k in base:
    if k != "regions":
        assert d[k][:len(base[k])] == base[k] if isinstance(base[k], list) else d[k] == base[k], k


class Dumper(yaml.SafeDumper):
    pass


def _list(dumper, data):
    flow = all(isinstance(v, (int, float)) for v in data)
    return dumper.represent_sequence("tag:yaml.org,2002:seq", data, flow_style=flow)


Dumper.add_representer(list, _list)
with open(os.path.join(HERE, "coast.yaml"), "w") as f:
    f.write("# r12 coast: generated by coast-gen.py from main.yaml (append-only coast set pieces)\n")
    yaml.dump(d, f, Dumper=Dumper, sort_keys=False)
print("regions +%d, islands +%d, plateaus +%d, points +%d" % (len(new_regions), len(new_islands),
                                                           len(new_plateaus), len(new_points)))
