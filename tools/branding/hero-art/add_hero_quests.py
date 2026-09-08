# -*- coding: utf-8 -*-
"""Add Side: Hall of Heroes BetterQuesting lines for Legends / Superheroes Unlimited."""
from __future__ import print_function
import json
import os
import shutil
from datetime import datetime

SRC = r"C:\Users\a2dsu\AppData\Roaming\.crazycraft4\config\betterquesting\DefaultQuests.json"
BACKUP_DIR = r"C:\Users\a2dsu\OneDrive\Desktop\QuestForge-Work\_heroes-20260904"
CHAPTER_ID = 18
START_QID = 300

# Lootbag damage already used in DefaultQuests / Lootbags_BagConfig.cfg
LB_COMMON, LB_UNCOMMON, LB_RARE, LB_EPIC, LB_LEGEND = 0, 1, 2, 3, 4

def L(id_, count=1, dmg=0):
    return (id_, count, dmg)

def suit(name, piece):
    return "legends:%s.%s" % (name, piece)


# Character registry names from getName() + ArmorType.name (helmet/chestplate/leggings/boots).
# no_helmet: I3SlotSuit or confirmed missing default helmet texture (skip helmet IDs).
# All of these are SAU-craftable except Iron Man family (Stark Workbench) and War Machine.
CHARS = [
    # DC
    dict(name="superman", display="Superman", no_helmet=True, major=True,
         early=[L("legends:kryptonianMetal", 4), L("legends:supermanLogo"), L("lootbags:lootbag", 1, LB_UNCOMMON)],
         late=[L("legends:kryptonianAlloy", 2), L("legends:kryptonianSyringe"), L("lootbags:lootbag", 1, LB_EPIC)],
         d1="The cape came off the rack smelling like cornfields and ozone.",
         d2="Chest, legs, boots. No cowl. The S does the talking."),
    dict(name="supergirl", display="Supergirl", no_helmet=False, major=False,
         early=[L("legends:kryptonianMetal", 2), L("lootbags:lootbag", 1, LB_UNCOMMON)],
         late=[L("legends:kryptonianAlloy"), L("lootbags:lootbag", 1, LB_RARE)],
         d1="She borrowed the crest. She did not borrow the attitude.",
         d2="Full set. National City can wait one more minute."),
    dict(name="generalzod", display="General Zod", no_helmet=True, major=False,
         early=[L("legends:kryptonianMetal", 2), L("lootbags:lootbag", 1, LB_UNCOMMON)],
         late=[L("legends:kryptoniteSyringe"), L("lootbags:lootbag", 1, LB_RARE)],
         d1="Kneel is a suggestion until the armor is on.",
         d2="Kryptonian parade dress. Earth is the parade."),
    dict(name="batman", display="Batman", no_helmet=False, major=True,
         early=[L("legends:wayneTech", 4), L("legends:batmanLogo"), L("lootbags:lootbag", 1, LB_UNCOMMON)],
         late=[L("legends:batarang", 8), L("legends:grapplingHook"), L("legends:batbelt"), L("lootbags:lootbag", 1, LB_EPIC)],
         d1="The cowl hit the table. Gotham did not get quieter.",
         d2="Four pieces and a belt that weighs more than the alibi."),
    dict(name="wonderwoman", display="Wonder Woman", no_helmet=False, major=True,
         early=[L("legends:wonderWomanLogo"), L("lootbags:lootbag", 1, LB_UNCOMMON)],
         late=[L("legends:lasso"), L("legends:amazonianWeapons"), L("lootbags:lootbag", 1, LB_EPIC)],
         d1="The tiara is not jewelry. It is a warning.",
         d2="Lasso, blades, and the rest of the armor. Themyscira would approve."),
    dict(name="flash", display="Flash", no_helmet=False, major=True,
         early=[L("legends:flashLogo"), L("legends:lightningIngot", 4), L("lootbags:lootbag", 1, LB_UNCOMMON)],
         late=[L("legends:flashRing"), L("lootbags:lootbag", 1, LB_EPIC)],
         d1="The lightning hit the fabric first. Then the rest of Central City.",
         d2="Full scarlet. The ring is how you get dressed in a hurry."),
    dict(name="kidflash", display="Kid Flash", no_helmet=False, major=False,
         early=[L("legends:kidFlashLogo"), L("lootbags:lootbag", 1, LB_COMMON)],
         late=[L("legends:lightningIngot", 4), L("lootbags:lootbag", 1, LB_RARE)],
         d1="Yellow is not a junior color when you outrun the lecture.",
         d2="Whole kit. Try not to vibrate through the floor."),
    dict(name="flash_west", display="Flash (Wally West)", no_helmet=False, major=False,
         early=[L("legends:lightningIngot", 2), L("lootbags:lootbag", 1, LB_UNCOMMON)],
         late=[L("legends:flashLogo"), L("lootbags:lootbag", 1, LB_RARE)],
         d1="He already knew the route. The suit just kept up.",
         d2="West's colors, all four pieces."),
    dict(name="flash_garrick", display="Flash (Jay Garrick)", no_helmet=False, major=False,
         early=[L("legends:lightningIngot", 2), L("lootbags:lootbag", 1, LB_UNCOMMON)],
         late=[L("legends:flashLogo"), L("lootbags:lootbag", 1, LB_RARE)],
         d1="The helmet has wings. The man does not need them.",
         d2="Old-school scarlet. Still faster than the rumor."),
    dict(name="reverseflash", display="Reverse-Flash", no_helmet=False, major=False,
         early=[L("legends:reverseFlashLogo"), L("lootbags:lootbag", 1, LB_UNCOMMON)],
         late=[L("legends:reverseFlashRing"), L("lootbags:lootbag", 1, LB_RARE)],
         d1="Yellow that wants to be a crime scene.",
         d2="Suit and ring. Do not stand in front of him."),
    dict(name="zoom", display="Zoom", no_helmet=False, major=False,
         early=[L("legends:zoomLogo"), L("lootbags:lootbag", 1, LB_UNCOMMON)],
         late=[L("legends:lightningIngot", 4), L("lootbags:lootbag", 1, LB_RARE)],
         d1="The breath sounds wrong. The suit is supposed to.",
         d2="Full predator kit. Central City should lock its doors."),
    dict(name="shazam", display="Shazam", no_helmet=False, major=False,
         early=[L("legends:shazamLogo"), L("lootbags:lootbag", 1, LB_UNCOMMON)],
         late=[L("legends:lightningIngot", 6), L("lootbags:lootbag", 1, LB_RARE)],
         d1="Say the word. The lightning brings the tailoring.",
         d2="Cape, crest, the whole thunderclap."),
    dict(name="blackadam", display="Black Adam", no_helmet=True, major=False,
         early=[L("legends:shazamLogo"), L("lootbags:lootbag", 1, LB_UNCOMMON)],
         late=[L("legends:kryptonianAlloy"), L("lootbags:lootbag", 1, LB_RARE)],
         d1="Kahndaq does not issue a helmet. It issues an ultimatum.",
         d2="Chest, legs, boots. The lightning is optional. The temper is not."),
    dict(name="martianmanhunter", display="Martian Manhunter", no_helmet=False, major=False,
         early=[L("legends:techAlien", 2), L("lootbags:lootbag", 1, LB_UNCOMMON)],
         late=[L("legends:techAlien", 4), L("lootbags:lootbag", 1, LB_RARE)],
         d1="He wore a face that would not scare the neighbors. The suit is honest.",
         d2="Full Martian dress. Cookies later."),
    dict(name="greenarrow", display="Green Arrow", no_helmet=False, major=False,
         early=[L("legends:wayneTech", 2), L("lootbags:lootbag", 1, LB_UNCOMMON)],
         late=[L("legends:greenArrowBow"), L("legends:kryptoniteArrow", 4), L("lootbags:lootbag", 1, LB_RARE)],
         d1="Hood up. The quiver is the rest of the personality.",
         d2="Suit and a real bow. Star City can stop calling him the other one."),
    dict(name="joker", display="Joker", no_helmet=False, major=False,
         early=[L("legends:jokerCard", 8), L("lootbags:lootbag", 1, LB_UNCOMMON)],
         late=[L("legends:jokerGun"), L("legends:jokerCard", 16), L("lootbags:lootbag", 1, LB_RARE)],
         d1="Purple is a threat if you wear it like a punchline.",
         d2="The whole joke. The gun is the rimshot."),
    dict(name="nightwing", display="Nightwing", no_helmet=False, major=False,
         early=[L("legends:robinLogo"), L("lootbags:lootbag", 1, LB_UNCOMMON)],
         late=[L("legends:escrimaSticks"), L("lootbags:lootbag", 1, LB_RARE)],
         d1="He left the R on a grave and kept the acrobatics.",
         d2="Blue bird, full kit, sticks that hum."),
    dict(name="redhood", display="Red Hood", no_helmet=False, major=False,
         early=[L("legends:robinLogo"), L("lootbags:lootbag", 1, LB_UNCOMMON)],
         late=[L("legends:pistols"), L("lootbags:lootbag", 1, LB_RARE)],
         d1="The helmet is the argument. The rest is the vote.",
         d2="Full hood. Gotham can file a complaint."),
    dict(name="redrobin", display="Red Robin", no_helmet=False, major=False,
         early=[L("legends:robinLogo"), L("lootbags:lootbag", 1, LB_UNCOMMON)],
         late=[L("legends:rrDisc", 8), L("lootbags:lootbag", 1, LB_RARE)],
         d1="The R got sharper. So did the plan.",
         d2="Suit and a pocket full of discs."),
    dict(name="robin_grayson", display="Robin (1st)", no_helmet=False, major=False,
         early=[L("legends:robinLogo"), L("lootbags:lootbag", 1, LB_COMMON)],
         late=[L("legends:throwingBird", 8), L("lootbags:lootbag", 1, LB_UNCOMMON)],
         d1="First R. The circus never really left.",
         d2="The original colors, complete."),
    dict(name="robin_todd", display="Robin (2nd)", no_helmet=False, major=False,
         early=[L("legends:robinLogo"), L("lootbags:lootbag", 1, LB_COMMON)],
         late=[L("legends:rShuriken", 8), L("lootbags:lootbag", 1, LB_UNCOMMON)],
         d1="Second R. He hit harder than the lesson plan.",
         d2="Full set. The alley remembers."),
    dict(name="robin_drake", display="Robin (3rd)", no_helmet=False, major=False,
         early=[L("legends:robinLogo"), L("lootbags:lootbag", 1, LB_COMMON)],
         late=[L("legends:boStaff"), L("lootbags:lootbag", 1, LB_UNCOMMON)],
         d1="Third R. He brought a staff and a better map.",
         d2="Suit and staff. Detectives dress like this."),
    dict(name="robin_brown", display="Robin (4th)", no_helmet=False, major=False,
         early=[L("legends:robinLogo"), L("lootbags:lootbag", 1, LB_COMMON)],
         late=[L("legends:rShuriken", 8), L("lootbags:lootbag", 1, LB_UNCOMMON)],
         d1="Fourth R. She did not ask permission.",
         d2="The whole uniform. The cave can adjust."),
    dict(name="robin_wayne", display="Robin (5th)", no_helmet=False, major=False,
         early=[L("legends:robinLogo"), L("lootbags:lootbag", 1, LB_COMMON)],
         late=[L("legends:throwingBird", 8), L("lootbags:lootbag", 1, LB_UNCOMMON)],
         d1="Fifth R. Blood does not make the cape lighter.",
         d2="Wayne colors. Still a Robin."),
    dict(name="captaincold", display="Captain Cold", no_helmet=False, major=False,
         early=[L("legends:tech", 4), L("lootbags:lootbag", 1, LB_UNCOMMON)],
         late=[L("legends:coldGun"), L("lootbags:lootbag", 1, LB_RARE)],
         d1="The goggles frost first. Then the room.",
         d2="Parka, gun, the rest of the cold."),
    dict(name="heatwave", display="Heat Wave", no_helmet=False, major=False,
         early=[L("legends:tech", 4), L("lootbags:lootbag", 1, LB_UNCOMMON)],
         late=[L("legends:heatGun"), L("lootbags:lootbag", 1, LB_RARE)],
         d1="Asbestos is a personality if you commit.",
         d2="Full burn kit and a gun that does not do nuance."),
    dict(name="turtle", display="Turtle", no_helmet=False, major=False,
         early=[L("legends:tech", 2), L("lootbags:lootbag", 1, LB_COMMON)],
         late=[L("legends:techHigh"), L("lootbags:lootbag", 1, LB_UNCOMMON)],
         d1="He slows the room down. The shell is just honest.",
         d2="Whole suit. The Flash can wait."),
    dict(name="scarecrow", display="Scarecrow", no_helmet=False, major=False,
         early=[L("legends:gasPellet", 4), L("lootbags:lootbag", 1, LB_UNCOMMON)],
         late=[L("legends:gasPellet", 8), L("lootbags:lootbag", 1, LB_RARE)],
         d1="The mask is the thesis. Fear is the bibliography.",
         d2="Full harvest. Do not breathe in."),
    dict(name="blackcanary", display="Black Canary", no_helmet=False, major=False,
         early=[L("legends:tech", 2), L("lootbags:lootbag", 1, LB_UNCOMMON)],
         late=[L("legends:escrimaSticks"), L("lootbags:lootbag", 1, LB_RARE)],
         d1="Leather first. The scream comes standard.",
         d2="Jacket to boots. Star City should wear earplugs."),
    # Marvel
    dict(name="captainamerica", display="Captain America", no_helmet=False, major=True,
         early=[L("legends:captainAmericaLogo"), L("legends:clothStar"), L("lootbags:lootbag", 1, LB_UNCOMMON)],
         late=[L("legends:capShield"), L("legends:vibranium", 2), L("lootbags:lootbag", 1, LB_EPIC)],
         d1="The A on the helmet is a promise. Keep it.",
         d2="Stars, stripes, and a shield that does not bounce opinions."),
    dict(name="thor", display="Thor", no_helmet=False, major=True,
         early=[L("legends:asgardianSteel", 4), L("lootbags:lootbag", 1, LB_UNCOMMON)],
         late=[L("legends:mjolnir"), L("legends:asgardianForging"), L("lootbags:lootbag", 1, LB_EPIC)],
         d1="Asgardian steel sits heavier than pride.",
         d2="Full armor and a hammer that argues with weather."),
    dict(name="hulk", display="Hulk", no_helmet=False, major=True,
         early=[L("legends:mutantGene", 2), L("lootbags:lootbag", 1, LB_UNCOMMON)],
         late=[L("legends:mutantGene", 4), L("lootbags:lootbag", 1, LB_EPIC)],
         d1="Purple pants are a public service.",
         d2="The whole smash wardrobe. Do not ask him to smile."),
    dict(name="redhulk", display="Red Hulk", no_helmet=False, major=False,
         early=[L("legends:mutantGene", 2), L("lootbags:lootbag", 1, LB_UNCOMMON)],
         late=[L("legends:mutantGene", 3), L("lootbags:lootbag", 1, LB_RARE)],
         d1="Red is what happens when the army gets ideas.",
         d2="Full heat. Stay off the asphalt."),
    dict(name="abomination", display="Abomination", no_helmet=False, major=False,
         early=[L("legends:mutantGene", 2), L("lootbags:lootbag", 1, LB_UNCOMMON)],
         late=[L("legends:mutantGene", 3), L("lootbags:lootbag", 1, LB_RARE)],
         d1="He asked for more. The suit is the receipt.",
         d2="The whole monster. Harlem still has opinions."),
    dict(name="antman", display="Ant-Man", no_helmet=False, major=False,
         early=[L("legends:pymParticle", 2), L("lootbags:lootbag", 1, LB_UNCOMMON)],
         late=[L("legends:pymParticle", 4), L("legends:regulator"), L("lootbags:lootbag", 1, LB_RARE)],
         d1="The helmet clicks. The ants already voted.",
         d2="Full Pym kit. Watch the pockets."),
    dict(name="wasp", display="Wasp", no_helmet=False, major=False,
         early=[L("legends:pymParticle", 2), L("lootbags:lootbag", 1, LB_UNCOMMON)],
         late=[L("legends:pymParticle", 4), L("lootbags:lootbag", 1, LB_RARE)],
         d1="Wings first. The sting is a footnote.",
         d2="Complete Wasp. Do not swat."),
    dict(name="blackpanther", display="Black Panther", no_helmet=False, major=True,
         early=[L("legends:vibranium", 2), L("legends:wakandanMap"), L("lootbags:lootbag", 1, LB_UNCOMMON)],
         late=[L("legends:pantherNecklace"), L("legends:vibranium", 4), L("lootbags:lootbag", 1, LB_EPIC)],
         d1="The mask is a border. Vibranium is the law inside it.",
         d2="Full habit and the necklace that remembers kings."),
    dict(name="spiderman", display="Spider-Man", no_helmet=False, major=True,
         early=[L("legends:spiderManLogo"), L("legends:radioactiveFabric", 2), L("lootbags:lootbag", 1, LB_UNCOMMON)],
         late=[L("legends:webShooters"), L("legends:webCartridge", 8), L("lootbags:lootbag", 1, LB_EPIC)],
         d1="The eyes are wider than the rent.",
         d2="Red and blue, shooters loaded. Queens can exhale."),
    dict(name="spiderman2099", display="Spider-Man 2099", no_helmet=False, major=False,
         early=[L("legends:radioactiveFabric"), L("lootbags:lootbag", 1, LB_UNCOMMON)],
         late=[L("legends:webCartridge", 8), L("lootbags:lootbag", 1, LB_RARE)],
         d1="The future sent a suit. It has claws in the fine print.",
         d2="Full 2099. Watch the talons."),
    dict(name="symbiotespiderman", display="Symbiote Spider-Man", no_helmet=False, major=False,
         early=[L("legends:symbiote"), L("lootbags:lootbag", 1, LB_UNCOMMON)],
         late=[L("legends:webShooters"), L("legends:symbiote"), L("lootbags:lootbag", 1, LB_RARE)],
         d1="Black looks good until it answers back.",
         d2="The other costume. Keep a church bell handy."),
    dict(name="ironspider", display="Iron Spider", no_helmet=False, major=False,
         early=[L("legends:starkTech", 2), L("lootbags:lootbag", 1, LB_UNCOMMON)],
         late=[L("legends:repulsorType1"), L("legends:webCartridge", 8), L("lootbags:lootbag", 1, LB_RARE)],
         d1="Stark left legs on the back. That is either generous or a threat.",
         d2="Gold-red webbing. Assemble it on the Stark bench."),
    dict(name="vision", display="Vision", no_helmet=False, major=False,
         early=[L("legends:unstableMolecule", 2), L("lootbags:lootbag", 1, LB_UNCOMMON)],
         late=[L("legends:unstableMolecule", 4), L("legends:techHigh", 2), L("lootbags:lootbag", 1, LB_RARE)],
         d1="He put on a face so the room would stay polite.",
         d2="The synthezoid wardrobe, complete."),
    dict(name="wolverine", display="Wolverine", no_helmet=False, major=False,
         early=[L("legends:adamantium", 2), L("lootbags:lootbag", 1, LB_UNCOMMON)],
         late=[L("legends:adamantium", 4), L("legends:liquidAdamantium"), L("lootbags:lootbag", 1, LB_RARE)],
         d1="Yellow is a dare. The claws are the RSVP.",
         d2="Full mask. The bath already happened."),
    dict(name="deadpool", display="Deadpool", no_helmet=False, major=False,
         early=[L("legends:katanas"), L("lootbags:lootbag", 1, LB_UNCOMMON)],
         late=[L("legends:chimichanga", 8), L("legends:pistols"), L("lootbags:lootbag", 1, LB_RARE)],
         d1="The mask is so you do not have to watch the healing.",
         d2="Suit, katanas, and a snack that should not be this powerful."),
    dict(name="daredevil", display="Daredevil", no_helmet=False, major=False,
         early=[L("legends:tech", 2), L("lootbags:lootbag", 1, LB_UNCOMMON)],
         late=[L("legends:billyClub"), L("lootbags:lootbag", 1, LB_RARE)],
         d1="Red is how Hell's Kitchen stays honest.",
         d2="Horns, club, the rest of the vow."),
    dict(name="venom", display="Venom", no_helmet=False, major=False,
         early=[L("legends:symbiote"), L("lootbags:lootbag", 1, LB_UNCOMMON)],
         late=[L("legends:symbiote"), L("legends:radioactiveFabric", 2), L("lootbags:lootbag", 1, LB_RARE)],
         d1="We are wearing the suit. The suit is wearing us.",
         d2="Full symbiote. Bring a chocolate backup."),
    dict(name="warmachine_mark1", display="War Machine (Mark 1)", no_helmet=False, major=False,
         early=[L("legends:starkTech", 2), L("lootbags:lootbag", 1, LB_UNCOMMON)],
         late=[L("legends:repulsorType1"), L("legends:miniArcReactor"), L("lootbags:lootbag", 1, LB_EPIC)],
         d1="Rhodey painted it like a threat assessment.",
         d2="Mark 1, complete. The unibeam is not a greeting."),
]

# lightningIngot and techAlien and wakandanMap and pistols - verify in lang
# I used some IDs I should verify:
# legends:lightningIngot - YES item.lightningIngot.name in legends lang
# legends:techAlien - YES item.techAlien.name
# legends:wakandanMap - YES item.wakandanMap.name
# legends:pistols - YES item.pistols.name
# legends:liquidAdamantium - YES
# legends:kryptonianSyringe - YES
# legends:asgardianForging - YES
# legends:regulator - YES
# legends:gasPellet - YES (field gasPellet, lang item.gasPellet.name)

def stack(id_, count, dmg):
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


def make_quest(qid, name, desc, icon, tasks, rewards, prereqs, is_main=0):
    return {
        "questID:3": qid,
        "preRequisites:11": prereqs,
        "properties:10": {
            "betterquesting:10": {
                "snd_complete:8": "minecraft:entity.player.levelup",
                "taskLogic:8": "AND",
                "visibility:8": "ALWAYS",
                "isMain:1": is_main,
                "simultaneous:1": 0,
                "icon:10": stack(icon, 1, 0),
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


def pieces_for(ch):
    if ch["no_helmet"]:
        return ["chestplate", "leggings", "boots"]
    return ["helmet", "chestplate", "leggings", "boots"]


def first_piece(ch):
    return "chestplate" if ch["no_helmet"] else "helmet"


def main():
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = os.path.join(BACKUP_DIR, "DefaultQuests.pre-heroes-%s.json" % stamp)
    shutil.copy2(SRC, backup)
    print("backup", backup)

    with open(SRC, "r", encoding="utf-8") as f:
        raw = f.read()
    if raw.startswith(u"\ufeff"):
        raise SystemExit("BOM present in source")
    data = json.loads(raw)

    qdb = data["questDatabase:9"]
    used = set()
    for k, q in qdb.items():
        used.add(q["questID:3"])
    if any(i >= START_QID for i in used):
        raise SystemExit("START_QID collides: %s" % sorted(i for i in used if i >= START_QID))

    lines = data["questLines:9"]
    for k, ch in lines.items():
        if ch.get("lineID:3") == CHAPTER_ID:
            raise SystemExit("chapter %s already exists" % CHAPTER_ID)

    qid = START_QID
    new_quests = {}
    layout = []  # (qid, x, y, size)

    # Intro — does not gate anything
    intro_id = qid
    new_quests[qid] = make_quest(
        qid,
        "Hall of Heroes",
        "§oWorkshop tab. Capes are optional. The paperwork is not.§r\n\n"
        "Suits come off the §eSuit Assembly Unit§r. Stark's toys come off the §eStark Workbench§r. "
        "Every line on this page is its own job. Finishing Batman does not unlock Superman.\n\n"
        "§eRetrieve Electronics.§r The logos in the reward are how the machine knows which universe you meant.",
        "legends:DCLogo",
        retrieval_task([L("legends:tech")]),
        item_rewards([
            L("legends:DCLogo"),
            L("legends:MarvelLogo"),
            L("legends:superDex"),
            L("legends:fabric", 16),
            L("lootbags:lootbag", 1, LB_COMMON),
            L("lucky:lucky_block", 4),
        ]),
        [],
    )
    layout.append((qid, 0, 0, 24))
    qid += 1

    # Optional collector — gates nothing
    collector_id = qid
    new_quests[qid] = make_quest(
        qid,
        "§6★ Costume Closet ★",
        "§6§l✦ OPTIONAL HOARD ✦§r\n\n"
        "§oThis does not unlock anything. It is just a closet with standards.§r\n\n"
        "Bring the chestplates: Superman, Batman, Wonder Woman, Flash, Captain America, Thor, Spider-Man, Black Panther.\n\n"
        "§eRetrieve those eight chests.§r Nobody else on this page is waiting.",
        "legends:captainamerica.chestplate",
        retrieval_task([
            L(suit("superman", "chestplate")),
            L(suit("batman", "chestplate")),
            L(suit("wonderwoman", "chestplate")),
            L(suit("flash", "chestplate")),
            L(suit("captainamerica", "chestplate")),
            L(suit("thor", "chestplate")),
            L(suit("spiderman", "chestplate")),
            L(suit("blackpanther", "chestplate")),
        ]),
        item_rewards([
            L("lootbags:lootbag", 1, LB_LEGEND),
            L("lucky:lucky_block", 16),
            L("legends:techHigh", 4),
            L("legends:nanobot", 8),
        ]),
        [],
    )
    layout.append((qid, 400, 0, 32))
    qid += 1

    # Iron Man family — one line, intra-prereqs only
    im = []
    im_defs = [
        ("ironman_mark0", "chestplate", ["chestplate", "leggings", "boots"],
         "Iron Man: Underarmor",
         "§oThe flight suit under the flight suit.§r\n\nStark wears this to the bench. No helmet. The reactor comes later.\n\n§eRetrieve the Mark 0 chest.§r",
         [L("legends:palladium", 4), L("legends:starkTech", 2), L("lootbags:lootbag", 1, LB_UNCOMMON)]),
        ("ironman_mark1", "chestplate", ["helmet", "chestplate", "leggings", "boots"],
         "Iron Man: Mark 1",
         "§oIt looks like a boiler that learned to punch.§r\n\nCave iron. The first one that walked out.\n\n§eRetrieve the Mark 1 chest.§r",
         [L("legends:miniArcReactor"), L("legends:titaniumPlate", 4), L("lootbags:lootbag", 1, LB_RARE)]),
        ("ironman_mark3", "chestplate", ["helmet", "chestplate", "leggings", "boots"],
         "Iron Man: Mark 3",
         "§oRed and gold. The one the posters remember.§r\n\nFull Mark 3 off the Stark Workbench.\n\n§eRetrieve the complete Mark 3.§r",
         [L("legends:palladiumArcReactor"), L("legends:repulsorType1"), L("lootbags:lootbag", 1, LB_EPIC)]),
        ("ironman_mark7", "chestplate", ["helmet", "chestplate", "leggings", "boots"],
         "Iron Man: Mark 7",
         "§oThe one that catches you in midair.§r\n\nAvengers red. Pod optional. Suit required.\n\n§eRetrieve the complete Mark 7.§r",
         [L("legends:vibraniumArcReactor"), L("legends:repulsorType1"), L("lootbags:lootbag", 1, LB_EPIC)]),
        ("ironman_mark21", "chestplate", ["helmet", "chestplate", "leggings", "boots"],
         "Iron Man: Mark 21",
         "§oLate-number vanity. Still a real registered suit.§r\n\nEnd of this line. Other heroes are not locked behind it.\n\n§eRetrieve the Mark 21 chest.§r",
         [L("lootbags:lootbag", 1, LB_LEGEND), L("lucky:lucky_block", 8), L("legends:starkTech", 4)]),
    ]
    prev = None
    for i, (nm, icon_piece, need, title, desc, rew) in enumerate(im_defs):
        tasks = retrieval_task([L(suit(nm, p)) for p in need] if i >= 2 and i <= 3 else [L(suit(nm, icon_piece))])
        # mark3 and mark7 ask for full set; others ask for the signature piece
        if i in (2, 3):
            tasks = retrieval_task([L(suit(nm, p)) for p in need])
        q = make_quest(qid, title, desc, suit(nm, icon_piece), tasks, item_rewards(rew), [prev] if prev else [])
        new_quests[qid] = q
        layout.append((qid, i * 56, 64, 24))
        im.append(qid)
        prev = qid
        qid += 1

    # Independent 2-quest lines
    cols = 6
    x0, y0, dx, dy = 0, 128, 120, 56
    for idx, ch in enumerate(CHARS):
        col = idx % cols
        row = idx // cols
        x = x0 + col * dx
        y = y0 + row * dy
        pcs = pieces_for(ch)
        first = first_piece(ch)
        q1 = qid
        new_quests[q1] = make_quest(
            q1,
            ch["display"],
            "§o%s§r\n\nIndependent line. Nobody else is waiting on this.\n\n§eRetrieve the %s %s.§r Assemble it in the Suit Assembly Unit."
            % (ch["d1"], ch["display"], first),
            suit(ch["name"], "chestplate"),
            retrieval_task([L(suit(ch["name"], first))]),
            item_rewards(ch["early"] + [L("lucky:lucky_block", 2)]),
            [],
        )
        layout.append((q1, x, y, 24))
        qid += 1
        q2 = qid
        bag = LB_EPIC if ch["major"] else LB_RARE
        late = list(ch["late"])
        # avoid double-adding bags if already present
        if not any(t[0] == "lootbags:lootbag" for t in late):
            late.append(L("lootbags:lootbag", 1, bag))
        new_quests[q2] = make_quest(
            q2,
            "%s: Full Set" % ch["display"],
            "§o%s§r\n\n§eRetrieve the complete %s suit.§r" % (ch["d2"], ch["display"]),
            suit(ch["name"], "chestplate"),
            retrieval_task([L(suit(ch["name"], p)) for p in pcs]),
            item_rewards(late),
            [q1],
        )
        layout.append((q2, x + 48, y, 24))
        qid += 1

    # Insert quests
    for qid_k, q in new_quests.items():
        key = "%d:10" % qid_k
        if key in qdb:
            raise SystemExit("quest key exists %s" % key)
        qdb[key] = q

    # Chapter
    qmap = {}
    for i, (qid_k, x, y, size) in enumerate(layout):
        qmap["%d:10" % i] = {
            "sizeX:3": size,
            "x:3": x,
            "y:3": y,
            "id:3": qid_k,
            "sizeY:3": size,
        }
    lines["%d:10" % CHAPTER_ID] = {
        "quests:9": qmap,
        "lineID:3": CHAPTER_ID,
        "properties:10": {
            "betterquesting:10": {
                "visibility:8": "ALWAYS",
                "name:8": "Side: Hall of Heroes",
                "icon:10": stack("legends:superman.chestplate", 1, 0),
                "bg_image:8": "",
                "bg_size:3": 256,
                "desc:8": "§b✦ INDEPENDENT SUIT LINES ✦§r\n\n"
                          "§oSide tab. Not the spine. Batman does not unlock Superman.§r\n\n"
                          "Every column is its own character. Iron Man Marks share one family line. "
                          "The costume closet at the top is optional and locks nothing.\n\n"
                          "Build suits at the Suit Assembly Unit. Stark armor at the Stark Workbench.",
            }
        },
        "order:3": 18,
    }

    settings = data["questSettings:10"]["betterquesting:10"]
    if settings.get("editMode:1") != 0:
        raise SystemExit("editMode was not 0")
    settings["editMode:1"] = 0

    # Validate IDs
    allowed = build_allowlist()
    bad = []
    for q in new_quests.values():
        for path, item in walk_items(q):
            if item not in allowed:
                bad.append((q["questID:3"], path, item))
    if bad:
        for row in bad[:40]:
            print("BAD", row)
        raise SystemExit("%d unknown item IDs" % len(bad))

    # nether star / banned
    banned_sub = ("nether_star", "projecte", "morph", "klein", "pe_matter", "pe_covalence")
    for q in new_quests.values():
        blob = json.dumps(q).lower()
        for b in banned_sub:
            if b in blob:
                raise SystemExit("banned token %s in Q%s" % (b, q["questID:3"]))

    tmp = SRC + ".tmp-heroes"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    # confirm no BOM and parse
    with open(tmp, "rb") as f:
        head = f.read(4)
    if head.startswith(b"\xef\xbb\xbf"):
        raise SystemExit("wrote BOM")
    with open(tmp, "r", encoding="utf-8") as f:
        json.load(f)
    os.replace(tmp, SRC)
    print("wrote", SRC)
    print("new_quests", len(new_quests), "ids", START_QID, "-", qid - 1)
    print("lines", 1 + 1 + 1 + len(CHARS), "intro+collector+ironman+chars")
    print("chapter", CHAPTER_ID, "Side: Hall of Heroes")


def walk_items(obj, path=""):
    if isinstance(obj, dict):
        if "id:8" in obj:
            yield path, obj["id:8"]
        for k, v in obj.items():
            for p in walk_items(v, path + "/" + k):
                yield p
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            for p in walk_items(v, path + "[%d]" % i):
                yield p


def build_allowlist():
    allowed = set()
    # vanilla / shared already in book
    allowed.update([
        "lootbags:lootbag", "lucky:lucky_block",
        "minecraft:emerald", "minecraft:diamond", "minecraft:iron_ingot",
        "minecraft:gold_ingot", "minecraft:leather",
    ])
    # suit pieces we quest
    for ch in CHARS:
        for p in pieces_for(ch):
            allowed.add(suit(ch["name"], p))
    for n in ("ironman_mark0", "ironman_mark1", "ironman_mark3", "ironman_mark7", "ironman_mark21"):
        for p in ("helmet", "chestplate", "leggings", "boots"):
            allowed.add(suit(n, p))
    # lang-backed gadgets / mats (sum + legends)
    lang_files = [
        os.path.join(BACKUP_DIR, "assets_sum_lang_en_US.lang"),
        os.path.join(BACKUP_DIR, "assets_legends_lang_en_US.lang"),
    ]
    for fp in lang_files:
        with open(fp, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("item.") and line.endswith(".name") is False and ".name=" in line:
                    key = line.split("=", 1)[0]
                    # item.foo.name or item.foo.bar.name (skip subtype keys for allow of base)
                    inner = key[len("item."):-len(".name")]
                    if "." not in inner:
                        allowed.add("legends:" + inner)
    # explicit extras used
    allowed.update([
        "legends:DCLogo", "legends:MarvelLogo", "legends:superDex",
        "legends:superman.chestplate", "legends:captainamerica.chestplate",
        "legends:batman.chestplate", "legends:flash.chestplate",
        "legends:wonderwoman.chestplate", "legends:thor.chestplate",
        "legends:spiderman.chestplate", "legends:blackpanther.chestplate",
    ])
    return allowed


if __name__ == "__main__":
    main()
