import yaml, math, numpy as np, sys
LX, LZ, LR = float(sys.argv[1]), float(sys.argv[2]), float(sys.argv[3])
s = yaml.safe_load(open("docs/design/world/r7/main.yaml", encoding="utf-8"))
rng = np.random.default_rng(8)
# A ragged lake outline: lobes at several scales plus per-vertex jitter.
def ragged(R, seed, n=180, aspect=0.8):
    g = np.random.default_rng(seed)
    terms = [(k, g.uniform(0, 6.283), 0.32 / k ** 0.9) for k in range(2, 40)]
    out = []
    for i in range(n):
        t = 2 * math.pi * i / n
        f = 1 + sum(a * math.sin(k * t + ph) for k, ph, a in terms) * 0.55
        f = max(f, 0.45)
        out.append([round(LX + R * f * math.cos(t)), round(LZ + R * aspect * f * math.sin(t))])
    return out
pts = ragged(LR, 8)
shore = ragged(LR * 1.3, 9)
s["lakes"].append({"polygon": pts})
s["islands"] += [{"circle": [LX - 1300, LZ - 700, 850]}, {"circle": [LX + 1500, LZ + 300, 700]},
                 {"circle": [LX + 200, LZ + 1100, 560]}, {"circle": [LX - 300, LZ - 1700, 220]},
                 {"circle": [19200, 6900, 900]}]
R = s["regions"]
# Grassland cells become lakeshore transitions; a savanna cell carries the shore toward the desert.
for r in R:
    if r.get("at") == [640, 2708]:
        r.update({"biomes": [[253, 3], [138, 2]], "tier": 2})
    if r.get("at") == [6660, -990]:
        r.update({"biomes": [[138, 3], [169, 2]]})
R.append({"tier": 2, "biomes": [[35, 3], [70, 1]], "base": 72, "relief": 40, "patch": 3000, "at": [6200, 6600], "size": 0.6})
new = [
    {"tier": 2, "biome": 185, "base": 72, "relief": 40, "circle": [LX - 1300, LZ - 700, 1050], "exact": True},   # Mystic Grove isle
    {"tier": 2, "biome": 87, "base": 70, "relief": 30, "circle": [LX + 1500, LZ + 300, 880], "exact": True},    # Fungi Forest isle
    {"tier": 1, "biome": 189, "base": 70, "relief": 25, "circle": [LX + 200, LZ + 1100, 720], "exact": True},   # Origin Valley isle
    {"tier": 2, "biome": 77, "base": 74, "relief": 60, "circle": [LX - 300, LZ - 1700, 320], "exact": True},    # Crag rock
    {"tier": 3, "biomes": [[187, 2], [240, 1]], "base": 72, "relief": 50, "patch": 600,
     "circle": [19200, 6900, 1100], "exact": True},                                                            # haunted isle
    {"tier": 2, "biomes": [[159, 2], [252, 2], [84, 1]], "base": 63, "relief": 6, "patch": 900,
     "polygon": shore, "exact": True},                                                            # marsh and reed-bed shore
]
s["regions"] = new + R
s["regions"].insert(len(new), {"biome": 7, "sea": True, "polygon": pts})   # freshwater
s["plateaus"].append({"circle": [LX - 300, LZ - 1700, 220], "top": 110, "wall": 25, "top_relief": 4, "relief": 20, "biome": 77})
# Rivers: the long east river now feeds the lake; one great river drains it to the southern gulf.
riv = s["rivers"]
riv[0]["points"] = [[10960, 2450], [9300, 2700], [LX + LR * 1.05, LZ + 400]]
riv[1]["points"] = [[LX + 600, LZ + LR * 0.8], [3900, 6100], [2400, 7300], [640, 8212]]
riv[1].update({"width": 110, "meander": 380, "valley": 260, "biome": 150})
riv += [{"points": [[1758, -4000], [2600, -1800], [LX - 500, LZ - LR * 0.75]], "width": 40},
        {"points": [[9600, -3800], [7800, -1200], [LX + LR * 0.8, LZ - 1500]], "width": 36},
        {"points": [[-1200, 2600], [LX - LR * 1.0, LZ + 600]], "width": 32}]
for p_ in s["points"]:
    if p_.get("x") == 640 and p_.get("z") == 3912:
        p_["x"], p_["z"] = -1400, 4300
s["points"].append({"name": "Haunted isle", "kind": "landmark", "x": 19200, "z": 6900})
hdr = "# Round 8, Great Lake: r7 with the central grassland replaced by a vast freshwater lake.\n"
open("docs/design/world/r8/great-lake.yaml", "w", encoding="utf-8").write(hdr + yaml.safe_dump(s, sort_keys=False, default_flow_style=None, width=140))
print("ok")
