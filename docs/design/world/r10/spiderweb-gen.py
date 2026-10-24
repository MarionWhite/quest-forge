# Round 10, Spiderweb: r9 thousand with the lake rebuilt as a web (radial arms crossed by ring
# channels, islands as the cells), a Silkglades spider island at its centre, a mountain backbone,
# terrain-following rivers and the volcano moved west.
#   py -3.10 docs/design/world/r10/spiderweb-gen.py     (run from the repo root)
import yaml, math, numpy as np
from scipy.spatial import ConvexHull

s = yaml.safe_load(open("docs/design/world/r9/thousand.yaml", encoding="utf-8"))
rng = np.random.default_rng(1010)

# ---------------------------------------------------------------- 1. the volcano moves west and a little south
OLD = (-4520, -1850)
DX, DZ = -4200, 1000
def is_volc(c):
    return abs(c[0] - OLD[0]) < 1 and abs(c[1] - OLD[1]) < 1
def mv(c):
    c[0] += DX; c[1] += DZ
for key in ("lakes", "islands", "surfaces"):
    for e in s[key]:
        if "circle" in e and is_volc(e["circle"]):
            mv(e["circle"])
for r in s["regions"]:
    if "circle" in r and is_volc(r["circle"]):
        mv(r["circle"])
        if r.get("sea"):
            r["exact"] = True   # the region warp is position-dependent; unwarped it stays on the crater
for rd in s["ridges"]:
    if "arc" in rd and is_volc(rd["arc"]):
        mv(rd["arc"])
    elif "points" in rd and is_volc(rd["points"][0]):
        for p in rd["points"]:
            mv(p)
VX, VZ = OLD[0] + DX, OLD[1] + DZ

# ---------------------------------------------------------------- 2. the web
C = np.array([3000.0, 2400.0])
HUB, RINGS = 760, [1700, 2850, 4050]
# Eight radial strands (angle deg, 0 = east, 90 = south; length), each ending in a fork like a
# snowflake's tip. Lengths follow r9's arms, so the outline the author liked stays.
ARMS = [(-42, 6000), (-97, 5200), (-140, 3900), (186, 5000), (148, 4800), (88, 4100), (30, 4600), (2, 5500)]
lakes, hulls = [], []

def strand(p0, p1, w0, w1, bend=0.0):
    """Jittered chain of circles from p0 to p1, bowed sideways by `bend` (fraction of length)."""
    p0, p1 = np.array(p0, float), np.array(p1, float)
    L = float(np.hypot(*(p1 - p0)))
    nrm = np.array([-(p1 - p0)[1], (p1 - p0)[0]]) / L
    circ, t = [], 0.0
    while t <= L:
        f = t / L
        p = p0 + (p1 - p0) * f + nrm * bend * L * 4 * f * (1 - f)
        r = (w0 + (w1 - w0) * f) / 2 * rng.uniform(0.88, 1.12)
        p = p + nrm * rng.normal(0, r * 0.12)
        circ.append([float(p[0]), float(p[1]), float(r)])
        t += r * 0.8
    lakes.extend(circ)
    hulls.append([[x + r * math.cos(a), z + r * math.sin(a)] for x, z, r in circ for a in np.linspace(0, 6.28, 12)])

def at(ang, rad):
    a = math.radians(ang)
    return C + rad * np.array([math.cos(a), math.sin(a)])

# Hub: open water round the spider island.
lakes.append([float(C[0]), float(C[1]), float(HUB)])
hulls.append([[C[0] + HUB * math.cos(a), C[1] + HUB * math.sin(a)] for a in np.linspace(0, 6.28, 24)])
ends = []
for k, (ang, L) in enumerate(ARMS):
    # Slight curl, all the same way, so the web reads as spun, not ruled.
    mid = at(ang + 4, L * 0.55)
    strand(at(ang, HUB * 0.8), mid, 480, 340, 0.03)
    tip = at(ang + 7, L)
    strand(mid, tip, 340, 220, -0.04)
    ends.append(tip)
    # Forked tip: two short fingers off the arm's end.
    for side in (-1, 1):
        fa = math.radians(ang + 7 + side * rng.uniform(38, 52))
        fl = rng.uniform(800, 1300)
        strand(tip, tip + fl * np.array([math.cos(fa), math.sin(fa)]), 220, 150, side * 0.08)
    # A side pair half-way along the longer arms (the snowflake's barbs), beyond the outer ring.
    if L > 4700:
        b = at(ang + 6, RINGS[-1] + 500)
        for side in (-1, 1):
            fa = math.radians(ang + 6 + side * 60)
            strand(b, b + 700 * np.array([math.cos(fa), math.sin(fa)]), 200, 140)

# Rings: straight-ish chords between neighbouring arms, sagging inward like silk under weight.
# Each junction sits a little off the ideal radius, so the web looks spun, not ruled.
order = sorted(range(len(ARMS)), key=lambda k: ARMS[k][0] % 360)
jit = rng.uniform(-0.09, 0.09, (len(RINGS), len(ARMS)))
ring_pts = []
for ri, R in enumerate(RINGS):
    pts = []
    for a, b in zip(order, order[1:] + order[:1]):
        A, B = ARMS[a], ARMS[b]
        if ri == len(RINGS) - 1 and (A[1] < R + 300 or B[1] < R + 300):
            pts.append(None)
            continue   # the outer ring only spans arms long enough to hold it
        ra, rb = R * (1 + jit[ri, a]), R * (1 + jit[ri, b])
        a0 = A[0] + 4 * min(1, ra / (A[1] * 0.55))
        a1 = B[0] + 4 * min(1, rb / (B[1] * 0.55))
        p0, p1 = at(a0, ra), at(a1, rb)
        sag = -0.06 - 0.02 * ri
        strand(p0, p1, 300 - ri * 30, 300 - ri * 30, sag)
        nrm = np.array([-(p1 - p0)[1], (p1 - p0)[0]])
        pts.append([p0 + (p1 - p0) * f + nrm * sag * 4 * f * (1 - f) for f in np.linspace(0, 1, 9)[:-1]])
    ring_pts.append(pts)

s["lakes"] = [l for l in s["lakes"] if is_volc([l["circle"][0] - DX, l["circle"][1] - DZ])] + \
             [{"circle": [round(x), round(z), round(r)]} for x, z, r in lakes]
s["islands"] = [i for i in s["islands"] if "ring" in i or not (-3000 < i["circle"][0] < 9000 and -4000 < i["circle"][1] < 8000)]
s["islands"].append({"circle": [round(C[0]), round(C[1]), 430]})   # the spider island

# ---------------------------------------------------------------- regions
R = s["regions"]
drop = [r for r in R[10:16]]                         # r9's big-island looks
R = [r for r in R if not any(r is d for d in drop) and not (r.get("sea") and r.get("biome") == 7 and "polygon" in r)]
web = [
    {"tier": 4, "biome": 237, "base": 72, "relief": 45, "circle": [round(C[0]), round(C[1]), HUB], "exact": True},
    # Each band's border is its ring channel, so the biome changes on the water, not on land.
    {"tier": 3, "biomes": [[237, 3], [87, 2], [29, 2]], "base": 72, "relief": 40, "patch": 700,
     "polygon": [[round(x), round(z)] for seg in ring_pts[0] for x, z in seg], "exact": True},
    {"tier": 2, "biomes": [[29, 3], [87, 2], [185, 1]], "base": 72, "relief": 35, "patch": 900,
     "polygon": [[round(x), round(z)] for seg in ring_pts[1] for x, z in seg], "exact": True},
    {"tier": 1, "biomes": [[29, 1], [145, 3], [235, 2], [141, 1]], "base": 72, "relief": 35, "patch": 1100,
     "circle": [round(C[0]), round(C[1]), RINGS[2] + 300]},
]
fresh = [{"biome": 7, "sea": True, "exact": True,
          "polygon": [[round(a), round(b)] for a, b in np.array(h)[ConvexHull(np.array(h)).vertices]]} for h in hulls]
s["regions"] = R[:2] + web + R[2:] + fresh

# ---------------------------------------------------------------- 3. the backbone
# One great range across the north of the continent, west coast range to the Alps: three high
# segments with low passes between, spurs south that frame the lake country and tie in the
# volcano, and a lower southern spur off the volcano splitting the maple west from the lakes.
BB = [
    {"points": [[-12600, -7600], [-10200, -6700], [-7600, -6300], [-5000, -6900]], "height": 205, "width": 1700,
     "relief": 210, "peak_spacing": 1100},
    {"points": [[-3900, -6800], [-1800, -5900], [600, -5700], [2600, -6400]], "height": 222, "width": 1900,
     "relief": 220, "biome": 60, "biome_above": 0.85, "peak_spacing": 1100},
    {"points": [[3700, -6700], [6000, -7300], [8300, -8000], [10400, -9400]], "height": 200, "width": 1700,
     "relief": 210, "peak_spacing": 1100},
    # spurs
    {"points": [[-8800, -6400], [-9600, -5000], [VX - 600, VZ - 2700]], "height": 160, "width": 1200, "relief": 180},
    {"points": [[-1200, -5800], [-1700, -4200], [-1100, -2600], [-1500, -1500]], "height": 150, "width": 1100, "relief": 170},
    {"points": [[1600, -5900], [3200, -4600], [3700, -3800]], "height": 135, "width": 1000, "relief": 150},
    {"points": [[6200, -7200], [7200, -5600], [7500, -4600]], "height": 165, "width": 1100, "relief": 170},
    {"points": [[-5200, -6800], [-5500, -8600]], "height": 150, "width": 1000, "relief": 160},   # north spur
    {"points": [[VX + 1500, VZ + 3200], [-5600, 4400], [-4200, 6200]], "height": 140, "width": 1100, "relief": 160},
]
s["ridges"] += BB

# ---------------------------------------------------------------- rivers
# Auto rivers do the draining; keep the deliberate ones: the lake's great outflow to the gulf
# and the corrupted core's dead river.
keep = [r for r in s["rivers"] if r["points"][0] == [3200, 6500] or r.get("biome") == 79]
s["rivers"] = keep
s["auto_rivers"] = {"cell": 128, "threshold_km2": 10, "min_width": 14, "max_width": 100}

# ---------------------------------------------------------------- points
for p_ in s["points"]:
    if p_.get("name") == "Thousand Islands":
        p_["x"], p_["z"] = round(C[0]), round(C[1] - 1400)
    if p_.get("kind") == "spawn" and p_.get("x") == -400 and p_.get("z") == 900:
        p_["x"], p_["z"] = -1500, 300
s["points"].append({"name": "Spider lair", "kind": "landmark", "x": round(C[0]), "z": round(C[1])})

hdr = ("# Round 10, Spiderweb: r9 thousand with the lake spun into a web around a Silkglades spider island,\n"
       "# a mountain backbone, auto rivers and the volcano moved west. Generated by spiderweb-gen.py.\n")
open("docs/design/world/r10/spiderweb.yaml", "w", encoding="utf-8").write(
    hdr + yaml.safe_dump(s, sort_keys=False, default_flow_style=None, width=140))
print("lakes", len(lakes), "volcano", VX, VZ)
