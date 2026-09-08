# -*- coding: utf-8 -*-
"""Fix placeholders, bad rewards, tab titles, and Secrets order. Do not re-run expand."""
from __future__ import print_function
import json
import os
import shutil
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.normpath(os.path.join(
    HERE, "..", "..", "minecraft", "config", "betterquesting", "DefaultQuests.json"
))
LIVE = os.path.expanduser(
    "~/Library/Application Support/PrismLauncher/instances/Quest Forge/"
    "minecraft/config/betterquesting/DefaultQuests.json"
)

BAD_IDS = (
    "adventurebackpack:blockSleepingBag",
    "adventurebackpack:backpackTank",
    "levelup:XPTalisman",
    "levelup:RespecBook",
    "Sync:Sync_SyncCore",
    "OpenBlocks:gliderwing",
    "InventoryPets:petAchieveItem",
)


def stack(id_, count=1, dmg=0):
    return {"id:8": id_, "Count:3": count, "Damage:2": dmg, "OreDict:8": ""}


def by_qid(qdb, qid):
    for q in qdb.values():
        if q.get("questID:3") == qid:
            return q
    raise KeyError("missing quest %s" % qid)


def walk_ids(obj):
    found = []
    if isinstance(obj, dict):
        if "id:8" in obj:
            found.append(obj)
        for v in obj.values():
            found.extend(walk_ids(v))
    elif isinstance(obj, list):
        for v in obj:
            found.extend(walk_ids(v))
    return found


def replace_id(qdb, old, new, dmg=None):
    n = 0
    for item in walk_ids(qdb):
        if item.get("id:8") == old:
            item["id:8"] = new
            if dmg is not None:
                item["Damage:2"] = dmg
            n += 1
    return n


def set_checkbox(q):
    q["tasks:9"] = {
        "0:10": {
            "index:3": 0,
            "taskID:8": "bq_standard:checkbox",
        }
    }


def main():
    if not os.path.isfile(SRC):
        raise SystemExit("missing " + SRC)
    backup = os.path.join(
        HERE, "DefaultQuests.pre-cleanup-%s.json" % datetime.now().strftime("%Y%m%d-%H%M%S")
    )
    shutil.copy2(SRC, backup)
    print("backup", backup)

    with open(SRC, "r", encoding="utf-8") as f:
        data = json.load(f)

    qdb = data["questDatabase:9"]
    lines = data["questLines:9"]

    # --- Welcome: usable bed, shorter copy so the left pane does not chew it ---
    q0 = by_qid(qdb, 0)
    q0["properties:10"]["betterquesting:10"]["desc:8"] = (
        "§6✦ QUEST FORGE ✦§r\n\n"
        "§oThe old chronicle called this CrazyCraft. Same shattered sky. Same titans.§r\n\n"
        "We numbered the disasters in the order you should meet them. "
        "Main chapters are the climb. Side pages are hobbies. Secrets stay quiet.\n\n"
        "§eClaim this and start walking.§r"
    )
    q0["rewards:9"]["0:10"]["rewards:9"]["2:10"] = stack("minecraft:bed")

    # --- Pick a Class: real Level Up registry names ---
    q431 = by_qid(qdb, 431)
    q431["properties:10"]["betterquesting:10"]["icon:10"] = stack("levelup:respecBook")
    q431["properties:10"]["betterquesting:10"]["desc:8"] = (
        "§oLevel Up! is a second skill tree the HUD does not introduce.§r\n\n"
        "Open the Level Up GUI (default L) and pick a class. "
        "Miner, Warrior, Scout - they all pay rent. "
        "The Book of Unlearning is there if you hate the first choice.\n\n"
        "§7\"He picked Freelancer for the points. He still could not punch a Warg.\" - Trainer§r\n\n"
        "§eChoose a class. Check the box when the HUD agrees.§r"
    )
    q431["rewards:9"]["0:10"]["rewards:9"]["0:10"] = stack("levelup:xpTalisman")

    # --- Spare You: Sync Core is registered as Sync_ItemPlaceholder ---
    q432 = by_qid(qdb, 432)
    q432["properties:10"]["betterquesting:10"]["icon:10"] = stack("Sync:Sync_ItemPlaceholder")
    q432["tasks:9"]["0:10"]["requiredItems:9"]["0:10"] = stack("Sync:Sync_ItemPlaceholder")

    # --- Hang glider: wing is OpenBlocks:generic damage 0 ---
    q423 = by_qid(qdb, 423)
    q423["rewards:9"]["0:10"]["rewards:9"]["0:10"] = stack("OpenBlocks:generic", 2, 0)

    # --- Tanks: tank is backpackComponent damage 2. Sleeping bag block is not an item. ---
    q435 = by_qid(qdb, 435)
    q435["properties:10"]["betterquesting:10"]["icon:10"] = stack(
        "adventurebackpack:backpackComponent", 1, 2
    )
    q435["properties:10"]["betterquesting:10"]["desc:8"] = (
        "§oThe backpack is a chest until you add plumbing.§r\n\n"
        "A Backpack Tank holds fluid. A Hose is how you fill it, dump it, or drink it. "
        "Sleep in the bed from the first page. This page is the plumbing.\n\n"
        "§7\"He filled the left tank with lava. The hose had opinions.\" - Outfitter§r\n\n"
        "§eCraft a Backpack Tank and a Backpack Hose.§r"
    )
    q435["tasks:9"]["0:10"]["requiredItems:9"]["0:10"] = stack(
        "adventurebackpack:backpackComponent", 1, 2
    )
    q435["rewards:9"]["0:10"]["rewards:9"]["1:10"] = stack(
        "adventurebackpack:adventureHat"
    )

    # --- Legendary pets: achievement icons do nothing. Swap for shelf trophies. ---
    trophies = {
        67: stack("minecraft:record_11"),
        83: stack("minecraft:record_wait"),
        215: stack("thejungle:ancientSkull"),
        208: stack("statues:statues.statue"),
    }
    for qid, item in trophies.items():
        q = by_qid(qdb, qid)
        rewards = q["rewards:9"]["0:10"]["rewards:9"]
        for key, slot in list(rewards.items()):
            if str(slot.get("id:8", "")).startswith("InventoryPets:petAchieve"):
                rewards[key] = item
        desc = q["properties:10"]["betterquesting:10"]["desc:8"]
        q["properties:10"]["betterquesting:10"]["desc:8"] = desc.replace("—", "-")

    # --- Pet Collector: the 10-pet trinket is never given in survival ---
    q71 = by_qid(qdb, 71)
    q71["properties:10"]["betterquesting:10"]["icon:10"] = stack("InventoryPets:feedBag")
    q71["properties:10"]["betterquesting:10"]["desc:8"] = (
        "§d§l✦ TEN POCKETS ✦§r\n\n"
        "§oA true Pet Keeper does not choose favorites. They collect them all.§r\n\n"
        "Inventory Pets never hands you a 10-pet trinket in this pack. "
        "That item is an achievement icon, not loot, so the book cannot detect it. "
        "This page does not gate anything else.\n\n"
        "§eCheck the box when ten different pets actually live on you.§r"
    )
    set_checkbox(q71)

    # Sweep any leftover wrong registry names.
    print("replaced XPTalisman", replace_id(qdb, "levelup:XPTalisman", "levelup:xpTalisman"))
    print("replaced RespecBook", replace_id(qdb, "levelup:RespecBook", "levelup:respecBook"))
    print("replaced SyncCore", replace_id(qdb, "Sync:Sync_SyncCore", "Sync:Sync_ItemPlaceholder"))
    print("replaced gliderwing", replace_id(qdb, "OpenBlocks:gliderwing", "OpenBlocks:generic", 0))
    print("replaced backpackTank", replace_id(qdb, "adventurebackpack:backpackTank", "adventurebackpack:backpackComponent", 2))
    print("replaced sleepingBagBlock", replace_id(qdb, "adventurebackpack:blockSleepingBag", "minecraft:bed"))

    # --- Tab titles: GuiHome clips long names. Secrets last. ---
    rename = {
        "Chapter 1: Humble Beginnings": ("Ch 1: Start", 0),
        "Chapter 2: Base Building": ("Ch 2: Base", 1),
        "Chapter 3: Into the Twilight": ("Ch 3: Twilight", 2),
        "Chapter 4: Witchery - The Old Ways": ("Ch 4: Witchery", 3),
        "Chapter 5: Witchery - The Dark Paths": ("Ch 5: Dark Paths", 4),
        "Chapter 6: The Hardcore End": ("Ch 6: The End", 5),
        "Chapter 7: OreSpawn Boss Rush": ("Ch 7: OreSpawn", 6),
        "Chapter 8: TragicMC - The Doom Dimensions": ("Ch 8: TragicMC", 7),
        "Chapter 9: ProjectE - Earned Power": ("Ch 9: ProjectE", 8),
        "Side: Railcraft - Steel and Steam": ("Railcraft", 9),
        "Side: Gadgets and Glory": ("Gadgets", 10),
        "Side: The Beastiary": ("Beastiary", 17),
        "Side: Exploration and Security": ("Exploration", 11),
        "Workshop: Building and Living": ("Workshop", 12),
        "Side: Danger Zone": ("Danger Zone", 13),
        "Side: War Machines": ("War Machines", 14),
        "Workshop: Inventory Pets": ("Pets", 15),
        "★ Rewards and Achievements ★": ("Rewards", 16),
        "Side: Hall of Heroes": ("Heroes", 18),
        "★ Secrets ★": ("Secrets", 19),
    }
    seen = set()
    for line in lines.values():
        bq = line["properties:10"]["betterquesting:10"]
        old = bq["name:8"]
        if old not in rename:
            raise SystemExit("unexpected tab name: %r" % old)
        new_name, order = rename[old]
        bq["name:8"] = new_name
        line["order:3"] = order
        seen.add(old)
        print("tab", old, "->", new_name, "order", order)
    missing = set(rename) - seen
    if missing:
        raise SystemExit("missing tabs: %s" % missing)

    settings = data["questSettings:10"]["betterquesting:10"]
    settings["pack_version:3"] = int(settings.get("pack_version:3", 1)) + 1

    leftover = []
    for item in walk_ids(qdb):
        iid = item.get("id:8", "")
        if any(bad in iid for bad in BAD_IDS):
            leftover.append(iid)
    if leftover:
        raise SystemExit("leftover bad ids: %s" % leftover)

    orders = sorted((ln["order:3"], ln["properties:10"]["betterquesting:10"]["name:8"]) for ln in lines.values())
    print("order dump:")
    for order, name in orders:
        print(" ", order, name)
    if orders[-1][1] != "Secrets":
        raise SystemExit("Secrets is not last")
    if len({o for o, _ in orders}) != len(orders):
        raise SystemExit("duplicate tab orders: %s" % orders)

    text = json.dumps(data, indent=2, ensure_ascii=False)
    # BQ 3 files use 2-space indent already; keep a trailing newline.
    with open(SRC, "w", encoding="utf-8") as f:
        f.write(text)
        f.write("\n")
    shutil.copy2(SRC, LIVE)
    print("wrote", SRC)
    print("synced", LIVE)
    print("quests", len(qdb), "tabs", len(lines), "pack_version", settings["pack_version:3"])


if __name__ == "__main__":
    main()
