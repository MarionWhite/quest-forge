"""Turns the IconBake render into the inventory icon.

The bake (debug build, -Dqf.iconbake=<file>, shader pack off so the chrome
reflects) is a 1024-pixel picture of the live model on a transparent ground.
This crops it to the cabinet, fits it into a square with a little margin, and
filters it down with premultiplied alpha so the edges do not pick up a dark
fringe from the transparent black around them.

    py -3.10 make_icon.py [bake.png]
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "out" / "icon" / "jukebox_icon_1024.png"
DEST = (HERE.parents[2] / "mods" / "qf-content" / "src" / "main" / "resources" / "assets"
        / "qfcontent" / "textures" / "items" / "jukebox_icon.png")
SIZE = 64
MARGIN = 1

a = np.asarray(Image.open(SRC).convert("RGBA")).astype(np.float32) / 255
alpha = a[..., 3]
ys, xs = np.nonzero(alpha > 0.02)
a = a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
h, w = a.shape[:2]

# Square it on a transparent ground, the cabinet centred and standing on the foot.
side = max(h, w)
sq = np.zeros((side, side, 4), np.float32)
x0 = (side - w) // 2
sq[side - h:, x0:x0 + w] = a

pre = sq.copy()
pre[..., :3] *= pre[..., 3:4]
inner = SIZE - 2 * MARGIN
chans = [np.asarray(Image.fromarray(pre[..., c]).resize((inner, inner), Image.LANCZOS))
         for c in range(4)]
small = np.clip(np.stack(chans, -1), 0, 1)
rgb = np.where(small[..., 3:4] > 1e-4, small[..., :3] / np.maximum(small[..., 3:4], 1e-4), 0)
out = np.zeros((SIZE, SIZE, 4), np.float32)
out[MARGIN:MARGIN + inner, MARGIN:MARGIN + inner, :3] = np.clip(rgb, 0, 1)
out[MARGIN:MARGIN + inner, MARGIN:MARGIN + inner, 3] = small[..., 3]

DEST.parent.mkdir(parents=True, exist_ok=True)
Image.fromarray((out * 255 + 0.5).astype(np.uint8), "RGBA").save(DEST)
print("alpha range of bake:", float(alpha.min()), float(alpha.max()))
print("wrote", DEST)
