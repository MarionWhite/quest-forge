#!/usr/bin/env python3
"""Automatic checks for one shader round, run before any critic call
(docs/design/shaders/review-loop.md, step 3).

Reads what C:\\qfb\\run_bench.ps1 leaves in an Angelica client dir:
  <client>\\bench\\<tag>.txt               FrameBench stats, one line per scene
  <client>\\screenshots\\bench-<tag>*.png  one 2560x1440 frame per scene shot

and checks:
  frame time   shader cost (p50 minus the shaders-off run's p50) against the
               tier budget; 1% low and frames over 33 ms must not get worse
               than --prev (the last accepted round)
  exposure     % of pixels crushed (luma <= 2) and clipped (>= 253), with the
               HUD masked out
  luminance    mean luma per frame, against --band SCENE=LO,HI if given
  noise        mean absolute difference of a still-camera pair (--pair A B)

Prints one JSON report; exit status 1 if any check fails, so a failing change
goes back to the author without spending a critic call.

Usage (py -3.10 -I):
  check_frames.py --client C:\\qfb\\client-ang --tag r12 --off m-B0 --prev r11 --tier ultra
  check_frames.py --client C:\\qfb\\client-ang --tag r12-low --off m-B0 --tier low-proxy --band torch=0.06,0.30
"""
import argparse, glob, json, os, re, sys

import numpy as np
from PIL import Image

# Shader cost budgets in ms on the DEV PC (RTX 5070 Ti), from performance-rules.md.
# The *-proxy tiers stand in for the GTX 1060 / integrated targets until a real
# weak PC has run the scene set.
BUDGET_MS = {"ultra": 3.0, "low-proxy": 0.9, "potato-proxy": 0.4}

# HUD rectangles in this pack's FrameBench frames, as fractions (x0, y0, x1, y1):
# Doom meter (top left), JourneyMap minimap (top right), hotbar and offhand row.
HUD = [(0.0, 0.0, 0.22, 0.12), (0.82, 0.0, 1.0, 0.35), (0.0, 0.89, 1.0, 1.0)]

LINE = re.compile(r"^(\w+)\s+frames\s+(\d+)\s+mean\s+([\d.]+) fps\s+p50\s+([\d.]+) ms\s+p99\s+([\d.]+) ms\s+"
                  r"1%low\s+([\d.]+) fps\s+worst\s+([\d.]+) ms\s+>33ms\s+(\d+)")


def bench(client, tag):
    path = os.path.join(client, "bench", tag + ".txt")
    if not os.path.exists(path):
        sys.exit("no FrameBench result: %s" % path)
    out = {}
    for line in open(path, encoding="utf8", errors="replace"):
        m = LINE.match(line)
        if m:
            s = m.groups()
            out[s[0]] = {"frames": int(s[1]), "mean_fps": float(s[2]), "p50_ms": float(s[3]), "p99_ms": float(s[4]),
                         "low1_fps": float(s[5]), "worst_ms": float(s[6]), "over33": int(s[7])}
    return out


def luma(path):
    a = np.asarray(Image.open(path).convert("RGB"), dtype=np.float32)
    y = 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]   # on the sRGB-encoded values
    keep = np.ones(y.shape, bool)
    h, w = y.shape
    for x0, y0, x1, y1 in HUD:
        keep[int(y0 * h):int(y1 * h), int(x0 * w):int(x1 * w)] = False
    return y, keep


def frame_stats(path):
    y, keep = luma(path)
    v = y[keep]
    return {"crushed_pct": round(100.0 * float((v <= 2).mean()), 2),
            "clipped_pct": round(100.0 * float((v >= 253).mean()), 2),
            "mean_luma": round(float(v.mean()) / 255.0, 4)}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--client", default=r"C:\qfb\client-ang")
    ap.add_argument("--tag", required=True, help="this round's FrameBench tag")
    ap.add_argument("--off", help="tag of the shaders-off run in the same client (for shader cost)")
    ap.add_argument("--prev", help="tag of the last accepted round (1%% low / >33 ms must not regress)")
    ap.add_argument("--tier", choices=sorted(BUDGET_MS), default="ultra")
    ap.add_argument("--budget-ms", type=float, help="override the tier's shader-cost budget")
    ap.add_argument("--max-crushed", type=float, default=2.0, help="%% of non-HUD pixels at luma <= 2")
    ap.add_argument("--max-clipped", type=float, default=1.0, help="%% of non-HUD pixels at luma >= 253")
    ap.add_argument("--band", action="append", default=[], metavar="SHOT=LO,HI",
                    help="mean-luma band (0-1) for screenshots whose name contains SHOT")
    ap.add_argument("--pair", nargs=2, action="append", default=[], metavar=("A", "B"),
                    help="two consecutive still-camera frames: temporal noise")
    ap.add_argument("--max-noise", type=float, default=1.5, help="mean |A-B| in luma levels (0-255)")
    a = ap.parse_args()

    fails, report = [], {"tag": a.tag, "client": a.client, "tier": a.tier}
    budget = a.budget_ms if a.budget_ms is not None else BUDGET_MS[a.tier]
    cur = bench(a.client, a.tag)
    off = bench(a.client, a.off) if a.off else {}
    prev = bench(a.client, a.prev) if a.prev else {}
    scenes = {}
    for name, s in cur.items():
        r = dict(s)
        if name in off:
            r["shader_cost_ms"] = round(s["p50_ms"] - off[name]["p50_ms"], 2)
            if r["shader_cost_ms"] > budget:
                fails.append("%s: shader cost %.2f ms > %.2f ms budget" % (name, r["shader_cost_ms"], budget))
        if 4.0 <= s["p50_ms"] <= 4.2:   # 240 Hz = 4.17 ms; capped runs read 4.03-4.16
            fails.append("%s: p50 %.2f ms is almost certainly the 240 Hz vsync cap; set vsync_mode OFF "
                         "in config/angelica-options.json and re-run" % (name, s["p50_ms"]))
        if name in prev:
            p = prev[name]
            if s["low1_fps"] < p["low1_fps"] * 0.97:
                fails.append("%s: 1%% low %.1f < previous %.1f" % (name, s["low1_fps"], p["low1_fps"]))
            if s["over33"] > p["over33"]:
                fails.append("%s: %d frames over 33 ms (previous %d)" % (name, s["over33"], p["over33"]))
        scenes[name] = r
    report["scenes"] = scenes
    if not off:
        report["note"] = "no --off run: shader cost not checked"

    bands = {}
    for b in a.band:
        k, v = b.split("=", 1)
        lo, hi = (float(x) for x in v.split(","))
        bands[k] = (lo, hi)
    shots = {}
    for path in sorted(glob.glob(os.path.join(a.client, "screenshots", "bench-%s*.png" % a.tag))):
        st = frame_stats(path)
        name = os.path.basename(path)
        if st["crushed_pct"] > a.max_crushed:
            fails.append("%s: %.2f%% crushed shadows" % (name, st["crushed_pct"]))
        if st["clipped_pct"] > a.max_clipped:
            fails.append("%s: %.2f%% clipped highlights" % (name, st["clipped_pct"]))
        for k, (lo, hi) in bands.items():
            if k in name and not lo <= st["mean_luma"] <= hi:
                fails.append("%s: mean luma %.3f outside %s band %.2f-%.2f" % (name, st["mean_luma"], k, lo, hi))
        shots[name] = st
    if not shots:
        fails.append("no screenshots matching bench-%s*.png" % a.tag)
    report["screenshots"] = shots

    noise = {}
    for p0, p1 in a.pair:
        y0, keep = luma(p0)
        y1, _ = luma(p1)
        n = round(float(np.abs(y0 - y1)[keep].mean()), 3)
        noise["%s | %s" % (os.path.basename(p0), os.path.basename(p1))] = n
        if n > a.max_noise:
            fails.append("temporal noise %.3f > %.3f between %s and %s" % (n, a.max_noise, p0, p1))
    if noise:
        report["temporal_noise"] = noise

    report["fails"] = fails
    report["pass"] = not fails
    print(json.dumps(report, indent=1))
    sys.exit(0 if not fails else 1)


if __name__ == "__main__":
    main()
