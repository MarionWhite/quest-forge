# -*- coding: utf-8 -*-
"""Fit CQ collectables onto Exploration. Weak rewards. Do not re-run expand."""
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


def stack(id_, count=1, dmg=0):
    return {"id:8": id_, "Count:3": count, "Damage:2": dmg, "OreDict:8": ""}


def retrieval_quest(qid, name, desc, icon, item, prereqs, rewards, ignore_nbt=1):
    rew = {}
    for i, (rid, count, dmg) in enumerate(rewards):
        rew["%d:10" % i] = stack(rid, count, dmg)
    return {
        "questID:3": qid,
        "preRequisites:11": list(prereqs),
        "properties:10": {
            "betterquesting:10": {
                "snd_complete:8": "minecraft:entity.player.levelup",
                "taskLogic:8": "AND",
                "visibility:8": "ALWAYS",
                "isMain:1": 0,
                "simultaneous:1": 0,
                "icon:10": stack(icon),
                "snd_update:8": "minecraft:entity.player.levelup",
                "repeatTime:3": -1,
                "globalShare:1": 0,
                "questLogic:8": "AND",
                "name:8": name,
                "lockedProgress:1": 0,
                "autoClaim:1": 0,
                "isSilent:1": 0,
                "desc:8": desc,
            }
        },
        "tasks:9": {
            "0:10": {
                "partialMatch:1": 1,
                "autoConsume:1": 0,
                "groupDetect:1": 0,
                "ignoreNBT:1": ignore_nbt,
                "index:3": 0,
                "consume:1": 0,
                "requiredItems:9": {"0:10": stack(item)},
                "taskID:8": "bq_standard:retrieval",
            }
        },
        "rewards:9": {
            "0:10": {
                "rewardID:8": "bq_standard:item",
                "index:3": 0,
                "rewards:9": rew,
            }
        },
    }


def line_by_id(lines, lid):
    for line in lines.values():
        if line.get("lineID:3") == lid:
            return line
    raise KeyError("missing line %s" % lid)


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


def place(qid, x, y, size=24):
    return {"sizeX:3": size, "x:3": x, "y:3": y, "id:3": qid, "sizeY:3": size}


def main():
    backup = os.path.join(
        HERE, "DefaultQuests.pre-cq-fit-%s.json" % datetime.now().strftime("%Y%m%d-%H%M%S")
    )
    shutil.copy2(SRC, backup)
    print("backup", backup)

    with open(SRC, "r", encoding="utf-8") as f:
        data = json.load(f)

    qdb = data["questDatabase:9"]
    lines = data["questLines:9"]

    # Moonlight's registry name is moonSword, not the Java field swordMoonLight.
    moon = qdb["441:10"]
    moon["properties:10"]["betterquesting:10"]["icon:10"] = stack("chocolateQuest:moonSword")
    moon["properties:10"]["betterquesting:10"]["desc:8"] = (
        "§oMost swords in this pack are tools. This one remembers who held it last.§r\n\n"
        "Moonlight is a named blade from a Chocolate Quest site, not a factory product. "
        "It will not skip Mobzilla. It will make the walk to the next silhouette less boring.\n\n"
        "§7\"He asked if it was Ultimate. It was not. He kept it anyway.\" - Armourer§r\n\n"
        "§eRetrieve Moonlight from a Chocolate Quest dungeon.§r"
    )
    moon["tasks:9"]["0:10"]["requiredItems:9"]["0:10"] = stack("chocolateQuest:moonSword")
    moon["rewards:9"]["0:10"]["rewards:9"] = {
        "0:10": stack("minecraft:name_tag"),
        "1:10": stack("minecraft:cooked_beef", 8),
    }
    moon["preRequisites:11"] = [440]

    qdb["440:10"]["rewards:9"]["0:10"]["rewards:9"] = {
        "0:10": stack("minecraft:map"),
        "1:10": stack("minecraft:cooked_beef", 8),
    }

    qdb["442:10"] = retrieval_quest(
        442,
        "The Library Had Opinions",
        "§oA stick that argues with physics.§r\n\n"
        "Chocolate Quest staffs turn up in castle chests. Nature is the polite one. "
        "It will not skip a titan. It will make the next hallway less embarrassing.\n\n"
        "§7\"He asked if it was a wand. The tree outside disagreed.\" - Librarian§r\n\n"
        "§eRetrieve a Nature Staff.§r",
        "chocolateQuest:staffPhysic",
        "chocolateQuest:staffPhysic",
        [440],
        [("minecraft:redstone", 8, 0), ("minecraft:glass", 8, 0)],
    )
    qdb["443:10"] = retrieval_quest(
        443,
        "Rust in the First Room",
        "§oSomeone else finished this dungeon first. They left the steel.§r\n\n"
        "Rusted Chocolate Quest blades are old loot, not a craft. If it is orange, you opened the right chest.\n\n"
        "§7\"He polished it. It was still rust. He kept it.\" - Quartermaster§r\n\n"
        "§eRetrieve a Rusted Dagger.§r",
        "chocolateQuest:rustedDagger",
        "chocolateQuest:rustedDagger",
        [440],
        [("minecraft:iron_ingot", 8, 0), ("minecraft:bread", 8, 0)],
    )
    qdb["444:10"] = retrieval_quest(
        444,
        "Soft Landing",
        "§oBoots that refuse the ground, briefly.§r\n\n"
        "Cloud Boots are a rare Chocolate Quest toy. The pack already has a glider. "
        "These are for the hallway after the jump.\n\n"
        "§7\"He walked off the battlement. The battlement was not impressed. The boots were.\" - Watch§r\n\n"
        "§eRetrieve Cloud Boots.§r",
        "chocolateQuest:cloudBoots",
        "chocolateQuest:cloudBoots",
        [440],
        [("minecraft:feather", 8, 0), ("minecraft:leather", 4, 0)],
    )

    explore = line_by_id(lines, 7)
    qmap = explore["quests:9"]
    qmap["8:10"] = place(440, 0, 192)
    qmap["9:10"] = place(442, 48, 192)
    qmap["10:10"] = place(443, 0, 240)
    qmap["11:10"] = place(444, 48, 240)
    qmap["12:10"] = place(441, 24, 288)

    explore["properties:10"]["betterquesting:10"]["desc:8"] = (
        "§o\"Leave the base. Come back. Ideally still shaped like yourself.\"§r\n\n"
        "Backpacks with plumbing, a glider, ships, soul shards, and a lock on the door. "
        "The ridge may grow a castle. The water may grow a ship. "
        "A banner proves you went in. A staff, rusted steel, or Cloud Boots are chest toys. "
        "Moonlight is the named blade. None of it is a factory, and none of it skips Mobzilla. "
        "SecurityCraft is how you stop the next raid from being a tour. "
        "Railcraft moved to its own Side tab — it grew out of this page."
    )

    data["questSettings:10"]["betterquesting:10"]["pack_version:3"] = 5

    ids = {q["questID:3"] for q in qdb.values()}
    placed = set()
    for line in lines.values():
        for slot in line.get("quests:9", {}).values():
            placed.add(slot["id:3"])
    bad_pre = []
    for q in qdb.values():
        for p in q.get("preRequisites:11") or []:
            if p not in ids:
                bad_pre.append((q["questID:3"], p))
    leftover_hbm = [
        item["id:8"] for item in walk_ids(data)
        if str(item.get("id:8", "")).startswith("hbm:")
    ]
    leftover_wrong_moon = [
        item["id:8"] for item in walk_ids(data)
        if item.get("id:8") == "chocolateQuest:swordMoonLight"
    ]
    secret_order = line_by_id(lines, 13)["order:3"]
    strong = []
    for qid in (440, 441, 442, 443, 444):
        for item in walk_ids(qdb["%d:10" % qid]["rewards:9"]):
            if item["id:8"] in (
                "minecraft:diamond",
                "minecraft:golden_apple",
                "chocolateQuest:moonSword",
                "chocolateQuest:diamondSwordAndShield",
            ):
                strong.append((qid, item["id:8"], item["Count:3"]))

    print("quests", len(ids))
    print("unplaced", sorted(ids - placed))
    print("bad_pre", bad_pre)
    print("hbm", leftover_hbm)
    print("wrong moon id", leftover_wrong_moon)
    print("strong rewards", strong)
    print("secrets order", secret_order)
    print("pack_version", data["questSettings:10"]["betterquesting:10"]["pack_version:3"])
    if bad_pre or leftover_hbm or leftover_wrong_moon or strong or secret_order != 19:
        raise SystemExit("validation failed")

    with open(SRC, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
    shutil.copy2(SRC, LIVE)
    print("synced", LIVE)


if __name__ == "__main__":
    main()
