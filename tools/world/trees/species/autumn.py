"""Autumn broadleaves: maples, oaks, elms and aspens in fall colour.

Forms (picked per seed):
  maple  - central leader, tall oval crown
  oak    - short trunk, broad spreading crown on heavy crooked limbs
  elm    - vase: trunk divides low into ascending limbs, crown widest at the top
  aspen  - slender pale trunk, narrow crown, nearly always yellow
Colour schemes: red, orange, yellow, mixed (clump by clump), turning (green inside and below,
colour on the sunlit top and outside). Real autumn crowns colour from the outside in and the
top down, which is what the role choice per foliage clump imitates.
Growth model: space colonisation in an irregular (multi-lobe) crown envelope, pipe-model limbs.
"""
import math
import numpy as np
from voxel import Grid, R
from growth import draw_trunk, draw_roots, trunk_chain, grow_crown, sample_envelope, cloud, unit

COUNTS = {'small': 10, 'medium': 12, 'large': 10, 'giant': 5}

SIZE = {
    'small':  dict(h=(6, 9), r=(0.5, 0.55)),
    'medium': dict(h=(10, 14), r=(0.6, 0.85)),
    'large':  dict(h=(15, 20), r=(1.0, 1.3)),
    'giant':  dict(h=(21, 28), r=(1.5, 2.0)),
}

SCHEMES = {          # (outer/top roles, inner/lower roles) as (role, weight) lists
    'red':     ([('leaf', 6), ('leaf2', 2)], [('leaf2', 3), ('leaf', 3), ('accent', 1)]),
    'orange':  ([('leaf2', 6), ('leaf', 1), ('leaf3', 2)], [('leaf2', 3), ('leaf3', 2), ('accent', 1)]),
    'yellow':  ([('leaf3', 7), ('leaf2', 1)], [('leaf3', 4), ('leaf4', 1)]),
    'mixed':   ([('leaf', 3), ('leaf2', 3), ('leaf3', 3)], [('leaf2', 2), ('leaf3', 2), ('leaf4', 1)]),
    'turning': ([('leaf', 3), ('leaf2', 3), ('leaf3', 1)], [('leaf4', 5), ('leaf3', 2)]),
}


def pick(rng, lst):
    w = np.array([x[1] for x in lst], float)
    return R[lst[int(rng.choice(len(lst), p=w / w.sum()))][0]]


def grow(rng, size):
    s = SIZE[size]
    H = rng.uniform(*s['h']); r0 = rng.uniform(*s['r'])
    form = str(rng.choice(['maple', 'oak', 'elm', 'aspen'], p=[0.35, 0.3, 0.2, 0.15]))
    if form == 'aspen':
        scheme = 'yellow' if rng.random() < 0.8 else 'orange'
        r0 *= 0.7
    elif form == 'maple':
        scheme = str(rng.choice(['red', 'orange', 'mixed', 'turning'], p=[0.4, 0.25, 0.2, 0.15]))
    else:
        scheme = str(rng.choice(['orange', 'yellow', 'mixed', 'turning', 'red'], p=[0.3, 0.2, 0.25, 0.15, 0.1]))
    shape = {  # crown base, crown radius (x H), crown half-height (x H), leader top, sprout from
        'maple': (0.28, 0.33, 0.36, 0.75, 0.35),
        'oak':   (0.25, 0.5, 0.32, 0.45, 0.45),
        'elm':   (0.3, 0.42, 0.33, 0.4, 0.75),
        'aspen': (0.3, 0.22, 0.36, 0.0, 0.4),
    }[form]
    cb = H * shape[0] * rng.uniform(0.85, 1.15)
    cr = max(2.6, H * shape[1] * rng.uniform(0.85, 1.15))
    ch = max((H - cb) * 0.55, H * shape[2] * 0.8)
    cy = cb + (H - cb) * 0.5
    g = Grid(cr + 6, H + 4, 1)
    lean = unit([rng.normal(), 0, rng.normal()]) * rng.uniform(0, 0.08) * H
    top_y = H * shape[3] if size in ('large', 'giant') and form != 'aspen' else min(max(H * shape[3], cb + 1.5), cb + 1.5)
    top = np.array([lean[0], top_y, lean[2]])
    chain = trunk_chain((0, 0, 0), top, rng, wobble=0.25 if form == 'oak' else 0.12)
    if form == 'elm':      # vase: attractors pushed to the upper rim
        inner = cloud(rng, cy + ch * 0.2, cr, ch * 0.85, n=7, ymin=cb + 1)
        env = lambda P: inner(P) & ((np.hypot(P[:, 0], P[:, 2]) > cr * 0.35) | (P[:, 1] > cy + ch * 0.4))
    else:
        env = cloud(rng, cy, cr, ch, n=int(rng.integers(5, 9)), ymin=cb + 1)
    attr = sample_envelope(rng, int(80 + 2.2 * cr * cr * ch), env, (-cr, cb, -cr), (cr, H, cr))
    c = grow_crown(g, rng, chain, attr, r0, sprout_from=shape[4], influence=6, kill=1.6,
                   tropism=(0, 0.12 if form != 'oak' else 0.0, 0), gamma=2.4 if form != 'oak' else 2.1,
                   trunk_role=R['bark'] if form == 'aspen' else R['trunk'],
                   branch_role=R['bark'] if form == 'aspen' else R['branch'])
    # flared foot
    draw_trunk(g, -1, 2, lambda y: r0 + r0 * 0.4 * math.exp(-max(y, 0) / 1.2), lambda y: (0, 0), rng,
               lambda y: [(5, 0.1, 1.0)], role=R['bark'] if form == 'aspen' else R['trunk'])
    if size in ('large', 'giant') and form != 'aspen':
        draw_roots(g, rng, int(rng.integers(4, 7)), r0, r0 + 2, y_top=1.5, y_end=-0.2, r_root=r0 * 0.4)

    outer, inner = SCHEMES[scheme]
    nodes = c['nodes']
    rr0 = 1.5 if size != 'small' else 1.45
    for i in c['twigs']:
        p = nodes[i]
        t = (p[1] - cb) / max(H - cb, 1)                         # 0 low .. 1 top
        rad = np.hypot(p[0] - lean[0], p[2] - lean[2]) / max(cr, 1)  # 0 centre .. 1 rim
        sun = 0.55 * t + 0.45 * rad + rng.normal(0, 0.15)
        role = pick(rng, outer if sun > 0.5 else inner)
        if scheme == 'mixed' and rng.random() < 0.5:              # whole limbs share a colour
            role = R[['leaf', 'leaf2', 'leaf3'][int(c['parent'][i]) % 3]]
        rr = rr0 * rng.uniform(0.85, 1.25)
        g.blob(p + [0, 0.3, 0], rr, rr * 0.8, rr, role, rng, rough=0.45, fill=0.9)
    g.prune_floating_leaves()
    return g, dict(form=form, scheme=scheme, height=round(H, 1), radius=round(r0, 2), crown_r=round(cr, 1))
