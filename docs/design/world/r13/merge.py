"""r13: r12 main plus every r12 feature slot (water, strange, frozen, coast), plus the r13
additions in r13/additions.yaml (south and south-east landmarks, passes through the divide).

Each r12 slot only appended to r12/main.yaml (new regions prepended), so the merge takes each
slot's additions and stacks them onto one copy of the base.
Run: py -3.10 merge.py
"""
import os
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
R12 = os.path.join(HERE, "..", "r12")
base = yaml.safe_load(open(os.path.join(R12, "main.yaml"), encoding="utf-8"))
out = yaml.safe_load(open(os.path.join(R12, "main.yaml"), encoding="utf-8"))
new_regions = []
sources = [yaml.safe_load(open(os.path.join(R12, f"{s}.yaml"), encoding="utf-8")) for s in ["water", "strange", "frozen", "coast"]]
for s in sources:
    for key, val in s.items():
        if isinstance(val, list) and key in base:
            have = base[key]
            if key == "regions":
                new_regions += val[:len(val) - len(have)]
            else:
                out[key] += val[len(have):]
        elif isinstance(val, list):
            out.setdefault(key, []).extend(val)
add_path = os.path.join(HERE, "additions.yaml")
if os.path.exists(add_path):
    add = yaml.safe_load(open(add_path, encoding="utf-8")) or {}
    new_regions = add.pop("regions", []) + new_regions
    for key, val in add.items():
        out.setdefault(key, []).extend(val)
out["regions"] = new_regions + out["regions"]

# --- r13 fixups, after the author's review --------------------------------------------------
import math
# Spire field: the hand-made cone grid looked stamped. Vanilla Ice Plains Spikes (140) grows
# real ice spikes by itself, so drop the cones and paint an irregular patch of that biome.
out["ridges"] = [r for r in out["ridges"]
                 if not (r.get("biome") == 140 and r.get("width", 999) < 300
                         and math.hypot(r["points"][0][0] - 6300, r["points"][0][1] + 17000) < 2000)]
spikes = [[6300 + rr * math.cos(a), -17000 + rr * math.sin(a)] for a, rr in
          zip([i * math.pi / 6 for i in range(12)], [1300, 1050, 1450, 1150, 1350, 950, 1250, 1500, 1100, 1300, 1000, 1400])]
out["regions"].insert(0, {"tier": 4, "biome": 140, "base": 70, "relief": 20, "exact": True,
                          "polygon": [[int(x), int(z)] for x, z in spikes]})
# Tidal lagoon: the salt marsh behind the spit was a rectangle; follow the shore instead.
for r in out["regions"]:
    if r.get("polygon") == [[-8600, 15750], [-6350, 15700], [-6300, 16480], [-8600, 16520]]:
        r["polygon"] = [[-8600, 16050], [-8150, 15780], [-7700, 15900], [-7250, 15720], [-6800, 15860],
                        [-6380, 16120], [-6450, 16420], [-6950, 16300], [-7500, 16450], [-8050, 16380], [-8500, 16520]]

# --- fixes after the r13 in-game test (r13-ingame-test.md, "Fixes and re-test") --------------
import random
import sys
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "..", "tools", "world"))
import plan  # noqa: E402  (noise only)


def centre(p):
    if "circle" in p:
        return p["circle"][:2]
    pts = p["polygon"]
    return [sum(x for x, _ in pts) / len(pts), sum(z for _, z in pts) / len(pts)]


def near(p, x, z, r):
    c = centre(p)
    return math.hypot(c[0] - x, c[1] - z) < r


def circle(x, z, r, n=48):
    return [[int(x + r * math.cos(2 * math.pi * i / n)), int(z + r * math.sin(2 * math.pi * i / n))] for i in range(n)]


# 1. Calving bay: open dark water, not pack ice. RWG Ice Ocean (210) freezes over by its stored
# temperature, so the bay round the berg field becomes vanilla Deep Ocean (24), which never
# freezes. Sea regions paint in list order (last wins), so it goes at the end. A basin deepens it
# so it reads dark between the bergs. Bergs and the snout get packed-ice ground, and glacier
# coasts lose the automatic Beach ring (a berg is ice down to the water, not an island).
CALV = (13150, -21300)
out["regions"].append({"biome": 24, "sea": True, "exact": True, "polygon": circle(CALV[0], CALV[1], 2300)})
out.setdefault("basins", []).append({"circle": [CALV[0], CALV[1] - 200, 2400], "floor": 34, "wall": 700})
for p in out["plateaus"]:
    if p.get("biome") == 89 and near(p, 13150, -21000, 2700):
        p["surface"] = "packed_ice"
out["beach_skip"] = [89]

# 3. Tepui: with the block-resolution plateau recut, `wall` is the real wall width; 12 blocks of
# run for an 80-block drop is a cliff.
for p in out["plateaus"]:
    if p.get("circle") == [15500, 13000, 1050]:
        p["wall"] = 12

# 5. Meteor crater: BoP Wasteland decorates 10 poison and 2 water lakes per chunk (the thousands
# of pools); BoP Crag decorates none. So the bowl floor, the ejecta apron and its rays become
# Crag on scorched ground; the black-sand eye stays.
CRATER = (-9400, 8900)
for p in out["plateaus"]:
    if p.get("biome") == 251 and p.get("top") == 0 and near(p, CRATER[0], CRATER[1], 1700):
        p["biome"] = 77
        p["surface"] = "scorched"
for c in out["canyons"]:
    if math.hypot(c["points"][0][0] - CRATER[0], c["points"][0][1] - CRATER[1]) < 50 and c.get("floor_biome") == 251:
        c["floor_biome"] = 77
out["surfaces"].insert(0, {"material": "scorched", "circle": [CRATER[0], CRATER[1], 1000]})
# Re-test 3: the bowl floor sat at sea level (62), so the sea flooded half of it and pocked the
# rest. A shallower cut (36 -> 22) puts the floor at about 77, well above the sea, and one pond in
# the black-sand eye holds the only water in the bowl.
for c in out["canyons"]:
    if math.hypot(c["points"][0][0] - CRATER[0], c["points"][0][1] - CRATER[1]) < 50:
        c["depth"] = 22
out["ponds"].append({"at": [CRATER[0], CRATER[1]], "r": 260, "depth": 7, "aspect": 1.15, "rot": 0.4})

# 6. Hot-spring terraces: open treads, and pools covering 30-50% of every tread instead of 3-4%.
# Sacred Springs decorates 30 trees a chunk (sacred oaks among them), so only the crown keeps it;
# the treads and their pools are BoP Shrubland (236): 1 tree a chunk, bushes and flowers. Each pool's level is pinned to its own tread (top - 1), so none takes a lower
# tread's level, and each keeps 1.6 radii clear of its tread's downhill lip, so none spills over.
HOT = (-6000, 1800)
SEED = out.get("seed", 1)
terr = sorted([p for p in out["plateaus"] if p.get("wall") == 6 and p.get("relief") == 6 and near(p, HOT[0], HOT[1], 1500)],
              key=lambda p: p["top"])
assert len(terr) == 6, len(terr)
is_hot = lambda p: p.get("biome") == 197 and math.hypot(p["at"][0] - HOT[0], p["at"][1] - HOT[1]) < 1500
out["ponds"] = [p for p in out["ponds"] if not (is_hot(p) and p["r"] != 75)]   # keep the crown's vent
TREAD = 236
for p in terr[:-1]:
    p["biome"] = TREAD
terr[-1]["biome"] = 197                                                         # the crown
# Tread masks at 4 blocks per pixel, warped exactly as plan.py warps plateau outlines.
G4, gn = 4, 650
gx0, gz0 = HOT[0] - 1300, HOT[1] - 1300
gx, gz = np.meshgrid(gx0 + (np.arange(gn) + 0.5) * G4, gz0 + (np.arange(gn) + 0.5) * G4)
wx = gx + 0.3 * 600 * plan.fbm(gx, gz, 2400, 4, SEED + 1)
wz = gz + 0.3 * 600 * plan.fbm(gx, gz, 2400, 4, SEED + 2)
jj = np.clip(((wx - gx0) / G4).astype(int), 0, gn - 1)
ii = np.clip(((wz - gz0) / G4).astype(int), 0, gn - 1)


def tmask(p):
    im = Image.new("L", (gn, gn), 0)
    ImageDraw.Draw(im).polygon([((x - gx0) / G4, (z - gz0) / G4) for x, z in p["polygon"]], fill=255)
    return (np.asarray(im) > 0)[ii, jj]


masks = [tmask(p) for p in terr]
rng = random.Random(1313)
for k, p in enumerate(terr[:-1]):
    above = np.zeros_like(masks[k])
    for m in masks[k + 1:]:
        above |= m
    tread = masks[k] & ~above
    d_lip = ndimage.distance_transform_edt(masks[k]) * G4       # to this tread's downhill lip
    d_riser = ndimage.distance_transform_edt(~above) * G4       # to the riser of the tread above
    cand = list(zip(*np.nonzero(tread)))
    rng.shuffle(cand)
    placed, area, tarea = [], 0.0, tread.sum() * G4 * G4
    for i, j in cand:
        if area > 0.42 * tarea:
            break
        r = min(95.0, d_lip[i, j] / 1.6, d_riser[i, j] / 1.05)
        if r < 32:
            continue
        x, z = gx[i, j], gz[i, j]
        if any(math.hypot(x - a, z - b) < (r + rb) * 1.08 for a, b, rb in placed):
            continue
        asp = rng.uniform(1.0, 1.5)
        placed.append((x, z, r))
        area += math.pi * r * r / asp
        out["ponds"].append({"at": [int(x), int(z)], "r": int(r), "depth": 5, "aspect": round(asp, 2),
                             "rot": round(rng.uniform(0, math.pi), 3), "biome": TREAD, "level": p["top"] - 1})
    print(f"hot springs tread {p['top']}: {len(placed)} pools, ~{100 * area / tarea:.0f}% of the tread (planned)")

# Spawns come from the r14 difficulty layer (ten rated spawns, spread over the whole map);
# tiers live there too (difficulty.py), so the old per-region spawn points are replaced.
_diff = yaml.safe_load(open(os.path.join(HERE, "..", "r14", "difficulty.yaml"), encoding="utf-8"))
out["points"] = [p for p in out["points"] if p.get("kind") != "spawn"] + [
    {"kind": "spawn", "name": f"Spawn: {s['where']}", "x": s["x"], "z": s["z"]} for s in _diff["spawns"]]

with open(os.path.join(HERE, "main.yaml"), "w", encoding="utf-8", newline="\n") as f:
    f.write("# r13 main: r12 main + all r12 feature slots + r13/additions.yaml (generated by merge.py)\n")
    yaml.safe_dump(out, f, sort_keys=False, default_flow_style=None, width=140)
print("added:", {k: len(out[k]) - len(base.get(k, [])) for k in out if isinstance(out[k], list)})
