# -*- coding: utf-8 -*-
"""LANCZOS 5120x2880 -> 3840x2160, write color-type-2 PNG, install mural + splash.properties."""
from __future__ import print_function

import shutil
import struct
import time
import zlib
from pathlib import Path

from PIL import Image

INST = Path(r"C:\Users\a2dsu\AppData\Roaming\.crazycraft4")
TITLE = INST / "resources" / "assets" / "minecraft" / "textures" / "gui" / "title"
WORK = Path(r"C:\Users\a2dsu\OneDrive\Desktop\QuestForge-Work\_splash-4k-buffer")
SRC = WORK / "hall_esrgan_x4.png"
OUT = WORK / "loading_mural.png"
W, H = 3840, 2160


def write_rgb_png(path, im):
    im = im.convert("RGB")
    w, h = im.size
    raw = im.tobytes()
    stride = w * 3
    rows = []
    for y in range(h):
        rows.append(b"\x00" + raw[y * stride : (y + 1) * stride])
    compressed = zlib.compress(b"".join(rows), 6)

    def chunk(tag, data):
        crc = zlib.crc32(tag + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)

    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    blob = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", compressed) + chunk(b"IEND", b"")
    path.write_bytes(blob)
    return w, h, len(blob)


def png_ihdr(path):
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise SystemExit("not a PNG")
    i = 8
    chunks = []
    while i + 8 <= len(data):
        ln = struct.unpack(">I", data[i : i + 4])[0]
        tag = data[i + 4 : i + 8]
        payload = data[i + 8 : i + 8 + ln]
        chunks.append(tag.decode("ascii"))
        if tag == b"IHDR":
            w, h, bit, ctype, comp, filt, inter = struct.unpack(">IIBBBBB", payload)
            print("IHDR", w, h, "bit", bit, "color_type", ctype, "interlace", inter)
        i += 12 + ln
        if tag == b"IEND":
            break
    print("chunks", chunks)
    return chunks


def write_splash_props(path):
    text = (
        "logoTexture=textures/gui/title/loading_mural.png\n"
        "forgeTexture=minecraft\\:textures/gui/title/emblem_corner.png\n"
        "rotate=false\n"
        "background=0xFFFFFF\n"
        "enabled=true\n"
        "font=0xE8E4F0\n"
        "barBackground=0x211B30\n"
        "barBorder=0x4A3A6B\n"
        "bar=0xC9A2FF\n"
        "resourcePackPath=resources\n"
        "logoOffset=0\n"
        "fontTexture=textures/font/ascii.png\n"
    )
    raw = text.encode("utf-8")
    if raw.startswith(b"\xef\xbb\xbf"):
        raise SystemExit("BOM leaked")
    path.write_bytes(raw)
    print("splash.properties", path, len(raw), "bom", False)


def main():
    stamp = time.strftime("%Y%m%d-%H%M%S")
    backup_dir = INST / ("_backup-mural-4k-%s" % stamp)
    backup_dir.mkdir(parents=True, exist_ok=True)
    live = TITLE / "loading_mural.png"
    if live.exists():
        shutil.copy2(live, backup_dir / "loading_mural.png")
        print("backup mural", backup_dir)
    props = INST / "config" / "splash.properties"
    if props.exists():
        shutil.copy2(props, backup_dir / "splash.properties")

    src = Image.open(SRC).convert("RGB")
    print("src", src.size)
    if src.size != (5120, 2880):
        raise SystemExit("unexpected ESRGAN size %s" % (src.size,))
    dest = src.resize((W, H), Image.Resampling.LANCZOS)
    write_rgb_png(OUT, dest)
    print("wrote", OUT, OUT.stat().st_size)
    chunks = png_ihdr(OUT)
    if chunks != ["IHDR", "IDAT", "IEND"]:
        raise SystemExit("unexpected chunks %s" % chunks)
    crop = dest.crop((900, 400, 1412, 912))
    crop.save(WORK / "detail_crop.png", "PNG")
    shutil.copy2(OUT, live)
    write_splash_props(INST / "config" / "splash.properties")
    installed = Image.open(live)
    print("installed", live, installed.size, installed.mode)
    emblem = TITLE / "emblem_corner.png"
    eim = Image.open(emblem)
    print("emblem untouched", emblem.stat().st_size, eim.size)
    print("DONE install")


if __name__ == "__main__":
    main()
