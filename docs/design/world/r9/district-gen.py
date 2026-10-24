"""Round 9, Lake District: r8 enchanted with a chain of six medium lakes stepping down from the
corrupted core to the southern gulf, linked by one river. Shores move from friendly (gulf end)
through fairy and dark-wood to haunted and corrupted (highland end).
Run from the repo root:  py -3.10 docs/design/world/r9/district-gen.py"""
import math, yaml, numpy as np

s = yaml.safe_load(open("docs/design/world/r8/enchanted.yaml", encoding="utf-8"))


def ragged(cx, cz, R, aspect, rot, seed, amp=0.38, n=160, fmin=0.72):
    """A lobed outline: semi-major R along angle rot (deg), minor R*aspect."""
    g = np.random.default_rng(seed)
    terms = [(k, g.uniform(0, 6.283), 0.32 / k ** 0.9) for k in range(2, 30)]
    c, sn = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    out = []
    for i in range(n):
        t = 2 * math.pi * i / n
        f = max(1 + sum(a * math.sin(k * t + ph) for k, ph, a in terms) * amp, fmin)
        u, v = R * f * math.cos(t), R * aspect * f * math.sin(t)
        out.append([round(cx + u * c - v * sn), round(cz + u * sn + v * c)])
    return out


def along(cx, cz, rot, d):
    return [round(cx + d * math.cos(math.radians(rot))), round(cz + d * math.sin(math.radians(rot)))]


# Lakes from the highland (corrupted) end down to the gulf (friendly) end.
# x, z, semi-major R, aspect, rot, inner shore, outer cell biomes, cell base, islands [(offset, r, biome)]
LAKES = [
    (10300, -3400, 1150, 0.70, 150, [[238, 1]], [[79, 3], [64, 1]], 88, [(-420, 360, 251)]),
    (7500, -1500, 1450, 0.55, 20, [[240, 1]], [[187, 3], [78, 1]], 84, [(450, 380, 240)]),
    (4700, 700, 1550, 0.55, 125, [[185, 1]], [[29, 4], [185, 1]], 80, [(-550, 400, 185), (650, 280, 29)]),
    (3400, 3900, 1350, 0.60, 75, [[88, 1]], [[132, 1]], 76, [(-450, 380, 88)]),
    (4200, 7100, 1250, 0.58, 170, [[145, 1]], [[235, 3], [145, 1]], 72, [(420, 360, 235)]),
    (5000, 10000, 1050, 0.66, 40, [[152, 1]], [[229, 3], [199, 1]], 68, [(-300, 320, 199)]),
]
TIERS = [4, 3, 3, 2, 1, 1]

R = s["regions"]
# Drop the r8 corrupted-core circles' inner sludge disc and its two ponds; the core lake replaces them.
R[:] = [r for r in R if not (r.get("circle") == [10500, -3200, 1400])]
s["ponds"] = [p for p in s["ponds"] if p["at"] not in ([11300, -2600], [9700, -3900])]
for r in R:
    if r.get("circle") == [10500, -3200, 2600]:
        r.update({"base": 86, "relief": 30, "circle": [10300, -3400, 2900]})
    at = r.get("at")
    if at == [6660, -990]:          # Mystic Grove cell: the chain's cells take over; shrink it east
        r.update({"at": [9600, 600], "size": 0.5, "biomes": [[185, 3], [29, 1]]})
    if at == [640, 2708]:           # central grassland -> the autumn band south of the volcano
        r.update({"at": [-600, 3000], "biomes": [[229, 3], [199, 1], [138, 1]], "relief": 45})
    if at == [5198, -8128]:         # north boreal -> mega spruce taiga
        r["biomes"] = [[160, 3], [32, 1]]
    if at == [13110, -7870]:        # northeast snowy conifers under the Alps -> Alps forest
        r["biomes"] = [[59, 3], [239, 2]]
    if at == [-3660, -8128]:        # north-centre conifers with heath
        r["biomes"] = [[74, 3], [141, 2]]

new_first, new_cells, arms = [], [], []
for i, (x, z, Rr, asp, rot, inner, outer, base, isl) in enumerate(LAKES):
    lake = ragged(x, z, Rr, asp, rot, 900 + i, amp=0.5, fmin=0.6)
    s["lakes"].append({"polygon": lake})
    # One long arm per lake, Finnish style: a narrow ragged bay reaching off the main basin.
    arm_a = rot + (65 if i % 2 else -70)
    ax, az = along(x, z, arm_a, Rr * asp * 1.05)
    arm = ragged(ax, az, Rr * 0.65, 0.32, arm_a + 15, 970 + i, amp=0.45, fmin=0.6)
    b_a = rot + 180 + (30 if i % 2 else -35)    # a shorter second bay on the far side
    bx, bz = along(x, z, b_a, Rr * 0.85)
    arm2 = ragged(bx, bz, Rr * 0.45, 0.4, b_a - 20, 990 + i, amp=0.45, fmin=0.6)
    for a_ in (arm, arm2):
        s["lakes"].append({"polygon": a_})
        arms.append(a_)
    for off, r_, b in isl:
        cx, cz = along(x, z, rot, off)
        s["islands"].append({"circle": [cx, cz, r_]})
        new_first.append({"biome": b, "base": base - 4, "relief": 30,
                          "circle": [cx, cz, r_ + 200], "exact": True})
    # The shore character sits at the inflow end (a delta, marsh or grove), not as a ring.
    px_, pz_ = LAKES[i - 1][:2] if i else (12500, -5400)
    L = math.hypot(px_ - x, pz_ - z)
    sx, sz = x + (px_ - x) / L * Rr * 0.6, z + (pz_ - z) / L * Rr * 0.6
    shore = ragged(sx, sz, Rr * 0.8 + 450, 0.75, rot + 40, 950 + i, amp=0.45, fmin=0.55)
    new_first.append({"biomes": inner, "base": base - 6, "relief": 12,
                      "polygon": shore, "exact": True, "_lake": lake})
    cell = {"tier": TIERS[i], "biomes": outer, "base": base, "relief": 45, "patch": 2200,
            "at": [x, z], "size": 0.8}
    if i == 4:
        cell["lakes"] = [8, 80, 240]
    new_cells.append(cell)

extra = [
    # Jade Cliffs: karst heights on the west bank between the dark-wood and fairy lakes.
    {"tier": 3, "biome": 143, "base": 110, "relief": 140, "polygon": ragged(1500, 300, 1500, 0.7, 100, 77, amp=0.55, fmin=0.5), "exact": True},
    # Ice Plains Spikes around the Ice castle.
    {"tier": 4, "biome": 140, "base": 76, "relief": 25, "polygon": ragged(7520, -16298, 2300, 0.8, 0, 78, amp=0.55, fmin=0.5), "exact": True},
    # Rainforest interior of the tropical peninsula, Tropics left on its rim.
    {"tier": 1, "biome": 195, "base": 74, "relief": 50, "polygon": ragged(15200, 12700, 2300, 0.8, 30, 79, amp=0.55, fmin=0.5), "exact": True},
]
# Ice castle's own Frost Forest circle must stay ahead of the spikes ring: hoist it.
castle = [r for r in R if r.get("circle") == [7520, -16298, 688]]
R[:] = [r for r in R if r.get("circle") != [7520, -16298, 688]]
R[:] = castle + new_first + extra + R + new_cells + [
    {"tier": 1, "biome": 83, "base": 72, "relief": 40, "patch": 2500, "at": [6400, 12200], "size": 0.9},
]
# Freshwater: river biome on every lake; sea regions paint in order, so these go last.
for r in list(new_first):
    if "_lake" in r:
        R.append({"biome": 7, "sea": True, "exact": True, "polygon": r.pop("_lake")})
for a in arms:
    R.append({"biome": 7, "sea": True, "exact": True, "polygon": a})

# Rivers: one chain river from the core through every lake to the gulf; old central rivers go.
riv = s["rivers"]
riv[:] = [rv for rv in riv if rv["points"][0] not in ([10960, 2450], [6660, 1160], [8380, 11910])]
chain = [[x, z] for x, z, *_ in LAKES]
# Shore-to-shore links (starting inside each lake), so no river cuts across an island.
for i in range(len(LAKES) - 1):
    (x1, z1, r1), (x2, z2, r2) = LAKES[i][:3], LAKES[i + 1][:3]
    L = math.hypot(x2 - x1, z2 - z1)
    ux, uz = (x2 - x1) / L, (z2 - z1) / L
    riv.append({"points": [[round(x1 + ux * r1 * 0.5), round(z1 + uz * r1 * 0.5)],
                           [round(x2 - ux * r2 * 0.5), round(z2 - uz * r2 * 0.5)]],
                "width": 50 + 8 * i, "meander": 300, "valley": 220, "biome": 7 if i < 2 else 150})
riv.append({"points": [[4400, 10300], [2600, 10700], [800, 11100], [-400, 11300]], "width": 100, "meander": 380, "valley": 260, "biome": 150})
for rv in riv:
    if rv["points"][0] == [4510, 13372]:      # southern tributary now joins the outflow
        rv["points"] = [[4510, 13372], [3200, 12000], [2400, 10750]]
riv.append({"points": [[8380, 11910], [7262, 9244], [6000, 7600], [5300, 7300]], "width": 36, "biome": 150})
riv.append({"points": [[-2200, 1600], [-200, 2900], [2200, 3700]], "width": 34, "biome": 150})

for p in s["points"]:
    if p.get("name") == "Corrupted core":
        p["x"], p["z"] = 10300, -3400
    if p.get("x") == 640 and p.get("z") == 3912:
        p["x"], p["z"] = 3300, 9600
hdr = "# Round 9, Lake District: r8 enchanted with a chain of six lakes stepping from the corrupted core to the southern gulf.\n"
open("docs/design/world/r9/district.yaml", "w", encoding="utf-8").write(
    hdr + yaml.safe_dump(s, sort_keys=False, default_flow_style=None, width=140))
print("ok")
