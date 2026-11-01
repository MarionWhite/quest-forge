#!/usr/bin/env python3
"""Connected gem LOOKS for diamond and emerald (r015; owner r014, every gem scene "neither": "These either look plastic or
very noisy. I'm not 100% sure what I'm looking for here, but I know that we are not even close").

r013-r014 tuned one material; round 15 shows five complete, different looks, each copied from something that works,
all on the connected layout the owner asked for (r012: frame only on a group's outer rim, gems_ctm.py):

  facets    the critic's: a few big flat facets per block, the plane structure of Patrix 32x's diamond_block normal
            map (about ten planes, median tilt 22 deg) made exactly planar, each facet one tone of the gem ramp from
            its own tilt (lit from the top left, as every pack draws it) with a light ridge on its lit edges; polished
            (the shader's gem path: smoothness 245, F0 0.17 diamond / 0.12 emerald), so each facet holds its own piece
            of the sky and flashes as a whole.
  staytrue  Stay True's own art, as it ships (16x, read at 4x): diamond's bevel and streaks made seamless inside a
            group, emerald's step-cut rings kept per block. No gem reflection: flat maps, smoothness 0.35, F0 0.04
            (no pixel reaches the gem path; rendered with QF_GEM_SSR 0 as well).
  jewel     a deep, clear stone: a dark saturated body with the light coming from inside. Each block is one cut seen
            through its table (diamond: a brilliant's star of pavilion facets; emerald: a step cut's rings), bright at
            the middle, dark and saturated at the girdle, three small sparkles. The surface is quiet (smoothness 0.80,
            F0 0.05: below the gem path, a faint sky sheen at grazing angles); only the sparkles are polished.
  calm      round 14's best (Faithful's streaks on the deeper ramp, Patrix amethyst crystal normals) with the noise
            taken out: the crystal tilts low-passed and halved, and one even gloss on every face pixel (r014's rough
            gaps switched the shader's gem path on and off per texel, which glitters at distance).
  frost     Soartex Forever's gems as it draws them (64x frosted, pale ice; emerald's rhombus bands): matte, a soft
            sheen (smoothness 0.55, F0 0.04), the face made seamless by quilting, the rim bevelled.

Reference packs are read at build time from C:\\qf-world\\reference-packs (owner's exception, CLAUDE.md); nothing from
them is committed. Output is only ever the private build zip.

    py -3.10 tools/textures/gems_look.py <faithful64.zip> <out_dir>      # flat and lit preview sheets of every look
"""
import io
import os
import sys
import zipfile

import numpy as np
from PIL import Image

import gems
import gems_ctm
import gems_mat

LOOKS = ("facets", "staytrue", "jewel", "calm", "frost")
REF = r"C:\qf-world\reference-packs"
PATRIX = os.path.join(REF, "Patrix 32x", "Patrix_26.3_32x_basic.zip")
STAY_TRUE = os.path.join(REF, "Stay True 1")
SOARTEX = os.path.join(REF, "Soartex Forever", "Soartex Forever.zip")
N = 64
LIGHT = np.array([-0.45, -0.55, 0.70]) / np.linalg.norm([-0.45, -0.55, 0.70])   # top-left, DirectX +y down

# jewel ramps: deeper and more saturated than gems_mat.RAMPS at the bottom, a glowing top that stays coloured
JEWEL = {
    "diamond_block": np.array([(2, 26, 44), (4, 52, 78), (8, 88, 116), (12, 132, 156), (24, 182, 196),
                               (70, 226, 232), (150, 250, 246), (214, 255, 252)], np.float32),
    "emerald_block": np.array([(2, 24, 10), (4, 46, 18), (8, 78, 28), (14, 116, 40), (22, 164, 60),
                               (52, 214, 98), (132, 248, 168), (204, 255, 220)], np.float32),
}


def lum(a):
    return a[..., :3].astype(np.float64) @ np.array([0.2126, 0.7152, 0.0722])


def n_png(vx, vy):
    return gems_mat._n_png(vx, vy)


def s_png(smooth, f0, shape=(N, N)):
    s = np.zeros(shape + (4,), np.uint8)
    s[..., 0], s[..., 1], s[..., 3] = smooth, f0, 255
    return s


def _png(z, name):
    return np.array(Image.open(io.BytesIO(z.read(name))).convert("RGBA"))


def up(a, k):
    return np.repeat(np.repeat(a, k, 0), k, 1)


# --- the connected tiles, shared by every look ----------------------------------------------------------------------
def connect(block, face, bands, bevel=True, frame_s=None):
    """block, face: (img, _n, _s) 64x64; face is what shows inside a group (64-periodic or meant to repeat per block).
    -> dict(block=..., tiles={i: (img, _n, _s)}) with gems_ctm's 47-tile layout: frame bands read from the block,
    the rest from the face; a bevel _n on kept bands (gems_ctm._tilt) unless bevel=False; frame_s overrides _s there."""
    atlas = [np.concatenate([b, f], 1) for b, f in zip(block, face)]
    ys, xs = np.mgrid[0:N, 0:N]
    pmap = np.stack([ys, xs + N], -1)
    maps = gems_ctm.tile_maps(atlas[0], bands, pmap=pmap)
    tiles = {}
    for i, (edges, inner) in gems_ctm.tile_layout().items():
        if i == 0:
            tiles[i] = block
            continue
        mp = maps[i]
        t = [a[mp[..., 0], mp[..., 1]].copy() for a in atlas]
        band = mp[..., 1] < N
        if bevel:
            v = gems_ctm._tilt(N, bands, edges, inner)
            bev = np.abs(v).sum(-1) > 0
            t[1][bev] = n_png(v[..., 0], v[..., 1])[bev]
        if frame_s is not None:
            t[2][band] = frame_s
        tiles[i] = tuple(t)
    return dict(block=block, tiles=tiles)


def frame_normals(n_face, bands):
    """The block's _n: the face's inside, the r013 bevel on the frame bands."""
    v = gems_ctm._tilt(N, bands, "TBLR", frozenset())
    bev = np.abs(v).sum(-1) > 0
    out = n_face.copy()
    out[bev] = n_png(v[..., 0], v[..., 1])[bev]
    return out


# --- facets ---------------------------------------------------------------------------------------------------------
def planar_field(n32, tol=0.09, min_px=10):
    """Patrix's 32x _n -> (labels, vx, vy) with every region exactly planar: 4-connected regions of near-equal normals
    (union-find, |dn| < tol), regions under min_px merged into the most similar neighbour, then each region's mean."""
    vx = n32[..., 0].astype(np.float64) / 127.5 - 1.0
    vy = n32[..., 1].astype(np.float64) / 127.5 - 1.0
    h, w = vx.shape
    par = list(range(h * w))

    def find(i):
        while par[i] != i:
            par[i] = par[par[i]]
            i = par[i]
        return i
    for y in range(h):
        for x in range(w):
            for dy, dx in ((0, 1), (1, 0)):
                yy, xx = y + dy, x + dx
                if yy < h and xx < w and np.hypot(vx[y, x] - vx[yy, xx], vy[y, x] - vy[yy, xx]) < tol:
                    a, b = find(y * w + x), find(yy * w + xx)
                    if a != b:
                        par[a] = b
    lab = np.array([find(i) for i in range(h * w)]).reshape(h, w)
    for _ in range(20):
        ids, cnt = np.unique(lab, return_counts=True)
        small = [i for i, c in zip(ids, cnt) if c < min_px]
        if not small:
            break
        for s in small:
            m = lab == s
            if not m.any():
                continue
            mx, my = vx[m].mean(), vy[m].mean()
            nb = set()
            ys, xs = np.nonzero(m)
            for y, x in zip(ys, xs):
                for dy, dx in ((0, 1), (1, 0), (0, -1), (-1, 0)):
                    yy, xx = y + dy, x + dx
                    if 0 <= yy < h and 0 <= xx < w and lab[yy, xx] != s:
                        nb.add(lab[yy, xx])
            if nb:
                best = min(nb, key=lambda k: np.hypot(vx[lab == k].mean() - mx, vy[lab == k].mean() - my))
                lab[m] = best
    ids = np.unique(lab)
    remap = {k: i for i, k in enumerate(ids)}
    lab = np.vectorize(remap.get)(lab)
    fx, fy = np.zeros(len(ids)), np.zeros(len(ids))
    for i in range(len(ids)):
        fx[i], fy[i] = vx[lab == i].mean(), vy[lab == i].mean()
    return lab, fx, fy


def facets(name, base, bands, refs):
    """Big facets: Patrix's diamond map is a bevelled rim round about six interior planes, 7-30 deg (median 22); the
    packs that draw gem blocks as facets (Faithless, Conquest, Soartex emerald) agree on one cut, a rhombus table with
    a triangle facet in each corner. That cut with Patrix's tilts: a flat table, four corner facets tipped 21 deg
    toward their corners, each split along the diagonal so the sun lands on one half at a time (8 planes + table).
    Straight edges only (45-degree pixel steps); in a connected floor four blocks' corners make one sunken rhombus."""
    ys, xs = (np.mgrid[0:N, 0:N] + 0.5) / N * 2 - 1
    table = np.abs(xs) + np.abs(ys) < 1.0
    qx, qy = np.sign(xs), np.sign(ys)
    half = np.abs(xs) > np.abs(ys)                     # which side of the corner's diagonal
    lab = np.where(table, 0, 1 + (qx > 0) * 1 + (qy > 0) * 2 + half * 4)
    tilt = np.sin(np.radians(21))
    # each half leans toward the corner and a little toward its own edge (Patrix's facets are never symmetric)
    dx = qx * np.where(half, 0.85, 0.53)
    dy = qy * np.where(half, 0.53, 0.85)
    vx = np.where(table, 0.0, dx * tilt)
    vy = np.where(table, 0.0, dy * tilt)
    vz = np.sqrt(np.clip(1 - vx * vx - vy * vy, 0, 1))
    d = vx * LIGHT[0] + vy * LIGHT[1] + vz * LIGHT[2]
    d0 = np.array([d[lab == i].mean() for i in range(9)])
    tf = (d0 - d0.min()) / max(np.ptp(d0), 1e-6)
    t = np.where(table, 0.58, 0.26 + 0.50 * tf[lab])
    # the table: one soft fall from its lit corner, and Faithful's own streak texture, faint, as the stone's body
    t = t + np.where(table, 0.08 * (-(xs + ys) / 2), 0.05 * (1 - (np.abs(xs) + np.abs(ys)) / 2))
    pm = gems_ctm.periodic_map(base, bands)
    fl = lum(base[pm[..., 0], pm[..., 1]])
    t = t + np.clip((fl - fl.mean()) / 255.0, -0.12, 0.12) * 0.45
    # ridges: the lit edge of every facet boundary, one texel
    ridge = np.zeros((N, N), bool)
    tl = np.where(table, 0.58, tf[lab])
    for sy, sx in ((0, 1), (1, 0), (0, -1), (-1, 0)):   # not across the block seam: that edge is a valley
        o = np.roll(np.roll(np.pad(lab, 1, mode="edge"), sy, 0), sx, 1)[1:-1, 1:-1]
        ot = np.roll(np.roll(np.pad(tl, 1, mode="edge"), sy, 0), sx, 1)[1:-1, 1:-1]
        ridge |= (o != lab) & (tl > ot + 0.1)
    t[ridge] += 0.14
    face = np.zeros((N, N, 4), np.uint8)
    face[..., :3] = np.round(gems_mat.ramp(np.clip(t, 0, 1), gems_mat.RAMPS[name])).astype(np.uint8)
    face[..., 3] = 255
    fn = n_png(vx, vy)
    f0 = 44 if name == "diamond_block" else 30
    fs = s_png(245, f0)
    img = gems_mat._block_from_face(base, face, bands)
    block = (img, frame_normals(fn, bands), fs.copy())
    return connect(block, (face, fn, fs), bands, frame_s=(240, f0, 0, 255))


# --- staytrue -------------------------------------------------------------------------------------------------------
def staytrue(name, base, bands, refs):
    im = np.array(Image.open(os.path.join(refs["stay_true"], "assets/minecraft/textures/block/%s.png" % name))
                  .convert("RGBA"))[:16]                                   # frame 0 (the still between glint sweeps)
    img = up(im, 4)
    flat = n_png(np.zeros((N, N)), np.zeros((N, N)))
    s = s_png(90, 10)
    if name == "diamond_block":
        b = (8, 8, 4, 4)                                                   # rim + highlight row/col, dark rim
        pm = gems_ctm.periodic_map(img, b)
        face = img[pm[..., 0], pm[..., 1]]
    else:
        b = (4, 4, 4, 4)                                                   # only the outer rim connects
        face = img.copy()
        table = np.array([0x17, 0xdd, 0x62, 255], np.uint8)                # the step cut's own table green
        face[:4], face[-4:], face[:, :4], face[:, -4:] = table, table, table, table
    block = (img, frame_normals(flat, b), s)
    return connect(block, (face, flat, s), b, frame_s=(90, 10, 0, 255))


# --- jewel ----------------------------------------------------------------------------------------------------------
def _cut(name):
    """(labels, vx, vy, t) of one cut seen from above, 64x64, coordinates -1..1. t: painted brightness 0..1."""
    ys, xs = (np.mgrid[0:N, 0:N] + 0.5) / N * 2 - 1
    r_inf = np.maximum(np.abs(xs), np.abs(ys))
    ang = np.arctan2(ys, xs)
    tilt = np.sin(np.radians(14))
    if name == "diamond_block":
        # a brilliant: octagonal table, eight crown facets
        r_oct = np.maximum(r_inf, (np.abs(xs) + np.abs(ys)) / 1.38)
        table = r_oct < 0.52
        sec = np.floor((ang + np.pi + np.pi / 8) / (np.pi / 4)).astype(int) % 8
        lab = np.where(table, 0, 1 + sec)
        ca = sec * (np.pi / 4) - np.pi
        vx = np.where(table, 0.0, np.cos(ca) * tilt)
        vy = np.where(table, 0.0, np.sin(ca) * tilt)
        vz = np.sqrt(1 - vx * vx - vy * vy)
        crown = vx * LIGHT[0] + vy * LIGHT[1] + vz * LIGHT[2]
        crown = 0.18 + 0.42 * (crown - crown.min()) / max(np.ptp(crown), 1e-6) - 0.16 * np.clip(r_oct - 0.52, 0, 1)
        # through the table: the pavilion's eight mains as a star, bright and dark by turns, brightest at the middle
        star = 0.5 + 0.5 * np.cos(8 * (ang + np.pi / 16))
        core = 1.0 - np.clip(r_oct / 0.52, 0, 1)
        t_table = 0.42 + 0.26 * star * (0.4 + 0.6 * (1 - core)) + 0.32 * core ** 1.5
        t = np.where(table, t_table, crown)
        sparkle = [(-0.30, -0.30), (0.52, -0.10), (0.05, 0.40)]
    else:
        # a step cut: three rings of steps round a rectangular table, the corners cut
        steps = np.digitize(r_inf, [0.42, 0.62, 0.82])                     # 0 table .. 3 outer step
        side = np.where(np.abs(xs) >= np.abs(ys), np.where(xs > 0, 0, 1), np.where(ys > 0, 2, 3))
        lab = np.where(steps == 0, 0, 1 + (steps - 1) * 4 + side)
        dirs = np.array([(1, 0), (-1, 0), (0, 1), (0, -1)], float)
        tl = tilt * (0.6 + 0.4 * steps / 3.0)
        vx = np.where(steps == 0, 0.0, dirs[side][..., 0] * tl)
        vy = np.where(steps == 0, 0.0, dirs[side][..., 1] * tl)
        vz = np.sqrt(1 - vx * vx - vy * vy)
        lit = vx * LIGHT[0] + vy * LIGHT[1] + vz * LIGHT[2]
        lit = (lit - lit.min()) / max(np.ptp(lit), 1e-6)
        ring = 0.62 - 0.11 * steps
        t_steps = ring + 0.22 * (lit - 0.5)
        core = 1.0 - np.clip(r_inf / 0.42, 0, 1)
        # through the table: the pavilion's steps as faint nested rectangles and the corner keel lines
        nest = 0.5 + 0.5 * np.cos(np.pi * r_inf / 0.42 * 3)
        keel = np.exp(-((np.abs(np.abs(xs) - np.abs(ys))) / 0.05) ** 2)
        t_table = 0.50 + 0.30 * core ** 1.2 + 0.07 * nest - 0.10 * keel * (1 - core)
        t = np.where(steps == 0, t_table, t_steps)
        sparkle = [(-0.30, -0.28), (0.66, -0.66), (0.20, 0.30)]
    sp = np.zeros((N, N), bool)
    for sx, sy in sparkle:
        cx, cy = int((sx + 1) / 2 * N), int((sy + 1) / 2 * N)
        sp[cy - 1:cy + 1, cx - 1:cx + 1] = True
        for ddx, ddy in ((-2, 0), (1, 0), (0, -2), (0, 1)):            # a four-point glint, one texel arms
            sp[cy + ddy:cy + ddy + 1, cx + ddx:cx + ddx + 1] = True
    return lab, vx, vy, t, sp


def jewel(name, base, bands, refs):
    lab, vx, vy, t, sp = _cut(name)
    # facet edges: one darker texel where two facets meet (the cut reads at a glance)
    edge = np.zeros((N, N), bool)
    for dy, dx in ((0, 1), (1, 0)):
        edge |= lab != np.roll(np.roll(lab, dy, 0), dx, 1)
    t = np.where(edge, t - 0.05, t)
    t = np.where(sp, 0.97, t)
    face = np.zeros((N, N, 4), np.uint8)
    face[..., :3] = np.round(gems_mat.ramp(np.clip(t, 0, 1), JEWEL[name])).astype(np.uint8)
    face[..., 3] = 255
    fn = n_png(vx, vy)
    fs = s_png(205, 12)
    fs[sp] = (255, 44, 0, 255)                                              # only the sparkles are polished
    b = (2, 2, 2, 2)                                                        # a dark girdle line on the group's rim
    img = face.copy()
    girdle = np.round(JEWEL[name][0]).astype(np.uint8)
    img[:2, :, :3], img[-2:, :, :3], img[:, :2, :3], img[:, -2:, :3] = girdle, girdle, girdle, girdle
    block = (img, frame_normals(fn, b), fs.copy())
    return connect(block, (face, fn, fs), b, frame_s=(205, 12, 0, 255))


# --- calm -----------------------------------------------------------------------------------------------------------
def _calm_parts(name, base, bands, refs):
    from scipy.ndimage import gaussian_filter
    mat = gems_mat.material(name, "faithful", base, bands, refs["patrix"])
    img, an, as_ = mat["atlas"]
    face = img[:, N:].copy()
    f = face[..., :3].astype(np.float64)   # Faithful's streak contrast eased a quarter (the critic's diagonal quilt)
    face[..., :3] = np.round(f.reshape(-1, 3).mean(0) + 0.75 * (f - f.reshape(-1, 3).mean(0))).astype(np.uint8)
    fn = an[:, N:].astype(np.float64)
    vx = gaussian_filter(fn[..., 0] / 127.5 - 1, 1.2, mode="wrap") * 0.5
    vy = gaussian_filter(fn[..., 1] / 127.5 - 1, 1.2, mode="wrap") * 0.5
    fn = n_png(vx, vy)
    fs = s_png(240, 34)
    bimg = gems_mat._block_from_face(mat["block"][0], face, bands)
    return dict(block=(bimg, frame_normals(fn, bands), fs.copy()), face=(face, fn, fs), bands=bands, s=(240, 34))


def calm(name, base, bands, refs):
    p = _calm_parts(name, base, bands, refs)
    return connect(p["block"], p["face"], p["bands"], frame_s=p["s"] + (0, 255))


# --- frost ----------------------------------------------------------------------------------------------------------
def _frost_parts(name, base, bands, refs):
    z = zipfile.ZipFile(refs["soartex"])
    img = _png(z, "assets/minecraft/textures/block/%s.png" % name)[:N]
    assert img.shape[:2] == (N, N), img.shape
    from scipy.ndimage import gaussian_filter
    b = (6, 6, 6, 6)                       # Soartex's soft light rim runs ~5 px in: it stays on the group's outline
    pm = gems_ctm.periodic_map(img, b)
    face = img[pm[..., 0], pm[..., 1]].copy()
    f = face[..., :3].astype(np.float64)   # the quilted face keeps a block-scale light/dark swell: take it out
    lo = np.stack([gaussian_filter(f[..., k], 9, mode="wrap") for k in range(3)], -1)
    face[..., :3] = np.clip(np.round(f - lo + f.reshape(-1, 3).mean(0)), 0, 255).astype(np.uint8)
    flat = n_png(np.zeros((N, N)), np.zeros((N, N)))
    s = s_png(140, 10)
    return dict(block=(img, frame_normals(flat, (2, 2, 2, 2)), s), face=(face, flat, s), bands=b, s=(140, 10))


def frost(name, base, bands, refs):
    p = _frost_parts(name, base, bands, refs)
    return connect(p["block"], p["face"], p["bands"], bevel=False, frame_s=p["s"] + (0, 255))


# --- the frost -> calm slider (r016) --------------------------------------------------------------------------------
# Owner r015 (gems15-close, picked E): "imagine a slider between the frost and the round 14 calmed, and begin sliding
# from the frost towards that one". Step t (0 = frost, 1 = calm) moves every axis that tells the two apart together:
#   colour   the face's mean colour, frost's pale ice -> calm's deep gem ramp (t)
#   pattern  the two faces' detail (each minus its mean) crossfaded by t, then rescaled to the contrast interpolated
#            between the two (a plain crossfade of two unrelated patterns loses ~30 % of its contrast: mud)
#   relief   calm's softened crystal normals, scaled by t (frost is flat)
#   gloss    smoothness / F0 per step (SLIDE_S). The shader's gem path is a switch (smoothness > 224 and F0 > 25.5:
#            body light x0.4, light from inside, real-scene reflection); below it a plain sky sheen. Steps 1-2 stay
#            under it, 3-4 are over it, so the slider shows both sides of that switch.
# Both faces are 64-periodic, so every blend is too: each step connects exactly as its ends do (frost's 6-px bands).
SLIDE_S = {20: (170, 14), 40: (205, 18), 60: (228, 27), 80: (234, 30)}
SLIDE = tuple("slide%d" % k for k in SLIDE_S)


def _nv(n):
    return n[..., 0].astype(np.float64) / 127.5 - 1.0, n[..., 1].astype(np.float64) / 127.5 - 1.0


def slide(name, base, bands, refs, pct):
    t = pct / 100.0
    fr, ca = _frost_parts(name, base, bands, refs), _calm_parts(name, base, bands, refs)
    b = tuple(max(x, y) for x, y in zip(fr["bands"], ca["bands"]))
    Ff, Cf = fr["face"][0][..., :3].astype(np.float64), ca["face"][0][..., :3].astype(np.float64)
    mF, mC = Ff.reshape(-1, 3).mean(0), Cf.reshape(-1, 3).mean(0)
    sd = lambda a: lum(a).std()
    d = (1 - t) * (Ff - mF) + t * (Cf - mC)
    k = ((1 - t) * sd(Ff - mF) + t * sd(Cf - mC)) / max(sd(d), 1e-6)
    m = (1 - t) * mF + t * mC

    def mix(fa, ca_):
        o = fa.copy()
        dd = (1 - t) * (fa[..., :3].astype(np.float64) - mF) + t * (ca_[..., :3].astype(np.float64) - mC)
        o[..., :3] = np.clip(np.round(m + k * dd), 0, 255).astype(np.uint8)
        o[..., 3] = 255
        return o

    def nmix(na, nb):
        ax, ay = _nv(na)
        bx, by = _nv(nb)
        return n_png((1 - t) * ax + t * bx, (1 - t) * ay + t * by)
    sm, f0 = SLIDE_S[pct]
    s = s_png(sm, f0)
    face = (mix(fr["face"][0], ca["face"][0]), nmix(fr["face"][1], ca["face"][1]), s)
    block = (mix(fr["block"][0], ca["block"][0]), nmix(fr["block"][1], ca["block"][1]), s.copy())
    return connect(block, face, b, bevel=False, frame_s=(sm, f0, 0, 255))


def material(name, look, base, bands, refs=None):
    """-> dict(block=(img, _n, _s), tiles={i: (img, _n, _s)}) for one gem block and look (module docstring)."""
    refs = dict(dict(patrix=PATRIX, stay_true=STAY_TRUE, soartex=SOARTEX), **(refs or {}))
    if look.startswith("slide"):
        return slide(name, base, bands, refs, int(look[5:]))
    return {"facets": facets, "staytrue": staytrue, "jewel": jewel, "calm": calm, "frost": frost}[look](
        name, base, bands, refs)


# --- previews -------------------------------------------------------------------------------------------------------
def lit(img, n, s, L=(0.55, -0.35, 0.76)):
    """A rough preview: albedo x (0.35 + 0.65 lambert) + a white sky sheen by smoothness (no shader, for layout)."""
    vx = n[..., 0] / 127.5 - 1
    vy = n[..., 1] / 127.5 - 1
    vz = np.sqrt(np.clip(1 - vx * vx - vy * vy, 0, 1))
    L = np.array(L) / np.linalg.norm(L)
    d = np.clip(vx * L[0] + vy * L[1] + vz * L[2], 0, 1)
    out = img[..., :3] * (0.35 + 0.65 * d)[..., None]
    H = (L + np.array([0, 0, 1])) / np.linalg.norm(L + np.array([0, 0, 1]))
    sp = np.clip(vx * H[0] + vy * H[1] + vz * H[2], 0, 1) ** (2 + 200 * (s[..., 0] / 255.0) ** 4)
    out = out + 255 * sp[..., None] * (s[..., 1] / 255.0)[..., None] * 2
    o = np.zeros(img.shape, np.uint8)
    o[..., :3] = np.clip(out, 0, 255)
    o[..., 3] = 255
    return o


if __name__ == "__main__":
    f64, outd = sys.argv[1:3]
    fa = zipfile.ZipFile(f64)
    root = fa.namelist()[0].split("/")[0] + "/"
    d = np.array(Image.open(io.BytesIO(fa.read(root + "assets/minecraft/textures/blocks/diamond_block.png"))).convert("RGBA"))
    bases = {"diamond_block": d, "emerald_block": gems.emerald_from_diamond(d)}
    shape = ["#####..", "#####..", "#####.#", "##.####", "#######"]
    looks = sys.argv[3:] or LOOKS
    for look in looks:
        rows = []
        for name in gems_mat.GEMS:
            mat = material(name, look, bases[name], gems_ctm.BLOCKS[name])
            tl = mat["tiles"]
            fl = gems_ctm.demo_floor({i: t[0] for i, t in tl.items()}, shape)
            fll = gems_ctm.demo_floor({i: lit(*t) for i, t in tl.items()}, shape)
            for f in (fl, fll):
                f = f.copy()
                f[..., 3] = np.where(f[..., 3] == 0, 0, 255)
                rows.append(Image.fromarray(f))
        W = Image.new("RGBA", (2 * (rows[0].width + 8), 2 * (rows[0].height + 8)), (40, 40, 40, 255))
        for j, r in enumerate(rows):
            W.paste(r, ((j % 2) * (r.width + 8), (j // 2) * (r.height + 8)))
        W.save("%s/look_%s.png" % (outd, look))
        print(look, "->", "%s/look_%s.png" % (outd, look))
