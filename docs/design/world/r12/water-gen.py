"""r12 water: three water set pieces added on top of main.yaml, nothing else changed.

The author rejected restructuring the map, so this script only APPENDS entries to main.yaml's
lists (plateaus, ponds, points). Every existing entry stays as it is and where it is;
the end of the script checks that.

No new regions: plan.py seeds each region's random lakes with the region's list index, so
prepending even one region re-rolls the lakes of every region on the map. Sacred Springs rides on
the pools instead (pond biomes are painted after drainage).
No new rivers either: auto rivers are numbered after the hand-drawn ones, and their meander
seeds would shift. The waterfall uses a river that already exists.

1. Great falls: a bench on the wet slope of the divide (a plateau that the slope above
   swallows), crossed by the existing tributary at x~3450. The lip is a horseshoe around the
   river, with a plunge pool at its foot.
2. Cenote: a small, very deep round pool (58 blocks) in the western rainforest belt, with two
   smaller sister sinkholes. Ponds only, so it touches no drainage.
3. Hot spring terraces: a stepped mound on the volcano's south-east flank, six terraces, BoP
   Sacred Springs pools strung along each terrace lip and a hot pool on the crown. The terraces
   keep the biomes already there (Crag, Wasteland, Dead Forest, Cherry Blossom Grove) on
   purpose: painting the mound Sacred Springs changes its rainfall, which re-widths auto rivers.
(A natural-bridge gorge on the x~700 tributary was tried and dropped: that river has high ground
on one bank only, so the cut read as a valley, not a gorge. A gorge cut down to near sea level
also re-rolled every random lake in the rainforest belt; see the note on lakes below.)

Lakes: plan.py picks each region's random lakes by shuffling the cells that qualify (land, above
sea level, not a plain-River channel), and seeds each auto river's meander by its list index.
The cenote and the springs leave all 151 random lakes in place (checked at --px 32). The falls
bench cannot: it reroutes one auto river head (+1 segment), which re-seeds every later auto
river's 22-block meander and so reshuffles the small random lakes in ~10 regions (91 of 151).
WATER_ONLY=cenote,springs builds the version without it. A plan.py fix (seed meanders and lake
picks by position, not list index) would make additions like this local.
Adding ponds also re-rolls the outlines (not places or sizes) of all random lakes: their shape
noise is seeded by pond list position.

Run: py -3.10 water-gen.py   (writes water.yaml next to it)
"""
import copy
import math
import os
import random
import sys

import numpy as np
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "..", "tools", "world"))
import plan  # noqa: E402  (only its noise and meander functions; plan.py is not changed)

base = yaml.safe_load(open(os.path.join(HERE, "main.yaml"), encoding="utf-8"))
d = copy.deepcopy(base)
SEED = d.get("seed", 1)
WARP = 0.3 * d.get("coast_warp", 600)   # plateau masks are domain-warped by this much
rng = random.Random(1212)
ONLY = os.environ.get("WATER_ONLY", "falls,cenote,springs").split(",")   # for testing one piece at a time


def unwarp(x, z):
    """plan.py samples plateau polygons at (p + warp(p)); place a vertex there so the plateau
    lands where it is drawn here, not up to ~180 blocks off."""
    ox = WARP * float(plan.fbm(np.array([x]), np.array([z]), 2400, 4, SEED + 1)[0])
    oz = WARP * float(plan.fbm(np.array([x]), np.array([z]), 2400, 4, SEED + 2)[0])
    return [int(round(x + ox)), int(round(z + oz))]


def river_path(k):
    r = base["rivers"][k]
    return plan.meander(r["points"], r.get("meander", 220), SEED + 500 + k)


def crossing(path, z):
    """x where a north-to-south river path crosses latitude z."""
    for (x0, z0), (x1, z1) in zip(path, path[1:]):
        if min(z0, z1) <= z <= max(z0, z1) and z1 != z0:
            return x0 + (x1 - x0) * (z - z0) / (z1 - z0)
    raise ValueError(z)


def lobed(cx, cz, r, amp, seed, n=40):
    """A closed outline around (cx, cz) whose radius wanders by +-amp: travertine lobes."""
    rr = random.Random(seed)
    ph = [rr.uniform(0, 2 * math.pi) for _ in range(3)]
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        w = (0.55 * math.sin(3 * a + ph[0]) + 0.3 * math.sin(5 * a + ph[1]) + 0.15 * math.sin(8 * a + ph[2]))
        pts.append((cx + (r + amp * w) * math.cos(a), cz + (r + amp * w) * math.sin(a)))
    return pts


plateaus, canyons, ponds, points = [], [], [], []

# ---------------------------------------------------------------- 1. great falls
if "falls" in ONLY:
    R11 = river_path(11)
    LIP_Z = -4650                       # the bench's south lip; the slope falls to ~90 below it
    TOP = 156                           # bench top: ~80 blocks above the plunge pool
    WEST, EAST = 3000, 3950             # kept east of the high valley at x~3100, z<-5800: covering
                                        # it dams the valley and sends its water over the divide
    rx = crossing(R11, LIP_Z)
    NOTCH = 170                         # horseshoe: the lip curls back upstream around the river
    south = [(EAST, LIP_Z - 250), (EAST - 60, LIP_Z + 30), (rx + NOTCH + 80, LIP_Z + 10)]
    for i in range(13):                 # the horseshoe, east to west via its back (north)
        a = math.radians(0 - 180 * i / 12)
        south.append((rx + NOTCH * math.cos(a), LIP_Z + NOTCH * 0.95 * math.sin(a)))
    south += [(rx - NOTCH - 80, LIP_Z + 20), (WEST + 60, LIP_Z - 10), (WEST, LIP_Z - 350)]
    north = [(3250, -5500), (3300, -6700), (EAST + 100, -6700), (EAST + 150, -5600)]
    bench = south + north
    plateaus.append({"polygon": [unwarp(x, z) for x, z in bench], "top": TOP, "wall": 24,
                     "top_relief": 5, "relief": 35})
    falls_z = LIP_Z - NOTCH * 0.95
    ponds.append({"at": [int(rx), int(LIP_Z - 70)], "r": 150, "depth": 18, "aspect": 1.15, "rot": 0.0})
    points.append({"name": "Great falls", "kind": "landmark", "x": int(rx), "z": int(falls_z)})

# ---------------------------------------------------------------- 2. cenote
if "cenote" in ONLY:
    # Ponds only: they are dug after the drainage pass, so they cannot disturb any river or lake.
    for (cx, cz), r, depth, asp, rot in [((-6600, -4750), 105, 58, 1.1, 0.4),
                                         ((-6330, -4560), 46, 34, 1.15, 1.9),
                                         ((-6820, -4560), 38, 28, 1.2, 0.9)]:
        ponds.append({"at": [cx, cz], "r": r, "depth": depth, "aspect": asp, "rot": rot})
    points.append({"name": "Cenote", "kind": "landmark", "x": -6600, "z": -4750})

# ---------------------------------------------------------------- 3. hot spring terraces
if "springs" in ONLY:
    VOLC = (-8520, -150)
    C = (-6000, 1800)                   # mound foot centre, ~3.2 km out on the volcano's flank
    ux, uz = C[0] - VOLC[0], C[1] - VOLC[1]
    L = math.hypot(ux, uz)
    ux, uz = ux / L, uz / L             # downhill: away from the volcano
    STEPS = 6
    for k in range(STEPS):
        R = 900 - 140 * k
        cx, cz = C[0] - ux * 115 * k, C[1] - uz * 115 * k   # each terrace sits further uphill
        top = 88 + 7 * k
        plateaus.append({"polygon": [unwarp(x, z) for x, z in lobed(cx, cz, R, 45 + 6 * k, 300 + k)],
                         "top": top, "wall": 6, "top_relief": 1, "relief": 6})
        if k == STEPS - 1:              # the vent: a hot pool on the crown
            ponds.append({"at": [int(cx), int(cz)], "r": 75, "depth": 9, "aspect": 1.3, "rot": 0.6,
                          "biome": 197})
            continue
        front = math.atan2(uz, ux)      # pools strung along the downhill lip of each terrace
        for j in range(3 if k < 4 else 2):
            a = front + math.radians(rng.uniform(-60, 60))
            rad = R - 125 + rng.uniform(-15, 15)
            px_, pz_ = cx + rad * math.cos(a), cz + rad * math.sin(a)
            ponds.append({"at": [int(px_), int(pz_)], "r": int(rng.uniform(45, 62)), "depth": 4,
                          "aspect": 2.4, "rot": round(a + math.pi / 2, 3), "biome": 197})
    points.append({"name": "Hot spring terraces", "kind": "landmark",
                   "x": int(C[0] - ux * 115 * (STEPS - 1)), "z": int(C[1] - uz * 115 * (STEPS - 1))})

# ---------------------------------------------------------------- append only
for key, new in [("plateaus", plateaus), ("canyons", canyons), ("ponds", ponds), ("points", points)]:
    d.setdefault(key, []).extend(new)
for key in base:                    # nothing that was there has moved or changed
    if isinstance(base[key], list):
        assert d[key][:len(base[key])] == base[key], key
    else:
        assert d[key] == base[key], key


class Dumper(yaml.SafeDumper):
    pass


def _list(dumper, data):
    flow = all(isinstance(v, (int, float)) for v in data)
    return dumper.represent_sequence("tag:yaml.org,2002:seq", data, flow_style=flow)


Dumper.add_representer(list, _list)
Dumper.add_representer(tuple, _list)
out = os.environ.get("WATER_OUT") or os.path.join(HERE, "water.yaml")
with open(out, "w") as f:
    f.write("# r12 water: generated by water-gen.py from main.yaml (appends three water set pieces)\n")
    yaml.dump(d, f, Dumper=Dumper, sort_keys=False, default_flow_style=False)
print(f"wrote water.yaml: +{len(plateaus)} plateaus, +{len(canyons)} canyons, +{len(ponds)} ponds, "
      f"+{len(points)} points")
