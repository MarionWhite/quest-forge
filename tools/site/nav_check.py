#!/usr/bin/env python3
"""Proof that nobody walks through a prop on the Lucky Block page.

    nav_check.py "lucky/?idle=60000" "lucky/?scene=mob_horde&at=14000" ...
    nav_check.py --bosses        # the boss and grand scenes: big mobs must clear trees and props
    nav_check.py --acts          # every one of the 29 activities alone, then 2 min of idle: feet, blocks, nav
    nav_check.py --cover         # 15 simulated minutes of idle: every activity must have started at least once

Each page is loaded like dump_frames.py does (?dump=1, headless Chrome). site/lucky/nav.js counts every
sampled position of Steve and of the ground mobs against the occupancy map and publishes
{samples, violations, first, by, feet, world, acts} as <html data-nav-stats>. Prints one line per page; exit 1
if any page has a violation or no samples. Beyond the footprint check there are two more:
  feet:  every frame, Steve's feet height against the real surface under him (ground, a hole, a placed block, the
         bench, the dais), error <= 0.05 unless he is in the air; a climb of more than half a block that is not a
         jump counts too
  world: every change to a block (break, place, plant, dig) must have an arm swing just before it, and a block
         put back silently must be out of the camera frame at that moment
"""
import html, json, os, re, shutil, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dump_frames as D


def run(exe, port, path, budget=60000, timeout=240):
    sep = "&" if "?" in path else "?"
    url = f"http://127.0.0.1:{port}/{path.lstrip('/')}{sep}dump=1"
    prof = tempfile.mkdtemp(prefix="navcheck-")
    cmd = [exe, "--headless=new", "--no-first-run", f"--user-data-dir={prof}", "--run-all-compositor-stages-before-draw",
           f"--virtual-time-budget={budget}", "--window-size=800,500", "--dump-dom", url]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout).stdout
    except subprocess.TimeoutExpired:
        return None
    finally:
        shutil.rmtree(prof, ignore_errors=True)
    m = re.search(r'data-nav-stats="([^"]*)"', out)
    return json.loads(html.unescape(m.group(1))) if m else None


# every boss and grand scene whose big mobs walk in (forced drop indexes of data/lucky.json), seen at the
# moment they have arrived. Their footprint is the model's real width times its scale (mobscenes.js).
BOSSES = [143, 144, 150, 151, 152, 162, 163, 164, 169, 170, 172, 186, 196, 204, 209]


ACTS = ["tree", "mine", "iron", "chest", "place", "fish", "sit", "sunset", "chicken", "pillar", "dance", "sneak",
        "harvest", "sapling", "eat", "dog", "shear", "milk", "torches", "read", "bow", "notes", "hut", "stones",
        "enchant", "brew", "parkour", "hole", "creeper"]


def bad_of(st):
    if not st or not st.get("samples"):
        return True
    w, f = st.get("world") or {}, st.get("feet") or {}
    return bool(st["violations"] or st.get("noroute") or w.get("bad") or f.get("bad"))


def main():
    exe = D.browser()
    httpd, port = D.serve()
    bad = 0
    args = sys.argv[1:]
    if "--bosses" in args:
        args = [a for a in args if a != "--bosses"] + [f"lucky/?force={i}&at=15500" for i in BOSSES]
    cover = "--cover" in args
    if "--acts" in args:
        args = [a for a in args if a != "--acts"] + [f"lucky/?idle=100000&act={a}" for a in ACTS]
    if cover:
        args = [a for a in args if a != "--cover"] + ["lucky/?idle=900000"]
    for p in args:
        st = run(exe, port, p, timeout=300)
        if bad_of(st):
            bad += 1
        if cover and "idle=900000" in p and st:
            missing = [a for a in ACTS if not (st.get("acts") or {}).get(a)]
            print("coverage: started", len(ACTS) - len(missing), "of", len(ACTS), "missing", missing, "first starts (s):", st.get("actFirst"))
            if missing:
                bad += 1
        print(p, "->", json.dumps(st))
    httpd.shutdown()
    sys.exit(1 if bad else 0)


main()
