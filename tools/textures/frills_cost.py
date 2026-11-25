"""What leaf frills cost: frame time and chunk-rebuild time, frills off vs on.

Reads two renderq/FrameBench bench files (C:/qfb/shaderdev/rounds/bench/TAG.txt) and the MeshStats files the same
boots wrote (qf-tweaks -Dqf.meshstats=FILE, one line of running totals every 2 s; see
mods/qf-tweaks/src/com/questforge/MeshStats.java). A scene's meshing work is what was built between the previous
scene's end and its own end (FrameBench's "wall" line), so it covers placing the camera, loading the chunks and
settling.

    py -3.10 tools/textures/frills_cost.py --off fr1a0 --on fr1a1 [--stats C:/qfb/frills/stats] [--md out.md]

Prints a markdown table per scene and for the whole boot: frame p50/p99, sections built, mean build time per section
and vertices per section (all sections, and "leafy" ones with 32+ leaf blocks), frill quads.
"""
import argparse
import os
import re

BENCH = r"C:\qfb\shaderdev\rounds\bench"
STATS = r"C:\qfb\frills\stats"
SCENE = re.compile(r"^(\w+)\s+frames\s+(\d+)\s+mean\s+([\d.]+) fps\s+p50\s+([\d.]+) ms\s+p99\s+([\d.]+) ms")
WALL = re.compile(r"^\s+wall (\d+)")


def bench(path):
    out, cur = [], None
    for line in open(path, encoding="utf-8", errors="replace"):
        m = SCENE.match(line)
        if m:
            cur = {"scene": m.group(1), "frames": int(m.group(2)), "fps": float(m.group(3)),
                   "p50": float(m.group(4)), "p99": float(m.group(5)), "wall": None}
            out.append(cur)
            continue
        m = WALL.match(line)
        if m and cur is not None and cur["wall"] is None:
            cur["wall"] = int(m.group(1))
    return out


def stats(path):
    rows = []
    for line in open(path, encoding="utf-8", errors="replace"):
        if line.startswith("#") or not line.strip():
            continue
        p = line.split()
        # epochMs all n ns verts leafy n ns verts leafBlocks frillQuads
        rows.append({"t": int(p[0]), "n": int(p[2]), "ns": int(p[3]), "v": int(p[4]),
                     "ln": int(p[6]), "lns": int(p[7]), "lv": int(p[8]), "leaves": int(p[9]), "fq": int(p[10])})
    return rows


def at(rows, t):
    """Running totals at time t: the last row written at or before t (zeros before the first)."""
    best = None
    for r in rows:
        if r["t"] <= t:
            best = r
        else:
            break
    return best or {k: 0 for k in ("t", "n", "ns", "v", "ln", "lns", "lv", "leaves", "fq")}


def delta(a, b):
    return {k: b[k] - a[k] for k in b if k != "t"}


def per_scene(tag, stats_dir):
    scenes = bench(os.path.join(BENCH, tag + ".txt"))
    rows = stats(os.path.join(stats_dir, tag + ".txt"))
    out, prev = {}, {k: 0 for k in ("t", "n", "ns", "v", "ln", "lns", "lv", "leaves", "fq")}
    for s in scenes:
        if s["wall"] is None:
            continue
        cur = at(rows, s["wall"])
        s["mesh"] = delta(prev, cur)
        prev = cur
        out[s["scene"]] = s
    total = rows[-1] if rows else prev
    return out, total


def pct(a, b):
    return "n/a" if not a else f"{(b - a) / a * 100:+.0f}%"


def ms_per(d, n, ns):
    return d[ns] / d[n] / 1e6 if d[n] else 0.0


def v_per(d, n, v):
    return d[v] / d[n] if d[n] else 0.0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--off", required=True, help="bench tag with frills off")
    ap.add_argument("--on", required=True, help="bench tag with frills on")
    ap.add_argument("--stats", default=STATS, help="folder holding TAG.txt MeshStats files")
    ap.add_argument("--md", help="also write the tables here")
    a = ap.parse_args()
    off, toff = per_scene(a.off, a.stats)
    on, ton = per_scene(a.on, a.stats)
    L = [f"Frills off `{a.off}` vs on `{a.on}`.", "",
         "| scene | frame p50 ms off / on | p99 ms off / on | leafy sections built off / on "
         "| ms per leafy section off / on | vertices per leafy section off / on | frill quads |",
         "|---|---|---|---|---|---|---|"]
    for name in off:
        if name not in on:
            continue
        o, n = off[name], on[name]
        mo, mn = o["mesh"], n["mesh"]
        L.append(f"| {name} | {o['p50']:.2f} / {n['p50']:.2f} ({pct(o['p50'], n['p50'])}) "
                 f"| {o['p99']:.2f} / {n['p99']:.2f} ({pct(o['p99'], n['p99'])}) "
                 f"| {mo['ln']} / {mn['ln']} "
                 f"| {ms_per(mo, 'ln', 'lns'):.2f} / {ms_per(mn, 'ln', 'lns'):.2f} "
                 f"({pct(ms_per(mo, 'ln', 'lns'), ms_per(mn, 'ln', 'lns'))}) "
                 f"| {v_per(mo, 'ln', 'lv'):.0f} / {v_per(mn, 'ln', 'lv'):.0f} "
                 f"({pct(v_per(mo, 'ln', 'lv'), v_per(mn, 'ln', 'lv'))}) | {mn['fq']} |")
    L += ["", "Whole boot (every section built, from world load to the last scene):", "",
          "| | sections | ms per section | vertices per section | leafy sections | ms per leafy section "
          "| vertices per leafy section | leaf blocks | frill quads |",
          "|---|---|---|---|---|---|---|---|---|"]
    for label, t in (("off", toff), ("on", ton)):
        L.append(f"| {label} | {t['n']} | {ms_per(t, 'n', 'ns'):.3f} | {v_per(t, 'n', 'v'):.0f} | {t['ln']} "
                 f"| {ms_per(t, 'ln', 'lns'):.3f} | {v_per(t, 'ln', 'lv'):.0f} | {t['leaves']} | {t['fq']} |")
    L.append(f"| change | | {pct(ms_per(toff, 'n', 'ns'), ms_per(ton, 'n', 'ns'))} "
             f"| {pct(v_per(toff, 'n', 'v'), v_per(ton, 'n', 'v'))} | "
             f"| {pct(ms_per(toff, 'ln', 'lns'), ms_per(ton, 'ln', 'lns'))} "
             f"| {pct(v_per(toff, 'ln', 'lv'), v_per(ton, 'ln', 'lv'))} | | |")
    text = "\n".join(L)
    print(text)
    if a.md:
        with open(a.md, "w", encoding="utf-8", newline="\n") as f:
            f.write(text + "\n")


if __name__ == "__main__":
    main()
