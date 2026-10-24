# Round 11, Rift: the divide, plus a rift valley on its dry (east) side, parallel to the divide's
# east limb, East-African-Rift style. Five long rift lakes step down from the north-east tundra to
# the Maelstrom coast, between stepped fault scarps (plateaus), with hot springs (BoP Sacred
# Springs), two small volcanic cones (BoP Volcano) in the rift floor, and Savanna/Brushland on the
# shoulders. The east coast moves out ~4 km to make room.
#   py -3.10 docs/design/world/r11/rift-gen.py     (run from the repo root)
import math, yaml
import numpy as np

s = yaml.safe_load(open("docs/design/world/r11/divide.yaml", encoding="utf-8"))

# ---------------------------------------------------------------- the rift axis (north -> south)
AXIS = [[15200, -8900], [16500, -6300], [17400, -3300], [17800, -300], [17500, 2600], [16900, 4900]]


def catmull(P, per=16):
    P = [P[0]] + P + [P[-1]]
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = map(np.array, P[i - 1:i + 3])
        for u in np.linspace(0, 1, per, endpoint=False):
            out.append(0.5 * (2 * p1 + (-p0 + p2) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u * u + (-p0 + 3 * p1 - 3 * p2 + p3) * u ** 3))
    out.append(np.array(P[-2], float))
    return np.array(out, float)


line = catmull(AXIS)
cum = np.concatenate([[0], np.cumsum(np.hypot(*np.diff(line, axis=0).T))])
L = float(cum[-1])


def at(f):
    """Point and east-pointing unit normal at axis fraction f; also the heading angle."""
    sv = f * L                      # past either end the axis runs on straight
    k = min(max(np.searchsorted(cum, sv, side="right") - 1, 0), len(line) - 2)
    t = (sv - cum[k]) / (cum[k + 1] - cum[k])
    p = line[k] + (line[k + 1] - line[k]) * t
    d = (line[k + 1] - line[k]) / np.hypot(*(line[k + 1] - line[k]))
    return p, np.array([d[1], -d[0]]), math.atan2(d[1], d[0])


def P(f, off):
    p, e, _ = at(f)
    return [round(float(p[0] + e[0] * off)), round(float(p[1] + e[1] * off))]


def strip(f0, f1, o0, o1, steps=10):
    fs = np.linspace(f0, f1, steps)
    return [P(f, o0) for f in fs] + [P(f, o1) for f in fs[::-1]]


# sanity: the east normal really points east in the middle of the axis
assert P(0.5, 1000)[0] > P(0.5, 0)[0]

# ---------------------------------------------------------------- coast: the east grows out
lm = s["landmasses"][3]
i0 = lm.index([16550, -9848])
i1 = lm.index([12680, 3396])
lm[i0:i1] = [[16700, -10150], [19200, -9500], [20900, -7000], [21300, -3600], [21200, -200],
             [20800, 2900], [19700, 4900], [17900, 5500], [16300, 5200], [15300, 4300], [14600, 4300]]
s["rough_zones"].append({"polygon": [[16000, -8200], [23500, -8200], [23500, 5200], [16000, 5200]], "mul": 1.4})

# ---------------------------------------------------------------- clear the lee spurs out of the rift
def in_rift(pt):
    x, z = pt
    return x > 15000 and -9200 < z < 5600
s["ridges"] = [r for r in s["ridges"] if "biome" in r or r.get("width", 0) >= 9000 or "arc" in r
               or not any(in_rift(q) for q in r["points"])]
s["rivers"] = [r for r in s["rivers"] if not r.get("dry")]

# ---------------------------------------------------------------- the graben: stepped scarps both sides
FLOOR = 1500          # half-width of the rift floor
SEG = [0.0, 0.18, 0.375, 0.57, 0.76, 1.02]   # one fault block per lake, breaks between the lakes
WEST = [176, 164, 150, 136, 120]     # the divide-side shoulder stands higher
EAST = [158, 146, 132, 118, 104]
FLOOR_TOP = [118, 105, 93, 81, 70]
for k in range(5):
    s["plateaus"].append({"polygon": strip(SEG[k] - 0.01, SEG[k + 1], -FLOOR - 2400, -FLOOR), "top": WEST[k],
                          "wall": 80, "top_relief": 14, "relief": 60})
    s["plateaus"].append({"polygon": strip(SEG[k] - 0.01, SEG[k + 1], FLOOR, FLOOR + 5200), "top": EAST[k],
                          "wall": 80, "top_relief": 12, "relief": 55})
    # the floor itself is a fault block too, one per lake, each a step below the last
    s["plateaus"].append({"polygon": strip(SEG[k] - 0.005, SEG[k + 1], -FLOOR - 100, FLOOR + 100), "top": FLOOR_TOP[k],
                          "wall": 220, "top_relief": 5, "relief": 30})

# the closed head of the rift: a horst block the floor cannot drain past
s["plateaus"].append({"polygon": strip(-0.1, 0.012, -FLOOR - 2400, FLOOR + 5200, 4), "top": 150, "wall": 80,
                      "top_relief": 14, "relief": 60})

# ---------------------------------------------------------------- regions (polygons first, so they win)
new = []
# hot springs and volcano patches on the floor
SPRINGS = [(0.165, -700, 500), (0.575, 700, 480), (0.95, -700, 560)]
for f, o, r in SPRINGS:
    x, z = P(f, o)
    new.append({"biome": 197, "base": 74, "relief": 25, "circle": [x, z, r], "exact": True})
CONES = [(0.355, 900, 182), (0.755, -900, 168)]
for f, o, h in CONES:
    x, z = P(f, o)
    new.append({"biome": 250, "base": 60, "relief": 60, "circle": [x, z, 560], "exact": True})
# the rift floor: base low, so the floor fault blocks (plateaus) set its stepped height
new.append({"tier": 2, "biomes": [[35, 3], [138, 2], [163, 1], [242, 1]], "base": 56, "relief": 30, "patch": 1100,
            "polygon": strip(-0.1, 1.15, -FLOOR - 150, FLOOR + 150), "exact": True})
# the shoulders
new.append({"tier": 1, "biomes": [[70, 3], [36, 2], [35, 2], [236, 1]], "base": 96, "relief": 60, "patch": 1500,
            "polygon": strip(-0.1, 1.15, -FLOOR - 3000, -FLOOR - 150), "exact": True})
new.append({"tier": 1, "biomes": [[35, 3], [70, 2], [190, 2], [36, 1]], "base": 92, "relief": 55, "patch": 1800,
            "polygon": strip(-0.1, 1.15, FLOOR + 150, FLOOR + 6000), "exact": True})
s["regions"] = s["regions"][:36] + new + s["regions"][36:]   # after the base landmarks (Haunted isle), before the cells
for r in s["regions"]:
    if r.get("at") == [16550, -216]:          # the old east steppe cell: what is left of it turns savanna
        r.update({"at": [19800, -6500], "biomes": [[242, 3], [70, 2], [35, 1]], "size": 0.6})

# ---------------------------------------------------------------- the rift lakes, stepping down
LAKES = [(0.09, 1000, 2.5, 0), (0.25, 1100, 2.7, 150), (0.47, 1300, 2.9, -120), (0.66, 1050, 2.5, 100),
         (0.86, 1250, 2.7, -80)]
for f, r, asp, o in LAKES:
    _, _, ang = at(f)
    s["ponds"].append({"at": P(f, o), "r": r, "aspect": asp, "rot": round(ang, 3), "depth": 14})

# ---------------------------------------------------------------- volcanic cones in the floor
for f, o, h in CONES:
    p, e, ang = at(f)
    c = P(f, o)
    s["ridges"].append({"points": [[c[0] - 180, c[1] - 120], [c[0] + 180, c[1] + 120]], "height": h,
                        "width": 1150, "relief": 200, "biome": 250, "biome_above": 0.2, "peak_spacing": 600})
    s["surfaces"].append({"material": "black_sand", "circle": [c[0], c[1], 360]})

# wadis: Dry Rivers off the east shoulder to the sea
for f in (0.2, 0.45, 0.7):
    s["rivers"].append({"points": [P(f, FLOOR + 700), P(f + 0.02, FLOOR + 2400), P(f + 0.05, FLOOR + 4600)], "width": 36,
                        "meander": 380, "dry": True, "depth": 5, "biome": 82})

# ---------------------------------------------------------------- points
for p in s["points"]:
    if p.get("kind") == "spawn" and p["x"] == 16550 and p["z"] == 644:
        p.update({"x": 20200, "z": 700})

hdr = ("# Round 11, Rift: the divide with a rift valley on its dry east side: five stepped rift lakes,\n"
       "# fault scarps both sides, hot springs and two volcanic cones on the floor. Generated by rift-gen.py.\n")
open("docs/design/world/r11/rift.yaml", "w", encoding="utf-8").write(hdr + yaml.safe_dump(s, sort_keys=False, default_flow_style=None, width=140))
print("axis length", round(L), "lakes", [P(f, o) for f, *_ , o in LAKES])
