#!/usr/bin/env python3
"""Two new main-menu button concepts for Quest Forge, rendered as idle + hover plates (1800x240 / 900x240)
and composed over the live menu background for review.

Concept A  "Forged Iron"   - no plate at all: the label itself is the button, cast in chamfered blackened iron
                              like the title wordmark, with a lavender rim-light on top and an ember under-light.
                              Hover: the iron heats from the bottom up, glowing deep amber with a soft bloom.
Concept B  "Obsidian Shard" - an angular volcanic-glass shard with sharp facets and a violet sheen; the label
                              is cut into the glass. Hover: molten amber bleeds through the facet seams and the
                              engraving fills with light.
"""
import io, os, sys, zipfile
from pathlib import Path
import cv2, numpy as np
from PIL import Image, ImageDraw, ImageFont

W = Path(__file__).resolve().parent
OUT = W / "out"; OUT.mkdir(exist_ok=True)
FONT = "/System/Library/Fonts/Supplemental/Georgia Bold.ttf"
BIG, SMALL = (1800, 240), (900, 240)
BUTTONS = [("single", "Singleplayer", BIG, 11), ("multiplayer", "Multiplayer", BIG, 23), ("mods", "Mods", BIG, 37),
           ("options", "Options", SMALL, 53), ("quit", "Quit", SMALL, 67)]
LIVE = Path(os.path.expanduser("~/Library/Application Support/PrismLauncher/instances/Quest Forge/minecraft"))


def value_noise(h, w, cx, cy, r):
    g = r.random((cy + 1, cx + 1)).astype(np.float32)
    return cv2.resize(g, (w, h), interpolation=cv2.INTER_CUBIC)


def fbm(h, w, r, base=6, octaves=5, persistence=0.5):
    out = np.zeros((h, w), np.float32); amp, tot = 1.0, 0.0
    cx, cy = base, max(1, int(round(base * h / w)))
    for _ in range(octaves):
        out += amp * value_noise(h, w, cx, cy, r); tot += amp; amp *= persistence; cx, cy = cx * 2, cy * 2
        if cx > w: break
    return out / tot


def blur(a, s): return cv2.GaussianBlur(a, (0, 0), s)
def sstep(x): x = np.clip(x, 0, 1); return x * x * (3 - 2 * x)


def text_mask(h, w, label, size_frac=0.56, max_w=0.80, spacing=0):
    size = int(h * size_frac)
    while True:
        font = ImageFont.truetype(FONT, size)
        l, t, rgt, b = font.getbbox(label)
        if rgt - l <= max_w * w or size < 20: break
        size -= 3
    im = Image.new("L", (w, h), 0)
    ImageDraw.Draw(im).text((w / 2, h / 2), label, fill=255, font=font, anchor="mm")
    return np.asarray(im).astype(np.float32) / 255.0


def shade(height, S=18.0, L=(-0.45, -0.6, 0.66)):
    gx = cv2.Sobel(height.astype(np.float32), cv2.CV_32F, 1, 0, ksize=3) / 8
    gy = cv2.Sobel(height.astype(np.float32), cv2.CV_32F, 0, 1, ksize=3) / 8
    nx, ny = -gx * S, -gy * S; norm = np.sqrt(nx * nx + ny * ny + 1)
    L = np.array(L); L = L / np.linalg.norm(L)
    diff = np.clip((nx * L[0] + ny * L[1] + L[2]) / norm, 0, 1)
    H = L + np.array([0, 0, 1.0]); H /= np.linalg.norm(H)
    spec = np.clip((nx * H[0] + ny * H[1] + H[2]) / norm, 0, 1)
    return diff, spec, nx / norm, ny / norm


def save(rgb, alpha, path):
    Image.fromarray(np.dstack([np.clip(rgb, 0, 255).astype(np.uint8), np.clip(alpha * 255, 0, 255).astype(np.uint8)]), "RGBA").save(path, "PNG", optimize=True)


# ================================================================== Concept A: forged iron letters
def concept_iron(name, label, size, seed):
    w, h = size; r = np.random.default_rng(seed)
    T = text_mask(h, w, label, size_frac=0.62, max_w=0.86)
    Tb = (T > 0.5).astype(np.uint8)
    dist_in = cv2.distanceTransform(Tb, cv2.DIST_L2, 5).astype(np.float32)
    # chamfered letter: flat top with a bevel ~9px wide, plus forged surface noise
    bev = 9.0
    height = sstep(dist_in / bev) * 0.9 + 0.1
    surf = (fbm(h, w, r, 40, 3) - 0.5) * 0.06 + (fbm(h, w, r, 200, 2) - 0.5) * 0.03
    height = (height + surf) * T
    diff, spec, nx, ny = shade(height, S=26.0, L=(-0.35, -0.7, 0.6))
    # iron albedo: near-black with steel-grey mottling, hammer marks
    mottle = fbm(h, w, r, 30, 4); hammer = np.abs(2 * fbm(h, w, r, 70, 3) - 1)
    alb = np.array([38, 36, 40], np.float32)[None, None, :] * (0.7 + 0.6 * mottle)[..., None] * (0.85 + 0.3 * hammer)[..., None]
    col = alb * (0.35 + 0.9 * diff)[..., None] + (spec ** 30 * 90)[..., None] * np.array([1.0, 0.98, 1.05])
    # rim lights: lavender on the upward-facing bevels, ember on the downward-facing bevels (like the wordmark)
    up = np.clip(-ny, 0, 1) * (1 - sstep((dist_in - bev) / 2))
    down = np.clip(ny, 0, 1) * (1 - sstep((dist_in - bev) / 2))
    col += up[..., None] * np.array([120, 104, 150], np.float32) * 0.9
    col += down[..., None] * np.array([190, 92, 20], np.float32) * 0.75
    alpha = T.copy()
    # soft ground shadow so the letters sit on the dark scene
    sh = blur(T, 9) * 0.85
    rgb_idle = col.copy(); a_idle = np.clip(alpha + sh * (1 - alpha), 0, 1)
    idle_rgb = (col * alpha[..., None] + np.array([4, 2, 6], np.float32) * (1 - alpha)[..., None] * 1.0)
    idle_rgb = np.where(alpha[..., None] > 0.02, col, np.array([4, 2, 6], np.float32))
    # hover: heat rises from the bottom of each letter, amber inner glow, bloom outside
    ys = np.linspace(0, 1, h)[:, None]
    ytop, ybot = h * 0.28, h * 0.72
    heat = sstep((ys * h - ytop) / (ybot - ytop)) * 0.85 + 0.15
    heat = heat * (0.85 + 0.15 * fbm(h, w, r, 60, 3))
    emis_rgb = np.array([255, 150, 40], np.float32)[None, None, :] * heat[..., None]
    hot_core = sstep((dist_in - bev) / 3)                                  # the flat top of the letter glows hardest
    hover = col * (1 - 0.55 * heat * T)[..., None] + emis_rgb * (T * (0.35 + 0.65 * hot_core) * heat)[..., None]
    hover += (down[..., None] * np.array([255, 160, 60], np.float32) * 0.6)
    bloom = blur(T * heat, 14) * 0.9 + blur(T * heat, 40) * 0.5
    hover_rgb = np.where(alpha[..., None] > 0.02, hover, np.array([4, 2, 6], np.float32)) + bloom[..., None] * np.array([230, 110, 24], np.float32) * 0.9
    a_hover = np.clip(alpha + bloom * 0.9 + sh * 0.4 * (1 - alpha), 0, 1)
    # embers: a few bright specks drifting above the letters
    for _ in range(int(w / 45)):
        x = r.uniform(0.12 * w, 0.88 * w); y = r.uniform(h * 0.05, h * 0.55); rad = r.uniform(1.2, 3.2)
        cv2.circle(hover_rgb, (int(x), int(y)), int(rad), (255, 200, 110), -1, lineType=cv2.LINE_AA)
        cv2.circle(a_hover, (int(x), int(y)), int(rad) + 1, 1.0, -1, lineType=cv2.LINE_AA)
    save(idle_rgb, a_idle, OUT / f"iron_{name}.png"); save(hover_rgb, a_hover, OUT / f"iron_{name}over.png")
    return Image.open(OUT / f"iron_{name}.png"), Image.open(OUT / f"iron_{name}over.png")


# ================================================================== Concept B: obsidian shard
def concept_obsidian(name, label, size, seed):
    w, h = size; r = np.random.default_rng(seed)
    # shard silhouette: an elongated irregular polygon with sharp facets
    m = 14
    pts = []
    n_top, n_bot = int(r.integers(4, 7)), int(r.integers(4, 7))
    xs_top = np.sort(r.uniform(m, w - m, n_top)); xs_bot = np.sort(r.uniform(m, w - m, n_bot))
    pts.append((m + r.uniform(0, 40), h / 2 + r.uniform(-25, 25)))
    for x in xs_top: pts.append((x, m + r.uniform(0, 22)))
    pts.append((w - m - r.uniform(0, 40), h / 2 + r.uniform(-25, 25)))
    for x in xs_bot[::-1]: pts.append((x, h - m - r.uniform(0, 22)))
    poly = np.array(pts, np.int32)
    mask = np.zeros((h, w), np.float32); cv2.fillPoly(mask, [poly], 1.0)
    mask_b = (mask > 0.5).astype(np.uint8)
    dist = cv2.distanceTransform(mask_b, cv2.DIST_L2, 5).astype(np.float32)
    # facets: voronoi cells, each with its own tilt
    n = int(w / 110)
    sx, sy = r.uniform(0, w, n), r.uniform(0, h, n)
    xs, ys = np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))
    d = np.stack([np.hypot(xs - a, ys - b) for a, b in zip(sx, sy)], 0)
    cell = d.argmin(0); dd = np.sort(d, 0); seam = np.clip(1 - (dd[1] - dd[0]) / 2.2, 0, 1)
    tilt_x, tilt_y = r.uniform(-1, 1, n), r.uniform(-1, 1, n)
    height = 0.6 * sstep(dist / 26) + 0.12 * (tilt_x[cell] * (xs - w / 2) / w + tilt_y[cell] * (ys - h / 2) / h) * 4
    height += (fbm(h, w, r, 25, 3) - 0.5) * 0.05
    height = (height * mask).astype(np.float32)
    diff, spec, nx, ny = shade(height, S=14.0, L=(-0.4, -0.6, 0.68))
    # glassy black with violet sheen and sharp specular streaks
    base = np.array([12, 9, 16], np.float32)
    sheen = np.clip(spec, 0, 1) ** 6
    streak = sstep((fbm(h, w, r, 6, 2) - 0.55) / 0.2) * np.clip(spec, 0, 1) ** 2
    col = base[None, None, :] * (0.6 + 0.8 * diff)[..., None]
    col += sheen[..., None] * np.array([150, 110, 210], np.float32) * 0.12
    col += streak[..., None] * np.array([200, 170, 255], np.float32) * 0.10
    col += (spec ** 80)[..., None] * np.array([230, 220, 255], np.float32) * 0.5
    col *= (1 - 0.6 * seam * mask)[..., None]
    # engraved label: dark inset with a bright lower-left lip
    T = text_mask(h, w, label, size_frac=0.5, max_w=0.7)
    Tb = (T > 0.5).astype(np.uint8); tin = cv2.distanceTransform(Tb, cv2.DIST_L2, 5).astype(np.float32)
    eng_h = -sstep(tin / 4) * 0.5
    ediff, espec, enx, eny = shade(eng_h.astype(np.float32), S=22.0, L=(-0.4, -0.6, 0.68))
    lip = np.clip(-eny, 0, 1) * T; floor = sstep((tin - 4) / 2)
    col_e = col * (1 - 0.65 * T)[..., None] + (lip * 160)[..., None] * np.array([1.0, 0.95, 1.1])
    col_e += (floor * T)[..., None] * np.array([150, 140, 165], np.float32) * 0.8
    idle = col_e
    # hover: molten amber leaks through the seams and floods the engraving
    seam_glow = blur(seam * mask, 3) + blur(seam * mask, 12) * 0.6
    hover = col_e + seam_glow[..., None] * np.array([235, 120, 20], np.float32) * 0.9
    eng_glow = blur(T, 2) * 1.0 + blur(T, 14) * 0.6
    hover = hover * (1 - 0.6 * T)[..., None] + (T * floor)[..., None] * np.array([255, 178, 70], np.float32)
    hover += eng_glow[..., None] * np.array([230, 110, 26], np.float32) * 0.6
    edge = (1 - sstep(dist / 6)) * mask
    hover += edge[..., None] * np.array([200, 90, 20], np.float32) * 0.5
    a_idle = mask; a_hover = np.clip(mask + blur(mask, 12) * 0.35, 0, 1)
    save(idle, a_idle, OUT / f"obs_{name}.png"); save(hover, a_hover, OUT / f"obs_{name}over.png")
    return Image.open(OUT / f"obs_{name}.png"), Image.open(OUT / f"obs_{name}over.png")


# ================================================================== preview
def preview(results, tag):
    with zipfile.ZipFile(LIVE / "resourcepacks" / "QuestForge.zip") as z:
        bg = Image.open(io.BytesIO(z.read("assets/custommenu/background.jpg"))).convert("RGBA")
    canvas = bg.resize((2560, 1369), Image.Resampling.LANCZOS)
    big_w, big_h, small_w = 896, 120, 444
    x0 = (2560 - big_w) // 2
    for n, y in (("single", 612), ("multiplayer", 733), ("mods", 855)):
        im = results[n][1 if n == "multiplayer" else 0].resize((big_w, big_h), Image.Resampling.LANCZOS)
        canvas.alpha_composite(im, (x0, y))
    for n, x, k in (("options", 817, 0), ("quit", 1325, 1)):
        canvas.alpha_composite(results[n][k].resize((small_w, big_h), Image.Resampling.LANCZOS), (x, 1028))
    canvas.crop((760, 560, 1800, 1180)).convert("RGB").save(OUT / f"preview_{tag}.png")


if __name__ == "__main__":
    ra, rb = {}, {}
    for name, label, size, seed in BUTTONS:
        ra[name] = concept_iron(name, label, size, seed)
        rb[name] = concept_obsidian(name, label, size, seed)
        print("rendered", name)
    preview(ra, "A_forged_iron"); preview(rb, "B_obsidian")
    print("previews in", OUT)
