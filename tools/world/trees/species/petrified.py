"""Petrified trees: dead trees turned to stone. Gnarled fluted trunks, broken limbs, no leaves,
moss (mossy cobble / mossy brick) on upward-facing surfaces near the ground, and fallen
fragments around the foot.

Styles (picked per seed):
  snag   - a dead broadleaf: gnarled trunk, crooked recursive limbs with snapped ends
  spire  - a tall twisted trunk with a few stubs and a broken, jagged top
  split  - trunk splits into two or three heavy leaning leaders
Growth model: recursive branching with strong random turns (gnarl) and early termination.
"""
import math
import numpy as np
from voxel import Grid, R
from growth import draw_trunk, draw_roots, limb, draw_polyline, direction, unit

COUNTS = {'small': 8, 'medium': 10, 'large': 8, 'giant': 5}

SIZE = {
    'small':  dict(h=(6, 10), r=(0.7, 1.0)),
    'medium': dict(h=(10, 16), r=(1.1, 1.5)),
    'large':  dict(h=(16, 24), r=(1.6, 2.2)),
    'giant':  dict(h=(24, 34), r=(2.4, 3.2)),
}


def grow(rng, size):
    s = SIZE[size]
    H = rng.uniform(*s['h']); r0 = rng.uniform(*s['r'])
    style = str(rng.choice(['snag', 'spire', 'split'], p=[0.5, 0.25, 0.25]))
    g = Grid(H * 0.6 + r0 + 4, H + 4, 1)
    # gnarled centre path: smoothed random walk
    steps = int(H) + 2
    walk = np.cumsum(rng.normal(0, 0.18, (steps, 2)), axis=0)
    lean = unit([rng.normal(), 0, rng.normal()])[[0, 2]] * rng.uniform(0, 0.12)
    walk += np.outer(np.arange(steps), lean)
    for _ in range(2):
        walk[1:-1] = 0.5 * walk[1:-1] + 0.25 * (walk[:-2] + walk[2:])
    walk -= walk[0]

    def centre(y):
        i = int(min(max(y, 0), steps - 1))
        return float(walk[i, 0]), float(walk[i, 1])

    ht = H * (0.92 if style == 'spire' else rng.uniform(0.45, 0.65))

    def radius(y):
        f = min(max(y, 0) / ht, 1)
        top = 0.35 if style != 'spire' else 0.5
        return r0 * (1 - (1 - top) * f) + r0 * 0.45 * math.exp(-max(y, 0) / 2)

    k = int(rng.integers(3, 6)); ph = rng.uniform(0, 6.3)
    draw_trunk(g, -1, ht, radius, centre, rng, lambda y: [(k, 0.14, ph + y * 0.12), (2, 0.06, ph)])
    draw_roots(g, rng, int(rng.integers(4, 7)), radius(0), r0 + 1.5 + H * 0.05, y_top=1.6, y_end=-0.3,
               r_root=max(0.5, r0 * 0.45))

    def gnarl(p, d, L, r, depth):
        pts = limb(p, d, L, rng, step=1.0, gravity=rng.uniform(-0.08, 0.02), wobble=0.3, up_bend=0.03)
        if rng.random() < 0.35:                     # snapped off
            pts = pts[:max(2, int(len(pts) * rng.uniform(0.4, 0.8)))]
        draw_polyline(g, pts, r, max(0.5, r * 0.55), R['branch'])
        if depth == 0 or len(pts) < 3:
            return
        for _ in range(int(rng.integers(1, 4))):
            j = int(rng.integers(len(pts) // 2, len(pts)))
            nd = unit(unit(pts[-1] - pts[-2]) + rng.normal(scale=0.7, size=3) + [0, 0.25, 0])
            gnarl(pts[j], nd, L * rng.uniform(0.45, 0.7), max(0.5, r * 0.6), depth - 1)

    depth = {'small': 1, 'medium': 2, 'large': 2, 'giant': 3}[size]
    cx, cz = centre(ht)
    top = np.array([cx, ht, cz])
    if style == 'snag':
        n = int(rng.integers(3, 6))
        for i in range(n):
            a = rng.uniform(0, 6.3)
            y = rng.uniform(ht * 0.55, ht)
            x0, z0 = centre(y)
            gnarl(np.array([x0, y, z0]), direction(a, rng.uniform(0.2, 0.9)), (H - ht) * rng.uniform(0.6, 1.0) + 2,
                  max(0.6, radius(y) * 0.55), depth)
        gnarl(top, unit([rng.normal() * 0.3, 1, rng.normal() * 0.3]), H - ht, max(0.6, radius(ht) * 0.8), depth)
    elif style == 'split':
        n = int(rng.integers(2, 4))
        a0 = rng.uniform(0, 6.3)
        for i in range(n):
            a = a0 + 2 * math.pi * i / n + rng.uniform(-0.4, 0.4)
            gnarl(top, direction(a, rng.uniform(0.9, 1.25)), H - ht, max(0.7, radius(ht) * 0.75), depth)
    else:  # spire: stubs and a jagged broken top
        for _ in range(int(rng.integers(2, 6))):
            y = rng.uniform(ht * 0.3, ht * 0.9)
            x0, z0 = centre(y)
            gnarl(np.array([x0, y, z0]), direction(rng.uniform(0, 6.3), rng.uniform(-0.1, 0.6)),
                  rng.uniform(1.5, 2 + H * 0.12), max(0.5, radius(y) * 0.4), 0)
        for _ in range(int(rng.integers(2, 4))):
            q = top + [rng.uniform(-1, 1) * radius(ht) * 0.6, 0, rng.uniform(-1, 1) * radius(ht) * 0.6]
            g.capsule(q, q + [rng.normal() * 0.4, rng.uniform(1, 4), rng.normal() * 0.4], 0.6, 0.5, R['trunk'])

    # fallen fragments around the foot
    for _ in range(int(rng.integers(1, 3 + int(r0 * 2)))):
        a = rng.uniform(0, 6.3); d = r0 + rng.uniform(1.5, 3 + H * 0.15)
        p = np.array([math.cos(a) * d, 0.3, math.sin(a) * d])
        if rng.random() < 0.5:
            q = p + direction(rng.uniform(0, 6.3), 0) * rng.uniform(2, 2 + H * 0.2)
            g.capsule(p, q, rng.uniform(0.5, 0.5 + r0 * 0.3), 0.5, R['branch'])
        else:
            g.blob(p, 1.0, 0.8, 1.0, R['root'], rng, rough=0.4)

    moss(g, rng, H)
    return g, dict(style=style, height=round(H, 1), radius=round(r0, 2))


def moss(g, rng, H):
    """Upward-facing stone in the lower part of the tree turns mossy."""
    role = g.role
    stone = np.isin(role, [R['trunk'], R['branch'], R['root']])
    open_up = np.zeros_like(stone); open_up[:-1] = role[1:] == 0
    ys = (np.arange(role.shape[0]) - g.below)[:, None, None]
    p = np.clip(0.75 - ys / (H * 0.6), 0.05, 0.75)
    m = stone & open_up & (rng.random(role.shape) < p)
    role[m] = R['bark']
