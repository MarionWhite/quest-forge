# Round 11, High Plateau: r11 divide with the rain-shadow side lifted into a high desert plateau.
#   py -3.10 docs/design/world/r11/plateau-gen.py     (run from the repo root)
# Behind the divide crest the lee side rises in two steps (a grand staircase: y ~138 under the
# crest, y ~122 further out) and ends in a ragged escarpment above a narrow coastal strip. Four
# gorges run from the crest across both steps to the sea, cut by the few rivers the dry side has.
# On top: mesas and buttes, a hoodoo field (vanilla Mesa (Bryce)) and dry salt pans.
# The windward side is untouched, so the contrast across the divide is rainforest vs. high desert.
import math
import numpy as np
import yaml

s = yaml.safe_load(open("docs/design/world/r11/divide.yaml", encoding="utf-8"))
rng = np.random.default_rng(1111)

# ---------------------------------------------------------------- more land on the lee side
lm1 = s["landmasses"][0]
k = lm1.index([2962, -10278])
lm1[k - 1:k + 1] = [[-2400, -10500], [210, -11200], [2962, -11400]]
s["landmasses"][3] = [[1930, -11500], [5500, -11900], [9500, -12100], [13000, -11800], [16500, -10900],
                      [19500, -9800], [20700, -7000], [20800, -3500], [20300, -300], [19000, 2200],
                      [17000, 3300], [14500, 3500], [12680, 3396], [10100, 3052], [9240, 5460],
                      [8810, 7610], [2962, 5976]]
for z in s["rough_zones"]:
    if z["mul"] == 2.6:            # the east coast was shredded; an escarpment coast reads better calmer
        z["mul"] = 1.3
        z["polygon"] = [[8380, -12300], [21800, -12300], [21800, 3310], [8380, 3310]]

# ---------------------------------------------------------------- the crest and its lee normal
ARC = [[-15000, -9900], [-12600, -8200], [-10200, -6900], [-7500, -6100], [-4500, -5900], [-1500, -6300],
       [1500, -6700], [4500, -6200], [7500, -6300], [10200, -6100], [12600, -4900], [14000, -2600],
       [14400, 0], [14200, 2200], [13500, 3900]]
def catmull(P, per=40):
    P = [P[0]] + P + [P[-1]]
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = map(np.array, P[i - 1:i + 3])
        for u in np.linspace(0, 1, per, endpoint=False):
            out.append(0.5 * (2 * p1 + (-p0 + p2) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u * u + (-p0 + 3 * p1 - 3 * p2 + p3) * u ** 3))
    out.append(np.array(P[-2], float))
    return np.array(out)
crest = catmull(ARC)
cum = np.concatenate([[0], np.cumsum(np.hypot(*np.diff(crest, axis=0).T))])
tang = np.gradient(crest, axis=0)
for _ in range(60):                 # smooth normals: offsets must not wobble with the crest's kinks
    tang[1:-1] = (tang[:-2] + tang[1:-1] + tang[2:]) / 3
tang /= np.hypot(*tang.T)[:, None]
norm = np.stack([tang[:, 1], -tang[:, 0]], 1)   # left of travel = north, then east: the lee

def interp(arr, sv):
    return np.stack([np.interp(sv, cum, arr[:, 0]), np.interp(sv, cum, arr[:, 1])], -1)

# Escarpment line: where the plateau ends above the coastal strip.
OUTER = [(-7600, -8600), (-5000, -9800), (-2000, -10400), (2000, -10800), (6000, -11000), (10000, -11000),
         (14000, -10300), (17200, -9300), (18900, -7600), (19500, -4500), (19300, -1500), (18500, 800),
         (16900, 2500)]
def ray_hit(p, d):
    best = None
    for a, b in zip(OUTER, OUTER[1:]):
        a, b = np.array(a, float), np.array(b, float)
        e = b - a
        den = d[0] * e[1] - d[1] * e[0]
        if abs(den) < 1e-9:
            continue
        w = a - p
        t = (w[0] * e[1] - w[1] * e[0]) / den
        u = (w[0] * d[1] - w[1] * d[0]) / den
        if t > 0 and 0 <= u <= 1 and (best is None or t < best):
            best = t
    return best

RIM = 450                           # plateau starts this far behind the crest line
def noise1(x, seed, scales=((3200, 380), (1100, 220), (420, 110))):
    v = 0.0
    for sc, amp in scales:
        ph = (seed * 0.6180339 * (sc + 7)) % 1.0
        v += amp * math.sin(2 * math.pi * (x / sc + ph)) * 0.6 + amp * 0.4 * math.sin(2 * math.pi * (x / (sc * 0.53) + ph * 3.1))
    return v

def sx(sv, t, seed=0):
    """(arclength along the crest, 0..1 across the plateau) -> block coordinates."""
    p, d = interp(crest, sv), interp(norm, sv)
    d = d / np.hypot(*d)
    D = ray_hit(p, d)
    if D is None:
        D = 3000.0
    D = D - RIM + noise1(sv, 3) * min(1.0, t * 1.3)      # ragged escarpment, quiet at the rim
    return p + d * (RIM + t * D)

S0 = float(cum[np.argmin(np.abs(crest[:, 0] + 4300) + 1e5 * (crest[:, 1] < -7500))])   # west end
S1 = float(cum[np.argmin(np.abs(crest[:, 1] - 1600) + 1e5 * (crest[:, 0] < 13000))])  # south-east end
print(f"plateau arclength {S0:.0f}..{S1:.0f} ({S1 - S0:.0f} blocks)")

def at_x(x):
    i = np.argmin(np.abs(crest[:, 0] - x) + 1e5 * (crest[:, 1] > -3000))
    return float(cum[i])
def at_z(z):
    i = np.argmin(np.abs(crest[:, 1] - z) + 1e5 * (crest[:, 0] < 13000))
    return float(cum[i])

# Gorges: s(t) = s0 + drift * t + wander; four of them, crest to sea.
GORGES = [dict(s0=at_x(1300), drift=-400, seed=11), dict(s0=at_x(6300), drift=900, seed=12),
          dict(s0=at_x(10600), drift=700, seed=13), dict(s0=at_z(-1800), drift=-900, seed=14)]
def gs(g, t):
    return g["s0"] + g["drift"] * t + noise1(t * 5000, g["seed"], ((2600, 260), (900, 160), (380, 60)))

GAP = 260        # half-width of the gap between plateau blocks: the gorge floor
def bank(g, side, ts, extra=0):
    return [(gs(g, t) + side * (GAP + extra), t) for t in ts]

def block(sa, sb, t0, t1, extra=0, n_edge=40):
    """A plateau block in (s, t) between two boundaries (each a gorge or a ragged end)."""
    ts = np.linspace(t0, t1, 22)
    left = [(sa(t) + extra, t) for t in ts]                # going out
    right = [(sb(t) - extra, t) for t in ts[::-1]]          # coming back
    outer = [(u, t1) for u in np.linspace(left[-1][0], right[0][0], n_edge)[1:-1]]
    inner = [(u, t0) for u in np.linspace(right[-1][0], left[0][0], n_edge)[1:-1]]
    pts = left + outer + right + inner
    return [[round(float(v), 0) for v in sx(u, t)] for u, t in pts]

west_end = lambda t: S0 + 900 * t + noise1(t * 4000, 21, ((1500, 300), (500, 120)))
east_end = lambda t: S1 - 700 * t + noise1(t * 4000, 22, ((1500, 300), (500, 120)))
bounds = [west_end] + [(lambda g: (lambda t: gs(g, t)))(g) for g in GORGES] + [east_end]

# Lower step: the whole plateau out to the escarpment. Upper step: the crest half, set back from
# each gorge so the canyon walls step down in benches.
plateaus = []
up_t = lambda u: 0.5 + 0.0001 * noise1(u, 31, ((2200, 900), (700, 450)))
for i in range(len(bounds) - 1):
    a, b = bounds[i], bounds[i + 1]
    ga = 0 if i == 0 else GAP
    gb = 0 if i == len(bounds) - 2 else GAP
    poly = block(lambda t, a=a, ga=ga: a(t) + ga, lambda t, b=b, gb=gb: b(t) - gb, -0.02, 1.0)
    plateaus.append({"polygon": poly, "top": 118, "wall": 300, "top_relief": 12, "relief": 45})
    tu = up_t((a(0) + b(0)) / 2)
    poly = block(lambda t, a=a, ga=ga: a(t) + ga + 380, lambda t, b=b, gb=gb: b(t) - gb - 380, -0.02, tu)
    plateaus.append({"polygon": poly, "top": 140, "wall": 160, "top_relief": 10, "relief": 40})
plateaus[1]["tier"] = 3     # the Tibet-like high step under the crest, west

def clear(x, z, r):
    """True if a feature of radius r at (x, z) stays off the gorges."""
    for g in GORGES:
        for t in np.linspace(0, 1, 60):
            if math.hypot(*(sx(gs(g, t), t) - (x, z))) < r + GAP + 450:
                return False
    return True

def blob(x, z, r, k=28, rough=0.42, aspect=1.0, rot=0.0):
    out = []
    ph = rng.uniform(0, 6.3, 3)
    for i in range(k):
        a = 2 * math.pi * i / k
        rr = r * (1 + rough * (0.6 * math.sin(2 * a + ph[0]) + 0.3 * math.sin(3 * a + ph[1]) + 0.25 * math.sin(5 * a + ph[2])))
        u, v = rr * math.cos(a) * aspect, rr * math.sin(a)
        out.append([round(x + u * math.cos(rot) - v * math.sin(rot)), round(z + u * math.sin(rot) + v * math.cos(rot))])
    return out

# Mesas (big flat tables) and buttes (small towers), out on the lower step.
mesas, buttes = [], []
for tries in range(4000):
    if len(mesas) >= 9:
        break
    u = rng.uniform(S0 + 1200, S1 - 1200)
    t = rng.uniform(0.55, 0.9)
    x, z = sx(u, t)
    r = rng.uniform(450, 900)
    if not clear(x, z, r) or any(math.hypot(x - m[0], z - m[1]) < r + m[2] + 1600 for m in mesas):
        continue
    mesas.append((x, z, r))
for x, z, r in mesas:
    plateaus.append({"polygon": blob(x, z, r, aspect=rng.uniform(1.2, 2.2), rot=rng.uniform(0, 3.14)),
                     "top": int(rng.integers(150, 166)), "wall": 45, "top_relief": 4, "relief": 25,
                     "biome": int(rng.choice([39, 39, 38]))})
for tries in range(6000):
    if len(buttes) >= 20:
        break
    u = rng.uniform(S0 + 800, S1 - 800)
    t = rng.uniform(0.5, 0.95)
    x, z = sx(u, t)
    r = rng.uniform(110, 230)
    if not clear(x, z, r) or any(math.hypot(x - m[0], z - m[1]) < r + m[2] + 500 for m in mesas + buttes):
        continue
    buttes.append((x, z, r))
for x, z, r in buttes:
    plateaus.append({"circle": [round(x), round(z), round(r)], "top": int(rng.integers(146, 172)), "wall": 26,
                     "top_relief": 3, "relief": 15, "biome": 39})

# Hoodoo field: dozens of thin spires on the east lower step.
HX, HZ = sx(at_z(-4600), 0.66)
hoodoos = []
for tries in range(5000):
    if len(hoodoos) >= 55:
        break
    a, rr = rng.uniform(0, 6.283), 1700 * math.sqrt(rng.uniform(0, 1))
    x, z = HX + rr * math.cos(a) * 1.3, HZ + rr * math.sin(a) * 0.8
    r = rng.uniform(45, 95)
    if not clear(x, z, r) or any(math.hypot(x - h[0], z - h[1]) < r + h[2] + 90 for h in hoodoos):
        continue
    hoodoos.append((x, z, r))
for x, z, r in hoodoos:
    plateaus.append({"circle": [round(x), round(z), round(r)], "top": int(rng.integers(133, 150)), "wall": 12,
                     "top_relief": 2, "relief": 8, "biome": 165})
s["plateaus"] += plateaus
s["regions"].append({"tier": 3, "biome": 165, "base": 90, "relief": 40, "circle": [round(HX), round(HZ), 2000]})

# ---------------------------------------------------------------- gorges and salt pans (canyons)
for gi, g in enumerate(GORGES):
    pts = [sx(gs(g, t), t) for t in np.linspace(-0.04, 1.0, 40)]
    d = interp(norm, gs(g, 1.0))
    d = d / np.hypot(*d)
    pts += [pts[-1] + d * k for k in (500, 1100, 1800, 2600)]      # out across the coastal strip
    s["canyons"].append({"points": [[round(float(p[0])), round(float(p[1]))] for p in pts], "width": 760,
                         "depth": 18, "meander": 0, "wall_biome": 71, "floor_biome": 82,
                         **({"tier": 3} if gi in (1, 3) else {})})
pans = []
for tries in range(4000):
    if len(pans) >= 4:
        break
    u = rng.uniform(S0 + 1500, S1 - 1500)
    t = rng.uniform(0.1, 0.35)
    x, z = sx(u, t)
    r = rng.uniform(700, 1100)
    if not clear(x, z, r) or any(math.hypot(x - p[0], z - p[1]) < r + p[2] + 3000 for p in pans):
        continue
    pans.append((x, z, r))
for x, z, r in pans:
    a = rng.uniform(0, 6.28)
    s["canyons"].append({"points": [[round(x - 300 * math.cos(a)), round(z - 300 * math.sin(a))],
                                    [round(x + 300 * math.cos(a)), round(z + 300 * math.sin(a))]],
                         "width": round(2 * r), "depth": 12, "meander": 0, "wall_biome": 254, "floor_biome": 2})
x, z, r = pans[0]
s["ponds"].append({"at": [round(x), round(z)], "r": 260})           # one pan still holds a brine lake

# ---------------------------------------------------------------- the lee climate
def cell(at):
    return next(r for r in s["regions"] if r.get("at") == at)
for at, mix in [([-3660, -8128], [[242, 4], [247, 1], [236, 1]]),      # cold high steppe under the crest
                ([5198, -8128], [[190, 3], [242, 2], [254, 1]]),       # outback and steppe
                ([13110, -7870], [[37, 3], [190, 2], [254, 1]]),       # red mesa country
                ([16550, -216], [[254, 3], [37, 2], [242, 1]])]:       # xeric shrubland down to the bay
    r = cell(at)
    r["biomes"], r["base"], r["relief"] = mix, 92, 45
    r.pop("lakes", None)
s["regions"].append({"tier": 2, "biomes": [[190, 3], [37, 2]], "base": 92, "relief": 45, "patch": 3000,
                     "at": [9800, -9300], "size": 0.6})
s["regions"].append({"tier": 2, "biomes": [[37, 3], [254, 1]], "base": 92, "relief": 45, "patch": 3000,
                     "at": [18200, -7800], "size": 0.55})
# The old dry washes on the east steppe now cross the plateau; the gorges replace them.
s["rivers"] = [r for r in s["rivers"] if not r.get("dry")]

yaml.safe_dump(s, open("docs/design/world/r11/plateau.yaml", "w", encoding="utf-8"), sort_keys=False,
               default_flow_style=None, width=200)
print(f"{len(mesas)} mesas, {len(buttes)} buttes, {len(hoodoos)} hoodoos, {len(pans)} salt pans")
