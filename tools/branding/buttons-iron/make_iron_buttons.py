#!/usr/bin/env python3
"""Forged-iron main-menu buttons (concept A) as runtime assets for qf.menu.QFButtons.

Per button (1800x240 big / 900x240 small):
  out/<name>.png        idle: chamfered blackened-iron letters, lavender top rim, ember under-light
  out/<name>over.png    identical to idle (the animated hover is drawn by QFButtons, not by a texture swap)
  out/qf/<name>_heat.png  emissive amber letters, alpha = letter mask (drawn additively, rising with hover)
  out/qf/<name>_glow.png  soft amber bloom around the letters (additive)
  out/qf/<name>_mask.png  letter mask used to spawn ember particles
"""
import io, os, zipfile
from pathlib import Path
import cv2, numpy as np
from PIL import Image, ImageDraw, ImageFont

W = Path(__file__).resolve().parent
OUT = W / "out"; (OUT / "qf").mkdir(parents=True, exist_ok=True)
FONT = "/System/Library/Fonts/Supplemental/Georgia Bold.ttf"
BIG, SMALL = (1800, 240), (900, 240)
BUTTONS = [("single", "Singleplayer", BIG, 11), ("multiplayer", "Multiplayer", BIG, 23), ("mods", "Mods", BIG, 37),
           ("publicserver", "Official Public Server", BIG, 41), ("options", "Options", SMALL, 53), ("quit", "Quit", SMALL, 67)]
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


def text_mask(h, w, label, size_frac=0.62, max_w=0.86):
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


def render(name, label, size, seed):
    w, h = size; r = np.random.default_rng(seed)
    T = text_mask(h, w, label)
    Tb = (T > 0.5).astype(np.uint8)
    dist_in = cv2.distanceTransform(Tb, cv2.DIST_L2, 5).astype(np.float32)
    bev = 9.0
    height = sstep(dist_in / bev) * 0.9 + 0.1
    surf = (fbm(h, w, r, 40, 3) - 0.5) * 0.06 + (fbm(h, w, r, 200, 2) - 0.5) * 0.03
    height = (height + surf) * T
    diff, spec, nx, ny = shade(height, S=26.0, L=(-0.35, -0.7, 0.6))
    mottle = fbm(h, w, r, 30, 4); hammer = np.abs(2 * fbm(h, w, r, 70, 3) - 1)
    alb = np.array([40, 38, 42], np.float32)[None, None, :] * (0.7 + 0.6 * mottle)[..., None] * (0.85 + 0.3 * hammer)[..., None]
    col = alb * (0.38 + 0.9 * diff)[..., None] + (spec ** 30 * 95)[..., None] * np.array([1.0, 0.98, 1.05])
    up = np.clip(-ny, 0, 1) * (1 - sstep((dist_in - bev) / 2))
    down = np.clip(ny, 0, 1) * (1 - sstep((dist_in - bev) / 2))
    col += up[..., None] * np.array([120, 104, 150], np.float32) * 0.9
    col += down[..., None] * np.array([190, 92, 20], np.float32) * 0.75
    # ground shadow so the letters separate from the scene; it is part of the idle texture
    sh = blur(T, 9) * 0.85 + blur(T, 30) * 0.5
    a_idle = np.clip(T + sh * (1 - T), 0, 1)
    idle_rgb = np.where(T[..., None] > 0.02, col, np.array([3, 2, 5], np.float32))
    save(idle_rgb, a_idle, OUT / f"{name}.png")
    save(idle_rgb, a_idle, OUT / f"{name}over.png")
    # heat: emissive amber letters, brighter on the flat tops, deep amber on bevels
    hot_core = sstep((dist_in - bev) / 3)
    heat_rgb = np.array([200, 84, 14], np.float32)[None, None, :] * (1 - hot_core)[..., None] + np.array([255, 168, 62], np.float32) * hot_core[..., None]
    heat_rgb *= (0.85 + 0.15 * fbm(h, w, r, 60, 3))[..., None]
    save(heat_rgb, T, OUT / "qf" / f"{name}_heat.png")
    # glow: bloom outside the letters (additive)
    bloom = blur(T, 14) * 0.9 + blur(T, 40) * 0.55
    save(np.zeros((h, w, 3), np.float32) + np.array([235, 118, 26]), np.clip(bloom, 0, 1), OUT / "qf" / f"{name}_glow.png")
    # mask for particle spawning
    Image.fromarray((T * 255).astype(np.uint8), "L").save(OUT / "qf" / f"{name}_mask.png", optimize=True)
    return Image.open(OUT / f"{name}.png")


def preview(results):
    with zipfile.ZipFile(LIVE / "resourcepacks" / "QuestForge.zip") as z:
        bg = Image.open(io.BytesIO(z.read("assets/custommenu/background.jpg"))).convert("RGBA")
    canvas = bg.resize((2560, 1369), Image.Resampling.LANCZOS)
    big_w, big_h, small_w = 896, 120, 444
    x0 = (2560 - big_w) // 2
    for n, y in (("single", 612), ("multiplayer", 733), ("mods", 855)):
        canvas.alpha_composite(results[n].resize((big_w, big_h), Image.Resampling.LANCZOS), (x0, y))
    for n, x in (("options", 817), ("quit", 1325)):
        canvas.alpha_composite(results[n].resize((small_w, big_h), Image.Resampling.LANCZOS), (x, 1028))
    canvas.crop((760, 560, 1800, 1180)).convert("RGB").save(OUT / "preview_idle.png")


if __name__ == "__main__":
    res = {}
    for name, label, size, seed in BUTTONS:
        res[name] = render(name, label, size, seed); print("rendered", name)
    preview(res); print("done")
