#!/usr/bin/env python3
"""Leaves for QF Textures r010: Faithful 64x's own leaf art made denser and darker, after the way
Stay True builds its canopies (studied from the owner's r009 screenshots, never its pixels), plus
the leaf-edge texture for the leaf frills (ops/checkpoints/r010-leaf-frills.md).

    py -3.10 tools/textures/leaves_dense.py <faithful64.zip> <preview.png> [<faithful32.zip>]
    (columns: faithful | rim | fine (crowns without the 32x zip) | frill)

Directions (all grey, biome-tinted in game like vanilla):
  faithful  Faithful 64x as is (the owner's pick in all three r009 leaf scenes).
  dense     a mirrored, shifted, darker copy of Faithful's own leaves behind it fills most see-through
            holes, so a canopy reads as a mass with depth instead of a sieve (faithless-study item 13).
  crowns    dense + a tileable large-scale light pattern: each ~32 px cluster gets a lit crown and a
            dark underside (Stay True's value structure), so the canopy reads as clumps from afar.
  rim       dense inside, but Faithful's own see-through holes kept in a wavy band 3-10 px wide along the
            tile edge, so a canopy is a mass yet its outline stays ragged (r010 review: dense and crowns
            turned every leaf block into a hard-edged opaque cube).
  fine      Faithful 32x's leaves (smaller, clustered: the closest licensed art to Stay True's grain),
            four mirrored copies per 64 px tile = half-size leaves at 64x pixel size, then rim.
frill(...)  whole Faithful leaves (connected units, never cut mid-leaf) inside a bottom-heavy blob, on
            transparency: the texture for the outward frill quads.

Faithful 64x is under the Faithful licence (credited in CREDITS.txt / LICENSE-Faithful.txt).
"""
import io
import sys
import zipfile

import numpy as np
from PIL import Image
from scipy import ndimage

KINDS = ["oak", "big_oak", "birch", "jungle", "acacia"]          # spruce keeps its own needles
TINTS = {"oak": (72, 181, 24), "big_oak": (72, 181, 24), "birch": (128, 167, 85), "jungle": (48, 187, 11), "acacia": (174, 164, 42)}


def read_faithful(zp, name):
    z = zipfile.ZipFile(zp)
    for p in z.namelist():
        if p.endswith("textures/blocks/" + name):
            return np.array(Image.open(io.BytesIO(z.read(p))).convert("RGBA")).astype(np.float32)
    raise KeyError(name)


def _over(dst, src):
    m = src[..., 3:4] > 25
    return np.where(m, src, dst)


def dense(leaf, back=0.58, shifts=((21, 13), (-11, 29))):
    """Darker mirrored copies of the same leaves behind, wrapped (the tile repeats), then Faithful's
    own layer on top: the holes close with leaves in shadow, so it reads as depth."""
    out = np.zeros_like(leaf)
    for i, (dx, dy) in enumerate(shifts):
        c = leaf[:, ::-1] if i % 2 == 0 else leaf[::-1, :]
        c = np.roll(np.roll(c, dy, 0), dx, 1).copy()
        c[..., :3] *= back - 0.08 * i
        out = _over(out, c)
    return _over(out, leaf)


def _periodic_noise(size, cells, seed):
    """Smooth noise that tiles: random values on a cells x cells torus, bicubic-upsampled with wrap."""
    rng = np.random.default_rng(seed)
    g = rng.random((cells, cells)).astype(np.float32)
    big = np.tile(g, (3, 3))
    im = Image.fromarray(big, "F").resize((size * 3, size * 3), Image.BICUBIC)
    return np.array(im)[size:2 * size, size:2 * size]


def crowns(leaf, seed=5, depth=0.30):
    """dense + clumps: a 2x2-cell tileable light field; its downward slope (lit from above) and
    its value make lit crowns on top of each clump and dark undersides."""
    d = dense(leaf)
    n = _periodic_noise(leaf.shape[0], 2, seed)
    n = (n - n.min()) / max(n.max() - n.min(), 1e-6)
    up = np.roll(n, 3, 0) - n                     # > 0 where the field rises toward the top: a crown
    light = 1.0 + depth * (n - 0.5) * 1.2 + depth * np.clip(-up * 6, -0.6, 0.6)
    d = d.copy()
    d[..., :3] = np.clip(d[..., :3] * light[..., None], 0, 255)
    return d


def rim(leaf, lo=-8, hi=8, seed=11, d=None):
    """dense() in the core, the original alpha (Faithful's holes) in a wavy band along the tile edge.
    lo < 0: some stretches of edge get no band at all, so neighbouring blocks don't print a grid."""
    size = leaf.shape[0]
    d = dense(leaf) if d is None else d
    y, x = np.mgrid[0:size, 0:size]
    edge = np.minimum(np.minimum(x, size - 1 - x), np.minimum(y, size - 1 - y)).astype(np.float32)
    n = _periodic_noise(size, 6, seed)
    n = (n - n.min()) / max(n.max() - n.min(), 1e-6)
    band = edge < lo + (hi - lo) * n * size / 64.0
    out = d.copy()
    out[band] = leaf[band]
    return out


def fine(leaf32):
    """Faithful 32x tiled 2x2 (seamless; half-size leaves). The darker back layers are shifted by
    offsets that are not multiples of 32 and a 64-periodic light field lies over it all, so only the
    front layer repeats inside a block. (Mirrored quadrants were tried: they print kaleidoscopes.)"""
    t = np.tile(leaf32, (2, 2, 1))
    d = crowns(t, seed=7, depth=0.12)          # 0.26 (render t10lf) printed dark stains on every block of a crown
    return rim(t, d=d)


def frill(leaf, seed=0):
    """Whole leaves inside a bottom-heavy blob (wide at the base, ragged leafy top), transparent
    elsewhere. The frill quad's base sits on the leaf block's face."""
    size = leaf.shape[0]
    d = dense(leaf)
    L = d[..., :3].mean(-1)
    units, nu = ndimage.label((d[..., 3] > 25) & (L > 0.62 * L[d[..., 3] > 25].max()))
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:size, 0:size] / (size - 1.0)
    # the blob: full at the base, a wavy top edge between 35% and 75% of the height
    wav = 0.55 + 0.12 * np.sin(x * np.pi * 3 + rng.random() * 6) + 0.08 * np.sin(x * np.pi * 7 + rng.random() * 6)
    blob = (1 - y) < wav
    keep = np.zeros(size * size, bool).reshape(size, size)
    for u in range(1, nu + 1):
        m = units == u
        if m.sum() < 12:                                       # crumbs, not leaves
            continue
        cy, cx = ndimage.center_of_mass(m)
        if blob[int(cy), int(cx)]:
            keep |= ndimage.binary_dilation(m, iterations=1)   # the leaf with its own outline
    keep |= (1 - y) < wav * 0.45                               # a solid base, its edge as wavy as the top
    out = d.copy()
    out[~keep, 3] = 0
    out[keep, 3] = np.where(out[keep, 3] > 25, 255, 0)
    return out


def tint(a, rgb):
    t = a.copy()
    t[..., :3] = a[..., :3] * np.array(rgb, np.float32) / 255.0
    return t


def main():
    zp, outp = sys.argv[1], sys.argv[2]
    k, rep = 3, 3
    rows = []
    for kind in KINDS:
        leaf = read_faithful(zp, "leaves_%s.png" % kind)
        tiles = [leaf, rim(leaf), fine(read_faithful(sys.argv[3], "leaves_%s.png" % kind)) if len(sys.argv) > 3 else crowns(leaf), frill(leaf)]
        row = []
        for t in tiles:
            tt = tint(t, TINTS[kind])
            big = np.tile(tt, (rep, rep, 1)) if t is not tiles[3] else tt
            im = Image.fromarray(np.clip(big, 0, 255).astype(np.uint8), "RGBA")
            im = im.resize((im.width * k // (1 if t is not tiles[3] else 1), im.height * k), Image.NEAREST)
            bg = Image.new("RGBA", (64 * rep * k, 64 * rep * k), (135, 175, 220, 255))
            bg.alpha_composite(im, (0, 64 * rep * k - im.height))
            row.append(bg)
        rows.append(row)
    W = 4 * (64 * rep * k + 6)
    sheet = Image.new("RGBA", (W, len(rows) * (64 * rep * k + 6)), (255, 0, 255, 255))
    for r, row in enumerate(rows):
        for c, im in enumerate(row):
            sheet.alpha_composite(im, (c * (64 * rep * k + 6), r * (64 * rep * k + 6)))
    sheet = sheet.resize((sheet.width // 2, sheet.height // 2), Image.NEAREST)
    sheet.save(outp)


if __name__ == "__main__":
    main()
