#!/usr/bin/env python3
"""Compile-check the Quest Forge shader pack offline, before a client is booted.

Iris on Angelica reports compile errors only in game (and only with enableDebugOptions);
a boot costs a minute even on a slim trial. This expands the pack's absolute `#include
"/..."` lines the way Iris does, defines the macros Angelica would (IS_ANGELICA,
IRIS_VERSION, MC_VERSION, the IRIS_FEATURE_* that are always on), sets QF_PRESET, and runs
Khronos glslang on every program stage, for every preset.

glslang is stricter than the NVIDIA driver in a few places and laxer in none that matter
here, so a clean run here means the driver will compile it. It does not check Iris's own
transform (core-profile rewrite, attribute renames): read patched_shaders/ for those.

Usage (py -3.10 -I):
    check_glsl.py [--pack shaders/QuestForge] [--glslang C:\\qfb\\shaderdev\\tools-dl\\glslang\\x\\bin\\glslang.exe]
                  [--presets 0,1,2,3,4] [--program gbuffers_terrain]
Exit status 1 on any error.
"""
import argparse, os, re, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
DEFAULT_GLSLANG = r"C:\qfb\shaderdev\tools-dl\glslang\x\bin\glslang.exe"
IRIS_DEFINES = {
    "IS_ANGELICA": "1", "IS_IRIS": "1", "IRIS_VERSION": "10803", "MC_VERSION": "10710",
    "MC_GL_VERSION": "460", "MC_GLSL_VERSION": "460", "MC_OS_WINDOWS": "1",
    "IRIS_FEATURE_SEPARATE_HARDWARE_SAMPLERS": "1", "IRIS_FEATURE_PER_BUFFER_BLENDING": "1",
}
INCLUDE = re.compile(r'^\s*#include\s+"([^"]+)"', re.M)


def expand(path, root, seen=()):
    out = []
    for i, line in enumerate(open(path, encoding="utf-8").read().split("\n")):
        m = INCLUDE.match(line)
        if m:
            inc = m.group(1)
            p = os.path.join(root, inc.lstrip("/")) if inc.startswith("/") else os.path.join(os.path.dirname(path), inc)
            if p in seen:
                sys.exit(f"include loop: {p}")
            out.append(expand(p, root, seen + (p,)))
        else:
            out.append(line)
    return "\n".join(out)


def program_source(path, root, preset):
    src = expand(path, root)
    lines = src.split("\n")
    if not lines[0].startswith("#version"):
        sys.exit(f"{path}: first line must be #version")
    defs = dict(IRIS_DEFINES)
    head = [lines[0]] + [f"#define {k} {v}" for k, v in defs.items()]
    body = "\n".join(lines[1:])
    # The option default lives in lib/settings.glsl; override it the way Iris writes the
    # player's choice into the source.
    body = re.sub(r"^#define QF_PRESET \d+", f"#define QF_PRESET {preset}", body, flags=re.M)
    return "\n".join(head) + "\n#line 2\n" + body


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pack", default=os.path.join(REPO, "shaders", "QuestForge"))
    ap.add_argument("--glslang", default=DEFAULT_GLSLANG)
    ap.add_argument("--presets", default="0,1,2,3,4")
    ap.add_argument("--program", help="only programs whose name starts with this")
    a = ap.parse_args()
    if not os.path.isfile(a.glslang):
        sys.exit(f"glslang not found at {a.glslang} (Khronos release zip, bin/glslang.exe)")
    root = os.path.join(a.pack, "shaders")
    files = sorted(f for f in os.listdir(root) if f.endswith((".vsh", ".fsh")))
    if a.program:
        files = [f for f in files if f.startswith(a.program)]
    errors = 0
    tmp = tempfile.mkdtemp(prefix="qfglsl-")
    for preset in a.presets.split(","):
        for f in files:
            stage = "vert" if f.endswith(".vsh") else "frag"
            src = program_source(os.path.join(root, f), root, preset)
            p = os.path.join(tmp, f"{f}.{stage}")
            with open(p, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(src)
            r = subprocess.run([a.glslang, "-S", stage, p], capture_output=True, text=True)
            msg = (r.stdout + r.stderr).strip()
            bad = r.returncode != 0 or "ERROR" in msg
            if bad:
                errors += 1
                print(f"--- preset {preset}  {f}")
                for line in msg.splitlines():
                    if "ERROR" in line or "WARNING" in line:
                        print("   " + line.replace(p, f))
                print(f"   (expanded source: {p})")
    print(f"{len(files)} stages x {len(a.presets.split(','))} presets: {errors} with errors")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
