# -*- coding: utf-8 -*-
"""Quest Forge: 4K mural + ant menu bg, 50% emblem, stone buttons, desktop ico."""
from __future__ import print_function

import io
import os
import random
import shutil
import struct
import time
import zipfile
from collections import deque
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageFont

INST = Path(r"C:\Users\a2dsu\AppData\Roaming\.crazycraft4")
ASSETS = Path(r"C:\Users\a2dsu\.cursor\projects\c-Users-a2dsu-OneDrive-Desktop-New-folder\assets")
WORK = Path(r"C:\Users\a2dsu\OneDrive\Desktop\QuestForge-Work\_work-hires-splash")
TITLE = INST / "resources" / "assets" / "minecraft" / "textures" / "gui" / "title"
STAMP = time.strftime("%Y%m%d-%H%M%S")
BACKUP = INST / ("_backup-splash-ui-%s" % STAMP)
OUT = WORK / "out"
FONTS = Path(r"C:\Windows\Fonts")

W4K, H4K = 3840, 2160
WHITE = (255, 255, 255)
TEXT = (232, 228, 240, 255)
TEXT_SHADOW = (8, 6, 12, 220)


def ensure_dirs():
    WORK.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    BACKUP.mkdir(parents=True, exist_ok=True)


def backup(src):
    src = Path(src)
    if not src.exists():
        return
    dest = BACKUP / src.name
    shutil.copy2(src, dest)
    print("backup", dest)


def open_rgb(path):
    return Image.open(path).convert("RGB")


def open_rgba(path):
    return Image.open(path).convert("RGBA")


def feather_mask(w, h, left, top, right, bottom):
    """Linear feather 0..255, opaque in the inner rect."""
    m = Image.new("L", (w, h), 0)
    px = m.load()
    for y in range(h):
        fy = 1.0
        if top > 0 and y < top:
            fy = y / float(top)
        elif bottom > 0 and y > h - 1 - bottom:
            fy = (h - 1 - y) / float(bottom)
        for x in range(w):
            fx = 1.0
            if left > 0 and x < left:
                fx = x / float(left)
            elif right > 0 and x > w - 1 - right:
                fx = (w - 1 - x) / float(right)
            v = int(255 * fx * fy)
            if v < 0:
                v = 0
            elif v > 255:
                v = 255
            px[x, y] = v
    return m


def paste_feather(dst, src, box, feather=96):
    """Resize src into box on dst with edge feather. box = (x,y,w,h) on dst."""
    x, y, bw, bh = box
    src = src.convert("RGB").resize((bw, bh), Image.Resampling.LANCZOS)
    # clip to canvas
    dx0 = max(0, x)
    dy0 = max(0, y)
    dx1 = min(dst.size[0], x + bw)
    dy1 = min(dst.size[1], y + bh)
    if dx1 <= dx0 or dy1 <= dy0:
        return
    sx0 = dx0 - x
    sy0 = dy0 - y
    cw, ch = dx1 - dx0, dy1 - dy0
    piece = src.crop((sx0, sy0, sx0 + cw, sy0 + ch))
    left = feather if x <= 0 or sx0 > 0 else (feather if dx0 > 0 else 0)
    top = feather if y <= 0 or sy0 > 0 else (feather if dy0 > 0 else 0)
    # Always feather sides that are interior overlaps; skip only true canvas edges of this piece
    fl = feather if dx0 > 0 else 0
    ft = feather if dy0 > 0 else 0
    fr = feather if dx1 < dst.size[0] else 0
    fb = feather if dy1 < dst.size[1] else 0
    mask = feather_mask(cw, ch, fl, ft, fr, fb)
    dst.paste(piece, (dx0, dy0), mask)


def unsharp(im, radius=1.35, percent=115, threshold=2):
    return im.filter(ImageFilter.UnsharpMask(radius=radius, percent=percent, threshold=threshold))


def compose_mural():
    orig = open_rgb(TITLE / "loading_mural.png")
    full = open_rgb(ASSETS / "loading_mural_full.png")
    canvas = orig.resize((W4K, H4K), Image.Resampling.LANCZOS)
    full4 = full.resize((W4K, H4K), Image.Resampling.LANCZOS)
    canvas = Image.blend(canvas, full4, 0.62)

    tiles = [
        ("mural_tile_tl.png", (0, 0, 1280, 1280)),
        ("mural_tile_tc.png", (1280, 0, 1280, 1280)),
        ("mural_tile_tr.png", (2560, 0, 1280, 1280)),
        ("mural_wall_left.png", (0, 180, 1280, 1280)),
        ("mural_wall_right.png", (2560, 180, 1280, 1280)),
        ("mural_tile_bl.png", (0, 880, 1280, 1280)),
        ("mural_tile_bc.png", (1280, 760, 1280, 1400)),
        ("mural_tile_br.png", (2560, 880, 1280, 1280)),
    ]
    extra = [
        ("mural_hall_full.png", (0, 0, W4K, H4K), 0.18),
        ("mural_floor.png", (0, 900, W4K, 1260), 0.22),
    ]
    for name, box in tiles:
        p = ASSETS / name
        if not p.exists():
            print("skip missing", name)
            continue
        paste_feather(canvas, open_rgb(p), box, feather=110)
        print("tile", name, box)

    # Mild extra full-scene gens if present (color continuity, not the only source)
    for name, box, alpha in extra:
        p = ASSETS / name
        if not p.exists():
            continue
        x, y, bw, bh = box
        layer = open_rgb(p).resize((bw, bh), Image.Resampling.LANCZOS)
        tmp = canvas.copy()
        tmp.paste(layer, (x, y))
        canvas = Image.blend(canvas, tmp, alpha)
        print("blend", name, alpha)

    canvas = unsharp(canvas, 1.25, 125, 2)
    dest = OUT / "loading_mural.png"
    canvas.save(dest, "PNG", optimize=False)
    print("mural", canvas.size, dest, dest.stat().st_size)
    return canvas


def compose_ant_bg():
    orig_path = Path(
        r"C:\Users\a2dsu\OneDrive\Desktop\QuestForge-Work\cc4-branding-v2\resourcepack\assets\custommenu\background.jpg"
    )
    orig = open_rgb(orig_path)
    full = open_rgb(ASSETS / "menu_ant_full.png")
    canvas = orig.resize((W4K, H4K), Image.Resampling.LANCZOS)
    canvas = Image.blend(canvas, full.resize((W4K, H4K), Image.Resampling.LANCZOS), 0.48)

    # Native ant close-up over the foreground left (the part the owner wants sharper)
    paste_feather(canvas, open_rgb(ASSETS / "menu_ant_left.png"), (0, 620, 1680, 1680), feather=140)
    # Sky / kaiju / planet
    paste_feather(canvas, open_rgb(ASSETS / "menu_ant_sky.png"), (980, 0, 2860, 1610), feather=150)

    canvas = unsharp(canvas, 1.2, 110, 2)
    png_path = OUT / "background.png"
    jpg_path = OUT / "background.jpg"
    nologo = OUT / "background-nologo.jpg"
    canvas.save(png_path, "PNG")
    rgb = canvas.convert("RGB")
    rgb.save(jpg_path, "JPEG", quality=93, subsampling=0, optimize=True)
    rgb.save(nologo, "JPEG", quality=93, subsampling=0, optimize=True)
    print("ant bg", canvas.size, jpg_path, jpg_path.stat().st_size)
    return canvas


def flood_chroma(im, corner_tol=28):
    """Punch edge-connected margin (magenta / white / near-flat) to alpha."""
    im = im.convert("RGBA")
    w, h = im.size
    px = im.load()
    seeds = [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1), (w // 2, 0), (w // 2, h - 1)]
    visited = bytearray(w * h)

    def near_key(r, g, b):
        if abs(r - 255) <= 18 and g <= 18 and abs(b - 255) <= 18:
            return True  # magenta
        if r >= 245 and g >= 245 and b >= 245:
            return True  # white
        if r >= 220 and g >= 220 and b >= 220 and abs(r - g) < 12 and abs(g - b) < 12:
            return True  # light gray studio
        return False

    q = deque()
    for sx, sy in seeds:
        r, g, b, a = px[sx, sy]
        if near_key(r, g, b):
            q.append((sx, sy, r, g, b))
            visited[sy * w + sx] = 1

    bg = []
    while q:
        x, y, sr, sg, sb = q.popleft()
        bg.append((x, y))
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if nx < 0 or ny < 0 or nx >= w or ny >= h:
                continue
            i = ny * w + nx
            if visited[i]:
                continue
            r, g, b, a = px[nx, ny]
            if abs(r - sr) <= corner_tol and abs(g - sg) <= corner_tol and abs(b - sb) <= corner_tol:
                visited[i] = 1
                q.append((nx, ny, sr, sg, sb))
            elif near_key(r, g, b):
                visited[i] = 1
                q.append((nx, ny, r, g, b))

    for x, y in bg:
        px[x, y] = (255, 255, 255, 0)
    return im


def alpha_bbox(im, thresh=12):
    a = im.split()[-1]
    bb = a.getbbox()
    if not bb:
        return (0, 0, im.size[0], im.size[1])
    return bb


def rugged_edge_mask(w, h, chip=7, seed=7):
    rng = random.Random(seed)
    m = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(m)
    # irregular polygon inset
    pts = []
    # top
    x = 0
    while x < w:
        pts.append((x, rng.randint(1, chip)))
        x += rng.randint(6, 14)
    pts.append((w - 1, rng.randint(1, chip)))
    # right
    y = 0
    while y < h:
        pts.append((w - 1 - rng.randint(1, chip), y))
        y += rng.randint(4, 10)
    pts.append((w - 1 - rng.randint(1, chip), h - 1))
    # bottom
    x = w - 1
    while x > 0:
        pts.append((x, h - 1 - rng.randint(1, chip)))
        x -= rng.randint(6, 14)
    pts.append((0, h - 1 - rng.randint(1, chip)))
    # left
    y = h - 1
    while y > 0:
        pts.append((rng.randint(1, chip), y))
        y -= rng.randint(4, 10)
    d.polygon(pts, fill=255)
    m = m.filter(ImageFilter.GaussianBlur(0.6))
    return m


def fit_plate(src, tw, th, seed=3):
    im = flood_chroma(src)
    bb = alpha_bbox(im)
    im = im.crop(bb)
    # cover target, keep rugged alpha
    scale = max(tw / float(im.size[0]), th / float(im.size[1]))
    nw = max(tw, int(im.size[0] * scale) + 2)
    nh = max(th, int(im.size[1] * scale) + 2)
    im = im.resize((nw, nh), Image.Resampling.LANCZOS)
    cx = (nw - tw) // 2
    cy = (nh - th) // 2
    im = im.crop((cx, cy, cx + tw, cy + th))
    mask = rugged_edge_mask(tw, th, chip=max(4, th // 14), seed=seed)
    a = ImageChops.multiply(im.split()[-1], mask)
    im.putalpha(a)
    return im


def load_font(size):
    for name in ("georgiab.ttf", "timesbd.ttf", "cambriab.ttf", "constanb.ttf"):
        p = FONTS / name
        if p.exists():
            return ImageFont.truetype(str(p), size)
    return ImageFont.load_default()


def draw_label(im, text):
    im = im.copy()
    w, h = im.size
    # Fit font to ~78% width, ~55% height
    size = int(h * 0.52)
    font = load_font(size)
    dtmp = ImageDraw.Draw(im)

    def tw(f):
        bbox = dtmp.textbbox((0, 0), text, font=f)
        return bbox[2] - bbox[0], bbox[3] - bbox[1]

    twid, thgt = tw(font)
    while (twid > w * 0.82 or thgt > h * 0.72) and size > 10:
        size -= 1
        font = load_font(size)
        twid, thgt = tw(font)
    x = (w - twid) // 2
    y = (h - thgt) // 2 - max(1, h // 30)
    # shadow
    d = ImageDraw.Draw(im)
    for ox, oy in ((2, 2), (1, 2), (2, 1), (0, 2)):
        d.text((x + ox, y + oy), text, font=font, fill=TEXT_SHADOW)
    d.text((x, y), text, font=font, fill=TEXT)
    return im


def make_buttons():
    idle_src = open_rgba(ASSETS / "btn_stone_normal.png")
    hover_src = open_rgba(ASSETS / "btn_wide_hover.png")
    idle_alt = open_rgba(ASSETS / "btn_stone_idle.png")
    hover_alt = open_rgba(ASSETS / "btn_stone_hover.png")

    large_idle = fit_plate(idle_src, 600, 80, seed=11)
    large_hover = fit_plate(hover_src, 600, 80, seed=11)
    small_idle = fit_plate(idle_alt, 450, 120, seed=17)
    small_hover = fit_plate(hover_alt, 450, 120, seed=17)

    labels_large = [
        ("single", "Singleplayer"),
        ("multiplayer", "Multiplayer"),
        ("mods", "Mods"),
        ("publicserver", "Public Server"),
    ]
    labels_small = [
        ("options", "Options"),
        ("quit", "Quit"),
    ]
    out = {}
    for stem, label in labels_large:
        a = draw_label(large_idle, label)
        b = draw_label(large_hover, label)
        ap = OUT / ("%s.png" % stem)
        bp = OUT / ("%sover.png" % stem)
        a.save(ap, "PNG")
        b.save(bp, "PNG")
        out[stem] = ap
        out[stem + "over"] = bp
        print("btn", stem, a.size, ap.stat().st_size)
    for stem, label in labels_small:
        a = draw_label(small_idle, label)
        b = draw_label(small_hover, label)
        ap = OUT / ("%s.png" % stem)
        bp = OUT / ("%sover.png" % stem)
        a.save(ap, "PNG")
        b.save(bp, "PNG")
        out[stem] = ap
        out[stem + "over"] = bp
        print("btn", stem, a.size, ap.stat().st_size)
    return out


def make_widgets():
    src = INST / "_work-splash" / "widgets_vanilla.png"
    if not src.exists():
        # pull from minecraft.jar
        jar = INST / "bin" / "minecraft.jar"
        with zipfile.ZipFile(jar, "r") as z:
            data = z.read("assets/minecraft/textures/gui/widgets.png")
        im = Image.open(io.BytesIO(data)).convert("RGBA")
    else:
        im = Image.open(src).convert("RGBA")
    px = im.load()
    # Vanilla button rows: y=46/66/86, x=0..199, h=20
    for y0 in (46, 66, 86):
        for y in range(y0, y0 + 20):
            for x in range(0, 200):
                r, g, b, a = px[x, y]
                px[x, y] = (r, g, b, 0)
    dest = OUT / "widgets.png"
    im.save(dest, "PNG")
    print("widgets", im.size, dest)
    return dest


def make_emblem_512():
    src = TITLE / "emblem_corner.png"
    im = open_rgba(src)
    im = im.resize((512, 512), Image.Resampling.LANCZOS)
    dest = OUT / "emblem_corner.png"
    im.save(dest, "PNG")
    print("emblem", im.size, "on-screen Forge quad = %dx%d px (was 512x512)" % (im.size[0] // 2, im.size[1] // 2))
    return im, dest


def circular_icon(im, size):
    im = im.convert("RGBA")
    w, h = im.size
    a = im.split()[-1]
    bb = a.getbbox() or (0, 0, w, h)
    # square around content
    cx = (bb[0] + bb[2]) / 2.0
    cy = (bb[1] + bb[3]) / 2.0
    side = int(max(bb[2] - bb[0], bb[3] - bb[1]) * 1.06)
    x0 = int(cx - side / 2)
    y0 = int(cy - side / 2)
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.paste(im, (-x0, -y0))
    mask = Image.new("L", (side, side), 0)
    d = ImageDraw.Draw(mask)
    inset = max(1, side // 80)
    d.ellipse((inset, inset, side - 1 - inset, side - 1 - inset), fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(max(0.4, side / 256.0)))
    out = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    out.paste(canvas, (0, 0))
    oa = ImageChops.multiply(out.split()[-1], mask)
    out.putalpha(oa)
    out = out.resize((size, size), Image.Resampling.LANCZOS)
    if size <= 32:
        out = ImageEnhance.Contrast(out).enhance(1.18)
        out = ImageEnhance.Sharpness(out).enhance(1.35)
    return out


def make_ico(emblem_src):
    # Use the original 1024 emblem for icon quality, not the 512 splash version
    live = open_rgba(TITLE / "emblem_corner.png")
    sizes = [256, 48, 32, 16]
    imgs = [circular_icon(live, s) for s in sizes]
    for s, im in zip(sizes, imgs):
        im.save(OUT / ("icon%d.png" % s), "PNG")
    ico_path = OUT / "questforge.ico"
    # PIL writes all sizes from the largest when sizes= is given
    imgs[0].save(
        ico_path,
        format="ICO",
        sizes=[(256, 256), (48, 48), (32, 32), (16, 16)],
        append_images=imgs[1:],
    )
    print("ico", ico_path, ico_path.stat().st_size)
    return ico_path


def write_splash_properties():
    text = (
        "#Splash screen properties\n"
        "#Quest Forge — 4K loading mural; corner emblem is 512px (half prior on-screen size)\n"
        "#background must be white: Forge multiplies logo RGB by this color\n"
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
    dest = OUT / "splash.properties"
    dest.write_bytes(text.encode("utf-8"))
    return dest


def replace_zip(zip_path, mapping_paths, extra_bytes=None):
    """mapping_paths: zip-entry -> filesystem Path. extra_bytes: zip-entry -> bytes."""
    extra_bytes = extra_bytes or {}
    zip_path = Path(zip_path)
    tmp = zip_path.with_suffix(zip_path.suffix + ".tmpqf")
    names_new = {k: Path(v) for k, v in mapping_paths.items()}
    with zipfile.ZipFile(zip_path, "r") as zin, zipfile.ZipFile(tmp, "w") as zout:
        seen = set()
        for item in zin.infolist():
            if item.filename in names_new or item.filename in extra_bytes:
                data = extra_bytes[item.filename] if item.filename in extra_bytes else names_new[item.filename].read_bytes()
                zi = zipfile.ZipInfo(item.filename, date_time=item.date_time)
                zi.compress_type = zipfile.ZIP_DEFLATED
                zout.writestr(zi, data)
                seen.add(item.filename)
            else:
                zout.writestr(item, zin.read(item.filename))
        for name, path in names_new.items():
            if name not in seen:
                zi = zipfile.ZipInfo(name)
                zi.compress_type = zipfile.ZIP_DEFLATED
                zout.writestr(zi, path.read_bytes())
        for name, data in extra_bytes.items():
            if name not in seen:
                zi = zipfile.ZipInfo(name)
                zi.compress_type = zipfile.ZIP_DEFLATED
                zout.writestr(zi, data)
    os.replace(str(tmp), str(zip_path))
    print("updated zip", zip_path)


def install():
    mural = OUT / "loading_mural.png"
    emblem = OUT / "emblem_corner.png"
    props = OUT / "splash.properties"
    ico = OUT / "questforge.ico"
    bg = OUT / "background.jpg"
    nologo = OUT / "background-nologo.jpg"
    widgets = OUT / "widgets.png"

    shutil.copy2(mural, TITLE / "loading_mural.png")
    shutil.copy2(emblem, TITLE / "emblem_corner.png")
    shutil.copy2(props, INST / "config" / "splash.properties")
    shutil.copy2(ico, INST / "questforge.ico")
    print("installed mural/emblem/properties/ico")

    btn_names = [
        "single",
        "singleover",
        "multiplayer",
        "multiplayerover",
        "mods",
        "modsover",
        "publicserver",
        "publicserverover",
        "options",
        "optionsover",
        "quit",
        "quitover",
    ]
    mapping = {"assets/custommenu/%s.png" % n: OUT / ("%s.png" % n) for n in btn_names}
    mapping["assets/custommenu/background.jpg"] = bg
    mapping["assets/custommenu/background-nologo.jpg"] = nologo
    mapping["assets/minecraft/textures/gui/widgets.png"] = widgets

    rp = INST / "resourcepacks" / "QuestForge.zip"
    replace_zip(rp, mapping)

    cm = INST / "mods" / "CustomMenu.jar"
    cm_map = {k: v for k, v in mapping.items() if k.startswith("assets/custommenu/")}
    replace_zip(cm, cm_map)

    # staging copies
    staging = Path(r"C:\Users\a2dsu\OneDrive\Desktop\QuestForge-Work\cc4-branding-v2\resourcepack")
    if staging.exists():
        (staging / "assets" / "custommenu").mkdir(parents=True, exist_ok=True)
        shutil.copy2(bg, staging / "assets" / "custommenu" / "background.jpg")
        for n in btn_names:
            shutil.copy2(OUT / ("%s.png" % n), staging / "assets" / "custommenu" / ("%s.png" % n))


def verify():
    mural = Image.open(TITLE / "loading_mural.png")
    emblem = Image.open(TITLE / "emblem_corner.png")
    print("VERIFY mural", mural.size, mural.mode)
    print("VERIFY emblem", emblem.size, emblem.mode)
    print("VERIFY emblem on-screen", emblem.size[0] // 2, "x", emblem.size[1] // 2, "px")
    ico = INST / "questforge.ico"
    print("VERIFY ico", ico.exists(), ico.stat().st_size if ico.exists() else 0)
    with zipfile.ZipFile(INST / "resourcepacks" / "QuestForge.zip") as z:
        bg = Image.open(io.BytesIO(z.read("assets/custommenu/background.jpg")))
        print("VERIFY pack bg", bg.size)
        s = Image.open(io.BytesIO(z.read("assets/custommenu/single.png")))
        so = Image.open(io.BytesIO(z.read("assets/custommenu/singleover.png")))
        print("VERIFY single", s.size, "over", so.size)
        print("VERIFY widgets", "assets/minecraft/textures/gui/widgets.png" in z.namelist())
    props = (INST / "config" / "splash.properties").read_bytes()
    print("VERIFY props BOM", props[:3] == b"\xef\xbb\xbf", "logo", b"loading_mural" in props, "rotate", b"rotate=false" in props)


def main():
    ensure_dirs()
    backup(TITLE / "loading_mural.png")
    backup(TITLE / "emblem_corner.png")
    backup(INST / "config" / "splash.properties")
    backup(INST / "resourcepacks" / "QuestForge.zip")
    backup(INST / "mods" / "CustomMenu.jar")
    lnk = Path(r"C:\Users\a2dsu\OneDrive\Desktop\Quest Forge.lnk")
    if lnk.exists():
        backup(lnk)

    print("=== mural ===")
    compose_mural()
    print("=== ant bg ===")
    compose_ant_bg()
    print("=== emblem ===")
    make_emblem_512()
    print("=== buttons ===")
    make_buttons()
    print("=== widgets ===")
    make_widgets()
    print("=== ico ===")
    make_ico(None)
    print("=== properties ===")
    write_splash_properties()
    print("=== install ===")
    install()
    verify()
    print("BACKUP", BACKUP)
    print("DONE")


if __name__ == "__main__":
    main()
