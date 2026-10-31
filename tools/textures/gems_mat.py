#!/usr/bin/env python3
"""Connected gem MATERIALS for diamond and emerald (r014; owner r013 gems: "Right idea, but I don't like this. It looks
like plastic"; all three connected-gem scenes "neither"). The connected layout (gems_ctm.py, 47-tile MCPatcher ctm,
Faithful 64x frame on a group's outer rim) stays; what changes is what the face is made of.

Why r013 read as plastic (numbers in ops/checkpoints/r014-textures.md, from the r013 frames): one uniform gloss
(_s 240 / F0 44 on every pixel) over a flat, bright colour (Faithful's diamond face: 9 tones, luma CV 0.09, no pixel
below 0.6x the mean), so the face is the textbook plastic BRDF, a white specular coat on even paint. On the flat
connected face 74-89 % of the brightness variation is one smooth sky gradient, and the sun leaves white dashes (top 3 %
saturation 0.16 against the body's 0.62) that all lean the same way (half of them in one 30-degree bin).

The three materials, each copied from how a pack makes gems read as gems:

  crystal  Patrix 32x's amethyst block, the most gem-like of the reference packs: a druse of crystals, each a few
           flat facets (LabPBR _n, median tilt 28 deg) with smooth crystals and rough gaps (_s), dark gaps between
           bright crystals (luma CV 0.38). Its 4x4-block repeat texture is read at native size (crystals at our 64x
           texel), re-toned by value onto the gem's ramp (Faithful's own colours plus two deeper shades), its _n kept,
           its _s mapped onto the shader's gem path: crystals mirror, gaps do not.
  deep     Faithful 64x's own face, seen through a polished table: the surface is flat (one mirror, as a polished
           gem's table is), but the colour has depth. Interior facets (Patrix's diamond _n regions, the way a cut
           stone's pavilion shows through its table) shade the face from deep to bright; Faithful's streaks ride on
           top; the brightest tones stay coloured. F0 0.11, so the colour leads and the mirror rises at grazing angles.
  cut      deep's colour with the surface itself cut: an irregular field of flat facets (Voronoi, 64-periodic, so it
           runs on across blocks), each tipped 8-24 deg in its own direction with its own smoothness and F0, the way
           Patrix's diamond _n and amethyst _n are built. The sky breaks into a mosaic and the sun lands on a few
           facets in different directions instead of on parallel streaks.

Reference packs are read at build time from C:\\qf-world\\reference-packs (owner's exception, CLAUDE.md); nothing from
them is committed. Output is only ever the private build zip.

    py -3.10 tools/textures/gems_mat.py <faithful64.zip> <patrix.zip> <out_dir>      # sheets of all three
"""
import io
import sys
import zipfile

import numpy as np
from PIL import Image

import gems
import gems_ctm

MATERIALS = ("crystal", "polished", "faithful")
GEMS = ("diamond_block", "emerald_block")
PATRIX_DIR = "assets/minecraft/"
AMETHYST_CTM = PATRIX_DIR + "optifine/ctm/patrix/amethyst/block/"
AMETHYST = PATRIX_DIR + "textures/block/amethyst_block"
# Patrix's amethyst properties: tiles=1-3 <default> 5-16, method=repeat 4x4 (row-major).
AMETHYST_ORDER = ["1", "2", "3", None] + [str(i) for i in range(5, 17)]

# Ramps, dark -> light. Diamond: Faithful 64x's own diamond tones (gems_ctm r013 palette) with two deeper teals under
# them; emerald: gems.EMERALD_RAMP with one deeper green. The top stays coloured (no pure white in the body).
RAMPS = {
    "diamond_block": np.array([(6, 70, 92), (10, 112, 132), (14, 150, 164), (21, 194, 198), (61, 224, 229),
                               (101, 245, 227), (158, 254, 235), (205, 255, 246)], np.float32),
    "emerald_block": np.array([(6, 52, 22), (12, 82, 30), (16, 112, 36), (28, 152, 41), (23, 197, 68),
                               (23, 221, 98), (65, 243, 132), (140, 248, 180)], np.float32),
}
GEM_SMOOTH_MIN = 230      # shader gem path: smoothness > 0.88 (224.4) and F0 > 0.1 (25.5)


def lum(a):
    return a[..., :3].astype(np.float64) @ np.array([0.2126, 0.7152, 0.0722])


def ramp(t, r):
    """t in 0..1 -> colour along ramp r (linear between stops)."""
    t = np.clip(t, 0.0, 1.0) * (len(r) - 1)
    j = np.minimum(np.floor(t).astype(int), len(r) - 2)
    w = (t - j)[..., None]
    return r[j] * (1 - w) + r[j + 1] * w


def _png(z, name):
    return np.array(Image.open(io.BytesIO(z.read(name))).convert("RGBA"))


def amethyst_big(patrix_zip):
    """Patrix's amethyst as the 128x128 texture its 4x4 repeat rule lays out: (albedo, _n, _s)."""
    z = zipfile.ZipFile(patrix_zip)
    out = []
    for suf in ("", "_n", "_s"):
        big = np.zeros((128, 128, 4), np.uint8)
        for k, t in enumerate(AMETHYST_ORDER):
            p = (AMETHYST + suf + ".png") if t is None else (AMETHYST_CTM + t + suf + ".png")
            y, x = divmod(k, 4)
            big[y * 32:y * 32 + 32, x * 32:x * 32 + 32] = _png(z, p)[:32]
        out.append(big)
    return out


def periodic(src, size=64, pad=4, origin=(0, 0)):
    """(size, size, 2) coords into src (larger than size) whose image is size-periodic: a (size-2*pad)^2 window at
    `origin` widened by gems_ctm's quilting (every pixel still one of src's own)."""
    y0, x0 = origin
    pseudo = src[y0:y0 + size, x0:x0 + size]
    m = gems_ctm.periodic_map(pseudo, (pad, pad, pad, pad))
    return m + np.array([y0, x0])


def _block_from_face(base, face, bands):
    """The 64x64 block: base's frame bands around `face` (64-periodic); the face shows through inside the bands."""
    n = base.shape[0]
    t, l, b, r = bands
    out = base.copy()
    out[t:n - b, l:n - r] = face[t:n - b, l:n - r]
    return out


def voronoi_facets(n=64, cells=18, seed=7):
    """(labels, centres) of an n-periodic Voronoi field: irregular flat facets that run on across block seams."""
    rng = np.random.default_rng(seed)
    # jittered grid keeps cells even-sized (no huge or sliver facets)
    g = int(np.ceil(np.sqrt(cells)))
    pts = []
    for i in range(g):
        for j in range(g):
            if len(pts) < cells:
                pts.append(((i + rng.uniform(0.15, 0.85)) * n / g, (j + rng.uniform(0.15, 0.85)) * n / g))
    pts = np.array(pts)
    ys, xs = np.mgrid[0:n, 0:n] + 0.5
    best = np.full((n, n), np.inf)
    lab = np.zeros((n, n), int)
    for k, (py, px) in enumerate(pts):
        dy = np.abs(ys - py); dy = np.minimum(dy, n - dy)
        dx = np.abs(xs - px); dx = np.minimum(dx, n - dx)
        d = dy * dy + dx * dx
        m = d < best
        best[m] = d[m]
        lab[m] = k
    return lab, pts


def _n_png(vx, vy, ao=None):
    nm = np.zeros(vx.shape + (4,), np.uint8)
    nm[..., 0] = np.clip(np.round((vx + 1.0) * 127.5), 0, 255)
    nm[..., 1] = np.clip(np.round((vy + 1.0) * 127.5), 0, 255)
    nm[..., 2] = 255 if ao is None else ao
    nm[..., 3] = 255
    return nm


def facet_field(n, cells, seed, tilt_deg=(8, 24), level=0):
    """An n-periodic field of flat facets: (labels, vx, vy) per pixel, each facet tipped by its own angle in its own
    direction (sin of the tilt; DirectX +y down); `level` facets lie flat (table-like mirrors)."""
    lab, _ = voronoi_facets(n, cells, seed)
    rng = np.random.default_rng(seed + 1000)
    k = lab.max() + 1
    ang = rng.uniform(0, 2 * np.pi, k)
    tilt = np.sin(np.radians(rng.uniform(tilt_deg[0], tilt_deg[1], k)))
    if level:
        tilt[rng.choice(k, level, replace=False)] = 0.0
    return lab, (np.cos(ang) * tilt)[lab], (np.sin(ang) * tilt)[lab]


def _interior_depth(vx, vy):
    """0..1 flat shading of facets by one interior light from the top-left (as Faithful's streaks run): how a cut
    stone's facets each return their own brightness (Patrix's diamond and amethyst _n are built of such planes)."""
    zc = np.sqrt(np.clip(1.0 - vx * vx - vy * vy, 0.0, 1.0))
    L = np.array([-0.5, -0.6, 0.62]); L /= np.linalg.norm(L)
    d = vx * L[0] + vy * L[1] + zc * L[2]
    return (d - d.min()) / max(d.max() - d.min(), 1e-6)


def _deep_face(name, face, depth, w_depth=0.62):
    """deep / cut colour: Faithful's face rank (its streaks) over the facets' depth, on the deep ramp."""
    Lf = lum(face)
    levels = np.unique(np.round(Lf, 1))
    rank = np.searchsorted(levels, np.round(Lf, 1)) / max(len(levels) - 1, 1)
    t = w_depth * depth + (1.0 - w_depth) * rank
    lo, hi = np.percentile(t, 2), np.percentile(t, 99.5)
    t = np.clip((t - lo) / (hi - lo), 0, 1) ** 1.15
    out = face.copy()
    out[..., :3] = np.round(ramp(t, RAMPS[name])).astype(np.uint8)
    return out


def material(name, mode, base, bands, patrix_zip):
    """-> dict(block=(img, n, s) 64x64 with Faithful's frame; atlas=(img, n, s) 64x128 = [block | periodic face];
    pmap = coords of the periodic face in the atlas) for gems_ctm.tile_maps(atlas_img, bands, pmap)."""
    n = base.shape[0]
    assert n == 64 and base.shape[1] == 64, "gems_mat expects Faithful 64x blocks"
    pm = gems_ctm.periodic_map(base, bands)
    r013_face = base[pm[..., 0], pm[..., 1]]
    if mode in ("crystal", "polished", "faithful"):
        a, an, as_ = amethyst_big(patrix_zip)
        mp = periodic(a, n, pad=3, origin=(20, 36))
        face = a[mp[..., 0], mp[..., 1]].copy()
        La = lum(face)
        lo, hi = np.percentile(La, 1), np.percentile(La, 99.5)
        face[..., :3] = np.round(ramp(np.clip((La - lo) / (hi - lo), 0, 1) ** 0.9, RAMPS[name])).astype(np.uint8)
        face[..., 3] = 255
        fs = np.zeros((n, n, 4), np.uint8)
        fs[..., 3] = 255
        if mode == "faithful":
            # Faithful's own face (the art the owner picked), its tones spread by rank over the deeper ramp
            Lf = np.round(lum(r013_face), 1)
            levels = np.unique(Lf)
            rank = np.searchsorted(levels, Lf) / max(len(levels) - 1, 1)
            face = r013_face.copy()
            face[..., :3] = np.round(ramp(0.18 + 0.82 * rank, RAMPS[name])).astype(np.uint8)
        if mode in ("crystal", "faithful"):
            pn = an[mp[..., 0], mp[..., 1]].astype(np.float64)
            fn = _n_png(pn[..., 0] / 127.5 - 1.0, pn[..., 1] / 127.5 - 1.0)
            sm = as_[mp[..., 0], mp[..., 1], 0].astype(np.float64)
            crystal = sm >= 200
            fs[..., 0] = np.where(crystal, np.round(GEM_SMOOTH_MIN + (sm - 200) / 55.0 * (255 - GEM_SMOOTH_MIN)),
                                  np.round(sm * 0.85)).clip(0, 255)
            fs[..., 1] = np.where(crystal, 44, 10)
        else:
            # the same crystal mass cut and polished flat: one mirror table over its colour, F0 0.12 so the
            # colour leads face-on and the mirror rises toward grazing
            fn = _n_png(np.zeros((n, n)), np.zeros((n, n)))
            fs[..., 0], fs[..., 1] = 250, 30
    else:
        raise ValueError(mode)
    img = _block_from_face(base, face, bands)
    # block-level _n: the face's normals inside, Faithful's frame as the r013 bevel; _s: face inside, r013's frame
    v = gems_ctm._tilt(n, bands, "TBLR", frozenset())
    bev = np.abs(v).sum(-1) > 0
    bn = fn.copy()
    bn[bev] = _n_png(v[..., 0], v[..., 1])[bev]
    bs = fs.copy()
    t, l, b, r = bands
    frame = np.ones((n, n), bool)
    frame[t:n - b, l:n - r] = False
    bs[frame] = (240, 44, 0, 255)
    atlas = (np.concatenate([img, face], 1), np.concatenate([bn, fn], 1), np.concatenate([bs, fs], 1))
    ys, xs = np.mgrid[0:n, 0:n]
    pmap = np.stack([ys, xs + n], -1)
    return dict(block=(img, bn, bs), atlas=atlas, pmap=pmap)


def ctm_tiles(mat, bands):
    """{i: (albedo, _n, _s)} for the 47 tiles: coords through the atlas; frame-band normals = the r013 bevel."""
    img, an, as_ = mat["atlas"]
    n = img.shape[0]
    maps = gems_ctm.tile_maps(img, bands, pmap=mat["pmap"])
    out = {}
    for i, (edges, inner) in gems_ctm.tile_layout().items():
        mp = maps[i]
        t_img = img[mp[..., 0], mp[..., 1]]
        t_n = an[mp[..., 0], mp[..., 1]].copy()
        t_s = as_[mp[..., 0], mp[..., 1]].copy()
        if i == 0:
            out[i] = mat["block"]
            continue
        v = gems_ctm._tilt(n, bands, edges, inner)
        bev = np.abs(v).sum(-1) > 0
        t_n[bev] = _n_png(v[..., 0], v[..., 1])[bev]
        band = mp[..., 1] < n                                  # pixels read from the block's frame
        t_s[band] = (240, 44, 0, 255)
        out[i] = (t_img, t_n, t_s)
    return out


if __name__ == "__main__":
    f64, patrix, outd = sys.argv[1:4]
    fa = zipfile.ZipFile(f64)
    root = fa.namelist()[0].split("/")[0] + "/"
    d = np.array(Image.open(io.BytesIO(fa.read(root + "assets/minecraft/textures/blocks/diamond_block.png"))).convert("RGBA"))
    bases = {"diamond_block": d, "emerald_block": gems.emerald_from_diamond(d)}
    shape = ["#####..", "#####..", "#####.#", "##.####", "#######"]
    for mode in MATERIALS:
        rows = []
        for name in GEMS:
            mat = material(name, mode, bases[name], gems_ctm.BLOCKS[name], patrix)
            tl = ctm_tiles(mat, gems_ctm.BLOCKS[name])
            for k in range(3):
                fl = gems_ctm.demo_floor({i: t[k] for i, t in tl.items()}, shape)
                fl = fl.copy(); fl[..., 3] = np.where(fl[..., 3] == 0, 0, 255)
                rows.append(Image.fromarray(fl))
        W = Image.new("RGBA", (3 * (rows[0].width + 8), 2 * (rows[0].height + 8)), (40, 40, 40, 255))
        for j, r in enumerate(rows):
            W.paste(r, ((j % 3) * (r.width + 8), (j // 3) * (r.height + 8)))
        W.save("%s/mat_%s.png" % (outd, mode))
        print(mode, "->", "%s/mat_%s.png" % (outd, mode))
