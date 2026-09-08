# -*- coding: utf-8 -*-
"""Retarget Hall of Heroes FULL-SET rewards to another line's piece-cost mats."""
from __future__ import print_function

import json
import os
import shutil
import sys
from collections import OrderedDict
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import retune_hero_rewards as R

SRC = R.SRC
WORK = R.WORK
PIECE_FRACTION = R.PIECE_FRACTION  # ~30% of one other piece

# from-set -> thematic other line (nudge, not a finished piece)
RETARGET = {
    "ironman_mark3": "ironman_mark7",
    "ironman_mark7": "warmachine_mark1",
    "superman": "supergirl",
    "supergirl": "generalzod",
    "generalzod": "superman",
    "batman": "nightwing",
    "nightwing": "redhood",
    "redhood": "redrobin",
    "redrobin": "nightwing",
    "robin_grayson": "nightwing",
    "robin_todd": "redhood",
    "robin_drake": "redrobin",
    "robin_brown": "redrobin",
    "robin_wayne": "batman",
    "joker": "scarecrow",
    "scarecrow": "joker",
    "flash": "kidflash",
    "kidflash": "flash_west",
    "flash_west": "flash",
    "flash_garrick": "flash",
    "reverseflash": "zoom",
    "zoom": "reverseflash",
    "wonderwoman": "martianmanhunter",
    "shazam": "blackadam",
    "blackadam": "shazam",
    "martianmanhunter": "superman",
    "greenarrow": "blackcanary",
    "blackcanary": "greenarrow",
    "captaincold": "heatwave",
    "heatwave": "captaincold",
    "turtle": "captaincold",
    "captainamerica": "blackpanther",
    "thor": "captainamerica",
    "hulk": "redhulk",
    "redhulk": "abomination",
    "abomination": "hulk",
    "antman": "wasp",
    "wasp": "antman",
    "blackpanther": "captainamerica",
    "spiderman": "spiderman2099",
    "spiderman2099": "ironspider",
    "symbiotespiderman": "venom",
    "ironspider": "warmachine_mark1",
    "vision": "ironspider",
    "wolverine": "deadpool",
    "deadpool": "wolverine",
    "daredevil": "spiderman",
    "venom": "symbiotespiderman",
    "warmachine_mark1": "ironman_mark21",
}

# If the mapped line is unique-key-only, hop to a sibling with real stacks.
DONOR_FALLBACK = {
    "symbiotespiderman": "spiderman",
    "venom": "spiderman",
}

FAMILY_FALLBACK = {
    "kryptonian": [
        ("legends:fabric", 3, 1),
        ("legends:fabric", 4, 6),
        ("legends:stainedLeather", 1, 1),
    ],
    "bat": [("legends:wayneTech", 2, 0), ("legends:fabric", 4, 15)],
    "speed": [("legends:lightningIngot", 2, 0), ("legends:fabric", 4, 14)],
    "stark": [("legends:titaniumPlate", 2, 0), ("legends:starkTech", 3, 0)],
    "spider": [("legends:radioactiveFabric", 2, 0), ("legends:fabric", 4, 10)],
    "hulk": [("legends:mutantGene", 1, 0), ("legends:fabric", 4, 5)],
    "pym": [("legends:pymParticle", 1, 0), ("legends:tech", 2, 0)],
    "asgard": [("legends:asgardianSteel", 2, 0)],
    "wakanda": [("legends:vibranium", 1, 0), ("legends:fabric", 4, 15)],
    "generic": [("legends:fabric", 4, 0), ("legends:tech", 2, 0)],
}

FAMILY_OF = {
    "superman": "kryptonian", "supergirl": "kryptonian", "generalzod": "kryptonian",
    "batman": "bat", "nightwing": "bat", "redhood": "bat", "redrobin": "bat",
    "robin_grayson": "bat", "robin_todd": "bat", "robin_drake": "bat",
    "robin_brown": "bat", "robin_wayne": "bat", "joker": "bat", "scarecrow": "bat",
    "flash": "speed", "kidflash": "speed", "flash_west": "speed",
    "flash_garrick": "speed", "reverseflash": "speed", "zoom": "speed",
    "ironman_mark0": "stark", "ironman_mark1": "stark", "ironman_mark3": "stark",
    "ironman_mark7": "stark", "ironman_mark21": "stark", "warmachine_mark1": "stark",
    "ironspider": "stark", "vision": "stark",
    "spiderman": "spider", "spiderman2099": "spider",
    "symbiotespiderman": "spider", "venom": "spider",
    "hulk": "hulk", "redhulk": "hulk", "abomination": "hulk",
    "antman": "pym", "wasp": "pym",
    "thor": "asgard",
    "blackpanther": "wakanda", "captainamerica": "wakanda",
}

KEEP_EXTRA_IDS = {
    "lootbags:lootbag",
    "lucky:lucky_block",
}
# gadgets that are not unique 100% keys
for _glist in R.LINE_GADGETS.values():
    for _g in _glist:
        KEEP_EXTRA_IDS.add(_g[0])

IM_FULL = {
    "Iron Man: Mark 3": "ironman_mark3",
    "Iron Man: Mark 7": "ironman_mark7",
}

FALLBACK_USED_BY_RETUNE = {
    ("legends:radioactiveFabric", 0),
    ("legends:fabric", 10),
}


def classify(q):
    name = q.get("properties:10", {}).get("betterquesting:10", {}).get("name:8", "")
    qid = q.get("questID:3")
    if qid == 300 or name == "Hall of Heroes":
        return "intro", None
    if qid == 301 or "Costume Closet" in name:
        return "closet", None
    if name in IM_FULL:
        return "full", IM_FULL[name]
    if name.endswith(": Full Set"):
        kind, char = R.char_from_quest(q)
        return "full", char
    kind, char = R.char_from_quest(q)
    if kind == "full":
        # IM classifier in retune is messy; trust name for non-Full-Set
        tasks = q.get("tasks:9") or {}
        ids = []
        for t in tasks.values():
            req = (t or {}).get("requiredItems:9") or {}
            for it in req.values():
                if isinstance(it, dict) and R.is_armor_id(it.get("id:8", "")):
                    ids.append(it["id:8"])
        if len(ids) >= 3:
            return "full", char
        return "piece", char
    return kind, char


def current_reward_stacks(q):
    out = []
    rew = q.get("rewards:9") or {}
    for rv in rew.values():
        inner = (rv or {}).get("rewards:9") or {}
        for item in inner.values():
            if isinstance(item, dict) and "id:8" in item:
                out.append((item["id:8"], int(item.get("Count:3", 1)), int(item.get("Damage:2", 0))))
    return out


def source_strip_ids(char, recipes, lang):
    ids = set()
    if char and char in recipes:
        for m in recipes[char]["mats"]:
            ids.add(m["id"])
        sliced, _ = R.mats_to_rewards(R.piece_cost_mats(recipes[char]), 0.40, lang)
        for row in sliced:
            ids.add(row[0])
        if not sliced:
            ids.add("legends:radioactiveFabric")
            ids.add("legends:fabric")
    return ids


def slice_for(char, recipes, lang):
    if not char or char not in recipes:
        return [], ["no-recipe %s" % char]
    entry = recipes[char]
    piece_mats = R.piece_cost_mats(entry)
    sliced, notes = R.mats_to_rewards(piece_mats, PIECE_FRACTION, lang)
    items = [(iid, n, dmg) for iid, n, dmg, rec, fr, actual in sliced]
    if entry.get("full_suit_recipe"):
        notes.append("donor recipe had armor ingredients; counts/4 then *30%")
    else:
        notes.append("donor per-piece getMaterials *30%")
    return items, notes


def resolve_donor(src, recipes, lang):
    notes = []
    want = RETARGET.get(src)
    seen = set()
    hops = 0
    while want and hops < 6:
        if want == src:
            notes.append("skip self-donor %s" % want)
            want = DONOR_FALLBACK.get(want)
            hops += 1
            continue
        items, sn = slice_for(want, recipes, lang)
        if items:
            return want, items, notes + sn
        notes.append("thin donor %s: %s" % (want, "; ".join(sn)))
        seen.add(want)
        nxt = DONOR_FALLBACK.get(want) or RETARGET.get(want)
        if not nxt or nxt in seen or nxt == src:
            break
        want = nxt
        hops += 1
    fam = FAMILY_OF.get(RETARGET.get(src), FAMILY_OF.get(src, "generic"))
    fb = list(FAMILY_FALLBACK.get(fam, FAMILY_FALLBACK["generic"]))
    notes.append("family fallback %s via %s" % (fam, RETARGET.get(src)))
    return RETARGET.get(src) or src, fb, notes


def keep_extras(old_stacks, strip_ids):
    kept = []
    for iid, c, d in old_stacks:
        if R.is_armor_id(iid) or iid in R.BANNED_IDS or any(b in iid.lower() for b in R.BANNED_SUBSTR):
            continue
        if R.is_unique_key(iid):
            continue
        if iid in strip_ids:
            continue
        if iid in KEEP_EXTRA_IDS or iid.startswith("lootbags:") or iid.startswith("lucky:"):
            kept.append((iid, c, d))
            continue
        # leftover cool extras that are not same-set mats
        kept.append((iid, c, d))
    return kept


def merge_stacks(items):
    cleaned = []
    for iid, c, d in items:
        found = False
        for i, (a, b, e) in enumerate(cleaned):
            if a == iid and e == d:
                cleaned[i] = (a, b + c, e)
                found = True
                break
        if not found:
            cleaned.append((iid, c, d))
    return cleaned


def hall_targets(data):
    qdb = data["questDatabase:9"]
    ch18 = set()
    for line in data.get("questLines:9", {}).values():
        if line.get("lineID:3") == 18:
            for e in line.get("quests:9", {}).values():
                ch18.add(e.get("id:3"))
    out = []
    seen = set()
    for key, q in qdb.items():
        qid = q.get("questID:3")
        if qid is None or qid in seen:
            continue
        if 300 <= qid <= 400 or qid in ch18:
            seen.add(qid)
            out.append((key, q))
    out.sort(key=lambda t: t[1]["questID:3"])
    return out


def main():
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = os.path.join(WORK, "DefaultQuests.pre-fullset-retarget-%s.json" % stamp)
    os.makedirs(WORK, exist_ok=True)
    shutil.copy2(SRC, backup)
    side = os.path.join(
        os.path.dirname(SRC), "DefaultQuests.json.bak-fullset-retarget"
    )
    shutil.copy2(SRC, side)
    print("backup", backup)
    print("backup", side)

    recipes, skipped, lang = R.load_recipes()
    print("recipes", len(recipes), "skipped_rows", len(skipped))

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
    targets = hall_targets(data)

    report = []
    piece_fingerprints_before = {}
    untouched = []
    rewritten = 0
    missing_map = []

    for key, q in targets:
        qid = q["questID:3"]
        name = q["properties:10"]["betterquesting:10"]["name:8"]
        kind, char = classify(q)
        old = current_reward_stacks(q)
        if kind != "full":
            piece_fingerprints_before[qid] = (kind, char, name, old)
            untouched.append((qid, kind, char, name))
            continue
        if not char:
            missing_map.append((qid, name, char))
            continue
        if char not in RETARGET:
            missing_map.append((qid, name, char))
            continue

        strip_ids = source_strip_ids(char, recipes, lang)
        extras = keep_extras(old, strip_ids)
        donor, mats, notes = resolve_donor(char, recipes, lang)
        items = merge_stacks(list(mats) + list(extras))

        cleaned = []
        for iid, c, d in items:
            if R.is_armor_id(iid) or iid in R.BANNED_IDS or any(b in iid.lower() for b in R.BANNED_SUBSTR):
                notes.append("stripped %s" % iid)
                continue
            if R.is_unique_key(iid):
                notes.append("stripped unique %s" % iid)
                continue
            if iid.startswith("legends:") and not R.lang_item_ok(iid, lang):
                base = iid.split(":")[1]
                if base not in lang and ("item.%s.name" % base) not in lang:
                    notes.append("stripped no-lang %s" % iid)
                    continue
            cleaned.append((iid, c, d))
        items = merge_stacks(cleaned)
        if not any(i[0] not in ("lootbags:lootbag", "lucky:lucky_block") for i in items):
            fam = FAMILY_OF.get(donor, "generic")
            items = merge_stacks(list(FAMILY_FALLBACK[fam]) + list(extras))
            notes.append("emergency family mats after strip")

        q["rewards:9"] = R.item_rewards(items)
        R.flatten_rewards(q)
        rewritten += 1
        report.append({
            "id": qid,
            "name": name,
            "from": char,
            "to": donor,
            "before": old,
            "after": items,
            "mats": mats,
            "extras_kept": extras,
            "notes": notes,
        })

    if missing_map:
        raise SystemExit("unmapped full-set quests: %s" % missing_map)

    # validate hall rewards
    armor_left = []
    bad = []
    pets_touched = False
    for key, q in qdb.items():
        qid = q.get("questID:3")
        name = q.get("properties:10", {}).get("betterquesting:10", {}).get("name:8", "")
        if "Inventory Pet" in name or (qid is not None and qid < 300 and qid != 32):
            # do not care unless we rewrote it — we didn't
            pass
        if qid is None or not (300 <= qid <= 400):
            continue
        rew = q.get("rewards:9") or {}
        for rv in rew.values():
            inner = (rv or {}).get("rewards:9") or {}
            for item in inner.values():
                if not isinstance(item, dict):
                    continue
                extra_keys = set(item.keys()) - {"id:8", "Count:3", "Damage:2", "OreDict:8"}
                if extra_keys:
                    bad.append((qid, "wrapper", sorted(extra_keys)))
                iid = item.get("id:8", "")
                if R.is_armor_id(iid):
                    armor_left.append((qid, iid))
                if any(b in iid.lower() for b in R.BANNED_SUBSTR):
                    bad.append((qid, "banned", iid))
                if iid.startswith("legends:") and not R.lang_item_ok(iid, lang):
                    base = iid.split(":")[1]
                    if base not in lang and ("item.%s.name" % base) not in lang:
                        bad.append((qid, "lang", iid))

    if armor_left:
        raise SystemExit("armor rewards remain: %s" % armor_left)
    if bad:
        raise SystemExit("bad rewards: %s" % bad[:30])

    # piece quests must be byte-identical in reward stacks
    piece_changed = []
    for key, q in targets:
        qid = q["questID:3"]
        if qid not in piece_fingerprints_before:
            continue
        kind, char, name, old = piece_fingerprints_before[qid]
        now = current_reward_stacks(q)
        if now != old:
            piece_changed.append((qid, name, old, now))
    if piece_changed:
        raise SystemExit("piece/intro/closet rewards changed: %s" % piece_changed[:5])

    tmp = SRC + ".tmp-fullset"
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

    rep_path = os.path.join(WORK, "fullset_retarget_report.json")
    with open(rep_path, "w", encoding="utf-8") as f:
        json.dump({
            "rewritten_fullsets": rewritten,
            "untouched": [
                {"id": a, "kind": b, "char": c, "name": d} for a, b, c, d in untouched
            ],
            "fraction_other": PIECE_FRACTION,
            "retarget": RETARGET,
            "report": report,
        }, f, indent=2, ensure_ascii=False)

    print("wrote", SRC)
    print("rewritten_fullsets", rewritten)
    print("untouched", len(untouched))
    print("report", rep_path)
    print("--- FULL SET RETARGETS ---")
    for row in report:
        mats = ", ".join("%s x%d:%d" % (a, b, c) for a, b, c in row["mats"][:6])
        print("Q%s %s | %s -> %s | %s" % (row["id"], row["name"], row["from"], row["to"], mats))


if __name__ == "__main__":
    main()
