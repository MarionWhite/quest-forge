"""Round 9 main: the r8 enchanted map with a great lake between the grassland and the enchanted
quarter. Run from the repo root: py -3.10 docs/design/world/r9/main-gen.py"""
import math, yaml, numpy as np

s = yaml.safe_load(open("docs/design/world/r8/enchanted.yaml", encoding="utf-8"))
LX, LZ, RX, RZ = 4300.0, 2000.0, 3300.0, 2900.0


def lake_outline(n=240):
    """Polar outline: low harmonics for bays, narrow negative bumps for peninsulas."""
    g = np.random.default_rng(91)
    terms = [(k, g.uniform(0, 6.283), 0.20 / k ** 0.85) for k in range(2, 30)]
    pen = [(140, 0.25, 9), (62, 0.38, 10), (350, 0.22, 8)]    # deg (0 east, 90 south), depth, width deg
    bay = [(35, 0.14, 12), (215, 0.16, 13), (160, 0.12, 10)]
    out = []
    for i in range(n):
        t = 2 * math.pi * i / n
        d = math.degrees(t)
        f = 1 + sum(a * math.sin(k * t + ph) for k, ph, a in terms) * 0.5
        for a0, dep, w in pen:
            dd = (d - a0 + 180) % 360 - 180
            f -= dep * math.exp(-(dd / w) ** 2)
        for a0, dep, w in bay:
            dd = (d - a0 + 180) % 360 - 180
            f += dep * math.exp(-(dd / w) ** 2)
        f = max(f, 0.4)
        out.append([round(LX + RX * f * math.cos(t)), round(LZ + RZ * f * math.sin(t))])
    return out


def arm(path, r0, r1, step=260):
    """A lake arm: a chain of shrinking circles along a path."""
    pts = np.array(path, float)
    seg = np.hypot(*np.diff(pts, axis=0).T)
    cum = np.concatenate([[0], np.cumsum(seg)])
    out = []
    for t in np.arange(0, cum[-1] + 1, step):
        k = min(np.searchsorted(cum, t, side="right") - 1, len(seg) - 1)
        p = pts[k] + (pts[k + 1] - pts[k]) * (t - cum[k]) / (seg[k] or 1)
        out.append({"circle": [round(p[0]), round(p[1]), round(r0 + (r1 - r0) * t / cum[-1])]})
    return out


body = lake_outline()
arms = (arm([[7000, 500], [7800, -300], [8300, -1300], [8100, -2500]], 700, 280)       # NE arm into the Mystic Grove
        + arm([[2700, -300], [2200, -1100], [2000, -2000]], 520, 240)                  # NW arm into the autumn woods
        + arm([[2400, 4300], [1900, 5100], [1400, 5700]], 650, 300))                  # SW arm, the outflow
lakes = [{"polygon": body}] + arms
s["lakes"] += lakes

# Four substantial isles, each themed to the shore it faces.
isles = [  # x, z, island r, region r, biome mix, tier, base, relief
    (2429, 1670, 950, 1100, [[229, 5], [199, 4]], 1, 72, 30),   # Seasonal Forest isle (west, grassland side)
    (4740, 358, 950, 1100, [[185, 1]], 2, 74, 40),              # Mystic Grove isle (north)
    (6232, 2518, 850, 1000, [[29, 1]], 3, 72, 35),              # Roofed Forest isle (east, dark wood side)
    (4147, 3550, 850, 1000, [[87, 1]], 2, 70, 30),              # Fungi Forest isle (south)
]
new = []
for x, z, ir, rr, mix, tier, base, rel in isles:
    s["islands"].append({"circle": [x, z, ir]})
    reg = {"tier": tier, "base": base, "relief": rel, "circle": [x, z, rr], "exact": True}
    reg.update({"biome": mix[0][0]} if len(mix) == 1 else {"biomes": mix, "patch": 700})
    new.append(reg)

R = s["regions"]
def cell(at):
    return next(r for r in R if r.get("at") == at)

# West shore: friendly grassland; the autumn band runs from the volcano's foot to the north shore.
cell([640, 2708]).update({"at": [100, 3300], "biomes": [[138, 3], [169, 1]], "size": 1.0})
cell([1758, -4000]).update({"at": [1500, -2600], "biomes": [[229, 5], [199, 4]], "tier": 1,
                            "base": 72, "relief": 40, "patch": 2500, "lakes": [6, 80, 220], "size": 0.75})
# North shore: lakeland (Shield, Land of Lakes) under the mega taiga.
R.append({"tier": 2, "biomes": [[145, 1], [235, 1]], "base": 68, "relief": 35, "patch": 2500,
          "lakes": [22, 90, 320], "at": [4600, -4200], "size": 0.75})
cell([5198, -8128]).update({"at": [4800, -8300], "biomes": [[160, 3], [32, 2], [66, 1]]})
cell([-3660, -8128]).update({"biomes": [[74, 1], [141, 1]]})            # Heathland uplands
cell([13110, -7870]).update({"biomes": [[239, 3], [59, 2], [66, 1]]})   # Alps Forest foothills
# East shore: the enchanted quarter, fairy edge on the water deepening into dark woods.
cell([6660, -990]).update({"at": [8900, -2300], "biomes": [[185, 4], [197, 1]], "size": 0.7})   # Mystic Grove
R.append({"tier": 1, "biomes": [[132, 1], [88, 1]], "base": 68, "relief": 25, "patch": 1800,
          "at": [8300, 1700], "size": 0.65})                                     # fairy edge
R.append({"tier": 3, "biomes": [[29, 4], [87, 1]], "base": 72, "relief": 40, "patch": 2000,
          "at": [11300, 300], "size": 0.6})                                      # Roofed Forest dark wood
# South shore: Lush Swamp around the outflow; Eucalyptus in the warm south.
R.append({"tier": 1, "biomes": [[152, 3], [159, 1]], "base": 63, "relief": 8, "patch": 1500,
          "at": [4300, 6000], "size": 0.5})
R.append({"tier": 2, "biomes": [[83, 3], [190, 1]], "base": 74, "relief": 40, "patch": 2500,
          "at": [5600, 10000], "size": 0.6})
# Jade Cliffs beside the Cherry Blossom Grove.
R.append({"tier": 2, "biome": 143, "base": 105, "relief": 150, "at": [-7000, 6300], "size": 0.45})

# Corrupted core moves east, so the Mystic Grove has room between it and the lake.
DX, DZ = 1800, -300
for r in R:
    if r.get("circle", [None])[:2] == [10500, -3200]:
        r["circle"][0] += DX; r["circle"][1] += DZ
for p in s["ponds"]:
    if p["at"] in ([11300, -2600], [9700, -3900]):
        p["at"] = [p["at"][0] + DX, p["at"][1] + DZ]
for p in s["points"]:
    if p.get("name") == "Corrupted core":
        p["x"] += DX; p["z"] += DZ
cell([13540, -1420]).update({"at": [14600, -1800]})
# The tropical isle's circle grows to own its outlying islets (r8 leaked Ominous Woods onto one).
for r in R:
    if r.get("circle", [None])[:2] == [15002, 12856]:
        r["circle"][2] = 5800
        r["biomes"] = [[246, 3], [195, 2], [62, 1]]

# Ice Plains Spikes around the Ice castle (after the castle's own circle, so the castle keeps it).
k = next(i for i, r in enumerate(R) if r.get("circle", [None])[:2] == [7520, -16298])
R.insert(k + 1, {"tier": 3, "biome": 140, "base": 70, "relief": 25, "circle": [7520, -16298, 2400]})

s["regions"] = new + R
for l in lakes:   # freshwater over the lake (after the sea bands, so it wins)
    s["regions"].append(dict(biome=7, sea=True, exact=True, **l))

# Rivers: the east river feeds the lake, a black river drains the core into the NE arm, and
# the great river leaves the SW arm for the southern gulf.
riv = s["rivers"]
riv[0]["points"] = [[10960, 2450], [9300, 3300], [7300, 3000]]
riv[0].update({"width": 64, "meander": 300})
riv[1]["points"] = [[1400, 5700], [1100, 6900], [640, 8212], [-1682, 8040]]
riv[1].update({"width": 120, "meander": 380, "valley": 300, "biome": 150})
riv[3]["points"] = [[8380, 11910], [7262, 9244], [5300, 7600], [2000, 6600]]
riv.append({"points": [[12300, -3500], [10600, -2300], [8100, -2100]], "width": 72, "meander": 300, "biome": 79})
riv.append({"points": [[4600, -6500], [4500, -3500], [4300, -500]], "width": 40})
riv[-3]["points"][0] = [12300, -3500]   # the old core river, now from the moved core
for p in s["points"]:
    if p.get("kind") == "spawn" and p.get("x") == 640 and p.get("z") == 3912:
        p["x"], p["z"] = -600, 3600

hdr = ("# Round 9 main: r8 enchanted + a great lake (~6 km) between the grassland (west shore) and the\n"
       "# enchanted quarter (east shore); four themed isles; generated by main-gen.py.\n")
open("docs/design/world/r9/main.yaml", "w", encoding="utf-8").write(
    hdr + yaml.safe_dump(s, sort_keys=False, default_flow_style=None, width=140))
print("ok")
