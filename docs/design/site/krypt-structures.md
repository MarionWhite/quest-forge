# Krypt structure catalogue (research for the endless Krypt, 2026-10-26)

Feeds `docs/design/site/krypt-endless.md`. Every entry is a design described in our own words after
reading the pack's jars; nothing here is copied geometry. A builder should be able to turn any entry
into a walk-through corridor segment ("kind") without opening the mod.

Sources read (read-only copies, unzipped in the session scratchpad): Doomlike Dungeons 1.11.0.1,
Roguelike Dungeons 1.5.0b, Chocolate Quest 1.1d, Recurrent Complex 0.9.7.1.1, The Twilight Forest 2.4.3,
OreSpawn 20.2, Lucky Blocks 5.1.0, Hardcore Ender Expansion 1.8.6, Witchery 0.24.1, SecretRooms 4.7.1,
Lycanites Mobs 1.13.0.5, and the vanilla 1.7.10 jar.

## How to read an entry

- **Frame.** Unless the entry says otherwise, a segment is a corridor with a 3-wide, 3-high walking
  channel (kinds may widen to 5-7 and rise to 4-8), a floor, a ceiling, and **grave alcoves**: recesses
  1 deep, 2 wide, 2 high, cut into either wall every 4 blocks (so up to 2 graves per 4 blocks).
  "Alcove dressing" says what frames the recess in that kind.
- **Block ids** are 1.7.10 numeric ids (meta in brackets): stone 1, cobble 4, planks 5, lava 10/11,
  water 8/9, sand 12, gravel 13, log 17, leaves 18, glass 20, lapis 22, sandstone 24, rails 27/66,
  web 30, wool 35, TNT 46, bookshelf 47, mossy cobble 48, obsidian 49, torch 50, fire 51, spawner 52,
  chest 54, stairs 53/67/108/109/114/128, ladder 65, pressure plate 70/72, ice 79, snow 80, clay 82,
  fence 85, netherrack 87, soul sand 88, glowstone 89, stone brick 98 (0 plain, 1 mossy, 2 cracked,
  3 carved), iron bars 101, vine 106, nether brick 112, nether brick fence 113, end stone 121,
  end portal frame 120, redstone lamp 123/124, cobble wall 139, quartz 155, stained clay 159,
  hardened clay 172, packed ice 174, hay 170, carpet 171.
- **Texture code** names the jar that holds the PNG and the licence status the owner needs for the
  open decision in `ops/DECISIONS.md` (Site, game assets):

| Code | Jar and path | Licence status |
|---|---|---|
| VAN | `1.7.10.jar` : `assets/minecraft/textures/blocks/` | Mojang. Already in use on the site; covered by the open decision. |
| OS | `orespawn.zip` : `assets/orespawn/textures/blocks/` | Already in use per the spec; no licence file in the zip. |
| TF | `TwilightForest-2.4.3.jar` : `assets/twilightforest/textures/blocks/` | No licence file in the jar. Unverified: treat as all-rights-reserved until the owner confirms. |
| HEE | `HardcoreEnderExpansionMCv.jar` : `assets/hardcoreenderexpansion/textures/blocks/` | No licence file. Unverified, same treatment. |
| WIT | `Witchery.jar` : `assets/witchery/textures/blocks/` | No licence file; credits point to the author's site. Unverified. |
| SR | `secretroomsmod.jar` : `assets/secretroomsmod/textures/blocks/` | No licence file. Unverified. |
| CQ | `chocolateQuest-1.7.10-1.1d.jar` : `assets/chocolatequest/` | No licence file. Its dungeons use almost only vanilla blocks, so no CQ texture is needed. |
| none | Roguelike, Doomlike, Recurrent Complex, Lucky | These build with vanilla blocks only (Lucky has only its own lucky block). Nothing to license beyond VAN. |

  Rule of thumb for a builder: an entry marked "VAN only" can ship if the VAN decision lands; an entry
  that needs TF, HEE, WIT, SR or CQ art should have a VAN fallback (given in its line) so it can be
  dropped or swapped without losing the kind.

## Where the data lives (for krypt-gen)

| Mod | Machine-readable files | Format |
|---|---|---|
| Chocolate Quest | `assets/chocolatequest/Chocolate/DungeonConfig/Building/**/*.schematic` (stronghold rooms `stronghold/rooms/room0..room102.schematic`, 15x10x15 each; `boss_room/`, `stairs/`, `entrance/`, `entrance_desert/`, `castles/`, `snowCastles/`, `village/`, `ships/`, `pigcity/`) and `DungeonConfig/*.prop` | Schematics are gzip NBT (MCEdit: `Width`, `Height`, `Length`, `Blocks`, `Data`). Ids 165 and 176-178 are Chocolate Quest's own blocks; 178 fills 20-70% of big castles and is almost certainly a placeholder (treat as air). `.prop` files are plain `key = value` text. |
| Recurrent Complex | `assets/reccomplex/structures/active/structures/*.rcst` (60 top-level, plus `stoneMaze/`, `mesoMaze/`, `pyramid/`, `forestMaze/`, `village/` maze-piece folders) | Each `.rcst` is a ZIP of `structure.json` (generation rules, authors) and `worldData.nbt` (gzip NBT: `blockCollection` with `mapping` = block names, `blocks.blocksCompressed`, `width`, `height`, `length`, plus `tileEntities`, `entities`). Block names are readable, so a parser can pull palettes without decoding the voxel stream. |
| Doomlike Dungeons | `jaredbgreat/dldungeons/res/themes/*.cfg` (classic, common, dank, desert, frozen, jungle, mesa, nether, oceanic, urban, villagelike, volcanic, continentalShelf, template) plus `chests.cfg`, `nbt.cfg` | Plain text key = value lists: `walls`, `floors`, `ceilings`, `fencing`, `liquid`, `pillarBlock`, `commonMobs`, probability ladders. Easy to parse; the "layout" is code (`planner/Dungeon`). |
| Roguelike Dungeons | none; all code (`dungeon/rooms/*`, `dungeon/segment/part/*`, `theme/Theme*.class`) | Rooms, wall segments and themes are classes; use this document as the data. |
| Twilight Forest | none; all code (`twilightforest/structures/**`) | Classes only. Recurrent Complex's maze folders approximate the labyrinth pieces as files. |
| OreSpawn, Lucky, HEE, Witchery | none; all code | Classes only. |

## Strata (descending order, shallow to deep)

Each stratum is a band of a few hundred graves. Order and the kinds each stratum draws from:

| # | Stratum | Character | Entries |
|---|---|---|---|
| 1 | Stone crypts and old mines | grey stone brick, torches, dust | 1-7 |
| 2 | Catacombs and ossuaries | bones, skulls, niches, tombs | 8-14 |
| 3 | Sewers, flooded halls and the drowned deep | water, iron bars, green damp | 15-21 |
| 4 | Mosswild: jungle, roots and fungus | moss, vines, mushrooms, webs | 22-28 |
| 5 | Sand temples and pyramids | sandstone, traps, gold light | 29-35 |
| 6 | The Hedge and the Labyrinth (Twilight Forest) | mazestone, hedges, hollow hills | 36-42 |
| 7 | The Knight stronghold and the towers (Twilight Forest) | carved stone, tower wood, forcefields | 43-49 |
| 8 | Halls of Chocolate Quest | castles, strongholds, ships, cathedrals | 50-56 |
| 9 | Arcane halls and witch lairs | libraries, labs, smithies, covens, secret doors | 57-64 |
| 10 | The Nether | nether brick, lava, fire, soul sand | 65-71 |
| 11 | The End (Hardcore Ender Expansion) | obsidian, ravaged brick, energy | 72-77 |
| 12 | The Hollow Beyond (OreSpawn vaults, altars, Lucky) | crystal, gems, cages, altars | 78-84 |

Mood sequence for the owner's brightening rule: inside each stratum the torch count rises and the
light warms from cold white (`#cfe3ff`) toward amber (`#ffb347`); the first segment of a stratum is
always the stratum's darkest, coolest one.

---

## Stratum 1: Stone crypts and old mines

### 1. Doomlike "classic" hall
- **Source:** Doomlike Dungeons, `res/themes/classic.cfg` and `common.cfg`, layout in `planner/Dungeon`.
- **Layout:** 2-10 rectangular rooms joined by short passages, many sizes (the theme gives size ladders from small to huge), optional sub-rooms, islands (raised platforms in a room), pillars, fences, inner symmetry. Y 30-50. A Doom-style level: a room, a doorway, a room.
- **Blocks:** walls stone brick 98 / cobble 4 / sandstone 24 / brick 45; floors stone brick, cobble, dirt 3, stone 1; ceilings stone brick, cobble, planks 5, double slab 43; cobble wall 139 / fence 85 for rails; water and lava pools. **Tex:** VAN only.
- **Features:** pillars every few blocks, lava/water pits in floors, rooms with spawners and chests, stairs between levels.
- **Mobs:** Zombie, Skeleton, Spider (common), Creeper, Enderman, Cave Spider (hard), Witch (brute).
- **Mood:** plain, slightly random, a first-level dungeon.
- **Segment:** "classic hall": corridor widens to 7 wide x 4 high for 14-24 blocks, a stone brick floor with a 1-wide cobble strip or dirt patch, pillars (98[3] carved) every 6 blocks standing 1 in from the wall, double-slab ceiling. Alcoves are plain recesses with a cobble-wall lip. Vary: swap wall set, add an island (a 3x3 raised platform in the middle of the path with a torch fence post), add a water pit the path skirts.

### 2. Doomlike "common" crypt (darker variant)
- **Source:** Doomlike Dungeons, `res/themes/common.cfg`.
- **Layout:** same planner, Y 25-50, adds mossy-brick (98[1]) weighting through the `stonebrick(2)` entries (cracked), `caveblock` stone.
- **Blocks:** stone brick 98 / 98[2] cracked / cobble; ceilings planks and double slab. **Tex:** VAN only.
- **Features:** cracked brick ratio rising with depth; spawner cells.
- **Mobs:** as classic. **Mood:** colder than 1, older.
- **Segment:** "worn crypt": narrower 3x3 corridor, 25% of wall blocks swapped to cracked 98[2], 10% of floor to gravel 13, ceiling dips to 2 high at the alcove mouths. Torch every 8 blocks only.

### 3. Roguelike "Crypt" theme
- **Source:** Roguelike Dungeons, `theme/ThemeCrypt`, rooms `DungeonsCrypt`, segment `SegmentTomb`.
- **Layout:** a hall lined with 2x2 tomb recesses; each recess holds a quartz-bordered sarcophagus (quartz 155 + stairs) in the room version.
- **Blocks:** andesite (not in 1.7.10: substitute stone 1), stone brick 98 / 98[1] / 98[2], cobble 4, gravel 13; tombs use quartz 155 with quartz stairs 156. **Tex:** VAN only.
- **Features:** every recess has a skeleton or zombie spawner 52 behind or a chest with weapons or armour; some alcoves get a skull.
- **Mobs:** Skeleton, Zombie. **Mood:** reverent and ominous, the closest thing in the pack to our own graves.
- **Segment:** "tomb gallery": 20 blocks long, 5 wide; the walls are lined with quartz-capped tomb recesses (alcoves) 2 high, a 156 stair lip at the recess mouth, a sconce (torch 50) between every pair. Because each recess is a grave, this is the best direct fit: alcove dressing = quartz slab cap (44[7]) over the grave, stone brick pilaster between recesses.

### 4. Roguelike "Tower" and "Grey" themes (bare vault)
- **Source:** Roguelike Dungeons, `theme/ThemeTower`, `ThemeGrey`, `ThemeBrick`.
- **Layout:** the grey/tower theme is used for corridor stubs with arches (`SegmentArch`, `SegmentSquareArch`) every 3-4 blocks.
- **Blocks:** polished andesite (not in 1.7.10: stone 1), stone brick 98 and variants, cobble, gravel; stairs 109. **Tex:** VAN only.
- **Features:** repeating arches, insets (`SegmentInset`), blank walls. Torches in insets.
- **Mobs:** none specific (the dungeon level picks).
- **Mood:** clean, institutional, a "ledger hall".
- **Segment:** "arch run": repeating stone-brick arches (stairs 109 on each side, a slab 44 keystone) every 4 blocks over a 3-wide path; alcoves go between arches. Cheap, fast, useful as a filler between ornate segments.

### 5. Vanilla monster dungeon room
- **Source:** vanilla 1.7.10, `WorldGenDungeons` (the cobblestone cell with a spawner).
- **Layout:** one room 5x5 to 9x9, floor-to-ceiling 4, solid walls; floor is a mix of cobble and mossy cobble 48 (about 1 in 4 mossy); a spawner 52 in the centre on a single block; two chests in the walls.
- **Blocks:** cobble 4, mossy cobble 48, spawner 52, chest 54. **Tex:** VAN only (`cobblestone`, `cobblestone_mossy`, `mob_spawner`, `chest` model).
- **Features:** the spawner cage glimmer; chests; no light of its own (dark).
- **Mobs:** Zombie, Skeleton, Spider.
- **Mood:** the first, simplest, most iconic Minecraft dungeon: a beginner's shock.
- **Segment:** "spawner cell": a 7x7x4 room the path crosses diagonally; a spawner on a pedestal in the middle (a short stub of cobble wall 139 supports it), mossy/cobble checker floor, chest alcoves in the corners; the room lights with two wall torches only. Great as a breather every ~20 segments.

### 6. Vanilla mineshaft corridor
- **Source:** vanilla 1.7.10, `StructureMineshaftPieces` (corridor, crossing, room, stairs).
- **Layout:** 3-wide, 3-high tunnels, with a support frame every 4-5 blocks (two fence posts 85 and a plank beam 5 across), optional minecart rails 66 down the middle, cobwebs 30 across the passage, occasional cave-spider spawner 52 inside a web-filled stub with a chest minecart.
- **Blocks:** planks 5, fence 85, rails 27/66, web 30, torch 50, spawner 52. **Tex:** VAN only.
- **Features:** the rhythmic timber frames; a rail line along the floor; webs thickening toward the spawner; a floor of dirt/gravel.
- **Mobs:** Cave Spider. **Mood:** dusty, creaky, cramped.
- **Segment:** "timber shaft": the 3x3 channel with the support frame every 4 blocks (the alcoves sit between frames; the graves are cut into the stone with a fence-post jamb), rails down the middle, web 30 tufts in corners, and a stub where a spawner sits behind iron bars. Strong rhythm. Kind parameter: web density, rail broken-gap count.

### 7. Recurrent Complex "Small Abandoned Mine", "Underground Crypt", "Peaceful Crypt"
- **Source:** Recurrent Complex, `structures/SmallAbandonedMine.rcst` (26x14x16), `UndergroundCrypt.rcst` (29x15x15, Y 30-45 above bedrock, rotatable), `PeacefulCrypt.rcst` (25x6x17, surface).
- **Layout:** the mine is a ledge with rails and a vine-hung adit; the underground crypt is a 29-long hall with a spawner each end, two stone-brick bays, carpet runner, hanging wool banners; the peaceful crypt is a small mausoleum with a redstone/lever secret.
- **Blocks:** crypt: stone 1, stone brick 98, stairs 109, slab 44/126, cobble, carpet 171, stained glass 95, redstone torch 76, wool 35, mob_spawner 52, a chest; mine: rail 66, coal ore 16, iron ore 15, vine 106, fence 85, planks 5, gravel 13, lever 69. **Tex:** VAN only.
- **Features:** red-and-white wool hangings, carpet aisle, coloured-glass window slots (stained 95 shows as dim colour), levers.
- **Mobs:** Bat, Skeleton, Zombie (crypt). **Mood:** dignified crypt, a little warmer.
- **Segment:** "carpet crypt": 29 long, 5 wide, a red carpet 171[14] runner, banners (wool 35[14] strips) hung on the walls between alcoves, stained-glass slits (95) in the ceiling for coloured shafts of light, redstone torches (76) as the only light (a dim red glow). Strong for a distinct palette.

---

## Stratum 2: Catacombs and ossuaries

### 8. Roguelike Ossuary
- **Source:** Roguelike Dungeons, `rooms/DungeonOssuary`, `segment/part/SegmentSkull`.
- **Layout:** a small chamber whose walls are filled with skull and bone niches: skull items (Skull.SKELETON, WITHER, ZOMBIE) set into inset recesses.
- **Blocks:** skeleton skull / wither skull heads (144 meta 0/1/2), stone brick 98, quartz 155 trim, chests. **Tex:** VAN only (skulls are an entity-model block).
- **Features:** heads on shelves in the wall; wither skulls show as dark skulls.
- **Mobs:** Skeleton, Wither Skeleton. **Mood:** morbid, quiet.
- **Segment:** "skull wall": the alcoves in this kind are not graves but skull niches (1x1) stacked 3 high between the real grave alcoves. The side wall becomes 60% skulls and niches. Excellent for the catacomb stratum's identity.

### 9. Roguelike "Dark Hall" and tomb segments
- **Source:** Roguelike Dungeons, `rooms/DungeonDarkHall`, `ThemeDarkHall`, `SegmentTomb`, `SegmentShelf`.
- **Layout:** a long hall with dark-oak stairs forming a vaulted ceiling, mossy and cracked brick, gravel.
- **Blocks:** stone brick 98 (0/1/2), cobble 4/mossy 48, gravel 13, dark oak stairs (1.7.10 has no dark oak: use spruce stairs 134, planks 5[1]). **Tex:** VAN only.
- **Features:** wooden roof beams, long barren hall, no spawners in the hall itself.
- **Mobs:** Zombie, Skeleton. **Mood:** hush before something.
- **Segment:** "vaulted hall": 6 wide, 5 high with a stair-stepped vault (stairs 134 along the upper wall), crossbeams of spruce log 17[1] every 6 blocks. Light: one torch per beam. Good as a slow-pace pause.

### 10. Chocolate Quest stronghold "skull room" and library
- **Source:** Chocolate Quest, `DungeonConfig/Building/stronghold/rooms/room11.schematic` (skull room), `room6.schematic` (library), `boss_room/bossLibrary.schematic`.
- **Layout:** 15x10x15 chambers. room11: stone brick floor with planks and fences, 20 glowstone 89, 7 skulls (144), four doors, silverfish bricks. room6: 360 bookshelves 47 in tiers, planks galleries, ladder 65 x4, web 30 patches. bossLibrary: 364 bookshelves with mineral-ore reward blocks (diamond ore 56, emerald ore 129, lapis ore 21, gold ore 14) hidden in three chests.
- **Blocks:** stone brick 98, bookshelf 47, planks 5, glowstone 89, skull 144, ladder 65, web 30, ore blocks. **Tex:** VAN only.
- **Features:** the glowstone-and-skull room is a warm-lit death shrine; the library is cobwebby tiers of books.
- **Mobs:** Skeleton, Silverfish.
- **Mood:** abandoned scriptorium, melancholy.
- **Segment:** "scriptorium": the path crosses a 15-long room in which the side walls are bookshelves 47 three high, with a web-hung gallery above (planks 5 + ladder), and the graves are recessed between shelf bays. Warm glowstone sconces. Parameter: bookshelf density, web count.

### 11. Recurrent Complex "Meso Maze" pieces
- **Source:** Recurrent Complex, `structures/mesoMaze/*.rcst` (11 pieces: Corridor, 3Way, Crossing, Turn, End, CorridorCollapse, SpiderTurn, StairCorridor, StairTurn, Storage, ZombieTable).
- **Layout:** a modular catacomb: 3x4x3 cells for corridor, turn, 3-way, crossing and dead end; larger 6x4x6 rooms for the spider turn (cave spider spawner in webs), storage (chest with stairs and slabs as shelves), zombie table (zombie spawner with stair seats), 6x8x3/6 stair pieces going down a storey, a 3x8x5 corridor-collapse (slabs fallen into the passage).
- **Blocks:** stone brick 98, stairs 109, slab 44, web 30, mob_spawner 52, chest 54. **Tex:** VAN only.
- **Features:** the collapse piece is a ready-made "ceiling fell in" segment; stair pieces change level.
- **Mobs:** Cave Spider, Zombie.
- **Mood:** structured and claustrophobic.
- **Segment:** "meso cell chain": pieces are only 3 long, so combine 5-8 into a 15-24 block corridor of 3x4 cells with a turn or a collapse (slabs 44 half-blocking the floor so you step over, rubble gravel). Keep the cell as the alcove rhythm (alcove in every second cell).

### 12. Recurrent Complex "Stone Maze" pieces
- **Source:** Recurrent Complex, `structures/StoneMaze.rcst` (36x5x36), `StoneMazeSmall.rcst` (24x5x24, Y 10-30, bedrock-anchored), `stoneMaze/*.rcst` (Corridor, 3Way, Crossing, End, EndChest, Turn, Fountain 9x6x9 with lava, LitRoom with glowstone, ShootingRange 9x6x6 with lava and a skeleton spawner, SpiderRoom with webs and chest, Study 15x4x9 with bookshelves).
- **Blocks:** plain stone 1 (walls), stone brick 98, lava 10/11, glowstone 89, bookshelf 47, carpet 171, oak/spruce stairs 53/134, web, a log. **Tex:** VAN only.
- **Features:** a stone maze with small rooms: lava fountain, shooting range (a skeleton firing across a lava moat), a study with books and carpet.
- **Mobs:** Skeleton, Cave Spider.
- **Mood:** solemn labyrinth in raw stone; unlike the brick pieces this uses plain stone 1 for a cut-rock feeling.
- **Segment:** "raw-rock tunnel": a 3x4 smooth stone corridor (no bricks), with a lava moat (2 wide) in the floor crossing every 14 blocks and a bridge of stone slabs; the "shooting range" version has a skeleton spawner behind the lava. This is also the natural source of the **gap-with-lava** the endless spec wants at bends.

(Entries 13 and 14 continue below.)
