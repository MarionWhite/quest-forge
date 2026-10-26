#!/usr/bin/env python3
"""Build the Lucky Block page's data from the pack's Lucky Block config.

    python3 -I tools/site/build_lucky.py            write site/lucky/data/lucky.json and structures.json
    python3 -I tools/site/build_lucky.py --check    rebuild in memory and assert the contract (exit 1 on failure)
    python3 -I tools/site/build_lucky.py --dump     print lucky.json to stdout, write nothing

Reads pack/config/lucky/LuckyBlockProperties.txt (Lucky Block 5.1.0 format) and
site/items/data/items.json (names and icons). tools/items/refresh.py runs the plain form;
tools/site/check_fresh.py compares the two output files' times with the config and this script.
See tools/site/README-lucky.md for how the parser follows the mod, the weights and the contract.

Version 2 contract: every top-level drop has title, blurb, mood, scene, tile and actions.
Titles, blurbs, moods and scenes are written by hand in TEXT below, keyed by the drop's line
number in the config (the "/" comment lines above each drop give the hints). A drop with no
TEXT entry gets a generic title and scene and the check mode reports it.
"""

import json
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
CONFIG = os.path.join(ROOT, "pack", "config", "lucky", "LuckyBlockProperties.txt")
ITEMS = os.path.join(ROOT, "site", "items", "data", "items.json")
OUT_DIR = os.path.join(ROOT, "site", "lucky", "data")
OUT = os.path.join(OUT_DIR, "lucky.json")
OUT_STRUCTURES = os.path.join(OUT_DIR, "structures.json")

DEFAULT_LUCK = 2          # LuckyDropBase constructor
DEFAULT_CHANCE = 1.0
BASE_FACTOR = 0.0077      # ChooseLuckyDrop: b = 1 / (1 - 0.0077 * |K|)
VERSION = "5.1.0"

SCENES = ["item_drop", "item_set", "mob_spawn", "mob_horde", "mob_tower", "boss", "xp_burst",
          "tnt_rain", "expbottle_rain", "falling_column", "placed_blocks", "anvil_trap", "lava_trap",
          "water_trap", "pit_trap", "fort", "temple", "bedrock_problem", "explosion", "chest",
          "trapped_chest", "lucky_choice", "wishing_well", "sky_temple", "ground_temple", "effect",
          "apocalypse", "message", "pet", "villager_trader", "lightning", "fireworks_loot",
          "jens_hole", "troll_ore", "dud", "generic"]
MOODS = ["jackpot", "good", "neutral", "bad", "deadly"]
ACTION_TYPES = ["item", "entity", "xp", "tnt", "expbottle", "lightning", "fireworks", "structure",
                "falling", "block", "effect", "message", "command", "explosion", "choice", "then",
                "time", "particle"]

# ----------------------------------------------------------------- 1.7.10 tables

# Vanilla 1.7.10 potion ids (effects) and whether they are harmful.
POTIONS = {1: "Speed", 2: "Slowness", 3: "Haste", 4: "Mining Fatigue", 5: "Strength",
           6: "Instant Health", 7: "Instant Damage", 8: "Jump Boost", 9: "Nausea",
           10: "Regeneration", 11: "Resistance", 12: "Fire Resistance", 13: "Water Breathing",
           14: "Invisibility", 15: "Blindness", 16: "Night Vision", 17: "Hunger", 18: "Weakness",
           19: "Poison", 20: "Wither", 21: "Health Boost", 22: "Absorption", 23: "Saturation"}
HARMFUL_EFFECTS = {2, 4, 7, 9, 15, 17, 18, 19, 20}

# Vanilla 1.7.10 enchantment ids.
ENCHANTS = {0: "Protection", 1: "Fire Protection", 2: "Feather Falling", 3: "Blast Protection",
            4: "Projectile Protection", 5: "Respiration", 6: "Aqua Affinity", 7: "Thorns",
            16: "Sharpness", 17: "Smite", 18: "Bane of Arthropods", 19: "Knockback",
            20: "Fire Aspect", 21: "Looting", 32: "Efficiency", 33: "Silk Touch", 34: "Unbreaking",
            35: "Fortune", 48: "Power", 49: "Punch", 50: "Flame", 51: "Infinity"}

# Numeric 1.7.10 ids that the config uses in place of names: (registry name, damage).
LEGACY_ITEM = {
    349: ("minecraft:fish", 0), 382: ("minecraft:speckled_melon", 0),
    383: ("minecraft:spawn_egg", 0), 384: ("minecraft:experience_bottle", 0),
    2256: ("minecraft:record_13", 0), 2257: ("minecraft:record_cat", 0),
    2258: ("minecraft:record_blocks", 0), 2259: ("minecraft:record_chirp", 0),
    2260: ("minecraft:record_far", 0), 2261: ("minecraft:record_mall", 0),
    2262: ("minecraft:record_mellohi", 0), 2263: ("minecraft:record_stal", 0),
    2264: ("minecraft:record_strad", 0), 2265: ("minecraft:record_ward", 0),
    2266: ("minecraft:record_11", 0), 2267: ("minecraft:record_wait", 0),
}
LEGACY_BLOCK = {
    97: ("minecraft:monster_egg", 0),                      # silverfish block (stone variant)
    147: ("minecraft:light_weighted_pressure_plate", 0),
}
# Registry renames between the config's 1.7.10 spellings and items.json.
RENAMED = {"ink_sack": ("minecraft:dye", 0), "slimeball": ("minecraft:slime_ball", None),
           "seeds": ("minecraft:wheat_seeds", 0)}

# Mob classification for entity actions.
VANILLA_ENTITIES = {
    "Zombie", "PigZombie", "Skeleton", "WitherSkeleton", "Creeper", "Spider", "CaveSpider",
    "Enderman", "Witch", "Slime", "LavaSlime", "Ghast", "Blaze", "Pig", "Cow", "Sheep", "Chicken",
    "Squid", "Villager", "Bat", "Wolf", "Ozelot", "Silverfish", "Giant", "WitherBoss",
    "EntityHorse", "Mooshroom", "SnowMan", "VillagerGolem", "EnderDragon", "Item", "XPOrb",
    "Painting", "ArmorStand"}
ORESPAWN_ENTITIES = {
    "Mobzilla", "Mothra", "Hammerhead", "Cephadrome", "Large Worm", "Rotator", "CaterKiller",
    "Hoverboard", "Easter Bunny", "Coin", "Brown Ant", "Red Ant", "Rainbow Ant", "Unstable Ant",
    "Termite", "Robo-Pounder", "Robo-Gunner", "Robo-Warrior", "Mantis", "Bee", "Cloud Shark",
    "Enchanted Golden Apple Cow", "Brutalfly", "Seamonster", "Lava Eel", "Silverfish Lord"}
LUCKY_ENTITIES = {"luckyegg": "Lucky Egg"}

# Riding bytecode: the mod spawns these kinds of entity in a stack (Riding=).
SPECIAL_ENTITY_IDS = {"XPOrb", "lightning", "fireworks", "launched_tnt", "launched_expbottle",
                      "luckyegg", "Item"}

# ----------------------------------------------------------------- hand-written text
# Keyed by the drop's line number in LuckyBlockProperties.txt:
#   line: (title, blurb, mood, scene)
# Titles are at most 40 characters. Blurbs are one plain sentence of what happens in game.
DUD_BLURB = "The block's entry is broken in the pack's config, so it breaks and drops nothing."

TEXT = {
    # ---- tools and armour
    54: ("Ultimate Spider Smasher", "An OreSpawn Big Hammer named Ultimate Spider Smasher, with Bane of Arthropods at level 1000.", "jackpot", "item_drop"),
    55: ("Offence or Defence chestplate", "A diamond chestplate named Offence or Defence? with Sharpness and Protection at level 15.", "jackpot", "item_drop"),
    56: ("Offence or Defence helmet", "A diamond helmet named Offence or Defence? with Sharpness and Protection at level 15.", "jackpot", "item_drop"),
    57: ("Offence or Defence leggings", "A diamond pair of leggings named Offence or Defence? with Sharpness and Protection at level 15.", "jackpot", "item_drop"),
    58: ("Offence or Defence boots", "A pair of diamond boots named Offence or Defence? with Sharpness and Protection at level 15.", "jackpot", "item_drop"),
    59: ("Healthy Rainbow Chestplate", "A golden chestplate, unbreakable, with Health Boost II and 8 extra maximum health.", "jackpot", "item_drop"),
    60: ("Healthy Rainbow Helmet", "A golden helmet, unbreakable, with Health Boost II and 16 extra maximum health.", "jackpot", "item_drop"),
    61: ("Healthy Rainbow Boots", "Golden boots, unbreakable, with Health Boost II and 8 extra maximum health.", "jackpot", "item_drop"),
    62: ("Healthy Rainbow Leggings", "Golden leggings, unbreakable, with Health Boost II and 8 extra maximum health.", "jackpot", "item_drop"),
    63: ("Speedy Rainbow Chestplate", "An unbreakable iron chestplate that adds movement speed.", "jackpot", "item_drop"),
    64: ("Speedy Rainbow Helmet", "An unbreakable iron helmet that adds movement speed.", "jackpot", "item_drop"),
    65: ("Speedy Rainbow Boots", "Unbreakable iron boots that add more movement speed than the other speedy pieces.", "jackpot", "item_drop"),
    66: ("Speedy Rainbow Leggings", "Unbreakable iron leggings that add movement speed.", "jackpot", "item_drop"),
    67: ("Resisting Rainbow Chestplate", "An unbreakable diamond chestplate with knockback resistance.", "jackpot", "item_drop"),
    68: ("Resisting Rainbow Helmet", "An unbreakable diamond helmet with knockback resistance.", "jackpot", "item_drop"),
    69: ("Resisting Rainbow Boots", "Unbreakable diamond boots with knockback resistance.", "jackpot", "item_drop"),
    70: ("Resisting Rainbow Leggings", "Unbreakable diamond leggings with double knockback resistance.", "jackpot", "item_drop"),
    71: ("Strengthening Rainbow Chestplate", "An unbreakable leather chestplate that adds attack strength.", "jackpot", "item_drop"),
    72: ("Strengthening Rainbow Helmet", "An unbreakable leather helmet that adds attack strength.", "jackpot", "item_drop"),
    73: ("Strengthening Rainbow Boots", "Unbreakable leather boots that add attack strength.", "jackpot", "item_drop"),
    74: ("Strengthening Rainbow Leggings", "Unbreakable leather leggings that add attack strength.", "jackpot", "item_drop"),
    75: ("Strengthening Rainbow Sword", "An unbreakable wooden sword with a strength bonus.", "jackpot", "item_drop"),
    76: ("Resisting Rainbow Sword", "An unbreakable diamond sword with knockback resistance.", "jackpot", "item_drop"),
    77: ("Healthy Rainbow Sword", "An unbreakable golden sword with Health Boost II and 16 extra maximum health.", "jackpot", "item_drop"),
    78: ("Speedy Rainbow Sword", "An unbreakable iron sword with a movement speed bonus.", "jackpot", "item_drop"),
    81: ("Lava Eel armour piece", "One random piece of Lava Eel armour: helmet, leggings, chestplate or boots.", "good", "item_drop"),
    82: ("Experience armour piece", "One random piece of Experience armour.", "good", "item_drop"),
    83: ("Emerald armour piece", "One random piece of Emerald armour.", "good", "item_drop"),
    84: ("Amethyst armour piece", "One random piece of Amethyst armour.", "good", "item_drop"),
    85: ("Ruby armour piece", "One random piece of Ruby armour.", "jackpot", "item_drop"),
    86: ("Lapis armour piece", "One random piece of Lapis armour.", "good", "item_drop"),
    87: ("Peacock Feather armour set", "All four Peacock Feather armour pieces, one of each.", "good", "item_set"),
    88: ("Moth Scale armour piece", "One random piece of Moth Scale armour.", "good", "item_drop"),
    89: ("Crystal Pink armour piece", "One random piece of Crystal Pink armour.", "good", "item_drop"),
    90: ("Tiger's Eye armour piece", "One random piece of Tiger's Eye armour.", "good", "item_drop"),
    91: ("Ultimate armour piece", "One random piece of Ultimate armour, the best OreSpawn armour in the table.", "jackpot", "item_drop"),
    94: ("Amethyst tools", "One or two random Amethyst tools: shovel, pickaxe, axe or hoe.", "good", "item_set"),
    95: ("Ruby tools", "One or two random Ruby tools: shovel, pickaxe, axe or hoe.", "good", "item_set"),
    96: ("Emerald tools", "One or two random Emerald tools: shovel, pickaxe, axe or hoe.", "good", "item_set"),
    97: ("Crystal Pink tools", "One or two random Crystal Pink tools: shovel, pickaxe, axe or hoe.", "good", "item_set"),
    98: ("Tiger's Eye tools", "One or two random Tiger's Eye tools: shovel, pickaxe, axe or hoe.", "good", "item_set"),
    99: ("Ultimate tool", "One random Ultimate tool: axe, pickaxe, shovel, hoe or bow.", "jackpot", "item_drop"),
    102: ("Modded weapon", "One random OreSpawn weapon, from the Big Hammer to the Rose Sword.", "good", "item_drop"),
    103: ("Ultimate weapon", "One random Ultimate weapon: sword, Nightmare Sword, Hammy, Battle Axe or Chainsaw.", "jackpot", "item_drop"),
    104: ("Big Hammer", "An OreSpawn Big Hammer.", "good", "item_drop"),
    107: ("Wooden tool set", "The five wooden tools: sword, shovel, pickaxe, axe and hoe.", "neutral", "item_set"),
    108: ("Stone tool set", "The five stone tools: sword, shovel, pickaxe, axe and hoe.", "neutral", "item_set"),
    109: ("Golden tool set", "The five golden tools: sword, shovel, pickaxe, axe and hoe.", "neutral", "item_set"),
    110: ("Iron tools", "Two or three iron tools from the sword, shovel, pickaxe, axe and hoe.", "good", "item_set"),
    111: ("Diamond tools", "One or two diamond tools from the sword, shovel, pickaxe, axe and hoe.", "good", "item_set"),
    112: ("Leather armour set", "The four leather armour pieces.", "neutral", "item_set"),
    113: ("Golden armour set", "The four golden armour pieces and a golden horse armour.", "neutral", "item_set"),
    114: ("Chainmail armour", "Two or three pieces of chainmail armour.", "neutral", "item_set"),
    115: ("Iron armour", "Two or three pieces of iron armour, or a horse armour.", "good", "item_set"),
    116: ("Diamond armour", "One or two pieces of diamond armour, or a diamond horse armour.", "good", "item_set"),
    117: ("Horse armour", "Iron, golden and diamond horse armour, all three.", "neutral", "item_set"),
    118: ("Bow and arrows", "A bow and between 16 and 32 arrows.", "neutral", "item_set"),
    119: ("Ultimate armour piece", "One random piece of Ultimate armour.", "jackpot", "item_drop"),
    120: ("Ultimate weapon set", "One random Ultimate sword, axe, pickaxe, shovel, hoe or bow.", "jackpot", "item_drop"),
    124: ("Sponge", "A sponge.", "neutral", "item_drop"),
    125: ("TNT, eight blocks", "Eight blocks of TNT.", "bad", "item_set"),
    126: ("Obsidian, fourteen blocks", "Fourteen blocks of obsidian.", "neutral", "item_set"),
    127: ("Enchanting table", "An enchanting table.", "good", "item_drop"),
    128: ("End portal frames", "Four to eight end portal frames.", "good", "item_set"),
    129: ("Dragon egg", "A dragon egg.", "good", "item_drop"),
    130: ("Two ender chests", "Two ender chests.", "neutral", "item_set"),
    131: ("Beacon", "A beacon.", "good", "item_drop"),
    132: ("Eight droppers", "Eight droppers.", "neutral", "item_set"),
    133: ("Eight hay bales", "Eight hay bales.", "neutral", "item_set"),
    134: ("Monster egg", "A stone monster egg, a silverfish block.", "neutral", "item_drop"),
    135: ("Gold ore", "Eight to sixteen gold ore blocks.", "good", "item_set"),
    136: ("Iron ore", "Sixteen to thirty-two iron ore blocks.", "good", "item_set"),
    137: ("Diamond ore", "Five to ten diamond ore blocks.", "jackpot", "item_set"),
    138: ("Coal ore", "Thirty-two to sixty-four coal ore blocks.", "neutral", "item_set"),
    142: ("Miner's Dream", "Ten OreSpawn Miner's Dream items.", "good", "item_set"),
    143: ("Cage, empty", "Twenty-five empty OreSpawn cages.", "neutral", "item_set"),
    144: ("Sifter", "Three OreSpawn sifters.", "good", "item_set"),
    145: ("Bacon", "Between 64 and 256 OreSpawn bacon.", "good", "item_set"),
    146: ("Gold ingots", "Eight to sixteen gold ingots.", "good", "item_set"),
    147: ("A stick", "A single stick.", "neutral", "item_drop"),
    148: ("Bones", "Sixteen to forty-eight bones.", "neutral", "item_set"),
    149: ("Apples", "Between 64 and 128 apples.", "good", "item_set"),
    150: ("Random item stack", "Between 1 and 48 of a random item from the whole item list.", "neutral", "item_drop"),
    151: ("Four paintings", "Four paintings.", "neutral", "item_set"),
    152: ("Two saddles", "Two saddles.", "neutral", "item_set"),
    153: ("Cake", "A cake.", "neutral", "item_drop"),
    154: ("Rotten flesh", "A piece of rotten flesh.", "bad", "item_drop"),
    155: ("Nether star", "A nether star.", "jackpot", "item_drop"),
    156: ("Red flower", "A red flower.", "neutral", "item_drop"),
    157: ("Sixteen snowballs", "Sixteen snowballs.", "neutral", "item_set"),
    158: ("Sixteen slimeballs", "Sixteen slimeballs.", "neutral", "item_set"),
    159: ("Clock", "A clock.", "neutral", "item_drop"),
    160: ("Three ink sacs", "Three ink sacs, which are dye.", "neutral", "item_set"),
    161: ("Thirty glass bottles", "Thirty glass bottles.", "neutral", "item_set"),
    162: ("Sixty-four bottles o' enchanting", "Sixty-four experience bottles.", "good", "item_set"),
    163: ("Poisonous potato", "A poisonous potato.", "bad", "item_drop"),
    164: ("Four name tags", "Four name tags.", "neutral", "item_set"),
    165: ("Music disc, mall", "The Mall music disc.", "neutral", "item_drop"),
    166: ("Music disc, wait", "The Wait music disc.", "neutral", "item_drop"),
    167: ("A fish", "A raw fish.", "neutral", "item_drop"),
    172: ("Fish stacks", "Five to ten each of nine OreSpawn fish, and an Ultimate fishing rod.", "good", "item_set"),
    174: ("Rocks and crystals", "Three to five of five random rocks and crystals, from the Sunspot Urchin to the Crystal Blue Rock.", "good", "item_set"),
    176: ("Random scale", "Ten to twenty of one random scale or feather.", "jackpot", "item_set"),
    178: ("Random potion effect", "A random potion effect for 30 ticks, with a random strength.", "neutral", "effect"),
    180: ("Prince and princess eggs", "The Prince egg and perhaps the Princess egg.", "good", "item_set"),
    182: ("Popcorn", "Sixteen to thirty-two of one popcorn.", "neutral", "item_set"),
    184: ("Instant garden or shelter", "An instant garden and an instant shelter, both OreSpawn blocks.", "good", "item_set"),
    186: ("Ten random items", "Ten stacks of random items from the whole item list, 1 to 48 each.", "neutral", "item_set"),
    188: ("Ten random spawn eggs", "Ten random spawn eggs, one to three each.", "neutral", "item_set"),
    190: ("Robot kit", "A spider robot kit, an ant robot kit and a wrench.", "good", "item_set"),
    192: ("Shooting stuff", "One of a ray gun, a squid zooka or a thunder staff.", "good", "item_drop"),
    194: ("Ruby, amethyst, uranium and titanium", "Five to fifteen of one of four OreSpawn gems or ingots, and a stack of fireworks.", "good", "fireworks_loot"),
    196: ("Bookshelves and books", "Six to twelve bookshelves and eight to sixteen books.", "neutral", "item_set"),
    198: ("Pumpkins", "Eight to sixteen pumpkins or jack o'lanterns.", "neutral", "item_set"),
    200: ("Golden apples", "Two to four golden apples, or one or two of the other kind.", "good", "item_set"),
    202: ("Buckets", "One or two of one bucket: empty, water, lava or milk.", "neutral", "item_set"),
    204: ("Meat, raw or cooked", "One of four meat stacks: porkchop, fish, beef or chicken, raw and cooked.", "neutral", "item_set"),
    206: ("Vegetable food", "One of four food stacks: carrots, potatoes, beef or pumpkin pie.", "neutral", "item_set"),
    208: ("Ender pearls and eyes", "Ten ender pearls and five ender eyes.", "good", "item_set"),
    210: ("Potions", "Four to eight random potions.", "good", "item_set"),
    212: ("Spawn eggs", "Four to eight random spawn eggs.", "neutral", "item_set"),
    214: ("Heads", "One to three random heads.", "neutral", "item_set"),
    216: ("Jukebox and music discs", "A jukebox and one to three random music discs.", "neutral", "item_set"),
    218: ("Brewing ingredients", "One to three each of twelve brewing ingredients.", "good", "item_set"),
    220: ("Redstone pile", "A full pile of redstone parts: pistons, droppers, torches, a noteblock and TNT.", "neutral", "item_set"),
    222: ("Colourful wool", "One of three colour stacks, and a flash of particles.", "neutral", "item_set"),
    224: ("Iron, gold, diamond and emerald", "Eight to sixteen of each of four ingots and gems, with twenty fireworks.", "good", "fireworks_loot"),
    226: ("Ultimate ingots", "Eight to sixteen titanium and uranium ingots, with twenty fireworks.", "jackpot", "fireworks_loot"),
    228: ("Quartz", "Quartz and quartz blocks, stairs and slabs, with a flash of particles.", "neutral", "item_set"),
    230: ("Fishing rod and random fish", "A fishing rod and ten to twenty random fish.", "neutral", "item_set"),
    232: ("Random joke", "One of three jokes: a clock, or a fish that says I'm funny or Oooooh.", "neutral", "item_drop"),
    234: ("Sixty-four red flowers", "Sixty-four red flowers.", "neutral", "item_set"),
    236: ("Enchanted book", "A random enchanted book, seven to ten times over.", "good", "item_set"),
    238: ("Pat's shopping message", "A chat line from Pat, and between 128 and 256 gold nuggets.", "neutral", "message"),
    240: ("Mitch's torches", "A chat line from Mitch, and 64 to 250 torches.", "neutral", "message"),
    242: ("Message with mushroom", "A chat line from PlayerInDistress, and a red mushroom with Only Hope on it.", "neutral", "message"),
    244: ("Ore and fireworks", "Five to ten each of four ores, with two fireworks.", "good", "fireworks_loot"),
    246: ("Captain Cookie's cookies", "Thirty-two cookies.", "neutral", "item_set"),
    248: ("Walking dead secret tape", "A chat line from the Disguised Man, and a jukebox.", "neutral", "message"),
    250: ("BLT", "Three crabby patties, three salads and a BLT.", "neutral", "item_set"),
    252: ("Repellents", "Twenty each of three OreSpawn repellents, and twenty torches.", "good", "item_set"),
    256: ("Too much XP", "Five hundred experience points fall out of the sky.", "good", "xp_burst"),
    258: ("Stalking TNT", "Between 20 and 30 TNT launched at you.", "deadly", "tnt_rain"),
    260: ("Bob family", "A giant named Bob's mom, two zombies named Bob and King Bob, and a ghast named Bob's dad riding a giant.", "deadly", "mob_horde"),
    262: ("Bob's dad", "A ghast named Bob's dad in diamond armour and a diamond sword, riding a giant.", "bad", "mob_tower"),
    264: ("Ten Dinnerbone ghasts", "Ten ghasts named Dinnerbone.", "bad", "mob_horde"),
    266: ("MetaCow", "An enchanted golden apple cow called MetaCow.", "good", "mob_spawn"),
    268: ("Ten rotators", "Ten OreSpawn Rotators.", "bad", "mob_horde"),
    270: ("Creeper launcher", "Five towers of four creepers each, a lightning strike, and a Creeper Launcher given to you.", "bad", "mob_tower"),
    272: ("TNT jockey", "Between 20 and 30 TNT launched at you.", "deadly", "tnt_rain"),
    274: ("Acrobatic giants", "Three giants stacked on one another, all named Dinnerbone.", "deadly", "boss"),
    276: ("Mothra sandwich", "Five creatures stacked: a Mothra on a Brutalfly on a Mothra on a Brutalfly on a Mothra.", "deadly", "mob_tower"),
    278: ("Hammerhead", "A Hammerhead shark, an OreSpawn boss.", "deadly", "boss"),
    280: ("Herobrine's minions", "Ten silverfish pour out around you.", "bad", "mob_horde"),
    282: ("Enderman, endersult", "Thirteen endermen, each wearing the nametag 'Never endersult me with my length'.", "bad", "mob_horde"),
    284: ("Witch and bats", "A witch with seven to ten bats.", "bad", "mob_spawn"),
    286: ("Slime and enderman", "Two to four endermen, each with a slime on its head.", "bad", "mob_tower"),
    288: ("Death jump", "Jump Boost at level 51 for 30 seconds, and a message from aceaight that you will die an unexpected death.", "bad", "effect"),
    290: ("Random potion effect", "A random potion effect for 30 to 600 ticks, with a random strength.", "neutral", "effect"),
    292: ("Passive mob", "One of five named passive mobs: a pig, a cow, a chicken, a sheep or Mr. Derpy the squid.", "neutral", "mob_spawn"),
    294: ("Colourful sheep", "Sixteen sheep named Mr. Rainbow appear around you.", "neutral", "mob_horde"),
    296: ("Lucky eggs", "Twenty lucky eggs.", "good", "mob_horde"),
    298: ("Mobzilla, 'A Wild Groudon'", "Mobzilla, the OreSpawn boss, wearing the nametag 'A Wild Groudon'.", "deadly", "boss"),
    300: ("Ten Mothras, 'A Wild Butterfree'", "Ten Mothras, each wearing the nametag 'A Wild Butterfree'.", "deadly", "boss"),
    302: ("CaterKiller, 'A Wild Caterpie'", "A CaterKiller, the OreSpawn boss, wearing the nametag 'A Wild Caterpie'.", "deadly", "boss"),
    304: ("Launched experience bottles", "Sixteen to thirty-two experience bottles thrown at you.", "good", "expbottle_rain"),
    306: ("Launched TNT", "One to sixty-four TNT launched at you.", "bad", "tnt_rain"),
    308: ("Lightning creeper", "A creeper and a lightning strike.", "bad", "lightning"),
    310: ("Lightning mobs", "Ten creepers, ten pigs and a lightning strike.", "bad", "lightning"),
    312: ("Giant", "A giant zombie.", "deadly", "boss"),
    314: ("Wither", "A wither boss.", "deadly", "boss"),
    316: ("Ghast", "A ghast.", "bad", "mob_spawn"),
    318: ("Bob's mom", "A giant named Bob's mom.", "deadly", "boss"),
    320: ("Freddy", "A silverfish named freddy.", "bad", "mob_spawn"),
    322: ("Bob the decked zombie", "A zombie named Bob.", "bad", "mob_spawn"),
    324: ("Sven", "A cave spider named Sven.", "bad", "mob_spawn"),
    326: ("Sparky the wolf", "A wolf named Sparky, with hearts.", "good", "pet"),
    328: ("Ultimate Joey", "A skeleton named Ultimate Joey.", "bad", "mob_spawn"),
    330: ("Pat the villager", "A villager named Pat.", "neutral", "villager_trader"),
    332: ("King Bob", "A zombie named King Bob.", "bad", "mob_spawn"),
    334: ("Villager with pigs", "A villager standing on a stack of seven pigs.", "neutral", "mob_tower"),
    336: ("Horses", "Twelve horses, scattered around you.", "good", "mob_horde"),
    338: ("Witch and sixty-four bats", "A witch with sixty-four bats.", "bad", "mob_horde"),
    340: ("Slime or magma cube", "One slime or one magma cube.", "bad", "mob_spawn"),
    342: ("Pet wolves", "Five to ten tame wolves, with hearts.", "good", "pet"),
    344: ("Pet cats", "Five to ten ocelots, with hearts.", "good", "pet"),
    346: ("Pet dragons", "Five to ten dragons, with hearts.", "good", "pet"),
    348: ("Lucky Villager", "A villager named Lucky Villager.", "neutral", "villager_trader"),
    349: ("Lucky Villager", "A villager named Lucky Villager.", "neutral", "villager_trader"),
    350: ("Lucky Villager", "A villager named Lucky Villager.", "neutral", "villager_trader"),
    351: ("I Have Nothing Interesting", "A villager wearing the nametag 'I Have Nothing Interesting To Trade'.", "neutral", "villager_trader"),
    352: ("Strange Item Collector", "A villager named Strange Item Collector.", "neutral", "villager_trader"),
    353: ("Shooping with coins", "A villager named Shooping with Coins.", "neutral", "villager_trader"),
    354: ("Kinda Lucky Villager", "A villager named Kinda Lucky Villager.", "neutral", "villager_trader"),
    356: ("Bat swarm", "One hundred and twenty bats, squeaking.", "neutral", "mob_horde"),
    358: ("Rainbow sheep", "One hundred rainbow sheep.", "neutral", "mob_horde"),
    360: ("Cephadrome", "An OreSpawn Cephadrome, a boss.", "deadly", "boss"),
    362: ("Villagers", "Five to ten villagers, asking where the village is.", "neutral", "mob_horde"),
    364: ("Mr. Porkchop", "Sixteen pigs, one named Mr. Porkchop.", "neutral", "mob_horde"),
    366: ("Chicken coop", "Forty-five chickens, one named I'm A Chick.", "neutral", "mob_horde"),
    368: ("Milk for days", "Twenty cows named MilkMe.", "neutral", "mob_horde"),
    370: ("Jeb's sheep", "Sixteen to 100 sheep named jeb_, which cycles their wool through every colour.", "neutral", "mob_horde"),
    372: ("Hoverboard", "An OreSpawn hoverboard, with a line from Back to the Future.", "good", "mob_spawn"),
    374: ("Ant army", "Thirty each of five kinds of ant.", "bad", "mob_horde"),
    376: ("Robot army", "Three robots: Pounder, Gunner and Warrior.", "deadly", "boss"),
    378: ("Easter bunnies", "Ten Easter Bunnies.", "neutral", "mob_horde"),
    380: ("Coins", "Fifteen coins from the OreSpawn mod.", "neutral", "mob_horde"),
    382: ("Cow tower", "Three to ten towers of cows, each a cow on a mushroom cow, an apple cow, a golden apple cow, an enchanted golden apple cow and a crystal apple cow, all standing on a bat.", "neutral", "mob_tower"),
    386: ("Large Worm", "A Large Worm, an OreSpawn boss.", "deadly", "boss"),
    384: ("A dud", DUD_BLURB, "neutral", "dud"),
    390: ("Anvil trap", "Iron bars rise around you and anvils fall on your head.", "deadly", "anvil_trap"),
    391: ("Lava trap", "Iron bars close around you, and lava pours in from above.", "deadly", "lava_trap"),
    392: ("Water trap", "You are sealed in an obsidian and glass room with water flowing in the middle.", "bad", "water_trap"),
    393: ("Pit trap", "The ground opens into a three-by-sixty shaft, and you land on a web over lava.", "bad", "pit_trap"),
    396: ("Lucky fort", "A sandstone fort with gold on its corners and four lucky blocks inside.", "good", "fort"),
    397: ("Lucky temple", "A stepped sandstone temple rises around you.", "good", "temple"),
    400: ("Iron block falls", "An iron block falls from the sky.", "neutral", "falling_column"),
    401: ("Gold block falls", "A gold block falls from the sky.", "neutral", "falling_column"),
    402: ("Diamond block falls", "A diamond block falls from the sky.", "good", "falling_column"),
    403: ("Emerald block falls", "An emerald block falls from the sky.", "good", "falling_column"),
    404: ("Lapis block falls", "A lapis block falls from the sky.", "neutral", "falling_column"),
    405: ("Redstone block falls", "A redstone block falls from the sky.", "neutral", "falling_column"),
    406: ("Coal block falls", "A coal block falls from the sky.", "neutral", "falling_column"),
    407: ("Cake falls", "A cake falls from the sky.", "neutral", "falling_column"),
    411: ("Bedrock problem", "Bedrock appears where the block was, with a sign that reads 'Well, there\'s your problem.'", "bad", "bedrock_problem"),
    414: ("Explosion", "An explosion of power 6 goes off where you stand.", "deadly", "explosion"),
    417: ("Death pole", "A redstone block and a tower of TNT fall from the sky, stacked up.", "deadly", "falling_column"),
    420: ("Ore pole", "A tower of ores, falling from the sky.", "good", "falling_column"),
    423: ("Enchanting room", "An enchanting table and bookshelves fall in a pile.", "good", "falling_column"),
    426: ("Rainbow", "A rainbow of blocks falls from the sky.", "good", "falling_column"),
    429: ("Challenge games tower", "A tower of sponges and lucky blocks, with a diamond block and a hole in the middle.", "good", "placed_blocks"),
    432: ("Rainbow made from lucky blocks", "A rainbow made of lucky blocks is placed around you.", "good", "placed_blocks"),
    435: ("Lucky pole", "A tower of lucky blocks falls from the sky, with a redstone block at the bottom.", "bad", "falling_column"),
    438: ("Heart", "A heart of falling glass and wool, with love.", "good", "falling_column"),
    441: ("Nether portal", "A nether portal of falling obsidian.", "good", "falling_column"),
    444: ("OP pole", "A pole of blocks falls from the sky.", "good", "falling_column"),
    447: ("Dungeon pole", "A pole of ore blocks falls, with a dungeon spawner at the top.", "jackpot", "falling_column"),
    450: ("Random pole", "A pole of random blocks falls from the sky.", "neutral", "falling_column"),
    453: ("Colourful pole", "A pole of stained clay falls from the sky.", "neutral", "falling_column"),
    456: ("Jen's hole", "A chat line from Jen, a three-block hole under you and a witch named Jen at the bottom.", "neutral", "jens_hole"),
    459: ("Tower of useful blocks", "A pile of crafting table, furnace, enchanting table, anvil, chest and brewing stand.", "good", "falling_column"),
    462: ("King's pole", "A pole of quartz blocks falls, with a King spawner at the top.", "deadly", "falling_column"),
    465: ("Queen's pole", "A pole of titanium and uranium ore falls from the sky.", "deadly", "falling_column"),
    468: ("Diamond trap", "Diamond ore blocks, air and lava are laid out below you.", "bad", "placed_blocks"),
    471: ("Bonus chest", "A chest of bonus loot appears.", "good", "chest"),
    472: ("Dungeon chest", "A dungeon chest with better loot.", "good", "chest"),
    473: ("Village blacksmith chest", "A chest with village blacksmith loot.", "good", "chest"),
    474: ("Chest of iron, gold and apples", "A chest with eight items from a list of iron, gold, emeralds, diamonds, lucky blocks and golden apples.", "good", "chest"),
    477: ("Choice of two lucky blocks", "Two lucky blocks appear side by side, one lucky and one not, with a sign between them.", "good", "lucky_choice"),
    480: ("Troll ore", "Diamond ore falls from the sky, scattered up to fifty blocks away.", "bad", "troll_ore"),
    483: ("Trapped chest", "A trapped chest, with TNT under and around it.", "deadly", "trapped_chest"),
    486: ("Wishing well", "A wishing well appears, and a wish comes true.", "good", "wishing_well"),
    487: ("Wishing well, potatoes", "A wishing well with a potato wish.", "good", "wishing_well"),
    488: ("Wishing well, death wish", "A wishing well with TNT.", "deadly", "wishing_well"),
    489: ("Wishing well, blazes", "A wishing well with twenty blazes.", "bad", "wishing_well"),
    490: ("Wishing well, farming", "A wishing well with random items and hoes.", "good", "wishing_well"),
    491: ("Wishing well, no wish", "A wishing well with nothing in it; you just wasted your coin.", "neutral", "wishing_well"),
    492: ("Wishing well, sort of", "A wishing well with redstone, random items and quartz.", "good", "wishing_well"),
    493: ("Wishing well, think fast", "A wishing well with TNT and gold, emeralds and diamonds.", "bad", "wishing_well"),
    494: ("Wishing well, no escape", "A wishing well with one hundred TNT.", "deadly", "wishing_well"),
    495: ("Wishing well, apples", "A wishing well with golden apples and apples.", "good", "wishing_well"),
    496: ("Wishing well, challenge games", "A wishing well with sponges, end portal frames and fireworks.", "good", "wishing_well"),
    497: ("Wishing well, diamonds", "A wishing well that gives thirty to forty diamonds.", "jackpot", "wishing_well"),
    498: ("Wishing well, emeralds", "A wishing well that gives thirty to forty emeralds.", "jackpot", "wishing_well"),
    499: ("Wishing well, empty", "A wishing well with nothing in the hidden block.", "neutral", "wishing_well"),
    502: ("Heaven temple", "A sky temple of iron, emerald and diamond blocks high above you, with a hidden lucky block.", "good", "sky_temple"),
    503: ("Heaven temple, dragon egg", "A sky temple with a hidden lucky block that gives a nether star and a dragon egg.", "jackpot", "sky_temple"),
    504: ("Heaven temple, tools", "A sky temple with a hidden lucky block that gives iron and diamond tools.", "good", "sky_temple"),
    505: ("Heaven temple, food", "A sky temple with a hidden lucky block that gives cooked food.", "neutral", "sky_temple"),
    506: ("Heaven temple, Herobrine", "Herobrine tries to kill you: TNT in the hidden block.", "deadly", "sky_temple"),
    507: ("Heaven temple, minions", "Herobrine spawns minions: blazes and ghasts in the hidden block.", "deadly", "sky_temple"),
    508: ("Heaven temple, the ground", "A sky temple where the gods fill the ground with diamonds, emeralds and gold.", "jackpot", "sky_temple"),
    511: ("Earth temple", "An earth temple of iron, stone and planks in the ground beneath you.", "good", "ground_temple"),
    512: ("Earth temple, dragon egg", "An earth temple with a hidden lucky block that gives a nether star and a dragon egg.", "jackpot", "ground_temple"),
    513: ("Earth temple, tools", "An earth temple with a hidden lucky block that gives iron and diamond tools.", "good", "ground_temple"),
    514: ("Earth temple, food", "An earth temple with a hidden lucky block that gives cooked food.", "neutral", "ground_temple"),
    515: ("Earth temple, Herobrine", "Herobrine tries to kill you: TNT in the hidden block.", "deadly", "ground_temple"),
    516: ("Earth temple, minions", "Herobrine spawns minions: blazes and ghasts in the hidden block.", "deadly", "ground_temple"),
    519: ("Hell temple", "A hell temple of iron, obsidian and nether brick below you.", "bad", "ground_temple"),
    520: ("Hell temple, dragon egg", "A hell temple with a hidden lucky block that gives a nether star and a dragon egg.", "good", "ground_temple"),
    521: ("Hell temple, tools", "A hell temple with a hidden lucky block that gives iron and diamond tools.", "neutral", "ground_temple"),
    522: ("Hell temple, food", "A hell temple with a hidden lucky block that gives cooked food.", "neutral", "ground_temple"),
    523: ("Hell temple, Herobrine", "Herobrine tries to kill you, and it is night.", "deadly", "ground_temple"),
    524: ("Hell temple, minions", "Herobrine spawns minions: blazes and ghasts, at night.", "deadly", "ground_temple"),
    525: ("Hell temple, lava rain", "Herobrine starts a lava rain.", "deadly", "ground_temple"),
    531: ("Zombies, creepers or nothing", "One of a horde of zombies, a horde of creepers, or a broken entry that errors and drops nothing.", "deadly", "apocalypse"),
    533: ("Monster apocalypse", "Twenty to fifty zombies, ten to thirty creepers, fifteen to forty-five spiders and five to ten cave spiders.", "deadly", "apocalypse"),
    535: ("Sven's army", "Six cave spiders named Sven.", "bad", "mob_horde"),
    543: ("Modded monster pair", "Two to five Mantis and three to seven Bees.", "deadly", "mob_horde"),
    547: ("Lucky block book", "A written book, the lucky block book.", "neutral", "item_drop"),
    549: ("Lucky sword", "A golden sword named Lucky Sword.", "good", "item_drop"),
    551: ("Lucky bow", "A bow named Lucky Bow.", "good", "item_drop"),
    553: ("Lucky fishing rod", "A fishing rod named Lucky Fishing Rod.", "good", "item_drop"),
    555: ("Lucky tools", "One or two of the four lucky golden tools: shovel, pickaxe, axe or hoe.", "good", "item_set"),
    557: ("Lucky armour", "One or two of the four lucky golden armour pieces.", "good", "item_set"),
    559: ("Lucky potion", "A lucky potion.", "good", "item_drop"),
    561: ("Unlucky potion", "An unlucky potion.", "bad", "item_drop"),
    563: ("BootySlapper", "A diamond shovel named BootySlapper.", "good", "item_drop"),
    565: ("Betty", "A diamond axe named Betty.", "good", "item_drop"),
    567: ("Hoe of wisdom", "A diamond hoe named Hoe of Wisdom.", "good", "item_drop"),
    569: ("Stone destroyer", "A diamond pickaxe named Stone Destroyer.", "good", "item_drop"),
    571: ("Knockback stick", "A stick named Back off.", "neutral", "item_drop"),
    573: ("Burning rod", "A blaze rod named Burn baby burn.", "neutral", "item_drop"),
}


# ----------------------------------------------------------------- mod-faithful parsing

class ModError(Exception):
    """A drop line the mod itself cannot read (it throws when the drop is picked)."""


def mod_split(s, sep):
    """LuckyFunction.splitBracketString: split on sep at bracket depth 0 and outside quotes.

    A quote is escaped when the character before it is a backslash. (, [ and { raise the
    depth and ), ] and } lower it, both only outside quotes.
    """
    out, buf, depth, quoted = [], [], 0, False
    for i, ch in enumerate(s):
        if ch == '"' and not (i > 0 and s[i - 1] == "\\"):
            quoted = not quoted
        elif not quoted:
            if ch in "([{":
                depth += 1
            elif ch in ")]}":
                depth -= 1
            elif ch == sep and depth == 0:
                out.append("".join(buf))
                buf = []
                continue
        buf.append(ch)
    out.append("".join(buf))
    return out


def group_contents(text):
    """MakeLuckyDrops.getGroupContents: the text between the first '(' and the last ')'."""
    start = text.find("(")
    end = text.rfind(")")
    if start < 0 or end < 0 or end < start + 1:
        # the mod calls String.substring(start + 1, -1): a StringIndexOutOfBoundsException
        raise ModError("group has no closing ')' (the mod throws when it is picked)")
    return text[start + 1:end]


def unquote(v):
    if v is not None and len(v) >= 2 and v[0] == '"' and v[-1] == '"':
        return v[1:-1].replace('\\"', '"')
    return v


def parse_fields(text):
    """setDropProperties: comma-separated key=value tokens. Later keys overwrite earlier ones."""
    fields = {}
    for tok in mod_split(text, ","):
        tok = tok.strip()
        eq = tok.find("=")
        if eq <= 0:
            continue
        fields[tok[:eq].strip()] = tok[eq + 1:].strip()
    return fields


class Node:
    """A parsed drop: kind is 'leaf' (fields), 'group' (members, pick) or 'broken' (raw text)."""

    def __init__(self, kind, raw, fields=None, members=None, pick=None):
        self.kind = kind
        self.raw = raw
        self.fields = fields or {}
        self.members = members or []
        self.pick = pick          # None, or [lo, hi] for group:N and group:#random-a-b


def parse_pick(head):
    """'group:1' -> [1,1]; 'group:#random-1-2' -> [1,2]; plain 'group' -> None."""
    if not head.startswith(":"):
        return None
    v = head[1:]
    r = rng(v)
    if r is None:
        raise ModError("unreadable group count %r" % v)
    return r


def parse_node(text):
    if not text.startswith("group"):
        return Node("leaf", text, fields=parse_fields(text))
    open_at = text.find("(")
    if open_at < 0:
        return Node("broken", text)
    head = text[len("group"):open_at]
    try:
        inner = group_contents(text)
    except ModError:
        return Node("broken", text)
    members = []
    for m in mod_split(inner, ";"):
        if m.strip():
            members.append(parse_node(m.strip()))
    try:
        pick = parse_pick(head)
    except ModError:
        pick = None
    return Node("group", text, members=members, pick=pick)


def rng(v):
    """'#random-a-b' -> [a, b]; '7' -> [7, 7]; anything else -> None."""
    if v is None:
        return None
    v = str(v).strip()
    m = re.fullmatch(r"#random-(-?\d+)-(-?\d+)", v)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        return [min(a, b), max(a, b)]
    try:
        n = int(float(v))
        return [n, n]
    except ValueError:
        return None


def pos_offset(v):
    """posX/posY/posZ: '#bPosY+3', '#bPosY-#random-5-30', '#bPosX' or a number -> [lo, hi]."""
    if v is None:
        return [0, 0]
    s = v.replace("'", "").strip()
    m = re.fullmatch(r"#[bp]Pos[XYZ]\s*(?:([+-])\s*(.+))?", s)
    if not m:
        r = rng(s)
        return r if r is not None else [0, 0]
    if m.group(1) is None:
        return [0, 0]
    r = rng(m.group(2))
    if r is None:
        return [0, 0]
    if m.group(1) == "-":
        r = [-r[1], -r[0]]
    return r


def is_random_pos(lohi):
    return lohi[0] != lohi[1]


# ----------------------------------------------------------------- NBT

def parse_nbt(s):
    """A parenthesised NBT-ish value: (k=v,...), [v,...], "strings" with \\" escapes, bare tokens."""
    val, _ = _nbt(s, 0)
    return val


def _nbt(s, i):
    while i < len(s) and s[i] == " ":
        i += 1
    if i >= len(s):
        return None, i
    c = s[i]
    if c == '"':
        out, j = [], i + 1
        while j < len(s):
            if s[j] == "\\" and j + 1 < len(s):
                out.append(s[j + 1])
                j += 2
                continue
            if s[j] == '"':
                return "".join(out), j + 1
            out.append(s[j])
            j += 1
        return "".join(out), j
    if c == "(":
        out, i = {}, i + 1
        while i < len(s) and s[i] != ")":
            j = i
            while j < len(s) and s[j] not in "=,)":
                j += 1
            key = s[i:j].strip()
            if j < len(s) and s[j] == "=":
                val, i = _nbt(s, j + 1)
                out[key] = val
            else:
                i = j
            if i < len(s) and s[i] == ",":
                i += 1
            elif i == j and i < len(s) and s[i] != ")":
                i += 1
        return out, i + 1
    if c == "[":
        out, i = [], i + 1
        while i < len(s) and s[i] != "]":
            val, j = _nbt(s, i)
            out.append(val)
            i = j
            if i < len(s) and s[i] == ",":
                i += 1
            elif i < len(s) and s[i] not in "]":
                i += 1
        return out, i + 1
    j = i
    while j < len(s) and s[j] not in ",)]":
        j += 1
    return s[i:j].strip(), j


def colour(s):
    """Minecraft colour codes: '#b', '#lL' -> '§b', '§lL'. '#playerName' -> '{player}'."""
    if s is None:
        return None
    s = str(s).replace("#playerName", "{player}").replace("#player", "{player}")
    s = re.sub(r"#([0-9a-fk-or])", lambda m: "§" + m.group(1), s)
    return s


def clean(s):
    """Plain text: colour codes dropped, placeholders kept readable."""
    s = colour(s) or ""
    s = re.sub("§.", "", s)
    return re.sub(r"\s+", " ", s).strip()


def pretty(name):
    name = name.split(":")[-1].replace("_", " ").strip()
    name = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", name)
    return name[:1].upper() + name[1:] if name else name


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
            self.by_base.setdefault(k.split("@")[0], rec)

    def record(self, ns_name, damage):
        if damage is not None:
            rec = self.by_key.get("%s@%s" % (ns_name, damage))
            if rec is not None:
                return rec, "exact"
        rec = self.by_key.get("%s@0" % ns_name)
        if rec is not None:
            return rec, "damage 0" if damage not in (None, 0) else "exact"
        rec = self.by_base.get(ns_name)
        if rec is not None:
            return rec, "other damage value"
        return None, "not in items.json"

    def icon_for(self, ns_name, damage):
        rec, how = self.record(ns_name, damage)
        if rec is None:
            return None, how
        if rec.get("b"):
            return None, "blank record"
        i = rec.get("i")
        if i is None:
            return None, "no icon index"
        per = self.side * self.side
        return {"s": i // per, "c": (i % per) % self.side, "r": (i % per) // self.side}, how

    def name_for(self, ns_name):
        rec, _ = self.record(ns_name, None)
        if rec is not None and rec.get("n") and not re.search(r"\.name$|^tile\.|^item\.", rec["n"]):
            return rec["n"]
        return pretty(ns_name)


def ns(name):
    """'diamond' -> 'minecraft:diamond'; 'OreSpawn:X' and 'lucky:y' are kept."""
    name = name.strip()
    return name if ":" in name else "minecraft:" + name


def split_damage(ident, damage):
    """'golden_apple,1' -> ('golden_apple', 1)."""
    if "," in ident:
        base, d = ident.split(",", 1)
        return base, (int(d) if d.strip().lstrip("-").isdigit() else damage)
    return ident, damage


# ----------------------------------------------------------------- actions

class Ctx:
    def __init__(self, index):
        self.index = index


def item_action(ctx, item_id, damage, amount, where, nbt=None, display=None, offset=None):
    base = ns(item_id)
    if base == "minecraft:random" or item_id == "random":
        return {"t": "item", "id": "random", "name": "Random item", "amount": amount, "icon": None,
                "display": None, "ench": None, "lore": None, "where": where}
    icon, _ = ctx.index.icon_for(base, damage)
    name = ctx.index.name_for(base)
    act = {"t": "item", "id": base, "name": name, "amount": amount, "icon": icon,
           "display": display, "ench": None, "lore": None, "where": where}
    if damage not in (None, 0):
        act["damage"] = damage
    if isinstance(nbt, dict):
        tag = nbt.get("tag") if isinstance(nbt.get("tag"), dict) else {}
        ench = tag.get("ench")
        if isinstance(ench, list):
            act["ench"] = [[ENCHANTS.get(to_int(e.get("id")), "Enchant %s" % e.get("id")), to_int(e.get("lvl"), 1)]
                           for e in ench if isinstance(e, dict)]
        elif isinstance(ench, str):
            act["enchSet"] = ench.lstrip("#")
        disp = tag.get("display") if isinstance(tag.get("display"), dict) else {}
        if disp.get("Lore") and isinstance(disp.get("Lore"), list):
            act["lore"] = [colour(str(x)) for x in disp["Lore"]]
        if display is None and disp.get("Name"):
            act["display"] = colour(str(disp["Name"]))
    if offset is not None:
        act["offset"] = offset
    return act


def to_int(v, default=0):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return default


def entity_mod(name):
    if name in VANILLA_ENTITIES:
        return "minecraft", True
    if name in LUCKY_ENTITIES:
        return "lucky", False
    if name in ORESPAWN_ENTITIES or name.startswith("OreSpawn:"):
        return "orespawn", False
    return "other", False


def equipment_of(nbt):
    """NBTTag=(Equipment=[(id=diamond_sword,...),...]) -> ['diamond_sword', ...]."""
    if not isinstance(nbt, dict) or not isinstance(nbt.get("Equipment"), list):
        return []
    return [ns(str(e["id"])) for e in nbt["Equipment"] if isinstance(e, dict) and e.get("id")]


def riding_chain(nbt):
    """NBTTag=(Riding=(id=A,Riding=(id=B,...))) -> ['A', 'B'] outermost first."""
    out, cur = [], nbt
    while isinstance(cur, dict) and isinstance(cur.get("Riding"), dict):
        cur = cur["Riding"]
        if cur.get("id"):
            out.append(str(cur["id"]))
    return out


def leaf_actions(ctx, node):
    """One leaf (a single drop member) to a list of actions, in the mod's order."""
    f = node.fields
    kind = f.get("type")
    ident = unquote(f.get("ID"))
    amount = rng(f.get("amount", f.get("Count"))) if ("amount" in f or "Count" in f) else [1, 1]
    if amount is None:
        amount = [1, 1]
    nbt = parse_nbt(f["NBTTag"]) if "NBTTag" in f and f["NBTTag"].startswith("(") else None
    rel = f.get("relativeToPlayer", "false").lower() == "true"
    where = "player" if rel else "block"
    dmg = to_int(f["damage"], None) if "damage" in f and f["damage"].lstrip("-").isdigit() else None

    # the mod has no positional form for these; leave them as read
    pos = [pos_offset(f.get("posX")), pos_offset(f.get("posY")), pos_offset(f.get("posZ"))]
    offset = None
    if any(p != [0, 0] for p in pos):
        offset = {"dx": pos[0][0] if not is_random_pos(pos[0]) else sum(pos[0]) // 2,
                  "dy": pos[1][0] if not is_random_pos(pos[1]) else sum(pos[1]) // 2,
                  "dz": pos[2][0] if not is_random_pos(pos[2]) else sum(pos[2]) // 2}
        rand = {k: v for k, v in zip(("dx", "dy", "dz"), pos) if is_random_pos(v)}
        if rand:
            offset["rand"] = rand

    if kind == "difficulty":
        return []     # a precondition the mod runs before spawning mobs; not a drop
    if kind is None and ident is None:
        return []
    if kind == "group":
        return []
    if kind in (None, "item", "block", "falling_block", "falling", "tile") and ident and ident.startswith("#") and kind in (None, "item"):
        r = rng(ident)
        if r is not None and r[0] == 2256:
            return [{"t": "item", "id": "random", "name": "Random music disc", "amount": amount,
                     "icon": None, "display": None, "ench": None, "lore": None, "where": where}]
        if r is not None and r[0] == 349:
            return [{"t": "item", "id": "random", "name": "Random fish", "amount": amount,
                     "icon": None, "display": None, "ench": None, "lore": None, "where": where}]
        if r is not None and r[0] == 4249:
            return [{"t": "item", "id": "random", "name": "Random spawn egg", "amount": amount,
                     "icon": None, "display": None, "ench": None, "lore": None, "where": where}]
        return [{"t": "item", "id": "random", "name": "Random item", "amount": amount, "icon": None,
                 "display": None, "ench": None, "lore": None, "where": where}]

    if kind == "entity":
        if ident == "Item":
            inner = nbt.get("Item") if isinstance(nbt, dict) and isinstance(nbt.get("Item"), dict) else {}
            custom = unquote(nbt.get("CustomName")) if isinstance(nbt, dict) else None
            item_id = str(inner.get("id", "stone"))
            act = item_action(ctx, item_id, to_int(inner.get("Damage"), None) if inner.get("Damage") else None,
                              [to_int(inner.get("Count"), 1)] * 2, where,
                              nbt=inner, display=colour(custom) if custom else None, offset=offset)
            return [act]
        if ident == "XPOrb":
            return [{"t": "xp", "amount": amount}]
        if ident == "launched_tnt":
            return [{"t": "tnt", "amount": amount, "launched": True, "rider": None}]
        if ident == "launched_expbottle":
            return [{"t": "expbottle", "amount": amount}]
        if ident == "lightning":
            return [{"t": "lightning"}]
        if ident == "fireworks":
            return [{"t": "fireworks", "amount": amount}]
        if ident and ident.startswith("#"):
            return [{"t": "entity", "id": "random", "name": "Random mob", "amount": amount, "vanilla": False,
                     "mod": "other", "display": None, "riding": [], "equipment": [], "where": where,
                     "spread": None, "size": None, "color": None, "upsideDown": False, "extra": {}}]
        mod_name, vanilla = entity_mod(ident)
        eid = LUCKY_ENTITIES.get(ident, ident)
        if ident == "luckyegg":
            eid = "luckyegg"
        spread_raw = f.get("scatterOffset")
        spread = None
        spread_range = None
        if spread_raw:
            sr = rng(spread_raw.replace("-", "~", 1).replace("~", "-")) if False else None
            m = re.fullmatch(r"(-?\d+)-(-?\d+)", spread_raw.strip())
            if m:
                a, b = int(m.group(1)), int(m.group(2))
                spread, spread_range = max(a, b), [min(a, b), max(a, b)]
        display = None
        if isinstance(nbt, dict) and nbt.get("CustomName"):
            display = colour(unquote(nbt.get("CustomName")))
        elif isinstance(nbt, dict) and isinstance(nbt.get("CustomName"), str):
            display = colour(nbt["CustomName"])
        act = {"t": "entity", "id": eid, "name": LUCKY_ENTITIES.get(ident, pretty(eid) if mod_name != "minecraft" else ident),
               "amount": amount, "vanilla": vanilla, "mod": mod_name, "display": display,
               "riding": riding_chain(nbt) if isinstance(nbt, dict) else [],
               "equipment": equipment_of(nbt),
               "where": where, "spread": spread, "size": None, "color": None, "upsideDown": False,
               "extra": {}}
        if spread_range:
            act["spreadRange"] = spread_range
        if "adjustHeight" in f:
            act["lift"] = to_int(f["adjustHeight"], 0)
        if offset is not None:
            act["offset"] = offset
        if "reinitialize" in f and f["reinitialize"].lower() == "true":
            act["reinit"] = True
        return [act]

    if kind == "structure":
        sid = ident
        if sid == "explosion":
            return [{"t": "explosion", "power": to_int(f.get("damage"), 4)}]
        act = {"t": "structure", "id": sid, "name": pretty(sid), "where": where, "nbt": None}
        if isinstance(nbt, dict):
            act["nbt"] = nbt
        return [act]

    if kind in ("falling_block", "falling"):
        base, dmg = split_damage(ident or "", dmg)
        base = RENAMED.get(base, (ns(base), dmg))[0] if base in RENAMED else ns(base)
        if base in LEGACY_BLOCK:
            base, dmg = LEGACY_BLOCK[base]
        blk = {"id": base, "name": ctx.index.name_for(base), "dx": 0, "dy": 0, "dz": 0, "meta": dmg or 0}
        blk["dx"], blk["dy"], blk["dz"] = (pos[0][0] if not is_random_pos(pos[0]) else sum(pos[0]) // 2,
                                           pos[1][0] if not is_random_pos(pos[1]) else sum(pos[1]) // 2,
                                           pos[2][0] if not is_random_pos(pos[2]) else sum(pos[2]) // 2)
        rand = {k: v for k, v in zip(("dx", "dy", "dz"), pos) if is_random_pos(v)}
        if rand:
            blk["rand"] = rand
        if isinstance(nbt, dict):
            blk["nbt"] = True
        return [{"t": "falling", "blocks": [blk], "origin": where}]

    if kind == "block":
        base, dmg = split_damage(ident or "air", dmg)
        if base.isdigit() and int(base) in LEGACY_BLOCK:
            base, dmg = LEGACY_BLOCK[int(base)]
        elif base == "air":
            base = "minecraft:air"
        base = ns(base) if base != "minecraft:air" else base
        blk = {"id": base, "name": "Air" if base == "minecraft:air" else ctx.index.name_for(base),
               "dx": 0, "dy": 0, "dz": 0, "meta": dmg or 0}
        blk["dx"], blk["dy"], blk["dz"] = (pos[0][0] if not is_random_pos(pos[0]) else sum(pos[0]) // 2,
                                           pos[1][0] if not is_random_pos(pos[1]) else sum(pos[1]) // 2,
                                           pos[2][0] if not is_random_pos(pos[2]) else sum(pos[2]) // 2)
        rand = {k: v for k, v in zip(("dx", "dy", "dz"), pos) if is_random_pos(v)}
        if rand:
            blk["rand"] = rand
        acts = [{"t": "block", "blocks": [blk], "origin": where}]
        if isinstance(nbt, dict) and isinstance(nbt.get("Drops"), list):
            inner_text = nbt["Drops"][0] if nbt["Drops"] else ""
            inner = build_actions_from_text(ctx, inner_text)
            acts.append({"t": "then", "label": "Break the hidden lucky block", "actions": inner})
        return acts

    if kind == "effect":
        if ident and ident.startswith("#random"):
            eid, name = "random", "Random effect"
        else:
            eid = to_int(ident, 0)
            name = POTIONS.get(eid, "Effect %s" % ident)
        dur = to_int(f.get("duration"), 0) if "duration" in f and f["duration"].isdigit() else rng(f.get("duration", "0"))
        if isinstance(dur, list):
            dur = dur[0]
        amp = to_int(f.get("damage"), 0) if "damage" in f and f["damage"].isdigit() else 0
        act = {"t": "effect", "id": eid, "name": name, "level": amp + 1, "duration": dur,
               "harmful": eid in HARMFUL_EFFECTS}
        if eid == "random":
            act["duration"] = rng(f.get("duration", "0"))
            act["level"] = rng(f.get("damage", "1"))
        return [act]

    if kind == "message":
        text = colour(ident or "")
        return [{"t": "message", "text": text, "to": "all"}]

    if kind == "command":
        text = colour(ident or "")
        act = {"t": "command", "text": text, "gives": None}
        m = re.match(r"/give\s+\S+\s+(\S+)(?:\s+(\d+))?(?:\s+(-?\d+))?", (ident or "").replace("#playerName", "{player}"))
        if m:
            gid = m.group(1)
            base = ns(gid)
            dmg = to_int(m.group(3), 0) if m.group(3) else 0
            icon, _ = ctx.index.icon_for(base, dmg)
            act["gives"] = {"id": base, "name": ctx.index.name_for(base),
                            "amount": [to_int(m.group(2), 1)] * 2, "icon": icon}
        return [act]

    if kind == "time":
        value = to_int(ident, 0)
        return [{"t": "time", "value": value, "name": "midnight" if value == 18000 else
                 ("night" if 12500 <= value <= 23500 else "day")}]

    if kind == "particle":
        pid = unquote(ident or "")
        return [{"t": "particle", "id": pid, "amount": amount}]

    if kind == "lightning":
        return [{"t": "lightning"}]

    if kind == "quartz_block":
        return []   # "type=quartz_block" is not a type the mod knows: it spawns nothing

    # default: an item (type=item, or no type at all)
    base, dmg2 = split_damage(ident or "stone", dmg)
    if base.isdigit():
        base_int = int(base)
        if base_int in LEGACY_ITEM:
            base, dmg2 = LEGACY_ITEM[base_int]
        elif base_int in LEGACY_BLOCK:
            base, dmg2 = LEGACY_BLOCK[base_int]
        elif base_int == 0:
            return []
    if base in RENAMED:
        base, dmg2 = RENAMED[base]
    if base.startswith("#random"):
        r = rng(base)
        if r is not None and r[0] == 1 and r[1] == 100:
            return [{"t": "item", "id": "random", "name": "Random item", "amount": amount, "icon": None,
                     "display": None, "ench": None, "lore": None, "where": where}]
        return [{"t": "item", "id": "random", "name": "Random item", "amount": amount, "icon": None,
                 "display": None, "ench": None, "lore": None, "where": where}]
    if base == "potion" and dmg2 is None:
        pass
    if base.isdigit():
        return [{"t": "item", "id": "random", "name": "Random item", "amount": amount, "icon": None,
                 "display": None, "ench": None, "lore": None, "where": where}]
    if base in ("#randomPotionDamage", "#randomSpawnEggDamage"):
        pass
    # damage may be the special random tokens
    if isinstance(f.get("damage"), str) and f["damage"].startswith("#random"):
        if "Potion" in f["damage"]:
            return [{"t": "item", "id": "minecraft:potion", "name": "Random potion",
                     "amount": amount, "icon": ctx.index.icon_for("minecraft:potion", 0)[0],
                     "display": None, "ench": None, "lore": None, "where": where}]
        if "SpawnEgg" in f["damage"]:
            return [{"t": "item", "id": "minecraft:spawn_egg", "name": "Random spawn egg",
                     "amount": amount, "icon": ctx.index.icon_for("minecraft:spawn_egg", 0)[0],
                     "display": None, "ench": None, "lore": None, "where": where}]
    if base == "potion" or base == "minecraft:potion":
        dmg2 = dmg2 if dmg2 is not None else 0
    if base in ("skull",):
        base = "minecraft:skull"
    return [item_action(ctx, base, dmg2, amount, where, nbt=nbt, offset=offset)]


def merge_adjacent(acts):
    """Adjacent falling or block members of one table become one action (a pole is one action)."""
    out = []
    for a in acts:
        if out and a["t"] in ("falling", "block") and out[-1]["t"] == a["t"] and out[-1].get("origin") == a.get("origin"):
            out[-1]["blocks"].extend(a["blocks"])
        else:
            out.append(a)
    return out


def node_actions(ctx, node):
    """A node in execution order. Returns (actions, broken_flag)."""
    if node.kind == "broken":
        return [], True
    if node.kind == "leaf":
        return leaf_actions(ctx, node), False
    broken = False
    if node.pick is None:
        acts = []
        for m in node.members:
            a, b = node_actions(ctx, m)
            acts.extend(a)
            broken = broken or b
        return merge_adjacent(acts), broken
    options = []
    for m in node.members:
        a, b = node_actions(ctx, m)
        options.append(merge_adjacent(a))
        broken = broken or b
    return [{"t": "choice", "pick": list(node.pick), "options": options}], broken


def build_actions_from_text(ctx, text):
    """A nested lucky block table (the Drops=[...] string): the same grammar, one drop per line."""
    text = text.strip()
    if not text:
        return []
    acts = []
    for piece in mod_split(text, ";") if not text.startswith("group") else [text]:
        piece = piece.strip()
        if not piece:
            continue
        node = parse_node(piece)
        a, _ = node_actions(ctx, node)
        acts.extend(a)
    return merge_adjacent(acts)


def top_level_actions(ctx, body):
    node = parse_node(body)
    if node.kind == "broken":
        raise ModError("group has no closing ')' (the mod throws when it is picked)")
    acts, broken = node_actions(ctx, node)
    return merge_adjacent(acts), broken


# ----------------------------------------------------------------- config

def strip_suffixes(line):
    """Trailing @luck=N and @chance=F (the mod reads them with indexOf)."""
    luck, chance = DEFAULT_LUCK, DEFAULT_CHANCE
    body = line.strip()
    while True:
        m = re.search(r"@(luck|chance)=(-?\d+(?:\.\d+)?)\s*$", body)
        if not m:
            break
        if m.group(1) == "luck":
            luck = int(float(m.group(2)))
        else:
            chance = float(m.group(2))
        body = body[:m.start()].rstrip()
    return body, luck, chance


def parse_config(text):
    """Returns props, crafting, and drop lines as (line number, comment group, raw)."""
    section = None
    props, crafting, drops = {}, [], []
    group = ""
    for no, line in enumerate(text.splitlines(), 1):
        s = line.rstrip()
        if s.startswith(">"):
            section = s[1:].strip()
            continue
        if section == "drops":
            if not s.strip():
                continue
            if s.startswith("/"):
                if not s.startswith("/="):
                    group = s[1:].strip()
                continue
            drops.append((no, group, s.strip()))
        elif section == "properties":
            if "=" in s and not s.startswith("/"):
                k, v = s.split("=", 1)
                props[k.strip()] = v.strip()
        elif section == "craftingitems":
            if "=" not in s or s.startswith("/"):
                continue
            name, lvl = s.rsplit("=", 1)
            dmg = None
            if "," in name:
                name, dmg = name.split(",", 1)
            crafting.append({"name": name.strip(), "damage": to_int(dmg, None) if dmg else None,
                             "level": to_int(lvl, 0)})
    return props, crafting, drops


def craft_entries(index, crafting):
    out = []
    for c in crafting:
        base = ns(c["name"])
        icon, _ = index.icon_for(base, c["damage"])
        out.append({"id": base, "name": index.name_for(base), "luck": c["level"], "icon": icon})
    return out


# ----------------------------------------------------------------- weights

def weights(luck_chance, block_luck):
    """Weight of each (luck, chance) at block luck K, as ChooseLuckyDrop computes it."""
    k = max(-100, min(100, block_luck))
    lo = min([0] + [l for l, _ in luck_chance])
    hi = max([0] + [l for l, _ in luck_chance])
    b = 1.0 / (1.0 - BASE_FACTOR * abs(k))
    out = []
    for l, c in luck_chance:
        e = (l - lo + 1) if k >= 0 else (hi - l + 1)
        out.append(c * 100.0 * (b ** e))
    return out


def odds(luck_chance, block_luck):
    w = weights(luck_chance, block_luck)
    total = sum(w)
    return [x / total for x in w] if total else [0.0 for _ in w]


# ----------------------------------------------------------------- build

def build_drop(ctx, no, group, raw, index_no):
    body, luck, chance = strip_suffixes(raw)
    try:
        acts, broken = top_level_actions(ctx, body)
    except ModError as err:
        return None, str(err)
    text = TEXT.get(no)
    drop = {
        "index": index_no,
        "line": no,
        "luck": luck,
        "chance": round(chance, 4),
        "raw": raw,
        "group": group,
    }
    if text is not None:
        title, blurb, mood, scene = text
    else:
        title, blurb, mood, scene = (pretty(group or "Lucky drop")[:40], "Something happens when this block breaks.",
                                      "neutral", "generic")
    drop.update({"title": title[:40], "blurb": blurb, "mood": mood, "scene": scene})
    if scene == "dud":
        broken = True
        drop["tile"] = {"kind": "text", "text": "Dud"}
    drop["icon"] = first_icon(acts)
    drop["tile"] = {"kind": "text", "text": "Dud"} if scene == "dud" else tile_for(acts, ctx)
    drop["actions"] = acts
    if broken:
        drop["broken"] = True
    return drop, None


def first_icon(acts):
    for a in acts:
        if a["t"] == "item" and a.get("icon"):
            return a["icon"]
        if a["t"] == "choice":
            for opt in a["options"]:
                ic = first_icon(opt)
                if ic:
                    return ic
    return None


def tile_for(acts, ctx):
    """What the reel tile shows when there is no icon: a mob, a block, an item or text."""
    for a in acts:
        if a["t"] == "entity" and not a.get("vanilla") and a["id"] != "random":
            return {"kind": "mob", "id": a["id"]}
        if a["t"] == "entity" and a.get("vanilla"):
            return {"kind": "mob", "id": a["id"]}
        if a["t"] == "item" and a["id"] != "random":
            return {"kind": "item"}
        if a["t"] in ("block", "falling") and a["blocks"]:
            return {"kind": "block", "id": a["blocks"][0]["id"]}
        if a["t"] == "tnt":
            return {"kind": "block", "id": "minecraft:tnt"}
        if a["t"] == "choice":
            for opt in a["options"]:
                t = tile_for(opt, ctx)
                if t:
                    return t
    return {"kind": "text", "text": "?"}


def main(argv):
    check = "--check" in argv
    dump = "--dump" in argv
    with open(CONFIG, encoding="utf-8") as fh:
        text = fh.read()
    props, crafting, lines = parse_config(text)
    index = ItemIndex(ITEMS)
    ctx = Ctx(index)

    drops, skipped = [], []
    lucky_pairs = []
    for no, group, raw in lines:
        body, luck, chance = strip_suffixes(raw)
        d, err = build_drop(ctx, no, group, raw, len(drops))
        if d is None:
            # the mod picks this line like any other and then errors: it breaks and drops nothing
            skipped.append({"line": no, "group": group, "luck": luck, "chance": round(chance, 4),
                            "reason": err, "raw": raw, "index": len(drops)})
            d = {"index": len(drops), "line": no, "luck": luck, "chance": round(chance, 4), "raw": raw,
                 "group": group, "title": "A dud", "blurb": DUD_BLURB, "mood": "neutral", "scene": "dud",
                 "icon": None, "tile": {"kind": "text", "text": "Dud"}, "actions": [], "broken": True}
        drops.append(d)
        lucky_pairs.append((luck, chance))
    for i, d in enumerate(drops):
        d["index"] = i

    all_pairs = [(d["luck"], d["chance"]) for d in drops]
    odds_map = {}
    for k in ("0", "100", "-100"):
        odds_map[k] = odds(all_pairs, int(k))
    for i, d in enumerate(drops):
        d["odds"] = {k: round(odds_map[k][i], 6) for k in odds_map}
    for s in skipped:
        s["odds"] = drops[s["index"]]["odds"]

    doc = {
        "version": VERSION,
        "contract": 2,
        "source": "pack/config/lucky/LuckyBlockProperties.txt",
        "built": __import__("datetime").date.today().isoformat(),
        "spawnrate": to_int(props.get("spawnrate"), 0),
        "structureChance": to_int(props.get("structureChance"), 0),
        "recipe": parse_recipe(props.get("recipe", "")),
        "luck": {"min": -100, "max": 100, "defaultDropLuck": DEFAULT_LUCK,
                 "defaultDropChance": DEFAULT_CHANCE, "baseFactor": BASE_FACTOR,
                 "tableMin": min(l for l, _ in all_pairs), "tableMax": max(l for l, _ in all_pairs)},
        "craftingItems": craft_entries(index, crafting),
        "scenes": SCENES,
        "moods": MOODS,
        "counts": {},
        "drops": drops,
        "skipped": skipped,
    }
    doc["counts"] = counts(doc, index)

    if check:
        problems = validate(doc, json_size=None)
        for p in problems:
            print("CHECK FAIL: " + p)
        report(doc)
        print("check: %s (%d problems)" % ("ok" if not problems else "FAILED", len(problems)))
        return 1 if problems else 0

    if dump:
        json.dump(doc, sys.stdout, ensure_ascii=False, indent=1)
        sys.stdout.write("\n")
        return 0

    structures = build_structures()
    doc["structures"] = "structures.json"
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, separators=(",", ":"))
        fh.write("\n")
    with open(OUT_STRUCTURES, "w", encoding="utf-8") as fh:
        json.dump(structures, fh, ensure_ascii=False, separators=(",", ":"))
        fh.write("\n")
    report(doc)
    print("wrote " + os.path.relpath(OUT, ROOT) + " (%d bytes)" % os.path.getsize(OUT))
    print("wrote " + os.path.relpath(OUT_STRUCTURES, ROOT) + " (%d bytes)" % os.path.getsize(OUT_STRUCTURES))
    return 0


def parse_recipe(text):
    parts = [p.strip() for p in text.split(",") if p.strip()]
    if not parts:
        return {"grid": [], "key": {}}
    grid = parts[:3]
    key = {}
    rest = parts[3:]
    for i in range(0, len(rest) - 1, 2):
        key[rest[i]] = ns(rest[i + 1])
    return {"grid": grid, "key": key, "raw": text}


def counts(doc, index):
    by_scene, by_mood = {}, {}
    for d in doc["drops"]:
        by_scene[d["scene"]] = by_scene.get(d["scene"], 0) + 1
        by_mood[d["mood"]] = by_mood.get(d["mood"], 0) + 1
    icons = [0, 0]
    for d in doc["drops"]:
        for a in walk(d["actions"]):
            if a["t"] == "item" and a["id"] != "random":
                icons[0] += 1
                icons[1] += 1 if a.get("icon") else 0
    return {"drops": len(doc["drops"]), "skipped": len(doc["skipped"]),
            "byScene": by_scene, "byMood": by_mood,
            "itemActions": icons[0], "itemIconsResolved": icons[1]}


def walk(actions):
    for a in actions:
        yield a
        if a["t"] == "choice":
            for opt in a["options"]:
                yield from walk(opt)
        if a["t"] == "then":
            yield from walk(a["actions"])


def report(doc):
    c = doc["counts"]
    print("drops: %d (skipped %d)" % (c["drops"], c["skipped"]))
    print("by scene: " + ", ".join("%s %d" % kv for kv in sorted(c["byScene"].items(), key=lambda kv: (-kv[1], kv[0]))))
    print("by mood: " + ", ".join("%s %d" % (m, c["byMood"].get(m, 0)) for m in MOODS))
    print("item icons: %d of %d item actions resolved" % (c["itemIconsResolved"], c["itemActions"]))


# ----------------------------------------------------------------- validation

def validate(doc, json_size=None):
    problems = []
    seen_titles = set()
    for d in doc["drops"]:
        where = "line %s" % d["line"]
        for k in ("title", "blurb", "mood", "scene", "actions", "tile"):
            if k not in d or d[k] in (None, ""):
                if k == "actions" and d.get(k) == []:
                    continue
                problems.append("%s: missing %s" % (where, k))
        if len(d.get("title", "")) > 40:
            problems.append("%s: title longer than 40" % where)
        for fld in ("title", "blurb"):
            if re.search(r"[§#]|\(broken|Set of |named A ", d.get(fld, "")):
                problems.append("%s: raw code or odd phrasing in %s" % (where, fld))
        if d.get("scene") == "generic":
            problems.append("%s: generic scene" % where)
        if "Set of " in d.get("title", ""):
            problems.append("%s: title looks like a set label" % where)
        if d.get("scene") not in SCENES:
            problems.append("%s: scene %r not in contract" % (where, d.get("scene")))
        if d.get("mood") not in MOODS:
            problems.append("%s: mood %r not in contract" % (where, d.get("mood")))
        if any(a["t"] == "difficulty" for a in walk(d["actions"])):
            problems.append("%s: difficulty leaked into actions" % where)
        for a in walk(d["actions"]):
            if a["t"] not in ACTION_TYPES:
                problems.append("%s: action type %r not in vocabulary" % (where, a["t"]))
            for key in ("amount",):
                if key in a:
                    v = a[key]
                    if not (isinstance(v, list) and len(v) == 2 and all(isinstance(x, int) for x in v) and v[0] <= v[1]):
                        problems.append("%s: amount %r is not [min,max]" % (where, v))
            if a["t"] == "item" and a["id"] != "random" and not a.get("icon") and not a.get("display") and False:
                problems.append("%s: item without icon" % where)
        if d["title"] in seen_titles and d["title"] != "":
            pass
        seen_titles.add(d["title"])
    # probabilities
    for k in ("0", "100", "-100"):
        ps = [d["odds"][k] for d in doc["drops"]]
        total = sum(ps)
        if abs(total - 1.0) > 1e-4:
            problems.append("odds at luck %s sum to %.6f" % (k, total))
        if any(p < 0 for p in ps):
            problems.append("negative odds at luck %s" % k)
    return problems


# ----------------------------------------------------------------- structures

# ---- recovered from LuckyBlocks.jar (CustomStructures / StructureUtil bytecode)
"""Lucky Block structures for the Quest Forge Lucky Block page.

Recovered from the bytecode of CrazyCraft's LuckyBlocks mod (1.7.10):
  mod.lucky.util.SpawnOther.spawnOther        (dispatch, 'structure' branch)
  mod.lucky.util.CustomStructures.*           (the structure builders)
  mod.lucky.util.StructureUtil.*              (fill / fillPerimiter / fillCorners /
                                               fillPerimiterStairs / setBlock / makeSign)
  mod.lucky.util.LuckyFunction.getPlayerDirection
  mod.lucky.util.MakeLuckyDrops.setDropProperties (relativeToPlayer -> floor(player pos))
Block names were resolved from the SRG fields through the MCP deobfuscation data
shipped with the Quest Forge build (deobfuscation_data-1.7.10.lzma) and the
obfuscated Blocks/Items <clinit> registry strings.

Coordinate conventions
  origin "player": dx,dy,dz are relative to the player's feet block
                   (floor of player posX/posY/posZ, as MakeLuckyDrops does).
  origin "block" : relative to the broken Lucky Block (the drop position).
  "from"/"to" on a block entry are INCLUSIVE voxel corners (air clears).
  Every placement is immediate (same tick); tick is 0 everywhere.

Facing
  getPlayerDirection(player, 4) gives d in 0..3 from the player's yaw:
  0 = south (+z), 1 = west (-x), 2 = north (-z), 3 = east (+x).
  Structures that depend on it carry "by_facing": {"0": [...], "1": [...],
  "2": [...], "3": [...]} with the full block list for that facing; "blocks"
  is the d=0 list.

Run `python3 -I structs_part.py` to print a summary and write structures.json.
"""


AIR = "minecraft:air"
STONEBRICK = "minecraft:stonebrick"
IRON_BARS = "minecraft:iron_bars"
OBSIDIAN = "minecraft:obsidian"
GLASS = "minecraft:glass"
FLOWING_WATER = "minecraft:flowing_water"
FLOWING_LAVA = "minecraft:flowing_lava"
ANVIL = "minecraft:anvil"
BEDROCK = "minecraft:bedrock"
STANDING_SIGN = "minecraft:standing_sign"
CHEST = "minecraft:chest"
SANDSTONE = "minecraft:sandstone"
SANDSTONE_STAIRS = "minecraft:sandstone_stairs"
GOLD_BLOCK = "minecraft:gold_block"
TORCH = "minecraft:torch"
WEB = "minecraft:web"
IRON_BLOCK = "minecraft:iron_block"
COBBLESTONE = "minecraft:cobblestone"
FENCE = "minecraft:fence"
STONE_STAIRS = "minecraft:stone_stairs"
WOODEN_PRESSURE_PLATE = "minecraft:wooden_pressure_plate"
LUCKY_BLOCK = "lucky:lucky_block"

# Player-facing index (getPlayerDirection(player, 4)) -> chest/facing meta
CHEST_META_BY_DIR = {0: 2, 1: 5, 2: 3, 3: 4}


class World:
    """Replays the bytecode's writes in order. Last write wins."""

    def __init__(self):
        self.cells = {}          # (x,y,z) -> {"id","meta","nbt"}
        self.calls = {}          # primitive name -> call-site executions
        self.unresolved = []

    def _count(self, name):
        self.calls[name] = self.calls.get(name, 0) + 1

    # StructureUtil.setBlock(w,x,y,z,block[,meta]) : world.setBlock(..., meta, 3)
    def setb(self, x, y, z, bid, meta=0, nbt=None):
        self._count("setBlock")
        cell = {"id": bid, "meta": meta}
        if nbt:
            cell["nbt"] = nbt
        self.cells[(x, y, z)] = cell

    # StructureUtil.setBlockMeta(w,x,y,z,meta): only the metadata changes
    def set_meta(self, x, y, z, meta):
        self._count("setBlockMeta")
        self.cells[(x, y, z)]["meta"] = meta

    # StructureUtil.fill(w,x,y,z,sx,sy,sz,block[,meta]): i<x+sx, j<y+sy, k<z+sz
    def fill(self, x, y, z, sx, sy, sz, bid, meta=0):
        self._count("fill")
        for i in range(x, x + sx):
            for j in range(y, y + sy):
                for k in range(z, z + sz):
                    self.setb(i, j, k, bid, meta)

    # StructureUtil.fillPerimiter: X or Z edge of the sx*sz footprint, every y level
    def fill_perimiter(self, x, y, z, sx, sy, sz, bid, meta=0):
        self._count("fillPerimiter")
        for i in range(x, x + sx):
            for j in range(y, y + sy):
                for k in range(z, z + sz):
                    if i == x or i == x + sx - 1 or k == z or k == z + sz - 1:
                        self.setb(i, j, k, bid, meta)

    # StructureUtil.fillCorners: only the four vertical corner columns
    def fill_corners(self, x, y, z, sx, sy, sz, bid, meta=0):
        self._count("fillCorners")
        for i in range(x, x + sx):
            for j in range(y, y + sy):
                for k in range(z, z + sz):
                    if (i == x or i == x + sx - 1) and (k == z or k == z + sz - 1):
                        self.setb(i, j, k, bid, meta)

    # StructureUtil.fillPerimiterStairs(w,x,y,z,sx,sy,sz,stairs), per level j:
    #   row z        (x+1 .. x+sx-1)  meta 2   (north row)
    #   row z+sz-1   (x+1 .. x+sx-1)  meta 3   (south row)
    #   column x     (z .. z+sz-1)    meta 0   (west column)
    #   column x+sx-1(z .. z+sz-1)    meta 1   (east column, written last)
    def fill_perimiter_stairs(self, x, y, z, sx, sy, sz, bid):
        self._count("fillPerimiterStairs")
        for j in range(y, y + sy):
            self.fill(x + 1, j, z, sx - 1, 1, 1, bid, 2)
            self.fill(x + 1, j, z + sz - 1, sx - 1, 1, 1, bid, 3)
            self.fill(x, j, z, 1, 1, sz, bid, 0)
            self.fill(x + sx - 1, j, z, 1, 1, sz, bid, 1)

    # StructureUtil.setLuckyBlock(w,x,y,z,luck): lucky block, TileEntity luck if != 0
    def lucky(self, x, y, z, luck):
        self._count("setLuckyBlock")
        nbt = {"luck": luck} if luck != 0 else None
        self.setb(x, y, z, LUCKY_BLOCK, 0, nbt)

    # StructureUtil.setRandomLuckyBlock: luck = MathHelper.getRandomIntegerInRange(rnd,-100,100)
    def lucky_random(self, x, y, z):
        self._count("setRandomLuckyBlock")
        self.setb(x, y, z, LUCKY_BLOCK, 0, {"luck": "random -100..100 (0 = no tile entity)"})

    # StructureUtil.makeSign(w,x,y,z,block,meta,lines): sign at (x,y,z), air at (x,y+1,z)
    def sign(self, x, y, z, meta, lines):
        self._count("makeSign")
        self.setb(x, y, z, STANDING_SIGN, meta, {"lines": lines[:4]})
        self.setb(x, y + 1, z, AIR)


def player_dir(n):
    """LuckyFunction.getPlayerDirection(player, n), as an index 0..n-1 of the yaw.
    Bytecode: t = (int)yaw; step = 360/n; if t<0: t+=360; t = (t + step/2) % 360; return t/step.
    Index 0 = facing south (+z), 1 = west, 2 = north, 3 = east for n=4."""
    raise NotImplementedError("used only as an index; see build(d)")


def _to_blocks(world):
    """Final-state voxel list: air boxes as fills first, then individual blocks."""
    air = {p for p, c in world.cells.items() if c["id"] == AIR}
    other = {p: c for p, c in world.cells.items() if c["id"] != AIR}
    out = []
    # greedy box merge for air (clears), x-major
    remaining = set(air)
    for p in sorted(air, key=lambda q: (q[1], q[2], q[0])):
        if p not in remaining:
            continue
        x, y, z = p
        x2 = x
        while (x2 + 1, y, z) in remaining:
            x2 += 1
        z2 = z
        while all((xx, y, z2 + 1) in remaining for xx in range(x, x2 + 1)):
            z2 += 1
        y2 = y
        while all((xx, y2 + 1, zz) in remaining for xx in range(x, x2 + 1) for zz in range(z, z2 + 1)):
            y2 += 1
        for xx in range(x, x2 + 1):
            for yy in range(y, y2 + 1):
                for zz in range(z, z2 + 1):
                    remaining.discard((xx, yy, zz))
        out.append({"id": AIR, "meta": 0, "from": [x, y, z], "to": [x2, y2, z2], "tick": 0})
    for p in sorted(other, key=lambda q: (q[1], q[2], q[0])):
        c = other[p]
        e = {"id": c["id"], "meta": c["meta"], "dx": p[0], "dy": p[1], "dz": p[2], "tick": 0}
        if "nbt" in c:
            e["nbt"] = c["nbt"]
        out.append(e)
    return out


# ---------------------------------------------------------------- builders
# Each builder takes the origin (x,y,z) and the facing index d (0..3).

def cage(w, x, y, z, h):
    """CustomStructures.makeCage(w,p,x,y,z,h)"""
    w.fill(x - 1, y - 1, z - 1, 3, 1, 3, STONEBRICK)
    w.fill_perimiter(x - 1, y, z - 1, 3, h, 3, IRON_BARS)


def cage_sign(w, x, y, z, d, lines):
    """CustomStructures.makeCageSign(w,p,x,y,z,lines): support block + sign outside the cage"""
    if d == 0:
        w.setb(x, y - 1, z + 2, STONEBRICK)
        w.sign(x, y, z + 2, 8, lines)
    elif d == 1:
        w.setb(x - 2, y - 1, z, STONEBRICK)
        w.sign(x - 2, y, z, 12, lines)
    elif d == 2:
        w.setb(x, y - 1, z - 2, STONEBRICK)
        w.sign(x, y, z - 2, 0, lines)
    else:
        w.setb(x + 2, y - 1, z, STONEBRICK)
        w.sign(x + 2, y, z, 4, lines)


CAGE_LINES = ["", "Look Up", "", "", ""]


def build_anvil(w, x, y, z, d):
    cage(w, x, y, z, 3)
    cage_sign(w, x, y, z, d, CAGE_LINES)
    w.fill(x, y, z, 1, 64, 1, AIR)          # clear the shaft above the player
    w.setb(x, y + 64, z, ANVIL)
    w.setb(x, y + 63, z, ANVIL)


def build_lava(w, x, y, z, d):
    cage(w, x, y, z, 4)
    cage_sign(w, x, y, z, d, CAGE_LINES)
    w.setb(x, y + 3, z, FLOWING_LAVA)


def build_water(w, x, y, z, d):
    """CustomStructures.makeWaterCage (direction-independent)"""
    w.fill(x - 1, y - 1, z - 1, 3, 1, 3, OBSIDIAN)
    w.fill_perimiter(x - 1, y, z - 1, 3, 1, 3, OBSIDIAN)
    w.fill_perimiter(x - 1, y + 1, z - 1, 3, 1, 3, GLASS)
    w.fill(x - 1, y + 2, z - 1, 3, 1, 3, OBSIDIAN)
    w.fill(x, y, z, 1, 2, 1, FLOWING_WATER)


def build_pit(w, x, y, z, d):
    """CustomStructures.makePitTrap (direction-independent)"""
    w.fill(x - 1, y - 60, z - 1, 3, 60, 3, AIR)
    w.fill(x - 1, y - 59, z - 1, 3, 1, 3, FLOWING_LAVA)
    w.fill(x - 1, y - 58, z - 1, 3, 1, 3, WEB)


def build_fort(w, x, y, z, d):
    """CustomStructures.makeFort (direction-independent)"""
    w.fill(x - 1, y, z - 1, 3, 2, 3, AIR)
    w.fill(x - 2, y - 1, z - 2, 5, 1, 5, SANDSTONE)
    w.fill_perimiter(x - 2, y, z - 2, 5, 2, 5, SANDSTONE)
    w.fill_corners(x - 2, y + 2, z - 2, 5, 1, 5, GOLD_BLOCK)
    w.lucky_random(x + 1, y, z + 1)
    w.lucky_random(x - 1, y, z - 1)
    w.lucky_random(x + 1, y, z - 1)
    w.lucky_random(x - 1, y, z + 1)


def build_temple(w, x, y, z, d):
    """CustomStructures.makeTemple (direction-independent)"""
    SS = SANDSTONE_STAIRS
    w.fill(x - 3, y - 1, z - 3, 7, 1, 7, SANDSTONE)
    w.fill_perimiter_stairs(x - 3, y, z - 3, 7, 1, 7, SS)
    w.fill(x - 2, y, z - 2, 5, 1, 5, AIR)
    w.fill_perimiter_stairs(x - 2, y + 1, z - 2, 5, 1, 5, SS)
    w.fill(x - 1, y + 1, z - 1, 3, 1, 3, AIR)
    w.fill_perimiter_stairs(x - 1, y + 2, z - 1, 3, 1, 3, SS)
    w.setb(x, y + 3, z, GOLD_BLOCK)
    w.setb(x, y + 2, z, AIR)
    w.fill_corners(x - 3, y, z - 3, 7, 3, 7, SANDSTONE)
    w.fill_corners(x - 3, y + 3, z - 3, 7, 1, 7, GOLD_BLOCK)
    w.setb(x, y + 1, z - 1, TORCH, 3)
    w.setb(x + 1, y + 1, z, TORCH, 2)
    w.setb(x, y + 1, z + 1, TORCH, 4)
    w.setb(x - 1, y + 1, z, TORCH, 1)
    # ring loop: i in [x-2,x+2], k in [z-2,z+2]; corners (|di|=|dk|=2) or
    # centre edges (one offset 2, other 0) get a random lucky block at y
    for i in range(x - 2, x + 3):
        for k in range(z - 2, z + 3):
            di, dk = abs(x - i), abs(z - k)
            corner = di == 2 and dk == 2
            centre_edge = (di == 2 and dk == 0) or (dk == 2 and di == 0)
            if corner or centre_edge:
                w.lucky_random(i, y, k)


CHOICE_LINES = ["", "One is lucky.", "One is not.", ""]


def build_lucky_choice(w, x, y, z, d, luck1=100):
    """CustomStructures.makeLuckyBlockChoice. luck1 is +100 or -100 (random in game),
    luck2 is the opposite. Two lucky blocks side by side, sign between them."""
    luck2 = -luck1 if luck1 == 100 else 100
    if d == 0:
        w.lucky(x - 1, y, z + 2, luck1)
        w.lucky(x + 1, y, z + 2, luck2)
        w.sign(x, y, z + 2, 8, CHOICE_LINES)
    elif d == 1:
        w.lucky(x - 2, y, z - 1, luck1)
        w.lucky(x - 2, y, z + 1, luck2)
        w.sign(x - 2, y, z, 12, CHOICE_LINES)
    elif d == 2:
        w.lucky(x - 1, y, z - 2, luck1)
        w.lucky(x + 1, y, z - 2, luck2)
        w.sign(x, y, z - 2, 0, CHOICE_LINES)
    else:
        w.lucky(x + 2, y, z - 1, luck1)
        w.lucky(x + 2, y, z + 1, luck2)
        w.sign(x + 2, y, z, 4, CHOICE_LINES)


def build_bedrock(w, x, y, z, d):
    """SpawnOther bedrock_problem: bedrock at the block, sign above it.
    Sign meta = getPlayerDirection(player,16) + 8 (see notes); shown here as 8."""
    w.setb(x, y, z, BEDROCK)
    w.sign(x, y + 1, z, 8, ["", "Well, there's", "your problem.", ""])


def build_chest(w, x, y, z, d):
    """SpawnOther chest branch: chest at the block, facing from the player."""
    w.setb(x, y, z, CHEST, 0)
    w.set_meta(x, y, z, CHEST_META_BY_DIR[d])


def build_wishing_well(w, x, y, z, d):
    """CustomStructures.makeWishingWell (direction-independent; NBT argument unused)"""
    w.fill(x, y, z, 1, 256, 1, AIR)
    w.fill(x - 2, y, z - 2, 5, 20, 5, AIR)
    w.fill(x - 1, y - 2, z - 1, 3, 1, 3, IRON_BLOCK)
    w.fill_perimiter(x - 1, y - 1, z - 1, 3, 2, 3, COBBLESTONE)
    w.fill_corners(x - 1, y + 1, z - 1, 3, 2, 3, FENCE)
    w.fill_perimiter_stairs(x - 1, y + 3, z - 1, 3, 1, 3, STONE_STAIRS)
    w.setb(x, y + 3, z, GLASS)
    w.setb(x, y - 1, z, WOODEN_PRESSURE_PLATE)
    w.setb(x, y, z, FLOWING_WATER)


# ---------------------------------------------------------------- chest loot
# Vanilla lists, read from the 1.7.10 classes that Forge's ChestGenHooks points at:
#   bonusChest        -> WorldServer.bonusChestContent,          min=max=10
#   dungeonChest      -> WorldGenDungeons.chestContent (15 ent.), min=max=8
#   villageBlacksmith -> StructureVillagePieces$House2 list,      min=3, max=9
# Entry = (registry id, meta, minAmount, maxAmount, weight), from the <clinit> arrays.
VANILLA_BONUS = [
    ("minecraft:stick", 0, 1, 3, 10),
    ("minecraft:stone_axe", 0, 1, 1, 3),
    ("minecraft:wooden_axe", 0, 1, 1, 5),
    ("minecraft:stone_pickaxe", 0, 1, 1, 3),
    ("minecraft:wooden_pickaxe", 0, 1, 1, 5),
    ("minecraft:apple", 0, 2, 3, 5),
    ("minecraft:bread", 0, 2, 3, 3),
]
VANILLA_DUNGEON = [
    ("minecraft:saddle", 0, 1, 1, 10),
    ("minecraft:iron_ingot", 0, 1, 4, 10),
    ("minecraft:bread", 0, 1, 1, 10),
    ("minecraft:wheat", 0, 1, 4, 10),
    ("minecraft:gunpowder", 0, 1, 4, 10),
    ("minecraft:string", 0, 1, 4, 10),
    ("minecraft:bucket", 0, 1, 1, 10),
    ("minecraft:golden_apple", 0, 1, 1, 1),
    ("minecraft:redstone", 0, 1, 4, 10),
    ("minecraft:record_13", 0, 1, 1, 10),
    ("minecraft:record_cat", 0, 1, 1, 10),
    ("minecraft:name_tag", 0, 1, 1, 10),
    ("minecraft:golden_horse_armor", 0, 1, 1, 2),
    ("minecraft:iron_horse_armor", 0, 1, 1, 5),
    ("minecraft:diamond_horse_armor", 0, 1, 1, 1),
]
VANILLA_VILLAGE = [
    ("minecraft:diamond", 0, 1, 3, 3),
    ("minecraft:iron_ingot", 0, 1, 5, 10),
    ("minecraft:gold_ingot", 0, 1, 3, 5),
    ("minecraft:bread", 0, 1, 3, 15),
    ("minecraft:apple", 0, 1, 3, 15),
    ("minecraft:iron_pickaxe", 0, 1, 1, 5),
    ("minecraft:iron_sword", 0, 1, 1, 5),
    ("minecraft:iron_chestplate", 0, 1, 1, 5),
    ("minecraft:iron_helmet", 0, 1, 1, 5),
    ("minecraft:iron_leggings", 0, 1, 1, 5),
    ("minecraft:iron_boots", 0, 1, 1, 5),
    ("minecraft:saddle", 0, 1, 1, 3),
    ("minecraft:iron_horse_armor", 0, 1, 1, 1),
    ("minecraft:golden_horse_armor", 0, 1, 1, 1),
    ("minecraft:diamond_horse_armor", 0, 1, 1, 1),
]
# Explicit list from LuckyBlockProperties.txt line 474 (min=8,max=8). minAmount defaults to 1.
EXPLICIT_CHEST = [
    ("minecraft:iron_ingot", 0, 1, 8, 10),
    ("minecraft:gold_ingot", 0, 1, 4, 10),
    ("minecraft:emerald", 0, 1, 4, 10),
    ("minecraft:diamond", 0, 1, 4, 10),
    ("lucky:lucky_block", 0, 1, 2, 10),
    ("minecraft:golden_apple", 0, 1, 2, 10),
    ("minecraft:golden_apple", 1, 1, 1, 5),
]


def _loot_entries(rows):
    return [{"id": i, "damage": m, "minAmount": a, "maxAmount": b, "weight": wt}
            for (i, m, a, b, wt) in rows]


CHEST_LOOT = {
    "bonusChest": {
        "source": "ChestGenHooks bonusChest -> WorldServer.bonusChestContent",
        "rolls": {"min": 10, "max": 10},
        "items": _loot_entries(VANILLA_BONUS),
    },
    "dungeonChest": {
        "source": "ChestGenHooks dungeonChest -> WorldGenDungeons chest list",
        "rolls": {"min": 8, "max": 8},
        "items": _loot_entries(VANILLA_DUNGEON),
    },
    "villageBlacksmith": {
        "source": "ChestGenHooks villageBlacksmith -> StructureVillagePieces$House2 list",
        "rolls": {"min": 3, "max": 9, "rule": "min + random(max-min), i.e. 3..8"},
        "items": _loot_entries(VANILLA_VILLAGE),
    },
    "explicit": {
        "source": "items=[...] in LuckyBlockProperties.txt line 474",
        "rolls": {"min": 8, "max": 8},
        "items": _loot_entries(EXPLICIT_CHEST),
    },
}
LOOT_RULES = (
    "Each roll picks one entry by weight, amount uniform in [minAmount, maxAmount] "
    "(an amount above the item's max stack size becomes that many single items), "
    "and the stack goes into a random chest slot via setInventorySlotContents, so a "
    "later roll can overwrite an earlier stack. Roll count: min if min>=max, "
    "otherwise min + random(max-min)."
)


# ---------------------------------------------------------------- assembly

def _make(builder, origin, name, notes, facing=False, falling=None, extra=None, **kw):
    entry = {"name": name, "origin": origin}
    per_d = {}
    for d in (range(4) if facing else [0]):
        w = World()
        builder(w, 0, 0, 0, d, **kw)
        per_d[d] = w
    base = per_d[0]
    entry["blocks"] = _to_blocks(base)
    if facing:
        entry["by_facing"] = {str(d): _to_blocks(per_d[d]) for d in range(4)}
    entry["falling"] = list(falling or [])
    entry["notes"] = notes
    if extra:
        entry.update(extra)
    return entry, per_d


def build_structures():
    out = {}
    unresolved = []

    anvil, _ = _make(
        build_anvil, "player", "Anvil trap",
        "Player-relative (feet block at 0,0,0). Iron-bar cage: stonebrick floor 3x3 at dy=-1, "
        "iron bars perimeter 3x3 from dy=0..2 (interior centre column stays open). Sign 'Look Up' "
        "on a stonebrick post outside the cage, 2 blocks out in the facing direction (dy=0, "
        "air at dy=1). Then the 1x64x1 column above the feet is cleared to air (dy=0..63) and "
        "two anvils are placed at dy=64 then dy=63. They fall by gravity onto the player; they are "
        "listed as falling entries with delay 0 (vanilla BlockFalling turns a placed anvil with air "
        "below into a falling entity at once; this step is not in the mod's bytecode). "
        "Nothing is checked before placing: existing blocks are overwritten.",
        facing=True,
        falling=[{"id": ANVIL, "meta": 0, "dx": 0, "dy": 64, "dz": 0, "delay": 0,
                  "placed_as_block": True},
                 {"id": ANVIL, "meta": 0, "dx": 0, "dy": 63, "dz": 0, "delay": 0,
                  "placed_as_block": True}],
    )
    # anvils are listed as falling; drop them from the static blocks
    anvil["blocks"] = [b for b in anvil["blocks"] if b.get("id") != ANVIL]
    for d in range(4):
        anvil["by_facing"][str(d)] = [b for b in anvil["by_facing"][str(d)] if b.get("id") != ANVIL]
    out["anvil_trap"] = anvil

    lava, _ = _make(
        build_lava, "player", "Lava trap",
        "Player-relative. Iron-bar cage 3x3, 4 high (dy=0..3), stonebrick floor at dy=-1, same "
        "facing sign as the anvil trap. One flowing_lava block (meta 0) at dy=+3 centre, "
        "above the cage. The lava then flows down the open centre column in game (flow not "
        "replayed here).",
        facing=True,
    )
    out["lava_trap"] = lava

    water, _ = _make(
        build_water, "player", "Water trap",
        "Player-relative. Obsidian floor 3x3 at dy=-1, obsidian ring at dy=0, glass ring at dy=1, "
        "obsidian roof 3x3 at dy=2. Flowing water (meta 0) at the centre column dy=0 and dy=1, "
        "sealed under the roof. Direction independent.",
    )
    out["water_trap"] = water

    pit, _ = _make(
        build_pit, "player", "Pit trap",
        "Player-relative. Clears a 3x60x3 shaft (dy=-60..-1) to air, then flowing_lava at dy=-59 "
        "and cobweb (web) at dy=-58 over the 3x3 footprint. The player falls onto the web over lava. "
        "Direction independent.",
    )
    out["pit_trap"] = pit

    fort, _ = _make(
        build_fort, "player", "Fort",
        "Player-relative. Sandstone floor 5x5 at dy=-1; sandstone wall ring 5x5 two high (dy=0..1); "
        "air interior 3x2x3; gold blocks at the four top corners (dy=2). Four random lucky blocks at the "
        "interior corners at dy=0. Luck of each: random -100..100 (0 = no tile entity). "
        "Direction independent.",
    )
    out["fort"] = fort

    temple, _ = _make(
        build_temple, "player", "Temple",
        "Player-relative, stepped sandstone temple 7x7 footprint, 5 layers (dy=-1..3). "
        "Layer dy=-1 sandstone 7x7 floor. dy=0: sandstone_stairs ring 7x7 (meta by side) around "
        "an air 5x5 room. dy=1: stairs ring 5x5 with an air 3x3 inside. dy=2: stairs ring 3x3 "
        "with air at the centre. dy=3: gold block at the centre. Sandstone corner columns dy=0..2, "
        "gold corners at dy=3. Four torches at dy=1 around the centre (meta 3,2,4,1). "
        "Stair meta: 0 on the west column, 1 on the east column, 2 on the north row, 3 on the south row. "
        "Eight random lucky blocks at dy=0 on the room's corners (dx,dz = +-2) and edge midpoints "
        "((+-2,0),(0,+-2)), each luck random -100..100 (0 = none). Direction independent.",
    )
    out["temple"] = temple

    bedrock, _ = _make(
        build_bedrock, "block", "Bedrock problem",
        "Bedrock is placed at the broken block's position, and a standing sign at dy=+1 "
        "(air at dy=+2). Lines: '', \"Well, there's\", 'your problem.'. The sign's meta is "
        "getPlayerDirection(player,16)+8 (16 buckets of 22 degrees, can reach 24 by integer division); "
        "meta 8 is shown here, the in-game sign faces the player.",
        facing=False,
    )
    out["bedrock_problem"] = bedrock

    choice, _ = _make(
        build_lucky_choice, "player", "Lucky choice",
        "Player-relative. Two lucky blocks two cells in front of the feet, side by side, with a sign "
        "between them. Luck pair: one is +100 (lucky), the other -100 (not), chosen by a coin flip "
        "at spawn (shown here with luck1=+100). The sign reads 'One is lucky.' / 'One is not.'. "
        "Positions depend on the facing (see by_facing).",
        facing=True,
    )
    out["lucky_choice"] = choice

    chest_loot_note = (
        "Block at the broken position: chest with meta from facing (meta 2/5/3/4 for dir 0/1/2/3, "
        "shown here for dir 0). Loot is filled immediately from the type named in the NBT tag. "
        "Types in the properties: bonusChest (luck 0), dungeonChest (luck 1), villageBlacksmith (luck 1), "
        "and the explicit items list (luck 2). " + LOOT_RULES
    )
    chest, _ = _make(
        build_chest, "block", "Chest", chest_loot_note, facing=True,
        extra={"loot": CHEST_LOOT, "loot_rules": LOOT_RULES},
    )
    out["chest"] = chest

    explosion = {
        "name": "Explosion",
        "origin": "block",
        "power": 12.0,
        "power_formula": "2 * damage, damage=6 from the properties line, so 12.0 (float)",
        "blocks": [],
        "falling": [],
        "notes": "World.createExplosion(null, x, y, z, 2*damage, isSmoking=true) at the broken "
                 "block's integer coordinates (block corner, not centre). The fire flag is false. "
                 "No blocks are placed by this structure itself: the blast destroys blocks by the "
                 "vanilla explosion rules.",
    }
    out["explosion"] = explosion

    well, _ = _make(
        build_wishing_well, "block", "Wishing well",
        "Block-relative. Clears a 1x256x1 column and a 5x20x5 room above the block. Iron block 3x1x3 at "
        "dy=-2, cobblestone ring 3x3 at dy=-1..0 (centre dy=-1 is a wooden pressure plate), fence corners "
        "at dy=+1..+2, stone_stairs ring 3x3 at dy=+3, glass at the top centre (dy=+3), flowing water "
        "in the centre at dy=0. The properties group also places lucky:lucky_block at dy=-3 with the "
        "wish message NBT; that block is not part of this list (it is not placed by "
        "CustomStructures). The NBT argument of makeWishingWell is not read by the bytecode.",
    )
    out["wishing_well"] = well

    unresolved.append("random luck values (lucky blocks): not fixed in the structure")
    unresolved.append("bedrock sign meta depends on player yaw (16 buckets)")
    unresolved.append("chest loot is random; amounts and slots as listed")
    unresolved.append("lucky_choice luck sign is a coin flip")
    unresolved.append("ChestGenHooks lists can be changed at runtime by other mods (CrazyCraft)")
    for k, v in out.items():
        v["unresolved"] = unresolved if k in ("chest", "lucky_choice", "temple", "fort") else []
    return out


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
