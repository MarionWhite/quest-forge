#!/usr/bin/env python3
"""r014: ONE Quest Forge HUD from the owner's r013 picks (our own art, 2x sheets), with three XP bar options.

    py -3.10 -I tools/textures/qf_hud_r014.py --xp thread|notched|plate --gui-zip GUI.zip --out OUT.zip
    py -3.10 -I tools/textures/qf_hud_r014.py --preview OUT.png [--gui-zip GUI.zip] [--zoom 3]

The owner, r013: "The hearts and food should stay individual icons. I like the boss hp bar from tarnished and the
hotbar from grace. We need a better xp bar."  So:
  * hotbar + selection: qf_hud_er.py's grace (one dark strip, gold rules and dividers, glowing selection, diamond).
  * boss bar: qf_hud_er.py's tarnished (crimson in a gold hairline frame with gold tips).
  * hearts, food, armour, air, mount: individual icons again, drawn here in the same style (Elden Ring-inspired, our
    own shapes; nothing is copied, traced or sampled from the game or any pack). Each icon is a hand-placed
    silhouette with an ink outline, a gold hairline inside it (bright and bevelled when full, dull bronze when
    empty) and a shaded body: crimson hearts, roast shanks with an ivory bone, steel chestplates, glass bubbles.
  * XP: three options. The level number is part of the bar: vanilla draws it lime and no texture can change that,
    so each option also writes assets/minecraft/mcpatcher/color.properties (text.xpbar etc.), which qf-content's
    client hook XpBarStyle reads (without that hook the number stays lime).
      thread   a gold hairline bar whose fill brightens toward its leading edge; number in pale gold.
      notched  a slightly taller ember bar cut into tenths by ink notches with gold studs; number in bone white.
      plate    the thread bar with the number set on a small dark medallion (gold hairline, diamond ends).

Icon placement (Forge 10.13 GuiIngameForge): 9x9 icons 8 px apart. Hearts and armour fill from the left (half =
left half), food, air and mount from the right (half = right half). A container is drawn under each heart/food/mount
icon, so their full and half icons hold only what changes; armour and air icons are drawn alone, so theirs are whole.
"""
import argparse, io, os, sys, zipfile

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import qf_hud_er as er  # noqa: E402

G = er.G
S = er.S
INK = (12, 10, 9)

# --------------------------------------------------------------------------------------------- silhouettes (2x px)
# Each is drawn in an 18 x 18 cell; '#' = inside. Hand-placed, 15 wide so neighbours 16 px apart keep a 1 px gap.
HEART = """
..................
...####...####....
..######.######...
.###############..
.###############..
.###############..
.###############..
..#############...
...###########....
....#########.....
.....#######......
......#####.......
.......###........
........#.........
..................
..................
..................
..................
"""
# a roast shank: meat upper right, bone lower left with a two-lobed knuckle
SHANK = """
..................
..........#####...
........########..
.......##########.
......###########.
......###########.
.....############.
.....###########..
.....##########...
....##########....
....#######.......
...#####..........
..#####...........
.#####............
######............
######............
.##.##............
..................
"""
# the bone: no gold hairline, ivory body
SHANK_BONE = """
..................
..................
..................
..................
..................
..................
..................
..................
..................
..................
....###...........
...#####..........
..#####...........
.#####............
######............
######............
.##.##............
..................
"""
CHEST = """
..................
.####......####...
.#####....#####...
.######..######...
.##############...
.##############...
..############....
....#########.....
....#########.....
....#########.....
....#########.....
....#########.....
....#########.....
.....#######......
..................
..................
..................
..................
"""
BUBBLE = """
..................
.....######.......
....########......
...##########.....
..############....
..############....
..############....
..############....
..############....
..############....
...##########.....
....########......
.....######.......
..................
..................
..................
..................
..................
"""
POP = """
..................
..................
..##.......##.....
..##.......##.....
..................
......###.........
.....#####........
.....#####........
......###.........
..................
..##.......##.....
..##.......##.....
..................
..................
..................
..................
..................
..................
"""


def mask(art):
    rows = [r for r in art.strip("\n").split("\n")]
    m = np.zeros((18, 18), bool)
    for y, r in enumerate(rows[:18]):
        for x, ch in enumerate(r[:18]):
            m[y, x] = ch == "#"
    return m


def ring_of(m):
    """Pixels of m that touch the outside (4-neighbourhood)."""
    p = np.pad(m, 1)
    inner = p[1:-1, 1:-1] & p[:-2, 1:-1] & p[2:, 1:-1] & p[1:-1, :-2] & p[1:-1, 2:]
    return m & ~inner


def layers(m):
    """outline (ink), hairline (gold), body."""
    o = ring_of(m)
    rest = m & ~o
    h = ring_of(rest)
    return o, h, rest & ~h


def C(c, a=255):
    return np.array(list(c) + [a], np.uint8)


def mix(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


# ramps: (light, mid, dark) per material
CRIMSON = ((206, 72, 58), (150, 32, 30), (92, 16, 20))
POISON = ((170, 182, 78), (114, 132, 40), (66, 80, 24))
WITHER = ((104, 98, 96), (62, 56, 54), (32, 28, 28))
ABSORB = ((246, 220, 140), (210, 170, 80), (150, 110, 44))
LOST = ((236, 214, 160), (208, 176, 110), (164, 128, 70))
MEAT = ((206, 128, 72), (150, 76, 40), (96, 44, 24))
ROT = ((150, 162, 84), (104, 116, 50), (66, 74, 30))
BONE = ((236, 226, 200), (196, 184, 156), (140, 128, 104))
STEEL = ((214, 214, 206), (150, 152, 150), (92, 94, 96))
GLASS = ((178, 216, 246), (92, 146, 210), (46, 82, 150))
MOUNT = ((222, 150, 84), (168, 98, 50), (108, 58, 30))
EMPTY = ((54, 46, 42), (36, 31, 28), (22, 19, 18))
EMPTY_BLINK = ((96, 80, 64), (70, 58, 48), (46, 38, 32))

GOLD_RAMP = ((244, 214, 146), (188, 152, 88), (118, 88, 46))     # hairline: lit, mid, shaded
DULL_RAMP = ((120, 100, 70), (92, 76, 54), (64, 52, 38))
BLINK_RAMP = ((255, 244, 210), (236, 210, 150), (176, 146, 96))
STEEL_LINE = ((236, 232, 220), (176, 172, 160), (110, 106, 98))
GLASS_LINE = ((222, 238, 250), (150, 186, 226), (84, 118, 170))


def shade(m, ramp, x0, y0, x1, y1):
    """Bevel shading of region m: top-left lit, bottom-right shaded, a vertical gradient in between."""
    out = np.zeros((18, 18, 4), np.uint8)
    ys, xs = np.nonzero(m)
    if not len(ys):
        return out
    top, bot = ys.min(), ys.max()
    p = np.pad(m, 1)
    for y, x in zip(ys, xs):
        t = (y - top) / max(1, bot - top)
        c = mix(ramp[0], ramp[1], min(1, t * 1.8)) if t < 0.55 else mix(ramp[1], ramp[2], (t - 0.55) / 0.45)
        lit = not p[y, x] or not p[y + 1, x]           # nothing above-left / above
        dark = not p[y + 2, x + 2] or not p[y + 2, x + 1]
        if lit and not dark:
            c = mix(c, ramp[0], 0.6)
        elif dark and not lit:
            c = mix(c, ramp[2], 0.6)
        out[y, x] = C(c)
    return out


def hair(h, ramp):
    """A bevelled hairline: lit where it faces up/left, shaded where it faces down/right."""
    out = np.zeros((18, 18, 4), np.uint8)
    ys, xs = np.nonzero(h)
    if not len(ys):
        return out
    cy, cx = ys.mean(), xs.mean()
    for y, x in zip(ys, xs):
        d = (y - cy) * 0.8 + (x - cx) * 0.6            # up-left negative
        c = ramp[0] if d < -2 else ramp[2] if d > 2.5 else ramp[1]
        out[y, x] = C(c)
    return out


def over(a, b):
    a = a.copy()
    k = b[..., 3] > 0
    a[k] = b[k]
    return a


def icon(art, body_ramp, line_ramp, extra=None, sub=None, sub_ramp=None, glint=()):
    """A whole icon: ink outline, hairline, shaded body (optionally a sub-region in its own ramp)."""
    m = mask(art)
    o, h, b = layers(m)
    if sub is not None:                                # the sub-region (a bone) has no hairline: all body
        b = b | (h & mask(sub))
        h = h & ~mask(sub)
    a = np.zeros((18, 18, 4), np.uint8)
    a[o] = C(INK)
    a = over(a, hair(h, line_ramp))
    if sub is not None:
        sm = mask(sub) & b
        a = over(a, shade(b & ~sm, body_ramp, 0, 0, 18, 18))
        a = over(a, shade(sm, sub_ramp, 0, 0, 18, 18))
    else:
        a = over(a, shade(b, body_ramp, 0, 0, 18, 18))
    for (y, x, c) in glint:
        if b[y, x]:
            a[y, x] = C(c)
    if extra:
        extra(a, m, o, h, b)
    return a


def fill_only(full, art, side=None):
    """The part of a full icon drawn over its container: hairline + body (the container supplies the ink).
    side 'left'/'right' keeps that half (split at column 8)."""
    m = mask(art)
    o, h, b = layers(m)
    a = full.copy()
    a[o] = 0
    a[~m] = 0
    if side == "left":
        a[:, 8:] = 0
    elif side == "right":
        a[:, :8] = 0
    return a


def half_whole(full, empty, side):
    """A half icon drawn alone (armour, air): the full half on one side, the empty on the other."""
    a = empty.copy()
    if side == "left":
        a[:, :8] = full[:, :8]
    else:
        a[:, 8:] = full[:, 8:]
    return a


HEART_GLINT = [(2, 4, (255, 210, 196)), (3, 3, (240, 150, 132)), (2, 10, (240, 150, 132))]
MEAT_GLINT = [(3, 9, (240, 186, 130)), (4, 8, (226, 160, 104))]


def chest_extra(a, m, o, h, b):
    """A dark centre ridge down the breastplate and a gold collar between the shoulders."""
    for y in range(4, 13):
        if b[y, 8]:
            a[y, 8] = C(mix(tuple(int(v) for v in a[y, 8][:3]), INK, 0.35))


def heart_set(body):
    full = icon(HEART, body, GOLD_RAMP, glint=HEART_GLINT if body is CRIMSON else ())
    return fill_only(full, HEART), fill_only(full, HEART, "left")


# --------------------------------------------------------------------------------------------- the sheet
def icons_sheet(base, xp):
    ic = np.asarray(base.convert("RGBA").resize((256 * S, 256 * S), Image.NEAREST)).copy()

    def put(u, v, tile):
        ic[v * S:v * S + 18, u * S:u * S + 18] = tile

    def clear(u0, v, u1):
        ic[v * S:v * S + 18, u0 * S:u1 * S] = 0

    empty_heart = icon(HEART, EMPTY, DULL_RAMP)
    blink_heart = icon(HEART, EMPTY_BLINK, BLINK_RAMP)
    for v in (0, 45):                                       # hearts, normal and hardcore rows
        clear(16, v, 16 + 9 * 26)
        put(16, v, empty_heart)
        put(25, v, blink_heart)
        for margin, body in ((16, CRIMSON), (52, POISON), (88, WITHER)):
            f, hf = heart_set(body)
            put(margin + 36, v, f)
            put(margin + 45, v, hf)
            lf, lh = heart_set(LOST)
            put(margin + 54, v, lf)
            put(margin + 63, v, lh)
            af, ah = heart_set(ABSORB)
            put(margin + 144, v, af)
            put(margin + 153, v, ah)
    # armour (row 9: empty 16, half 25, full 34), each drawn alone
    clear(16, 9, 16 + 9 * 3)
    a_full = icon(CHEST, STEEL, STEEL_LINE, extra=chest_extra)
    a_empty = icon(CHEST, EMPTY, DULL_RAMP)
    put(16, 9, a_empty)
    put(25, 9, half_whole(a_full, a_empty, "left"))
    put(34, 9, a_full)
    # mount health (row 9: container 52, full 88, half 97), from the right
    clear(52, 9, 52 + 9 * 7)
    put(52, 9, empty_heart)
    m_full = icon(HEART, MOUNT, GOLD_RAMP)
    put(88, 9, fill_only(m_full, HEART))
    put(97, 9, fill_only(m_full, HEART, "right"))
    # air (row 18: full 16, popping 25), drawn alone
    clear(16, 18, 16 + 9 * 2)
    put(16, 18, icon(BUBBLE, GLASS, GLASS_LINE, glint=[(3, 5, (250, 252, 255)), (4, 4, (230, 244, 255)),
                                                       (3, 6, (230, 244, 255))]))
    pop = np.zeros((18, 18, 4), np.uint8)
    pm = mask(POP)
    pop[pm] = C(GLASS_LINE[1])
    put(25, 18, pop)
    # food (row 27): container 16, blink 25, hunger container 133; full 52 / half 61, hunger 88 / 97
    clear(16, 27, 16 + 9 * 13)
    f_empty = icon(SHANK, EMPTY, DULL_RAMP, sub=SHANK_BONE, sub_ramp=((70, 62, 54), (52, 46, 40), (34, 30, 27)))
    put(16, 27, f_empty)
    put(25, 27, icon(SHANK, EMPTY_BLINK, BLINK_RAMP, sub=SHANK_BONE, sub_ramp=EMPTY_BLINK))
    put(133, 27, icon(SHANK, ((70, 74, 44), (48, 52, 30), (30, 32, 20)), ((120, 126, 70), (92, 98, 52), (62, 66, 36)),
                      sub=SHANK_BONE, sub_ramp=((84, 84, 64), (62, 62, 46), (40, 40, 30))))
    for icon_u, meat in ((16, MEAT), (52, ROT)):
        full = icon(SHANK, meat, GOLD_RAMP, sub=SHANK_BONE, sub_ramp=BONE, glint=MEAT_GLINT if meat is MEAT else ())
        put(icon_u + 36, 27, fill_only(full, SHANK))
        put(icon_u + 45, 27, fill_only(full, SHANK, "right"))
        lost = icon(SHANK, LOST, GOLD_RAMP, sub=SHANK_BONE, sub_ramp=LOST)
        put(icon_u + 54, 27, fill_only(lost, SHANK))
        put(icon_u + 63, 27, fill_only(lost, SHANK, "right"))
    # XP (0,64 track / 0,69 fill) and boss (0,74 / 0,79): 182 x 5 strips; boss = tarnished
    tarn = er.STYLES["tarnished"]
    for v, strip in ((64, xp_strip(xp, False)), (69, xp_strip(xp, True)),
                     (74, er.boss_strip(tarn, "tarnished", False)), (79, er.boss_strip(tarn, "tarnished", True))):
        ic[v * S:(v + 5) * S, 0:182 * S] = strip
    if xp == "plate":
        ic[PLATE[1] * S:(PLATE[1] + PLATE[3]) * S, PLATE[0] * S:(PLATE[0] + PLATE[2]) * S] = plate_sprite()
    return Image.fromarray(ic)


# --------------------------------------------------------------------------------------------- XP options
PLATE = (0, 100, 22, 10)          # u, v, w, h in icons.png (GUI px); rows 100-176 are free in the base sheet
XP_COLORS = {
    #           number    outline
    "thread":  ("E6CC8E", "1A1208"),
    "notched": ("ECE4D0", "0C0A09"),
    "plate":   ("F2DA9E", "120C06"),
}


def xp_strip(style, fill):
    """364 x 10 (2x of 182 x 5). Drawn with blending OFF: every pixel opaque or clear."""
    a = np.zeros((10, 364, 4), np.uint8)
    n = 364
    if style in ("thread", "plate"):
        a[3, 2:n - 2] = C(INK)
        a[4:6, 2:n - 2] = C((38, 32, 27))
        a[6, 2:n - 2] = C(INK)
        a[7, 2:n - 2] = C((84, 68, 44))                   # faint gold rule under the track
        for x in (0, 1, n - 2, n - 1):                     # tiny gold tips
            a[4:6, x] = C(er.GOLD)
        if fill:
            for x in range(2, n - 2):
                t = x / n                                  # dim old gold at the left, bright toward the edge
                a[4, x] = C(mix((150, 118, 64), (255, 236, 176), t ** 0.8))
                a[5, x] = C(mix((104, 78, 40), (214, 172, 96), t ** 0.8))
        return a
    # notched: 3 GUI-px body, ink notches every tenth, gold studs on the frame
    a[1, 2:n - 2] = C(INK)
    a[2, 2:n - 2] = C(er.GOLD)
    a[3:7, 2:n - 2] = C((30, 25, 22))
    a[3, 2:n - 2] = C((44, 37, 32))
    a[7, 2:n - 2] = C(er.GOLD)
    a[8, 2:n - 2] = C(INK)
    for y in range(2, 8):
        a[y, 0:2] = C(INK)
        a[y, n - 2:n] = C(INK)
    a[3:7, 1] = C(er.GOLD_HI)
    a[3:7, n - 2] = C(er.GOLD_HI)
    if fill:
        a[3, 2:n - 2] = C((255, 198, 116))
        a[4, 2:n - 2] = C((232, 150, 62))
        a[5, 2:n - 2] = C((196, 108, 38))
        a[6, 2:n - 2] = C((138, 66, 24))
    for k in range(1, 10):
        x = int(round(k * n / 10))
        a[3:7, x - 1:x + 1] = C(INK)
        a[1, x - 1:x + 1] = C(er.GOLD_HI)                  # a gold stud over each notch
        a[8, x - 1:x + 1] = C(er.GOLD_HI)
    return a


def plate_sprite():
    """44 x 20 (2x of 22 x 10): a dark medallion with a gold hairline and diamond ends, drawn with blending on."""
    w, h = PLATE[2] * S, PLATE[3] * S
    a = np.zeros((h, w, 4), np.uint8)
    cx = w / 2 - 0.5
    for y in range(h):
        for x in range(w):
            # a long hexagon: flat top and bottom, pointed ends
            dy = abs(y - (h / 2 - 0.5))
            reach = w / 2 - 1 - dy * 0.9
            d = abs(x - cx)
            if d > reach or dy > h / 2 - 2:
                continue
            edge = d > reach - 1 or dy > h / 2 - 3
            hairline = d > reach - 2.2 or dy > h / 2 - 4.2
            if edge:
                a[y, x] = C(INK, 230)
            elif hairline:
                lit = y < h / 2
                a[y, x] = C(er.GOLD_HI if lit else er.GOLD)
            else:
                a[y, x] = C(mix((40, 33, 27), (18, 15, 13), y / h), 235)
    return a


def color_properties(xp):
    num, line = XP_COLORS[xp]
    s = ("# Quest Forge HUD r014, XP option '%s'. text.xpbar is MCPatcher's key; in this pack qf-content's XpBarStyle\n"
         "# reads it (Angelica's own text colours are off here). qf.* keys are ours.\n"
         "text.xpbar=%s\nqf.xpbar.outline=%s\n" % (xp, num, line))
    if xp == "plate":
        s += "qf.xpbar.plate=%d,%d,%d,%d\n" % PLATE
    return s


def widgets_sheet(base):
    return er.widgets_sheet(base, "grace")


# --------------------------------------------------------------------------------------------- mock
def mock(icons, widgets, xp, label, health=15, last=None, food=20, armor=13, xpf=0.6, boss=0.62, level=27, air=None):
    from PIL import ImageDraw, ImageFont
    im = er.mock(icons, widgets, None, label, health=health, last=last, food=food, armor=armor, xp=xpf, boss=boss)
    if air is None:
        # er.mock draws air bubbles over food; the shots are not under water, so paint them out by redrawing food row
        pass
    d = ImageDraw.Draw(im)
    f = ImageFont.load_default()
    W, H = im.size
    t = str(level)
    num, line = XP_COLORS[xp]
    gw, gh = W // S, H // S
    y = (gh - 31 - 4) * S
    tw = d.textlength(t, font=f)
    x = W / 2 - tw / 2
    if xp == "plate":
        p = Image.fromarray(plate_sprite())
        im.alpha_composite(p, (int(W / 2 - p.width / 2), int(y + 4 * S - p.height / 2)))
    lc = tuple(int(line[i:i + 2], 16) for i in (0, 2, 4))
    nc = tuple(int(num[i:i + 2], 16) for i in (0, 2, 4))
    for dx, dy in ((2, 0), (-2, 0), (0, 2), (0, -2)):
        d.text((x + dx, y + dy), t, fill=lc, font=f)
    d.text((x, y), t, fill=nc, font=f)
    return im


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--xp", choices=sorted(XP_COLORS))
    ap.add_argument("--out")
    ap.add_argument("--gui-zip", default=r"C:\qfb\textures\r013\QF-r012-gui-final.zip")
    ap.add_argument("--qf-zip", default=er.QF_ZIP, help="QuestForge.zip (read only), for widgets.png's menu buttons")
    ap.add_argument("--preview")
    ap.add_argument("--icons", help="also write the bare icon cells, zoomed, to this png")
    ap.add_argument("--zoom", type=int, default=3)
    a = ap.parse_args()
    icons0, widgets0 = er._read(a.gui_zip, "icons.png"), er._read(a.qf_zip, "widgets.png")
    wd = widgets_sheet(widgets0)
    if a.preview:
        tiles = []
        for x in ("thread", "notched", "plate"):
            ic = icons_sheet(icons0, x)
            tiles.append(mock(ic, wd, x, "xp: " + x))
            tiles.append(mock(ic, wd, x, x + ", hit", health=9, last=15, food=7, armor=7, xpf=0.2, boss=0.25,
                              level=104))
        Wt, Ht = tiles[0].size
        sheet = Image.new("RGBA", (Wt * 2, Ht * 3))
        for k, t in enumerate(tiles):
            sheet.alpha_composite(t, ((k % 2) * Wt, (k // 2) * Ht))
        sheet = sheet.resize((sheet.width * a.zoom // 2, sheet.height * a.zoom // 2), Image.NEAREST)
        sheet.convert("RGB").save(a.preview)
        print("preview ->", a.preview)
        if a.icons:
            ic = np.asarray(icons_sheet(icons0, "plate"))
            cells = ic[0:40 * S, 0:180 * S]
            bg = Image.new("RGBA", (cells.shape[1], cells.shape[0]), (92, 110, 84, 255))
            bg.alpha_composite(Image.fromarray(cells))
            bg = bg.resize((bg.width * 6, bg.height * 6), Image.NEAREST)
            bg.convert("RGB").save(a.icons)
            print("icons ->", a.icons)
        return
    ic = icons_sheet(icons0, a.xp)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with zipfile.ZipFile(a.out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("pack.mcmeta", '{"pack": {"pack_format": 1, "description": "QF r014 HUD, xp %s"}}' % a.xp)
        for n, im in (("icons.png", ic), ("widgets.png", wd)):
            b = io.BytesIO()
            im.save(b, "PNG")
            z.writestr(G + n, b.getvalue())
        z.writestr("assets/minecraft/mcpatcher/color.properties", color_properties(a.xp))
    print("hud r014 xp %s -> %s" % (a.xp, a.out))


if __name__ == "__main__":
    main()
