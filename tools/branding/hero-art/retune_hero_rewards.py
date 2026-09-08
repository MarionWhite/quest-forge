# -*- coding: utf-8 -*-
"""Retune Hall of Heroes rewards from real Superheroes Unlimited / Legends getMaterials()."""
from __future__ import print_function

import json
import os
import re
import shutil
import struct
import zipfile
from collections import OrderedDict
from datetime import datetime

SRC = r"C:\Users\a2dsu\AppData\Roaming\.crazycraft4\config\betterquesting\DefaultQuests.json"
JAR = r"C:\Users\a2dsu\AppData\Roaming\.crazycraft4\mods\1Legends-1.7.10-8.6.2.jar"
WORK = r"C:\Users\a2dsu\OneDrive\Desktop\QuestForge-Work\_heroes-20260904"

# ~30% of one piece (owner asked 20-40%, never a full next piece)
PIECE_FRACTION = 0.30
FULLSET_FRACTION = 0.40
DIVIDE_WHEN_ARMOR_INGREDIENT = True

LB_COMMON, LB_UNCOMMON, LB_RARE, LB_EPIC, LB_LEGEND = 0, 1, 2, 3, 4

# 1.7.10 MCP field names we expect in getMaterials
VANILLA_ITEMS = {
    "field_151043_k": "minecraft:diamond",
    "field_151042_j": "minecraft:iron_ingot",
    "field_151074_bl": "minecraft:gold_ingot",
    "field_151116_aA": "minecraft:leather",
    "field_151007_F": "minecraft:string",
    "field_151055_y": "minecraft:paper",
    "field_151044_h": "minecraft:coal",
    "field_151145_ak": "minecraft:redstone",
    "field_151166_bC": "minecraft:nether_star",
    "field_151156_bN": "minecraft:nether_star",
    "field_151045_i": "minecraft:diamond",
    "field_151072_bj": "minecraft:glowstone_dust",
    "field_151065_br": "minecraft:dye",
    "field_151100_aR": "minecraft:dye",
    "field_151121_aF": "minecraft:slime_ball",
    "field_151069_bo": "minecraft:gunpowder",
    "field_151016_H": "minecraft:gunpowder",
    "field_151123_aH": "minecraft:bone",
    "field_151070_bp": "minecraft:ender_pearl",
    "field_151068_bn": "minecraft:blaze_rod",
    "field_151064_bs": "minecraft:ghast_tear",
    "field_151073_bk": "minecraft:sugar",
    "field_151015_O": "minecraft:wheat",
    "field_151120_aE": "minecraft:feather",
    "field_151009_A": "minecraft:flint",
    "field_151106_aX": "minecraft:emerald",
    "field_151075_bm": "minecraft:fermented_spider_eye",
    "field_151024_Q": "minecraft:leather_helmet",
    "field_151027_R": "minecraft:leather_chestplate",
    "field_151026_S": "minecraft:leather_leggings",
    "field_151021_T": "minecraft:leather_boots",
}
VANILLA_BLOCKS = {
    "field_150397_co": "minecraft:stained_glass_pane",
    "field_150359_w": "minecraft:glass_pane",
    "field_150410_aZ": "minecraft:glass_pane",
    "field_150399_cn": "minecraft:stained_glass",
    "field_150359_w": "minecraft:glass",
    "field_150340_R": "minecraft:gold_block",
    "field_150325_L": "minecraft:wool",
    "field_150343_Z": "minecraft:obsidian",
    "field_150339_S": "minecraft:iron_block",
    "field_150484_ah": "minecraft:redstone_block",
    "field_150451_bX": "minecraft:emerald_block",
    "field_150475_bE": "minecraft:diamond_block",
}

BANNED_IDS = {
    "minecraft:nether_star",
    "legends:mjolnir",
}
BANNED_SUBSTR = (
    "nether_star", "projecte", "morph", "klein", "pe_matter", "pe_covalence",
    "mjolnir",
)
ARMOR_FIELD_HINTS = (
    "helmet", "chestplate", "leggings", "boots",
    "ironManChest", "ironManLegs", "ironManBoots", "ironManHelmet",
    "Chest", "Legs", "Boots", "Helmet",
)
ARMOR_ID_RE = re.compile(
    r"(helmet|chestplate|leggings|boots)$|ironMan(Chest|Legs|Boots|Helmet)",
    re.I,
)

# Iron Man / War Machine getName() is computed ("ironman_mark" + index), not a ldc.
CLASS_REGNAME = {
    "com/tihyo/superheroes/characters/ironman/UnderArmor.class": "ironman_mark0",
    "com/tihyo/superheroes/characters/ironman/Mark1.class": "ironman_mark1",
    "com/tihyo/superheroes/characters/ironman/Mark3.class": "ironman_mark3",
    "com/tihyo/superheroes/characters/ironman/Mark7.class": "ironman_mark7",
    "com/tihyo/superheroes/characters/ironman/Mark21.class": "ironman_mark21",
    "com/tihyo/superheroes/characters/WarMachineMark1.class": "warmachine_mark1",
}
NAME_ALIASES = {
    "warmachine_mark": "warmachine_mark1",
    "ironman_mark": None,  # parent string; use CLASS_REGNAME
}

# Themed non-armor extras (must exist in lang). Never armor.
LINE_GADGETS = {
    "batman": [("legends:grapplingHook", 1, 0)],
    "nightwing": [("legends:grapplingHook", 1, 0)],
    "redhood": [("legends:grapplingHook", 1, 0)],
    "spiderman": [("legends:webCartridge", 4, 0)],
    "spiderman2099": [("legends:webCartridge", 4, 0)],
    "symbiotespiderman": [("legends:webCartridge", 4, 0)],
    "ironspider": [("legends:webCartridge", 4, 0)],
    "joker": [("legends:jokerCard", 8, 0)],
    "deadpool": [("legends:chimichanga", 4, 0)],
    "greenarrow": [("legends:kryptoniteArrow", 2, 0)],
    "scarecrow": [("legends:gasPellet", 2, 0)],
    "flash": [("legends:lightningIngot", 2, 0)],
}

MAJOR_LINES = {
    "superman", "batman", "wonderwoman", "flash", "captainamerica",
    "thor", "hulk", "blackpanther", "spiderman",
    "ironman_mark3", "ironman_mark7", "ironman_mark21", "warmachine_mark1",
}
HARDEST_LEGENDARY = {
    "closet", "ironman_mark7",
}

# Unique 1-count keys: never reward at 100% of a piece ingredient.
SKIP_UNIQUE_NAMES = (
    "Logo", "logo", "Ring", "Reactor", "Gem", "clothStar", "batbelt",
    "capShield", "lasso", "pantherNecklace", "mjolnir", "webShooters",
    "flashRing", "reverseFlashRing", "regulator", "miniArcReactor",
    "palladiumArcReactor", "vibraniumArcReactor",
)


# ---------------------------------------------------------------------------
# Class-file helpers
# ---------------------------------------------------------------------------

def _u1(b, i):
    return b[i], i + 1


def _u2(b, i):
    return struct.unpack(">H", b[i:i + 2])[0], i + 2


def _u4(b, i):
    return struct.unpack(">I", b[i:i + 4])[0], i + 4


def parse_constant_pool(data):
    magic, i = _u4(data, 0)
    if magic != 0xCAFEBABE:
        raise ValueError("not a class")
    _min, i = _u2(data, i)
    _maj, i = _u2(data, i)
    count, i = _u2(data, i)
    cp = [None]
    n = 1
    while n < count:
        tag = data[i]
        i += 1
        if tag == 1:
            ln, i = _u2(data, i)
            s = data[i:i + ln].decode("utf-8", "replace")
            i += ln
            cp.append(("Utf8", s))
        elif tag == 3:
            v, i = _u4(data, i)
            cp.append(("Integer", struct.unpack(">i", struct.pack(">I", v))[0]))
        elif tag == 4:
            i += 4
            cp.append(("Float", None))
        elif tag in (5, 6):
            i += 8
            cp.append(("Long" if tag == 5 else "Double", None))
            cp.append(None)
            n += 1
        elif tag == 7:
            idx, i = _u2(data, i)
            cp.append(("Class", idx))
        elif tag == 8:
            idx, i = _u2(data, i)
            cp.append(("String", idx))
        elif tag in (9, 10, 11):
            cls, i = _u2(data, i)
            nt, i = _u2(data, i)
            kind = {9: "Fieldref", 10: "Methodref", 11: "InterfaceMethodref"}[tag]
            cp.append((kind, cls, nt))
        elif tag == 12:
            n1, i = _u2(data, i)
            n2, i = _u2(data, i)
            cp.append(("NameAndType", n1, n2))
        elif tag == 15:
            i += 3
            cp.append(("MethodHandle", None))
        elif tag == 16:
            i += 2
            cp.append(("MethodType", None))
        elif tag == 18:
            i += 4
            cp.append(("InvokeDynamic", None))
        else:
            raise ValueError("unknown cp tag %s" % tag)
        n += 1
    return cp, i


def utf8(cp, idx):
    if idx and cp[idx] and cp[idx][0] == "Utf8":
        return cp[idx][1]
    return ""


def cp_string(cp, idx):
    if not idx or not cp[idx]:
        return ""
    if cp[idx][0] == "String":
        return utf8(cp, cp[idx][1])
    if cp[idx][0] == "Utf8":
        return cp[idx][1]
    return ""


def field_info(cp, idx):
    ent = cp[idx]
    if not ent or ent[0] != "Fieldref":
        return None
    cls = utf8(cp, cp[ent[1]][1]) if cp[ent[1]][0] == "Class" else ""
    nt = cp[ent[2]]
    name = utf8(cp, nt[1])
    desc = utf8(cp, nt[2])
    return cls, name, desc


def method_info(cp, idx):
    ent = cp[idx]
    if not ent or ent[0] not in ("Methodref", "InterfaceMethodref"):
        return None
    cls = utf8(cp, cp[ent[1]][1]) if cp[ent[1]][0] == "Class" else ""
    nt = cp[ent[2]]
    name = utf8(cp, nt[1])
    desc = utf8(cp, nt[2])
    return cls, name, desc


INSN_LEN = {}
for op in range(256):
    INSN_LEN[op] = 1
for op in (0x10, 0x12, 0x15, 0x16, 0x17, 0x18, 0x19, 0x36, 0x37, 0x38, 0x39, 0x3A,
           0xA9, 0xBC):
    INSN_LEN[op] = 2
for op in (0x11, 0x13, 0x14, 0x84, 0x99, 0x9A, 0x9B, 0x9C, 0x9D, 0x9E, 0x9F, 0xA0,
           0xA1, 0xA2, 0xA3, 0xA4, 0xA5, 0xA6, 0xA7, 0xA8, 0xC6, 0xC7,
           0xB2, 0xB3, 0xB4, 0xB5, 0xB6, 0xB7, 0xB8, 0xBB, 0xBD, 0xC0, 0xC1):
    INSN_LEN[op] = 3
INSN_LEN[0xC5] = 4  # multianewarray
INSN_LEN[0xB9] = 5  # invokeinterface
INSN_LEN[0xBA] = 5  # invokedynamic
INSN_LEN[0xC8] = 5  # goto_w
INSN_LEN[0xC9] = 5  # jsr_w


def iter_insns(code):
    i = 0
    n = len(code)
    while i < n:
        op = code[i]
        if op == 0xAA:  # tableswitch
            j = (i + 4) & ~3
            default, lo, hi = struct.unpack(">iii", code[j:j + 12])
            count = hi - lo + 1
            j += 12 + 4 * count
            yield i, op, code[i:j]
            i = j
        elif op == 0xAB:  # lookupswitch
            j = (i + 4) & ~3
            default, npairs = struct.unpack(">ii", code[j:j + 8])
            j += 8 + 8 * npairs
            yield i, op, code[i:j]
            i = j
        elif op == 0xC4:  # wide
            op2 = code[i + 1]
            ln = 6 if op2 == 0x84 else 4
            yield i, op, code[i:i + ln]
            i += ln
        else:
            ln = INSN_LEN.get(op, 1)
            yield i, op, code[i:i + ln]
            i += ln


def parse_methods(data, cp, start):
    i = start
    flags, i = _u2(data, i)
    this, i = _u2(data, i)
    sup, i = _u2(data, i)
    icount, i = _u2(data, i)
    for _ in range(icount):
        i += 2
    fcount, i = _u2(data, i)
    for _ in range(fcount):
        i += 6
        ac, i = _u2(data, i)
        for _ in range(ac):
            i += 2
            alen, i = _u4(data, i)
            i += alen
    mcount, i = _u2(data, i)
    methods = []
    for _ in range(mcount):
        acc, i = _u2(data, i)
        nidx, i = _u2(data, i)
        didx, i = _u2(data, i)
        ac, i = _u2(data, i)
        code = None
        for _a in range(ac):
            an, i = _u2(data, i)
            alen, i = _u4(data, i)
            aval = data[i:i + alen]
            i += alen
            if utf8(cp, an) == "Code" and len(aval) >= 8:
                clen = struct.unpack(">I", aval[4:8])[0]
                code = aval[8:8 + clen]
        methods.append((utf8(cp, nidx), utf8(cp, didx), code))
    return methods


def extract_getname(methods, cp):
    for name, desc, code in methods:
        if name == "getName" and desc == "()Ljava/lang/String;" and code:
            for _, op, raw in iter_insns(code):
                if op == 0x12:
                    s = cp_string(cp, raw[1])
                    if s:
                        return s
                if op in (0x13, 0x14):
                    idx = struct.unpack(">H", raw[1:3])[0]
                    s = cp_string(cp, idx)
                    if s:
                        return s
    return None


def int_from_insn(op, raw, cp):
    if 0x02 <= op <= 0x08:  # iconst_m1 .. iconst_5
        return op - 0x03
    if op == 0x10:
        return struct.unpack("b", raw[1:2])[0]
    if op == 0x11:
        return struct.unpack(">h", raw[1:3])[0]
    if op == 0x12:
        ent = cp[raw[1]]
        if ent and ent[0] == "Integer":
            return ent[1]
    if op == 0x13:
        idx = struct.unpack(">H", raw[1:3])[0]
        ent = cp[idx]
        if ent and ent[0] == "Integer":
            return ent[1]
    return None


def extract_getmaterials(methods, cp):
    want = "(Lnet/minecraft/entity/player/EntityPlayer;Ljava/lang/String;)Ljava/util/List;"
    stacks = []
    for name, desc, code in methods:
        if name != "getMaterials" or not code:
            continue
        if desc != want and "getMaterials" == name:
            # still try
            pass
        pending_field = None
        ints = []
        for _, op, raw in iter_insns(code):
            if op == 0xB2:  # getstatic
                idx = struct.unpack(">H", raw[1:3])[0]
                fi = field_info(cp, idx)
                if fi:
                    pending_field = fi
                    ints = []
            elif pending_field is not None:
                iv = int_from_insn(op, raw, cp)
                if iv is not None:
                    ints.append(iv)
                elif op == 0xB7:  # invokespecial
                    idx = struct.unpack(">H", raw[1:3])[0]
                    mi = method_info(cp, idx)
                    if mi and mi[1] == "<init>" and "ItemStack" in mi[0]:
                        stacks.append((pending_field, list(ints), mi[2]))
                    pending_field = None
                    ints = []
                elif op in (0xBB, 0x59, 0x57, 0x00):
                    continue
                elif op in (0xB6, 0xB9, 0xB8):
                    # other calls — keep waiting a bit
                    continue
        break
    return stacks


def field_to_id(cls, fname, lang_items):
    """Map a getstatic field to a registry id. Returns (id or None, reason)."""
    simple = cls.split("/")[-1]
    if fname in ARMOR_FIELD_HINTS or any(h == fname for h in ARMOR_FIELD_HINTS):
        return None, "armor-field"
    if re.search(r"(Helmet|Chestplate|Leggings|Boots|Chest|Legs)$", fname):
        if "RegisterItems" not in cls:
            return None, "armor-field"
    if "init/Items" in cls:
        vid = VANILLA_ITEMS.get(fname)
        if vid:
            if vid in BANNED_IDS:
                return None, "banned-vanilla"
            return vid, "vanilla-item"
        return None, "unmapped-vanilla-item:%s" % fname
    if "init/Blocks" in cls:
        vid = VANILLA_BLOCKS.get(fname)
        if vid:
            return vid, "vanilla-block"
        return None, "unmapped-vanilla-block:%s" % fname
    if fname in lang_items or ("item.%s.name" % fname) in lang_items:
        return "legends:" + fname, "lang"
    # field name is usually the registry name
    if simple.startswith("Register"):
        return "legends:" + fname, "field-guess"
    return None, "unknown-field:%s.%s" % (simple, fname)


def stack_from_ctor(field, ints, desc):
    """ItemStack constructors: (Item), (Item,I), (Item,II), (Block,I), (Block,II)."""
    count, dmg = 1, 0
    # desc like (Lnet/minecraft/item/Item;II)V
    args = desc[desc.find("(") + 1:desc.find(")")]
    # count I's after the object type
    i_count = args.count("I")
    if i_count == 1:
        count = ints[0] if ints else 1
    elif i_count >= 2:
        if len(ints) >= 2:
            count, dmg = ints[0], ints[1]
        elif len(ints) == 1:
            count = ints[0]
    elif i_count == 0:
        count, dmg = 1, 0
    return count, dmg


# ---------------------------------------------------------------------------
# Recipe + reward math
# ---------------------------------------------------------------------------

def is_armor_id(item_id):
    n = (item_id or "").split(":")[-1].replace(".", "_")
    if ARMOR_ID_RE.search(n):
        # don't treat "rocket" etc. as armor; require helmet/chest/legs/boots token
        low = n.lower()
        return low.endswith(("helmet", "chestplate", "leggings", "boots")) or low in (
            "ironmanchest", "ironmanlegs", "ironmanboots", "ironmanhelmet",
        )
    return False


def is_unique_key(item_id):
    name = item_id.split(":")[-1]
    return any(s in name for s in SKIP_UNIQUE_NAMES)


def slice_count(recipe_count, fraction):
    """Meaningful slice, always < full piece ingredient."""
    if recipe_count <= 0:
        return 0
    if recipe_count == 1:
        return 0
    raw = int(round(recipe_count * fraction))
    lo = max(1, int(recipe_count * 0.20 + 0.9999)) if recipe_count >= 5 else 1
    # 20% of 2-4 is <1, so floor is 1
    if recipe_count <= 4:
        lo = 1
    hi = max(1, int(recipe_count * 0.40))
    n = max(lo, min(raw if raw else 1, hi))
    if n >= recipe_count:
        n = recipe_count - 1
    return max(0, n)


def build_lang(zfile):
    items = set()
    for name in zfile.namelist():
        if name.endswith("en_US.lang") and (
            "/sum/" in name or "/legends/" in name or name.endswith("assets/sum/lang/en_US.lang")
            or name.endswith("assets/legends/lang/en_US.lang")
        ):
            text = zfile.read(name).decode("utf-8", "replace")
            for line in text.splitlines():
                line = line.strip()
                if (line.startswith("item.") or line.startswith("tile.")) and ".name=" in line:
                    key = line.split("=", 1)[0]
                    items.add(key)
                    prefix = "item." if key.startswith("item.") else "tile."
                    inner = key[len(prefix):]
                    if inner.endswith(".name"):
                        inner = inner[:-5]
                    items.add(inner)
                    items.add(inner.split(".")[0])
                    items.add("item.%s.name" % inner.split(".")[0])
                    items.add("tile.%s.name" % inner.split(".")[0])
    return items


def load_recipes():
    skipped = []
    by_name = {}
    with zipfile.ZipFile(JAR, "r") as z:
        lang = build_lang(z)
        classes = [n for n in z.namelist() if n.endswith(".class") and (
            n.startswith("com/tihyo/superheroes/characters/")
        )]
        for n in classes:
            if "$" in n:
                continue
            data = z.read(n)
            try:
                cp, rest = parse_constant_pool(data)
                methods = parse_methods(data, cp, rest)
            except Exception as e:
                skipped.append((n, "parse-fail:%s" % e))
                continue
            gname = extract_getname(methods, cp)
            raw_stacks = extract_getmaterials(methods, cp)
            raw_stacks = first_recipe_block(raw_stacks)
            mats = []
            hero_suit_ingredient = False
            for field, ints, desc in raw_stacks:
                cls, fname, fdesc = field
                count, dmg = stack_from_ctor(field, ints, desc)
                iid, why = field_to_id(cls, fname, lang)
                if why == "armor-field" or (fname and fname[:1].islower() and fname.endswith(("Chest", "Legs", "Boots", "Helmet"))):
                    hero_suit_ingredient = True
                    skipped.append((gname or n, fname, "hero-suit-ingredient", count, dmg))
                    continue
                if iid is None:
                    skipped.append((gname or n, fname, why, count, dmg))
                    continue
                if is_armor_id(iid):
                    # vanilla leather/iron armor is a mat we refuse to reward, not a suit-conversion
                    if iid.startswith("minecraft:"):
                        skipped.append((gname or n, fname, "vanilla-armor-mat", count, dmg))
                    else:
                        hero_suit_ingredient = True
                        skipped.append((gname or n, fname, "hero-suit-ingredient", count, dmg))
                    continue
                if iid in BANNED_IDS or any(b in iid.lower() for b in BANNED_SUBSTR):
                    skipped.append((gname or n, fname, "banned", count, dmg))
                    continue
                mats.append({
                    "id": iid,
                    "count": count,
                    "dmg": dmg,
                    "field": fname,
                    "class": cls,
                    "has_armor_sibling": False,
                })
            armor_in = hero_suit_ingredient
            reg = CLASS_REGNAME.get(n)
            if not reg:
                reg = NAME_ALIASES.get(gname, gname)
            if not reg:
                skipped.append((n, "no-regname", gname))
                continue
            by_name[reg] = {
                "class": n,
                "getName": gname,
                "mats": mats,
                "full_suit_recipe": armor_in,
                "raw_count": len(raw_stacks),
            }
    return by_name, skipped, lang


def first_recipe_block(raw_stacks):
    """Keep the default SAU list; drop alt-suit duplicates that start with a second gem."""
    gems = 0
    out = []
    for field, ints, desc in raw_stacks:
        fname = field[1] if field else ""
        if fname.endswith("Gem"):
            gems += 1
            if gems >= 2 and len(out) >= 3:
                break
        out.append((field, ints, desc))
    return out


def piece_cost_mats(entry):
    """If recipe includes previous armor (full conversion), divide by 4."""
    mats = entry["mats"]
    if entry.get("full_suit_recipe") and DIVIDE_WHEN_ARMOR_INGREDIENT:
        out = []
        for m in mats:
            c = max(1, int(round(m["count"] / 4.0))) if m["count"] >= 4 else m["count"]
            # after divide, still treat as one-piece cost
            nm = dict(m)
            nm["count"] = c
            nm["divided"] = True
            out.append(nm)
        return out
    return mats


def mats_to_rewards(piece_mats, fraction, lang_ok):
    rewards = []
    notes = []
    for m in piece_mats:
        iid, count, dmg = m["id"], m["count"], m["dmg"]
        if is_unique_key(iid) and count <= 2:
            notes.append("skip unique %s x%d" % (iid, count))
            continue
        if iid.startswith("legends:") and not lang_item_ok(iid, lang_ok) and iid.split(":")[1] not in (
            "fabric", "stainedLeather", "goldTitaniumAlloy",
        ):
            # subtypes use base key
            notes.append("skip no-lang %s" % iid)
            continue
        n = slice_count(count, fraction)
        if n <= 0:
            notes.append("skip slice0 %s x%d" % (iid, count))
            continue
        if iid in ("legends:bullet", "minecraft:arrow") and n > 12:
            n = 12
            notes.append("capped ammo %s at 12 (was slice of %d)" % (iid, count))
        rewards.append((iid, n, dmg, count, fraction, n / float(count) if count else 0))
    return rewards, notes


def lang_item_ok(iid, lang_ok):
    if iid.startswith("minecraft:") or iid.startswith("lootbags:") or iid.startswith("lucky:"):
        return True
    name = iid.split(":", 1)[1]
    base = name.split(".")[0]
    return (
        name in lang_ok
        or base in lang_ok
        or ("item.%s.name" % name) in lang_ok
        or ("item.%s.name" % base) in lang_ok
        or ("tile.%s.name" % name) in lang_ok
        or ("tile.%s.name" % base) in lang_ok
    )


def stack(id_, count, dmg):
    return {"id:8": id_, "Count:3": int(count), "Damage:2": int(dmg), "OreDict:8": ""}


def item_rewards(items):
    rew = OrderedDict()
    for i, (id_, count, dmg) in enumerate(items):
        rew["%d:10" % i] = stack(id_, count, dmg)
    return OrderedDict([
        ("0:10", OrderedDict([
            ("rewardID:8", "bq_standard:item"),
            ("index:3", 0),
            ("rewards:9", rew),
        ]))
    ])


def walk_items(obj, path=""):
    if isinstance(obj, dict):
        if "id:8" in obj:
            yield path, obj
        for k, v in obj.items():
            for p in walk_items(v, path + "/" + k):
                yield p
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            for p in walk_items(v, path + "[%d]" % i):
                yield p


def flatten_rewards(q):
    """Ensure reward stacks are flat id/Count/Damage/OreDict only."""
    rewards = q.get("rewards:9")
    if not isinstance(rewards, dict):
        return
    for rk, rv in list(rewards.items()):
        if not isinstance(rv, dict):
            continue
        inner = rv.get("rewards:9")
        if not isinstance(inner, dict):
            continue
        for ik, item in list(inner.items()):
            if not isinstance(item, dict) or "id:8" not in item:
                continue
            # unwrap nested betterquesting-style wrappers
            tag = item.get("tag:10")
            if isinstance(tag, dict) and "id:8" in tag:
                item = {
                    "id:8": tag.get("id:8", item["id:8"]),
                    "Count:3": tag.get("Count:3", item.get("Count:3", 1)),
                    "Damage:2": tag.get("Damage:2", item.get("Damage:2", 0)),
                    "OreDict:8": "",
                }
                inner[ik] = item
            keep = {
                "id:8": item["id:8"],
                "Count:3": item.get("Count:3", 1),
                "Damage:2": item.get("Damage:2", 0),
                "OreDict:8": item.get("OreDict:8", ""),
            }
            inner[ik] = keep


def char_from_quest(q):
    """Return (kind, char_name) from tasks / title."""
    name = q.get("properties:10", {}).get("betterquesting:10", {}).get("name:8", "")
    qid = q.get("questID:3")
    if qid == 300 or name == "Hall of Heroes":
        return "intro", None
    if qid == 301 or "Costume Closet" in name:
        return "closet", None
    tasks = q.get("tasks:9") or {}
    ids = []
    for t in tasks.values():
        req = (t or {}).get("requiredItems:9") or {}
        for it in req.values():
            if isinstance(it, dict) and "id:8" in it:
                ids.append(it["id:8"])
    chars = []
    for iid in ids:
        if iid.startswith("legends:") and "." in iid.split(":", 1)[1]:
            chars.append(iid.split(":", 1)[1].split(".", 1)[0])
    char = chars[0] if chars else None
    if name.endswith(": Full Set") or (char and name.endswith("Full Set")):
        return "full", char
    if name.startswith("Iron Man"):
        if "Underarmor" in name or "Mark 0" in name:
            return "piece", "ironman_mark0"
        if "Mark 1" in name:
            return "piece", "ironman_mark1"
        if "Mark 3" in name:
            return "full" if "complete" in q.get("properties:10", {}).get("betterquesting:10", {}).get("desc:8", "").lower() or "complete" in name.lower() or True else "piece", "ironman_mark3"
        if "Mark 7" in name:
            return "full", "ironman_mark7"
        if "Mark 21" in name:
            return "piece", "ironman_mark21"
    if char:
        # mark3/7 ask for multiple pieces
        piece_ids = [i for i in ids if is_armor_id(i)]
        if len(piece_ids) >= 3:
            return "full", char
        return "piece", char
    return "other", None


def bag_for(kind, char):
    if kind == "intro":
        return LB_COMMON
    if kind == "closet" or char in HARDEST_LEGENDARY:
        return LB_LEGEND
    if kind == "full":
        return LB_RARE if char in MAJOR_LINES else LB_UNCOMMON
    # piece
    return LB_UNCOMMON if char in MAJOR_LINES else LB_COMMON


def lucky_for(kind):
    if kind == "closet":
        return 8
    if kind == "full":
        return 4
    if kind == "intro":
        return 4
    return 2


def desc_needs_fix(desc):
    if not desc:
        return False
    low = desc.lower()
    promises = (
        "reward" in low and any(w in low for w in ("chestplate", "helmet", "leggings", "boots", "full suit as", "free suit")),
        "gives you the" in low and "suit" in low,
        "free" in low and any(w in low for w in ("chestplate", "helmet", "suit piece", "armor")),
    )
    return any(promises)


GENERIC_STARTER = [
    ("legends:fabric", 8, 0),
    ("legends:fabric", 4, 1),
    ("legends:fabric", 4, 6),
    ("legends:tech", 4, 0),
    ("legends:titaniumPlate", 2, 0),
]

CLOSET_CACHE = [
    ("legends:techHigh", 2, 0),
    ("legends:nanobot", 3, 0),
    ("legends:titaniumPlate", 2, 0),
    ("legends:vibranium", 1, 0),
    ("legends:kryptonianMetal", 1, 0),
    ("legends:wayneTech", 3, 0),
    ("legends:radioactiveFabric", 2, 0),
]


def main():
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = os.path.join(WORK, "DefaultQuests.pre-retune-%s.json" % stamp)
    os.makedirs(WORK, exist_ok=True)
    shutil.copy2(SRC, backup)
    print("backup", backup)

    recipes, skipped, lang = load_recipes()
    rec_path = os.path.join(WORK, "extracted_recipes.json")
    with open(rec_path, "w", encoding="utf-8") as f:
        json.dump({"recipes": recipes, "skipped": skipped}, f, indent=2, ensure_ascii=False)
    print("recipes", len(recipes), "skipped_rows", len(skipped), "->", rec_path)

    with open(SRC, "r", encoding="utf-8") as f:
        raw = f.read()
    if raw.startswith(u"\ufeff"):
        raise SystemExit("BOM present")
    data = json.loads(raw, object_pairs_hook=OrderedDict)

    settings = data["questSettings:10"]["betterquesting:10"]
    if settings.get("editMode:1") not in (0, 0.0):
        raise SystemExit("editMode was %s" % settings.get("editMode:1"))
    settings["editMode:1"] = 0

    qdb = data["questDatabase:9"]
    before = {}
    report = []
    rewritten = 0
    missing_recipe = []

    # Q32 check
    q32 = None
    for q in qdb.values():
        if q.get("questID:3") == 32:
            q32 = q
            break
    q32_armor = False
    if q32:
        for _, item in walk_items(q32.get("rewards:9", {})):
            if is_armor_id(item.get("id:8", "")):
                q32_armor = True
        print("Q32 armor-in-rewards", q32_armor)

    targets = []
    for key, q in qdb.items():
        qid = q.get("questID:3")
        if qid is None:
            continue
        if 300 <= qid <= 400:
            targets.append((key, q))

    # also any chapter-18 quests outside that range (shouldn't happen)
    ch18_ids = set()
    for line in data.get("questLines:9", {}).values():
        if line.get("lineID:3") == 18:
            for e in line.get("quests:9", {}).values():
                ch18_ids.add(e.get("id:3"))
    for key, q in qdb.items():
        qid = q.get("questID:3")
        if qid in ch18_ids and not (300 <= qid <= 400):
            targets.append((key, q))

    seen = set()
    unique_targets = []
    for key, q in targets:
        qid = q["questID:3"]
        if qid in seen:
            continue
        seen.add(qid)
        unique_targets.append((key, q))

    for key, q in sorted(unique_targets, key=lambda t: t[1]["questID:3"]):
        qid = q["questID:3"]
        pname = q["properties:10"]["betterquesting:10"]["name:8"]
        old = []
        for _, item in walk_items(q.get("rewards:9", {})):
            if "Count:3" in item or "id:8" in item:
                old.append((item.get("id:8"), item.get("Count:3"), item.get("Damage:2")))
        # de-dup walk (icon also has id)
        # only reward section
        old = []
        rew = q.get("rewards:9") or {}
        for rv in rew.values():
            inner = (rv or {}).get("rewards:9") or {}
            for item in inner.values():
                if isinstance(item, dict) and "id:8" in item:
                    old.append((item["id:8"], item.get("Count:3", 1), item.get("Damage:2", 0)))
        before[qid] = {"name": pname, "rewards": old}

        kind, char = char_from_quest(q)
        items = []
        frac_notes = []

        if kind == "intro":
            items = list(GENERIC_STARTER)
            items.append(("legends:DCLogo", 1, 0))
            items.append(("legends:MarvelLogo", 1, 0))
            items.append(("legends:superDex", 1, 0))
            items.append(("lootbags:lootbag", 1, LB_COMMON))
            items.append(("lucky:lucky_block", lucky_for("intro"), 0))
            frac_notes.append("intro generic starter (not a piece recipe)")
        elif kind == "closet":
            items = list(CLOSET_CACHE)
            items.append(("lootbags:lootbag", 1, LB_LEGEND))
            items.append(("lucky:lucky_block", lucky_for("closet"), 0))
            frac_notes.append("closet mixed cache; no armor")
        elif char and char in recipes:
            entry = recipes[char]
            piece_mats = piece_cost_mats(entry)
            frac = FULLSET_FRACTION if kind == "full" else PIECE_FRACTION
            sliced, notes = mats_to_rewards(piece_mats, frac, lang)
            frac_notes.extend(notes)
            if entry.get("full_suit_recipe"):
                frac_notes.append("recipe had armor ingredients; counts/4 then *%.0f%%" % (frac * 100))
            else:
                frac_notes.append("per-piece getMaterials *%.0f%%" % (frac * 100))
            for iid, n, dmg, rec, fr, actual in sliced:
                items.append((iid, n, dmg))
            if kind == "full":
                for g in LINE_GADGETS.get(char, []):
                    if lang_item_ok(g[0], lang) and g[0] not in BANNED_IDS:
                        items.append(g)
                        frac_notes.append("gadget %s" % g[0])
            items.append(("lootbags:lootbag", 1, bag_for(kind, char)))
            items.append(("lucky:lucky_block", lucky_for(kind), 0))
            if not any(i[0] not in ("lootbags:lootbag", "lucky:lucky_block") for i in items):
                # unique-only recipes (e.g. symbiote) — shared family mats, never a suit piece
                items = [
                    ("legends:radioactiveFabric", 3, 0),
                    ("legends:fabric", 4, 10),
                    ("lootbags:lootbag", 1, bag_for(kind, char)),
                    ("lucky:lucky_block", lucky_for(kind), 0),
                ]
                frac_notes.append("fallback family mats; recipe was unique-only")
        else:
            missing_recipe.append((qid, pname, char, kind))
            # safe fallback: generic hero mats, no armor
            items = [
                ("legends:fabric", 6, 0),
                ("legends:tech", 2, 0),
                ("lootbags:lootbag", 1, bag_for(kind, char)),
                ("lucky:lucky_block", lucky_for(kind), 0),
            ]
            frac_notes.append("FALLBACK no recipe for %s" % char)

        # drop banned / armor if any slipped in
        cleaned = []
        seen_stack = set()
        for iid, c, d in items:
            if is_armor_id(iid) or iid in BANNED_IDS or any(b in iid.lower() for b in BANNED_SUBSTR):
                frac_notes.append("stripped %s" % iid)
                continue
            if iid.startswith("legends:") and not lang_item_ok(iid, lang):
                # allow fabric / stainedLeather / goldTitaniumAlloy always (subtype lang)
                base = iid.split(":")[1]
                if base not in lang and ("item.%s.name" % base) not in lang:
                    frac_notes.append("stripped no-lang %s" % iid)
                    continue
            key_s = (iid, d)
            # merge same id+dmg
            found = False
            for i, (a, b, e) in enumerate(cleaned):
                if a == iid and e == d:
                    cleaned[i] = (a, b + c, e)
                    found = True
                    break
            if not found:
                cleaned.append((iid, c, d))
        items = cleaned

        q["rewards:9"] = item_rewards(items)
        flatten_rewards(q)

        desc = q["properties:10"]["betterquesting:10"].get("desc:8", "")
        if desc_needs_fix(desc):
            q["properties:10"]["betterquesting:10"]["desc:8"] = (
                desc + "\n\n§7Rewards are craft materials and extras — not another suit piece."
            )
            frac_notes.append("desc footnote")

        rewritten += 1
        report.append({
            "id": qid,
            "name": pname,
            "kind": kind,
            "char": char,
            "before": old,
            "after": items,
            "notes": frac_notes,
        })

    # Q32: only if it currently gives a suit piece
    if q32 and q32_armor:
        q32["rewards:9"] = item_rewards([
            ("minecraft:emerald", 8, 0),
            ("legends:fabric", 6, 0),
            ("legends:tech", 2, 0),
        ])
        flatten_rewards(q32)
        rewritten += 1
        report.append({"id": 32, "name": "Legends: Become a Hero", "kind": "q32-fix",
                       "notes": ["removed free suit piece"]})

    # validate
    allowed_extra = {
        "lootbags:lootbag", "lucky:lucky_block",
        "minecraft:emerald", "minecraft:diamond", "minecraft:iron_ingot",
        "minecraft:gold_ingot", "minecraft:leather", "minecraft:string",
        "minecraft:stained_glass_pane", "minecraft:glass_pane", "minecraft:wool",
        "minecraft:dye", "minecraft:glass",
    }
    bad = []
    armor_left = []
    for row in report:
        qid = row["id"]
        q = None
        for qq in qdb.values():
            if qq.get("questID:3") == qid:
                q = qq
                break
        if not q:
            continue
        rew = q.get("rewards:9") or {}
        for rv in rew.values():
            inner = (rv or {}).get("rewards:9") or {}
            for item in inner.values():
                iid = item.get("id:8", "")
                if is_armor_id(iid):
                    armor_left.append((qid, iid))
                if any(b in iid.lower() for b in BANNED_SUBSTR):
                    bad.append((qid, "banned", iid))
                if iid.startswith("legends:") and not lang_item_ok(iid, lang) and iid.split(":")[1] not in lang:
                    bad.append((qid, "lang", iid))

    # chapter 18 reward armor sweep
    ch18_armor = []
    for qid in ch18_ids:
        for qq in qdb.values():
            if qq.get("questID:3") == qid:
                rew = qq.get("rewards:9") or {}
                for rv in rew.values():
                    inner = (rv or {}).get("rewards:9") or {}
                    for item in inner.values():
                        if is_armor_id(item.get("id:8", "")):
                            ch18_armor.append((qid, item["id:8"]))

    if armor_left or ch18_armor:
        raise SystemExit("armor rewards remain: %s %s" % (armor_left, ch18_armor))
    if bad:
        print("WARN bad ids", bad[:20])

    tmp = SRC + ".tmp-retune"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    with open(tmp, "rb") as f:
        head = f.read(4)
    if head.startswith(b"\xef\xbb\xbf"):
        raise SystemExit("wrote BOM")
    with open(tmp, "r", encoding="utf-8") as f:
        json.load(f)
    os.replace(tmp, SRC)

    rep_path = os.path.join(WORK, "retune_report.json")
    with open(rep_path, "w", encoding="utf-8") as f:
        json.dump({
            "rewritten": rewritten,
            "missing_recipe": missing_recipe,
            "q32_armor": q32_armor,
            "chapter18_armor_rewards": ch18_armor,
            "fraction": {"piece": PIECE_FRACTION, "full": FULLSET_FRACTION},
            "report": report,
            "skipped_extract": skipped,
        }, f, indent=2, ensure_ascii=False)

    print("wrote", SRC)
    print("rewritten", rewritten)
    print("missing_recipe", missing_recipe)
    print("q32_changed", bool(q32 and q32_armor))
    print("ch18_armor", ch18_armor)
    print("report", rep_path)


if __name__ == "__main__":
    main()
