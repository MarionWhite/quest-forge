"""Round 9, Dark Mirror: r8 enchanted + a pair of lakes.

A big bright lake in the friendly grassland and a small, dark, near-circular lake in the
corrupted core with one island at its centre (a spooky mirror of the volcano's crater lake).
A river links them, its water changing from clear (Lush River) to black (Ominous Woods).

  py -3.10 docs/design/world/r9/mirror-gen.py      (run from the repo root)
"""
import math, yaml

s = yaml.safe_load(open("docs/design/world/r8/enchanted.yaml", encoding="utf-8"))
R = s["regions"]

# ---------------------------------------------------------------- the bright lake
LX, LZ = 1700, 2500          # centre, in the grassland
A, B = 3100, 2150            # semi-axes: ~6 km x 4 km
ROT = math.radians(-12)      # long axis WSW -> ENE, pointing at the dark lake


def bump(t, at, width, amp):
    d = math.atan2(math.sin(t - math.radians(at)), math.cos(t - math.radians(at)))
    return amp * math.exp(-(d / width) ** 2)


def bright_outline(scale=1.0, n=160):
    pts = []
    for i in range(n):
        t = 2 * math.pi * i / n
        f = (1 + 0.07 * math.sin(2 * t + 0.6) + 0.05 * math.sin(3 * t + 2.1) + 0.03 * math.sin(5 * t + 4.0)
             + bump(t, 200, 0.35, 0.22)      # a broad western bay
             + bump(t, 0, 0.30, 0.18)        # the eastern arm, toward the river to the dark lake
             - bump(t, 95, 0.16, 0.45)       # a long peninsula reaching in from the south shore
             - bump(t, 300, 0.22, 0.20))     # a headland on the north shore, under the cliffs
        u, v = A * f * math.cos(t) * scale, B * f * math.sin(t) * scale
        pts.append([round(LX + u * math.cos(ROT) - v * math.sin(ROT)), round(LZ + u * math.sin(ROT) + v * math.cos(ROT))])
    return pts


def at(u, v):
    return [round(LX + u * math.cos(ROT) - v * math.sin(ROT)), round(LZ + u * math.sin(ROT) + v * math.cos(ROT))]


lake = bright_outline()
s["lakes"].append({"polygon": lake})
isle_a, isle_b = at(-1500, -150), at(1250, 250)
s["islands"] += [{"circle": isle_a + [950]}, {"circle": isle_b + [780]}]

# ---------------------------------------------------------------- the dark lake
DX, DZ = 10500, -3200
s["lakes"].append({"circle": [DX, DZ, 1600]})
s["islands"].append({"circle": [DX, DZ, 650]})
s["surfaces"].append({"material": "black_sand", "circle": [DX, DZ, 1800]})
s["basins"].append({"circle": [DX, DZ, 1400], "floor": 8, "wall": 160, "biome": 187})
s["ridges"].append({"points": [[DX, DZ], [DX + 1, DZ + 1]], "height": 150, "width": 760, "relief": 140,
                    "biome": 78, "biome_above": 0.15})
s["ponds"] = [p for p in s["ponds"] if p["biome"] != 238]   # the old sludge ponds sat where the lake is now

# Replace the corrupted core's two rings with: island, a sludge and dead-swamp shore, a roofed dark wood.
R[:] = [r for r in R if r.get("circle", [None])[:2] != [10500, -3200]]
core = [
    {"tier": 4, "biome": 78, "base": 74, "relief": 60, "circle": [DX, DZ, 800], "exact": True},
    {"tier": 4, "biomes": [[79, 3], [238, 2]], "base": 64, "relief": 10, "patch": 900, "circle": [DX, DZ, 2300]},
    {"tier": 3, "biomes": [[29, 4], [187, 1]], "base": 70, "relief": 35, "patch": 2200, "circle": [DX, DZ, 3900]},
]

# ---------------------------------------------------------------- around the bright lake
bright = [
    {"tier": 1, "biome": 189, "base": 72, "relief": 30, "circle": isle_a + [1150], "exact": True},     # Origin Valley isle
    {"tier": 2, "biome": 88, "base": 70, "relief": 25, "circle": isle_b + [980], "exact": True},       # Garden isle
    {"tier": 1, "biomes": [[152, 3], [252, 1]], "base": 63, "relief": 6, "patch": 800,
     "circle": at(300, 2500) + [1500]},                                                                 # Lush Swamp south bay
]
new_cells = [
    # fairy edge of the enchanted quarter, between the bright lake and the Mystic Grove
    {"tier": 1, "biomes": [[132, 3], [88, 1]], "base": 72, "relief": 35, "patch": 2200, "at": [5400, 1500], "size": 0.65},
    # autumn band south of the Maple Woods
    {"tier": 1, "biomes": [[229, 3], [199, 2]], "base": 76, "relief": 50, "patch": 3000, "lakes": [6, 100, 300],
     "at": [-8600, 4300], "size": 0.75},
    # heath moor between the snowy and coniferous forests
    {"tier": 2, "biome": 141, "base": 80, "relief": 55, "at": [-8300, -6600], "size": 0.55},
    # Canadian-shield lakeland in the north
    {"tier": 2, "biomes": [[235, 3], [145, 2]], "base": 70, "relief": 40, "patch": 2500, "lakes": [18, 120, 420],
     "at": [400, -7600], "size": 0.7},
    # eucalyptus in the warm south, between the grassland and the outback
    {"tier": 1, "biome": 83, "base": 74, "relief": 40, "at": [4400, 10200], "size": 0.5},
]
extra_circles = [
    {"tier": 1, "biome": 195, "base": 74, "relief": 50, "circle": [15600, 12600, 2000]},     # Rainforest heart of the tropical isle
]
for r in R:
    if r.get("at") == [5198, -8128]:                 # boreal cell -> mega spruce
        r["biomes"] = [[160, 3], [241, 1]]
ice = next(i for i, r in enumerate(R) if r.get("biome") == 86)
R.insert(ice + 1, {"tier": 3, "biome": 140, "base": 70, "relief": 25, "circle": [7520, -16298, 2400]})
tropics = next(i for i, r in enumerate(R) if r.get("circle", [0])[:2] == [15002, 12856])
for c in extra_circles:
    R.insert(tropics, c)
first_cell = next(i for i, r in enumerate(R) if "at" in r)
R[first_cell:first_cell] = new_cells
# Lake water last: sea regions paint in order, so the ocean bands would cover them.
s["regions"] = core + bright + R + [{"biome": 150, "sea": True, "polygon": lake},
                                    {"biome": 187, "sea": True, "circle": [DX, DZ, 1700]}]

# ---------------------------------------------------------------- ridges
# Jade Cliffs behind the bright lake's north shore.
s["ridges"].append({"points": [[-500, -700], [1500, -1300], [3800, -1400], [5600, -600]], "height": 150, "width": 1300,
                    "relief": 190, "biome": 143, "biome_above": 0.3})
# Alps Forest skirts the eastern Alps: a zero-height band painted before the Alps ridge.
alps = next(i for i, r in enumerate(s["ridges"]) if r.get("points", [[0]])[0] == [10960, -9848])
s["ridges"].insert(alps, {"points": [[10960, -9848], [14400, -7010], [15518, -2710]], "height": 62, "width": 3000,
                          "relief": 110, "biome": 59, "biome_above": 0.15})

# ---------------------------------------------------------------- rivers
riv = s["rivers"]
riv[-1]["points"] = [[10150, -4500], [9800, -5800], [9000, -7400], [8400, -9200]]   # black outflow north
riv[-1].update({"width": 128, "biome": 187, "meander": 300})
e = at(A * 1.12, 0)
# The link: clear -> plain -> swampy -> black, each stretch ending where the next begins.
link = [e, [6000, 600], [7600, -700], [8700, -1700], [9500, -2350]]
for (p, q), b in zip(zip(link, link[1:]), [150, 7, 79, 187]):
    riv.append({"points": [p, q], "width": 112, "meander": 260, "valley": 220, "biome": b})
# The bright lake drains south to the gulf.
riv.append({"points": [at(200, 2600), [800, 7000], [640, 8212], [-1682, 8040]], "width": 100, "meander": 300,
            "valley": 260, "biome": 150})

for p_ in s["points"]:
    if (p_.get("x"), p_.get("z")) == (640, 3912):
        p_["x"], p_["z"] = 600, 5600

hdr = "# Round 9, Dark Mirror: r8 enchanted + a bright lake in the grassland and a dark crater-like lake in the corrupted core.\n"
open("docs/design/world/r9/mirror.yaml", "w", encoding="utf-8").write(
    hdr + yaml.safe_dump(s, sort_keys=False, default_flow_style=None, width=140))
print("ok")
