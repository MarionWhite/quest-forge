#!/usr/bin/env python3
"""Encode the loading plates the mod ships, from the 4K finish masters.

The masters are 3840x2160 PNG, 140 MB, and are not in this repository -- they
live on the `art-masters-2026-09-08` release. What the mod ships is derived from
them, so this script is the artifact and the JPEGs under
`mods/qf-content/src/main/resources/assets/qfcontent/textures/gui/loading/` are
its output.

WHY JPEG. These are photographic 16:9 stills behind a loading screen, which is
the case JPEG exists for. At q92 the whole set is 14 MB against 100 MB of PNG,
with nothing visible lost at the size it is drawn. The pack already ships its
menu backgrounds as .jpg for the same reason, and Minecraft reads them through
ImageIO like any other image.

WHY 2560x1440 BY DEFAULT. That is the native resolution of the machine this pack
is developed and played on, so a plate is drawn 1:1 with no upscale. 1280 -- what
was tried first -- is a 2x upscale on that display and looks it. 4K costs 10 MB
more in the jar and 32 MB of texture memory per plate shown, and only pays off on
a monitor nobody here has. Pass --width/--height to change it.

    python make_shipped_plates.py --masters <dir with the 4k pngs>
    python make_shipped_plates.py --masters <dir> --width 3840 --height 2160
"""
import argparse
import os
import sys

try:
    from PIL import Image
except ImportError:
    sys.exit("Pillow is required: pip install Pillow")


DEST = os.path.join("mods", "qf-content", "src", "main", "resources",
                    "assets", "qfcontent", "textures", "gui", "loading")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--masters", required=True,
                    help="directory holding the 3840x2160 finish masters")
    ap.add_argument("--repo", default=".", help="repo root")
    ap.add_argument("--width", type=int, default=2560)
    ap.add_argument("--height", type=int, default=1440)
    ap.add_argument("--quality", type=int, default=92)
    args = ap.parse_args()

    masters = []
    for root, _, files in os.walk(args.masters):
        for f in sorted(files):
            if f.lower().endswith(".png"):
                masters.append(os.path.join(root, f))

    if not masters:
        sys.exit("no .png masters found under %s" % args.masters)

    dest = os.path.join(args.repo, DEST)
    os.makedirs(dest, exist_ok=True)

    total = 0
    for path in sorted(masters):
        image = Image.open(path).convert("RGB")

        if image.size != (args.width, args.height):
            # LANCZOS to match how the finish pass produced the masters, so a
            # downscale here is the same operation run twice rather than a
            # different one layered on top.
            image = image.resize((args.width, args.height), Image.LANCZOS)

        out = os.path.join(dest, os.path.basename(path)[:-4] + ".jpg")
        image.save(out, "JPEG", quality=args.quality, optimize=True)
        total += os.path.getsize(out)

    print("wrote %d plates at %dx%d, q%d -- %.1f MB"
          % (len(masters), args.width, args.height, args.quality, total / 1048576.0))
    print("dimension -> file mapping lives in LoadingPlates.java, not here;")
    print("tools/verify_pack.py checks the two agree.")


if __name__ == "__main__":
    main()
