# Round 9, Thousand Islands: r8 enchanted with a many-armed lakeland lake in the middle.
#   py -3.10 docs/design/world/r9/thousand-gen.py     (run from the repo root)
import yaml, math, numpy as np
from scipy import ndimage
from scipy.spatial import ConvexHull

s = yaml.safe_load(open("docs/design/world/r8/enchanted.yaml", encoding="utf-8"))
rng = np.random.default_rng(909)

# ---------------------------------------------------------------- the lake: a branching tree of arms
# Each arm is a polyline with a start and end width; it becomes a chain of jittered circles,
# so shores get bays and capes. The core is a few big overlapping basins.
CORE = [[2600, 2500, 1500], [3900, 3200, 1250], [1900, 3700, 1000], [4300, 1900, 1050], [3000, 1300, 900]]
ARMS = [  # points, w0, w1
    ([[4300, 1900], [5500, 700], [6600, -400], [7500, -1700]], 950, 380),      # NE arm into the enchanted quarter
    ([[5500, 700], [5100, -900], [5500, -2500]], 520, 240),                    #   its north finger
    ([[6600, -400], [7700, 300], [8500, 0]], 420, 220),                        #   its east finger
    ([[3000, 1300], [2400, -100], [2700, -1600], [2200, -2800]], 720, 260),    # north arm
    ([[2400, -100], [1100, -700], [300, -500]], 440, 200),                     #   its west finger
    ([[1300, 3000], [0, 2300], [-1200, 2600], [-2100, 1700]], 820, 300),       # west arm toward the volcano
    ([[0, 2300], [-600, 3800], [-1600, 4500]], 520, 240),                      #   its south finger
    ([[-1200, 2600], [-1500, 1200], [-1000, 200]], 380, 200),                  #   its north finger
    ([[1800, 4300], [900, 5300], [-100, 5900]], 620, 300),                     # south-west arm
    ([[3500, 4200], [3700, 5400], [3200, 6500]], 700, 380),                    # south arm, the outflow
    ([[4700, 3700], [5800, 4500], [6800, 4800]], 700, 300),                    # south-east arm
    ([[5800, 4500], [6000, 5700]], 360, 200),                                  #   its south finger
    ([[4900, 2700], [6300, 2400], [7500, 3000], [8500, 2500]], 700, 300),      # east arm, fed by the east river
    ([[7500, 3000], [7800, 4000]], 340, 180),                                  #   its south finger
]
lakes, arm_hulls = [], []
for x, z, r in CORE:
    lakes.append([x, z, r])
arm_hulls.append([[x + r * math.cos(t), z + r * math.sin(t)] for x, z, r in CORE for t in np.linspace(0, 6.28, 24)])
for pts, w0, w1 in ARMS:
    w0, w1 = w0 * 1.6, w1 * 1.5   # wide enough to hold islands, so each arm is a maze of channels
    pts = np.array(pts, float)
    seg = np.diff(pts, axis=0)
    L = np.hypot(*seg.T)
    cum = np.concatenate([[0], np.cumsum(L)])
    t, circ = 0.0, []
    while t <= cum[-1]:
        k = min(np.searchsorted(cum, t, side="right") - 1, len(seg) - 1)
        f = (t - cum[k]) / L[k]
        p = pts[k] + seg[k] * f
        nrm = np.array([-seg[k][1], seg[k][0]]) / L[k]
        r = (w0 + (w1 - w0) * t / cum[-1]) / 2 * rng.uniform(0.85, 1.15)
        r *= 1 + 0.45 * max(0.0, math.sin(t / 900 + len(lakes)))   # bulges: open bays between narrows
        p = p + nrm * rng.normal(0, r * 0.18)
        circ.append([float(p[0]), float(p[1]), float(r)])
        t += r * 0.75
    lakes += circ
    arm_hulls.append([[x + r * math.cos(a), z + r * math.sin(a)] for x, z, r in circ for a in np.linspace(0, 6.28, 16)])
# Short inlets and coves off every shore, so the outline never reads as a tube.
for _ in range(16):
    x, z, r = lakes[rng.integers(len(lakes))]
    a = rng.uniform(0, 6.283)
    rr = rng.uniform(180, 300)   # a short fjord-like inlet: three shrinking circles outward
    for j, f in enumerate((0.5, 1.2, 1.8)):
        lakes.append([x + (r + rr * f) * math.cos(a), z + (r + rr * f) * math.sin(a), rr * (1 - 0.25 * j)])
s["lakes"] = [l for l in s["lakes"] if l["circle"][0] < -4000] + [{"circle": [round(x), round(z), round(r)]} for x, z, r in lakes]

# Rasterise the lake at 32 blocks to place islands where water surrounds them.
G, X0 = 32, -4000
W, H = 14000 // G, 12000 // G
gx, gz = np.meshgrid(X0 + (np.arange(W) + 0.5) * G, -4000 + (np.arange(H) + 0.5) * G)
wet = np.zeros((H, W), bool)
for x, z, r in lakes:
    wet |= np.hypot(gx - x, gz - z) < r
dist = ndimage.distance_transform_edt(wet) * G
islands, taken = [], np.zeros_like(wet)
sizes = [820, 760, 700, 620] + [520] * 5 + [400] * 8 + [300] * 16 + [220] * 26 + [160] * 34 + [120] * 30
for target in sizes:
    for _ in range(400):
        iz, ix = rng.integers(H), rng.integers(W)
        r = target * rng.uniform(0.8, 1.15)
        if dist[iz, ix] < r * 0.95 + 140:
            continue
        x, z = gx[iz, ix], gz[iz, ix]
        if any(math.hypot(x - a, z - b) < r + c + 90 for a, b, c in islands):
            continue
        islands.append([float(x), float(z), float(r)])
        break
s["islands"] = [i for i in s["islands"] if "ring" in i or not (-3000 < i["circle"][0] < 9000 and -4000 < i["circle"][1] < 8000)]
s["islands"] += [{"circle": [round(x), round(z), round(r)]} for x, z, r in islands]
big = sorted(islands, key=lambda i: -i[2])

# ---------------------------------------------------------------- regions
R = s["regions"]
def cell(at):
    return next(r for r in R if r.get("at") == at)
cell([640, 2708]).update({"biomes": [[235, 3], [145, 3], [141, 1]], "patch": 3200, "lakes": [16, 80, 260], "relief": 35})   # lakeland
cell([5198, -8128]).update({"biomes": [[160, 3], [66, 2]]})                    # Mega Spruce Taiga north
cell([-3660, -8128]).update({"biomes": [[74, 3], [32, 2]]})                    # Mega Taiga in the conifers
cell([13110, -7870]).update({"biomes": [[239, 3], [59, 2], [66, 1]]})          # Alps Forest on the alps flanks
cell([6660, -990]).update({"biomes": [[185, 1]], "size": 0.7})                 # the enchanted heart
next(r for r in R if r.get("circle") == [15002, 12856, 4300]).update({"biomes": [[246, 2], [195, 2], [62, 1]]})
R.append({"tier": 1, "biomes": [[229, 3], [199, 2]], "base": 76, "relief": 45, "patch": 2600,
          "lakes": [6, 100, 300], "at": [-8800, 3600], "size": 0.8})          # autumn band
R.append({"tier": 1, "biomes": [[83, 1]], "base": 72, "relief": 40, "at": [6200, 10200], "size": 0.45})   # eucalyptus
frost = next(k for k, r in enumerate(R) if r.get("circle") == [7520, -16298, 688])
R.insert(frost + 1, {"tier": 3, "biome": 140, "base": 70, "relief": 25, "circle": [7520, -16298, 2300]})
new = [
    # enchanted quarter grows down the NE and north arms: fairy edge, then dark wood.
    {"tier": 2, "biome": 132, "base": 70, "relief": 30, "circle": [5300, 400, 1500]},          # Flower Forest shore
    {"tier": 2, "biome": 88, "base": 70, "relief": 20, "circle": [5600, -2100, 900]},          # Garden at the north finger
    {"tier": 2, "biome": 88, "base": 70, "relief": 20, "circle": [2300, -2600, 800]},          # Garden at the north arm's head
    {"tier": 3, "biome": 29, "base": 72, "relief": 35, "circle": [8900, -300, 1600]},          # Roofed Forest between grove and core
    # lake shores
    {"tier": 1, "biome": 152, "base": 64, "relief": 8, "circle": [-300, 6000, 1000]},          # Lush Swamp bays
    {"tier": 1, "biome": 152, "base": 64, "relief": 8, "circle": [6900, 5000, 900]},
    {"tier": 1, "biome": 152, "base": 64, "relief": 8, "circle": [3300, 6600, 700]},
    {"tier": 2, "biome": 143, "base": 100, "relief": 160, "circle": [-1700, 4700, 1300]},      # Jade Cliffs over the SW finger
]
# The biggest islands get their own character; the rest are lakeland.
looks = [185, 229, 240, 88, 229, 185]
for (x, z, r), b in zip(big, looks):
    new.append({"biome": b, "base": 72, "relief": 35, "circle": [round(x), round(z), round(r * 1.25)], "exact": True})
fresh = [{"biome": 7, "sea": True, "exact": True,
          "polygon": [[round(a), round(b)] for a, b in np.array(h)[ConvexHull(np.array(h)).vertices]]} for h in arm_hulls]
corr = 2   # the corrupted core's two circles stay first
s["regions"] = R[:corr] + new + R[corr:] + fresh   # sea regions: the last one painted wins

# ---------------------------------------------------------------- rivers and points
riv = s["rivers"]
riv[0].update({"points": [[10960, 2450], [9600, 2900], [8500, 2500]]})                       # east river feeds the east arm
riv[1].update({"points": [[3200, 6500], [2300, 7400], [640, 8212], [-1682, 8040]], "width": 110,
               "meander": 380, "valley": 260})                                                 # outflow to the gulf
riv[3].update({"points": [[8380, 11910], [7262, 9244], [6000, 5700]]})
for p_ in s["points"]:
    if p_.get("x") == 640 and p_.get("z") == 3912:
        p_["x"], p_["z"] = -400, 900
s["points"].append({"name": "Thousand Islands", "kind": "landmark", "x": 2600, "z": 2500})

hdr = "# Round 9, Thousand Islands: r8 enchanted with a branching many-armed lake in the lakeland middle.\n# Generated by thousand-gen.py.\n"
open("docs/design/world/r9/thousand.yaml", "w", encoding="utf-8").write(hdr + yaml.safe_dump(s, sort_keys=False, default_flow_style=None, width=140))
print("lakes", len(lakes), "islands", len(islands), "big", [round(i[2]) for i in big[:6]])
