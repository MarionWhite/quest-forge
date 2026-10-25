"""Illustrated fantasy-map render of a continent plan (the layers tools/world/plan.py writes).

    py -3.10 tools/world/illustrate.py PLANDIR OUT.png [--size 4096] [--no-labels] [--crop OUT_CROP.png]

Painterly sea with depth shading, coastal halo and shallow-water bands; land as soft biome washes
(real biome families, muted palette) textured with noise and multiplied by hillshade; mountains
drawn with hachure strokes and ridge crests; forests as tree stipple; rivers and lakes in clean
blue; parchment frame and compass rose. Labels: landmarks (icons + serif names), spawns (stars),
and the largest biome patches by their real names. --no-labels gives the clean spawn-picker art.
"""
import argparse
import json
import math
import os
import re
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from plan import SEA, OCEAN, DEEP_OCEAN, RIVER, BEACH, STONE_BEACH, biome_names  # noqa: E402

FONT_DIR = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")

# Biome family -> (colour, forest stipple density 0..1). First match wins; names as biome_names() gives them.
FAMILIES = [
    (r"dry river", (196, 172, 120), 0),
    (r"ice|glacier|polar|arctic|frozen|snow|frost", (228, 233, 234), 0),
    (r"tundra", (196, 198, 176), 0.05),
    (r"volcan|wasteland|ash|scorched|burnt", (92, 80, 72), 0),
    (r"alps|crag|mountain|cliff|extreme|peak|highland", (156, 146, 122), 0.1),
    (r"mesa|badland|canyon", (196, 136, 92), 0),
    (r"desert|dune|outback|xeric|oasis", (208, 184, 128), 0),
    (r"savanna|steppe|brush|scrub|chaparral|prairie", (186, 172, 108), 0.08),
    (r"swamp|bog|fen|marsh|bayou|wetland|mangrove|quagmire|moor|sludge", (112, 116, 72), 0.45),
    (r"jungle|tropic|rainforest|bamboo", (74, 108, 50), 1.0),
    (r"redwood|taiga|conifer|boreal|spruce|pine|fir", (76, 98, 70), 0.95),
    (r"ominous|dead|mystic|spectral|haunt|corrupt|twilight", (96, 92, 86), 0.6),
    (r"cherry|lavender|flower|orchard|garden|blossom", (166, 156, 112), 0.4),
    (r"forest|wood|grove|maple|thicket|roofed|birch|oak|deciduous|seasonal", (96, 118, 62), 0.85),
    (r"plain|meadow|grass|heath|shrub|field|pasture", (152, 156, 96), 0.02),
]
DEFAULT = ((146, 146, 96), 0.15)


def font(name, size):
    for f in (name, "pala.ttf", "georgia.ttf", "times.ttf"):
        try:
            return ImageFont.truetype(os.path.join(FONT_DIR, f), size)
        except OSError:
            continue
    return ImageFont.load_default()


def resize(a, shape, resample=Image.BICUBIC):
    return np.asarray(Image.fromarray(np.ascontiguousarray(a, np.float32), "F").resize((shape[1], shape[0]), resample))


def fbm(shape, seed, cell, octaves=5, gain=0.55):
    """Fractal value noise in about -1..1, built from upsampled random grids."""
    rng = np.random.default_rng(seed)
    out = np.zeros(shape, np.float32)
    amp, tot = 1.0, 0.0
    for _ in range(octaves):
        gh, gw = max(2, int(shape[0] / cell) + 2), max(2, int(shape[1] / cell) + 2)
        g = rng.standard_normal((gh, gw)).astype(np.float32)
        out += amp * resize(g, (int(gh * cell), int(gw * cell)))[:shape[0], :shape[1]]
        tot += amp
        amp *= gain
        cell = max(1.0, cell / 2)
    return out / tot


def lerp(a, b, t):
    return a + (b - a) * t


def family_luts(names):
    col = np.zeros((256, 3), np.float32)
    tree = np.zeros(256, np.float32)
    for bid in range(256):
        nm = names.get(bid, "")
        c, d = DEFAULT
        for pat, cc, dd in FAMILIES:
            if re.search(pat, nm, re.I):
                c, d = cc, dd
                break
        col[bid], tree[bid] = c, d
    col[BEACH] = col[STONE_BEACH] = (222, 206, 160)
    tree[BEACH] = tree[STONE_BEACH] = 0
    for b in (OCEAN, DEEP_OCEAN, RIVER):
        tree[b] = 0
    return col, tree


def hillshade(H, cell, az=315.0, alt=40.0, z=1.0):
    gy, gx = np.gradient(H, cell)
    gx, gy = gx * z, gy * z
    slope = np.arctan(np.hypot(gx, gy))
    aspect = np.arctan2(-gx, gy)
    a, e = math.radians(az), math.radians(alt)
    s = math.sin(e) * np.cos(slope) + math.cos(e) * np.sin(slope) * np.cos(a - math.pi / 2 - aspect)
    return np.clip(s, 0, 1), slope


def star(cx, cy, r_out, r_in, n=5, rot=-math.pi / 2):
    pts = []
    for i in range(2 * n):
        r = r_out if i % 2 == 0 else r_in
        a = rot + i * math.pi / n
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def compass(img, cx, cy, R, ink, paper):
    d = ImageDraw.Draw(img)
    w = max(1, int(R / 60))
    for rr, ww in ((R * 1.0, w * 2), (R * 0.93, w), (R * 0.42, w)):
        d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), outline=ink, width=ww)
    for k in range(64):   # tick ring
        a = k * math.pi / 32
        r0 = R * (0.93 if k % 4 else 0.86)
        d.line((cx + r0 * math.cos(a), cy + r0 * math.sin(a), cx + R * math.cos(a), cy + R * math.sin(a)),
               fill=ink, width=w)
    for a_deg, L, Wd in [(45 + 90 * k, 0.62, 0.09) for k in range(4)] + [(90 * k, 0.98, 0.13) for k in range(4)]:
        a = math.radians(a_deg - 90)
        tip = (cx + R * L * math.cos(a), cy + R * L * math.sin(a))
        l = (cx + R * Wd * math.cos(a - math.pi / 2), cy + R * Wd * math.sin(a - math.pi / 2))
        r = (cx + R * Wd * math.cos(a + math.pi / 2), cy + R * Wd * math.sin(a + math.pi / 2))
        d.polygon([(cx, cy), l, tip], fill=ink)
        d.polygon([(cx, cy), r, tip], fill=paper, outline=ink)
        d.line([(cx, cy), tip], fill=ink, width=w)
    d.ellipse((cx - R * 0.05, cy - R * 0.05, cx + R * 0.05, cy + R * 0.05), fill=paper, outline=ink, width=w)
    f = font("palab.ttf", int(R * 0.26))
    d.text((cx, cy - R * 1.17), "N", fill=ink, font=f, anchor="mm")


def render(plan_dir, out, size=4096, labels=True, crop=None, title="Quest Forge"):
    t_h = np.asarray(Image.open(f"{plan_dir}/height.png")).astype(np.float32) / 257
    t_b = np.asarray(Image.open(f"{plan_dir}/biome.png"))
    meta = json.load(open(f"{plan_dir}/plan.json"))
    n = t_b.shape[0]
    t_land = (np.asarray(Image.open(f"{plan_dir}/land.png")) > 0) if os.path.exists(f"{plan_dir}/land.png") else t_h >= SEA
    t_w = np.asarray(Image.open(f"{plan_dir}/water.png")).astype(np.float32) if os.path.exists(f"{plan_dir}/water.png") \
        else np.zeros_like(t_h)
    t_s = np.asarray(Image.open(f"{plan_dir}/surface.png")) if os.path.exists(f"{plan_dir}/surface.png") \
        else np.zeros_like(t_b)
    t_r = np.asarray(Image.open(f"{plan_dir}/relief.png")).astype(np.float32) / 255 \
        if os.path.exists(f"{plan_dir}/relief.png") else np.zeros_like(t_h)
    names = biome_names()
    lut, tree_lut = family_luts(names)

    N = size
    margin = int(N * 0.045)
    M = N - 2 * margin
    sh = (M, M)
    k = M / n                       # output px per plan px
    cell = meta["size"] / M         # blocks per output px
    U = max(1.0, N / 4096)          # stroke unit
    s = N / 4096

    # ---------------------------------------------------------------- fields at output resolution
    H = resize(ndimage.gaussian_filter(t_h, 0.6), sh)
    relief = resize(t_r, sh, Image.BILINEAR)
    cf = resize(ndimage.gaussian_filter(t_land.astype(np.float32), 0.7), sh, Image.BILINEAR)
    land = (cf + 0.10 * fbm(sh, 11, 9 * s, 4)) > 0.5
    lake_t = (t_w > 0) & (t_h < t_w)
    lake = (resize(ndimage.gaussian_filter(lake_t.astype(np.float32), 0.6), sh, Image.BILINEAR)
            + 0.08 * fbm(sh, 12, 8 * s, 3)) > 0.5
    riv_t = (t_b == RIVER).astype(np.float32)
    river = resize(riv_t, sh, Image.BILINEAR) > 0.42
    river &= land
    cold_t = np.zeros(256, bool)
    for bid, nm in names.items():
        cold_t[bid] = bool(re.search(r"snow|frost|glacier|polar|arctic|ice|tundra|frozen|alps", nm, re.I))

    # Biome wash: blurred family colours, sampled through a noise warp so edges look brushed.
    col_t = lut[t_b]
    # Rivers and beaches take the colour of their surroundings in the wash; they are drawn on top.
    fill = (t_b == RIVER) | (t_b == OCEAN) | (t_b == DEEP_OCEAN)
    if fill.any() and (~fill).any():
        idx = ndimage.distance_transform_edt(fill, return_distances=False, return_indices=True)
        col_t = col_t[idx[0], idx[1]]
    col_t[t_s == 1] = (70, 64, 62)
    col_t[t_s == 2] = (110, 92, 74)
    col_t[t_s == 3] = (214, 226, 232)
    col_t = np.stack([ndimage.gaussian_filter(col_t[..., c], 1.6) for c in range(3)], -1)
    wx = fbm(sh, 21, 70 * s, 4) * 30 * s
    wz = fbm(sh, 22, 70 * s, 4) * 30 * s
    yy, xx = np.mgrid[0:M, 0:M].astype(np.float32)
    sx = np.clip((xx + wx) / k - 0.5, 0, n - 1)
    sz = np.clip((yy + wz) / k - 0.5, 0, n - 1)
    del xx, yy
    wash = np.stack([ndimage.map_coordinates(col_t[..., c], [sz, sx], order=1) for c in range(3)], -1)
    trees = ndimage.map_coordinates(ndimage.gaussian_filter(tree_lut[t_b], 0.8), [sz, sx], order=1)
    tb_near = t_b[np.clip(sz.round().astype(int), 0, n - 1), np.clip(sx.round().astype(int), 0, n - 1)]
    del sx, sz, wx, wz

    # ---------------------------------------------------------------- relief + hillshade
    detail = (1 - np.abs(fbm(sh, 31, 26 * s, 5, 0.5))) ** 2   # ridged noise for craggy mountains
    alt = np.clip((H - SEA) / 120, 0, 1)
    Hd = H + detail * (6 + 40 * relief + 30 * alt ** 1.5) * land
    shade, slope = hillshade(ndimage.gaussian_filter(Hd, 1.2 * s), cell, z=2.2)
    shade2, _ = hillshade(ndimage.gaussian_filter(H, 6 * s), cell, az=300, alt=35, z=3.0)
    shade = 0.55 * shade + 0.45 * shade2
    flat = math.sin(math.radians(40))
    shade_mul = np.clip(0.62 + 0.52 * shade / flat, 0.45, 1.25)

    # Land colour: wash * paper noise * shade; height lifts toward grey-white near the peaks.
    n_big = fbm(sh, 41, 180 * s, 4)
    n_mid = fbm(sh, 42, 30 * s, 4)
    n_fine = fbm(sh, 43, 4 * s, 2)
    landc = wash * (1 + 0.07 * n_big + 0.06 * n_mid + 0.035 * n_fine)[..., None]
    rock = np.array((150, 140, 124), np.float32)
    high = np.clip((H - (SEA + 70)) / 70, 0, 1) ** 1.2 * (1 - 0.6 * (np.abs(wash - (228, 233, 234)).sum(-1) < 40))
    landc = lerp(landc, rock, (high * 0.65)[..., None])
    snowcap = np.clip((H - (SEA + 135)) / 30, 0, 1)
    landc = lerp(landc, np.array((236, 238, 236), np.float32), (snowcap * 0.85)[..., None])
    grey = landc.mean(-1, keepdims=True)
    landc = lerp(landc, grey, 0.18)              # muted, painterly saturation
    landc = landc * shade_mul[..., None]
    # Lowland warm glow, highland cool.
    landc *= (1 + 0.04 * (1 - alt))[..., None]

    # ---------------------------------------------------------------- sea
    d_out = ndimage.distance_transform_edt(~land)
    d_in = ndimage.distance_transform_edt(land)
    depth = np.clip((SEA - H) / 45, 0, 1)
    farness = np.clip(d_out / (M * 0.05), 0, 1)
    dd = np.clip(0.55 * depth + 0.6 * farness ** 0.7, 0, 1)
    shallow = np.array((130, 178, 160), np.float32)
    mid = np.array((66, 124, 116), np.float32)
    deep = np.array((34, 74, 78), np.float32)
    seac = np.where((dd < 0.5)[..., None], lerp(shallow, mid, (dd / 0.5)[..., None]),
                    lerp(mid, deep, ((dd - 0.5) / 0.5)[..., None]))
    halo = np.exp(-d_out / (M * 0.006))
    seac = lerp(seac, np.array((168, 204, 182), np.float32), (0.55 * halo)[..., None])
    band_col = np.array((190, 214, 196), np.float32)
    for i, dk in enumerate((0.005, 0.0105)):
        dpx = M * dk
        wv = dpx * (1 + 0.08 * n_mid)
        band = np.exp(-((d_out - wv) / (1.1 * U)) ** 2) * (0.38 - 0.14 * i)
        seac = lerp(seac, band_col, band[..., None])
    wave = fbm(sh, 51, 120 * s, 5)
    ripple = np.sin((np.arange(M)[:, None] * 0.9 / s + 18 * fbm(sh, 52, 40 * s, 3) * 1.0)) * 0.5 + 0.5
    seac *= (1 + 0.09 * wave + 0.025 * n_fine + 0.018 * (ripple - 0.5) * (1 - halo))[..., None]

    img = np.where(land[..., None], landc, seac)
    del landc, seac, wash

    # Lakes: clean blue, pale if cold; darker rim.
    lk = lake & land
    if lk.any():
        cold = cold_t[tb_near]
        d_lk = ndimage.distance_transform_edt(lk)
        lakec = np.where(cold[..., None], np.array((200, 222, 230), np.float32), lerp(
            np.array((108, 158, 168), np.float32), np.array((70, 122, 142), np.float32),
            np.clip(d_lk / (8 * s), 0, 1)[..., None]))
        img = np.where(lk[..., None], lakec, img)
        rim = lk & (d_lk <= 1.6 * U)
        img[rim] = img[rim] * 0.55 + np.array((40, 60, 70)) * 0.45
    # Rivers: thin clean blue with a darker edge.
    if river.any():
        rv = river & ~lk
        d_rv = ndimage.distance_transform_edt(rv)
        img[rv] = (82, 132, 158)
        edge = rv & (d_rv <= 1.0)
        img[edge] = (58, 96, 120)

    # Coast ink line + a light rim just outside.
    coast = np.exp(-((d_in - 0.6 * U) / (0.9 * U)) ** 2) * land + np.exp(-(d_out / (0.8 * U)) ** 2) * (~land) * 0.6
    img = lerp(img, np.array((52, 46, 36), np.float32), (np.clip(coast, 0, 1) * 0.85)[..., None])
    foam = np.exp(-((d_out - 2.4 * U) / (1.0 * U)) ** 2) * (~land)
    img = lerp(img, np.array((214, 226, 208), np.float32), (foam * 0.45)[..., None])

    # Parchment tone over everything: faint warm cast, stains and vignette.
    stain = fbm(sh, 61, 400 * s, 5)
    img *= (1 + 0.06 * stain)[..., None]
    img = lerp(img, np.array((214, 196, 150), np.float32), 0.10)
    vy = (np.arange(M) / M - 0.5)[:, None]
    vx = (np.arange(M) / M - 0.5)[None, :]
    vig = 1 - 0.55 * np.clip(np.hypot(vx, vy) - 0.33, 0, 1) ** 1.3
    img *= vig[..., None]

    base = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    del img

    # ---------------------------------------------------------------- strokes: hachures, ridges, trees
    ov = Image.new("RGBA", (M, M), (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)
    rng = np.random.default_rng(5)
    Hs = ndimage.gaussian_filter(Hd, 2.0 * s)
    gy, gx = np.gradient(Hs, cell)
    sl = np.hypot(gx, gy)
    mtn = land & (H > SEA + 40) & ~lk
    # Hachures: short strokes down the fall line, darker on the shadow side.
    step = 5 * s
    g = np.mgrid[0:M:step, 0:M:step].reshape(2, -1).T.astype(np.float32)
    g += rng.uniform(-step / 2, step / 2, g.shape)
    g = np.clip(g, 0, M - 1)
    gi = g.astype(int)
    keep = mtn[gi[:, 0], gi[:, 1]] & (sl[gi[:, 0], gi[:, 1]] > 0.25)
    for (py, px) in g[keep]:
        iy, ix = int(py), int(px)
        ax, ay = gx[iy, ix], gy[iy, ix]
        m = math.hypot(ax, ay)
        ux, uy = -ax / m, -ay / m                     # downhill
        L = min(1.0, m / 1.6) * 9 * s + 2 * s
        lit = shade[iy, ix]
        if lit < 0.5:                                 # shadow side: firm ink strokes
            c = (58, 42, 28, int(190 * min(1, 0.4 + m / 2)))
        elif lit < 0.75:                              # half-lit: faint strokes keep the form
            c = (70, 54, 38, int(70 * min(1, 0.4 + m / 2)))
        else:
            continue
        od.line((px, py, px + ux * L, py + uy * L), fill=c, width=max(1, round(1.2 * U)))
    # Ridge crests: where the smoothed surface is convex across the fall line.
    lap = ndimage.gaussian_laplace(H, 3.0 * s)
    ridge = mtn & (lap < -np.percentile(-lap[mtn], 70) if mtn.any() else mtn) & (H > SEA + 60)
    ry, rx = np.nonzero(ridge)
    if len(ry):
        pick = rng.random(len(ry)) < 0.5
        for y, x in zip(ry[pick], rx[pick]):
            a = gx[y, x], gy[y, x]
            m = math.hypot(*a) + 1e-6
            tx, ty = -a[1] / m, a[0] / m               # along the ridge
            L = 3 * s
            od.line((x - tx * L, y - ty * L, x + tx * L, y + ty * L), fill=(44, 32, 22, 150), width=max(1, round(1.5 * U)))
    # Forest stipple: little canopies with a shadow and a highlight.
    step = 6.2 * s
    g = np.mgrid[0:M:step, 0:M:step].reshape(2, -1).T.astype(np.float32)
    g += rng.uniform(-step * 0.6, step * 0.6, g.shape)
    g = np.clip(g, 0, M - 1)
    gi = g.astype(int)
    dens = trees[gi[:, 0], gi[:, 1]] * np.clip(0.6 + 0.8 * fbm(sh, 71, 50 * s, 3)[gi[:, 0], gi[:, 1]], 0, 1)
    ok = land[gi[:, 0], gi[:, 1]] & ~lk[gi[:, 0], gi[:, 1]] & ~river[gi[:, 0], gi[:, 1]] & \
        (d_in[gi[:, 0], gi[:, 1]] > 3 * s) & (rng.random(len(g)) < dens) & (H[gi[:, 0], gi[:, 1]] < SEA + 120)
    basearr = np.asarray(base)
    for (py, px) in g[ok]:
        iy, ix = int(py), int(px)
        c = basearr[iy, ix].astype(np.float32)
        r = (2.0 + rng.random() * 1.2) * s * (0.55 + 0.45 * min(1.0, trees[iy, ix] / 0.5))   # sparse = small brush
        dark = tuple(int(v) for v in c * 0.42) + (150,)
        mid_ = tuple(int(v) for v in np.clip(c * 0.78, 0, 255)) + (230,)
        hi = tuple(int(v) for v in np.clip(c * 1.12 + 10, 0, 255)) + (170,)
        od.ellipse((px - r + r * 0.5, py - r + r * 0.6, px + r + r * 0.5, py + r + r * 0.6), fill=dark)
        od.ellipse((px - r, py - r, px + r, py + r), fill=mid_)
        od.ellipse((px - r * 0.55, py - r * 0.6, px + r * 0.05, py), fill=hi)
    base = Image.alpha_composite(base.convert("RGBA"), ov)
    del ov, Hs, gx, gy, sl

    # ---------------------------------------------------------------- frame
    paper = np.array((226, 210, 172), np.float32)
    pf = fbm((N, N), 81, 200 * s, 6)
    frame = paper * (1 + 0.07 * pf + 0.03 * fbm((N, N), 82, 6 * s, 2))[..., None]
    fy = (np.arange(N) / N - 0.5)[:, None]
    fx = (np.arange(N) / N - 0.5)[None, :]
    frame *= (1 - 0.35 * np.clip(np.maximum(np.abs(fx), np.abs(fy)) - 0.45, 0, 1) * 10)[..., None].clip(0.6, 1)
    canvas = Image.fromarray(np.clip(frame, 0, 255).astype(np.uint8)).convert("RGBA")
    canvas.paste(base, (margin, margin))
    d = ImageDraw.Draw(canvas)
    ink = (52, 40, 28, 255)
    m0 = margin
    d.rectangle((m0 - 1, m0 - 1, N - m0, N - m0), outline=ink, width=max(2, round(3 * U)))
    o = margin * 0.42
    d.rectangle((o, o, N - o, N - o), outline=ink, width=max(2, round(3 * U)))
    o2 = margin * 0.52
    d.rectangle((o2, o2, N - o2, N - o2), outline=ink, width=max(1, round(U)))
    # Graduated band between o2 and the map edge: alternating ink / paper segments.
    seg = M / 32
    b0, b1 = margin * 0.66, margin * 0.80
    for i in range(32):
        if i % 2:
            continue
        a0, a1 = m0 + i * seg, m0 + (i + 1) * seg
        d.rectangle((a0, b0, a1, b1), fill=ink)
        d.rectangle((a0, N - b1, a1, N - b0), fill=ink)
        d.rectangle((b0, a0, b1, a1), fill=ink)
        d.rectangle((N - b1, a0, N - b0, a1), fill=ink)
    for bb in (b0, b1):
        d.rectangle((bb, bb, N - bb, N - bb), outline=ink, width=max(1, round(U)))

    # Compass rose in the corner with the most sea.
    q = int(M * 0.2)
    corners = {(0, 0): land[:q, :q].mean(), (0, 1): land[:q, -q:].mean(),
               (1, 0): land[-q:, :q].mean(), (1, 1): land[-q:, -q:].mean()}
    cy_, cx_ = min(corners, key=corners.get)
    R = M * 0.065
    ccx = m0 + (M - q * 0.55 if cx_ else q * 0.55)
    ccy = m0 + (M - q * 0.5 if cy_ else q * 0.55)
    rose = Image.new("RGBA", (N, N), (0, 0, 0, 0))
    compass(rose, ccx, ccy, R, (44, 36, 26, 215), (232, 220, 186, 215))
    canvas = Image.alpha_composite(canvas, rose)

    if labels:
        canvas = draw_labels(canvas, meta, names, t_b, n, m0, k, s, U, corners,
                             (ccx - R * 1.3, ccy - R * 1.45, ccx + R * 1.3, ccy + R * 1.3), title)

    canvas = canvas.convert("RGB")
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    canvas.save(out)
    print(f"wrote {out} ({N}x{N})")
    if crop:
        cx0, cy0, cw, path = crop if isinstance(crop, tuple) else (N // 2 - N // 8, N // 2 - N // 8, N // 4, crop)
        canvas.crop((cx0, cy0, cx0 + cw, cy0 + cw)).save(path)
        print(f"wrote {path} (crop {cw}px at {cx0},{cy0})")


def draw_labels(canvas, meta, names, t_b, n, m0, k, s, U, corners, rose_box, title):
    N = canvas.size[0]
    M = N - 2 * m0
    half, px = meta["size"] / 2, meta["px"]
    lay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    ink = (46, 34, 24, 255)
    halo = (238, 226, 196, 200)
    cream = (236, 226, 196, 255)
    taken = [rose_box]
    sw = max(2, round(3 * s))

    def to_px(x, z):
        return m0 + (x + half) / px * k, m0 + (z + half) / px * k

    def free(bb):
        if bb[0] < m0 or bb[1] < m0 or bb[2] > N - m0 or bb[3] > N - m0:
            return False
        return all(bb[2] < t[0] or bb[0] > t[2] or bb[3] < t[1] or bb[1] > t[3] for t in taken)

    def spaced(t):
        return " ".join(t.upper())

    def corner_box(c, w, h):
        x = m0 + 50 * s if c[1] == 0 else N - m0 - 50 * s - w
        y = m0 + 50 * s if c[0] == 0 else N - m0 - 50 * s - h
        return x, y

    # Title cartouche and key in the two most open corners after the compass rose.
    rest = sorted(corners, key=corners.get)
    tc, kc = rest[1], rest[2]
    ft = font("palab.ttf", int(70 * s))
    tw = d.textbbox((0, 0), spaced(title), font=ft)
    w_, h_ = tw[2] - tw[0] + 90 * s, tw[3] - tw[1] + 60 * s
    tx, ty = corner_box(tc, w_, h_)
    d.rectangle((tx, ty, tx + w_, ty + h_), fill=(232, 218, 182, 235), outline=ink, width=max(2, round(3 * U)))
    d.rectangle((tx + 8 * s, ty + 8 * s, tx + w_ - 8 * s, ty + h_ - 8 * s), outline=ink, width=max(1, round(U)))
    d.text((tx + w_ / 2, ty + h_ / 2), spaced(title), font=ft, anchor="mm", fill=ink)
    taken.append((tx - 20 * s, ty - 20 * s, tx + w_ + 20 * s, ty + h_ + 20 * s))

    blocks = 5000
    L = blocks / meta["size"] * M
    kw, kh = max(L + 70 * s, 300 * s), 200 * s
    kx0, ky0 = corner_box(kc, kw, kh)
    d.rectangle((kx0, ky0, kx0 + kw, ky0 + kh), fill=(232, 218, 182, 225), outline=ink, width=max(1, round(2 * U)))
    d.rectangle((kx0 + 6 * s, ky0 + 6 * s, kx0 + kw - 6 * s, ky0 + kh - 6 * s), outline=ink, width=1)
    taken.append((kx0 - 20 * s, ky0 - 20 * s, kx0 + kw + 20 * s, ky0 + kh + 20 * s))
    fk = font("pala.ttf", int(26 * s))
    kx, ky = kx0 + 40 * s, ky0 + 38 * s
    spawn_marker(d, kx, ky, 12 * s, ink, U)
    d.text((kx + 30 * s, ky), "Spawn", font=fk, anchor="lm", fill=ink)
    landmark_icon(d, kx, ky + 46 * s, 7 * s, "", ink, cream, U)
    d.text((kx + 30 * s, ky + 46 * s), "Landmark", font=fk, anchor="lm", fill=ink)
    sx, sy = kx0 + 35 * s, ky + 92 * s
    for i in range(5):
        d.rectangle((sx + i * L / 5, sy, sx + (i + 1) * L / 5, sy + 9 * s), fill=ink if i % 2 == 0 else cream, outline=ink)
    d.text((sx + L / 2, sy + 22 * s), f"{blocks:,} blocks", font=fk, anchor="mt", fill=ink)

    # Markers reserve their space before any text.
    pts = meta.get("points", [])
    r = 7 * s
    for p in pts:
        x, y = to_px(p["x"], p["z"])
        if p.get("kind") == "spawn":
            R = 15 * s
            spawn_marker(d, x, y, R, ink, U)
            taken.append((x - R * 1.2, y - R * 1.2, x + R * 1.2, y + R * 1.2))
        elif p.get("kind") == "landmark":
            landmark_icon(d, x, y, r, p.get("name", ""), ink, cream, U)
            taken.append((x - r * 1.3, y - r * 1.6, x + r * 1.3, y + r * 1.3))

    # Landmark names, at most once per name within a neighbourhood (a cluster of wrecks gets one label).
    f_lm = font("pala.ttf", int(26 * s))
    f_lmi = font("palai.ttf", int(26 * s))
    placed = {}
    for p in pts:
        if p.get("kind") != "landmark" or not p.get("name"):
            continue
        x, y = to_px(p["x"], p["z"])
        nm = p["name"]
        if any(math.hypot(x - a, y - b) < 260 * s for a, b in placed.get(nm, [])):
            continue
        f = f_lmi if re.search(r"fall|spring|lake|oasis|lagoon|cenote|maelstrom|cove|arch|front", nm, re.I) else f_lm
        off = 13 * s
        for anchor, (dx, dy) in (("lm", (off, 0)), ("rm", (-off, 0)), ("mb", (0, -off * 1.1)), ("mt", (0, off * 1.1)),
                                 ("lb", (off * 0.7, -off * 0.7)), ("lt", (off * 0.7, off * 0.7))):
            bb = d.textbbox((x + dx, y + dy), nm, font=f, anchor=anchor)
            bb = (bb[0] - 3 * s, bb[1] - 2 * s, bb[2] + 3 * s, bb[3] + 2 * s)
            if free(bb):
                d.text((x + dx, y + dy), nm, font=f, anchor=anchor, fill=ink, stroke_width=sw, stroke_fill=halo)
                taken.append(bb)
                placed.setdefault(nm, []).append((x, y))
                break

    # Biome names: the largest patches of real biomes in spaced small caps; seas in pale italics.
    min_px = (n / 18) ** 2
    cands = []
    for bid in np.unique(t_b):
        if bid in (OCEAN, DEEP_OCEAN, RIVER, BEACH, STONE_BEACH, 10, 11, 82, 150):
            continue
        lab, nl = ndimage.label(t_b == bid)
        if nl == 0:
            continue
        sizes = ndimage.sum(np.ones_like(lab), lab, range(1, nl + 1))
        for i in np.nonzero(sizes >= min_px)[0]:
            inner = ndimage.distance_transform_edt(lab == i + 1)
            zz, xx = np.unravel_index(inner.argmax(), inner.shape)
            cands.append((sizes[i], inner.max(), int(bid), xx, zz))
    cands.sort(reverse=True)
    used = set()
    count = 0
    for area, rad, bid, xx, zz in cands[:50]:
        nm = re.sub(r"^(BoP|RWG|Jungle) ", "", names.get(bid, ""))
        if not nm or nm in used:
            continue
        sea = bool(re.search(r"ocean|sea\b", nm, re.I))
        fs = int(36 * s) if sea else int(np.clip(rad * k * 0.18, 28 * s, 46 * s))
        f = font("palai.ttf" if sea else "pala.ttf", fs)
        txt = spaced(nm)
        x0, y0 = m0 + (xx + 0.5) * k, m0 + (zz + 0.5) * k
        for dy in (0, -1.5, 1.5, -3, 3):
            y = y0 + dy * fs
            bb = d.textbbox((x0, y), txt, font=f, anchor="mm")
            bb = (bb[0] - 8 * s, bb[1] - 6 * s, bb[2] + 8 * s, bb[3] + 6 * s)
            if bb[2] - bb[0] <= rad * k * 2.8 and free(bb):
                if sea:
                    d.text((x0, y), txt, font=f, anchor="mm", fill=(200, 220, 204, 175))
                else:
                    d.text((x0, y), txt, font=f, anchor="mm", fill=(50, 36, 24, 205), stroke_width=sw,
                           stroke_fill=(236, 226, 196, 90))
                taken.append(bb)
                used.add(nm)
                count += 1
                break
        if count >= 16:
            break
    return Image.alpha_composite(canvas, lay)


def spawn_marker(d, x, y, R, ink, U):
    d.ellipse((x - R * 1.15, y - R * 1.15, x + R * 1.15, y + R * 1.15), fill=(244, 232, 196, 235), outline=ink,
              width=max(1, round(1.6 * U)))
    d.polygon(star(x, y, R, R * 0.42), fill=(166, 36, 30, 255), outline=(60, 20, 14, 255))


def landmark_icon(d, x, y, r, nm, ink, cream, U):
    w = max(1, round(1.5 * U))
    if re.search(r"wreck", nm, re.I):
        d.line((x - r, y - r, x + r, y + r), fill=ink, width=max(1, round(2 * U)))
        d.line((x - r, y + r, x + r, y - r), fill=ink, width=max(1, round(2 * U)))
    elif re.search(r"fall|spring|lake|oasis|lagoon|cenote|sinkhole|maelstrom", nm, re.I):
        d.ellipse((x - r, y - r, x + r, y + r), fill=(84, 136, 168, 255), outline=ink, width=w)
        d.ellipse((x - r * 0.35, y - r * 0.35, x + r * 0.35, y + r * 0.35), fill=(236, 240, 236, 255))
    elif re.search(r"castle|lighthouse|core", nm, re.I):
        d.rectangle((x - r * 0.7, y - r * 1.1, x + r * 0.7, y + r * 0.8), fill=ink)
        for j in (-0.7, 0.0, 0.7):
            d.rectangle((x + r * (j - 0.25), y - r * 1.5, x + r * (j + 0.25), y - r * 1.0), fill=ink)
        d.rectangle((x - r * 0.2, y + r * 0.1, x + r * 0.2, y + r * 0.8), fill=cream)
    else:
        d.polygon([(x, y - r * 1.2), (x - r, y + r * 0.7), (x + r, y + r * 0.7)], fill=cream, outline=ink, width=w)
        d.ellipse((x - r * 0.25, y - r * 0.05, x + r * 0.25, y + r * 0.45), fill=ink)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("plan_dir")
    ap.add_argument("out")
    ap.add_argument("--size", type=int, default=4096, help="output pixels per side (default 4096)")
    ap.add_argument("--no-labels", action="store_true", help="clean art: no names, markers, title or key")
    ap.add_argument("--crop", help="also write a zoomed crop: PATH or X,Y,W,PATH in output pixels")
    ap.add_argument("--title", default="Quest Forge")
    a = ap.parse_args()
    crop = None
    if a.crop:
        parts = a.crop.split(",")
        crop = (int(parts[0]), int(parts[1]), int(parts[2]), ",".join(parts[3:])) if len(parts) >= 4 else a.crop
    render(a.plan_dir, a.out, a.size, not a.no_labels, crop, a.title)


if __name__ == "__main__":
    main()
