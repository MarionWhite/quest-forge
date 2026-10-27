#!/usr/bin/env python3
"""A motion clip for the Shader Lab from a renderq burst (2026-10-25, round 8).

A renderq job with "burst" leaves bench-TAG-SCENE-f000.png, -f001.png, ... in
rounds/screenshots and a "burst ... times 0 66 133 ..." line in rounds/bench/TAG.txt. This turns
them into a looping animated WebP, each frame shown for its real capture interval, so clouds,
waves and meteors move at the speed they move in the game. The quality (then the size) steps
down until the file is under --max-mb. A poster JPEG (the first frame) is written beside it.

    py -3.10 -I tools/shaders/review/make_clip.py TAG SCENE [-o out.webp] [--scale 0.75] [--max-mb 3]
    py -3.10 -I tools/shaders/review/make_clip.py --frames "C:/x/bench-t-v-f*.png" -o out.webp --ms 66

spec_scenes.py uses it through roundlib's ov(): ov("A", "Meteors", "rv", "night_sky").
"""
import argparse, glob, os, re, sys

ROUNDS = r"C:\qfb\shaderdev\rounds"
FRAME = re.compile(r"-f(\d{3})\.png$")


def find_frames(rounds, tag, scene):
    fs = glob.glob(os.path.join(rounds, "screenshots", f"bench-{glob.escape(tag)}-{glob.escape(scene)}-f[0-9][0-9][0-9].png"))
    return sorted(fs, key=lambda p: int(FRAME.search(p).group(1)))


def bench_times(rounds, tag, scene):
    """The capture times (ms from the first frame) of TAG's burst on SCENE, or None."""
    p = os.path.join(rounds, "bench", tag + ".txt")
    if not os.path.exists(p):
        return None
    cur = None
    for l in open(p, encoding="utf-8", errors="replace"):
        m = re.match(r"^(\w+)\s+(frames\s|no frames recorded)", l)
        if m:
            cur = m.group(1)
            continue
        m = re.match(r"\s+burst .*; times ([\d ]+)$", l.rstrip("\n"))
        if m and cur == scene:
            return [int(t) for t in m.group(1).split()]
    return None


def poster_path(out):
    return os.path.splitext(out)[0] + "-poster.jpg"


def durations(n, times, ms):
    if times and len(times) >= n and n > 1:
        d = [max(20, times[i + 1] - times[i]) for i in range(n - 1)]
        d.append(round(sum(d) / len(d)))
        return d
    return [ms] * n


def make_clip(frames, out, times=None, ms=66, scale=1.0, max_mb=3.0, quality=82, min_quality=40,
              fps=None, quiet=False):
    """Write an animated WebP from frame files; returns (bytes, quality, scale)."""
    from PIL import Image
    if not frames:
        raise SystemExit("make_clip: no frames")
    dur = durations(len(frames), times, ms)
    if fps:   # resample to a steady rate (drops or repeats frames by their real times)
        t, acc = [], 0
        for d in dur:
            t.append(acc)
            acc += d
        step, keep, nd, i = 1000.0 / fps, [], [], 0
        k = 0.0
        while k < acc:
            while i + 1 < len(t) and t[i + 1] <= k:
                i += 1
            keep.append(frames[i])
            nd.append(round(step))
            k += step
        frames, dur = keep, nd
    src = [Image.open(f).convert("RGB") for f in frames]
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    q, sc = quality, scale
    while True:
        ims = src if sc == 1.0 else [im.resize((max(2, round(im.width * sc)), max(2, round(im.height * sc))),
                                               Image.LANCZOS) for im in src]
        tmp = out + ".tmp.webp"
        ims[0].save(tmp, "WEBP", save_all=True, append_images=ims[1:], duration=dur, loop=0,
                    quality=q, method=5, minimize_size=True)
        size = os.path.getsize(tmp)
        if size <= max_mb * 1e6 or (q <= min_quality and sc <= 0.35):
            break
        if q > min_quality:
            q = max(min_quality, q - 10)
        else:
            q, sc = quality - 10, round(sc * 0.8, 3)
    os.replace(tmp, out)
    ims[0].save(poster_path(out), "JPEG", quality=90)
    if not quiet:
        print(f"{out}: {len(ims)} frames {ims[0].width}x{ims[0].height}, {sum(dur) / 1000:.1f} s, "
              f"quality {q}, scale {sc}, {size / 1e6:.2f} MB (poster {os.path.basename(poster_path(out))})")
    return size, q, sc


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tag", nargs="?")
    ap.add_argument("scene", nargs="?")
    ap.add_argument("--frames", help="a glob of frame files instead of TAG SCENE")
    ap.add_argument("--rounds", default=ROUNDS)
    ap.add_argument("-o", "--out")
    ap.add_argument("--scale", type=float, default=1.0)
    ap.add_argument("--max-mb", type=float, default=3.0)
    ap.add_argument("--quality", type=int, default=82)
    ap.add_argument("--ms", type=int, default=66, help="frame time when the bench txt has no capture times")
    ap.add_argument("--fps", type=float, help="resample to a steady frame rate")
    ap.add_argument("--speedup", type=float, default=1.0,
                    help="divide the capture times by this: a burst rendered in slow motion (QF_METEOR_SLOW 0.25: "
                         "the slow PNG writer's uneven intervals jerk the motion 4x less) plays back at game speed")
    a = ap.parse_args()
    if a.frames:
        frames = sorted(glob.glob(a.frames))
        times = None
    elif a.tag and a.scene:
        frames = find_frames(a.rounds, a.tag, a.scene)
        times = bench_times(a.rounds, a.tag, a.scene)
        if times and a.speedup != 1.0:
            times = [t / a.speedup for t in times]
    else:
        ap.error("give TAG SCENE or --frames")
    out = a.out or os.path.join(os.getcwd(), f"{a.tag or 'clip'}-{a.scene or 'frames'}.webp")
    make_clip(frames, out, times=times, ms=a.ms, scale=a.scale, max_mb=a.max_mb, quality=a.quality, fps=a.fps)


if __name__ == "__main__":
    main()
