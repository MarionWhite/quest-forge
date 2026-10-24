"""Round 11, hanging-valleys slot: builds fjords.yaml from divide.yaml.

Five glacial U-valleys cut into the divide's windward flank. Each valley is the gap between
sheer-walled fjell blocks (plateaus), floored by a long narrow lake (lakes polygon) and fed by
hanging side valleys: notches in the fjell walls floored by a lower plateau, so their rivers
drop over the lip into the lake. The two western valleys open to the north sea (true fjords);
the three eastern ones are inland finger lakes draining to the thousand-islands lake.

    py -3.10 make_fjords.py      (writes fjords.yaml next to this file)
"""
import math
import os

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
spec = yaml.safe_load(open(os.path.join(HERE, "divide.yaml"), encoding="utf-8"))


def interp(axis, z):
    """x of a valley axis (list of (x, z), z monotonic) at z, extrapolated flat past its ends."""
    pts = sorted(axis, key=lambda p: p[1])
    if z <= pts[0][1]:
        return pts[0][0]
    for (x1, z1), (x2, z2) in zip(pts, pts[1:]):
        if z <= z2:
            return x1 + (x2 - x1) * (z - z1) / (z2 - z1)
    return pts[-1][0]


def zs(z0, z1, step=150):
    n = max(2, int(abs(z1 - z0) / step) + 1)
    return [z0 + (z1 - z0) * i / (n - 1) for i in range(n)]


# Valleys: axis (x, z) points, half-gap between the walls, lake z-range, lake half-width,
# head (where the valley starts in the divide; None for the sea fjords, whose head is south).
V = {
    "V1": dict(axis=[(-13750, -7900), (-13900, -6300), (-14150, -4800), (-14550, -3200)], g=430,
               lake=(-8100, -4500), lw=300, sea=True),
    "V2": dict(axis=[(-10950, -8000), (-11050, -6500), (-11250, -5100), (-11550, -3900)], g=420,
               lake=(-8100, -5300), lw=290, sea=True),
    "V3": dict(axis=[(-2600, -6000), (-2500, -4600), (-2700, -2700)], g=430,
               lake=(-5050, -3000), lw=275, head=-6000),
    "V4": dict(axis=[(1950, -6100), (2200, -4500), (1950, -2900)], g=420,
               lake=(-5200, -3250), lw=265, head=-6100),
    "V5": dict(axis=[(4450, -6300), (4050, -4600), (4450, -2900)], g=420,
               lake=(-5350, -3300), lw=270, head=-6300),
}

lakes, plateaus, canyons, rivers, ridges, regions = [], [], [], [], [], []

# ---------------------------------------------------------------- finger lakes / fjords
for k, v in V.items():
    za, zb = v["lake"]
    left, right = [], []
    for z in zs(za, zb, 120):
        t = (z - za) / (zb - za)
        # widest a third of the way down, pinched at the ends; a slight waist mid-lake
        if v.get("sea"):
            w = v["lw"] * (0.55 + 0.45 * math.sin(math.pi * min(1, 0.5 + t * 0.9)) - 0.12 * math.sin(3 * math.pi * t) ** 2)
            w = max(w, v["lw"] * 0.45)
        else:
            w = v["lw"] * (0.35 + 0.65 * math.sin(math.pi * t) ** 0.6 - 0.15 * math.sin(2.5 * math.pi * t) ** 2)
        x = interp(v["axis"], z)
        left.append([round(x - w), round(z)])
        right.append([round(x + w), round(z)])
    lakes.append({"polygon": left + right[::-1]})

# ---------------------------------------------------------------- fjell blocks with notches
# A block lies between a left curve L(z) and a right curve R(z). Notches are indentations
# on a side: {side, z, a (half-width), d (depth), s (slant of the back end, + = south),
# top (hanging floor height)}. Each notch gets a hanging-valley floor plateau and a river.


def edge(axis_key, off, rag=0, ph=0.0):
    """A block edge following a valley axis; rag > 0 makes it an outer, ragged edge."""
    v = V[axis_key]
    return lambda z: interp(v["axis"], z) + off + rag * (0.6 * math.sin(z / 640 + ph) + 0.4 * math.sin(z / 270 + 2.1 * ph))


def block(name, L, R, z0, z1, top, notches=(), taper=900):
    """Polygon of a fjell block: trace L from z0 to z1, then R back up, with notches."""
    zz = zs(z0, z1, 150)

    def width_scale(z):   # the lower end narrows to a prow
        return min(1.0, (z1 - z) / taper) if taper else 1.0

    def lx(z):
        c = (L(z) + R(z)) / 2
        return c + (L(z) - c) * max(0.12, width_scale(z))

    def rx(z):
        c = (L(z) + R(z)) / 2
        return c + (R(z) - c) * max(0.12, width_scale(z))

    left = [[lx(z), z] for z in zz]
    right = [[rx(z), z] for z in zz[::-1]]

    def cut(pts, side):
        out = list(pts)
        for nt in [n for n in notches if n["side"] == side]:
            zc, a, d, s = nt["z"], nt["a"], nt["d"], nt["s"]
            sign = 1 if side == "L" else -1          # left side notch goes +x (into the block)
            ex = lx if side == "L" else rx
            keep = [p for p in out if not (zc - a <= p[1] <= zc + a)]
            ins = [[ex(zc - a), zc - a], [ex(zc - a) + sign * d, zc - a + s],
                   [ex(zc + a) + sign * d, zc + a + s], [ex(zc + a), zc + a]]
            if side == "R":
                ins = ins[::-1]
            # splice in at the right place (pts are ordered by z: ascending on L, descending on R)
            idx = next((i for i, p in enumerate(keep) if (p[1] > zc if side == "L" else p[1] < zc)), len(keep))
            out = keep[:idx] + ins + keep[idx:]
            # hanging floor: a lower plateau filling the notch, its lip on the valley wall
            hx0, hx1 = ex(zc) - sign * 40, ex(zc) + sign * (d + 250)
            plateaus.append({"polygon": [[round(hx0), round(zc - a - 40)], [round(hx1), round(zc - a + s - 40)],
                                         [round(hx1), round(zc + a + s + 40)], [round(hx0), round(zc + a + 40)]],
                             "top": nt["top"], "wall": 40, "top_relief": 6, "relief": 60})
            # its stream: from the back of the notch to the lake, over the lip
            vx = nt["valley_x"](zc)
            rivers.append({"points": [[round(ex(zc) + sign * (d - 60)), round(zc + s * 0.9)],
                                      [round(ex(zc) + sign * d * 0.45), round(zc + s * 0.4)],
                                      [round(ex(zc) - sign * 30), round(zc)],
                                      [round(vx), round(zc - (s * 0.1))]],
                           "width": 14, "meander": 50, "valley": 60, "biome": 7})
        return out

    left = cut(left, "L")
    right = cut(right, "R")
    poly = [[round(x), round(z)] for x, z in left + right]
    plateaus.append({"polygon": poly, "top": top, "wall": 55, "top_relief": 14, "relief": 110})
    return poly


def N(side, z, a, d, s, top, valley):
    ax = (lambda zz, k=valley: interp(V[k]["axis"], zz))
    return {"side": side, "z": z, "a": a, "d": d, "s": s, "top": top, "valley_x": ax}


g1, g2, g3, g4, g5 = (V[k]["g"] for k in ("V1", "V2", "V3", "V4", "V5"))
# West group: the two sea fjords (drain north, so tributaries slant north at their backs).
block("W0", edge("V1", -g1 - 1500, 280, 0.7), edge("V1", -g1), -7500, -2900, 168,
      [N("R", -6900, 170, 900, 350, 122, "V1"), N("R", -5300, 160, 850, 300, 118, "V1")])
block("W1", edge("V1", g1), edge("V2", -g2), -7700, -3600, 182,
      [N("L", -6100, 170, 800, 300, 128, "V1"), N("R", -6900, 150, 700, 280, 132, "V2"),
       N("L", -4700, 150, 700, 250, 116, "V1")])
block("W2", edge("V2", g2), edge("V2", g2 + 1500, 280, 2.3), -7800, -4100, 176,
      [N("L", -6000, 170, 900, 320, 126, "V2")])
# East group: inland finger lakes (drain south, so tributaries slant north = up-valley).
block("E0", edge("V3", -g3 - 1500, 260, 4.1), edge("V3", -g3), -6000, -2600, 166,
      [N("R", -4300, 170, 900, -380, 120, "V3")])
block("E1", edge("V3", g3), edge("V4", -g4), -6150, -2700, 186,
      [N("L", -4700, 160, 1000, -400, 128, "V3"), N("L", -3500, 150, 900, -350, 112, "V3"),
       N("R", -4300, 170, 1000, -420, 126, "V4")])
block("E2", edge("V4", g4), edge("V5", -g5), -6300, -2800, 178,
      [N("L", -3800, 150, 500, -300, 118, "V4"), N("R", -4700, 150, 500, -320, 124, "V5")])
block("E3", edge("V5", g5), edge("V5", g5 + 1400, 260, 1.4), -6300, -2700, 166,
      [N("L", -4100, 170, 850, -360, 120, "V5")])

# ---------------------------------------------------------------- valley floors and heads
for k, v in V.items():
    zl = sorted(z for _, z in v["axis"])
    if not v.get("sea"):
        zl[0] += 200
    full = [[round(interp(v["axis"], z)), round(z)] for z in zs(zl[0], zl[-1], 400)]
    canyons.append({"points": full, "width": 2 * v["g"] + 300, "depth": 0, "meander": 40,
                    "wall_biome": 74, "floor_biome": 243})
    if not v.get("sea"):
        # no head cut: the lake runs up against the divide's flank, a steep cirque headwall
        # (cutting deeper here notched the divide crest into a pass)
        hz = v["head"]
        ridges.append({"points": [[round(interp(v["axis"], hz)), hz - 700], [round(interp(v["axis"], hz)), hz - 150]],
                       "height": 62, "width": 900, "relief": 230, "biome": 89, "biome_above": 0.45})
    else:
        # the sea fjords' heads are south, where the valley climbs out into the maple woods
        za = v["lake"][1]
        head = [[round(interp(v["axis"], z)), round(z)] for z in zs(za + 550, zl[-1] + 300, 250)]
        canyons.append({"points": head, "width": 2 * v["g"] + 200, "depth": 14, "meander": 30,
                        "wall_biome": 74, "floor_biome": 243})

# Alpine crests along the wide fjell blocks: peaks standing above the flat tops.
for pts in ([[-15300, -7200], [-15450, -5600], [-15700, -3900]],
            [[-12700, -7300], [-12650, -5600], [-12900, -4300]],
            [[-9800, -7300], [-9900, -5800]],
            [[-200, -6200], [-150, -4800], [-500, -3600]],
            [[3200, -6400], [3150, -5000]],
            [[5600, -6400], [5650, -4900]],
            [[-4300, -5900], [-4250, -4400]]):
    ridges.append({"points": pts, "height": 62, "width": 1700, "relief": 120, "biome": 59, "biome_above": 0.25})
    ridges.append({"points": pts, "height": 212, "width": 1000, "relief": 210, "peak_spacing": 900,
                   "biome": 60, "biome_above": 0.55})

# Outlets: the inland lakes spill down to the thousand-islands lake.
rivers += [
    {"points": [[-2700, -3150], [-2600, -2200], [-2000, -1100], [-1500, 150]], "width": 34, "meander": 220,
     "valley": 160, "biome": 150},
    {"points": [[1950, -3400], [2050, -3000], [2210, -2650]], "width": 30, "meander": 90, "valley": 120, "biome": 150},
    {"points": [[4450, -3400], [4800, -2900], [5350, -2300]], "width": 30, "meander": 120, "valley": 120, "biome": 150},
]

spec["lakes"] = spec["lakes"] + lakes
spec["plateaus"] = spec["plateaus"] + plateaus
spec["canyons"] = spec["canyons"] + canyons
spec["ridges"] = spec["ridges"] + ridges
spec["rivers"] = spec["rivers"] + rivers
spec["regions"] = regions + spec["regions"]     # first, so they own the fjell tops
rain = spec["auto_rivers"].setdefault("rain", {})
rain["coniferous|alps forest"] = 3.2


class Dumper(yaml.SafeDumper):
    pass


def _seq(d, data):
    flow = all(isinstance(x, (int, float)) for x in data) and len(data) <= 6
    return d.represent_sequence("tag:yaml.org,2002:seq", data, flow_style=flow)


Dumper.add_representer(list, _seq)
with open(os.path.join(HERE, "fjords.yaml"), "w", encoding="utf-8") as f:
    f.write("# Round 11 - hanging valleys. Generated by make_fjords.py from divide.yaml; edit that, not this.\n")
    yaml.dump(spec, f, Dumper=Dumper, sort_keys=False, width=200)
print("lakes", len(lakes), "plateaus", len(plateaus), "rivers", len(rivers))
