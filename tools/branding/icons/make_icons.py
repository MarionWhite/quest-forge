"""Emblem icon set from the 1024 emblem master: key out the flat margin, fit on transparent canvas,
export PNGs (1024/512/256/128/64/32/16), an .icns for -Xdock:icon, pack.png 256."""
import os, shutil, subprocess
from pathlib import Path
import numpy as np, cv2
from PIL import Image, ImageFilter
W = Path(__file__).resolve().parent; OUT = W / "out"; OUT.mkdir(exist_ok=True)
SRC = W.parent / "cc4-branding-v2" / "_work" / "emblem_1024_master.png"
im = Image.open(SRC).convert("RGBA"); a = np.array(im)
rgb = a[..., :3].astype(np.int16)
# flood from every border pixel through the flat margin (tolerance per channel)
bg = np.array([20, 16, 28]); tol = 14
near = (np.abs(rgb - bg) <= tol).all(axis=2).astype(np.uint8)
h, w = near.shape
mask = np.zeros((h + 2, w + 2), np.uint8)
flood = near.copy()
# connected components touching the border
num, lab = cv2.connectedComponents(near, connectivity=4)
border_labels = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]])))
border_labels.discard(0)
margin = np.isin(lab, list(border_labels)).astype(np.float32)
# feather the alpha edge slightly so no halo
alpha = 1.0 - margin
alpha = cv2.GaussianBlur(alpha, (0, 0), 0.8)
alpha = np.clip((alpha - 0.35) / 0.3, 0, 1)
# de-fringe: pull edge pixels toward emblem colours (remove violet margin tint on soft edges)
out = a.copy().astype(np.float32)
out[..., 3] = alpha * 255
ys, xs = np.where(alpha > 0.02)
y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
crop = Image.fromarray(out.astype(np.uint8), "RGBA").crop((x0, y0, x1, y1))
print("keyed bbox", (x0, y0, x1, y1), "margin px", int(margin.sum()))
side = 1024; pad = 0.06
cw, ch = crop.size; scale = side * (1 - 2 * pad) / max(cw, ch)
crop = crop.resize((int(cw * scale), int(ch * scale)), Image.Resampling.LANCZOS)
canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
canvas.alpha_composite(crop, ((side - crop.width) // 2, (side - crop.height) // 2))
# subtle drop shadow for dock legibility
sh = Image.new("RGBA", (side, side), (0, 0, 0, 0)); sh.paste((0, 0, 0, 150), (0, 0), canvas.getchannel("A"))
sh = sh.filter(ImageFilter.GaussianBlur(14))
final = Image.new("RGBA", (side, side), (0, 0, 0, 0)); final.alpha_composite(sh, (0, 10)); final.alpha_composite(canvas)
final.save(OUT / "emblem_icon_1024.png")
iconset = OUT / "QuestForge.iconset"; shutil.rmtree(iconset, ignore_errors=True); iconset.mkdir()
for s in (16, 32, 64, 128, 256, 512):
    r = final.resize((s, s), Image.Resampling.LANCZOS); r.save(OUT / f"emblem_icon_{s}.png")
    r.save(iconset / f"icon_{s}x{s}.png")
    final.resize((s * 2, s * 2), Image.Resampling.LANCZOS).save(iconset / f"icon_{s}x{s}@2x.png")
subprocess.run(["iconutil", "-c", "icns", str(iconset), "-o", str(OUT / "QuestForge.icns")], check=True)
final.resize((256, 256), Image.Resampling.LANCZOS).save(OUT / "pack.png")
print("done", sorted(p.name for p in OUT.iterdir()))
