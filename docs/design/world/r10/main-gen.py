# Round 10, main: r9 thousand with the three approved changes and nothing else:
#   1. terrain-following auto rivers (hand rivers they make redundant removed),
#   2. a mountain backbone across the main continent,
#   3. the volcano complex moved west and a little south, every element by one offset.
#   py -3.10 docs/design/world/r10/main-gen.py     (run from the repo root)
import math, yaml
import numpy as np

s = yaml.safe_load(open("docs/design/world/r9/thousand.yaml", encoding="utf-8"))

# ---------------------------------------------------------------- 3. move the volcano
OLD = (-4520, -1850)
DX, DZ = -3000, 1000          # west and a little south; the crag rim stays ~3 km clear of the redwood strip
def mv(c):
    if list(c[:2]) == list(OLD):
        return [c[0] + DX, c[1] + DZ] + list(c[2:])
    return c
for key in ("lakes", "islands", "surfaces", "regions"):
    for e in s.get(key, []):
        if "circle" in e:
            e["circle"] = mv(e["circle"])
for r in s["ridges"]:
    if "arc" in r:
        r["arc"] = mv(r["arc"])
    elif "points" in r and abs(r["points"][0][0] - OLD[0]) < 2 and abs(r["points"][0][1] - OLD[1]) < 2:
        r["points"] = [[x + DX, z + DZ] for x, z in r["points"]]
# The crater's sea paint was region-warped; at the new site the warp no longer lines up with the
# lake, so pin it exactly.
for r in s["regions"]:
    if r.get("sea") and r.get("circle", [0])[:2] == [OLD[0] + DX, OLD[1] + DZ]:
        r["exact"] = True

# ---------------------------------------------------------------- 1. rivers
# Keep the deliberate ones: the lake's great outflow to the gulf and the corrupted core's
# Dead Swamp river (it runs north through the pass between the backbone and the NE alps).
keep = []
for r in s["rivers"]:
    p0 = r["points"][0]
    if p0 == [3200, 6500] or r.get("biome") == 79:
        keep.append(r)
s["rivers"] = keep
s["auto_rivers"] = {"cell": 128, "threshold_km2": 10, "min_width": 14, "max_width": 100}

# ---------------------------------------------------------------- 2. the backbone
# One great range from the volcano's north-east shoulder across the north of the continent to the
# Dead Swamp pass: separate crests (passes between them) of different heights, spurs north to the
# coast and south toward the lake country, and a lower southern range down the south-east lobe.
def ridge(points, height, width, relief=190, biome=None, above=0.6, spacing=1400):
    r = {"points": points, "height": height, "width": width, "relief": relief, "peak_spacing": spacing}
    if biome:
        r.update({"biome": biome, "biome_above": above})
    return r

ALPS = 60   # snow only along the highest crest lines; the flanks keep their forests
crests = [
    # west massif, rising off the volcano's crag
    ridge([[-6400, -4600], [-5000, -5900], [-3000, -6500]], 190, 2000, 200, ALPS, 0.8, 1300),
    # pass at ~(-2300, -6600); then the high central massif, the range's roof
    ridge([[-1600, -6700], [200, -7100], [2100, -6600], [3700, -6900]], 220, 2500, 220, ALPS, 0.72, 1700),
    # its lower southern fore-range: a high valley between the two crests
    ridge([[-900, -4900], [900, -5000], [2600, -4600]], 160, 1400, 180, None, 0.7, 1100),
    # pass at ~(4400, -6600); then the eastern crest, lower and broken
    ridge([[5100, -6400], [6500, -6900], [7900, -6400]], 180, 1800, 190, ALPS, 0.82, 1100),
    # long spurs: one parts the volcano from the lake country, one frames the north arm
    ridge([[-3000, -6500], [-3400, -4400], [-3000, -2300], [-3500, -500]], 165, 1300, 180, None, 0.7, 1000),
    ridge([[2100, -6600], [3700, -4900], [4100, -3300]], 145, 1100, 160, None, 0.7, 900),
    # the southern range down the south-east lobe, between the eucalyptus and the western plains
    ridge([[5700, 7300], [5200, 9300], [4900, 11300], [4000, 13500]], 170, 1900, 180, None, 0.7, 1200),
]
# Ribs: short side ridges off every crest, alternating sides, so each range reads as a spine
# with valleys between its ribs rather than one wall. Rivers form in those valleys.
rng = np.random.default_rng(1010)
ribs = []
for c in crests:
    pts = np.array(c["points"], float)
    seg = np.diff(pts, axis=0)
    L = np.hypot(*seg.T)
    cum = np.concatenate([[0], np.cumsum(L)])
    t, side = 700.0, 1
    while t < cum[-1] - 500:
        k = min(np.searchsorted(cum, t, side="right") - 1, len(seg) - 1)
        p = pts[k] + seg[k] * (t - cum[k]) / L[k]
        d = seg[k] / L[k]
        nrm = np.array([-d[1], d[0]]) * side
        ang = rng.uniform(-0.6, 0.6)
        v = nrm * math.cos(ang) + d * math.sin(ang)
        ln = rng.uniform(1500, 2900) * (c["width"] / 2000) ** 0.5
        mid = p + v * ln * 0.5 + nrm * rng.normal(0, 150)
        end = p + v * ln
        ribs.append(ridge([[round(x), round(z)] for x, z in (p, mid, end)],
                          round(c["height"] * rng.uniform(0.62, 0.78)), round(c["width"] * 0.5), 150, None, 0.7, 800))
        t += rng.uniform(1100, 1700)
        side = -side
backbone = crests + ribs
s["ridges"] += backbone

hdr = ("# Round 10, main: r9 thousand + auto rivers, a mountain backbone, and the volcano moved west/south.\n"
       "# Generated by main-gen.py.\n")
open("docs/design/world/r10/main.yaml", "w", encoding="utf-8").write(
    hdr + yaml.safe_dump(s, sort_keys=False, default_flow_style=None, width=140))
print("rivers kept", len(keep), "ridges", len(s["ridges"]))
