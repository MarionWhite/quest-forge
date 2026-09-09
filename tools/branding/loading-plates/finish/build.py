#!/usr/bin/env python3
"""Finish pass for the 27 loading plates.

Does not touch selected/ or work/. Writes only under finish/.

1. Crop true letterbox bars (top AND bottom), then restore 16:9.
2. One cohesion curve: near-blacks toward #07060B, ember ramp lifted.
   End, Chaos, and Compact Machines skip the extra crush.
3. Darken the UI safe zones (top eighth, bottom quarter).
4. Export 1280 masters and 3840x2160 LANCZOS 4K.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
SEL = ROOT / "selected"
OUT = ROOT / "finish"
OUT_1280 = OUT / "1280"
OUT_4K = OUT / "4k"
VOID = np.array([7.0, 6.0, 11.0], dtype=np.float32)  # #07060B

# Symmetric black bars only. End's void is top-only and must not be cropped.
LETTERBOX = {
    "07-lost-world.png",
    "11-ilum.png",
    "14-korriban.png",
    "20-imortus.png",
}

# Opened on purpose for dim screens, or a bright-interior override.
NO_CRUSH = {
    "02-end.png",
    "08-compact-machines.png",
    "27-chaos.png",
}

W, H = 1280, 720
W4K, H4K = 3840, 2160


def load_rgb(path: Path) -> np.ndarray:
    return np.array(Image.open(path).convert("RGB"), dtype=np.float32)


def crop_letterbox(a: np.ndarray) -> np.ndarray:
    row = a.mean(axis=(1, 2))
    h = a.shape[0]
    top = 0
    while top < h and row[top] < 1.5:
        top += 1
    bot = 0
    while bot < h and row[h - 1 - bot] < 1.5:
        bot += 1
    if top < 8 or bot < 8:
        return a
    cropped = a[top : h - bot]
    im = Image.fromarray(np.clip(cropped, 0, 255).astype(np.uint8))
    return np.array(im.resize((W, H), Image.Resampling.LANCZOS), dtype=np.float32)


def cohesion(a: np.ndarray, name: str) -> np.ndarray:
    r, g, b = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    luma = 0.2126 * r + 0.7152 * g + 0.0722 * b
    chroma = np.maximum(np.maximum(r, g), b) - np.minimum(np.minimum(r, g), b)
    out = a.copy()

    if name not in NO_CRUSH:
        t = np.clip(1.0 - luma / 14.0, 0, 1) * 0.50
        out = out * (1.0 - t[..., None]) + VOID * t[..., None]

    warm = (r > g + 8) & (r > b + 15) & (chroma > 18) & (luma > 22)
    out[:, :, 0] = np.where(warm, np.clip(out[:, :, 0] * 1.055 + 3.0, 0, 255), out[:, :, 0])
    out[:, :, 1] = np.where(warm, np.clip(out[:, :, 1] * 1.025 + 1.0, 0, 255), out[:, :, 1])
    return out


def safe_zones(a: np.ndarray, name: str) -> np.ndarray:
    h, w, _ = a.shape
    y = np.arange(h, dtype=np.float32)[:, None]
    top = np.clip((h / 8.0 - y) / (h / 8.0), 0, 1)
    bot = np.clip((y - 3.0 * h / 4.0) / (h / 4.0), 0, 1)
    top = top * top * (3.0 - 2.0 * top)
    bot = bot * bot * (3.0 - 2.0 * bot)
    band = np.maximum(top, bot)

    luma = (0.2126 * a[:, :, 0] + 0.7152 * a[:, :, 1] + 0.0722 * a[:, :, 2]).mean()
    if name == "08-compact-machines.png":
        strength = 0.42
    elif luma < 22:
        strength = 0.22
    elif name in NO_CRUSH:
        strength = 0.28
    else:
        strength = 0.38

    mix = (band * strength)[..., None]
    return a * (1.0 - mix) + VOID * mix


def process(path: Path) -> np.ndarray:
    a = load_rgb(path)
    if a.shape[1] != W or a.shape[0] != H:
        a = np.array(
            Image.fromarray(a.astype(np.uint8)).resize((W, H), Image.Resampling.LANCZOS),
            dtype=np.float32,
        )
    if path.name in LETTERBOX:
        a = crop_letterbox(a)
    a = cohesion(a, path.name)
    a = safe_zones(a, path.name)
    return np.clip(a, 0, 255)


def contact_sheet(paths: list[Path], dest: Path) -> None:
    thumb_w, thumb_h = 320, 180
    cols, rows = 9, 3
    sheet = Image.new("RGB", (cols * thumb_w, rows * thumb_h), (7, 6, 11))
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 14)
    except OSError:
        font = ImageFont.load_default()
    for i, p in enumerate(paths):
        im = Image.open(p).convert("RGB").resize((thumb_w, thumb_h), Image.Resampling.LANCZOS)
        draw = ImageDraw.Draw(im)
        label = p.stem
        draw.rectangle((0, thumb_h - 22, thumb_w, thumb_h), fill=(7, 6, 11))
        draw.text((6, thumb_h - 18), label, fill=(232, 228, 240), font=font)
        x = (i % cols) * thumb_w
        y = (i // cols) * thumb_h
        sheet.paste(im, (x, y))
    sheet.save(dest)


def main() -> None:
    srcs = sorted(SEL.glob("*.png"))
    if len(srcs) != 27:
        raise SystemExit(f"expected 27 selected plates, found {len(srcs)}")

    OUT_1280.mkdir(parents=True, exist_ok=True)
    OUT_4K.mkdir(parents=True, exist_ok=True)

    hashes = []
    for src in srcs:
        arr = process(src)
        im = Image.fromarray(arr.astype(np.uint8))
        p1280 = OUT_1280 / src.name
        im.save(p1280)
        im4 = im.resize((W4K, H4K), Image.Resampling.LANCZOS)
        p4k = OUT_4K / src.name
        im4.save(p4k, optimize=True)
        digest = hashlib.sha256(p4k.read_bytes()).hexdigest()
        hashes.append(f"{digest}  {src.name}  {p4k.stat().st_size}")
        print(f"ok {src.name}")

    (OUT / "4K-SHA256.txt").write_text("\n".join(hashes) + "\n")
    contact_sheet([OUT_1280 / p.name for p in srcs], OUT / "contact-sheet-1280.png")
    print(f"wrote {len(srcs)} plates to {OUT}")


if __name__ == "__main__":
    main()
