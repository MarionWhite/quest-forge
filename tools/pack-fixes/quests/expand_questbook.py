# -*- coding: utf-8 -*-
"""Add the distribution-review quest lines and tighten mismatched copy.

Saints Pack is a music core, not relics — skipped on purpose.
Lycanites 1.13.0.5 only has Rahovart (no Asmodeus / Amalgalich).
"""
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

LB_COMMON, LB_UNCOMMON, LB_RARE, LB_EPIC, LB_LEGEND = 0, 1, 2, 3, 4


def stack(id_, count=1, dmg=0):
    return {"id:8": id_, "Count:3": count, "Damage:2": dmg, "OreDict:8": ""}


def retrieval_task(items):
    req = {}
    for i, (id_, count, dmg) in enumerate(items):
        req["%d:10" % i] = stack(id_, count, dmg)
    return {
        "0:10": {
            "partialMatch:1": 1,
            "autoConsume:1": 0,
            "groupDetect:1": 0,
            "ignoreNBT:1": 1,
            "index:3": 0,
            "consume:1": 0,
            "requiredItems:9": req,
            "taskID:8": "bq_standard:retrieval",
        }
    }


def checkbox_task():
    return {
        "0:10": {
            "index:3": 0,
            "taskID:8": "bq_standard:checkbox",
        }
    }


def item_rewards(items):
    rew = {}
    for i, (id_, count, dmg) in enumerate(items):
        rew["%d:10" % i] = stack(id_, count, dmg)
    return {
        "0:10": {
            "rewardID:8": "bq_standard:item",
            "index:3": 0,
            "rewards:9": rew,
        }
    }


def make_quest(qid, name, desc, icon, tasks, rewards, prereqs, main=0, vis="ALWAYS"):
    icon_id, icon_count, icon_dmg = icon if isinstance(icon, tuple) else (icon, 1, 0)
    return {
        "questID:3": qid,
        "preRequisites:11": list(prereqs),
        "properties:10": {
            "betterquesting:10": {
                "snd_complete:8": "minecraft:entity.player.levelup",
                "taskLogic:8": "AND",
                "visibility:8": vis,
                "isMain:1": main,
                "simultaneous:1": 0,
                "icon:10": stack(icon_id, icon_count, icon_dmg),
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
        "tasks:9": tasks,
        "rewards:9": rewards,
    }


def L(id_, count=1, dmg=0):
    return (id_, count, dmg)


def place(line, qid, x, y, size=24):
    quests = line["quests:9"]
    nxt = 0
    while "%d:10" % nxt in quests:
        nxt += 1
    quests["%d:10" % nxt] = {
        "sizeX:3": size,
        "x:3": x,
        "y:3": y,
        "id:3": qid,
        "sizeY:3": size,
    }


def find_line(lines, name):
    for key, line in lines.items():
        if line["properties:10"]["betterquesting:10"]["name:8"] == name:
            return key, line
    raise SystemExit("missing quest line: " + name)


# ---------------------------------------------------------------------------
# New quests
# ---------------------------------------------------------------------------

NEW = []


def add(qid, name, desc, icon, tasks, rewards, prereqs, main=0, vis="ALWAYS"):
    NEW.append(make_quest(qid, name, desc, icon, tasks, rewards, prereqs, main, vis))
    return qid


# Side: The Beastiary (Lycanites 1.13 — Rahovart is the only world boss)
Q_GAZER = add(
    401, "The Soulgazer",
    "§oThe overworld was already using a second bestiary. The book just never filed it.§r\n\n"
    "Lycanites mobs are not OreSpawn and they are not vanilla. A Soulgazer is how you write one down. "
    "Use it on a creature, then open the Beastiary (the key is unbound in Controls until you set it).\n\n"
    "§7\"I named it. It did not get friendlier.\" - Field Notes§r\n\n"
    "§eCraft a Soulgazer. Point it at something that looks like it has a Latin name.§r",
    "lycanitesmobs:soulgazer",
    retrieval_task([L("lycanitesmobs:soulgazer")]),
    item_rewards([L("forestmobs:wargtreat", 2), L("lootbags:lootbag", 1, LB_UNCOMMON)]),
    [4], main=1,
)

Q_TREAT = add(
    402, "Bribery Works",
    "§oSome of them will take a job. The rest will take the treat and you.§r\n\n"
    "Wargs are the overworld's obvious mount. A Warg Treat is how you start the argument. "
    "Feed a young one until the nametag changes its mind.\n\n"
    "§7\"The first one bit the hand. The second one waited.\" - Kennel Ledger§r\n\n"
    "§eCraft a Warg Treat. Do not test this on a demon.§r",
    "forestmobs:wargtreat",
    retrieval_task([L("forestmobs:wargtreat")]),
    item_rewards([L("lycanitesmobs:soulstone"), L("minecraft:bone", 16)]),
    [Q_GAZER], main=1,
)

Q_STONE = add(
    403, "Soulbound",
    "§oTame is temporary. A Soulstone is the paperwork.§r\n\n"
    "Use a Soulstone on a tamed Lycanites creature. It binds to you, shows up in the Pet or Mount manager, "
    "and comes back after it dies. That is the difference between a pet and a story about a pet.\n\n"
    "§7\"We buried the collar. The stone hummed in the chest the whole walk home.\" - Handler§r\n\n"
    "§eCraft a Soulstone. Bind something you can live with.§r",
    "lycanitesmobs:soulstone",
    retrieval_task([L("lycanitesmobs:soulstone")]),
    item_rewards([L("lycanitesmobs:soulkey"), L("lootbags:lootbag", 1, LB_RARE)]),
    [Q_TREAT], main=1,
)

Q_KEY = add(
    404, "The Soulkey",
    "§oAltars are just rocks until someone brings the right insult.§r\n\n"
    "A Soulkey activates a built altar: rare subspecies, events, and the one summon this version of Lycanites "
    "actually treats as a world boss. Build the altar first. The key does nothing in your pocket.\n\n"
    "§7\"He turned it in the air like a house key. The ground disagreed.\" - Witness§r\n\n"
    "§eHold a Soulkey. Read the altar schematic before you guess.§r",
    "lycanitesmobs:soulkey",
    retrieval_task([L("lycanitesmobs:soulkey")]),
    item_rewards([L("demonmobs:doomfirecharge", 8), L("lootbags:lootbag", 1, LB_RARE)]),
    [Q_STONE], main=1,
)

Q_CUBE = add(
    405, "A Box That Should Stay Shut",
    "§oThe Demonic Soulcube is not storage. It is bait.§r\n\n"
    "Rahovart is this pack's Lycanites world boss. The cube is how you tell him the address. "
    "Asmodeus and Amalgalich are not in this 1.7.10 build. Do not wait for them.\n\n"
    "§7\"We asked for a light. We got a landlord.\" - Cult Inventory§r\n\n"
    "§eCraft a Demonic Soulcube. Place it only when you mean the rest of the week.§r",
    "demonmobs:soulcubedemonic",
    retrieval_task([L("demonmobs:soulcubedemonic")]),
    item_rewards([L("demonmobs:hellfirecharge", 8), L("lootbags:lootbag", 1, LB_EPIC)]),
    [Q_KEY], main=1,
)

Q_RAHO = add(
    406, "Rahovart",
    "§oThe lord of the underworld is one fight, not a chapter of three.§r\n\n"
    "Kill him. Bring back a Demon Crystal. That is the receipt. He is late-game on purpose — "
    "diamond is the admission ticket, not the loadout.\n\n"
    "§7\"The name was the scary part until the health bar started.\" - Last Volunteer§r\n\n"
    "§eRetrieve a Demon Crystal. That means he is down.§r",
    "demonmobs:demoncrystal",
    retrieval_task([L("demonmobs:demoncrystal")]),
    item_rewards([L("lootbags:lootbag", 1, LB_LEGEND), L("lucky:lucky_block", 8), L("demonmobs:devillasagna", 4)]),
    [Q_CUBE], main=1,
)

# HBM factory — this NTM build has a press already; no anvil block. Assembler / oil / reactor instead.
Q_ASM = add(
    410, "HBM: The Assembler",
    "§oThe press makes plates. The assembler makes the rest of the argument.§r\n\n"
    "HBM's Assembly Machine is the factory floor. Templates in, parts out. "
    "If you skip this, every later machine is a pile of ingredients with no verb.\n\n"
    "§7\"Anyone can smelt. This is where it becomes a schedule.\" - Floor Foreman§r\n\n"
    "§eBuild an Assembly Machine.§r",
    "hbm:tile.machine_assembler",
    retrieval_task([L("hbm:tile.machine_assembler")]),
    item_rewards([L("hbm:item.circuit_copper", 8), L("hbm:item.plate_iron", 16)]),
    [149],
)

Q_DET = add(
    411, "HBM: Listen to the Ground",
    "§oOil does not announce itself. The detector does, if you point it down.§r\n\n"
    "Right-click the Oil Reservoir Detector on dirt that looks boring. "
    "It only bothers with the large deposits. Small puddles are not its problem.\n\n"
    "§7\"He scanned the garden. The garden was not oil. He scanned it again.\" - Survey§r\n\n"
    "§eCraft an Oil Reservoir Detector.§r",
    "hbm:item.oil_detector",
    retrieval_task([L("hbm:item.oil_detector")]),
    item_rewards([L("hbm:item.canister_empty", 4), L("hbm:item.battery_generic")]),
    [Q_ASM],
)

Q_OIL = add(
    412, "HBM: Crude",
    "§oBlack, heavy, and not yet useful. That is the point.§r\n\n"
    "An Oil Derrick or Pumpjack over a deposit fills canisters. Crude is the start of diesel, kerosene, and every bad idea that follows.\n\n"
    "§7\"We drank to the first barrel. Nobody drank the barrel.\" - Rig§r\n\n"
    "§eHold a Crude Oil Canister.§r",
    "hbm:item.canister_oil",
    retrieval_task([L("hbm:item.canister_oil")]),
    item_rewards([L("hbm:item.canister_empty", 4), L("lootbags:lootbag", 1, LB_RARE)]),
    [Q_DET],
)

Q_DIESEL = add(
    413, "HBM: Diesel",
    "§oRefine it or keep carrying a museum of sludge.§r\n\n"
    "Diesel is the first oil product that makes the rest of the factory move. "
    "Boilers, engines, and a lot of vehicles would like a word.\n\n"
    "§7\"Crude is a resource. Diesel is a decision.\" - Refinery Slate§r\n\n"
    "§eHold a Diesel Canister.§r",
    "hbm:item.canister_fuel",
    retrieval_task([L("hbm:item.canister_fuel")]),
    item_rewards([L("hbm:item.canister_fuel", 2), L("hbm:item.canister_canola")]),
    [Q_OIL],
)

Q_RX = add(
    414, "HBM: The Small Pile",
    "§oA reactor is a kettle that files complaints in sieverts.§r\n\n"
    "The Nuclear Reactor is the milestone. Not a silo. Not a crater. "
    "Learn the cooling and the fuel before you invent a second sun.\n\n"
    "§7\"It was on. That was the whole status report.\" - Night Shift§r\n\n"
    "§eBuild a Nuclear Reactor. Wear the Geiger like you mean it.§r",
    "hbm:tile.machine_reactor_small",
    retrieval_task([L("hbm:tile.machine_reactor_small")]),
    item_rewards([L("hbm:item.radaway", 16), L("hbm:item.geiger_counter"), L("lootbags:lootbag", 1, LB_EPIC)]),
    [Q_DIESEL],
)

Q_FAT = add(
    415, "§4★ Fat Man ★",
    "§oThe book said it would not hand you a nuke. You built one anyway.§r\n\n"
    "Fat Man is optional. It is not the spine. It is not how you skip Mobzilla. "
    "If you place this, you are writing a different kind of chronicle.\n\n"
    "§7\"We had a reactor. We had a spare afternoon. Those are not reasons.\" - Site Lead§r\n\n"
    "§eYou already had it. This is just the stamp.§r",
    "hbm:tile.nuke_man",
    retrieval_task([L("hbm:tile.nuke_man")]),
    item_rewards([L("hbm:item.radaway", 16), L("lootbags:lootbag", 1, LB_LEGEND)]),
    [],
    vis="COMPLETED",
)

# Jungle — two short flavor quests. Saints Pack skipped (music, not relics).
Q_SAPPH = add(
    420, "Soul Sapphire",
    "§oThe jungle keeps a second religion under the canopy.§r\n\n"
    "Welcome to the Jungle is temples, Saur-Ohn, and stones they thought held the dead. "
    "A Soul Sapphire is the first thing that proves you left the path.\n\n"
    "§7\"It looked like loot. It felt like a stare.\" - Temple Notes§r\n\n"
    "§eBring back a Sapphire.§r",
    "thejungle:sapphire",
    retrieval_task([L("thejungle:sapphire")]),
    item_rewards([L("thejungle:stewJungle", 4), L("lootbags:lootbag", 1, LB_UNCOMMON)]),
    [4],
)

Q_BOOK = add(
    421, "The Book of Scale",
    "§oFour fragments. One excuse to keep walking into the mist.§r\n\n"
    "The Book of Scale is how the Saur-Ohn filed their gods. Find a copy. "
    "The Lost World portal is later, and it wants the ceremonial kit — this page is only the reading.\n\n"
    "§7\"I started it for the recipes. I finished it because the stew was a quest.\" - Cook§r\n\n"
    "§eRetrieve the Book of Scale.§r",
    "thejungle:bookScale",
    retrieval_task([L("thejungle:bookScale")]),
    item_rewards([L("thejungle:ancientSkull"), L("lootbags:lootbag", 1, LB_RARE)]),
    [Q_SAPPH],
)

# Compact Machines
Q_CM = add(
    422, "A Room in a Block",
    "§oThe fortress got a filing cabinet that contains a room.§r\n\n"
    "A Small Compact Machine is a pocket dimension with a door the size of a brick. "
    "The Personal Shrinking Device is how you go in. Put a farm inside if you like your overworld quiet.\n\n"
    "§7\"We lost a cow. It was still producing. We just could not hear it.\" - Accountant§r\n\n"
    "§eCraft a Small Compact Machine and a Personal Shrinking Device.§r",
    ("CompactMachines:machine", 1, 1),
    retrieval_task([L("CompactMachines:machine", 1, 1), L("CompactMachines:psd")]),
    item_rewards([L("CompactMachines:innerwall", 32), L("lootbags:lootbag", 1, LB_UNCOMMON)]),
    [7],
)

# OpenBlocks + Ender Storage
Q_GLIDE = add(
    423, "Leave the Ground",
    "§oA frame, two wings, and the sudden discovery that falling is optional.§r\n\n"
    "The Hang Glider goes on your back. Jump. Shift to dive. Graves from OpenBlocks will still catch you "
    "if the landing is a suggestion.\n\n"
    "§7\"He cleared the wall. The wall was not the problem. The lake was.\" - Watch§r\n\n"
    "§eCraft a Hang Glider.§r",
    "OpenBlocks:hangglider",
    retrieval_task([L("OpenBlocks:hangglider")]),
    item_rewards([L("OpenBlocks:gliderwing", 2), L("minecraft:feather", 16)]),
    [4],
)

Q_ELEV = add(
    424, "Up Is a Block",
    "§oJump. Crouch. Same color. Empty shaft. That is the whole manual.§r\n\n"
    "Place two Elevators on the same column, three or more blocks apart, dyed to match. "
    "OpenBlocks graves still appear when you test this the wrong way. That is also a feature.\n\n"
    "§7\"We installed a ladder. Then we installed an argument against ladders.\" - Mason§r\n\n"
    "§eCraft an Elevator.§r",
    "OpenBlocks:elevator",
    retrieval_task([L("OpenBlocks:elevator")]),
    item_rewards([L("OpenBlocks:elevator"), L("minecraft:dye", 8, 1)]),
    [7],
)

Q_ENDER = add(
    425, "The Same Chest Twice",
    "§oThree dyes and a frequency. Distance becomes a rumor.§r\n\n"
    "An Ender Storage chest is not a vanilla ender chest. Color the three spots. "
    "Build a second one with the same colors somewhere you actually go. That is logistics.\n\n"
    "§7\"We put one in the hole and one in the kitchen. The hole started paying rent.\" - Quartermaster§r\n\n"
    "§eCraft an Ender Chest. Dye it on purpose.§r",
    "EnderStorage:enderChest",
    retrieval_task([L("EnderStorage:enderChest")]),
    item_rewards([L("EnderStorage:enderPouch"), L("minecraft:ender_pearl", 4)]),
    [7],
)

# Infernal / Level Up / Sync
Q_INF = add(
    430, "The Name Was Longer",
    "§oSome of them come with extra adjectives. That is Infernal Mobs.§r\n\n"
    "A nametag that reads like a resume means extra health, extra mods, and loot that is actually worth the swing. "
    "Kill one. Check the box when you have.\n\n"
    "§7\"It said '1UP Regenerating Ghastly.' I said no.\" - Night Watch§r\n\n"
    "§eSurvive an Infernal. Then admit it.§r",
    "minecraft:name_tag",
    checkbox_task(),
    item_rewards([L("minecraft:golden_apple", 2), L("lootbags:lootbag", 1, LB_UNCOMMON)]),
    [4],
)

Q_LVL = add(
    431, "Pick a Class",
    "§oLevel Up! is a second skill tree the HUD does not introduce.§r\n\n"
    "Open the Level Up GUI (default L) and pick a class. Miner, Warrior, Scout — they all pay rent. "
    "The Book of Unlearning is there if you hate the first choice.\n\n"
    "§7\"He picked Freelancer for the points. He still could not punch a Warg.\" - Trainer§r\n\n"
    "§eChoose a class. Check the box when the HUD agrees.§r",
    "levelup:RespecBook",
    checkbox_task(),
    item_rewards([L("levelup:XPTalisman"), L("minecraft:experience_bottle", 8)]),
    [4],
)

Q_SYNC = add(
    432, "A Spare You",
    "§oSync is a second body with your name on the paperwork.§r\n\n"
    "A Sync Core is the expensive part. The Shell Constructor is the room. "
    "The Treadmill is how a pig pays the power bill. Die near a finished shell and you get a second try.\n\n"
    "§7\"We kept the spare in the basement. The spare kept us.\" - Archive§r\n\n"
    "§eCraft a Sync Core.§r",
    "Sync:Sync_SyncCore",
    retrieval_task([L("Sync:Sync_SyncCore")]),
    item_rewards([L("lootbags:lootbag", 1, LB_RARE), L("minecraft:iron_ingot", 16)]),
    [6],
)

# OreSpawn travel beat — Sky trees sit in another OreSpawn world
Q_SKY = add(
    433, "OreSpawn: The Sky Trees",
    "§oThe bosses are the headline. The other sky is the commute.§r\n\n"
    "OreSpawn keeps more than one world. The floating islands grow trees that do not exist in the overworld. "
    "Bring back a Sky Tree Log. Crystal is later, and it waits until the Queen is a receipt.\n\n"
    "§7\"I looked down. That was the whole mistake.\" - First Flight§r\n\n"
    "§eRetrieve a Sky Tree Log.§r",
    "OreSpawn:OreSpawn_SkyTreeLog",
    retrieval_task([L("OreSpawn:OreSpawn_SkyTreeLog")]),
    item_rewards([L("OreSpawn:OreSpawn_MagicApple", 4), L("lootbags:lootbag", 1, LB_RARE)]),
    [20], main=1,
)

# McHeli / backpack depth
Q_FUEL = add(
    434, "Keep It in the Air",
    "§oThe airframe is not a trophy. It drinks.§r\n\n"
    "A Bell 47G without fuel is lawn art. Craft fuel, refuel the tank, and take off on purpose this time. "
    "The wrench from the last quest is how you fix the part you hit the barn with.\n\n"
    "§7\"He landed. The gauge said no. The field said yes.\" - Ground Crew§r\n\n"
    "§eCraft McHeli fuel.§r",
    "mcheli:fuel",
    retrieval_task([L("mcheli:fuel")]),
    item_rewards([L("mcheli:fuel", 2), L("mcheli:wrench")]),
    [33],
)

Q_TANK = add(
    435, "Tanks and a Nap",
    "§oThe backpack is a chest until you add plumbing.§r\n\n"
    "A Backpack Tank holds fluid. A Hose is how you fill it, dump it, or drink it. "
    "The sleeping bag from the first page still works. Use it somewhere that is not your bed.\n\n"
    "§7\"He filled the left tank with lava. The hose had opinions.\" - Outfitter§r\n\n"
    "§eCraft a Backpack Tank and a Backpack Hose.§r",
    "adventurebackpack:backpackTank",
    retrieval_task([L("adventurebackpack:backpackTank"), L("adventurebackpack:backpackHose")]),
    item_rewards([L("adventurebackpack:melonJuiceBottle", 4), L("adventurebackpack:blockSleepingBag")]),
    [35],
)


# ---------------------------------------------------------------------------
# Narrative pass — only the pages that fight the current voice
# ---------------------------------------------------------------------------

REWRITE = {
    0: (
        "Welcome to Quest Forge",
        "§6✦ QUEST FORGE ✦§r\n\n"
        "§oThe old chronicle called this CrazyCraft. Same shattered sky. Same titans. "
        "We numbered the disasters in the order you should meet them.§r\n\n"
        "Main chapters are the climb: overworld, Twilight, Witchery, the End, OreSpawn, TragicMC, "
        "then ProjectE as the receipt.\n\n"
        "Side pages are factories, toys, workshops, and a beastiary the overworld was already using. "
        "Secrets do not introduce themselves.\n\n"
        "§eClaim this and start walking.§r",
    ),
    1: (
        "Punch Some Trees",
        "§oWood is the first argument the forest will still lose.§r\n\n"
        "Tools come from here. Shelter comes from here. Standing still is how the night writes your name "
        "on a grave from OpenBlocks.\n\n"
        "§7\"He said stone was good enough. A Mutant Zombie filed the rebuttal.\" - Camp Log§r\n\n"
        "§eGather 16 wood. Then move.§r",
    ),
    2: (
        "Crafting Station",
        "§oA table is not furniture. It is the first machine.§r\n\n"
        "Everything later — presses, altars, reactors — is this block with more opinions. "
        "The old recipes still work. The new ones assume you built this first.\n\n"
        "§7\"Fifty years and the same four logs. The table outlived the theories.\" - Workshop§r\n\n"
        "§eCraft a Crafting Table.§r",
    ),
    3: (
        "Better Tools",
        "§oIron is the first metal that bites the things that live here.§r\n\n"
        "Stone chips. Wood splinters. Iron is what the book means when it says you have started. "
        "You will replace these. You will not skip them.\n\n"
        "§7\"Survivor steel. Not special. Just required.\" - Smith§r\n\n"
        "§eMake iron tools. Wear the time they buy.§r",
    ),
    4: (
        "Armor Up!",
        "§oLeather is a suggestion. Iron is a policy.§r\n\n"
        "Infernal nametags and mutant skeletons do not respect cloth. "
        "Put iron on all four slots. The Beastiary and the jungle can wait until you have a chestplate.\n\n"
        "§7\"She said she would run past them. We buried the boots.\" - Watch§r\n\n"
        "§eCraft a full set of iron armor. Wear it.§r",
    ),
    5: (
        "Diamond Dreams",
        "§oDiamonds are still the key. The basement just got louder.§r\n\n"
        "Enchanting, the Twilight portal, and a dozen recipes you do not have yet all ask for the same crystal. "
        "Below Y-16 the ores change and so does the wildlife.\n\n"
        "§7\"The glow was new. The teeth were not.\" - Last Survey§r\n\n"
        "§eBring back diamonds. Watch the dark.§r",
    ),
    6: (
        "Diamond Gear",
        "§oThis is the admission ticket. Not the ending.§r\n\n"
        "Twilight, Witchery, the End, and everything with a proper name expect diamond. "
        "Below this you are loot. Above it you are allowed to start the climb.\n\n"
        "§7\"Diamond is how the book knows you are serious.\" - Quartermaster§r\n\n"
        "§eWear diamond. Then open the next chapter.§r",
    ),
    7: (
        "Organized Storage",
        "§oChests are a pile with a lid. Drawers are a system.§r\n\n"
        "Storage Drawers keep one item in a face you can read from the door. "
        "You will own thousands of ingots. The floor is not a plan.\n\n"
        "§7\"We found his base. We could not find his iron. That was the compliment.\" - Raider§r\n\n"
        "§eCraft a drawer. Fill it with something you will need twice.§r",
    ),
    8: (
        "Iron Chest",
        "§oThe wooden box is a prototype. Upgrade it before it overflows.§r\n\n"
        "Iron Chests go to gold, diamond, and past that. Same footprint. More honesty.\n\n"
        "§7\"He had sixteen wooden chests. We called it a fire.\" - Inspector§r\n\n"
        "§eCraft an Iron Chest.§r",
    ),
    10: (
        "Witchery: First Brews",
        "§oMutandis is how the garden starts lying.§r\n\n"
        "The Witches' Oven turns logs into Foul Fume. That fume becomes Mutandis. "
        "Mutandis is how vanilla plants become the plants the rest of this chapter spends.\n\n"
        "§7\"It smelled like a mistake. It grew like a plan.\" - Coven Ledger§r\n\n"
        "§eMake Mutandis. Keep the oven fed.§r",
    ),
    18: (
        "Twilight: Ur-Ghast",
        "§oThe Dark Tower has a ceiling, and the ceiling has a face.§r\n\n"
        "The Ur-Ghast runs the tower and a flock that thinks it is weather. "
        "Clear the floors. Do not fight it from the front door.\n\n"
        "§7\"We climbed. It waited. That was the whole strategy, on both sides.\" - Tower Notes§r\n\n"
        "§eKill the Ur-Ghast. Bring back what it drops.§r",
    ),
    19: (
        "Twilight: The Snow Queen",
        "§oThe glacier has a palace. The palace has a landlord.§r\n\n"
        "The Snow Queen is ice magic with a throne. Alpha Yeti Fur is the proof. "
        "This is the last of the numbered Twilight lords on this page.\n\n"
        "§7\"Pretty, until the floor was a suggestion.\" - Alpine Log§r\n\n"
        "§eDefeat the Snow Queen.§r",
    ),
    21: (
        "OreSpawn: Ultimate Gear",
        "§oThe headline bosses do not respect diamond. They respect this.§r\n\n"
        "Ultimate Sword and the rest of the set come from the ugly ores: ruby, uranium, titanium, the ones that glow wrong. "
        "Craft them before Mobzilla. Crafting them after is a eulogy.\n\n"
        "§7\"We had diamond. We had a plan. We did not have Ultimate.\" - After-Action§r\n\n"
        "§eCraft the Ultimate Sword.§r",
    ),
    22: (
        "OreSpawn: MOBZILLA!",
        "§oIt does not hunt. It occupies.§r\n\n"
        "Mobzilla is the first of the three receipts that unlock ProjectE. "
        "Armies are insects. Diamond is a joke. Ultimate gear is the minimum.\n\n"
        "§7\"Fifty soldiers. Three came back. None wanted to talk about the shadow.\" - Archive§r\n\n"
        "§eKill Mobzilla. Bring the scales. The Transmutation Table is listening.§r",
    ),
    23: (
        "OreSpawn: THE KING",
        "§oThe King is a weather system with a crown.§r\n\n"
        "Treat him like the chapter tab said: weather you can stab. "
        "The Royal Guardian Sword is the proof this pack uses, because the King himself does not drop a tidy souvenir.\n\n"
        "§7\"I have seen gods bleed. This one made me put the sentence down.\" - Champion§r\n\n"
        "§eSurvive The King. Hold the Royal Guardian Sword.§r",
    ),
    24: (
        "OreSpawn: THE QUEEN",
        "§oAfter the King. That is the whole warning.§r\n\n"
        "The Queen is the last titan on the spine. Red Matter waits on her scale. "
        "If you are here early, you are lost. If you are here on purpose, you already know.\n\n"
        "§7\"You think the King was the end. The book does not.\" - Final Testament§r\n\n"
        "§eKill The Queen. Bring a Queen Scale.§r",
    ),
    28: (
        "Mutant Creatures: The Hunt",
        "§oVanilla, with the safety filed off.§r\n\n"
        "A Mutant Skeleton is a skeleton that learned extra rules. Unique attacks. Too much health. "
        "Hunt one. Do not assume the bow range you remember.\n\n"
        "§7\"It shot the wall. The wall became the problem.\" - Range Report§r\n\n"
        "§eBring back what it drops.§r",
    ),
    29: (
        "Mutant Creatures: Hulk Hammer",
        "§oThe Mutant Zombie leaves a tool. The tool leaves a crater.§r\n\n"
        "The Hulk Hammer slams the ground and sends things away. Including you, if you swing like a tourist.\n\n"
        "§7\"We asked for a weapon. We got urban renewal.\" - Quartermaster§r\n\n"
        "§eObtain the Hulk Hammer.§r",
    ),
    30: (
        "MrCrayfish's Furniture",
        "§oA table that is not a crafting table. Radical.§r\n\n"
        "Crayfish is chairs, counters, and the difference between a hole and a house. "
        "The climb does not care. You will.\n\n"
        "§7\"We came back from Twilight. The base still looked like a crime.\" - Tenant§r\n\n"
        "§eCraft a piece of furniture. Sit down on purpose.§r",
    ),
    31: (
        "Decocraft Decorations",
        "§oClay that pretends to be a life.§r\n\n"
        "Decocraft is hundreds of props. Start with the clay. The kitchen can wait until the walls exist.\n\n"
        "§7\"He decorated the bunker. The bunker still exploded. It exploded nicer.\" - Inspector§r\n\n"
        "§eCraft Decocraft Clay.§r",
    ),
    32: (
        "Legends: Become a Hero",
        "§oThe Hall of Heroes is a side tab. This is the door.§r\n\n"
        "Suits come off the Suit Assembly Unit. Stark's toys come off the Stark Workbench. "
        "Captain America's chestplate is a fine first proof. Batman does not unlock Superman.\n\n"
        "§7\"He put the shield on. The Warg did not vote.\" - Recruiter§r\n\n"
        "§eCraft a Captain America chestplate. The rest of the closet is optional.§r",
    ),
    34: (
        "ProjectE: Red Matter",
        "§4[UNLOCKED BY THE QUEEN]§r\n\n"
        "§oThe last alchemical step. Not a victory lap.§r\n\n"
        "Red Matter is gated on a Queen Scale. That is the receipt. "
        "The recipe is in CraftTweaker. The book will not pretend this is a hobby.\n\n"
        "§7\"You wanted equivalent exchange. She wanted a fight. Both of you got one.\" - Alchemist§r\n\n"
        "§eCraft Red Matter. Then decide whether you are still playing.§r",
    ),
    35: (
        "Adventure Awaits!",
        "§oA chest you wear, with opinions.§r\n\n"
        "Adventure Backpacks hold items and fluids. Some skins do extra work — Bat for night, Squid for gills. "
        "Craft the first one. Tanks and a hose are the next page.\n\n"
        "§7\"He put lava in the left tank. We stopped lending him backpacks.\" - Outfitter§r\n\n"
        "§eCraft an Adventure Backpack.§r",
    ),
    36: (
        "Set Sail!",
        "§oBuild a hull. Add a helm. Discover that water was a suggestion.§r\n\n"
        "Archimedes' Ships turns a pile of blocks into a vessel. Airships count. "
        "The compile button is how you find out what you forgot to attach.\n\n"
        "§7\"It floated. The kitchen did not.\" - Captain§r\n\n"
        "§eBuild a ship with a helm.§r",
    ),
    37: (
        "Soul Collector",
        "§oA shard that learns a face, then prints it.§r\n\n"
        "Soul Shards fill by killing the same mob. Higher tiers become a spawner you own. "
        "This is how farms stop being a prayer.\n\n"
        "§7\"We named the shard after the first zombie. It did not care.\" - Rancher§r\n\n"
        "§eCraft a Soul Shard and start the count.§r",
    ),
    40: (
        "Railcraft: Locomotive Engineer",
        "§oA boiler that moves, and takes the rest of the train with it.§r\n\n"
        "The Steam Locomotive is the end of this side page. Carts, tracks, and a whistle you will regret at night.\n\n"
        "§7\"Fastest way to travel. Fastest way to meet a cow.\" - Conductor§r\n\n"
        "§eBuild a Steam Locomotive.§r",
    ),
    41: (
        "Security First",
        "§oA lock that is not a wooden door and a sign that says please.§r\n\n"
        "SecurityCraft starts with a keypad. The code is the whole joke until someone guesses it. "
        "Use it on the room you actually care about.\n\n"
        "§7\"We changed the code. We did not change the sticky note.\" - Guard§r\n\n"
        "§eCraft a Keypad.§r",
    ),
    42: (
        "Laser Security",
        "§oA red line that means the room has opinions.§r\n\n"
        "Laser Blocks make a tripwire you can see. Wire them to alarms, doors, or something unkind.\n\n"
        "§7\"The cat learned the pattern. The raiders did not.\" - Night Shift§r\n\n"
        "§eCraft Laser Blocks.§r",
    ),
    43: (
        "Creature of the Night",
        "§oWitchery's vampire path is a door that only opens outward.§r\n\n"
        "Blood, night, and a list of powers that will get you killed in daylight if you skip the reading. "
        "Finish the Old Ways first. This chapter is still mid-book.\n\n"
        "§7\"Immortal is a strong word for thirsty.\" - Coven Elder§r\n\n"
        "§eStart the vampire path. Bring the kit the previous page made.§r",
    ),
    48: (
        "Pandora's Box",
        "§cThis is a bad idea with a lid.§r\n\n"
        "Pandora's Box rolls the table. Diamonds. Bosses. Both. "
        "The Danger Zone tab exists so this does not live on the spine.\n\n"
        "§7\"I felt lucky. The box felt luckier.\" - Volunteer§r\n\n"
        "§eOpen one if you must. Do it away from the base.§r",
    ),
    51: (
        "Master Builder: Slopes",
        "§oStairs were a compromise. Carpenter's is the actual angle.§r\n\n"
        "Carpenter's Blocks take the texture of whatever you apply. Roofs stop looking like staircases.\n\n"
        "§7\"We had a house. Then we had a shape.\" - Mason§r\n\n"
        "§eCraft a Carpenter's slope.§r",
    ),
    52: (
        "BiblioCraft Library",
        "§oShelves that show the book. Stands that show the armor.§r\n\n"
        "BiblioCraft is how a room admits it is finished. The climb does not require this. Pride does.\n\n"
        "§7\"He built a library. He still could not read the Witchery tooltip.\" - Archivist§r\n\n"
        "§eCraft a BiblioCraft shelf or stand.§r",
    ),
    53: (
        "Trophy Hunter",
        "§oKill it. Bottle the outline. Put it where guests can fail to be polite.§r\n\n"
        "A Statue Core captures a mob you have already dealt with. This is not combat. This is filing.\n\n"
        "§7\"The Hydra looks smaller in plaster. That is the point.\" - Curator§r\n\n"
        "§eCraft a Statue Core.§r",
    ),
    61: (
        "Loot Bag Basics",
        "§oMobs drop bags. Bags drop excuses to keep fighting.§r\n\n"
        "Common, Uncommon, Rare, Epic, Legend. The color is the only honest part of the tooltip.\n\n"
        "§7\"I opened a Common. I got string. I opened another Common. I got hope.\" - Auditor§r\n\n"
        "§eOpen a Loot Bag.§r",
    ),
    63: (
        "§6★ PACK MASTER ★",
        "§6✦ THE CLIMB, FILED §r\n\n"
        "§oYou numbered the disasters. Then you walked them.§r\n\n"
        "Twilight, the titans, the rest of the spine. This page only wants the three OreSpawn receipts in bulk. "
        "It is a closet with standards, not a new boss.\n\n"
        "§7\"The chronicle is a list. You are the last line.\" - Keeper§r\n\n"
        "§eBring stacks of Mobzilla scale blocks, Royal Guardian proof, and Queen Scales.§r",
    ),
}


LINE_DESCS = {
    "Chapter 1: Humble Beginnings":
        "§o\"The numbered chapters are the climb. Everything else is how you stay alive on it.\"§r\n\n"
        "Wood, iron, diamonds. The overworld still kills people who skip this page. "
        "The right column is the extra HUD: Infernal nametags and a Level Up class. "
        "Side tabs are hobbies. The Beastiary is not a hobby. Secrets do not introduce themselves.",
    "Chapter 2: Base Building":
        "§o\"A fortress is a filing system that can survive a raid.\"§r\n\n"
        "Drawers, iron chests, a handle that picks the whole box up, a room you can put in a block, "
        "an elevator, and a chest that exists in two places. Furniture lives on the Workshop tab — "
        "this page is where loot stops living on the floor.",
    "Chapter 7: OreSpawn Boss Rush":
        "§o\"They came from beyond the void. They rule now.\"§r\n\n"
        "This is late. Twilight, Witchery, and the End were the warm-up. "
        "Sky trees are a commute. Mobzilla, the King, and the Queen are why ProjectE is locked in a cupboard. "
        "Treat them like weather you can stab.",
    "Side: Gadgets and Glory":
        "§o\"In chaos, humanity found wonders. And several OSHA violations.\"§r\n\n"
        "Portal Guns, Gravity Guns, shields for the off-hand, mutant trophies, a spare body, "
        "superhero kits, helicopters that drink fuel, and a snack that turns you into a particle effect. "
        "Pets have their own Workshop tab now.",
    "Side: Exploration and Security":
        "§o\"Leave the base. Come back. Ideally still shaped like yourself.\"§r\n\n"
        "Backpacks with plumbing, a glider, ships, soul shards, and a lock on the door. "
        "SecurityCraft is how you stop the next raid from being a tour. "
        "Railcraft moved to its own Side tab — it grew out of this page.",
    "Side: Danger Zone":
        "§cDANGER AHEAD§r\n\n"
        "Doctor Who's box, the angels that win if you blink, a box that should have stayed shut, "
        "and a jungle that keeps its own gods. HEE and TragicMC graduated to numbered chapters. "
        "This page is the remaining bad ideas.",
    "Side: War Machines":
        "§o\"The factory that kills people is still a factory.\"§r\n\n"
        "HBM and ICBM are optional wars. They are not the story spine and they are not how you skip Mobzilla.\n\n"
        "Geiger. Press. Assembler. Oil. Diesel. A small reactor. The Uzi is a side arm. "
        "The silo is a secret, and the book will not hand you a nuke.",
    "★ Secrets ★":
        "§oIf this page is blank, that is working.§r\n\n"
        "Nothing here introduces itself. Retrieval still counts in your pockets. "
        "When a title appears, you already knew why.\n\n"
        "The numbered chapters are the climb. This closet is the receipts "
        "you were not told to keep.",
}


def apply_rewrites(qdb):
    n = 0
    for qid, (name, desc) in REWRITE.items():
        key = "%d:10" % qid
        if key not in qdb:
            raise SystemExit("rewrite target missing Q%d" % qid)
        bq = qdb[key]["properties:10"]["betterquesting:10"]
        if bq["name:8"] != name and qid != 63:
            # PACK MASTER name has section codes; allow
            pass
        bq["desc:8"] = desc
        n += 1
    return n


def apply_line_descs(lines):
    n = 0
    for line in lines.values():
        bq = line["properties:10"]["betterquesting:10"]
        name = bq["name:8"]
        if name in LINE_DESCS:
            bq["desc:8"] = LINE_DESCS[name]
            n += 1
    return n


def main():
    if not os.path.isfile(SRC):
        raise SystemExit("missing " + SRC)

    backup = os.path.join(HERE, "DefaultQuests.pre-expand-%s.json" % datetime.now().strftime("%Y%m%d-%H%M%S"))
    shutil.copy2(SRC, backup)
    print("backup", backup)

    with open(SRC, "r", encoding="utf-8") as f:
        data = json.load(f)

    qdb = data["questDatabase:9"]
    lines = data["questLines:9"]

    used = {q["questID:3"] for q in qdb.values()}
    for q in NEW:
        if q["questID:3"] in used:
            raise SystemExit("id collision %s" % q["questID:3"])
        qdb["%d:10" % q["questID:3"]] = q

    rewrites = apply_rewrites(qdb)
    line_rewrites = apply_line_descs(lines)

    # New Beastiary tab
    layout = [
        (Q_GAZER, 0, 0, 24),
        (Q_TREAT, 48, 0, 24),
        (Q_STONE, 0, 48, 24),
        (Q_KEY, 48, 48, 24),
        (Q_CUBE, 0, 96, 24),
        (Q_RAHO, 48, 96, 32),
    ]
    qmap = {}
    for i, (qid, x, y, size) in enumerate(layout):
        qmap["%d:10" % i] = {
            "sizeX:3": size, "x:3": x, "y:3": y, "id:3": qid, "sizeY:3": size,
        }
    lines["19:10"] = {
        "quests:9": qmap,
        "lineID:3": 19,
        "properties:10": {
            "betterquesting:10": {
                "visibility:8": "ALWAYS",
                "name:8": "Side: The Beastiary",
                "icon:10": stack("lycanitesmobs:soulgazer"),
                "bg_image:8": "",
                "bg_size:3": 256,
                "desc:8":
                    "§o\"The overworld already had a second book. This is it.\"§r\n\n"
                    "Lycanites is not a stamp collection. Soulgazer, treat, soulstone, key, cube, Rahovart. "
                    "That is the whole campaign. Asmodeus and Amalgalich are not in this build.\n\n"
                    "Open the Beastiary from Controls. Bind the key. The mobs will not wait.",
            }
        },
        "order:3": 10,
    }

    _, ch1 = find_line(lines, "Chapter 1: Humble Beginnings")
    place(ch1, Q_INF, 48, 192, 24)
    place(ch1, Q_LVL, 48, 240, 24)

    _, ch2 = find_line(lines, "Chapter 2: Base Building")
    place(ch2, Q_CM, 0, 96, 24)
    place(ch2, Q_ELEV, 48, 96, 24)
    place(ch2, Q_ENDER, 0, 144, 24)

    _, os_line = find_line(lines, "Chapter 7: OreSpawn Boss Rush")
    place(os_line, Q_SKY, 96, 0, 24)

    _, gadgets = find_line(lines, "Side: Gadgets and Glory")
    place(gadgets, Q_SYNC, 0, 192, 24)
    place(gadgets, Q_FUEL, 48, 192, 24)

    _, explore = find_line(lines, "Side: Exploration and Security")
    place(explore, Q_GLIDE, 0, 144, 24)
    place(explore, Q_TANK, 48, 144, 24)

    _, danger = find_line(lines, "Side: Danger Zone")
    place(danger, Q_SAPPH, 48, 0, 24)
    place(danger, Q_BOOK, 48, 48, 24)

    _, war = find_line(lines, "Side: War Machines")
    place(war, Q_ASM, 0, 96, 24)
    place(war, Q_DET, 48, 96, 24)
    place(war, Q_OIL, 0, 144, 24)
    place(war, Q_DIESEL, 48, 144, 24)
    place(war, Q_RX, 96, 144, 24)

    _, secrets = find_line(lines, "★ Secrets ★")
    place(secrets, Q_FAT, 48, 48, 32)

    data["questSettings:10"]["betterquesting:10"]["editMode:1"] = 0

    tmp = SRC + ".tmp-expand"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    with open(tmp, "r", encoding="utf-8") as f:
        check = json.load(f)
    os.replace(tmp, SRC)

    qids = [q["questID:3"] for q in NEW]
    print("wrote", SRC)
    print("new_quests", len(NEW), "ids", min(qids), "-", max(qids))
    print("rewrites", rewrites, "line_descs", line_rewrites)
    print("total_quests", len(check["questDatabase:9"]))
    print("total_lines", len(check["questLines:9"]))

    if os.path.isfile(LIVE):
        shutil.copy2(SRC, LIVE)
        print("synced live", LIVE)
    else:
        print("live instance missing, skipped copy")


if __name__ == "__main__":
    main()
