"""Coast redwood (Sequoia sempervirens): huge straight fluted trunk with flared buttresses,
long clear bole, and a high, narrow crown of short drooping limbs carrying flat foliage sprays.
Old giants get reiterated leaders (candelabra tops), broken snag tops, fire-scar hollows
("goosepens") and fuzzy epicormic sprouts on the bole.

Growth model: recursive branching. Primary limbs whorl up the crown on a golden-angle spiral;
each limb sprouts sprays, each spray ends in a flattened foliage pad.
"""
import math
import numpy as np
from voxel import Grid, R
from growth import draw_trunk, draw_roots, limb, draw_polyline, direction, unit

COUNTS = {'small': 8, 'medium': 10, 'large': 10, 'giant': 8}

SIZE = {          # height, base radius, clear-bole fraction, crown radius as fraction of height
    'small':  dict(h=(20, 30), r=(0.9, 1.3), bole=(0.18, 0.3), cw=(0.17, 0.22)),
    'medium': dict(h=(34, 46), r=(1.6, 2.1), bole=(0.32, 0.45), cw=(0.13, 0.16)),
    'large':  dict(h=(52, 66), r=(2.5, 3.2), bole=(0.45, 0.55), cw=(0.11, 0.135)),
    'giant':  dict(h=(72, 94), r=(3.6, 4.7), bole=(0.5, 0.6), cw=(0.095, 0.12)),
}


def grow(rng, size):
    s = SIZE[size]
    H = int(rng.integers(*s['h']))
    r0 = rng.uniform(*s['r'])
    yc = H * rng.uniform(*s['bole'])            # crown base
    cw = H * rng.uniform(*s['cw'])              # crown half-width at its widest
    flare = rng.uniform(0.35, 0.6)
    hf = max(2.0, H * 0.05)
    lean_dir = rng.uniform(0, 2 * math.pi)
    lean = rng.uniform(0, 0.025) * H
    big = size in ('large', 'giant')
    snag = size == 'giant' and rng.random() < 0.35
    reiter = int(rng.integers(1, 4)) if size == 'giant' and rng.random() < 0.7 else (1 if size == 'large' and rng.random() < 0.3 else 0)
    below = 2 if big else 1
    g = Grid(cw + r0 * 3 + 6, H + 6, below)
    wob = [rng.uniform(0, 2 * math.pi) for _ in range(2)]

    def centre(y):
        f = max(y, 0) / H
        w = 0.35 * (r0 / 2) * math.sin(f * 7 + wob[0])
        return (math.cos(lean_dir) * lean * f ** 1.5 + w * math.cos(wob[1]),
                math.sin(lean_dir) * lean * f ** 1.5 + w * math.sin(wob[1]))

    r_top = 0.45

    def radius(y):
        f = min(max(y, 0) / H, 1)
        base = r_top + (r0 - r_top) * (1 - f) ** 0.8
        return base + r0 * flare * math.exp(-max(y, 0) / hf)

    nb = int(rng.integers(5, 9))
    ph = rng.uniform(0, 2 * math.pi)

    def lobes(y):
        a = 0.22 * math.exp(-max(y, 0) / (hf * 1.6))
        return [(nb, a, ph), (3, 0.05 + a * 0.3, ph * 1.7), (2, 0.04, ph * 0.3)]

    trunk_top = H - (rng.uniform(3, 6) if snag else 0)
    draw_trunk(g, -below, trunk_top, radius, centre, rng, lobes)
    if big or size == 'medium':
        draw_roots(g, rng, nb, radius(1), r0 * 1.2 + 1.5, y_top=hf * 1.1, y_end=-0.3, sink=below - 1,
                   phase=ph, r_root=r0 * 0.45)

    # fire scar / goosepen: a hollow at the base opening on one side
    if size == 'giant' and rng.random() < 0.45 or size == 'large' and rng.random() < 0.2:
        a = rng.uniform(0, 2 * math.pi)
        hs = rng.uniform(4, 9) * r0 / 4
        cx, cz = centre(0)

        def scar(X, Y, Z):
            dx, dz = X - cx, Z - cz
            ang = np.abs((np.arctan2(dz, dx) - a + np.pi) % (2 * np.pi) - np.pi)
            rr = np.sqrt(dx * dx + dz * dz)
            inner = rr < (r0 * 0.75)
            mouth = (ang < 0.45) & (rr < r0 * 2.5)
            return (Y >= 0) & (Y < hs * (1 - rr / (r0 * 3))) & (inner | mouth)
        g.carve(scar, (cx - r0 * 3, 0, cz - r0 * 3), (cx + r0 * 3, hs, cz + r0 * 3))

    # dead stubs and epicormic sprouts on the clear bole
    for _ in range(int(rng.integers(2, 6)) + (4 if big else 0) if yc > H * 0.2 + 2 else 0):
        y = rng.uniform(H * 0.2, yc)
        a = rng.uniform(0, 2 * math.pi)
        cx, cz = centre(y)
        p = np.array([cx, y, cz]) + direction(a, 0) * radius(y)
        L = rng.uniform(1, 2.5 + r0 * 0.4)
        draw_polyline(g, limb(p, direction(a, rng.uniform(-0.4, 0.1)), L, rng, wobble=0.1), 0.5, 0.5, R['branch'])
    for _ in range(int(rng.integers(0, 4 + int(r0 * 3))) if yc > hf * 1.5 + 2 else 0):
        y = rng.uniform(hf * 1.5, yc)
        a = rng.uniform(0, 2 * math.pi)
        cx, cz = centre(y)
        p = np.array([cx, y, cz]) + direction(a, 0) * (radius(y) + 0.8)
        g.blob(p, 1.2, 1.4, 1.2, R['accent'], rng, rough=0.5)

    # crown: golden-angle whorl of short limbs, narrow envelope, slight droop
    def envelope(t):              # 0 at crown base .. 1 at tip
        rise = min(1.0, 0.45 + t / 0.2)
        return rise * (1 - t) ** 0.85

    golden = math.pi * (3 - math.sqrt(5))
    az = rng.uniform(0, 2 * math.pi)
    y = yc
    pad_r = 1.9 + 0.4 * r0
    limb_r = max(0.5, 0.25 * r0)
    tops = []
    while y < trunk_top - 1.5:
        t = (y - yc) / max(trunk_top - yc, 1)
        L = max(1.5, cw * envelope(t) * rng.uniform(0.7, 1.15))
        az += golden + rng.uniform(-0.3, 0.3)
        el = -0.35 + 0.75 * t + rng.uniform(-0.15, 0.15)
        cx, cz = centre(y)
        p = np.array([cx, y, cz]) + direction(az, 0) * radius(y) * 0.9
        pts = limb(p, direction(az, el), L, rng, gravity=-0.05, up_bend=0.12, wobble=0.08)
        draw_polyline(g, pts, limb_r * (1.2 - t), 0.5, R['branch'])
        # sprays: flat pads along the outer two thirds of the limb, drooping below it
        for k in range(max(1, len(pts) // 4), len(pts), 1 if big else 2):
            q = pts[k] + np.array([rng.uniform(-.6, .6), -0.6, rng.uniform(-.6, .6)])
            f = k / len(pts)
            rr = pad_r * (0.75 + 0.45 * f) * (1 - 0.4 * t)
            g.blob(q, rr, rr * 0.5 + 0.4, rr, R['leaf'], rng, rough=0.45, fill=0.9)
        tip = pts[-1]
        g.blob(tip + [0, -0.3, 0], pad_r * (1 - 0.3 * t), pad_r * 0.55, pad_r * (1 - 0.3 * t), R['leaf'], rng, rough=0.4)
        y += rng.choice([1, 1, 2]) if big else rng.choice([1, 2])
        tops.append(tip)

    # spire top
    cx, cz = centre(trunk_top)
    if not snag and size == 'giant' and rng.random() < 0.5:      # old rounded, clumpy top
        for k in range(6):
            q = np.array([cx, trunk_top - 1, cz]) + rng.normal(scale=[1.6, 1.0, 1.6])
            g.blob(q, pad_r + 0.6, pad_r * 0.7, pad_r + 0.6, R['leaf2'], rng, rough=0.4)
    elif not snag:
        for k in range(4):
            yy = trunk_top - 3 + k * 1.2
            rr = max(0.8, (pad_r + 0.6) * (1 - k / 4))
            g.blob((cx, yy, cz), rr, 1.2, rr, R['leaf2'], rng, rough=0.35)
        g.put(cx, trunk_top + 2, cz, R['leaf2'])
    else:
        g.capsule((cx, trunk_top - 2, cz), (cx + rng.uniform(-1, 1), H, cz + rng.uniform(-1, 1)), 0.5, 0.5, R['trunk'])

    # reiterated leaders: limbs that turn upward into secondary spires (candelabra)
    for k in range(reiter):
        y0 = rng.uniform(0.7, 0.86) * H
        a = rng.uniform(0, 2 * math.pi)
        cx, cz = centre(y0)
        p = np.array([cx, y0, cz]) + direction(a, 0) * radius(y0)
        out = rng.uniform(2, 3 + r0 * 0.6)
        knee = p + direction(a, 0.35) * out
        top_h = rng.uniform(8, 16) * (r0 / 4)
        top = knee + np.array([rng.uniform(-1, 1), top_h, rng.uniform(-1, 1)])
        rr = max(0.75, r0 * 0.3)
        g.capsule(p, knee, rr, rr * 0.9, R['branch'])
        g.capsule(knee, top, rr * 0.9, 0.5, R['trunk'])
        for j in range(int(top_h)):
            f = j / max(top_h, 1)
            q = knee + (top - knee) * f
            if j % 2 == 0:
                aa = rng.uniform(0, 2 * math.pi)
                L = (1 - f) * cw * 0.35 + 1
                pts = limb(q, direction(aa, -0.2), L, rng, up_bend=0.1, wobble=0.1)
                draw_polyline(g, pts, 0.5, 0.5, R['branch'])
                g.blob(pts[-1], pad_r * (1 - 0.4 * f), pad_r * 0.5, pad_r * (1 - 0.4 * f), R['leaf'], rng, rough=0.4)
        g.blob(top, 1.3, 1.8, 1.3, R['leaf2'], rng, rough=0.3)

    g.prune_floating_leaves()
    return g, dict(height=H, radius=round(r0, 2), crown_base=int(yc), crown_halfwidth=round(cw, 1),
                   snag=snag, reiterations=reiter)
