#!/usr/bin/env python3
"""Paint Quest Forge's own 32x horror mob skins for the Krypt page (site/graves/tex/mobs/).

    /usr/local/bin/python3.11 -I tools/textures/mobs/paint_mobs.py            # write the skins
    /usr/local/bin/python3.11 -I tools/textures/mobs/paint_mobs.py --preview DIR   # and upscaled previews

Original art. Every pixel comes from this script: procedural shading (value noise quantised onto hand-picked
colour ramps, lit from above) plus hand-authored pixel grids for the faces and wounds. No Mojang, Patrix or other
pack pixels are read. The 1.7.10 sheets were only used for their UV layout, which is encoded below as model boxes
(u, v, w, h, d in 1x texels, doubled here: the zombie sheet is 128x128, the spider and its eyes 128x64).
"""
import argparse
import math
import os
import random

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
OUT = os.path.join(ROOT, "site", "graves", "tex", "mobs")
S = 2  # scale over the vanilla 16x layout


def H(s):
    s = s.lstrip("#")
    return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16), 255)


def ramp(*hexes):
    return [H(h) for h in hexes]


def mix(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3)) + (255,)


# ---------------------------------------------------------------------------------------------- noise
class Noise:
    def __init__(self, seed):
        self.seed = seed & 0x7FFFFFFF

    def lat(self, ix, iy, o):
        h = (ix * 374761393 + iy * 668265263 + self.seed * 1442695041 + o * 1274126177) & 0xFFFFFFFF
        h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
        return ((h ^ (h >> 16)) & 0xFFFF) / 65535.0

    def val(self, x, y, o=0):
        ix, iy = math.floor(x), math.floor(y)
        tx, ty = x - ix, y - iy
        sx, sy = tx * tx * (3 - 2 * tx), ty * ty * (3 - 2 * ty)
        a = self.lat(ix, iy, o) * (1 - sx) + self.lat(ix + 1, iy, o) * sx
        b = self.lat(ix, iy + 1, o) * (1 - sx) + self.lat(ix + 1, iy + 1, o) * sx
        return a * (1 - sy) + b * sy

    def fbm(self, x, y, octs=((5.0, 0.5), (2.5, 0.3), (1.0, 0.2)), sx=1.0, sy=1.0):
        return sum(w * self.val(x / (s * sx), y / (s * sy), i) for i, (s, w) in enumerate(octs))


# ---------------------------------------------------------------------------------------------- sheet
class Sheet:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        self.px = self.img.load()
        self.locked = set()  # hand-placed pixels the cleanup pass leaves alone

    def put(self, x, y, c, lock=False):
        if c is None or not (0 <= x < self.w and 0 <= y < self.h):
            return
        self.px[x, y] = c
        if lock:
            self.locked.add((x, y))

    def get(self, x, y):
        return self.px[x, y]


def box(u, v, w, h, d):
    """The six face rectangles (x, y, w, h) of a 1.7.10 ModelBox at 2x."""
    u, v, w, h, d = (a * S for a in (u, v, w, h, d))
    return {"top": (u + d, v, w, d), "bottom": (u + d + w, v, w, d), "right": (u, v + d, d, h),
            "front": (u + d, v + d, w, h), "left": (u + d + w, v + d, d, h), "back": (u + 2 * d + w, v + d, w, h)}


def fill(sh, rect, fn):
    x0, y0, w, h = rect
    for ly in range(h):
        for lx in range(w):
            sh.put(x0 + lx, y0 + ly, fn(lx, ly, w, h, x0 + lx, y0 + ly))


def material(rmp, nz, base, amp, light=0.0, grain=None, sx=1.0, sy=1.0, octs=None, edge=0.0, dark_bottom=0.0):
    """A shading function: noise around `base` (ramp index), lit from the top of the face, darker at its edges."""
    def f(lx, ly, w, h, X, Y):
        n = nz.fbm(X, Y, octs or ((5.0, 0.5), (2.5, 0.3), (1.0, 0.2)), sx, sy) - 0.5
        v = base + n * amp * 2
        if h > 1:
            v += light * (0.5 - ly / (h - 1))
            v -= dark_bottom * max(0.0, ly / (h - 1) - 0.6) / 0.4
        if edge and (lx == 0 or ly == 0 or lx == w - 1 or ly == h - 1):
            v -= edge
        i = int(round(max(0, min(len(rmp) - 1, v))))
        return rmp[i]
    return f


def stamp(sh, x0, y0, rows, key, lock=True):
    """Hand-authored pixels: one string per row, '.' keeps what is there, other chars index `key`."""
    for j, row in enumerate(rows):
        for i, ch in enumerate(row):
            if ch == "." or ch == " ":
                continue
            c = key[ch]
            if callable(c):
                c = c(sh.get(x0 + i, y0 + j))
            sh.put(x0 + i, y0 + j, c, lock)


def cleanup(sh, rect, passes=1):
    """Pixel-art cleanup: a lone pixel whose four neighbours (inside the face) all share one colour joins them."""
    x0, y0, w, h = rect
    for _ in range(passes):
        changes = []
        for y in range(y0, y0 + h):
            for x in range(x0, x0 + w):
                if (x, y) in sh.locked:
                    continue
                nb = [sh.get(a, b) for a, b in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1))
                      if x0 <= a < x0 + w and y0 <= b < y0 + h]
                if len(nb) >= 3 and all(n == nb[0] for n in nb) and sh.get(x, y) != nb[0]:
                    changes.append((x, y, nb[0]))
        for x, y, c in changes:
            sh.put(x, y, c)


def shift(rmp, d):
    """A key entry that moves whatever is under it `d` steps along a ramp (by nearest colour)."""
    def f(c):
        i = min(range(len(rmp)), key=lambda k: sum((rmp[k][q] - c[q]) ** 2 for q in range(3)))
        return rmp[max(0, min(len(rmp) - 1, i + d))]
    return f


def walk(sh, rng, x, y, n, dirs, color_fn, rect, lock=False):
    """A 1px random walk (veins, cracks, hairs) kept inside rect."""
    x0, y0, w, h = rect
    pts = []
    for _ in range(n):
        if not (x0 <= x < x0 + w and y0 <= y < y0 + h):
            break
        if (x, y) not in sh.locked:
            sh.put(x, y, color_fn(sh.get(x, y)), lock)
        pts.append((x, y))
        dx, dy = rng.choice(dirs)
        x, y = x + dx, y + dy
    return pts


def blend_to(target, t):
    """A key entry that pulls whatever is under it a fraction t toward a colour (tints, stains)."""
    return lambda c: mix(c, target, t)


def check_grid(rows, w, name):
    bad = [i for i, r in enumerate(rows) if len(r) != w]
    if bad:
        raise SystemExit(f"{name}: rows {bad} are not {w} wide")


# ============================================================================================== ZOMBIE
ZSKIN = ramp("#11170e", "#1b2515", "#27341d", "#344528", "#435733", "#546a3e", "#68804c", "#7d955c")
ZBRUISE = H("#3a2f44")
ZSHIRT = ramp("#081615", "#0e2322", "#15312f", "#1c403d", "#26514d", "#31625d", "#3e746e", "#4f8781")
ZPANTS = ramp("#0c0b1a", "#141227", "#1c1934", "#252142", "#2f2a51", "#3a3461", "#474072")
ZSHOE = ramp("#100e0c", "#1a1714", "#25211c", "#312b24", "#3e372e", "#4c4438")
ZMUD = ramp("#16110c", "#1f1810", "#2a2015")
ZKEY = {
    "0": ZSKIN[0], "1": ZSKIN[1], "2": ZSKIN[2], "3": ZSKIN[3], "4": ZSKIN[4], "5": ZSKIN[5], "6": ZSKIN[6], "7": ZSKIN[7],
    "k": H("#060605"), "K": H("#100d0a"), "j": H("#1a1410"),
    "e": H("#7c7a62"), "E": H("#c9c6a6"), "i": H("#4a4830"),
    "t": H("#8c8769"), "T": H("#aba585"), "d": H("#57523d"),
    "m": H("#0e0303"), "M": H("#240806"),
    "g": H("#5c1f17"), "G": H("#7c2c20"), "f": H("#3a130f"),
    "r": H("#3e0a07"), "R": H("#6a130c"), "w": H("#9c2516"),
    "x": H("#8f8467"), "X": H("#bcb08b"), "z": H("#5a5140"),
    "a": ZSHIRT[0], "A": ZSHIRT[6], "n": ZPANTS[1], "N": ZPANTS[5],
    "b": blend_to(ZBRUISE, 0.45),
}

# The face (head front, 16x16), viewer's left first. Heavy lit brows over two deep sockets: on the left a pale dead
# eye in the dark, on the right nothing, and blood run from it down the cheek and chin. The nose is a cavity. The lips
# have rotted off: broken teeth clenched in a grin, upper row on row 11, lower on row 12, because the zombie scare cuts
# the jaw there (fnaf.js splitJaw, the head's bottom two 1x rows) and opens a real mouth between them. A gash in the
# forehead shows the bone.
ZFACE = [
    "................",
    "...........fg...",
    "..........fGXg..",
    "..........gXxf..",
    ".........fgxg...",
    "..5543.22.3455..",
    "3245665225665423",
    "21kkkk2112kkkk12",
    "31KeEK2332KkkK13",
    "32KkrK3kk3KkkK23",
    "4552432kk2345r54",
    "321dTtkTTdtTdr12",
    "21ktTdtkkTtdkr12",
    "321fgGfgfGgfgR12",
    "2321112221121r32",
    "1211.2112.1.r121",
]

# Torso front (16x24): blood from the mouth pooled at the collar and run down the shirt, a tear over the left ribs.
ZTORSO_FRONT = [
    "....rr54445r....",
    "...rrRr344rr....",
    "....rRrrr.r.....",
    "...r.rRr.r......",
    ".....r.r...aAAa.",
    ".....r.r..aK1kKA",
    ".....r..r.AzxXxa",
    "........r.a1k21A",
    "........r.KzxXxa",
    ".........aA2k11A",
    ".........AzxXxza",
    ".........a1kk2Aa",
    "..........aAkKa.",
    "...........aAa..",
] + ["................"] * 10

ZSCALP = [
    "................",
    "......jj....j...",
    "....j.j.j..j....",
    "...j..jj.fgf.j..",
    "..j.....gxXxg...",
    ".......fXXzXxg..",
    "........gxXzXf..",
    ".........fgxg...",
    "..........fg.j..",
    "..j..........j..",
    "...j........j...",
    "................",
    "................",
    "................",
    "................",
    "................",
]

ZEAR = [
    "..j.j..j..j.j...",
    "...j..j...j.....",
    "................",
    "................",
    "................",
    "................",
    "................",
    "........fgg.....",
    ".......fkkMg....",
    ".......gkkkG....",
    ".......fMkkg....",
    "........fgf.....",
    "................",
    "................",
    "................",
    "................",
]

ZBACK = [
    ".j..j.j..j..j.j.",
    "..j.j..jj..j.j..",
    ".j..jj.j..j..j..",
    "...j..j...j.....",
    "................",
    "..........fgf...",
    ".........fgRgf..",
    "..........gRf...",
    "...........r....",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
]


def paint_zombie():
    sh = Sheet(128, 128)
    rng = random.Random(7)
    nz = Noise(11)
    head = box(0, 0, 8, 8, 8)
    body = box(16, 16, 8, 12, 4)
    arm = box(40, 16, 4, 12, 4)
    leg = box(0, 16, 4, 12, 4)
    for g, n in ((ZFACE, "ZFACE"), (ZSCALP, "ZSCALP"), (ZEAR, "ZEAR"), (ZBACK, "ZBACK")):
        check_grid(g, 16, n)
    check_grid(ZTORSO_FRONT, 16, "ZTORSO_FRONT")

    skin = material(ZSKIN, nz, 3.6, 1.8, light=0.9)
    skin_dark = material(ZSKIN, nz, 2.8, 1.6, light=0.7)
    bruise_nz = Noise(23)

    def mottled(base_fn):
        """Dead skin: livid purple-grey patches tinted into the green, and darker rot in the hollows."""
        def f(lx, ly, w, h, X, Y):
            c = base_fn(lx, ly, w, h, X, Y)
            b = bruise_nz.fbm(X, Y, ((4.0, 0.7), (1.5, 0.3)))
            if b > 0.70:
                return mix(c, ZBRUISE, 0.35 if b < 0.76 else 0.55)
            if b < 0.25 and c in ZSKIN:
                return ZSKIN[max(0, ZSKIN.index(c) - 1)]
            return c
        return f

    # ---- head
    for name, r in head.items():
        fill(sh, r, mottled(skin if name in ("front", "top") else skin_dark))
    stamp(sh, *head["front"][:2], ZFACE, ZKEY)
    stamp(sh, *head["top"][:2], ZSCALP, ZKEY)
    stamp(sh, *head["right"][:2], ZEAR, ZKEY)
    stamp(sh, *head["left"][:2], [r[::-1] for r in ZEAR], ZKEY)
    stamp(sh, *head["back"][:2], ZBACK, ZKEY)
    # the chin's underside: the jaw's dark inside at the front edge (bottom rows face forward)
    bx, by, bw, bh = head["bottom"]
    stamp(sh, bx, by + 13, ["..1kmmmmmmmmk1..", "..2kmmmmmmmmk2..", "...2kkkkkkkk2..."], ZKEY)
    for side in ("right", "left", "back"):
        x0, y0, w, h = head[side]
        for _ in range(2):
            walk(sh, rng, x0 + rng.randrange(2, w - 2), y0 + rng.randrange(9, 13), rng.randrange(4, 8),
                 [(0, 1), (1, 1), (-1, 1), (0, 1)], lambda c: mix(c, ZBRUISE, 0.6), head[side])

    # ---- torso: shirt, grime toward the hem, pants below
    shirt = material(ZSHIRT, Noise(31), 4.2, 1.5, light=0.9, sx=0.6, sy=2.2)
    for name, r in body.items():
        fill(sh, r, shirt)
    grime = Noise(37)
    for name in ("front", "back", "right", "left"):
        x0, y0, w, h = body[name]
        for ly in range(h):
            for lx in range(w):
                g = grime.fbm(x0 + lx, y0 + ly, ((3.0, 0.6), (1.0, 0.4)), 0.7, 1.8) + (ly / h) * 0.35
                if g > 0.80:
                    sh.put(x0 + lx, y0 + ly, mix(shift(ZSHIRT, -2)(sh.get(x0 + lx, y0 + ly)), ZMUD[1], 0.3))
                elif g > 0.70:
                    sh.put(x0 + lx, y0 + ly, shift(ZSHIRT, -1)(sh.get(x0 + lx, y0 + ly)))
    pants = material(ZPANTS, Noise(41), 3.4, 1.3, light=0.5, sx=0.8, sy=1.6)
    for name in ("front", "back", "right", "left"):
        x0, y0, w, h = body[name]
        fill(sh, (x0, y0 + h - 6, w, 6), pants)
        for lx in range(w):  # the shirt's ragged hem hangs over the waist
            if rng.random() < 0.55:
                sh.put(x0 + lx, y0 + h - 6, ZSHIRT[1])
            if rng.random() < 0.25:
                sh.put(x0 + lx, y0 + h - 5, ZSHIRT[2])
    fill(sh, body["bottom"], pants)
    x0, y0, w, h = body["top"]
    for ly in range(h):
        for lx in range(5, 11):
            sh.put(x0 + lx, y0 + ly, skin_dark(lx, ly, 6, h, x0 + lx, y0 + ly))
    stamp(sh, *body["front"][:2], ZTORSO_FRONT, ZKEY)
    stamp(sh, *body["back"][:2], [
        "................",
        "................",
        "...a......a.....",
        "...k2a....k3a...",
        "....k3a....k3a..",
        "....ak2a...ak2..",
        ".....kR3a...k3a.",
        "......k2a....kk.",
        ".......kk.......",
        "................",
        "................",
        ".........r......",
        "........rR......",
        "................",
    ], ZKEY)
    for name in ("right", "left"):
        x0, y0, w, h = body[name]
        for _ in range(2):
            x, y = x0 + rng.randrange(w), y0 + rng.randrange(2, h - 10)
            for k in range(rng.randrange(2, 5)):
                sh.put(x, y + k, ZKEY["r"] if k else ZKEY["R"])

    # ---- arms: ragged sleeve, dead skin, a clawed hand
    for name, r in arm.items():
        x0, y0, w, h = r
        if name == "top":
            fill(sh, r, shirt)
            continue
        if name == "bottom":
            continue
        fill(sh, r, mottled(skin_dark))
        hem = [7, 8, 9, 8, 10, 8, 7, 9] if w == 8 else [8] * w
        for lx in range(w):
            for ly in range(hem[lx % len(hem)]):
                sh.put(x0 + lx, y0 + ly, shirt(lx, ly, w, h, x0 + lx, y0 + ly))
            sh.put(x0 + lx, y0 + hem[lx % len(hem)] - 1, ZSHIRT[1])
        for ly in range(h - 5, h):
            for lx in range(w):
                sh.put(x0 + lx, y0 + ly, shift(ZSKIN, -1)(sh.get(x0 + lx, y0 + ly)))
        for lx in range(w):
            sh.put(x0 + lx, y0 + h - 1, ZKEY["j"] if lx % 2 == 0 else ZKEY["K"])
            if lx % 2 == 1:
                sh.put(x0 + lx, y0 + h - 2, ZSKIN[1])
        sh.put(x0 + 1, y0 + h - 5, ZSKIN[5])
        sh.put(x0 + 5, y0 + h - 5, ZSKIN[5])
        for _ in range(2):
            walk(sh, rng, x0 + rng.randrange(1, w - 1), y0 + h - 6, rng.randrange(6, 10),
                 [(0, -1), (1, -1), (-1, -1), (0, -1)], lambda c: mix(c, ZBRUISE, 0.6), (x0, y0 + 9, w, h - 14))
    stamp(sh, *arm["right"][:2], ["........"] * 10 + [
        "...fg...", "..fRxg..", "..gXRf..", "...gr...", "....r...",
    ], ZKEY)
    stamp(sh, *arm["bottom"][:2], [
        "21222212",
        "1kK11Kk1",
        "1KjkkjK1",
        "21j11j12",
        "2kK22Kk2",
        "1KjkkjK1",
        "11j11j11",
        "21122112",
    ], ZKEY)

    # ---- legs: dark pants frayed at the knee, a little mud, worn shoes
    for name, r in leg.items():
        x0, y0, w, h = r
        if name == "top":
            fill(sh, r, pants)
            continue
        if name == "bottom":
            fill(sh, r, material(ZSHOE, Noise(53), 1.2, 1.0))
            continue
        fill(sh, r, pants)
        mud = Noise(59)
        for ly in range(h - 9, h - 5):
            for lx in range(w):
                m = mud.fbm(x0 + lx, y0 + ly, ((2.0, 0.6), (1.0, 0.4))) + (ly - (h - 9)) / 4 * 0.3
                if m > 0.66:
                    sh.put(x0 + lx, y0 + ly, ZMUD[min(2, int((m - 0.66) * 8))])
        fill(sh, (x0, y0 + h - 5, w, 5), material(ZSHOE, Noise(61), 2.6, 1.2, light=0.8))
        for lx in range(w):
            sh.put(x0 + lx, y0 + h - 5, ZSHOE[1])

    for r in list(head.values()) + list(body.values()) + list(arm.values()) + list(leg.values()):
        cleanup(sh, r)
    return sh


# ============================================================================================== SPIDER
SHAIR = ramp("#090706", "#120e0b", "#1b1510", "#251d17", "#30261e", "#3d3126", "#4c3e30", "#5f4e3c", "#76624b")
SPALE = ramp("#3e3226", "#5a4a37", "#7a6750", "#9a8668")
SKEY = {
    "0": SHAIR[0], "1": SHAIR[1], "2": SHAIR[2], "3": SHAIR[3], "4": SHAIR[4], "5": SHAIR[5], "6": SHAIR[6], "7": SHAIR[7], "8": SHAIR[8],
    "a": SPALE[0], "b": SPALE[1], "c": SPALE[2], "C": SPALE[3],
    "k": H("#050403"), "m": H("#140504"),
    "e": H("#3a0604"), "E": H("#6e0e08"), "o": H("#160302"),
    "F": H("#0b0807"), "G": H("#8a7f74"),
    "r": H("#3a0906"), "R": H("#6e130b"),
}
# The face (head front 16x16): two big domed eyes centred where the spider scare hangs its glow halos (2x u 5 and 11,
# v 7), a small pair above-outside, two tiny ones between, the laterals at the corners (they wrap round onto the
# sides, like the game's). Rows 12-15 are the scare's two mandibles (cut at the centre): each a hairy chelicera with a
# pale-based black fang, red at the tip.
SFACE = [
    "................",
    "................",
    "................",
    "2Ee332E22E233eE2",
    "1eo221o11o122oe1",
    "211oEeokkoEeo112",
    "3k1EeeekkEeee1k3",
    "EekeeeekkeeeekEe",
    "eokoeeokkoeeokeo",
    "o2321k1221k1232o",
    "2234433223344322",
    "1233322112233321",
    "1456654114566541",
    "1345543113455431",
    "0234FG2002GF4320",
    "0012kFR00RFk2100",
]
SCARAPACE = [
    "1222333333332221",
    "2233444444443322",
    "2344455555544432",
    "3445556666555443",
    "2445566776655442",
    "3245667777665423",
    "3324566776654233",
    "3333456666543333",
    "3244566116654423",
    "3445666776665443",
    "2345566776655432",
    "3234566556654323",
    "3345667667665433",
    "2345666776665432",
    "2334ok6666ko4332",
    "2233oEk55kEo3322",
]
SUNDER = [
    "0001122222211000",
    "0012FF1mm1FF2100",
    "0012FG1mm1GF2100",
    "0001FF0mm0FF1000",
    "00001RFkkFR10000",
]
SWRAP_R = ["..", "..", "..", "..", "2k", "ko", "Eo", "ee", "eo", "o2"]   # right face, its two front columns
SWRAP_L = [r[::-1] for r in SWRAP_R]
# The eyes layer, additive (black adds nothing): the same pixels, lit.
SEYES_KEY = {"e": H("#c4160c"), "E": H("#ff3e26"), "o": H("#3e0503")}


def eyes_of(rows):
    return ["".join(ch if ch in "eEo" else "." for ch in row) for row in rows]


def paint_spider():
    sh = Sheet(128, 64)
    eyes = Sheet(128, 64)
    rng = random.Random(5)
    head = box(32, 4, 8, 8, 8)
    neck = box(0, 0, 6, 6, 6)
    abd = box(0, 12, 10, 8, 12)
    leg = box(18, 0, 16, 2, 2)
    for g, n in ((SFACE, "SFACE"), (SCARAPACE, "SCARAPACE"), (SUNDER, "SUNDER")):
        check_grid(g, 16, n)

    def hairy(base, amp, light, seed, sx=1.0, sy=1.0):
        return material(SHAIR, Noise(seed), base, amp, light=light, sx=sx, sy=sy,
                        octs=((4.0, 0.45), (1.8, 0.3), (0.8, 0.25)))

    def hair_strokes(rect, n, along, dark=False, seed=0):
        """Coarse hair: short strokes along the fur (dx, dy), light with a pale tip, or dark partings."""
        r = random.Random(seed)
        x0, y0, w, h = rect
        for _ in range(n):
            x, y = x0 + r.randrange(w), y0 + r.randrange(h)
            L = r.randrange(2, 4)
            for k in range(L):
                xx, yy = x + along[0] * k, y + along[1] * k
                if x0 <= xx < x0 + w and y0 <= yy < y0 + h and (xx, yy) not in sh.locked:
                    sh.put(xx, yy, SHAIR[1] if dark else (SHAIR[7] if k == L - 1 else SHAIR[6]))

    # ---- head
    for name, r in head.items():
        fill(sh, r, hairy(3.0, 1.5, 1.0 if name != "bottom" else 0.0, 71 + len(name)))
    for name in ("right", "left", "back", "front"):
        hair_strokes(head[name], 20, (0, 1), seed=len(name))
        hair_strokes(head[name], 10, (0, 1), dark=True, seed=len(name) + 50)
    stamp(sh, *head["top"][:2], SCARAPACE, SKEY)
    stamp(sh, *head["front"][:2], SFACE, SKEY)
    rx, ry = head["right"][0] + 14, head["right"][1]
    lx, ly = head["left"][0], head["left"][1]
    stamp(sh, rx, ry, SWRAP_R, SKEY)
    stamp(sh, lx, ly, SWRAP_L, SKEY)
    stamp(sh, head["bottom"][0], head["bottom"][1] + 11, SUNDER, SKEY)

    # ---- neck
    for name, r in neck.items():
        fill(sh, r, hairy(2.6, 1.4, 0.8, 81 + len(name)))
        hair_strokes(r, 10, (0, 1), seed=90 + len(name))

    # ---- abdomen
    for name, r in abd.items():
        fill(sh, r, hairy(3.3 if name == "top" else 2.8, 1.6, 0.9 if name != "bottom" else 0.0, 91 + len(name), sy=1.4))
    for name in ("top", "right", "left", "back", "front"):
        x0, y0, w, h = abd[name]
        hair_strokes(abd[name], w * h // 10, (0, 1), seed=100 + len(name))
        hair_strokes(abd[name], w * h // 16, (0, 1), dark=True, seed=150 + len(name))
    # The back (top face; its bottom rows face the head): a dark heart mark from the front, then chevrons to the rear.
    x0, y0, w, h = abd["top"]
    cx = x0 + w // 2   # the two middle columns are cx-1 and cx
    for ly in range(h - 1, h - 13, -1):           # the heart mark, front half
        t = (h - 1 - ly) / 11
        half = int(round(0.6 + 1.9 * math.sin(math.pi * min(1, t * 1.05))))
        for dx in range(-half, half):
            sh.put(cx + dx, y0 + ly, SKEY["k"], True)
        sh.put(cx - half - 1, y0 + ly, SKEY["r"], True)
        sh.put(cx + half, y0 + ly, SKEY["r"], True)
    for i, tip in enumerate((10, 6, 2)):          # chevrons, pointing forward, shrinking to the rear
        arm_len = 5 - i
        for k in range(arm_len):
            yy = y0 + tip - k
            for xx, col in ((cx - 1 - k, SPALE[0] if k else SPALE[1]), (cx + k, SPALE[0] if k else SPALE[1])):
                sh.put(xx, yy, col, True)
                sh.put(xx, yy + 1, SHAIR[0], True)
    x0, y0, w, h = abd["back"]
    stamp(sh, x0, y0 + 10, [
        "........1111........",
        ".......1abba1.......",
        "......1abccba1......",
        ".......1bkkb1.......",
        "........1111........",
    ], SKEY)
    x0, y0, w, h = abd["bottom"]
    stamp(sh, x0, y0 + 16, [
        "....aa........aa....",
        "...abba......abba...",
        "....aa........aa....",
        "..1111111111111111..",
    ], SKEY)

    # ---- legs: one strip shared, unmirrored, by all eight legs (the tip is at either end), so the pattern is
    # symmetric along it: hairy segments, pale joint rings at a third and two thirds, dark at both ends.
    for name, r in leg.items():
        x0, y0, w, h = r
        fill(sh, r, hairy(3.0 if name != "bottom" else 2.0, 1.2, 0.0, 120 + len(name), sx=2.5, sy=0.6))
        if w >= 32:
            hair_strokes(r, 30, (1, 0), seed=200 + len(name))
            for ring, col in ((9, SHAIR[1]), (10, SPALE[1]), (11, SPALE[2]), (12, SHAIR[1]),
                              (19, SHAIR[1]), (20, SPALE[2]), (21, SPALE[1]), (22, SHAIR[1])):
                for yy in range(h):
                    sh.put(x0 + ring, y0 + yy, col, True)
            for end, col in ((0, SHAIR[0]), (1, SHAIR[1]), (w - 2, SHAIR[1]), (w - 1, SHAIR[0])):
                for yy in range(h):
                    sh.put(x0 + end, y0 + yy, col, True)
            if name in ("top", "front", "back"):
                for _ in range(8):
                    x = x0 + rng.randrange(2, w - 2)
                    if (x, y0) not in sh.locked:
                        sh.put(x, y0 + rng.randrange(h), SHAIR[8])

    for r in list(head.values()) + list(neck.values()) + list(abd.values()) + list(leg.values()):
        cleanup(sh, r)

    # ---- eyes layer
    stamp(eyes, *head["front"][:2], eyes_of(SFACE), SEYES_KEY)
    stamp(eyes, *head["top"][:2], eyes_of(SCARAPACE), SEYES_KEY)
    stamp(eyes, rx, ry, eyes_of(SWRAP_R), SEYES_KEY)
    stamp(eyes, lx, ly, eyes_of(SWRAP_L), SEYES_KEY)
    return sh, eyes


# ============================================================================================== preview
def preview(img, path, k=8):
    big = img.resize((img.width * k, img.height * k), Image.NEAREST)
    bg = Image.new("RGBA", big.size, (200, 0, 200, 255))
    bg.alpha_composite(big)
    bg.convert("RGB").save(path)


def crop(img, r, mirror=False):
    c = img.crop((r[0], r[1], r[0] + r[2], r[1] + r[3]))
    return c.transpose(Image.FLIP_LEFT_RIGHT) if mirror else c


def figure_zombie(img):
    """Flat front and side views, assembled from the faces (a quick read of the figure, not a render)."""
    head, body, arm, leg = box(0, 0, 8, 8, 8), box(16, 16, 8, 12, 4), box(40, 16, 4, 12, 4), box(0, 16, 4, 12, 4)
    fig = Image.new("RGBA", (32 + 4 + 24 + 4 + 8, 64), (40, 40, 40, 255))
    fig.paste(crop(img, head["front"]), (8, 0))
    fig.paste(crop(img, arm["front"]), (0, 16)); fig.paste(crop(img, body["front"]), (8, 16))
    fig.paste(crop(img, arm["front"], True), (24, 16))
    fig.paste(crop(img, leg["front"]), (8, 40)); fig.paste(crop(img, leg["front"], True), (16, 40))
    sx = 36
    fig.paste(crop(img, head["right"]), (sx, 0)); fig.paste(crop(img, body["right"]), (sx + 4, 16))
    fig.paste(crop(img, arm["right"]), (sx + 4, 16)); fig.paste(crop(img, leg["right"]), (sx + 4, 40))
    fig.paste(crop(img, head["back"]), (sx + 20, 0)); fig.paste(crop(img, body["back"]), (sx + 20, 16))
    fig.paste(crop(img, arm["bottom"]), (sx + 28, 48))
    return fig


def figure_spider(img, eyes):
    head, abd, leg = box(32, 4, 8, 8, 8), box(0, 12, 10, 8, 12), box(18, 0, 16, 2, 2)
    lit = img.copy()
    e = eyes.copy()
    for y in range(lit.height):
        for x in range(lit.width):
            a, b = lit.getpixel((x, y)), e.getpixel((x, y))
            if b[3]:
                lit.putpixel((x, y), tuple(min(255, a[i] + b[i]) for i in range(3)) + (255,))
    fig = Image.new("RGBA", (16 + 2 + 16 + 2 + 20 + 2 + 32, 40), (40, 40, 40, 255))
    fig.paste(crop(lit, head["front"]), (0, 0)); fig.paste(crop(lit, head["top"]), (0, 18))
    fig.paste(crop(lit, head["right"]), (18, 0)); fig.paste(crop(lit, head["bottom"]), (18, 18))
    fig.paste(crop(lit, abd["top"]), (36, 0)); fig.paste(crop(lit, abd["back"]), (36, 24))
    fig.paste(crop(lit, leg["top"]), (58, 0)); fig.paste(crop(lit, leg["front"]), (58, 6))
    fig.paste(crop(lit, abd["right"]), (58, 12))
    return fig


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview", help="also write upscaled sheets here")
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    z = paint_zombie()
    sp, se = paint_spider()
    z.img.save(os.path.join(OUT, "zombie.png"))
    sp.img.save(os.path.join(OUT, "spider.png"))
    se.img.save(os.path.join(OUT, "spider_eyes.png"))
    if a.preview:
        os.makedirs(a.preview, exist_ok=True)
        preview(z.img, os.path.join(a.preview, "zombie_sheet.png"), 6)
        preview(sp.img, os.path.join(a.preview, "spider_sheet.png"), 6)
        preview(se.img, os.path.join(a.preview, "spider_eyes_sheet.png"), 6)
        preview(figure_zombie(z.img), os.path.join(a.preview, "zombie_fig.png"), 10)
        preview(figure_spider(sp.img, se.img), os.path.join(a.preview, "spider_fig.png"), 10)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
