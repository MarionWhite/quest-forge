"""Eucalyptus (mountain ash / ghost gum / blue gum): tall, pale, smooth trunk with a long clear
bole, often forking into two or three leaders; an open, lumpy, see-through crown high up, made
of drooping leaf clumps. Some trees keep a rough dark "stocking" of bark on the lower trunk.

Growth model: tapered trunk + space colonisation inside a crown built from a few separate lumps
(eucalypt crowns are clumpy, not round), with high kill distance so the crown stays airy.
"""
import math
import numpy as np
from voxel import Grid, R
from growth import draw_trunk, draw_roots, trunk_chain, grow_crown, sample_envelope, unit

COUNTS = {'small': 6, 'medium': 10, 'large': 10, 'giant': 5}

SIZE = {
    'small':  dict(h=(14, 20), r=(0.6, 0.8)),
    'medium': dict(h=(22, 32), r=(1.0, 1.3)),
    'large':  dict(h=(34, 46), r=(1.5, 2.0)),
    'giant':  dict(h=(48, 62), r=(2.1, 2.7)),
}


def grow(rng, size):
    s = SIZE[size]
    H = rng.uniform(*s['h']); r0 = rng.uniform(*s['r'])
    bole = rng.uniform(*{'small': (0.35, 0.5), 'medium': (0.45, 0.6)}.get(size, (0.5, 0.62)))
    yf = H * bole                                   # where the crown / forks start
    cw = H * rng.uniform(0.18, 0.26)
    g = Grid(cw + r0 + 6, H + 4, 1)
    lean = unit([rng.normal(), 0, rng.normal()]) * rng.uniform(0, 0.06) * H
    bend = rng.uniform(0, 6.3); bamp = rng.uniform(0.0, 0.6) * (1 + r0)

    def centre(y):
        f = max(y, 0) / H
        return (lean[0] * f ** 1.4 + bamp * math.sin(f * 3.1) * math.cos(bend),
                lean[2] * f ** 1.4 + bamp * math.sin(f * 3.1) * math.sin(bend))

    def radius(y):
        f = min(max(y, 0) / yf, 1)
        return r0 * (1 - 0.45 * f) + r0 * 0.35 * math.exp(-max(y, 0) / 2)

    ph = rng.uniform(0, 6.3)
    draw_trunk(g, -1, yf, radius, centre, rng, lambda y: [(3, 0.05, ph)])
    if rng.random() < 0.4:                         # rough-barked stocking on the lower trunk
        hs = yf * rng.uniform(0.2, 0.45)
        draw_trunk(g, -1, hs, lambda y: radius(y) + 0.2, centre, rng, lambda y: [(5, 0.1, ph + y)],
                   role=R['bark'])
    if size != 'small':
        draw_roots(g, rng, int(rng.integers(3, 6)), radius(0), r0 + 1.5, y_top=1.5, y_end=-0.2,
                   r_root=max(0.5, r0 * 0.35))

    # crown: a few separate lumps, high up, spread around
    cx, cz = centre(yf)
    lumps = []
    for k in range(int(rng.integers(3, 7))):
        a = rng.uniform(0, 6.3)
        d = rng.uniform(0.2, 0.7) * cw
        y = rng.uniform(yf + (H - yf) * 0.3, H - 2)
        lumps.append((cx + math.cos(a) * d, y, cz + math.sin(a) * d, cw * rng.uniform(0.35, 0.55),
                      (H - yf) * rng.uniform(0.25, 0.4)))
    lumps.append((cx, H - 2.5, cz, cw * 0.35, 2.5))

    def inside(P):
        m = np.zeros(len(P), bool)
        for x, y, z, a, b in lumps:
            m |= ((P[:, 0] - x) / a) ** 2 + ((P[:, 1] - y) / b) ** 2 + ((P[:, 2] - z) / a) ** 2 <= 1
        return m

    attr = sample_envelope(rng, int(80 + cw * cw * (H - yf) * 0.5), inside, (cx - cw, yf, cz - cw), (cx + cw, H, cz + cw))
    chain = trunk_chain((cx, yf - 3, cz), (cx, yf + (H - yf) * 0.25, cz), rng, wobble=0.15)
    c = grow_crown(g, rng, chain, attr, radius(yf), sprout_from=0.2, influence=8, kill=2.0,
                   tropism=(0, 0.25, 0), gamma=2.2, trunk_role=R['trunk'])
    for i in c['twigs']:
        p = c['nodes'][i]
        rr = rng.uniform(1.4, 2.1)
        g.blob(p - [0, 0.8, 0], rr, rr * 1.15, rr, R['leaf'] if rng.random() < 0.8 else R['leaf2'], rng,
               rough=0.55, fill=0.7)
    g.prune_floating_leaves()
    return g, dict(height=round(H, 1), radius=round(r0, 2), clear_bole=round(yf, 1), lumps=len(lumps))
