#!/usr/bin/env python3
"""Build site/lucky/data/lucky.json from the pack's Lucky Block config.

Run with `python3 -I tools/site/build_lucky.py` from anywhere.

Reads pack/config/lucky/LuckyBlockProperties.txt (Lucky Block 5.1.0 format) and
site/items/data/items.json (for icons), and writes:

  - the crafting luck modifiers (>craftingitems) and the block's recipe/spawn data,
  - every drop of the >drops table as {kind, label, id, count, luck, chance,
    nbtSummary, icon, reveal, ...}, with the raw line kept for debugging.

Luck weighting (recovered from LuckyBlocks.jar, mod/lucky/util/ChooseLuckyDrop.class,
method chooseDrop(LuckyDropBase[], int luck)):

  L     = block luck, clamped to -100..100 by LuckyCrafting when the block is crafted
  b     = 1 / (1 - 0.0077 * |L|)
  minL  = min(0, min drop luck), maxL = max(0, max drop luck)
  weight(drop) = chance * 100 * b ^ e
  e     = (drop.luck - minL + 1)      when L >= 0
          (maxL - drop.luck + 1)      when L < 0

The constant factors (100, the -minL shift and the maxL shift) cancel when the
weights are normalised, so the probability of a drop is
    P = chance * b^e / sum(chance_j * b^e_j).
A drop with no @luck suffix has luck 2 (the LuckyDropBase constructor default), and
a drop with no @chance suffix has chance 1.0.
"""

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
CONFIG = os.path.join(ROOT, "pack", "config", "lucky", "LuckyBlockProperties.txt")
ITEMS = os.path.join(ROOT, "site", "items", "data", "items.json")
OUT_DIR = os.path.join(ROOT, "site", "lucky", "data")
OUT = os.path.join(OUT_DIR, "lucky.json")

DEFAULT_LUCK = 2
DEFAULT_CHANCE = 1.0

# Vanilla 1.7.10 potion ids, for effect drops.
POTIONS = {1: "Speed", 2: "Slowness", 3: "Haste", 4: "Mining Fatigue", 5: "Strength",
           6: "Instant Health", 7: "Instant Damage", 8: "Jump Boost", 9: "Nausea",
           10: "Regeneration", 11: "Resistance", 12: "Fire Resistance", 13: "Water Breathing",
           14: "Invisibility", 15: "Blindness", 16: "Night Vision", 17: "Hunger", 18: "Weakness",
           19: "Poison", 20: "Wither", 21: "Health Boost", 22: "Absorption", 23: "Saturation"}

# Vanilla 1.7.10 enchantment ids that appear in the config.
ENCHANTS = {0: "Protection", 1: "Fire Protection", 2: "Feather Falling", 3: "Blast Protection",
            4: "Projectile Protection", 5: "Respiration", 6: "Aqua Affinity", 7: "Thorns",
            16: "Sharpness", 17: "Smite", 18: "Bane of Arthropods", 19: "Knockback",
            20: "Fire Aspect", 21: "Looting", 32: "Efficiency", 33: "Silk Touch", 34: "Unbreaking",
            35: "Fortune", 48: "Power", 49: "Punch", 50: "Flame", 51: "Infinity"}

# Legacy numeric ids (1.7.10 item/block numbers) that the config uses as bare ids.
LEGACY = {
    97: ("monster_egg", 0), 147: ("light_weighted_pressure_plate", 0), 349: ("fish", 0),
    382: ("speckled_melon", 0), 384: ("experience_bottle", 0),
    2256: ("record_13", 0), 2257: ("record_cat", 0), 2258: ("record_blocks", 0),
    2259: ("record_chirp", 0), 2260: ("record_far", 0), 2261: ("record_mall", 0),
    2262: ("record_mellohi", 0), 2263: ("record_stal", 0), 2264: ("record_strad", 0),
    2265: ("record_ward", 0), 2266: ("record_11", 0), 2267: ("record_wait", 0),
}
# Registry renames between 1.7.10 spellings used in the config and items.json.
RENAMED = {"ink_sack": ("dye", 0), "slimeball": ("slime_ball", None)}

KNOWN_TYPES = {"item", "block", "falling_block", "falling", "entity", "structure", "effect",
               "message", "difficulty", "time", "command", "particle", "lightning", "quartz", "potion"}

MOB_CATEGORY = [
    (re.compile(r"^(zombie|pigzombie|husk)", re.I), "zombie"),
    (re.compile(r"^creeper", re.I), "creeper"),
    (re.compile(r"^(skeleton|witherskeleton|stray)", re.I), "skeleton"),
    (re.compile(r"^(cavespider|spider)$", re.I), "spider"),
    (re.compile(r"^villager", re.I), "villager"),
]


# ----------------------------------------------------------------- parsing helpers

def split_top(s, sep):
    """Split s on sep where it is not inside (), [], {} or double quotes."""
    parts, buf, depth, quoted = [], [], 0, False
    for ch in s:
        if ch == '"':
            quoted = not quoted
        elif not quoted:
            if ch in "([{":
                depth += 1
            elif ch in ")]}":
                depth -= 1
            elif ch == sep and depth == 0:
                parts.append("".join(buf))
                buf = []
                continue
        buf.append(ch)
    parts.append("".join(buf))
    return parts


def find_close(s, start):
    """Index of the bracket that closes s[start], honouring quotes."""
    opener = s[start]
    closer = {"(": ")", "[": "]", "{": "}"}[opener]
    depth, quoted = 0, False
    for i in range(start, len(s)):
        ch = s[i]
        if ch == '"':
            quoted = not quoted
        elif not quoted:
            if ch == opener:
                depth += 1
            elif ch == closer:
                depth -= 1
                if depth == 0:
                    return i
    return -1


def parse_nbt(s):
    """Parse an NBT-ish value: (k=v,...) compounds, [..] lists, "strings", raw tokens."""
    value, _ = _nbt_value(s, 0)
    return value


def _nbt_value(s, i):
    if i < len(s) and s[i] == '"':
        j = s.index('"', i + 1) if '"' in s[i + 1:] else len(s) - 1
        return s[i + 1:j], j + 1
    if i < len(s) and s[i] == "(":
        out = {}
        i += 1
        while i < len(s) and s[i] != ")":
            start = i
            j = i
            while j < len(s) and s[j] not in "=,)":
                j += 1
            key = s[i:j].strip()
            if j < len(s) and s[j] == "=":
                val, i = _nbt_value(s, j + 1)
                out[key] = val
            else:
                i = j
            if i < len(s) and s[i] == ",":
                i += 1
            if i == start:  # no progress on malformed input
                i += 1
        return out, i + 1
    if i < len(s) and s[i] == "[":
        out = []
        i += 1
        while i < len(s) and s[i] != "]":
            start = i
            val, i = _nbt_value(s, i)
            out.append(val)
            if i < len(s) and s[i] == ",":
                i += 1
            if i == start:  # a stray ')' inside a list: skip it
                i += 1
        return out, i + 1
    j = i
    while j < len(s) and s[j] not in ",)]":
        j += 1
    return s[i:j].strip(), j


def to_number(v, default=None):
    try:
        f = float(str(v).rstrip("fFdDlLbBsS"))
        return int(f) if f == int(f) and "." not in str(v) else f
    except (TypeError, ValueError):
        return default


SUFFIX = re.compile(r"(?:@|(?<=\)))(luck|chance)=(-?\d+(?:\.\d+)?)\s*$")


def strip_suffixes(line):
    """Pull trailing @luck= / @chance= off a drop line, returning (body, luck, chance)."""
    luck, chance = DEFAULT_LUCK, DEFAULT_CHANCE
    body = line.strip().rstrip(";").rstrip()
    while True:
        m = SUFFIX.search(body)
        if not m:
            break
        if m.group(1) == "luck":
            luck = int(float(m.group(2)))
        else:
            chance = float(m.group(2))
        body = body[:m.start()].rstrip()
    return body, luck, chance


def clean_text(s):
    """Chat-style text from the config: #playerName, colour codes, #bPosY and friends."""
    s = s.replace("#playerName", "you").replace("#pPosX", "here").replace("#pPosY", "here")
    s = s.replace("#pPosZ", "here").replace("#bPosX", "here").replace("#bPosY", "here")
    s = s.replace("#bPosZ", "here")
    s = re.sub(r"#[0-9a-fklmnor]", "", s)
    return re.sub(r"\s+", " ", s).strip()


def pretty(name):
    name = name.split(":")[-1]
    name = name.replace("_", " ").strip()
    name = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", name)
    return name[:1].upper() + name[1:] if name else name


def enchant_summary(ench):
    if isinstance(ench, str):
        if ench.startswith("#"):
            family = re.sub(r"^#luckyg?|Enchantments$", "", ench)
            return "enchanted (%s set)" % (pretty(family).lower() or "random")
        return ""
    if not isinstance(ench, list):
        return ""
    bits = []
    for e in ench:
        if isinstance(e, dict):
            eid = to_number(e.get("id"), -1)
            lvl = e.get("lvl", "?")
            bits.append("%s %s" % (ENCHANTS.get(eid, "enchant #%s" % eid), lvl))
    return ", ".join(bits)


def nbt_summary(nbt):
    """One-line summary of a drop's NBT (name, lore, enchantments, custom properties)."""
    if not isinstance(nbt, dict):
        return ""
    bits = []
    tag = nbt.get("tag") if isinstance(nbt.get("tag"), dict) else nbt
    name = None
    if isinstance(tag.get("display"), dict):
        name = tag["display"].get("Name")
    name = name or nbt.get("CustomName")
    if name:
        bits.append('"%s"' % clean_text(str(name)))
    ench = enchant_summary(tag.get("ench"))
    if ench:
        bits.append(ench)
    if tag.get("Unbreakable") in (True, "true"):
        bits.append("unbreakable")
    if isinstance(tag.get("AttributeModifiers"), list):
        for am in tag["AttributeModifiers"]:
            if isinstance(am, dict):
                bits.append("%s %s" % (am.get("AttributeName", "attribute"), am.get("Amount", "")))
    if isinstance(tag.get("display"), dict) and isinstance(tag["display"].get("Lore"), list):
        bits.extend(clean_text(str(x)) for x in tag["display"]["Lore"][:1])
    if "CustomPotionEffects" in nbt:
        bits.append("custom potion effects")
    return "; ".join(b for b in bits if b)


# ----------------------------------------------------------------- items index

class ItemIndex:
    def __init__(self, path):
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        self.by_key = {}
        self.by_base = {}
        self.cell = data.get("cell", 32)
        self.side = data.get("side", 64)
        for rec in data["items"]:
            k = rec.get("k", "")
            self.by_key[k] = rec
            base = k.split("@")[0]
            self.by_base.setdefault(base, rec)

    def icon_for(self, ns_name, damage):
        """Return ({s, c, r}, how) for an item id, or (None, reason)."""
        if ":" not in ns_name:
            ns_name = "minecraft:" + ns_name
        keys = ["%s@%s" % (ns_name, damage)] if damage is not None else []
        keys.append("%s@0" % ns_name)
        for k in keys:
            rec = self.by_key.get(k)
            if rec is not None:
                return self._icon(rec, "exact" if k.endswith("@%s" % damage) or damage is None else "damage 0")
        rec = self.by_base.get(ns_name)
        if rec is not None:
            return self._icon(rec, "other damage value")
        return None, "not in items.json"

    def _icon(self, rec, how):
        if rec.get("b"):
            return None, "blank record"
        i = rec.get("i")
        if i is None:
            return None, "no icon index"
        per = self.side * self.side
        return {"s": i // per, "c": (i % per) % self.side, "r": (i % per) // self.side}, how


# ----------------------------------------------------------------- drop parsing

def parse_member(text):
    """One drop, e.g. type=entity,ID=Item,NBTTag=(...). Returns a dict of raw fields."""
    fields = {}
    positional = []
    for tok in split_top(text, ","):
        tok = tok.strip()
        if not tok:
            continue
        eq = tok.find("=")
        if eq > 0 and re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", tok[:eq]):
            fields[tok[:eq]] = tok[eq + 1:]
        else:
            positional.append(tok)
    if positional:
        # bare "golden_apple,1" form: id then damage
        fields.setdefault("ID", positional[0])
        if len(positional) > 1:
            fields.setdefault("damage", positional[1])
    return fields


def unquote(v):
    if v is not None and len(v) >= 2 and v[0] == '"' and v[-1] == '"':
        return v[1:-1]
    return v


def build_drop(index, fields, luck, chance, raw):
    """Turn a parsed member into the record the page uses."""
    kind = fields.get("type", "item")
    ident = unquote(fields.get("ID", ""))
    if kind not in KNOWN_TYPES:
        # A typo such as type=quartz_block: read it as a block of that name.
        if not ident:
            ident = kind
        kind = "block"
    count_raw = fields.get("amount", fields.get("Count"))
    damage_raw = fields.get("damage")
    nbt = parse_nbt(fields["NBTTag"]) if "NBTTag" in fields else None
    rec = {"kind": kind, "label": "", "id": ident, "count": 1, "luck": luck,
           "chance": round(chance, 4), "nbtSummary": "", "icon": None,
           "reveal": "unknown", "raw": raw}
    if count_raw is not None:
        rec["count"] = to_number(count_raw, count_raw)

    damage = to_number(damage_raw) if damage_raw is not None and not str(damage_raw).startswith("#") else None

    if ident.startswith("#") and kind in ("item", "block"):
        rec.update(kind="item", reveal="item", label="Random item", icon=None, iconNote="macro id")
        rec["id"] = ident
        return rec
    ident_raw = ident
    if ident.isdigit() and kind in ("item", "block", "falling_block", "falling"):
        legacy = LEGACY.get(int(ident))
        if legacy:
            ident, legacy_dmg = legacy
            damage = legacy_dmg if damage is None else damage
            rec["legacyId"] = int(ident_raw)
        elif int(ident) == 0:
            rec.update(kind="block", reveal="nothing", label="Air", icon=None, iconNote="air")
            return rec
    if ident == "air" and kind in ("item", "block"):
        rec.update(kind="block", reveal="nothing", label="Air", icon=None, iconNote="air")
        return rec
    if ident in RENAMED:
        ident, renamed_dmg = RENAMED[ident]
        damage = renamed_dmg if damage is None else damage

    # Entity wrapping an item: ID=Item with Item=(id=...) inside the NBT.
    if kind == "entity" and ident == "Item" and isinstance(nbt, dict) and isinstance(nbt.get("Item"), dict):
        inner = nbt["Item"]
        item_id = inner.get("id", "stone")
        tag = inner.get("tag") if isinstance(inner.get("tag"), dict) else {}
        display = tag.get("display") if isinstance(tag.get("display"), dict) else {}
        custom = unquote(nbt.get("CustomName")) or display.get("Name")
        rec.update(kind="item", id=item_id, reveal="item", viaEntity=True)
        rec["label"] = clean_text(str(custom)) if custom else pretty(item_id)
        rec["count"] = to_number(inner.get("Count", 1), 1)
        rec["nbtSummary"] = nbt_summary({"tag": tag, "CustomName": custom})
        rec["icon"], rec["iconNote"] = index.icon_for(item_id, to_number(inner.get("Damage"), None))
        return rec

    if kind in ("item", "block", "falling_block", "potion", "tile", "entity") or kind == "":
        pass

    if kind == "entity":
        rec["mob"] = "beast"
        for pat, cat in MOB_CATEGORY:
            if pat.search(ident):
                rec["mob"] = cat
                break
        rec["label"] = pretty(ident)
        rec["reveal"] = "entity"
        if ident in ("launched_tnt",):
            rec["reveal"] = "explosion"
        elif "lightning" in ident.lower():
            rec["reveal"] = "lightning"
        elif ident in ("launched_expbottle", "XPOrb"):
            rec["reveal"] = "particle"
        elif ident == "Item":
            rec["reveal"] = "item"
        if isinstance(nbt, dict):
            rec["nbtSummary"] = nbt_summary(nbt)
        return rec

    if kind == "falling_block" or kind == "falling":
        rec.update(kind="falling", reveal="falling")
        base_id, dmg = split_damage(ident, damage)
        rec["label"] = "Falling " + pretty(base_id).lower()
        rec["id"] = base_id
        rec["icon"], rec["iconNote"] = index.icon_for(base_id, dmg)
        return rec

    if kind == "block":
        base_id, dmg = split_damage(ident, damage)
        rec["id"] = base_id
        rec["label"] = pretty(base_id)
        if base_id in ("tnt", "lit_tnt"):
            rec["reveal"] = "explosion"
        elif base_id in ("lava", "flowing_lava", "fire"):
            rec["reveal"] = "lava"
        else:
            rec["reveal"] = "blocks"
        rec["icon"], rec["iconNote"] = index.icon_for(base_id, dmg)
        return rec

    if kind == "structure":
        rec["reveal"] = "structure"
        rec["label"] = pretty(ident)
        rec["data"] = {"structure": ident}
        return rec

    if kind == "effect":
        if ident.startswith("#random"):
            rec.update(reveal="effect", label="Random effect", data={"name": "Random effect", "duration": to_number(fields.get("duration", "0"), 0), "amplifier": 0})
            return rec
        eid = to_number(ident, None)
        dur = to_number(fields.get("duration", "0"), 0)
        dmg = to_number(fields.get("damage", "0"), 0)
        rec["reveal"] = "effect"
        if isinstance(eid, int) and eid in POTIONS:
            name = POTIONS[eid]
        else:
            name = "effect %s" % ident
        rec["label"] = name
        rec["data"] = {"name": name, "duration": dur, "amplifier": dmg}
        return rec

    if kind == "message":
        text = clean_text(ident)
        rec["label"] = "Chat message"
        rec["id"] = text
        rec["reveal"] = "message"
        rec["data"] = {"text": text}
        return rec

    if kind == "difficulty":
        rec["reveal"] = "difficulty"
        rec["label"] = "Difficulty: " + pretty(ident).lower()
        rec["data"] = {"difficulty": ident}
        return rec

    if kind == "time":
        rec["reveal"] = "time"
        rec["label"] = "Time: " + ident
        rec["data"] = {"time": ident}
        return rec

    if kind == "command":
        rec["reveal"] = "command"
        rec["label"] = "Command"
        rec["data"] = {"command": ident}
        return rec

    if kind == "particle":
        rec["reveal"] = "particle"
        rec["label"] = "Particle " + ident
        rec["data"] = {"particle": ident}
        return rec

    if kind == "lightning":
        rec["reveal"] = "lightning"
        rec["label"] = "Lightning"
        return rec

    if kind == "quartz":
        rec["reveal"] = "unknown"
        rec["label"] = "quartz (stray)"
        return rec

    # Default: an item (type absent, or type=item).
    base_id, dmg = split_damage(ident, damage)
    rec["id"] = base_id
    rec["kind"] = "item"
    rec["reveal"] = "item"
    rec["label"] = pretty(base_id)
    if isinstance(nbt, dict):
        rec["nbtSummary"] = nbt_summary(nbt)
        if isinstance(nbt.get("display"), dict) and nbt["display"].get("Name"):
            rec["label"] = clean_text(str(nbt["display"]["Name"]))
    rec["icon"], rec["iconNote"] = index.icon_for(base_id, dmg)
    return rec


def split_damage(ident, damage):
    """'golden_apple,1' -> ('golden_apple', 1); 'diamond_sword' -> (..., damage)."""
    if "," in ident:
        base, d = ident.split(",", 1)
        return base, to_number(d, damage)
    return ident, damage


class Malformed(Exception):
    pass


def parse_group(body):
    """group(...), group:1(...), group:#random-1-2(...) and group=(...).

    Returns (pick, inner) or None when the body is not a group. Raises Malformed
    when the group's parenthesis never closes (the config has a few of those).
    """
    if not body.startswith("group"):
        return None
    open_at = body.find("(")
    if open_at < 0:
        raise Malformed("group without '('")
    head = body[len("group"):open_at].strip(":=").strip() or None
    close = find_close(body, open_at)
    if close < 0:
        raise Malformed("group '(' never closes")
    trailing = body[close + 1:].strip()
    if trailing and trailing.strip(")") != "":
        raise Malformed("text after group close: %r" % trailing[:40])
    return head, body[open_at + 1:close]


def expand_members(inner, index, depth=0):
    """Members of a group, with nested groups flattened into the same list."""
    out = []
    for mtxt in split_top(inner, ";"):
        mtxt = mtxt.strip()
        if not mtxt:
            continue
        mbody, mluck, mchance = strip_suffixes(mtxt)
        nested = parse_group(mbody) if mbody.startswith("group") else None
        if nested is not None and depth < 4:
            out.extend(expand_members(nested[1], index, depth + 1))
            continue
        fields = parse_member(mbody)
        out.append(build_drop(index, fields, mluck, mchance, mtxt))
    return out


def parse_drops(lines, index, skipped):
    drops = []
    for raw in lines:
        body, luck, chance = strip_suffixes(raw)
        if not body:
            continue
        try:
            grp = parse_group(body)
            bare = grp is None and len(split_top(body, ";")) > 1
            if bare:
                # Several drops joined by ';' with no group(...) wrapper (one line in the config).
                grp = (None, body)
            if grp is not None:
                pick, inner = grp
                members = expand_members(inner, index)
                rec = {"kind": "group", "label": "", "id": "", "count": len(members), "luck": luck,
                       "chance": round(chance, 4), "nbtSummary": "", "icon": None,
                       "reveal": "group", "raw": raw, "pick": pick, "bareSemicolon": bare,
                       "members": [{k: m[k] for k in ("kind", "label", "id", "count", "icon", "reveal", "mob", "data")
                                    if k in m} for m in members]}
                counts = {}
                for m in members:
                    if m["label"]:
                        counts[m["label"]] = counts.get(m["label"], 0) + 1
                names = [n if c == 1 else "%s x%d" % (n, c) for n, c in counts.items()]
                rec["label"] = "Set of %d: %s" % (len(members), ", ".join(names[:4]) + (" and more" if len(names) > 4 else ""))
                drops.append(rec)
                continue
            fields = parse_member(body)
            drops.append(build_drop(index, fields, luck, chance, raw))
        except Malformed as err:
            skipped.append({"reason": str(err), "raw": raw})
    for i, d in enumerate(drops):
        d["index"] = i
    return drops


def parse_config(text):
    section = None
    props, crafting, drop_lines = {}, [], []
    for line in text.splitlines():
        s = line.rstrip()
        if s.startswith(">"):
            section = s[1:].strip()
            continue
        if section == "drops":
            if not s.strip() or s.startswith("/"):
                continue
            drop_lines.append(s.strip())
        elif section == "properties":
            if "=" in s:
                k, v = s.split("=", 1)
                props[k.strip()] = v.strip()
        elif section == "craftingitems":
            if "=" not in s or s.startswith("/"):
                continue
            name, lvl = s.rsplit("=", 1)
            name, dmg = (name.split(",", 1) + [None])[:2] if "," in name else (name, None)
            crafting.append({"id": ("" if ":" in name else "minecraft:") + name.strip(),
                             "damage": to_number(dmg) if dmg is not None else None,
                             "level": to_number(lvl, 0), "label": pretty(name.strip())})
    return props, crafting, drop_lines


# ----------------------------------------------------------------- main

def main():
    with open(CONFIG, encoding="utf-8") as fh:
        text = fh.read()
    props, crafting, drop_lines = parse_config(text)
    index = ItemIndex(ITEMS)
    skipped = []
    drops = parse_drops(drop_lines, index, skipped)

    kinds = {}
    for d in drops:
        kinds[d["kind"]] = kinds.get(d["kind"], 0) + 1
    reveals = {}
    for d in drops:
        reveals[d["reveal"]] = reveals.get(d["reveal"], 0) + 1

    # Flat list of icon-able entries, including members of groups (for the report).
    icon_total = icon_hit = 0
    unresolved = []
    for d in drops:
        if d["kind"] in ("item", "block", "falling"):
            icon_total += 1
            if d["icon"]:
                icon_hit += 1
            else:
                unresolved.append("%s: %s (%s)" % (d["kind"], d["id"], d.get("iconNote", "")))
        for m in d.get("members", []):
            if m["kind"] in ("item", "block", "falling"):
                icon_total += 1
                if m["icon"]:
                    icon_hit += 1
                else:
                    unresolved.append("set member %s: %s" % (m["kind"], m["label"]))

    doc = {
        "version": "5.1.0",
        "source": "pack/config/lucky/LuckyBlockProperties.txt",
        "spawnrate": to_number(props.get("spawnrate"), 0),
        "structureChance": to_number(props.get("structureChance"), 0),
        "recipe": props.get("recipe", ""),
        "luck": {
            "min": -100,
            "max": 100,
            "defaultDropLuck": DEFAULT_LUCK,
            "defaultDropChance": DEFAULT_CHANCE,
            "baseFactor": 0.0077,
        },
        "craftingItems": crafting,
        "counts": {"drops": len(drops), "byKind": kinds, "byReveal": reveals,
                   "iconTotal": icon_total, "iconResolved": icon_hit},
        "drops": drops,
        "skipped": skipped,
    }
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, separators=(",", ":"))
        fh.write("\n")

    print("drops: %d" % len(drops))
    print("by kind: " + ", ".join("%s %d" % kv for kv in sorted(kinds.items(), key=lambda kv: -kv[1])))
    print("by reveal: " + ", ".join("%s %d" % kv for kv in sorted(reveals.items(), key=lambda kv: -kv[1])))
    print("crafting items: %d" % len(crafting))
    print("skipped (malformed config lines): %d" % len(skipped))
    for sk in skipped:
        print("  skipped: %s | %s" % (sk["reason"], sk["raw"][:90]))
    print("icons: %d of %d item/block/falling entries resolved (set members included)" % (icon_hit, icon_total))
    for u in unresolved:
        print("  unresolved: " + u)
    print("wrote " + os.path.relpath(OUT, ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
