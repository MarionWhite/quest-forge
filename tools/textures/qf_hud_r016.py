#!/usr/bin/env python3
"""r016: FOUR minimal, sleek Quest Forge HUDs and FOUR chunky boss bars (our own art, 2x sheets).

    py -3.10 -I tools/textures/qf_hud_r016.py --design refined|glass|gunmetal|wine --out OUT.zip
    py -3.10 -I tools/textures/qf_hud_r016.py --mock OUT.png [--icons OUT2.png] [--boss OUT3.png]   (offline)

The owner, r015 (every rich design rejected): "These are all worse. WAY worse. Back to a minimal design, but don't get
stuck in the Elden ring inspiration."  And r014 (minimal): "too far minimalist... I want it to look more sleek and
pleasing on the eyes."  So: no bands, cells or ornaments behind the rows (r015's mistake), and no gold hairline
"grace" strip or diamond finials (r014's Elden Ring motifs). The finish goes into the icons themselves (one light
source, glossy domed shading, a clean keyline, a single specular) and into one quiet hotbar per design:

  refined   r014 grown up: crisp ink keylines, glossy domed bodies; a slim smoked strip with soft rounded ends and
            faint dividers; a warm white-gold selection with a soft glow; a gold glass XP thread; a capsule medallion.
  glass     frosted glass: each slot its own rounded tile; candy-gloss icons with tinted (not black) keylines;
            a white selection ring; a mint capsule XP bar; a frosted pill medallion.
  gunmetal  machined steel: a bevelled gunmetal strip with recessed wells; chrome-rimmed icons; a steel selection
            with a crimson inner line; an amber XP bar in a steel track; a chamfered steel tag.
  wine      wine glass and gold: a dark wine strip between two bevelled gold rails, chamfered gold selection;
            gold-rimmed icons; a gold XP bar on wine; a gold-ringed wine medallion (the boss bars' family).

Boss bars (owner, r015: "Try for something closer to the terraria infernum mod with the custom health bars and UI").
Studied, never copied (notes: ops/checkpoints/r016-packs.md, step 1): one THICK bar, a medallion socket at one end that
the fill drains toward, opaque bevelled rails, a dark-but-coloured empty channel, a slanted stepped sheen on the fill,
a bright cap riding the fill's edge, the health in percent. Ours, each with the boss name outlined above it:

  gilded    gold rails, crimson fill, a round gold-ringed wine medallion with a horned skull, a pointed end, the percent
            in a gold-rimmed tab under the bar's end.
  obsidian  black glass with a violet edge light (r015 E grown up), a magenta fill, an octagonal amethyst socket with a
            slit eye, a crystal-shard cap, crystal spikes at the end, the percent inside the bar.
  ironclad  riveted gunmetal, a blood-red fill cut into tenths, a steel shield emblem, a square end clamp holding the
            percent.
  ember     blackened bronze, a molten fill (white-yellow core to deep red), a bronze sun medallion with a flame, a
            glowing cap, the percent after the bar's point.

The chunky bar, its medallion, the percent and the fade-in are drawn by qf-content's client hook XpBarStyle ("bar
mode", qf.boss.* keys in assets/minecraft/mcpatcher/color.properties, sprites in textures/gui/qf_bossbar.png). So are
the XP number's colour, the XP medallion and the boss name's outline. Without the hook (the owner's yes) the number
is lime, there is no medallion, and the boss bar is vanilla's 182 x 5 strip (drawn here in each design's colours).
1.7.10 has no per-boss icon or phase data, so every boss shows the design's emblem and the rails carry quarter ticks.

Nothing is copied, traced or sampled from any game or pack; every pixel is drawn by this script.
GUI scale 1 shows only the odd texels of a 2x sheet: every keyline and rim that must survive it is two texels wide.
"""
import argparse, io, math, os, sys, zipfile

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import qf_hud_r015 as b  # noqa: E402  (toolkit: over, Font, backdrop, item icons)

G = "assets/minecraft/textures/gui/"
S = 2
QF_ZIP = b.QF_ZIP
GUI_ZIP = b.GUI_ZIP
over, mix, C = b.over, b.mix, b.C

DESIGNS = ["refined", "glass", "gunmetal", "wine"]
BOSS_OF = {"refined": "ember", "glass": "obsidian", "gunmetal": "ironclad", "wine": "gilded"}
TITLES = {"refined": "A  Refined", "glass": "B  Glass", "gunmetal": "C  Gunmetal", "wine": "D  Wine & gold"}
BOSS_TITLES = {"ember": "A  Ember", "obsidian": "B  Obsidian", "ironclad": "C  Ironclad", "gilded": "D  Gilded"}
PLATE = (0, 100, 18, 10)      # XP medallion in icons.png (GUI px); hearts end at w/2-10, food starts at w/2+10
BOSS_SHEET = "textures/gui/qf_bossbar.png"
BOSS_TOP = 12                 # bar top row (the outlined name sits on rows 1-10)
INK = (14, 11, 12)


# =============================================================================================== small helpers
def mask(art):
    rows = [r for r in art.strip("\n").split("\n")]
    m = np.zeros((18, 18), bool)
    for y, r in enumerate(rows[:18]):
        for x, ch in enumerate(r[:18]):
            m[y, x] = ch == "#"
    return m


def edge(m):
    p = np.pad(m, 1)
    inner = p[1:-1, 1:-1] & p[:-2, 1:-1] & p[2:, 1:-1] & p[1:-1, :-2] & p[1:-1, 2:]
    return m & ~inner


def dist_in(m, cap=4):
    """4-neighbour distance from the outside, capped (0 outside, 1 on the edge)."""
    d = np.where(m, cap, 0).astype(np.int32)
    d[edge(m)] = 1
    for k in range(1, cap):
        p = np.pad(d, 1)
        nb = np.minimum.reduce([p[:-2, 1:-1], p[2:, 1:-1], p[1:-1, :-2], p[1:-1, 2:]])
        d = np.where(m & (d > k) & (nb == k), k + 1, d)
    return d


def ramp(r, t):
    t = max(0.0, min(1.0, t)) * (len(r) - 1)
    i = min(int(t), len(r) - 2)
    return mix(r[i], r[i + 1], t - i)


def quant(r, t):
    """Pick the nearest ramp step (pixel-art: no blended in-betweens)."""
    t = max(0.0, min(1.0, t))
    return r[int(round(t * (len(r) - 1)))]


def dome(m, r, light=(-0.6, -0.8), spec=None, rim=None, flat=0.0, steps=True):
    """Glossy domed shading of mask m from ramp r (lit .. deep). spec: a colour for the specular texels; rim: a
    reflected-light colour along the lower-right edge. flat > 0 flattens the dome (metal plates)."""
    out = np.zeros(m.shape + (4,), np.uint8)
    if not m.any():
        return out
    d = dist_in(m, 4).astype(np.float32)
    h = np.sqrt(np.clip(d / 4.0, 0, 1))
    gy, gx = np.gradient(h)
    ys, xs = np.nonzero(m)
    cy, cx = ys.mean(), xs.mean()
    ry, rx = max(1.0, (ys.max() - ys.min()) / 2), max(1.0, (xs.max() - xs.min()) / 2)
    lx, ly = light
    for y, x in zip(ys, xs):
        nx, ny = -gx[y, x] * 2.2, -gy[y, x] * 2.2
        u, v = (x - cx) / rx, (y - cy) / ry
        lam = 0.5 * (u * lx + v * ly) * (1 - flat) + (nx * lx + ny * ly) * 0.55
        t = 0.48 - lam * 0.55
        out[y, x] = C(quant(r, t) if steps else ramp(r, t))
    if rim is not None:
        e = edge(m)
        p = np.pad(m, 1)
        for y, x in zip(*np.nonzero(e)):
            if (not p[y + 2, x + 1] or not p[y + 1, x + 2]) and (x - cx) + (y - cy) > 1.5:
                out[y, x] = C(rim)
    if spec is not None:
        # the specular: the inner texels nearest the upper-left of the dome
        cand = [(y, x) for y, x in zip(ys, xs) if d[y, x] >= 2]
        if cand:
            sc = sorted(cand, key=lambda p: (p[1] - cx) / rx * 0.6 + (p[0] - cy) / ry * 0.8)
            ty, tx = sc[0]
            for (y, x) in ((ty, tx), (ty, tx + 1), (ty + 1, tx)):
                if 0 <= y < m.shape[0] and 0 <= x < m.shape[1] and m[y, x] and d[y, x] >= 2:
                    out[y, x] = C(spec)
    return out


def facet(m, r, spec=None):
    """Cut-gem shading: four flat facets round the centre (top-left lit .. bottom-right deep) and a bright table
    edge along the top-left facet's ridge."""
    out = np.zeros(m.shape + (4,), np.uint8)
    if not m.any():
        return out
    ys, xs = np.nonzero(m)
    cy, cx = (ys.min() + ys.max()) / 2 - 0.5, (xs.min() + xs.max()) / 2
    for y, x in zip(ys, xs):
        u, v = x + 0.5 - cx, y + 0.5 - cy
        if v < -abs(u) * 0.35:
            t = 0.12 if u < 0 else 0.38
        else:
            t = 0.55 if u < 0 else 0.85
        if abs(u) < 0.6 and v > -1:
            t = 0.7
        out[y, x] = C(quant(r, t))
    if spec is not None:
        d = dist_in(m, 3)
        cand = [(y, x) for y, x in zip(ys, xs) if d[y, x] >= 2 and x + 0.5 < cx and y + 0.5 < cy]
        for (y, x) in sorted(cand, key=lambda p: p[0] + p[1])[:2]:
            out[y, x] = C(spec)
    return out


def keyline(m, col, al=255):
    a = np.zeros(m.shape + (4,), np.uint8)
    a[edge(m)] = C(col, al)
    return a


def rect(a, x0, y0, x1, y1, c, al=255):
    y0, y1, x0, x1 = max(0, y0), min(a.shape[0], y1), max(0, x0), min(a.shape[1], x1)
    if x1 > x0 and y1 > y0:
        a[y0:y1, x0:x1] = C(c, al)


def blend_px(a, x, y, c, al):
    if 0 <= y < a.shape[0] and 0 <= x < a.shape[1]:
        t = np.zeros((1, 1, 4), np.uint8)
        t[0, 0] = C(c, al)
        over(a, t, x, y)


def rounded(w, h, r):
    """A rounded-rect mask (corner radius r texels, pixel-art corners)."""
    m = np.ones((h, w), bool)
    for y in range(r):
        for x in range(r):
            if (r - x - 0.5) ** 2 + (r - y - 0.5) ** 2 > r * r:
                m[y, x] = m[y, w - 1 - x] = m[h - 1 - y, x] = m[h - 1 - y, w - 1 - x] = False
    return m


def chamfer(w, h, c):
    m = np.ones((h, w), bool)
    for y in range(c):
        for x in range(c - y):
            m[y, x] = m[y, w - 1 - x] = m[h - 1 - y, x] = m[h - 1 - y, w - 1 - x] = False
    return m


def paint_mask(a, m, col, al=255, x=0, y=0):
    t = np.zeros(m.shape + (4,), np.uint8)
    t[m] = C(col, al)
    over(a, t, x, y)


def ring_of(m, t=2):
    inner = m.copy()
    for _ in range(t):
        inner = inner & ~edge(inner)
    return m & ~inner, inner


def disc(w, h, cx, cy, r):
    yy, xx = np.mgrid[0:h, 0:w]
    return (xx + 0.5 - cx) ** 2 + (yy + 0.5 - cy) ** 2 <= r * r


# =============================================================================================== silhouettes (2x px)
# Each icon is an 18 x 18 cell; '#' = inside, keyline included. 15 wide so neighbours 16 texels apart keep 1 clear.
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
"""
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
"""
BONE_PART = """
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
"""
CHEST = """
..................
.####......####...
.#####....#####...
.######..######...
.##############...
.##############...
..############....
...##########.....
....#########.....
....#########.....
....#########.....
....#########.....
....#########.....
.....#######......
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
"""

# body ramps: spec-ish light .. deep (5 steps)
CRIMSON = [(255, 136, 120), (232, 64, 60), (184, 30, 38), (128, 16, 28), (80, 8, 20)]
POISON = [(208, 222, 120), (156, 178, 56), (112, 134, 36), (74, 92, 22), (44, 56, 14)]
WITHER = [(150, 142, 140), (98, 92, 90), (66, 60, 60), (42, 38, 38), (24, 22, 22)]
ABSORB = [(255, 244, 176), (246, 206, 96), (212, 156, 48), (156, 106, 28), (98, 64, 16)]
LOST = [(255, 246, 222), (240, 222, 178), (214, 186, 132), (172, 140, 92), (124, 96, 60)]
MOUNT = [(250, 196, 128), (226, 140, 70), (178, 96, 42), (124, 60, 24), (78, 34, 14)]
MEAT = [(248, 182, 120), (220, 122, 62), (172, 82, 38), (118, 50, 22), (74, 28, 12)]
ROT = [(196, 206, 116), (146, 160, 66), (104, 118, 40), (68, 78, 24), (40, 46, 14)]
BONE = [(255, 252, 238), (234, 224, 198), (198, 186, 156), (152, 140, 112), (106, 96, 76)]
STEEL = [(250, 252, 255), (210, 216, 224), (160, 168, 180), (110, 118, 132), (66, 72, 84)]
DIAMOND = [(236, 255, 255), (140, 236, 240), (70, 190, 204), (36, 128, 148), (18, 76, 92)]
GLASS = [(240, 250, 255), (150, 200, 245), (84, 142, 214), (44, 90, 164), (22, 50, 108)]


# =============================================================================================== HUD designs
class Hud:
    name = "base"
    shading = "dome"              # dome (glossy) or facet (cut)
    key = INK                     # keyline colour (None: a darker tone of each body)
    key_al = 255
    empty = [(78, 70, 70), (58, 52, 52), (44, 40, 40), (32, 29, 29), (22, 20, 20)]
    empty_al = 200
    blink = [(255, 255, 255), (232, 226, 220), (196, 188, 180), (150, 142, 134), (110, 104, 98)]
    spec = (255, 255, 255)
    rim = None
    armor_body = STEEL
    xp_num, xp_outline = "F2DFA8", "1A1208"
    boss = "ember"
    hairline = None               # an inner hairline ramp (lit, shaded) drawn inside the keyline, or None

    # ---- icons
    def icon(self, art, body, sub=None, sub_body=None, empty=False, key=None):
        m = mask(art)
        a = np.zeros((18, 18, 4), np.uint8)
        kcol = key or self.key or body[4]
        k = edge(m)
        inner = m & ~k
        if self.hairline is not None and not empty:
            hl = edge(inner)
            inner2 = inner & ~hl
        else:
            hl, inner2 = None, inner
        sp, rm = (None, None) if empty else (self.spec, self.rim)

        def shade(mm, rr, spec):
            if self.shading == "facet" and not empty:
                return facet(mm, rr, spec)
            return dome(mm, rr, spec=spec, rim=rm)
        if sub is not None:
            sm = mask(sub) & inner2
            a = over(a, shade(inner2 & ~sm, body, sp))
            a = over(a, shade(sm, sub_body, None))
        else:
            a = over(a, shade(inner2, body, sp))
        if hl is not None:
            lit, shd = self.hairline
            ys, xs = np.nonzero(m)
            cx, cy = xs.mean(), ys.mean()
            for y, x in zip(*np.nonzero(hl)):
                a[y, x] = C(lit if (x - cx) + (y - cy) * 1.3 < 0 else shd)
        a[k] = C(kcol, self.key_al if not empty else max(self.key_al, 220))
        if empty:
            a[inner, 3] = np.minimum(a[inner, 3], self.empty_al)
        return a

    def body_only(self, full, art, side=None):
        """What a full icon draws over its container (the container supplies the keyline)."""
        m = mask(art)
        a = full.copy()
        a[edge(m)] = 0
        a[~m] = 0
        if side == "left":
            a[:, 9:] = 0
        elif side == "right":
            a[:, :9] = 0
        return a

    @staticmethod
    def half_whole(full, empty, side):
        a = empty.copy()
        if side == "left":
            a[:, :9] = full[:, :9]
        else:
            a[:, 9:] = full[:, 9:]
        return a

    def icons(self, base):
        ic = np.asarray(base.convert("RGBA").resize((256 * S, 256 * S), Image.NEAREST)).copy()

        def put(u, v, tile):
            ic[v * S:v * S + 18, u * S:u * S + 18] = tile

        def clear(u0, v, u1):
            ic[v * S:v * S + 18, u0 * S:u1 * S] = 0

        e_heart = self.icon(HEART, self.empty, empty=True)
        b_heart = self.icon(HEART, self.blink, empty=True)
        for v in (0, 45):
            clear(16, v, 16 + 9 * 26)
            put(16, v, e_heart)
            put(25, v, b_heart)
            for margin, body in ((16, CRIMSON), (52, POISON), (88, WITHER)):
                f = self.icon(HEART, body)
                put(margin + 36, v, self.body_only(f, HEART))
                put(margin + 45, v, self.body_only(f, HEART, "left"))
                lo = self.icon(HEART, LOST)
                put(margin + 54, v, self.body_only(lo, HEART))
                put(margin + 63, v, self.body_only(lo, HEART, "left"))
                ab = self.icon(HEART, ABSORB)
                put(margin + 144, v, self.body_only(ab, HEART))
                put(margin + 153, v, self.body_only(ab, HEART, "left"))
        clear(16, 9, 16 + 9 * 3)
        a_full = self.icon(CHEST, self.armor_body)
        a_empty = self.icon(CHEST, self.empty, empty=True)
        put(16, 9, a_empty)
        put(25, 9, self.half_whole(a_full, a_empty, "left"))
        put(34, 9, a_full)
        clear(52, 9, 52 + 9 * 7)
        put(52, 9, e_heart)
        mf = self.icon(HEART, MOUNT)
        put(88, 9, self.body_only(mf, HEART))
        put(97, 9, self.body_only(mf, HEART, "right"))
        clear(16, 18, 16 + 9 * 2)
        put(16, 18, self.icon(BUBBLE, GLASS))
        pop = np.zeros((18, 18, 4), np.uint8)
        pop[mask(POP)] = C(GLASS[1])
        put(25, 18, pop)
        clear(16, 27, 16 + 9 * 13)
        f_empty = self.icon(SHANK, self.empty, sub=BONE_PART, sub_body=self.empty, empty=True)
        put(16, 27, f_empty)
        put(25, 27, self.icon(SHANK, self.blink, sub=BONE_PART, sub_body=self.blink, empty=True))
        hunger = [(110, 118, 64), (84, 92, 46), (64, 70, 34), (46, 50, 24), (30, 34, 16)]
        put(133, 27, self.icon(SHANK, hunger, sub=BONE_PART, sub_body=hunger, empty=True))
        for u, meat in ((16, MEAT), (52, ROT)):
            full = self.icon(SHANK, meat, sub=BONE_PART, sub_body=BONE)
            put(u + 36, 27, self.body_only(full, SHANK))
            put(u + 45, 27, self.body_only(full, SHANK, "right"))
            lost = self.icon(SHANK, LOST, sub=BONE_PART, sub_body=LOST)
            put(u + 54, 27, self.body_only(lost, SHANK))
            put(u + 63, 27, self.body_only(lost, SHANK, "right"))
        for v, strip in ((64, self.xp(False)), (69, self.xp(True))):
            ic[v * S:(v + 5) * S, 0:182 * S] = binary(strip)
        bb = BOSSES[self.boss]()
        for v, strip in ((74, bb.vanilla(False)), (79, bb.vanilla(True))):
            ic[v * S:(v + 5) * S, 0:182 * S] = strip
        pl = self.medallion()
        ic[PLATE[1] * S:(PLATE[1] + PLATE[3]) * S, PLATE[0] * S:(PLATE[0] + PLATE[2]) * S] = pl
        return Image.fromarray(ic)

    # ---- hotbar
    def widgets(self, base):
        w = np.asarray(base.convert("RGBA").resize((256 * S, 256 * S), Image.NEAREST)).copy()
        w[0:44, 0:364] = self.hotbar()
        w[44:88, 0:48] = self.selection()
        return Image.fromarray(w)

    def xp(self, full):
        raise NotImplementedError

    def medallion(self):
        raise NotImplementedError

    def color_properties(self):
        bb = BOSSES[self.boss]()
        return ("# Quest Forge HUD r016 '%s' + boss bar '%s' (tools/textures/qf_hud_r016.py). text.xpbar / text.boss are\n"
                "# MCPatcher's keys; qf-content's client hook XpBarStyle reads them and the qf.* keys.\n"
                "text.xpbar=%s\nqf.xpbar.outline=%s\nqf.xpbar.plate=%d,%d,%d,%d\n"
                % ((self.name, self.boss, self.xp_num, self.xp_outline) + PLATE)) + bb.properties()


def binary(a):
    a = a.copy()
    a[..., 3] = np.where(a[..., 3] >= 128, 255, 0)
    return a


def strip_track(track, fill, full, top_rows=(0, 2), rows=(2, 8), hi=None, edge_col=INK, w=364):
    """A 182 x 5 XP strip (2x): transparent outside `rows` + its keyline; the bar 'rows' (texel rows y0..y1)."""
    a = np.zeros((10, w, 4), np.uint8)
    y0, y1 = rows
    rect(a, 0, y0 - 1, w, y0, edge_col)
    rect(a, 0, y1, w, y1 + 1, edge_col)
    rect(a, 0, y0 - 1, 1, y1 + 1, edge_col)
    rect(a, w - 1, y0 - 1, w, y1 + 1, edge_col)
    for y in range(y0, y1):
        t = (y - y0) / max(1, y1 - y0 - 1)
        col = ramp(fill if full else track, t)
        rect(a, 1, y, w - 1, y + 1, col)
    if full and hi is not None:
        rect(a, 1, y0, w - 1, y0 + 1, hi)
    return a


class Refined(Hud):
    name = "refined"
    key = INK
    spec = (255, 250, 240)
    rim = None
    xp_num, xp_outline = "F4E2AE", "1E1408"
    boss = "ember"

    def hotbar(self):
        a = np.zeros((44, 364, 4), np.uint8)
        m = rounded(364, 44, 6)
        paint_mask(a, m, (16, 16, 20), 168)
        k, _ = ring_of(m, 2)
        paint_mask(a, k & np.r_[np.ones(22, bool), np.zeros(22, bool)][:, None], (150, 140, 120), 150)
        paint_mask(a, k & np.r_[np.zeros(22, bool), np.ones(22, bool)][:, None], (60, 56, 52), 190)
        rect(a, 6, 2, 358, 3, (255, 244, 220), 40)                       # a soft glass highlight under the rim
        for i in range(1, 9):                                             # short, faint dividers
            x = 40 * i
            rect(a, x, 12, x + 2, 32, (200, 190, 170), 70)
        return a

    def selection(self):
        a = np.zeros((44, 48, 4), np.uint8)
        m = rounded(48, 44, 6)
        k, _ = ring_of(m, 2)
        g, _ = ring_of(m, 4)
        paint_mask(a, g & ~k, (255, 226, 150), 70)                        # inner glow
        cols = np.zeros((44, 48), bool)
        cols[:22] = True
        paint_mask(a, k & cols, (255, 246, 214))
        paint_mask(a, k & ~cols, (222, 182, 104))
        return a

    def xp(self, full):
        return strip_track([(58, 50, 40), (36, 30, 24), (26, 22, 18)],
                           [(255, 236, 160), (240, 196, 92), (196, 140, 50)], full, rows=(3, 8),
                           hi=(255, 250, 220), edge_col=(20, 15, 10))

    def medallion(self):
        a = np.zeros((20, 36, 4), np.uint8)
        m = rounded(36, 20, 9)
        paint_mask(a, m, (20, 15, 12), 235)
        k, _ = ring_of(m, 2)
        cols = np.zeros((20, 36), bool)
        cols[:10] = True
        paint_mask(a, k & cols, (246, 214, 140))
        paint_mask(a, k & ~cols, (168, 120, 58))
        return a


class Glass(Hud):
    name = "glass"
    key = None                     # a deep tone of each body
    spec = (255, 255, 255)
    rim = (255, 220, 230)
    empty = [(120, 130, 146), (96, 106, 122), (74, 82, 98), (56, 62, 76), (40, 44, 56)]
    empty_al = 150
    xp_num, xp_outline = "F4FBFF", "102030"
    boss = "obsidian"

    def icon(self, art, body, sub=None, sub_body=None, empty=False, key=None):
        a = super().icon(art, body, sub, sub_body, empty, key)
        if not empty:                                                     # a white rim-light along the top-left
            m = mask(art)
            inner = m & ~edge(m)
            e2 = edge(inner)
            ys, xs = np.nonzero(m)
            cx, cy = xs.mean(), ys.mean()
            for y, x in zip(*np.nonzero(e2)):
                if (x - cx) * 0.6 + (y - cy) < -3.0:
                    a[y, x] = C(mix(tuple(int(v) for v in a[y, x][:3]), (255, 255, 255), 0.45))
            # a candy-glass highlight: a short bright bar across the upper-left of the body
            d = dist_in(inner, 3)
            cand = [(y, x) for y, x in zip(*np.nonzero(inner)) if d[y, x] >= 2 and y < cy - 1 and x < cx]
            if cand:
                y0 = min(c[0] for c in cand)
                row = sorted(x for (y, x) in cand if y == y0 + 1)
                for x in row[:3]:
                    a[y0 + 1, x] = C((255, 255, 255))
        return a

    def hotbar(self):
        a = np.zeros((44, 364, 4), np.uint8)
        for i in range(9):
            x0 = 40 * i + 2
            m = rounded(40, 40, 6)
            t = np.zeros((40, 40, 4), np.uint8)
            paint_mask(t, m, (22, 30, 44), 140)
            k, _ = ring_of(m, 2)
            top = np.zeros((40, 40), bool)
            top[:20] = True
            paint_mask(t, k & top, (226, 238, 255), 150)
            paint_mask(t, k & ~top, (150, 170, 196), 110)
            rect(t, 6, 3, 34, 4, (255, 255, 255), 50)
            over(a, t, x0, 2)
        return a

    def selection(self):
        a = np.zeros((44, 48, 4), np.uint8)
        m = rounded(44, 44, 8)
        k, inner = ring_of(m, 3)
        g, _ = ring_of(inner, 2)
        t = np.zeros((44, 44, 4), np.uint8)
        paint_mask(t, k, (255, 255, 255))
        paint_mask(t, g, (190, 230, 255), 90)
        over(a, t, 2, 0)
        return a

    def xp(self, full):
        a = np.zeros((10, 364, 4), np.uint8)
        m = rounded(364, 6, 3)
        tr = np.zeros((6, 364, 4), np.uint8)
        fill = [(220, 255, 236), (120, 236, 180), (54, 186, 132)]
        track = [(70, 84, 100), (44, 54, 68), (34, 42, 54)]
        for y in range(6):
            col = ramp(fill if full else track, y / 5)
            tr[y][m[y]] = C(col)
        if full:
            tr[1][m[1]] = C((240, 255, 248))
        a[2:8] = tr
        k = edge(np.pad(m, ((2, 2), (0, 0))))
        return a

    def medallion(self):
        a = np.zeros((20, 36, 4), np.uint8)
        m = rounded(36, 20, 9)
        paint_mask(a, m, (24, 34, 50), 205)
        k, _ = ring_of(m, 2)
        top = np.zeros((20, 36), bool)
        top[:10] = True
        paint_mask(a, k & top, (240, 248, 255))
        paint_mask(a, k & ~top, (150, 172, 200))
        return a


class Gunmetal(Hud):
    name = "gunmetal"
    shading = "facet"
    key = (34, 36, 42)
    spec = (255, 255, 255)
    hairline = ((214, 220, 230), (96, 102, 114))     # a chrome rim inside the keyline
    xp_num, xp_outline = "F2F4F8", "16181C"
    boss = "ironclad"

    def hotbar(self):
        a = np.zeros((44, 364, 4), np.uint8)
        m = chamfer(364, 44, 3)
        paint_mask(a, m, (46, 50, 58), 235)
        k, inner = ring_of(m, 2)
        top = np.zeros((44, 364), bool)
        top[:22] = True
        paint_mask(a, k & top, (150, 158, 170))
        paint_mask(a, k & ~top, (22, 24, 28))
        for i in range(9):                                                 # recessed wells
            x0 = 40 * i + 4
            w = np.zeros((36, 36, 4), np.uint8)
            wm = chamfer(36, 36, 2)
            paint_mask(w, wm, (24, 26, 31), 245)
            wk, _ = ring_of(wm, 1)
            top2 = np.zeros((36, 36), bool)
            top2[:18] = True
            paint_mask(w, wk & top2, (14, 15, 18))
            paint_mask(w, wk & ~top2, (98, 104, 116))
            over(a, w, x0, 4)
        return a

    def selection(self):
        a = np.zeros((44, 48, 4), np.uint8)
        m = chamfer(48, 44, 4)
        k, inner = ring_of(m, 2)
        r2, _ = ring_of(inner, 1)
        top = np.zeros((44, 48), bool)
        top[:22] = True
        paint_mask(a, k & top, (236, 240, 246))
        paint_mask(a, k & ~top, (150, 156, 168))
        paint_mask(a, r2, (214, 44, 52))
        return a

    def xp(self, full):
        return strip_track([(40, 42, 48), (28, 30, 34), (20, 21, 24)],
                           [(255, 230, 150), (255, 170, 60), (214, 104, 28)], full, rows=(2, 8),
                           hi=(255, 246, 210), edge_col=(120, 126, 138))

    def medallion(self):
        a = np.zeros((20, 36, 4), np.uint8)
        m = chamfer(36, 20, 5)
        paint_mask(a, m, (40, 43, 50), 245)
        k, _ = ring_of(m, 2)
        top = np.zeros((20, 36), bool)
        top[:10] = True
        paint_mask(a, k & top, (220, 226, 236))
        paint_mask(a, k & ~top, (100, 106, 118))
        return a


class Wine(Hud):
    name = "wine"
    key = (26, 8, 14)
    spec = (255, 246, 230)
    hairline = ((250, 222, 150), (150, 104, 46))      # gold rim inside the keyline
    empty = [(96, 50, 60), (72, 36, 46), (56, 26, 36), (40, 18, 26), (28, 12, 18)]
    empty_al = 210
    xp_num, xp_outline = "F6D88E", "2A0A12"
    boss = "gilded"

    def hotbar(self):
        a = np.zeros((44, 364, 4), np.uint8)
        rect(a, 0, 4, 364, 40, (36, 8, 18), 175)
        for (y, c) in ((0, (110, 74, 30)), (1, (250, 222, 150)), (2, (214, 168, 84)), (3, (110, 74, 30)),
                       (40, (110, 74, 30)), (41, (226, 184, 104)), (42, (168, 120, 58)), (43, (70, 44, 18))):
            rect(a, 2, y, 362, y + 1, c)
        for x in (0, 1, 362, 363):
            rect(a, x, 1, x + 1, 43, (168, 120, 58))
        for i in range(1, 9):
            rect(a, 40 * i, 8, 40 * i + 2, 36, (214, 168, 84), 90)
        return a

    def selection(self):
        a = np.zeros((44, 48, 4), np.uint8)
        m = chamfer(48, 44, 6)
        k, inner = ring_of(m, 3)
        top = np.zeros((44, 48), bool)
        top[:22] = True
        paint_mask(a, k & top, (255, 232, 166))
        paint_mask(a, k & ~top, (200, 146, 66))
        g, _ = ring_of(inner, 2)
        paint_mask(a, g, (255, 210, 120), 60)
        return a

    def xp(self, full):
        return strip_track([(70, 20, 34), (48, 12, 24), (34, 8, 16)],
                           [(255, 236, 170), (238, 194, 96), (184, 128, 46)], full, rows=(2, 8),
                           hi=(255, 250, 224), edge_col=(24, 6, 12))

    def medallion(self):
        a = np.zeros((20, 36, 4), np.uint8)
        m = chamfer(36, 20, 6)
        paint_mask(a, m, (52, 10, 24), 240)
        k, _ = ring_of(m, 2)
        top = np.zeros((20, 36), bool)
        top[:10] = True
        paint_mask(a, k & top, (250, 222, 150))
        paint_mask(a, k & ~top, (160, 110, 48))
        return a


HUDS = {c.name: c for c in (Refined, Glass, Gunmetal, Wine)}


# =============================================================================================== boss bars
EMBLEM_SKULL = """
................................
..##........................##..
..###......................###..
...###....................###...
...####..................####...
....####....########....####....
.....####.############.####.....
......####################......
.......##################.......
......####################......
.....######################.....
.....######################.....
.....######################.....
.....###....########....###.....
.....##......######......##.....
.....##......######......##.....
.....###....###..###....###.....
......###########.#########.....
.......#######.....#######......
.........######...######........
.........##############.........
.........#.##.##.##.##.#........
..........#.##.##.##.##.........
................................
"""
EMBLEM_FLAME = """
..............##..............
.............###..............
............####..............
...........#####....#.........
..........######...##.........
.........#######..###.........
........#########.###.........
........##############........
.......################.......
......#################.......
......##################......
.....###################......
.....########.##########......
.....#######...#########......
.....######.....########......
.....######.....#######.......
......#####.....######........
.......#####...######.........
........############..........
..........########............
"""


def emblem(art):
    rows = [r for r in art.strip("\n").split("\n")]
    m = np.zeros((len(rows), max(len(r) for r in rows)), bool)
    for y, r in enumerate(rows):
        for x, ch in enumerate(r):
            m[y, x] = ch == "#"
    return m


class Boss:
    name = "base"
    W, H = 228, 26               # the back/over sprites (GUI px)
    FX, FY, FW, FH = 22, 8, 188, 9   # the fill: where it sits in the back, its size
    TIP = (6, 13)                # tip sprite w, h (GUI px); its top sits at FY - (h - FH) // 2
    name_col, name_outline = "F4E8CC", "140E08"
    pct = None                   # (colour, outline or 'none', dx, dy, align)

    def __init__(self):
        self.T = S

    # sprite canvases at 2x
    def canvas(self, w, h):
        return np.zeros((h * S, w * S, 4), np.uint8)

    def back(self):
        raise NotImplementedError

    def fill(self):
        raise NotImplementedError

    def tip(self):
        return None

    def over(self):
        return None

    def vanilla(self, full):
        """The plain 182 x 5 strip for when the hook is absent: the fill's middle rows, keylined."""
        f = self.fill()
        h = f.shape[0]
        a = np.zeros((10, 364, 4), np.uint8)
        rect(a, 0, 0, 364, 10, (18, 10, 12))
        if full:
            src = np.asarray(Image.fromarray(f).resize((360, 8), Image.NEAREST))
            a[1:9, 2:362] = src
        else:
            src = np.asarray(Image.fromarray(self.back()).crop(
                (self.FX * S, self.FY * S, (self.FX + self.FW) * S, (self.FY + self.FH) * S)).resize((360, 8),
                                                                                                  Image.NEAREST))
            a[1:9, 2:362] = src
        a[..., 3] = np.where(a[..., 3] > 0, 255, 0)
        return a

    def sheet(self):
        sh = np.zeros((256 * S, 256 * S, 4), np.uint8)
        bk = self.back()
        sh[0:bk.shape[0], 0:bk.shape[1]] = bk
        f = self.fill()
        sh[48 * S:48 * S + f.shape[0], 0:f.shape[1]] = f
        t = self.tip()
        if t is not None:
            sh[72 * S:72 * S + t.shape[0], 0:t.shape[1]] = t
        o = self.over()
        if o is not None:
            sh[96 * S:96 * S + o.shape[0], 0:o.shape[1]] = o
        return Image.fromarray(sh)

    def properties(self):
        s = ("text.boss=%s\nqf.boss.outline=%s\n" % (self.name_col, self.name_outline) +
             "qf.boss.sheet=%s\nqf.boss.top=%d\nqf.boss.namey=2\nqf.boss.fade=20\n" % (BOSS_SHEET, BOSS_TOP) +
             "qf.boss.back=0,0,%d,%d\n" % (self.W, self.H) +
             "qf.boss.fill=0,48,%d,%d,%d,%d\n" % (self.FW, self.FH, self.FX, self.FY))
        if self.tip() is not None:
            tw, th = self.TIP
            s += "qf.boss.tip=0,72,%d,%d,%d\n" % (tw, th, self.FY - (th - self.FH) // 2)
        if self.over() is not None:
            s += "qf.boss.over=0,96,%d,%d\n" % (self.W, self.H)
        if self.pct:
            s += "qf.boss.pct=%s,%s,%d,%d,%s\n" % self.pct
        return s

    # ---- shared painters (texel space)
    def sheen_fill(self, ramp_v, stripe=(255, 255, 255), stripe_al=26, hi=None, lo=None, period=28, band=10):
        """The fill: a vertical ramp, slanted lighter bands (stepped every 2 texels), a highlight row, a shadow row."""
        w, h = self.FW * S, self.FH * S
        a = np.zeros((h, w, 4), np.uint8)
        for y in range(h):
            col = ramp(ramp_v, y / (h - 1))
            a[y, :] = C(col)
        for y in range(h):
            for x in range(w):
                if ((x + (h - y) // 2 * 1) // 2 * 2) % period < band:
                    c = a[y, x]
                    a[y, x] = C(mix(tuple(int(v) for v in c[:3]), stripe, stripe_al / 255))
        if hi:
            rect(a, 0, 1, w, 2, hi)
        if lo:
            rect(a, 0, h - 1, w, h, lo)
        return a

    def channel(self, a, ramp_v, stripe=(255, 255, 255), stripe_al=10, period=28, band=10):
        x0, y0 = self.FX * S, self.FY * S
        w, h = self.FW * S, self.FH * S
        for y in range(h):
            col = ramp(ramp_v, y / (h - 1))
            rect(a, x0, y0 + y, x0 + w, y0 + y + 1, col)
        for y in range(h):
            for x in range(w):
                if ((x + (h - y) // 2) // 2 * 2) % period < band:
                    blend_px(a, x0 + x, y0 + y, stripe, stripe_al)

    def rails(self, a, x0, x1, top_rows, bot_rows):
        """top_rows / bot_rows: lists of colours, one per texel row, outward to inward for top (y going down)."""
        y = self.FY * S - len(top_rows)
        for c in top_rows:
            rect(a, x0, y, x1, y + 1, c)
            y += 1
        y = (self.FY + self.FH) * S
        for c in bot_rows:
            rect(a, x0, y, x1, y + 1, c)
            y += 1

    def ticks(self, a, col, al=255, h=2):
        """Quarter ticks on the rails (over the fill: only on the rails)."""
        for q in (0.25, 0.5, 0.75):
            x = int(round((self.FX + self.FW * q) * S)) - 1
            yt = self.FY * S - 4
            yb = (self.FY + self.FH) * S
            rect(a, x, yt, x + 2, yt + h * 2 - 1, col, al)
            rect(a, x, yb + 1, x + 2, yb + 1 + h * 2 - 1, col, al)


class Gilded(Boss):
    name = "gilded"
    W, H = 228, 30
    FX, FY, FW, FH = 24, 8, 182, 9
    TIP = (5, 13)
    name_col, name_outline = "F8E6B8", "2A0810"
    pct = ("F6D88E", "none", 207, 21, "R")
    MED = (13, 12.5, 12.5)          # medallion centre x, y, radius (GUI px)
    GOLD = [(255, 246, 204), (246, 214, 140), (214, 168, 84), (160, 112, 46), (98, 64, 24)]

    def back(self):
        a = self.canvas(self.W, self.H)
        x0, x1 = (self.FX - 4) * S, (self.FX + self.FW) * S
        # drop shadow under the tube
        rect(a, x0, (self.FY + self.FH + 2) * S + 1, x1 + 8, (self.FY + self.FH + 2) * S + 3, (10, 4, 6), 120)
        self.channel(a, [(60, 10, 24), (40, 6, 16), (28, 4, 12)], stripe=(255, 120, 140), stripe_al=8)
        G = self.GOLD
        self.rails(a, x0, x1, [(60, 36, 14), G[1], G[0], G[2], (110, 70, 26)],
                   [(110, 70, 26), G[2], G[1], G[3], (60, 36, 14)])
        # the pointed end (right): a gold chevron that closes the tube
        px0 = (self.FX + self.FW) * S
        cy = (self.FY * S + (self.FY + self.FH) * S) / 2
        half = (self.FH * S) / 2 + 5
        for x in range(0, 22):
            hh = half - x * (half / 21)
            for y in range(int(cy - hh), int(math.ceil(cy + hh))):
                d = abs(y + 0.5 - cy)
                col = G[1] if (y + 0.5 < cy) else G[3]
                if d > hh - 2.2:
                    col = (60, 36, 14)
                elif x < 4:
                    col = G[0] if y + 0.5 < cy else G[2]
                blend_px(a, px0 + x, y, col, 255)
        # the percent tab, hanging under the bar's right end
        tx0, tx1 = 170 * S, 210 * S
        ty0, ty1 = (self.FY + self.FH + 2) * S, (self.FY + self.FH + 13) * S
        tm = chamfer(tx1 - tx0, ty1 - ty0, 6)
        tm[:6] = True
        t = np.zeros(tm.shape + (4,), np.uint8)
        paint_mask(t, tm, (44, 8, 20), 245)
        k, _ = ring_of(tm, 2)
        k[:2] = False
        paint_mask(t, k, G[2])
        over(a, t, tx0, ty0)
        return a

    def fill(self):
        return self.sheen_fill([(248, 92, 96), (214, 44, 60), (168, 22, 46), (120, 12, 34)],
                               stripe=(255, 190, 190), stripe_al=40, hi=(255, 168, 160), lo=(90, 8, 26))

    def tip(self):
        tw, th = self.TIP
        a = self.canvas(tw, th)
        G = self.GOLD
        for y in range(th * S):
            for x in range(tw * S):
                d = abs(y + 0.5 - th * S / 2)
                if d > th * S / 2 - 1:
                    continue
                if 3 <= x <= 6:
                    col = G[0] if x in (3, 4) else G[2]
                    if d > th * S / 2 - 3:
                        col = G[3]
                    a[y, x] = C(col)
                elif x < 3:
                    a[y, x] = C((255, 220, 180), 110 if x == 2 else 50)
        return a

    def over(self):
        a = self.canvas(self.W, self.H)
        self.ticks(a, (98, 64, 24), 200)
        cx, cy, r = [v * S for v in self.MED]
        w, h = a.shape[1], a.shape[0]
        d = disc(w, h, cx, cy, r)
        ring, inner = ring_of(d, 5)
        yy, xx = np.mgrid[0:h, 0:w]
        G = self.GOLD
        lit = ((xx - cx) * 0.6 + (yy - cy) * 0.8) / r
        t = np.zeros((h, w, 4), np.uint8)
        for y, x in zip(*np.nonzero(ring)):
            rr = math.hypot(x + 0.5 - cx, y + 0.5 - cy) / r
            l = lit[y, x]
            k = 0.15 + 0.35 * (l + 1) if rr > 0.86 else 0.85 - 0.35 * (l + 1)
            if rr > 0.97 or (0.8 < rr < 0.84):
                t[y, x] = C((60, 36, 14))
            else:
                t[y, x] = C(quant(G, k))
        for y, x in zip(*np.nonzero(inner)):
            l = lit[y, x]
            t[y, x] = C(ramp([(84, 16, 34), (56, 8, 22), (34, 4, 14)], 0.5 + 0.5 * l))
        over(a, t)
        sk = emblem(EMBLEM_SKULL)
        e = np.zeros(sk.shape + (4,), np.uint8)
        k2 = edge(sk)
        e[sk] = C(G[1])
        lowr = np.zeros_like(sk)
        lowr[sk.shape[0] // 2:] = True
        e[sk & lowr] = C(G[2])
        e[k2] = C(G[3])
        e[sk & ~k2 & np.roll(~sk, 1, 0)] = C(G[0])
        over(a, e, int(cx - sk.shape[1] / 2), int(cy - sk.shape[0] / 2) + 1)
        return a


class Obsidian(Boss):
    name = "obsidian"
    W, H = 232, 24
    FX, FY, FW, FH = 24, 7, 186, 9
    TIP = (6, 15)
    name_col, name_outline = "F4E6FF", "1A0828"
    pct = ("FFFFFF", "2A0620", 205, 8, "R")
    AM = [(250, 230, 255), (214, 160, 252), (160, 98, 224), (100, 54, 160), (52, 26, 88)]

    def back(self):
        a = self.canvas(self.W, self.H)
        x0, x1 = (self.FX - 4) * S, (self.FX + self.FW) * S
        self.channel(a, [(40, 10, 34), (26, 6, 24), (16, 4, 16)], stripe=(220, 120, 255), stripe_al=10)
        A = self.AM
        self.rails(a, x0, x1, [(10, 6, 16), (34, 24, 50), (190, 140, 250), (24, 16, 36), (8, 4, 12)],
                   [(8, 4, 12), (24, 16, 36), (60, 40, 96), (34, 24, 50), (10, 6, 16)])
        # a lilac specular streak on the top rail
        rect(a, x0 + 40, self.FY * S - 3, x0 + 140, self.FY * S - 2, (240, 210, 255))
        # the spiked end: three crystal shards
        ex = (self.FX + self.FW) * S
        cy = (self.FY * S + (self.FY + self.FH) * S) // 2
        shards = [(0, 0, 26, 7), (-2, -9, 16, 4), (-2, 9, 16, 4)]
        for (dx, dy, ln, hw) in shards:
            for x in range(ln):
                hh = hw * (1 - x / ln)
                for y in range(int(cy + dy - hh), int(math.ceil(cy + dy + hh)) + 1):
                    top = y + 0.5 < cy + dy
                    col = A[1] if top else A[3]
                    if abs(y + 0.5 - cy - dy) > hh - 1.5:
                        col = (16, 8, 28)
                    blend_px(a, ex + dx + x, y, col, 255)
        return a

    def fill(self):
        return self.sheen_fill([(255, 120, 190), (236, 56, 128), (180, 22, 92), (110, 8, 60)],
                               stripe=(255, 210, 240), stripe_al=46, hi=(255, 196, 230), lo=(70, 6, 44))

    def tip(self):
        tw, th = self.TIP
        a = self.canvas(tw, th)
        A = self.AM
        cx, cy = tw * S / 2, th * S / 2
        for y in range(th * S):
            for x in range(tw * S):
                d = abs(x + 0.5 - cx) / (tw * S / 2) + abs(y + 0.5 - cy) / (th * S / 2)
                if d <= 1:
                    col = A[0] if (x + 0.5 < cx and y + 0.5 < cy) else A[1] if y + 0.5 < cy else A[2]
                    if d > 0.8:
                        col = (40, 18, 70)
                    a[y, x] = C(col)
        return a

    def over(self):
        a = self.canvas(self.W, self.H)
        self.ticks(a, (190, 140, 250), 140)
        A = self.AM
        # an octagonal amethyst socket at the left end
        s = 24 * S
        m = chamfer(s, s, 7 * 2)
        k, inner = ring_of(m, 4)
        t = np.zeros((s, s, 4), np.uint8)
        yy, xx = np.mgrid[0:s, 0:s]
        lit = ((xx - s / 2) * 0.6 + (yy - s / 2) * 0.8) / (s / 2)
        for y, x in zip(*np.nonzero(k)):
            outer = not (inner[y, x])
            t[y, x] = C(quant(A, 0.2 + 0.35 * (lit[y, x] + 1)))
        ok = edge(m)
        t[ok] = C((14, 6, 24))
        for y, x in zip(*np.nonzero(inner)):
            t[y, x] = C(ramp([(54, 20, 70), (30, 10, 44), (16, 4, 26)], 0.5 + 0.5 * lit[y, x]))
        # the slit eye
        cx, cy = s / 2, s / 2
        for y in range(s):
            for x in range(s):
                u, v = (x + 0.5 - cx) / 10.5, (y + 0.5 - cy)
                hh = 6.0 * max(0.0, 1 - u * u) ** 1.2          # an almond: pointed at both ends
                if abs(u) < 1 and abs(v) < hh and inner[y, x]:
                    edge_eye = abs(v) > hh - 1.2
                    t[y, x] = C((150, 30, 100) if edge_eye else (255, 150, 206) if v < 0 else (236, 80, 150))
                    if abs(x + 0.5 - cx) < 1.6 and abs(v) < hh - 0.8:
                        t[y, x] = C((30, 4, 24))
        over(a, t, 0, 0)
        return a


class Ironclad(Boss):
    name = "ironclad"
    W, H = 232, 24
    FX, FY, FW, FH = 24, 7, 178, 9
    TIP = (4, 13)
    name_col, name_outline = "F2F2F2", "141416"
    pct = ("F4F4F4", "16181C", 217, 8, "C")
    ST = [(240, 244, 250), (190, 196, 206), (136, 142, 154), (88, 94, 106), (46, 50, 58)]

    def back(self):
        a = self.canvas(self.W, self.H)
        x0, x1 = (self.FX - 4) * S, (self.FX + self.FW) * S
        self.channel(a, [(52, 14, 16), (34, 8, 10), (22, 6, 8)], stripe=(255, 255, 255), stripe_al=0)
        T = self.ST
        self.rails(a, x0, x1, [(20, 22, 26), T[2], T[1], T[2], T[3], (24, 26, 30)],
                   [(24, 26, 30), T[3], T[2], T[3], T[4], (20, 22, 26)])
        # rivets on the rails
        for xg in range(self.FX + 10, self.FX + self.FW - 4, 24):
            for yy in (self.FY * S - 5, (self.FY + self.FH) * S + 2):
                rect(a, xg * S, yy, xg * S + 3, yy + 3, T[3])
                rect(a, xg * S, yy, xg * S + 2, yy + 2, T[0])
        # the end clamp holding the percent
        cx0, cx1 = (self.FX + self.FW - 1) * S, (self.W - 1) * S
        cy0, cy1 = 2 * S, (self.H - 2) * S
        cm = chamfer(cx1 - cx0, cy1 - cy0, 4)
        t = np.zeros(cm.shape + (4,), np.uint8)
        paint_mask(t, cm, (44, 48, 56))
        k, inner = ring_of(cm, 2)
        top = np.zeros(cm.shape, bool)
        top[:cm.shape[0] // 2] = True
        paint_mask(t, k & top, T[1])
        paint_mask(t, k & ~top, (18, 20, 24))
        win = np.zeros(cm.shape, bool)
        win[8:-8, 6:-6] = True
        paint_mask(t, win & inner, (20, 22, 26))
        over(a, t, cx0, cy0)
        return a

    def fill(self):
        a = self.sheen_fill([(236, 80, 70), (196, 30, 34), (150, 16, 24), (100, 8, 16)],
                            stripe=(255, 200, 190), stripe_al=0, hi=(255, 150, 136), lo=(70, 6, 12))
        for k in range(1, 10):                       # cut into tenths
            x = int(round(self.FW * S * k / 10))
            rect(a, x - 1, 0, x + 1, a.shape[0], (60, 6, 12))
        return a

    def tip(self):
        tw, th = self.TIP
        a = self.canvas(tw, th)
        T = self.ST
        for y in range(th * S):
            for x in range(2, 6):
                a[y, x] = C(T[0] if x == 2 else T[1] if x < 5 else T[3])
        rect(a, 2, 0, 6, 1, (20, 22, 26))
        rect(a, 2, th * S - 1, 6, th * S, (20, 22, 26))
        return a

    def over(self):
        a = self.canvas(self.W, self.H)
        self.ticks(a, (240, 244, 250), 160)
        T = self.ST
        # a heater shield at the left end
        w, h = 22 * S, 24 * S
        m = np.zeros((h, w), bool)
        for y in range(h):
            if y < h * 0.5:
                hw = w / 2
            else:
                tt = (y - h * 0.5) / (h * 0.5)
                hw = (w / 2) * math.sqrt(max(0, 1 - tt * tt))
            for x in range(w):
                if abs(x + 0.5 - w / 2) <= hw:
                    m[y, x] = True
        k, inner = ring_of(m, 3)
        t = np.zeros((h, w, 4), np.uint8)
        for y, x in zip(*np.nonzero(k)):
            l = (x - w / 2) * 0.6 + (y - h / 2) * 0.8
            t[y, x] = C(T[1] if l < -4 else T[2] if l < 6 else T[3])
        t[edge(m)] = C((18, 20, 24))
        for y, x in zip(*np.nonzero(inner)):
            t[y, x] = C(ramp([(190, 34, 36), (140, 18, 24), (96, 10, 16)], y / h))
        # a steel chevron
        for y, x in zip(*np.nonzero(inner)):
            yy = y - h * 0.32
            if abs(yy - abs(x + 0.5 - w / 2) * 0.7) < 2.2:
                t[y, x] = C(T[0] if x < w / 2 else T[1])
        over(a, t, 1 * S, 0)
        return a


class Ember(Boss):
    name = "ember"
    W, H = 236, 24
    FX, FY, FW, FH = 22, 7, 180, 9
    TIP = (6, 13)
    name_col, name_outline = "FFE6B8", "2A1006"
    pct = ("FFD890", "2A1006", 212, 8, "L")
    BR = [(246, 200, 140), (196, 138, 76), (140, 90, 44), (90, 54, 24), (46, 28, 12)]

    def back(self):
        a = self.canvas(self.W, self.H)
        x0, x1 = (self.FX - 4) * S, (self.FX + self.FW) * S
        self.channel(a, [(50, 20, 10), (34, 12, 6), (22, 8, 4)], stripe=(255, 140, 60), stripe_al=8)
        B = self.BR
        self.rails(a, x0, x1, [(18, 10, 6), B[2], B[1], B[3], (26, 14, 8)],
                   [(26, 14, 8), B[3], B[2], B[4], (18, 10, 6)])
        # the point (right)
        px0 = (self.FX + self.FW) * S
        cy = (self.FY * S + (self.FY + self.FH) * S) / 2
        half = (self.FH * S) / 2 + 4
        for x in range(0, 18):
            hh = half - x * (half / 17)
            for y in range(int(cy - hh), int(math.ceil(cy + hh))):
                col = B[1] if y + 0.5 < cy else B[3]
                if abs(y + 0.5 - cy) > hh - 2:
                    col = (18, 10, 6)
                blend_px(a, px0 + x, y, col, 255)
        return a

    def fill(self):
        w, h = self.FW * S, self.FH * S
        a = np.zeros((h, w, 4), np.uint8)
        rv = [(255, 214, 120), (255, 246, 200), (255, 196, 80), (240, 120, 36), (190, 56, 20), (120, 20, 10)]
        for y in range(h):
            a[y, :] = C(ramp(rv, y / (h - 1)))
        for y in range(h):
            for x in range(w):
                if ((x + (h - y) // 2) // 2 * 2) % 34 < 8:
                    c = a[y, x]
                    a[y, x] = C(mix(tuple(int(v) for v in c[:3]), (255, 250, 220), 0.22))
        rect(a, 0, h - 1, w, h, (90, 14, 6))
        return a

    def tip(self):
        tw, th = self.TIP
        a = self.canvas(tw, th)
        for y in range(th * S):
            d = abs(y + 0.5 - th * S / 2) / (th * S / 2)
            for x in range(tw * S):
                dx = abs(x + 0.5 - tw * S / 2)
                if dx < 1.5 and d < 0.86:
                    a[y, x] = C((255, 252, 230))
                elif dx < 3.5 and d < 0.92:
                    a[y, x] = C((255, 200, 90), 190)
                elif d < 0.95:
                    a[y, x] = C((255, 140, 40), 70)
        return a

    def over(self):
        a = self.canvas(self.W, self.H)
        self.ticks(a, (40, 22, 10), 220)
        B = self.BR
        cx, cy, r = 11.5 * S, 12 * S, 11.5 * S
        w, h = a.shape[1], a.shape[0]
        d = disc(w, h, cx, cy, r)
        ring, inner = ring_of(d, 4)
        t = np.zeros((h, w, 4), np.uint8)
        yy, xx = np.mgrid[0:h, 0:w]
        lit = ((xx - cx) * 0.6 + (yy - cy) * 0.8) / r
        for y, x in zip(*np.nonzero(ring)):
            t[y, x] = C(quant(B, 0.15 + 0.35 * (lit[y, x] + 1)))
        t[edge(d)] = C((18, 10, 6))
        for y, x in zip(*np.nonzero(inner)):
            t[y, x] = C(ramp([(60, 22, 10), (34, 12, 6), (20, 8, 4)], 0.5 + 0.5 * lit[y, x]))
        over(a, t)
        fl = emblem(EMBLEM_FLAME)
        e = np.zeros(fl.shape + (4,), np.uint8)
        ys, xs = np.nonzero(fl)
        for y, x in zip(ys, xs):
            tt = y / fl.shape[0]
            e[y, x] = C(ramp([(255, 120, 40), (255, 180, 60), (255, 236, 160), (255, 252, 230)], tt))
        e[edge(fl)] = C((150, 40, 10))
        over(a, e, int(cx - fl.shape[1] / 2), int(cy - fl.shape[0] / 2))
        return a


BOSSES = {c.name: c for c in (Gilded, Obsidian, Ironclad, Ember)}


# =============================================================================================== sheets / zip
def _read(zp, name, prefix=G):
    with zipfile.ZipFile(zp) as z:
        return Image.open(io.BytesIO(z.read(prefix + name))).convert("RGBA")


def build(design, gui_zip=GUI_ZIP, qf_zip=QF_ZIP):
    d = HUDS[design]()
    return d, d.icons(_read(gui_zip, "icons.png")), d.widgets(_read(qf_zip, "widgets.png")), BOSSES[d.boss]().sheet()


def write_zip(design, out, gui_zip=GUI_ZIP, qf_zip=QF_ZIP):
    d, ic, wd, bs = build(design, gui_zip, qf_zip)
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("pack.mcmeta", '{"pack": {"pack_format": 1, "description": "QF r016 HUD: %s + %s"}}'
                   % (design, d.boss))
        for n, im in (("icons.png", ic), ("widgets.png", wd), ("qf_bossbar.png", bs)):
            bb = io.BytesIO()
            im.save(bb, "PNG")
            z.writestr(G + n, bb.getvalue())
        z.writestr("assets/minecraft/mcpatcher/color.properties", d.color_properties())
    print("hud r016 %s + %s -> %s" % (design, d.boss, out))


# =============================================================================================== offline mock
def backdrop(W, H, night=False):
    if not night:
        return b.backdrop(W, H)
    a = np.zeros((H, W, 4), np.uint8)
    for y in range(H):
        a[y, :] = C(mix((8, 10, 22), (22, 26, 44), y / H))
    rng = np.random.default_rng(3)
    for _ in range(W * H // 900):
        x, y = rng.integers(0, W), rng.integers(0, int(H * 0.5))
        a[y, x] = C((200, 205, 230))
    g0 = int(H * 0.55)
    for y in range(g0, H, 4):
        for x in range(0, W, 4):
            n = rng.integers(-6, 7)
            a[y:y + 4, x:x + 4] = C((24 + n, 36 + n, 22 + n // 2))
    return a


def draw_boss(im, d, bb, sheet, font, gw, hp):
    """Emulates XpBarStyle bar mode (back, fill cut to hp, tip, over, percent, outlined name)."""
    sh = np.asarray(sheet)

    def spr(u, v, w, h):
        return sh[v * S:(v + h) * S, u * S:(u + w) * S]

    x0 = gw // 2 - bb.W // 2
    y0 = BOSS_TOP
    over(im, spr(0, 0, bb.W, bb.H), x0 * S, y0 * S)
    fw = int(round(bb.FW * hp * S))
    if fw > 0:
        over(im, sh[48 * S:(48 + bb.FH) * S, 0:fw], (x0 + bb.FX) * S, (y0 + bb.FY) * S)
    if bb.tip() is not None and hp > 0:
        tw, th = bb.TIP
        tx = int(round(x0 + bb.FX + bb.FW * hp - tw / 2))
        over(im, spr(0, 72, tw, th), tx * S, (y0 + bb.FY - (th - bb.FH) // 2) * S)
    if bb.over() is not None:
        over(im, spr(0, 96, bb.W, bb.H), x0 * S, y0 * S)
    out = Image.fromarray(im)
    if bb.pct:
        col, ol, dx, dy, al = bb.pct
        t = "%d%%" % math.ceil(hp * 100 - 0.001)
        tw = font.width(t)
        tx = x0 + dx - (tw if al == "R" else tw // 2 if al == "C" else 0)
        ty = y0 + dy
        if ol != "none":
            for ddx, ddy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                out = font.draw(out, t, tx + ddx, ty + ddy, b.hexc(ol))
        out = font.draw(out, t, tx, ty, b.hexc(col))
    name = "Ender Dragon"
    nx = gw // 2 - font.width(name) // 2
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dx or dy:
                out = font.draw(out, name, nx + dx, 2 + dy, b.hexc(bb.name_outline))
    out = font.draw(out, name, nx, 2, b.hexc(bb.name_col))
    im[:] = np.asarray(out)


def mock(design, health=15, last=None, food=20, armor=13, xpf=0.62, boss=0.62, level=27, air=None, sel=0,
         font=None, items=None, gui_w=260, gui_h=112, night=False, boss_name=None):
    d, icons, widgets, bsheet = build(design)
    bb = BOSSES[boss_name or d.boss]()
    if boss_name:
        bsheet = bb.sheet()
    ic, wd = np.asarray(icons), np.asarray(widgets)
    W, H = gui_w * S, gui_h * S
    im = backdrop(W, H, night)
    font = font or b.Font()
    gw, gh = gui_w, gui_h

    def blit(sheet, u, v, w, h, x, y, blend=True):
        tile = sheet[v * S:(v + h) * S, u * S:(u + w) * S]
        if blend:
            over(im, tile, x * S, y * S)
        else:
            m = tile[..., 3] > 25
            reg = im[y * S:(y + h) * S, x * S:(x + w) * S]
            reg[m] = tile[m]

    draw_boss(im, d, bb, bsheet, font, gw, boss)
    left = gw // 2 - 91
    top = gh - 39
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
    blit(ic, 0, 64, 182, 5, left, gh - 29, blend=False)
    k = int(xpf * 183)
    if k:
        blit(ic, 0, 69, k, 5, left, gh - 29, blend=False)
    blit(wd, 0, 0, 182, 22, left, gh - 22)
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
            out = font.draw(out, t, x + dx, y + dy, b.hexc(d.xp_outline))
        out = font.draw(out, t, x, y, b.hexc(d.xp_num))
        im[:] = np.asarray(out)
    return Image.fromarray(im)


def gui1(im):
    """What GUI scale 1 samples from a 2x render (odd texels), shown 4x."""
    a = np.asarray(im)
    one = Image.fromarray(np.ascontiguousarray(a[1::2, 1::2]))
    return one.resize((one.width * 4, one.height * 4), Image.NEAREST)


def stack(tiles, bg=(12, 12, 12, 255)):
    W = max(t.width for t in tiles)
    out = Image.new("RGBA", (W, sum(t.height for t in tiles)), bg)
    y = 0
    for t in tiles:
        out.paste(t, (0, y))
        y += t.height
    return out


def side(a, bb_):
    g = Image.new("RGBA", (a.width + bb_.width, max(a.height, bb_.height)))
    g.paste(a, (0, 0))
    g.paste(bb_, (a.width, 0))
    return g


def mock_sheet(path, icons_path=None, boss_path=None):
    font = b.Font()
    items = b._items()
    tiles = []
    for dn in DESIGNS:
        a = mock(dn, font=font, items=items)
        c = mock(dn, health=9, last=15, food=7, armor=7, xpf=0.2, boss=0.25, level=104, air=6, sel=4, font=font,
                 items=items, night=True)
        g2 = side(a, c).resize(((a.width + c.width) * 2, a.height * 2), Image.NEAREST)
        tiles.append(b.label(g2, "%s   (GUI scale 4; left: day; right: night, just hit, under water)" % TITLES[dn],
                             font))
        tiles.append(b.label(gui1(side(a, c)), "%s at GUI scale 1, shown 4x" % TITLES[dn], font))
    stack(tiles).convert("RGB").save(path)
    print("mock ->", path)
    if boss_path:
        rows = []
        for bn in ("ember", "obsidian", "ironclad", "gilded"):
            dn = [k for k, v in BOSS_OF.items() if v == bn][0]
            ims = []
            for night, hp in ((False, 0.62), (True, 0.62), (False, 0.08), (True, 1.0)):
                im = np.asarray(Image.new("RGBA", (260 * S, 52 * S))).copy()
                im[:] = backdrop(260 * S, 112 * S, night)[:52 * S]
                bb = BOSSES[bn]()
                draw_boss(im, None, bb, bb.sheet(), font, 260, hp)
                ims.append(Image.fromarray(im))
            r = side(side(ims[0], ims[1]), side(ims[2], ims[3]))
            rows.append(b.label(r.resize((r.width * 2, r.height * 2), Image.NEAREST),
                                "%s: 62%% day, 62%% night, 8%% day, 100%% night (GUI scale 4)" % BOSS_TITLES[bn],
                                font))
            rows.append(b.label(gui1(r), "%s at GUI scale 1, shown 4x" % BOSS_TITLES[bn], font))
        stack(rows).convert("RGB").save(boss_path)
        print("boss ->", boss_path)
    if icons_path:
        rows = []
        for dn in DESIGNS:
            d, icn, wd, _ = build(dn)
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
            row = Image.fromarray(bg).resize((row.width * 6, row.height * 6), Image.NEAREST)
            rows.append(b.label(row, TITLES[dn] + ": heart row, blink, full, half, lost, absorb; armour; food; air; "
                                                  "medallion", font, scale=4))
        stack(rows).convert("RGB").save(icons_path)
        print("icons ->", icons_path)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--design", choices=DESIGNS)
    ap.add_argument("--out")
    ap.add_argument("--gui-zip", default=GUI_ZIP)
    ap.add_argument("--qf-zip", default=QF_ZIP)
    ap.add_argument("--mock")
    ap.add_argument("--icons")
    ap.add_argument("--boss")
    a = ap.parse_args()
    if a.mock:
        mock_sheet(a.mock, a.icons, a.boss)
        return
    write_zip(a.design, a.out, a.gui_zip, a.qf_zip)


if __name__ == "__main__":
    main()
