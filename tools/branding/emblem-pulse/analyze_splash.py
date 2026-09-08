# -*- coding: utf-8 -*-
from pathlib import Path
from PIL import Image

p = Path(r"C:\Users\a2dsu\OneDrive\Desktop\QuestForge-Work\_emblem-pulse")
im = Image.open(p / "smoke_splash1.png").convert("RGBA")
w, h = im.size
print("size", w, h)
# save quadrants
im.crop((w // 2, h // 2, w, h)).save(p / "smoke_splash1_br.png")
# scan for orange-ish pixels (gem/bloom)
px = im.load()
orange = []
for y in range(h):
    for x in range(w):
        r, g, b, a = px[x, y]
        if r > 160 and r > g + 30 and g > b and r + g > 280:
            orange.append((x, y, r, g, b))
print("orange_count", len(orange))
if orange:
    xs = [t[0] for t in orange]
    ys = [t[1] for t in orange]
    print("orange bbox", min(xs), min(ys), max(xs), max(ys))
    print("sample", orange[len(orange)//2])
