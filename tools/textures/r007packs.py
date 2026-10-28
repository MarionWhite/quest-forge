#!/usr/bin/env python3
"""r011: copy the best parts of the packs the owner named in Shader Lab round 7 into an overlay resource pack.

    py -3.10 -I tools/textures/r007packs.py --out C:\\qfb\\textures\\QF-r011-packs.zip [--parts items,cit,tnt,...]
    py -3.10 -I tools/textures/r007packs.py --sheet DIR      (contact sheets of what was taken, for review)

The owner, 2026-10-27: "copy from the other [packs] that we pointed out ... in round 7". Copying is allowed into the
private pack only (CLAUDE.md "Licences"; C:\\qf-world\\reference-packs\\README.txt). Nothing from those zips is ever
committed: this script reads them at build time, and its output zip is never committed or published.

The output is an OVERLAY: list it ABOVE the QF Textures build (renderq "resourcepacks": [QFTextures, this]). It does not
touch tools/textures/build_qf_textures.py (another agent edits that in parallel).

Parts (--parts, default all):
  items   Faithless v1.2 item sprites under 1.7.10 names (textures/items/), with its .mcmeta animations; bow pull
          stages picked from its pull predicates; compass/clock frame strips composited from its dial and needle parts.
  cit     Faithless per-effect potions (normal/strong/long caps) and per-enchantment books as MCPatcher CIT on 1.7.10
          damage bits / numeric enchantment ids, written at qf_items.py's paths so they REPLACE our r010 prototypes;
          worn-tool sprites (damage %) and stack piles (stackSize). CIT is off in the live config; renderq "cit": true.
  tnt     Faithless TNT (Standard Galactic lettering), the one block the owner asked for.
  books   Soartex Forever bookshelves: three random variants + its biome variants (CTM), replacing our drawn ones.
  mobs    Patrix 32x mob skins where the texture keeps the 1.7.10 model's aspect (judged in game; see MOB_SKIP).
  env     Conquest_ 1.8 environment files that 1.7.10 + our shader can show: particles, rain and snow, ambient sounds.
  gui     Faithless GUI re-composited onto 1.7.10's layouts (see gui section).
Block textures (tnt, bookshelves) get LabPBR _n/_s maps from labpbr.py, so the shader never pairs them with the
lower pack's maps for the old art.
"""
import argparse, io, json, os, re, sys, zipfile

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "shaders"))

REF = r"C:\qf-world\reference-packs"
FAITHLESS = os.path.join(REF, "Faithless", "Faithless.zip")
PATRIX = os.path.join(REF, "Patrix 32x", "Patrix_26.3_32x_basic.zip")
CONQUEST = os.path.join(REF, "Conquest_", "Conquest_1.8.zip")
SOARTEX = os.path.join(REF, "Soartex Forever", "Soartex Forever.zip")
LIVE = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), ".crazycraft4")
MC_JAR = os.path.join(LIVE, "bin", "minecraft.jar")

A = "assets/minecraft/"
T = A + "textures/"
ITEMS = T + "items/"
BLOCKS = T + "blocks/"
CIT = A + "mcpatcher/cit/"
CTM = A + "mcpatcher/ctm/"
PARTS = ("items", "cit", "tnt", "books", "mobs", "env", "gui")


class Pack:
    """Read-only view of a reference zip."""
    def __init__(self, path):
        self.z = zipfile.ZipFile(path)
        self.names = set(self.z.namelist())

    def has(self, n):
        return n in self.names

    def read(self, n):
        return self.z.read(n)

    def img(self, n):
        return Image.open(io.BytesIO(self.z.read(n))).convert("RGBA")

    def json(self, n):
        return json.loads(self.z.read(n).decode("utf-8-sig"))


def png(im):
    b = io.BytesIO()
    im.save(b, "PNG")
    return b.getvalue()


# --- items: 1.7.10 name -> modern item id (or "tex:<texture path under textures/item/>") ----------------------------
DYES = {"black": "ink_sac", "blue": "lapis_lazuli", "brown": "cocoa_beans", "white": "bone_meal",
        "silver": "light_gray_dye"}
ITEM_IDS = {
    "apple_golden": "golden_apple", "bed": "red_bed", "beef_cooked": "cooked_beef", "beef_raw": "beef",
    "boat": "oak_boat", "book_enchanted": "enchanted_book", "book_normal": "book", "book_writable": "writable_book",
    "book_written": "written_book", "bucket_empty": "bucket", "bucket_lava": "lava_bucket",
    "bucket_milk": "milk_bucket", "bucket_water": "water_bucket", "carrot_golden": "golden_carrot",
    "chicken_cooked": "cooked_chicken", "chicken_raw": "chicken", "door_iron": "iron_door", "door_wood": "oak_door",
    "fireball": "fire_charge", "fireworks": "firework_rocket", "fireworks_charge": "firework_star",
    "fireworks_charge_overlay": "tex:firework_star_overlay", "fish_clownfish_raw": "tropical_fish",
    "fish_cod_cooked": "cooked_cod", "fish_cod_raw": "cod", "fish_pufferfish_raw": "pufferfish",
    "fish_salmon_cooked": "cooked_salmon", "fish_salmon_raw": "salmon", "fishing_rod_cast": "tex:fishing_rod_cast",
    "fishing_rod_uncast": "tex:fishing_rod", "gold_horse_armor": "golden_horse_armor", "map_empty": "map",
    "map_filled": "filled_map", "melon": "melon_slice", "melon_speckled": "glistering_melon_slice",
    "minecart_chest": "chest_minecart", "minecart_command_block": "command_block_minecart",
    "minecart_furnace": "furnace_minecart", "minecart_hopper": "hopper_minecart", "minecart_normal": "minecart",
    "minecart_tnt": "tnt_minecart", "netherbrick": "nether_brick", "porkchop_cooked": "cooked_porkchop",
    "porkchop_raw": "porkchop", "potato_baked": "baked_potato", "potato_poisonous": "poisonous_potato",
    "potion_bottle_drinkable": "tex:potion", "potion_bottle_empty": "glass_bottle",
    "potion_bottle_splash": "tex:splash_potion", "potion_overlay": "tex:potion_overlay",
    "redstone_dust": "redstone", "reeds": "sugar_cane", "seeds_melon": "melon_seeds",
    "seeds_pumpkin": "pumpkin_seeds", "seeds_wheat": "wheat_seeds", "sign": "oak_sign", "slimeball": "slime_ball",
    "spider_eye_fermented": "fermented_spider_eye", "leather_boots_overlay": "tex:leather_boots_overlay",
    "leather_chestplate_overlay": "tex:leather_chestplate_overlay",
    "leather_helmet_overlay": "tex:leather_helmet_overlay", "leather_leggings_overlay": "tex:leather_leggings_overlay",
    "spawn_egg": "tex:spawn_egg", "spawn_egg_overlay": "tex:spawn_egg_overlay",
}
for _c in ("cyan", "gray", "green", "light_blue", "lime", "magenta", "orange", "pink", "purple", "red", "yellow"):
    DYES.setdefault(_c, _c + "_dye")
for _c, _id in DYES.items():
    ITEM_IDS["dye_powder_" + _c] = _id
for _m in ("axe", "hoe", "pickaxe", "shovel", "sword", "boots", "chestplate", "helmet", "leggings"):
    ITEM_IDS["gold_" + _m] = "golden_" + _m
    ITEM_IDS["wood_" + _m] = "wooden_" + _m
ITEM_SKIP = {"quiver", "ruby",                       # unused in 1.7.10
             "skull_creeper", "skull_skeleton", "skull_steve", "skull_wither", "skull_zombie",   # modern heads are 3D
             "bow_standby", "bow_pulling_0", "bow_pulling_1", "bow_pulling_2", "compass", "clock",   # special below
             # drawn for Faithless's slot frames: shipped with its GUI (r007gui.py), not alone
             "empty_armor_slot_boots", "empty_armor_slot_chestplate", "empty_armor_slot_helmet",
             "empty_armor_slot_leggings"}
# 1.7.10 bow stages (ItemBow.getItemIconForUseDuration): pulling_0 under 13 ticks, _1 from 13, _2 from 18 (of 20)
BOW_PULL = {"bow_pulling_0": 0.3, "bow_pulling_1": 0.7, "bow_pulling_2": 0.95}


def item_texture(fl, mid):
    """Faithless's GUI sprite for a modern item id: textures/item/<id>.png, else the model chain's layer0."""
    if mid.startswith("tex:"):
        p = T + "item/" + mid[4:] + ".png"
        return p if fl.has(p) else None
    p = T + "item/" + mid + ".png"
    if fl.has(p):
        return p
    m = A + "models/item/" + mid + ".json"
    for _ in range(6):
        if not fl.has(m):
            return None
        d = fl.json(m)
        lay = d.get("textures", {}).get("layer0")
        if lay:
            lay = lay.split(":")[-1]
            p = T + lay + ".png"
            return p if fl.has(p) else None
        par = d.get("parent", "").split(":")[-1]
        if not par.startswith("item/"):
            return None
        m = A + "models/" + par + ".json"
    return None


def bow_frame(fl, pull):
    """The bow sprite Faithless shows at this pull (last override whose pull <= value), with its nocked arrow.

    Faithless draws the arrow as a separate rotated plane (texture block/entity/arrow) in the 3D bow model; a 1.7.10
    pulling sprite must carry it. Rasterise that plane's south face (the side the GUI sees) into the 16x16 sprite:
    each pixel centre, rotated back about the element's origin, is looked up in the face's UV rectangle."""
    d = fl.json(A + "models/item/bow.json")
    best = None
    for o in d["overrides"]:
        pr = o["predicate"]
        if pr.get("pulling") == 1 and pr.get("pull", 0) <= pull:
            best = o["model"].split(":")[-1]
    m = fl.json(A + "models/" + best + ".json")
    tex = dict(m.get("textures", {}))
    elems = m.get("elements")
    par = m.get("parent", "").split(":")[-1]
    while elems is None and par:
        pm = fl.json(A + "models/" + par + ".json")
        elems = pm.get("elements")
        tex = dict(pm.get("textures", {}), **tex)
        par = pm.get("parent", "").split(":")[-1] if elems is None else ""
    sprite = fl.img(T + tex["layer0"].split(":")[-1] + ".png")
    arrow = np.asarray(fl.img(T + tex["1"].split(":")[-1] + ".png")).astype(np.float32)
    ah, aw = arrow.shape[:2]
    lay = np.zeros((16, 16, 4), np.float32)
    for e in elems or []:
        f = e["faces"].get("south")
        if not f or f["texture"] != "#1":
            continue
        (x0, y0, _), (x1, y1, _) = e["from"], e["to"]
        r = e.get("rotation") or {"angle": 0, "origin": [8, 8, 8]}
        a = np.radians(-r["angle"])               # inverse rotation about z (checked: string drawn to the lower right, head top left)
        ox, oy = r["origin"][0], r["origin"][1]
        u0, v0, u1, v1 = f["uv"]
        for py in range(16):
            for px in range(16):
                acc, n = np.zeros(4, np.float32), 0
                for sy in (0.25, 0.75):            # 2x2 supersampling, coverage in alpha
                    for sx in (0.25, 0.75):
                        X, Y = px + sx, 16 - (py + sy)
                        dx, dy = X - ox, Y - oy
                        mx, my = ox + dx * np.cos(a) - dy * np.sin(a), oy + dx * np.sin(a) + dy * np.cos(a)
                        if x0 <= mx <= x1 and y0 <= my <= y1:
                            u = u0 + (mx - x0) / (x1 - x0) * (u1 - u0)
                            v = v0 + (y1 - my) / (y1 - y0) * (v1 - v0)
                            c = arrow[min(ah - 1, int(v / 16 * ah)), min(aw - 1, int(u / 16 * aw))]
                            if c[3] > 0:
                                acc += c
                                n += 1
                if n >= 2:                         # pixel mostly covered: keep it, opaque (pixel art)
                    lay[py, px] = acc / n
                    lay[py, px, 3] = 255
    under = Image.fromarray(lay.astype(np.uint8), "RGBA")
    under.alpha_composite(sprite)                  # the bow and string over the arrow shaft
    return under


def compass_strip(fl, frames=32):
    """1.7.10's compass is one vertical strip, frame k = needle at k/frames of a turn (TextureCompass; frame 0 points
    ahead). Faithless's compass is 50 models picked by the 'angle' predicate, each showing item/compass/<n> to the
    GUI; frame k takes the model the predicate would pick at angle k/frames (same convention: 0 = ahead, clockwise)."""
    ov = fl.json(A + "models/item/compass.json")["overrides"]
    ov = sorted((o["predicate"]["angle"], o["model"].split(":")[-1]) for o in ov if "angle" in o["predicate"])
    strip = Image.new("RGBA", (16, 16 * frames))
    for k in range(frames):
        model = ([m for a, m in ov if a <= k / frames + 1e-9] or ["item/compass"])[-1]   # below the first: base model
        lay = fl.json(A + "models/" + model + ".json")["textures"]["layer0"].split(":")[-1]
        strip.paste(fl.img(T + lay + ".png"), (0, 16 * k))
    return strip


# Faithless's clock is a 3D dial whose hands are separate rotating elements: it has no per-time GUI frames to build
# 1.7.10's 64-frame clock strip from, so the clock stays as the lower pack has it.


def part_items(out, fl, mc, log):
    mcn = [n for n in mc.namelist() if n.startswith(ITEMS) and n.endswith(".png")]
    took, miss = [], []
    for n in sorted(mcn):
        name = n[len(ITEMS):-4]
        if name in ITEM_SKIP:
            continue
        mid = ITEM_IDS.get(name)
        if mid is None and name.startswith("record_"):
            mid = "music_disc_" + name[7:]
        mid = mid or name
        src = item_texture(fl, mid)
        if src is None:
            miss.append(name)
            continue
        out[n] = fl.read(src)
        if fl.has(src + ".mcmeta"):
            out[n + ".mcmeta"] = fl.read(src + ".mcmeta")
        took.append(name)
    out[ITEMS + "bow_standby.png"] = fl.read(T + "item/bow/bow.png")
    for name, pull in BOW_PULL.items():
        out[ITEMS + name + ".png"] = png(bow_frame(fl, pull))
    took += ["bow_standby"] + list(BOW_PULL)
    out[ITEMS + "compass.png"] = png(compass_strip(fl))
    out[ITEMS + "compass.png.mcmeta"] = b'{"animation": {}}'   # as vanilla's: a frame strip, not a broken sprite
    took.append("compass")
    log["items"] = "%d item sprites from Faithless; not in Faithless (kept as is): %s" % (len(took), " ".join(miss))
    return took


# --- cit: potions and books (1.7.10 damage bits / enchantment ids) ---------------------------------------------------
POTION_BITS = {1: "regeneration", 2: "swiftness", 3: "fire_resistance", 4: "poison", 5: "healing", 6: "night_vision",
               8: "weakness", 9: "strength", 10: "slowness", 12: "harming", 13: "water_breathing", 14: "invisibility"}
STRONG, LONG, SPLASH = 32, 64, 16384
ENCHANT_IDS = {0: "protection", 1: "fire_protection", 2: "feather_falling", 3: "blast_protection",
               4: "projectile_protection", 5: "respiration", 6: "aqua_affinity", 7: "thorns", 16: "sharpness",
               17: "smite", 18: "bane_of_arthropods", 19: "knockback", 20: "fire_aspect", 21: "looting",
               32: "efficiency", 33: "silk_touch", 34: "unbreaking", 35: "fortune", 48: "power", 49: "punch",
               50: "flame", 51: "infinity", 61: "luck_of_the_sea", 62: "lure"}
WORN = ["%s_%s" % (m, t) for m in ("wooden", "stone", "iron", "golden", "diamond")
        for t in ("sword", "pickaxe", "axe", "shovel", "hoe")]
STACKS = {"arrow": "arrow", "seeds_wheat": "wheat_seeds", "seeds_melon": "melon_seeds",
          "seeds_pumpkin": "pumpkin_seeds"}


def potion_sprite(fl, effect, variant, splash):
    """Faithless's bottle (full colour, untinted) with its cap, as one 16x16 sprite."""
    body = T + "item/potions/%s%s.png" % (effect, "_strong" if variant == "strong" else "")
    if not fl.has(body):
        body = T + "item/potions/%s.png" % effect
    im = fl.img(body)
    cap = "cap_%s%s" % ("splash" if splash else "normal", "_long" if variant == "long" else "")
    im.alpha_composite(fl.img(T + "item/potions/%s.png" % cap))
    return im


def part_cit(out, fl, mc, log):
    n = 0
    d = CIT + "potions/"                     # qf_items.py's folder: same file names replace the r010 prototypes
    clear = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    out[d + "clear.png"] = png(clear)
    for bits, eff in POTION_BITS.items():
        for splash in (False, True):
            for variant, vbits in (("normal", 0), ("strong", STRONG), ("long", LONG)):
                if variant == "strong" and not fl.has(T + "item/potions/%s_strong.png" % eff):
                    continue
                key = "%s%s%s" % (eff, "_splash" if splash else "", "" if variant == "normal" else "_" + variant)
                out[d + "fl_%s.png" % key] = png(potion_sprite(fl, eff, variant, splash))
                layer = "potion_bottle_splash" if splash else "potion_bottle_drinkable"
                dmg = bits | vbits | (SPLASH if splash else 0)
                # 0x406F: effect bits, strong, long and splash all must match (r010's rules used 0x400F)
                fname = eff + ("_splash" if splash else "") + ("" if variant == "normal" else "_" + variant)
                out[d + "%s.properties" % fname] = (
                    "type=item\nitems=minecraft:potion\ndamage=%d\ndamageMask=16495\n"
                    "texture.%s=fl_%s\ntexture.potion_overlay=clear\n" % (dmg, layer, key)).encode()
                n += 1
    d = CIT + "books/"
    for eid, name in ENCHANT_IDS.items():
        src = A + "optifine/cit/books/%s.png" % name
        if not fl.has(src):
            continue
        out[d + "%s.png" % name] = fl.read(src)
        out[d + "%s.properties" % name] = ("type=item\nitems=minecraft:enchanted_book\nenchantmentIDs=%d\n"
                                           "texture=%s\n" % (eid, name)).encode()
        n += 1
    # worn tools: Faithless's <tool>_1.._5 by the damage predicate (fraction of max damage used)
    d = CIT + "worn/"
    for tool in WORN:
        m = A + "models/item/%s.json" % tool
        if not fl.has(m):
            continue
        ov = [o for o in fl.json(m).get("overrides", []) if "damage" in o["predicate"]]
        ov.sort(key=lambda o: o["predicate"]["damage"])
        old = tool.replace("wooden_", "wood_").replace("golden_", "gold_")
        for i, o in enumerate(ov):
            lo = o["predicate"]["damage"]
            hi = ov[i + 1]["predicate"]["damage"] if i + 1 < len(ov) else 1.0
            tex = fl.json(A + "models/" + o["model"].split(":")[-1] + ".json")["textures"]["layer0"].split(":")[-1]
            nm = os.path.basename(tex)
            out[d + nm + ".png"] = fl.read(T + tex + ".png")
            out[d + nm + ".properties"] = ("type=item\nitems=minecraft:%s\ndamage=%d%%-%d%%\ntexture=%s\n"
                                           % (old, round(lo * 100), round(hi * 100) - (1 if hi < 1 else 0), nm)).encode()
            n += 1
    d = CIT + "stacks/"
    for old, mid in STACKS.items():
        for k in (1, 2, 3):
            pr = A + "optifine/cit/stackables/%s%d.properties" % (mid, k)
            if not fl.has(pr):
                continue
            props = dict(l.split("=", 1) for l in fl.read(pr).decode().splitlines() if "=" in l)
            tex = A + "optifine/cit/stackables/%s%d.png" % (mid, k)
            if not fl.has(tex):
                continue
            out[d + "%s%d.png" % (old, k)] = fl.read(tex)
            ident = {"arrow": "arrow", "seeds_wheat": "wheat_seeds", "seeds_melon": "melon_seeds",
                     "seeds_pumpkin": "pumpkin_seeds"}[old]
            out[d + "%s%d.properties" % (old, k)] = ("type=item\nitems=minecraft:%s\nstackSize=%s\ntexture=%s%d\n"
                                                     % (ident, props["stackSize"], old, k)).encode()
            n += 1
    log["cit"] = "%d CIT rules (potions per effect x normal/strong/long x drink/splash, %d books, worn tools, stacks)" % (
        n, sum(1 for k in out if k.startswith(CIT + "books/") and k.endswith(".properties")))
    return n


# --- tnt (Faithless) and bookshelves (Soartex) --------------------------------------------------------------------
def block_pbr(out, path, im):
    """LabPBR maps for a block texture we bring in, so the lower pack's maps (other art) never apply."""
    import gen_surface_pack as gsp
    import labpbr
    a = np.asarray(im.convert("RGBA"))
    mat = os.path.basename(path)[:-4]
    kind, _, strength = gsp.classify(mat)
    n, s = labpbr.pbr_maps(mat, a, strength, kind, None)
    out[path[:-4] + "_n.png"] = png(Image.fromarray(n))
    out[path[:-4] + "_s.png"] = png(Image.fromarray(s))


def part_tnt(out, fl, mc, log):
    """Faithless's TNT with its Standard Galactic lettering on every block. (Faithless's own blockstate letters one
    block in five, tnt_side2 at weight 1 of 5; the owner, r011: "I don't know why some of them have the normal
    lettering", so r012 drops the mix.) The CTM rule stays at its path, one tile, so a lower pack's rule never wins."""
    for side in ("side", "top", "bottom"):
        src = T + "block/tnt_%s.png" % ("side2" if side == "side" else side)
        p = BLOCKS + "tnt_%s.png" % side
        out[p] = fl.read(src)
        block_pbr(out, p, fl.img(src))
    d = CTM + "tnt/"
    out[d + "0.png"] = fl.read(T + "block/tnt_side2.png")
    block_pbr(out, d + "0.png", fl.img(T + "block/tnt_side2.png"))
    out[d + "tnt.properties"] = b"matchTiles=tnt_side\nmethod=fixed\nfaces=sides\ntiles=0\n"
    log["tnt"] = "Faithless TNT (+ our LabPBR maps); enchanting-table lettering on every block"


SOARTEX_VARIANTS = ("brim", "color", "react", "tome")   # its biome rules already use 1.7 names (swamplandm, hell)


def part_books(out, so, mc, log):
    """Soartex Forever's bookshelf: 3 random sides (its blockstate) + biome variants. 64x on a 1.7.10 cube."""
    d = CTM + "bookshelf/"
    tiles = []
    for i in (1, 2, 3):
        p = d + "%d.png" % (i - 1)
        im = so.img(T + "block/bookshelf/%d.png" % i)
        out[p] = png(im)
        block_pbr(out, p, im)
        tiles.append(p)
    out[BLOCKS + "bookshelf.png"] = png(so.img(T + "block/bookshelf/1.png"))   # item icon, no-CTM fallback
    block_pbr(out, BLOCKS + "bookshelf.png", so.img(T + "block/bookshelf/1.png"))
    # same path as build_qf_textures.py's rule, so this one replaces our drawn shelves (tiles 0-2; 3 is not used)
    out[d + "bookshelf.properties"] = b"matchTiles=bookshelf\nmethod=random\nfaces=sides\ntiles=0-2\n"
    for var in SOARTEX_VARIANTS:
        src = A + "optifine/ctm/bookshelf/%s/%s.png" % (var, var)
        if not so.has(src):
            continue
        rule = so.read(A + "optifine/ctm/bookshelf/%s/bookshelf.properties" % var).decode()
        biomes = re.search(r"^biomes=(.*)$", rule, re.M).group(1).strip()
        p = d + "%s/%s.png" % (var, var)
        im = so.img(src)
        out[p] = png(im)
        block_pbr(out, p, im)
        out[d + "%s/bookshelf_%s.properties" % (var, var)] = (
            "matchTiles=bookshelf\nmethod=fixed\nfaces=sides\ntiles=%s\nbiomes=%s\nweight=10\n" % (var, biomes)).encode()
    log["books"] = "Soartex bookshelves: 3 random variants + %d biome variants" % len(SOARTEX_VARIANTS)


# --- mobs (Patrix) ----------------------------------------------------------------------------------------------------
MOBS = {   # 1.7.10 entity texture -> Patrix 26.3 path (under textures/entity/)
    "creeper/creeper.png": "creeper/creeper.png", "zombie/zombie.png": "zombie/zombie.png",
    "spider/spider.png": "spider/spider.png", "spider/cave_spider.png": "spider/cave_spider.png",
    "enderman/enderman.png": "enderman/enderman.png", "enderman/enderman_eyes.png": "enderman/enderman_eyes.png",
    "sheep/sheep.png": "sheep/sheep.png", "sheep/sheep_fur.png": "sheep/sheep_wool.png",
    "ghast/ghast.png": "ghast/ghast.png", "ghast/ghast_shooting.png": "ghast/ghast_shooting.png",
    "wolf/wolf.png": "wolf/wolf.png", "wolf/wolf_tame.png": "wolf/wolf_tame.png",
    "wolf/wolf_angry.png": "wolf/wolf_angry.png", "slime/slime.png": "slime/slime.png",
    "slime/magmacube.png": "slime/magmacube.png", "snowman.png": "snow_golem/snow_golem.png",
    "iron_golem.png": "iron_golem/iron_golem.png", "pig/pig.png": "pig/pig_temperate.png",
    "witch.png": "witch/witch.png", "cat/ocelot.png": "cat/ocelot.png", "cat/black.png": "cat/cat_tabby.png",
    "cat/red.png": "cat/cat_red.png", "cat/siamese.png": "cat/cat_siamese.png", "squid.png": "squid/squid.png",
    "cow/cow.png": "cow/cow_temperate.png", "skeleton/skeleton.png": "skeleton/skeleton.png",
    "skeleton/wither_skeleton.png": "skeleton/wither_skeleton.png", "chicken.png": "chicken/chicken_temperate.png",
    "silverfish.png": "silverfish/silverfish.png", "blaze.png": "blaze/blaze.png", "bat.png": "bat/bat.png",
    "zombie_pigman.png": "piglin/zombified_piglin.png", "wither/wither.png": "wither/wither.png",
}
# From the in-game lineup (render 1027-222844-textures-r011-packs, r11p1 r11_mob_1..6): skins whose layout is Patrix's
# CEM one, not the 1.7.10 model's. Seen broken: chicken (a plain box), cow (body pattern on the head), sheep (the wool
# has no face window: a blank block), blaze (head missing), witch (hat broken into a floating ring), zombie pigman
# (a piglin face on a pigman body). Not seen in a frame yet, held back until they are: slime, magma cube, ghast,
# squid, bat, wither.
MOB_SKIP = {"chicken.png", "cow/cow.png", "sheep/sheep.png", "sheep/sheep_fur.png", "blaze.png", "witch.png",
            "zombie_pigman.png", "slime/slime.png", "slime/magmacube.png", "ghast/ghast.png",
            "ghast/ghast_shooting.png", "squid.png", "bat.png", "wither/wither.png",
            "iron_golem.png"}     # r11p3: square like vanilla, but a CEM layout (face lands on the chest)


# r012, the owner: "We need to fix the ones that still have vanilla skins" and "find something for the passive mobs".
# Every 1.7.10 mob texture now gets non-vanilla art, in this order: Patrix as it is (layout already 1.7.10's), Patrix
# remapped face by face onto 1.7.10's boxes (patrix_remap.py; mode "remap" only), then Conquest_ 1.8, whose entity
# textures are drawn for the 1.7/1.8 models (villagers, horses, squid, bat, slimes, ghast, wither, dragon...).
MOB_TEX = ("bat.png", "blaze.png", "chicken.png", "cow/", "creeper/creeper.png", "enderdragon/dragon.png",
           "enderman/", "ghast/", "horse/", "iron_golem.png", "slime/", "pig/pig.png", "sheep/", "silverfish.png",
           "skeleton/", "snowman.png", "spider/", "squid.png", "villager/", "witch.png", "wither/", "wolf/",
           "zombie/", "zombie_pigman.png", "cat/")


def part_mobs(out, px, mc, log, mode="remap", cq=None):
    import patrix_remap
    E = T + "entity/"
    took, aspect, remapped, conq, left = [], [], [], [], []
    for v, p in MOBS.items():
        if v in MOB_SKIP or not px.has(E + p):
            continue
        van = Image.open(io.BytesIO(mc.read(E + v)))
        im = px.img(E + p)
        if im.width * van.height != im.height * van.width:
            aspect.append(v)
            continue
        out[E + v] = png(im)
        took.append(v)
    if mode == "remap":
        for v in patrix_remap.SPECS:
            out[E + v] = png(patrix_remap.remap(px, v))
            remapped.append(v)
    if cq is not None:
        for n in sorted(mc.namelist()):
            if not (n.startswith(E) and n.endswith(".png")):
                continue
            v = n[len(E):]
            if not v.startswith(MOB_TEX) or E + v in out:
                continue
            src = next((q for q in (E + v, "minecraft/textures/entity/" + v) if cq.has(q)), None)
            if src is None:
                left.append(v)
                continue
            van = Image.open(io.BytesIO(mc.read(n)))
            im = cq.img(src)
            if im.width * van.height != im.height * van.width:
                left.append(v)
                continue
            out[E + v] = png(im)
            conq.append(v)
    log["mobs"] = ("%d Patrix as is; %d Patrix remapped (%s); %d Conquest (%s); still vanilla: %s" % (
        len(took), len(remapped), " ".join(r[:-4] for r in remapped), len(conq), " ".join(c[:-4] for c in conq),
        " ".join(left) or "none"))
    return took


# --- env (Conquest) ------------------------------------------------------------------------------------------------------
ENV_FILES = ["textures/particle/particles.png", "textures/particle/footprint.png",
             "textures/environment/rain.png", "textures/environment/snow.png"]


def part_env(out, cq, mc, log):
    took = []
    for f in ENV_FILES:
        if cq.has(A + f):
            out[A + f] = cq.read(A + f)
            took.append(f)
    sounds = [n for n in cq.names if n.startswith(A + "sounds/ambient/") and n.endswith(".ogg")]
    for n in sounds:
        out[n] = cq.read(n)
    log["env"] = "Conquest: %s; %d ambient sounds (cave, rain) at their 1.7.10 paths" % (" ".join(took), len(sounds))


# --- main ------------------------------------------------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", help="overlay zip (never commit it)")
    ap.add_argument("--parts", default=",".join(PARTS), help="comma list of: " + ",".join(PARTS))
    ap.add_argument("--mc-jar", default=MC_JAR, help="1.7.10 client jar, read only (names and layouts)")
    ap.add_argument("--mobs", default="remap", choices=("remap", "conquest", "patrix"),
                    help="mobs part: Patrix as is + Patrix remapped + Conquest for the rest (remap), Patrix as is + "
                         "Conquest (conquest), or Patrix as is only (patrix, r011)")
    ap.add_argument("--creative", default="faithless", choices=("faithless", "book"),
                    help="gui part: creative screen style (Faithless's framed panel, or its recipe-book page)")
    a = ap.parse_args()
    parts = [p for p in a.parts.split(",") if p]
    bad = [p for p in parts if p not in PARTS]
    if bad:
        sys.exit("unknown part(s): %s" % bad)
    mc = zipfile.ZipFile(a.mc_jar)
    out, log = {}, {}
    fl = Pack(FAITHLESS) if {"items", "cit", "tnt", "gui"} & set(parts) else None
    if "items" in parts:
        part_items(out, fl, mc, log)
    if "cit" in parts:
        part_cit(out, fl, mc, log)
    if "tnt" in parts:
        part_tnt(out, fl, mc, log)
    if "books" in parts:
        part_books(out, Pack(SOARTEX), mc, log)
    if "mobs" in parts:
        part_mobs(out, Pack(PATRIX), mc, log, mode=a.mobs, cq=Pack(CONQUEST) if a.mobs != "patrix" else None)
    if "env" in parts:
        part_env(out, Pack(CONQUEST), mc, log)
    if "gui" in parts:
        import r007gui
        r007gui.part_gui(out, fl, mc, log, creative=a.creative)
    meta = {"pack": {"pack_format": 1, "description": "QF r011: Faithless items/GUI, Patrix mobs, Soartex shelves, "
                                                      "Conquest effects (private; never redistribute)"}}
    credits = ("Copied at build time for a private friends' server pack only (owner's call 2026-10-27). Never "
               "redistribute this zip.\n"
               "  Faithless by Stitch: https://modrinth.com/resourcepack/faithless (items, potions, books, GUI, TNT)\n"
               "  Patrix 32x by Patrix: https://modrinth.com/resourcepack/patrix-32x (mob skins)\n"
               "  Soartex Forever by Soar49 and fans: https://modrinth.com/resourcepack/soartex-forever (bookshelves)\n"
               "  Conquest_ 1.8: https://modrinth.com/resourcepack/conquest_ (particles, weather, ambient sounds)\n")
    with zipfile.ZipFile(a.out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("pack.mcmeta", json.dumps(meta, indent=1))
        z.writestr("CREDITS-r011.txt", credits)
        for k in sorted(out):
            z.writestr(k, out[k])
    for k in parts:
        print("%-6s %s" % (k, log.get(k, "")))
    print("-> %s (%d files, %.1f MB)" % (a.out, len(out), os.path.getsize(a.out) / 1e6))


if __name__ == "__main__":
    main()
