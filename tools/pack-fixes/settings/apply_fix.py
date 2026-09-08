# -*- coding: utf-8 -*-
"""Restore vanilla widgets.png plates; lightly sharpen hall + ant at safe sizes."""
from __future__ import print_function

import io
import os
import shutil
import struct
import time
import zipfile
import zlib
from pathlib import Path

from PIL import Image, ImageFilter

INST = Path(r"C:\Users\a2dsu\AppData\Roaming\.crazycraft4")
WORK = Path(r"C:\Users\a2dsu\OneDrive\Desktop\QuestForge-Work")
OUT = WORK / "_fix-settings-20260904"
TITLE = INST / "resources" / "assets" / "minecraft" / "textures" / "gui" / "title"
HALL_1920 = INST / "_backup-splash-20260904-051600" / "loading_mural.png"
ORIG_ANT = WORK / "cc4-branding-v2" / "_work" / "questforge-zip" / "assets" / "custommenu" / "background.jpg"
VANILLA_WIDGETS = OUT / "vanilla_widgets.png"
STAMP = time.strftime("%Y%m%d-%H%M%S")
BACKUP = INST / ("_backup-settings-fix-%s" % STAMP)
MAX_PIXELS = 4194304


def seam_score(im, thirds=(1 / 3.0, 2 / 3.0), band=3):
    rgb = im.convert("RGB")
    w, h = rgb.size
    px = rgb.load()
    scores = []
    for frac in thirds:
        x = int(w * frac)
        acc = 0.0
        n = 0
        for col in range(max(1, x - band), min(w - 1, x + band + 1)):
            for y in range(h):
                a = px[col - 1, y]
                b = px[col, y]
                acc += abs(a[0] - b[0]) + abs(a[1] - b[1]) + abs(a[2] - b[2])
                n += 1
        scores.append(acc / float(n) if n else 0)
    base = 0.0
    bn = 0
    step = max(1, h // 120)
    for y in range(0, h, step):
        for x in range(1, w, 8):
            a = px[x - 1, y]
            b = px[x, y]
            base += abs(a[0] - b[0]) + abs(a[1] - b[1]) + abs(a[2] - b[2])
            bn += 1
    baseline = base / float(bn) if bn else 1.0
    return scores, baseline, [s / baseline for s in scores]


def save_simple_rgb_png(im, dest):
    """RGB PNG: signature + IHDR + IDAT + IEND only, color type 2."""
    rgb = im.convert("RGB")
    w, h = rgb.size
    if w * h >= MAX_PIXELS:
        raise SystemExit("TOO MANY PIXELS %s (%sx%s)" % (w * h, w, h))
    raw = bytearray()
    pixels = rgb.tobytes()
    stride = w * 3
    for y in range(h):
        raw.append(0)
        raw.extend(pixels[y * stride:(y + 1) * stride])

    def chunk(tag, data):
        crc = zlib.crc32(tag + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)

    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    idat = zlib.compress(bytes(raw), 6)
    data = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")
    dest = Path(dest)
    dest.write_bytes(data)
    # verify
    rawf = dest.read_bytes()
    chunks = []
    off = 8
    while off + 8 <= len(rawf):
        ln = struct.unpack(">I", rawf[off:off + 4])[0]
        tag = rawf[off + 4:off + 8]
        chunks.append(tag.decode("ascii"))
        off += 12 + ln
    print("wrote", dest.name, "%sx%s" % (w, h), "pixels=%s" % (w * h),
          "bytes=%s" % dest.stat().st_size, "chunks=%s" % chunks)
    if chunks != ["IHDR", "IDAT", "IEND"]:
        raise SystemExit("unexpected PNG chunks %s" % chunks)
    if rawf[25] != 2:
        raise SystemExit("color type %s want 2" % rawf[25])
    return dest


def replace_zip_files(zip_path, mapping):
    zip_path = Path(zip_path)
    tmp = zip_path.with_suffix(zip_path.suffix + ".tmpnew")
    with zipfile.ZipFile(zip_path, "r") as zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        replaced = set()
        for info in zin.infolist():
            if info.filename in mapping:
                data = Path(mapping[info.filename]).read_bytes()
                zout.writestr(info, data)
                replaced.add(info.filename)
                print("  zip replace", info.filename, len(data))
            else:
                zout.writestr(info, zin.read(info.filename))
        for name, src in mapping.items():
            if name not in replaced:
                zout.write(src, name)
                print("  zip add", name)
    os.replace(str(tmp), str(zip_path))
    print("wrote zip", zip_path, zip_path.stat().st_size)


def button_row_alpha(path):
    im = Image.open(path).convert("RGBA")
    px = im.load()
    stats = {}
    for y0 in (46, 66, 86):
        opaque = 0
        total = 0
        for y in range(y0, y0 + 20):
            for x in range(0, 200):
                a = px[x, y][3]
                total += 1
                if a >= 200:
                    opaque += 1
        stats[y0] = (opaque, total, 100.0 * opaque / total)
    return im.size, stats


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    print("=== BACKUP ===")
    BACKUP.mkdir(parents=True, exist_ok=True)
    for srcp in [
        TITLE / "loading_mural.png",
        INST / "mods" / "CustomMenu.jar",
        INST / "resourcepacks" / "QuestForge.zip",
        INST / "config" / "splash.properties",
    ]:
        if srcp.exists():
            shutil.copy2(srcp, BACKUP / srcp.name)
            print("backup", srcp.name, srcp.stat().st_size)

    print("=== WIDGETS ===")
    if not VANILLA_WIDGETS.exists():
        with zipfile.ZipFile(INST / "bin" / "minecraft.jar") as z:
            VANILLA_WIDGETS.write_bytes(z.read("assets/minecraft/textures/gui/widgets.png"))
    size, stats = button_row_alpha(VANILLA_WIDGETS)
    print("vanilla widgets", size, "opaque% by row", stats)
    for y0, (op, tot, pct) in stats.items():
        if pct < 90:
            raise SystemExit("vanilla button row y=%s only %.1f%% opaque" % (y0, pct))
    # current pack widgets for contrast
    with zipfile.ZipFile(INST / "resourcepacks" / "QuestForge.zip") as z:
        cur = Image.open(io.BytesIO(z.read("assets/minecraft/textures/gui/widgets.png"))).convert("RGBA")
        px = cur.load()
        a66 = sum(1 for x in range(200) for y in range(66, 86) if px[x, y][3] < 16)
        print("current pack button-row y=66 transparent pixels", a66, "/ 4000")

    replace_zip_files(INST / "resourcepacks" / "QuestForge.zip", {
        "assets/minecraft/textures/gui/widgets.png": str(VANILLA_WIDGETS),
    })
    with zipfile.ZipFile(INST / "resourcepacks" / "QuestForge.zip") as z:
        installed = OUT / "installed_widgets.png"
        installed.write_bytes(z.read("assets/minecraft/textures/gui/widgets.png"))
    _, inst_stats = button_row_alpha(installed)
    print("installed widgets opaque%", inst_stats)
    # CustomMenu.jar must not override widgets
    with zipfile.ZipFile(INST / "mods" / "CustomMenu.jar") as z:
        names = [n for n in z.namelist() if "widgets" in n.lower()]
        print("CustomMenu.jar widgets entries", names)

    print("=== MURAL SHARPEN ===")
    hall = Image.open(HALL_1920).convert("RGB")
    print("hall source", HALL_1920, hall.size, HALL_1920.stat().st_size)
    s0, b0, r0 = seam_score(hall)
    print("hall1920 seams", s0, "base", b0, "ratio", r0)

    hall_sharp = hall.filter(ImageFilter.UnsharpMask(radius=1.05, percent=65, threshold=4))
    s1, b1, r1 = seam_score(hall_sharp)
    print("hall1920+unsharp seams", s1, "base", b1, "ratio", r1)

    hall2560 = hall.resize((2560, 1440), Image.Resampling.LANCZOS)
    s2, b2, r2 = seam_score(hall2560)
    print("hall2560 raw seams", s2, "base", b2, "ratio", r2)
    hall2560_sharp = hall2560.filter(ImageFilter.UnsharpMask(radius=0.9, percent=50, threshold=5))
    s3, b3, r3 = seam_score(hall2560_sharp)
    print("hall2560+unsharp seams", s3, "base", b3, "ratio", r3)

    # Prefer native 1920 if upscale+sharpen raises third-column seam ratio vs native sharp
    pick_1920 = max(r3) > max(r1) * 1.08 or max(r3) > 1.35
    if pick_1920:
        chosen = hall_sharp
        choice = "1920 native + light UnsharpMask(r=1.05,p=65,t=4)"
        out_mural = OUT / "loading_mural_1920_sharp.png"
    else:
        chosen = hall2560_sharp
        choice = "2560 LANCZOS + conservative UnsharpMask(r=0.9,p=50,t=5)"
        out_mural = OUT / "loading_mural_2560_sharp.png"
    print("CHOSEN MURAL:", choice, chosen.size)
    save_simple_rgb_png(chosen, out_mural)
    shutil.copy2(out_mural, TITLE / "loading_mural.png")
    # also keep the other candidate on disk
    save_simple_rgb_png(hall_sharp, OUT / "loading_mural_1920_sharp.png")
    save_simple_rgb_png(hall2560_sharp, OUT / "loading_mural_2560_sharp.png")
    (OUT / "mural_choice.txt").write_text(choice + "\n" + str(chosen.size) + "\n", encoding="utf-8")

    print("=== ANT SHARPEN ===")
    ant = Image.open(ORIG_ANT).convert("RGB")
    print("ant source", ORIG_ANT, ant.size, ORIG_ANT.stat().st_size)
    if ant.size != (1920, 1080):
        raise SystemExit("ant is %s, want 1920x1080" % (ant.size,))
    ant_sharp = ant.filter(ImageFilter.UnsharpMask(radius=0.9, percent=45, threshold=4))
    ant_out = OUT / "background_1920_sharp.jpg"
    ant_sharp.save(ant_out, "JPEG", quality=93, optimize=True, subsampling=0)
    print("ant jpeg", ant_out.stat().st_size, Image.open(ant_out).size)
    if Image.open(ant_out).size != (1920, 1080):
        raise SystemExit("ant jpeg resized")
    mapping_bg = {"assets/custommenu/background.jpg": str(ant_out)}
    replace_zip_files(INST / "mods" / "CustomMenu.jar", mapping_bg)
    replace_zip_files(INST / "resourcepacks" / "QuestForge.zip", mapping_bg)

    print("=== splash.properties UTF-8 no BOM, enabled ===")
    props = (
        "logoTexture=textures/gui/title/loading_mural.png\n"
        "background=0xFFFFFF\n"
        "font=0xE8E4F0\n"
        "barBackground=0x211B30\n"
        "barBorder=0x4A3A6B\n"
        "rotate=false\n"
        "bar=0xC9A2FF\n"
        "enabled=true\n"
        "resourcePackPath=resources\n"
        "logoOffset=0\n"
        "forgeTexture=minecraft\\:textures/gui/title/emblem_corner.png\n"
        "fontTexture=textures/font/ascii.png\n"
    )
    props_path = INST / "config" / "splash.properties"
    props_path.write_bytes(props.encode("utf-8"))
    raw = props_path.read_bytes()
    print("splash bytes", len(raw), "bom", raw[:3] == b"\xef\xbb\xbf", "enabled", b"enabled=true" in raw)

    print("=== VERIFY LIVE ===")
    live = Image.open(TITLE / "loading_mural.png")
    print("live mural", live.size, live.mode, (TITLE / "loading_mural.png").stat().st_size)
    print("DONE choice=", choice)


if __name__ == "__main__":
    main()
