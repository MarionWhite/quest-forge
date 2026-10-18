#!/usr/bin/env python3
"""Overview render of a whole expanded continent (decision 0003): biome colours with hillshade,
built from the full-resolution piece heights that WorldPainter exported (plan.py expand output),
with region labels, spawn/landmark points and optional boxes for test areas.

    py -3.10 tools/world/render_overview.py PIECES_DIR PLAN_DIR OUT.png [--scale 8]
        [--box NAME X Z R ...]

--scale is blocks per output pixel (8 -> a 4096 px image for a 32,768-block world).
Biome colours follow the WorldPainter palette in wp_common.js, by biome name.
"""
import argparse, glob, json, os, re
import numpy as np
from PIL import Image, ImageDraw, ImageFont

Image.MAX_IMAGE_PIXELS = None
SEA = 62
PALETTE = [
    (r"snow|frost|glacier|polar|arctic|ice|alps|tundra|frozen", (232, 240, 248)),
    (r"redwood|sequoia", (122, 46, 30)),
    (r"volcan|wasteland|ash|dead|scorched", (95, 85, 80)),
    (r"desert|dune|mesa|badland|canyon|outback|savanna|steppe|xeric|arid", (217, 181, 106)),
    (r"swamp|bog|fen|marsh|moor|bayou|wetland|sludge|mangrove|quagmire", (74, 94, 58)),
    (r"jungle|tropic|rainforest|bamboo|rain forest", (46, 139, 46)),
    (r"deep ocean", (30, 60, 140)),
    (r"ocean|sea|coral|kelp|reef|lagoon|lake", (58, 111, 194)),
    (r"river", (70, 130, 220)),
    (r"beach|shore|oasis", (220, 205, 150)),
    (r"lavender", (170, 140, 210)),
    (r"cherry", (230, 170, 200)),
    (r"mystic|ominous|mushroom|fungi", (120, 80, 140)),
    (r"mountain|peak|crag|cliff|hill|highland|ridge|plateau", (140, 140, 140)),
    (r"taiga|pine|conifer|boreal|spruce|fir", (47, 93, 74)),
    (r"forest|wood|grove|thicket|orchard|maple|birch|seasonal", (63, 127, 47)),
    (r"plain|prairie|meadow|field|grass|heath|shrub|flower", (141, 179, 96)),
]


def biome_lut(tsv):
    lut = np.array([(150, 150, 150)] * 256, np.float32)
    for line in open(tsv, encoding="utf-8"):
        if line.startswith("#") or line.startswith("id\t"):
            continue
        f = line.rstrip("\n").split("\t")
        i, n = int(f[0]), f[1].lower()
        for pat, c in PALETTE:
            if re.search(pat, n):
                lut[i] = c
                break
    return lut


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pieces")
    ap.add_argument("plan")
    ap.add_argument("out")
    ap.add_argument("--scale", type=int, default=8)
    ap.add_argument("--box", nargs=4, action="append", default=[], metavar=("NAME", "X", "Z", "R"))
    ap.add_argument("--biomes", default=os.path.join(os.path.dirname(__file__), "..", "..", "docs", "survey", "biome-ids.tsv"))
    a = ap.parse_args()
    meta = json.load(open(os.path.join(a.plan, "plan.json")))
    size, k = meta["size"], a.scale
    half, n = size // 2, size // a.scale
    H = np.zeros((n, n), np.float32)
    B = np.zeros((n, n), np.uint8)
    for d in glob.glob(os.path.join(a.pieces, "piece_*")):
        ox, oz = map(int, open(os.path.join(d, "origin.txt")).read().split())
        h = np.asarray(Image.open(os.path.join(d, "height.png"))).astype(np.float32) / 257
        b = np.asarray(Image.open(os.path.join(d, "biome.png")))
        p = h.shape[0] // k
        h = h[:p * k, :p * k].reshape(p, k, p, k).mean(axis=(1, 3))
        b = b[k // 2::k, k // 2::k][:p, :p]
        px, pz = (ox + half) // k, (oz + half) // k
        H[pz:pz + p, px:px + p], B[pz:pz + p, px:px + p] = h, b
        del h, b
    rgb = biome_lut(a.biomes)[B]
    gz, gx = np.gradient(H)
    shade = np.clip(1 + (-gx - gz) * 0.6 / k * 8, 0.5, 1.5)
    land = H >= SEA
    alt = 0.8 + 0.4 * np.clip((H - SEA) / 140, 0, 1)
    depth = np.clip((SEA - H) / 40, 0, 1)
    rgb = np.where(land[..., None], rgb * (shade * alt)[..., None], rgb * (1 - 0.45 * depth)[..., None])
    im = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8))
    dr = ImageDraw.Draw(im)
    try:
        font = ImageFont.truetype("arial.ttf", max(14, n // 160))
        big = ImageFont.truetype("arialbd.ttf", max(18, n // 110))
    except OSError:
        font = big = ImageFont.load_default()
    w2p = lambda x, z: ((x + half) / k, (z + half) / k)
    for lab in meta["labels"]:
        pts = lab["polygon"]
        ar = cx = cz = 0.0
        for (x1, z1), (x2, z2) in zip(pts, pts[1:] + pts[:1]):
            c = x1 * z2 - x2 * z1
            ar, cx, cz = ar + c, cx + (x1 + x2) * c, cz + (z1 + z2) * c
        if abs(ar) < 1e-6:
            continue
        dr.text(w2p(cx / (3 * ar), cz / (3 * ar)), lab["name"], fill="white", font=font, anchor="mm",
                stroke_width=2, stroke_fill="black")
    for p in meta.get("points", []):
        x, z = w2p(p["x"], p["z"])
        col = {"spawn": "#ffe14d", "landmark": "#ff5050"}.get(p.get("kind"), "white")
        dr.ellipse((x - 7, z - 7, x + 7, z + 7), fill=col, outline="black", width=2)
        dr.text((x + 11, z), p["name"], fill=col, font=font, anchor="lm", stroke_width=2, stroke_fill="black")
    for name, X, Z, R in a.box:
        X, Z, R = int(X), int(Z), int(R)
        x0, z0 = w2p(X - R, Z - R)
        x1, z1 = w2p(X + R, Z + R)
        dr.rectangle((x0, z0, x1, z1), outline="#00ffff", width=4)
        dr.text((x0, z0 - 4), name, fill="#00ffff", font=big, anchor="lb", stroke_width=3, stroke_fill="black")
    # piece seams (16,384-block pieces meet at x=0 and z=0)
    mid = n // 2
    for t in range(0, n, 40):
        dr.line([(mid, t), (mid, t + 18)], fill=(255, 255, 255), width=1)
        dr.line([(t, mid), (t + 18, mid)], fill=(255, 255, 255), width=1)
    dr.text((20, 20), f"Continent v0, {size} blocks, 1 px = {k} blocks; dashed: piece seams x=0, z=0",
            fill="white", font=big, stroke_width=3, stroke_fill="black")
    im.save(a.out, optimize=True)
    print(f"overview {n}x{n} -> {a.out}")


if __name__ == "__main__":
    main()
