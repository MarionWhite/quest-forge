"""Ice-crystal trees for the frozen fairy forest: twisting packed-ice trunks with stained-glass
canopies, crystal shards, icicles, and a few glowstone hearts hidden in the canopy so the grove
glows at night through the coloured glass.

Styles (picked per seed):
  frost    - space-colonised round crown of frosted glass clumps tipped with crystal points
  shard    - recursive upswept limbs that end in fans of tapering crystal shards
  weeping  - a frozen willow: arching limbs trailing curtains of glass that end in icicles
Colour schemes: frost (white / pale blue), glacier (cyan / blue), aurora (cyan below fading
to magenta and purple at the top).
"""
import math
import numpy as np
from voxel import Grid, R, PRIO
from growth import (draw_trunk, draw_roots, limb, draw_polyline, direction, unit, trunk_chain,
                    grow_crown, sample_envelope, cloud, hang, small_frame)

COUNTS = {'small': 8, 'medium': 10, 'large': 8, 'giant': 5}

SIZE = {
    'small':  dict(h=(7, 10), r=(0.6, 0.9)),
    'medium': dict(h=(11, 16), r=(0.8, 1.2)),
    'large':  dict(h=(17, 24), r=(1.2, 1.7)),
    'giant':  dict(h=(26, 36), r=(1.8, 2.5)),
}


def scheme_role(scheme, t, rng):
    """Glass role for relative height t (0 bottom of crown .. 1 top)."""
    if scheme == 'frost':
        return R['leaf'] if rng.random() < 0.65 else R['leaf4']
    if scheme == 'glacier':
        return R['leaf2'] if rng.random() < 0.6 else R['leaf']
    # aurora: cyan -> light blue -> magenta/purple
    u = t + rng.normal(0, 0.15)
    return R['leaf2'] if u < 0.35 else R['leaf'] if u < 0.65 else R['leaf3']


def shard(g, p, d, L, r, role):
    """A pointed crystal: tapered prism from radius r to a 1-block point."""
    q = np.asarray(p, float) + unit(d) * L
    g.capsule(p, q, r, 0.3, role)
    g.put(*q, role)


def grow(rng, size):
    s = SIZE[size]
    H = rng.uniform(*s['h']); r0 = rng.uniform(*s['r'])
    style = rng.choice(['frost', 'shard', 'weeping'], p=[0.4, 0.35, 0.25])
    scheme = rng.choice(['frost', 'glacier', 'aurora'], p=[0.35, 0.3, 0.35])
    if size == 'small':
        return grow_small(rng, H, r0, str(style), str(scheme))
    cr = H * (0.5 if style != 'weeping' else 0.55)
    g = Grid(cr + 6, H + 6, 1)
    twist_a = rng.uniform(0.3, 0.8) * (r0 + 0.5) * 0.6
    twist_w = rng.uniform(0.15, 0.35)
    ph = rng.uniform(0, 6.3)

    def centre(y):
        f = max(y, 0) / H
        return twist_a * f * math.sin(twist_w * y + ph), twist_a * f * math.cos(twist_w * y + ph)

    ht = H * (rng.uniform(0.3, 0.42) if style != 'shard' else rng.uniform(0.28, 0.4))

    def radius(y):
        f = max(y, 0) / H
        return r0 * (1 - 0.5 * f) + r0 * 0.25 * math.exp(-max(y, 0) / 2.5)

    nl = int(rng.integers(4, 7))

    def lobes(y):          # spiral ridges twisting up the trunk
        return [(nl, 0.12, ph + y * 0.35)]

    draw_trunk(g, -1, ht, radius, centre, rng, lobes)
    if size in ('large', 'giant'):
        draw_roots(g, rng, int(rng.integers(4, 7)), radius(0), r0 + 1.5, y_top=1.5, y_end=-0.2,
                   r_root=max(0.5, r0 * 0.4))
    cx, cz = centre(ht)
    top = np.array([cx, ht, cz])

    if style == 'frost':
        chain = trunk_chain(top - [0, 2, 0], top + [0, (H - ht) * 0.35, 0], rng, wobble=0.1)
        cy = ht + (H - ht) * 0.5
        attr = sample_envelope(rng, int(80 + cr * cr * 4), cloud(rng, cy, cr * 0.9, (H - ht) * 0.55, n=6, ymin=ht),
                               (-cr, ht, -cr), (cr, H, cr))
        c = grow_crown(g, rng, chain, attr, radius(ht), sprout_from=0.0, influence=6, kill=2.0,
                       tropism=(0, 0.15, 0), gamma=2.3, trunk_role=R['branch'])
        for i in c['tips']:
            p = c['nodes'][i]
            t = (p[1] - ht) / (H - ht)
            rr = rng.uniform(1.4, 2.3)
            g.blob(p, rr, rr * 0.8, rr, scheme_role(scheme, t, rng), rng, rough=0.5, fill=0.8)
            if rng.random() < 0.45:
                d = unit(p - [0, ht, 0] + rng.normal(scale=2, size=3))
                shard(g, p + d * rr * 0.6, d, rng.uniform(1.5, 3.5), 0.75, scheme_role(scheme, t, rng))
    elif style == 'shard':
        tips = []

        def up_branch(p, d, L, r, depth):
            pts = limb(p, d, L, rng, step=1.0, wobble=0.12, up_bend=0.12)
            draw_polyline(g, pts, r, max(0.5, r * 0.6), R['branch'])
            # small crystal buds along the limb
            for q in pts[2::3]:
                if rng.random() < 0.5:
                    shard(g, q, unit(rng.normal(size=3) + [0, 0.8, 0]), rng.uniform(1, 2.5), 0.5,
                          scheme_role(scheme, (q[1] - ht) / (H - ht), rng))
            if depth == 0:
                tips.append((pts[-1], unit(pts[-1] - pts[-2])))
                return
            for _ in range(int(rng.integers(2, 4))):
                up_branch(pts[-1], unit(unit(pts[-1] - pts[-2]) + rng.normal(scale=0.6, size=3) + [0, 0.4, 0]),
                          L * rng.uniform(0.55, 0.75), max(0.5, r * 0.65), depth - 1)
        n = int(rng.integers(3, 6))
        for k in range(n):
            a = ph + k * 2 * math.pi / n + rng.uniform(-0.3, 0.3)
            up_branch(top, direction(a, rng.uniform(0.7, 1.1)), (H - ht) * 0.45, max(0.6, r0 * 0.55),
                      2 if size in ('large', 'giant') else 1)
        up_branch(top, [0, 1, 0], (H - ht) * 0.5, max(0.6, r0 * 0.6), 1)
        for p, d in tips:
            t = (p[1] - ht) / (H - ht)
            for _ in range(int(rng.integers(3, 6))):
                dd = unit(d + rng.normal(scale=0.45, size=3) + [0, 0.5, 0])
                shard(g, p, dd, rng.uniform(2, 3.5 + r0 * 1.5), rng.uniform(0.6, 1.0 + r0 * 0.2),
                      scheme_role(scheme, t, rng))
            g.blob(p, 1.0, 1.0, 1.0, R['accent'], rng, rough=0.2)      # clear-ice heart of the cluster
    else:  # weeping
        n = int(rng.integers(5, 9))
        for k in range(n):
            a = ph + k * 2 * math.pi / n + rng.uniform(-0.3, 0.3)
            y0 = ht + rng.uniform(-1, (H - ht) * 0.5)
            cx0, cz0 = centre(y0)
            pts = limb((cx0, y0, cz0), direction(a, rng.uniform(0.6, 1.0)), cr * rng.uniform(0.7, 1.0), rng,
                       gravity=-0.12, wobble=0.08)
            draw_polyline(g, pts, max(0.5, r0 * 0.45), 0.5, R['branch'])
            for j, q in enumerate(pts[1:]):
                t = (q[1] - ht) / (H - ht)
                g.blob(q + [0, 0.5, 0], 1.3, 0.9, 1.3, scheme_role(scheme, t, rng), rng, rough=0.5, fill=0.85)
                for _ in range(2):
                    if rng.random() < 0.7:
                        o = q + [rng.uniform(-1.4, 1.4), 0, rng.uniform(-1.4, 1.4)]
                        L = int(rng.uniform(0.3, 0.75) * max(q[1], 2))
                        role = scheme_role(scheme, t, rng)
                        hang(g, o, L, role)
                        g.put(o[0], o[1] - L, o[2], R['accent'])
        g.blob(top + [0, (H - ht) * 0.55, 0], 2.2, 1.8, 2.2, scheme_role(scheme, 1, rng), rng, rough=0.4)

    decorate(g, rng, size)
    g.prune_floating_leaves()
    return g, dict(style=str(style), scheme=str(scheme), height=round(H, 1), trunk_r=round(r0, 2))


def grow_small(rng, H, r0, style, scheme):
    """Small ice trees on an explicit frame: a twisting 1-block packed-ice trunk (2x2 at the foot
    when it is thick), single-block limbs, and separate glass clumps or crystal fans on the limb
    ends, so they read as trees at 7-10 blocks instead of a glass blob."""
    ph = rng.uniform(0, 6.3)
    tw = rng.uniform(0.5, 0.9)

    def centre(y):            # a gentle corkscrew, one block of travel over the height
        f = max(y, 0) / H
        return tw * f * math.sin(0.5 * y + ph), tw * f * math.cos(0.5 * y + ph)

    if style == 'frost':
        cb, top, cr, n, elev, clump = H * 0.36, H * 0.8, H * 0.52, (4, 5), (22, 42), (1.6, 2.0)
    elif style == 'shard':
        cb, top, cr, n, elev, clump = H * 0.32, H * 0.8, H * 0.5, (4, 5), (32, 50), None
    else:   # weeping
        cb, top, cr, n, elev, clump = H * 0.5, H * 0.92, H * 0.48, (5, 6), (10, 28), (1.0, 1.2)
    g = Grid(cr + 6, H + 5, 1)
    sites = small_frame(g, rng, cb, top, cr, int(rng.integers(*n, endpoint=True)), elev,
                        limb_top=top - 1, fork_p=0.5 if style != 'weeping' else 0.3, centre=centre,
                        gravity=-0.1 if style == 'weeping' else 0.0, up_bend=0.1 if style == 'shard' else 0.02,
                        trunk_role=R['trunk'], branch_role=R['branch'], wobble=0.08)
    if r0 > 0.75:             # thick foot: 2x2 for the lowest layers, then the 1-block trunk
        sx, sz = rng.choice([-1, 1]), rng.choice([-1, 1])
        for y in range(-1, 2):
            for dx, dz in ((sx, 0), (0, sz), (sx, sz)):
                if y < 1 or (dx and dz) == 0:
                    g.put(dx, y, dz, R['trunk'])
    g.put(rng.choice([-1, 1]), 0, 0, R['root'], 1)          # a snowy root stub
    for q, kind, f in sites:
        q = np.asarray(q, float)
        t = min(1.0, max(0.0, (q[1] - cb) / max(H - cb, 1)))
        d = unit(q - [0, cb, 0])
        if style == 'shard':
            # a fan of thin crystal shards with a clear-ice heart at the joint
            g.blob(q, 1.0, 1.0, 1.0, R['accent'], rng, rough=0.1)
            k = int(rng.integers(3, 5))
            a0 = math.atan2(d[2], d[0])
            for j in range(k):     # spread round the limb direction, all pointing up and out
                dd = unit(direction(a0 + (j - (k - 1) / 2) * 0.7 + rng.normal(0, 0.15), rng.uniform(0.6, 1.2)))
                g.capsule(q, q + dd * rng.uniform(2.2, 3.6), 0.8, 0.3, scheme_role(scheme, t, rng))
            continue
        rx = rng.uniform(*clump) * (1.25 if kind == 'top' else 0.85 if kind == 'fork' else 1.0)
        if style == 'weeping':
            g.blob(q + [0, 0.4, 0], rx, 0.9, rx, scheme_role(scheme, t, rng), rng, rough=0.2, fill=0.9)
            for _ in range(int(rng.integers(2, 4))):         # glass curtain ending in an icicle
                o = q + [rng.uniform(-1.2, 1.2), 0, rng.uniform(-1.2, 1.2)]
                L = int(rng.uniform(0.35, 0.6) * max(q[1], 2))
                hang(g, o, L, scheme_role(scheme, t, rng))
                g.put(o[0], o[1] - L, o[2], R['accent'])
            continue
        g.blob(q + [0, 0.3, 0], rx, rx * 0.8, rx, scheme_role(scheme, t, rng), rng, rough=0.2, fill=0.88)
        if rng.random() < 0.6:        # a crystal point poking out of the clump
            g.line(q, q + unit(d + [0, 0.5, 0]) * (rx + rng.uniform(1.0, 2.0)), scheme_role(scheme, t, rng))
    decorate(g, rng, 'small')
    g.prune_floating_leaves()
    return g, dict(style=style, scheme=scheme, height=round(H, 1), trunk_r=round(r0, 2), small=True)


def decorate(g, rng, size):
    """Icicles under glass and branches; glowstone hearts deep inside the canopy."""
    role = g.role
    glassy = (PRIO[role] == 1)
    woody = (role == R['branch'])
    air_below = np.zeros_like(glassy); air_below[1:] = role[:-1] == 0
    cand = np.argwhere((glassy | woody) & air_below)
    rng.shuffle(cand)
    for y, z, x in cand[:max(3, len(cand) // 12)]:
        L = int(rng.integers(1, 4))
        for k in range(1, L + 1):
            if y - k >= 0 and role[y - k, z, x] == 0:
                role[y - k, z, x] = R['accent']
            else:
                break
    # glow: glass voxels with all 6 neighbours solid
    solid = role != 0
    enc = np.zeros_like(solid)
    enc[1:-1, 1:-1, 1:-1] = (solid[:-2, 1:-1, 1:-1] & solid[2:, 1:-1, 1:-1] & solid[1:-1, :-2, 1:-1] &
                             solid[1:-1, 2:, 1:-1] & solid[1:-1, 1:-1, :-2] & solid[1:-1, 1:-1, 2:])
    c = np.argwhere(enc & (PRIO[role] == 1))
    n = {'small': 1, 'medium': 2, 'large': 4, 'giant': 7}[size]
    if len(c):
        for y, z, x in c[rng.choice(len(c), min(n, len(c)), replace=False)]:
            role[y, z, x] = R['glow']
