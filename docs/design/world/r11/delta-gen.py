# Round 11, DELTA slot: the divide, with two deltas as its showpieces.
#   py -3.10 docs/design/world/r11/delta-gen.py     (run from the repo root)
# Wet side: the thousand-islands lake drains south through two outlets that meet at an apex on the
# bay head, then fan out into the bay as a braided delta: Wetland and Lush Swamp near the apex,
# Bayou mid-fan, Mangrove on the sea front, barrier islets off the mouths.
# Dry side: the east rain-shadow peninsula becomes desert. A panhandle river comes down off the
# Alps Forest highlands and fans out (Okavango style) into Marsh and Land of Lakes Marsh, its
# channels dying one by one in the sand; the longest reach an inland Oasis lake with an Oasis island.
import math, yaml
import numpy as np

s = yaml.safe_load(open("docs/design/world/r11/divide.yaml", encoding="utf-8"))
rng = np.random.default_rng(1111)


def sector(c, a0, a1, r1, r0=0.0, step=3):
    """Ring sector around point c (deg: 0 = east, 90 = south)."""
    n = max(4, int((a1 - a0) / step))
    A = [math.radians(a0 + (a1 - a0) * i / n) for i in range(n + 1)]
    out = [[round(c[0] + r1 * math.cos(a)), round(c[1] + r1 * math.sin(a))] for a in A]
    if r0 > 0:
        out += [[round(c[0] + r0 * math.cos(a)), round(c[1] + r0 * math.sin(a))] for a in reversed(A)]
    else:
        out.append([round(c[0]), round(c[1])])
    return out


def braided_fan(apex, a0, a1, n, R, lengths, w0, w1, wob, seed, biome=None, start_frac=0.0, links=2):
    """n channels leaving one apex. Each spreads to its own heading as it runs out, and weaves
    (sinusoid in angle) by about a channel spacing, so neighbours cross and re-split: a braid.
    Each channel is cut in three pieces that narrow downstream."""
    r = np.random.default_rng(seed)
    out, mouths, lines = [], [], []
    mid = (a0 + a1) / 2
    for i in range(n):
        th = a0 + (a1 - a0) * (i + 0.5) / n
        L = R * lengths[i]
        ph, fr = r.uniform(0, 2 * math.pi), r.uniform(2.2, 3.6)
        pts = []
        for k in range(29):
            t = k / 28
            rad = L * (start_frac + (1 - start_frac) * t)
            spread = min(1.0, (rad / R) * 2.2) ** 0.8
            ang = mid + (th - mid) * spread + wob * math.sin(ph + fr * math.pi * t) * min(1, t * 3)
            a = math.radians(ang)
            pts.append([round(apex[0] + rad * math.cos(a)), round(apex[1] + rad * math.sin(a))])
        mouths.append(pts[-1])
        lines.append(pts)
        for (p0, p1), w in zip([(0, 11), (10, 20), (19, 28)], [w0, (w0 + w1) / 2, w1]):
            rv = {"points": pts[p0:p1 + 1], "width": int(w), "meander": 70, "valley": int(60 + w)}
            if biome:
                rv["biome"] = biome
            out.append(rv)
    # Anabranches: short diagonal channels between neighbours, so the braid links sideways too.
    for i in range(n - 1):
        for _ in range(links):
            k = int(r.integers(6, 24))
            p, q = lines[i][k], lines[i + 1][min(28, k + int(r.integers(1, 4)))]
            if r.random() < 0.5:
                p, q = lines[i + 1][k], lines[i][min(28, k + int(r.integers(1, 4)))]
            rv = {"points": [p, q], "width": int(w1 * 0.8), "meander": 50, "valley": int(50 + w1)}
            if biome:
                rv["biome"] = biome
            out.append(rv)
    return out, mouths


R = s["regions"]
front = []          # regions put first in the list own their land before the base's regions

# ================================================================ wet side: the bay-head delta
APEX = (300, 6500)
WA0, WA1, WR = 62, 172, 4100
# The fan lobe: radius bulges at each mouth, so the front is cuspate rather than a clean arc.
mouth_ang = [WA0 + (WA1 - WA0) * (i + 0.5) / 11 for i in range(11)]
lobe = []
for k in range(56):
    a = WA0 - 6 + (WA1 - WA0 + 12) * k / 55
    rr = WR + 650 * max(math.exp(-((a - m) / 4.5) ** 2) for m in mouth_ang) - 200
    lobe.append([round(APEX[0] + rr * math.cos(math.radians(a))), round(APEX[1] + rr * math.sin(math.radians(a)))])
lobe += [[APEX[0] - 2500, APEX[1] - 800], [APEX[0], APEX[1] - 1200], [APEX[0] + 2600, APEX[1] - 300]]
s["landmasses"].append(lobe)
s["rough_zones"].append({"polygon": sector(APEX, WA0 - 20, WA1 + 20, WR + 1800), "mul": 0.28})
# Barrier islets off the front.
s["island_chains"].append({"points": sector(APEX, WA0 + 8, WA1 - 6, WR + 1000)[:-1], "count": 16, "r": [90, 260], "jitter": 260})

wet_rivers = []
# Two outlets from the lake's southern spokes meet at the apex: the great river.
wet_rivers.append({"points": [[22, 5764], [150, 6150], list(APEX)], "width": 150, "meander": 120, "valley": 220, "biome": 150})
wet_rivers.append({"points": [[3244, 6314], [2400, 6450], [1400, 6600], list(APEX)], "width": 130, "meander": 160, "valley": 200, "biome": 150})
fan, wet_mouths = braided_fan(APEX, WA0, WA1, 11, WR + 500, [1.0, 0.95, 1.05, 1.0, 0.9, 1.05, 1.0, 0.95, 1.0, 1.05, 0.95],
                              105, 64, 6.0, 31, biome=150, links=2)
wet_rivers += fan

front += [
    {"tier": 1, "biomes": [[252, 3], [152, 2]], "base": 64, "relief": 8, "patch": 700, "polygon": sector(APEX, WA0 - 20, WA1 + 20, 2000)},
    {"tier": 1, "biomes": [[63, 3], [152, 2], [252, 1]], "base": 64, "relief": 6, "patch": 650, "polygon": sector(APEX, WA0 - 6, WA1 + 6, WR - 400)},
    {"tier": 2, "biomes": [[153, 4], [63, 1]], "base": 63, "relief": 4, "patch": 600, "polygon": sector(APEX, WA0 - 2, WA1 + 2, WR + 1300)},
]

# ================================================================ dry side: the inland delta
lm = s["landmasses"][3]
i0 = lm.index([16550, -9848])
lm[i0 + 1:i0 + 4] = [[19400, -6800], [20800, -2600], [20900, 1200], [19400, 4100], [16800, 4700], [14600, 3900]]
s["rough_zones"].append({"polygon": [[14800, -5200], [22500, -5200], [22500, 5600], [14800, 5600]], "mul": 0.55})

DAPEX = (17400, -3000)
DA0, DA1, DR = 42, 140, 3700
OASIS = (17300, 1500)
s["lakes"].append({"circle": [OASIS[0], OASIS[1], 880]})
s["islands"].append({"circle": [OASIS[0] + 60, OASIS[1] + 20, 380]})
# Panhandle: off the Alps Forest highlands, down a single channel to the apex.
dry_rivers = [{"points": [[15700, -8300], [16300, -6800], [16700, -5400], [17200, -4200], list(DAPEX)], "width": 70,
               "meander": 260, "valley": 160}]
lengths = [0.55, 0.8, 0.62, 0.95, 1.0, 1.25, 1.0, 0.9, 0.6, 0.75, 0.5]
dfan, dry_mouths = braided_fan(DAPEX, DA0, DA1, 11, DR, lengths, 40, 20, 5.0, 77, links=2)
dry_rivers += dfan
# The longest channels run on into the oasis lake.
for m in dry_mouths:
    if math.hypot(m[0] - OASIS[0], m[1] - OASIS[1]) < 1500:
        dry_rivers.append({"points": [m, [round((m[0] + OASIS[0]) / 2), round((m[1] + OASIS[1]) / 2)], list(OASIS)], "width": 26, "meander": 90, "valley": 70})

front = [
    {"biome": 186, "base": 64, "relief": 6, "exact": True, "circle": [OASIS[0] + 60, OASIS[1] + 20, 560]},     # Oasis island
    {"tier": 2, "biomes": [[186, 3], [148, 1]], "base": 66, "relief": 10, "patch": 500, "circle": [OASIS[0], OASIS[1], 1500]},
    {"tier": 2, "biomes": [[159, 3], [146, 2], [148, 1]], "base": 67, "relief": 6, "patch": 700, "lakes": [40, 50, 190],
     "polygon": sector(DAPEX, DA0 - 6, DA1 + 6, DR * 0.95)},
    {"biomes": [[35, 3], [148, 2], [159, 1]], "base": 70, "relief": 18, "patch": 900, "polygon": sector(DAPEX, DA0 - 20, DA1 + 20, DR + 1500)},
    {"tier": 1, "biomes": [[2, 3], [190, 2], [254, 2]], "base": 76, "relief": 35, "patch": 1400,
     "polygon": [[15200, -5600], [23000, -5600], [23000, 6000], [15200, 6000]]},
] + front
# The old steppe cell on the peninsula goes dry too, for whatever land it still holds.
for r in R:
    if r.get("at") == [16550, -216]:
        r["biomes"] = [[190, 3], [254, 2], [2, 2], [242, 1]]
# Oasis lake water: painted River like the thousand-islands lake.
sea = [{"biome": 7, "sea": True, "circle": [OASIS[0], OASIS[1], 1000]}]
s["regions"] = front + R + sea

# ================================================================ rivers
old = s["rivers"]
keep = [r for r in old if not r.get("dry") and r["points"][0] != [3200, 6500]]   # drop the old Lush outflow and the steppe dry beds
s["rivers"] = keep + wet_rivers + dry_rivers
ar = s["auto_rivers"]
ar["rain"] = dict(ar.get("rain", {}))
# The inland delta must not feed a river to the sea: its marshes and oasis are rain-poor terrain.
ar["rain"]["^Desert$|Outback|Xeric"] = 0.08
ar["rain"]["^BoP Marsh$|Land of Lakes Marsh|^BoP Oasis$|Lush Desert|^Savanna$"] = 0.12

hdr = ("# Round 11, DELTA: the divide with a braided bay-head delta on the wet side (Wetland, Lush Swamp,\n"
       "# Bayou, Mangrove) and an Okavango-style inland delta dying into Marsh and an Oasis lake on the dry side.\n"
       "# Generated by delta-gen.py from divide.yaml.\n")
open("docs/design/world/r11/delta.yaml", "w", encoding="utf-8").write(hdr + yaml.safe_dump(s, sort_keys=False, default_flow_style=None, width=140))
print("wet mouths", len(wet_mouths), "dry channels", len(dry_rivers), "regions", len(s["regions"]))
