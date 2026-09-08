# -*- coding: utf-8 -*-
"""Fix the Secrets tab: hide everything, drop the pet, repair the old closets."""
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


def set_retrieval(q, items, ignore_nbt=1):
    req = {}
    for i, (id_, count, dmg) in enumerate(items):
        req["%d:10" % i] = stack(id_, count, dmg)
    q["tasks:9"]["0:10"]["requiredItems:9"] = req
    q["tasks:9"]["0:10"]["ignoreNBT:1"] = ignore_nbt


def rewrite(q, name, desc, vis="COMPLETED", prereqs=None):
    bq = q["properties:10"]["betterquesting:10"]
    bq["name:8"] = name
    bq["desc:8"] = desc
    bq["visibility:8"] = vis
    if prereqs is not None:
        q["preRequisites:11"] = list(prereqs)


def place_map(coords):
    out = {}
    for i, (qid, x, y, size) in enumerate(coords):
        out["%d:10" % i] = {
            "sizeX:3": size, "x:3": x, "y:3": y, "id:3": qid, "sizeY:3": size,
        }
    return out


def main():
    if not os.path.isfile(SRC):
        raise SystemExit("missing " + SRC)
    backup = os.path.join(
        HERE, "DefaultQuests.pre-secrets-%s.json" % datetime.now().strftime("%Y%m%d-%H%M%S")
    )
    shutil.copy2(SRC, backup)
    print("backup", backup)

    with open(SRC, "r", encoding="utf-8") as f:
        data = json.load(f)

    qdb = data["questDatabase:9"]
    lines = data["questLines:9"]

    # Pet Collector stays on Inventory Pets. The Collector was Pack Master in a
    # BiblioCraft trench coat — delete it rather than leave an unplaced ghost.
    if "72:10" in qdb:
        del qdb["72:10"]
        print("deleted Q72 The Collector")

    rewrite(
        qdb["73:10"],
        "§b★ Dimensional Traveler ★",
        "§oA brick from every sky the pack actually has.§r\n\n"
        "Netherrack does not count. End stone does not count. "
        "Bring back something that only exists after you left.\n\n"
        "§7\"He said he had been everywhere. He had a stack of cobble.\" - Customs§r\n\n"
        "§eHold a souvenir from each other world at once.§r",
        prereqs=[],
    )
    qdb["73:10"]["properties:10"]["betterquesting:10"]["icon:10"] = stack(
        "HardcoreEnderExpansion:endium_ingot"
    )
    set_retrieval(qdb["73:10"], [
        ("minecraft:ghast_tear", 1, 0),
        ("TwilightForest:item.torchberries", 1, 0),
        ("HardcoreEnderExpansion:endium_ingot", 1, 0),
        ("OreSpawn:OreSpawn_CrystalPinkIngot", 1, 0),
        ("TragicMC:synapseCrystal", 1, 0),
        ("witchery:somniancotton", 1, 0),
        ("thejungle:sapphire", 1, 0),
    ])

    rewrite(
        qdb["75:10"],
        "§c★ Full Arsenal ★",
        "§oEmerald, ruby, royal, Bertha, Ultimate. The ladder, in one scabbard.§r\n\n"
        "The chapter asked for the top. This page wants the rungs you threw in a chest and forgot.\n\n"
        "§7\"He kept the first sword. That is how you know it was not a phase.\" - Armourer§r\n\n"
        "§eCarry every OreSpawn sword tier at once.§r",
        prereqs=[],
    )

    rewrite(
        qdb["76:10"],
        "§d★ Twilight Master ★",
        "§oThe forest does not surrender. You empty it.§r\n\n"
        "Naga, Lich, Hydra, Ur-Ghast, Snow Queen. Scales, scepters, blood, chops, "
        "carminite, fur, and every head on a plaque.\n\n"
        "§7\"Pretty country. No landlords left to collect the rent.\" - Surveyor§r\n\n"
        "§eHold the full Twilight take at once.§r",
        prereqs=[],
    )
    set_retrieval(qdb["76:10"], [
        ("TwilightForest:item.nagaScale", 12, 0),
        ("TwilightForest:item.scepterTwilight", 1, 0),
        ("TwilightForest:item.scepterLifeDrain", 1, 0),
        ("TwilightForest:item.scepterZombie", 1, 0),
        ("TwilightForest:item.fieryBlood", 1, 0),
        ("TwilightForest:item.hydraChop", 1, 0),
        ("TwilightForest:item.carminite", 1, 0),
        ("TwilightForest:item.alphaFur", 4, 0),
        ("TwilightForest:item.trophy", 1, 0),  # Hydra
        ("TwilightForest:item.trophy", 1, 1),  # Naga
        ("TwilightForest:item.trophy", 1, 2),  # Lich
        ("TwilightForest:item.trophy", 1, 3),  # Ur-Ghast
        ("TwilightForest:item.trophy", 1, 4),  # Snow Queen
    ])

    rewrite(
        qdb["415:10"],
        "§4★ Fat Man ★",
        "§oThe book said it would not hand you a nuke. You built one anyway.§r\n\n"
        "Fat Man is optional. It is not the spine. It is not how you skip Mobzilla. "
        "If you place this, you are writing a different kind of chronicle.\n\n"
        "§7\"We had a reactor. We had a spare afternoon. Those are not reasons.\" - Site Lead§r\n\n"
        "§eYou already had it. This is just the stamp.§r",
        prereqs=[],
    )

    secrets = None
    for line in lines.values():
        name = line["properties:10"]["betterquesting:10"]["name:8"]
        if "SECRET" in name.upper() or name in ("★ Secrets ★", "§6★ SECRET ACHIEVEMENTS ★"):
            secrets = line
            break
    if secrets is None:
        raise SystemExit("secrets line missing")

    bq = secrets["properties:10"]["betterquesting:10"]
    bq["name:8"] = "★ Secrets ★"
    bq["icon:10"] = stack("minecraft:ender_eye")
    bq["desc:8"] = (
        "§oIf this page is blank, that is working.§r\n\n"
        "Nothing here introduces itself. Retrieval still counts in your pockets. "
        "When a title appears, you already knew why.\n\n"
        "The numbered chapters are the climb. This closet is the receipts "
        "you were not told to keep."
    )
    secrets["quests:9"] = place_map([
        (73, 0, 0, 24),
        (76, 48, 0, 24),
        (75, 0, 48, 24),
        (415, 48, 48, 32),
        (141, 0, 96, 24),
        (142, 48, 96, 24),
        (143, 0, 144, 24),
        (144, 48, 144, 24),
    ])

    tmp = SRC + ".tmp-secrets"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    with open(tmp, "r", encoding="utf-8") as f:
        check = json.load(f)
    os.replace(tmp, SRC)

    qdb = check["questDatabase:9"]
    placed = set()
    bad_prereq = []
    for line in check["questLines:9"].values():
        for e in line.get("quests:9", {}).values():
            placed.add(e["id:3"])
    for q in qdb.values():
        qid = q["questID:3"]
        for p in q.get("preRequisites:11", []):
            if ("%d:10" % p) not in qdb:
                bad_prereq.append((qid, p))
    unplaced = sorted(set(q["questID:3"] for q in qdb.values()) - placed)
    print("wrote", SRC)
    print("quests", len(qdb), "unplaced", unplaced, "bad_prereq", bad_prereq)

    sec = None
    for line in check["questLines:9"].values():
        if line["properties:10"]["betterquesting:10"]["name:8"] == "★ Secrets ★":
            sec = line
            break
    ids = sorted(e["id:3"] for e in sec["quests:9"].values())
    print("secrets ids", ids)
    for qid in ids:
        bq = qdb["%d:10" % qid]["properties:10"]["betterquesting:10"]
        print("  Q%d vis=%s name=%s" % (qid, bq["visibility:8"], bq["name:8"]))

    # Pet Collector must remain on Pets only
    pet_lines = []
    for line in check["questLines:9"].values():
        lname = line["properties:10"]["betterquesting:10"]["name:8"]
        for e in line.get("quests:9", {}).values():
            if e["id:3"] == 71:
                pet_lines.append(lname)
    print("Q71 still on", pet_lines)
    assert 71 not in ids
    assert 72 not in qdb
    assert all(
        qdb["%d:10" % qid]["properties:10"]["betterquesting:10"]["visibility:8"] == "COMPLETED"
        for qid in ids
    )
    assert not unplaced
    assert not bad_prereq

    if os.path.isfile(LIVE):
        shutil.copy2(SRC, LIVE)
        print("synced live", LIVE)


if __name__ == "__main__":
    main()
