"""Round r6: the refs-5 west half kept, five different right sides, each with the Maelstrom.

    py -3.10 docs/design/world/r6/gen.py      # writes v1.yaml .. v5.yaml next to this file

Shared by every version (built from ../refs/5-formena-river.yaml):
  - the west half as it was: redwood coast, the small atoll island, the biome layout, the
    south-west desert arm and its tip, the old centre, the tropical south-east lobe and gulf;
  - the glacial caldera moved off the mainland onto its own island in the north-west
    (about 21.6k from the old centre instead of 9.2k);
  - the island chain to the northern tundra painted cold (BoP Tundra, vanilla Ice Plains,
    BoP Snowy Coniferous), and the tundra pulled in from the canvas edge.
Each version adds its own right-side landmass, regions, ridges, river head and Maelstrom.
"""
import math, os
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "refs", "5-formena-river.yaml")

CALDERA = (-17000, -18800)

# The west half plus the shared south-east tropical lobe and gulf. Each right side joins it
# along x 3000..4200, between the north coast and (11000, 8500).
WEST = [[-21000, -12000], [-12000, -12800], [-5000, -11800], [1000, -12400], [4200, -12300], [4200, 6600],
        [11000, 8500], [9500, 11500], [9500, 16000], [6500, 19000], [3000, 17500], [1800, 12500],
        [-1500, 8200], [-5200, 12500], [-6000, 18500], [-8200, 24200], [-11800, 21300], [-14500, 15000],
        [-17500, 9000], [-20500, 3000], [-22200, -4000], [-22200, -9000]]
TUNDRA = [[-3000, -18800], [2000, -20800], [10000, -21400], [18000, -21000], [21000, -19300], [19000, -17300],
          [11000, -17200], [4000, -17600]]
CALDERA_ISLAND = [[round(CALDERA[0] + 3700 * math.cos(math.radians(a))), round(CALDERA[1] + 3300 * math.sin(math.radians(a)))]
                  for a in range(0, 360, 30)]
GREAT_RIVER_TAIL = [[11000, 7400], [6000, 8600], [1500, 9200], [-1200, 9000]]

# ---------------------------------------------------------------- the Maelstrom block
R = 2000
STACKS = [(15, 1.08, 440, 140, 4), (65, 0.92, 380, 126, 4), (120, 1.05, 460, 150, 4),
          (170, 0.95, 400, 122, 4), (215, 1.10, 430, 146, 4), (270, 0.90, 390, 132, None),
          (320, 1.02, 450, 138, None)]


def polar(cx, cz, ang, r):
    a = math.radians(ang)
    return round(cx + r * math.cos(a)), round(cz + r * math.sin(a))


def maelstrom(cx, cz, wrecks, step_angle, step_biome):
    """Irregular deep basin (floor y 5) under vanilla Deep Ocean, seven BoP Crag sea stacks
    (five T4), two black-sand wreck islets, a stepping-stone island; shelves form round them."""
    land, sea, islands, plateaus, surfaces, points = [], [], [], [], [], []
    for ang, f, r, top, tier in STACKS:
        x, z = polar(cx, cz, ang, R * f)
        islands.append({"circle": [x, z, r]})
        plateaus.append({"circle": [x, z, r - 20], "top": top, "wall": 30, "top_relief": 4, "relief": 20, "biome": 77})
        reg = {"biome": 77, "base": 70, "relief": 40, "circle": [x, z, r - 60]}
        land.append({"tier": tier, **reg} if tier else reg)
    for ang in wrecks:
        x, z = polar(cx, cz, ang, R + 1300)
        islands.append({"circle": [x, z, 380]})
        surfaces.append({"material": "black_sand", "circle": [x, z, 460]})
        land.append({"tier": 4, "biome": 250, "base": 66, "relief": 20, "circle": [x, z, 440]})
        points.append({"name": "Wreck", "kind": "landmark", "x": x, "z": z})
    x, z = polar(cx, cz, step_angle, R + 2400)
    islands.append({"circle": [x, z, 600]})
    land.append({"tier": 3, "biome": step_biome, "base": 70, "relief": 45, "circle": [x, z, 680]})
    ox, oz = polar(0, 0, 315, 750)
    sea = [{"biome": 24, "sea": True, "circle": [cx, cz, 3300]},
           {"biome": 24, "sea": True, "circle": [cx + ox, cz + oz, 2600]}]
    basins = [{"circle": [cx, cz, 1500], "floor": 5, "wall": 140, "biome": 24},
              {"circle": [cx + ox, cz + oz, 1000], "floor": 5, "wall": 120, "biome": 24}]
    points.insert(0, {"name": "Maelstrom", "kind": "landmark", "x": cx, "z": cz})
    return dict(land=land, sea=sea, islands=islands, plateaus=plateaus, surfaces=surfaces, basins=basins,
                points=points)


# ---------------------------------------------------------------- the five right sides
def reg(tier, biomes, base, relief, at, size=None, lakes=None, patch=3500):
    r = {"tier": tier, "biomes": biomes, "base": base, "relief": relief, "patch": patch}
    if lakes:
        r["lakes"] = lakes
    r["at"] = at
    if size:
        r["size"] = size
    return r


VERSIONS = {
    "v1": dict(
        note="Hook: an arm curls from the north-east round the east and back west, wrapping the Maelstrom bay.",
        poly=[[3000, -12300], [8000, -12400], [13000, -12600], [18500, -12300], [21000, -10000], [21300, -4000],
              [20800, 2500], [19200, 7000], [16200, 9200], [13800, 9600], [13600, 8100], [16200, 6600],
              [18000, 3200], [18300, -1500], [17600, -7200], [15300, -9600], [12300, -9900], [10500, -7600],
              [10700, -3000], [10200, 2400], [11000, 6000], [11000, 8500], [4200, 6600]],
        rough=[{"circle": [14600, -1800, 5200], "mul": 0.6}],
        maelstrom=dict(cx=14600, cz=-1600, wrecks=[110, 300], step_angle=200, step_biome=142),
        regions=[reg(2, [[66, 3], [241, 2]], 76, 80, [6800, -10200], 0.8, [10, 120, 450]),
                 reg(2, [[239, 3], [66, 1]], 72, 100, [17500, -11500], 0.7, [8, 120, 400]),
                 reg(2, [[142, 3], [183, 2]], 86, 70, [20000, -3500], 0.6, [8, 80, 300]),
                 reg(1, [[242, 3], [35, 1]], 70, 35, [18500, 5200], 0.6, [3, 100, 300]),
                 reg(2, [[142, 2], [138, 2]], 80, 60, [8000, -3500], 0.8, [10, 100, 350])],
        hidden=[{"tier": 2, "biome": 240, "base": 86, "relief": 30, "circle": [8200, -6500, 600]}],
        ridges=[{"points": [[15500, -12600], [19600, -10200], [20200, -3500], [19300, 3000]],
                 "height": 200, "width": 1800, "relief": 220, "biome": 60, "biome_above": 0.55}],
        river_head=[[10600, 3500], [11000, 7400]],
        spawn=[19800, 1500]),
    "v2": dict(
        note="Fjord lobe: a fjord-shredded eastern lobe; the Maelstrom in the sound between it and an offshore isle.",
        poly=[[3000, -12300], [9000, -12400], [15000, -12500], [20000, -11800], [21300, -8000], [21000, -2500],
              [19500, 2200], [15500, 3600], [12500, 3200], [11500, 6000], [11000, 8500], [4200, 6600]],
        extra_land=[[[15500, 12000], [18000, 10800], [20800, 11800], [21300, 14800], [19800, 17800],
                     [16800, 18000], [15000, 15500]]],
        rough=[{"polygon": [[10500, -13500], [23000, -13500], [23000, 3500], [10500, 3500]], "mul": 2.6},
               {"polygon": [[10500, 9000], [16000, 9000], [16000, 19500], [10500, 19500]], "mul": 0.35},
               {"circle": [15600, 7400, 4200], "mul": 0.45}],
        maelstrom=dict(cx=15600, cz=7300, wrecks=[20, 200], step_angle=150, step_biome=246),
        regions=[reg(2, [[66, 3], [241, 2]], 76, 80, [6800, -9800], 0.8, [10, 120, 450]),
                 reg(2, [[239, 3], [66, 2]], 72, 110, [16000, -9500], 0.9, [10, 120, 400]),
                 reg(2, [[142, 3], [183, 2]], 86, 70, [16500, -2000], 0.8, [10, 80, 300]),
                 reg(1, [[242, 3], [193, 1]], 70, 35, [20000, -600], 0.5, [3, 100, 300]),
                 reg(2, [[138, 3], [169, 1]], 74, 45, [8500, -1500], 0.8, [8, 120, 400])],
        hidden=[{"tier": 1, "biomes": [[246, 2], [62, 1]], "base": 68, "relief": 40, "patch": 1500,
                 "circle": [18200, 14600, 3800]}],
        ridges=[{"points": [[13500, -11800], [17500, -8500], [18800, -3500]],
                 "height": 195, "width": 1900, "relief": 210, "biome": 60, "biome_above": 0.55}],
        river_head=[[13500, 2500], [11000, 7400]],
        spawn=[20000, 400],
        drop_se_isles=True),
    "v3": dict(
        note="Peninsula: a long dry peninsula reaches south-east; the Maelstrom lies in open sea off its tip.",
        poly=[[3000, -12300], [9000, -12900], [14500, -11800], [17500, -8200], [16800, -3200], [14500, -1200],
              [17200, 1000], [19000, 5000], [20500, 9000], [20000, 11800], [18600, 12200], [17400, 9000], [15500, 6200], [13200, 6400],
              [11400, 8200], [11000, 8500], [4200, 6600]],
        rough=[{"polygon": [[13000, -1500], [22500, -1500], [22500, 10000], [13000, 10000]], "mul": 0.7},
               {"circle": [18500, 16500, 4500], "mul": 0.5}],
        maelstrom=dict(cx=18500, cz=16600, wrecks=[330, 150], step_angle=250, step_biome=190),
        regions=[reg(2, [[66, 3], [239, 2]], 74, 90, [10500, -10000], 0.8, [12, 120, 450]),
                 reg(2, [[142, 3], [183, 2]], 86, 70, [11500, -4500], 0.8, [12, 80, 300]),
                 reg(1, [[242, 3], [193, 1]], 70, 35, [15800, 2400], 0.6, [3, 100, 300]),
                 reg(2, [[190, 3], [70, 1]], 72, 50, [19300, 9200], 0.5),
                 reg(2, [[138, 3], [169, 1]], 74, 45, [7800, -1500], 0.8, [8, 120, 400])],
        hidden=[],
        ridges=[{"points": [[14800, 1200], [17600, 4600], [19500, 9800]],
                 "height": 160, "width": 1400, "relief": 190, "biome": 60, "biome_above": 0.7}],
        river_head=[[12800, 5200], [11000, 7400]],
        spawn=[17600, 3300],
        drop_se_isles=True),
    "v4": dict(
        note="Deep bay: a bay bites in from the north between the body and an eastern lobe; the Maelstrom fills it.",
        poly=[[3000, -12300], [6800, -12600], [6700, -8000], [6200, -3000], [7200, 1200], [10200, 3000],
              [13600, 2300], [15600, -1500], [15900, -7000], [15200, -12000], [18500, -12400], [21300, -10200],
              [21300, -3000], [20300, 4000], [18300, 8000], [15000, 9400], [11000, 8500], [4200, 6600]],
        rough=[{"circle": [11000, -4800, 5000], "mul": 0.55}],
        maelstrom=dict(cx=11000, cz=-5000, wrecks=[60, 240], step_angle=270, step_biome=66),
        regions=[reg(2, [[66, 3], [241, 2]], 76, 80, [5000, -7000], 0.6, [6, 120, 400]),
                 reg(2, [[239, 3], [66, 1]], 72, 100, [18500, -10500], 0.7, [8, 120, 400]),
                 reg(2, [[142, 3], [183, 2]], 86, 70, [18800, -3000], 0.7, [10, 80, 300]),
                 reg(1, [[242, 3], [35, 1]], 70, 35, [17800, 5000], 0.6, [3, 100, 300]),
                 reg(1, [[138, 3], [169, 1]], 74, 45, [10500, 5500], 0.6, [5, 120, 400])],
        hidden=[{"tier": 2, "biome": 240, "base": 86, "relief": 30, "circle": [19500, -6500, 600]}],
        ridges=[{"points": [[18200, -12500], [19300, -7000], [18800, -1500], [17600, 3500]],
                 "height": 210, "width": 2000, "relief": 220, "biome": 60, "biome_above": 0.55}],
        river_head=[[20000, 5800], [15500, 7600], [11000, 7400]],
        spawn=[20200, 1500]),
    "v5": dict(
        note="Three fingers: the east splits into cold, temperate and dry fingers; the Maelstrom sits between "
             "the middle and southern fingers.",
        poly=[[3000, -12300], [9000, -12800], [15000, -12600], [20500, -12300], [21300, -10600], [20000, -9800],
              [14500, -9500], [10800, -8300], [11200, -4800], [16500, -4800], [21000, -4300], [21300, -2700],
              [19500, -1500], [14000, -1000], [11000, 1300], [11000, 5000], [14500, 6000], [19500, 6600],
              [20500, 8700], [18500, 10000], [14000, 9800], [11000, 8500], [4200, 6600]],
        rough=[{"polygon": [[11000, -13000], [22500, -13000], [22500, 10500], [11000, 10500]], "mul": 0.35},
               {"circle": [16200, 2500, 3600], "mul": 0.45}],
        maelstrom=dict(cx=16600, cz=2600, wrecks=[0, 180], step_angle=90, step_biome=242),
        regions=[reg(2, [[66, 3], [142, 1]], 78, 80, [7200, -5500], 0.9, [10, 120, 450]),
                 reg(2, [[239, 3], [247, 1]], 72, 90, [16000, -10800], 0.6, [8, 120, 400]),
                 reg(2, [[183, 3], [141, 1]], 82, 60, [16500, -3200], 0.6, [8, 80, 300]),
                 reg(1, [[242, 2], [190, 2]], 70, 40, [16500, 8200], 0.6, [3, 100, 300]),
                 reg(1, [[138, 3], [169, 1]], 74, 45, [8000, 3500], 0.6, [6, 120, 400])],
        hidden=[],
        ridges=[{"points": [[12500, -10800], [20000, -10600]], "height": 185, "width": 1400, "relief": 200,
                 "biome": 60, "biome_above": 0.6}],
        river_head=[[18500, 8200], [13500, 8200], [11000, 7400]],
        spawn=[19300, 8000]),
}


# ---------------------------------------------------------------- the shared west and the merge
def west():
    s = yaml.safe_load(open(SRC, encoding="utf-8"))
    s["landmasses"] = [WEST, TUNDRA, CALDERA_ISLAND]
    chains = s["island_chains"]
    s["island_chains"] = [c for c in chains if c["points"][0] == [-1500, -18600]]   # the tundra bridge
    se_isles = [c for c in chains if c["points"][0][0] > 10000]
    cx, cz = CALDERA
    s["plateaus"] = [{"circle": [cx, cz, 2900], "top": 150, "wall": 90, "top_relief": 14, "relief": 60,
                      "biome": 89, "tier": 3}]
    s["ponds"] = [{"at": [cx, cz], "r": 1300, "biome": 89}] + [p for p in s["ponds"] if p["at"][0] != -11000]
    ridges = []
    for r in s["ridges"]:
        if "arc" in r and r["arc"][0] == -11000:
            r = dict(r, arc=[cx, cz, 2000] + r["arc"][3:])
        elif "points" in r and r["points"][0] == [17200, -8200]:
            continue                                                    # the old eastern range
        elif "points" in r and r["points"][0] == [13000, -22000]:
            r = dict(r, points=[[13000, -20200], [16800, -19600], [19500, -18800]], width=1500)
        ridges.append(r)
    s["ridges"] = ridges
    keep = []
    for r in s["regions"]:
        c, a = r.get("circle"), r.get("at")
        if c and c[:2] == [-11000, -9000]:
            continue                                                    # old caldera site: the snowy forest takes it
        if c and c[:2] == [-20000, -20500]:
            r = {"tier": 3, "biomes": [[89, 3], [192, 1]], "base": 120, "relief": 60, "patch": 2500,
                 "circle": [cx, cz, 3600]}
        if c and c[:2] == [9500, -20800]:
            r = dict(r, circle=[9500, -19300, 800])
        if c and c[:2] in ([14000, -4000], [19000, 17200]):
            continue                                                    # per-version
        if a and a[0] >= 4900 and a[1] > -17000:
            continue                                                    # the old right side
        if a == [8000, -20500]:
            r = dict(r, at=[8000, -19200])
        if a == [19000, -20200]:
            r = dict(r, at=[18500, -19000])
        keep.append(r)
    # The island chain to the tundra is cold, whichever region the Voronoi would give it.
    # One zone over the whole strait: region borders are warped by up to ~2.6k, so small circles
    # on the islands themselves missed some.
    cold = [{"tier": 2, "biomes": [[247, 2], [12, 1], [239, 1]], "base": 70, "relief": 30, "patch": 900,
             "polygon": [[-7500, -21000], [2500, -21000], [2500, -12600], [-7500, -12600]]}]
    s["regions"] = cold + keep
    rivers, great = [], None
    for rv in s["rivers"]:
        p0 = rv["points"][0]
        if p0 == [20200, 3200]:
            great = rv
            continue                                                    # the great river: per-version head
        if p0 in ([13500, 9200], [6000, -9000]):
            continue
        if p0 == [6000, -20000]:
            rv = dict(rv, points=[[6000, -19400], [4500, -18400], [3500, -17600]])
        rivers.append(rv)
    s["rivers"] = rivers
    pts = []
    for p in s["points"]:
        if p.get("name") == "Ice castle":
            p = dict(p, z=-19300)
        if p.get("kind") == "spawn" and [p["x"], p["z"]] == [13000, -19500]:
            p = dict(p, z=-18700)
        if p.get("kind") == "spawn" and [p["x"], p["z"]] == [20500, -1500]:
            continue
        if p.get("kind") == "spawn" and [p["x"], p["z"]] == [-7600, 20500]:
            p = dict(p, x=-8200, z=17700)                               # onto the arm, clear of the eroded tip
        pts.append(p)
    s["points"] = pts
    se_region = {"tier": 1, "biomes": [[246, 2], [62, 1]], "base": 68, "relief": 40, "patch": 1500,
                 "circle": [19000, 17200, 4200]}
    return s, great, se_isles, se_region


SCALE, SHIFT_X, SHIFT_Z = 0.86, -650, 300  # shrink the whole layout uniformly so land keeps ~3k off the canvas edge


def _xy(p):
    return [round(p[0] * SCALE + SHIFT_X), round(p[1] * SCALE + SHIFT_Z)]


def fit(s):
    """Uniformly scale and shift every position and horizontal size; shapes and layout are
    unchanged, heights and coast-noise settings are not touched."""
    poly = lambda ps: [_xy(p) for p in ps]
    circ = lambda c: _xy(c[:2]) + [round(c[2] * SCALE)] + list(c[3:])
    s["landmasses"] = [poly(p) for p in s["landmasses"]]
    for z in s.get("rough_zones", []):
        if "polygon" in z: z["polygon"] = poly(z["polygon"])
        if "circle" in z: z["circle"] = circ(z["circle"])
    for c in s.get("island_chains", []):
        c["points"] = poly(c["points"])
        c["r"] = [round(r * SCALE) for r in c["r"]]
        c["jitter"] = round(c.get("jitter", 300) * SCALE)
    for key in ("lakes", "islands", "surfaces", "plateaus", "basins"):
        for it in s.get(key, []):
            if "circle" in it: it["circle"] = circ(it["circle"])
            if "ring" in it:
                x, z = _xy(it["ring"][:2]); it["ring"] = [x, z] + [round(r * SCALE) for r in it["ring"][2:]]
            if "wall" in it and key == "plateaus": it["wall"] = max(30, round(it["wall"] * SCALE))
    for c in s.get("canyons", []):
        c["points"] = poly(c["points"]); c["width"] = round(c["width"] * SCALE)
    for r in s["regions"]:
        if "circle" in r: r["circle"] = circ(r["circle"])
        if "polygon" in r and not (r.get("sea") and max(abs(c) for pt in r["polygon"] for c in pt) >= 24000):
            r["polygon"] = poly(r["polygon"])        # canvas-wide sea bands stay as they are
        if "at" in r: r["at"] = _xy(r["at"])
    for p in s.get("ponds", []):
        p["at"] = _xy(p["at"]); p["r"] = round(p["r"] * SCALE)
    for r in s.get("ridges", []):
        if "points" in r: r["points"] = poly(r["points"])
        if "arc" in r: r["arc"] = _xy(r["arc"][:2]) + [round(r["arc"][2] * SCALE)] + list(r["arc"][3:])
        r["width"] = round(r["width"] * SCALE)
    for r in s.get("rivers", []):
        r["points"] = poly(r["points"])
    for p in s.get("points", []):
        p["x"], p["z"] = _xy([p["x"], p["z"]])
    return s


def build(key, v):
    s, great, se_isles, se_region = west()
    s["landmasses"] = s["landmasses"] + [v["poly"]] + v.get("extra_land", [])
    s["rough_zones"] = s["rough_zones"] + [{"polygon": [[3000, -17200], [24576, -17200], [24576, -12600], [3000, -12600]], "mul": 0.3}] + v.get("rough", [])
    hidden = list(v["hidden"])
    if not v.get("drop_se_isles"):
        s["island_chains"] += se_isles
        hidden.append(se_region)
    m = maelstrom(**v["maelstrom"])
    s["islands"] = s.get("islands", []) + m["islands"]
    s["plateaus"] = s["plateaus"] + m["plateaus"]
    s["surfaces"] = s.get("surfaces", []) + m["surfaces"]
    s["basins"] = s.get("basins", []) + m["basins"]
    s["rivers"] = [dict(great, points=v["river_head"][:-1] + GREAT_RIVER_TAIL)] + s["rivers"]
    s["ridges"] = s["ridges"] + v["ridges"]
    # Maelstrom islets win land first, then this version's small circles, then the shared
    # regions; this version's cells come after them, and the Maelstrom's dark water last.
    s["regions"] = m["land"] + hidden + s["regions"] + v["regions"] + m["sea"]
    s["points"] = m["points"] + s["points"] + [{"kind": "spawn", "tier": 1, "x": v["spawn"][0], "z": v["spawn"][1]}]
    fit(s)
    head = (f"# Round r6 {key}: {v['note']}\n"
            f"# GENERATED by gen.py from ../refs/5-formena-river.yaml; edit gen.py, not this file.\n"
            f"# Render: py -3.10 tools/world/plan.py render docs/design/world/r6/{key}.yaml PLANDIR --px 64\n")
    with open(os.path.join(HERE, f"{key}.yaml"), "w", encoding="utf-8") as f:
        f.write(head)
        yaml.safe_dump(s, f, default_flow_style=None, sort_keys=False, width=140)


if __name__ == "__main__":
    for key, v in VERSIONS.items():
        build(key, v)
        print("wrote", key)
