#!/usr/bin/env python3
"""Ripe carrot and potato variants for the crop-variant hook (qf-tweaks CropVariants, r010; the owner
said yes in ops/DECISIONS.md). Each crop block draws one of these by a hash of its position, so a field
never tiles: Stay True's technique for its fields (studied from the owner's r009 screenshots, never its
pixels). Built from Faithful 64x's own ripe stage, like wheat_dense.py:

  - back copies of the plant's leafy part (never its roots/tubers), mirrored, shifted and darker, so the
    row reads as a lush mass instead of three separate sprigs;
  - each variant a different height (0.80-1.0 of the tile) and its own shifts;
  - potatoes: two of the four variants carry a few small white flowers on the topmost leaves (potato
    plants flower when the tubers are ready), the one note of colour in a green row.

    py -3.10 tools/textures/crops_dense.py <faithful64.zip> <preview.png>

The hook's file names: textures/blocks/<crop>_stage_<n>_v0.png .. _v<k>.png (CropVariants.java).
Faithful 64x is under the Faithful licence (credited in CREDITS.txt / LICENSE-Faithful.txt).
"""
import sys

import numpy as np
from PIL import Image

from wheat_dense import read_faithful, scale_v, layer, SIZE

# (height, (back-copy shifts), mirror the front plant, flowers)
CARROTS = [(1.0, (13, -21), False, 0), (0.88, (-9, 25), True, 0), (0.94, (23, -7), False, 0), (0.82, (-17, 11), True, 0)]
POTATOES = [(1.0, (15, -23), False, 4), (0.86, (-11, 19), True, 0), (0.94, (25, -9), True, 3), (0.80, (-19, 7), False, 0)]
ROOT_ROWS = 14            # bottom rows at 64 px holding Faithful's carrots / tubers: front plant only
FLOWER = (238, 236, 222)  # petals (own values: off-white, not paper white)
EYE = (226, 190, 70)      # centre


def leafy(a):
    """The plant without its root band, so back copies never stack carrots or tubers."""
    b = a.copy()
    b[SIZE - ROOT_ROWS:, :, 3] = 0
    return b


def ragged_sides(a, seed, lo=2, hi=9):
    """Clear a ragged strip at the tile's left and right edges (2-9 px, varying by row in runs of 3), so
    a back copy that wrapped round the tile never ends in a straight vertical cut at the block edge."""
    b = a.copy()
    rng = np.random.default_rng(seed)
    w = np.repeat(rng.integers(lo, hi + 1, (SIZE // 3 + 1, 2)), 3, axis=0)[:SIZE]
    for y in range(SIZE):
        b[y, :w[y, 0], 3] = 0
        b[y, SIZE - w[y, 1]:, 3] = 0
    return b


BLOSSOM = [".PP.", "PEEP", "PEEP", ".PP."]   # 4x4 at 64 px: big enough to read from a few blocks


def flowers(a, n, seed):
    """n small round blossoms (petals round a yellow eye) on the topmost leaf pixels, spread apart."""
    out = a.copy()
    solid = out[..., 3] > 25
    rng = np.random.default_rng(seed)
    cols = [x for x in range(3, SIZE - 3) if solid[:, x].any()]
    rng.shuffle(cols)
    placed = []
    for x in cols:
        if len(placed) == n:
            break
        if any(abs(x - px) < 10 for px in placed):
            continue
        y = int(np.argmax(solid[:, x]))
        if y < 4 or y > SIZE * 0.6:          # only on the upper canopy
            continue
        for j, row in enumerate(BLOSSOM):
            for i, c in enumerate(row):
                if c != ".":
                    out[y - 2 + j, x - 2 + i] = (*(FLOWER if c == "P" else EYE), 255)
        placed.append(x)
    return out


def compose(stage, height, shifts, mirror, nflowers, seed):
    out = np.zeros_like(stage)
    for i, sh in enumerate(shifts):
        back = layer(np.zeros_like(stage), scale_v(leafy(stage), height * (0.86 + 0.08 * i)), sh, 0.60 + 0.12 * i, i % 2 == 0)
        out = layer(out, ragged_sides(back, seed * 7 + i), 0, 1.0, False)
    out = layer(out, scale_v(stage, height), 0, 1.0, mirror)
    out[..., 3] = np.where(out[..., 3] > 25, 255, 0)
    return flowers(out, nflowers, seed) if nflowers else out


def variants(stage, kind):
    spec = CARROTS if kind == "carrots" else POTATOES
    return [compose(stage, h, sh, m, f, seed=31 + i) for i, (h, sh, m, f) in enumerate(spec)]


def main():
    zp, outp = sys.argv[1], sys.argv[2]
    k = 4
    rows = []
    for kind in ("carrots", "potatoes"):
        st = read_faithful(zp, "%s_stage_3.png" % kind)
        rows.append([st] + variants(st, kind))
    sheet = Image.new("RGBA", (5 * (SIZE * k + 8), 2 * (SIZE * k + 8)), (92, 64, 40, 255))
    for r, row in enumerate(rows):
        for c, t in enumerate(row):
            im = Image.fromarray(np.clip(t, 0, 255).astype(np.uint8), "RGBA").resize((SIZE * k, SIZE * k), Image.NEAREST)
            sheet.alpha_composite(im, (c * (SIZE * k + 8), r * (SIZE * k + 8)))
    sheet.save(outp)


if __name__ == "__main__":
    main()
