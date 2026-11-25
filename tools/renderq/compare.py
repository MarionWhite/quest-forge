#!/usr/bin/env python3
"""Are two renders of the same job the same? Pixel difference and frame-cost difference per scene.

    py -3.10 -I tools/renderq/compare.py TAG_A TAG_B [TAG_A2 TAG_B2 ...] [--rounds DIR]

For each scene both tags have: the mean absolute difference of the frames (0-255 per channel),
the share of pixels that differ by more than 8 levels, and each tag's p50/p99 frame time. Run it
on two separate boots of one job first: that is the noise floor (clouds drift with time, so no two
renders of a sky are identical), which a batched render must stay within.
"""
import argparse, os, re, sys

import numpy as np
from PIL import Image

ROUNDS = r"C:\qfb\shaderdev\rounds"
LINE = re.compile(r"^(\w+)\s+frames\s+(\d+)\s+mean\s+([\d.]+) fps\s+p50\s+([\d.]+) ms\s+p99\s+([\d.]+) ms")


def stats(rounds, tag):
    out = {}
    p = os.path.join(rounds, "bench", tag + ".txt")
    for l in open(p, encoding="utf-8", errors="replace"):
        m = LINE.match(l)
        if m:
            out[m.group(1)] = (float(m.group(4)), float(m.group(5)))
    return out


def diff(a, b):
    x = np.asarray(Image.open(a).convert("RGB"), dtype=np.int16)
    y = np.asarray(Image.open(b).convert("RGB"), dtype=np.int16)
    if x.shape != y.shape:
        return None, None
    d = np.abs(x - y)
    return float(d.mean()), float((d.max(axis=2) > 8).mean() * 100)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tags", nargs="+")
    ap.add_argument("--rounds", default=ROUNDS)
    a = ap.parse_args()
    if len(a.tags) % 2:
        sys.exit("give tags in pairs")
    print(f"{'pair':<22} {'scene':<14} {'MAD':>6} {'>8 %':>6}  {'p50 A':>6} {'p50 B':>6} {'dp50':>6}  {'p99 A':>6} {'p99 B':>6}")
    for i in range(0, len(a.tags), 2):
        ta, tb = a.tags[i], a.tags[i + 1]
        sa, sb = stats(a.rounds, ta), stats(a.rounds, tb)
        for sc in sa:
            if sc not in sb:
                continue
            fa = os.path.join(a.rounds, "screenshots", f"bench-{ta}-{sc}.png")
            fb = os.path.join(a.rounds, "screenshots", f"bench-{tb}-{sc}.png")
            mad, big = diff(fa, fb) if os.path.exists(fa) and os.path.exists(fb) else (None, None)
            (pa, qa), (pb, qb) = sa[sc], sb[sc]
            print(f"{ta + ' vs ' + tb:<22} {sc:<14} {mad if mad is None else round(mad, 2)!s:>6} "
                  f"{big if big is None else round(big, 2)!s:>6}  {pa:6.2f} {pb:6.2f} {pb - pa:+6.2f}  {qa:6.2f} {qb:6.2f}")


if __name__ == "__main__":
    main()
