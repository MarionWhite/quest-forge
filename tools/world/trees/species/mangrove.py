"""Red mangrove (Rhizophora): the trunk starts in mid-air, held up by a skirt of arching prop
roots that leave the stem, bow outwards and plunge into the water. Large trees also drop
aerial roots from their limbs. Crown: low, broad, dense dome (space colonisation).

Place on the sea/lagoon bed: y = 0 is where the roots end, so 2-4 blocks of water leaves the
arches standing proud of the surface. The trunk base sits at `root_h`.
"""
import math
import numpy as np
from voxel import Grid, R
from growth import (trunk_chain, grow_crown, sample_envelope, cloud, draw_polyline, unit)

COUNTS = {'small': 6, 'medium': 10, 'large': 10, 'giant': 4}

SIZE = {   # total height, trunk base height (top of the root skirt), trunk radius, crown radius, roots
    'small':  dict(h=(8, 11), rh=(2.5, 3.5), r=(0.5, 0.7), cr=(3.5, 4.5), n=(5, 7)),
    'medium': dict(h=(11, 15), rh=(3.5, 5), r=(0.9, 1.2), cr=(5, 7), n=(8, 11)),
    'large':  dict(h=(15, 20), rh=(4.5, 6.5), r=(1.2, 1.6), cr=(7, 9.5), n=(12, 16)),
    'giant':  dict(h=(20, 26), rh=(6, 8), r=(1.8, 2.3), cr=(10, 13), n=(14, 19)),
}


def bezier(p0, p1, p2, p3, n):
    t = np.linspace(0, 1, n)[:, None]
    return (1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * p1 + 3 * (1 - t) * t ** 2 * p2 + t ** 3 * p3


def arch(g, rng, start, out_dir, reach, r0, role=R['root']):
    """Prop root: leaves `start` outward and slightly up, then arcs down to y = 0."""
    h = start[1]
    end = start + out_dir * reach
    end[1] = rng.uniform(-0.5, 0)
    p1 = start + out_dir * reach * rng.uniform(0.35, 0.55) + np.array([0, h * rng.uniform(0.1, 0.3), 0])
    p2 = end + np.array([0, h * rng.uniform(0.55, 0.8), 0]) - out_dir * reach * 0.05
    pts = bezier(start, p1, p2, end, max(6, int(reach + h) * 2))
    draw_polyline(g, list(pts), r0, 0.5, role)
    return pts


def grow(rng, size):
    s = SIZE[size]
    H = rng.uniform(*s['h']); rh = rng.uniform(*s['rh']); r0 = rng.uniform(*s['r'])
    cr = rng.uniform(*s['cr'])
    g = Grid(cr + 6, H + 4, 1)
    lean = unit([rng.normal(), 0, rng.normal()]) * rng.uniform(0, 0.12)
    cb = rh + (H - rh) * rng.uniform(0.25, 0.4)          # where the crown begins
    base = np.array([0, rh - 0.5, 0.0])
    chain = trunk_chain(base, base + np.array([lean[0] * H, cb - rh + 1, lean[2] * H]), rng, wobble=0.15)
    cy = cb + (H - cb) * 0.5
    env = cloud(rng, cy, cr * 0.95, (H - cb) * 0.55, n=int(4 + cr), ymin=cb + 0.5, flat_top=True)
    attr = sample_envelope(rng, int(100 + cr * cr * 7), env, (-cr, cb, -cr), (cr, H, cr))
    c = grow_crown(g, rng, chain, attr, r0, sprout_from=0.5, influence=6.5, kill=1.7,
                   tropism=(0, 0.05, 0), gamma=2.3)
    nodes, radius = c['nodes'], c['radius']

    # foliage: dense glossy clumps at every twig, flattened, plus a few darker inner clumps
    for i in c['tips']:
        p = nodes[i]
        rr = rng.uniform(1.5, 2.1) * (1.0 if size != 'small' else 0.85)
        g.blob(p + [0, 0.3, 0], rr, rr * 0.65, rr, R['leaf'], rng, rough=0.45, fill=0.9)
    for i in range(c['chain'], len(nodes)):
        if c['depth'][i] == 3 and rng.random() < 0.3:
            g.blob(nodes[i], 1.6, 1.1, 1.6, R['leaf2'], rng, rough=0.3)

    # prop roots: a skirt of arches from the lower trunk
    n = int(rng.integers(*s['n']))
    a0 = rng.uniform(0, 2 * math.pi)
    for k in range(n):
        a = a0 + 2 * math.pi * k / n + rng.uniform(-0.25, 0.25)
        d = np.array([math.cos(a), 0, math.sin(a)])
        y = rng.uniform(rh * 0.55, rh + (cb - rh) * 0.6)
        start = np.array([0, y, 0]) + d * r0 * 0.6
        reach = r0 + y * rng.uniform(0.6, 1.1) + rng.uniform(0.5, 2)
        rr = min(0.95, r0 * rng.uniform(0.4, 0.55)) if size in ('large', 'giant') else 0.5
        pts = arch(g, rng, start, d, reach, rr)
        # secondary arch forking off the outer half
        if size != 'small' and rng.random() < 0.45:
            j = int(len(pts) * rng.uniform(0.3, 0.5))
            d2 = unit(d + np.array([math.cos(a + 1.6), 0, math.sin(a + 1.6)]) * rng.uniform(-0.8, 0.8))
            arch(g, rng, pts[j].copy(), d2, pts[j][1] * rng.uniform(0.6, 1.0) + 1, 0.5)

    # aerial roots: from big limbs straight-ish down into the water
    if size in ('large', 'giant'):
        cand = [i for i in range(c['chain'], len(nodes)) if radius[i] > 0.35 * r0 and nodes[i][1] > cb
                and np.hypot(nodes[i][0], nodes[i][2]) > cr * 0.35]
        rng.shuffle(cand)
        for i in cand[:int(rng.integers(3, 8 if size == 'large' else 14))]:
            p = nodes[i].copy()
            d = unit([p[0], 0, p[2]])
            arch(g, rng, p, d, rng.uniform(0.5, 2.0), 0.5)

    g.prune_floating_leaves()
    return g, dict(height=round(H, 1), root_height=round(rh, 1), trunk_r=round(r0, 2), crown_r=round(cr, 1),
                   prop_roots=n)
