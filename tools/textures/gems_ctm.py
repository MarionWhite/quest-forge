#!/usr/bin/env python3
"""Connected gem and metal blocks (r013; owner, r012 gems-lit: "I think they should have connected textures though").

A floor or pillar of diamond, emerald, gold, iron or lapis blocks reads as ONE polished slab: the block's own frame
(Faithful 64x's bevel) is drawn only on the outer rim of a connected group, and the face inside it continues across
block boundaries without a seam.

Path (evidence in ops/checkpoints/r013-textures.md): Angelica 2.2.33 bundles MCPatcherForge, whose `method=ctm`
takes the standard 47-tile MCPatcher layout (TileOverrideImpl$CTM; NEIGHBOR_MAP below is its table, read from
TileOverride's static initialiser with javap). No reference pack in C:\\qf-world\\reference-packs or Faithful's
1.7.10 zips has connected gem or metal blocks, so the layout is the one Stay True and Faithful use for their glass,
and the art is the block's own Faithful 64x pixels:

  1. periodic_map(): the face inside the frame (59x59 at 64x) is made 64-periodic by quilting (Efros-Freeman): a strip
     of the same face is laid over each wrap seam and joined along the minimum-difference cut, so every pixel is still
     one of Faithful's own pixels (no blending, no new colours).
  2. tiles(): tile i = that periodic face, plus the block's own frame bands on the edges that tile keeps, plus a small
     concave corner where two connected neighbours meet around a missing diagonal. Tile 0 (all edges) is the block
     exactly as Faithful draws it, so a lone block and the held item look unchanged.
  3. normals(): LabPBR _n (DirectX, +G down). The frame bands are a bevel (the outline tilts 27 deg outward, the
     highlight line 11 deg); the face is flat ("flat"), or its glint streaks are flat tilted facets ("facet"). Either
     way there is no per-block dome, so a connected floor has no per-block pattern in its reflection either (r012's
     dome is what made option C's reflection "wobble like wet plastic" and checker the sun-behind floors).

Redstone is left out on purpose: Faithful's redstone block is a dark vignette blob inside a bright rim, so any
periodic face still shows one blob per block (a grid); connecting it needs new art.

    py -3.10 tools/textures/gems_ctm.py <faithful64.zip> <preview.png>     # contact sheet of all tiles
"""
import io
import sys
import zipfile

import numpy as np
from PIL import Image

# MCPatcher's neighbour bits -> tile (Angelica 2.2.33, com/prupe/mcpatcher/ctm/TileOverride.neighborMap).
# Bits: 0 W, 1 SW, 2 S, 3 SE, 4 E, 5 NE, 6 N, 7 NW (a set bit = that neighbour connects).
NEIGHBOR_MAP = [
    0, 3, 0, 3, 12, 5, 12, 15, 0, 3, 0, 3, 12, 5, 12, 15, 1, 2, 1, 2, 4, 7, 4, 29, 1, 2, 1, 2, 13, 31, 13, 14,
    0, 3, 0, 3, 12, 5, 12, 15, 0, 3, 0, 3, 12, 5, 12, 15, 1, 2, 1, 2, 4, 7, 4, 29, 1, 2, 1, 2, 13, 31, 13, 14,
    36, 17, 36, 17, 24, 19, 24, 43, 36, 17, 36, 17, 24, 19, 24, 43, 16, 18, 16, 18, 6, 46, 6, 21, 16, 18, 16, 18,
    28, 9, 28, 22, 36, 17, 36, 17, 24, 19, 24, 43, 36, 17, 36, 17, 24, 19, 24, 43, 37, 40, 37, 40, 30, 8, 30, 34,
    37, 40, 37, 40, 25, 23, 25, 45, 0, 3, 0, 3, 12, 5, 12, 15, 0, 3, 0, 3, 12, 5, 12, 15, 1, 2, 1, 2, 4, 7, 4, 29,
    1, 2, 1, 2, 13, 31, 13, 14, 0, 3, 0, 3, 12, 5, 12, 15, 0, 3, 0, 3, 12, 5, 12, 15, 1, 2, 1, 2, 4, 7, 4, 29, 1, 2,
    1, 2, 13, 31, 13, 14, 36, 39, 36, 39, 24, 41, 24, 27, 36, 39, 36, 39, 24, 41, 24, 27, 16, 42, 16, 42, 6, 20, 6,
    10, 16, 42, 16, 42, 28, 35, 28, 44, 36, 39, 36, 39, 24, 41, 24, 27, 36, 39, 36, 39, 24, 41, 24, 27, 37, 38, 37,
    38, 30, 11, 30, 32, 37, 38, 37, 38, 25, 33, 25, 26]

# Frame band widths in Faithful 64x (rows/cols whose luminance differs from the face; measured 2026-10-29):
# (top, left, bottom, right). Diamond and gold: 2 px outline + 1 px highlight on the lit (top/left) sides.
BLOCKS = {
    "diamond_block": (3, 3, 2, 2),
    "emerald_block": (3, 3, 2, 2),     # gems.py: the diamond's art re-toned
    "gold_block": (3, 3, 2, 2),
    "iron_block": (3, 2, 2, 2),
    "lapis_block": (2, 2, 2, 2),
}

# "facet" normals only where the face's brightest tones are glint streaks (iron's are plate seams, lapis's are noise).
FACETED = {"diamond_block", "emerald_block", "gold_block"}


def tile_layout():
    """{tile: (kept edges "TBLR", inner corners {"TL","TR","BL","BR"})}, derived from NEIGHBOR_MAP and checked to be
    consistent for every mask that reaches the tile."""
    out = {}
    for m in range(256):
        W, SW, S, SE, E, NE, N, NW = ((m >> b) & 1 for b in range(8))
        edges = "".join(e for e, c in (("T", N), ("B", S), ("L", W), ("R", E)) if not c)
        inner = frozenset(k for k, a, b, d in (("TL", N, W, NW), ("TR", N, E, NE), ("BL", S, W, SW), ("BR", S, E, SE))
                          if a and b and not d)
        t = NEIGHBOR_MAP[m]
        if t in out and out[t] != (edges, inner):
            raise AssertionError("tile %d: %r vs %r" % (t, out[t], (edges, inner)))
        out[t] = (edges, inner)
    assert sorted(out) == list(range(47))
    return out


def _dp_cut(e, wrap=False):
    """Minimum-error path through e (rows, k) from the first row to the last, moving at most one column per row.
    wrap: the rows themselves wrap around (a seam across a periodic image), so the path must end within one column
    of where it started. Returns (column per row, cost)."""
    R, K = e.shape
    best = None
    for s in (range(K) if wrap else [None]):
        c = e.copy()
        if s is not None:
            c[0, :] = np.inf
            c[0, s] = e[0, s]
        back = np.zeros((R, K), int)
        for y in range(1, R):
            for x in range(K):
                lo, hi = max(0, x - 1), min(K, x + 2)
                j = lo + int(np.argmin(c[y - 1, lo:hi]))
                back[y, x] = j
                c[y, x] += c[y - 1, j]
        ends = range(K) if s is None else range(max(0, s - 1), min(K, s + 2))
        x = min(ends, key=lambda i: c[-1, i])
        if best is not None and c[-1, x] >= best[1]:
            continue
        path = [x]
        for y in range(R - 1, 0, -1):
            x = back[y, x]
            path.append(x)
        best = (path[::-1], float(c[-1, path[0]]))
    return best


def _widen(src, coords, size, ov_l=8, ov_r=6, wrap=False):
    """coords (h, w, 2) -> (h, size, 2), periodic along axis 1: a strip of the same image covers the wrap seam and the
    missing columns, joined to both sides along minimum-difference cuts (the strip with the cheapest cuts wins)."""
    h, w = coords.shape[:2]
    W = ov_l + (size - w) + ov_r
    col = lambda C: src[C[..., 0], C[..., 1]]
    best = None
    for sx in range(0, w - W + 1):
        strip = coords[:, sx:sx + W]
        el = np.linalg.norm(col(coords[:, w - ov_l:]) - col(strip[:, :ov_l]), axis=-1)
        er = np.linalg.norm(col(coords[:, :ov_r]) - col(strip[:, W - ov_r:]), axis=-1)
        pl, cl = _dp_cut(el, wrap)
        pr, cr = _dp_cut(er, wrap)
        if best is None or cl + cr < best[0]:
            best = (cl + cr, sx, pl, pr)
    _, sx, pl, pr = best
    strip = coords[:, sx:sx + W]
    out = np.zeros((h, size, 2), int)
    out[:, :w] = coords
    for y in range(h):
        for k in range(W):
            X = (w - ov_l + k) % size
            if k < ov_l:
                take = k >= pl[y]
            elif k >= W - ov_r:
                take = k - (W - ov_r) < pr[y]
            else:
                take = True
            if take:
                out[y, X] = strip[y, k]
    return out


def periodic_map(img, bands):
    """(n, n, 2) source coordinates into img: the face inside the frame bands, made n-periodic (module docstring)."""
    n = img.shape[0]
    t, l, b, r = bands
    src = img[..., :3].astype(np.float64)
    ys, xs = np.mgrid[t:n - b, l:n - r]
    coords = np.stack([ys, xs], -1)
    H = _widen(src, coords, n)                                        # periodic in x, still h rows
    V = _widen(src, H.transpose(1, 0, 2), n, wrap=True)               # rows: cuts wrap around the x period
    return V.transpose(1, 0, 2)


def _band_src(n, bands, edges):
    """(n, n, 2) source coords for each tile pixel that belongs to a kept frame band, -1 elsewhere. A band runs the
    whole edge; where the perpendicular edge is open, the band continues with its own middle pixels."""
    t, l, b, r = bands
    mid = n // 2
    S = -np.ones((n, n, 2), int)
    ys, xs = np.mgrid[0:n, 0:n]

    def along(v, lo, hi, keep_lo, keep_hi):
        # coordinate along a band: inside a kept corner keep it, inside an open corner use the band's middle
        v = v.copy()
        v[(v < lo) & ~keep_lo] = mid - lo + v[(v < lo) & ~keep_lo]
        v[(v >= n - hi) & ~keep_hi] = mid + (v[(v >= n - hi) & ~keep_hi] - (n - hi))
        return v
    K = {e: np.full((n, n), e in edges) for e in "TBLR"}
    if "T" in edges:
        m = ys < t
        S[m] = np.stack([ys, along(xs, l, r, K["L"], K["R"])], -1)[m]
    if "B" in edges:
        m = ys >= n - b
        S[m] = np.stack([ys, along(xs, l, r, K["L"], K["R"])], -1)[m]
    if "L" in edges:
        m = xs < l
        S[m] = np.stack([along(ys, t, b, K["T"], K["B"]), xs], -1)[m]
    if "R" in edges:
        m = xs >= n - r
        S[m] = np.stack([along(ys, t, b, K["T"], K["B"]), xs], -1)[m]
    return S


def _inner_corner(n, bands, which):
    """Concave corner (two connected neighbours around a missing diagonal): the two neighbours' frame bands meet
    here, so the outline turns the corner in a (band x band) square. Returns its source coords (h, w, 2): per pixel,
    the band whose outline is nearer (the horizontal band's row or the vertical band's column, from the middle)."""
    t, l, b, r = bands
    mid = n // 2
    h = t if which[0] == "T" else b
    w = l if which[1] == "L" else r
    patch = np.zeros((h, w, 2), int)
    for y in range(h):
        for x in range(w):
            dy = y if which[0] == "T" else h - 1 - y          # distance from the tile's horizontal edge
            dx = x if which[1] == "L" else w - 1 - x
            if dy <= dx:
                patch[y, x] = (dy if which[0] == "T" else n - 1 - dy, mid)
            else:
                patch[y, x] = (mid, dx if which[1] == "L" else n - 1 - dx)
    return patch


def tile_maps(img, bands, pmap=None):
    """{i: (n, n, 2) source coords into the block texture} for the 47 ctm tiles (module docstring). The builder
    applies the same maps to the block's _s, so every tile keeps the block's own material per pixel."""
    n = img.shape[0]
    pmap = periodic_map(img, bands) if pmap is None else pmap
    ys, xs = np.mgrid[0:n, 0:n]
    ident = np.stack([ys, xs], -1)
    out = {}
    for i, (edges, inner) in tile_layout().items():
        if i == 0:
            out[i] = ident.copy()
            continue
        tl = pmap.copy()
        S = _band_src(n, bands, edges)
        m = S[..., 0] >= 0
        tl[m] = S[m]
        for c in inner:
            p = _inner_corner(n, bands, c)
            h, w = p.shape[:2]
            y0 = 0 if c[0] == "T" else n - h
            x0 = 0 if c[1] == "L" else n - w
            tl[y0:y0 + h, x0:x0 + w] = p
        out[i] = tl
    return out


def tiles(img, bands, pmap=None):
    """{i: (n, n, 4) uint8} for the 47 ctm tiles of one block face."""
    return {i: img[m[..., 0], m[..., 1]] for i, m in tile_maps(img, bands, pmap).items()}


def _tilt(n, bands, edges, inner, outline=0.45, highlight=0.19):
    """(n, n, 2) normal x/y (DirectX, +y down) for the frame bands of one tile: the outline (outer 2 px) tilts
    `outline` (sin, 27 deg), any band pixel inside it `highlight` (11 deg), always outward."""
    t, l, b, r = bands
    v = np.zeros((n, n, 2))
    ys, xs = np.mgrid[0:n, 0:n]

    def amt(d, w):
        return np.where(d < 2, outline, highlight) * (d < w)
    if "T" in edges:
        v[..., 1] -= amt(ys, t)
    if "B" in edges:
        v[..., 1] += amt(n - 1 - ys, b)
    if "L" in edges:
        v[..., 0] -= amt(xs, l)
    if "R" in edges:
        v[..., 0] += amt(n - 1 - xs, r)
    for c in inner:                    # a concave corner tilts inward-diagonal: the two neighbours' bevels meet
        h = t if c[0] == "T" else b
        w = l if c[1] == "L" else r
        sy, sx = (-1 if c[0] == "T" else 1), (-1 if c[1] == "L" else 1)
        y0 = 0 if c[0] == "T" else n - h
        x0 = 0 if c[1] == "L" else n - w
        v[y0:y0 + h, x0:x0 + w] = (sx * highlight, sy * highlight)
    return v


def normals(img, tile_imgs, bands, mode="flat", facet=0.17):
    """{i: LabPBR _n} for tiles(): flat face + bevelled frame bands; mode "facet": the face's bright glint tones
    (the top three luminance levels of the face, Faithful's diagonal streaks) are flat facets tilted `facet`
    (sin, 10 deg) toward the top-left light, so a streak flashes as one sharp plane instead of a smooth dome.
    B (AO) and A (height) 255."""
    n = img.shape[0]
    out = {}
    lum = lambda a: 0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]
    t, l, b, r = bands
    face_levels = np.unique(np.round(lum(img[t:n - b, l:n - r].astype(np.float64)), 1))
    bright = face_levels[-3:] if len(face_levels) > 4 else face_levels[-1:]
    for i, (edges, inner) in tile_layout().items():
        v = _tilt(n, bands, edges if i else "TBLR", inner if i else frozenset())
        if mode == "facet":
            L = np.round(lum(tile_imgs[i].astype(np.float64)), 1)
            f = np.isin(L, bright) & (np.abs(v).sum(-1) == 0)
            v[f] = (-facet * 0.7071, -facet * 0.7071)
        nm = np.zeros((n, n, 4), np.uint8)
        nm[..., 0] = np.clip(np.round((v[..., 0] + 1.0) * 127.5), 0, 255)
        nm[..., 1] = np.clip(np.round((v[..., 1] + 1.0) * 127.5), 0, 255)
        nm[..., 2] = 255
        nm[..., 3] = 255
        out[i] = nm
    return out


def rule(name):
    """The .properties for one block's ctm folder (matchTiles = the block texture; connect=tile by default)."""
    return "matchTiles=%s\nmethod=ctm\ntiles=0-46\nconnect=tile\nfaces=all\n" % name


def sheet(tile_imgs, scale=2):
    """Contact sheet in the standard 12-wide MCPatcher template order."""
    n = tile_imgs[0].shape[0] * scale
    W = Image.new("RGBA", (12 * (n + 2), 4 * (n + 2)), (40, 40, 40, 255))
    for i, t in tile_imgs.items():
        W.paste(Image.fromarray(t).resize((n, n), Image.NEAREST), ((i % 12) * (n + 2), (i // 12) * (n + 2)))
    return W


def demo_floor(tile_imgs, shape):
    """A floor of `shape` (list of strings, '#' = block) laid with the tiles MCPatcher would pick."""
    rows, cols = len(shape), len(shape[0])
    n = tile_imgs[0].shape[0]
    out = np.zeros((rows * n, cols * n, 4), np.uint8)
    at = lambda y, x: 0 <= y < rows and 0 <= x < cols and shape[y][x] == "#"
    for y in range(rows):
        for x in range(cols):
            if not at(y, x):
                continue
            nb = [at(y, x - 1), at(y + 1, x - 1), at(y + 1, x), at(y + 1, x + 1), at(y, x + 1), at(y - 1, x + 1),
                  at(y - 1, x), at(y - 1, x - 1)]
            m = sum(1 << k for k, c in enumerate(nb) if c)
            out[y * n:(y + 1) * n, x * n:(x + 1) * n] = tile_imgs[NEIGHBOR_MAP[m]]
    return out


if __name__ == "__main__":
    zp, outp = sys.argv[1], sys.argv[2]
    z = zipfile.ZipFile(zp)
    rows = []
    for name, bands in BLOCKS.items():
        if name == "emerald_block":
            continue
        p = next(q for q in z.namelist() if q.endswith("textures/blocks/" + name + ".png"))
        img = np.array(Image.open(io.BytesIO(z.read(p))).convert("RGBA"))
        img = img[:img.shape[1]]
        tl = tiles(img, bands)
        floor = demo_floor(tl, ["#####..", "#####..", "#####.#", "##.####", "#######"])
        rows.append(Image.fromarray(floor))
    W = Image.new("RGBA", (sum(r.width for r in rows) + 10 * len(rows), rows[0].height), (40, 40, 40, 255))
    x = 0
    for r in rows:
        W.paste(r, (x, 0))
        x += r.width + 10
    W.save(outp)
