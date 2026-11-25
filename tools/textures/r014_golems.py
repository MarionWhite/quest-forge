#!/usr/bin/env python3
"""r014: snow golem options, one tiny overlay zip each (entity/snowman.png only), copied from the reference packs.

    py -3.10 -I tools/textures/r014_golems.py --out-dir C:\\qfb\\textures\\r014

The owner, r013 view 6: "Snow golem is still default" (round 12's set A has Patrix's, near-vanilla white). Options, all
on the vanilla 64x64 box layout (checked by eye against 1.7.10's sheet; HD sizes scale with the model's UVs):
  faithless  Faithless: red scarf and hat band (r013's B)
  soartex    Soartex Forever: soft shaded snow, coal buttons down the front
  conquest   Conquest_ 1.8: rough packed snow (its pumpkin-head overlay needs MCPatcher random mobs, off in this pack)
Patrix is not offered: it is what reads as default. Read from C:\\qf-world\\reference-packs at build time (the owner
allows copying these packs into the private pack); the zips are never committed and never on the public site.
These sit in renderq's rps_top so they win over QF-r012-packs-final.zip's snowman.png.
"""
import argparse, io, os, zipfile

from PIL import Image

REF = r"C:\qf-world\reference-packs"
SRC = {
    "faithless": (os.path.join(REF, "Faithless", "Faithless.zip"), "assets/minecraft/textures/entity/snow_golem.png"),
    "soartex": (os.path.join(REF, "Soartex Forever", "Soartex Forever.zip"),
                "assets/minecraft/textures/entity/snow_golem.png"),
    "conquest": (os.path.join(REF, "Conquest_", "Conquest_1.8.zip"), "assets/minecraft/textures/entity/snowman.png"),
}
DEST = "assets/minecraft/textures/entity/snowman.png"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out-dir", required=True)
    a = ap.parse_args()
    os.makedirs(a.out_dir, exist_ok=True)
    for name, (zp, member) in SRC.items():
        with zipfile.ZipFile(zp) as z:
            im = Image.open(io.BytesIO(z.read(member))).convert("RGBA")
        if im.width != im.height:
            raise SystemExit("%s: %dx%d is not the 1.7.10 square sheet" % (name, im.width, im.height))
        b = io.BytesIO()
        im.save(b, "PNG")
        out = os.path.join(a.out_dir, "QF-r014-golem-%s.zip" % name)
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("pack.mcmeta", '{"pack": {"pack_format": 1, "description": "QF r014 snow golem: %s"}}' % name)
            z.writestr(DEST, b.getvalue())
        print("golem %s (%dx%d) -> %s" % (name, im.width, im.height, out))


if __name__ == "__main__":
    main()
