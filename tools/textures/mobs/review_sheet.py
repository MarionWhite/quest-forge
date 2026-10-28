#!/usr/bin/env python3
"""Review sheet for the Krypt's mob skins: vanilla beside the skin layer the Krypt uses, under its torchlight.

    /usr/local/bin/python3.11 -I tools/textures/mobs/review_sheet.py [OUTDIR] [--mobs Zombie,Spider] [--skin local|own]

One row per mob: close (face-on at about the scares' distance), 6 blocks front, 6 blocks three-quarter; each
vanilla | skin. Frames come from the Krypt's ?dump=1&skinreview hook (site/graves/tex/mobs/review.js) through
tools/site/dump_frames.py, one browser at a time. --skin local shows the local layer (tex/mobs-local, e.g. Patrix);
--skin own shows our painted skins (?ownskins).

The frames can contain third-party pixels, so OUTDIR must be outside the repo or git-ignored; the default is
site/graves/tex/mobs-local/review/ (ignored, local only). Writes OUTDIR/sheet.png and OUTDIR/frames/.
"""
import argparse
import json
import os
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
DEFAULT_OUT = os.path.join(ROOT, "site", "graves", "tex", "mobs-local", "review")
MOBS = ["Zombie", "Skeleton", "WitherSkeleton", "Spider", "CaveSpider", "Creeper", "Enderman", "Witch", "Slime",
        "LavaSlime", "Blaze", "Ghast", "Silverfish", "PigZombie"]
LABEL = {"WitherSkeleton": "Wither Skeleton", "CaveSpider": "Cave Spider", "LavaSlime": "Magma Cube", "PigZombie": "Zombie Pigman"}
# close: (distance, look-at height above the mob's floor); far: look-at height at 6 blocks
CLOSE = {"Zombie": (1.1, 1.72), "Skeleton": (1.1, 1.72), "WitherSkeleton": (1.3, 2.05), "Spider": (1.2, 0.55),
         "CaveSpider": (0.9, 0.35), "Creeper": (1.1, 1.38), "Enderman": (1.5, 2.55), "Witch": (1.1, 1.75),
         "Slime": (1.3, 0.5), "LavaSlime": (1.3, 0.5), "Blaze": (1.3, 1.5), "Ghast": (2.6, 0.95), "Silverfish": (0.8, 0.15),
         "PigZombie": (1.1, 1.72)}
FAR_AIM = {"Ghast": 1.0, "Enderman": 1.5, "WitherSkeleton": 1.2}
EXTRA = {"Ghast": "&scale=0.4"}   # full size, its face is inside most corridor ceilings


def safe_out(path):
    p = os.path.abspath(path)
    if not (p + os.sep).startswith(ROOT + os.sep):
        return True
    return subprocess.run(["git", "-C", ROOT, "check-ignore", "-q", os.path.join(p, "sheet.png")]).returncode == 0


def font(n):
    for f in ("/System/Library/Fonts/Supplemental/Arial Bold.ttf", "/System/Library/Fonts/Supplemental/Arial.ttf",
              "/Library/Fonts/Arial.ttf", "C:/Windows/Fonts/arialbd.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
        if os.path.exists(f):
            return ImageFont.truetype(f, n)
    return ImageFont.load_default()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("out", nargs="?", default=DEFAULT_OUT)
    ap.add_argument("--mobs", default=",".join(MOBS))
    ap.add_argument("--skin", choices=["local", "own"], default="local")
    ap.add_argument("--reuse", action="store_true", help="compose from frames already in OUTDIR/frames")
    a = ap.parse_args()
    if not safe_out(a.out):
        sys.exit(f"review_sheet: {a.out} is inside the repo and not git-ignored; frames may hold third-party art")
    mobs = [m for m in a.mobs.split(",") if m]
    fdir = os.path.join(a.out, "frames")
    os.makedirs(fdir, exist_ok=True)
    skinq = "&ownskins" if a.skin == "own" else ""
    shots = []
    for m in mobs:
        d, h = CLOSE[m]
        for tag, q in (("v", "&vanillaskins"), ("s", skinq)):
            q += EXTRA.get(m, "")
            shots.append((f"{m}_close_{tag}", f"graves/?skinreview={m}&dist={d}&ang=0&aimy={h}{q}"))
            shots.append((f"{m}_far_{tag}", f"graves/?skinreview={m}&dist=6&ang=0" + (f"&aimy={FAR_AIM[m]}" if m in FAR_AIM else "") + q))
            shots.append((f"{m}_34_{tag}", f"graves/?skinreview={m}&dist=6&ang=40" + (f"&aimy={FAR_AIM[m]}" if m in FAR_AIM else "") + q))
    if not a.reuse:
        lst = os.path.join(fdir, "shots.txt")
        with open(lst, "w", encoding="utf-8") as f:
            f.write("".join(f"{n}\t{p}\n" for n, p in shots))
        subprocess.run([sys.executable, "-I", os.path.join(ROOT, "tools", "site", "dump_frames.py"), fdir, "--list", lst,
                        "--jobs", "1"], check=False)

    CW, CH, LW = 380, 300, 150
    cols = [("close", "close"), ("far", "6 blocks"), ("34", "6 blocks, 3/4")]
    sheet = Image.new("RGB", (LW + len(cols) * 2 * CW + (len(cols) - 1) * 10, 40 + len(mobs) * (CH + 6)), (14, 12, 16))
    dr = ImageDraw.Draw(sheet)
    f1, f2 = font(22), font(16)
    for ci, (_, title) in enumerate(cols):
        x = LW + ci * (2 * CW + 10)
        dr.text((x + 6, 10), f"{title}: vanilla", font=f2, fill=(200, 200, 200))
        dr.text((x + CW + 6, 10), f"{title}: {'local skin' if a.skin == 'local' else 'our skin'}", font=f2, fill=(255, 200, 120))
    problems = []
    for ri, m in enumerate(mobs):
        y = 40 + ri * (CH + 6)
        dr.text((8, y + CH // 2 - 12), LABEL.get(m, m), font=f1, fill=(235, 230, 240))
        for ci, (key, _) in enumerate(cols):
            for ti, tag in enumerate(("v", "s")):
                n = f"{m}_{key}_{tag}"
                x = LW + ci * (2 * CW + 10) + ti * CW
                png, js = os.path.join(fdir, n + ".png"), os.path.join(fdir, n + ".json")
                if not os.path.exists(png):
                    problems.append(n + ": no frame")
                    continue
                try:
                    info = json.load(open(js, encoding="utf-8"))
                    if info.get("errors") or info.get("skinreview") != m:
                        problems.append(n + ": " + str(info.get("errors") or "no skinreview frame"))
                except (OSError, ValueError):
                    pass
                im = Image.open(png).convert("RGB")
                W, H = im.size
                if key == "close":
                    k = min(W / CW, H / CH)
                    cw, ch = int(CW * k), int(CH * k)
                else:
                    cw, ch = int(W * 0.34), int(W * 0.34 * CH / CW)
                cx, cy = W // 2, H // 2
                im = im.crop((cx - cw // 2, cy - ch // 2, cx - cw // 2 + cw, cy - ch // 2 + ch)).resize((CW, CH), Image.LANCZOS)
                sheet.paste(im, (x, y))
    out = os.path.join(a.out, "sheet.png")
    sheet.save(out)
    for p in problems:
        print("problem:", p)
    print("sheet:", out)


if __name__ == "__main__":
    main()
