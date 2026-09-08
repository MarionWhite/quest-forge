#!/usr/bin/env python3
"""Quest Forge main-menu buttons: dark fissured stone plates, rugged edges,
fissures dark when idle and amber-lit on hover.

Output: out/<name>.png + out/<name>over.png (RGBA) and matching .mcmeta (bilinear),
sizes 1800x240 (big, drawn at 180x24 GUI units) and 900x240 (small, 90x24).
Run with --install to back up and write into the live QuestForge.zip and CustomMenu.jar.
"""
import io, json, os, shutil, sys, time, zipfile
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W = Path(__file__).resolve().parent
OUT = W / "out"
FONT = "/System/Library/Fonts/Supplemental/Georgia Bold.ttf"
BIG, SMALL = (1800, 240), (900, 240)
BAKE_TEXT = "--no-text" not in sys.argv
BUTTONS = [
    ("single", "Singleplayer", BIG, 11),
    ("multiplayer", "Multiplayer", BIG, 23),
    ("mods", "Mods", BIG, 37),
    ("publicserver", "Official Public Server", BIG, 41),
    ("options", "Options", SMALL, 53),
    ("quit", "Quit", SMALL, 67),
]
LIVE = Path(os.path.expanduser("~/Library/Application Support/PrismLauncher/instances/Quest Forge/minecraft"))


# ----------------------------------------------------------------- noise helpers
def value_noise(h, w, cx, cy, r):
    g = r.random((cy + 1, cx + 1)).astype(np.float32)
    return cv2.resize(g, (w, h), interpolation=cv2.INTER_CUBIC)


def fbm(h, w, r, base_cells=6, octaves=5, persistence=0.5):
    out = np.zeros((h, w), np.float32)
    amp, tot = 1.0, 0.0
    cx, cy = base_cells, max(1, int(round(base_cells * h / w)))
    for _ in range(octaves):
        out += amp * value_noise(h, w, cx, cy, r)
        tot += amp
        amp *= persistence
        cx, cy = cx * 2, cy * 2
        if cx > w:
            break
    return out / tot


def blur(a, s):
    return cv2.GaussianBlur(a, (0, 0), s)


def smoothstep(x):
    x = np.clip(x, 0, 1)
    return x * x * (3 - 2 * x)


# ----------------------------------------------------------------- plate shape
def plate_mask(h, w, r):
    m = int(h * 0.07)
    mask = np.zeros((h, w), np.float32)
    mask[m:h - m, m:w - m] = 1
    xs, ys = np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))
    wx = (fbm(h, w, r, 7, 3) - 0.5) * 2 * 8 + (fbm(h, w, r, 45, 2) - 0.5) * 2 * 3
    wy = (fbm(h, w, r, 7, 3) - 0.5) * 2 * 8 + (fbm(h, w, r, 45, 2) - 0.5) * 2 * 3
    mask = cv2.remap(mask, xs + wx, ys + wy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    # angular chips bitten out of the rim
    for _ in range(int(w / 70)):
        side = r.integers(4)
        if side == 0:
            cx, cy = r.uniform(0, w), m + r.uniform(-3, 3)
        elif side == 1:
            cx, cy = r.uniform(0, w), h - m + r.uniform(-3, 3)
        elif side == 2:
            cx, cy = m + r.uniform(-3, 3), r.uniform(0, h)
        else:
            cx, cy = w - m + r.uniform(-3, 3), r.uniform(0, h)
        n = int(r.integers(3, 6))
        ang = np.sort(r.uniform(0, 2 * np.pi, n))
        rad = r.uniform(5, 18, n)
        pts = np.stack([cx + np.cos(ang) * rad * 1.6, cy + np.sin(ang) * rad], 1).astype(np.int32)
        cv2.fillPoly(mask, [pts], 0.0)
    # corners: knock the corners off irregularly
    for (cx, cy) in ((m, m), (w - m, m), (m, h - m), (w - m, h - m)):
        n = int(r.integers(3, 5))
        ang = np.sort(r.uniform(0, 2 * np.pi, n))
        rad = r.uniform(10, 26, n)
        pts = np.stack([cx + np.cos(ang) * rad * 1.5, cy + np.sin(ang) * rad], 1).astype(np.int32)
        cv2.fillPoly(mask, [pts], 0.0)
    hard = (mask > 0.5).astype(np.float32)
    return blur(hard, 0.7)


# ----------------------------------------------------------------- fissures
def voronoi_edges(h, w, r, n_seeds, warp_amp, warp_cells):
    xs, ys = np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))
    wx = (fbm(h, w, r, warp_cells, 4) - 0.5) * 2 * warp_amp
    wy = (fbm(h, w, r, warp_cells, 4) - 0.5) * 2 * warp_amp
    px, py = xs + wx, ys + wy
    sx = r.uniform(-0.05 * w, 1.05 * w, n_seeds)
    sy = r.uniform(-0.3 * h, 1.3 * h, n_seeds)
    d = np.stack([np.hypot(px - a, py - b) for a, b in zip(sx, sy)], 0)
    d.sort(axis=0)
    return (d[1] - d[0]).astype(np.float32)  # 0 on the cell boundary


def fissures(h, w, r):
    # main deep fissures: sparse, wandering, tapering out
    e = voronoi_edges(h, w, r, int(w / 150), 30, 5)
    width = 6.0 + 7.0 * fbm(h, w, r, 9, 3)
    prof = np.clip(1 - e / width, 0, 1) ** 1.3
    keep = fbm(h, w, r, 5, 4)
    prof *= smoothstep((keep - 0.42) / 0.14)
    # hairline cracks: sparse, thin, faint
    e2 = voronoi_edges(h, w, r, int(w / 75), 14, 9)
    hair = np.clip(1 - e2 / 1.6, 0, 1)
    keep2 = fbm(h, w, r, 7, 4)
    hair *= smoothstep((keep2 - 0.58) / 0.10)
    hair *= (1 - prof)
    return prof, hair


# ----------------------------------------------------------------- text
def text_mask(h, w, label):
    size = int(h * 0.50)
    while True:
        font = ImageFont.truetype(FONT, size)
        l, t, rgt, b = font.getbbox(label)
        if rgt - l <= 0.74 * w or size < 20:
            break
        size -= 3
    im = Image.new("L", (w, h), 0)
    ImageDraw.Draw(im).text((w / 2, h / 2 - h * 0.015), label, fill=255, font=font, anchor="mm")
    return np.asarray(im).astype(np.float32) / 255.0


def shift(a, dx, dy):
    return np.roll(np.roll(a, dy, 0), dx, 1)


# ----------------------------------------------------------------- render
def render(name, label, size, seed):
    w, h = size
    r = np.random.default_rng(seed)
    mask = plate_mask(h, w, r)
    dist = cv2.distanceTransform((mask > 0.5).astype(np.uint8), cv2.DIST_L2, 5).astype(np.float32)
    bevel = smoothstep(dist / 11.0)
    crack, hair = fissures(h, w, r)
    crack *= smoothstep((dist - 2) / 6.0)
    hair *= smoothstep((dist - 1) / 4.0)

    # height field and lighting
    ridged = 1 - np.abs(2 * fbm(h, w, r, 12, 4) - 1)          # angular flake facets
    facets = np.abs(2 * fbm(h, w, r, 28, 3) - 1)
    pits = smoothstep((fbm(h, w, r, 90, 2) - 0.74) / 0.10)     # small pockmarks
    height = (0.55 + (fbm(h, w, r, 4, 3) - 0.5) * 0.45 + (ridged - 0.5) * 0.22 + (facets - 0.5) * 0.14
              + (fbm(h, w, r, 60, 3) - 0.5) * 0.12 + (fbm(h, w, r, 220, 2) - 0.5) * 0.06 - pits * 0.08)
    height = (height * bevel - 1.25 * crack - 0.30 * hair).astype(np.float32)
    gx = cv2.Sobel(height, cv2.CV_32F, 1, 0, ksize=3) / 8.0
    gy = cv2.Sobel(height, cv2.CV_32F, 0, 1, ksize=3) / 8.0
    S = 22.0
    nx, ny = -gx * S, -gy * S
    norm = np.sqrt(nx * nx + ny * ny + 1)
    L = np.array([-0.45, -0.60, 0.66]); L /= np.linalg.norm(L)
    diff = np.clip((nx * L[0] + ny * L[1] + L[2]) / norm, 0, 1)
    Hh = L + np.array([0, 0, 1.0]); Hh /= np.linalg.norm(Hh)
    spec = np.clip((nx * Hh[0] + ny * Hh[1] + Hh[2]) / norm, 0, 1) ** 28 * 0.10

    # albedo: dark grey stone with mottling, patches, grain, a few warm veins
    mottle = fbm(h, w, r, 5, 4)
    patches = fbm(h, w, r, 13, 3)
    grain = fbm(h, w, r, 260, 2)
    streak = fbm(h, w, r, 40, 3)
    streak = cv2.resize(cv2.resize(streak, (w // 6, h), interpolation=cv2.INTER_AREA), (w, h), interpolation=cv2.INTER_CUBIC)
    alb = np.array([44, 43, 48], np.float32)[None, None, :] * (0.70 + 0.60 * mottle)[..., None]
    alb *= (0.82 + 0.36 * patches)[..., None]
    alb *= (0.90 + 0.20 * streak)[..., None]
    alb *= (0.82 + 0.36 * ridged)[..., None]
    alb += (grain - 0.5)[..., None] * 30
    alb *= (1 - 0.22 * pits)[..., None]
    warm = smoothstep((patches - 0.62) / 0.3) * 0.6
    alb += warm[..., None] * np.array([18, 8, -6], np.float32)
    ao = 1 - 0.65 * blur(crack, 9) - 0.35 * blur(crack, 3) - 0.22 * blur(hair, 3)
    ao *= 0.62 + 0.38 * bevel
    shade = 0.26 + 0.84 * diff
    col = alb * shade[..., None] * ao[..., None] + spec[..., None] * np.array([190, 190, 205], np.float32)

    # fissure interiors: near black when idle
    core = smoothstep(crack / 0.55)
    col = col * (1 - 0.96 * core[..., None]) + np.array([6, 5, 8], np.float32) * (0.96 * core[..., None])
    col *= (1 - 0.55 * hair)[..., None]
    idle = col.copy()

    # hover: fissures glow deep amber, with glow spill and a faint warm rim
    hover = col.copy()
    t = np.clip(crack, 0, 1)
    edge_c = np.array([112, 46, 6], np.float32)
    mid_c = np.array([214, 116, 20], np.float32)
    core_c = np.array([255, 186, 82], np.float32)
    ramp = edge_c * (1 - t)[..., None] + mid_c * t[..., None]
    t2 = smoothstep((t - 0.66) / 0.34)
    ramp = ramp * (1 - t2)[..., None] + core_c * t2[..., None]
    emis = smoothstep(crack / 0.40)
    hover = hover * (1 - emis)[..., None] + ramp * emis[..., None]
    glow = blur(crack, 8) * 0.80 + blur(crack, 30) * 0.35
    hover += glow[..., None] * np.array([176, 88, 16], np.float32)
    hover = hover * (1 - hair * 0.8)[..., None] + np.array([232, 140, 44], np.float32) * (hair * 0.8)[..., None]
    hover += blur(hair, 2.5)[..., None] * np.array([110, 52, 10], np.float32) * 0.6
    rim = (1 - smoothstep(dist / 16.0)) * (mask > 0.5)
    hover += rim[..., None] * np.array([70, 30, 6], np.float32) * 0.18

    # label
    if BAKE_TEXT and label:
        T = text_mask(h, w, label)
        grain2 = fbm(h, w, r, 200, 2)
        ds = blur(shift(T, 3, 4), 3.0) * 0.85
        halo = blur(T, 10) * 0.55
        hl = np.clip(T - shift(T, 2, 2), 0, 1)
        sh = np.clip(T - shift(T, -2, -2), 0, 1)
        for img, fill, warmglow in ((idle, np.array([214, 209, 222], np.float32), 0.0),
                                    (hover, np.array([255, 241, 216], np.float32), 1.0)):
            img *= (1 - 0.85 * ds * (1 - T))[..., None]
            img *= (1 - 0.45 * halo * (1 - T))[..., None]
            tex = fill[None, None, :] * (0.86 + 0.28 * grain2)[..., None]
            img[:] = img * (1 - T)[..., None] + tex * T[..., None]
            img += (hl * 34)[..., None]
            img -= (sh * 58)[..., None]
            if warmglow:
                img += blur(T, 12)[..., None] * np.array([120, 62, 16], np.float32) * 0.45

    alpha = mask
    outs = {}
    for key, img in (("", idle), ("over", hover)):
        rgb = np.clip(img, 0, 255).astype(np.uint8)
        a = np.clip(alpha * 255, 0, 255).astype(np.uint8)
        rgba = np.dstack([rgb, a])
        im = Image.fromarray(rgba, "RGBA")
        p = OUT / f"{name}{key}.png"
        im.save(p, "PNG", optimize=True)
        (OUT / f"{name}{key}.png.mcmeta").write_text(json.dumps({"texture": {"blur": True, "clamp": True}}))
        outs[key] = im
    return outs


# ----------------------------------------------------------------- preview
def preview(results):
    bgp = LIVE / "resourcepacks" / "QuestForge.zip"
    with zipfile.ZipFile(bgp) as z:
        bg = Image.open(io.BytesIO(z.read("assets/custommenu/background.jpg"))).convert("RGBA")
    canvas = bg.resize((2560, 1369), Image.Resampling.LANCZOS)
    big_w, big_h, small_w = 896, 120, 444
    x0 = (2560 - big_w) // 2
    rows = [("single", 612), ("multiplayer", 733), ("mods", 855)]
    for i, (n, y) in enumerate(rows):
        key = "over" if n == "multiplayer" else ""
        im = results[n][key].resize((big_w, big_h), Image.Resampling.LANCZOS)
        canvas.alpha_composite(im, (x0, y))
    for n, x, key in (("options", 817, ""), ("quit", 1325, "over")):
        im = results[n][key].resize((small_w, big_h), Image.Resampling.LANCZOS)
        canvas.alpha_composite(im, (x, 1028))
    canvas.convert("RGB").save(OUT / "preview_menu.png", "PNG")
    canvas.crop((780, 580, 1780, 1180)).save(OUT / "preview_menu_crop.png", "PNG")


# ----------------------------------------------------------------- install
def replace_entries(path, mapping):
    tmp = path.with_suffix(path.suffix + ".tmpqf")
    with zipfile.ZipFile(path) as zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        done = set()
        for info in zin.infolist():
            if info.filename in mapping:
                zi = zipfile.ZipInfo(info.filename, date_time=info.date_time)
                zi.compress_type = zipfile.ZIP_DEFLATED
                zout.writestr(zi, mapping[info.filename]); done.add(info.filename)
            else:
                zout.writestr(info, zin.read(info.filename))
        for name, data in mapping.items():
            if name not in done:
                zi = zipfile.ZipInfo(name); zi.compress_type = zipfile.ZIP_DEFLATED
                zout.writestr(zi, data)
    os.replace(tmp, path)


def install():
    stamp = time.strftime("%Y%m%d-%H%M%S")
    bdir = W / f"backup-before-{stamp}"; bdir.mkdir()
    zp, jp = LIVE / "resourcepacks" / "QuestForge.zip", LIVE / "mods" / "CustomMenu.jar"
    for p in (zp, jp):
        shutil.copy2(p, bdir / p.name)
    mapping = {}
    for name, _, _, _ in BUTTONS:
        for key in ("", "over"):
            f = f"{name}{key}.png"
            mapping[f"assets/custommenu/{f}"] = (OUT / f).read_bytes()
            mapping[f"assets/custommenu/{f}.mcmeta"] = (OUT / f"{f}.mcmeta").read_bytes()
    for p in (zp, jp):
        replace_entries(p, mapping)
        with zipfile.ZipFile(p) as z:
            assert z.testzip() is None
            for name, _, size, _ in BUTTONS:
                im = Image.open(io.BytesIO(z.read(f"assets/custommenu/{name}.png")))
                assert im.size == size, (p, name, im.size)
        print("installed into", p, p.stat().st_size, "bytes")
    print("backup in", bdir)


def main():
    OUT.mkdir(exist_ok=True)
    results = {}
    for name, label, size, seed in BUTTONS:
        results[name] = render(name, label, size, seed)
        print("rendered", name, size)
    preview(results)
    print("preview", OUT / "preview_menu.png")
    if "--install" in sys.argv:
        install()


if __name__ == "__main__":
    main()
