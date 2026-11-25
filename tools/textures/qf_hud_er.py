#!/usr/bin/env python3
"""r013: three Quest Forge HUD directions in the spirit of Elden Ring (our own art, at 2x).

    py -3.10 -I tools/textures/qf_hud_er.py --style tarnished|grace|ashen --out C:\\qfb\\textures\\r013\\QF-r013-hud-tarnished.zip
    py -3.10 -I tools/textures/qf_hud_er.py --preview OUT.png        (the three on a mock HUD)

The owner, r012 (HUD, neither, 5): "Try going for something Elden Ring inspired." What we take from that style, not
its pixels (nothing here is copied, traced or sampled from the game; every shape is drawn by this script): minimal,
long thin bars, a dark muted frame with fine gold hairlines, a quiet hotbar, a boss bar as a thin bar under its name.

How 1.7.10 (Forge 10.13 GuiIngameForge) is made to draw bars:
  * hearts, food, armour, air and mount health are ten 9x9 icons each, 8 px apart. Every icon here is an 8 px bar
    segment (column 8 transparent), so the ten tile into one continuous 80 px bar; a half heart/shank is a half
    segment. Hearts and armour fill from the left, food, air and mount from the right (their half segment is the
    right half). 1 HP = 4 px of bar.
  * damage blink (BACKGROUND 25, MARGIN+54/63) draws the lost part in pale gold, then the live bar over it.
  * the XP bar (0,64/0,69) is drawn with blending OFF and the bars with it ON; every icon pixel is fully opaque or
    fully clear, so both look the same. Only the hotbar (blend on) uses translucency.
  * the boss bar is one 182x5 strip at y 12 under the boss name, drawn once at full width, so it gets end caps.
  * 2x sheets (512x512): fine hairlines are half a GUI pixel. Not 4x: at GUI scale 2 a 4x sheet is minified with
    nearest sampling and its hairlines drop out.
Base sheets: icons.png from the gui overlay (Faithless: crosshair, ping bars and the rest kept, upscaled 2x);
widgets.png from QuestForge.zip (its menu buttons kept, upscaled 2x), because this sheet must sit ABOVE QuestForge.zip
in the pack stack (renderq job field rps_top) and replace its hotbar.

  tarnished  charcoal and old gold: hairline-framed bars (crimson HP, moss stamina = food, steel armour, blue air),
             a row of dark glass cells with gold hairlines, a gold-ringed selection, a gold-tipped boss bar.
  grace      warmer and brighter: one long dark strip for the hotbar with gold rules and slot dividers, a glowing
             selection with a small diamond over it, a fully framed boss bar with diamond tips.
  ashen      the quietest: no gold on the bars (bone hairlines), thinner bars, the hotbar only as corner brackets,
             a bare thin boss bar.
"""
import argparse, io, os, zipfile

import numpy as np
from PIL import Image, ImageDraw, ImageFont

G = "assets/minecraft/textures/gui/"
S = 2                                                      # sheet scale
GUI_ZIP = r"C:\qfb\textures\r012\QF-r012-gui.zip"
QF_ZIP = os.path.expandvars(r"%APPDATA%\.crazycraft4\resourcepacks\QuestForge.zip")   # read only

GOLD = (156, 128, 78)
GOLD_HI = (214, 184, 120)
BONE = (176, 168, 150)
INK = (10, 9, 8)

# bar body colours: (top, mid, bottom)
HP = ((178, 54, 46), (142, 30, 28), (100, 18, 20))
LOST = ((222, 190, 120), (196, 158, 90), (150, 112, 58))
POISON = ((152, 166, 72), (118, 134, 44), (82, 96, 28))
WITHER = ((98, 92, 90), (66, 60, 58), (40, 36, 36))
ABSORB = ((236, 210, 136), (206, 172, 88), (160, 124, 52))
STAM = ((112, 150, 86), (78, 118, 60), (52, 86, 42))
HUNGER = ((158, 150, 82), (122, 114, 52), (88, 82, 34))
ARMOR = ((182, 176, 162), (148, 142, 130), (112, 106, 96))
AIR = ((116, 156, 218), (72, 108, 180), (46, 72, 134))
MOUNT = ((186, 120, 74), (150, 92, 52), (108, 62, 34))
TRACK = ((36, 31, 28), (24, 21, 19), (18, 16, 15))

STYLES = {
    #            bar rows (2x px, in the 18 px icon): frame top, body rows, frame bottom; hairline colour; armour body
    "tarnished": dict(top=10, body=4, line=GOLD, line_hi=GOLD_HI, edge=INK, armor_body=2, boss="tips"),
    "grace":     dict(top=8, body=6, line=GOLD_HI, line_hi=(240, 214, 150), edge=INK, armor_body=2, boss="frame"),
    "ashen":     dict(top=11, body=3, line=(92, 86, 76), line_hi=BONE, edge=INK, armor_body=2, boss="bare"),
}


def rgba(c, a=255):
    return np.array(list(c) + [a], np.uint8)


# ----------------------------------------------------------------------------------------------- bar segments
def _body_rows(n, cols):
    """n body rows from a (top, mid, bottom) triple: a lit top row, the middle, a shaded bottom row."""
    top, mid, bot = cols
    if n == 1:
        return [mid]
    if n == 2:
        return [top, bot]
    return [top] + [mid] * (n - 2) + [bot]


def segment(st, body, kind="frame", half=None, body_n=None):
    """One 18x18 (2x) icon: an 8 GUI px bar segment, column 8 clear.
    kind 'frame' = edge, hairline, body, hairline, edge (a container or a self-framed piece);
    'fill' = body rows only (drawn over a container). half: None, 'left' or 'right'."""
    a = np.zeros((18, 18, 4), np.uint8)
    n = body_n or st["body"]
    y = st["top"]
    rows = []
    if kind == "frame":
        rows += [st["edge"], st["line"]]
    rows += _body_rows(n, body)
    if kind == "frame":
        rows += [st["line"], st["edge"]]
    y0 = y if kind == "frame" else y + 2
    x0, x1 = 0, 16
    if half == "left":
        x1 = 8
    elif half == "right":
        x0 = 8
    for i, c in enumerate(rows):
        a[y0 + i, x0:x1] = rgba(c)
    return a


def icons_sheet(base, style):
    st = STYLES[style]
    ic = np.asarray(base.convert("RGBA").resize((256 * S, 256 * S), Image.NEAREST)).copy()

    def put(u, v, tile):
        ic[v * S:v * S + 18, u * S:u * S + 18] = tile

    def clear(u0, v, u1):
        ic[v * S:v * S + 18, u0 * S:u1 * S] = 0

    flash = dict(st, line=st["line_hi"])
    for v in (0, 45):                                       # hearts, normal and hardcore rows
        clear(16, v, 16 + 9 * 26)
        put(16, v, segment(st, TRACK))                      # container
        put(25, v, segment(flash, ((74, 64, 56), (58, 50, 44), (44, 38, 34))))   # container while blinking
        for margin, body in ((16, HP), (52, POISON), (88, WITHER)):
            put(margin + 36, v, segment(st, body, "fill"))
            put(margin + 45, v, segment(st, body, "fill", "left"))
            put(margin + 54, v, segment(st, LOST, "fill"))
            put(margin + 63, v, segment(st, LOST, "fill", "left"))
            put(margin + 144, v, segment(st, ABSORB, "fill"))
            put(margin + 153, v, segment(st, ABSORB, "fill", "left"))
    # armour (row 9, 16/25/34): a thinner steel bar on its own track, filling from the left
    clear(16, 9, 16 + 9 * 3)
    an = st["armor_body"]
    arm = dict(st, top=st["top"] + (st["body"] - an) // 2)
    put(16, 9, segment(arm, TRACK, body_n=an))
    full = segment(arm, TRACK, body_n=an)
    full[arm["top"] + 2:arm["top"] + 2 + an, 0:16] = segment(arm, ARMOR, "fill", body_n=an)[arm["top"] + 2:arm["top"] + 2 + an, 0:16]
    put(34, 9, full)
    halfa = segment(arm, TRACK, body_n=an)
    halfa[arm["top"] + 2:arm["top"] + 2 + an, 0:8] = segment(arm, ARMOR, "fill", body_n=an)[arm["top"] + 2:arm["top"] + 2 + an, 0:8]
    put(25, 9, halfa)
    # mount health (row 9: container 52, full 88, half 97), from the right
    clear(52, 9, 52 + 9 * 7)
    put(52, 9, segment(st, TRACK))
    put(88, 9, segment(st, MOUNT, "fill"))
    put(97, 9, segment(st, MOUNT, "fill", "right"))
    # air (row 18: full 16, popping 25), no container: self-framed, from the right
    clear(16, 18, 16 + 9 * 2)
    put(16, 18, segment(st, AIR))
    put(25, 18, segment(dict(st, line=TRACK[0]), ((60, 80, 120), (46, 62, 96), (34, 46, 72))))
    # food (row 27): container 16, hunger container 133, full 52 / half 61, hunger 88 / 97, unused blink 70/79 106/115
    clear(16, 27, 16 + 9 * 13)
    put(16, 27, segment(st, TRACK))
    put(25, 27, segment(flash, TRACK))
    put(133, 27, segment(dict(st, line=(120, 112, 60)), TRACK))
    for icon, body in ((16, STAM), (52, HUNGER)):
        put(icon + 36, 27, segment(st, body, "fill"))
        put(icon + 45, 27, segment(st, body, "fill", "right"))
        put(icon + 54, 27, segment(st, LOST, "fill"))
        put(icon + 63, 27, segment(st, LOST, "fill", "right"))
    # XP (0,64 track / 0,69 fill) and boss (0,74 / 0,79): 182 x 5 strips
    for v, strip in ((64, xp_strip(st, style, False)), (69, xp_strip(st, style, True)),
                     (74, boss_strip(st, style, False)), (79, boss_strip(st, style, True))):
        ic[v * S:(v + 5) * S, 0:182 * S] = strip
    return Image.fromarray(ic)


def xp_strip(st, style, fill):
    """XP: a hairline. Drawn with blending off, so every pixel is opaque or clear."""
    a = np.zeros((10, 364, 4), np.uint8)
    if style == "ashen":
        a[4:6, :] = rgba((30, 28, 26))
        if fill:
            a[4, :] = rgba(BONE)
            a[5, :] = rgba((128, 120, 104))
        return a
    a[3, :] = rgba(INK)
    a[4:6, :] = rgba((40, 34, 28))
    a[6, :] = rgba(INK)
    if fill:
        a[4, :] = rgba(GOLD_HI)
        a[5, :] = rgba(GOLD)
    if style == "grace":                                    # faint gold rule under the track
        a[7, :] = rgba((92, 76, 48))
    return a


def boss_strip(st, style, fill):
    """Boss: a thin crimson bar in a hairline frame; caps at both ends (drawn once at full width)."""
    a = np.zeros((10, 364, 4), np.uint8)
    if style == "ashen":
        a[3, :] = rgba(INK)
        a[4:6, :] = rgba(TRACK[1])
        a[6, :] = rgba(INK)
        if fill:
            a[4, :] = rgba((168, 50, 42))
            a[5, :] = rgba((120, 28, 26))
        return a
    line = st["line"]
    a[1, 4:360] = rgba(INK)
    a[2, 4:360] = rgba(line)
    a[3:7, 4:360] = rgba(TRACK[1])
    a[3, 4:360] = rgba(TRACK[0])
    a[7, 4:360] = rgba(line)
    a[8, 4:360] = rgba(INK)
    if fill:
        a[3, 4:360] = rgba(HP[0])
        a[4:6, 4:360] = rgba(HP[1])
        a[6, 4:360] = rgba(HP[2])
    # caps: a gold point at each end (rows 1-8 taper to a tip at x 0 / 363)
    for y in range(1, 9):
        d = abs(y - 4.5)                                   # 0.5 .. 3.5
        reach = int(round(4 - d))                          # 3 .. 0: how far toward the tip this row runs
        for k in range(reach + 1):
            for x in (4 - k, 359 + k):
                a[y, x] = rgba(line if k < reach else GOLD_HI)
        a[y, 4] = a[y, 359] = rgba(GOLD_HI if style == "grace" else line)
    if style == "grace":                                   # ink keyline round the tips
        for y in (0, 9):
            a[y, 3:361] = 0
    return a


# ----------------------------------------------------------------------------------------------- hotbar
def _blend_px(a, y, x, c, alpha):
    a[y, x] = rgba(c, alpha)


def rect(a, x0, y0, x1, y1, c, alpha=255):
    a[y0:y1, x0:x1] = rgba(c, alpha)


def ring(a, x0, y0, x1, y1, c, alpha=255, t=1):
    rect(a, x0, y0, x1, y0 + t, c, alpha)
    rect(a, x0, y1 - t, x1, y1, c, alpha)
    rect(a, x0, y0, x0 + t, y1, c, alpha)
    rect(a, x1 - t, y0, x1, y1, c, alpha)


def brackets(a, x0, y0, x1, y1, c, alpha, arm):
    for (cx, cy, dx, dy) in ((x0, y0, 1, 1), (x1 - 1, y0, -1, 1), (x0, y1 - 1, 1, -1), (x1 - 1, y1 - 1, -1, -1)):
        for k in range(arm):
            for (py, px) in ((cy, cx + dx * k), (cy + dy * k, cx)):
                if 0 <= py < a.shape[0] and 0 <= px < a.shape[1]:   # clipped to the sheet cell
                    a[py, px] = rgba(c, alpha)


def hotbar(style):
    """364 x 44 (2x of 182 x 22). Slot i's item sits at GUI x 3+20i .. 19+20i, y 3..19 -> 2x 6+40i .., 6..38."""
    a = np.zeros((44, 364, 4), np.uint8)
    if style == "tarnished":
        for i in range(9):
            x0 = 4 + 40 * i
            rect(a, x0, 4, x0 + 36, 40, (14, 12, 11), 120)
            ring(a, x0, 4, x0 + 36, 40, GOLD, 190)
            ring(a, x0 - 1, 3, x0 + 37, 41, INK, 120)
    elif style == "grace":
        rect(a, 2, 4, 362, 40, (16, 14, 12), 130)
        rect(a, 2, 3, 362, 4, INK, 110)
        rect(a, 2, 4, 362, 5, GOLD, 210)
        rect(a, 2, 39, 362, 40, GOLD, 210)
        rect(a, 2, 40, 362, 41, INK, 110)
        for i in range(1, 9):                                    # dividers, fading toward the rules
            x = 2 + 40 * i
            for y in range(8, 36):
                al = int(150 * (1 - abs(y - 21.5) / 14.5) ** 0.7)
                if al > 26:
                    a[y, x] = rgba(GOLD, al)
        for cx in (2, 361):                                      # diamond tips on both ends
            for k in range(4):
                for y in range(22 - k, 22 + k):
                    xx = cx - (3 - k) if cx < 100 else cx + (3 - k)
                    a[y, xx] = rgba(GOLD_HI)
    else:  # ashen
        for i in range(9):
            x0 = 4 + 40 * i
            rect(a, x0, 4, x0 + 36, 40, (12, 12, 12), 70)
            brackets(a, x0, 4, x0 + 36, 40, BONE, 170, 5)
    return a


def selection(style):
    """48 x 44 (2x of 24 x 22), drawn 1 GUI px left of and above the slot's 20 px cell."""
    a = np.zeros((44, 48, 4), np.uint8)
    x0, y0, x1, y1 = 6, 6, 42, 42                              # the slot's cell in selection coordinates
    if style == "tarnished":
        rect(a, x0, y0, x1, y1, (60, 48, 30), 70)
        ring(a, x0 + 1, y0 + 1, x1 - 1, y1 - 1, (230, 196, 120), 70)
        ring(a, x0, y0, x1, y1, GOLD_HI, 255)
        ring(a, x0 - 1, y0 - 1, x1 + 1, y1 + 1, INK, 200)
        brackets(a, x0 - 3, y0 - 3, x1 + 3, y1 + 3, GOLD_HI, 255, 6)
    elif style == "grace":
        for k, al in ((1, 110), (2, 70), (3, 40), (4, 22)):    # inner glow
            ring(a, x0 + k, y0 + k, x1 - k, y1 - k, (240, 204, 130), al)
        ring(a, x0, y0, x1, y1, (246, 222, 160), 255)
        ring(a, x0 - 1, y0 - 1, x1 + 1, y1 + 1, GOLD, 160)
        for k in range(3):                                      # a small diamond over the slot
            a[1 + k, 24 - 1 - k:24 + 1 + k] = rgba(GOLD_HI)
            a[5 - k if k else 4, 24 - 1 - k:24 + 1 + k] = rgba(GOLD_HI)
        a[0, 23:25] = rgba(GOLD_HI)
    else:
        rect(a, x0, y0, x1, y1, (200, 196, 186), 30)
        ring(a, x0, y0, x1, y1, (226, 220, 206), 230)
        brackets(a, x0 - 2, y0 - 2, x1 + 2, y1 + 2, (236, 232, 220), 255, 7)
    return a


def widgets_sheet(base, style):
    w = np.asarray(base.convert("RGBA").resize((256 * S, 256 * S), Image.NEAREST)).copy()
    w[0:44, 0:364] = hotbar(style)
    w[44:88, 0:48] = selection(style)
    return Image.fromarray(w)


def build(style, icons_src, widgets_src):
    return icons_sheet(icons_src, style), widgets_sheet(widgets_src, style)


def _read(zp, name):
    with zipfile.ZipFile(zp) as z:
        return Image.open(io.BytesIO(z.read(G + name))).convert("RGBA")


# ----------------------------------------------------------------------------------------------- mock
def mock(icons, widgets, bg, label, health=15, last=None, food=14, armor=13, xp=0.6, boss=0.62):
    """GuiIngameForge's layout at 2x (GUI 240 x 100): boss bar and name, armour, hearts, food, XP, hotbar."""
    W, H = 240 * S, 100 * S
    im = bg.resize((W, H)).convert("RGBA") if bg else Image.new("RGBA", (W, H), (70, 96, 60, 255))
    cx = W // 2

    def blit(sheet, u, v, w, h, x, y):
        im.alpha_composite(sheet.crop((u * S, v * S, (u + w) * S, (v + h) * S)), (x * S, y * S))

    gw = W // S
    gh = H // S
    d = ImageDraw.Draw(im)
    f = ImageFont.load_default()
    name = "Ender Dragon"
    tw = d.textlength(name, font=f)
    d.text((cx - tw / 2 + 1, 2 * S + 1), name, fill=(40, 40, 40), font=f)
    d.text((cx - tw / 2, 2 * S), name, fill=(255, 255, 255), font=f)
    blit(icons, 0, 74, 182, 5, gw // 2 - 91, 12)
    blit(icons, 0, 79, int(boss * 182), 5, gw // 2 - 91, 12)
    left = gw // 2 - 91
    top = gh - 39
    for i in range(9, -1, -1):                     # hearts, descending as Forge draws them
        x = left + i * 8
        blit(icons, 25 if last else 16, 0, 9, 9, x, top)
        if last:
            if i * 2 + 1 < last:
                blit(icons, 70, 0, 9, 9, x, top)
            elif i * 2 + 1 == last:
                blit(icons, 79, 0, 9, 9, x, top)
        if i * 2 + 1 < health:
            blit(icons, 52, 0, 9, 9, x, top)
        elif i * 2 + 1 == health:
            blit(icons, 61, 0, 9, 9, x, top)
    for k, i in enumerate(range(1, 20, 2)):        # armour above, ascending
        u = 34 if i < armor else 25 if i == armor else 16
        blit(icons, u, 9, 9, 9, left + 8 * k, top - 10)
    right = gw // 2 + 91
    for i in range(10):                            # food, from the right
        x = right - i * 8 - 9
        blit(icons, 16, 27, 9, 9, x, top)
        if i * 2 + 1 < food:
            blit(icons, 52, 27, 9, 9, x, top)
        elif i * 2 + 1 == food:
            blit(icons, 61, 27, 9, 9, x, top)
    for i in range(7):                             # air, from the right, above food
        blit(icons, 16 if i < 6 else 25, 18, 9, 9, right - i * 8 - 9, top - 10)
    blit(icons, 0, 64, 182, 5, left, gh - 29)
    blit(icons, 0, 69, int(xp * 183), 5, left, gh - 29)
    blit(widgets, 0, 0, 182, 22, left, gh - 22)
    blit(widgets, 0, 22, 24, 22, left - 1 + 20 * 2, gh - 23)
    d.text((4, H - 12), label, fill=(255, 240, 200), font=f)
    return im


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--style", choices=sorted(STYLES))
    ap.add_argument("--out")
    ap.add_argument("--gui-zip", default=GUI_ZIP, help="the gui overlay whose icons.png we build on")
    ap.add_argument("--qf-zip", default=QF_ZIP, help="QuestForge.zip, whose widgets.png (menu buttons) we build on")
    ap.add_argument("--preview")
    ap.add_argument("--bg", help="a frame to put under the mock (scaled to the GUI)")
    ap.add_argument("--zoom", type=int, default=2)
    a = ap.parse_args()
    icons0, widgets0 = _read(a.gui_zip, "icons.png"), _read(a.qf_zip, "widgets.png")
    if a.preview:
        bg = Image.open(a.bg) if a.bg else None
        tiles = []
        for s in ("tarnished", "grace", "ashen"):
            ic, wd = build(s, icons0, widgets0)
            tiles.append(mock(ic, wd, bg, s))
            tiles.append(mock(ic, wd, bg, s + ", hit (lost HP in gold)", health=9, last=15, food=7, armor=7, xp=0.2,
                              boss=0.25))
        Wt, Ht = tiles[0].size
        sheet = Image.new("RGBA", (Wt * 2, Ht * 3))
        for k, t in enumerate(tiles):
            sheet.alpha_composite(t, ((k % 2) * Wt, (k // 2) * Ht))
        sheet = sheet.resize((sheet.width * a.zoom // 2, sheet.height * a.zoom // 2), Image.NEAREST)
        sheet.convert("RGB").save(a.preview)
        print("preview ->", a.preview)
        return
    icons, widgets = build(a.style, icons0, widgets0)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with zipfile.ZipFile(a.out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("pack.mcmeta", '{"pack": {"pack_format": 1, "description": "QF r013 HUD: %s"}}' % a.style)
        for n, im in (("icons.png", icons), ("widgets.png", widgets)):
            b = io.BytesIO()
            im.save(b, "PNG")
            z.writestr(G + n, b.getvalue())
    print("hud %s -> %s" % (a.style, a.out))


if __name__ == "__main__":
    main()
