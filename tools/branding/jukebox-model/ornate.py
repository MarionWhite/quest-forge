"""Cabinet-maker's materials for the jukebox: burl, inlay, nebula glass.

Imported by make_jukebox_textures.py. Kept apart because these are a different
kind of work from the neon and chrome sheets -- those are shading profiles, these
are *figure*: the swirl of a burl, the run of a crossbanding, the dust in a
nebula -- and figure is almost entirely domain warping and careful palettes.

Everything returns float RGB in 0..1 (or RGBA where noted), HxWx3.
"""
import math

import numpy as np
from scipy.ndimage import gaussian_filter, map_coordinates


# ----------------------------------------------------------------------
# Noise
# ----------------------------------------------------------------------

def tile_field(h, w, sigma, seed):
    """Smooth unit-variance noise that wraps at the edges, so a sheet tiles."""
    rng = np.random.default_rng(seed)
    a = rng.standard_normal((h, w)).astype(np.float32)
    a = gaussian_filter(a, sigma, mode="wrap")
    return (a - a.mean()) / (a.std() + 1e-6)


def fbm(h, w, seed, base=64.0, octaves=6, gain=0.55):
    out = np.zeros((h, w), np.float32)
    amp, tot, s = 1.0, 0.0, base
    for o in range(octaves):
        out += amp * tile_field(h, w, max(0.6, s), seed * 31 + o)
        tot += amp
        amp *= gain
        s /= 2.0
    return out / tot


def warp(field, dx, dy):
    """Samples field at (y+dy, x+dx), wrapping."""
    h, w = field.shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    return map_coordinates(field, [(yy + dy) % h, (xx + dx) % w],
                           order=1, mode="wrap")


def palette(t, stops):
    """Maps t (any shape, 0..1) through (pos, rgb) stops."""
    t = np.clip(t, 0.0, 1.0)
    pos = np.array([p for p, _ in stops], np.float32)
    cols = np.array([c for _, c in stops], np.float32)
    out = np.zeros(t.shape + (3,), np.float32)
    for c in range(3):
        out[..., c] = np.interp(t, pos, cols[:, c])
    return out


# ----------------------------------------------------------------------
# Burl walnut
# ----------------------------------------------------------------------

BURL = [
    (0.00, (0.085, 0.036, 0.018)),
    (0.22, (0.200, 0.088, 0.040)),
    (0.48, (0.395, 0.185, 0.080)),
    (0.70, (0.600, 0.330, 0.140)),
    (0.88, (0.760, 0.480, 0.215)),
    (1.00, (0.880, 0.620, 0.310)),
]


def burl(h, w, seed=7, eyes=70):
    """Figured burl walnut, tileable.

    A burl is grain that grew round a cluster of dormant buds, so it has no
    direction: the figure is contour lines of a field that has been warped twice
    and pinched round scattered "eyes". Each eye is a dark pip with the grain
    wrapping tight about it, which is what separates burl from swirly noise.
    """
    base = fbm(h, w, seed, base=w * 0.055)
    # Pinch the field round the eyes before contouring, so grain wraps them.
    rng = np.random.default_rng(seed + 99)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    pinch = np.zeros((h, w), np.float32)
    pips = np.zeros((h, w), np.float32)
    for _ in range(eyes):
        cy, cx = rng.uniform(0, h), rng.uniform(0, w)
        r = rng.uniform(0.006, 0.016) * w
        dy = np.abs(yy - cy); dy = np.minimum(dy, h - dy)
        dx = np.abs(xx - cx); dx = np.minimum(dx, w - dx)
        d = np.sqrt(dx * dx + dy * dy)
        pinch += np.exp(-(d / (r * 3.2)) ** 2) * rng.uniform(1.2, 2.4)
        pips += np.exp(-(d / (r * 0.55)) ** 2)

    f1 = base + pinch * 0.9
    wx = fbm(h, w, seed + 3, base=w * 0.045) * w * 0.030
    wy = fbm(h, w, seed + 5, base=w * 0.045) * h * 0.030
    f2 = warp(f1, wx, wy)
    wx2 = fbm(h, w, seed + 8, base=w * 0.03) * w * 0.010
    wy2 = fbm(h, w, seed + 9, base=w * 0.03) * h * 0.010
    f3 = warp(f2, wx2, wy2)

    # Figure: contour bands of the warped field, kept soft. Hard-edged contour
    # lines are what made the first pass read as a topographic map.
    rings = np.sin(f3 * 7.0) * 0.5 + 0.5
    rings = gaussian_filter(rings, 0.8, mode="wrap") ** 1.3
    fine = np.sin(f3 * 23.0 + fbm(h, w, seed + 12, base=w * 0.015) * 2.5) * 0.5 + 0.5
    curl = fbm(h, w, seed + 13, base=w * 0.012)

    # Tone varies only at a scale well under the tile, so repeats do not show.
    tone = 0.47 + 0.11 * fbm(h, w, seed + 15, base=w * 0.09)
    t = (tone + 0.16 * rings + 0.07 * fine + 0.05 * curl
         - 0.42 * np.clip(pips, 0, 1))
    rgb = palette(t, BURL)

    # Chatoyance: the figure catches light in patches, lifting the golden tone.
    chat = np.clip(fbm(h, w, seed + 21, base=w * 0.05), 0, None) ** 1.5
    rgb += chat[..., None] * np.array([0.10, 0.065, 0.025], np.float32)
    return np.clip(rgb, 0, 1.2)


def straight_grain(h, w, seed, vertical=True, tone=0.52):
    """Quartersawn walnut for crossbanding: tight straight grain, slight ray fleck."""
    n = fbm(h, w, seed, base=w * 0.08)
    if vertical:
        stripes = gaussian_filter(np.random.default_rng(seed).standard_normal(
            (1, w)).astype(np.float32), (0, 1.2), mode="wrap")
        stripes = np.repeat(stripes, h, axis=0)
    else:
        stripes = gaussian_filter(np.random.default_rng(seed).standard_normal(
            (h, 1)).astype(np.float32), (1.2, 0), mode="wrap")
        stripes = np.repeat(stripes, w, axis=1)
    stripes = (stripes - stripes.mean()) / (stripes.std() + 1e-6)
    t = tone + 0.07 * stripes + 0.08 * n
    return palette(t, BURL)


# ----------------------------------------------------------------------
# Inlay
# ----------------------------------------------------------------------

BOXWOOD = np.array([0.86, 0.73, 0.50], np.float32)
EBONY = np.array([0.045, 0.030, 0.022], np.float32)


def rect_band(h, w, inset, width):
    """A mask for a rectangular line `width` wide, `inset` from the edge (px)."""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.minimum(np.minimum(xx, w - 1 - xx), np.minimum(yy, h - 1 - yy))
    return np.clip(1.0 - np.abs(d - inset) / (width * 0.5), 0, 1)


def lay(rgb, mask, colour):
    m = np.clip(mask, 0, 1)[..., None]
    return rgb * (1 - m) + colour * m


def lacquer(rgb, strength=1.0, seed=0):
    """A high-gloss finish: a broad sheen, and a soft specular streak."""
    h, w = rgb.shape[:2]
    y = np.linspace(0, 1, h, dtype=np.float32)[:, None, None]
    x = np.linspace(0, 1, w, dtype=np.float32)[None, :, None]
    sheen = np.exp(-((x - 0.34) / 0.30) ** 2) * (0.75 + 0.25 * (1 - y))
    streak = np.exp(-((x - 0.28 - (y - 0.5) * 0.10) / 0.035) ** 2) * (1 - y * 0.6)
    return rgb * (1.0 + 0.10 * strength * sheen) + 0.10 * strength * streak


def fan(h, w, cx, cy, r, quadrant, leaves=7):
    """A quarter fan inlay at (cx, cy): alternating leaves, shaded towards the hub.

    Returns (mask, shade) -- shade picks light or dark veneer per leaf.
    `quadrant` is the angular range the fan opens into, in radians.
    """
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    dx, dy = xx - cx, yy - cy
    d = np.sqrt(dx * dx + dy * dy)
    a = np.arctan2(dy, dx)
    a0, a1 = quadrant
    inside = (d < r) & (a >= a0) & (a <= a1)
    f = (a - a0) / (a1 - a0)
    leaf = np.floor(f * leaves).astype(np.int32)
    within = (f * leaves) % 1.0
    # Each leaf is shaded across its width, as sand-scorched veneer is.
    # Alternate leaves in satinwood and a darker harewood, each scorched in hot
    # sand towards the hub -- that shading is the whole of what makes a fan inlay
    # read as carved light rather than as a printed wedge.
    shade = np.where(leaf % 2 == 0, 1.00, 0.62) * (0.80 + 0.20 * np.sin(within * np.pi))
    shade = shade * (0.42 + 0.58 * np.clip(d / r, 0, 1) ** 0.7)
    edge = np.clip((r - d) / 2.0, 0, 1) * inside
    return edge.astype(np.float32), shade.astype(np.float32)


def panel(h, w, seed=3, fans=True, oval=True, border=0.075):
    """A veneered panel, laid up the way a cabinet-maker would.

    From the outside in: a crossbanded border in straight-grain walnut, a line
    of boxwood stringing and one of ebony, then a quartered burl field -- four
    leaves mirrored about both centrelines, so the figure is symmetrical the way
    only matched veneer is. Quarter-fan inlays sit in the field's corners and an
    oval of stringing reserves its centre.
    """
    b = int(border * w)

    # The field: one quarter of burl, mirrored into all four.
    qh, qw = (h + 1) // 2, (w + 1) // 2
    q = burl(qh, qw, seed=seed, eyes=10)
    top = np.concatenate([q[:, ::-1], q], axis=1)[:, :w]
    field = np.concatenate([top[::-1], top], axis=0)[:h]

    # Crossbanding: grain running perpendicular to each edge.
    rgb = field.copy()
    cb_v = straight_grain(h, w, seed + 40, vertical=False, tone=0.46)
    cb_h = straight_grain(h, w, seed + 41, vertical=True, tone=0.46)
    yy, xx = np.mgrid[0:h, 0:w]
    near_x = np.minimum(xx, w - 1 - xx)
    near_y = np.minimum(yy, h - 1 - yy)
    in_border = (np.minimum(near_x, near_y) < b)
    use_h = near_y < near_x               # top/bottom bands
    cb = np.where(use_h[..., None], cb_h, cb_v)
    rgb = np.where(in_border[..., None], cb, rgb)

    # Stringing: boxwood at the outer edge and inside the band, ebony beside it.
    lw = max(1.5, w * 0.006)
    rgb = lay(rgb, rect_band(h, w, lw * 1.5, lw), BOXWOOD)
    rgb = lay(rgb, rect_band(h, w, b, lw), BOXWOOD)
    rgb = lay(rgb, rect_band(h, w, b + lw * 1.8, lw * 0.8), EBONY)

    fy, fx = b + lw * 3, b + lw * 3        # the field's inner corner
    if fans:
        r = 0.15 * w
        for cx, cy, quad in ((fx, fy, (0, math.pi / 2)),
                             (w - 1 - fx, fy, (math.pi / 2, math.pi)),
                             (fx, h - 1 - fy, (-math.pi / 2, 0)),
                             (w - 1 - fx, h - 1 - fy, (-math.pi, -math.pi / 2))):
            m, shade = fan(h, w, cx, cy, r, quad)
            satin = np.array([0.90, 0.72, 0.44], np.float32)
            grain_ = 0.92 + 0.08 * np.sin(np.arctan2(yy - cy, xx - cx) * 260.0)
            veneer = satin * (shade * grain_)[..., None]
            rgb = rgb * (1 - m[..., None]) + veneer * m[..., None]
            # A line of boxwood round each fan.
            d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
            a = np.arctan2(yy - cy, xx - cx)
            ring = np.clip(1.0 - np.abs(d - r) / lw, 0, 1) * \
                   ((a >= quad[0]) & (a <= quad[1]))
            rgb = lay(rgb, ring, BOXWOOD)

    if oval:
        cy, cx = h * 0.5, w * 0.5
        ry, rx = h * 0.17, w * 0.24
        e = np.sqrt(((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2)
        rgb = lay(rgb, np.clip(1.0 - np.abs(e - 1.0) * rx / lw, 0, 1), BOXWOOD)
        rgb = lay(rgb, np.clip(1.0 - np.abs(e - 1.06) * rx / (lw * 0.8), 0, 1), EBONY)
        inner = np.clip((1.0 - e) * rx / 2.0, 0, 1)[..., None]
        rgb = rgb * (1 - inner * 0.22)    # the reserve sits a shade deeper

    return np.clip(lacquer(rgb, 1.0), 0, 1.3)


# ----------------------------------------------------------------------
# Nebula glass
# ----------------------------------------------------------------------

def nebula(size=1024, seed=11, aspect=1.5):
    """Black glass with a small nebula behind it, for the dome under the arch.

    Clouds are layered fbm, each pushed through a threshold so they come out as
    wisps with clear sky between rather than as uniform haze, and cut through
    by dust lanes. It is kept compact -- one cloud in the middle of a lot of
    black sky -- because a frame full of nebula reads as wallpaper. Stars follow
    a power law, a great many faint and a handful bright, and the bright few
    carry short diffraction spikes. Drawn at the dome's own 3:2 proportions and
    squared up at the end, so the stars come back round once the sheet is
    stretched over the opening.
    """
    n = size
    W = int(n * aspect)
    rgb = np.zeros((n, W, 3), np.float32)
    rgb[...] = np.array([0.004, 0.004, 0.011], np.float32)
    py, px = np.mgrid[0:n, 0:W].astype(np.float32)
    yy, xx = py / n, px / n                    # x runs 0..aspect

    def cloud(sd, base, warp_amt, thresh, power):
        f = fbm(n, W, sd, base=n * base)
        wx = fbm(n, W, sd + 1, base=n * base * 0.8) * n * warp_amt
        wy = fbm(n, W, sd + 2, base=n * base * 0.8) * n * warp_amt
        f = warp(f, wx, wy)
        return np.clip((f - thresh) * 1.6, 0, 1) ** power

    cx0, cy0 = aspect * 0.5, 0.52
    core = np.exp(-(((xx - cx0 - 0.04) / 0.16) ** 2 + ((yy - cy0 - 0.03) / 0.13) ** 2))
    halo = np.exp(-(((xx - cx0) / 0.34) ** 2 + ((yy - cy0) / 0.27) ** 2))

    magenta = cloud(seed, 0.10, 0.09, -0.10, 1.6) * halo
    violet = cloud(seed + 10, 0.14, 0.07, 0.05, 1.4) * halo
    teal = cloud(seed + 20, 0.08, 0.10, 0.20, 1.8) * halo
    ember = cloud(seed + 30, 0.05, 0.06, 0.10, 2.0) * core

    rgb += magenta[..., None] * np.array([0.70, 0.12, 0.46], np.float32)
    rgb += violet[..., None] * np.array([0.25, 0.11, 0.70], np.float32)
    rgb += teal[..., None] * np.array([0.05, 0.38, 0.52], np.float32)
    rgb += ember[..., None] * np.array([1.00, 0.48, 0.16], np.float32)
    rgb += core[..., None] * np.array([0.16, 0.07, 0.13], np.float32)

    dust = cloud(seed + 40, 0.045, 0.12, 0.10, 1.2)
    rgb *= (1.0 - 0.80 * dust * halo)[..., None]

    # Stars.
    rng = np.random.default_rng(seed + 50)
    count = 8200
    sy = rng.integers(0, n, count)
    sx = rng.integers(0, W, count)
    # Only the faint field is painted in. The bright stars are geometry now, so
    # they can twinkle; a bright one baked in here would sit still beside them.
    mag = np.clip(rng.pareto(2.2, count).astype(np.float32) / 6.0, 0.03, 0.30)
    point = np.zeros((n, W), np.float32)
    np.add.at(point, (sy, sx), mag)
    tint_b = np.zeros((n, W), np.float32)
    np.add.at(tint_b, (sy, sx), mag * rng.uniform(-1, 1, count).astype(np.float32))
    stars = gaussian_filter(point, 0.55) * 7.0
    tint = gaussian_filter(tint_b, 0.55) * 7.0
    rgb += np.clip(np.stack([stars - tint * 0.25, stars, stars + tint * 0.35], -1), 0, None)

    # The bright few, worked in a small window each. A spike that decays
    # exponentially has a tail across the whole sheet -- the faint grid of
    # lines the first pass drew.
    for i in np.argsort(mag)[-16:][:0]:
        cy, cx = int(sy[i]), int(sx[i])
        b = float(mag[i])
        y0, y1 = max(0, cy - 60), min(n, cy + 61)
        x0, x1 = max(0, cx - 60), min(W, cx + 61)
        dy, dx = py[y0:y1, x0:x1] - cy, px[y0:y1, x0:x1] - cx
        glow = np.exp(-(dx ** 2 + dy ** 2) / (2 * (1.8 + 3.5 * b) ** 2)) * (0.5 + 0.7 * b)
        sp = 9.0 + 20.0 * b
        spikes = (np.exp(-(dy / 0.65) ** 2) * np.exp(-(dx / sp) ** 2)
                  + np.exp(-(dx / 0.65) ** 2) * np.exp(-(dy / sp) ** 2))
        c = np.array([0.95, 0.97, 1.0], np.float32) if i % 3 else \
            np.array([1.0, 0.86, 0.70], np.float32)
        rgb[y0:y1, x0:x1] += (glow + spikes * 0.60 * b)[..., None] * c

    # The glass: darker towards its edges, one soft reflection across it.
    vig = np.clip(1.0 - ((((xx - cx0) / aspect) ** 2) * 2.4 + (yy - 0.55) ** 2) * 1.5,
                  0.35, 1.0)
    rgb *= vig[..., None]
    band = np.exp(-(((xx - yy * 0.55) - 0.22) / 0.07) ** 2) * np.clip(1.2 - yy, 0, 1)
    rgb += band[..., None] * 0.040
    rgb = np.clip(rgb, 0, 1.4)

    from PIL import Image
    out = np.zeros((n, n, 3), np.float32)
    for c in range(3):
        ch = Image.fromarray((np.clip(rgb[..., c] / 1.4, 0, 1) * 255).astype(np.uint8))
        out[..., c] = np.asarray(ch.resize((n, n), Image.LANCZOS)).astype(np.float32) / 255 * 1.4
    return out


# ----------------------------------------------------------------------
# The crest's smoked glass
# ----------------------------------------------------------------------

def crest_glass(size=256):
    """Smoked glass for the chevron, lit amber from deep inside its point."""
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32) / size
    rgb = np.zeros((size, size, 3), np.float32)
    rgb[...] = np.array([0.020, 0.014, 0.012], np.float32)
    # The lamp sits low in the point; light falls off up and out from it.
    d = np.sqrt(((xx - 0.5) / 0.55) ** 2 + ((yy - 0.92) / 0.75) ** 2)
    glow = np.exp(-d * 2.6)
    rgb += glow[..., None] * np.array([0.62, 0.24, 0.05], np.float32)
    # A faint reflection streak, and a darker rim where the glass is thickest.
    streak = np.exp(-(((xx - yy * 0.4) - 0.18) / 0.05) ** 2) * (1 - yy) * 0.08
    rgb += streak[..., None]
    rim = np.clip(np.minimum(np.minimum(xx, 1 - xx), np.minimum(yy, 1 - yy)) * 18, 0, 1)
    rgb *= (0.55 + 0.45 * rim)[..., None]
    return np.clip(rgb, 0, 1.2)


def black_glass(size=1024, aspect=1.5):
    """Sleek black glass for the dome under the arch.

    Almost all of it is black. What makes it read as glass rather than paint is
    what it reflects: a faint fall of sky from the top, one broad soft sheen
    crossing it on the diagonal with a thin sharp streak inside it, and the
    slight lift at the rim where glass meets the frame at a glancing angle.
    Laid out on the same 3:2 dome as the face's UVs -- u across, v from the
    crown (0) down to the springing (1) -- and squared up at the end.
    """
    h, w = size, int(size * aspect)
    v, u = np.mgrid[0:h, 0:w].astype(np.float32)
    u /= (w - 1); v /= (h - 1)

    base = np.array([0.012, 0.013, 0.018], np.float32)
    sky = np.array([0.085, 0.092, 0.110], np.float32)
    img = base + sky * ((1 - v) ** 2.2)[..., None]

    # The sheen: a soft band and the crisp streak riding in it.
    d = (u - 0.30) * 0.82 + (v - 0.40) * 0.57
    band = np.exp(-(d / 0.16) ** 2) * (0.35 + 0.65 * (1 - v))
    streak = np.exp(-((d + 0.045) / 0.012) ** 2) * np.clip(1.15 - v, 0, 1)
    tint = np.array([0.80, 0.84, 0.95], np.float32)
    img += tint * (0.120 * band + 0.230 * streak)[..., None]

    # Fresnel lift at the rim of the ellipse.
    e = np.sqrt(((u - 0.5) / 0.5) ** 2 + (v - 1.0) ** 2)
    rim = np.clip((e - 0.80) / 0.20, 0, 1) ** 3
    img += np.array([0.080, 0.086, 0.100], np.float32) * rim[..., None]

    # A trace of grain so the gradients don't band in 8 bits.
    rng = np.random.default_rng(3)
    img += rng.normal(0, 0.0022, img.shape).astype(np.float32)

    from PIL import Image
    out = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8))
    return np.asarray(out.resize((size, size), Image.LANCZOS)).astype(np.float32) / 255
