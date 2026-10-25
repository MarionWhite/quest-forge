"""Baobab (Adansonia): a massive swollen, fluted trunk that ends abruptly in a crown of short,
thick, gnarled limbs spread like roots, with small sparse leaf clumps (or bare, dry season).

Three trunk forms, picked per seed:
  bottle    - A. digitata: swollen middle, pinched neck (the classic African baobab)
  column    - A. grandidieri: tall smooth cylinder with a flat-topped crown (Avenue of the Baobabs)
  squat     - ancient, very wide base, quick taper, sprawling crown
Growth model: recursive branching of the crown limbs (2-3 orders).
"""
import math
import numpy as np
from voxel import Grid, R
from growth import draw_trunk, draw_roots, limb, draw_polyline, direction, unit

COUNTS = {'small': 6, 'medium': 8, 'large': 8, 'giant': 5}

SIZE = {
    'small':  dict(h=(9, 13), r=(1.4, 2.0)),
    'medium': dict(h=(13, 18), r=(2.2, 3.0)),
    'large':  dict(h=(17, 23), r=(3.0, 4.0)),
    'giant':  dict(h=(22, 30), r=(4.3, 5.8)),
}


def branch(g, rng, p, d, L, r, depth, tips, flat):
    pts = limb(p, d, L, rng, step=1.0, gravity=-0.02, wobble=0.18, up_bend=0.04 if not flat else -0.02)
    draw_polyline(g, pts, r, max(0.5, r * 0.6), R['branch'])
    if depth == 0 or L < 2:
        tips.append(pts[-1])
        return
    end = pts[-1]
    dd = unit(pts[-1] - pts[-2])
    for _ in range(int(rng.integers(2, 4))):
        nd = unit(dd + rng.normal(scale=0.55, size=3) + [0, 0.15 if not flat else 0.0, 0])
        branch(g, rng, end, nd, L * rng.uniform(0.4, 0.6), max(0.5, r * 0.65), depth - 1, tips, flat)


def grow(rng, size):
    s = SIZE[size]
    H = rng.uniform(*s['h']); r0 = rng.uniform(*s['r'])
    form = rng.choice(['bottle', 'bottle', 'column', 'squat'])
    if form == 'column':
        r0 *= 0.75; ht = H * rng.uniform(0.72, 0.8)
    elif form == 'squat':
        r0 *= 1.15; H *= 0.85; ht = H * rng.uniform(0.5, 0.6)
    else:
        ht = H * rng.uniform(0.6, 0.7)
    crown_r = max(3.0, (H - ht) * 1.1 + r0)
    g = Grid(crown_r + r0 + 6, H + 4, 1)
    bulge = rng.uniform(0.15, 0.3)
    lean = unit([rng.normal(), 0, rng.normal()]) * rng.uniform(0, 0.05) * H

    def radius(y):
        f = min(max(y, 0) / ht, 1.0)
        if form == 'column':
            r = r0 * (1.08 - 0.22 * f)
        elif form == 'squat':
            r = r0 * (1.0 - 0.45 * f ** 0.9)
        else:
            r = r0 * (0.95 + bulge * math.sin(math.pi * min(f * 1.15, 1.0)) - 0.35 * f ** 3)
        r += r0 * 0.25 * math.exp(-max(y, 0) / 1.5)               # foot flare
        return r

    def centre(y):
        f = max(y, 0) / H
        return lean[0] * f, lean[2] * f

    k = int(rng.integers(7, 12)); ph = rng.uniform(0, 6.3)

    def lobes(y):
        return [(k, 0.06, ph + y * 0.05), (2, 0.07, ph * 0.5), (3, 0.04, ph * 1.3)]

    draw_trunk(g, -1, ht, radius, centre, rng, lobes, role=R['trunk'])
    draw_roots(g, rng, int(rng.integers(4, 7)), radius(0) * 0.9, r0 * 0.6 + 1, y_top=1.2, y_end=-0.3,
               r_root=max(0.6, r0 * 0.25))

    # crown limbs leave the rim of the trunk top
    tips = []
    rt = radius(ht)
    cx, cz = centre(ht)
    n = int(rng.integers(5, 9))
    a0 = rng.uniform(0, 6.3)
    flat = form == 'column'
    for i in range(n):
        a = a0 + 2 * math.pi * i / n + rng.uniform(-0.3, 0.3)
        p = np.array([cx, ht - rng.uniform(0, 1.5), cz]) + direction(a, 0) * rt * rng.uniform(0.3, 0.7)
        el = rng.uniform(0.35, 0.75) if not flat else rng.uniform(0.25, 0.5)
        L = (H - ht) * rng.uniform(0.5, 0.75) + 1
        branch(g, rng, p, direction(a, el), L, max(0.75, rt * rng.uniform(0.32, 0.45)),
               2 if size in ('large', 'giant') else 1, tips, flat)
    # a stubby central limb or two
    for _ in range(int(rng.integers(0, 3))):
        p = np.array([cx, ht, cz])
        branch(g, rng, p, unit([rng.normal() * 0.3, 1, rng.normal() * 0.3]), (H - ht) * 0.6, max(0.75, rt * 0.3), 1,
               tips, flat)

    leafy = rng.random() < 0.75
    for t in tips:
        if leafy:
            rr = rng.uniform(1.2, 1.9)
            g.blob(t + [0, 0.4, 0], rr, rr * 0.6, rr, R['leaf'], rng, rough=0.45, fill=0.85)
        elif rng.random() < 0.25:
            g.blob(t, 0.9, 0.7, 0.9, R['leaf'], rng, rough=0.5)
    g.prune_floating_leaves()
    return g, dict(form=str(form), height=round(H, 1), radius=round(r0, 2), trunk_height=round(ht, 1), leafy=leafy)
