#!/usr/bin/env python3
"""r015: FIVE complete Quest Forge HUD designs (our own art, 2x sheets), richer than r014.

    py -3.10 -I tools/textures/qf_hud_r015.py --design gilded|cloisonne|ironbound|moonsilver|obsidian --out OUT.zip
    py -3.10 -I tools/textures/qf_hud_r015.py --mock OUT.png [--icons OUT2.png]   (all five, offline)

The owner, r014 ("neither", 4): "I like the idea of a medallion, but we are going too far minimalist here with these
designs. I want it to look more sleek and pleasing on the eyes."  And: "I want to see at least 5 unique designs before
we commit."  So each design here is a whole HUD (hotbar, selection, hearts, food, armour, air, mount, XP bar with a
medallion, boss bar with a frame) in one material, and the five differ in material and silhouette:

  gilded      smoky glass in bevelled gold; a gold-railed ribbon behind the hearts and food, gold studs; a gold coin
              medallion with clasps; the grace hotbar and tarnished boss bar grown up (r014's picks, richer).
  cloisonne   lapis enamel cells in gold wire: every heart, shank and slot sits in its own cell; turquoise jewels;
              a lapis medallion in a double gold ring.
  ironbound   blackened, riveted iron plate; sunken slots; faceted rubies set in steel; molten XP; a hex-nut medallion
              with an ember ring; iron clamps on the boss bar.
  moonsilver  silver filigree on midnight blue: an arcade (each heart under its own silver arch), gothic arched slots,
              a full-moon medallion, crescent moons on the boss bar.
  obsidian    black volcanic glass with amethyst glow: angled seams, chamfered slots, crystal hearts, a rune-stone
              medallion, thorned boss bar.

Nothing is copied, traced or sampled from any game or pack; every pixel is drawn by this script.

How 1.7.10 (Forge 10.13 GuiIngameForge) draws these, and what that allows (all checked against the mock below):
  * hearts/food/armour/mount are 9x9 icons 8 px apart. Hearts, food, mount and air are drawn right to left, so each
    icon's column 8 covers its right neighbour's column 0; armour is drawn left to right, the other way round. So
    every icon here keeps its art in columns 1-7 and draws the same divider in column 0 and column 8: whichever is on
    top, the row looks the same, and the ends of each row are closed.
  * a container is drawn under every heart/food/mount icon (all ten, whatever the health), so the container carries
    the row's band (the frame behind the icons) plus an empty socket; full and half icons hold only the gem itself.
    Armour icons are drawn alone (all ten when armour > 0), so each carries the band too. Air is drawn alone and only
    while under water, so bubbles have no band.
  * the XP bar is drawn with blending off: every XP pixel is opaque or clear. Everything else blends.
  * the XP number, the medallion behind it, the boss-name outline and the boss frame are drawn by qf-content's
    client hook XpBarStyle from assets/minecraft/mcpatcher/color.properties (text.xpbar, qf.xpbar.outline,
    qf.xpbar.plate, text.boss, qf.boss.outline, qf.boss.frame). Without that hook (the owner's yes) the number stays
    lime, the medallion, boss outline and boss frame are not drawn; the rest of the HUD is plain textures.
  * at GUI scale 1 a 2x sheet shows only its odd texels (u = 2x + 1), so every rim and divider that must read at 1x
    is two texels wide; one-texel lines are finish for scales 2 and up.
"""
import argparse, io, math, os, sys, zipfile

import numpy as np
from PIL import Image

G = "assets/minecraft/textures/gui/"
S = 2
QF_ZIP = os.path.expandvars(r"%APPDATA%\.crazycraft4\resourcepacks\QuestForge.zip")   # read only
GUI_ZIP = r"C:\qfb\textures\r013\QF-r012-gui-final.zip"
MC_JAR = os.path.expandvars(r"%APPDATA%\.crazycraft4\bin\minecraft.jar")               # read only: mock font/items

PLATE = (0, 100, 26, 15)       # medallion sprite in icons.png (GUI px): drawn at w/2-13, rows h-38..h-24
MX, MY = 25, 13                # the number's centre in the 52 x 30 sprite (2x px): one texel left of the middle
FRAME = (0, 120, 214, 15)      # boss frame sprite: centred on the boss bar (bar = frame cols 16-197, rows 5-9)
DESIGNS = ["gilded", "cloisonne", "ironbound", "moonsilver", "obsidian"]
TITLES = {"gilded": "A  Gilded", "cloisonne": "B  Cloisonne", "ironbound": "C  Ironbound",
          "moonsilver": "D  Moonsilver", "obsidian": "E  Obsidian"}

INK = (10, 8, 8)


# =============================================================================================== drawing toolkit
def C(c, a=255):
    return np.array([int(c[0]), int(c[1]), int(c[2]), int(a)], np.uint8)


def mix(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


def ramp_at(r, t):
    """r: list of colours from lit (t=0) to deep (t=1)."""
    t = max(0.0, min(1.0, t)) * (len(r) - 1)
    i = min(int(t), len(r) - 2)
    return mix(r[i], r[i + 1], t - i)


def blank(w, h):
    return np.zeros((h, w, 4), np.uint8)


def rect(a, x0, y0, x1, y1, c, al=255):
    y0, y1, x0, x1 = max(0, y0), min(a.shape[0], y1), max(0, x0), min(a.shape[1], x1)
    if x1 > x0 and y1 > y0:
        a[y0:y1, x0:x1] = C(c, al)


def px(a, x, y, c, al=255):
    if 0 <= y < a.shape[0] and 0 <= x < a.shape[1]:
        a[y, x] = C(c, al)


def over(a, b, x=0, y=0):
    """Composite b over a at (x, y) (straight alpha)."""
    h, w = b.shape[:2]
    y0, x0 = max(0, y), max(0, x)
    y1, x1 = min(a.shape[0], y + h), min(a.shape[1], x + w)
    if y1 <= y0 or x1 <= x0:
        return a
    src = b[y0 - y:y1 - y, x0 - x:x1 - x].astype(np.float32) / 255
    dst = a[y0:y1, x0:x1].astype(np.float32) / 255
    sa, da = src[..., 3:4], dst[..., 3:4]
    oa = sa + da * (1 - sa)
    oc = np.where(oa > 0, (src[..., :3] * sa + dst[..., :3] * da * (1 - sa)) / np.maximum(oa, 1e-6), 0)
    a[y0:y1, x0:x1] = np.clip(np.concatenate([oc, oa], -1) * 255 + 0.5, 0, 255).astype(np.uint8)
    return a


def mask_of(art):
    rows = [r for r in art.strip("\n").split("\n")]
    m = np.zeros((len(rows), max(len(r) for r in rows)), bool)
    for y, r in enumerate(rows):
        for x, ch in enumerate(r):
            m[y, x] = ch == "#"
    return m


def ring(m, diag=False):
    p = np.pad(m, 1)
    inner = p[1:-1, 1:-1] & p[:-2, 1:-1] & p[2:, 1:-1] & p[1:-1, :-2] & p[1:-1, 2:]
    if diag:
        inner &= p[:-2, :-2] & p[:-2, 2:] & p[2:, :-2] & p[2:, 2:]
    return m & ~inner


def dilate(m):
    p = np.pad(m, 1)
    return p[1:-1, 1:-1] | p[:-2, 1:-1] | p[2:, 1:-1] | p[1:-1, :-2] | p[1:-1, 2:]


def place(m, w, h, x, y):
    out = np.zeros((h, w), bool)
    out[y:y + m.shape[0], x:x + m.shape[1]] = m
    return out


def shade_body(m, r, light=(0.55, 0.85), lift=0.0):
    """Body shading: r = [light, mid, dark, deep]; lit toward the top-left, edge pixels pushed one step."""
    out = np.zeros(m.shape + (4,), np.uint8)
    ys, xs = np.nonzero(m)
    if not len(ys):
        return out
    cy, cx = (ys.min() + ys.max()) / 2, (xs.min() + xs.max()) / 2
    ry, rx = max(1, (ys.max() - ys.min()) / 2), max(1, (xs.max() - xs.min()) / 2)
    p = np.pad(m, 1)
    for y, x in zip(ys, xs):
        u, v = (x - cx) / rx, (y - cy) / ry
        t = 0.42 + 0.42 * (u * light[0] + v * light[1]) / (light[0] + light[1]) - lift
        if not p[y, x + 1] or not p[y, x]:            # above / above-left outside: lit edge
            t -= 0.25
        if not p[y + 2, x + 1] or not p[y + 2, x + 2]:  # below / below-right outside: shaded edge
            t += 0.25
        out[y, x] = C(ramp_at(r, t))
    return out


def bevel_ring(rm, m, r):
    """A metal rim: rm = rim pixels of shape m; r = [spec, light, mid, dark, deep]. Faces up-left are lit."""
    out = np.zeros(rm.shape + (4,), np.uint8)
    p = np.pad(m, 1)
    for y, x in zip(*np.nonzero(rm)):
        ny = (0 if p[y + 2, x + 1] else 1) - (0 if p[y, x + 1] else 1)
        nx = (0 if p[y + 1, x + 2] else 1) - (0 if p[y + 1, x] else 1)
        d = -(nx * 0.55 + ny * 0.85)                    # >0: faces the light
        t = 0.15 if d > 0.6 else 0.35 if d > 0.1 else 0.6 if d > -0.4 else 0.85
        out[y, x] = C(ramp_at(r, t))
    return out


def facets(m, r, cx=None, cy=None, n=6, table=0.0):
    """Faceted gem body: sectors round (cx, cy) in fixed tones (lit top-left), a bright table near the centre."""
    out = np.zeros(m.shape + (4,), np.uint8)
    ys, xs = np.nonzero(m)
    if cy is None:
        cy = (ys.min() + ys.max()) / 2 - 1
    if cx is None:
        cx = (xs.min() + xs.max()) / 2
    tones = {0: 0.05, 1: 0.3, 2: 0.55, 3: 0.95, 4: 0.75, 5: 0.45}
    for y, x in zip(ys, xs):
        ang = math.atan2(y - cy, x - cx)                 # -pi..pi, 0 = right
        k = int(((ang + math.pi * (1 + 1 / n) + math.pi / 2) % (2 * math.pi)) / (2 * math.pi) * n) % n
        t = tones.get(k, 0.5)
        if table and ((x - cx) / 3.2) ** 2 + ((y - cy) / 2.4) ** 2 < table:
            t = 0.12
        out[y, x] = C(ramp_at(r, t))
    return out


# =============================================================================================== shapes (2x px)
HEART = mask_of("""
..####..####..
.#####..#####.
##############
##############
##############
.############.
..##########..
...########...
....######....
.....####.....
......##......
""")
HEART_GEM = mask_of("""
..###....###..
.#####..#####.
##############
##############
.############.
..##########..
...########...
....######....
.....####.....
......##......
""")
SHANK = mask_of("""
.......#####..
.....########.
....##########
....##########
...###########
...##########.
...#########..
..#########...
..######......
.####.........
####..........
####..........
.#..#.........
""")
BONE = mask_of("""
..............
..............
..............
..............
..............
..............
..............
..............
..##..........
.####.........
####..........
####..........
.#..#.........
""")
CHEST = mask_of("""
.###......###.
#####....#####
######..######
##############
##############
.############.
..##########..
..##########..
..##########..
..##########..
..##########..
...########...
""")
BUBBLE = mask_of("""
....######....
..##########..
.############.
.############.
##############
##############
##############
##############
.############.
.############.
..##########..
....######....
""")


def shape_cell(m, oy):
    """Put a 14-wide shape into an 18x18 cell at columns 2..15 (GUI 1..7), top row oy."""
    return place(m, 18, 18, 2, oy)


# =============================================================================================== icon painter
class Gem:
    """How one design paints a gem (heart, shank, chest, bubble)."""

    def __init__(self, rim, glint=(255, 250, 240), faceted=False, rim2=None, outline=None):
        self.rim, self.glint, self.faceted, self.rim2, self.outline = rim, glint, faceted, rim2, outline

    def paint(self, m, body, sub=None, sub_body=None, glints=(), rim=None, faceted=None):
        rim = rim or self.rim
        faceted = self.faceted if faceted is None else faceted
        a = np.zeros(m.shape + (4,), np.uint8)
        if self.outline is not None:                    # an ink keyline outside the rim (drawn-alone icons)
            o = dilate(m) & ~m
            a[o] = C(self.outline, 200)
        rm = ring(m)
        inner = m & ~rm
        if sub is not None:
            rm = rm & ~sub
            inner = (m & ~rm)
        a = over(a, bevel_ring(rm, m, rim))
        b = inner & ~sub if sub is not None else inner
        a = over(a, facets(b, body, table=1.0) if faceted else shade_body(b, body))
        if sub is not None:
            a = over(a, shade_body(m & sub, sub_body))
        for (x, y) in glints:
            if 0 <= y < m.shape[0] and 0 <= x < m.shape[1] and inner[y, x]:
                a[y, x] = C(self.glint)
        return a


def half(a, side):
    """Keep the left (columns < 9) or right (>= 9) half of a cell (the shapes are centred on column 8.5)."""
    a = a.copy()
    if side == "left":
        a[:, 9:] = 0
    else:
        a[:, :9] = 0
    return a


# =============================================================================================== palettes
GOLD = [(255, 244, 200), (240, 208, 130), (198, 152, 74), (140, 100, 44), (86, 60, 28)]
SILVER = [(255, 255, 255), (220, 228, 240), (164, 174, 194), (106, 114, 134), (56, 60, 76)]
STEEL = [(232, 236, 240), (176, 182, 190), (118, 124, 134), (74, 78, 86), (40, 42, 48)]
IRON = [(176, 180, 188), (124, 128, 136), (82, 86, 94), (52, 54, 60), (28, 29, 33)]
AMETHYST = [(250, 226, 255), (214, 156, 252), (158, 96, 222), (100, 54, 160), (50, 26, 86)]
BRONZE = [(236, 196, 140), (190, 140, 84), (140, 96, 52), (96, 62, 32), (56, 36, 20)]
DULL = [(132, 112, 82), (104, 88, 64), (78, 66, 48), (56, 46, 34), (36, 30, 22)]

CRIMSON = [(236, 104, 88), (186, 40, 38), (128, 20, 24), (78, 10, 16)]
RUBY = [(255, 150, 150), (226, 54, 62), (160, 18, 34), (92, 6, 20)]
POISON = [(186, 200, 90), (124, 146, 44), (78, 94, 26), (46, 58, 16)]
WITHER = [(120, 114, 112), (72, 66, 64), (44, 40, 40), (24, 22, 22)]
ABSORB = [(255, 236, 160), (232, 190, 88), (176, 128, 46), (110, 76, 26)]
LOST = [(250, 236, 196), (226, 204, 150), (184, 156, 104), (130, 104, 66)]
MOUNT = [(236, 170, 100), (184, 108, 54), (124, 66, 32), (74, 38, 18)]
MEAT = [(232, 156, 96), (178, 90, 46), (118, 54, 26), (70, 30, 14)]
ROT = [(168, 180, 96), (114, 128, 54), (72, 82, 32), (42, 48, 18)]
BONEC = [(250, 244, 224), (214, 202, 174), (160, 148, 120), (110, 100, 80)]
ARMOR_STEEL = [(240, 242, 244), (180, 186, 194), (120, 126, 136), (72, 76, 86)]
GLASS = [(214, 236, 255), (110, 164, 226), (54, 96, 168), (28, 52, 104)]


# =============================================================================================== base design
class Design:
    name = "base"
    gem = Gem(GOLD)
    heart_shape, heart_oy = HEART, 4
    hearts = {"crimson": CRIMSON}
    xp_num, xp_outline = "F2DA9E", "120C06"
    boss_name, boss_outline = "F4E8CC", "140E08"
    socket_rim = DULL
    socket_body = [(52, 44, 38), (38, 32, 28), (28, 24, 21), (20, 17, 15)]
    blink_rim = [(255, 250, 230), (250, 236, 196), (222, 196, 140), (170, 140, 90), (110, 88, 56)]
    heart_glints = [(4, 6), (5, 6), (4, 7)]
    meat_glints = [(10, 6), (11, 7)]

    # ---- the band behind a row: 18x18, divider in cols 0-1 and 16-17 (identical), art in cols 2-15
    def band(self, kind="normal"):
        raise NotImplementedError

    def socket(self, m, kind="normal"):
        """An empty socket for shape m in the band: a recessed silhouette, rim lit bottom-right (sunken)."""
        a = np.zeros((18, 18, 4), np.uint8)
        rm = ring(m)
        rimr = self.blink_rim if kind == "blink" else self.socket_rim
        a = over(a, bevel_ring(rm, m, list(reversed(rimr))))
        a = over(a, shade_body(m & ~rm, self.socket_body))
        return a

    def gem_cell(self, m, body, **kw):
        return self.gem.paint(m, body, **kw)

    # ---- the icon sheet
    def icons(self, base):
        ic = np.asarray(base.convert("RGBA").resize((256 * S, 256 * S), Image.NEAREST)).copy()

        def put(u, v, tile):
            ic[v * S:v * S + 18, u * S:u * S + 18] = tile

        def clear(u0, v, u1):
            ic[v * S:v * S + 18, u0 * S:u1 * S] = 0

        hm = shape_cell(self.heart_shape, self.heart_oy)
        sm = shape_cell(SHANK, 3)
        bm = shape_cell(BONE, 3)
        cm = shape_cell(CHEST, 3)
        hg = [(x + 2, y + self.heart_oy) for x, y in self.heart_glints]
        mg = [(x + 2, y + 3) for x, y in self.meat_glints]
        band, bandb = self.band("normal"), self.band("blink")
        cont = over(band.copy(), self.socket(hm))
        cont_b = over(bandb.copy(), self.socket(hm, "blink"))
        for v in (0, 45):
            clear(16, v, 16 + 9 * 26)
            put(16, v, cont)
            put(25, v, cont_b)
            for margin, body in ((16, self.hearts.get("crimson", CRIMSON)), (52, POISON), (88, WITHER)):
                full = self.gem_cell(hm, body, glints=hg if margin == 16 else ())
                put(margin + 36, v, full)
                put(margin + 45, v, half(full, "left"))
                lost = self.gem_cell(hm, LOST, rim=self.blink_rim)
                put(margin + 54, v, lost)
                put(margin + 63, v, half(lost, "left"))
                ab = self.gem_cell(hm, ABSORB, glints=hg)
                put(margin + 144, v, ab)
                put(margin + 153, v, half(ab, "left"))
        # armour: drawn alone (band included), left to right
        clear(16, 9, 16 + 9 * 3)
        a_empty = over(band.copy(), self.socket(cm))
        a_full = over(band.copy(), self.gem_cell(cm, self.armor_body()))
        put(16, 9, a_empty)
        put(25, 9, over(a_empty.copy(), half(self.gem_cell(cm, self.armor_body()), "left")))
        put(34, 9, a_full)
        # mount
        clear(52, 9, 52 + 9 * 7)
        put(52, 9, cont)
        mf = self.gem_cell(hm, MOUNT)
        put(88, 9, mf)
        put(97, 9, half(mf, "right"))
        # air: alone, no band, an ink keyline
        clear(16, 18, 16 + 9 * 2)
        bub = place(BUBBLE, 18, 18, 2, 3)
        put(16, 18, Gem(self.gem.rim, outline=INK).paint(bub, GLASS, glints=[(5, 5), (6, 5), (5, 6), (6, 4)]))
        pop = np.zeros((18, 18, 4), np.uint8)
        for (x, y) in ((3, 4), (4, 4), (3, 5), (13, 4), (14, 4), (14, 5), (8, 9), (9, 9), (8, 10), (9, 10),
                       (3, 13), (3, 14), (4, 14), (14, 13), (13, 14), (14, 14)):
            pop[y, x] = C(GLASS[0])
        put(25, 18, pop)
        # food
        clear(16, 27, 16 + 9 * 13)
        f_cont = over(band.copy(), self.socket(sm))
        put(16, 27, f_cont)
        put(25, 27, over(bandb.copy(), self.socket(sm, "blink")))
        put(133, 27, over(band.copy(), self.socket(sm)))
        for u, meat in ((16, MEAT), (52, ROT)):
            full = self.gem_cell(sm, meat, sub=bm, sub_body=BONEC, glints=mg if meat is MEAT else ())
            put(u + 36, 27, full)
            put(u + 45, 27, half(full, "right"))
            lost = self.gem_cell(sm, LOST, sub=bm, sub_body=LOST, rim=self.blink_rim)
            put(u + 54, 27, lost)
            put(u + 63, 27, half(lost, "right"))
        # XP and boss strips
        for v, strip in ((64, self.xp(False)), (69, self.xp(True)), (74, self.boss(False)), (79, self.boss(True))):
            ic[v * S:(v + 5) * S, 0:182 * S] = strip
        # hook sprites
        pl = self.medallion()
        ic[PLATE[1] * S:(PLATE[1] + PLATE[3]) * S, PLATE[0] * S:(PLATE[0] + PLATE[2]) * S] = pl
        fr = self.boss_frame()
        ic[FRAME[1] * S:(FRAME[1] + FRAME[3]) * S, FRAME[0] * S:(FRAME[0] + FRAME[2]) * S] = fr
        return Image.fromarray(ic)

    def armor_body(self):
        return ARMOR_STEEL

    def widgets(self, base):
        w = np.asarray(base.convert("RGBA").resize((256 * S, 256 * S), Image.NEAREST)).copy()
        w[0:44, 0:364] = self.hotbar()
        w[44:88, 0:48] = self.selection()
        return Image.fromarray(w)

    def color_properties(self):
        return ("# Quest Forge HUD r015, design '%s' (tools/textures/qf_hud_r015.py). text.xpbar / text.boss are\n"
                "# MCPatcher's keys; here qf-content's client hook XpBarStyle reads them and the qf.* keys.\n"
                "text.xpbar=%s\nqf.xpbar.outline=%s\nqf.xpbar.plate=%d,%d,%d,%d\n"
                "text.boss=%s\nqf.boss.outline=%s\nqf.boss.frame=%d,%d,%d,%d\n"
                % ((self.name, self.xp_num, self.xp_outline) + PLATE + (self.boss_name, self.boss_outline) + FRAME))


# helpers shared by designs ---------------------------------------------------------------------------------
def hrule(a, x0, x1, y, c, al=255):
    rect(a, x0, y, x1, y + 1, c, al)


def vrule(a, x, y0, y1, c, al=255):
    rect(a, x, y0, x + 1, y1, c, al)


def vgrad(a, x0, y0, x1, y1, top, bot, al=255, al_bot=None):
    for y in range(y0, y1):
        t = (y - y0) / max(1, y1 - y0 - 1)
        alv = al if al_bot is None else int(round(al + (al_bot - al) * t))
        rect(a, x0, y, x1, y + 1, mix(top, bot, t), alv)


def diamond(a, cx, cy, r, c, al=255, c2=None):
    """A filled diamond of radius r centred between pixels (cx-0.5, cy-0.5) -> even-sized, crisp at 2x."""
    for y in range(cy - r, cy + r):
        for x in range(cx - r, cx + r):
            d = abs(x + 0.5 - cx) + abs(y + 0.5 - cy)
            if d <= r:
                col = c if (c2 is None or (x < cx and y < cy) or d <= r - 1.5) else c2
                px(a, x, y, col, al)


def disc_mask(w, h, cx, cy, rx, ry):
    yy, xx = np.mgrid[0:h, 0:w]
    return ((xx + 0.5 - cx) / rx) ** 2 + ((yy + 0.5 - cy) / ry) ** 2 <= 1.0


def frame_box(a, x0, y0, x1, y1, r, t=2, lit_tl=True):
    """A bevelled rectangular frame of thickness t from ramp r (top/left lit, bottom/right shaded)."""
    for k in range(t):
        tt = k / max(1, t - 1)
        rect(a, x0 + k, y0 + k, x1 - k, y0 + k + 1, ramp_at(r, 0.1 + 0.3 * tt if lit_tl else 0.8))
        rect(a, x0 + k, y0 + k, x0 + k + 1, y1 - k, ramp_at(r, 0.25 + 0.3 * tt if lit_tl else 0.7))
        rect(a, x0 + k, y1 - k - 1, x1 - k, y1 - k, ramp_at(r, 0.75 + 0.2 * tt if lit_tl else 0.2))
        rect(a, x1 - k - 1, y0 + k, x1 - k, y1 - k, ramp_at(r, 0.65 + 0.2 * tt if lit_tl else 0.3))


def binary(a):
    """XP strips are drawn with blending off: snap alpha to 0/255."""
    a = a.copy()
    a[..., 3] = np.where(a[..., 3] >= 128, 255, 0)
    return a


# =============================================================================================== A: gilded
class Gilded(Design):
    name = "gilded"
    gem = Gem(GOLD)
    xp_num, xp_outline = "F6DFA4", "1A1006"
    boss_name, boss_outline = "F6EBD0", "1A1006"
    PANEL = ((40, 32, 26), (18, 14, 12))

    def band(self, kind="normal"):
        a = blank(18, 18)
        vgrad(a, 0, 2, 18, 16, *self.PANEL, al=210, al_bot=225)
        rect(a, 0, 0, 18, 1, GOLD[1])
        rect(a, 0, 1, 18, 2, GOLD[3])
        rect(a, 0, 16, 18, 17, GOLD[2])
        rect(a, 0, 17, 18, 18, GOLD[4])
        if kind == "blink":
            rect(a, 0, 0, 18, 2, GOLD[0])
            rect(a, 0, 16, 18, 18, GOLD[1])
        for x in (0, 16):                                  # studs on the seams: a small gold drop top and bottom
            rect(a, x, 2, x + 2, 3, GOLD[2])
            px(a, x, 2, GOLD[1])
            rect(a, x, 15, x + 2, 16, GOLD[3])
        return a

    def hotbar(self):
        a = blank(364, 44)
        vgrad(a, 2, 5, 362, 39, (44, 36, 29), (14, 11, 9), al=195, al_bot=215)
        rect(a, 2, 2, 362, 3, INK, 150)
        rect(a, 2, 3, 362, 4, GOLD[1])
        rect(a, 2, 4, 362, 5, GOLD[3])
        rect(a, 2, 39, 362, 40, GOLD[2])
        rect(a, 2, 40, 362, 41, GOLD[4])
        rect(a, 2, 41, 362, 42, INK, 150)
        for i in range(1, 9):                              # gold pillars between slots, a diamond at each end
            x = 40 * i + 1
            for y in range(7, 37):
                al = int(80 + 120 * (abs(y - 21.5) / 15) ** 1.5)
                px(a, x, y, GOLD[2], al)
                px(a, x + 1, y, GOLD[3], al)
            diamond(a, x + 1, 6, 3, GOLD[1], c2=GOLD[2])
            diamond(a, x + 1, 38, 3, GOLD[2], c2=GOLD[3])
        for cx, sgn in ((2, -1), (362, 1)):                # end caps: a gold bar with a diamond finial
            rect(a, cx - 1 if sgn < 0 else cx - 1, 3, cx + 1, 41, GOLD[2])
            diamond(a, cx, 22, 4, GOLD[0], c2=GOLD[2])
            diamond(a, cx, 22, 2, GOLD[3])
        return a

    def selection(self):
        a = blank(48, 44)
        for k, al in ((2, 120), (3, 80), (4, 50), (5, 26)):  # inner glow
            frame_box(a, 2 + k, 2 + k, 46 - k, 44 - k, [(250, 220, 150)] * 2, t=1)
            a[2 + k:44 - k, 2 + k:46 - k][..., 3] = np.where(ring(np.ones((42 - 2 * k, 44 - 2 * k), bool)),
                                                               al, a[2 + k:44 - k, 2 + k:46 - k][..., 3])
        a[7:39, 7:41] = 0
        frame_box(a, 1, 1, 47, 44, [INK] * 5, t=1)
        frame_box(a, 2, 2, 46, 43, GOLD, t=3)
        frame_box(a, 5, 5, 43, 40, [(255, 236, 180)] * 5, t=1)
        diamond(a, 24, 3, 4, GOLD[0], c2=GOLD[2])          # diamonds over the top and under the bottom rule
        diamond(a, 24, 42, 3, GOLD[1], c2=GOLD[3])
        for (x, y) in ((2, 2), (44, 2), (2, 42), (44, 42)):  # corner studs
            rect(a, x, y, x + 2, y + 2, GOLD[0])
        return a

    def xp(self, fill):
        a = blank(364, 10)
        rect(a, 0, 1, 364, 2, INK)
        rect(a, 0, 2, 364, 3, GOLD[2])
        rect(a, 0, 3, 364, 7, (30, 24, 20))
        rect(a, 0, 3, 364, 4, (44, 36, 28))
        rect(a, 0, 7, 364, 8, GOLD[3])
        rect(a, 0, 8, 364, 9, INK)
        rect(a, 0, 1, 2, 9, GOLD[1])
        rect(a, 362, 1, 364, 9, GOLD[2])
        if fill:
            for x in range(2, 362):
                t = (x / 364) ** 0.8
                px(a, x, 3, mix((196, 156, 84), (255, 246, 196), t))
                px(a, x, 4, mix((168, 126, 60), (250, 220, 140), t))
                px(a, x, 5, mix((132, 96, 44), (226, 182, 98), t))
                px(a, x, 6, mix((96, 66, 30), (170, 124, 58), t))
        return binary(a)

    def medallion(self):
        w, h = PLATE[2] * S, PLATE[3] * S                   # 48 x 30
        a = blank(w, h)
        for side in (0, 1):                                 # clasps over the band ends
            x0 = 0 if side == 0 else w - 8
            rect(a, x0, 3, x0 + 7, 15, GOLD[3])
            rect(a, x0, 3, x0 + 7, 4, GOLD[1])
            rect(a, x0, 14, x0 + 7, 15, GOLD[4])
            rect(a, x0 + (1 if side == 0 else 0), 5, x0 + (6 if side == 0 else 6), 13, GOLD[2])
        outer = disc_mask(w, h, MX, MY + 1, 21, 14)
        a[outer] = C(INK, 235)
        rim = disc_mask(w, h, MX, MY + 1, 20, 13)
        rr = ring(rim) | ring(rim & ~ring(rim))
        a = over(a, bevel_ring(rr, rim, GOLD))
        inner = disc_mask(w, h, MX, MY + 0.5, 17.5, 10.5)
        body = shade_body(inner, [(62, 50, 38), (36, 29, 23), (24, 19, 16), (14, 11, 9)])
        a = over(a, body)
        a[ring(inner)] = C(GOLD[3])
        a[ring(rim & ~rr) & ~inner] = C(GOLD[2])
        diamond(a, MX, 1, 2, GOLD[0])
        diamond(a, MX, 28, 2, GOLD[2])
        return a

    def boss(self, fill):
        a = blank(364, 10)
        rect(a, 2, 0, 362, 1, INK, 200)
        rect(a, 2, 1, 362, 2, GOLD[1])
        rect(a, 2, 2, 362, 8, (34, 16, 16))
        rect(a, 2, 2, 362, 3, (52, 26, 24))
        rect(a, 2, 8, 362, 9, GOLD[3])
        rect(a, 2, 9, 362, 10, INK, 200)
        rect(a, 0, 0, 2, 10, GOLD[2])
        rect(a, 362, 0, 364, 10, GOLD[2])
        if fill:
            rows = [(232, 96, 78), (196, 48, 42), (164, 30, 30), (136, 22, 24), (104, 16, 20), (74, 10, 14)]
            for i, c in enumerate(rows):
                rect(a, 2, 2 + i, 362, 3 + i, c)
        return a

    def boss_frame(self):
        w, h = FRAME[2] * S, FRAME[3] * S                  # 428 x 30; bar at cols 32..395, rows 10..19
        a = blank(w, h)
        for side in (0, 1):
            def X(x):
                return x if side == 0 else w - 1 - x
            # a long gold blade from the bar end to a diamond tip, a curl above and below
            for x in range(4, 34):
                t = (x - 4) / 30
                half_h = 1 + int(round(3 * t))
                for y in range(15 - half_h, 15 + half_h):
                    px(a, X(x), y, ramp_at(GOLD, 0.15 + 0.6 * abs(y + 0.5 - 15) / max(1, half_h)))
            for y in range(13, 17):
                for x in range(0, 6):
                    if abs(x - 3.5) + abs(y + 0.5 - 15) * 1.5 <= 3.5:
                        px(a, X(x), y, GOLD[0])
            for (x, y) in ((22, 6), (23, 6), (24, 7), (25, 8), (21, 7), (20, 8), (19, 9), (26, 9),
                           (22, 23), (23, 23), (24, 22), (25, 21), (21, 22), (20, 21), (19, 20), (26, 20)):
                px(a, X(x), y, GOLD[1] if y < 15 else GOLD[2])
            px(a, X(22), 7, INK, 180)
            px(a, X(23), 22, INK, 180)
            # end plate over the bar's end
            rect(a, min(X(30), X(35)), 8, max(X(30), X(35)) + 1, 22, GOLD[3])
            rect(a, min(X(31), X(34)), 9, max(X(31), X(34)) + 1, 21, GOLD[1])
            rect(a, min(X(32), X(33)), 10, max(X(32), X(33)) + 1, 20, GOLD[2])
            diamond(a, X(33) + (1 if side == 0 else 0), 15, 2, GOLD[0])
        # hairlines along the bar, fading toward the centre (row 8 above, row 21 below)
        for x in range(36, w - 36):
            d = abs(x - w / 2) / (w / 2 - 36)
            al = int(255 * min(1, max(0, (d - 0.15) / 0.5)))
            if al > 20:
                px(a, x, 8, GOLD[2], al)
                px(a, x, 21, GOLD[3], al)
        return a


# =============================================================================================== B: cloisonne
LAPIS = [(70, 112, 200), (44, 76, 160), (28, 50, 116), (16, 30, 76)]
TURQ = [(200, 255, 246), (96, 214, 206), (40, 150, 156), (20, 92, 100)]
ENAMEL_RED = [(250, 120, 108), (210, 46, 50), (166, 26, 36), (110, 14, 24)]


class Cloisonne(Design):
    name = "cloisonne"
    gem = Gem(GOLD)
    hearts = {"crimson": ENAMEL_RED}
    socket_rim = [(176, 140, 80), (150, 116, 62), (120, 92, 48), (92, 70, 36), (60, 46, 24)]
    socket_body = [(30, 50, 104), (24, 40, 88), (18, 32, 72), (14, 24, 58)]
    xp_num, xp_outline = "FFE7A8", "0A1230"
    boss_name, boss_outline = "FFF0CC", "0A1230"

    def band(self, kind="normal"):
        a = blank(18, 18)
        vgrad(a, 0, 2, 18, 16, LAPIS[1], LAPIS[3])
        hi = GOLD[0] if kind == "blink" else GOLD[1]
        rect(a, 0, 0, 18, 1, INK, 220)
        rect(a, 0, 1, 18, 2, hi)
        rect(a, 0, 16, 18, 17, GOLD[3])
        rect(a, 0, 17, 18, 18, INK, 220)
        for x in (0, 16):                                   # gold cloison walls (identical in cols 0-1 and 16-17)
            rect(a, x, 1, x + 1, 17, GOLD[2])
            rect(a, x + 1, 1, x + 2, 17, GOLD[1] if kind != "blink" else GOLD[0])
        for (x, y) in ((2, 2), (15, 2), (2, 15), (15, 15)):  # chamfered cell corners
            px(a, x, y, GOLD[2])
        for y in range(3, 15):                              # a lighter enamel sheen on the upper rows
            pass
        rect(a, 2, 2, 16, 3, LAPIS[0], 255)
        return a

    def hotbar(self):
        a = blank(364, 44)
        rect(a, 0, 2, 364, 42, LAPIS[2])
        vgrad(a, 0, 2, 364, 42, LAPIS[1], LAPIS[3])
        rect(a, 0, 1, 364, 2, INK, 200)
        rect(a, 0, 2, 364, 3, GOLD[1])
        rect(a, 0, 41, 364, 42, GOLD[3])
        rect(a, 0, 42, 364, 43, INK, 200)
        rect(a, 0, 2, 2, 42, GOLD[2])
        rect(a, 362, 2, 364, 42, GOLD[3])
        for i in range(9):
            x0, y0, x1, y1 = 40 * i + 3, 4, 40 * i + 41, 40
            win = np.zeros((44, 364), bool)
            win[y0:y1, x0:x1] = True
            for k in range(3):                              # chamfer the corners (octagon)
                win[y0 + k, x0:x0 + 3 - k] = win[y0 + k, x1 - 3 + k:x1] = False
                win[y1 - 1 - k, x0:x0 + 3 - k] = win[y1 - 1 - k, x1 - 3 + k:x1] = False
            rimm = ring(win, diag=True)
            a[win] = C((10, 16, 36), 200)
            a = over(a, bevel_ring(rimm, win, GOLD))
            inner = win & ~rimm
            a[ring(inner, diag=True)] = C((8, 12, 28), 200)
        for i in range(10):                                 # turquoise jewels at the junctions
            cx = 40 * i + 2 if 0 < i < 9 else (2 if i == 0 else 362)
            if 0 < i < 9:
                for y0 in (1, 39):
                    rect(a, cx - 2, y0, cx + 2, y0 + 4, GOLD[3])
                    rect(a, cx - 1, y0 + 1, cx + 1, y0 + 3, TURQ[1])
                    px(a, cx - 1, y0 + 1, TURQ[0])
        return a

    def selection(self):
        a = blank(48, 44)
        win = np.zeros((44, 48), bool)
        win[2:44, 2:46] = True
        for k in range(4):
            win[2 + k, 2:6 - k] = win[2 + k, 42 + k:46] = False
            win[43 - k, 2:6 - k] = win[43 - k, 42 + k:46] = False
        r1 = ring(win, diag=True)
        r2 = ring(win & ~r1, diag=True)
        r3 = ring(win & ~r1 & ~r2, diag=True)
        a[r1] = C(INK, 220)
        a = over(a, bevel_ring(r2, win, GOLD))
        a[r3] = C(TURQ[1])
        r4 = ring(win & ~r1 & ~r2 & ~r3, diag=True)
        a[r4] = C(TURQ[0], 90)
        for (x0, y0) in ((21, 0), (21, 39)):               # a turquoise drop in a gold setting, top and bottom
            rect(a, x0, y0, x0 + 6, y0 + 5, GOLD[3])
            rect(a, x0 + 1, y0 + 1, x0 + 5, y0 + 4, TURQ[2])
            rect(a, x0 + 1, y0 + 1, x0 + 3, y0 + 3, TURQ[0])
        return a

    def xp(self, fill):
        a = blank(364, 10)
        rect(a, 0, 1, 364, 2, INK)
        rect(a, 0, 2, 364, 3, GOLD[1])
        rect(a, 0, 3, 364, 7, LAPIS[3])
        rect(a, 0, 3, 364, 4, LAPIS[2])
        rect(a, 0, 7, 364, 8, GOLD[3])
        rect(a, 0, 8, 364, 9, INK)
        if fill:
            for x in range(0, 364):
                t = (x / 364) ** 0.9
                px(a, x, 3, mix((150, 230, 220), (230, 255, 250), t))
                px(a, x, 4, mix(TURQ[2], TURQ[1], t))
                px(a, x, 5, mix(TURQ[3], TURQ[2], t))
                px(a, x, 6, mix((14, 64, 72), TURQ[3], t))
        for k in range(1, 10):                              # gold cloisons every tenth
            x = int(round(k * 36.4))
            rect(a, x, 2, x + 1, 8, GOLD[2])
            rect(a, x + 1, 2, x + 2, 8, GOLD[1])
        rect(a, 0, 1, 2, 9, GOLD[2])
        rect(a, 362, 1, 364, 9, GOLD[3])
        return binary(a)

    def medallion(self):
        w, h = PLATE[2] * S, PLATE[3] * S
        a = blank(w, h)
        outer = disc_mask(w, h, MX, MY + 1, 22, 14)
        a[outer] = C(INK, 230)
        r1 = disc_mask(w, h, MX, MY + 1, 21, 13)
        a = over(a, bevel_ring(ring(r1) | ring(r1 & ~ring(r1)), r1, GOLD))
        r2 = disc_mask(w, h, MX, MY + 1, 19, 11)
        a[r2] = C(LAPIS[2])
        a = over(a, shade_body(r2, LAPIS))
        r3 = disc_mask(w, h, MX, MY + 0.5, 17.5, 9.5)
        a[ring(r2) & ~r3] = C(GOLD[2])
        a[ring(r3)] = C(GOLD[3])
        body = r3 & ~ring(r3)
        a = over(a, shade_body(body, [(34, 58, 124), (22, 40, 96), (16, 28, 72), (10, 18, 50)]))
        for (x, y) in ((MX, 1), (MX, 28), (MX - 20, MY + 1), (MX + 21, MY + 1)):  # turquoise studs N, S, W, E
            rect(a, x - 1, y - 1, x + 1, y + 1, TURQ[1])
            px(a, x - 1, y - 1, TURQ[0])
        return a

    def boss(self, fill):
        a = blank(364, 10)
        rect(a, 0, 0, 364, 1, INK, 220)
        rect(a, 0, 1, 364, 2, GOLD[1])
        rect(a, 0, 2, 364, 8, LAPIS[3])
        rect(a, 0, 8, 364, 9, GOLD[3])
        rect(a, 0, 9, 364, 10, INK, 220)
        if fill:
            rows = [ENAMEL_RED[0], ENAMEL_RED[1], ENAMEL_RED[1], ENAMEL_RED[2], ENAMEL_RED[2], ENAMEL_RED[3]]
            for i, c in enumerate(rows):
                rect(a, 0, 2 + i, 364, 3 + i, c)
        for k in range(1, 20):                              # gold wires every twentieth
            x = int(round(k * 364 / 20))
            rect(a, x, 2, x + 1, 8, GOLD[2])
        rect(a, 0, 0, 2, 10, GOLD[2])
        rect(a, 362, 0, 364, 10, GOLD[3])
        return a

    def boss_frame(self):
        w, h = FRAME[2] * S, FRAME[3] * S
        a = blank(w, h)
        for side in (0, 1):
            def X(x):
                return x if side == 0 else w - 1 - x
            # a lapis lozenge cap in a gold wire, a round turquoise jewel at its centre
            for y in range(2, 28):
                for x in range(6, 36):
                    d = abs(x + 0.5 - 21) / 15 + abs(y + 0.5 - 15) / 13
                    if d <= 1:
                        edge = d > 0.84
                        px(a, X(x), y, (GOLD[3] if d > 0.93 else GOLD[1]) if edge else
                           ramp_at(LAPIS, 0.2 + 0.6 * (y - 2) / 26))
            jm = disc_mask(9, 9, 4.5, 4.5, 4.5, 4.5)
            jr = ring(jm)
            for y in range(9):
                for x in range(9):
                    if jm[y, x]:
                        c = GOLD[2] if jr[y, x] else ramp_at(TURQ, 0.2 + 0.6 * (x + y) / 16)
                        px(a, X(17 + x), 11 + y, c)
            px(a, X(19), 13, TURQ[0])
            px(a, X(20), 13, TURQ[0])
            for x in range(0, 6):                           # a gold point beyond the cap
                px(a, X(x), 14, GOLD[1])
                px(a, X(x), 15, GOLD[3])
        return a

    def armor_body(self):
        return [(250, 250, 255), (196, 204, 222), (134, 144, 170), (80, 88, 116)]


# =============================================================================================== C: ironbound
EMBER = [(255, 236, 170), (255, 170, 70), (220, 96, 30), (140, 40, 16)]


class Ironbound(Design):
    name = "ironbound"
    gem = Gem(STEEL, faceted=True)
    heart_shape, heart_oy = HEART_GEM, 4
    hearts = {"crimson": RUBY}
    heart_glints = [(3, 3), (4, 3)]
    socket_rim = IRON
    socket_body = [(30, 30, 34), (22, 22, 26), (16, 16, 19), (10, 10, 12)]
    xp_num, xp_outline = "FFE2A6", "0A0806"
    boss_name, boss_outline = "FFF2DC", "0A0806"
    PLATE_C = ((70, 72, 80), (42, 44, 50))

    def plate(self, w, h, seed=7):
        rng = np.random.default_rng(seed)
        a = blank(w, h)
        for y in range(h):
            t = y / max(1, h - 1)
            c = mix(self.PLATE_C[0], self.PLATE_C[1], t)
            for x in range(w):
                n = rng.integers(-5, 6)
                px(a, x, y, (c[0] + n, c[1] + n, c[2] + n))
        return a

    def rivet(self, a, x, y):
        px(a, x, y, (214, 218, 224))
        px(a, x + 1, y, (150, 154, 162))
        px(a, x, y + 1, (120, 124, 132))
        px(a, x + 1, y + 1, (58, 60, 66))
        px(a, x + 1, y + 2, (20, 20, 24), 160)
        px(a, x + 2, y + 1, (20, 20, 24), 160)

    def band(self, kind="normal"):
        a = self.plate(18, 18)
        rect(a, 0, 0, 18, 1, INK)
        rect(a, 0, 1, 18, 2, IRON[0] if kind != "blink" else (255, 190, 110))
        rect(a, 0, 2, 18, 3, IRON[2])
        rect(a, 0, 15, 18, 16, IRON[3])
        rect(a, 0, 16, 18, 17, IRON[4])
        rect(a, 0, 17, 18, 18, INK)
        for x in (0, 16):                                   # a seam with a rivet top and bottom
            rect(a, x, 3, x + 1, 15, (26, 27, 30))
            rect(a, x + 1, 3, x + 2, 15, (96, 100, 108))
            self.rivet(a, x, 3)
            self.rivet(a, x, 12)
        return a

    def hotbar(self):
        a = self.plate(364, 44, seed=3)
        a[0:2] = 0
        a[42:44] = 0
        rect(a, 0, 2, 364, 3, INK)
        rect(a, 0, 3, 364, 4, IRON[0])
        rect(a, 0, 4, 364, 5, IRON[1])
        rect(a, 0, 39, 364, 40, IRON[3])
        rect(a, 0, 40, 364, 41, IRON[4])
        rect(a, 0, 41, 364, 42, INK)
        rect(a, 0, 2, 1, 42, INK)
        rect(a, 1, 3, 2, 41, IRON[1])
        rect(a, 363, 2, 364, 42, INK)
        rect(a, 362, 3, 363, 41, IRON[3])
        for i in range(9):                                  # sunken windows: shadow top-left, light bottom-right
            x0, y0, x1, y1 = 40 * i + 4, 6, 40 * i + 40, 38
            rect(a, x0, y0, x1, y1, (12, 12, 14), 215)
            rect(a, x0, y0, x1, y0 + 1, (0, 0, 0), 255)
            rect(a, x0, y0 + 1, x1, y0 + 2, (0, 0, 0), 120)
            rect(a, x0, y0, x0 + 1, y1, (0, 0, 0), 255)
            rect(a, x0 + 1, y0, x0 + 2, y1, (0, 0, 0), 110)
            rect(a, x0, y1 - 1, x1, y1, IRON[1])
            rect(a, x1 - 1, y0, x1, y1, IRON[2])
        for i in range(10):                                 # rivets on the posts
            x = 40 * i + 1 if i < 9 else 360
            self.rivet(a, x, 5 if i else 5)
            self.rivet(a, x, 35)
        return a

    def selection(self):
        a = blank(48, 44)
        frame_box(a, 2, 2, 46, 44, IRON, t=2)
        rect(a, 1, 1, 47, 2, INK)
        rect(a, 1, 1, 2, 44, INK)
        rect(a, 46, 1, 47, 44, INK)
        frame_box(a, 4, 4, 44, 42, [EMBER[0], EMBER[1], EMBER[1], EMBER[2], EMBER[3]], t=2)
        for k, al in ((6, 110), (7, 60), (8, 30)):
            m = np.zeros((44, 48), bool)
            m[k:44 - k, k:48 - k] = True
            a[ring(m)] = C(EMBER[1], al)
        for (x, y) in ((2, 2), (43, 2), (2, 39), (43, 39)):
            self.rivet(a, x, y)
        return a

    def xp(self, fill):
        a = blank(364, 10)
        rect(a, 0, 0, 364, 1, INK)
        rect(a, 0, 1, 364, 2, IRON[3])
        rect(a, 0, 2, 364, 3, (0, 0, 0))
        rect(a, 0, 3, 364, 7, (20, 16, 14))
        rect(a, 0, 7, 364, 8, IRON[1])
        rect(a, 0, 8, 364, 9, IRON[3])
        rect(a, 0, 9, 364, 10, INK)
        if fill:
            for x in range(0, 364):
                t = (x / 364) ** 1.2
                px(a, x, 2, mix((90, 20, 8), (200, 90, 30), t))
                px(a, x, 3, mix((200, 70, 20), (255, 236, 170), t))
                px(a, x, 4, mix((170, 50, 16), (255, 180, 80), t))
                px(a, x, 5, mix((130, 34, 12), (240, 130, 40), t))
                px(a, x, 6, mix((86, 20, 8), (180, 70, 20), t))
        for x in (0, 362):
            rect(a, x, 0, x + 2, 10, IRON[2])
        return binary(a)

    def medallion(self):
        w, h = PLATE[2] * S, PLATE[3] * S
        a = blank(w, h)
        hexm = np.zeros((h, w), bool)
        for y in range(h):
            for x in range(w):
                dy = abs(y + 0.5 - 14.5)
                reach = 23 - max(0, dy - 6) * 1.2
                hexm[y, x] = dy <= 14.5 and abs(x + 0.5 - MX) <= reach
        a[hexm] = C(INK)
        nut = hexm & ~ring(hexm, diag=True)
        a = over(a, shade_body(nut, [IRON[0], IRON[1], IRON[2], IRON[3]]))
        a = over(a, bevel_ring(ring(nut), nut, IRON))
        hole = np.zeros((h, w), bool)
        hole[2:24, MX - 17:MX + 17] = True
        for k in range(4):                                  # chamfered corners
            hole[2 + k, MX - 17:MX - 13 - k] = False
            hole[2 + k, MX + 13 + k:MX + 17] = False
            hole[23 - k, MX - 17:MX - 13 - k] = False
            hole[23 - k, MX + 13 + k:MX + 17] = False
        rm = ring(hole, diag=True)
        a[hole] = C((18, 13, 11))
        a[rm] = C(EMBER[2])
        top = np.zeros_like(hole)
        top[:3] = True
        a[rm & top] = C(EMBER[3])
        a[ring(hole & ~rm, diag=True)] = C((70, 24, 10))
        for (x, y) in ((MX - 21, 12), (MX + 19, 12)):
            self.rivet(a, x, y)
        return a

    def boss(self, fill):
        a = blank(364, 10)
        rect(a, 0, 0, 364, 1, INK)
        rect(a, 0, 1, 364, 2, IRON[3])
        rect(a, 0, 2, 364, 8, (24, 12, 10))
        rect(a, 0, 2, 364, 3, (0, 0, 0))
        rect(a, 0, 8, 364, 9, IRON[1])
        rect(a, 0, 9, 364, 10, INK)
        if fill:
            rows = [(255, 120, 90), (226, 52, 40), (190, 30, 26), (150, 20, 20), (110, 14, 14), (70, 8, 10)]
            for i, c in enumerate(rows):
                rect(a, 0, 2 + i, 364, 3 + i, c)
        return a

    def boss_frame(self):
        w, h = FRAME[2] * S, FRAME[3] * S
        a = blank(w, h)
        for side in (0, 1):
            def X(x):
                return x if side == 0 else w - 1 - x
            x0, x1 = (8, 38) if side == 0 else (w - 38, w - 8)
            pl = self.plate(30, 26, seed=11 + side)
            a = over(a, pl, x0, 2)
            frame_box(a, x0, 2, x1, 28, IRON, t=2)
            rect(a, x0 - 1, 1, x1 + 1, 2, INK)
            rect(a, x0 - 1, 28, x1 + 1, 29, INK)
            rect(a, x0 - 1, 1, x0, 29, INK)
            rect(a, x1, 1, x1 + 1, 29, INK)
            self.rivet(a, x0 + 4, 5)
            self.rivet(a, x0 + 4, 22)
            self.rivet(a, x1 - 7, 5)
            self.rivet(a, x1 - 7, 22)
            # a spike outward
            for x in range(0, 8):
                hh = (8 - x) / 8 * 4
                for y in range(int(15 - hh), int(15 + hh) + 1):
                    px(a, X(x), y, IRON[1] if y < 15 else IRON[3])
            # an ember slot across the plate in line with the bar
            rect(a, min(X(14), X(32)), 13, max(X(14), X(32)) + 1, 17, (20, 10, 8))
            rect(a, min(X(15), X(31)), 14, max(X(15), X(31)) + 1, 16, EMBER[2])
            rect(a, min(X(17), X(29)), 14, max(X(17), X(29)) + 1, 15, EMBER[1])
        # a riveted rail above and below the bar
        rect(a, 38, 8, w - 38, 9, INK)
        rect(a, 38, 21, w - 38, 22, INK)
        return a

    def armor_body(self):
        return [(236, 238, 242), (168, 174, 184), (110, 116, 126), (64, 68, 78)]


# =============================================================================================== D: moonsilver
NAVY = ((34, 42, 82), (12, 16, 36))
MOON_RED = [(250, 130, 140), (204, 44, 66), (146, 22, 44), (86, 10, 30)]


class Moonsilver(Design):
    name = "moonsilver"
    gem = Gem(SILVER)
    hearts = {"crimson": MOON_RED}
    heart_oy = 5
    socket_rim = [(150, 160, 186), (116, 126, 152), (88, 96, 122), (60, 66, 92), (38, 42, 64)]
    socket_body = [(30, 36, 70), (24, 28, 58), (18, 22, 46), (12, 14, 34)]
    xp_num, xp_outline = "EAF2FF", "0A0E22"
    boss_name, boss_outline = "EEF4FF", "0A0E22"

    @staticmethod
    def arch_y(x):
        """Top edge of the arch over a cell column x (0..17): pillars at 0-1 / 16-17, apex at 8.5."""
        d = abs(x + 0.5 - 9) / 7.5                           # 0 at the apex, 1 at the pillars
        return int(round(1 + 3.2 * d ** 2))

    def band(self, kind="normal"):
        a = blank(18, 18)
        line = SILVER[0] if kind == "blink" else SILVER[1]
        for x in range(18):
            y0 = self.arch_y(x) if 2 <= x <= 15 else 0
            vgrad(a, x, y0 + 1, x + 1, 16, NAVY[0], NAVY[1], al=200, al_bot=225)
            if 2 <= x <= 15:
                px(a, x, y0, line)
                px(a, x, y0 - 1, INK, 150)
                px(a, x, y0 + 1, SILVER[3])
        for x in (0, 16):                                   # slender pillars with a bead on top
            rect(a, x, 2, x + 1, 16, SILVER[2])
            rect(a, x + 1, 2, x + 2, 16, SILVER[3])
            rect(a, x, 0, x + 2, 2, SILVER[0] if kind == "blink" else SILVER[1])
        rect(a, 0, 16, 18, 17, SILVER[2])
        rect(a, 0, 17, 18, 18, INK, 200)
        return a

    def hotbar(self):
        a = blank(364, 44)
        for i in range(9):
            x0 = 40 * i + 2
            for x in range(x0, x0 + 40):
                lx = x - x0
                d = abs(lx + 0.5 - 20) / 18.5
                top = int(round(4 + 7 * (1 - math.sqrt(max(0, 1 - d)))))   # a pointed (gothic) arch
                vgrad(a, x, top + 1, x + 1, 40, NAVY[0], NAVY[1], al=200, al_bot=225)
                if 1 <= lx <= 38:
                    px(a, x, top, SILVER[1])
                    px(a, x, top - 1, INK, 140)
                    px(a, x, top + 1, SILVER[3], 200)
            # apex finial
            rect(a, x0 + 19, 1, x0 + 21, 4, SILVER[0])
        for i in range(10):                                  # pillars
            x = 40 * i + 1
            rect(a, x, 8, x + 1, 40, SILVER[1])
            rect(a, x + 1, 8, x + 2, 40, SILVER[3])
            rect(a, x - 1, 6, x + 3, 8, SILVER[0])
        rect(a, 0, 40, 364, 41, SILVER[1])
        rect(a, 0, 41, 364, 42, SILVER[3])
        rect(a, 0, 42, 364, 43, INK, 160)
        return a

    def selection(self):
        a = blank(48, 44)
        for x in range(2, 46):
            d = abs(x + 0.5 - 24) / 21.5
            top = int(round(5 + 8 * (1 - math.sqrt(max(0, 1 - d)))))
            px(a, x, top - 1, INK, 180)
            px(a, x, top, SILVER[0])
            px(a, x, top + 1, SILVER[0])
            px(a, x, top + 2, SILVER[2])
            for k, al in ((3, 130), (4, 80), (5, 40)):
                px(a, x, top + k, (200, 220, 255), al)
        for x in (1, 44):
            rect(a, x, 12, x + 3, 44, SILVER[0] if x == 1 else SILVER[1])
            rect(a, x + (2 if x == 1 else 0), 12, x + (3 if x == 1 else 1), 44, SILVER[2])
            for k, al in ((3, 130), (4, 80), (5, 40)):
                xx = x + k if x == 1 else x - k + 2
                rect(a, xx, 14, xx + 1, 41, (200, 220, 255), al)
        rect(a, 1, 41, 47, 44, SILVER[1])
        rect(a, 1, 41, 47, 42, SILVER[0])
        # a crescent moon over the apex
        cm = disc_mask(10, 8, 5, 4, 4, 4) & ~disc_mask(10, 8, 6.6, 3.2, 3.6, 3.6)
        for y, x in zip(*np.nonzero(cm)):
            px(a, 19 + x, y - 1, SILVER[0])
        return a

    def xp(self, fill):
        a = blank(364, 10)
        rect(a, 0, 1, 364, 2, INK)
        rect(a, 0, 2, 364, 3, SILVER[1])
        rect(a, 0, 3, 364, 7, (14, 18, 40))
        rect(a, 0, 7, 364, 8, SILVER[3])
        rect(a, 0, 8, 364, 9, INK)
        if fill:
            for x in range(0, 364):
                t = (x / 364) ** 0.8
                px(a, x, 3, mix((150, 176, 230), (250, 252, 255), t))
                px(a, x, 4, mix((100, 132, 200), (214, 230, 255), t))
                px(a, x, 5, mix((70, 96, 168), (170, 200, 250), t))
                px(a, x, 6, mix((44, 60, 120), (110, 140, 210), t))
        for x in (0, 362):
            rect(a, x, 1, x + 2, 9, SILVER[1])
        return binary(a)

    def medallion(self):
        w, h = PLATE[2] * S, PLATE[3] * S
        a = blank(w, h)
        outer = disc_mask(w, h, MX, MY + 1, 18.5, 14.5)
        a[outer] = C(INK, 230)
        r1 = disc_mask(w, h, MX, MY + 1, 17.5, 13.5)
        a = over(a, bevel_ring(ring(r1) | ring(r1 & ~ring(r1)), r1, SILVER))
        body = disc_mask(w, h, MX, MY + 1, 15.5, 11.5)
        a = over(a, shade_body(body, [(44, 54, 104), (26, 32, 68), (16, 20, 46), (10, 12, 30)]))
        cres = body & ~disc_mask(w, h, MX + 2.5, MY + 0.5, 15.5, 11.5)
        a[cres] = C((176, 196, 240))                        # moonlight on the left inside edge
        a[cres & ~dilate(~body)] = C((120, 140, 200))
        for cx, cy, r in ((3, 21, 3), (47, 21, 3)):         # four-point stars either side, on the bar
            for k in range(-r, r + 1):
                px(a, cx + k, cy, SILVER[0] if abs(k) < 2 else SILVER[2])
                px(a, cx, cy + k, SILVER[0] if abs(k) < 2 else SILVER[2])
        return a

    def boss(self, fill):
        a = blank(364, 10)
        rect(a, 0, 0, 364, 1, INK, 200)
        rect(a, 0, 1, 364, 2, SILVER[1])
        rect(a, 0, 2, 364, 8, (16, 18, 40))
        rect(a, 0, 8, 364, 9, SILVER[3])
        rect(a, 0, 9, 364, 10, INK, 200)
        if fill:
            rows = [MOON_RED[0], MOON_RED[1], MOON_RED[1], MOON_RED[2], MOON_RED[2], MOON_RED[3]]
            for i, c in enumerate(rows):
                rect(a, 0, 2 + i, 364, 3 + i, c)
        rect(a, 0, 0, 2, 10, SILVER[1])
        rect(a, 362, 0, 364, 10, SILVER[2])
        return a

    def boss_frame(self):
        w, h = FRAME[2] * S, FRAME[3] * S
        a = blank(w, h)
        for side in (0, 1):
            def X(x):
                return x if side == 0 else w - 1 - x
            # a crescent moon opening outward, at each end
            big = disc_mask(30, 30, 15, 15, 13.5, 13.5)
            cut = disc_mask(30, 30, 9.5, 15, 11.5, 11.5)
            cm = big & ~cut
            sh = shade_body(cm, [SILVER[0], SILVER[1], SILVER[2], SILVER[3]])
            for y, x in zip(*np.nonzero(cm)):
                a[y, X(6 + x)] = sh[y, x]
            for y, x in zip(*np.nonzero(dilate(cm) & ~cm)):
                if a[y, X(6 + x)][3] == 0:
                    a[y, X(6 + x)] = C(INK, 170)
            # silver arcs above and below the bar, from the moons inward
            for x in range(34, 110):
                t = (x - 34) / 76
                al = int(255 * (1 - t) ** 0.8)
                yb = 8 - int(round(2 * t))
                px(a, X(x), yb, SILVER[1], al)
                px(a, X(x), 29 - yb, SILVER[2], al)
            # stars
            for (sx, sy) in ((40, 3), (52, 5)):
                px(a, X(sx), sy, SILVER[0])
                px(a, X(sx) + 1, sy, SILVER[2])
                px(a, X(sx) - 1, sy, SILVER[2])
                px(a, X(sx), sy - 1, SILVER[2])
                px(a, X(sx), sy + 1, SILVER[2])
        return a

    def armor_body(self):
        return [(250, 252, 255), (200, 210, 230), (140, 152, 182), (84, 94, 126)]


# =============================================================================================== E: obsidian
OBS = ((30, 24, 42), (8, 6, 14))
CRYSTAL = [(255, 170, 200), (236, 60, 100), (170, 24, 64), (96, 8, 40)]


class Obsidian(Design):
    name = "obsidian"
    gem = Gem(AMETHYST, faceted=True)
    heart_shape, heart_oy = HEART_GEM, 4
    hearts = {"crimson": CRYSTAL}
    heart_glints = [(3, 3), (4, 3), (3, 4)]
    socket_rim = [(120, 84, 160), (92, 62, 128), (66, 44, 96), (46, 30, 70), (28, 18, 44)]
    socket_body = [(30, 22, 44), (22, 16, 34), (16, 12, 26), (10, 8, 18)]
    xp_num, xp_outline = "F4DCFF", "12061E"
    boss_name, boss_outline = "F8E8FF", "12061E"

    def band(self, kind="normal"):
        a = blank(18, 18)
        vgrad(a, 0, 2, 18, 16, OBS[0], OBS[1], al=225, al_bot=235)
        glow = AMETHYST[0] if kind == "blink" else AMETHYST[1]
        rect(a, 0, 0, 18, 1, AMETHYST[4], 220)
        rect(a, 0, 1, 18, 2, glow)
        rect(a, 0, 2, 18, 3, AMETHYST[3], 200)
        rect(a, 0, 15, 18, 16, AMETHYST[3], 200)
        rect(a, 0, 16, 18, 17, AMETHYST[2])
        rect(a, 0, 17, 18, 18, AMETHYST[4], 220)
        for x in (0, 16):                                   # angled seams: a glowing chevron
            for y in range(3, 15):
                d = abs(y + 0.5 - 9)
                xx = x + (1 if d < 3 else 0)
                px(a, xx, y, AMETHYST[2], 200)
        return a

    def hotbar(self):
        a = blank(364, 44)
        for i in range(9):
            x0, y0, x1, y1 = 40 * i + 3, 3, 40 * i + 41, 41
            win = np.zeros((44, 364), bool)
            win[y0:y1, x0:x1] = True
            for k in range(6):                              # chamfer two opposite corners: a slanted cell
                win[y0 + k, x0:x0 + 6 - k] = False
                win[y1 - 1 - k, x1 - 6 + k:x1] = False
            for k in range(2):
                win[y0 + k, x1 - 2 + k:x1] = False
                win[y1 - 1 - k, x0:x0 + 2 - k] = False
            r1 = ring(win, diag=True)
            r2 = ring(win & ~r1, diag=True)
            inner = win & ~r1 & ~r2
            ys = np.nonzero(inner)[0]
            for y, x in zip(*np.nonzero(inner)):
                t = (y - 5) / 34
                a[y, x] = C(mix(OBS[0], OBS[1], t), 215)
            a[r1] = C(AMETHYST[4], 230)
            a = over(a, bevel_ring(r2, win & ~r1, AMETHYST))
            for (gx, gy) in ((x0 + 3, y0 + 7), (x1 - 4, y1 - 8)):   # small amethyst points at the cut corners
                rect(a, gx - 1, gy - 1, gx + 1, gy + 1, AMETHYST[0])
        for i in range(1, 9):                               # chevrons between cells
            cx = 40 * i + 2
            for k in range(3):
                px(a, cx - 1 + (k % 2), 20 + k, AMETHYST[1])
                px(a, cx - 1 + (k % 2), 24 - k, AMETHYST[1])
        return a

    def selection(self):
        a = blank(48, 44)
        win = np.zeros((44, 48), bool)
        win[2:44, 2:46] = True
        for k in range(7):
            win[2 + k, 2:9 - k] = False
            win[43 - k, 39 + k:46] = False
        r1 = ring(win, diag=True)
        r2 = ring(win & ~r1, diag=True)
        r3 = ring(win & ~r1 & ~r2, diag=True)
        r4 = ring(win & ~r1 & ~r2 & ~r3, diag=True)
        a[r1] = C(AMETHYST[4])
        a[r2] = C(AMETHYST[0])
        a[r3] = C(AMETHYST[1])
        a[r4] = C(AMETHYST[1], 120)
        a[ring(win & ~r1 & ~r2 & ~r3 & ~r4, diag=True)] = C(AMETHYST[1], 55)
        for k in range(4):                                  # chevrons pointing in, above and below
            px(a, 22 + k, k, AMETHYST[0])
            px(a, 25 - k, k, AMETHYST[0])
            px(a, 22 + k, 43 - k, AMETHYST[0])
            px(a, 25 - k, 43 - k, AMETHYST[0])
        return a

    def xp(self, fill):
        a = blank(364, 10)
        rect(a, 0, 1, 364, 2, AMETHYST[4])
        rect(a, 0, 2, 364, 3, AMETHYST[2])
        rect(a, 0, 3, 364, 7, (16, 10, 24))
        rect(a, 0, 7, 364, 8, AMETHYST[3])
        rect(a, 0, 8, 364, 9, AMETHYST[4])
        if fill:
            for x in range(0, 364):
                t = (x / 364) ** 0.8
                px(a, x, 3, mix((170, 110, 230), (255, 236, 255), t))
                px(a, x, 4, mix((130, 70, 200), (236, 170, 255), t))
                px(a, x, 5, mix((96, 46, 164), (196, 120, 246), t))
                px(a, x, 6, mix((62, 28, 112), (130, 70, 196), t))
        for x in (0, 362):
            rect(a, x, 1, x + 2, 9, AMETHYST[1])
        return binary(a)

    def medallion(self):
        w, h = PLATE[2] * S, PLATE[3] * S
        a = blank(w, h)
        m = np.zeros((h, w), bool)
        for y in range(h):
            for x in range(w):
                dx, dy = abs(x + 0.5 - MX), abs(y + 0.5 - 14.5)
                m[y, x] = dx <= 22 and dy <= 14.5 and dx + dy * 1.1 <= 28
        a[m] = C(AMETHYST[4])
        r1 = m & ~ring(m, diag=True)
        a[ring(r1, diag=True)] = C(AMETHYST[1])
        r2 = r1 & ~ring(r1, diag=True)
        a[ring(r2, diag=True)] = C(AMETHYST[3])
        body = r2 & ~ring(r2, diag=True)
        for y, x in zip(*np.nonzero(body)):
            a[y, x] = C(mix(OBS[0], OBS[1], (y - 3) / 24))
        for (x0, y0) in ((MX - 19, 13), (MX + 17, 13)):      # rune ticks at the points
            rect(a, x0, y0, x0 + 2, y0 + 3, AMETHYST[1])
        return a

    def boss(self, fill):
        a = blank(364, 10)
        rect(a, 0, 0, 364, 1, AMETHYST[4], 230)
        rect(a, 0, 1, 364, 2, AMETHYST[1])
        rect(a, 0, 2, 364, 8, (20, 10, 26))
        rect(a, 0, 8, 364, 9, AMETHYST[2])
        rect(a, 0, 9, 364, 10, AMETHYST[4], 230)
        if fill:
            rows = [(255, 140, 180), CRYSTAL[1], CRYSTAL[1], CRYSTAL[2], CRYSTAL[2], CRYSTAL[3]]
            for i, c in enumerate(rows):
                rect(a, 0, 2 + i, 364, 3 + i, c)
        return a

    def boss_frame(self):
        w, h = FRAME[2] * S, FRAME[3] * S
        a = blank(w, h)
        for side in (0, 1):
            def X(x):
                return x if side == 0 else w - 1 - x
            # thorns: three angular spikes from the bar's end, glowing edges
            for (tip_x, tip_y, base_y0, base_y1) in ((2, 15, 11, 19), (16, 2, 10, 14), (16, 28, 16, 20)):
                base_x = 34
                for x in range(min(tip_x, base_x), base_x + 1):
                    t = (x - tip_x) / max(1, base_x - tip_x)
                    yc = tip_y + (((base_y0 + base_y1) / 2) - tip_y) * t
                    hh = (base_y1 - base_y0) / 2 * t
                    for y in range(int(math.floor(yc - hh)), int(math.ceil(yc + hh)) + 1):
                        if 0 <= y < h:
                            edge = abs(y - yc) >= hh - 0.8
                            px(a, X(x), y, AMETHYST[1] if edge else mix(OBS[0], (70, 40, 110), 0.5))
            rect(a, min(X(30), X(35)), 9, max(X(30), X(35)) + 1, 21, AMETHYST[3])
            rect(a, min(X(31), X(34)), 10, max(X(31), X(34)) + 1, 20, AMETHYST[1])
        for x in range(36, w - 36):
            d = abs(x - w / 2) / (w / 2 - 36)
            al = int(255 * min(1, max(0, (d - 0.3) / 0.5)))
            if al > 20:
                px(a, x, 8, AMETHYST[2], al)
                px(a, x, 21, AMETHYST[3], al)
        return a

    def armor_body(self):
        return [(236, 226, 250), (176, 160, 206), (116, 100, 152), (66, 54, 98)]


CLASSES = {c.name: c for c in (Gilded, Cloisonne, Ironbound, Moonsilver, Obsidian)}


# =============================================================================================== sheets / zip
def _read(zp, name, prefix=G):
    with zipfile.ZipFile(zp) as z:
        return Image.open(io.BytesIO(z.read(prefix + name))).convert("RGBA")


def build(design, gui_zip=GUI_ZIP, qf_zip=QF_ZIP):
    d = CLASSES[design]()
    return d, d.icons(_read(gui_zip, "icons.png")), d.widgets(_read(qf_zip, "widgets.png"))


def write_zip(design, out, gui_zip=GUI_ZIP, qf_zip=QF_ZIP):
    d, ic, wd = build(design, gui_zip, qf_zip)
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("pack.mcmeta", '{"pack": {"pack_format": 1, "description": "QF r015 HUD: %s"}}' % design)
        for n, im in (("icons.png", ic), ("widgets.png", wd)):
            b = io.BytesIO()
            im.save(b, "PNG")
            z.writestr(G + n, b.getvalue())
        z.writestr("assets/minecraft/mcpatcher/color.properties", d.color_properties())
    print("hud r015 %s -> %s" % (design, out))


# =============================================================================================== offline mock
class Font:
    """The vanilla 8x8 ascii font, read from the client jar (read only), drawn like FontRenderer."""

    def __init__(self):
        with zipfile.ZipFile(MC_JAR) as z:
            im = Image.open(io.BytesIO(z.read("assets/minecraft/textures/font/ascii.png"))).convert("RGBA")
        self.g = np.asarray(im)[..., 3] > 0
        self.cw = {}
        for c in range(256):
            gx, gy = (c % 16) * 8, (c // 16) * 8
            cols = [x for x in range(8) if self.g[gy:gy + 8, gx + x].any()]
            self.cw[c] = 4 if c == 32 else (max(cols) + 2 if cols else 0)

    def width(self, s):
        return sum(self.cw.get(ord(ch), 6) for ch in s)

    def draw(self, im, s, x, y, col, scale=S):
        a = np.asarray(im).copy()
        for ch in s:
            c = ord(ch)
            gx, gy = (c % 16) * 8, (c // 16) * 8
            for yy in range(8):
                for xx in range(8):
                    if self.g[gy + yy, gx + xx]:
                        X, Y = (x + xx) * scale, (y + yy) * scale
                        a[Y:Y + scale, X:X + scale] = list(col) + [255]
            x += self.cw.get(c, 6)
        return Image.fromarray(a)


def hexc(h):
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _items():
    names = ["diamond_sword", "bow_standby", "iron_pickaxe", "potion_bottle_drinkable", "book_enchanted",
             "apple_golden", "compass", "bread", "ender_pearl"]
    out = []
    try:
        with zipfile.ZipFile(MC_JAR) as z:
            for n in names:
                p = "assets/minecraft/textures/items/%s.png" % n
                try:
                    im = Image.open(io.BytesIO(z.read(p))).convert("RGBA")
                    if im.height > 16:
                        im = im.crop((0, 0, 16, 16))
                    out.append(im.resize((16 * S, 16 * S), Image.NEAREST))
                except KeyError:
                    out.append(None)
    except FileNotFoundError:
        pass
    return out


def backdrop(W, H):
    """Sky with a bright cloud behind the boss name (the critic's hard case), grass under the HUD; 2x px."""
    a = np.zeros((H, W, 4), np.uint8)
    for y in range(H):
        t = y / H
        c = mix((120, 160, 220), (190, 210, 236), min(1, t * 2))
        a[y, :] = C(c)
    yy, xx = np.mgrid[0:H, 0:W]
    cloud = ((xx - W / 2) / (W * 0.32)) ** 2 + ((yy - 14) / 34.0) ** 2 < 1
    a[cloud] = C((246, 246, 244))
    g0 = int(H * 0.55)
    rng = np.random.default_rng(1)
    for y in range(g0, H, 4):
        for x in range(0, W, 4):
            n = rng.integers(-14, 15)
            a[y:y + 4, x:x + 4] = C((88 + n, 132 + n, 60 + n // 2))
    return a


def mock(design, health=15, last=None, food=20, armor=13, xpf=0.62, boss=0.62, level=27, air=None, sel=0,
         font=None, items=None, gui_w=240, gui_h=112):
    d, icons, widgets = build(design)
    ic, wd = np.asarray(icons), np.asarray(widgets)
    W, H = gui_w * S, gui_h * S
    im = backdrop(W, H)
    font = font or Font()
    gw, gh = gui_w, gui_h

    def blit(sheet, u, v, w, h, x, y, blend=True):
        tile = sheet[v * S:(v + h) * S, u * S:(u + w) * S]
        if blend:
            over(im, tile, x * S, y * S)
        else:
            m = tile[..., 3] > 25
            reg = im[y * S:(y + h) * S, x * S:(x + w) * S]
            reg[m] = tile[m]

    # boss bar, frame, name
    bx = gw // 2 - 91
    blit(ic, 0, 74, 182, 5, bx, 12)
    blit(ic, 0, 74, 182, 5, bx, 12)
    k = int(boss * 183)
    if k:
        blit(ic, 0, 79, k, 5, bx, 12)
    blit(ic, FRAME[0], FRAME[1], FRAME[2], FRAME[3], gw // 2 - FRAME[2] // 2, 12 + (5 - FRAME[3]) // 2)
    out = Image.fromarray(im)
    name = "Ender Dragon"
    nx = gw // 2 - font.width(name) // 2
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dx or dy:
                out = font.draw(out, name, nx + dx, 2 + dy, hexc(d.boss_outline))
    out = font.draw(out, name, nx, 2, hexc(d.boss_name))
    im[:] = np.asarray(out)
    left = gw // 2 - 91
    top = gh - 39
    # armour (left to right), hearts (right to left), food (right to left), air
    if armor > 0:
        for kk, i in enumerate(range(1, 20, 2)):
            u = 34 if i < armor else 25 if i == armor else 16
            blit(ic, u, 9, 9, 9, left + 8 * kk, top - 10)
    for i in range(9, -1, -1):
        x = left + i * 8
        blit(ic, 25 if last else 16, 0, 9, 9, x, top)
        if last:
            if i * 2 + 1 < last:
                blit(ic, 70, 0, 9, 9, x, top)
            elif i * 2 + 1 == last:
                blit(ic, 79, 0, 9, 9, x, top)
        if i * 2 + 1 < health:
            blit(ic, 52, 0, 9, 9, x, top)
        elif i * 2 + 1 == health:
            blit(ic, 61, 0, 9, 9, x, top)
    right = gw // 2 + 91
    for i in range(10):
        x = right - i * 8 - 9
        blit(ic, 16, 27, 9, 9, x, top)
        if i * 2 + 1 < food:
            blit(ic, 52, 27, 9, 9, x, top)
        elif i * 2 + 1 == food:
            blit(ic, 61, 27, 9, 9, x, top)
    if air:
        for i in range(air):
            blit(ic, 16, 18, 9, 9, right - i * 8 - 9, top - 10)
    # XP (blend off), medallion, number
    blit(ic, 0, 64, 182, 5, left, gh - 29, blend=False)
    k = int(xpf * 183)
    if k:
        blit(ic, 0, 69, k, 5, left, gh - 29, blend=False)
    blit(widgets_ := wd, 0, 0, 182, 22, left, gh - 22)
    blit(wd, 0, 22, 24, 22, left - 1 + 20 * sel, gh - 23)
    if items:
        for i, it in enumerate(items):
            if it is not None:
                over(im, np.asarray(it), (left + 3 + 20 * i) * S, (gh - 19) * S)
    if level > 0:
        t = str(level)
        y = gh - 31 - 4
        blit(ic, PLATE[0], PLATE[1], PLATE[2], PLATE[3], gw // 2 - PLATE[2] // 2, y + 4 - PLATE[3] // 2)
        x = (gw - font.width(t)) // 2
        out = Image.fromarray(im)
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            out = font.draw(out, t, x + dx, y + dy, hexc(d.xp_outline))
        out = font.draw(out, t, x, y, hexc(d.xp_num))
        im[:] = np.asarray(out)
    return Image.fromarray(im)


def label(im, text, font, scale=2, col=(255, 240, 200)):
    a = Image.new("RGBA", (im.width, 12 * scale), (18, 16, 14, 255))
    a = font.draw(a, text, 3, 2, col, scale=scale)
    out = Image.new("RGBA", (im.width, im.height + a.height))
    out.paste(a, (0, 0))
    out.paste(im, (0, a.height))
    return out


def mock_sheet(path, icons_path=None):
    font = Font()
    items = _items()
    tiles = []
    for dn in DESIGNS:
        a = mock(dn, font=font, items=items)
        b = mock(dn, health=9, last=15, food=7, armor=7, xpf=0.2, boss=0.25, level=104, air=6, sel=4, font=font,
                 items=items)
        g2 = Image.new("RGBA", (a.width * 2, a.height))
        g2.paste(a, (0, 0))
        g2.paste(b, (a.width, 0))
        g2 = g2.resize((g2.width * 2, g2.height * 2), Image.NEAREST)        # GUI scale 4 view
        one = np.asarray(g2.resize((g2.width // 2, g2.height // 2), Image.NEAREST))   # back to sheet res
        one = Image.fromarray(np.ascontiguousarray(one[1::2, 1::2]))       # what GUI scale 1 samples
        one = one.resize((one.width * 4, one.height * 4), Image.NEAREST)  # shown 4x so it can be judged
        t = label(g2, "%s   (GUI scale 4; left normal, right just hit + under water)" % TITLES[dn], font)
        t1 = label(one, "%s at GUI scale 1, shown 4x" % TITLES[dn], font)
        tiles.append((t, t1))
    Wt = max(t.width for t, _ in tiles)
    Ht = sum(t.height + t1.height for t, t1 in tiles)
    sheet = Image.new("RGBA", (Wt, Ht), (12, 12, 12, 255))
    y = 0
    for t, t1 in tiles:
        sheet.paste(t, (0, y))
        y += t.height
        sheet.paste(t1, (0, y))
        y += t1.height
    sheet.convert("RGB").save(path)
    print("mock ->", path)
    if icons_path:
        rows = []
        for dn in DESIGNS:
            d, icn, wd = build(dn)
            a = np.asarray(icn)
            cells = [(16, 0), (25, 0), (52, 0), (61, 0), (70, 0), (160, 0), (16, 9), (25, 9), (34, 9), (16, 27),
                     (52, 27), (61, 27), (16, 18)]
            row = Image.new("RGBA", (len(cells) * 20 * S + 60 * S, 20 * S), (92, 110, 84, 255))
            for k, (u, v) in enumerate(cells):
                bg = np.asarray(row).copy()
                if (u, v) in ((52, 0), (61, 0), (70, 0), (160, 0)):
                    over(bg, a[0:18, 16 * S:16 * S + 18], k * 20 * S + 2, 2)
                elif (u, v) in ((52, 27), (61, 27)):
                    over(bg, a[27 * S:27 * S + 18, 16 * S:16 * S + 18], k * 20 * S + 2, 2)
                over(bg, a[v * S:v * S + 18, u * S:u * S + 18], k * 20 * S + 2, 2)
                row = Image.fromarray(bg)
            bg = np.asarray(row).copy()
            over(bg, a[PLATE[1] * S:(PLATE[1] + PLATE[3]) * S, 0:PLATE[2] * S], len(cells) * 20 * S + 4, 4)
            row = Image.fromarray(bg)
            row = row.resize((row.width * 6, row.height * 6), Image.NEAREST)
            rows.append(label(row, TITLES[dn] + ": heart row, blink, full, half, lost, absorb; armour; food; air; "
                                                "medallion", font, scale=4))
        Wt = max(r.width for r in rows)
        out = Image.new("RGBA", (Wt, sum(r.height for r in rows)), (12, 12, 12, 255))
        y = 0
        for r in rows:
            out.paste(r, (0, y))
            y += r.height
        out.convert("RGB").save(icons_path)
        print("icons ->", icons_path)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--design", choices=DESIGNS)
    ap.add_argument("--out")
    ap.add_argument("--gui-zip", default=GUI_ZIP)
    ap.add_argument("--qf-zip", default=QF_ZIP)
    ap.add_argument("--mock")
    ap.add_argument("--icons")
    a = ap.parse_args()
    if a.mock:
        mock_sheet(a.mock, a.icons)
        return
    write_zip(a.design, a.out, a.gui_zip, a.qf_zip)


if __name__ == "__main__":
    main()
