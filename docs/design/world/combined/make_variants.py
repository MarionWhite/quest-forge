"""Build maelstrom-a..d.yaml from base.yaml plus one Maelstrom block placed at four sites.

    py -3.10 docs/design/world/combined/make_variants.py

The Maelstrom is defined once, relative to its centre (MAELSTROM below), so the four maps
differ only in where it sits. The block is:
  - an irregular deep basin (two overlapping basins, floor y 5) under darker water
    (vanilla Deep Ocean);
  - a ring of seven BoP Crag sea stacks, five of them T4;
  - two wrecks (black-sand BoP Volcano islets, T4) at the ring's edges;
  - a stepping-stone island just outside the ring, on the side ships approach from;
  - a "Maelstrom" landmark point.
Shallow shelves form naturally round the stacks, the wrecks and the stepping stone.
Option b also cuts a gulf into the main continent's north coast (its only coast change).
"""
import copy, math, os
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
R = 2000                                   # stack ring radius

# Stacks: (angle deg, radius factor, island radius, top y, tier or None)
STACKS = [(15, 1.08, 440, 140, 4), (65, 0.92, 380, 126, 4), (120, 1.05, 460, 150, 4),
          (170, 0.95, 400, 122, 4), (215, 1.10, 430, 146, 4), (270, 0.90, 390, 132, None),
          (320, 1.02, 450, 138, None)]
WRECKS = [100, 290]                        # default angles; at R + 1300 (a site may override)

SITES = {
    # a: the northern sea, on the way north to the Ice castle; stepping stone toward the island chain
    "a": {"at": (-4300, -10450), "step_angle": 215, "step_biome": 66, "wrecks": [355, 175],
          "note": "Northern sea, between the main continent and the northern land: the way north to the Ice castle."},
    # b: a gulf cut into the main continent's north coast, enclosed on three sides
    "b": {"at": (6200, -3500), "step_angle": 270, "step_biome": 74, "wrecks": [140, 40],
          "note": "A gulf cut into the main continent's north coast, enclosed on three sides, opening north."},
    # c: open sea east of the main continent, between the steppe and the southern desert land
    "c": {"at": (18800, 7400), "step_angle": 180, "step_biome": 246,
          "note": "Open sea east of the main continent, between the steppe and the southern desert land."},
    # d: the sound at the great river's mouth, between the main continent and the south land
    "d": {"at": (800, 8450), "step_angle": 0, "step_biome": 246,
          "note": "The sound between the main continent and the south land, where the great river empties: "
                  "the inland sea every north-south trip crosses."},
}

# Option b's coast change: the north coast between x 3000 and 8000 becomes a gulf.
B_OLD = [[3000, -6700], [8000, -6000]]
B_NEW = [[2600, -6700], [2200, -3600], [3400, -800], [6200, 300], [9000, -700], [10400, -3400], [9900, -6100]]


def polar(cx, cz, ang, r):
    a = math.radians(ang)
    return round(cx + r * math.cos(a)), round(cz + r * math.sin(a))


def maelstrom(site):
    cx, cz = site["at"]
    land_regions, sea_regions, islands, plateaus, surfaces, points = [], [], [], [], [], []
    for ang, f, r, top, tier in STACKS:
        x, z = polar(cx, cz, ang, R * f)
        islands.append({"circle": [x, z, r]})
        plateaus.append({"circle": [x, z, r - 20], "top": top, "wall": 30, "top_relief": 4, "relief": 20, "biome": 77})
        reg = {"biome": 77, "base": 70, "relief": 40, "circle": [x, z, r - 60]}
        if tier:
            reg = {"tier": tier, **reg}
        land_regions.append(reg)
    for ang in site.get("wrecks", WRECKS):
        x, z = polar(cx, cz, ang, R + 1300)
        islands.append({"circle": [x, z, 380]})
        surfaces.append({"material": "black_sand", "circle": [x, z, 460]})
        land_regions.append({"tier": 4, "biome": 250, "base": 66, "relief": 20, "circle": [x, z, 440]})
        points.append({"name": "Wreck", "kind": "landmark", "x": x, "z": z})
    x, z = polar(cx, cz, site["step_angle"], R + 2400)
    islands.append({"circle": [x, z, 600]})
    land_regions.append({"tier": 3, "biome": site["step_biome"], "base": 70, "relief": 45, "circle": [x, z, 680]})
    ox, oz = polar(0, 0, 315, 750)
    sea_regions += [{"biome": 24, "sea": True, "circle": [cx, cz, 3300]},
                    {"biome": 24, "sea": True, "circle": [cx + ox, cz + oz, 2600]}]
    basins = [{"circle": [cx, cz, 1500], "floor": 5, "wall": 140, "biome": 24},
              {"circle": [cx + ox, cz + oz, 1000], "floor": 5, "wall": 120, "biome": 24}]
    points.insert(0, {"name": "Maelstrom", "kind": "landmark", "x": cx, "z": cz})
    return dict(land_regions=land_regions, sea_regions=sea_regions, islands=islands, plateaus=plateaus,
                surfaces=surfaces, basins=basins, points=points)


def build(key):
    spec = yaml.safe_load(open(os.path.join(HERE, "base.yaml"), encoding="utf-8"))
    site, m = SITES[key], maelstrom(SITES[key])
    if key == "b":
        coast = spec["landmasses"][0]
        i = coast.index(B_OLD[0])
        assert coast[i + 1] == B_OLD[1]
        spec["landmasses"][0] = coast[:i] + B_NEW + coast[i + 2:]
        spec["rough_zones"].append({"circle": [6200, -3200, 4300], "mul": 0.3})   # keep the gulf clean
    spec["islands"] = spec.get("islands", []) + m["islands"]
    spec["plateaus"] = spec.get("plateaus", []) + m["plateaus"]
    spec["surfaces"] = spec.get("surfaces", []) + m["surfaces"]
    spec["basins"] = spec.get("basins", []) + m["basins"]
    spec["regions"] = m["land_regions"] + spec["regions"] + m["sea_regions"]   # stacks win land; dark water last
    spec["points"] = m["points"] + spec["points"]
    head = (f"# Combined map, Maelstrom option {key}: {site['note']}\n"
            f"# GENERATED by make_variants.py from base.yaml; edit those, not this file.\n")
    with open(os.path.join(HERE, f"maelstrom-{key}.yaml"), "w", encoding="utf-8") as f:
        f.write(head)
        yaml.safe_dump(spec, f, default_flow_style=None, sort_keys=False, width=140)


if __name__ == "__main__":
    for k in SITES:
        build(k)
        print("wrote", f"maelstrom-{k}.yaml")
