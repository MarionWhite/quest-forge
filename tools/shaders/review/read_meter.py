#!/usr/bin/env python3
"""Decode the exposure readout patches of debug view 8 (QF_DEBUG_VIEW=8) from screenshots.

final.glsl draws 32x32 patches at the top left (16 px in, one every 40 px). Each holds a
value in [0, 1) as two undithered 8-bit channels (red high byte, green low byte). See
meterReadout() in shaders/QuestForge/shaders/program/final.glsl for the list.

Usage (py -3.10 -I):
  read_meter.py C:\\qfb\\shaderdev\\rounds\\screenshots\\bench-d8h-*.png
"""
import glob, math, os, sys

import numpy as np
from PIL import Image

NAMES = ["meter", "ct3_final", "shown/exp", "exposure", "target", "moonPhase", "moonE", "sunE", "frameTime",
         "lagMeter", "lagState", "fcMinusCarried", "frameCounter", "mean", "metered"]


def decode(img, i):
    x0 = 16 + 40 * i
    patch = np.asarray(img.convert("RGB"))[24:40, x0 + 8:x0 + 24].reshape(-1, 3).astype(np.int64)
    r = int(np.median(patch[:, 0]))
    g = int(np.median(patch[:, 1]))
    return (r + g / 255.0) / 255.0


def read(path):
    img = Image.open(path)
    out = {}
    for i, n in enumerate(NAMES):
        v = decode(img, i)
        if n == "moonPhase":
            out[n] = round(v * 8)
        elif n == "frameTime":
            out[n] = v / 10.0
        elif n.startswith("lag"):
            out[n] = round(v * 64)
        elif n in ("fcMinusCarried", "frameCounter"):
            out[n] = round(v * 2048)
        else:
            out[n] = v * 32.0 - 24.0    # log2
    return out


def main():
    paths = []
    for a in sys.argv[1:]:
        paths += sorted(glob.glob(a))
    if not paths:
        sys.exit(__doc__)
    print(f"{'frame':34} {'meter':>8} {'ct3':>8} {'shown':>8} {'log2E':>7} {'target':>7} {'E':>7} {'ms':>6}"
          "   (logs are log2 luminance; meter/ct3/shown as linear in brackets)")
    for p in paths:
        r = read(p)
        name = os.path.basename(p)[:-4]
        print(f"{name:34} {r['meter']:8.3f} {r['ct3_final']:8.3f} {r['shown/exp']:8.3f} {r['exposure']:7.3f} "
              f"{r['target']:7.3f} {2 ** r['exposure']:7.3f} {r['frameTime'] * 1000:6.2f}"
              f"   [{2 ** r['meter']:.5f} {2 ** r['ct3_final']:.5f} {2 ** r['shown/exp']:.5f}]"
              f"  lag {r['lagMeter']}/{r['lagState']} fc-carried {r['fcMinusCarried']} fc {r['frameCounter']}"
              f"  mean {r['mean']:.3f} metered {r['metered']:.3f}")


if __name__ == "__main__":
    main()
