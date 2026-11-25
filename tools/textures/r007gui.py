#!/usr/bin/env python3
"""r011: Faithless's GUI on 1.7.10 layouts (the 'gui' part of r007packs.py; see its docstring).

    py -3.10 -I tools/textures/r007packs.py --parts gui --out C:\\qfb\\textures\\QF-r011-gui.zip

What 1.7.10 reads and where Faithless (made for 1.20.5+) keeps it:
  * Container backgrounds (gui/container/*.png): Faithless still ships them in the pre-1.20.2 atlas layout, sprites
    included (furnace flame and arrow at 176,0 / 176,14, brewing arrow and bubbles, enchanting option bars at 0,166,
    effect icons in inventory.png). The 1.12-era slot layout equals 1.7.10's for the furnace, crafting table, chests,
    dispenser, hopper, anvil and beacon, so those copy as they are. Measured against 1.7.10's Container classes:
      - inventory: 1.9 moved the 2x2 grid from (88,26) to (98,18) and the result from (144,36) to (154,28), and
        added the offhand slot at (77,62). The grid, arrow and result are moved back by (-10, +8) and the offhand
        slot painted out with the panel's own colour.
      - brewing stand: 1.9 bottles sit 5 px lower than 1.7.10's (56,46 / 79,53 / 102,46); Faithless's stand is an
        illustration with no drawn slots, so the bottles just stand 5 px higher on it. Kept as is.
      - enchanting table: 1.8 split the slot into item (15,47) and lapis (35,47); 1.7.10's one slot (25,47) lands
        centred on Faithless's illustrated table. Kept as is.
      - villager, horse, book, title screens: not taken (modern villager trading layout; the owner did not want the
        main menu).
  * Creative tabs: Faithless's legacy tabs.png is 1.7.10's grid (28 px columns; column 5, 1.7.10's search and
    inventory tabs, is its red banner). tab_items / tab_item_search / tab_inventory copy as they are.
  * HUD sheets (icons.png, widgets.png): Faithless's legacy copies are partial, so they are composited here from its
    1.20 sprites (gui/sprites/hud, boss_bar, widget) onto vanilla 1.7.10's own sheet at the UVs GuiIngame and
    GuiButton read; any cell Faithless has no sprite for keeps vanilla's.
  * Boss bar: 1.7.10 has ONE bar (icons.png 0,74 / 0,79, 182x5) for every boss. Faithless's per-boss bars
    (bar_dragon.png, bar_wither.png, 194x18 with a frame) need a GuiIngame hook to draw; the plain bar here is its
    pink (Ender Dragon) one.
"""
import io

import numpy as np
from PIL import Image

A = "assets/minecraft/"
G = A + "textures/gui/"
SP = G + "sprites/"
DIRECT = ["crafting_table", "furnace", "generic_54", "dispenser", "hopper", "anvil", "beacon", "brewing_stand",
          "enchanting_table", "stats_icons"]
CREATIVE = ["tabs", "tab_items", "tab_item_search", "tab_inventory"]

# icons.png cells (x, y) by GuiIngame (1.7.10) <- Faithless sprite under gui/sprites/
HEARTS = {"container": 16, "container_blinking": 25, "full": 52, "half": 61, "full_blinking": 70,
          "half_blinking": 79, "poisoned_full": 88, "poisoned_half": 97, "poisoned_full_blinking": 106,
          "poisoned_half_blinking": 115, "withered_full": 124, "withered_half": 133, "withered_full_blinking": 142,
          "withered_half_blinking": 151, "absorbing_full": 160, "absorbing_half": 169}
ICONS = {(0, 0): "hud/crosshair",
         (16, 9): "hud/armor_empty", (25, 9): "hud/armor_half", (34, 9): "hud/armor_full",
         (52, 9): "hud/heart/vehicle_container", (88, 9): "hud/heart/vehicle_full", (97, 9): "hud/heart/vehicle_half",
         (16, 18): "hud/air", (25, 18): "hud/air_bursting",
         (16, 27): "hud/food_empty", (25, 27): "hud/food_empty", (133, 27): "hud/food_empty_hunger",
         (52, 27): "hud/food_full", (61, 27): "hud/food_half", (70, 27): "hud/food_full", (79, 27): "hud/food_half",
         (88, 27): "hud/food_full_hunger", (97, 27): "hud/food_half_hunger", (106, 27): "hud/food_full_hunger",
         (115, 27): "hud/food_half_hunger",
         (0, 64): "hud/experience_bar_background", (0, 69): "hud/experience_bar_progress",
         (0, 74): "boss_bar/pink_background", (0, 79): "boss_bar/pink_progress",
         (0, 84): "hud/jump_bar_background", (0, 89): "hud/jump_bar_progress"}
for _n, _x in HEARTS.items():
    ICONS[(_x, 0)] = "hud/heart/" + _n
    if _n.startswith("container"):
        hc = _n.replace("container", "container_hardcore")
    elif _n.split("_")[0] in ("full", "half"):
        hc = "hardcore_" + _n
    else:
        hc = _n.replace("_", "_hardcore_", 1)          # poisoned_full -> poisoned_hardcore_full
    ICONS[(_x, 45)] = "hud/heart/" + hc
WIDGETS = {(0, 0): "hud/hotbar", (0, 22): "hud/hotbar_selection", (0, 46): "widget/button_disabled",
           (0, 66): "widget/button", (0, 86): "widget/button_highlighted"}
INV_MOVE = ((96, 17, 168, 64), (-10, 8))     # 1.9 crafting block (grid, arrow, result) -> 1.7.10 place;
#                                              x 168+ is the wooden frame, y 15-16 the sign's shadow: both stay
INV_OFFHAND = (76, 61, 94, 79)


def _img(z, n):
    return Image.open(io.BytesIO(z.read(n))).convert("RGBA")


def _png(im):
    b = io.BytesIO()
    im.save(b, "PNG")
    return b.getvalue()


def _paste_sheet(base, fl, cells, log_miss):
    for (x, y), name in cells.items():
        p = SP + name + ".png"
        if p not in fl.names:
            log_miss.append(name)
            continue
        s = fl.img(p)
        if (x, y) == (0, 22):                       # 1.7.10 draws 24 x 22 of the selection
            s = s.crop((0, 0, 24, 22))
        base.paste(s, (x, y), None)                 # replace the cell, transparency included
    return base


def _panel_colour(a, box):
    """Most common opaque colour along a box's border: the flat panel the block sits on."""
    x0, y0, x1, y1 = box
    edge = np.concatenate([a[y0, x0:x1], a[y1 - 1, x0:x1], a[y0:y1, x0], a[y0:y1, x1 - 1]])
    edge = edge[edge[:, 3] > 0]
    vals, counts = np.unique(edge.reshape(-1, 4), axis=0, return_counts=True)
    return tuple(int(v) for v in vals[counts.argmax()])


def inventory(fl):
    im = fl.img(G + "container/inventory.png")
    (x0, y0, x1, y1), (dx, dy) = INV_MOVE
    block = im.crop((x0, y0, x1, y1))
    a = np.asarray(im).copy()
    col = _panel_colour(a, (x0, y0, x1, y1))
    a[y0:y1, x0:x1] = col
    for y in range(y0, y1):                     # the old result box's frame reached into the wooden frame
        if all(abs(int(a[y, 169, c]) - int(a[y, 169, 0])) < 6 for c in (1, 2)):   # grey, not wood
            a[y, 168:172] = a[20, 168:172]
    ox0, oy0, ox1, oy1 = INV_OFFHAND
    a[oy0:oy1, ox0:ox1] = _panel_colour(a, INV_OFFHAND)
    out = Image.fromarray(a)
    out.paste(block, (x0 + dx, y0 + dy))
    return out


# --- r012: text that reads, creative tabs on 1.7.10's grid ------------------------------------------------------------
# The owner, r011: "Make the text on screen pop out more. It gets muddled by the noisy background. Do this for all of
# the copied GUI." 1.7.10 draws every container title in 0x404040 without a shadow. Faithless's title plaques are a
# flat dark wood (104,61,39) sized for its own font, so 1.7.10's titles both sink into them and overrun them
# ("Enchant" and "Inventory" run off the plaque onto the illustration). Each plaque under a 1.7.10 title is widened
# to the title's measured width (1.7.10's own font metrics) and repainted in the light honey wood Faithless's later
# screens use, so the dark text sits on a light, flat field.
PLAQUE_FILL = (104, 61, 39)
PLAQUE_MAP = {(104, 61, 39): (226, 172, 112), (137, 76, 45): (243, 200, 142), (61, 32, 29): (150, 96, 58)}
TITLE = 0x404040
# (texture, title text, x or None = centred, y): 1.7.10's GuiContainer subclasses' drawGuiContainerForegroundLayer
TITLES = {
    "furnace": [("Furnace", None, 6), ("Inventory", 8, 72)],
    "crafting_table": [("Crafting", 28, 6), ("Inventory", 8, 72)],
    "brewing_stand": [("Brewing Stand", None, 6), ("Inventory", 8, 72)],
    "enchanting_table": [("Enchant", 12, 5), ("Inventory", 8, 72)],
    "anvil": [("Repair & Name", 60, 6)],     # 1.7.10's GuiRepair draws no "Inventory": its plaque stays Faithless's
    "dispenser": [("Dispenser", None, 6), ("Inventory", 8, 72)],
    "hopper": [("Item Hopper", 8, 6), ("Inventory", 8, 39)],
}
XSIZE = 176


class Font:
    """1.7.10 FontRenderer widths from textures/font/ascii.png (the per-glyph scan readFontTexture does)."""
    def __init__(self, mc):
        a = np.asarray(_img(mc, A + "textures/font/ascii.png"))[:, :, 3]
        self.cell = a.shape[1] // 16
        self.glyphs = a
        self.w = {}
        for ch in range(256):
            cx, cy = (ch % 16) * self.cell, (ch // 16) * self.cell
            g = a[cy:cy + self.cell, cx:cx + self.cell]
            cols = np.nonzero(g.max(0) > 0)[0]
            self.w[ch] = 4 if ch == 32 else (int(cols.max()) + 2 if len(cols) else 0) * 8 // self.cell
        self.w[32] = 4

    def width(self, s):
        return sum(self.w.get(ord(c), 6) for c in s)

    def draw(self, im, s, x, y, rgb, shadow=False):
        """Preview only: draw s at 1x (8 px cells) into an RGBA image."""
        a = np.asarray(im).copy()
        for dx, dy, col in ([(1, 1, tuple(c // 4 for c in rgb))] if shadow else []) + [(0, 0, rgb)]:
            cx = x + dx
            for c in s:
                ch = ord(c)
                gx, gy = (ch % 16) * self.cell, (ch // 16) * self.cell
                g = np.asarray(Image.fromarray(self.glyphs[gy:gy + self.cell, gx:gx + self.cell]).resize((8, 8)))
                ys, xs = np.nonzero(g > 0)
                for yy, xx in zip(ys, xs):
                    if 0 <= y + dy + yy < a.shape[0] and 0 <= cx + xx < a.shape[1]:
                        a[y + dy + yy, cx + xx, :3] = col
                        a[y + dy + yy, cx + xx, 3] = 255
                cx += self.w.get(ch, 6)
        return Image.fromarray(a)


def _component(mask, x, y):
    """Bounding box (x0, y0, x1, y1 exclusive) of the 4-connected True region holding (x, y)."""
    from collections import deque
    h, w = mask.shape
    seen = np.zeros_like(mask)
    q = deque([(x, y)])
    seen[y, x] = True
    xs, ys = [x], [y]
    while q:
        cx, cy = q.popleft()
        for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
            if 0 <= nx < w and 0 <= ny < h and mask[ny, nx] and not seen[ny, nx]:
                seen[ny, nx] = True
                q.append((nx, ny))
                xs.append(nx)
                ys.append(ny)
    return min(xs), min(ys), max(xs) + 1, max(ys) + 1


def plaque_fix(im, titles, font, log):
    """Widen each title plaque to its 1.7.10 title (+3 px each side) and repaint it light. Returns the new image."""
    a = np.asarray(im).copy()
    for text, tx, ty in titles:
        tw = font.width(text)
        x = (XSIZE - tw) // 2 if tx is None else tx
        fill = np.all(a[:, :, :3] == PLAQUE_FILL, axis=2) & (a[:, :, 3] > 0)
        ay = ty + 3
        ax = next((xx for xx in range(x, x + tw) if fill[ay, xx]), None)
        if ax is None:
            log.append("%s: no plaque" % text)
            continue
        x0, y0, x1, y1 = _component(fill, ax, ay)
        # the plaque proper: fill box + 1 px outline left/right, + its highlight/shadow rows below
        px0, px1, py0, py1 = x0 - 1, x1 + 1, y0, y1 + 2
        need0, need1 = min(px0, x - 3), max(px1, x + tw + 2)
        if (need0, need1) != (px0, px1):
            block = a[py0:py1, px0:px1].copy()
            mid = (px1 - px0) // 2
            new_w = need1 - need0
            grow = new_w - (px1 - px0)
            reps = block[:, mid:mid + 1]
            wide = np.concatenate([block[:, :mid]] + [reps] * grow + [block[:, mid:]], axis=1)
            # only paint where the plaque is opaque art (keep what is around it: shadow rows are partial)
            a[py0:py1, need0:need1] = wide
            log.append("%s: plaque %d-%d -> %d-%d" % (text, px0, px1, need0, need1))
            px0, px1 = need0, need1
        reg = a[py0 - 1:py1, px0:px1]
        for src, dst in PLAQUE_MAP.items():
            m = np.all(reg[:, :, :3] == src, axis=2)
            reg[m, :3] = dst
    return Image.fromarray(a)


# Enchanting options: 1.7.10 writes each option's spell in 0x685E4A over the ribbon at (0,166); on Faithless's red
# ribbon that is dark on dark. The ribbon's body becomes parchment (the same light field as the plaques) and its right
# end keeps Faithless's red and gold as a seal, where 1.7.10 right-aligns the green level number (x 94..106 for "30").
# r012: the seal narrowed 82 -> 91, the spell text (wrapped at 104 px, as on vanilla) ran onto the red for 24 px.
RIBBON = (0, 166, 108, 19)
RIBBON_SEAL_X = 91
PARCHMENT = {(181, 59, 38): (241, 222, 186), (161, 52, 33): (228, 205, 165), (148, 40, 33): (214, 188, 146),
             (107, 23, 29): (176, 140, 98)}


def enchant_fix(im):
    a = np.asarray(im).copy()
    x, y, w, h = RIBBON
    reg = a[y:y + h, x:x + RIBBON_SEAL_X]
    for src, dst in PARCHMENT.items():
        m = np.all(reg[:, :, :3] == src, axis=2)
        reg[m, :3] = dst
    # the remaining reds of the ribbon body (shading between those four) follow by luminance
    rest = (reg[:, :, 3] > 0) & (reg[:, :, 0] > reg[:, :, 1] + 40) & (reg[:, :, 0] < 200)
    lum = reg[rest, :3].astype(int).mean(1)
    reg[rest, :3] = np.clip(np.stack([176 + lum * 0.45, 140 + lum * 0.55, 98 + lum * 0.55], 1), 0, 255).astype(np.uint8)
    # seam between parchment and seal: Faithless's own dark outline and gold trim, where the ribbon body is
    body = a[y + 2:y + h - 2, x + RIBBON_SEAL_X]
    on = body[:, 3] > 0
    body[on, :3] = (7, 4, 2)
    seal = a[y + 2:y + h - 2, x + RIBBON_SEAL_X + 1]
    seal[seal[:, 3] > 0, :3] = (238, 168, 47)
    # hovered option (0,204): 1.7.10 writes it in light yellow; darken the busy sprite under it
    hv = a[204:223, 0:108]
    hv[:, :, :3] = (hv[:, :, :3].astype(int) * 0.45).astype(np.uint8)
    return Image.fromarray(a)


# Creative tabs. Faithless's legacy tabs.png (and its 1.20.2+ sprites) are drawn for the 1.19.3+ creative screen:
# 26 px tabs on a 26 px pitch, seven columns. 1.7.10 reads 28 px cells, six columns (u = 28 * column; column 5 is the
# right-hand search/inventory tab), so every 1.7.10 tab cut across two of Faithless's tabs: the seams and stray banner
# edges the owner called broken. The sheet is rebuilt on 1.7.10's grid from the sprites, each widened 26 -> 28 by
# repeating its middle column, with the scroller sprites at 1.7.10's (232,0) / (244,0).
TAB_ROWS = (("top", "unselected"), ("top", "selected"), ("bottom", "unselected"), ("bottom", "selected"))
CSP = SP + "container/creative_inventory/"
CR = G + "container/creative_inventory/"


def _widen(s, w):
    a = np.asarray(s)
    mid = a.shape[1] // 2
    grow = w - a.shape[1]
    return Image.fromarray(np.concatenate([a[:, :mid]] + [a[:, mid:mid + 1]] * grow + [a[:, mid:]], axis=1))


def tabs_sheet(fl, style):
    """style 'faithless': its grey tabs (columns 1-5) and red banner (column 7) for 1.7.10's right-hand tab.
    style 'book': every tab is the banner, as the bookmarks of Faithless's recipe book (dark red, bright when picked)."""
    out = Image.new("RGBA", (256, 256))
    for r, (side, sel) in enumerate(TAB_ROWS):
        for c in range(6):
            n = 7 if (c == 5 or style == "book") else c + 1
            out.paste(_widen(fl.img(CSP + "tab_%s_%s_%d.png" % (side, sel, n)), 28), (28 * c, 32 * r))
    out.paste(fl.img(CSP + "scroller.png"), (232, 0))
    out.paste(fl.img(CSP + "scroller_disabled.png"), (244, 0))
    return out


GRID = (8, 17, 9, 5)          # 1.7.10 ContainerCreative: 9 x 5 item slots at (9 + 18c, 18 + 18r); hotbar at y 112


def creative_faithless(fl):
    """Faithless's wood-framed creative screen (its search tab, minus the search field) with its hotbar cells repeated
    over the item grid: its plain tab_items is an older grey, slotless panel whose dark top band swallowed row one."""
    srch = np.asarray(fl.img(CR + "tab_item_search.png")).copy()
    # header: the search field (80..171, 4..16) becomes more header
    srch[4:17, 80:172] = srch[4:17, 60:61]
    items = srch.copy()
    cells = srch[111:129, 8:170].copy()          # one hotbar row: 9 cells with their rails
    x0, y0, nc, nr = GRID
    for r in range(nr):
        items[y0 + 18 * r:y0 + 18 * r + 18, x0:x0 + 162] = cells
    return Image.fromarray(items), Image.fromarray(np.asarray(fl.img(CR + "tab_item_search.png")).copy())


def _nine(src, box, size, cut):
    """Nine-slice: corners of `cut` (l, t, r, b) px kept, edges stretched, centre scaled."""
    x0, y0, x1, y1 = box
    l, t, r, b = cut
    s = src.crop(box)
    w, h = size
    sw, sh = x1 - x0, y1 - y0
    out = Image.new("RGBA", size)
    xs = [(0, l, 0, l), (l, sw - r, l, w - r), (sw - r, sw, w - r, w)]
    ys = [(0, t, 0, t), (t, sh - b, t, h - b), (sh - b, sh, h - b, h)]
    for sx0, sx1, dx0, dx1 in xs:
        for sy0, sy1, dy0, dy1 in ys:
            piece = s.crop((sx0, sy0, sx1, sy1)).resize((dx1 - dx0, dy1 - dy0), Image.NEAREST)
            out.paste(piece, (dx0, dy0))
    return out


def creative_book(fl):
    """The recipe book's parchment page (Faithless's recipe_book.png, the owner's r007 screenshots) stretched to the
    1.7.10 creative panel, items floating on it in faint pressed cells, a recessed scroll groove and a dark search
    field like the recipe book's."""
    rb = fl.img(G + "recipe_book.png")
    page = _nine(rb, (0, 0, 147, 166), (195, 136), (12, 10, 20, 26))
    a = np.asarray(page).copy()
    ink = np.array([150, 120, 80])

    def frame(x0, y0, x1, y1, fill_mul, edge_mul):
        reg = a[y0:y1, x0:x1, :3].astype(float)
        reg *= fill_mul
        reg[0, :] *= edge_mul
        reg[:, 0] *= edge_mul
        a[y0:y1, x0:x1, :3] = np.clip(reg, 0, 255).astype(np.uint8)

    x0, y0, nc, nr = GRID
    for r in range(nr):
        for c in range(nc):
            frame(x0 + 18 * c + 1, y0 + 18 * r + 1, x0 + 18 * c + 18, y0 + 18 * r + 18, 0.95, 0.9)
    for c in range(nc):                                         # hotbar
        frame(x0 + 18 * c + 1, 111, x0 + 18 * c + 18, 129, 0.88, 0.85)
    a[108, 9:170, :3] = (a[108, 9:170, :3].astype(float) * 0.82).astype(np.uint8)    # a ruled line over the hotbar
    a[108, 9:170, 0] = np.minimum(255, a[108, 9:170, 0].astype(int) + 30).astype(np.uint8)
    frame(174, 17, 188, 130, 0.8, 0.75)                          # scroll groove
    items = Image.fromarray(a.copy())
    b = a.copy()
    b[4:16, 80:172, :3] = (52, 34, 26)                           # search field, the recipe book's dark box
    b[4, 80:172, :3] = (30, 20, 16)
    b[4:16, 80, :3] = (30, 20, 16)
    del ink

    def sheet(img):                         # 1.7.10 reads GUI UVs over 256x256: a 195x136 file gets stretched
        s = Image.new("RGBA", (256, 256))
        s.paste(img, (0, 0))
        return s
    return sheet(items), sheet(Image.fromarray(b))


def preview_creative(tabs, bg, title, font, sel=(1, 1)):
    """What 1.7.10's GuiContainerCreative draws (tabs, panel, scroller, title), without items, at 1x."""
    W, H = 195 + 8, 136 + 64
    gl, gt = 4, 32
    im = Image.new("RGBA", (W, H), (60, 80, 60, 255))
    srow, scol = sel

    def tab(row, col, selected):
        x = gl + 28 * col + (col if 0 < col < 5 else 0)
        if col == 5:
            x = gl + 195 - 28
        v = (32 if selected else 0) + (0 if row == 0 else 64)
        y = gt - 28 if row == 0 else gt + 136 - 4
        im.alpha_composite(tabs.crop((28 * col, v, 28 * col + 28, v + 32)), (x, y))
    for row in (0, 1):
        for col in range(6):
            if (row, col) != (srow, scol):
                tab(row, col, False)
    im.alpha_composite(bg.crop((0, 0, 195, 136)), (gl, gt))
    im.alpha_composite(tabs.crop((232, 0, 244, 15)), (gl + 175, gt + 18))
    tab(srow, scol, True)
    return font.draw(im, title, gl + 8, gt + 6, (64, 64, 64))


def part_gui(out, fl, mc, log, creative="faithless"):
    miss = []
    font = Font(mc)
    notes = []
    for n in DIRECT:
        p = G + "container/%s.png" % n
        if p not in fl.names:
            miss.append(n)
            continue
        im = fl.img(p)
        if n in TITLES:
            im = plaque_fix(im, TITLES[n], font, notes)
        if n == "enchanting_table":
            im = enchant_fix(im)
        out[p] = _png(im)
    inv = inventory(fl)
    out[G + "container/inventory.png"] = _png(inv)
    for n in CREATIVE[1:]:
        out[CR + "%s.png" % n] = fl.read(CR + "%s.png" % n)
    tabs = tabs_sheet(fl, "book" if creative == "book" else "faithless")
    items, search = creative_book(fl) if creative == "book" else creative_faithless(fl)
    out[CR + "tabs.png"] = _png(tabs)
    out[CR + "tab_items.png"] = _png(items)
    out[CR + "tab_item_search.png"] = _png(search)
    log["gui_notes"] = "; ".join(notes)
    icons = _paste_sheet(_img(mc, G + "icons.png"), fl, ICONS, miss)
    out[G + "icons.png"] = _png(icons)
    widgets = _paste_sheet(_img(mc, G + "widgets.png"), fl, WIDGETS, miss)
    out[G + "widgets.png"] = _png(widgets)
    # the armour slots' empty icons (items atlas) are drawn for Faithless's slot frames: they belong with its GUI
    for s in ("boots", "chestplate", "helmet", "leggings"):
        out[A + "textures/items/empty_armor_slot_%s.png" % s] = fl.read(A + "textures/item/empty_armor_slot_%s.png" % s)
    log["gui"] = ("%d containers (inventory remapped), creative tabs, icons.png + widgets.png from its sprites; "
                  "kept vanilla for: %s" % (len(DIRECT) + 1, " ".join(miss) or "nothing"))
