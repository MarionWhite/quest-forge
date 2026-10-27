#!/usr/bin/env python3
"""QF Textures' own drawn art: foliage, bark, grass, crops and bookshelf books, made by code.

Nothing here reads another pack's pixels. Stay True (ARR) is the stated direction for the plant
art (dense, clustered leaves with light and shadow per leaf; golden, bushy wheat with distinct
ears), and Soartex (ARR) for the bookshelves (tall, varied, leather-bound books): we take the
idea only, and every pixel below comes from these generators, seeded so a build is reproducible.

Design rules (docs/design/textures/direction.md, "QF Textures v1"):
  * Tinted textures (leaves, grass, tall grass, fern) stay GREY: the biome colour still comes from
    the game, so swamp and birch forests keep their own greens.
  * Values sit near vanilla's (the shader is tuned on them): leaves mean ~135, grass top ~147.
  * Pixel art, not noise: a few flat value steps per shape, a light from the upper left, dark
    gaps between shapes. Every texture tiles (all drawing wraps).
  * `preview()` writes a tiled, tinted, upscaled sheet so each generator can be judged by eye.
"""
import math

import numpy as np

LIGHT = np.array([-0.55, -0.83])          # image space: from the upper left (x right, y down)
FOLIAGE = np.array([0x48, 0xB5, 0x18]) / 255.0   # vanilla's default foliage tint, for previews only
GRASS_TINT = np.array([0x79, 0xC0, 0x5A]) / 255.0


def rng(seed):
    return np.random.default_rng(seed)


def grey(v, a=None):
    """(h, w) value 0..1 (+ alpha mask) -> RGBA uint8, grey."""
    g = np.clip(v * 255.0 + 0.5, 0, 255).astype(np.uint8)
    al = np.full(v.shape, 255, np.uint8) if a is None else np.where(a, 255, 0).astype(np.uint8)
    return np.dstack([g, g, g, al])


def rgba(rgb, a=None):
    c = np.clip(rgb * 255.0 + 0.5, 0, 255).astype(np.uint8)
    al = np.full(rgb.shape[:2], 255, np.uint8) if a is None else np.where(a, 255, 0).astype(np.uint8)
    return np.dstack([c, al])


def quant(v, levels):
    """Snap values to a short ramp: pixel art has few value steps."""
    levels = np.asarray(levels, np.float32)
    return levels[np.abs(v[..., None] - levels).argmin(-1)]


def poisson(n, size, rmin, r, tries=4000):
    """Up to n points in a wrapped square, at least rmin apart (wrapped distance)."""
    pts = []
    for _ in range(tries):
        p = r.uniform(0, size, 2)
        ok = True
        for q in pts:
            d = np.abs(p - q)
            d = np.minimum(d, size - d)
            if d @ d < rmin * rmin:
                ok = False
                break
        if ok:
            pts.append(p)
            if len(pts) >= n:
                break
    return np.array(pts)


def wrapped_offsets(size, px, py):
    """Each pixel's offset from (px, py), wrapped to the nearest copy: (dy, dx) arrays."""
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32) + 0.5
    dx = (xx - px + size / 2) % size - size / 2
    dy = (yy - py + size / 2) % size - size / 2
    return dy, dx


# --- leaves -------------------------------------------------------------------------------------
LEAF_KINDS = {
    #            leaves, length, width, holes, ramp (dark .. light), seed
    "oak":      dict(n=46, length=(5.0, 7.5), width=(2.4, 3.4), holes=0.30, base=0.30, seed=11),
    "big_oak":  dict(n=54, length=(4.5, 6.5), width=(2.2, 3.0), holes=0.26, base=0.27, seed=12),
    "birch":    dict(n=40, length=(4.0, 6.0), width=(2.6, 3.6), holes=0.34, base=0.34, seed=13),
    "jungle":   dict(n=30, length=(7.0, 10.0), width=(3.0, 4.4), holes=0.24, base=0.28, seed=14),
    "acacia":   dict(n=60, length=(3.0, 4.5), width=(1.8, 2.4), holes=0.36, base=0.30, seed=15),
}
LEAF_RAMP = [0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80]


def leaf_shape(dy, dx, ang, length, width):
    """A pointed leaf (lens) along `ang`: inside mask, along-axis t (-1 tip .. 1 tip), across s."""
    ca, sa = math.cos(ang), math.sin(ang)
    u = dx * ca + dy * sa            # along
    v = -dx * sa + dy * ca           # across
    t = u / (length / 2)
    half = (width / 2) * np.clip(1 - t * t, 0, 1) ** 0.75
    inside = (np.abs(t) <= 1) & (np.abs(v) <= half + 0.15)
    return inside, t, v / np.maximum(half, 0.5)


def clump_field(size, centres, radii):
    """Metaball field of wrapped clumps, and per pixel the nearest clump's normalised offset."""
    f = np.zeros((size, size), np.float32)
    best = np.full((size, size), 1e9, np.float32)
    off = np.zeros((size, size, 2), np.float32)
    for (px, py), rad in zip(centres, radii):
        dy, dx = wrapped_offsets(size, px, py)
        d2 = (dx * dx + dy * dy) / (rad * rad)
        f += np.exp(-d2 * 1.6)
        closer = d2 < best
        best = np.where(closer, d2, best)
        off[..., 0] = np.where(closer, dx / rad, off[..., 0])
        off[..., 1] = np.where(closer, dy / rad, off[..., 1])
    return f, off, best


def leaves(kind="oak", size=32):
    """Grey, cut-out leaf canopy built like a painter would: a few round CLUMPS of leaves, each lit
    from the upper left (bright crown, dark underside), single leaves drawn inside a clump with dark
    seams between them, deep shadow between clumps, and see-through gaps only where clumps leave
    room (fancy graphics). The clump shading gives the block depth; the leaves give it texture."""
    k = LEAF_KINDS[kind]
    r = rng(k["seed"])
    nclump = {"jungle": 6, "acacia": 10}.get(kind, 8)
    cen = poisson(nclump, size, size * 0.26, r)
    rad = r.uniform(5.0, 6.8, len(cen)) * (size / 32)
    f, off, best = clump_field(size, cen, rad)
    core = f > 0.60
    # macro light in three value groups per clump (r009: 1a found per-leaf steps read as speckle):
    # lit crown toward the light, mid, shadowed underside; each clump gets its own overall value
    # so neighbouring masses separate instead of repeating one lighting pattern.
    nearest = np.zeros((size, size), np.int32)
    bd = np.full((size, size), 1e9, np.float32)
    for i, ((px, py), rd) in enumerate(zip(cen, rad)):
        dy, dx = wrapped_offsets(size, px, py)
        d2 = (dx * dx + dy * dy) / (rd * rd)
        nearest = np.where(d2 < bd, i, nearest)
        bd = np.minimum(bd, d2)
    # r009 1d: one light direction for every clump drew the same crown/underside split 8x per tile,
    # a diagonal hatch across a hedge: the crown was a straight half-plane cut, and the cuts lined up.
    # Now the crown is a round highlight pushed toward a per-clump light, with its own size.
    # (own stream, so the leaf and pocket layout below stay as reviewed)
    rj = rng(k["seed"] + 100)
    ang = math.atan2(LIGHT[1], LIGHT[0]) + rj.uniform(-0.8, 0.8, len(cen))
    lx, ly = np.cos(ang).astype(np.float32)[nearest], np.sin(ang).astype(np.float32)[nearest]
    lit = -(off[..., 0] * lx + off[..., 1] * ly)
    push = rj.uniform(0.25, 0.45, len(cen)).astype(np.float32)[nearest]
    rc = rj.uniform(0.45, 0.65, len(cen)).astype(np.float32)[nearest]
    crown = (off[..., 0] + push * lx) ** 2 + (off[..., 1] + push * ly) ** 2 < rc * rc
    shadow = (lit < -0.30) | (best > 0.75)
    clump_val = r.uniform(-0.08, 0.08, len(cen)).astype(np.float32)
    macro = 0.50 + clump_val[nearest] + np.where(crown, 0.16, 0.0) - np.where(shadow & ~crown, 0.16, 0.0)
    # micro: single leaves only on crowns and clump silhouettes, faint seams where leaves meet
    lid = np.full((size, size), -1, np.int32)
    lval = np.zeros((size, size), np.float32)
    pts = poisson(k["n"], size, 2.4, r)
    for i in r.permutation(len(pts)):
        px, py = pts[i]
        dy, dx = wrapped_offsets(size, px, py)
        ang = r.normal(math.pi / 2, 1.0)
        L = r.uniform(*k["length"]) * (size / 32)
        W = r.uniform(*k["width"]) * (size / 32)
        m, t, sv = leaf_shape(dy, dx, ang, L, W)
        nrm = np.array([-math.sin(ang), math.cos(ang)])
        facing = float(nrm @ -LIGHT)
        v = 0.05 * np.sign(sv) * facing + r.uniform(-0.05, 0.05) + 0.05 * (t < -0.5)
        m &= f > 0.30            # leaves fringe a clump; they never float in a gap
        m &= crown | (f < 0.75)  # ...and sit on the lit crown or the silhouette, not everywhere
        lid = np.where(m, i, lid)
        lval = np.where(m, v, lval)
    inside = core | (lid >= 0)
    seam = np.zeros((size, size), bool)
    for dy_, dx_ in ((0, 1), (1, 0)):
        nb = np.roll(np.roll(lid, -dy_, 0), -dx_, 1)
        seam |= (nb != lid)
    # a seam darkens the pixel on the shadow side (below/right) of a leaf edge
    val = np.where(inside, macro + lval - 0.06 * seam, 0.0)
    val = np.where(inside & (lid < 0), macro - 0.04, val)
    gap = ~inside
    # See-through gaps: only small pockets at the deepest points between clumps. Long gap
    # channels repeat block after block and read as a tiling pattern (r008 first render: a row of
    # zigzags along every oak canopy), so a pocket is kept only where the field is a local minimum.
    # r009 1c: pockets that followed the field's valleys still came out as oak zigzag columns,
    # jungle Y-shapes and acacia ticks; a pocket is now a round hole centred on each minimum.
    deep = f < {"jungle": 0.12, "acacia": 0.24}.get(kind, 0.18)
    low = f < {"jungle": 0.24, "acacia": 0.30}.get(kind, 0.26)
    nb_min = np.minimum.reduce([np.roll(np.roll(f, dy, 0), dx, 1)
                                for dy in range(-3, 4) for dx in range(-3, 4)])
    hole = np.zeros((size, size), bool)
    hr = {"jungle": 2.3, "acacia": 1.5, "oak": 1.7}.get(kind, 1.9) * (size / 32)
    for py, px in zip(*np.nonzero((f <= nb_min) & low)):
        # sizes vary and each pocket is two overlapping discs, so they never read as a dot grid
        s = hr * r.uniform(0.6, 1.4)
        for j in range(2):
            ox, oy = (0.0, 0.0) if j == 0 else r.uniform(-1.2, 1.2, 2) * s
            dy, dx = wrapped_offsets(size, px + 0.5 + ox, py + 0.5 + oy)
            hole |= dx * dx + dy * dy <= (s * (1.0 if j == 0 else 0.7)) ** 2
    hole &= gap | low
    deep |= hole
    val = np.where(gap & ~deep, 0.22 + 0.06 * f, val)
    alpha = ~hole
    if alpha.mean() < 0.55:      # never sparser than vanilla's 61 % opaque
        alpha = f > np.quantile(f, 0.38)
    ramp = [0.18, 0.27, 0.36, 0.45, 0.55, 0.65, 0.76]
    val = quant(np.clip(val, 0.15, 0.85), ramp)
    m = val[alpha].mean()
    val = quant(np.clip(val * (0.53 / m), 0.12, 0.88), ramp)
    return grey(val, alpha)


def needles(size=32, seed=21):
    """Spruce: layered needle sprays, darker and denser than broadleaf."""
    r = rng(seed)
    val = np.full((size, size), 0.24, np.float32)
    alpha = np.ones((size, size), bool)
    for i in range(70):
        x0, y0 = r.uniform(0, size, 2)
        ang = r.normal(math.pi * 0.62 if r.random() < 0.5 else math.pi * 0.38, 0.12)
        L = r.uniform(3, 6)
        depth = i / 70
        for j in range(int(L * 2)):
            x = int(x0 + math.cos(ang) * j / 2) % size
            y = int(y0 + math.sin(ang) * j / 2) % size
            val[y, x] = 0.36 + 0.34 * depth + (0.08 if j < 2 else 0.0)
    holes = r.random((size, size)) < 0.12
    alpha &= ~(holes & (val < 0.3))
    val = quant(val, [0.22, 0.32, 0.42, 0.52, 0.62, 0.72])
    m = val[alpha].mean()
    val = quant(np.clip(val * (0.47 / m), 0.12, 0.85), [0.22, 0.32, 0.42, 0.52, 0.62, 0.72])
    return grey(val, alpha)


# --- previews -------------------------------------------------------------------------------------
def tint(a, colour):
    out = a.astype(np.float32).copy()
    out[..., :3] *= colour
    return out.astype(np.uint8)


def preview(tiles, path, scale=6, rep=3, bg=(72, 108, 150)):
    """tiles: [(label, rgba, tint or None)] -> one sheet: each tile repeated rep x rep, upscaled."""
    from PIL import Image
    cell = max(t[1].shape[1] for t in tiles) * rep * scale // max(1, max(t[1].shape[1] for t in tiles) // 32)
    ims = []
    for _, a, col in tiles:
        a = tint(a, col) if col is not None else a
        h, w = a.shape[:2]
        if h > w:
            a = a[:w]
        big = np.tile(a, (rep, rep, 1))
        im = Image.fromarray(big, "RGBA")
        f = cell // im.width
        ims.append(im.resize((im.width * f, im.height * f), Image.NEAREST))
    W = sum(i.width for i in ims) + 8 * (len(ims) + 1)
    H = max(i.height for i in ims) + 16
    sheet = Image.new("RGBA", (W, H), bg + (255,))
    x = 8
    for im in ims:
        sheet.alpha_composite(im, (x, 8))
        x += im.width + 8
    sheet.save(path)


# --- bark and log ends ------------------------------------------------------------------------------
def hexes(*h):
    return np.array([[int(x[i:i + 2], 16) / 255.0 for i in (0, 2, 4)] for x in h], np.float32)


# Each wood: bark ramp dark..light, end-grain ramp dark..light (5 steps each). Hues follow vanilla's
# own log colours so builds keep their look; the ramps add the steps vanilla's 16x lacks.
WOODS = {
    "oak":     dict(bark=hexes("3a2b18", "564025", "6e5532", "896a40", "a07d4f"),
                    ring=hexes("6b5331", "8a6c41", "a3834f", "b8975e", "c8a96c"), plate=(5, 13), ridge=(3, 6), seed=31),
    "spruce":  dict(bark=hexes("1f160c", "2f2214", "40301c", "524026", "655033"),
                    ring=hexes("5a4126", "755633", "8d6a40", "a17c4c", "b28d59"), plate=(3, 8), ridge=(3, 5), seed=32),
    "birch":   dict(bark=hexes("2a2622", "8f8a80", "c5c0b4", "dcd8cc", "eeebe2"),
                    ring=hexes("8d7a52", "a99366", "c0aa79", "d2bd8a", "e0cc98"), plate=(6, 14), ridge=(4, 7), seed=33),
    "jungle":  dict(bark=hexes("2c2010", "45351a", "5c4823", "6f5a2c", "857038"),
                    ring=hexes("7a5333", "946642", "ab7a50", "bd8b5d", "cc9b69"), plate=(4, 10), ridge=(3, 6), seed=34),
    "acacia":  dict(bark=hexes("2f2c28", "45413b", "5b564e", "6f6a60", "848075"),
                    ring=hexes("8d4a26", "a85b30", "bd6c3a", "cd7c45", "da8c52"), plate=(4, 9), ridge=(2, 5), seed=35),
    "big_oak": dict(bark=hexes("1d140b", "2c1f11", "3b2a18", "4b3720", "5c462a"),
                    ring=hexes("4a3520", "5f452a", "735634", "85663e", "947548"), plate=(4, 10), ridge=(3, 5), seed=36),
}


def bark(wood="oak", size=32):
    """Log side: vertical bark ridges that wander a little, broken into plates by short cracks, each
    plate lit on its left edge and dark on its right, with dark fissures between ridges. Tiles
    vertically (a stacked trunk reads continuous) and horizontally (the four sides meet)."""
    w = WOODS[wood]
    r = rng(w["seed"])
    s = size / 32
    # ridge boundaries across the width, wandering with y (one sine period per tile so it tiles)
    cuts, x = [], 0.0
    while x < size - 2:
        x += r.uniform(*w["ridge"]) * s
        cuts.append(x)
    cuts = np.array(cuts[:-1] if size - cuts[-1] < 2 * s else cuts)
    cuts = cuts * (size / (cuts[-1] + r.uniform(*w["ridge"]) * s * 0.0 + (size - cuts[-1]))) if len(cuts) else cuts
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32)
    phase = r.uniform(0, 2 * math.pi, len(cuts))
    amp = r.uniform(0.4, 1.4, len(cuts)) * s
    bound = np.stack([(c + a * np.sin(2 * math.pi * yy / size + ph)) % size for c, a, ph in zip(cuts, amp, phase)], 0)
    # ridge index and position across the ridge for each pixel
    xs = np.sort(bound, axis=0)
    idx = (xx[None] >= xs).sum(0) % len(cuts)
    left = np.take_along_axis(xs, ((idx - 1) % len(cuts))[None], 0)[0]
    right = np.take_along_axis(xs, idx[None], 0)[0]
    width = (right - left) % size
    width = np.where(width < 0.5, size, width)
    u = ((xx - left) % size) / width                   # 0 at the ridge's left fissure, 1 at the right
    val = 2.4 - 1.5 * u                                 # lit left, darker right
    val += 0.5 * np.exp(-((u - 0.25) / 0.18) ** 2)      # a highlight a quarter in
    fissure = (u > 0.86) | (u < 0.06)
    # plates: per ridge, horizontal cracks at random heights (tiling: cracks wrap)
    crack = np.zeros((size, size), bool)
    plate_shift = np.zeros((size, size), np.float32)
    for k in range(len(cuts)):
        y, ys = r.uniform(0, size), []
        while len(ys) < 12:
            ys.append(y % size)
            y += r.uniform(*w["plate"]) * s
            if y - ys[0] >= size - 2 * s:
                break
        mask = idx == k
        for j, y0 in enumerate(ys):
            row = np.abs(((yy - y0 + size / 2) % size) - size / 2) < 0.5 * s
            crack |= mask & row & (u > 0.12) & (u < 0.82)
        tone = r.uniform(-0.35, 0.35)
        plate_shift = np.where(mask, tone, plate_shift)
    val = val + plate_shift
    val = np.where(crack, 0.6, val)
    val = np.where(fissure, 0.0, val)
    # the row below a crack catches light (the plate's top lip)
    lip = np.roll(crack, 1, 0) & ~crack & ~fissure
    val = np.where(lip, val + 0.6, val)
    lv = np.clip(np.round(val), 0, 4).astype(int)
    rgb = w["bark"][lv]
    if wood == "birch":
        rgb = birch_marks(rgb, r, size)
    return rgba(rgb)


def birch_marks(rgb, r, size):
    """Birch: pale bark with dark horizontal lenticels and a few dark scars, no ridged look."""
    s = size / 32
    pale = hexes("2a2622", "8f8a80", "c5c0b4", "dcd8cc", "eeebe2")
    yy, xx = np.mgrid[0:size, 0:size]
    soft = np.sin(2 * math.pi * xx / size * 2 + r.uniform(0, 6)) + 0.6 * np.sin(2 * math.pi * yy / size * 3 + r.uniform(0, 6))
    out = np.where((soft > 0.9)[..., None], pale[3], pale[4]).astype(np.float32)
    for _ in range(int(22 * s * s)):
        y, x = r.integers(0, size), r.integers(0, size)
        L = int(r.integers(2, 6) * s)
        for i in range(L):
            out[y, (x + i) % size] = pale[0] if i not in (0, L - 1) else pale[1]
        if r.random() < 0.5:
            out[(y + 1) % size, (x + 1) % size: (x + L - 1) % size] = pale[2]
    for _ in range(3):
        y, x = r.integers(0, size), r.integers(0, size)
        h, w_ = int(r.integers(2, 4) * s), int(r.integers(3, 7) * s)
        for dy in range(h):
            for dx in range(w_):
                if r.random() < 0.8:
                    out[(y + dy) % size, (x + dx) % size] = pale[0] if dy else pale[1]
    return out


def log_top(wood="oak", size=32):
    """Log end: wobbly growth rings around a dark pith, a ring of bark at the edge."""
    w = WOODS[wood]
    r = rng(w["seed"] + 100)
    c = size / 2 - 0.5 + r.uniform(-1.0, 1.0)
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32)
    dx, dy = xx - c, yy - c
    ang = np.arctan2(dy, dx)
    rad = np.sqrt(dx * dx + dy * dy) * (1 + 0.04 * np.sin(3 * ang + 1.3) + 0.03 * np.sin(5 * ang))
    sp = size / 32 * 2.6
    line = (rad % sp) < (size / 32 * 0.9)           # one-pixel growth lines, evenly spaced
    v = np.where(line, 1, 3) + ((rad < size * 0.22) & ~line)
    v = np.where(rad < size / 32 * 1.6, 0, v)
    rgb = w["ring"][np.clip(v, 0, 4)]
    # bark rim: Chebyshev distance to the edge
    edge = np.minimum(np.minimum(xx, size - 1 - xx), np.minimum(yy, size - 1 - yy))
    bark_rgb = w["bark"][np.where(edge < size / 32 * 1, 1, 3)]
    sap = edge < size / 32 * 3.0
    rgb = np.where(sap[..., None], bark_rgb, rgb)
    inner = (edge >= size / 32 * 3.0) & (edge < size / 32 * 4.0)
    rgb = np.where(inner[..., None], w["ring"][0], rgb)
    return rgba(rgb)


# --- plants -----------------------------------------------------------------------------------------
class Canvas:
    """A cut-out plant canvas: value or colour per pixel, drawn back to front."""

    def __init__(self, size, rgb=False):
        self.size = size
        self.v = np.zeros((size, size, 3 if rgb else 1), np.float32)
        self.a = np.zeros((size, size), bool)

    def put(self, x, y, c):
        x, y = int(round(x)), int(round(y))
        if 0 <= x < self.size and 0 <= y < self.size:
            self.v[y, x] = c
            self.a[y, x] = True

    def out(self):
        if self.v.shape[2] == 1:
            return grey(self.v[..., 0], self.a)
        return rgba(self.v, self.a)


def blade(cv, x0, h, lean, width, colour_at, bottom=None, steps=None):
    """One grass blade or stalk from (x0, bottom) up h pixels, bending by `lean` at the tip, tapering
    from `width`. colour_at(t, side) gives the colour along it (t 0 base .. 1 tip, side -1 left / +1
    right). Returns the tip position."""
    size = cv.size
    y0 = (size - 1) if bottom is None else bottom
    n = steps or int(h * 3)
    pts = []
    for i in range(n + 1):
        t = i / n
        x = x0 + lean * t * t
        y = y0 - h * t
        pts.append((x, y, t))
    for x, y, t in pts:
        w = max(0.5, width * (1 - t) ** 0.6)
        for dx in np.arange(-w / 2, w / 2 + 1e-3, 0.5):
            side = -1 if dx < 0 else 1
            cv.put(x + dx, y, colour_at(t, side))
    return pts[-1][0], pts[-1][1]


def tall_grass(size=32, seed=41):
    """Tall grass: a tuft of blades from one root, the outer ones arching out, lit on the left."""
    r = rng(seed)
    cv = Canvas(size)
    s = size / 32
    ramp = [0.32, 0.42, 0.52, 0.62, 0.72]
    blades = sorted([(r.uniform(9, 23) * s, r.uniform(12, 27) * s) for _ in range(13)], key=lambda b: -b[1])
    for x0, h in blades:
        lean = (x0 - 16 * s) * r.uniform(0.6, 1.1) + r.normal(0, 2) * s
        def col(t, side, k=r.uniform(0, 1)):
            i = 1 + (side < 0) + (t > 0.55) + (k > 0.6)
            return ramp[min(4, i)] - 0.1 * (t < 0.12)
        blade(cv, x0, h, lean, 2.2 * s, col)
    return cv.out()


def fern(size=32, seed=42):
    """Fern: three or four fronds, each a curved rib with paired leaflets that shorten to the tip."""
    r = rng(seed)
    cv = Canvas(size)
    s = size / 32
    ramp = [0.30, 0.40, 0.50, 0.60, 0.70]
    for k, (x0, h, lean) in enumerate([(14, 22, -9), (18, 24, 9), (16, 28, 2), (12, 16, -12), (20, 17, 12)]):
        x0, h, lean = x0 * s, h * s, lean * s
        n = int(h * 2)
        for i in range(n + 1):
            t = i / n
            x = x0 + lean * t * t
            y = size - 1 - h * t
            cv.put(x, y, ramp[1])
            if i % 3 == 0 and t > 0.1:
                L = (1 - t) * 5 * s + 1
                for j in range(1, int(L) + 1):
                    up = j * 0.45
                    cv.put(x - j, y - up, ramp[3] if j < L - 1 else ramp[4])
                    cv.put(x + j, y - up, ramp[2] if j < L - 1 else ramp[3])
    return cv.out()


WHEAT_GREEN = hexes("26400f", "3a5c16", "4f7a1e", "679a28", "82b334")
WHEAT_GOLD = hexes("6a5222", "947632", "b99a48", "d4b868", "e9d590")   # straw, not orange (r008 render)
WHEAT_TURN = hexes("4f5214", "70721e", "939329", "b2ad3a", "cdc65a")


EAR = [0, 0, 0, 0, 5, 7, 9, 10]   # ear length per stage at 32x: slim and long (v2d's 4-8 read as blobs)
WHEAT_RIPE = hexes("6e5a26", "9e8438", "c6a84c", "dfc468", "f2df92")   # v2: a step brighter and yellower


def wheat(stage, size=32, seed=51):
    """Wheat v2, stages 0-7. r008: v1 (wheat_v1 below) read as a solid chunky wall and the owner wants
    Stay True's crops (ARR, direction only: nothing of its pixels). So: separate plants with air
    between them, each a 1 px stalk (2 px, lit left, near the root) with one or two arching leaves;
    young stages are tufts that grow; from stage 4 a slim 2 px braided ear (alternating lit kernels,
    a kernel off the left every other row), sparse awns on its upper half from stage 6, the ripe ear nodding toward its lean.
    Back plants are shorter and a step darker for depth."""
    r = rng(seed + 10 * stage)
    cv = Canvas(size, rgb=True)
    s = size / 32
    grow = [0.14, 0.24, 0.36, 0.48, 0.60, 0.72, 0.84, 0.92][stage]
    stem = WHEAT_GREEN if stage < 6 else (WHEAT_TURN if stage == 6 else WHEAT_RIPE)
    ear_pal = WHEAT_GREEN if stage < 6 else (WHEAT_TURN if stage == 6 else WHEAT_RIPE)
    leaf_pal = WHEAT_GREEN if stage < 7 else WHEAT_TURN
    front = 5 if stage >= 2 else 4
    plants = [(x, False) for x in np.linspace(4, 28, front) + r.uniform(-0.7, 0.7, front)]
    if stage >= 3:   # back plants in three of the four gaps, so their ears don't merge with the front ones
        fx = sorted(x for x, _ in plants)
        gaps = r.choice(len(fx) - 1, 3, replace=False)
        plants = [((fx[g] + fx[g + 1]) / 2 + r.uniform(-0.5, 0.5), True) for g in gaps] + plants
    def leaf(x0, y0, d, L, back):
        """A leaf off the stalk at (x0, y0): a thin blade rising beside it and arching out by d."""
        blade(cv, x0 + d * 0.5, L, d * L * 0.8, 1.0 * s,
              lambda t, side: leaf_pal[max(0, 3 - back - (t > 0.75))], bottom=y0)
    for x0, back in plants:
        x0 *= s
        b = int(back)
        h = (size - 2 * s) * grow * r.uniform(0.75, 1.0) * (0.85 if back else 1.0)
        lean = float(np.clip(r.normal(0, 1.5) * s, 1.5 * s - x0, size - 3.5 * s - x0))   # tip stays in the tile
        if stage >= 4:   # stalk + ear fit under the top edge
            h = min(h, size - 2 * s - EAR[stage] * s)
        y0 = size - 1
        if stage < 3:
            # a tuft: two or three blades from the root, the outer ones arching out
            for d, k in [(-1, 0.75), (1, 0.85)] + ([(0, 1.0)] if stage >= 1 else []):
                blade(cv, x0 + d * 0.5, h * k, d * h * r.uniform(0.35, 0.6) + lean * 0.3, 1.0 * s,
                      lambda t, side, b=b: leaf_pal[max(0, 3 - b - (t < 0.3) + (t > 0.8 and side < 0))])
            continue
        # the stalk, 1 px, with a shaded right pixel near the root
        n = int(h)
        bow = r.normal(0, 0.9) * s
        for i in range(n + 1):
            t = i / max(1, n)
            x = x0 + lean * t * t + bow * 4 * t * (1 - t)   # a slight bow, so the stalks aren't posts
            cv.put(x, y0 - i, stem[max(0, 1 + (t > 0.4) - b)])
            if t < 0.12 and not back:
                cv.put(x + 1, y0 - i, stem[1])
        tx, ty = round(x0 + lean), y0 - n
        # one or two leaves off the stalk, low down, to opposite sides
        d = r.choice([-1, 1])
        for k in range(1 if stage >= 6 else 2):
            leaf(x0 + lean * 0.05, y0 - h * r.uniform(0.25, 0.5), d * (-1) ** k, int(r.uniform(4, 7) * s), b)
        if stage < 4:
            continue
        # the ear: 2 px wide, kernels braided, nodding toward the lean near the tip
        L = int(EAR[stage] * s)
        nod = 1 if lean >= 0 else -1
        for j in range(L):
            y = ty - j
            x = tx + nod * ((stage >= 6 and j >= L - 3) + (stage >= 7 and j >= L - 1))   # the tip nods
            odd = j % 2
            cv.put(x, y, ear_pal[max(0, 4 - b - odd)])
            cv.put(x + 1, y, ear_pal[max(0, 3 - b + odd)])
            if odd and 0 < j < L - 1:
                cv.put(x - 1, y, ear_pal[max(0, 2 - b)])   # a kernel off the left every other row
        # awns: a few fine hairs off the ear, up and out
        if stage >= 6:
            for j in range(L // 2, L, 2):
                side = -1 if (j // 2) % 2 else 1
                for k in range(1, 3):
                    cv.put(tx + (0.5 + 0.5 * side) + side * k, ty - j - k, ear_pal[max(0, 3 - b)])
    return cv.out()


def wheat_v1(stage, size=32, seed=51):
    """v1's wheat (r008; the build uses wheat() since v2; kept for comparison previews).
    Wheat, stages 0-7: green shoots that grow tall, set green ears, turn, and end golden and bushy.
    Stay True's idea (ARR, direction only): a dense crop, each head a fat ear that nods a little.
    Here: 11-13 stalks with a leaf or two, each ear a column of kernel pairs (light left, dark
    right, a dark seam between rows), fine awns above, back stalks a step darker for depth."""
    r = rng(seed + stage)
    cv = Canvas(size, rgb=True)
    s = size / 32
    grow = [0.20, 0.30, 0.42, 0.54, 0.66, 0.78, 0.90, 1.0][stage]
    pal = WHEAT_GREEN if stage < 6 else (WHEAT_TURN if stage == 6 else WHEAT_GOLD)
    stem = WHEAT_GREEN if stage < 6 else (WHEAT_TURN if stage == 6 else WHEAT_GOLD)
    nst = 13 if stage >= 4 else 9
    xs = np.linspace(3, 29, nst) * s + r.uniform(-1.0, 1.0, nst) * s
    depth = r.random(nst)
    for k in np.argsort(depth):            # back (low depth) first
        x0 = xs[k]
        back = depth[k] < 0.45
        h = (size - 2 * s) * grow * r.uniform(0.80, 1.0) * (0.92 if back else 1.0)
        lean = r.normal(0, 2.4) * s
        def scol(t, side, back=back):
            i = 2 + (side < 0) - back
            return stem[max(0, min(4, i))]
        tx, ty = blade(cv, x0, h, lean, 1.5 * s, scol)
        # a leaf off the stalk, low down
        if r.random() < 0.7:
            blade(cv, x0 + lean * 0.1, h * r.uniform(0.35, 0.6), r.choice([-1, 1]) * r.uniform(4, 7) * s, 1.6 * s,
                  lambda t, side, back=back: (WHEAT_GREEN if stage < 7 else WHEAT_TURN)[max(0, 3 - back - (side > 0))])
        if stage < 4:
            continue
        # the ear: kernel pairs down from the tip, nodding toward the lean
        ear = int(([0, 0, 0, 0, 5, 7, 9, 10][stage]) * s)
        nod = np.sign(lean) if lean else 1
        dk = -1 if back else 0
        for j in range(ear):
            y = ty + j + 1
            x = tx + nod * max(0, (ear * 0.35 - j)) * 0.35
            hi, mid, lo = pal[min(4, 4 + dk - (j % 2))], pal[max(0, 3 + dk - (j % 2))], pal[max(0, 1 + dk)]
            cv.put(x - 1, y, hi)
            cv.put(x, y, mid if j % 2 == 0 else lo)
            cv.put(x + 1, y, lo if j % 2 == 0 else mid)
        # awns: fine hairs fanning up from the ear
        if stage >= 5:
            for d in (-1, 0, 1):
                for j in range(1, int((3 + (stage >= 7)) * s) + 1):
                    cv.put(tx + d * j * 0.6, ty - j + 1, pal[3] if d <= 0 else pal[2])
    return cv.out()


def grass_top(size=32, seed=61):
    """v1's grass top (the build uses grass_top_from since v2; kept for comparison previews).
    Grey for the biome tint. Calm (the owner: no "noisy green carpet"): soft clump-
    scale light and shadow a few pixels across, and sparse short blade marks, all within a narrow
    value range so it reads as turf up close and as an even field at a distance."""
    r = rng(seed)
    s = size / 32
    cen = poisson(9, size, size * 0.22, r)
    f, off, best = clump_field(size, cen, r.uniform(4.5, 6.5, len(cen)) * s)
    lit = -(off[..., 0] * LIGHT[0] + off[..., 1] * LIGHT[1])
    val = 0.575 + 0.07 * np.clip(lit, -1, 1) * np.clip(f, 0, 1) - 0.03 * (f < 0.35)
    # blade marks: 2-3 px strokes, a light tip over a dark root
    for _ in range(int(70 * s * s)):
        x, y = r.integers(0, size), r.integers(0, size)
        L = r.integers(2, 4)
        lean = r.choice([-1, 0, 0, 1])
        for j in range(L):
            yy_, xx_ = (y - j) % size, (x + (lean if j == L - 1 else 0)) % size
            val[yy_, xx_] = val[yy_, xx_] + (0.07 if j == L - 1 else 0.035)
        val[(y + 1) % size, x] -= 0.05
    val = quant(np.clip(val, 0.40, 0.75), [0.47, 0.52, 0.565, 0.61, 0.655, 0.70])
    return grey(val)


def grass_top_from(vanilla, keep=0.75):
    """Grass top for v2, from vanilla's own 16x grass_top (the player's jar, read at build time).
    grass_top() above read as flat felt in r008 (6 grey values); the owner preferred r007's, which
    was vanilla's pattern doubled. So vanilla's pattern stays: its clump-scale shading is kept whole,
    only the pixel-to-pixel contrast is lowered (to `keep`), and each pixel is doubled with hard
    edges (r007 blurred after doubling, which softened them). At 32x, a pixel brighter than its
    neighbours gets a lit upper-left sub-pixel and a shaded lower-right one: a blade tip."""
    g = vanilla[..., :3].astype(np.float32).mean(-1) / 255.0
    blur = sum(np.roll(np.roll(g, dy, 0), dx, 1) for dy in (-1, 0, 1) for dx in (-1, 0, 1)) / 9.0
    hi = g - blur
    v = (blur + hi * keep).repeat(2, 0).repeat(2, 1)
    tip = np.clip(hi / 0.08, 0, 1) * 0.035
    v[0::2, 0::2] += tip
    v[1::2, 1::2] -= tip * 0.6
    return grey(v)


# --- bookshelf --------------------------------------------------------------------------------------
LEATHER = hexes("6e1f1a", "8a3b22", "2f4a2a", "3d5f3a", "243a5c", "34507a", "5a3d22", "7a5530",
                "4a2c4c", "6b4466", "8c6a2a", "3a3532", "7c2c3c", "2e5a5a")
GILT = hexes("c9a23e", "e6c867")
SHELF_BACK = hexes("1c130b", "2a1d11")


def book_row(cv, y0, y1, r, s):
    """Fill one shelf (rows y0..y1-1) with books: varied widths, heights and leathers, gilt or dark
    bands near the top and bottom, a title patch on some, now and then a leaning book or a gap."""
    size = cv.size
    x = 0
    H = y1 - y0
    while x < size:
        if r.random() < 0.07 and x > 2 * s and x < size - 6 * s:
            x += int(r.integers(2, 4) * s)            # a gap: the dark shelf back shows
            continue
        w = int(r.choice([2, 3, 3, 4, 4, 5]) * s)
        w = min(w, size - x)
        if w <= 0:
            break
        h = int(H - r.choice([0, 0, 1, 1, 2, 3, 4]) * s)
        col = LEATHER[r.integers(len(LEATHER))] * r.uniform(0.9, 1.08)
        lean = r.random() < 0.06 and x > size // 2 and w <= 3 * s
        band = r.random()
        for dx in range(w):
            for dy in range(h):
                yy = y1 - 1 - dy
                xx = x + dx + (int(dy * 0.5) if lean else 0)
                if xx >= size:
                    continue
                c = col.copy()
                if dx == 0:
                    c = c * 1.28               # lit left edge (rounded spine)
                elif dx == w - 1:
                    c = c * 0.62               # shadowed right edge
                elif dx == 1 and w >= 4 * s:
                    c = c * 1.12
                top = h - 1 - dy               # rows from the book's top
                if band < 0.55 and top in (int(1 * s), int(1 * s) + 1, h - int(2 * s)) and 0 < dx < w - 1:
                    c = GILT[top % 2] if band < 0.35 else c * 0.55
                if band > 0.8 and int(h * 0.35) <= top <= int(h * 0.35) + int(2 * s) and 0 < dx < w - 1:
                    c = hexes("d8cdb0")[0] * (0.85 if dx == w - 2 else 1.0)   # title label
                if top == 0:
                    c = c * 0.8
                cv.v[yy, xx] = np.clip(c, 0, 1)
        x += w


def bookshelf(size=32, seed=71, planks=None):
    """Bookshelf side: two shelves of characterful books between oak boards. `planks` is the
    game's oak plank texture (any size): its colours make the boards so they match the top."""
    r = rng(seed)
    s = size / 32
    cv = Canvas(size, rgb=True)
    cv.a[:] = True
    back = SHELF_BACK
    cv.v[:] = back[0]
    if planks is not None:
        p = planks[..., :3].reshape(-1, 3).astype(np.float32) / 255.0
        lum = p @ np.array([0.3, 0.59, 0.11])
        ramp = [p[(lum >= np.quantile(lum, a)) & (lum <= np.quantile(lum, b))].mean(0)
                for a, b in ((0, .15), (.15, .4), (.4, .7), (.7, .9), (.9, 1))]
        board = np.array(ramp, np.float32)
    else:
        board = WOODS["oak"]["ring"]
    rows = [(0, int(2 * s)), (int(14 * s), int(18 * s)), (int(30 * s), size)]
    for a, b in rows:
        for y in range(a, b):
            k = 3 if y == a else (1 if y == b - 1 else 2)
            cv.v[y, :] = board[k]
        # grain: a few darker dashes along each board
        for _ in range(int(4 * s)):
            y = r.integers(a, b)
            x0 = r.integers(0, size)
            for dx in range(int(r.integers(3, 8) * s)):
                cv.v[y, (x0 + dx) % size] = board[1]
    # board ends: vertical joints at the edges, so neighbouring shelves read as separate units
    for a, b in rows:
        cv.v[a:b, 0] = board[1]
        cv.v[a:b, size - 1] = board[0]
    book_row(cv, int(2 * s), int(14 * s), r, s)
    book_row(cv, int(18 * s), int(30 * s), r, s)
    # shadow under each top board
    for y in (int(2 * s), int(18 * s)):
        cv.v[y] = cv.v[y] * 0.6
    return cv.out()


# --- leaf edges (CTM) -------------------------------------------------------------------------------
def opaque(a, fill=0.16):
    """Fast-graphics leaves (*_opaque): the see-through gaps filled with deep shadow."""
    out = a.copy()
    hole = out[..., 3] == 0
    v = int(fill * 255)
    out[hole] = (v, v, v, 255)
    return out


def ragged_tile(base, edges, seed, depth=3.2):
    """A leaf texture whose `edges` (any of T, B, L, R: the sides with no leaf block beyond them)
    are bitten into: leaves end irregularly instead of on the block's straight edge. The cut follows
    a wandering profile 0..depth px deep (at 32x), with a darker pixel just inside the cut so the
    new outline reads as leaves overlapping, not as a hole."""
    a = base.copy()
    size = a.shape[0]
    s = size / 32
    r = rng(seed)
    t = np.arange(size, dtype=np.float32)
    yy, xx = np.mgrid[0:size, 0:size]
    cut = np.zeros((size, size), bool)
    rim = np.zeros((size, size), bool)
    for e in edges:
        prof = np.zeros(size, np.float32)
        for k, amp in ((1, 0.9), (2, 0.7), (3, 0.5), (5, 0.35)):
            prof += amp * np.sin(2 * math.pi * k * t / size + r.uniform(0, 6.3))
        prof = (prof - prof.min()) / max(1e-3, np.ptp(prof)) * depth * s
        # a few deeper notches between leaf clumps
        for _ in range(3):
            c = r.uniform(0, size)
            prof += 1.6 * s * np.exp(-((t - c) / (1.6 * s)) ** 2)
        d = {"T": yy, "B": size - 1 - yy, "L": xx, "R": size - 1 - xx}[e].astype(np.float32)
        along = xx if e in "TB" else yy
        p = prof[along]
        cut |= d < p - 0.5
        rim |= (d >= p - 0.5) & (d < p + 0.6 * s)
    a[cut, 3] = 0
    rim &= ~cut & (a[..., 3] > 0)
    a[rim, :3] = (a[rim, :3].astype(np.float32) * 0.72).astype(np.uint8)
    return a
