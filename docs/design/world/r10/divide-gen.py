# Round 10, Great Divide: r9 thousand with one continental divide as the continent's skeleton.
#   py -3.10 docs/design/world/r10/divide-gen.py     (run from the repo root)
# The divide arcs from the north-west coast (the glacial caldera's side), along the north and down
# the east to the Maelstrom bay. The heartland inside the arc is the wet windward side; the north
# strip and the east steppe peninsula lie in its rain shadow. Rivers come from auto_rivers.
import yaml, math

s = yaml.safe_load(open("docs/design/world/r9/thousand.yaml", encoding="utf-8"))
OLD = (-4520, -1850)
DX, DZ = -4000, 1700          # the whole volcano complex moves west and a little south
NEW = (OLD[0] + DX, OLD[1] + DZ)

def at_old(c):
    return abs(c[0] - OLD[0]) < 1 and abs(c[1] - OLD[1]) < 1

def mv(c):
    c[0] += DX; c[1] += DZ

# ---------------------------------------------------------------- the volcano complex, moved as one
for l in s["lakes"]:
    if at_old(l["circle"]): mv(l["circle"])
for i in s["islands"]:
    if "circle" in i and at_old(i["circle"]): mv(i["circle"])
for f in s["surfaces"]:
    if at_old(f["circle"]): mv(f["circle"])
for r in s["regions"]:
    if "circle" in r and at_old(r["circle"]): mv(r["circle"])
for rg in s["ridges"]:
    if "arc" in rg and at_old(rg["arc"]): mv(rg["arc"])
    if "points" in rg and at_old(rg["points"][0]):
        for p in rg["points"]: mv(p)
        rg["height"] = 245     # the cone: the noise under the new site is lower, so lift it back to r9's look
for r in s["regions"]:
    if r.get("sea") and "circle" in r and r["circle"][:2] == list(NEW):
        r["exact"] = True      # region warp is position-dependent; pin the crater water's Volcano biome

# ---------------------------------------------------------------- the divide
import numpy as np
rng = np.random.default_rng(1010)
# The crest line: a smooth arc through these points, cut into ~2.3 km massifs. Small notches
# between massifs, three real passes, a zigzag so the crest never runs ruler-straight.
ARC = [[-15000, -9900], [-12600, -8200], [-10200, -6900], [-7500, -6100], [-4500, -5900], [-1500, -6300],
       [1500, -6700], [4500, -6200], [7500, -6300], [10200, -6100], [12600, -4900], [14000, -2600],
       [14400, 0], [14200, 2200], [13500, 3900]]
def catmull(P, per=12):
    P = [P[0]] + P + [P[-1]]
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = map(np.array, P[i - 1:i + 3])
        for u in np.linspace(0, 1, per, endpoint=False):
            out.append(0.5 * (2 * p1 + (-p0 + p2) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u * u + (-p0 + 3 * p1 - 3 * p2 + p3) * u ** 3))
    out.append(np.array(P[-2], float))
    return np.array(out)
line = catmull(ARC)
cum = np.concatenate([[0], np.cumsum(np.hypot(*np.diff(line, axis=0).T))])
L = cum[-1]
def at(sv):
    k = min(np.searchsorted(cum, sv, side="right") - 1, len(line) - 2)
    f = (sv - cum[k]) / (cum[k + 1] - cum[k])
    p = line[k] + (line[k + 1] - line[k]) * f
    d = line[k + 1] - line[k]
    return p, np.array([-d[1], d[0]]) / np.hypot(*d)     # point, left normal (points north-east of travel = lee)
PASSES = [0.25, 0.52, 0.76, 0.9]       # arc fractions: real passes, 1.4-1.8 km wide
CREST, GLACIER, SPURS = [], [], []
sv, side, i = 0.0, 1, 0
while sv < L - 400:
    seg = rng.uniform(1900, 2700)
    e = min(L, sv + seg)
    pts = []
    for u in np.linspace(sv, e, 4):
        p, nrm = at(u)
        pts.append((p + nrm * side * rng.uniform(0, 380) * (1 if u not in (sv, e) else 0.4)).round().tolist())
    frac = (sv + e) / 2 / L
    h = 216 + 16 * math.sin(i * 2.1) * rng.uniform(0.6, 1) - (34 if frac > 0.9 else 0) - (12 if frac < 0.12 else 0)
    w = rng.uniform(2300, 3100) * (0.75 if frac > 0.9 else 1)
    CREST.append((pts, round(h), round(w)))
    if h >= 220 and frac < 0.9:
        GLACIER.append(pts[1:3])
    # spurs from this massif's middle, alternately to the lee (north/east) and the windward side
    for sd in (1, -1):
        if rng.random() < (0.85 if sd == 1 else 0.6):
            p, nrm = at((sv + e) / 2 + rng.uniform(-500, 500))
            ang = rng.uniform(-0.6, 0.6)
            dvec = np.array([nrm[0] * math.cos(ang) - nrm[1] * math.sin(ang), nrm[0] * math.sin(ang) + nrm[1] * math.cos(ang)]) * sd
            ln = rng.uniform(1500, 2600) * (1.25 if sd == 1 else 0.8)
            a0 = p + dvec * 700
            a1 = a0 + dvec * ln * 0.55
            bend = np.array([-dvec[1], dvec[0]]) * rng.uniform(-0.4, 0.4)
            a2 = a1 + (dvec + bend) * ln * 0.45
            a3 = a2 + (dvec + bend * 2) * rng.uniform(700, 1300)
            SPURS.append(([a0.round().tolist(), a1.round().tolist(), a2.round().tolist()], round(h - rng.uniform(40, 60)), round(rng.uniform(1100, 1500))))
            SPURS.append(([(a2 + (dvec + bend) * 320).round().tolist(), a3.round().tolist()], round(h - rng.uniform(75, 95)), round(rng.uniform(800, 1100))))
    gap = 1600 if any(abs(e / L - q) < seg / L / 2 + 0.02 for q in PASSES) else rng.uniform(250, 550)
    sv, side, i = e + gap, -side, i + 1
# keep spurs out of the lake, the volcano and the corrupted core
def clear(pt):
    x, z = pt
    return not (math.hypot(x - NEW[0], z - NEW[1]) < 4200 or math.hypot(x - 10500, z - 3200 * -1) < 2900
                or (-2600 < x < 9000 and -2900 < z < 6500))
SPURS = [s_ for s_ in SPURS if all(clear(q) for q in s_[0])]
SPURS.append(([[-9800, -5300], [-9300, -4400], [-9100, -3700]], 170, 1300))     # the west foothills, down to the volcano
ridges = [r for r in s["ridges"] if r.get("points") != [[10960, -9848], [14400, -7010], [15518, -2710]]]   # the old NE alps join the divide
allpts = [p for pts, _, _ in CREST for p in pts]
ridges.append({"points": allpts, "height": 116, "width": 9000, "relief": 110})             # the foothill swell under the whole range
for pts, h, w in CREST:
    ridges.append({"points": pts, "height": h, "width": w, "relief": 230, "biome": 60, "biome_above": 0.62})
for pts in GLACIER:
    ridges.append({"points": pts, "height": 62, "width": 1500, "relief": 230, "biome": 89, "biome_above": 0.6})
for pts, h, w in SPURS:
    ridges.append({"points": pts, "height": h, "width": w, "relief": 190})
s["ridges"] = ridges

# ---------------------------------------------------------------- regions: windward wet, lee dry
R = s["regions"]
def cell(at):
    return next(r for r in R if r.get("at") == at)
# Lee: the north strip and the east peninsula.
cell([-3660, -8128]).update({"biomes": [[66, 3], [241, 2], [247, 1]], "lakes": [4, 100, 300]})          # Boreal, Spruce Woods, Tundra
cell([5198, -8128]).update({"biomes": [[247, 3], [242, 2], [66, 1]], "lakes": [3, 100, 300], "relief": 50})   # Tundra, Steppe, Boreal
cell([13110, -7870]).update({"biomes": [[247, 2], [59, 2], [66, 1]]})                                   # Tundra, Alps Forest, Boreal
st = cell([16550, -216]); st.update({"biomes": [[242, 3], [236, 2], [254, 1], [193, 1]], "size": 0.8, "lakes": [0, 100, 300]})
cell([13540, -1420])["at"] = [12000, -900]                                                              # Ominous Woods stays inside the arc
# Windward: the heartland face of the divide gets rainforest.
cell([-10970, -560]).update({"at": [-12200, -4300]})                                                    # Maple Woods between redwoods and volcano
cell([-8800, 3600]).update({"at": [-9600, 4800]})                                                       # Seasonal band below the volcano
for r in R:
    if r.get("circle") == [-11400, 2450, 559]:
        r["circle"] = [-11900, 4900, 559]                                                               # Mystic Grove out of the volcano band
R += [
    {"tier": 2, "biomes": [[243, 3], [32, 2]], "base": 84, "relief": 80, "patch": 2600, "lakes": [8, 100, 300], "at": [-7000, -4700], "size": 0.75},   # Temperate Rainforest, Mega Taiga
    {"tier": 2, "biomes": [[32, 3], [74, 2], [243, 1]], "base": 84, "relief": 75, "patch": 2600, "lakes": [8, 100, 300], "at": [-1600, -5000], "size": 0.7},
    {"tier": 2, "biomes": [[243, 3], [160, 2]], "base": 82, "relief": 70, "patch": 2600, "lakes": [6, 100, 300], "at": [8600, -5300], "size": 0.6},
]

# ---------------------------------------------------------------- rivers: auto, plus the special ones
riv = s["rivers"]
keep = [riv[1]]                                                                                        # the lake's great outflow to the gulf
keep.append({"points": [[10500, -3200], [9700, -1500], [8500, 0]], "width": 48, "meander": 320, "biome": 79})   # the core's Dead Swamp river into the east arm
keep.append({"points": [[15300, -1600], [17000, -300], [19600, 1000]], "width": 40, "meander": 400, "dry": True, "depth": 5, "biome": 82})   # a Dry River in the steppe
keep.append({"points": [[15000, 1600], [16900, 2700], [18600, 3600]], "width": 32, "meander": 350, "dry": True, "depth": 4, "biome": 82})
s["rivers"] = keep
s["auto_rivers"] = {"cell": 128, "threshold_km2": 10, "min_width": 14, "max_width": 100}

hdr = ("# Round 10, Great Divide: r9 thousand with one continental divide from the north-west coast to the\n"
       "# Maelstrom bay; wet windward heartland, dry lee in the north and east; volcano moved (%+d, %+d).\n"
       "# Generated by divide-gen.py.\n" % (DX, DZ))
open("docs/design/world/r10/divide.yaml", "w", encoding="utf-8").write(hdr + yaml.safe_dump(s, sort_keys=False, default_flow_style=None, width=140))
print("volcano at", NEW, "crest", len(CREST), "spurs", len(SPURS), "glacier", len(GLACIER))
