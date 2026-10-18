#!/usr/bin/env python3
"""Render the owner's taste-survey image set (Shader Lab round r000) with our own pack.

Each question varies ONE development option (QF_CAL_* in shaders/QuestForge/shaders/lib/
settings.glsl; 0 is the pack as tuned). Every run is a slim-trial bench_round.py render
at High, 1920x1080, of the question's scenes. The frames are saved as 1920 px JPEGs
(quality 90) in OUT\\<question>-<key>-<scene>.jpg, and listed in OUT\\manifest.json as
[{question, key, label, scene, path, ms, settings}]. ms is the scene's FrameBench p50.

The variants are throwaway. When the owner picks one, fold its settings into the
pack's tuned values; don't make a QF_CAL_* value a default.

Usage (py -3.10 -I, run it as a BACKGROUND task, about an hour):
  calibration.py [--only direction,night] [--skip-render]
"""
import argparse, json, os, re, subprocess, sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
BENCH = os.path.join(HERE, "bench_round.py")
ROUNDS = r"C:\qfb\shaderdev\rounds"
OUT = r"C:\qfb\shaderdev\calibration"

# One run per (tag, options, scenes). "base" is the pack as tuned, shared by the options
# that equal it.
RUNS = {
    "calbase": ({}, "plains_noon,forest_golden,shore_noon,shore_sunset,night_full,night_new,underwater,dawn_wide,torch"),
    "caldirA": ({"QF_CAL_GRADE": 1}, "plains_noon,forest_golden"),
    "caldirB": ({"QF_CAL_GRADE": 2}, "plains_noon,forest_golden"),
    "caldirC": ({"QF_CAL_GRADE": 3}, "plains_noon,forest_golden"),
    "calnightA": ({"QF_CAL_NIGHT": 1}, "night_full,night_new"),
    "calnightB": ({"QF_CAL_NIGHT": 2}, "night_full,night_new"),
    "calnightC": ({"QF_CAL_NIGHT": 3}, "night_full,night_new"),
    "calsunA": ({"QF_CAL_SUNSET": 1}, "forest_golden,shore_sunset"),
    "calsunB": ({"QF_CAL_SUNSET": 2}, "forest_golden,shore_sunset"),
    "calwatA": ({"QF_CAL_WATER": 1}, "shore_noon,underwater"),
    "calwatB": ({"QF_CAL_WATER": 2}, "shore_noon,underwater"),
    "calfogA": ({"QF_CAL_FOG": 1}, "plains_noon,dawn_wide"),
    "calfogB": ({}, "plains_noon,dawn_wide"),
    "calfogC": ({"QF_CAL_FOG": 3}, "plains_noon,dawn_wide"),
    # Bloom needs something bright in frame: the held light in the torch tunnel never
    # crosses the glow threshold, so the moon and the setting sun stand in for it.
    "calglowA": ({"QF_CAL_BLOOM": 1}, "night_moon,shore_sunset"),
    "calglowB": ({"QF_CAL_BLOOM": 2}, "night_moon,shore_sunset"),
    "calglowC": ({"QF_CAL_BLOOM": 3}, "night_moon,shore_sunset"),
}

# question -> [(key, label, run tag, settings note)], scenes
QUESTIONS = {
    "direction": ([
        ("A", "Photoreal: neutral grade, restrained bloom", "caldirA", "QF_CAL_GRADE=1: as tuned, plus a subtle glow (threshold 0.85, gain 0.10)"),
        ("B", "Cinematic: teal/orange grade, deeper contrast, richer bloom", "caldirB", "QF_CAL_GRADE=2: shadows x(0.90,1.0,1.10), highlights x(1.10,1.0,0.86), contrast 1.18 about 0.18, glow (0.45, 0.30)"),
        ("C", "Storybook: softer, more saturated, gentle contrast", "caldirC", "QF_CAL_GRADE=3: saturation 1.3, contrast 0.85, black lift 0.008, subtle glow"),
    ], ["plains_noon", "forest_golden"]),
    "night": ([
        ("A", "Truly dark (mean luma near 0.03)", "calnightA", "QF_CAL_NIGHT=1: night exposure -1.2 stops, saturation 0.5"),
        ("B", "Moonlit, blue and readable (near 0.07)", "calnightB", "QF_CAL_NIGHT=2: night exposure as tuned, cool tint x(0.82,0.95,1.18)"),
        ("C", "Gentle (near 0.12)", "calnightC", "QF_CAL_NIGHT=3: night exposure +1.5 stops, near-neutral"),
    ], ["night_full", "night_new"]),
    "sunset": ([
        ("A", "Intense orange and gold", "calsunA", "QF_CAL_SUNSET=1: at low sun, saturation up to 1.5, warm x(1.22,1.04,0.74)"),
        ("B", "Soft pastel: pink, peach, lilac", "calsunB", "QF_CAL_SUNSET=2: at low sun, saturation 0.7, tint x(1.08,0.93,1.06), lift 0.01"),
        ("C", "Naturalistic: brief gold, then a cool blue hour", "calbase", "as tuned (physical sky, no grade)"),
    ], ["forest_golden", "shore_sunset"]),
    "water": ([
        ("A", "Clear tropical: low absorption, visible bottom", "calwatA", "QF_CAL_WATER=1: absorb (0.03,0.012,0.014), scatter (0.0008,0.006,0.006)"),
        ("B", "Deep and dark: strong absorption, strong reflections", "calwatB", "QF_CAL_WATER=2: absorb (0.30,0.16,0.12), Fresnel x1.6 + 0.08"),
        ("C", "Realistic depth gradient", "calbase", "as tuned: absorb (0.075,0.042,0.038)"),
    ], ["shore_noon", "underwater"]),
    "fog": ([
        ("A", "Crisp: no haze", "calfogA", "QF_CAL_FOG=1: haze density 0 (chunk-edge fade only)"),
        ("B", "Natural sky-blue haze", "calfogB", "as tuned: haze from 35% of render distance"),
        ("C", "Moody: thick valley and dawn fog", "calfogC", "QF_CAL_FOG=3: haze from 4 blocks, density x3, x4 more near sea level"),
    ], ["plains_noon", "dawn_wide"]),
    "bloom": ([
        ("A", "None", "calglowA", "QF_CAL_BLOOM=1: no glow (as tuned)"),
        ("B", "Subtle", "calglowB", "QF_CAL_BLOOM=2: glow threshold 0.85, gain 0.10"),
        ("C", "Strong", "calglowC", "QF_CAL_BLOOM=3: glow threshold 0.45, gain 0.30"),
    ], ["night_moon", "shore_sunset"]),
}

LINE = re.compile(r"^(\w+)\s+frames\s+\d+\s+mean\s+[\d.]+ fps\s+p50\s+([\d.]+) ms")


def p50s(tag):
    path = os.path.join(ROUNDS, "bench", tag + ".txt")
    out = {}
    if os.path.exists(path):
        for line in open(path, encoding="utf-8", errors="replace"):
            m = LINE.match(line)
            if m:
                out[m.group(1)] = float(m.group(2))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", help="comma-separated questions")
    ap.add_argument("--skip-render", action="store_true", help="only rebuild the JPEGs and the manifest")
    ap.add_argument("--quiet-min", default="1")
    a = ap.parse_args()
    qs = a.only.split(",") if a.only else list(QUESTIONS)
    tags = sorted({t for q in qs for (_, _, t, _) in QUESTIONS[q][0]})
    if not a.skip_render:
        for tag in tags:
            if os.path.exists(os.path.join(ROUNDS, "bench", tag + ".txt")):
                print("have", tag)
                continue
            opts, scenes = RUNS[tag]
            cmd = [sys.executable, "-I", BENCH, "--tag", tag, "--preset", "3", "--size", "1920x1080",
                   "--scenes", scenes, "--quiet-min", a.quiet_min]
            for k, v in opts.items():
                cmd += ["--opt", f"{k}={v}"]
            print("render", tag, opts, flush=True)
            r = subprocess.run(cmd, capture_output=True, text=True)
            ok = os.path.exists(os.path.join(ROUNDS, "bench", tag + ".txt"))
            print("  ", "ok" if ok else "FAILED: " + (r.stdout + r.stderr)[-400:], flush=True)
    os.makedirs(OUT, exist_ok=True)
    manifest = []
    mpath = os.path.join(OUT, "manifest.json")
    if os.path.exists(mpath):
        manifest = [m for m in json.load(open(mpath, encoding="utf-8")) if m["question"] not in qs]
    for q in qs:
        options, scenes = QUESTIONS[q]
        for key, label, tag, note in options:
            ms = p50s(tag)
            for scene in scenes:
                src = os.path.join(ROUNDS, "screenshots", f"bench-{tag}-{scene}.png")
                if not os.path.exists(src):
                    print("missing", src)
                    continue
                dst = os.path.join(OUT, f"{q}-{key}-{scene}.jpg")
                im = Image.open(src).convert("RGB")
                if im.width != 1920:
                    im = im.resize((1920, round(im.height * 1920 / im.width)), Image.LANCZOS)
                im.save(dst, "JPEG", quality=90)
                manifest.append({"question": q, "key": key, "label": label, "scene": scene, "path": dst,
                                 "ms": ms.get(scene), "settings": note, "run": tag})
    json.dump(manifest, open(mpath, "w", encoding="utf-8"), indent=1)
    print(f"{len(manifest)} images; manifest {mpath}")


if __name__ == "__main__":
    main()
