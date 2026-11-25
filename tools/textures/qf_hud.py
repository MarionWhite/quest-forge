#!/usr/bin/env python3
"""r012: three Quest Forge HUD directions (hotbar, selection, XP bar, boss bar) at 1.7.10's sheet UVs.

    py -3.10 -I tools/textures/qf_hud.py --style iron|arcane|banner --out C:\\qfb\\textures\\r012\\QF-r012-hud-iron.zip
    py -3.10 -I tools/textures/qf_hud.py --preview OUT.png      (all three on a mock HUD, 4x)

The owner, r011 (HUD, neither): "I think we can do better on these. Something custom to Quest Forge." Our own art
(no reference-pack pixels), so these overlays carry no licence limits. They sit ABOVE QF-r011-gui.zip and replace only
widgets.png (hotbar 0,0 182x22; selection 0,22 24x22) and icons.png rows 64-84 (XP bar 0,64 / 0,69 and boss bar 0,74 /
0,79, each 182x5); hearts, armour and food stay Faithless's (read from the gui overlay's icons.png).

  iron    the main menu's forged-iron plates: blackened iron, lavender rim, ember-amber selection, molten XP,
          violet boss bar.
  arcane  the enchanting table: deep indigo with gold filigree, a gem-cornered gold selection, a faceted emerald XP
          channel, a crimson boss bar with Standard Galactic runes etched in its channel.
  banner  Faithless's red banners and the book creative screen: walnut with brass, a red-and-gold banner selection,
          gold-leaf XP, a red ribbon boss bar with gold edges.

1.7.10 limits: the boss bar is ONE 182 x 5 strip for every boss (GuiIngame.renderBossHealth), drawn at y 12 under the
name. A taller framed or per-boss bar (Faithless's bar_dragon 194x18) needs a GuiIngame hook in qf-tweaks.
"""
import argparse, io, os, zipfile

import numpy as np
from PIL import Image

G = "assets/minecraft/textures/gui/"
HERE = os.path.dirname(os.path.abspath(__file__))
GUI_ZIP = r"C:\qfb\textures\QF-r011-gui.zip"

# palette per style: dark outline, panel lo/hi, rim, well, well edge, sel outer/inner/glow,
# xp (top, mid, bottom), boss fill (top, mid, bottom), boss channel, accent
STYLES = {
    "iron": dict(outline=(11, 9, 16), panel=((38, 34, 48), (58, 53, 70)), rim=(201, 162, 255), rim2=(143, 122, 184),
                 well=(20, 17, 27), well_edge=(74, 58, 107), sel=((255, 196, 96), (196, 106, 28), (255, 236, 170)),
                 xp=((255, 230, 140), (255, 154, 46), (196, 82, 26)), boss=((232, 210, 255), (160, 112, 224), (90, 58, 154)),
                 channel=(30, 25, 40), accent=(255, 154, 46), grain="brushed"),
    "arcane": dict(outline=(9, 7, 20), panel=((26, 20, 48), (40, 31, 72)), rim=(240, 200, 96), rim2=(154, 116, 40),
                   well=(14, 12, 30), well_edge=(64, 52, 120), sel=((255, 222, 120), (170, 120, 40), (120, 240, 255)),
                   xp=((150, 255, 170), (47, 180, 90), (19, 102, 46)), boss=((255, 120, 150), (200, 40, 90), (110, 16, 60)),
                   channel=(30, 12, 28), accent=(120, 240, 255), grain="none"),
    "banner": dict(outline=(20, 10, 6), panel=((62, 38, 24), (86, 54, 32)), rim=(238, 168, 47), rim2=(170, 110, 30),
                   well=(34, 20, 12), well_edge=(110, 70, 40), sel=((238, 168, 47), (168, 58, 42), (255, 220, 140)),
                   xp=((255, 236, 140), (238, 190, 60), (170, 120, 30)), boss=((230, 90, 64), (181, 59, 38), (107, 23, 29)),
                   channel=(40, 14, 12), accent=(238, 168, 47), grain="wood"),
}
SGA = [  # 3x3 rune glyphs (Standard Galactic-like strokes), etched into the arcane boss channel
    ["x.x", ".x.", "x.x"], ["xxx", "..x", "xxx"], ["x..", "xxx", "x.."], [".x.", "x.x", "..."], ["xx.", "x..", "xx."],
    ["..x", ".x.", "x.."], ["x.x", "x.x", ".x."], ["xxx", ".x.", ".x."]]


def _rng(seed):
    return np.random.default_rng(seed)


def _mix(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def panel(w, h, st, seed):
    """Panel fill with the style's grain; rows: outline, rim, body ..., shade, outline."""
    r = _rng(seed)
    lo, hi = st["panel"]
    a = np.zeros((h, w, 4), np.uint8)
    a[:, :, 3] = 255
    for y in range(h):
        t = 1 - y / max(1, h - 1)
        base = np.array(_mix(lo, hi, 0.25 + 0.5 * t), float)
        if st["grain"] == "brushed":
            noise = r.normal(0, 7.0, w)
            row = base[None, :] + noise[:, None] * np.array([1, 1, 1.2])
        elif st["grain"] == "wood":
            ph = np.sin(np.arange(w) / 7.0 + y * 0.9 + np.sin(np.arange(w) / 23.0) * 2.0)
            row = base[None, :] * (1 + 0.18 * ph[:, None]) + r.normal(0, 2.5, (w, 1))
        else:
            row = np.repeat(base[None, :], w, 0)
        a[y, :, :3] = np.clip(row, 0, 255).astype(np.uint8)
    a[0, :, :3] = st["outline"]
    a[-1, :, :3] = st["outline"]
    a[:, 0, :3] = st["outline"]
    a[:, -1, :3] = st["outline"]
    a[1, 1:-1, :3] = st["rim2"]
    # rim highlight: sparse bright pixels along the top edge, brighter toward the middle
    for x in range(2, w - 2):
        if (x * 7 + seed) % 5 == 0 or abs(x - w / 2) < w * 0.18:
            a[1, x, :3] = st["rim"]
    a[-2, 1:-1, :3] = _mix(st["outline"], lo, 0.5)
    return a


def well(a, x, y, st):
    """An 18 x 18 recessed slot well at (x, y) (outer edge), item area 16 x 16 inside."""
    a[y:y + 18, x:x + 18, :3] = st["well"]
    a[y, x:x + 18, :3] = st["outline"]
    a[y:y + 18, x, :3] = st["outline"]
    a[y + 1, x + 1:x + 17, :3] = _mix(st["well"], st["outline"], 0.6)        # inner shadow, top-left
    a[y + 1:y + 17, x + 1, :3] = _mix(st["well"], st["outline"], 0.6)
    a[y + 17, x + 1:x + 18, :3] = st["well_edge"]                              # lit lip, bottom-right
    a[y + 1:y + 18, x + 17, :3] = st["well_edge"]


def hotbar(st, style):
    a = panel(182, 22, st, 11)
    for i in range(9):
        well(a, 2 + 20 * i, 2, st)
        x0 = 2 + 20 * i
        if style == "iron":                     # brushed well floor: lighter toward the bottom
            for y in range(3, 19):
                a[y, x0 + 2:x0 + 17, :3] = _mix(st["well"], st["well_edge"], 0.05 + 0.25 * (y - 3) / 15)
        if style == "arcane":                   # gold corner ticks inside each well
            for (cx, cy) in ((2, 2), (15, 2), (2, 15), (15, 15)):
                a[2 + cy, x0 + cx, :3] = st["rim2"]
            a[2 + 2, x0 + 3, :3] = st["rim2"]
            a[2 + 15, x0 + 14, :3] = st["rim2"]
        if style == "banner":                   # stitched leather edge: every other pixel of the lit lip
            for k in range(1, 17, 2):
                a[2 + 16, x0 + k, :3] = st["rim2"]
                a[2 + k, x0 + 16, :3] = st["rim2"]
    for i in range(1, 9):                       # seams between wells (x = 20 i, 2 px)
        x = 20 * i
        if style == "iron":
            a[2:20, x:x + 2, :3] = st["outline"]
            a[3, x:x + 2, :3] = st["rim"]           # a lavender rivet head top and bottom
            a[18, x:x + 2, :3] = st["rim2"]
        elif style == "arcane":
            a[2:20, x:x + 2, :3] = st["rim2"]
            a[2:20, x, :3] = st["rim"]
            a[10:12, x:x + 2, :3] = st["accent"]   # a cyan gem mid-seam
        else:
            a[2:20, x:x + 2, :3] = _mix(st["rim2"], st["outline"], 0.35)
            a[4, x:x + 2, :3] = st["rim"]
            a[17, x:x + 2, :3] = st["rim"]
    if style == "arcane":                       # double gold frame
        a[1, 1:181, :3] = st["rim"]
        a[20, 1:181, :3] = st["rim2"]
        a[1:21, 1, :3] = st["rim"]
        a[1:21, 180, :3] = st["rim2"]
    if style == "banner":                       # brass corner plates
        for cx in (1, 178):
            a[1:4, cx:cx + 3, :3] = st["rim"]
            a[18:21, cx:cx + 3, :3] = st["rim"]
    return a


def selection(st, style):
    """24 x 22 frame drawn over the hotbar (1.7.10 draws it at the slot's x - 1, y - 1 of the bar)."""
    a = np.zeros((24, 24, 4), np.uint8)
    outer, inner, glow = st["sel"]

    def ring(o, col):
        a[o, o:24 - o, :3] = col
        a[21 - o, o:24 - o, :3] = col
        a[o:22 - o, o, :3] = col
        a[o:22 - o, 23 - o, :3] = col
        a[o, o:24 - o, 3] = a[21 - o, o:24 - o, 3] = 255
        a[o:22 - o, o, 3] = a[o:22 - o, 23 - o, 3] = 255
    ring(0, st["outline"])
    ring(1, outer)
    ring(2, inner)
    for (cx, cy) in ((1, 1), (22, 1), (1, 20), (22, 20)):        # corner accents
        a[cy, cx, :3] = glow
    if style == "arcane":                                         # gem corners
        for (cx, cy) in ((0, 0), (22, 0), (0, 20), (22, 20)):
            a[cy:cy + 2, cx:cx + 2, :3] = glow
            a[cy:cy + 2, cx:cx + 2, 3] = 255
    if style == "banner":                                         # notched banner tails at the bottom corners
        a[21, 0:3, 3] = 0
        a[21, 21:24, 3] = 0
        a[20, 1, :3] = outer
        a[20, 22, :3] = outer
    if style == "iron":                                           # ember glow just inside the frame
        for o in (3,):
            a[o, o:24 - o, :3] = _mix(inner, (0, 0, 0), 0.35)
            a[o, o:24 - o, 3] = 140
    return a[:22]


def bar(st, kind, style):
    """(background, fill) 182 x 5 strips."""
    bg = np.zeros((5, 182, 4), np.uint8)
    bg[:, :, 3] = 255
    bg[:, :, :3] = st["outline"]
    bg[1:4, 1:181, :3] = st["channel"]
    bg[1, 1:181, :3] = _mix(st["channel"], (0, 0, 0), 0.4)
    top, mid, bot = st["xp"] if kind == "xp" else st["boss"]
    fill = bg.copy()
    fill[1, 1:181, :3] = top
    fill[2, 1:181, :3] = mid
    fill[3, 1:181, :3] = bot
    if kind == "xp":
        for x in range(1, 181):                 # tick marks every 18 px (levels read like the hotbar's slots)
            if x % 18 == 0:
                bg[1:4, x, :3] = st["well_edge"]
                fill[1:4, x, :3] = _mix(mid, bot, 0.7)
        if style == "arcane":                   # facets: a light diagonal every 6 px
            for x in range(1, 181):
                if x % 6 == 0:
                    fill[1, x, :3] = (230, 255, 235)
                    fill[2, x - 1 if x > 1 else x, :3] = _mix(top, mid, 0.5)
        if style == "iron":                     # molten sparkle
            r = _rng(5)
            for x in r.choice(np.arange(2, 180), 14, replace=False):
                fill[1, x, :3] = (255, 250, 220)
    else:
        if style == "arcane":                   # runes etched in the channel, faintly
            x = 4
            i = 0
            while x + 3 < 178:
                g = SGA[i % len(SGA)]
                for gy in range(3):
                    for gx in range(3):
                        if g[gy][gx] == "x":
                            bg[1 + gy, x + gx, :3] = _mix(st["channel"], st["rim"], 0.35)
                x += 6
                i += 1
        if style == "iron":
            for x in range(1, 181):
                if x % 4 == 0:
                    fill[1, x, :3] = _mix(top, (255, 255, 255), 0.5)
        if style == "banner":
            fill[0, :, :3] = st["rim"]
            fill[4, :, :3] = st["rim2"]
            bg[0, :, :3] = st["rim2"]
            bg[4, :, :3] = st["rim2"]
        # end caps (accent) on the background and the fill's left end
        for arr in (bg, fill):
            arr[:, 0:2, :3] = st["rim"] if style != "iron" else st["rim2"]
        bg[:, 180:182, :3] = st["rim"] if style != "iron" else st["rim2"]
    return bg, fill


def build(style, icons_src, widgets_src):
    st = STYLES[style]
    w = np.asarray(widgets_src.convert("RGBA")).copy()
    w[0:22, 0:182] = hotbar(st, style)
    w[22:44, 0:24] = selection(st, style)
    ic = np.asarray(icons_src.convert("RGBA")).copy()
    for kind, y in (("xp", 64), ("boss", 74)):
        bg, fill = bar(st, kind, style)
        ic[y:y + 5, 0:182] = bg
        ic[y + 5:y + 10, 0:182] = fill
    return Image.fromarray(ic), Image.fromarray(w)


def _base_sheets(gui_zip):
    z = zipfile.ZipFile(gui_zip)
    rd = lambda n: Image.open(io.BytesIO(z.read(G + n))).convert("RGBA")   # noqa: E731
    return rd("icons.png"), rd("widgets.png")


def mock(icons, widgets, label):
    """1.7.10 GuiIngame layout at 1x on a grass-green field: boss bar + name, hotbar, hearts, food, XP."""
    W, H = 240, 74
    im = Image.new("RGBA", (W, H), (78, 120, 60, 255))
    cx = W // 2
    im.alpha_composite(icons.crop((0, 74, 182, 79)), (cx - 91, 12))
    im.alpha_composite(icons.crop((0, 79, 120, 84)), (cx - 91, 12))
    y = H - 22
    im.alpha_composite(widgets.crop((0, 0, 182, 22)), (cx - 91, y))
    im.alpha_composite(widgets.crop((0, 22, 24, 44)), (cx - 91 - 1 + 20 * 2, y - 1))
    im.alpha_composite(icons.crop((0, 64, 182, 69)), (cx - 91, y - 7))
    im.alpha_composite(icons.crop((0, 69, 110, 74)), (cx - 91, y - 7))
    for i in range(10):
        im.alpha_composite(icons.crop((16, 0, 25, 9)), (cx - 91 + 8 * i, y - 17))
        im.alpha_composite(icons.crop((52, 0, 61, 9)), (cx - 91 + 8 * i, y - 17))
        im.alpha_composite(icons.crop((16, 27, 25, 36)), (cx + 91 - 9 - 8 * i, y - 17))
        im.alpha_composite(icons.crop((52, 27, 61, 36)), (cx + 91 - 9 - 8 * i, y - 17))
    return im


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--style", choices=sorted(STYLES))
    ap.add_argument("--out")
    ap.add_argument("--gui-zip", default=GUI_ZIP, help="the gui overlay whose icons.png (Faithless hearts) we keep")
    ap.add_argument("--preview")
    a = ap.parse_args()
    icons0, widgets0 = _base_sheets(a.gui_zip)
    if a.preview:
        tiles = [mock(icons0, widgets0, "r011")] + [mock(*build(s, icons0, widgets0), s) for s in ("iron", "arcane", "banner")]
        S = Image.new("RGBA", (tiles[0].width, sum(t.height for t in tiles)))
        y = 0
        for t in tiles:
            S.alpha_composite(t, (0, y))
            y += t.height
        S.resize((S.width * 4, S.height * 4), Image.NEAREST).convert("RGB").save(a.preview)
        print("preview ->", a.preview)
        return
    icons, widgets = build(a.style, icons0, widgets0)
    with zipfile.ZipFile(a.out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("pack.mcmeta", '{"pack": {"pack_format": 1, "description": "QF r012 HUD: %s"}}' % a.style)
        for n, im in (("icons.png", icons), ("widgets.png", widgets)):
            b = io.BytesIO()
            im.save(b, "PNG")
            z.writestr(G + n, b.getvalue())
    print("hud %s -> %s" % (a.style, a.out))


if __name__ == "__main__":
    main()
