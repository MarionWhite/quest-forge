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
from growth import (draw_trunk, draw_roots, trunk_chain, grow_crown, sample_envelope, cloud, unit,
                    small_frame)

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
    if size == 'small':
        return grow_small(rng, H, form, scheme)
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


# small trees -----------------------------------------------------------------------------
# (crown base, leader top, crown radius as fractions of H; limb count; limb elevation in degrees)
SMALL = {
    'maple': dict(cb=0.3, top=0.86, cr=0.46, n=(4, 6), elev=(25, 45), fork=0.5, clump=(1.7, 2.1, 1.4)),
    'oak':   dict(cb=0.34, top=0.6, cr=0.58, n=(3, 5), elev=(10, 30), fork=0.7, clump=(1.8, 2.3, 1.25)),
    'elm':   dict(cb=0.36, top=0.4, cr=0.55, n=(3, 4), elev=(42, 58), fork=0.8, clump=(1.7, 2.1, 1.3)),
    'aspen': dict(cb=0.4, top=0.95, cr=0.27, n=(4, 6), elev=(25, 45), fork=0.2, clump=(1.3, 1.5, 1.5)),
}


def grow_small(rng, H, form, scheme):
    """Small trees get an explicit frame: a 1-block trunk, single-log limbs and a few separate
    foliage clumps on the limb ends, so trunk, branches and crown shape all read at 6-9 blocks."""
    p = SMALL[form]
    H = H + (1.5 if form == 'aspen' else 0)
    cb = H * p['cb'] * rng.uniform(0.9, 1.1)
    top = max(cb + 1, H * p['top'])
    cr = max(2.2, H * p['cr'] * rng.uniform(0.9, 1.15))
    g = Grid(cr + 5, H + 4, 1)
    wood = R['bark'] if form == 'aspen' else R['trunk']
    lean = tuple(unit([rng.normal(), 0, rng.normal()])[[0, 2]] * rng.uniform(0, 0.6))
    if form == 'elm':           # vase: limbs fork from one height and climb, the rim carries the crown
        lt = cb + 0.5
    elif form == 'oak':
        lt = top
    else:
        lt = top - 1
    sites = small_frame(g, rng, cb, top, cr, int(rng.integers(*p['n'], endpoint=True)), p['elev'],
                        limb_top=lt, fork_p=p['fork'], crook=0.6 if form == 'oak' else 0.25, lean=lean,
                        up_bend=0.08 if form == 'elm' else 0.03, gravity=-0.02 if form == 'oak' else 0.0,
                        trunk_role=wood, branch_role=wood, len_f=(0.8, 1.1) if form != 'elm' else (0.9, 1.15))
    # a root stub or two so the foot does not look like a post stuck in the ground
    for k in range(int(rng.integers(1, 3))):
        a = rng.uniform(0, 2 * math.pi)
        g.put(round(math.cos(a)), 0, round(math.sin(a)), wood, 1 if abs(math.cos(a)) > 0.7 else 2)
    outer, inner = SCHEMES[scheme]
    rx0, rx1, ry = p['clump']
    for q, kind, f in sites:
        q = np.asarray(q, float)
        if kind == 'top':
            if form == 'elm':
                continue            # keep the vase open in the middle
            # the crown's upper dome: wider than a limb clump, sitting just above the leader
            rx = cr * (0.62 if form != 'aspen' else 0.8)
            g.blob(q + [0, 0.8, 0], rx, max(1.6, rx * 0.7), rx, pick(rng, outer), rng, rough=0.25, fill=0.82)
            continue
        t = (q[1] - cb) / max(H - cb, 1)
        rad = np.hypot(q[0], q[2]) / max(cr, 1)
        sun = 0.55 * t + 0.45 * rad + rng.normal(0, 0.15)
        role = pick(rng, outer if sun > 0.45 else inner)
        rx = rng.uniform(rx0, rx1) * (0.85 if kind == 'fork' else 1.0)
        g.blob(q + [0, 0.3, 0], rx, rx * ry / 1.6 + 0.2, rx, role, rng, rough=0.2, fill=0.9)
        if rng.random() < 0.6:     # a second, offset lobe so clumps are not spheres
            o = q + [rng.uniform(-1, 1), rng.uniform(0.2, 1.0), rng.uniform(-1, 1)]
            g.blob(o, rx * 0.75, rx * 0.6, rx * 0.75, pick(rng, outer), rng, rough=0.2, fill=0.9)
    g.prune_floating_leaves()
    return g, dict(form=form, scheme=scheme, height=round(H, 1), crown_r=round(cr, 1), small=True)
