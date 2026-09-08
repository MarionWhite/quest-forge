# -*- coding: utf-8 -*-
from pathlib import Path
from PIL import Image

p = Path(r"C:\Users\a2dsu\OneDrive\Desktop\QuestForge-Work\_emblem-pulse")
files = ["smoke_splash1.png", "smoke_splash2.png", "smoke_splash3.png"]
for name in files:
    im = Image.open(p / name).convert("RGB")
    w, h = im.size
    # lower-right 40%
    crop = im.crop((int(w * 0.55), int(h * 0.45), w, h))
    crop.save(p / (name.replace(".png", "_br.png")))
    px = list(crop.getdata())
    # orange-ish
    oranges = [c for c in px if c[0] > 150 and c[0] > c[1] + 20 and c[1] > c[2] - 15]
    if oranges:
        avg = tuple(sum(c[i] for c in oranges) / len(oranges) for i in range(3))
        mx = max(c[0] for c in oranges)
    else:
        avg, mx = (0, 0, 0), 0
    # also whole-crop mean
    mean = tuple(sum(c[i] for c in px) / len(px) for i in range(3))
    print(name, "size", crop.size, "orange_n", len(oranges), "orange_avg", [round(x, 1) for x in avg], "orange_maxR", mx, "crop_mean", [round(x, 1) for x in mean])
