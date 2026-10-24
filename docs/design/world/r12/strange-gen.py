"""r12 strange: main.yaml plus four 'ancient and strange' set pieces, appended only.

Nothing in main.yaml is edited, removed or reordered. Every new entry is appended to the end
of its list. No regions are added: a prepended region shifts every region index, and plan.py
seeds the per-region auto lakes by index, so the whole map's lakes would move. Biome patches
are stamped instead with a 'plateau' whose top sits below the ground (it raises nothing and
only paints its biome), and pits are short canyons (a canyon with a near-zero length is a round
bowl with steep walls and a flat floor).

  1. Meteor crater, Outback (-9400, 8900): raised Crag rim, Wasteland bowl, black-sand floor,
     a crater pond, and a Wasteland ejecta apron.
  2. Petrified forest, south flank of the volcano (-7900, 4300): a Dead Forest field where the
     ash slope meets the Seasonal Forest, studded with Crag spires.
  3. Rock pillar, Shrubland of the east landmass (17200, -1200), 2 km from the T1 spawn: one
     sheer Crag tower ~120 blocks tall standing in a patch of Grassland.
  4. Spider hollow, Ominous Woods (10300, 1500): a sunken Silkglades bowl under Ominous Woods
     walls, below the Corrupted core.

Run: py -3.10 strange-gen.py
"""
import copy
import math
import os
import random

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
src = yaml.safe_load(open(os.path.join(HERE, "main.yaml"), encoding="utf-8"))
d = copy.deepcopy(src)
rng = random.Random(1212)


def add(key, item):
    d.setdefault(key, []).append(item)


def blob(x, z, r, k=14, wob=0.25, seed=0):
    """Irregular closed polygon around (x, z)."""
    rr = random.Random(seed)
    ph = [rr.uniform(0, 2 * math.pi) for _ in range(3)]
    pts = []
    for i in range(k * 2):
        a = 2 * math.pi * i / (k * 2)
        f = 1 + wob * (0.6 * math.sin(2 * a + ph[0]) + 0.3 * math.sin(3 * a + ph[1]) + 0.2 * math.sin(5 * a + ph[2]))
        pts.append([int(x + r * f * math.cos(a)), int(z + r * f * math.sin(a))])
    return pts


def stamp(biome, **shape):
    """Biome-only patch: a plateau whose top is far below the ground never raises anything."""
    add("plateaus", dict(shape, top=0, wall=8, top_relief=0, relief=255, biome=biome))


def pit(x, z, width, depth, wall_biome, floor_biome):
    add("canyons", {"points": [[x - 2, z], [x + 2, z]], "width": width, "depth": depth,
                    "meander": 0, "wall_biome": wall_biome, "floor_biome": floor_biome})


# ---- 1. Meteor crater (Outback) -------------------------------------------------------------
CX, CZ = -9400, 8900
outer = blob(CX, CZ, 1080, wob=0.25, seed=1)
inner = [[int(CX + 880 * math.cos(-2 * math.pi * i / 32)), int(CZ + 900 * math.sin(-2 * math.pi * i / 32))] for i in range(33)]
stamp(251, polygon=outer + [outer[0]] + inner)                      # ejecta apron (keyhole ring), Wasteland
add("ridges", {"arc": [CX, CZ, 680, 0, 359], "height": 100, "width": 520, "relief": 60,
               "peak_spacing": 2600, "biome": 77, "biome_above": 0.3})   # raised rim, Crag
pit(CX, CZ, 1050, 36, 77, 251)                                       # the bowl
for k in range(7):                                                   # ejecta rays past the apron
    a = math.radians(k * 360 / 7 + rng.uniform(-18, 18))
    tip, hw = rng.uniform(1350, 1500), math.radians(rng.uniform(3.5, 5))
    stamp(251, polygon=[[int(CX + 850 * math.cos(a - hw)), int(CZ + 850 * math.sin(a - hw))],
                        [int(CX + tip * math.cos(a)), int(CZ + tip * math.sin(a))],
                        [int(CX + 850 * math.cos(a + hw)), int(CZ + 850 * math.sin(a + hw))]])
ring = lambda r, s=1: [[int(CX + r * math.cos(s * 2 * math.pi * i / 32)), int(CZ + r * math.sin(s * 2 * math.pi * i / 32))] for i in range(33)]
add("surfaces", {"material": "black_sand", "polygon": ring(380) + ring(170, -1)})  # scorched ring, Wasteland eye
# No crater pond: plan.py numbers explicit ponds ahead of the auto lakes and seeds each lake's
# shape by that number, so one appended pond reshapes every auto lake on the map. The pond is
# ready below for when plan.py seeds lakes by position instead:
# add("ponds", {"at": [CX, CZ], "r": 170, "depth": 6, "aspect": 1.15, "rot": 0.6})
# Marker on the south rim, so the preview dot does not hide the pond.
add("points", {"name": "Meteor crater", "kind": "landmark", "x": CX, "z": CZ + 650})

# ---- 2. Petrified forest (volcano's south flank) -------------------------------------------
PX_, PZ = -7900, 4300
stamp(78, polygon=blob(PX_, PZ, 1050, wob=0.35, seed=2))             # Dead Forest
spires = []
while len(spires) < 11:
    a, r = rng.uniform(0, 2 * math.pi), 850 * math.sqrt(rng.random())
    x, z = PX_ + r * math.cos(a), PZ + r * math.sin(a) * 0.85
    big = len(spires) < 3
    rad = rng.uniform(110, 150) if big else rng.uniform(55, 90)
    if all(math.hypot(x - sx, z - sz) > rad + sr + 120 for sx, sz, sr in spires):
        spires.append((x, z, rad))
for x, z, rad in spires:
    add("plateaus", {"circle": [int(x), int(z), int(rad)], "top": int(rng.uniform(118, 140) if rad > 100 else rng.uniform(102, 122)),
                     "wall": 22, "top_relief": 4, "relief": 25, "biome": 77})
add("points", {"name": "Petrified forest", "kind": "landmark", "x": PX_, "z": PZ})

# ---- 3. Rock pillar (east Shrubland, in sight of the T1 spawn) ------------------------------
TX, TZ = 17200, -1200
stamp(138, polygon=blob(TX, TZ, 750, k=20, wob=0.45, seed=3))              # Grassland (same rainfall as the Shrubland)
add("plateaus", {"circle": [TX, TZ, 150], "top": 205, "wall": 70, "top_relief": 5,
                 "relief": 20, "biome": 77})
add("points", {"name": "Rock pillar", "kind": "landmark", "x": TX, "z": TZ + 330})   # at its foot: the dot would hide it

# ---- 4. Spider hollow (Ominous Woods) -------------------------------------------------------
SX, SZ = 9950, 1150
pit(SX, SZ, 1100, 20, 187, 237)                                      # Silkglades floor, main lobe
pit(SX + 430, SZ + 260, 700, 16, 187, 237)                           # side lobe
pit(SX - 300, SZ - 330, 520, 14, 187, 237)                           # back den
pit(SX + 150, SZ - 420, 380, 12, 187, 237)                           # north den
add("points", {"name": "Spider hollow", "kind": "landmark", "x": SX, "z": SZ})

# Guard: the original entries are untouched and in order.
for k, v in src.items():
    if isinstance(v, list):
        assert d[k][:len(v)] == v, k
    else:
        assert d[k] == v, k

out = os.path.join(HERE, "strange.yaml")
with open(out, "w", encoding="utf-8") as f:
    f.write("# r12 strange: generated by strange-gen.py from main.yaml (appended set pieces only)\n")
    yaml.safe_dump(d, f, sort_keys=False, default_flow_style=None, width=120)
print("wrote", out)
