import yaml, sys
s = yaml.safe_load(open("docs/design/world/r7/main.yaml", encoding="utf-8"))
# --- land: drop the southern desert lobe from the mainland and the tropical isle; the south-east becomes islands
L = s["landmasses"]
main = L[0]
lobe = [[8810, 7610], [7520, 10190], [7520, 14060], [4940, 16640], [1930, 15350], [898, 11050]]
s["landmasses"][0] = [p for p in main if p not in lobe]
del s["landmasses"][4]
import math
def blob(cx, cz, r, sx=1.0, sz=1.0, n=9, rot=0.3):
    return [[round(cx + r * sx * math.cos(rot + 2 * math.pi * i / n) * (0.85 + 0.3 * ((i * 37) % 5) / 4)),
             round(cz + r * sz * math.sin(rot + 2 * math.pi * i / n) * (0.85 + 0.3 * ((i * 53) % 5) / 4))] for i in range(n)]
isles = {
    "desert":  [[800, 10600], [4600, 10000], [7600, 11200], [8000, 14000], [6600, 16400], [3200, 17000], [900, 15600], [200, 12800]],
    "volcano": blob(11600, 12300, 1300),
    "jungle":  blob(17200, 12600, 2200, 1.0, 1.1),
    "mangrove":blob(12300, 17600, 1500, 1.2, 0.9),
    "savanna": blob(18200, 18300, 1500, 1.1, 0.9),
    "bamboo":  blob(6000, 19700, 1000, 1.3, 0.8),
    "mesa":    blob(19500, 7600, 1000, 1.0, 1.15),
}
s["landmasses"] += list(isles.values())
# archipelago coasts: moderate roughness so islands keep their identity (straits stay open)
s["rough_zones"] = [z for z in s["rough_zones"] if not (z.get("polygon") and z["polygon"][0] == [8380, 8040])]
s["rough_zones"].append({"polygon": [[-1500, 8500], [24576, 8500], [24576, 24576], [-1500, 24576]], "mul": 0.3})
s["rough_zones"].append({"polygon": [[15000, 3800], [24576, 3800], [24576, 9200], [15000, 9200]], "mul": 0.3})
# islet chains through the straits
s["island_chains"] += [
    {"points": [[9000, 9700], [12000, 10100], [15000, 9800]], "count": 7, "r": [110, 380], "jitter": 260},
    {"points": [[9400, 15100], [11500, 15200], [14700, 15500]], "count": 7, "r": [110, 360], "jitter": 260},
    {"points": [[200, 18400], [2500, 19300], [4300, 20200]], "count": 6, "r": [100, 340], "jitter": 240},
    {"points": [[20400, 9600], [20700, 12500], [20600, 15400]], "count": 6, "r": [100, 320], "jitter": 200},
]
s["islands"] += [{"ring": [15400, 15900, 0, 0]}] if False else []
s["islands"].append({"ring": [9600, 19600, 800, 500]})   # small lagoon atoll between desert and volcano isles
# --- regions: each island gets an exact identity, listed first so it wins
R = [r for r in s["regions"] if r.get("circle") != [15002, 12856, 3268]]
new = [
    {"tier": 3, "biomes": [[187, 2], [240, 1]], "base": 70, "relief": 50, "patch": 600, "circle": [16300, 9300, 750], "exact": True},
    {"tier": 1, "biome": 224, "base": 66, "relief": 15, "circle": [9600, 19600, 1100], "exact": True},
    {"biome": 75, "sea": True, "circle": [9600, 19600, 520]},
    {"tier": 1, "biomes": [[245, 4], [62, 1]], "base": 72, "relief": 70, "patch": 2500, "circle": [17200, 12600, 3600], "exact": True},
    {"tier": 3, "biome": 250, "base": 74, "relief": 90, "circle": [11600, 12300, 2500], "exact": True},
    {"tier": 1, "biomes": [[153, 3], [195, 1]], "base": 64, "relief": 20, "patch": 2000, "circle": [12300, 17600, 2900], "exact": True},
    {"tier": 2, "biomes": [[35, 3], [36, 1]], "base": 72, "relief": 40, "patch": 2000, "circle": [18200, 18300, 2700], "exact": True},
    {"tier": 3, "biomes": [[37, 2], [39, 1]], "base": 74, "relief": 60, "circle": [19500, 7600, 1900], "exact": True},
    {"tier": 1, "biome": 62, "base": 70, "relief": 40, "circle": [6000, 19700, 2100], "exact": True},
    {"tier": 1, "biome": 224, "base": 66, "relief": 15, "circle": [9600, 19600, 1100], "exact": True},
    {"biome": 75, "sea": True, "circle": [9600, 19600, 520]},
    {"tier": 3, "biomes": [[187, 2], [240, 1]], "base": 70, "relief": 50, "patch": 600, "circle": [16300, 9300, 750], "exact": True},
    {"biome": 75, "sea": True, "shallow": True, "polygon": [[-1500, 8500], [21500, 8500], [21500, 21800], [-1500, 21800]]},
]
s["regions"] = new + R
# haunted isle north of the jungle isle, at the Maelstrom's southern edge
s["islands"].append({"circle": [16300, 9300, 600]})
# volcano cone + black sand; mesa table-top; desert island canyon
s["ridges"].append({"points": [[11600, 12300], [11601, 12301]], "height": 180, "width": 1700, "relief": 160, "biome": 250, "biome_above": 0.3})
s["surfaces"].append({"material": "black_sand", "circle": [11600, 12300, 1900]})
s["plateaus"].append({"circle": [19500, 7600, 850], "top": 118, "wall": 50, "top_relief": 6, "relief": 40, "biome": 38, "tier": 3})
for r in s["regions"]:
    if r.get("at") == [2618, 13630]:
        r["base"] = 96
s["canyons"].append({"points": [[1200, 11200], [3800, 13200], [6200, 16600]], "width": 900, "depth": 30, "meander": 300,
                     "wall_biome": 71, "floor_biome": 82, "tier": 3})
s["points"] = [p for p in s["points"] if not (p.get("kind") == "spawn" and p.get("x") == 5800)]
s["points"] += [{"kind": "spawn", "tier": 1, "x": 3600, "z": 11200},
                {"kind": "spawn", "tier": 1, "x": 17200, "z": 13200},
                {"name": "Haunted isle", "kind": "landmark", "x": 16300, "z": 9300}]
hdr = ("# Round 8, creative slot: Shattered South. r7's north, west, centre, caldera and Maelstrom kept;\n"
       "# the south-east becomes an archipelago sea (desert, jungle, volcano, mangrove, savanna, mesa, bamboo isles).\n")
open(sys.argv[1], "w", encoding="utf-8").write(hdr + yaml.safe_dump(s, sort_keys=False, default_flow_style=None, width=140))
