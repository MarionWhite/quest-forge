# -*- coding: utf-8 -*-
import json, re, os, unicodedata

rows = {r['file']: r for r in json.load(open('mods.json'))}

# file -> (category, display name, blurb, version_override)
T = [
 # ---------------- Quests & Progression ----------------
 ("BetterQuesting-3.0.328.jar", "Quests", "Better Questing", None,
  "The questing engine the whole pack is built on. Quest lines, prerequisites, party support and reward chests, all driven from an in-game book."),
 ("StandardExpansion-3.0.181.jar", "Quests", "Standard Expansion", None,
  "The task and reward library for Better Questing — retrieval, crafting, kill and location objectives, loot rewards, and the quest-line themes."),
 ("questbook-3.0.0-1.7.10.jar", "Quests", "Quest Book", "3.0.0",
  "Puts the quest interface on a physical book you carry, so you can open your quest log without a keybind or a command."),
 ("QuestForgeContent-1.0.0.jar", "Quests", "QuestForge Content", None,
  "The pack's own mod: 81 custom enchantments with their own application rules, a proximity voice chat, a working in-game jukebox, and the survey tools used to balance the pack."),
 ("LevelUp.jar", "Quests", "Level Up!", None,
  "An RPG skill tree layered over vanilla. Spend levels on Mining, Sword, Archery and more, or pick a class; a Book of Unlearning lets you respec."),
 ("LootBags-1.7.10-2.0.17.jar", "Quests", "Loot Bags", None,
  "Mobs drop sealed pouches instead of only their usual loot. Open one for a weighted roll from a pack-wide loot table."),

 # ---------------- New Dimensions ----------------
 ("TwilightForest-2.4.3.jar", "Dimensions", "The Twilight Forest", None,
  "A permanently dusk-lit forest dimension gated behind a progression of bosses — the Naga, the Lich, the Hydra — each one unlocking the next region."),
 ("HardcoreEnderExpansionMCv.jar", "Dimensions", "Hardcore Ender Expansion", None,
  "Rebuilds the End into a real destination: a genuinely difficult Ender Dragon, new biomes and ores, endermen that behave, and a reward worth the fight."),
 ("WelcomeToTheJungle.jar", "Dimensions", "Welcome to the Jungle", None,
  "Overhauls jungle biomes with dense new growth, dinosaurs, and jungle-specific gear and structures."),

 # ---------------- Dungeons & Worldgen ----------------
 ("chocolateQuest-1.7.10-1.1d.jar", "Dungeons", "Chocolate Quest", None,
  "Large hand-designed dungeons — castles, pyramids, ships, walled towns — filled with scripted humanoid bosses and their loot. Formerly Better Dungeons."),
 ("roguelike-1.7.10-1.5.0b.jar", "Dungeons", "Roguelike Dungeons", None,
  "Multi-floor dungeons that get harder and richer the deeper you go, ending in a boss room. Generated fresh every world."),
 ("DoomlikeDungeons-1.11.0.1-MC1.7.10.jar", "Dungeons", "Doomlike Dungeons", None,
  "Sprawling multi-room complexes generated in the style of classic Doom levels — themed rooms, locked routes and spawner clusters."),
 ("RecurrentComplex.jar", "Dungeons", "Recurrent Complex", None,
  "The structure engine behind much of the pack's worldgen. Places custom villages, ruins and set-pieces, and can import or export any build."),

 # ---------------- Creatures & Bosses ----------------
 ("LycanitesMobsComplete 1.13.0.5 [1.7.10].jar", "Creatures", "Lycanites Mobs", "1.13.0.5",
  "A full bestiary keyed to biome and element — every environment gets its own set of predators, plus tameable mounts, summonable pets and elemental bosses."),
 ("MutantCreatures.jar", "Creatures", "Mutant Creatures", None,
  "Mini-boss versions of the vanilla mobs. The Mutant Creeper, Enderman and Zombie all hit far harder than the originals and drop trophies worth having."),
 ("TragicMC.jar", "Creatures", "TragicMC 2", None,
  "Its own progression of mobs, bosses and dimensions, leaning hard into large multi-stage boss fights."),
 ("orespawn.zip", "Creatures", "OreSpawn", None,
  "Enormous creatures, royal dragons, new dimensions and joke-scale weapons. Loud, chaotic, and the source of several of the pack's late-game targets."),
 ("InfernalMobs-1.7.10.jar", "Creatures", "Infernal Mobs", None,
  "Diablo-style rare modifiers on ordinary mobs. A random zombie can roll Vengeance, Sprint and Ender — much deadlier, and much better loot."),
 ("CustomNpcs.jar", "Creatures", "Custom NPCs", None,
  "The tool behind the pack's named characters: questgivers, shopkeepers and dialogue trees, all authored in-game."),
 ("MobProperties.jar", "Creatures", "Mob Properties", None,
  "Rewrites any mob's drops, attributes and NBT from config — the lever used to retune spawns and loot across every mob mod at once."),
 ("JustAnotherSpawner-0.17.8.jar", "Creatures", "Just Another Spawner", None,
  "Takes over vanilla spawning so a dozen mob mods can share a world without one of them flooding every biome."),
 ("ColorfulMobsMC.jar", "Creatures", "Colorful Mobs", None,
  "Dye any living thing. Comes with a colour wand, invisibility powder and rainbow dust for the ones you can't reach."),
 ("LuckyEgg.jar", "Creatures", "Lucky Egg", None,
  "An egg that summons something. Occasionally that something is survivable."),
 ("KillerPacman.jar", "Creatures", "Killer Pacman", None,
  "Adds Pacman as a hostile mob, plus a block that keeps him away from wherever you'd rather he wasn't."),

 # ---------------- Combat & Gear ----------------
 ("MineBladeBattlegearBullseye.jar", "Combat", "Mine & Blade: Battlegear 2", None,
  "Real dual-wielding, shields with a block stance, quivers, and a sheath system that puts your weapons on your back."),
 ("SoulShardsTheOldWays.jar", "Combat", "Soul Shards: The Old Ways", None,
  "Bind the souls of the mobs you kill to a shard, then cash a full shard in for a controllable spawner. The classic soul-cage grind."),
 ("Baubles.jar", "Combat", "Baubles", None,
  "Adds ring, amulet and belt slots to the inventory. Several mods in the pack put their best passive gear in them."),
 ("AdventureBackpack.jar", "Combat", "Adventure Backpack", None,
  "Wearable backpacks with built-in fluid tanks, a sleeping bag and tool slots. Each variant is themed to the mob or biome it's made from."),
 ("DamageIndicators.jar", "Combat", "Damage Indicators", None,
  "Floating damage numbers and a boss-style health bar for whatever you're currently hitting, with its name and active potion effects."),
 ("MobAmputation-4.0.1.jar", "Combat", "Mob Amputation", None,
  "Limbs come off when you hit hard enough, and the mob keeps coming without them."),
 ("MobDismemberment-4.0.0.jar", "Combat", "Mob Dismemberment", None,
  "The gorier companion to Mob Amputation — mobs come apart on death rather than politely vanishing."),

 # ---------------- Magic & the Arcane ----------------
 ("Witchery.jar", "Magic", "Witchery", None,
  "A deep witchcraft system: cauldron brewing, ritual circles, broomsticks, voodoo poppets, lycanthropy and vampirism, and demons that notice you meddling."),
 ("ProjectE.jar", "Magic", "ProjectE", None,
  "The modern rewrite of Equivalent Exchange 2 — EMC values, transmutation tables and the Philosopher's Stone line all the way up."),
 ("PandorasBox.jar", "Magic", "Pandora's Box", None,
  "One box, hundreds of possible effects, no way to know which you'll get. Ranges from a free diamond to a localised apocalypse."),
 ("LuckyBlocks.jar", "Magic", "Lucky Blocks", None,
  "Break the block and roll the dice: loot, structures, mob ambushes or something considerably worse."),
 ("Psychedelicraft-1.5.2.jar", "Magic", "Psychedelicraft", None,
  "Brewing, distilling and the substances that follow, with genuinely elaborate shader-driven visual effects."),
 ("Sync-4.0.1.jar", "Magic", "Sync", None,
  "Build a body-swap shell and store a copy of yourself in it. Die anywhere and wake up in the shell with your inventory intact."),

 # ---------------- Franchises & Fiction ----------------
 ("1Legends-1.7.10-8.6.2.jar", "Fiction", "Legends Mod", "8.6.2",
  "Five packs in one — Superheroes, Star Wars, Kaiju, Horror and Battlebourn — each with its own characters, suits, bosses and gear."),
 ("TransformersMod-0.6.3-qf1.jar", "Fiction", "Transformers", None,
  "Transformable vehicles and characters, built from the FiskFille original and rebuilt locally for this pack."),
 ("TardisMod.jar", "Fiction", "TARDIS Mod", None,
  "A working TARDIS: bigger on the inside, flyable between dimensions, with a console room you upgrade over time."),
 ("WeepingAngels.jar", "Fiction", "Weeping Angels", None,
  "They only move when you aren't looking. Blink and you're somewhere else entirely."),
 ("PortalGun-4.0.0-beta-6-fix-1.jar", "Fiction", "Portal Gun", None,
  "The Aperture Science handheld portal device, with companion cubes, turrets, hard light bridges and long fall boots."),
 ("GravityGun.jar", "Fiction", "Gravity Gun", None,
  "Pick up, hold and launch almost anything — blocks, mobs, other players. The supercharged variant disintegrates what it grabs."),
 ("MCHeli.zip", "Fiction", "MC Helicopter", None,
  "Flyable helicopters, jets and tanks with working weapon systems and a proper cockpit view."),

 # ---------------- Tech, Transport & Storage ----------------
 ("Railcraft.jar", "Tech", "Railcraft", None,
  "The definitive rail mod: real track switching and signalling, steam and electric locomotives, tunnel bores, coke ovens and blast furnaces."),
 ("ICBM.jar", "Tech", "ICBM Classic", None,
  "Missiles, launch platforms, radar and remote detonators, from small tactical rockets up to warheads you should not use near your base."),
 ("VoltzEngine.jar", "Tech", "Voltz Engine", None,
  "The engine layer ICBM runs on, providing its energy system, multiblocks and world-edit handling."),
 ("compactmachines-1.7.10-1.21.jar", "Tech", "Compact Machines", None,
  "Cubes that hold a whole room inside. Walk in through a tunnel and build a full factory in a space one block wide."),
 ("enderutilities-1.7.10-0.5.3.jar", "Tech", "Ender Utilities", None,
  "Ender-themed logistics: linked storage, remote inventory access, teleport tools and a builder's wand set."),
 ("OpenBlocks-1.7.10-1.6.jar", "Tech", "OpenBlocks", None,
  "A grab bag that turned out to be essential — elevators, hang gliders, sponges, tanks, trophies, the golden eye, and a sprinkler."),
 ("ArchimedesPlus.jar", "Tech", "Archimedes' Ships Plus", None,
  "Build a vessel out of ordinary blocks, attach a helm, and sail or fly the whole thing as one moving object."),
 ("StorageDrawers.jar", "Tech", "Storage Drawers", None,
  "Wall-mounted drawers that each hold one item type in bulk, with the contents shown on the front. The pack's default bulk storage."),
 ("ironchestuniversal.jar", "Tech", "Iron Chest", None,
  "The chest upgrade ladder — iron, gold, diamond, crystal — each step wider than the last, upgradeable in place."),
 ("EnderStorage-1.7.10-1.4.7.37-universal.jar", "Tech", "Ender Storage", None,
  "Colour-coded chests and tanks that share one inventory across any distance or dimension."),
 ("ChestTransporter.jar", "Tech", "Chest Transporter", None,
  "Pick up a full chest and carry it somewhere else without unpacking it first."),
 ("hopperductmod-1.7.10-1.3.2.jar", "Tech", "Hopper Ducts", None,
  "Hoppers that move items sideways and upward, for item routing that doesn't need a tech mod."),
 ("ChickenChunks-1.7.10-1.3.4.19-universal.jar", "Tech", "ChickenChunks", None,
  "Chunk loaders with a map interface, so your farms and quarries keep running while you're elsewhere."),
 ("WR-CBE-1.7.10-1.4.1.9-universal.jar", "Tech", "Wireless Redstone", None,
  "Redstone signals sent by frequency instead of wire, with handheld remotes and receiver blocks."),
 ("SecurityCraftv.jar", "Tech", "SecurityCraft", None,
  "Keypads, retinal scanners, laser grids, cameras and mines — everything needed to make a base genuinely annoying to rob."),

 # ---------------- Building & Decoration ----------------
 ("Chisel.jar", "Building", "Chisel 2", None,
  "Dozens of alternate textures for nearly every building block, cycled with a single chisel tool."),
 ("CarpentersBlocks.jar", "Building", "Carpenter's Blocks", None,
  "Slopes, stairs, doors and beds that take on the texture of whatever block you cover them with."),
 ("ArchitectureCraft-1.7.2-mc1.7.10.jar", "Building", "ArchitectureCraft", None,
  "Rounded and angled architectural shapes — arches, domes, cladding and window frames — cut from any material."),
 ("BiblioCraft.jar", "Building", "BiblioCraft", None,
  "Display and organisation furniture: bookcases, tool racks, weapon cases, potion shelves, desks, map frames and labelled storage."),
 ("Decocraft.jar", "Building", "Decocraft", None,
  "Over 500 detailed props — kitchenware, instruments, plush toys, tools and clutter — for dressing an interior."),
 ("MrCrayfishsFurnitureMod.jar", "Building", "MrCrayfish's Furniture Mod", None,
  "Working household furniture: fridges that store food, cookers, televisions, showers and blinds."),
 ("malisisdoors.jar", "Building", "Malisis' Doors", None,
  "Animated doors, trapdoors, garage doors, sliding panels and a working elevator, all with proper opening animations."),
 ("Statues.jar", "Building", "Statues", None,
  "A hammer that carves large decorative statues from ordinary building blocks."),
 ("MobStatues.jar", "Building", "Mob Statues", None,
  "Poseable statues of the mobs themselves, for trophies and displays."),
 ("secretroomsmod.jar", "Building", "The SecretRoomsMod", None,
  "Camouflaged blocks, one-way glass and hidden levers for building doors nobody else can find."),
 ("Hats.jar", "Building", "Hats", None,
  "A large wardrobe of cosmetic hats that also show up on mobs you meet."),
 ("HatStand.jar", "Building", "Hat Stand", None,
  "A poseable stand for displaying the hats you've collected."),

 # ---------------- Comfort & Interface ----------------
 ("journeymappunlimited.jar", "Comfort", "JourneyMap", None,
  "The pack's map: live minimap, full-screen world map, waypoints and mob radar, mapped as you explore. Bound to [J]."),
 ("Waila.jar", "Comfort", "Waila", None,
  "Shows what you're looking at and which mod it came from, in a tooltip at the top of the screen."),
 ("NotEnoughItemsuniversal.jar", "Comfort", "Not Enough Items", None,
  "The recipe browser. Search every item in the pack, view its recipe and its uses, and see what it's used for."),
 ("NEIAddons.jar", "Comfort", "NEI Addons", None,
  "Extra NEI panels for mods that ship their own crafting and villager trading systems."),
 ("NEIIntegrationMC.jar", "Comfort", "NEI Integration", None,
  "Fills in NEI recipe handlers for mods that never wrote their own."),
 ("InventoryTweaksdev.jar", "Comfort", "Inventory Tweaks", None,
  "One-key inventory and chest sorting, plus automatic replacement of a tool or stack the moment it runs out."),
 ("Controlling.jar", "Comfort", "Controlling", None,
  "Makes the controls screen searchable — necessary once a hundred mods have all claimed a keybind."),
 ("NoMoreRecipeConflict.jar", "Comfort", "No More Recipe Conflict", None,
  "When two mods claim the same recipe shape, this lets you cycle between the results instead of always getting one."),
 ("GraveStones 1.7.10 -3.jar", "Comfort", "Gravestones", None,
  "Death drops your inventory into a grave at the spot instead of scattering it across the floor to despawn."),
 ("CustomMenu.jar", "Comfort", "Custom Menu", None,
  "Drives the pack's custom title screen — its background, layout and menu music."),
 ("SoundFilters-0.8_for_1.7.X.jar", "Comfort", "Sound Filters", "0.8",
  "Adds reverb in caves and muffles sound underwater and through walls. Small change, large effect underground."),
 ("FastLeafDecay-1.7.10-1.4.jar", "Comfort", "Fast Leaf Decay", None,
  "Leaves decay in seconds after you fell a tree instead of hanging around for minutes."),
 ("inventorypets-1.7.10-1.5.2-universal.jar", "Comfort", "Inventory Pets", None,
  "Living pets that sit in your inventory and grant a passive effect as long as you keep them fed."),
 ("FoodPlus.jar", "Comfort", "Food Plus", None,
  "A large spread of new dishes, drinks and ingredients, with the crops and cooking gear to make them."),
 ("FoodExpansionmc.jar", "Comfort", "Food Expansion", None,
  "More recipes for the food already in the game, so ordinary ingredients have somewhere to go."),
 ("Origin.jar", "Comfort", "Origin", None,
  "A small addition that puts lamb chops on the menu, raw and cooked, under its own Country Gamer tab."),
 ("TrailMix.jar", "Comfort", "Trail Mix", None,
  "A snack that grants a random temporary skill — a fireball, a jump boost — for as long as the effect lasts."),

 # ---------------- Performance & Background ----------------
 ("fastcraft-1.25.jar", "Under", "FastCraft", None,
  "The single biggest frame-rate gain in the pack. Optimises chunk rendering and world ticking with no gameplay change."),
 ("BetterFps-1.0.1.jar", "Under", "BetterFps", None,
  "Swaps in faster maths routines for the hot paths in the render loop."),
 ("OptiFine_1.7.10_HD_U_E7.jar", "Under", "OptiFine", "1.7.10 HD U E7",
  "Render settings, connected textures, dynamic lights and the video options needed to tune the pack to your machine."),
 ("AIImprovements-1.7.10-0.0.1b19-dev.jar", "Under", "AI Improvements", None,
  "Cuts the cost of mob pathfinding, which matters when this many mob mods are loaded at once."),
 ("ChunkPregeneratorV.jar", "Under", "Chunk Pregenerator", None,
  "Generates world chunks ahead of time so exploring doesn't stutter while worldgen catches up."),
 ("MobiusCore.jar", "Under", "MobiusCore", None,
  "Core hooks used for server profiling and diagnostics."),
 ("CraftTweaker-1.7.10-3.1.0-legacy.jar", "Under", "CraftTweaker", None,
  "Lets the pack add, remove and rewrite recipes by script — how the pack's crafting tree is kept coherent across a hundred mods."),
 ("ModTweaker2-0.9.6.jar", "Under", "ModTweaker 2", None,
  "Extends CraftTweaker's reach to mod-specific machines and rituals."),
 ("QuestForgeTweaks-1.0.jar", "Under", "QuestForge Tweaks", None,
  "The pack's own coremod — two bytecode patches, one for the quest panel UI and one for menu music control."),
 ("CodeChickenCore.jar", "Under", "CodeChicken Core", None, "Loader and patching layer required by NEI and the ChickenBones mods."),
 ("1.7.10/CodeChickenLib-1.7.10-1.1.3.138-universal.jar", "Under", "CodeChicken Lib", None, "Shared rendering and utility code for the ChickenBones mods."),
 ("1.7.10/ForgeMultipart-1.7.10-1.2.0.345-universal.jar", "Under", "Forge Multipart", None, "Lets several separate parts — cables, covers, panels — occupy one block space."),
 ("1.7.10/CodingLib-0.2.8b50.jar", "Under", "CodingLib", None, "Support library for the Legends Mod."),
 ("OpenModsLib-1.7.10-0.10.1.jar", "Under", "OpenMods Lib", None, "Shared framework behind OpenBlocks."),
 ("iChunUtil.jar", "Under", "iChunUtil", None, "Shared library for Portal Gun, Gravity Gun, Hats, Sync and the dismemberment mods."),
 ("AnimationAPI.jar", "Under", "AnimationAPI", None, "Model animation framework used by Mutant Creatures and others."),
 ("IvToolkit.jar", "Under", "IvToolkit", None, "Shared toolkit for Recurrent Complex and Pandora's Box."),
 ("malisiscore.jar", "Under", "MalisisCore", None, "Rendering and GUI framework behind Malisis' Doors."),
 ("asielib.jar", "Under", "asielib", None, "Small utility library used by Computronics-family mods."),
 ("DarkCore.jar", "Under", "Dark Core", None, "Core functionality for the DarkCraft mods."),
 ("MovingWorld.jar", "Under", "Moving World", None, "The physics layer that lets Archimedes' Ships move built structures with their tile entities intact."),
 ("Saintscore.jar", "Under", "Saintscore", None, "Core file and pack loader for the Saints content packs."),
 ("littleMaidMobXx.jar", "Under", "MMMLib", None, "Model and multi-model support library for the Little Maid mods."),
 ("MobiusCore.jar_dup", "Under", "", None, ""),
]
T = [t for t in T if t[1] != "Under" or t[2]]

CATS = [
 ("Quests", "Quests &amp; Progression", "The spine of the pack — what to do next, and what you get for doing it."),
 ("Dimensions", "New Dimensions", "Places that aren't the Overworld, each with its own progression."),
 ("Dungeons", "Dungeons &amp; Worldgen", "What fills the map between the dimensions."),
 ("Creatures", "Creatures &amp; Bosses", "Everything that wants you dead, and the tools used to keep it balanced."),
 ("Combat", "Combat &amp; Gear", "How fights actually play out, and what you carry into them."),
 ("Magic", "Magic &amp; the Arcane", "Systems with their own rules, rituals and consequences."),
 ("Fiction", "Franchises &amp; Fiction", "Guest appearances from outside Minecraft."),
 ("Tech", "Tech, Transport &amp; Storage", "Machines, logistics, rails, vehicles and where to put it all."),
 ("Building", "Building &amp; Decoration", "For when the fighting is done and the base still looks like a dirt hut."),
 ("Comfort", "Comfort &amp; Interface", "Information, convenience and the small mercies."),
 ("Under", "Performance &amp; Background", "Nothing to interact with. Libraries, loaders and the mods that keep the frame rate up."),
]

def clean(v):
    """Strip Minecraft colour codes and undecodable bytes.

    Several mods write their mcmod.info with legacy colour codes (MrCrayfish's
    version field is "\xa783.4.7") or in a non-UTF-8 encoding, which decodes to
    U+FFFD. Left in, those characters reach the rendered page and are rejected by
    strict HTML publishers.
    """
    v = re.sub(r'[\ufffd\u00a7]\w?', '', str(v)).strip()
    return ''.join(c for c in v if c.isprintable())

out = []
missing = []
seen = set()
for f, cat, name, vover, desc in T:
    r = rows.get(f)
    if r is None:
        missing.append(f); continue
    seen.add(f)
    ver = vover or r.get('version')
    if ver in (None, 'None', 'null'): ver = ''
    out.append({'cat': cat, 'name': clean(name), 'ver': clean(ver),
                'desc': clean(desc), 'file': f})

unlisted = [f for f in rows if f not in seen and 'CachedResources' not in f]
print("MISSING FROM JARS (typo in table):", missing)
print("JARS NOT CATEGORISED:", unlisted)
print("total listed:", len(out))
from collections import Counter
c = Counter(o['cat'] for o in out)
for k, label, _ in CATS: print(f"  {k:12} {c[k]}")
if missing or unlisted:
    raise SystemExit(
        "catalog is out of sync with the instance:\n"
        + "".join(f"  catalog names a jar that is not installed: {f}\n" for f in missing)
        + "".join(f"  installed jar has no catalog entry:        {f}\n" for f in unlisted)
        + "\nAdd or remove entries in the table above, then re-run."
    )
json.dump({'cats': CATS, 'mods': out}, open('catalog.json','w'), indent=1)
print("wrote catalog.json")
