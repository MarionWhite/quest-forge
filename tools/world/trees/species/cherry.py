"""Cherry blossom (sakura), mid-size: a short dark sinuous trunk that splits low into a few
spreading leaders, carrying a wide, flattened, cloud-like canopy of pink blossom with white
highlights on top, deeper pink underneath, a few fresh green leaves, and short drapes of petals.
A quarter are weeping cherries (shidarezakura) with long hanging curtains.

Growth model: space colonisation in a wide flattened multi-lobe dome, pipe-model limbs.
"""
import math
import numpy as np
from voxel import Grid, R, PRIO
from growth import draw_trunk, draw_roots, trunk_chain, grow_crown, sample_envelope, cloud, unit

COUNTS = {'small': 8, 'medium': 12, 'large': 10, 'giant': 3}

SIZE = {
    'small':  dict(h=(5, 7), r=(0.5, 0.6)),
    'medium': dict(h=(7, 10), r=(0.7, 1.0)),
    'large':  dict(h=(10, 13), r=(1.0, 1.4)),
    'giant':  dict(h=(13, 18), r=(1.5, 2.0)),
}


def grow(rng, size):
    s = SIZE[size]
    H = rng.uniform(*s['h']); r0 = rng.uniform(*s['r'])
    weeping = rng.random() < 0.25
    ys = H * rng.uniform(0.22, 0.38)                    # split height
    cr = H * (rng.uniform(0.6, 0.85) if not weeping else rng.uniform(0.45, 0.6))
    cb = ys + 0.5
    ch = (H - cb) * 0.5
    g = Grid(cr + 6, H + 4, 1)
    lean = unit([rng.normal(), 0, rng.normal()]) * rng.uniform(0.05, 0.2) * H
    chain = trunk_chain((0, 0, 0), (lean[0], ys + 1.5, lean[2]), rng, wobble=0.3)
    env = cloud(rng, cb + ch, cr, ch, n=int(rng.integers(6, 10)), ymin=cb + 0.5, lobe=0.5)
    attr = sample_envelope(rng, int(80 + cr * cr * 5), env, (-cr, cb, -cr), (cr, H, cr))
    c = grow_crown(g, rng, chain, attr, r0, sprout_from=0.55, influence=6.5, kill=1.8,
                   tropism=(0, -0.05 if weeping else 0.04, 0), gamma=2.2, jitter=0.25)
    draw_trunk(g, -1, 1.5, lambda y: r0 + r0 * 0.4 * math.exp(-max(y, 0) / 1.2), lambda y: (0, 0), rng,
               lambda y: [(4, 0.12, 0.5)])
    if size in ('large', 'giant'):
        draw_roots(g, rng, int(rng.integers(3, 6)), r0, r0 + 1.5, y_top=1.2, y_end=-0.2, r_root=r0 * 0.4)

    nodes = c['nodes']
    for i in c['tips']:
        p = nodes[i]
        rr = rng.uniform(1.4, 2.1) * (0.85 if size == 'small' else 1.0)
        u = rng.random()
        role = R['leaf4'] if u < 0.06 else R['leaf3'] if u < 0.2 else R['leaf']
        g.blob(p + [0, 0.4, 0], rr, rr * 0.7, rr, role, rng, rough=0.45, fill=0.92)
        if rng.random() < 0.55:                          # white highlight on the upper surface
            g.blob(p + [0, 0.4 + rr * 0.55, 0], rr * 0.8, rr * 0.35, rr * 0.8, R['leaf2'], rng, rough=0.5)

    # drapes of blossom hanging from the canopy underside
    role = g.role
    blossom = (PRIO[role] == 1)
    air_below = np.zeros_like(blossom); air_below[1:] = role[:-1] == 0
    cand = np.argwhere(blossom & air_below)
    rng.shuffle(cand)
    frac, Lmax = (3, 3) if not weeping else (2, int(H * 0.55))
    for y, z, x in cand[:len(cand) // frac]:
        L = int(rng.integers(1, Lmax + 1))
        for k in range(1, L + 1):
            if y - k > g.below + 1 and role[y - k, z, x] == 0:
                role[y - k, z, x] = R['leaf'] if rng.random() < 0.8 else R['leaf2']
            else:
                break
    g.prune_floating_leaves()
    return g, dict(weeping=weeping, height=round(H, 1), radius=round(r0, 2), crown_r=round(cr, 1))
