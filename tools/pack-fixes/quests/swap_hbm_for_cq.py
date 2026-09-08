# -*- coding: utf-8 -*-
"""One-shot: pull HBM, keep ICBM, add ChocolateQuest 1.1d. Do not re-run expand."""
from __future__ import print_function

import json
import os
import shutil
import zipfile
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
UNPACKED = os.path.normpath(os.path.join(HERE, "..", "..", "minecraft"))
LIVE = os.path.expanduser(
    "~/Library/Application Support/PrismLauncher/instances/Quest Forge/minecraft"
)
SRC = os.path.join(UNPACKED, "config", "betterquesting", "DefaultQuests.json")
LIVE_Q = os.path.join(LIVE, "config", "betterquesting", "DefaultQuests.json")
CQ_JAR_SRC = "/tmp/qf-cq/cq.jar"
CQ_JAR_NAME = "chocolateQuest-1.7.10-1.1d.jar"
HBM_QUESTS = (148, 149, 155, 410, 411, 412, 413, 414, 415)

CHANCE_PATCH = {
    "caveTests.prop": 0,
    "castlesRandomized.prop": 200,
    "castlesSchematic.prop": 80,
    "castlesSchematicSnow.prop": 30,
    "ship.prop": 20,
    "npcVillage.prop": 80,
    "netherCity.prop": 30,
    "stronghold.prop": 70,
    "stronghold_desert.prop": 60,
}

CQ_CFG = """# Configuration file

general {
    I:distanceToDespawn=64
    I:dungeonBuilderSpeed=1000
    I:dungeonSeparation=24
    B:dungeonsInFlat=false
    B:extractData=false
    I:potionMinePreventionID=31
    B:useInstantDungeonBuilder=true
}
"""


def stack(id_, count=1, dmg=0):
    return {"id:8": id_, "Count:3": count, "Damage:2": dmg, "OreDict:8": ""}


def retrieval_quest(qid, name, desc, icon, item, prereqs, rewards, ignore_nbt=1):
    req = {"0:10": stack(item)}
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
                "requiredItems:9": req,
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


def place_map(coords):
    out = {}
    for i, (qid, x, y, size) in enumerate(coords):
        out["%d:10" % i] = {
            "sizeX:3": size,
            "x:3": x,
            "y:3": y,
            "id:3": qid,
            "sizeY:3": size,
        }
    return out


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


def line_by_id(lines, lid):
    for line in lines.values():
        if line.get("lineID:3") == lid:
            return line
    raise KeyError("missing line %s" % lid)


def patch_living_groups(path):
    if not os.path.isfile(path):
        return 0
    return strip_hbm_lines(path)


def strip_hbm_lines(path):
    if not os.path.isfile(path):
        return 0
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
    keep = [ln for ln in lines if "hbm:" not in ln and '"hbm.' not in ln and "hbm.entity" not in ln]
    n = len(lines) - len(keep)
    if n:
        with open(path, "w", encoding="utf-8") as f:
            f.writelines(keep)
    return n


def rm(path):
    if os.path.isdir(path):
        shutil.rmtree(path)
        print("rmdir", path)
    elif os.path.isfile(path):
        os.remove(path)
        print("rm", path)


def install_cq_and_strip_hbm(root):
    mods = os.path.join(root, "mods")
    cfg = os.path.join(root, "config")
    dest_jar = os.path.join(mods, CQ_JAR_NAME)
    shutil.copy2(CQ_JAR_SRC, dest_jar)
    print("cq jar", dest_jar)

    rm(os.path.join(mods, "hbmBETA.jar"))
    rm(os.path.join(cfg, "hbm.cfg"))
    rm(os.path.join(cfg, "hbmTemplate.json"))
    rm(os.path.join(cfg, "JustAnotherSpawner", "WorldSettings", "BASIC", "DEFAULT", "EntityHandlers", "hbm.cfg"))
    rm(os.path.join(cfg, "MobProperties", "hbm"))
    for extra in (
        os.path.join(root, "journeymap", "icon", "entity", "2D", "hbm"),
        os.path.join(root, "journeymap", "icon", "entity", "3D", "hbm"),
    ):
        rm(extra)

    n = patch_living_groups(
        os.path.join(cfg, "JustAnotherSpawner", "WorldSettings", "BASIC", "DEFAULT", "LivingGroups.cfg")
    )
    print("living groups hbm keys", n, root)
    print("heatmap hbm lines", strip_hbm_lines(os.path.join(cfg, "bbm", "ve", "HeatMap.cfg")), root)
    print("sstow hbm lines", strip_hbm_lines(os.path.join(cfg, "SSTOW", "BlackList.cfg")), root)

    chocolate = os.path.join(cfg, "Chocolate")
    if os.path.isdir(chocolate):
        shutil.rmtree(chocolate)
    os.makedirs(chocolate)
    with zipfile.ZipFile(CQ_JAR_SRC) as zf:
        for info in zf.infolist():
            prefix = "assets/chocolatequest/Chocolate/"
            if not info.filename.startswith(prefix) or info.filename.endswith("/"):
                continue
            rel = info.filename[len(prefix):]
            out = os.path.join(chocolate, rel)
            os.makedirs(os.path.dirname(out), exist_ok=True)
            with zf.open(info) as src, open(out, "wb") as dst:
                dst.write(src.read())

    patched = 0
    dungeon_cfg = os.path.join(chocolate, "DungeonConfig")
    for dirpath, _, files in os.walk(dungeon_cfg):
        for name in files:
            if name not in CHANCE_PATCH:
                continue
            path = os.path.join(dirpath, name)
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                text = f.read()
            new = []
            done = False
            for ln in text.splitlines(True):
                if not done and ln.strip().startswith("chance"):
                    new.append("chance = %d\n" % CHANCE_PATCH[name])
                    if ln.endswith("\r\n"):
                        new[-1] = "chance = %d\r\n" % CHANCE_PATCH[name]
                    done = True
                else:
                    new.append(ln)
            with open(path, "w", encoding="utf-8") as f:
                f.writelines(new)
            patched += 1
            print("chance", name, CHANCE_PATCH[name])
    if patched != len(CHANCE_PATCH):
        raise SystemExit("expected %d chance patches, got %d" % (len(CHANCE_PATCH), patched))

    with open(os.path.join(cfg, "chocolateQuest.cfg"), "w", encoding="utf-8") as f:
        f.write(CQ_CFG)
    print("wrote chocolateQuest.cfg", root)


def edit_quests():
    backup = os.path.join(
        HERE, "DefaultQuests.pre-hbm-out-%s.json" % datetime.now().strftime("%Y%m%d-%H%M%S")
    )
    shutil.copy2(SRC, backup)
    print("backup", backup)

    with open(SRC, "r", encoding="utf-8") as f:
        data = json.load(f)

    qdb = data["questDatabase:9"]
    lines = data["questLines:9"]
    drop = set(HBM_QUESTS)

    for qid in HBM_QUESTS:
        key = "%d:10" % qid
        if key in qdb:
            del qdb[key]
            print("deleted quest", qid)

    for q in qdb.values():
        pre = q.get("preRequisites:11") or []
        cleaned = [p for p in pre if p not in drop]
        if cleaned != list(pre):
            q["preRequisites:11"] = cleaned
            print("stripped prereqs on", q.get("questID:3"))

    qdb["440:10"] = retrieval_quest(
        440,
        "The Ridge Has a Landlord",
        "§oThe skyline grew a landlord. The landlord had a flag.§r\n\n"
        "Chocolate Quest puts castles on ridges, ships on the water, and the occasional stronghold under the sand. "
        "The banner is how you prove you went inside instead of taking a screenshot.\n\n"
        "§7\"He said it was abandoned. The flag was still warm.\" - Survey§r\n\n"
        "§eBring back a Chocolate Quest banner. Any colour. The ridge does not care.§r",
        "chocolateQuest:banner",
        "chocolateQuest:banner",
        [4],
        [("minecraft:map", 1, 0), ("minecraft:cooked_beef", 8, 0), ("minecraft:ender_pearl", 2, 0)],
        ignore_nbt=1,
    )
    qdb["441:10"] = retrieval_quest(
        441,
        "A Blade With a Name",
        "§oMost swords in this pack are tools. This one remembers who held it last.§r\n\n"
        "Moonlight is a named blade from a Chocolate Quest site, not a factory product. "
        "It will not skip Mobzilla. It will make the walk to the next silhouette less boring.\n\n"
        "§7\"He asked if it was Ultimate. It was not. He kept it anyway.\" - Armourer§r\n\n"
        "§eRetrieve a Moonlight Sword from a Chocolate Quest dungeon.§r",
        "chocolateQuest:swordMoonLight",
        "chocolateQuest:swordMoonLight",
        [440],
        [("minecraft:name_tag", 1, 0), ("minecraft:diamond", 3, 0), ("minecraft:golden_apple", 2, 0)],
        ignore_nbt=1,
    )

    war = line_by_id(lines, 17)
    war["quests:9"] = place_map(((150, 0, 0, 24), (151, 48, 0, 24)))
    wprops = war["properties:10"]["betterquesting:10"]
    wprops["icon:10"] = stack("icbmclassic:icbmCGrenade")
    wprops["desc:8"] = (
        "§o\"Range is a privilege. So is having a roof tomorrow.\"§r\n\n"
        "ICBM is the optional silo. It is not the story spine and it is not how you skip Mobzilla. "
        "Grenade first. Launcher when you mean it.\n\n"
        "The horizon landmarks moved. Castles and ships are on Exploration now."
    )

    secrets = line_by_id(lines, 13)
    kept = []
    for slot in secrets["quests:9"].values():
        qid = slot["id:3"]
        if qid in drop:
            continue
        kept.append((qid, slot["x:3"], slot["y:3"], slot.get("sizeX:3", 24)))
    secrets["quests:9"] = place_map(kept)

    explore = line_by_id(lines, 7)
    eprops = explore["properties:10"]["betterquesting:10"]
    eprops["desc:8"] = (
        "§o\"Leave the base. Come back. Ideally still shaped like yourself.\"§r\n\n"
        "Backpacks with plumbing, a glider, ships, soul shards, and a lock on the door. "
        "The ridge may grow a castle. The water may grow a ship. Chocolate Quest is optional raiding, not a factory. "
        "SecurityCraft is how you stop the next raid from being a tour. Railcraft moved to its own Side tab — it grew out of this page."
    )
    explore["quests:9"]["8:10"] = {
        "sizeX:3": 24, "x:3": 0, "y:3": 192, "id:3": 440, "sizeY:3": 24,
    }
    explore["quests:9"]["9:10"] = {
        "sizeX:3": 24, "x:3": 48, "y:3": 192, "id:3": 441, "sizeY:3": 24,
    }

    data["questSettings:10"]["betterquesting:10"]["pack_version:3"] = 4

    placed = set()
    for line in lines.values():
        for slot in line.get("quests:9", {}).values():
            placed.add(slot["id:3"])

    ids = {q["questID:3"] for q in qdb.values()}
    bad_pre = []
    for q in qdb.values():
        for p in q.get("preRequisites:11") or []:
            if p not in ids:
                bad_pre.append((q["questID:3"], p))
    unplaced = sorted(ids - placed)
    leftover_hbm = [item["id:8"] for item in walk_ids(data) if str(item.get("id:8", "")).startswith("hbm:")]
    secret_order = line_by_id(lines, 13)["order:3"]

    print("quests", len(ids))
    print("unplaced", unplaced)
    print("bad_pre", bad_pre)
    print("hbm leftover", leftover_hbm)
    print("secrets order", secret_order)
    print("pack_version", data["questSettings:10"]["betterquesting:10"]["pack_version:3"])

    if bad_pre or leftover_hbm or secret_order != 19:
        raise SystemExit("quest validation failed")

    with open(SRC, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
    shutil.copy2(SRC, LIVE_Q)
    print("synced", LIVE_Q)
    return len(ids)


def main():
    if not os.path.isfile(CQ_JAR_SRC):
        raise SystemExit("missing " + CQ_JAR_SRC)
    if not os.path.isfile(SRC):
        raise SystemExit("missing " + SRC)
    install_cq_and_strip_hbm(UNPACKED)
    install_cq_and_strip_hbm(LIVE)
    n = edit_quests()
    print("done", n)


if __name__ == "__main__":
    main()
