"""Illustrated fantasy-map render of a continent plan (the layers tools/world/plan.py writes).

    py -3.10 tools/world/illustrate.py PLANDIR OUT.png [--size 4096] [--no-labels] [--crop OUT_CROP.png]
        [--mountain-style relief|glyphs|both]

Painterly sea with depth shading, coastal halo and shallow-water bands; land as soft biome washes
(real biome families, muted palette) textured with noise; forests as tree stipple; rivers and lakes
in clean blue; parchment frame and compass rose. Mountains are found by height above the local
valley floor (works on any heightmap; passes read as gaps) and get a multi-directional hillshade lit
from the north-west, strong in the mountains (warm sunlit faces, cool shadows, ridge highlights,
snow only on the high crests). --mountain-style both (default) adds painted mountain glyphs over
that relief, sized by prominence and drawn north to south, with hill glyphs on the foothills;
glyphs keeps lowland-strength shading under them; relief draws shading and hachures only.
Escarpments and plateau walls (buttes, the tepui, the hot-spring terraces, the caldera's wall) draw
as cliff hachures, never peaks; plateau tops and terrace treads count relief from their own top;
desert and dune country gets no hill glyphs (terrain_character). Labels: landmarks (icons + serif names), spawns (stars + picker rating),
and the largest biome patches by their real names. --no-labels gives the clean spawn-picker art.
"""
import argparse
import json
import math
import os
import re
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
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
    (r"redwood", (98, 70, 62), 0.95),        # BoP Redwood Forest, RWG Redwood: burgundy-brown bark tone
    (r"taiga|conifer|boreal|spruce|pine|fir", (76, 98, 70), 0.95),
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


def shade_dir(gx, gy, az, alt):
    """Lambert shade of a surface with gradients gx (east) and gy (south), light from azimuth az
    (degrees clockwise from north) at elevation alt."""
    a, e = math.radians(az), math.radians(alt)
    lx, ly, lz = math.cos(e) * math.sin(a), -math.cos(e) * math.cos(a), math.sin(e)
    return np.clip((-gx * lx - gy * ly + lz) / np.sqrt(1 + gx * gx + gy * gy), 0, 1)


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


def render(plan_dir, out, size=4096, labels=True, crop=None, title="Quest Forge", mountain_style="both"):
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
    # Mountain weight from height above the local valley floor (a prominence proxy) rather than
    # absolute height, so it works on any heightmap: a crater rim or an ice ridge counts, a high
    # flat plateau barely does, and a pass reads as a gap because its floor is low.
    Hc = np.maximum(ndimage.gaussian_filter(t_h, 1.0), SEA)
    floor_t = ndimage.gaussian_filter(ndimage.minimum_filter(Hc, size=max(9, int(61 * 1536 / n) | 1)), 8)
    rel_t = np.clip(Hc - floor_t, 0, None)
    rel = resize(rel_t, sh, Image.BILINEAR)
    glyph_ok, cliff_t = terrain_character(t_h, Hc, rel_t, t_b, meta, names, n)
    glyph_ok = resize(glyph_ok, sh, Image.BILINEAR)
    cliff = resize(cliff_t, sh, Image.BILINEAR)
    alt = np.clip((H - SEA) / 120, 0, 1)
    mw = np.clip((rel - 22) / 75, 0, 1) ** 0.8 * np.clip((H - SEA - 12) / 40, 0, 1)
    mw = ndimage.gaussian_filter(mw * land, 2.5 * s)
    cold_o = ndimage.gaussian_filter(cold_t[tb_near].astype(np.float32), 6 * s)

    detail = (1 - np.abs(fbm(sh, 31, 26 * s, 5, 0.5))) ** 2   # ridged noise for craggy mountains
    Hd = H + detail * (5 + 30 * relief + 55 * mw) * land
    Hm = ndimage.gaussian_filter(Hd, 1.0 * s)
    gy, gx = np.gradient(Hm, cell)
    # Multi-directional shade (light mostly from the north-west), exaggerated in the mountains.
    z = (1.6 + 2.2 * mw)
    gx, gy = gx * z, gy * z
    shade = sum(wgt * shade_dir(gx, gy, az, 40) for az, wgt in ((315, .55), (270, .17), (0, .17), (225, .11)))
    gy, gx = np.gradient(ndimage.gaussian_filter(H, 5 * s), cell)
    shade = 0.62 * shade + 0.38 * shade_dir(gx * 3.0, gy * 3.0, 315, 35)
    slope = np.hypot(gx, gy)
    del gx, gy
    flat = 0.62 * math.sin(math.radians(40)) + 0.38 * math.sin(math.radians(35))
    sn = shade / flat - 1                         # 0 on flat ground, <0 in shadow, >0 sunlit

    # Land colour: wash * paper noise; mountains turn to rock, snow on the highest ridges only.
    n_big = fbm(sh, 41, 180 * s, 4)
    n_mid = fbm(sh, 42, 30 * s, 4)
    n_fine = fbm(sh, 43, 4 * s, 2)
    landc = wash * (1 + 0.07 * n_big + 0.06 * n_mid + 0.035 * n_fine)[..., None]
    rock = np.array((152, 138, 116), np.float32)
    landc = lerp(landc, rock, (np.clip(mw * 1.3, 0, 1) * 0.7 * (1 - 0.5 * cold_o))[..., None])
    grey = landc.mean(-1, keepdims=True)
    landc = lerp(landc, grey, 0.18)              # muted, painterly saturation
    tone = landc[::4, ::4].copy()                 # unlit local colour, for the glyphs
    # Crest convexity: positive on ridgelines, fine and broad scales.
    crest = np.clip(-ndimage.gaussian_laplace(Hd, 1.6 * s) / 2.0, 0, 1)
    crest_b = np.clip(-ndimage.gaussian_laplace(H, 6 * s) / 1.2, 0, 1)
    snowline = SEA + 150 - 75 * cold_o
    snow = np.clip((H + 28 * detail * mw + 40 * crest_b + 18 * crest - snowline) / 30, 0, 1)
    snow *= np.clip(1.4 - slope * 0.5, 0.35, 1) * np.clip(mw * 2.5, 0, 1)
    snow = np.clip(snow + 0.25 * n_mid * snow * (1 - snow) * 4, 0, 1)
    landc = lerp(landc, np.array((240, 240, 236), np.float32), (snow * 0.92)[..., None])
    # Lighting: gentle on lowland, strong in mountains; sunlit faces warm, shadow faces cool.
    gain = 0.42 + (0.4 if mountain_style == "glyphs" else 0.95) * mw
    landc *= np.clip(1 + gain * sn * 0.85, 0.32, 1.45)[..., None]
    w_cool = np.clip(-sn, 0, 1) * (0.25 + 0.75 * mw)
    landc *= lerp(1, np.array((0.80, 0.88, 1.10), np.float32), w_cool[..., None])
    w_warm = np.clip(sn, 0, 1) * mw
    landc *= lerp(1, np.array((1.07, 1.02, 0.90), np.float32), w_warm[..., None])
    # Crisp ridgeline highlights on the lit side of the crests.
    hl = crest * mw * np.clip(0.5 + sn * 2, 0, 1)
    landc = lerp(landc, np.array((252, 244, 222), np.float32), (np.clip(hl, 0, 1) * 0.55)[..., None])
    del crest, crest_b, Hm, slope
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
    if mountain_style == "relief":
        # Hachures: short strokes down the fall line on the shadow side of the mountains.
        Hs = ndimage.gaussian_filter(Hd, 2.0 * s)
        gy, gx = np.gradient(Hs, cell)
        sl = np.hypot(gx, gy)
        step = 5 * s
        g = np.mgrid[0:M:step, 0:M:step].reshape(2, -1).T.astype(np.float32)
        g += rng.uniform(-step / 2, step / 2, g.shape)
        g = np.clip(g, 0, M - 1)
        gi = g.astype(int)
        keep = (mw[gi[:, 0], gi[:, 1]] > 0.3) & ~lk[gi[:, 0], gi[:, 1]] & (sl[gi[:, 0], gi[:, 1]] > 0.25) & \
            (sn[gi[:, 0], gi[:, 1]] < -0.1)
        for (py, px) in g[keep]:
            iy, ix = int(py), int(px)
            ax, ay = gx[iy, ix], gy[iy, ix]
            m = math.hypot(ax, ay)
            L = min(1.0, m / 1.6) * 8 * s + 2 * s
            c = (50, 44, 48, int(150 * min(1, 0.3 + m / 2) * min(1, mw[iy, ix])))
            od.line((px, py, px - ax / m * L, py - ay / m * L), fill=c, width=max(1, round(1.1 * U)))
        del Hs, gx, gy, sl
    # Forest stipple: little canopies with a shadow and a highlight.
    step = 6.2 * s
    g = np.mgrid[0:M:step, 0:M:step].reshape(2, -1).T.astype(np.float32)
    g += rng.uniform(-step * 0.6, step * 0.6, g.shape)
    g = np.clip(g, 0, M - 1)
    gi = g.astype(int)
    dens = trees[gi[:, 0], gi[:, 1]] * np.clip(0.6 + 0.8 * fbm(sh, 71, 50 * s, 3)[gi[:, 0], gi[:, 1]], 0, 1)
    ok = land[gi[:, 0], gi[:, 1]] & ~lk[gi[:, 0], gi[:, 1]] & ~river[gi[:, 0], gi[:, 1]] & \
        (d_in[gi[:, 0], gi[:, 1]] > 3 * s) & (rng.random(len(g)) < dens * np.clip(1 - 1.6 * mw[gi[:, 0], gi[:, 1]], 0, 1)) & \
        (H[gi[:, 0], gi[:, 1]] < SEA + 120)
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
    del ov
    if mountain_style in ("glyphs", "both"):
        avoid = [((p["x"] + meta["size"] / 2) / meta["px"] * k, (p["z"] + meta["size"] / 2) / meta["px"] * k,
                  "pass" in p.get("name", "").lower())
                 for p in meta.get("points", []) if p.get("kind") in ("landmark", "spawn")]
        draw_cliffs(base, H, cliff, land & ~lk & ~river, cell, s, U)
        draw_mountain_glyphs(base, H, rel, mw, snow, cold_o, tone, land & ~lk & ~river, avoid, cell, s, U, glyph_ok)

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

    # Spawn labels carry the picker rating ("Spawn: Hard") when plan.json has one.
    f_sp = font("palab.ttf", int(28 * s))
    for p in pts:
        if p.get("kind") != "spawn" or not p.get("rating"):
            continue
        x, y = to_px(p["x"], p["z"])
        txt = f"Spawn: {p['rating']}"
        off = 22 * s
        for anchor, (dx, dy) in (("lm", (off, 0)), ("rm", (-off, 0)), ("mb", (0, -off)), ("mt", (0, off)),
                                 ("lb", (off * 0.7, -off * 0.7)), ("lt", (off * 0.7, off * 0.7))):
            bb = d.textbbox((x + dx, y + dy), txt, font=f_sp, anchor=anchor)
            bb = (bb[0] - 3 * s, bb[1] - 2 * s, bb[2] + 3 * s, bb[3] + 2 * s)
            if free(bb):
                d.text((x + dx, y + dy), txt, font=f_sp, anchor=anchor, fill=(120, 26, 20, 255), stroke_width=sw,
                       stroke_fill=halo)
                taken.append(bb)
                break

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


def _over(rgb, a, src, sa):
    """Paint src (a colour or a colour array) with alpha sa over rgb/a, in place."""
    out_a = sa + a * (1 - sa)
    rgb[:] = (np.asarray(src, np.float32) * sa[..., None] + rgb * (a * (1 - sa))[..., None]) / \
        np.maximum(out_a, 1e-6)[..., None]
    a[:] = out_a


def glyph_sprite(w, h, lit, shd, ink, sf, rng, U, hill=False):
    """A painted mountain (or hill) profile lit from the west. Returns (RGBA image, base-centre x, base y)
    with w, h in output px; lit/shd are the face colours; sf is the snow cap as a fraction of the height."""
    SS = 3
    w, h = float(w), float(h)
    ox, oy = 0.12 * w + 2, 0.06 * h + 2
    Wp, Hp = int((w * 1.62 + 4) * SS), int((h * 1.22 + 4) * SS)

    def P(pts):
        return [((ox + x) * SS, (oy + y) * SS) for x, y in pts]

    ax = w * rng.uniform(0.42, 0.58)
    if hill:
        n = 8
        left = [(ax * i / n, h * (1 - math.sin(math.pi / 2 * i / n) ** 0.75)) for i in range(n + 1)]
        right = [(ax + (w - ax) * i / n, h * (1 - math.cos(math.pi / 2 * i / n) ** 0.75)) for i in range(1, n + 1)]
        rx = ax + w * rng.uniform(0.04, 0.12)
        ridge = [(ax, 0), (lerp(ax, rx, 0.5) + w * rng.uniform(-0.03, 0.03), h * 0.5), (rx, h)]
    else:
        def side(x0, x1, y0, y1, k):
            pts = []
            sh_i = rng.integers(1, k) if rng.random() < 0.55 else -1   # an optional shoulder
            for i in range(1, k):
                t = i / k
                y = lerp(y0, y1, t) + h * rng.normal(0, 0.03) * 4 * t * (1 - t)
                if i == sh_i:
                    y -= h * rng.uniform(0.08, 0.18)
                pts.append((lerp(x0, x1, t) + w * rng.uniform(-0.02, 0.02), y))
            return pts
        left = [(0, h)] + side(0, ax, h, 0, 5) + [(ax, 0)]
        right = side(ax, w, 0, h, 5) + [(w, h)]
        rx = ax + w * rng.uniform(0.0, 0.16)
        ridge = [(ax, 0)]
        for t in (0.3, 0.62):
            ridge.append((lerp(ax, rx, t) + w * rng.uniform(-0.05, 0.05), h * t))
        ridge.append((rx, h))
    outline = left + right
    litm, shm, inkm, gsh = (Image.new("L", (Wp, Hp), 0) for _ in range(4))
    ImageDraw.Draw(litm).polygon(P(left + ridge[1:]), fill=255)
    ImageDraw.Draw(shm).polygon(P([(ax, 0)] + right + ridge[::-1]), fill=255)
    di = ImageDraw.Draw(inkm)
    di.line(P(outline), fill=235, width=max(1, round(1.15 * U * SS)), joint="curve")
    if not hill:
        di.line(P(ridge[:3]), fill=150, width=max(1, round(0.8 * U * SS)))
    if not hill:     # hachures on the shadow face, roughly parallel to the right slope
        for _ in range(int(rng.integers(3, 6))):
            t0 = rng.uniform(0.2, 0.75)
            xa, ya = lerp(ax, rx, t0) + w * 0.03, h * t0
            L = w * rng.uniform(0.1, 0.22)
            di.line(P([(xa, ya), (xa + L, ya + L * h / max(w - ax, 1) * 0.9)]), fill=110,
                    width=max(1, round(0.75 * U * SS)))
    ImageDraw.Draw(gsh).ellipse(P([(w * 0.25, h * 0.9), (w * 1.45, h * 1.12)]), fill=255)
    gsh = gsh.filter(ImageFilter.GaussianBlur(h * 0.08 * SS + 1))
    L_, S_, I_, G_ = (np.asarray(m_, np.float32) / 255 for m_ in (litm, shm, inkm, gsh))
    Y = (np.arange(Hp, dtype=np.float32)[:, None] / SS - oy) / h + np.zeros((1, Wp), np.float32)
    X = (np.arange(Wp, dtype=np.float32)[None, :] / SS - ox) / w + np.zeros((Hp, 1), np.float32)
    fade = np.clip((1.0 - Y) / 0.2, 0, 1) ** 0.9            # the foot melts into the ground
    rgb = np.zeros((Hp, Wp, 3), np.float32)
    # Brush texture: soft streaks running down the faces.
    tex = ndimage.gaussian_filter(rng.standard_normal((Hp, Wp)).astype(np.float32), (2.5 * SS, 0.6 * SS))
    tex = 1 + 0.06 * tex / (tex.std() + 1e-6)
    a = np.zeros((Hp, Wp), np.float32)
    _over(rgb, a, (40, 36, 40), G_ * 0.16 * np.clip(1 - S_ - L_, 0, 1))
    _over(rgb, a, np.asarray(lit, np.float32) * ((1 + 0.12 * (1 - Y)) * tex)[..., None], L_ * fade)
    _over(rgb, a, np.asarray(shd, np.float32) * ((0.85 + 0.15 * np.clip((X * w - ax) / max(w - ax, 1), 0, 1)) * tex)[..., None],
          S_ * fade)
    if sf > 0:
        wob = sum(np.sin(X * 2 * math.pi * f + rng.uniform(0, 6.3)) * 0.18 / f ** 0.5 for f in (1.3, 2.7, 5.1))
        rx_y = ax + (rx - ax) * np.clip(Y, 0, 1)
        near = np.exp(-((X * w - rx_y) / (0.06 * w)) ** 2)          # snow runs down the ridge line
        snow_m = np.clip((sf * (1 + wob) + 0.35 * sf * near - Y) * h * SS / 3, 0, 1)
        _over(rgb, a, (246, 246, 241), L_ * snow_m * fade)
        _over(rgb, a, (194, 200, 212), S_ * snow_m * fade)
    _over(rgb, a, ink, I_ * np.clip((1.0 - Y) / 0.35, 0, 1) ** 1.3 * (0.5 if hill else 0.9))
    im = Image.fromarray(np.dstack([np.clip(rgb, 0, 255), np.clip(a * 255, 0, 255)]).astype(np.uint8), "RGBA")
    im = im.convert("RGBa").resize((Wp // SS, Hp // SS), Image.LANCZOS).convert("RGBA")
    return im, ox + w / 2, oy + h


def terrain_character(t_h, Hc, rel_t, t_b, meta, names, n):
    """Where glyphs belong, and where the relief is a cliff instead (plan resolution).

    Returns (glyph_ok, cliff): glyph_ok is 1 for mountains, 0.5 for mountains only (no hill
    glyphs: dune country) and 0 for none; cliff is 0..1 on escarpments and plateau walls.
    - Plateau tops (plan.json plateaus: the hot-spring terraces, buttes, the tepui, mesas) count
      their relief from their own top, so a terrace tread or a butte top is not a hill, while the
      caldera rims standing on their plateau still are.
    - Peaks and ridges have lower ground on both sides along some line through them; a step
      (an escarpment's brow, a plateau's rim) has high ground continuing on one side. Ground
      whose drop on both sides is small next to its relief is a step: no glyph, cliff strokes.
    - Desert, dune and badland country gets no hill glyphs: its rolling relief is dunes."""
    px, half = meta["px"], meta["size"] / 2
    top = np.zeros((n, n), np.float32)
    walls = np.zeros((n, n), np.float32)
    low = ndimage.minimum_filter(Hc, 7)
    for pl in sorted(meta.get("plateaus", []), key=lambda q: q.get("top", 0)):
        if pl.get("top", 0) <= SEA + 2:          # surface paint (scorched ground), not a landform
            continue
        im = Image.new("L", (n, n), 0)
        ImageDraw.Draw(im).polygon([((x + half) / px, (z + half) / px) for x, z in pl["polygon"]], fill=255)
        m = np.asarray(im) > 0
        top = np.where(m, np.maximum(top, pl["top"]), top)
        ring = ndimage.binary_dilation(m, iterations=2) & ~ndimage.binary_erosion(m, iterations=2)
        walls = np.maximum(walls, ring * np.clip(pl["top"] - low, 0, None))     # the wall's height
    on_plat = top > 0
    rel_p = np.where(on_plat, np.clip(Hc - top - 6, 0, None), rel_t)
    # Ridge-ness of the high ground near each pixel (its top within ~450 blocks, so a flank
    # judges by its own crest): the larger of the two-sided drops from that top along four
    # lines, at two distances. A ridge or peak falls away on both sides; a brow does not.
    Hm = ndimage.gaussian_filter(Hc, 1.0)
    Hloc = ndimage.maximum_filter(Hm, size=2 * int(round(450 / px)) + 1)
    drop = np.full_like(Hm, -1e3)
    for dist in (1000, 2000):
        k = max(1, int(round(dist / px)))
        Hk = ndimage.maximum_filter(Hm, size=max(3, k // 3) | 1)
        for di, dj in ((1, 0), (0, 1), (1, 1), (1, -1)):
            a = np.roll(Hk, (di * k, dj * k), (0, 1))
            b = np.roll(Hk, (-di * k, -dj * k), (0, 1))
            drop = np.maximum(drop, Hloc - np.maximum(a, b))
    step = (drop < 0.3 * rel_p) & (rel_p > 15)
    step = ndimage.binary_opening(step)            # whole brows, not stray pixels in a massif
    ok = np.where(step, 0.0, 1.0)
    ok = np.where(on_plat & (ndimage.maximum_filter(rel_p, 5) < 15), 0.0, ok)     # treads and tops, not rims
    ok = np.where(ndimage.binary_dilation(walls > 12, iterations=3), 0.0, ok)     # the walls themselves
    dune = np.zeros(256, bool)
    for bid, nm in names.items():
        dune[bid] = bool(re.search(r"desert|dune|outback|xeric|oasis|mesa|badland|canyon", nm, re.I))
    ok = np.where(dune[t_b] & (ok > 0), 0.5, ok)
    gy, gx = np.gradient(Hc, px)
    sl = np.hypot(gx, gy)
    cliff = np.clip((sl - 0.25) / 0.5, 0, 1) * (step | (walls > 12))
    cliff = np.where(walls > 12, np.maximum(cliff, 0.8), cliff)
    return ndimage.gaussian_filter(ok.astype(np.float32), 0.7), ndimage.gaussian_filter(cliff.astype(np.float32), 0.6)


def draw_cliffs(base, H, cliff, ok, cell, s, U):
    """Cliff hachures on escarpments and plateau walls: short ink ticks down the fall line,
    packed along the brow, longer where the wall is taller."""
    M = H.shape[0]
    rng = np.random.default_rng(23)
    Hs = ndimage.gaussian_filter(H, 1.5 * s)
    gy, gx = np.gradient(Hs, cell)
    sl = np.hypot(gx, gy)
    step = 3.2 * s
    g = np.mgrid[0:M:step, 0:M:step].reshape(2, -1).T.astype(np.float32)
    g += rng.uniform(-step / 2, step / 2, g.shape)
    g = np.clip(g, 0, M - 1)
    gi = g.astype(int)
    c = cliff[gi[:, 0], gi[:, 1]]
    keep = ok[gi[:, 0], gi[:, 1]] & (c > 0.35) & (sl[gi[:, 0], gi[:, 1]] > 0.12) & (rng.random(len(g)) < c)
    ov = Image.new("RGBA", base.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)
    for (py, px) in g[keep]:
        iy, ix = int(py), int(px)
        ax, ay = gx[iy, ix], gy[iy, ix]
        m = math.hypot(ax, ay)
        L = (4 + 7 * min(1.0, m / 2.5)) * s
        a = int(215 * min(1.0, 0.25 + cliff[iy, ix]))
        od.line((px, py, px - ax / m * L, py - ay / m * L), fill=(40, 32, 28, a), width=max(1, round(1.3 * U)))
    base.alpha_composite(ov)
    print(f"cliff hachures: {int(keep.sum())}")


def draw_mountain_glyphs(base, H, rel, mw, snow, cold, tone, ok, avoid, cell, s, U, glyph_ok=None):
    """Painted mountain glyphs along the high ground and hill glyphs on the foothills, placed
    greedily from the most prominent ground down, then drawn back to front (north to south).
    glyph_ok (terrain_character): 0 = none (cliffs, terraces), 0.5 = mountains only (dunes)."""
    M = H.shape[0]
    rng = np.random.default_rng(17)
    step = 5 * s
    g = np.mgrid[0:M:step, 0:M:step].reshape(2, -1).T.astype(np.float32)
    g += rng.uniform(-step / 2, step / 2, g.shape)
    g = np.clip(g, 0, M - 1)
    gi = g.astype(int)
    r, m, h = rel[gi[:, 0], gi[:, 1]], mw[gi[:, 0], gi[:, 1]], H[gi[:, 0], gi[:, 1]]
    okp = ok[gi[:, 0], gi[:, 1]]
    go = glyph_ok[gi[:, 0], gi[:, 1]] if glyph_ok is not None else np.ones(len(g), np.float32)
    mtn = okp & (m > 0.5) & (r > 52) & (go > 0.4)
    pk = (rel >= ndimage.maximum_filter(rel, size=int(55 * s)) - 2)[gi[:, 0], gi[:, 1]]   # local summits
    hill = okp & ~mtn & (r > 15) & (m > 0.06) & (h > SEA + 8) & (go > 0.75)
    pr = np.where(mtn, r + 0.35 * (h - SEA) + 60 * pk, -1000 + r) + rng.uniform(0, 6, len(g))
    order = np.argsort(-pr)
    order = order[(mtn | hill)[order]]
    pass_r = 600 / cell
    bucket = 80 * s
    grid = {}
    placed = []
    for i in order:
        y, x = float(g[i, 0]), float(g[i, 1])
        is_m = bool(mtn[i])
        if is_m:
            t = min(1.0, (r[i] - 52) / 140)
            a_ = min(1.0, max(0.0, (h[i] - SEA) / 170))
            w = (30 + 50 * (0.5 * t + 0.5 * a_)) * s * rng.uniform(0.85, 1.15)
            if pk[i]:
                w *= 1.35
            hh = w * (0.5 + 0.25 * a_ + 0.08 * pk[i]) * rng.uniform(0.9, 1.1)
            fx, fy = 0.74, 0.7
        else:
            if rng.random() > 0.22:
                continue
            w = (13 + 12 * min(1.0, (r[i] - 15) / 30)) * s * rng.uniform(0.85, 1.15)
            hh = w * rng.uniform(0.38, 0.48)
            fx, fy = 1.5, 1.4
        by = y + 0.25 * hh
        x0, x1 = int(x - w * 0.42), int(x + w * 0.42)
        if x0 < 0 or x1 >= M or by >= M or by - hh < 0 or not (ok[int(by), x0] and ok[int(by), x1]):
            continue
        bad = False
        for px_, py_, is_pass in avoid:
            if is_pass:
                bad = math.hypot(x - px_, y - py_) < pass_r + w * 0.3
            else:     # keep landmark and spawn icons uncovered
                bad = abs(px_ - x) < w * 0.5 + 10 * s and by - hh - 10 * s < py_ < by + 8 * s
            if bad:
                break
        if bad:
            continue
        bx, byk = int(x // bucket), int(y // bucket)
        for ddx in (-1, 0, 1):
            for ddy in (-1, 0, 1):
                for (qx, qy, qw, qh, qm) in grid.get((bx + ddx, byk + ddy), ()):
                    kx, ky = (fx, fy) if (is_m and qm) else (1.0, 0.9)
                    ex = (x - qx) / (kx * (w + qw) / 2)
                    ey = (y - qy) / (ky * (hh + qh) / 2)
                    if ex * ex + ey * ey < 1:
                        bad = True
                        break
                if bad:
                    break
            if bad:
                break
        if bad:
            continue
        grid.setdefault((bx, byk), []).append((x, y, w, hh, is_m))
        placed.append((by, x, y, w, hh, is_m))
    placed.sort()
    ts = tone.shape
    ink = np.array((46, 38, 34), np.float32)
    for by, x, y, w, hh, is_m in placed:
        ty, tx = min(ts[0] - 1, int(y) // 4), min(ts[1] - 1, int(x) // 4)
        c = tone[max(0, ty - 2):ty + 3, max(0, tx - 2):tx + 3].reshape(-1, 3).mean(0)
        sv = float(snow[int(y), int(x)])
        cd = float(cold[int(y), int(x)])
        if is_m:
            c = lerp(c, np.array((146, 134, 118), np.float32), min(0.85, 0.5 + 0.35 * cd))
        lit = np.clip(c * 1.1 + (12, 8, 0), 0, 255)
        shd = np.clip(lerp(c * 0.6, np.array((84, 88, 104), np.float32), 0.3), 0, 255)
        sf = min(0.48, 0.16 + 0.3 * sv + 0.1 * cd) if is_m and (sv > 0.15 or cd > 0.5) else 0.0
        spr, axx, ayy = glyph_sprite(w, hh, lit, shd, ink, sf, rng, U, hill=not is_m)
        base.alpha_composite(spr, (int(round(x - axx)), int(round(by - ayy))))
    print(f"mountain glyphs: {sum(p[5] for p in placed)} peaks, {sum(not p[5] for p in placed)} hills")


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
    ap.add_argument("--mountain-style", choices=("relief", "glyphs", "both"), default="both",
                    help="relief: shaded terrain with hachures; glyphs: painted mountain and hill glyphs; "
                         "both (default): glyphs over the shaded relief")
    a = ap.parse_args()
    crop = None
    if a.crop:
        parts = a.crop.split(",")
        crop = (int(parts[0]), int(parts[1]), int(parts[2]), ",".join(parts[3:])) if len(parts) >= 4 else a.crop
    render(a.plan_dir, a.out, a.size, not a.no_labels, crop, a.title, a.mountain_style)


if __name__ == "__main__":
    main()
