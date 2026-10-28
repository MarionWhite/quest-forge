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


def part_gui(out, fl, mc, log):
    miss = []
    for n in DIRECT:
        p = G + "container/%s.png" % n
        if p in fl.names:
            out[p] = fl.read(p)
        else:
            miss.append(n)
    out[G + "container/inventory.png"] = _png(inventory(fl))
    for n in CREATIVE:
        p = G + "container/creative_inventory/%s.png" % n
        out[p] = fl.read(p)
    icons = _paste_sheet(_img(mc, G + "icons.png"), fl, ICONS, miss)
    out[G + "icons.png"] = _png(icons)
    widgets = _paste_sheet(_img(mc, G + "widgets.png"), fl, WIDGETS, miss)
    out[G + "widgets.png"] = _png(widgets)
    # the armour slots' empty icons (items atlas) are drawn for Faithless's slot frames: they belong with its GUI
    for s in ("boots", "chestplate", "helmet", "leggings"):
        out[A + "textures/items/empty_armor_slot_%s.png" % s] = fl.read(A + "textures/item/empty_armor_slot_%s.png" % s)
    log["gui"] = ("%d containers (inventory remapped), creative tabs, icons.png + widgets.png from its sprites; "
                  "kept vanilla for: %s" % (len(DIRECT) + 1, " ".join(miss) or "nothing"))
