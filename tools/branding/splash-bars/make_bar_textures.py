#!/usr/bin/env python3
"""Textures for the Quest Forge splash bars (drawn by qf.splash.QFBars inside the patched Forge jar).

Bar-local units: the Forge border box is 400x20 at the bar origin; the fill box is 398x18 at (1,1).
  trough.png  2300x150  covers x -30..430, y -5..25   (5 px per unit): tapered stone channel, dark interior
  rim.png     2300x200  same footprint, channel interior transparent with an inner-shadow lip
  magma.png   2048x144  horizontally tileable molten fill
  head.png    256x256   additive glow at the fill front
  plaque.png  920x120   soft dark backing behind title + bar (x -30..430, y -14..46)
Also writes an HD splash font (ascii.png, 1024x1024, Georgia Bold with baked outline + shadow).
"""
import sys
from pathlib import Path
import cv2, numpy as np
from PIL import Image, ImageDraw, ImageFont

W = Path(__file__).resolve().parent
OUT = W / "out"; OUT.mkdir(exist_ok=True)
FONT = "/System/Library/Fonts/Supplemental/Georgia Bold.ttf"
PX = 5  # texture px per bar unit


def value_noise(h, w, cx, cy, r, periodic_x=False):
    g = r.random((cy + 1, cx + 1)).astype(np.float32)
    if periodic_x:
        g[:, -1] = g[:, 0]
    return cv2.resize(g, (w, h), interpolation=cv2.INTER_CUBIC)


def fbm(h, w, r, base_cells=6, octaves=5, persistence=0.5, periodic_x=False):
    out = np.zeros((h, w), np.float32); amp, tot = 1.0, 0.0
    cx, cy = base_cells, max(1, int(round(base_cells * h / w)))
    for _ in range(octaves):
        out += amp * value_noise(h, w, cx, cy, r, periodic_x); tot += amp; amp *= persistence
        cx, cy = cx * 2, cy * 2
        if cx > w: break
    return out / tot


def blur(a, s): return cv2.GaussianBlur(a, (0, 0), s)
def sstep(x): x = np.clip(x, 0, 1); return x * x * (3 - 2 * x)


def save_rgba(rgb, alpha, path):
    rgba = np.dstack([np.clip(rgb, 0, 255).astype(np.uint8), np.clip(alpha * 255, 0, 255).astype(np.uint8)])
    Image.fromarray(rgba, "RGBA").save(path, "PNG", optimize=True)


# ----------------------------------------------------------------- trough + rim
def trough_and_rim():
    r = np.random.default_rng(7)
    w, h = 460 * PX, 30 * PX
    xs, ys = np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))
    cx = w / 2.0
    # outer silhouette: flat middle, tapering to chiselled points over the 30-unit caps at each end
    cap = 30 * PX
    dx = np.abs(xs - cx)
    half_len = w / 2.0
    into_cap = np.clip((dx - (half_len - cap)) / cap, 0, 1)          # 0 in the body, 1 at the tip
    env = 1 - into_cap ** 1.6                                          # concave taper -> spear-like point
    env = np.maximum(env, 0)
    half_h = (h / 2.0 - 4) * env
    edge_noise = (fbm(h, w, r, 60, 3) - 0.5) * 2 * 7 + (fbm(h, w, r, 240, 2) - 0.5) * 2 * 2.5
    body = (np.abs(ys - h / 2.0) < half_h + edge_noise)
    # chip the rim a little
    mask = body.astype(np.float32)
    for _ in range(26):
        px_, py_ = r.uniform(0, w), r.choice([r.uniform(0, 18), r.uniform(h - 18, h)])
        n = int(r.integers(3, 6)); ang = np.sort(r.uniform(0, 2 * np.pi, n)); rad = r.uniform(3, 9, n)
        pts = np.stack([px_ + np.cos(ang) * rad * 1.6, py_ + np.sin(ang) * rad], 1).astype(np.int32)
        cv2.fillPoly(mask, [pts], 0.0)
    mask = blur((mask > 0.5).astype(np.float32), 0.7)
    dist = cv2.distanceTransform((mask > 0.5).astype(np.uint8), cv2.DIST_L2, 5).astype(np.float32)

    # channel: rounded slot covering the 398x18 fill box plus 1 unit -> x 30..430 units, y 10..30 units
    ch_x0, ch_x1 = 30 * PX, 430 * PX
    ch_y0, ch_y1 = 5 * PX, 25 * PX
    rad_c = (ch_y1 - ch_y0) / 2.0
    ccx = np.clip(xs, ch_x0 + rad_c, ch_x1 - rad_c); ccy = (ch_y0 + ch_y1) / 2.0
    dch = np.hypot(xs - ccx, ys - ccy) - rad_c                          # signed distance to the channel edge
    channel = sstep(-dch / 1.5)                                          # 1 inside channel
    rim_only = mask * (1 - channel)

    # stone shading for the rim
    bevel = sstep(dist / 9.0)
    ridged = 1 - np.abs(2 * fbm(h, w, r, 14, 4) - 1)
    facets = np.abs(2 * fbm(h, w, r, 32, 3) - 1)
    grain = fbm(h, w, r, 300, 2)
    height = 0.55 + (fbm(h, w, r, 5, 3) - 0.5) * 0.4 + (ridged - 0.5) * 0.22 + (facets - 0.5) * 0.12 + (grain - 0.5) * 0.08
    # channel lip: the stone drops into the channel
    lip = sstep((dch) / 10.0)                                            # 0 at channel edge -> 1 further out
    height = height * bevel * (0.35 + 0.65 * lip)
    height = height.astype(np.float32)
    gx = cv2.Sobel(height, cv2.CV_32F, 1, 0, ksize=3) / 8; gy = cv2.Sobel(height, cv2.CV_32F, 0, 1, ksize=3) / 8
    S = 20; nx, ny = -gx * S, -gy * S; norm = np.sqrt(nx * nx + ny * ny + 1)
    L = np.array([-0.4, -0.65, 0.65]); L /= np.linalg.norm(L)
    diff = np.clip((nx * L[0] + ny * L[1] + L[2]) / norm, 0, 1)
    mottle = fbm(h, w, r, 24, 4); patches = fbm(h, w, r, 48, 3)
    alb = np.array([50, 48, 54], np.float32)[None, None, :] * (0.8 + 0.4 * mottle)[..., None]
    alb *= (0.88 + 0.24 * patches)[..., None] * (0.84 + 0.32 * ridged)[..., None]
    alb += (grain - 0.5)[..., None] * 28
    # faint fissures on the rim
    e = fbm(h, w, r, 40, 3); fiss = sstep((0.5 - np.abs(e - 0.5)) / 0.02) * sstep((fbm(h, w, r, 8, 3) - 0.5) / 0.1)
    ao = (1 - 0.5 * blur(fiss, 3)) * (0.6 + 0.4 * bevel)
    rim_rgb = alb * (0.28 + 0.82 * diff)[..., None] * ao[..., None]
    rim_rgb *= (1 - 0.7 * fiss)[..., None]

    # channel interior: near-black until magma fill is drawn on top (no baked orange)
    crust = fbm(h, w, r, 80, 4)
    inner_shadow = sstep((-dch) / (rad_c * 0.9))                        # 0 at edge -> 1 in the middle
    ch_rgb = np.array([6, 5, 5], np.float32)[None, None, :] * (0.55 + 0.55 * crust)[..., None]
    ch_rgb *= (0.45 + 0.55 * inner_shadow)[..., None]
    trough_rgb = rim_rgb * (1 - channel)[..., None] + ch_rgb * channel[..., None]
    save_rgba(trough_rgb, mask, OUT / "trough.png")

    # rim overlay: transparent channel, plus an inner shadow band just inside the channel edge
    inner_band = sstep((-dch) / 1.5) * (1 - sstep((-dch - 2) / (rad_c * 0.55)))   # 1 at edge fading inward
    rim_alpha = rim_only + channel * inner_band * 0.75
    rim_rgb2 = rim_rgb * (1 - channel)[..., None] + np.array([4, 3, 5], np.float32) * channel[..., None]
    save_rgba(rim_rgb2, rim_alpha * mask, OUT / "rim.png")
    print("trough/rim", (w, h))


# ----------------------------------------------------------------- magma
def magma():
    r = np.random.default_rng(3)
    w, h = 2048, 144
    heat = fbm(h, w, r, 12, 5, periodic_x=True)
    heat = (heat - heat.min()) / (heat.max() - heat.min())
    plates = fbm(h, w, r, 40, 3, periodic_x=True)
    seam = sstep((0.5 - np.abs(plates - 0.5)) / 0.035)                  # molten seams between crust plates
    pool = sstep((heat - 0.74) / 0.12)                                   # open molten pools
    molten = np.clip(seam * (0.55 + 0.45 * heat) + pool, 0, 1)
    glow = blur(molten, 6.0)
    # crust: dark reddish-black basalt, lit from the seams
    crust_tex = fbm(h, w, r, 160, 3, periodic_x=True)
    crust_rgb = np.array([26, 10, 7], np.float32)[None, None, :] * (0.5 + 0.9 * crust_tex)[..., None]
    crust_rgb += glow[..., None] * np.array([95, 30, 6], np.float32)
    # molten ramp: deep red -> orange -> pale yellow at the hottest cores
    c_red = np.array([170, 34, 6], np.float32); c_orange = np.array([245, 120, 18], np.float32); c_yellow = np.array([255, 215, 120], np.float32)
    t = np.clip(molten, 0, 1)
    hot = sstep((heat - 0.5) / 0.4) * t
    m_rgb = c_red * (1 - t)[..., None] + c_orange * t[..., None]
    m_rgb = m_rgb * (1 - hot)[..., None] + c_yellow * hot[..., None]
    rgb = crust_rgb * (1 - t)[..., None] + m_rgb * t[..., None]
    yy = np.abs(np.linspace(-1, 1, h))[:, None]
    rgb *= (1.0 - 0.30 * yy ** 2)[..., None]
    save_rgba(rgb, np.ones((h, w), np.float32), OUT / "magma.png")
    print("magma", (w, h))


# ----------------------------------------------------------------- head + plaque
def head():
    s = 256; y, x = np.mgrid[0:s, 0:s].astype(np.float32)
    d = np.hypot(x - s / 2, y - s / 2) / (s / 2)
    a = np.clip(1 - d, 0, 1) ** 2.2
    rgb = np.dstack([np.full((s, s), 255.0), 160 + 90 * a, 40 + 150 * a])
    save_rgba(rgb, a, OUT / "head.png")


def plaque():
    w, h = 920, 120
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    rx = np.clip(np.maximum(np.abs(x - w / 2) - (w / 2 - 110), 0), 0, None)
    ry = np.clip(np.maximum(np.abs(y - h / 2) - (h / 2 - 40), 0), 0, None)
    d = np.hypot(rx, ry)
    a = np.clip(1 - d / 90.0, 0, 1) ** 1.8 * 0.5
    save_rgba(np.zeros((h, w, 3), np.float32) + np.array([6, 4, 8]), a, OUT / "plaque.png")


# ----------------------------------------------------------------- HD font
ASCII_ORDER = ("ÀÁÂÈÊËÍÓÔÕÚßãõğİıŒœŞşŴŵžȇ\x00\x00\x00\x00\x00\x00\x00 !\"#$%&'()*+,-./0123456789:;<=>?@"
               "ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~\x00ÇüéâäàåçêëèïîìÄÅÉæÆôöòûùÿÖÜø£Ø×ƒáíóúñÑªº¿®¬½¼¡«»")


def font_png():
    cell = 64; size = cell * 16
    fnt = ImageFont.truetype(FONT, 48)
    glyphs = Image.new("L", (size, size), 0)
    for idx, ch in enumerate(ASCII_ORDER[:256]):
        if ch in (" ", "\x00"): continue
        cx, cy = (idx % 16) * cell, (idx // 16) * cell
        l, t, rgt, b = fnt.getbbox(ch, anchor="ls")          # left bearing may be negative (j, f, ...)
        tile = Image.new("L", (cell, cell), 0)
        # left-align ink at x=1 so FontRenderer's 8-unit quad + measured advance kerns tightly
        ImageDraw.Draw(tile).text((1 - l, 50), ch, font=fnt, fill=255, anchor="ls")
        glyphs.paste(tile, (cx, cy))                           # clipped to its own cell: no bleed into neighbours
    g = np.asarray(glyphs).astype(np.float32) / 255.0
    # 1px outline only — a baked shadow was counted as width and looked like mid-word gaps
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    outline = cv2.dilate(g, k)
    alpha = np.clip(g + outline * 0.90, 0, 1)
    alpha = np.where(alpha < 0.08, 0.0, alpha)
    # white glyph, near-black outline; splash.properties font= multiplies at draw time
    rgb = np.dstack([g, g, g]) * 255
    rgb = rgb + (1 - g)[..., None] * np.array([8, 6, 4])
    save_rgba(rgb, alpha, OUT / "ascii.png")
    print("font", (size, size))


if __name__ == "__main__":
    trough_and_rim(); magma(); head(); plaque(); font_png()
    print("done")
