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


def emerald_from_diamond(diamond, ramp=EMERALD_RAMP, by_value=False):
    """Every distinct diamond tone -> the emerald ramp, by luminance rank (keeps the tone count). An animated
    strip is mapped as one image, so a tone keeps its colour in every frame. by_value (Stay True's strip): place
    each tone by its luminance between frame 0's darkest and brightest instead, so the many near-white glint tones
    do not take the top of the ramp and squash the still face into a few dark greens (first try: std 14 vs 25)."""
    out = diamond.copy()
    L = lum(diamond.astype(np.float32))
    levels = np.unique(L[diamond[..., 3] > 25])
    w0 = diamond.shape[1]
    lo, hi = np.percentile(L[:w0], 1), np.percentile(L[:w0], 99)
    for i, lv in enumerate(levels):
        f = np.clip((lv - lo) / max(hi - lo, 1.0), 0.0, 1.0) if by_value else i / max(len(levels) - 1, 1)
        t = f * (len(ramp) - 1)
        j = int(np.floor(t))
        w = t - j
        c = ramp[j] * (1 - w) + ramp[min(j + 1, len(ramp) - 1)] * w
        out[(L == lv) & (diamond[..., 3] > 25), :3] = np.round(c).astype(out.dtype)
    return out


def ramp_from(img, k=7):
    """k colours spread by luminance rank over an image's distinct opaque colours (darkest first): r012 takes
    Stay True's own emerald palette this way, to re-tone its diamond (no nested squares) as emerald."""
    px = img[img[..., 3] > 25][:, :3].astype(np.float32)
    cols = np.unique(px, axis=0)
    cols = cols[np.argsort(lum(cols))]
    idx = np.round(np.linspace(0, len(cols) - 1, k)).astype(int)
    return cols[idx]


def dome_normal(size, frames=1, tilt=0.52):
    """LabPBR _n (DirectX: +G down) of a whole-face dome, the shape VNR gives diamond (r010 build: R and G run
    76..177 across the face, ~24 deg mean tilt): a flat face mirrors one direction, a domed one sweeps its
    reflection from sky to horizon across the block, which is what reads as polished. B (AO) and A (height) 255."""
    c = (np.arange(size) + 0.5) / size * 2.0 - 1.0
    x, y = np.meshgrid(c * tilt, c * tilt)
    n = np.zeros((size, size, 4), np.uint8)
    n[..., 0] = np.clip(np.round((x + 1.0) * 127.5), 0, 255)
    n[..., 1] = np.clip(np.round((y + 1.0) * 127.5), 0, 255)
    n[..., 2] = 255
    n[..., 3] = 255
    return np.tile(n, (frames, 1, 1))


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
