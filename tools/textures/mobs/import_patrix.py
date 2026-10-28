#!/usr/bin/env python3
"""Import Patrix 32x mob skins into the Krypt page's LOCAL-ONLY skin layer.

    /usr/local/bin/python3.11 -I tools/textures/mobs/import_patrix.py Patrix_26.3_32x_basic.zip [more.zip ...]

Patrix is All Rights Reserved. The owner uses its mob skins on his own machine only: this writes ONLY into
site/graves/tex/mobs-local/, which .gitignore excludes, and it refuses any output folder that git does not ignore.
Nothing it writes may ever be committed, pushed or deployed (the public site never loads it: see
site/graves/tex/mobs/skins.js).

Get the zips from https://modrinth.com/resourcepack/patrix-32x (the "basic" file has the entities). For each of the
14 Krypt mobs the first zip that has it wins, so put the preferred version first. The textures are read straight out
of the zips (nothing else is extracted), checked to be a whole multiple of the vanilla sheet size, converted to the
1.7.10 layout where it differs, and written with an index.json that skins.js reads:
  - zombie and pigman (64x64 bipeds): the modern second layer (jacket, right sleeve, right trouser) is drawn over
    the first, since the 1.7.10 model has only the hat as a second layer;
  - Zombie Pigman: packs for 1.16+ have only the zombified piglin, whose head is 10 wide with a separate snout and
    tusks: its middle 8 columns are kept and the snout and tusks are drawn onto the face (the ears are lost);
  - glow: a LabPBR specular map (<name>_s.png) keeps emission in its alpha (1-254); where a mob has enough of it and
    no eyes layer of its own, an additive glow sheet (colour x emission) is written beside the skin.
"""
import argparse
import hashlib
import io
import json
import os
import subprocess
import sys
import zipfile

from PIL import Image

Image.MAX_IMAGE_PIXELS = 4096 * 4096
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
OUT = os.path.join(ROOT, "site", "graves", "tex", "mobs-local")
ENT = "assets/minecraft/textures/entity/"
MAX_MEMBER = 8 * 1024 * 1024

# key (mobs.js MOB_SPECS) -> layers: (candidate paths under textures/entity/, vanilla 1x size, converter)
BIPED64 = (64, 64)
MOBS = {
    "Zombie": [(["zombie/zombie.png"], BIPED64, "biped64")],
    "Skeleton": [(["skeleton/skeleton.png"], (64, 32), None)],
    "WitherSkeleton": [(["skeleton/wither_skeleton.png"], (64, 32), None)],
    "Spider": [(["spider/spider.png"], (64, 32), None), (["spider/spider_eyes.png", "spider_eyes.png"], (64, 32), None)],
    "CaveSpider": [(["spider/cave_spider.png"], (64, 32), None), (["spider/spider_eyes.png", "spider_eyes.png"], (64, 32), None)],
    "Creeper": [(["creeper/creeper.png"], (64, 32), None)],
    "Enderman": [(["enderman/enderman.png"], (64, 32), None), (["enderman/enderman_eyes.png"], (64, 32), None)],
    "Witch": [(["witch/witch.png", "witch.png"], (64, 128), None)],
    "Slime": [(["slime/slime.png"], (64, 32), None), (["slime/slime.png"], (64, 32), None)],
    "LavaSlime": [(["slime/magmacube.png"], (64, 32), None)],
    "Blaze": [(["blaze/blaze.png", "blaze.png"], (64, 32), None)],
    "Ghast": [(["ghast/ghast.png"], (64, 32), None)],
    "Silverfish": [(["silverfish/silverfish.png", "silverfish.png"], (64, 32), None)],
    "PigZombie": [(["zombie_pigman.png", "piglin/zombified_piglin.png"], BIPED64, "pigman")],
}
GLOW_MIN_PIXELS, GLOW_MIN_LEVEL = 8, 16
# Reviewed on the 1.7.10 models in the Krypt (review_sheet.py, 2026-10-27, Patrix #92): these are laid out for
# Patrix's own OptiFine CEM models and break on ours, so they are left out unless --all. (Blaze: a crown where its
# face was; Witch: hair strands land on its arms. Both still read, so they stay in.)
BROKEN = {"LavaSlime": "its slices are a CEM layout: the cube falls apart into fragments",
          "Slime": "its eyes and mouth are CEM parts: a plain textured cube with no face"}


def die(msg):
    sys.exit("import_patrix: " + msg)


def ignored(path):
    """True when git ignores path (and nothing under it is tracked)."""
    r = subprocess.run(["git", "-C", ROOT, "check-ignore", "-q", path], capture_output=True)
    if r.returncode != 0:
        return False
    tracked = subprocess.run(["git", "-C", ROOT, "ls-files", "--", os.path.relpath(path, ROOT)], capture_output=True, text=True)
    return not tracked.stdout.strip()


def read_png(zf, name):
    info = zf.getinfo(name)
    if info.file_size > MAX_MEMBER:
        die(f"{name} is {info.file_size} bytes, too big for a mob skin")
    im = Image.open(io.BytesIO(zf.read(name)))
    if im.format != "PNG":
        die(f"{name} is not a PNG")
    return im.convert("RGBA")


def scale_of(im, size, name):
    s = im.width // size[0]
    if s < 1 or im.width != size[0] * s or im.height != size[1] * s:
        return None
    return s


def paste_region(dst, src, s, sbox, dpos, over=False):
    x, y, w, h = sbox
    part = src.crop((x * s, y * s, (x + w) * s, (y + h) * s))
    if over:
        dst.alpha_composite(part, (dpos[0] * s, dpos[1] * s))
    else:
        dst.paste(part, (dpos[0] * s, dpos[1] * s))


def biped64(im, s):
    """1.8+ biped (64x64) to the 1.7.10 one: the second layer of body, right arm and right leg drawn over the first."""
    out = im.copy()
    for src, dst in (((16, 32, 24, 16), (16, 16)), ((40, 32, 16, 16), (40, 16)), ((0, 32, 16, 16), (0, 16))):
        paste_region(out, im, s, src, dst, over=True)
    return out


def pigman(im, s, name):
    if not name.endswith("zombified_piglin.png"):
        return biped64(im, s)
    out = Image.new("RGBA", im.size, (0, 0, 0, 0))
    # head: the piglin's is 10 x 8 x 8 at (0, 0); keep the middle 8 columns of the front, back, top and bottom
    paste_region(out, im, s, (0, 8, 8, 8), (0, 8))      # right side
    paste_region(out, im, s, (18, 8, 8, 8), (16, 8))    # left side
    paste_region(out, im, s, (9, 8, 8, 8), (8, 8))      # front
    paste_region(out, im, s, (27, 8, 8, 8), (24, 8))    # back
    paste_region(out, im, s, (9, 0, 8, 8), (8, 0))      # top
    paste_region(out, im, s, (19, 0, 8, 8), (16, 0))    # bottom
    # the snout (4 x 4 x 1 at (31, 1), x -2..2, y -4..0) and the tusks (1 x 2 x 1 at (2, 4) x 2..3, (2, 0) x -3..-2)
    paste_region(out, im, s, (32, 2, 4, 4), (8 + 2, 8 + 4), over=True)
    paste_region(out, im, s, (3, 5, 1, 2), (8 + 6, 8 + 6), over=True)
    paste_region(out, im, s, (3, 1, 1, 2), (8 + 1, 8 + 6), over=True)
    # body, right arm, right leg as they are, then their second layer over them
    for box in ((16, 16, 24, 16), (40, 16, 16, 16), (0, 16, 16, 16)):
        paste_region(out, im, s, box, box[:2])
    for src, dst in (((16, 32, 24, 16), (16, 16)), ((40, 32, 16, 16), (40, 16)), ((0, 32, 16, 16), (0, 16))):
        paste_region(out, im, s, src, dst, over=True)
    return out


def glow_of(zf, names, base_name, base):
    """An additive glow sheet from a LabPBR specular map's alpha (emission 1..254), or None."""
    sname = base_name[:-4] + "_s.png"
    if sname not in names:
        return None, 0
    spec = read_png(zf, sname)
    if spec.size != base.size:
        return None, 0
    a = spec.getchannel("A")
    em = [v if 0 < v < 255 else 0 for v in a.getdata()]
    lit = [v for v in em if v]
    if len(lit) < GLOW_MIN_PIXELS or max(lit) < GLOW_MIN_LEVEL:
        return None, len(lit)
    g = base.copy()
    mask = Image.new("L", base.size)
    mask.putdata([min(255, round(v * 255 / 254)) for v in em])
    g.putalpha(Image.composite(mask, Image.new("L", base.size, 0), base.getchannel("A")))
    return g, len(lit)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("zips", nargs="+")
    ap.add_argument("--out", default=OUT, help="must be a folder git ignores (default: %(default)s)")
    ap.add_argument("--all", action="store_true", help="also import the mobs that look wrong on 1.7.10 models (BROKEN)")
    a = ap.parse_args()
    out = os.path.abspath(a.out)
    if not ignored(os.path.join(out, "index.json")):
        die(f"{out} is not ignored by git (or has tracked files): refusing to write third-party art there")
    os.makedirs(out, exist_ok=True)
    for f in os.listdir(out):                    # this importer's own files from an earlier run
        if f.endswith(".png") and f.split("_")[0].split(".")[0] in MOBS:
            os.remove(os.path.join(out, f))

    zips = []
    for p in a.zips:
        zf = zipfile.ZipFile(p)
        h = hashlib.sha256(open(p, "rb").read()).hexdigest()
        zips.append((p, zf, set(zf.namelist()), h))

    index = {"note": "LOCAL ONLY. Third-party art (Patrix 32x, All Rights Reserved): never commit, push or deploy.",
             "generator": "tools/textures/mobs/import_patrix.py",
             "sources": [{"zip": os.path.basename(p), "sha256": h} for p, _, _, h in zips], "mobs": {}}
    report = []
    for key, layers in MOBS.items():
        if key in BROKEN and not a.all:
            report.append(f"{key}: left out ({BROKEN[key]}); --all imports it anyway")
            continue
        files, srcs, zipname, glow = [], [], None, None
        for p, zf, names, _ in zips:
            got = []
            for cands, size, conv in layers:
                name = next((ENT + c for c in cands if ENT + c in names), None)
                if not name:
                    got = None
                    break
                im = read_png(zf, name)
                s = scale_of(im, size, name)
                if not s:
                    report.append(f"{key}: {name} is {im.size}, not a multiple of {size}; skipped in {os.path.basename(p)}")
                    got = None
                    break
                if conv == "biped64":
                    im = biped64(im, s)
                elif conv == "pigman":
                    im = pigman(im, s, name)
                got.append((name, im, s))
            if got:
                zipname = os.path.basename(p)
                for i, (name, im, s) in enumerate(got):
                    if i and name == got[0][0]:          # the same sheet again (slime outer)
                        files.append(files[0]); srcs.append(name[len(ENT):]); continue
                    fn = f"{key}{'' if i == 0 else '_' + str(i)}.png"
                    im.save(os.path.join(out, fn))
                    files.append(fn); srcs.append(name[len(ENT):])
                if len(layers) == 1:                     # mobs with an eyes layer already glow there
                    g, n = glow_of(zf, names, got[0][0], got[0][1])
                    if g is not None:
                        glow = f"{key}_glow.png"
                        g.save(os.path.join(out, glow))
                        report.append(f"{key}: glow layer from {got[0][0][len(ENT):-4]}_s.png ({n} px)")
                break
        if not files:
            report.append(f"{key}: not found in any zip; stays on the next skin down")
            continue
        entry = {"layers": files, "from": srcs, "zip": zipname, "scale": got[0][2]}
        if glow:
            entry["glow"] = glow
        index["mobs"][key] = entry
    with open(os.path.join(out, "index.json"), "w", encoding="utf-8") as f:
        json.dump(index, f, indent=1)
    for line in report:
        print(line)
    print(f"{len(index['mobs'])}/{len(MOBS)} mobs written to {os.path.relpath(out, ROOT)} (git-ignored, local only)")


if __name__ == "__main__":
    main()
