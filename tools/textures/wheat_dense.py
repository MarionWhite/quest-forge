#!/usr/bin/env python3
"""Dense ripe wheat for QF Textures r010: Faithful 64x's own stalks and ears, re-composed in the way
Stay True builds its fields (studied from the owner's r009 screenshots, never its pixels).

    py -3.10 tools/textures/wheat_dense.py <faithful64.zip> <preview.png> [plain|bushy]   # a 4x preview sheet

What Stay True does, and how we get there from licensed art:
  - a ripe block is one bushy gold mass across the whole tile, not separate airy plants
    -> Faithful's stage-7 plant layer copied 3-4 times, mirrored and shifted sideways, the back copies
       shorter and darker, so the gaps close but each stalk and ear is still Faithful's drawing;
  - strong value structure: near-black ochre at the base, saturated gold body, pale straw tips
    -> a gradient map over (height in the plant, pixel luminance) onto a 6-step gold ramp;
  - five variants of different heights mixed per block (CTM method=random), so a field never tiles
    -> the same composite with its own shifts per variant, scaled to 0.62-1.0 of the tile height.

Faithful 64x is under the Faithful licence (credited in CREDITS.txt / LICENSE-Faithful.txt).
"""
import io
import sys
import zipfile

import numpy as np
from PIL import Image

SIZE = 64
# The gold ramp, dark base to pale tip (sRGB). Our own values, picked from the target's read:
# deep ochre shadows, saturated gold, straw highlights.
RAMP = np.array([(52, 33, 14), (98, 63, 22), (151, 101, 32), (201, 145, 46), (232, 184, 76), (247, 222, 140)], np.float32)
# Variant heights (fraction of the tile) and the sideways shifts of the layered copies (px at 64).
VARIANTS = [(0.62, (11, -19, 27)), (0.72, (-7, 23, 15)), (0.82, (17, -13, 31)), (0.91, (-21, 9, -29)), (1.0, (5, -25, 19))]


def read_faithful(zp, name):
    z = zipfile.ZipFile(zp)
    for p in z.namelist():
        if p.endswith("textures/blocks/" + name):
            return np.array(Image.open(io.BytesIO(z.read(p))).convert("RGBA")).astype(np.float32)
    raise KeyError(name)


def lum(a):
    return 0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]


def scale_v(a, f):
    """Squash the plant vertically to f of the tile, bottom-anchored (nearest, keeps pixel art)."""
    h = max(8, int(round(SIZE * f)))
    im = Image.fromarray(a.astype(np.uint8), "RGBA").resize((SIZE, h), Image.NEAREST)
    out = np.zeros_like(a)
    out[SIZE - h:] = np.array(im).astype(np.float32)
    return out


def layer(dst, src, shift, dark, mirror):
    s = src[:, ::-1] if mirror else src
    s = np.roll(s, shift, axis=1)
    m = s[..., 3:4] > 25
    s = s.copy()
    s[..., :3] *= dark
    return np.where(m, s, dst)


def ears_only(ripe):
    """Faithful's ear pixels: the brightest fifth of the plant (the ears are its lightest drawing)."""
    L = lum(ripe)
    solid = ripe[..., 3] > 25
    m = solid & (L >= np.percentile(L[solid], 80))
    e = ripe.copy()
    e[~m, 3] = 0
    return e


# Ear stamps for heads="bushy": (sideways shift, drop in px, darkness).
EAR_STAMPS = [(7, 3, 0.85), (-12, 5, 0.8), (19, 2, 0.9), (-25, 6, 0.75), (29, 4, 0.85), (-4, 8, 0.7)]


def compose(ripe, height, shifts, heads="plain"):
    """Back copies first (shorter, darker), then for heads="bushy" extra copies of Faithful's ears
    across the top band, Faithful's own plant in front."""
    out = np.zeros_like(ripe)
    for i, sh in enumerate(shifts):
        f = height * (0.80 + 0.07 * i)
        out = layer(out, scale_v(ripe, f), sh, 0.62 + 0.1 * i, i % 2 == 0)
    if heads == "bushy":
        ears = scale_v(ears_only(ripe), height)
        for j, (sh, drop, dk) in enumerate(EAR_STAMPS):
            dropped = np.zeros_like(ears)
            dropped[drop:] = ears[:SIZE - drop]      # move down without wrapping the base onto the top
            out = layer(out, dropped, sh + shifts[j % len(shifts)] // 3, dk, j % 2 == 1)
    out = layer(out, scale_v(ripe, height), 0, 1.0, False)
    return out


def gold(a, height):
    """Gradient map: t from height in the plant (0 base, 1 top of this variant) and the pixel's own
    luminance (keeps Faithful's drawn shading inside each ear and blade)."""
    y = np.arange(SIZE, dtype=np.float32)[:, None]
    top = SIZE * (1 - height)
    hgt = np.clip((SIZE - y) / max(SIZE - top, 1), 0, 1)
    L = lum(a) / 255.0
    Ln = (L - 0.25) / 0.55
    t = np.clip(0.18 + 0.62 * hgt ** 0.8 + 0.45 * (Ln - 0.5), 0, 1)
    # darker where the source was dark (the back copies, drawn shadows)
    t = np.clip(t * (0.55 + 0.45 * np.clip(L / 0.6, 0, 1)), 0, 1)
    idx = t * (len(RAMP) - 1)
    # quantise to a 12-colour ramp so it stays pixel art, not a smooth gradient
    q = np.round(idx * 2) / 2
    j0 = np.floor(q).astype(int)
    j1 = np.minimum(j0 + 1, len(RAMP) - 1)
    wq = (q - j0)[..., None]
    rgb = RAMP[j0] * (1 - wq) + RAMP[j1] * wq
    out = a.copy()
    out[..., :3] = rgb
    out[..., 3] = np.where(a[..., 3] > 25, 255, 0)
    return out


def variants(ripe, heads="plain"):
    return [gold(compose(ripe, h, sh, heads), h) for h, sh in VARIANTS]


def main():
    zp, out = sys.argv[1], sys.argv[2]
    heads = sys.argv[3] if len(sys.argv) > 3 else "plain"
    ripe = read_faithful(zp, "wheat_stage_7.png")
    vs = variants(ripe, heads)
    tiles = [ripe] + vs
    k = 4
    W = len(tiles) * (SIZE * k + 8)
    sheet = Image.new("RGBA", (W, SIZE * k * 2 + 8), (70, 60, 50, 255))
    for i, t in enumerate(tiles):
        im = Image.fromarray(t.astype(np.uint8), "RGBA").resize((SIZE * k, SIZE * k), Image.NEAREST)
        sheet.alpha_composite(im, (i * (SIZE * k + 8), 0))
    # a field strip: the five variants side by side at 2x, random order, two rows overlapping
    rng = np.random.default_rng(3)
    strip = Image.new("RGBA", (W, SIZE * k), (92, 64, 40, 255))
    for row, yo in ((0, 0), (1, SIZE)):
        for c in range(W // (SIZE * 2) + 1):
            v = vs[rng.integers(len(vs))]
            im = Image.fromarray(v.astype(np.uint8), "RGBA").resize((SIZE * 2, SIZE * 2), Image.NEAREST)
            strip.alpha_composite(im, (c * SIZE * 2 - (SIZE if row else 0), yo + (SIZE * 2 - SIZE * 2)))
    sheet.alpha_composite(strip, (0, SIZE * k + 8))
    sheet.save(out)


if __name__ == "__main__":
    main()
