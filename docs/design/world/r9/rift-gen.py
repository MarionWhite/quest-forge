"""Round 9, Rift Lake: r8 enchanted with a long, narrow rift lake (Lake Tanganyika style) down
the middle, the line between the friendly west and the enchanted east.

  py -3.10 docs/design/world/r9/rift-gen.py      (from the repo root) -> docs/design/world/r9/rift.yaml
"""
import math, yaml, numpy as np

s = yaml.safe_load(open("docs/design/world/r8/enchanted.yaml", encoding="utf-8"))
g = np.random.default_rng(909)

# ---------------------------------------------------------------- the rift
# Centreline (x at z) and half-width, north to south. A gentle S; it bulges round the big island.
CL = [(-8500, 2700, 250), (-7900, 2850, 750), (-6800, 3000, 950), (-5200, 2850, 1000), (-3600, 2700, 1050),
      (-2400, 2800, 1300), (-1500, 2750, 1750), (-300, 2650, 1850), (800, 2600, 1350), (1800, 2450, 1000),
      (3000, 2250, 950), (4200, 2050, 1000), (5000, 1950, 800), (5600, 1900, 300)]
ZN, ZS = CL[0][0], CL[-1][0]
zs_ = np.array([c[0] for c in CL], float)


def cx(z):
    return float(np.interp(z, zs_, [c[1] for c in CL]))


def hw(z):
    return float(np.interp(z, zs_, [c[2] for c in CL]))


def wiggle(z, seed, amp):
    """Smooth ragged offset (blocks) along the lake: sines at several scales, random phases."""
    r = np.random.default_rng(seed)
    terms = [(L, r.uniform(0, 6.283), a) for L, a in [(3400, 0.5), (1700, 0.3), (800, 0.2), (420, 0.12)]]
    return amp * sum(a * math.sin(2 * math.pi * z / L + ph) for L, ph, a in terms)


def shore(z, side, extra=0.0):
    """x of the lake shore (side -1 west, +1 east), pushed `extra` blocks inland."""
    w = hw(z) * (1 + wiggle(z, 11 if side < 0 else 12, 0.22))
    return cx(z) + side * (w + extra)


def zsteps(z0, z1, step=150):
    n = max(2, int(abs(z1 - z0) / step))
    return [z0 + (z1 - z0) * i / n for i in range(n + 1)]


Z = zsteps(ZN, ZS)
lake = [[round(shore(z, -1)), round(z)] for z in Z] + [[round(shore(z, 1)), round(z)] for z in reversed(Z)]


def band(z0, z1, side, inner, outer, seed, tn=1800, ts=1800):
    """A strip along one shore: from `inner` blocks inland (negative = into the lake) to a ragged
    `outer` blocks inland, tapering to nothing over tn / ts blocks at its north / south ends."""
    zz = zsteps(z0, z1)

    def env(z):
        e = min(1.0, (z - z0) / tn, (z1 - z) / ts)
        e = max(0.0, e)
        return e * e * (3 - 2 * e)
    a = [[round(shore(z, side, inner)), round(z)] for z in zz]
    b = [[round(shore(z, side, max(inner + 40, env(z) * (outer + wiggle(z, seed, outer * 0.35))))), round(z)]
         for z in reversed(zz)]
    return a + b


def along(z0, z1, off, half):
    """A long thin island following the centreline, `off` blocks east of it, tapered ends."""
    zz = zsteps(z0, z1, 100)
    L = len(zz) - 1
    w = [half * max(0.0, math.sin(math.pi * i / L)) ** 0.6 * (1 + wiggle(z, 40 + abs(int(off)), 0.25)) for i, z in enumerate(zz)]
    return ([[round(cx(z) + off - wi), round(z)] for z, wi in zip(zz, w)] +
            [[round(cx(z) + off + wi), round(z)] for z, wi in reversed(list(zip(zz, w)))])


def blob(x0, z0, a, b, seed, n=48):
    """An elongated island (half-axes a across, b along), ragged edge."""
    r = np.random.default_rng(seed)
    terms = [(k, r.uniform(0, 6.283), 0.12 / k ** 0.7) for k in range(2, 9)]
    pts = []
    for i in range(n):
        t = 2 * math.pi * i / n
        f = 1 + sum(am * math.sin(k * t + ph) for k, ph, am in terms)
        pts.append([round(x0 + a * f * math.cos(t)), round(z0 + b * f * math.sin(t))])
    return pts


big = blob(cx(-800) + 60, -800, 650, 1500, 5)
big_reg = blob(cx(-800) + 60, -800, 850, 1700, 5)
thin = [(-6400, -3800, 280, 320), (1200, 3600, -280, 300), (3600, 5100, 240, 240)]
thin_land = [along(a, b, o, h) for a, b, o, h in thin]
thin_reg = [along(a, b, o, h + 220) for a, b, o, h in thin]

s["lakes"].append({"polygon": lake})
s["islands"] += [{"polygon": big}] + [{"polygon": p} for p in thin_land]

# Escarpments: stepped plateaus, highest at the water, each step a sheer wall. The inner edge sits
# 200 blocks into the lake, so the wall rises straight out of the water.
EZ0, EZ1 = -7000, 4600
s["plateaus"] += [
    {"polygon": band(EZ0, EZ1, -1, -200, 2000, 21, 2500, 2200), "top": 102, "wall": 48, "top_relief": 12, "relief": 70},
    {"polygon": band(EZ0 + 600, EZ1 - 500, -1, -200, 800, 22, 2500, 2200), "top": 132, "wall": 64, "top_relief": 12, "relief": 80},
    {"polygon": band(EZ0, EZ1, 1, -200, 2000, 23, 2500, 2200), "top": 98, "wall": 48, "top_relief": 12, "relief": 70},
    {"polygon": band(EZ0 + 600, EZ1 - 500, 1, -200, 800, 24, 2500, 2200), "top": 124, "wall": 64, "top_relief": 12, "relief": 80},
]
s["plateaus"] += [{"polygon": p, "top": 90, "wall": 24, "top_relief": 4, "relief": 40, "biome": 143} for p in thin_land]
# Deep troughs down the rift floor.
s["basins"] += [{"circle": [round(cx(z)), z, r], "floor": 14, "wall": 260} for z, r in [(-5200, 650), (-800, 900), (2600, 600)]]

# ---------------------------------------------------------------- regions
R = s["regions"]
for r in R:
    a = r.get("at")
    if a == [1758, -4000]:          # Fungi Forest: off the lake line, deeper into the east
        r.update({"at": [6900, -5300], "size": 0.7})
    elif a == [640, 2708]:          # west-shore grassland with heath
        r.update({"at": [-900, 2900], "biomes": [[138, 3], [141, 2], [169, 1]], "patch": 3000})
    elif a == [6660, -990]:         # Mystic Grove behind the fairy edge
        r.update({"at": [6700, -700], "size": 0.75})
    elif a == [-3660, -8128]:       # north: coniferous with Mega Spruce Taiga
        r.update({"biomes": [[74, 3], [160, 2]]})
    elif a == [5198, -8128]:        # north-east: boreal with Mega Taiga
        r.update({"biomes": [[66, 2], [32, 2], [241, 1]]})
    elif a == [13110, -7870]:       # snowy coniferous with Alps Forest under the range
        r.update({"biomes": [[239, 3], [59, 2]]})
    elif r.get("circle") == [15002, 12856, 4300]:   # tropical isle: Tropics and Rainforest
        r.update({"biomes": [[246, 2], [195, 2], [62, 1]]})

isles = [
    {"tier": 2, "biomes": [[185, 2], [132, 2]], "base": 78, "relief": 50, "patch": 900, "polygon": big_reg, "exact": True},
] + [{"tier": 2, "biome": 143, "base": 76, "relief": 40, "polygon": p, "exact": True} for p in thin_reg]
# Freshwater over the whole lake: exact (no region wobble) and a little wider than the cut, so no
# patch of the lake keeps the sea's biome.
lake_wide = [[round(shore(z, -1, 500)), round(z)] for z in zsteps(ZN - 500, ZS + 500)] +             [[round(shore(z, 1, 500)), round(z)] for z in reversed(zsteps(ZN - 500, ZS + 500))]
lake_sea = [{"biome": 7, "sea": True, "polygon": lake_wide, "exact": True}]
shoulders = [
    # west: autumn cliffs in the north, jade cliffs in the south
    {"tier": 2, "biome": 143, "base": 76, "relief": 60,
     "polygon": band(-4000, EZ1 + 300, -1, -200, 2400, 32, 3000, 1500), "exact": True},
    {"tier": 1, "biomes": [[229, 3], [199, 1]], "base": 76, "relief": 50, "patch": 1400,
     "polygon": band(EZ0 - 300, 600, -1, -200, 2400, 31, 1500, 3000), "exact": True},
    # east: the fairy edge, Flower Forest and Garden the whole way down
    {"tier": 2, "biomes": [[132, 3], [88, 2]], "base": 76, "relief": 45, "patch": 1500,
     "polygon": band(EZ0 - 300, EZ1 + 300, 1, -200, 1900, 33, 1500, 1500), "exact": True},
]
ends = [
    {"tier": 1, "biome": 152, "base": 64, "relief": 10, "circle": [1700, 5900, 1500]},            # Lush Swamp delta
    {"tier": 2, "biomes": [[145, 3], [235, 2]], "base": 70, "relief": 35, "patch": 1800,
     "lakes": [18, 100, 320], "circle": [2700, -8900, 2400]},                                     # north lakeland
    {"tier": 4, "biome": 140, "base": 70, "relief": 30, "circle": [7520, -16298, 2400]},          # Ice Plains Spikes round the castle
]
cells = [
    {"tier": 1, "biomes": [[229, 3], [199, 1]], "base": 76, "relief": 50, "patch": 2500, "lakes": [6, 100, 300],
     "at": [-500, -5200], "size": 0.8},                                                           # autumn band, west
    {"tier": 2, "biomes": [[132, 3], [88, 2], [185, 1]], "base": 74, "relief": 40, "patch": 2200, "lakes": [6, 80, 260],
     "at": [5800, 4300], "size": 0.7},                                                            # fairy meadows, south-east
    {"tier": 3, "biomes": [[29, 4], [185, 1]], "base": 74, "relief": 45, "patch": 2500, "lakes": [6, 80, 240],
     "at": [9700, 1500], "size": 0.75},                                                           # Roofed Forest dark wood
    {"tier": 1, "biome": 83, "base": 74, "relief": 40, "at": [5300, 10600], "size": 0.55},        # Eucalyptus, warm south
]
# Seas, islands and the caldera circles stay first; the new shapes go before the old cells.
first_cell = next(i for i, r in enumerate(R) if "at" in r)
old_first = [r for r in R[:first_cell] if not (r.get("circle") == [7520, -16298, 688])]
ice = [r for r in R[:first_cell] if r.get("circle") == [7520, -16298, 688]]
s["regions"] = isles + ice + ends[2:] + old_first + shoulders + ends[:2] + cells + R[first_cell:] + lake_sea   # sea regions paint in order: the lake last

# ---------------------------------------------------------------- rivers and points
riv = s["rivers"]
for rv in riv:
    if rv["points"][0] == [10500, -3200]:   # the black river now runs from the core into the rift
        rv["points"] = [[10500, -3200], [8600, -2700], [6600, -2300], [round(shore(-1900, 1, -100)), -1900]]
riv += [
    {"points": [[round(shore(5500, -1, -100)) + 300, 5500], [1300, 7000], [640, 8212]], "width": 90,
     "meander": 300, "valley": 240, "biome": 150},                                            # outflow to the gulf
    {"points": [[-2600, -7200], [-800, -6000], [round(shore(-5300, -1, -100)), -5300]], "width": 40},   # autumn creek
    {"points": [[6400, 2600], [4900, 1600], [round(shore(1000, 1, -100)), 1000]], "width": 36, "biome": 150},
]
for p_ in s["points"]:
    if p_.get("x") == 640 and p_.get("z") == 3912:
        p_["x"], p_["z"] = -1700, 3500
s["points"].append({"name": "Rift Lake", "kind": "landmark", "x": round(cx(-800)), "z": -800})

hdr = "# Round 9, Rift Lake: r8 enchanted with a long narrow rift lake (Tanganyika style) down the middle.\n# Generated by rift-gen.py next to this file; edit that, not this.\n"
open("docs/design/world/r9/rift.yaml", "w", encoding="utf-8").write(
    hdr + yaml.safe_dump(s, sort_keys=False, default_flow_style=None, width=140))
print("ok", len(lake), "lake vertices")
