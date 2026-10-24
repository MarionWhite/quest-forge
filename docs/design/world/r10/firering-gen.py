# Round 10, Ring of Fire: r9 thousand with a volcanic backbone.
#   py -3.10 docs/design/world/r10/firering-gen.py     (run from the repo root)
# The volcano complex moves west and a little south, and a volcanic arc curves around the west
# side of the thousand-islands lake: dormant snow-free Crag peaks to the north, the great crater
# in the middle, then a chain of cones running south-east to the desert gulf, each hotter and
# harder than the last, ending in a Volcano island in the gulf. Rivers are terrain-following.
import yaml

s = yaml.safe_load(open("docs/design/world/r9/thousand.yaml", encoding="utf-8"))
OLD = (-4520, -1850)
DX, DZ = -3600, 1400                      # every element of the volcano complex moves by this
C = (OLD[0] + DX, OLD[1] + DZ)            # the new crater centre


def near_old(x, z, r=5):
    return abs(x - OLD[0]) < r and abs(z - OLD[1]) < r


def shift_circle(o, key="circle"):
    if key in o and near_old(o[key][0], o[key][1]):
        o[key][0] += DX
        o[key][1] += DZ
        return True
    return False


# ---------------------------------------------------------------- move the volcano complex
moved = 0
for k in ("lakes", "islands", "surfaces", "regions"):
    for o in s[k]:
        moved += shift_circle(o)
for rd in s["ridges"]:
    if "arc" in rd:
        moved += shift_circle(rd, "arc")
    elif near_old(*rd["points"][0]):
        rd["points"] = [[x + DX, z + DZ] for x, z in rd["points"]]
        moved += 1
print("moved", moved, "volcano elements to", C)

# ---------------------------------------------------------------- rivers: drainage does the work
# Keep the lake's great outflow to the gulf and the corrupted core's dead river; the rest
# (volcano rivers, tropical tributaries, frozen northern streams, the east feeder) are drawn
# by auto_rivers along the real drainage.
s["rivers"] = [r for r in s["rivers"] if r["points"][0] in ([3200, 6500], [10500, -3200])]
s["auto_rivers"] = {"cell": 128, "threshold_km2": 10, "min_width": 14, "max_width": 100}

# ---------------------------------------------------------------- the arc
# Active cones from the crater to the gulf: (x, z, height, width, biome_above, tier, crater r)
# Lower biome_above = more of the cone painted Volcano: the chain heats up toward its end.
CONES = [
    (-6500, 3700, 150, 1500, 0.62, 2, 220),
    (-5000, 6600, 162, 1600, 0.48, 3, 0),
    (-4400, 8900, 176, 1700, 0.34, 3, 260),
    (-1500, 11400, 206, 1700, 0.16, 4, 0),       # the gulf island
    (2900, 13700, 214, 1900, 0.08, 5, 320),      # on the desert shore, the end of the line
]
A, B, Cc, D, E = [(c[0], c[1]) for c in CONES]
spine = [C, (-7300, 1700), A, (-5900, 5000)]          # a pass between the first two cones
spine2 = [B, (-4500, 7900), Cc]                       # then the arc runs out to sea
for pts in (spine, spine2):
    s["ridges"].append({"points": [list(p) for p in pts], "height": 112, "width": 2400, "relief": 170,
                        "peak_spacing": 1100})
# The arc crosses the gulf as a string of volcanic islets, island to desert shore.
s["island_chains"].append({"points": [list(Cc), list(D), [700, 12700], list(E)], "count": 9, "r": [140, 360],
                           "jitter": 260})
# Spurs off the spine, so the range has a skeleton and the valleys between carry rivers.
spurs = [
    [A, (-8300, 4800), (-9700, 5000)],          # west spur into the autumn band
    [B, (-3300, 5800)],                         # east spur toward the lake's south-west finger
    [B, (-6600, 7600)],                         # west spur toward the canyon rim
    [C, (-10300, 1600)],                        # the crater's south-west shoulder
    [(-7300, 1700), (-5300, 1500)],             # east shoulder toward the lakeland
    [E, (4600, 12400)],                         # the last cone's ridge into the desert
]
for pts in spurs:
    s["ridges"].append({"points": [list(p) for p in pts], "height": 106, "width": 1500, "relief": 150,
                        "peak_spacing": 900})
# The dormant north of the arc: older, eroded Crag peaks with passes between, toward the conifers.
for pts, ht in (([(-8700, -4200), (-8200, -6000)], 165), ([(-7300, -7300), (-5600, -8400)], 172),
                ([(-5600, -8400), (-6000, -9600)], 140)):
    s["ridges"].append({"points": [list(p) for p in pts], "height": ht, "width": 1700, "relief": 190,
                        "biome": 77, "biome_above": 0.62})
for x, z, ht, w, above, tier, cr in CONES:
    s["ridges"].append({"points": [[x, z], [x + 1, z + 1]], "height": ht, "width": w, "relief": 160,
                        "biome": 250, "biome_above": above})
    if cr:
        s["ponds"].append({"at": [x, z], "r": cr, "depth": 10})

# The gulf island under the fourth cone, big enough that the shore easing leaves it a summit.
s["islands"].append({"circle": [D[0], D[1], 1150]})

# Regions: each cone owns its flanks (tier marker); lava plains and Wasteland lie between them,
# mostly on the lake side, where the flows ran downhill.
chain = []
flank = {2: [[77, 1]], 3: [[77, 1], [251, 1]], 4: [[250, 1]], 5: [[250, 2], [251, 1]]}
for x, z, ht, w, above, tier, cr in CONES:
    chain.append({"tier": tier, "biomes": flank[tier], "base": 84, "relief": 120, "patch": 1400,
                  "circle": [x, z, round(w * 0.7)], **({"exact": True} if tier == 4 else {})})
plains = [   # (x, z, r, volcano weight, wasteland weight); no tier markers, they belong to the cones
    (-5500, 2100, 800, 1, 3),
    (-4100, 5000, 750, 1, 2),
    (-3000, 7600, 750, 2, 2),
    (4300, 12000, 950, 3, 1),
    (-9900, 600, 650, 1, 3),
]
for x, z, r, wv, ww in plains:
    chain.append({"biomes": [[250, wv], [251, ww]], "base": 68, "relief": 15, "patch": 900, "circle": [x, z, r]})
s["regions"] = s["regions"][:2] + chain + s["regions"][2:]

# Black sand: lava plains toward the hot end, the coastal cone, its beaches and the gulf island.
for x, z, r in ((-3000, 7600, 450), (-4400, 8900, 650), (-3700, 9700, 450), (-1500, 11400, 1350),
                (2900, 13700, 700), (1500, 13600, 550), (4300, 12000, 450)):
    s["surfaces"].append({"material": "black_sand", "circle": [x, z, r]})

hdr = ("# Round 10, Ring of Fire: r9 thousand with a volcanic arc for a backbone, the volcano moved\n"
       f"# {DX:+d} x, {DZ:+d} z, terrain-following rivers. Generated by firering-gen.py.\n")
open("docs/design/world/r10/firering.yaml", "w", encoding="utf-8").write(
    hdr + yaml.safe_dump(s, sort_keys=False, default_flow_style=None, width=140))
