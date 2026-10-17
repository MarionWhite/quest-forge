#!/usr/bin/env python3
"""Photographic textures for the jukebox model -- a Wurlitzer 1015 bubbler.

The earlier pass coloured this model per vertex. Flat fills cannot produce glass,
chrome or neon at any polygon count, so everything that carries a material is a
texture now, and every one of them is *shaded* rather than drawn:

  jukebox_arch.png      the arch band: three fused neon lobes, hot cores
  jukebox_tube_l.png    left column: glowing glass, cylindrical falloff
  jukebox_tube_r.png    right column, the pink counterpart
  jukebox_cap.png       the ring-stack capitals, chrome against lit rings
  jukebox_window.png    black glass, bevelled gold scrollwork, bloom
  jukebox_display.png   slatted selector, lamps with halos
  jukebox_coil.png      ribbed chrome
  jukebox_chrome.png    chrome environment ramp for frames and trim
  jukebox_cabinet.png   lacquered walnut
  jukebox.png           32px block sprite, break particles only

Three techniques do most of the work:

* **Distance-field bevels.** A stroke is rasterised as a mask, then
  `distance_transform_edt` gives its thickness, a height is raised from that, and
  the height's gradient is a surface normal. Lambert plus a tight specular then
  lights it. That is why the gold reads as bent wire and not as a painted line.
* **Cylindrical neon profiles.** Across a tube, intensity is the depth of gas
  seen through the glass -- brightest down the middle, with the hue washing out
  to white where it is hottest, a specular streak off-centre, and the glass rim
  catching light at the silhouette.
* **Baked bloom.** 1.7.10 has no bloom of its own. A blurred copy of the
  emissive mask is added back into the sheet, so the glow exists in the albedo.
  A shader pack that does bloom then adds its own on top, which is correct.

  py -3.10 make_jukebox_textures.py [--no-install]
"""
import argparse
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import distance_transform_edt, gaussian_filter

import ornate

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
ROOT = (HERE / ".." / ".." / "..").resolve()
ENTITY = ROOT / "mods/qf-content/src/main/resources/assets/qfcontent/textures/entity"
BLOCKS = ROOT / "mods/qf-content/src/main/resources/assets/qfcontent/textures/blocks"

SS = 3          # supersample factor for anything drawn with curves


# ----------------------------------------------------------------------
# Shading kit
# ----------------------------------------------------------------------

def normals_from_height(h, strength=1.0):
    """Surface normals from a height field, as three float arrays."""
    gy, gx = np.gradient(h.astype(np.float32))
    nx, ny = -gx * strength, -gy * strength
    nz = np.ones_like(nx)
    inv = 1.0 / np.sqrt(nx * nx + ny * ny + nz * nz)
    return nx * inv, ny * inv, nz * inv


def lit(nx, ny, nz, base, light=(-0.45, -0.62, 0.65),
        ambient=0.34, spec=0.85, shininess=48.0, spec_tint=(1, 1, 1)):
    """Lambert plus Blinn-Phong over a base colour. base is HxWx3 float 0..1."""
    L = np.array(light, np.float32)
    L /= np.linalg.norm(L)
    ndl = np.clip(nx * L[0] + ny * L[1] + nz * L[2], 0, 1)

    # Half vector against a viewer straight on.
    hx, hy, hz = L[0], L[1], L[2] + 1.0
    inv = 1.0 / math.sqrt(hx * hx + hy * hy + hz * hz)
    hx, hy, hz = hx * inv, hy * inv, hz * inv
    ndh = np.clip(nx * hx + ny * hy + nz * hz, 0, 1)
    s = (ndh ** shininess) * spec

    out = base * (ambient + (1.0 - ambient) * ndl)[..., None]
    out = out + s[..., None] * np.array(spec_tint, np.float32)
    return out


def bevel(mask, radius, strength=2.6):
    """A rounded height for a drawn stroke, from its distance field."""
    d = distance_transform_edt(mask)
    d = np.clip(d / max(radius, 1e-3), 0, 1)
    return np.sin(d * math.pi * 0.5) * strength


def bloom(rgb, emissive, radius, gain=0.9):
    """Bakes a glow into the sheet: 1.7.10 has none of its own."""
    g = np.zeros_like(rgb)
    for c in range(3):
        g[..., c] = gaussian_filter(emissive[..., c], radius)
    return rgb + g * gain


def ramp(stops, n):
    """A colour ramp of n rows from (position, rgb) stops in 0..1."""
    pos = np.array([p for p, _ in stops], np.float32)
    cols = np.array([c for _, c in stops], np.float32)
    x = np.linspace(0, 1, n, dtype=np.float32)
    out = np.zeros((n, 3), np.float32)
    for c in range(3):
        out[:, c] = np.interp(x, pos, cols[:, c])
    return out


def noise(shape, seed, scale, amount):
    rng = np.random.default_rng(seed)
    small = rng.random((max(2, shape[0] // scale), max(2, shape[1] // scale)))
    im = Image.fromarray((small * 255).astype(np.uint8), "L").resize(
        (shape[1], shape[0]), Image.BICUBIC)
    a = np.asarray(im).astype(np.float32) / 255.0
    return (gaussian_filter(a, 1.0) - 0.5) * amount


def save(a, path):
    if a.shape[2] == 4:
        Image.fromarray(np.clip(a * 255.0, 0, 255).astype(np.uint8), "RGBA").save(path)
    else:
        Image.fromarray(np.clip(a * 255.0, 0, 255).astype(np.uint8), "RGB").save(path)


# ----------------------------------------------------------------------
# Neon
# ----------------------------------------------------------------------

def neon_cross(n, lobes=1, glass=True):
    """Intensity across a glowing tube, and where the glass catches light.

    Returns (depth, spec, rim). depth is how much gas the eye looks through --
    a chord through a cylinder -- which is what makes the middle of a neon tube
    read hotter and less saturated than its edges."""
    u = np.linspace(0, 1, n, dtype=np.float32)
    depth = np.zeros(n, np.float32)
    spec = np.zeros(n, np.float32)
    rim = np.zeros(n, np.float32)
    for i in range(lobes):
        a, b = i / lobes, (i + 1) / lobes
        m = (u >= a) & (u <= b)
        if not m.any():
            continue
        t = (u[m] - a) / (b - a)                 # 0..1 across this lobe
        c = 1.0 - (2.0 * t - 1.0) ** 2           # chord through the cylinder
        depth[m] = np.sqrt(np.clip(c, 0, 1))
        if glass:
            spec[m] = np.exp(-((t - 0.33) / 0.075) ** 2) * 0.95
            rim[m] = np.exp(-((t - 0.03) / 0.05) ** 2) * 0.5 \
                   + np.exp(-((t - 0.97) / 0.05) ** 2) * 0.5
    return depth, spec, rim


def neon_sheet(w, h, stops, lobes=1, along="v", outline=0.055,
               white=0.55, spec_gain=0.45, floor=0.52):
    """A glowing tube (or fused row of them) as a texture.

    `along` says which axis carries the colour ramp; the other is across the
    tube. The hot middle washes towards white, because that is what a neon tube
    does and it is most of why one looks like light rather than paint."""
    if along == "v":
        cols = ramp(stops, h)[:, None, :]        # h x 1 x 3
        depth, spec, rim = neon_cross(w, lobes)
        depth = depth[None, :, None]
        spec = spec[None, :, None]
        rim = rim[None, :, None]
    else:
        cols = ramp(stops, w)[None, :, :]        # 1 x w x 3
        depth, spec, rim = neon_cross(h, lobes)
        depth = depth[:, None, None]
        spec = spec[:, None, None]
        rim = rim[:, None, None]

    hot = np.clip(depth, 0, 1) ** 1.35
    # Colour carries the tube. `white` is how much the deepest part of the gas
    # column washes out, and it wants to be small: at 0.6 the columns came back
    # looking like fluorescent strip lights with a rainbow painted on the rims,
    # because a tube seen head-on is nearly all core.
    base = cols * (floor + (1.0 - floor) * 1.35 * hot) + (hot ** 14) * white
    base = base + spec * spec_gain + rim * cols * 0.55

    # A dark seam at the very edge of each lobe, the glass against the dark.
    if along == "v":
        u = np.linspace(0, 1, w, dtype=np.float32)[None, :, None]
    else:
        u = np.linspace(0, 1, h, dtype=np.float32)[:, None, None]
    seam = np.ones_like(u)
    for i in range(lobes + 1):
        seam = np.minimum(seam, 1.0 - np.exp(
            -((u - i / lobes) / outline) ** 2) * 0.92)
    base = base * seam

    rgb = np.broadcast_to(base, (h, w, 3)).astype(np.float32).copy()
    rgb += noise((h, w), 5, 6, 0.035)[..., None]
    emissive = np.clip(rgb - 0.55, 0, None)
    return np.clip(bloom(rgb, emissive, max(w, h) * 0.012, 0.40), 0, 4)


ARCH_STOPS = [
    (0.00, (0.62, 0.03, 0.07)), (0.10, (0.95, 0.10, 0.08)),
    (0.24, (1.00, 0.34, 0.04)), (0.38, (1.00, 0.58, 0.07)),
    (0.50, (1.00, 0.80, 0.24)), (0.60, (1.00, 0.66, 0.52)),
    (0.72, (1.00, 0.32, 0.60)), (0.86, (0.88, 0.09, 0.52)),
    (1.00, (0.45, 0.06, 0.55)),
]

TUBE_L_STOPS = [
    (0.00, (1.00, 0.48, 0.10)), (0.22, (1.00, 0.78, 0.20)),
    (0.44, (0.55, 0.92, 0.42)), (0.68, (0.20, 0.80, 0.95)),
    (1.00, (0.18, 0.48, 0.95)),
]
TUBE_R_STOPS = [
    (0.00, (1.00, 0.40, 0.76)), (0.24, (0.96, 0.16, 0.60)),
    (0.48, (1.00, 0.70, 0.86)), (0.72, (0.52, 0.34, 0.95)),
    (1.00, (0.24, 0.66, 0.96)),
]


def make_arch(w=1024, h=192):
    """One tube. The arch is three swept tubes now, and each wears this sheet:
    U along the arc for the colour, V around the circumference for the glass."""
    return neon_sheet(w, h, ARCH_STOPS, lobes=1, along="h", outline=0.045,
                      white=0.20, spec_gain=0.32, floor=0.70)


def make_tube(stops, w=256, h=1024):
    # A column is seen head-on and fills a lot of the cabinet, so it keeps far
    # more of its hue than the arch does.
    return neon_sheet(w, h, stops, lobes=1, along="v", outline=0.050,
                      white=0.16, spec_gain=0.30, floor=0.72)


# ----------------------------------------------------------------------
# Chrome
# ----------------------------------------------------------------------

def chrome_ramp(n):
    """A chrome environment: dark ground, a hot horizon, bright sky."""
    x = np.linspace(0, 1, n, dtype=np.float32)
    sky = 0.55 + 0.42 * np.clip(1.0 - np.abs(x - 0.22) / 0.35, 0, 1)
    ground = 0.30 * np.clip(1.0 - np.abs(x - 0.86) / 0.22, 0, 1)
    horizon = 1.05 * np.exp(-((x - 0.46) / 0.045) ** 2)
    band = np.clip(sky + ground + horizon, 0.05, 1.6)
    tint = np.array([0.94, 0.97, 1.03], np.float32)
    return band[:, None] * tint[None, :]


def make_chrome(size=512):
    a = np.repeat(chrome_ramp(size)[None, :, :], size, axis=0)
    a += noise((size, size), 9, 2, 0.045)[..., None]        # brushing
    return np.clip(a, 0, 2)


def make_coil(w=256, h=512, ribs=13):
    """Ribbed chrome: the environment ramp wrapped round each rib."""
    v = np.linspace(0, 1, h, dtype=np.float32)
    phase = (v * ribs) % 1.0
    # Each rib is a torus in profile: a full sweep of the ramp per rib.
    idx = np.clip((phase * (w - 1)).astype(np.int32), 0, w - 1)
    ramp_ = chrome_ramp(w)
    along = ramp_[idx]                                       # h x 3
    across = chrome_ramp(w)                                  # w x 3
    a = (along[:, None, :] * 0.34 + across[None, :, :] * 0.58)
    a += noise((h, w), 13, 2, 0.04)[..., None]
    return np.clip(a, 0, 2)


def make_cap(w=256, h=256, rings=7):
    """The capitals: chrome rings alternating with lit ones."""
    across = chrome_ramp(w)
    a = np.zeros((h, w, 3), np.float32)
    glow = ramp([(0.0, (1.0, 0.22, 0.05)), (0.5, (1.0, 0.55, 0.10)),
                 (1.0, (1.0, 0.20, 0.34))], rings)
    depth, spec, rim = neon_cross(w, 1)
    for i in range(rings):
        y0, y1 = int(h * i / rings), int(h * (i + 1) / rings)
        if i % 2 == 0:
            hot = depth ** 1.3
            band = glow[i][None, :] * (0.30 + 0.95 * hot[:, None]) \
                 + (hot ** 3)[:, None] * 0.8 + spec[:, None] * 0.7
        else:
            band = across * 0.74
        # A dark seam between rings, so they read as separate pieces.
        rows = y1 - y0
        edge = np.ones((rows, 1), np.float32)
        edge[:2] = 0.25
        edge[-2:] = 0.25
        a[y0:y1] = band[None, :, :] * edge[:, :, None]
    a += noise((h, w), 21, 3, 0.03)[..., None]
    emissive = np.clip(a - 0.6, 0, None)
    return np.clip(bloom(a, emissive, 5, 0.5), 0, 3)


# ----------------------------------------------------------------------
# Drawn detail: the window, the display
# ----------------------------------------------------------------------

def bez(p0, p1, p2, p3, steps=140):
    out = []
    for i in range(steps + 1):
        t = i / steps
        u = 1.0 - t
        out.append((u ** 3 * p0[0] + 3 * u * u * t * p1[0]
                    + 3 * u * t * t * p2[0] + t ** 3 * p3[0],
                    u ** 3 * p0[1] + 3 * u * u * t * p1[1]
                    + 3 * u * t * t * p2[1] + t ** 3 * p3[1]))
    return out


def spiral(cx, cy, r0, turns, mirror=False, steps=200):
    pts = []
    for i in range(steps + 1):
        f = i / steps
        a = f * turns * 2 * math.pi
        r = r0 * (1.0 - 0.70 * f)
        dx = math.cos(a) * r
        pts.append((cx + (-dx if mirror else dx), cy + math.sin(a) * r))
    return pts


def scroll_strands(w, h):
    """The centre ornament as a list of strands, drawn in order.

    Returned separately rather than as one mask so the caller can lay them down
    one at a time with a shadow under each. That is what reads as interlace:
    where two strands cross, the later one is plainly *over* the earlier. Drawn
    as a single silhouette they merge into a flat web, which is what the last
    version did and why it looked like bent wire rather than woven ribbon.
    """
    cx = w / 2.0
    heavy = int(w * 0.040)
    light = int(w * 0.028)
    fine = int(w * 0.019)
    out = []

    def strand(pts, width, mirror=True):
        im = Image.new("L", (w, h), 0)
        d = ImageDraw.Draw(im)
        d.line(pts, fill=255, width=width, joint="curve")
        if mirror:
            d.line([(2 * cx - x, y) for x, y in pts], fill=255, width=width,
                   joint="curve")
        out.append(np.asarray(im).astype(np.float32) / 255.0)

    def blob(shapes):
        im = Image.new("L", (w, h), 0)
        d = ImageDraw.Draw(im)
        for x, y, r in shapes:
            d.ellipse([x - r, y - r, x + r, y + r], fill=255)
        out.append(np.asarray(im).astype(np.float32) / 255.0)

    # The shield, and an inner echo of it.
    strand(bez((cx, h * 0.070), (cx - w * 0.40, h * 0.145),
               (cx - w * 0.46, h * 0.560), (cx, h * 0.860)), heavy)
    strand(bez((cx, h * 0.130), (cx - w * 0.27, h * 0.200),
               (cx - w * 0.32, h * 0.540), (cx, h * 0.780)), light)

    # Two long ribbons that weave across the spine three times each. These are
    # what make it read as interlace rather than as a frame with things inside.
    strand(bez((cx - w * 0.20, h * 0.205), (cx + w * 0.26, h * 0.330),
               (cx - w * 0.26, h * 0.520), (cx + w * 0.19, h * 0.680)), light)
    strand(bez((cx - w * 0.14, h * 0.320), (cx + w * 0.20, h * 0.440),
               (cx - w * 0.20, h * 0.600), (cx + w * 0.12, h * 0.745)), fine)

    # C-scrolls turned in under the shoulders.
    strand(bez((cx - w * 0.055, h * 0.240), (cx - w * 0.30, h * 0.230),
               (cx - w * 0.315, h * 0.450), (cx - w * 0.135, h * 0.450)), light)

    # Spirals at the shoulders, waist and foot.
    for mirror in (False, True):
        sgn = -1 if mirror else 1
        strand(spiral(cx + w * 0.295 * sgn, h * 0.295, w * 0.072, 1.35, mirror),
               fine, mirror=False)
        strand(spiral(cx + w * 0.170 * sgn, h * 0.450, w * 0.055, 1.2, mirror),
               fine, mirror=False)
        strand(spiral(cx + w * 0.100 * sgn, h * 0.660, w * 0.048, 1.15, not mirror),
               fine, mirror=False)

    # The spine, its lozenge, the pendant and the crown.
    strand([(cx, h * 0.300), (cx, h * 0.600)], light, mirror=False)
    lz = Image.new("L", (w, h), 0)
    dl = ImageDraw.Draw(lz)
    dl.polygon([(cx, h * 0.395), (cx + w * 0.070, h * 0.475),
                (cx, h * 0.555), (cx - w * 0.070, h * 0.475)], fill=255)
    dl.polygon([(cx, h * 0.432), (cx + w * 0.038, h * 0.475),
                (cx, h * 0.518), (cx - w * 0.038, h * 0.475)], fill=0)
    out.append(np.asarray(lz).astype(np.float32) / 255.0)

    strand([(cx, h * 0.860), (cx, h * 0.928)], light, mirror=False)
    blob([(cx, h * 0.948, w * 0.040), (cx, h * 0.058, w * 0.036),
          (cx + w * 0.135, h * 0.450, w * 0.024),
          (cx - w * 0.135, h * 0.450, w * 0.024)])
    return out


def make_window(w=512, h=1024):
    strands = [np.asarray(Image.fromarray((m * 255).astype(np.uint8), "L")
                          .resize((w, h), Image.LANCZOS)).astype(np.float32) / 255.0
               for m in scroll_strands(w * SS, h * SS)]
    mask = np.zeros((h, w), np.float32)
    for m in strands:
        mask = np.maximum(mask, m)
    solid = mask > 0.5

    # Black glass, with a faint vertical wash so it is not a dead void.
    y = np.linspace(0, 1, h, dtype=np.float32)[:, None]
    glass = np.zeros((h, w, 3), np.float32)
    glass[...] = np.array([0.030, 0.026, 0.034], np.float32)
    glass += (np.clip(1.0 - np.abs(y - 0.42) / 0.55, 0, 1) * 0.055)[..., None]
    glass += noise((h, w), 3, 10, 0.018)[..., None]

    # Grille cloth behind the gold. A real cabinet has fabric back here and it
    # catches just enough light to stop the window reading as a hole.
    weave = np.arange(h)[:, None] % 6 < 3
    weave = weave ^ (np.arange(w)[None, :] % 6 < 3)
    glass += weave[..., None].astype(np.float32) * 0.022

    # The gold, bevelled off its own distance field.
    height = bevel(solid, radius=w * 0.020, strength=3.0)
    nx, ny, nz = normals_from_height(gaussian_filter(height, 0.7), strength=2.2)
    gold = np.zeros((h, w, 3), np.float32)
    gold[...] = np.array([0.78, 0.52, 0.13], np.float32)
    gold_lit = lit(nx, ny, nz, gold, ambient=0.30, spec=1.15, shininess=34.0,
                   spec_tint=(1.0, 0.93, 0.72))

    # Laid down in order, each strand shadowed onto whatever is already there,
    # so crossings read as over and under instead of as a merged web.
    rgb = glass.copy()
    for st in strands:
        drop = np.clip(gaussian_filter(st, w * 0.010) - st, 0, 1)
        rgb *= (1.0 - 0.60 * drop)[..., None]
        sm = st[..., None]
        rgb = rgb * (1.0 - sm) + gold_lit * sm
    m = mask[..., None]

    # Contact shadow under the wire, and a warm glow around it.
    shade = gaussian_filter(mask, w * 0.012)
    rgb *= (1.0 - 0.55 * np.clip(shade - mask, 0, 1))[..., None]
    emissive = (gold_lit * m) * 0.5
    rgb = bloom(rgb, emissive, w * 0.016, 0.35)
    return np.clip(rgb, 0, 2)


def make_strip(w=512, h=128):
    """The title strip: amber glass in a chrome surround, with song titles.

    It was a flat yellow rectangle with three bars on it. A real one is lit from
    behind, framed in metal, and carries two columns of little printed titles.
    """
    a = np.zeros((h, w, 3), np.float32)

    # The glass, brightest behind the middle where the lamp is.
    x = np.linspace(0, 1, w, dtype=np.float32)[None, :, None]
    y = np.linspace(0, 1, h, dtype=np.float32)[:, None, None]
    glow = np.clip(1.0 - np.abs(y - 0.45) * 1.5, 0, 1)
    warm = ramp([(0.0, (0.92, 0.62, 0.10)), (0.5, (1.00, 0.86, 0.34)),
                 (1.0, (0.86, 0.54, 0.08))], w)[None, :, :]
    a[...] = warm * (0.55 + 0.60 * glow)

    # Two columns of titles, as a real strip has.
    mask = Image.new("L", (w * SS, h * SS), 0)
    d = ImageDraw.Draw(mask)
    rng = np.random.default_rng(77)
    for col in range(2):
        x0 = (0.09 + 0.46 * col) * w * SS
        for row in range(4):
            yy = (0.20 + 0.19 * row) * h * SS
            wide = (0.20 + 0.16 * rng.random()) * w * SS
            d.rectangle([x0, yy, x0 + wide, yy + h * SS * 0.055], fill=255)
            d.rectangle([x0, yy + h * SS * 0.085,
                         x0 + wide * 0.62, yy + h * SS * 0.125], fill=170)
    m = np.asarray(mask.resize((w, h), Image.LANCZOS)).astype(np.float32) / 255.0
    a = a * (1.0 - m[..., None] * 0.88)

    # The chrome frame around it.
    frame = np.zeros((h, w), np.float32)
    b = int(h * 0.10)
    frame[:b, :] = 1.0
    frame[-b:, :] = 1.0
    frame[:, :b] = 1.0
    frame[:, -b:] = 1.0
    height = bevel(frame > 0.5, radius=b * 0.9, strength=2.4)
    nx, ny, nz = normals_from_height(gaussian_filter(height, 0.6), strength=2.0)
    metal = np.zeros((h, w, 3), np.float32)
    metal[...] = np.array([0.70, 0.74, 0.81], np.float32)
    chrome_ = lit(nx, ny, nz, metal, ambient=0.32, spec=1.1, shininess=44.0)
    a = a * (1.0 - frame[..., None]) + chrome_ * frame[..., None]

    a += noise((h, w), 83, 3, 0.02)[..., None]
    return np.clip(bloom(a, np.clip(a - 0.7, 0, None), 6, 0.35), 0, 3)


def make_display(w=512, h=512, slats=13):
    """The selector: coloured lamps burning behind a rank of chrome bars.

    Previously the lamps were dots sitting above the bars, which is not what the
    reference shows and not how the machine works -- the light is *behind* the
    grille, and the bars cut it into stripes.
    """
    a = np.zeros((h, w, 3), np.float32)
    a[...] = np.array([0.030, 0.028, 0.034], np.float32)

    # The lamps, as broad vertical washes behind everything else.
    cols = [(1.0, 0.14, 0.10), (1.0, 0.62, 0.10), (0.98, 0.92, 0.22),
            (0.26, 0.92, 0.34), (0.18, 0.62, 1.00), (0.72, 0.34, 1.00),
            (1.0, 0.30, 0.80)]
    xx = np.linspace(0, 1, w, dtype=np.float32)[None, :, None]
    yy = np.linspace(0, 1, h, dtype=np.float32)[:, None, None]
    fade = np.clip(1.0 - (yy - 0.16) / 0.95, 0, 1)
    for i, c in enumerate(cols):
        cx = (i + 0.5) / len(cols)
        band = np.exp(-((xx - cx) / 0.055) ** 2)
        a = a + band * fade * np.array(c, np.float32) * 0.85

    # The bars in front of them.
    mask = Image.new("L", (w * SS, h * SS), 0)
    d = ImageDraw.Draw(mask)
    for i in range(slats):
        x0 = (i + 0.20) / slats * w * SS
        d.rectangle([x0, h * SS * 0.10, x0 + w * SS / slats * 0.48,
                     h * SS * 0.97], fill=255)
    m = np.asarray(mask.resize((w, h), Image.LANCZOS)).astype(np.float32) / 255.0

    height = bevel(m > 0.5, radius=w * 0.008, strength=2.2)
    nx, ny, nz = normals_from_height(gaussian_filter(height, 0.5), strength=2.2)
    metal = np.zeros((h, w, 3), np.float32)
    metal[...] = np.array([0.60, 0.64, 0.72], np.float32)
    bars = lit(nx, ny, nz, metal, ambient=0.26, spec=1.15, shininess=46.0)
    a = a * (1.0 - m[..., None]) + bars * m[..., None]

    # A row of colour chips along the top, above the grille.
    chip = np.zeros((h, w, 3), np.float32)
    gy, gx = np.mgrid[0:h, 0:w].astype(np.float32)
    for i, c in enumerate(cols):
        cx = (i + 0.5) / len(cols) * w
        cy = h * 0.055
        r = w * 0.022
        core = np.clip(1.0 - np.maximum(np.abs(gx - cx), np.abs(gy - cy)) / r, 0, 1)
        chip += (core ** 0.4)[..., None] * np.array(c, np.float32) * 1.2
        chip += np.exp(-(((gx - cx) ** 2 + (gy - cy) ** 2) / (2 * (r * 1.6) ** 2))
                       )[..., None] * np.array(c, np.float32) * 0.35
    a = a + chip
    a += noise((h, w), 31, 4, 0.02)[..., None]
    return np.clip(bloom(a, np.clip(a - 0.55, 0, None), 8, 0.45), 0, 3)


def make_shoulder(w=512, h=256):
    """Marquetry for the cabinet's shoulder, mapped in polar.

    The shoulder is drawn as a fan from the crown, so a sheet laid on it in
    ordinary coordinates comes out as radial streaks -- combed-looking wood that
    reads as a rendering fault rather than as a surface. Here U is the angle
    round the arch and V is the distance out from the centre, so bands in this
    sheet become concentric arcs: a sunburst veneer with inlay lines between the
    courses, which is what a cabinet of this age actually has up there.
    """
    a = np.zeros((h, w, 3), np.float32)
    rad = np.linspace(0, 1, h, dtype=np.float32)[:, None, None]
    ang = np.linspace(0, 1, w, dtype=np.float32)[None, :, None]

    light = np.array([0.52, 0.30, 0.17], np.float32)
    dark = np.array([0.26, 0.135, 0.075], np.float32)

    # Courses of veneer, each a shade different from its neighbour.
    course = np.floor(rad * 2.0)
    mix = 0.5 + 0.5 * np.sin(course * 2.1)
    a[...] = dark + (light - dark) * mix

    # Rays: the leaves of the sunburst, alternating with the grain turned.
    rays = np.sin(ang * np.pi * 14.0)
    a *= (1.0 + 0.16 * rays)

    # Inlay lines between the courses, and one round the outer edge.
    edge = np.abs((rad * 2.0) % 1.0 - 0.5) * 2.0
    a *= (0.42 + 0.58 * np.clip(edge * 3.2, 0, 1))
    a *= (1.0 - 0.45 * np.clip(1.0 - np.abs(rad - 0.97) * 40.0, 0, 1))

    # Grain along each ray, and a sheen towards the crown.
    a += gaussian_filter(noise((h, w), 61, 2, 0.16), (2.5, 0.4))[..., None]
    a += (0.10 * np.exp(-((rad - 0.35) / 0.28) ** 2))
    return np.clip(a, 0, 1.2)


def make_chamber(w=512, h=512):
    """The inside of the mechanism well: dark, and deeper towards the top.

    A flat black back wall makes the record look pasted onto a hole. A gradient
    with a soft pool of light low down gives the well a floor for the disc to sit
    above.
    """
    a = np.zeros((h, w, 3), np.float32)
    a[...] = np.array([0.018, 0.019, 0.026], np.float32)
    y = np.linspace(0, 1, h, dtype=np.float32)[:, None, None]
    x = np.linspace(0, 1, w, dtype=np.float32)[None, :, None]
    a *= (0.55 + 0.75 * y)
    pool = np.exp(-(((x - 0.5) / 0.42) ** 2 + ((y - 0.82) / 0.30) ** 2))
    a = a + pool * np.array([0.085, 0.090, 0.105], np.float32)
    a += noise((h, w), 97, 6, 0.012)[..., None]
    return np.clip(a, 0, 1)


def make_glass(size=512):
    """Glass over the mechanism, as an alpha *cut-out* rather than a blend.

    A deferred pack cannot blend, so a translucent pane comes out opaque and
    hides what it covers -- the record case learned that expensively. What does
    survive is an alpha test: pixels are either there or they are not. So the
    pane is nothing but its highlights, two diagonal streaks and a bright edge,
    and everything between them is cut away entirely.
    """
    a = np.zeros((size, size, 4), np.float32)
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32) / size

    streak = np.zeros((size, size), np.float32)
    # Thin. Two broad bars of white across the glass hide the record behind them,
    # which rather defeats putting a window there.
    for cx, wid, strength in ((0.30, 0.020, 1.0), (0.44, 0.009, 0.75)):
        d = (xx - yy * 0.55) - cx
        streak = np.maximum(streak, np.exp(-(d / wid) ** 2) * strength)
    # Only the top two thirds catch the sky.
    streak *= np.clip(1.25 - yy, 0, 1)

    edge = np.zeros((size, size), np.float32)
    b = max(2, int(size * 0.018))
    edge[:b, :] = edge[-b:, :] = edge[:, :b] = edge[:, -b:] = 1.0
    edge = gaussian_filter(edge, size * 0.004)

    lum = np.clip(streak * 0.85 + edge * 0.55, 0, 1)
    a[..., 0] = 0.86
    a[..., 1] = 0.92
    a[..., 2] = 1.00
    a[..., 3] = (lum > 0.42).astype(np.float32)      # the cut
    a[..., :3] *= np.clip(lum, 0, 1)[..., None] * 1.15
    return a


def make_front(w=512, h=512):
    """The cabinet's front panel, with the tubes' light spilling onto it.

    A neon tube standing an inch off a lacquered panel throws colour onto it.
    Nothing in a fixed-function pipeline will do that for us -- there is no light
    here to bounce -- so it is painted in: a soft wash up each side in the hue of
    the column that stands there, falling off towards the middle.
    """
    a = ornate.burl(h, w, seed=17, eyes=40)

    x = np.linspace(0, 1, w, dtype=np.float32)[None, :, None]
    y = np.linspace(0, 1, h, dtype=np.float32)[:, None, None]
    left = np.exp(-((x - 0.17) / 0.13) ** 2)
    right = np.exp(-((x - 0.83) / 0.13) ** 2)
    height = np.clip(0.35 + 0.65 * y, 0, 1)

    l_col = ramp([(0.0, (0.24, 0.66, 0.96)), (0.5, (1.0, 0.40, 0.76)),
                  (1.0, (1.0, 0.46, 0.20))], h)[:, None, :]
    r_col = ramp([(0.0, (0.20, 0.80, 0.95)), (0.5, (0.55, 0.92, 0.42)),
                  (1.0, (1.0, 0.78, 0.20))], h)[:, None, :]
    a = a + left * height * l_col * 0.45 + right * height * r_col * 0.45
    return np.clip(ornate.lacquer(a, 0.8), 0, 2)


def make_hardware(size=256):
    """Selector buttons and the coin plate, bevelled off their own masks."""
    a = np.zeros((size, size, 3), np.float32)
    a[...] = np.array([0.055, 0.050, 0.058], np.float32)

    mask = Image.new("L", (size * SS, size * SS), 0)
    d = ImageDraw.Draw(mask)
    S = size * SS
    for row in range(2):
        for i in range(5):
            cx = S * (0.055 + 0.088 * i)
            cy = S * (0.30 + 0.34 * row)
            r = S * 0.030
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=255)
    d.rounded_rectangle([S * 0.56, S * 0.18, S * 0.94, S * 0.82],
                        radius=S * 0.04, fill=255)
    m = np.asarray(mask.resize((size, size), Image.LANCZOS)).astype(np.float32) / 255.0

    height = bevel(m > 0.5, radius=size * 0.020, strength=2.8)
    nx, ny, nz = normals_from_height(gaussian_filter(height, 0.7), strength=2.2)
    metal = np.zeros((size, size, 3), np.float32)
    metal[...] = np.array([0.66, 0.69, 0.76], np.float32)
    plate = lit(nx, ny, nz, metal, ambient=0.30, spec=1.1, shininess=44.0)
    a = a * (1.0 - m[..., None]) + plate * m[..., None]

    slot = Image.new("L", (size, size), 0)
    ds = ImageDraw.Draw(slot)
    ds.rounded_rectangle([size * 0.72, size * 0.30, size * 0.78, size * 0.70],
                         radius=size * 0.02, fill=255)
    sm = np.asarray(slot).astype(np.float32) / 255.0
    a = a * (1.0 - sm[..., None]) + np.array([0.02, 0.02, 0.025],
                                             np.float32) * sm[..., None]
    a += noise((size, size), 61, 3, 0.02)[..., None]
    return np.clip(a, 0, 2)


def make_env(size=256):
    """A sphere map for chrome: what the metal has to look at.

    Fixed-function OpenGL generates texture coordinates from the eye-space
    normal, so what the chrome reflects changes as you walk round it.
    """
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32)
    u = (xx - size / 2) / (size / 2)
    v = (yy - size / 2) / (size / 2)
    r2 = u * u + v * v
    inside = r2 <= 1.0
    nz = np.sqrt(np.clip(1.0 - r2, 0, 1))
    dir_y = np.clip(2.0 * nz * v, -1, 1)

    sky_top = np.array([0.62, 0.74, 0.95], np.float32)
    sky_low = np.array([0.86, 0.90, 0.97], np.float32)
    ground = np.array([0.16, 0.15, 0.14], np.float32)
    ground_far = np.array([0.34, 0.32, 0.30], np.float32)

    t = np.clip((-dir_y + 1.0) * 0.5, 0, 1)[..., None]
    sky = sky_low * (1 - t) + sky_top * t
    t2 = np.clip((dir_y + 1.0) * 0.5, 0, 1)[..., None]
    gnd = ground_far * (1 - t2) + ground * t2

    horizon = np.exp(-((dir_y) / 0.06) ** 2)[..., None]
    a = np.where((dir_y < 0)[..., None], sky, gnd) + horizon * 0.45

    sun = np.exp(-(((u + 0.42) ** 2 + (v + 0.46) ** 2) / 0.010))
    a = a + sun[..., None] * np.array([1.6, 1.5, 1.35], np.float32)
    a = a + gaussian_filter(sun, 14)[..., None] * 0.55
    a = a * inside[..., None]
    a += noise((size, size), 55, 3, 0.02)[..., None]
    return np.clip(a, 0, 2)


def make_cabinet(size=512):
    """Figured burl walnut for the carcass, tiling.

    No lacquer sheen is baked in: this sheet repeats across the body, and a
    highlight painted into a repeating sheet repeats with it. The fall of light
    down the cabinet comes from the geometry's own shading instead.
    """
    return ornate.burl(size, size, seed=7)


def side_panel():
    """The veneered panel let into each side of the body, at its true shape.

    The opening on the side is 2.4 times as tall as it is wide. The panel is
    laid out at that proportion -- so the oval reserve and the fans come out
    round -- and then squared to a power-of-two sheet, which the quad stretches
    back again.
    """
    a = ornate.panel(1229, 512, seed=3)
    return resize(a, 512, 1024)


def back_panel():
    return resize(ornate.panel(917, 512, seed=5), 512, 1024)


def resize(a, w, h):
    out = np.zeros((h, w, a.shape[2]), np.float32)
    top = float(max(a.max(), 1.0))
    for c in range(a.shape[2]):
        ch = Image.fromarray((np.clip(a[..., c] / top, 0, 1) * 255).astype(np.uint8))
        out[..., c] = np.asarray(ch.resize((w, h), Image.LANCZOS)) / 255.0 * top
    return out


def make_particle(size=32):
    a = np.zeros((size, size, 3), np.float32)
    a[...] = np.array([0.11, 0.065, 0.045], np.float32)
    a += noise((size, size), 29, 3, 0.10)[..., None]
    a[size // 3: size // 3 + 3] = np.array([0.92, 0.28, 0.14], np.float32)
    a[size // 3 + 3: size // 3 + 5] = np.array([1.0, 0.70, 0.22], np.float32)
    return np.clip(a, 0, 1)


SHEETS = {
    "jukebox_arch": make_arch,
    "jukebox_tube_l": lambda: make_tube(TUBE_L_STOPS),
    "jukebox_tube_r": lambda: make_tube(TUBE_R_STOPS),
    "jukebox_cap": make_cap,
    "jukebox_window": make_window,
    "jukebox_display": make_display,
    "jukebox_strip": make_strip,
    "jukebox_chamber": make_chamber,
    # The nebula is shelved in saved/nebula-dome; ornate.nebula(1024) brings it back.
    "jukebox_shoulder": lambda: ornate.black_glass(1024),
    "jukebox_panel_side": side_panel,
    "jukebox_panel_back": back_panel,
    "jukebox_glass": make_glass,
    "jukebox_coil": make_coil,
    "jukebox_chrome": make_chrome,
    "jukebox_env": make_env,
    "jukebox_front": make_front,
    "jukebox_hardware": make_hardware,
    "jukebox_cabinet": make_cabinet,
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-install", action="store_true")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    made = {}
    for name, fn in SHEETS.items():
        made[name] = fn()
        save(made[name], OUT / (name + ".png"))
        print("  %-22s %s" % (name, made[name].shape))
    particle = make_particle()
    save(particle, OUT / "jukebox.png")

    if not args.no_install:
        for name, a in made.items():
            save(a, ENTITY / (name + ".png"))
        save(particle, BLOCKS / "jukebox.png")
        print("installed ->", ENTITY)


if __name__ == "__main__":
    main()
