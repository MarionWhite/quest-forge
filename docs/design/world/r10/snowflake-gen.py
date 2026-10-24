# Round 10, Snowflake: r9 Thousand Islands with the lake recut as a six-armed dendritic snowflake,
# a chill that radiates from its centre, terrain-following rivers, a mountain backbone and the
# volcano complex moved west and a little south.
#   py -3.10 docs/design/world/r10/snowflake-gen.py     (run from the repo root)
import yaml, math, numpy as np
from scipy import ndimage

s = yaml.safe_load(open("docs/design/world/r9/thousand.yaml", encoding="utf-8"))
rng = np.random.default_rng(1010)

# ---------------------------------------------------------------- 1. the volcano complex moves west/south
OLD_V = (-4520, -1850)
DV = (-3200, 800)          # every element shifts by the same offset
NEW_V = (OLD_V[0] + DV[0], OLD_V[1] + DV[1])


def at_volcano(xz, tol=5):
    return abs(xz[0] - OLD_V[0]) < tol and abs(xz[1] - OLD_V[1]) < tol


def shift(c):
    c[0] += DV[0]
    c[1] += DV[1]


for coll in ("lakes", "islands", "surfaces", "regions"):
    for item in s[coll]:
        if "circle" in item and at_volcano(item["circle"]):
            shift(item["circle"])
for rd in s["ridges"]:
    if "arc" in rd and at_volcano(rd["arc"]):
        shift(rd["arc"])
    elif "points" in rd and at_volcano(rd["points"][0]):
        for p in rd["points"]:
            shift(p)
# The Maple Woods cell moves west with it, so a band of Maple Woods keeps the crag rim off the
# Redwood Forest strip.
for r in s["regions"]:
    if r.get("at") == [-10970, -560]:
        r["at"] = [-12500, 300]
        r["size"] = 1.1

# ---------------------------------------------------------------- 2. the snowflake lake
C = np.array([2800.0, 2400.0])
HEX_R = 1500                  # the central hexagonal plate of open water
CORE_R = 950                  # the landmark island in the middle
ARMS = {-90: 4800, -30: 5200, 30: 4600, 90: 4300, 150: 4600, 210: 4800}   # angle (0 = east, 90 = south): length
ROOT_W, TIP_W = 850, 150


def u(deg):
    return np.array([math.cos(math.radians(deg)), math.sin(math.radians(deg))])


def hexagon(c, r, rot=-90):
    return [[round(c[0] + r * math.cos(math.radians(rot + 60 * k))), round(c[1] + r * math.sin(math.radians(rot + 60 * k)))]
            for k in range(6)]


lake_polys, lake_circles = [], []
water_paths = []    # (p0, p1, w0, w1) for the raster used to place islands


def strip(p0, p1, w0, w1):
    """A tapered channel from p0 to p1: a crisp quad plus a round joint at the root."""
    d = (p1 - p0) / np.linalg.norm(p1 - p0)
    n = np.array([-d[1], d[0]])
    poly = [p0 + n * w0 / 2, p1 + n * w1 / 2, p1 + d * w1 * 0.9, p1 - n * w1 / 2, p0 - n * w0 / 2]
    lake_polys.append([[round(x), round(z)] for x, z in poly])
    lake_circles.append([round(p0[0]), round(p0[1]), round(w0 / 2)])
    water_paths.append((p0, p1, w0, w1))


def width_at(t):
    return ROOT_W + (TIP_W - ROOT_W) * t


lake_polys.append(hexagon(C, HEX_R))
for ang, L in ARMS.items():
    a = u(ang)
    # The main arm, in two pieces so it narrows between beads like a real dendrite.
    strip(C + a * HEX_R * 0.7, C + a * L * 0.55, width_at(0.1), width_at(0.55))
    strip(C + a * L * 0.55, C + a * L, width_at(0.55), TIP_W)
    # A small hexagonal bay where each side pair branches, like the plates on a stellar dendrite.
    for f, b, bw in ((0.45, 0.24, 400), (0.66, 0.19, 320), (0.84, 0.11, 210)):
        root = C + a * L * f
        lake_polys.append(hexagon(root, width_at(f) * 0.55, rot=ang))
        for side in (-60, 60):
            bd = u(ang + side)
            tip = root + bd * L * b
            strip(root, tip, bw, 90)
            if f < 0.7:   # twigs: off the outer half of each long branch, pointing outward
                for g, tl in ((0.45, 0.42), (0.75, 0.25)):
                    tr = root + bd * L * b * g
                    strip(tr, tr + a * L * b * tl, bw * 0.45, 70)
                    strip(tr, tr + u(ang + 2 * side) * L * b * tl * 0.7, bw * 0.4, 60)

# Drop the r9 lake (keep only the crater lake) and its islands, then add the snowflake.
s["lakes"] = [l for l in s["lakes"] if at_volcano([l["circle"][0] - DV[0], l["circle"][1] - DV[1]])]
s["lakes"] += [{"polygon": p} for p in lake_polys] + [{"circle": c} for c in lake_circles]

# Raster of the snowflake at 32 blocks, to bead a few islands along the wide channels.
G, X0, Z0 = 32, -4000, -4000
W, H = 14000 // G, 13000 // G
gx, gz = np.meshgrid(X0 + (np.arange(W) + 0.5) * G, Z0 + (np.arange(H) + 0.5) * G)
from PIL import Image, ImageDraw
img = Image.new("L", (W, H), 0)
dr = ImageDraw.Draw(img)
for p in lake_polys:
    dr.polygon([((x - X0) / G, (z - Z0) / G) for x, z in p], fill=255)
for x, z, r in lake_circles:
    dr.ellipse([(x - r - X0) / G, (z - r - Z0) / G, (x + r - X0) / G, (z + r - Z0) / G], fill=255)
wet = np.asarray(img) > 0
dist = ndimage.distance_transform_edt(wet) * G
isl = [[float(C[0]), float(C[1]), float(CORE_R)]]
for target in [300] * 6 + [220] * 12 + [160] * 20 + [110] * 30:
    for _ in range(500):
        iz, ix = rng.integers(H), rng.integers(W)
        r = target * rng.uniform(0.8, 1.15)
        if dist[iz, ix] < r + 110:
            continue
        x, z = gx[iz, ix], gz[iz, ix]
        if any(math.hypot(x - a, z - b) < r + c + 140 for a, b, c in isl):
            continue
        isl.append([float(x), float(z), float(r)])
        break
# Ring of six islets on the hexagon's inner corners: the crystal's facets.
for k in range(6):
    p = C + u(-60 + 60 * k) * (HEX_R * 0.78)
    isl.append([float(p[0]), float(p[1]), 170.0])
s["islands"] = [i for i in s["islands"] if "ring" in i or not (-3000 < i["circle"][0] < 9000 and -4000 < i["circle"][1] < 8000)]
s["islands"].append({"polygon": hexagon(C, CORE_R, rot=-60)})   # the centre island is a hexagon
s["islands"] += [{"circle": [round(x), round(z), round(r)]} for x, z, r in isl[1:]]

# ---------------------------------------------------------------- regions
R = s["regions"]
R = [r for r in R if not (r.get("exact") and r.get("biome") in (185, 229, 240, 88) and -3000 < r["circle"][0] < 9000
                          and -4000 < r["circle"][1] < 8000)]
R = [r for r in R if not (r.get("sea") and r.get("biome") == 7)]
jade = next(k for k, r in enumerate(R) if r.get("biome") == 143)
chill = [
    {"tier": 3, "biome": 140, "base": 74, "relief": 30, "circle": [round(C[0]), round(C[1]), CORE_R + 250], "exact": True},
    {"tier": 2, "biomes": [[140, 3], [86, 3]], "base": 72, "relief": 30, "patch": 800, "circle": [round(C[0]), round(C[1]), 2300]},
    {"tier": 2, "biomes": [[86, 3], [235, 3], [140, 1]], "base": 72, "relief": 35, "patch": 800,
     "circle": [round(C[0]), round(C[1]), 3300]},
]
R = R[:jade + 1] + chill + R[jade + 1:]
# Fresh-water biome over the snowflake: River, but Frozen River in the chilled heart.
R.append({"biome": 7, "sea": True, "exact": True, "circle": [round(C[0]), round(C[1]), 6000]})
R.append({"biome": 11, "sea": True, "exact": True, "circle": [round(C[0]), round(C[1]), 2300]})
s["regions"] = R

# Central plateau: a sheer hexagonal table of Ice Plains Spikes standing out of the lake.
s["plateaus"].append({"polygon": hexagon(C, CORE_R * 0.72, rot=-60), "top": 104, "wall": 40, "top_relief": 6,
                      "relief": 30, "biome": 140, "tier": 3})

# ---------------------------------------------------------------- 3. the mountain backbone
# One long spine across the continent's north-middle, from the western coastal range to the
# north-east Alps, with a high and a low pass, southern spurs that frame the lakeland and the
# volcano, and northern spurs into the conifers.
spine = [
    ([[-14200, -7400], [-12000, -5900], [-9600, -5000], [-7400, -5300]], 205, 2000),   # west massif
    ([[-7400, -5300], [-5600, -4700]], 130, 1400),                                      # western pass
    ([[-5600, -4700], [-3800, -4300], [-1800, -4900], [200, -5900], [1600, -6900]], 228, 2300),   # central massif
    ([[1600, -6900], [3300, -7000]], 115, 1400),                                        # the low pass
    ([[3300, -7000], [5400, -6300], [7600, -6600], [9400, -8000], [10700, -9600]], 200, 2000),   # east massif to the Alps
]
spurs = [
    ([[-9600, -5000], [-11000, -3400], [-12600, -2400]], 160, 1200),     # west of the volcano
    ([[-3800, -4300], [-3500, -2600], [-2600, -900], [-3000, 1000]], 178, 1400),   # between volcano and lake
    ([[200, -5900], [900, -4300], [700, -2900]], 150, 1100),             # toward the north arm
    ([[5400, -6300], [6700, -4600], [8300, -4000]], 165, 1200),          # between enchanted quarter and core
    ([[-7400, -5300], [-7900, -7600], [-7000, -9000]], 160, 1200),       # north into the conifers
    ([[-1800, -4900], [-2300, -7200], [-1700, -8800]], 165, 1100),
    ([[7600, -6600], [7300, -8600]], 150, 1000),
]
backbone = []
for pts, hgt, wid in spine:
    backbone.append({"points": pts, "height": hgt, "width": wid, "relief": 220, "peak_spacing": 1100,
                     **({"biome": 60, "biome_above": 0.74} if hgt > 190 else {})})
for pts, hgt, wid in spurs:
    backbone.append({"points": pts, "height": hgt, "width": wid, "relief": 180, "peak_spacing": 900})
s["ridges"] += backbone

# ---------------------------------------------------------------- rivers
s["auto_rivers"] = {"cell": 128, "threshold_km2": 10, "min_width": 14, "max_width": 100}
riv = s["rivers"]
keep = []
for r in riv:
    p0 = r["points"][0]
    if p0 == [3200, 6500]:                       # the great outflow from the south arm to the gulf
        r["points"][0] = [round(C[0]), round(C[1] + ARMS[90] - 200)]
        keep.append(r)
    elif r.get("biome") == 79:                   # the Dead Swamp channel out of the corrupted core
        keep.append(r)
s["rivers"] = keep

# ---------------------------------------------------------------- points
for p_ in s["points"]:
    if p_.get("x") == -400 and p_.get("z") == 900:
        p_["x"], p_["z"] = -1300, 2400
    if p_.get("name") == "Thousand Islands":
        p_.update({"name": "Ice Plains Spikes isle", "x": round(C[0]), "z": round(C[1])})
s["points"].append({"name": "Volcano", "kind": "landmark", "x": NEW_V[0], "z": NEW_V[1]})

hdr = ("# Round 10, Snowflake: r9 Thousand Islands with a six-armed dendritic snowflake lake, a chill around its\n"
       "# centre, auto rivers, a mountain backbone, and the volcano moved by (%d, %d).\n# Generated by snowflake-gen.py.\n" % DV)
open("docs/design/world/r10/snowflake.yaml", "w", encoding="utf-8").write(
    hdr + yaml.safe_dump(s, sort_keys=False, default_flow_style=None, width=140))
print("lake polys", len(lake_polys), "islands", len(isl))
