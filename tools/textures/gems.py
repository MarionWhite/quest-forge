#!/usr/bin/env python3
"""Emerald block in the diamond block's direction (owner r009: "aim for the diamond's direction rather
than the geometric look"): Faithful 64x's diamond_block (frame + soft diagonal glints) with each of its
tones mapped by rank onto an emerald ramp built from Faithful 64x's own emerald colours, one step deeper
at the bottom (emerald reads darker and more saturated than diamond).

    py -3.10 tools/textures/gems.py <faithful64.zip> <preview.png>

Faithful 64x is under the Faithful licence (credited in CREDITS.txt / LICENSE-Faithful.txt).
"""
import io
import sys
import zipfile

import numpy as np
from PIL import Image

# Faithful 64x emerald_block's six colours by luminance, plus one deeper shade below them (ours).
EMERALD_RAMP = np.array([(16, 104, 34), (28, 152, 41), (26, 174, 53), (23, 197, 68), (23, 221, 98),
                         (65, 243, 132), (130, 246, 173)], np.float32)


def lum(a):
    return 0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]


def emerald_from_diamond(diamond):
    """Every distinct diamond tone -> the emerald ramp, by luminance rank (keeps the tone count)."""
    out = diamond.copy()
    L = lum(diamond.astype(np.float32))
    levels = np.unique(L[diamond[..., 3] > 25])
    for i, lv in enumerate(levels):
        t = i / max(len(levels) - 1, 1) * (len(EMERALD_RAMP) - 1)
        j = int(np.floor(t))
        w = t - j
        c = EMERALD_RAMP[j] * (1 - w) + EMERALD_RAMP[min(j + 1, len(EMERALD_RAMP) - 1)] * w
        out[(L == lv) & (diamond[..., 3] > 25), :3] = np.round(c).astype(out.dtype)
    return out


def _read(zp, name):
    z = zipfile.ZipFile(zp)
    for p in z.namelist():
        if p.endswith("textures/blocks/" + name):
            return np.array(Image.open(io.BytesIO(z.read(p))).convert("RGBA"))
    raise KeyError(name)


if __name__ == "__main__":
    zp, outp = sys.argv[1], sys.argv[2]
    d, e = _read(zp, "diamond_block.png"), _read(zp, "emerald_block.png")
    tiles = [d, e, emerald_from_diamond(d)]
    S = Image.new("RGBA", (3 * 200 + 16, 192), (60, 60, 60, 255))
    for i, t in enumerate(tiles):
        im = Image.fromarray(np.tile(t, (3, 3, 1)), "RGBA").resize((192, 192), Image.NEAREST)
        S.alpha_composite(im, (i * 208, 0))
    S.save(outp)
