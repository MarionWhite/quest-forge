#!/usr/bin/env python3
"""Rank every modded block by how often players see it, and pair each with its texture files.

    py -3.10 -I tools/textures/rank_modded_blocks.py [--scans "C:\\qfs\\scan-n*.json"] [--mods DIR ...]
        [--out docs/design/textures/modded-blocks.tsv] [--only C:\\qfb\\textures\\top-modded.txt --top 150]
        [--sheet C:\\qfb\\textures\\sheet-modded-top.png]

The method is docs/design/textures/modded-blocks.md. Four signals, each scaled to 0-10:

  W worldgen   measured blocks per chunk from the ore survey's raw region scans (4 seeds, 30
               dimensions, every block counted: ores, biome terrain, trees, dungeons), per dimension
               weighted by how much players visit it (DIM_WEIGHT), on a log scale, times an exposure
               factor for blocks that sit at the surface (mean Y near the dimension's ground level).
               Biomes O' Plenty is not in the scans (it joins with the designed world), so its terrain
               blocks get an estimate from which biome classes reference them and how much of the
               continent plan those biomes cover.
  C craft      recipes that produce the block and recipes that use it (item dump), log scale.
  B base       a hand table: blocks players place in a base and stare at (storage, machines,
               decoration), tier 0-3.
  Q quests     quest-book references: tasks weigh most, icons next, rewards least.

  score = 0.45 W + 0.20 C + 0.25 B + 0.10 Q

Textures: each creative stack of the block (block@meta) is paired with a texture file in the mod's
jar by (a) name: registry name, display name and unlocalised name against the file name, and (b)
colour: the item dump's 32px inventory icon is the block rendered as an isometric cube whose mean
colour is 0.665 x the texture's (measured on vanilla stone and gold ore), so the nearest texture by
mean colour is a strong tie-breaker. Confidence is recorded per row: high / mid / low (colour +
name), name-high / name-mid (no cube icon: a model or a flat item), none.

The scans live outside the repo (C:\\qfs). When they are present the script refreshes
docs/design/textures/data/worldgen-modded.tsv, the committed per-dimension rates it reads otherwise.
"""
import argparse
import collections
import glob
import io
import json
import math
import os
import re
import sys
import zipfile

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
LIVE = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), ".crazycraft4")
DATA = os.path.join(REPO, "docs", "design", "textures", "data")

# How much of a player's time each dimension gets. Overworld = 1. From the quest book: Twilight is
# chapter 3 (93 mentions, a location task), the End chapter 6, OreSpawn chapter 7 (Crystal dimension
# quest), TragicMC chapter 8 (Synapse, 34 mentions; Collision), Witchery's Spirit World (Dream) in
# chapters 4-5. Legends' and OreSpawn's other dimensions have no quests. CompactMachines (4) is a
# base block, scored under B instead.
DIM_WEIGHT = {"0": 1.0, "7": 0.8, "-1": 0.5, "1": 0.5, "2": 0.35, "3": 0.3, "84": 0.25, "-37": 0.15, "58": 0.15,
              "80": 0.1, "81": 0.1, "82": 0.1, "83": 0.1, "85": 0.1, "-42": 0.1,
              "30": 0.08, "31": 0.08, "32": 0.08, "33": 0.08, "34": 0.08, "35": 0.08, "36": 0.08,
              "50": 0.05, "51": 0.08, "53": 0.08, "55": 0.05, "66": 0.08, "-38": 0.03, "-39": 0.03, "4": 0.0}
# Ground level per dimension, for the exposure factor (blocks whose mean Y is within 12 of it, or
# above, are seen from the surface). Twilight's terrain sits around Y 31.
GROUND = collections.defaultdict(lambda: 63, {"7": 31, "-1": 64, "1": 60, "2": 64, "3": 64, "84": 63})

# Base-building tier by (mod id, regex on the registry path). 3 = almost every base has it and looks
# at it daily; 2 = common in a base or machine room; 1 = placed sometimes. Everything else 0.
BASE = [
    ("EnderStorage", r"enderChest", 3), ("IronChest", r"BlockIronChest", 3), ("StorageDrawers", r"fullDrawers|halfDrawers|compDrawers|controller|trim", 3),
    ("CompactMachines", r"innerwall|machine|interface", 3), ("ProjectE", r"transmutation_table|condenser|collector|relay|alchemical_chest", 3),
    ("Railcraft", r"^track$|^machine\.(alpha|beta)$|^cube$|^glass$|^post|^brick\.|^stair$|^slab$|^wall\.|^detector$|^signal|^anchor", 2),
    ("ProjectE", r"dm_|rm_|interdiction|novaCatalyst|alchemical_coal|mobius|aeternalis", 1),
    ("witchery", r"altar|cauldron|witchesoven|distillery|poppetshelf|spinningwheel|kettle|bloodcrucible|brazier|candelabra|chalice|glowglobe|shadedglass|witchwood|witchlog|witchleaves|stairs|slab|door", 2),
    ("BiblioCraft", r"Bookcase|Shelf|Potion|Lamp|Lantern|Table|Desk|Case|Rack|Stand|Label|Clock|Painting|Frame|Pedestal|Typewriter|Seat|Press|Chair|Bell|Map|Disc|Cabinet|Fancy", 2),
    ("chisel", r"marble|limestone|factory|laboratory|technical|tyrian|futura|carpet|antiBlock|glass|holystone|concrete|iron|gold|diamond|lavastone|granite|diorite|andesite|cobblestone|stonebrick|sandstone|temple|voidstone|cloud|bookshelf|planks|paper|hex|dirt|ice|netherbrick|obsidian|quartz|redstone|lapis|emerald|coal|bricks|arcane|warning", 2),
    ("legends", r"concrete|granite|diorite|andesite|Smooth$|lantern|seaLantern|prismarine|redSandstone|smoothStone|boneBlock|basalt|blackstone|quartzBricks|chiseled|cracked|lightningBlock", 1),
    ("legends", r"heromaker|microscope|blastFurnace|smoker|smithing|batcomputer|monitor|cable", 2),
    ("OpenBlocks", r"tank|elevator|sponge|ladder|guide|blockbreaker|blockplacer|vacuumhopper|xpbottler|autoanvil|autoenchantmenttable|canvas|path|fan|beartrap|sprinkler|bigbutton|flag|paintcan", 1),
    ("securitycraft", r"reinforced|keypad|laserBlock|usernameLogger|alarm|retinalScanner|inventoryScanner|portableRadar|ironFence|cageTrap|unbreakable|frame|claymore|protecto|motionActivated|securityCamera|disguised|blockPocket|keycard", 1),
    ("malisisdoors", r".*", 1), ("CarpentersBlocks", r".*", 1), ("cfm", r".*", 1), ("props", r".*", 1),
    ("TwilightForest", r"TFPlank|TFTowerStone|TFMazestone|TFUncraftingTable|TFFireflyJar|TFNagastone|AuroraBrick|CastleBrick|TFTrophyPedestal|TFUnderBrick|KnightBrick", 1),
    ("TragicMC", r"Planks|darkStone|darkCobblestone|lightStone|lightCobblestone|darkSandstone|darkenedQuartz|celledLamp|starCrystal|wrappedLamp|boneBlock|erodedStone", 1),
    ("HardcoreEnderExpansion", r"ravaged_brick|obsidian_special|obsidian_end|laboratory|essence_altar|enhanced_brewing|decomposition|extraction|experience|accumulation|endium_block|void_chest|transport_beacon", 1),
    ("hopperductmod", r".*", 1), ("HopperDuctMod", r".*", 1), ("ChickenChunks", r".*", 1), ("enderutilities", r".*", 1),
    ("adventurebackpack", r".*", 1), ("SSTOW", r".*", 1), ("psychedelicraft", r"barrel|mash_tub|still|flask|dryingTable|bottleRack|glassChalice", 1),
    ("ArchimedesShipsPlus", r".*", 1), ("customnpcs", r"carpentry|npcCarpentyBench|banner|tallLamp|coffin|border|mailbox|waypoint|redstoneBlock|copy|chair|couch|stool|table|scripted", 1),
    ("icbmclassic", r"concrete|glass|reinforced|camouflage|spikes|launcher|radar|emp", 1),
    ("OreSpawn", r"CrystalWorkbench|CrystalFurnace|Crystal(Pink|Planks)|Block(Uranium|Titanium|Amethyst|Ruby|Teleport|MobzillaScale|EnderPearl|EyeOfEnder)|DuctTape|Pizza", 1),
    ("Chisel", r".*", 1), ("betterquesting", r".*", 1), ("transformers", r"energon_cube|transformium_block|energon_ore_block|ground_bridge|teleporter", 1),
    ("qfcontent", r".*", 2), ("StorageDrawers", r".*", 2), ("Railcraft", r".*", 1), ("BiblioCraft", r".*", 1), ("EnderStorage", r".*", 2),
    ("FoodPlus", r"Oven|Grill|Mixer|Chopper|Juicer|Fermenter|Fridge|Toaster|Blender|Press|Cooker|Barrel|Table", 1),
]
BASE = [(m, re.compile(r), t) for m, r, t in BASE]

# Biomes O' Plenty: not in the survey scans (it joins with the designed world), so each BoP block
# field gets a blocks-per-chunk estimate for the biomes whose classes reference it (the class scan in
# this script), times those biomes' share of the continent plan. [estimate]
BOP_FIELD_RATE = {  # blocks per chunk inside a biome that uses the field, and whether it is surface
    "hardDirt": 2500, "hardSand": 2500, "cragRock": 2500, "driedDirt": 2500, "ashStone": 2500, "hardIce": 2500,
    "originGrass": 256, "newBopGrass": 256, "newBopDirt": 700, "mud": 400, "ash": 800, "flesh": 800,
    "overgrownNetherrack": 256, "bopGrass": 256,
    "logs1": 60, "logs2": 60, "logs3": 60, "logs4": 60, "leaves1": 300, "leaves2": 300, "leaves3": 300, "leaves4": 300,
    "colorizedLeaves1": 300, "colorizedLeaves2": 300, "appleLeaves": 80, "persimmonLeaves": 80,
    "foliage": 40, "flowers": 12, "flowers2": 12, "plants": 20, "gemOre": 2.5, "treeMoss": 10, "ivy": 10,
    "flowerVine": 10, "bamboo": 40, "moss": 5, "mushrooms": 3, "coral1": 20, "coral2": 20, "stoneFormations": 3,
    "rocks": 25, "willow": 10, "bones": 20, "grave": 1, "hive": 1, "honey": 1, "poison": 1, "crystal": 1,
}


def log(*a):
    print(*a, file=sys.stderr)


# --- inputs -------------------------------------------------------------------------------------
def read_registry(path):
    out = []
    for l in open(path, encoding="utf-8"):
        if l.startswith("#") or l.startswith("name\t") or not l.strip():
            continue
        name, ident = l.rstrip("\n").split("\t")[:2]
        out.append((name, int(ident)))
    return out


def jars_in(dirs):
    seen = {}
    for d in dirs:
        for root, _, files in os.walk(d):
            for f in sorted(files):
                if f.endswith((".jar", ".zip")) and not re.search(r"\.(pre|broken)", f) and f not in seen:
                    seen[f] = os.path.join(root, f)
    return seen


BLOCK_TEX = re.compile(r"^assets/([^/]+)/textures/blocks/(.+)\.png$")


def texture_index(jars):
    """{texture path: (jar file, mean rgb, opaque share, width)} for every block texture."""
    out = {}
    for f, p in jars.items():
        try:
            z = zipfile.ZipFile(p)
        except zipfile.BadZipFile:
            continue
        for m in z.namelist():
            g = BLOCK_TEX.match(m)
            if not g or g.group(2).endswith(("_n", "_s")) or m in out:
                continue
            try:
                a = np.array(Image.open(io.BytesIO(z.read(m))).convert("RGBA"))
            except Exception:
                continue
            h, w = a.shape[:2]
            if h > w and h % w == 0:
                a = a[:w]
            op = a[..., 3] > 40
            if not op.any():
                continue
            out[m] = (f, a[op][..., :3].mean(0), float(op.mean()), int(w))
    return out


def norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


STOP = {"tile", "block", "blocks", "the", "and", "name", "of"}


def toks(s):
    s = re.sub(r"([a-z])([A-Z])", r"\1 \2", s)
    return set(t for t in re.split(r"[^a-zA-Z0-9]+", s.lower()) if len(t) > 2 and t not in STOP)


def match_texture(dom, name, display, ul, icon_rgb, textures_by_dom):
    """Best texture for one block stack. Returns (path, dist, overlap, exact, confidence, alternatives)."""
    cands = textures_by_dom.get(dom.lower(), [])
    if not cands:
        return None
    nm = toks(name) | toks(display) | toks(ul)
    uln = norm(re.sub(r"^tile\.", "", ul))
    best = []
    for m, (jar, tm, af, w) in cands:
        tname = m.split("/textures/blocks/")[1][:-4]
        tn, tfull = norm(tname.split("/")[-1]), norm(tname)
        dist = float(np.abs(tm - icon_rgb).sum()) if icon_rgb is not None else 400.0
        tt = toks(tname)
        overlap = len(nm & tt) / max(1, len(tt)) if tt else 0.0
        exact = bool(tn and (tn == norm(name) or tn == norm(display) or (uln and (uln.endswith(tn) or tfull.endswith(uln)))))
        score = dist - 200 * overlap - 250 * exact + (60 if af < 0.9 else 0)
        best.append((score, dist, overlap, exact, m))
    best.sort()
    s, dist, ov, ex, m = best[0]
    if icon_rgb is not None:
        conf = "high" if ex or (dist < 30 and ov >= 0.5) else ("mid" if dist < 15 or (ov >= 0.5 and dist < 80) else "low")
    else:
        conf = "name-high" if ex else ("name-mid" if ov >= 0.5 else "none")
    return m, round(dist, 1), round(ov, 2), ex, conf, [x[4].split("/textures/blocks/")[1] for x in best[1:3]]


# --- worldgen -----------------------------------------------------------------------------------
def worldgen_from_scans(pattern):
    """{dim: {block@meta: (blocks/chunk, mean Y)}} averaged over the scans' seeds."""
    tot = collections.defaultdict(collections.Counter)
    ysum = collections.defaultdict(collections.Counter)
    chunks = collections.Counter()
    files = sorted(glob.glob(pattern))
    for f in files:
        d = json.load(open(f))
        for dim, blocks in d["dimensions"].items():
            chunks[dim] += d["populated_chunks"].get(dim, 0)
            for rec in blocks.values():
                k = f"{rec['block']}@{rec['meta']}"
                tot[dim][k] += rec["total"]
                ysum[dim][k] += sum(int(y) * c for y, c in rec.get("by_y", {}).items())
    out = {}
    for dim in tot:
        c = chunks[dim] or 1
        out[dim] = {k: (t / c, (ysum[dim][k] / t if t else 0.0)) for k, t in tot[dim].items()}
    return out, len(files)


def write_worldgen_tsv(wg, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("# Modded blocks per populated chunk, per dimension, from the ore survey's region scans\n"
                "# (C:\\qfs\\scan-n1..4.json, 4 seeds, live mod set of 2026-09-10; no Biomes O' Plenty).\n"
                "# Written by tools/textures/rank_modded_blocks.py --scans. meanY is the block's mean height.\n"
                "dim\tblock@meta\tper_chunk\tmeanY\n")
        for dim in sorted(wg, key=int):
            for k, (r, y) in sorted(wg[dim].items(), key=lambda kv: -kv[1][0]):
                if k.startswith("minecraft:") or r < 0.001:
                    continue
                f.write(f"{dim}\t{k}\t{r:.4f}\t{y:.1f}\n")


def read_worldgen_tsv(path):
    out = collections.defaultdict(dict)
    for l in open(path, encoding="utf-8"):
        if l.startswith("#") or l.startswith("dim\t"):
            continue
        dim, k, r, y = l.rstrip("\n").split("\t")
        out[dim][k] = (float(r), float(y))
    return out


def bop_biome_blocks(bop_jar):
    """{biome class: [BoP block fields it references]} from the jar's constant pools."""
    z = zipfile.ZipFile(bop_jar)

    def strings(data):
        return set(m.group(2).decode("latin-1") for m in re.finditer(rb"\x01(..)([A-Za-z_][A-Za-z0-9_]{2,40})", data, re.S))
    fields = strings(z.read("biomesoplenty/api/content/BOPCBlocks.class"))
    fields = {f for f in fields if f[0].islower() and not f.startswith(("java", "net", "org", "biomesoplenty", "get", "set")) and f != "this"}
    out = {}
    for n in z.namelist():
        if "/biome/" in n and re.search(r"BiomeGen[A-Za-z]+\.class$", n):
            s = strings(z.read(n))
            out[n.split("/")[-1][:-6]] = sorted(f for f in fields if f in s)
    return out


def plan_biome_weights(plan_yaml, biome_tsv):
    names = {}
    for l in open(biome_tsv, encoding="utf-8"):
        if l.startswith("#") or l.startswith("id\t"):
            continue
        p = l.rstrip("\n").split("\t")
        names[int(p[0])] = p[1]
    txt = open(plan_yaml, encoding="utf-8").read()
    w = collections.Counter()
    for m in re.finditer(r"biome:\s*(\d+)", txt):
        w[int(m.group(1))] += 3
    for m in re.finditer(r"biomes:\s*\[((?:\[\d+,\s*\d+\],?\s*)+)\]", txt):
        for b, k in re.findall(r"\[(\d+),\s*(\d+)\]", m.group(1)):
            w[int(b)] += int(k)
    return {names[b]: c for b, c in w.items() if b in names}, names


def bop_class_name(biome_name):
    return "BiomeGen" + re.sub(r"[^A-Za-z]", "", biome_name)


# Hand-checked textures for blocks the automatic pairing gets wrong or cannot see (no creative
# stack, a model, or a group block whose variants share one registry name). File names were
# checked against the jars' textures/blocks/ listings [verified]; which metadata uses which file
# follows the mods' source where known and is otherwise a reading of the names [guess]. A
# "minecraft:" entry means the block draws a vanilla texture. An empty list with a note means the
# block's textures live outside textures/blocks/ (a tile-entity model), so block maps cannot reach it.
OVERRIDES = {
    "TwilightForest:tile.TFLog": (["oak_side", "oak_top", "canopy_side", "canopy_top", "mangrove_side", "mangrove_top", "darkwood_side", "darkwood_top"], "meta 0-3: twilight oak, canopy, mangrove, darkwood"),
    "TwilightForest:tile.TFLeaves": (["minecraft:leaves_oak", "minecraft:leaves_spruce", "minecraft:leaves_birch"], "TF's leaves 0-3 draw vanilla leaf textures (no oak/canopy/mangrove leaf file in the jar); only darkwood_leaves is TF's own"),
    "TwilightForest:tile.TFMagicLog": (["time_side", "time_section", "trans_side", "trans_section", "mine_side", "mine_section", "sort_side", "sort_section"], "time, transformation, mining, sorting"),
    "TwilightForest:tile.TFMagicLeaves": (["time_leaves", "trans_leaves", "sort_leaves"], "mining-tree leaves draw a vanilla texture"),
    "TwilightForest:tile.TFRoots": (["rootblock", "oreroots"], "meta 0 root, 1 liveroot"),
    "TwilightForest:tile.TFTowerStone": (["towerwood_planks", "towerwood_encased", "towerwood_cracked", "towerwood_mossy", "towerwood_infested"], "Dark Tower"),
    "TwilightForest:tile.TFMazestone": (["mazestone_plain", "mazestone_brick", "mazestone_decorative", "mazestone_mosaic", "mazestone_cracked", "mazestone_mossy", "mazestone_pillar", "mazestone_border"], "Labyrinth"),
    "TwilightForest:tile.CastleBrick": (["castleblock_brick", "castleblock_cracked", "castleblock_mossy", "castleblock_faded", "castleblock_roof"], "Final Castle"),
    "TwilightForest:tile.TFUnderBrick": (["knightbrick", "knightbrick_mossy", "knightbrick_cracked", "knightbrick_floor"], "Goblin Knight Stronghold"),
    "TwilightForest:tile.TFDeadrock": (["deadrock_solid", "deadrock_cracked", "deadrock_surface"], "Highlands terrain; meta 2 is the plain block"),
    "TwilightForest:tile.TFNagastone": (["nagastone_" + x for x in ("cross_section", "long_side", "face_front", "face_left", "face_right", "top_tip", "bottom_tip", "tip_left", "tip_right", "tip_long", "turn_top", "left_up", "left_down", "right_up", "right_down", "bottom_long")], "Naga courtyard"),
    "TwilightForest:tile.TFPlank": (["twilight_oak_planks", "canopy_planks", "mangrove_planks", "darkwood_planks", "timewood_planks", "transwood_planks", "minewood_planks", "sortingwood_planks"], "the eight TF planks"),
    "TwilightForest:tile.TFHedge": (["hedge", "darkwood_leaves"], "hedge; meta 1 is darkwood leaves"),
    "TwilightForest:tile.TFThorns": (["brown_thorns_side", "brown_thorns_top", "green_thorns_side", "green_thorns_top"], ""),
    "TwilightForest:tile.AuroraBrick": (["aurorabrick%d" % i for i in range(8)], "Aurora Palace, 8 random tiles"),
    "Railcraft:slab": (["brick.abyssal", "brick.bleachedbone", "brick.bloodstained", "brick.frostbound", "brick.infernal", "brick.nether", "brick.quarried", "brick.sandy", "cube.stone.abyssal", "cube.stone.quarried", "concrete", "cube.steel", "cube.copper", "cube.tin", "cube.lead", "cube.coke"], "slabs reuse the brick and cube textures"),
    "Railcraft:stair": (["brick.abyssal", "brick.bleachedbone", "brick.bloodstained", "brick.frostbound", "brick.infernal", "brick.nether", "brick.quarried", "brick.sandy", "cube.stone.abyssal", "cube.stone.quarried"], "stairs reuse the brick and cube textures"),
    "Railcraft:track": (["tracks/track.switch", "tracks/track.junction", "tracks/track.wye", "tracks/track.boarding", "tracks/track.holding", "tracks/track.locking", "tracks/track.oneway", "tracks/track.embarking", "tracks/track.disembarking", "tracks/track.control", "tracks/track.detector.direction", "tracks/track.gated", "tracks/track.launcher", "tracks/track.priming", "tracks/track.buffer.stop", "tracks/track.speed", "tracks/track.speed.boost", "tracks/track.reinforced", "tracks/track.reinforced.boost", "tracks/track.electric", "tracks/track.slow", "tracks/track.whistle", "tracks/track.coupler", "tracks/track.disposal", "tracks/track.routing", "tracks/track.limiter"], "flat rail textures; plain track is vanilla's rail"),
    "Railcraft:track.elevator": (["tracks/track.elevator"], ""),
    "Railcraft:post": (["post.wood", "post.metal"], ""),
    "Railcraft:wall.alpha": (["brick.infernal", "brick.sandy", "concrete", "cube.stone.abyssal", "cube.stone.quarried", "brick.frostbound", "brick.quarried", "brick.bloodstained"], "walls reuse brick and cube textures"),
    "Railcraft:wall.beta": (["brick.abyssal", "brick.bleachedbone", "brick.nether"], ""),
    "EnderStorage:enderChest": ([], "tile-entity model: the jar has no textures/blocks at all (textures under assets/enderstorage/textures/)"),
    "BiblioCraft:BiblioLantern": ([], "model: assets/bibliocraft/textures/models/ (181 files); the only block texture, frame, is a placeholder"),
    "BiblioCraft:BiblioIronLantern": ([], "model, see BiblioLantern"), "BiblioCraft:BiblioLamp": ([], "model, see BiblioLantern"), "BiblioCraft:BiblioIronLamp": ([], "model, see BiblioLantern"),
    "BiblioCraft:BiblioSwordPedestal": ([], "model, see BiblioLantern"),
    "legends:dynamicLegendsBlock1": (["red_sandstone", "red_sandstone_top", "red_sandstone_bottom"], "Red Sandstone: Korriban's whole surface, also in DIM 54"),
    "legends:dynamicLegendsBlock14": (["silverore"], "Silver Ore"), "legends:dynamicLegendsBlock46": (["nether_gold_ore"], "Nether Gold Ore"),
    "TragicMC:tragicOres": (["OreCoal", "OreIron", "OreGold", "OreDiamond", "OreEmerald", "OreLapis", "OreRuby", "OreSapphire", "OreTungsten", "OreMercury", "OreXP"], "Collision ores on dark stone"),
    "TragicMC:darkStone": (["SmoothDarkStone", "RedDarkStone", "GreenDarkStone", "TealDarkStone", "BrownDarkStone", "VioletDarkStone", "NavyDarkStone", "BeveledDarkStone", "CrackedDarkStone", "DarkBrick", "BlueDarkStone", "PurpleDarkStone", "YellowDarkStone", "SpikeTopDarkStone", "SpikeSideDarkStone"], "meta 0 is the Collision's whole terrain"),
    "HardcoreEnderExpansion:end_stone_terrain": (["endstone_ter_infested_side", "endstone_ter_infested_top", "endstone_ter_burned_side", "endstone_ter_burned_top", "endstone_ter_enchanted_side", "endstone_ter_enchanted_top"], "HEE End biomes"),
    "HardcoreEnderExpansion:obsidian_special": (["obsidian_chiseled", "obsidian_chiseled_top", "obsidian_pillar", "obsidian_pillar_top", "obsidian_smooth"], ""),
    "HardcoreEnderExpansion:ravaged_brick": (["ravaged_brick", "ravaged_brick_smooth", "ravaged_brick_cracked", "ravaged_brick_damaged_1", "ravaged_brick_damaged_2", "ravaged_brick_damaged_3", "ravaged_brick_damaged_4", "ravaged_brick_glow"], "Endstone Temple"),
    # Biomes O' Plenty group blocks (no creative stacks in the item dump: BoP is on the world-design server only)
    "BiomesOPlenty:hardDirt": (["harddirt"], ""), "BiomesOPlenty:hardSand": (["hardsand"], ""), "BiomesOPlenty:cragRock": (["cragrock"], ""),
    "BiomesOPlenty:driedDirt": (["drieddirt"], ""), "BiomesOPlenty:ashStone": (["ashstone"], ""), "BiomesOPlenty:hardIce": (["hardice"], ""),
    "BiomesOPlenty:mud": (["mud", "quicksand"], ""), "BiomesOPlenty:ash": (["ashblock"], ""), "BiomesOPlenty:flesh": (["flesh"], ""),
    "BiomesOPlenty:originGrass": (["origingrass1", "origingrass2", "origingrass3"], "Origin Valley"),
    "BiomesOPlenty:newBopGrass": (["grass_top", "grass_loamy_side", "grass_sandy_side", "grass_silty_side", "grass_loamy_side_snowed", "grass_sandy_side_snowed", "grass_silty_side_snowed"], "loamy / sandy / silty grass; top is tinted"),
    "BiomesOPlenty:newBopDirt": (["dirt_loamy", "dirt_sandy", "dirt_silty", "coarse_dirt_loamy", "coarse_dirt_sandy", "coarse_dirt_silty"], ""),
    "BiomesOPlenty:rocks": (["limestone", "limestonesmooth", "siltstone", "siltstonesmooth", "shale", "shalesmooth"], ""),
    "BiomesOPlenty:gemOre": (["amethystore", "rubyore", "peridotore", "topazore", "tanzaniteore", "malachiteore", "sapphireore", "amberore"], "eight gem ores"),
    "BiomesOPlenty:logs1": (["log_sacredoak_side", "log_sacredoak_heart", "log_cherry_side", "log_cherry_heart", "log_dark_side", "log_dark_heart", "log_fir_side", "log_fir_heart"], ""),
    "BiomesOPlenty:logs2": (["log_ethereal_side", "log_ethereal_heart", "log_magic_side", "log_magic_heart", "log_mangrove_side", "log_mangrove_heart", "log_palm_side", "log_palm_heart"], ""),
    "BiomesOPlenty:logs3": (["log_redwood_side", "log_redwood_heart", "log_willow_side", "log_willow_heart", "log_dead_side", "log_dead_heart", "bigflowerstem_side", "bigflowerstem_heart"], ""),
    "BiomesOPlenty:logs4": (["log_pine_side", "log_pine_heart", "log_hellbark_side", "log_hellbark_heart", "log_jacaranda_side", "log_jacaranda_heart", "log_mahogany_side", "log_mahogany_heart"], ""),
    "BiomesOPlenty:leaves1": (["leaves_yellowautumn_fancy", "leaves_bamboo_fancy", "leaves_magic_fancy", "leaves_dark_fancy"], "_fast variants exist too"),
    "BiomesOPlenty:leaves2": (["leaves_dead_fancy", "leaves_fir_fancy", "leaves_ethereal_fancy", "leaves_orangeautumn_fancy"], ""),
    "BiomesOPlenty:leaves3": (["leaves_origin_fancy", "leaves_pinkcherry_fancy", "leaves_maple_fancy", "leaves_whitecherry_fancy"], ""),
    "BiomesOPlenty:leaves4": (["leaves_hellbark_fancy", "leaves_jacaranda_fancy"], ""),
    "BiomesOPlenty:colorizedLeaves1": (["leaves_sacredoak_fancy", "leaves_mangrove_fancy", "leaves_palm_fancy", "leaves_redwood_fancy"], "biome-tinted"),
    "BiomesOPlenty:colorizedLeaves2": (["leaves_willow_fancy", "leaves_pine_fancy", "leaves_mahogany_fancy", "leaves_flowering_fancy", "leaves_flowering_overlay"], "biome-tinted"),
    "BiomesOPlenty:appleLeaves": (["leaves_apple%d_fancy" % i for i in range(4)], ""), "BiomesOPlenty:persimmonLeaves": (["leaves_persimmon%d_fancy" % i for i in range(4)], ""),
    "BiomesOPlenty:foliage": (["shortgrass", "mediumgrass", "bush", "sprout", "poisonivy", "berrybush", "shrub", "wheatgrass", "dampgrass", "koru", "cloverpatch", "leafpile", "deadleafpile", "duckweed", "flaxbottom", "flaxtop"], "biome-tinted cut-outs"),
    "BiomesOPlenty:flowers": (["clover", "swampflower", "deadbloom", "glowflower", "hydrangea", "cosmos", "daffodil", "wildflower", "violet", "anemone", "lilyflower", "enderlotus", "bromeliad", "eyebulbbottom", "eyebulbtop", "dandelion"], ""),
    "BiomesOPlenty:flowers2": (["hibiscus", "lilyofthevalley", "burningblossom", "lavender", "goldenrod", "bluebells", "minersdelight", "icyiris", "rose"], ""),
    "BiomesOPlenty:plants": (["deadgrass", "desertgrass", "desertsprouts", "dunegrass", "spectralfern", "thorn", "wildrice", "cattail", "cattailtop", "cattailbottom", "rivercane", "cactus", "witherwart", "reed", "root", "wildcarrot"], ""),
    "BiomesOPlenty:bopGrass": (["spectralmoss_top", "spectralmoss_side", "spectralmoss_bottom", "smolderinggrass_top", "smolderinggrass_side", "smolderinggrass_bottom"], "End and Nether"),
    "BiomesOPlenty:overgrownNetherrack": (["overgrownnetherrack1", "overgrownnetherrack2", "overgrownnetherrack3"], ""),
    "BiomesOPlenty:treeMoss": (["treemoss"], ""), "BiomesOPlenty:bamboo": (["bamboo", "bambootop"], ""), "BiomesOPlenty:ivy": (["ivy"], ""), "BiomesOPlenty:flowerVine": (["flowervine"], ""),
    "BiomesOPlenty:mushrooms": (["toadstool", "portobello", "bluemilk", "glowshroom", "flatmushroom", "shadowshroom"], ""),
    "BiomesOPlenty:coral1": (["kelpbottom", "kelpsingle", "kelptop", "kelpmiddle", "pinkcoral", "orangecoral", "bluecoral", "glowcoral"], ""), "BiomesOPlenty:coral2": (["algae"], ""),
    "BiomesOPlenty:stoneFormations": (["stalagmite", "stalactite"], ""), "BiomesOPlenty:bones": (["bones_small", "bones_medium", "bones_large"], ""),
    "BiomesOPlenty:mudBricks": (["mudbrick"], ""), "BiomesOPlenty:longGrass": (["longgrass1", "longgrass2", "longgrass3"], ""),
}


# --- scoring ------------------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--registry", default=os.path.join(REPO, "docs", "survey", "block-ids.tsv"))
    ap.add_argument("--items", default=os.path.join(REPO, "site", "items", "data", "items.json"))
    ap.add_argument("--recipes", default=os.path.join(REPO, "site", "items", "data", "recipes.json"))
    ap.add_argument("--scans", default=r"C:\qfs\scan-n*.json", help="raw survey scans (glob); refreshes the data TSV")
    ap.add_argument("--worldgen-tsv", default=os.path.join(DATA, "worldgen-modded.tsv"))
    ap.add_argument("--mods", action="append", help="mod jar folders (default: live mods + C:\\qfs\\v0\\mods for BoP/RWG)")
    ap.add_argument("--bop-jar", default=None, help="BiomesOPlenty jar (default: found in --mods)")
    ap.add_argument("--plan", default=os.path.join(REPO, "docs", "design", "world", "continent-v4.yaml"))
    ap.add_argument("--biomes", default=os.path.join(REPO, "docs", "survey", "biome-ids.tsv"))
    ap.add_argument("--out", default=os.path.join(REPO, "docs", "design", "textures", "modded-blocks.tsv"))
    ap.add_argument("--only", help="write the top blocks' texture paths, one per line (gen_surface_pack --only)")
    ap.add_argument("--top", type=int, default=150)
    ap.add_argument("--sheet", help="contact sheet PNG of the top blocks' textures")
    ap.add_argument("--map-json", default=None, help="also dump the per-stack texture pairing as JSON")
    a = ap.parse_args()
    mods = a.mods or [os.path.join(LIVE, "mods"), r"C:\qfs\v0\mods"]
    mods = [m for m in mods if os.path.isdir(m)]

    reg = read_registry(a.registry)
    modded = [(n, i) for n, i in reg if not n.startswith("minecraft:")]
    log(f"registry: {len(reg)} blocks, {len(modded)} modded")

    jars = jars_in(mods)
    tex = texture_index(jars)
    textures_by_dom = collections.defaultdict(list)
    for m, v in tex.items():
        textures_by_dom[BLOCK_TEX.match(m).group(1)].append((m, v))
    log(f"textures: {len(tex)} block textures in {len(textures_by_dom)} domains from {len(jars)} jars")

    # worldgen
    if glob.glob(a.scans):
        wg, nfiles = worldgen_from_scans(a.scans)
        write_worldgen_tsv(wg, a.worldgen_tsv)
        log(f"worldgen: {nfiles} scans -> {a.worldgen_tsv}")
    else:
        wg = read_worldgen_tsv(a.worldgen_tsv)
        log(f"worldgen: scans absent, read {a.worldgen_tsv}")
    W = collections.defaultdict(float)          # block id -> score
    Wmeta = collections.defaultdict(float)      # block@meta -> score (for texture choice)
    Wnote = collections.defaultdict(list)
    for dim, rows in wg.items():
        v = DIM_WEIGHT.get(dim, 0.05)
        if v <= 0:
            continue
        g = GROUND[dim]
        # Sum a block's variants first (Railcraft:ore has 11, VoltzEngine's ores 10), then take the
        # log: ten sub-ores at 10/chunk are one ore at 100/chunk to the eye.
        per_block = collections.defaultdict(lambda: [0.0, 0.0])
        for k, (rate, my) in rows.items():
            if k.startswith("minecraft:") or rate <= 0:
                continue
            bid = k.split("@")[0]
            per_block[bid][0] += rate
            per_block[bid][1] += rate * my
            Wmeta[k] += v * math.log10(1.0 + rate)
        for bid, (rate, ry) in per_block.items():
            my = ry / rate
            exposure = 1.5 if my >= g - 12 else 1.0
            W[bid] += v * math.log10(1.0 + rate) * exposure
            if rate >= 1.0 and v >= 0.1:
                Wnote[bid].append(f"dim {dim}: {rate:.1f}/chunk, mean Y {my:.0f}{' (surface)' if exposure > 1 else ''}")
    # Biomes O' Plenty estimate
    bop_jar = a.bop_jar or next((p for f, p in jars.items() if f.lower().startswith("biomesoplenty")), None)
    if bop_jar and os.path.exists(a.plan):
        refs = bop_biome_blocks(bop_jar)
        weights, _ = plan_biome_weights(a.plan, a.biomes)
        total = sum(weights.values()) or 1
        bop_rate, bop_where = collections.Counter(), collections.defaultdict(list)
        for biome, wgt in weights.items():
            cls = bop_class_name(biome)
            fields = refs.get(cls) or refs.get(cls.replace("BiomeGen", "BiomeGenBOP"))
            if not fields:
                continue
            share = wgt / total
            for f in fields:
                bop_rate[f] += BOP_FIELD_RATE.get(f, 2.0) * share
                bop_where[f].append((share, biome))
        for f, rate in bop_rate.items():
            bid = "BiomesOPlenty:" + f
            exposure = 1.0 if f in ("gemOre", "rocks", "stoneFormations") else 1.5   # ores and rock veins are underground
            W[bid] += 1.0 * math.log10(1.0 + rate) * exposure
            tops = ", ".join(b for _, b in sorted(bop_where[f], reverse=True)[:3])
            Wnote[bid].append(f"BoP estimate {rate:.1f}/chunk over the plan ({len(bop_where[f])} biomes: {tops})")
        log(f"BoP: {len(refs)} biome classes scanned, {len(weights)} plan biomes")

    # crafting
    items = json.load(open(a.items, encoding="utf-8"))
    rec = json.load(open(a.recipes, encoding="utf-8"))
    kinds = items["kinds"]
    stacks = [e for e in items["items"] if kinds[e["c"]] == "block"]
    ores = rec["ores"]
    n_out, n_in = collections.Counter(), collections.Counter()
    for r in rec["crafting"] + rec["smelting"]:
        out_id = r["out"].split("@")[0]
        ins = set()
        for i in set(x for x in r.get("in", []) if x):
            for e in (ores.get(i[4:], []) if i.startswith("ore:") else [i]):
                ins.add(e.split("@")[0])
        if out_id in ins:
            continue   # a recolour or variant swap (lamp + dye -> lamp): not a craft of the block
        n_out[out_id] += 1
        for e in ins:
            n_in[e] += 1
    # Caps: BiblioCraft registers one recipe per wood x colour (258 for a lamp); a player crafts one.
    C = {b: math.log2(1 + min(n_out[b], 16)) + 0.5 * math.log2(1 + min(n_in[b], 64)) for b in set(n_out) | set(n_in)}

    # quests
    Q = collections.defaultdict(float)
    Qnote = collections.defaultdict(list)
    for idx, refs in items["qrefs"].items():
        e = items["items"][int(idx)]
        bid = e["k"].split("@")[0]
        if kinds[e["c"]] != "block":
            continue
        for qid, role in refs:
            Q[bid] += {"task": 3.0, "icon": 1.0, "reward": 0.5}.get(role, 0.5)
        Qnote[bid].append(f"{len(refs)} quest ref(s): " + ", ".join(sorted({r for _, r in refs})))
    for b in Q:
        Q[b] = min(Q[b], 10.0)

    # base tier
    def base_tier(bid):
        mod, path = bid.split(":", 1)
        for m, rx, t in BASE:
            if m.lower() == mod.lower() and rx.search(path):
                return t
        return 0

    # icons
    sheets = [np.array(Image.open(os.path.join(os.path.dirname(a.items), f"icons-{i}.png")).convert("RGBA")) for i in range(items["sheets"])]
    cell, side = items["cell"], items["side"]

    def icon_rgb(e):
        i = e["i"]
        sh, p = i // (side * side), i % (side * side)
        y, x = (p // side) * cell, (p % side) * cell
        ic = sheets[sh][y:y + cell, x:x + cell]
        op = ic[..., 3] > 0
        if not (600 <= op.sum() <= 700):      # the isometric cube silhouette is 672 px; else a model/flat item
            return None
        return ic[op][..., :3].mean(0) / 0.665

    # texture pairing per stack
    pairing = {}
    stacks_by_block = collections.defaultdict(list)
    for e in stacks:
        bid = e["k"].split("@")[0]
        stacks_by_block[bid].append(e)
        dom, name = bid.split(":", 1)
        irgb = icon_rgb(e)
        m = match_texture(dom, name, e.get("n", ""), e.get("ul", ""), irgb, textures_by_dom)
        pairing[e["k"]] = {"name": e.get("n", ""), "cube": irgb is not None, "match": m}
    # registry blocks with no creative stack (BoP, hidden technical blocks): name-only pairing
    for bid, _ in modded:
        if bid in stacks_by_block:
            continue
        dom, name = bid.split(":", 1)
        m = match_texture(dom, name, "", "", None, textures_by_dom)
        pairing[bid + "@?"] = {"name": "", "cube": False, "match": m}

    # scores
    # Fixed references, so a score means the same thing between runs: W_REF is a block at 100 per
    # chunk at the Overworld surface (1.0 x log10(101) x 1.5); C_REF a block made by 16 recipes and
    # used in 64. Both saturate at 10.
    W_REF, C_REF, Q_REF = 3.0, 7.1, 10.0
    rows = []
    for bid, ident in modded:
        w = 10.0 * min(1.0, W.get(bid, 0.0) / W_REF)
        c = 10.0 * min(1.0, C.get(bid, 0.0) / C_REF)
        b = 10.0 * base_tier(bid) / 3.0
        q = 10.0 * min(1.0, Q.get(bid, 0.0) / Q_REF)
        score = 0.45 * w + 0.20 * c + 0.25 * b + 0.10 * q
        names = sorted({pairing[e["k"]]["name"] for e in stacks_by_block.get(bid, [])} - {""})
        # textures: distinct best matches over the block's stacks, strongest worldgen meta first
        texs = []
        seen = set()
        keys = [e["k"] for e in stacks_by_block.get(bid, [])] or [bid + "@?"]
        keys.sort(key=lambda k: -Wmeta.get(k.split("#")[0], 0.0))
        for k in keys:
            m = pairing[k]["match"]
            if not m or m[0] in seen:
                continue
            seen.add(m[0])
            texs.append((m[0].split("/textures/blocks/")[1][:-4], m[4]))
        note = ""
        if bid in OVERRIDES:
            ov, note = OVERRIDES[bid]
            dom = bid.split(":")[0].lower()
            texs = []
            for t in ov:
                if t.startswith("minecraft:"):
                    texs.append((t, "vanilla"))
                elif ("assets/%s/textures/blocks/%s.png" % (dom, t)) in tex:
                    texs.append((t, "verified"))
                else:
                    texs.append((t, "NOT FOUND"))
        rows.append({"block": bid, "id": ident, "mod": bid.split(":")[0], "names": names, "score": score, "W": w, "C": c, "B": b, "Q": q,
                     "note": note,
                     "n_out": n_out.get(bid, 0), "n_in": n_in.get(bid, 0), "tier": base_tier(bid),
                     "icon_is_texture": any(pairing[e["k"]]["cube"] for e in stacks_by_block.get(bid, [])),
                     "textures": texs, "domain": bid.split(":")[0].lower(),
                     "why": "; ".join(([note] if note else []) + Wnote.get(bid, [])[:4] + Qnote.get(bid, [])[:1])})
    rows.sort(key=lambda r: -r["score"])

    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w", encoding="utf-8", newline="\n") as f:
        f.write("# Every modded block in the pinned registry (docs/survey/block-ids.tsv), ranked by how often players see it.\n"
                "# Written by tools/textures/rank_modded_blocks.py; method and weights in docs/design/textures/modded-blocks.md.\n"
                "# textures = 'path inside assets/<domain>/textures/blocks/ (confidence)', strongest worldgen variant first.\n"
                "rank\tscore\tblock\tnames\tW_worldgen\tC_craft\tB_base\tQ_quest\trecipes_out\trecipes_in\ticon_is_texture\ttextures\twhy\n")
        for i, r in enumerate(rows, 1):
            f.write("\t".join([str(i), f"{r['score']:.2f}", r["block"], " | ".join(r["names"][:6]), f"{r['W']:.2f}", f"{r['C']:.2f}",
                               f"{r['B']:.2f}", f"{r['Q']:.2f}", str(r["n_out"]), str(r["n_in"]), "yes" if r["icon_is_texture"] else "no",
                               "; ".join(f"{t} ({c})" for t, c in r["textures"][:8]), r["why"]]) + "\n")
    log(f"ranking: {len(rows)} blocks -> {a.out}")

    if a.map_json:
        json.dump({k: {"name": v["name"], "cube": v["cube"], "match": v["match"]} for k, v in pairing.items()},
                  open(a.map_json, "w"), indent=0)

    top = rows[:a.top]
    if a.only:
        paths = []
        seen = set()
        for r in top:
            if r["block"] in OVERRIDES:
                dom = r["block"].split(":")[0].lower()
                for t, c in r["textures"]:
                    p = "assets/%s/textures/blocks/%s.png" % (dom, t)
                    if c == "verified" and p not in seen:
                        seen.add(p)
                        paths.append(p)
                continue
            for k in [e["k"] for e in stacks_by_block.get(r["block"], [])] or [r["block"] + "@?"]:
                m = pairing[k]["match"]
                if m and m[4] in ("high", "mid", "name-high") and m[0] not in seen:
                    seen.add(m[0])
                    paths.append(m[0])
        with open(a.only, "w", encoding="utf-8", newline="\n") as f:
            f.write("# textures of the top %d modded blocks (rank_modded_blocks.py --only); one path per line\n" % a.top)
            f.write("\n".join(paths) + "\n")
        log(f"--only: {len(paths)} texture paths -> {a.only}")

    if a.sheet:
        cells = []
        for r in top:
            ok = [t for t, c in r["textures"] if c not in ("vanilla", "NOT FOUND")]
            if ok:
                cells.append((r["block"], ok[0]))
        cols, cs = 10, 64
        rowsn = (len(cells) + cols - 1) // cols
        sheet = Image.new("RGBA", (cols * cs, rowsn * (cs + 12)), (40, 40, 40, 255))
        from PIL import ImageDraw
        dr = ImageDraw.Draw(sheet)
        zips = {}
        for i, (bid, t) in enumerate(cells):
            dom = bid.split(":")[0].lower()
            path = f"assets/{dom}/textures/blocks/{t}.png"
            jar = tex[path][0]
            z = zips.setdefault(jar, zipfile.ZipFile(jars[jar]))
            im = Image.open(io.BytesIO(z.read(path))).convert("RGBA")
            w = im.size[0]
            im = im.crop((0, 0, w, w)).resize((cs, cs), Image.NEAREST)
            x, y = (i % cols) * cs, (i // cols) * (cs + 12)
            sheet.paste(im, (x, y))
            dr.text((x + 1, y + cs), bid.split(":")[1][:11], fill=(230, 230, 230, 255))
        sheet.save(a.sheet)
        log(f"sheet: {len(cells)} textures -> {a.sheet}")

    print(f"{'rank':>4} {'score':>6} {'W':>5} {'C':>5} {'B':>5} {'Q':>5}  block  [names]  textures")
    for i, r in enumerate(top[:40], 1):
        print(f"{i:>4} {r['score']:>6.2f} {r['W']:>5.2f} {r['C']:>5.2f} {r['B']:>5.2f} {r['Q']:>5.2f}  {r['block']}  {r['names'][:3]}  "
              f"{[t for t, c in r['textures'][:3]]}")


if __name__ == "__main__":
    main()
