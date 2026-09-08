# -*- coding: utf-8 -*-
"""Composite a distant knight onto the approved hall; restore emblem gem glow."""
from __future__ import print_function

import shutil
import struct
import time
import zlib
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

INST = Path(r"C:\Users\a2dsu\AppData\Roaming\.crazycraft4")
TITLE = INST / "resources" / "assets" / "minecraft" / "textures" / "gui" / "title"
WORK = Path(r"C:\Users\a2dsu\OneDrive\Desktop\QuestForge-Work\_splash-knight-glow")
MURAL_LIVE = TITLE / "loading_mural.png"
EMBLEM_LIVE = TITLE / "emblem_corner.png"
KNIGHT_SRC = Path(
    r"C:\Users\a2dsu\.cursor\projects\c-Users-a2dsu-OneDrive-Desktop-New-folder\assets\knight_silhouette_front.png"
)
GLOW_SRC = INST / "_backup-splash-20260904-051600" / "emblem_corner.png"
CLEAN_MURAL = INST / "_backup-knight-glow-20260904-163442" / "loading_mural.png"


def write_rgb_png(path, im):
    im = im.convert("RGB")
    w, h = im.size
    raw = im.tobytes()
    stride = w * 3
    rows = [b"\x00" + raw[y * stride : (y + 1) * stride] for y in range(h)]
    compressed = zlib.compress(b"".join(rows), 6)

    def chunk(tag, data):
        crc = zlib.crc32(tag + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)

    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", compressed) + chunk(b"IEND", b"")
    )


def png_ihdr(path):
    data = path.read_bytes()
    i = 8
    chunks = []
    while i + 8 <= len(data):
        ln = struct.unpack(">I", data[i : i + 4])[0]
        tag = data[i + 4 : i + 8]
        payload = data[i + 8 : i + 8 + ln]
        chunks.append(tag.decode("ascii"))
        if tag == b"IHDR":
            w, h, bit, ctype, comp, filt, inter = struct.unpack(">IIBBBBB", payload)
            print("IHDR", path.name, w, h, "bit", bit, "color", ctype)
        i += 12 + ln
        if tag == b"IEND":
            break
    print("chunks", chunks)
    return chunks


def is_chroma(r, g, b, seed):
    """Hot-pink / magenta studio backdrop (gen tool is not pure #FF00FF)."""
    sr, sg, sb = seed
    if abs(r - sr) <= 42 and abs(g - sg) <= 28 and abs(b - sb) <= 42:
        return True
    # saturated pink-magenta: high R, low G, mid-high B
    if r >= 190 and g <= 55 and b >= 110 and r > g + 120:
        return True
    if r >= 220 and g <= 80 and b >= 90 and r + b > 2 * g + 160:
        return True
    return False


def key_magenta(im):
    im = im.convert("RGBA")
    w, h = im.size
    px = im.load()
    seed = px[2, 2][:3]
    visited = bytearray(w * h)
    stack = []
    for x in range(w):
        stack.append((x, 0))
        stack.append((x, h - 1))
    for y in range(h):
        stack.append((0, y))
        stack.append((w - 1, y))

    while stack:
        x, y = stack.pop()
        if x < 0 or y < 0 or x >= w or y >= h:
            continue
        i = y * w + x
        if visited[i]:
            continue
        visited[i] = 1
        r, g, b, a = px[x, y]
        if not is_chroma(r, g, b, seed):
            continue
        px[x, y] = (255, 255, 255, 0)
        stack.extend(((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)))

    # leftover pink fringe
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a == 0:
                continue
            if is_chroma(r, g, b, seed):
                px[x, y] = (255, 255, 255, 0)
    return im


def alpha_bbox(im, thresh=10):
    a = im.split()[-1].point(lambda v: 255 if v > thresh else 0)
    return a.getbbox() or (0, 0, im.size[0], im.size[1])


def tint_silhouette(im, rgb=(14, 7, 18)):
    im = im.convert("RGBA")
    w, h = im.size
    out = Image.new("RGBA", (w, h), (255, 255, 255, 0))
    sp = im.load()
    op = out.load()
    tr, tg, tb = rgb
    for y in range(h):
        for x in range(w):
            r, g, b, a = sp[x, y]
            if a <= 2:
                continue
            # keep smoke softer than the body
            lum = (r + g + b) / 3.0
            body = 1.0 - min(1.0, lum / 40.0)
            aa = int(a * (0.55 + 0.45 * body))
            op[x, y] = (tr, tg, tb, max(0, min(255, aa)))
    return out


def composite_knight(mural):
    src = key_magenta(Image.open(KNIGHT_SRC))
    bb = alpha_bbox(src, 12)
    src = src.crop(bb)
    # Distant figure: ~7.5% of frame height, readable sword + smoke.
    target_h = 138
    scale = target_h / float(src.size[1])
    tw = max(8, int(src.size[0] * scale))
    th = target_h
    src = src.resize((tw, th), Image.Resampling.LANCZOS)
    src = tint_silhouette(src)
    src = src.filter(ImageFilter.GaussianBlur(0.55))
    # Stand on the far floor in the purple fog, slightly right of dead center.
    feet_x = 1968
    feet_y = 1272
    x = feet_x - tw // 2
    y = feet_y - th + 8
    print("knight overlay", tw, th, "paste", x, y, "src", KNIGHT_SRC.name)
    mural = mural.convert("RGBA")
    mural.alpha_composite(src, (x, y))
    # preview crop
    crop = mural.crop((feet_x - 220, feet_y - 200, feet_x + 220, feet_y + 40)).convert("RGB")
    crop.save(WORK / "knight_region_preview.png", "PNG")
    return mural.convert("RGB"), (tw, th, x, y)


def white_under_alpha(im):
    im = im.convert("RGBA")
    w, h = im.size
    px = im.load()
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a == 0:
                px[x, y] = (255, 255, 255, 0)
    return im


def restore_emblem():
    src = Image.open(GLOW_SRC).convert("RGBA")
    print("glow source", GLOW_SRC, src.size, "orange-ish restore from 051600 backup")
    src = white_under_alpha(src)
    half = src.resize((512, 512), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (1024, 1024), (255, 255, 255, 0))
    canvas.paste(half, (512, 512), half)

    # Extra forehead bloom so the gem still reads at half on-screen size.
    cx, cy = 764, 694
    bloom = Image.new("RGBA", (1024, 1024), (0, 0, 0, 0))
    d = ImageDraw.Draw(bloom)
    d.ellipse((cx - 28, cy - 28, cx + 28, cy + 28), fill=(255, 72, 18, 90))
    d.ellipse((cx - 14, cy - 14, cx + 14, cy + 14), fill=(255, 140, 40, 160))
    d.ellipse((cx - 6, cy - 6, cx + 6, cy + 6), fill=(255, 220, 120, 230))
    bloom = bloom.filter(ImageFilter.GaussianBlur(7))
    # Screen-ish: add bloom only where we want light, keep existing stone.
    canvas = Image.alpha_composite(canvas, bloom)
    canvas = white_under_alpha(canvas)
    return canvas


def count_orange(im):
    px = im.convert("RGBA").load()
    w, h = im.size
    n = 0
    bright = (0, 0, 0, 0)
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a > 80 and r > 160 and g > 40 and r > g + 20:
                n += 1
                if r + g > bright[0] + bright[1]:
                    bright = (r, g, b, a)
    return n, bright


def main():
    WORK.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    backup = INST / ("_backup-knight-glow-%s" % stamp)
    backup.mkdir(parents=True, exist_ok=True)
    shutil.copy2(MURAL_LIVE, backup / "loading_mural.png")
    shutil.copy2(EMBLEM_LIVE, backup / "emblem_corner.png")
    print("backup", backup)

    mural = Image.open(CLEAN_MURAL).convert("RGB")
    if mural.size != (3840, 2160):
        raise SystemExit("refusing to alter unexpected mural size %s" % (mural.size,))
    print("mural in", mural.size, "pixels", mural.size[0] * mural.size[1])

    out_mural, knight_info = composite_knight(mural)
    write_rgb_png(WORK / "loading_mural.png", out_mural)
    shutil.copy2(WORK / "loading_mural.png", MURAL_LIVE)
    chunks = png_ihdr(MURAL_LIVE)
    if chunks != ["IHDR", "IDAT", "IEND"]:
        raise SystemExit("mural chunks %s" % chunks)

    emblem = restore_emblem()
    emblem.save(WORK / "emblem_corner.png", "PNG")
    shutil.copy2(WORK / "emblem_corner.png", EMBLEM_LIVE)
    n, bright = count_orange(emblem)
    print("emblem", emblem.size, emblem.mode, "orange", n, "brightest", bright)
    # verify white under zero alpha
    px = emblem.load()
    bad = 0
    for y in range(0, 1024, 4):
        for x in range(0, 512, 4):
            r, g, b, a = px[x, y]
            if a == 0 and (r, g, b) != (255, 255, 255):
                bad += 1
    print("white-under-alpha sample bad", bad)
    print("knight", knight_info)
    print("DONE")


if __name__ == "__main__":
    main()
