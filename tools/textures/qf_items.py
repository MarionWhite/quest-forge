#!/usr/bin/env python3
"""QF item sprites for MCPatcher custom item textures (CIT): a bottle shape per potion effect and a
cover per enchantment on enchanted books. Prototype for Shader Lab round 8.

Faithless (ARR) is the inspiration the owner named: "all of the potions having unique shapes, and
enchantments having unique books". Nothing is taken from it: every sprite below is a pixel grid
typed here by hand (a template system: one legend, one grid per shape, one emblem per
enchantment), so a human artist can later replace any grid without touching the code.

How the game draws them (Angelica's MCPatcherForge, com/prupe/mcpatcher/cit; CIT is OFF in the live
config, renderq turns it on per job with "cit": true):
  * A 1.7.10 potion draws two layers: `potion_overlay` (the liquid, tinted with the effect's
    colour) and `potion_bottle_drinkable` / `potion_bottle_splash` (the glass, untinted). A CIT
    rule replaces both by name (texture.potion_overlay=..., texture.potion_bottle_drinkable=...),
    so our bottle gets the game's own liquid colour: the shape tells the effect apart, the colour
    stays what players know.
  * Rules match the damage value's effect bits and the splash bit (damageMask 0x400F), so every
    level and duration of an effect shares its bottle.
  * Enchanted books match `enchantmentIDs` (CIT reads StoredEnchantments on books).

Legend (both kinds): . clear   o outline   O dark outline   w glass light   g glass   G glass dark
    h highlight   l liquid light  m liquid  d liquid dark   c cork  C cork dark   s label
    (books) b cover  B cover dark  k cover light  p page  P page dark  e emblem  E emblem dark
    y gilt  Y gilt dark
"""
import io

import numpy as np
from PIL import Image

# --- potion bottles: 16x16, one per effect ---------------------------------------------------------
BOTTLES = {
    # round flask, long neck (regeneration)
    "round": """
................
......oCCo......
......occo......
.......og.......
.......og.......
......ogwgo.....
....oogwhwgoo...
...ogwlmmmmmgo..
..ogwlmmmmmmdgo.
..ogllmmmmmmdgo.
..ogmmmmmmmddgo.
..ogmmmmmmdddgo.
...ogmmmmdddgo..
....oogdddgoo...
......ooooo.....
................""",
    # tall slim vial (swiftness)
    "vial": """
.......oCo......
......oCcCo.....
.......oCo......
......ogwgo.....
.....ogwhwgo....
.....ohllmmo....
.....ohlmmdo....
.....olmmmdo....
.....olmmmdo....
.....olmmmdo....
.....olmmddo....
.....olmmddo....
.....ommmddo....
.....ogmdddo....
......ooooo.....
................""",
    # squat wide jar, big cork (fire resistance)
    "jar": """
................
................
....oCCCCCCo....
....occcccco....
....oCCCCCCo....
...ogwwwwwwgo...
..ogwhggggggGo..
..ogllmmmmmmdo..
..oglmmmmmmmdo..
..ogmmmssmmmdo..
..ogmmmssmmddo..
..ogmmmmmmmddo..
..ogmmmmmmdddo..
...ogddddddgo...
....oooooooo....
................""",
    # heart bottle (healing)
    "heart": """
.......oCo......
.......oco......
.......ogo......
..ooo..ogo..ooo.
.oglmo.ogo.omdgo
oglmmmogwgommmdo
oglmmmmmmmmmmmdo
oghmmmmmmmmmmmdo
oglmmmmmmmmmmddo
.oglmmmmmmmmddo.
..oglmmmmmmddo..
...oglmmmmddo...
....oglmmddo....
.....oglddo.....
......oddo......
.......oo.......""",
    # conical flask (night vision)
    "cone": """
......oCCo......
......occo......
......ogwo......
......ogwo......
......ogwo......
.....ogwwgo.....
.....oglmgo.....
....ohlmmmgo....
....olmmmmdo....
...olmmmmmmdo...
...olmmmmmmdo...
..olmmmmmmmddo..
..olmmmmmmdddo..
.olmmmmmmddddgo.
.ooooooooooooooo
................""",
    # square bottle, broad shoulders (strength)
    "square": """
................
.......oCo......
.......oco......
......ogwgo.....
....oogwhwgoo...
...owwwwwwwwGo..
...ohlmmmmmmdo..
...ohlmmmmmmdo..
...olmmsssmmdo..
...olmmsssmmdo..
...olmmmmmmmdo..
...olmmmmmmddo..
...olmmmmmmddo..
...ogddddddddo..
...ooooooooooo..
................""",
    # teardrop with a wave (water breathing)
    "drop": """
.......oo.......
......oCCo......
......occo......
.......ogo......
......ogwgo.....
.....ogwhwgo....
....ogwlmmmgo...
....oglmmmmdo...
...oglmmmmmmdo..
...ohmmmlmmmdo..
...olmmlmlmmdo..
...olmlmmmlmdo..
...ogmmmmmmddo..
....ogmmmmddo...
.....ooddooo....
.......oo.......""",
    # splash: round grenade with a ring and a fuse cork (any splash potion)
    "splash": """
........oCo.....
.......oCco.....
...oo..oCo......
..o..o.ogo......
..o..ooggwo.....
...oogwwhwgo....
....ogwlmmmgo...
...oglmmmmmmgo..
...ohlmmmmmmdo..
...olmmmmmmmdo..
...olmmmmmmddo..
...ogmmmmmdddo..
....ogmmmdddo...
.....ogddddo....
......ooooo.....
................""",
}
# Per-effect motifs (r009: "some of the potions are kind of boring or need more detail or personality"):
# patches typed over the shape's grid as (row, col, chars), "." in chars keeps the pixel underneath.
# Every effect gets its own sprite, so two effects sharing a shape still read apart.
#   r R ribbon/wax   y Y gold/twine   f F feather   k K iron   x bone/eye white   v V leaf
EFFECTS = {   # effect bits -> (bottle, name for the files, patches, dashed outline)
    1: ("round", "regeneration", [        # ribbon bow on the neck, a sprout from the cork, rising bubbles
        (0, 9, "vV"), (1, 10, "v"), (3, 5, "rR..Rr"), (4, 6, "rrrr"), (9, 8, "l"), (11, 6, "l"), (10, 10, "l")], False),
    2: ("vial", "swiftness", [            # a feather tied to the neck, speed streaks
        (0, 13, "ff"), (1, 12, "fffF"), (2, 12, "ffF"), (3, 6, "yYyYy"), (3, 12, "fF"), (4, 12, "F"),
        (5, 12, "Y"), (7, 1, "ww"), (9, 0, "www"), (11, 1, "ww")], False),
    3: ("jar", "fire_resistance", [       # red wax cap with drips, a flame on the label
        (2, 5, "rrrrrr"), (3, 5, "r"), (3, 10, "R"), (4, 10, "R"), (5, 10, "R"), (4, 5, "R"),
        (7, 5, "ssssss"), (8, 5, "sssass"), (9, 5, "ssaass"), (10, 5, "saayas"), (11, 5, "sayyas"),
        (12, 5, "ssrrss")], False),
    4: ("drop", "poison", [               # a skull over the liquid, bubbles leaking from the cork
        (9, 8, "m"), (10, 7, "m.m"), (11, 6, "m...m"),
        (8, 7, "xxx"), (9, 7, "OxO"), (10, 7, "xxx"), (11, 7, "xOx"), (1, 10, "m"), (0, 11, "l")], False),
    5: ("heart", "healing", [             # gold cap and a sparkle
        (0, 8, "y"), (1, 8, "Y"), (0, 2, "h"), (1, 1, "hwh"), (2, 2, "h")], False),
    6: ("cone", "night_vision", [         # an open eye on the glass
        (10, 6, "OOOOO"), (11, 5, "OxyOyxO"), (12, 6, "OOOOO"), (1, 11, "y"), (2, 12, "Y")], False),
    8: ("vial", "weakness", [             # cracked glass held together with a bandage, cork askew
        (0, 7, ".oCCo"), (1, 6, "..oCo"), (6, 8, "O"), (7, 7, "O"), (8, 8, "O"),
        (9, 5, "sssssss"), (10, 5, "Fsssssss"), (11, 8, "O"), (12, 9, "O"), (13, 8, "O")], False),
    9: ("square", "strength", [           # iron bands with gold rivets, red gem on the label
        (7, 3, "KkkkkkkkkkK"), (12, 3, "KkkkkkkkkkK"), (7, 4, "y"), (7, 12, "y"), (12, 4, "y"), (12, 12, "y"),
        (8, 7, "ysy"), (9, 7, "srs"), (10, 7, "ysy"), (11, 7, "...")], False),
    10: ("jar", "slowness", [             # an hourglass, cobweb on the cork
        (8, 6, "YYYY"), (9, 7, "yy"), (10, 7, "YY"), (11, 6, "YyyY"), (12, 6, "YYYY"),
        (1, 11, "w.w"), (2, 12, "w"), (3, 12, "ww"), (1, 3, "w"), (2, 3, "h")], False),
    12: ("square", "harming", [           # a broken heart on a pale label, iron spikes
        (0, 8, "K"), (1, 7, "KkK"), (3, 4, "K"), (3, 12, "K"), (4, 3, "K"), (4, 13, "K"),
        (8, 4, "sssssssss"), (9, 4, "ssrrsrrss"), (10, 4, "srrrOrrrs"), (11, 4, "ssrOrrrss"), (12, 4, "ssssrssss")], False),
    13: ("drop", "water_breathing", [     # bubbles rising out of the cork
        (0, 10, "w"), (1, 11, "h"), (2, 10, "w"), (0, 12, "h"), (3, 12, "w")], False),
    14: ("cone", "invisibility", [        # a ghost of a bottle: dashed outline, sparkles
        (2, 2, "h"), (5, 12, "h"), (4, 13, "w"), (9, 1, "w"), (13, 14, "h")], True),
}
# r010 (owner r009: "the green potion is boring" = splash poison, the board's only green): every splash potion
# had one plain grenade. Now each effect's splash carries a small version of its motif on the grenade's body
# (rows 7-12, cols 4-12 are liquid; the fuse cork is rows 0-2, cols 8-10).
SPLASH = {   # effect bits -> (patches on the "splash" grid, dashed outline)
    1: ([(0, 11, "vV"), (1, 11, "v"), (3, 7, "rRr"), (9, 8, "l"), (11, 6, "l"), (10, 10, "l")], False),
    2: ([(0, 11, "ff"), (1, 11, "fF"), (2, 11, "F"), (8, 0, "ww"), (10, 1, "ww"), (12, 0, "ww")], False),
    3: ([(0, 8, "r"), (1, 8, "rR"), (8, 8, "a"), (9, 7, "aya"), (10, 7, "ayy"), (11, 7, "aaa")], False),
    4: ([(8, 7, "xxx"), (9, 7, "OxO"), (10, 7, "xxx"), (11, 7, "xOx"),
         (0, 12, "l"), (1, 11, "m"), (2, 12, "m"), (0, 14, "m"),
         (15, 7, "m"), (15, 10, "l"), (14, 12, "m")], False),
    5: ([(0, 9, "y"), (1, 9, "Y"), (8, 8, "h"), (9, 7, "hwh"), (10, 8, "h"), (1, 1, "h"), (2, 2, "w")], False),
    6: ([(9, 6, "OOOOO"), (10, 5, "OxyOyxO"), (11, 6, "OOOOO")], False),
    8: ([(0, 9, "c"), (1, 9, "C"), (9, 4, "sssssssss"), (8, 8, "O"), (10, 9, "O"), (11, 8, "O")], False),
    9: ([(8, 4, "kkkkkkkkk"), (8, 4, "y"), (8, 12, "y"), (10, 7, "ysy"), (11, 7, "srs"), (12, 7, "ysy")], False),
    10: ([(8, 7, "YYY"), (9, 8, "y"), (10, 7, "YyY"), (1, 5, "w.w"), (2, 6, "w")], False),
    12: ([(9, 6, "rr.rr"), (10, 6, "rrOrr"), (11, 7, "rOr"), (12, 8, "r"), (4, 3, "K"), (2, 2, "K")], False),
    13: ([(0, 11, "w"), (1, 12, "h"), (2, 11, "w"), (9, 6, "l"), (10, 9, "l"), (11, 7, "l")], False),
    14: ([(2, 2, "h"), (5, 13, "h"), (9, 1, "w"), (13, 14, "h")], True),
}
GLASS = {"o": (34, 30, 44, 255), "O": (20, 16, 26, 255), "w": (232, 240, 250, 200), "g": (178, 198, 222, 170),
         "G": (120, 136, 160, 190), "h": (255, 255, 255, 235), "c": (176, 128, 74, 255), "C": (118, 80, 42, 255),
         "s": (234, 222, 190, 255),
         "r": (204, 54, 62, 255), "R": (128, 26, 40, 255), "y": (234, 192, 78, 255), "Y": (158, 114, 40, 255),
         "f": (244, 242, 236, 255), "F": (168, 176, 188, 255), "k": (112, 118, 130, 255), "K": (60, 62, 72, 255),
         "x": (232, 226, 206, 255), "v": (112, 186, 70, 255), "V": (58, 120, 42, 255), "a": (246, 136, 34, 255)}
LIQUID = {"l": 255, "m": 205, "d": 150}


def grid(text):
    rows = [r for r in text.strip("\n").split("\n")]
    assert len(rows) == 16 and all(len(r) == 16 for r in rows), [len(r) for r in rows]
    return rows


def bottle_layers(shape, patches=(), dashed=False):
    """(bottle rgba, liquid rgba) 16x16: the liquid is grey so the game's potion colour tints it."""
    rows = [list(r) for r in grid(BOTTLES[shape])]
    for y, x0, chars in patches:
        for i, ch in enumerate(chars):
            if ch != ".":
                rows[y][x0 + i] = ch
    if dashed:   # every other outline pixel turns to faint glass
        rows = [[("w" if ch == "o" and (x + y) % 2 else ch) for x, ch in enumerate(r)] for y, r in enumerate(rows)]
    glass = np.zeros((16, 16, 4), np.uint8)
    liquid = np.zeros((16, 16, 4), np.uint8)
    for y, r in enumerate(rows):
        for x, ch in enumerate(r):
            if ch in GLASS:
                glass[y, x] = GLASS[ch]
            elif ch in LIQUID:
                v = LIQUID[ch]
                liquid[y, x] = (v, v, v, 255)
            elif ch != ".":
                raise ValueError(f"{shape}: unknown pixel {ch!r}")
    # a glint on the liquid: one bright glass pixel over the upper-left liquid edge
    return glass, liquid


# --- enchanted books: 16x16 base + emblem per enchantment ------------------------------------------
BOOK = """
................
...oooooooooo...
..oYkkkkkkkkbo..
..oYbbbbbbbbbo..
..oYbbbbbbbbbPo.
..oYbbbbbbbbbpo.
..oYbbbbbbbbbpo.
..oYbbbbbbbbbpo.
..oYbbbbbbbbbpo.
..oYbbbbbbbbbpo.
..oYbbbbbbbbbpo.
..oYbbbbbbbbbpo.
..oYBBBBBBBBBpo.
..oYyyyyyyyyyPo.
...oooooooooooo.
................"""
EMBLEMS = {   # 7x7, e emblem, E emblem dark, y gilt. Placed by bounding box on the cover's centre pixel (8, 7)
              # (emblem_origin); r010: every box must be odd-sized so it centres exactly (owner r009: logos off centre)
    "shield": """
.yyyyy.
yeeeeey
yeeEeey
yeEEEey
.yeEey.
..yey..
...y...""",
    "sword": """
.....ye
....yey
...yey.
y.yey..
.yEy...
.Ey.y..
E....y.""",
    "flame": """
...e...
..eEe..
..eEe.e
.eEyEee
eEyyyEe
.eEyEe.
..eee..""",
    "pickaxe": """
..yyy..
.y...y.
y..E..y
...E...
...E...
...E...
...E...""",
    "thread": """
yyyyyyy
.eeeee.
.EEEEE.
.eeeee.
.EEEEE.
yyyyyyy
....ee.""",
    "anvil": """
eeeeeey
.eEEEe.
..eEe..
..eEe..
..eEe..
.eeeee.
.EEEEE.""",
    "clover": """
...y...
..yey..
.yeeey.
yeeEeey
.yeeey.
..yey..
...y...""",
    "arrow": """
....yyy
.....yy
....y.y
...E...
..E....
eE.....
ee.....""",
}
ENCHANTS = {   # id -> (emblem, cover family, name)
    0: ("shield", "armor", "protection"), 1: ("flame", "armor", "fire_protection"),
    16: ("sword", "weapon", "sharpness"), 20: ("flame", "weapon", "fire_aspect"),
    32: ("pickaxe", "tool", "efficiency"), 33: ("thread", "tool", "silk_touch"),
    34: ("anvil", "tool", "unbreaking"), 35: ("clover", "tool", "fortune"),
    48: ("arrow", "bow", "power"),
}
COVERS = {    # family -> (cover dark, cover, cover light, emblem, emblem dark)
    "armor":  ((38, 58, 102), (58, 88, 150), (96, 132, 196), (214, 226, 240), (130, 150, 180)),
    "weapon": ((92, 22, 26), (140, 36, 40), (186, 70, 66), (236, 222, 206), (170, 150, 140)),
    "tool":   ((26, 76, 64), (40, 112, 92), (78, 156, 126), (232, 226, 200), (150, 150, 130)),
    "bow":    ((76, 50, 26), (116, 78, 40), (156, 112, 64), (236, 222, 196), (160, 140, 110)),
}
FLAME_EMBLEM = ((255, 160, 40), (196, 70, 20))
BOOK_FIXED = {"o": (30, 22, 20, 255), "y": (222, 186, 82, 255), "Y": (150, 112, 44, 255),
              "p": (236, 226, 200, 255), "P": (190, 176, 146, 255)}


def book(eid):
    emblem, fam, _ = ENCHANTS[eid]
    cd, c, cl, em, emd = COVERS[fam]
    if emblem == "flame":
        em, emd = FLAME_EMBLEM
    pal = dict(BOOK_FIXED)
    pal.update({"b": c + (255,), "B": cd + (255,), "k": cl + (255,)})
    out = np.zeros((16, 16, 4), np.uint8)
    for y, r in enumerate(grid(BOOK)):
        for x, ch in enumerate(r):
            if ch != ".":
                out[y, x] = pal[ch]
    rows = [r for r in EMBLEMS[emblem].strip("\n").split("\n")]
    epal = {"e": em + (255,), "E": emd + (255,), "y": BOOK_FIXED["y"]}
    ox, oy = emblem_origin(emblem)
    for dy, r in enumerate(rows):
        for dx, ch in enumerate(r):
            if ch != ".":
                out[oy + dy, ox + dx] = epal[ch]
    return out


COVER_CENTRE = (8, 7)   # the cover face is x 4-12, y 3-11 of BOOK


def emblem_origin(name):
    """Where to put an emblem's grid so its drawn pixels' bounding box is centred on COVER_CENTRE."""
    rows = EMBLEMS[name].strip("\n").split("\n")
    pts = [(x, y) for y, r in enumerate(rows) for x, c in enumerate(r) if c != "."]
    x0, x1 = min(p[0] for p in pts), max(p[0] for p in pts)
    y0, y1 = min(p[1] for p in pts), max(p[1] for p in pts)
    if (x1 - x0) % 2 or (y1 - y0) % 2:
        raise ValueError("emblem %s: bounding box %dx%d is even-sized, cannot centre exactly"
                         % (name, x1 - x0 + 1, y1 - y0 + 1))
    return COVER_CENTRE[0] - (x0 + x1) // 2, COVER_CENTRE[1] - (y0 + y1) // 2


def png(a):
    b = io.BytesIO()
    Image.fromarray(a, "RGBA").save(b, "PNG")
    return b.getvalue()


CIT = "assets/minecraft/mcpatcher/cit/"


def write_cit(z):
    """Write the potion and book rules + sprites into an open zip; returns the number of rules."""
    n = 0
    d = CIT + "potions/"
    sglass, sliquid = bottle_layers("splash")
    z.writestr(d + "bottle_splash.png", png(sglass))
    z.writestr(d + "liquid_splash.png", png(sliquid))
    for bits, (shape, name, patches, dashed) in EFFECTS.items():
        glass, liquid = bottle_layers(shape, patches, dashed)
        z.writestr(d + "bottle_%s.png" % name, png(glass))
        z.writestr(d + "liquid_%s.png" % name, png(liquid))
        sg, sl = bottle_layers("splash", *SPLASH[bits])
        z.writestr(d + "bottle_%s_splash.png" % name, png(sg))
        z.writestr(d + "liquid_%s_splash.png" % name, png(sl))
        z.writestr(d + "%s.properties" % name,
                   "type=item\nitems=minecraft:potion\ndamage=%d\ndamageMask=16399\n"
                   "texture.potion_bottle_drinkable=bottle_%s\ntexture.potion_overlay=liquid_%s\n" % (bits, name, name))
        z.writestr(d + "%s_splash.properties" % name,
                   "type=item\nitems=minecraft:potion\ndamage=%d\ndamageMask=16399\n"
                   "texture.potion_bottle_splash=bottle_%s_splash\ntexture.potion_overlay=liquid_%s_splash\n"
                   % (16384 | bits, name, name))
        n += 2
    for eid, (_, _, name) in ENCHANTS.items():
        d = CIT + "books/"
        z.writestr(d + "%s.png" % name, png(book(eid)))
        z.writestr(d + "%s.properties" % name,
                   "type=item\nitems=minecraft:enchanted_book\nenchantmentIDs=%d\ntexture=%s\n" % (eid, name))
        n += 1
    return n


def sheet(path, scale=8):
    """All prototypes on one sheet: each effect's bottle in its 1.7.10 potion colour, a splash, then the books."""
    tints = {1: 0xCD5CAB, 2: 0x7CAFC6, 3: 0xE49A3A, 4: 0x4E9331, 5: 0xF82423, 6: 0x1F1FA1, 8: 0x484D48,
             9: 0x932423, 10: 0x5A6C81, 12: 0x430A09, 13: 0x2E5299, 14: 0x7F8392, 0: 0x4E9331}
    tiles = []
    order = [(b, False) for b in tints if b] + [(b, True) for b in tints if b]   # drinkables, then each splash
    for bits, splash in order:
        c = tints[bits]
        t = (c >> 16, (c >> 8) & 255, c & 255)
        if splash:
            glass, liquid = bottle_layers("splash", *SPLASH[bits])
        else:
            shape, _, patches, dashed = EFFECTS[bits]
            glass, liquid = bottle_layers(shape, patches, dashed)
        lq = liquid.astype(np.float32)
        lq[..., :3] *= np.array(t) / 255.0
        im = Image.fromarray(lq.astype(np.uint8), "RGBA")
        im.alpha_composite(Image.fromarray(glass, "RGBA"))
        tiles.append(im)
    for eid in ENCHANTS:
        tiles.append(Image.fromarray(book(eid), "RGBA"))
    W = len(tiles) * (16 * scale + 8) + 8
    out = Image.new("RGBA", (W, 16 * scale + 16), (139, 139, 139, 255))
    for i, im in enumerate(tiles):
        out.alpha_composite(im.resize((16 * scale, 16 * scale), Image.NEAREST), (8 + i * (16 * scale + 8), 8))
    out.save(path)


if __name__ == "__main__":
    import sys
    sheet(sys.argv[1] if len(sys.argv) > 1 else "items-sheet.png")
