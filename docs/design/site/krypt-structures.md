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
| 7 | The Knight stronghold and the towers (Twilight Forest) | carved stone, tower wood, auroras | 43-49 |
| 8 | Halls of Chocolate Quest | castles, strongholds, ships, cathedrals | 50-56 |
| 9 | Arcane halls and witch lairs | libraries, smithies, covens, secret doors | 57-64 |
| 10 | The Nether | nether brick, lava, fire, soul sand | 65-71 |
| 11 | The End (Hardcore Ender Expansion) | obsidian, ravaged brick, lab glass | 72-77 |
| 12 | The Hollow Beyond (OreSpawn vaults, altars, Lucky traps) | crystal, gems, cages, altars | 78-84 |

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


### 13. Vanilla stronghold corridors, prison cells and library
- **Source:** vanilla 1.7.10, `StructureStrongholdPieces` (Straight, Prison cell, Library, Stairs, Chest corridor, Fountain, Portal room).
- **Layout:** 5-wide, 5-high halls of stone brick; the straight hall has a randomly placed iron-door gap; the prison hall has a row of 3-4 cells, each 1-wide, closed with iron bars 101 and a door; the library is 14x6x11 with two bookshelf tiers 47, a ladder-less gallery, cobweb 30 and a chest at the top; the chest corridor has a single chest 54 on a dais.
- **Blocks:** stone brick 98 (0/1/2/3), iron bars 101, iron door 71, bookshelf 47, torch 50, web 30, silverfish blocks 97 for the "infested" bricks. **Tex:** VAN only (`stonebrick*`, `iron_bars`, `bookshelf`).
- **Features:** the iron-barred cell row is the exact motif of a grave row; iron doors; arched ceilings in the library.
- **Mobs:** Silverfish (infested bricks).
- **Mood:** cold, cavernous, ancient.
- **Segment:** "barred cell row": each grave alcove gets an iron-bars front (101) with a 1-block gap like a cell door; mix 98[0], [1], [2]; torches only at the hall corners. Parameter: how many alcoves are barred versus open; silverfish infested-brick chance (visual only: render as cracked brick).

### 14. Roguelike prison cells and silverfish nest alcoves
- **Source:** Roguelike Dungeons, `segment/alcove/PrisonCell`, `segment/alcove/SilverfishNest`, `segment/part/SegmentPrisonCell`, `SegmentSilverfish`, `rooms/DungeonsPrison`.
- **Layout:** alcoves in the corridor wall: a prison cell is a 2-deep alcove closed by an iron door 71 (with a pressure plate 70 and a zombie spawner 52 behind); a silverfish nest alcove has soul sand 88 and a silverfish spawner.
- **Blocks:** iron bars 101, iron door 71, stone pressure plate 70, soul sand 88, spawner 52. **Tex:** VAN only.
- **Features:** alcoves that are hostile: stepping on the plate opens the cell.
- **Mobs:** Zombie, Silverfish. **Mood:** menace in the wall.
- **Segment:** "cell block alcoves": the same grave-alcove rhythm but 1 in 5 alcoves is a tiny prison (iron bars across, a pale shape visible inside: a standing skeleton or a pile of bones). Pairs well with the scares: a cell can be a jump-scare trigger.

---

## Stratum 3: Sewers, flooded halls and the drowned deep

### 15. Roguelike Sewer theme
- **Source:** Roguelike Dungeons, `theme/ThemeSewer`, `segment/part/SegmentSewer`, `SegmentSewerArch`, `SegmentSewerDoor`, `SegmentSewerDrain`.
- **Layout:** the walkway has a channel of flowing water down one side (1-2 wide, 1 deep); arches 3-4 apart; sewer doors (iron door 71 framed by bars 101 and a glowstone 89 above); drain grates in the wall.
- **Blocks:** stone brick 98 (0/1/2), mossy cobble 48, iron bars 101, water 8/9, glowstone 89, spruce leaves 18[1] as dangling growth. **Tex:** VAN only (`water_still`, `water_flow`, `iron_bars`).
- **Features:** water runs in a channel with the path as a raised stone curb; drains pour from the walls; green glowstone-lit doors.
- **Mobs:** Zombie, Slime, Skeleton. **Mood:** damp, echoing, a bit filthy.
- **Segment:** "sewer walk": 4 blocks across; a 1-wide 1-deep water channel along the left wall, curb stones on the right; alcoves (graves) on the dry side with iron-bar grates; glowstone lamps every 6 blocks with a pale yellow-green cast. Water flow animation (VAN `water_flow`) is the signature.

### 16. Roguelike drain/arch variants and sewer door cell
- **Source:** same, `SegmentSewerArch` (mossy arch with water jets), `SegmentSewerDrain` (a bars-fronted 2x2 outlet pouring water into the channel).
- **Layout:** one-block-deep inset in the wall, bars across, water source behind.
- **Blocks:** mossy cobble 48, bars 101, water 8. **Tex:** VAN only.
- **Features:** pouring water: animated, audible.
- **Segment:** "drain gallery": alternate grave alcoves and drains every 4 blocks; the drains keep the channel full. Vary the drain colour with wet-wall dark-stone shading (render mossy 98[1]). 8-16 blocks long.

### 17. Doomlike "dank" swamp hall
- **Source:** Doomlike Dungeons, `res/themes/dank.cfg`, type SWAMP flag SWAMPY.
- **Layout:** Y 40-50; the room floors are largely water (85% of the liquid ladder), with islands of dirt/planks as stepping platforms; verticle ladders favour low rooms.
- **Blocks:** mossy cobble 48, stone brick 98[1], planks 5, water 8/9, log 17; ceilings planks and mossy brick; fences: cobble wall 139[1] and fence 85. **Tex:** VAN only.
- **Features:** plank walkways across water (the dungeon's own bridging), islands, fences.
- **Mobs:** Zombie, Skeleton, Spider, Creeper, Cave Spider, Witch.
- **Mood:** rotten, boggy, creaking.
- **Segment:** "plank causeway": the path is a 1-wide plank (5) walkway with fence-post rails over a water floor (waist-deep: the visible water plane 1 block below), alcoves cut into mossy walls. Plank bridges can also be the **gaps** the spec calls "water gaps": a 2-3 block missing plank over water.

### 18. Doomlike oceanic and continental shelf halls
- **Source:** Doomlike Dungeons, `res/themes/oceanic.cfg`, `continentalShelf.cfg`.
- **Layout:** the oceanic theme puts water in rooms and in the ceiling (a ceiling entry of `water`); shelf: water everywhere (liquid ladder 100% water in oceanic), no entrance (`entrances 0`), Y 10-15.
- **Blocks:** stone brick, cobble, sandstone, brick 45; gravel 13 for seabed; ceilings can be water 9. **Tex:** VAN only.
- **Features:** you look up at a water ceiling; the room is a sealed pocket under the sea.
- **Mood:** deep, muffled, claustrophobic.
- **Segment:** "drowned hall": a normal brick corridor with a water layer for the ceiling (one extra layer rendered as translucent blue plane), blue-tinted fog, bubbles. Ties directly to the water-gap jump (fall into the flooded section). 12-20 long, with a single sunken stretch.

### 19. Roguelike Pit and Slime rooms
- **Source:** Roguelike Dungeons, `rooms/DungeonsPit`, `rooms/DungeonsSlime`.
- **Layout:** DungeonsPit: a chamber with a bedrock-looking floor drop, a pressure plate 70 wired with redstone 55 and redstone torches 76 that drops flooding water 8; DungeonsSlime: an iron-barred cell around a water-filled floor with slime spawn.
- **Blocks:** bedrock 7 (floor), stone pressure plate 70, redstone 55, redstone torch 76, water 8, iron bars 101. **Tex:** VAN only.
- **Features:** the pit trap floods; the redstone tell (little red torches in the wall).
- **Mobs:** Slime. **Mood:** a trap you can read, unlike the rest.
- **Segment:** "pressure plate flood": a 6-long corridor with a visible stone plate, red torch glints on the wall; stepping triggers (scare hook) a water surge. Pair with krypt-gap's takeover for a reaction.

### 20. Recurrent Complex "Well Shrine"
- **Source:** Recurrent Complex, `structures/WellShrine.rcst` (17x21x17 above-ground, 21 tall: a well).
- **Layout:** a stone-brick well shaft with white-wool banners descending 10+ blocks to water, with stairs/slabs forming a cap.
- **Blocks:** stone brick 98, stairs 109, slab 44, wool 35[0], water 8/9. **Tex:** VAN only.
- **Features:** vertical descent, banner-lined shaft.
- **Mood:** votive, quiet, clean.
- **Segment:** "well descent": the path spirals downward around a water shaft (a 5x5 shaft with a 1-wide stair along the wall), white banners hanging; 8 blocks deep, 20 stair steps; alcoves in the shaft wall. A natural **vertical transition** between strata.

### 21. Lucky Blocks water trap, wishing well and cage
- **Source:** Lucky Blocks, `mod/lucky/util/CustomStructures` (`makeWaterCage`, `makeWishingWell`, `makeCage`); data in `LuckyBlockProperties.txt` (IDs `water_trap`, `wishing_well`).
- **Layout:** a small cage built around the player: a hollow box of iron bars 101 with water 9 inside (water cage); a wishing well: ring of cobble 4 with a water pool and a hidden lucky block 3 below plus beacon 138 drop ("a wishing well").
- **Blocks:** iron bars 101, water 9, cobble 4, glass 20, iron block 42. **Tex:** VAN only. Lucky's own block texture is `assets/lucky/textures/blocks/lucky_block.png` in LuckyBlocks.jar (already used on the site).
- **Mobs:** none.
- **Mood:** a cruel joke; a coin in the well.
- **Segment:** "wish alcove": one alcove in a flooded hall is a mini wishing well (3x3 cobble ring, water, a gold-nugget glint); in the Krypt, the well is a grave-adjacent offering (players leave a coin). Fits a late-stratum surprise.

---

## Stratum 4: Mosswild (jungle, roots and fungus)

### 22. Doomlike jungle ruin
- **Source:** Doomlike Dungeons, `res/themes/jungle.cfg`.
- **Layout:** Y 25-50; more pillars, fewer symmetric rooms (symmetry 0 for small sizes), degeneracy 0 (rooms are intact); entrances plentiful (up to the top of the ladder).
- **Blocks:** stone brick 98 and mossy 98[1], mossy cobble 48, double slab 43, cobble wall 139[1], stone brick carved 98[3]. **Tex:** VAN only.
- **Mobs:** Zombie, Skeleton, Spider, Creeper, Enderman, Cave Spider, Witch.
- **Mood:** old, overgrown, still intact.
- **Segment:** "overgrown hall": normal hall with 30% mossy swaps, vine 106 hanging from the ceiling at random, a carved-brick (98[3]) pillar pair at the entrance. Add a "fallen pillar" (a lying line of carved bricks across the floor) as an obstacle.

### 23. Roguelike Jungle, Mossy and Muddy themes
- **Source:** Roguelike Dungeons, `theme/ThemeJungle`, `ThemeMossy`, `ThemeMuddy`, `segment/part/SegmentJungle`, `SegmentMossyArch`, `SegmentPlant`, `SegmentFlowers`, `SegmentWheat`.
- **Layout:** the jungle segment grows grass 2 and leaves 18[3] out of wall niches with water; the muddy theme mixes clay 82, dirt 3 (coarse -> 3), mycelium 110, soul sand 88, cobble and cracked bricks; plant niches have podzol (use dirt), fern, peony, rose.
- **Blocks:** mossy cobble 48, stone brick (0/1/2/3), grass 2, dirt 3, clay 82, mycelium 110, vines 106, leaves 18, water 8. **Tex:** VAN only.
- **Mobs:** Zombie, Skeleton, Spider, Creeper.
- **Mood:** wet, overgrown, spore-heavy.
- **Segment:** "root hall": alcoves are planter niches with moss/fern around the grave, the floor is muddy (mix dirt and clay), vines drip. Parameter: growth density. Pair with greenish low fog.

### 24. Roguelike Spider Nest and Mushroom segment
- **Source:** Roguelike Dungeons, `rooms/DungeonsSpiderNest`, `segment/part/SegmentMushrooms`.
- **Layout:** a chamber of gravel 13 and cobweb 30 with a cave-spider spawner 52; the mushroom segment sets a mycelium 110 bed with brown and red mushrooms in flower pots.
- **Blocks:** web 30, gravel 13, spawner 52, mycelium 110, mushroom 39/40, flower pot 140. **Tex:** VAN only (`web`, `mycelium_top`, `mushroom_*`).
- **Mobs:** Cave Spider.
- **Mood:** webbed and sticky, cautionary.
- **Segment:** "webway": the passage is draped with webs 30 across at head height (visual only, not blocking), thick web in the alcoves around the graves, a spawner cage with a spider eye glint. 10-16 long.

### 25. Recurrent Complex "Underground Treeoid"
- **Source:** Recurrent Complex, `structures/UndergroundTreeoid.rcst` (24x25x27, Y 8-40).
- **Layout:** a giant underground tree-shaped cavern: log trunk 17, leaves 18, red and brown mushroom blocks 99/100, grass 2, dirt, vines 106, web 30, redstone ore 73, a cave-spider spawner, water.
- **Blocks:** log, leaves, mushroom blocks, vine, web, stone. **Tex:** VAN only.
- **Features:** a living column at the cavern centre; roots and mushroom caps overhead.
- **Mobs:** Cave Spider, Bat.
- **Mood:** wonder in the dark, surprising.
- **Segment:** "root cavern": the path wraps 180 degrees around a log-and-mushroom trunk; ceiling hung with mushroom blocks and leaves; water pool below the path. 20-30 long. Provides a **big open space** to break up tunnels.

### 26. Recurrent Complex "Forest Maze" pieces
- **Source:** Recurrent Complex, `structures/ForestMaze.rcst` (53x18x53) and `forestMaze/*.rcst` (Corridor 9x11x9, Crossing, 3Way, Turn, End, Clearing 20x11x20 with a spider spawner and chest, Slimes 11x11x20 with slime spawner and chest).
- **Layout:** a leaf-walled maze: corridors 9 wide between rows of log 17 and leaves 18 on grass; clearing rooms hold saplings, flowers and a spawner.
- **Blocks:** leaves 18, log 17, grass 2, dirt 3, tall grass 31, flowers 37/38, sapling 6. **Tex:** VAN only.
- **Mobs:** Spider, Slime.
- **Mood:** green, dappled, deceptively calm.
- **Segment:** "leaf corridor": a corridor whose walls are leaf blocks with logs at the corners, overhead leaves letting dappled "light" through; alcove graves are leaf-framed hollows (wild flowers around). Not underground feel: use as the **breath stratum** between dark ones.

### 27. Vanilla jungle temple
- **Source:** vanilla 1.7.10, `ComponentScatteredFeaturePieces$JunglePyramid`.
- **Layout:** 12 wide, 10 high, 15 deep stepped mossy block pyramid; interior two floors: a lower chamber behind a hidden lever puzzle (3 levers 69 in a particular order opens a wall); tripwire 132 arrow dispenser corridor (dispensers 23 firing arrows); two chests 54 (one on each level); a hole stair in the floor; vines 106 draped on walls.
- **Blocks:** mossy cobble 48, cobble 4, stairs 67, vine 106, tripwire hook 131, tripwire 132, dispenser 23, lever 69, redstone 55, sticky piston 29, chest 54. **Tex:** VAN only.
- **Features:** the arrow trap corridor (dispensers fire when you cross a tripwire), a piston-hidden stairwell, a lever puzzle.
- **Mobs:** none (traps).
- **Mood:** treasure-hunt tension; the arrow corridor is "classic".
- **Segment:** "arrow gallery": 12 blocks of mossy corridor with dispenser holes in the wall at knee height (animated arrows crossing when a scare triggers); tripwire strands visible across the floor in the dark. Can fire arrows as a **scare**.

### 28. Roguelike Creeper Den
- **Source:** Roguelike Dungeons, `rooms/DungeonsCreeperDen`.
- **Layout:** a mossy-cobble room with gravel floor and TNT 46 buried among the walls, a creeper spawner 52, and ore chest.
- **Blocks:** mossy cobble 48, gravel 13, TNT 46, spawner 52. **Tex:** VAN only.
- **Mobs:** Creeper. **Mood:** hissing, tense.
- **Segment:** "powder room": a mossy-cobble alcove run with TNT blocks (46) visibly in the walls and the floor gravel; sound bed with hissing. A creeper silhouette in an alcove is a scare hook.

---

## Stratum 5: Sand temples and pyramids

### 29. Vanilla desert temple
- **Source:** vanilla 1.7.10, `ComponentScatteredFeaturePieces$DesertPyramid`.
- **Layout:** 21 x 14 x 21 stepped sandstone pyramid with a central chamber 5x5 floored with a blue stained-clay 159[11] cross pattern; beneath it a 3x3 room with a 9-TNT cache 46 over a pressure plate 70; four small chambers in the corners each with a chest 54; two corner towers.
- **Blocks:** sandstone 24 (0/1/2), sandstone stairs 128, stained clay 159[1] orange and [11] blue, TNT 46, stone pressure plate 70, chest 54. **Tex:** VAN only (`sandstone_*`, `hardened_clay_stained_*`, `tnt_*`).
- **Features:** the TNT trap beneath the pattern; orange/blue stained-clay motif.
- **Mobs:** none.
- **Mood:** dry, bright, deceptive: the shock is below.
- **Segment:** "pyramid vestibule": a 21-long sandstone hall with a blue-clay stripe set into the floor that leads to a trap chamber under it (a short descending passage with TNT stacks visible through a grate); chest alcoves in the corners = grave alcoves. TNT as a scare trigger.

### 30. Recurrent Complex "Pyramid Maze" pieces
- **Source:** Recurrent Complex, `structures/pyramid/*.rcst` (identical piece set to Meso Maze but in sandstone 24 and sandstone stairs 128: Corridor, 3Way, Crossing, Turn, End, CorridorCollapse 3x8x5, SpiderTurn, StairCorridor/Turn, Storage with a chest, ZombieTable with spawner).
- **Blocks:** sandstone 24, sandstone stairs 128, slab 44, web 30, spawner 52, chest 54. **Tex:** VAN only.
- **Mobs:** Cave Spider, Zombie.
- **Mood:** archaeological claustrophobia, warmer than the stone maze.
- **Segment:** "sand cell chain": as entry 11 but in sandstone; use smooth sandstone 24[2] for the floors and chiseled 24[1] for pilasters between alcoves. Warm torchlight (amber #ffb347).

### 31. Recurrent Complex Big and Small Pyramid, Temple Pyramid
- **Source:** Recurrent Complex, `BigPyramid.rcst` (49x34x62), `SmallPyramid.rcst` (33x18x37), `TemplePyramid.rcst` (63x32x63, stone brick 98 and stairs).
- **Layout:** big stepped pyramids with an interior of sand, obsidian 49 plugs, chests, torches, stairs sunk into the middle. The temple pyramid is a stone-brick stepped monument for a jungle look.
- **Blocks:** sandstone 24, stairs 128, slab 44, torch 50, obsidian 49, chest 54, stone brick 98. **Tex:** VAN only.
- **Mood:** monumental, awe-inspiring.
- **Segment:** "monument stair": a descending stair 5 wide x 20 steps long, flanked by tall stepped walls with obsidian plugs (sealed doors), with grave alcoves in the plugs; the player descends into the pyramid's belly.

### 32. Roguelike Pyramid theme and tomb rooms
- **Source:** Roguelike Dungeons, `theme/ThemePyramid`, `ThemeTemple`, `rooms/DungeonPyramidTomb`, `DungeonPyramidSpawner`, `DungeonPyramidCorner`, `dungeon/towers/PyramidTower`.
- **Layout:** chambers with sandstone walls (chiseled/smooth), the tomb room holds quartz-bordered sarcophagi with zombie spawners; the spawner room has a ring of sandstone around a spawner 52.
- **Blocks:** sandstone 24 (0/1/2), sandstone stairs 128, quartz 155, spawner 52, chest 54. **Tex:** VAN only.
- **Mobs:** Zombie.
- **Mood:** pharaoh tomb.
- **Segment:** "sarcophagus gallery": like entry 3 but sandstone with gold block (41) caps over the graves; the wall carved with chiseled sandstone friezes (24[1]).

### 33. Doomlike desert and mesa halls
- **Source:** Doomlike Dungeons, `res/themes/desert.cfg`, `res/themes/mesa.cfg`.
- **Layout:** desert Y 35-50; walls sandstone 24 (and [2] smooth); pillars include lapis block 22 and planks; mesa uses all 16 stained clay colours 159[0-15] and hardened clay 172 in walls, floors and ceilings in banded stripes.
- **Blocks:** sandstone 24, lapis block 22, hardened clay 172, stained clay 159 (all metas). **Tex:** VAN only.
- **Mood:** desert: bleak and bright; mesa: rainbow strata, unusual.
- **Segment:** "banded hall": a mesa kind with horizontal wall bands (e.g. 159 metas 1,7,14,12 repeating every 2 blocks high). Visually the most colourful kind in the catalogue; use sparingly.

### 34. Chocolate Quest desert entrances: sphinx, pyramid, statues, oasis
- **Source:** Chocolate Quest, `DungeonConfig/Building/stronghold/entrance_desert/{sphynx,sphynx_big,pyramid,pyramid_small,statues,oasis}.schematic`, config `DungeonConfig/stronghold_desert.prop`.
- **Layout:** sphynx_big 15x15x15 (sandstone + stone, one diamond block 57, a few lava), statues 15x18x16 (sandstone statues, 10 lava), oasis 15x11x15 (water 40, sand 209, cactus 17, leaves 55), pyramid 15x9x15 and small 15x5x15 (sandstone, slabs).
- **Blocks:** sandstone 24, slab 44, lava 11, water 9, sand 12, cactus 81, iron bars 101, diamond block 57. **Tex:** VAN only.
- **Mood:** monumental entrances to a sand underworld.
- **Segment:** "guardian court": a short 15x15 open room with sandstone statues of anubis-like figures flanking the path and two lava channels in the floor (2 wide); the entrance to a deeper desert corridor. Lava channels double as gaps.

### 35. Lucky Blocks fort and temple
- **Source:** Lucky Blocks, `mod/lucky/util/CustomStructures`: `makeFort`, `makeTemple` (7x7x7 cube, sandstone and gold with a lucky block inside), also `LuckyGenerator`.
- **Layout:** a 7x7x7 hollow cube of sandstone 24 with a gold block 41 trim, stairs 128 up the outside and torches 50 at the corners; a lucky block at the centre, lit.
- **Blocks:** sandstone 24, gold block 41, sandstone stairs 128, torch 50. **Tex:** VAN only (the lucky block itself is in LuckyBlocks.jar).
- **Mood:** a golden treat in a trap-heavy mine.
- **Segment:** "gold cell": a 7x7x7 sandstone chamber off the corridor with a lucky-block pedestal (gold block cap) — the grave of the most lucky death; keeps the site's Lucky motif consistent.

---

## Stratum 6: The Hedge and the Labyrinth (Twilight Forest)

All TF art below lives in `TwilightForest-2.4.3.jar` (`assets/twilightforest/textures/blocks/`) and is of unverified licence. Each entry gives a VAN fallback.

### 36. Minotaur labyrinth corridors
- **Source:** Twilight Forest, `twilightforest/structures/minotaurmaze/` (`ComponentTFMazeCorridor`, `...CorridorIronFence`, `...CorridorRoots`, `...CorridorShrooms`, `ComponentTFMinotaurMaze`, `StructureTFMazeStones`).
- **Layout:** an underground maze on a grid of narrow cells (about 5 blocks a side, 3-4 high). Corridors are plain, some with an iron-bar fence 101 across, some overgrown with roots or mushrooms.
- **Blocks:** TF `mazestone` (meta variants: plain `mazestone_plain`, brick `mazestone_brick`, chiseled/decorative `mazestone_decorative`, cracked `mazestone_cracked`, mossy `mazestone_mossy`, mosaic, border, pillar), iron bars 101, TF roots (`rootblock`, `oreroots`). **Tex:** TF (`mazestone_*.png`, `rootblock.png`, `oreroots.png`). **VAN fallback:** stone brick 98 (plain, mossy, cracked, carved), cobble, and vine 106.
- **Features:** the pale grey mazestone brick with a faint green cast, roots through the ceiling, iron fences blocking branches.
- **Mobs:** Minotaur, Maze Slime.
- **Mood:** oppressive pale stone, a "something is hunting".
- **Segment:** "mazestone run": 3 wide x 3 high, tight, pale 98/98[2] with an iron-bar fence across a side passage every ~10 blocks (decoys), roots hanging from the ceiling. Alcoves in the dead-end niches. Light: very sparse (wall torches only at junctions).

### 37. Labyrinth rooms: Vault, Fountain, Spawner Chests, Collapse
- **Source:** Twilight Forest, `ComponentTFMazeRoomVault` (15x15), `...RoomFountain`, `...RoomSpawnerChests` (11x11 with a Minotaur spawner), `...RoomCollapse` (14x14, ceiling fallen in: dirt, gravel, plants), `...MazeRoom`, `...MazeMushRoom`.
- **Layout:** the Vault is a 15x15 chamber with sand, TNT 46, pressure plate 70, chests 54: a treasure room with a TNT trap and the lure of a chest on a platform; the Fountain room has a water or lava basin; Spawner Chests has a spawner flanked by chests with iron bars and planks frames; Collapse is a rubble-filled square with gravel 13, dirt 3, grass 2 and ferns.
- **Blocks:** mazestone, sand 12, TNT 46, spawner 52, chests 54, iron bars 101, planks 5, gravel 13. **Tex:** TF (`mazestone_*`); VAN fallback as above.
- **Mobs:** Minotaur, Maze Slime.
- **Mood:** the "treasure room" and "collapsed ceiling" are great surprises.
- **Segment:** "vault crossing": a 15x15 room the path crosses diagonally, a chest dais in the middle (sand beneath and a visible TNT block under glass-like bars) and a collapsed corner of rubble. 15 long.

### 38. Labyrinth dead ends: torches, painting, trapped chest, lava fountain, roots
- **Source:** Twilight Forest, `ComponentTFMazeDeadEnd*` (Chest, TrappedChest, Fountain, FountainLava, Painting, Roots, Shrooms, Torches), `ComponentTFMazeEntranceShaft`, `ComponentTFMazeUpperEntrance`.
- **Layout:** each dead end is a cell terminating in a small dressing: a chest, a trapped chest 146, a water or lava fountain 8/10, a painting 321 item frame, a ring of torches.
- **Blocks:** chest 54 / trapped chest 146, lava 10/11, water 8/9, torch 50, painting (entity). **Tex:** VAN only for the dressing.
- **Mood:** a quiet "cul-de-sac" gift; the lava fountain is the dangerous one.
- **Segment:** "dead-end niche": every alcove is a grave alcove but one in six gets a dressing from this list. A "lava fountain" alcove is a 1x2 recess with lava 11 spilling down; a "painting" alcove has a framed painting above the grave (a memorial). Strong for variation without new geometry.

### 39. Twilight Forest hollow hill
- **Source:** Twilight Forest, `ComponentTFHollowHill` (three sizes; the class constants 64/128/256/512 give sizes), `ComponentTFHillMaze` (mazestone maze inside the hill).
- **Layout:** a grassy mound over a cavern with cobble 4 / stone 1 walls and spawners 52 (Redcap, Cave Spider, Creeper, Silverfish, Fire-beetle-ish "Pinch beetle"); the biggest hills hide a mazestone maze (`ComponentTFHillMaze`, 19 high by 27 wide).
- **Blocks:** stone 1, cobble 4, grass 2, dirt 3, spawner 52, mazestone, firefly lamps `fireflyjar_*`. **Tex:** TF only for jars; VAN fallback: glowstone 89.
- **Mood:** lush above, bleak and many-mobbed below.
- **Segment:** "hill burrow": a cave-like corridor (irregular; ceiling dips, stone/cobble mix, ladders of gravel) with 2-3 spawner stubs and a lantern-jar light (glowstone 89 in a glass 20 cage as a firefly jar fallback).

### 40. Twilight Forest hedge maze
- **Source:** Twilight Forest, `ComponentTFHedgeMaze` (50x50ish footprint, 3 high, Hedge Spider, Swarm spider, Hostile Wolf).
- **Layout:** a labyrinth of dense hedge walls (leaves) 3 tall, on grass; a central chamber with chest; fireflies in jars hang in lamps.
- **Blocks:** TF `hedge` (looks like thick leaves), leaves 18 (fallback), grass 2, firefly jars. **Tex:** TF `hedge.png`, `fireflyjar_*`; VAN fallback leaves 18 (opaque) and glowstone.
- **Mobs:** Hedge Spider, Swarm Spider, Hostile Wolf.
- **Mood:** fairy-tale menace, summery.
- **Segment:** "hedgerow": surface-feeling segment: leafy walls 3 high with sky above (a dim twilight ceiling, a few stars), grass floor, firefly jars glow along the hedge. Marks a gentle tonal break; alcoves are leafy bowers.

### 41. Twilight Forest Naga courtyard
- **Source:** Twilight Forest, `ComponentTFNagaCourtyard` (about 23 wide, 7 high walls with a boss spawner), `StructureTFNagaStones`, TF `nagastone` blocks (a family of 20+ rotating segments).
- **Layout:** a square courtyard enclosed by cobble walls 139 and stone slab 44 columns, an inner ring of stone slab and pillars, a serpent-themed floor (nagastone) arranged in a looping serpent pattern, the boss spawner at the centre.
- **Blocks:** TF `nagastone_*` (face, long side, tip, turns), cobble wall 139, stone slabs 44, stone brick, grass 2, firefly. **Tex:** TF (`nagastone_*.png` set of 20); VAN fallback: stone brick 98[3] carved with a snaking line of mossy 98[1].
- **Mobs:** Naga.
- **Mood:** ritual, serpent worship.
- **Segment:** "serpent court": a 23x23 courtyard crossed by a path that follows the serpent's coils (the floor is stone with a 1-wide snake of mossy brick), pillars (slab pillars) in a ring, a basin or brazier at the centre.

### 42. Twilight Forest troll cave and hydra lair
- **Source:** Twilight Forest, `trollcave/` (`ComponentTFTrollCaveMain`, `TrollCaveConnect`, `TrollCaveGarden`, `TrollVault` with 11x11 giant obsidian chest, `CloudCastle`), `ComponentTFHydraLair` (64x27x27 with a boss spawner).
- **Layout:** the troll cave: a large cave of stone and obsidian 49 (about 30 x 20 wide), troll root 'trollRoot', luminous `trollsteinn` stone and `uberousSoil`; the vault: a sealed room with a giant-obsidian block and chests; hydra: an open arena in stone.
- **Blocks:** stone 1, obsidian 49, TF `trollsteinn` / `trollsteinn_light`, `uberous_soil`, troll root. **Tex:** TF; VAN fallback: obsidian + glowstone 89 for the 'light' stone.
- **Mobs:** Troll, Hydra (boss).
- **Mood:** huge, primal, cave-troll cosy.
- **Segment:** "troll hollow": an irregular 8-wide cave with lumpy stone walls and glowing light-stone clusters (glowstone fallback) on the ceiling; the path wanders; a vault door (obsidian) in the side.

---

## Stratum 7: The Knight stronghold and the towers (Twilight Forest)

### 43. Knight stronghold hallways and turns
- **Source:** Twilight Forest, `structures/stronghold/` (`StrongholdSmallHallway`, `LeftTurn`, `RightTurn`, `Crossing`, `DeadEnd`, `UpperCorridor`, `UpperTIntersection`, `SmallStairs`, `UpperAscender`, `Entrance`, `AccessChamber`).
- **Layout:** a deep underground fortress of rooms about 18x?x18 each, joined by small hallways about 5 wide, 3-4 high; turns and crossings; the upper level has a lower ceiling.
- **Blocks:** TF `knightbrick` (and `knightbrick_cracked`, `_mossy`, `_floor`), `knightmetal_block`, iron bars 101, doors; `shield_inside` / `shield_outside` motifs on the walls. **Tex:** TF; VAN fallback: stone brick 98[3] and 98[2], iron block 42.
- **Mobs:** Skeleton knights ('Knight Phantom' in the boss room), Zombie, Skeleton.
- **Mood:** military, grim, cold iron.
- **Segment:** "knight hall": 5 wide, 4 high, regular stone-brick bays with an iron-block (42) shield plaque on each pilaster; alcoves between plaques; torches in iron brackets (torch 50 on 42). Colder blue-white light than the other strata; the light warms with depth.

### 44. Stronghold Atrium, Balcony, Training Room
- **Source:** Twilight Forest, `StrongholdAtrium` (17x?x17 with a central grass plot), `BalconyRoom`, `TrainingRoom` (planks 5, cobble 4, sand 12, water, a hay target?), `UpperAscender`.
- **Layout:** the atrium: a central courtyard open over several storeys with grass 2 in the middle, balcony walkways around; the training room: a 15x15 hall with sand pits and wooden dummies.
- **Blocks:** stone brick, grass 2, planks 5, cobble 4, sand 12, iron bars 101, cauldron 118 / anvil 145 (fallback fittings), water. **Tex:** VAN only (TF's own carved stone is optional).
- **Mood:** vertical grandeur in an underground fortress.
- **Segment:** "atrium drop": the path runs on a balcony ledge around a 9x9 open well (view of storeys below with grass and a lantern at the bottom); iron-rail fences; optional ladder down. A **vertical-feeling** relief; 14-20 blocks.

### 45. Stronghold Foundry and Treasure rooms
- **Source:** Twilight Forest, `StrongholdFoundry` (25 high: stone, gold block 41, iron ore 15, lava 10, redstone lamp, netherrack), `StrongholdTreasureRoom` (iron-bar cages), `StrongholdTreasureCorridor`.
- **Layout:** the foundry is a tall industrial room with lava forge channels, gold and iron blocks, and a netherrack-fed fire; the treasure room is a cage of iron bars around chests, with a hidden approach.
- **Blocks:** stone 1, lava 10/11, gold ore 14, iron ore 15, netherrack 87, fire 51, redstone lamp 123, iron bars 101, chests 54. **Tex:** VAN only.
- **Mobs:** Skeleton, Blaze (rare).
- **Mood:** forge-hall, orange underglow, in contrast with the cold stone.
- **Segment:** "forge gallery": a 20-long hall with a lava channel (2 wide) along one wall, walkway with iron railing, ore blocks piled in niches, orange light rising from below. Warms the palette suddenly: use as a stratum high point.

### 46. Stronghold boss room and knight shield room
- **Source:** Twilight Forest, `StrongholdBossRoom` (about 27x27, bossSpawner, stone slab 44, obsidian 49, iron bars, torches), `StructureTFStrongholdShield`, `StructureTFKnightStones`.
- **Layout:** an arena with a ring of slab seating, a central obsidian dais with the boss spawner, and iron bars closing the doors behind you.
- **Blocks:** obsidian 49, stone slab 44, iron bars 101, torch 50, spawner 52. **Tex:** VAN only.
- **Mobs:** Knight Phantoms.
- **Mood:** climax, the final test before a new band.
- **Segment:** "arena": the path enters a 27x27 round-ish room with a ring of slab benches, a dais with a spawner cage, torches at 8 compass points; doors close behind you (the corridor bars slam). Use as the last segment of a stratum (band boundary marker).

### 47. Twilight Lich tower
- **Source:** Twilight Forest, `structures/lichtower/` (`ComponentTFTowerMain`, `TowerWing`, `TowerBridge`, `TowerBeard`, `TowerRoof*`, `TowerOutbuilding`), `TFLichTowerPieces`.
- **Layout:** a tall cobble-and-planks tower (main shaft roughly 15 wide, up to ~55 tall) with spiral stairs, glass windows 20, iron bars, wings, bridges to outbuildings and pointy or slab roofs; the top room holds the Lich boss spawner; floors have zombie/skeleton/swarm spawners.
- **Blocks:** cobble 4, planks 5, glass 20, iron bars 101, stairs 53, torch 50, spawner 52. **Tex:** VAN only (mod art optional).
- **Mobs:** Skeleton, Zombie, Swarm spider, Lich (boss).
- **Mood:** wizard tower, drafty, high.
- **Segment:** "stair tower": a spiralling segment: the path turns 90 degrees every 5 blocks as a stairway round a 5x5 core, with glass windows showing an artificial dim sky; the shaft rises 10+ blocks. 25-40 long in path length. Provides **vertical travel**.

### 48. Twilight Dark Tower
- **Source:** Twilight Forest, `structures/darktower/` (`ComponentTFDarkTowerMain`, `Wing`, `Bridge`, `Balcony`, `Beard`, `Entrance`, `BossTrap`, `Roof*`), TF `towerDevice`, `towerWood`, `towerTranslucent` blocks.
- **Layout:** a black-and-wood skyscraper (main about 19 x 56 floors) full of trap devices: ghast traps, fire jets, vanishing and reappearing blocks, locked doors needing a tower key, builder blocks; rooms of cactus, ring and antenna roofs; blaze spawners (mini blazes) and boss trap.
- **Blocks:** TF `towerwood_*` (planks, cracked, mossy, infested, alt, encased), `towerdev_*` (antibuilder, builder, firejet, ghasttrap, lock, reactor, reappearing, smoker, vanish), `towerdev_lock_*`. **Tex:** TF; VAN fallback: dark oak-ish planks 5[5]/log 17[1] and red stone-lamps (123).
- **Mobs:** Tower Golem, Tower Ghast, Tower Termite, Tower Broodling, mini Ghast.
- **Mood:** menacing technological: the tower of traps.
- **Segment:** "trap corridor": a gantry corridor with periodic fire-jet vents in the walls (lava-orange glow as fire 51), a vanishing-floor tile (a section of floor that blinks out for 1 second then returns: a **gap**), lock doors. Heavy on scare-hook potential.

### 49. Twilight Ice tower and Yeti cave
- **Source:** Twilight Forest, `structures/icetower/` (`ComponentTFIceTowerMain` about 11x31+ footprint, `Wing`, `Entrance`, `Stairs`, `Bridge`, `BossWing`, `StructureTFAuroraBricks`), `ComponentTFYetiCave` (ice 79, packed ice 174, snow).
- **Layout:** a spiralling tower of aurora brick (a block that cycles through colours) and ice with crystalline rooms; the Yeti cave is a stone and snow cavern 20 wide with ice pillars.
- **Blocks:** TF `aurorabrick0..7` (animated, hue shift), `aurora_pillar_*`, `aurora_slab_side`; ice 79, packed ice 174, snow 80, snow layer 78. **Tex:** TF (aurora set, with `.mcmeta` animations); VAN fallback: packed ice + ice + quartz 155.
- **Mobs:** Ice Crystal, Ice Exploder, Ice Shooter, Yeti, Snow Queen (boss).
- **Mood:** cold beauty, aurora colours, the one colourful tower.
- **Segment:** "aurora gallery": ice floor (slippery look), aurora-brick walls slowly pulsing between blue, green, violet (animated tint in the Krypt's palette), crystal clusters in alcoves. The strongest "colour moment" outside the End.

---

## Stratum 8: Halls of Chocolate Quest

All CQ rooms/castles use vanilla blocks; the files are in `chocolateQuest-1.7.10-1.1d.jar` (licence unverified, but no CQ texture is needed). The 15x10x15 stronghold rooms are the workable unit, since a 15-block-long room is a segment.

### 50. CQ stronghold trap rooms (lava, redstone, pressure plates, silverfish)
- **Source:** Chocolate Quest, `stronghold/rooms/room{0,2,3,4,5,8,9,10,12,13,14,15,16}.schematic` (15x10x15). Examples: room0 (1152 stone brick, 13 lava, 3 silverfish blocks, 1 TNT), room3 (813 brick, iron bars, 6 lava, a spawner), room12 (145 lava, spawner, web), room13 (1747 stone brick, 29 redstone dust, 6 levers: a redstone door puzzle), room14 (plates 70, buttons, spawner), room16 (pistons 33, redstone, spawner, silverfish), room15 (9 end portal frames 120 + lava: an end-portal shrine).
- **Layout:** each room is a 15x15 floor, 10 high, with a doorway in each wall; contents differ: a lava moat room (room12), a lever-door puzzle (13), a pressure-plate trap with a spawner (14), a piston door (16), a portal-frame shrine (15).
- **Blocks:** stone brick 98, lava 10/11, iron bars 101, redstone 55, lever 69, plate 70, piston 33, TNT 46, endframe 120. **Tex:** VAN only.
- **Mobs:** Skeleton (CQ default: the theme `mob = default`), Silverfish.
- **Mood:** puzzle-box strongholds.
- **Segment:** "puzzle chamber": a 15-long room whose floor is a 3-wide stone bridge across a lava moat (room12), or with a visible piston wall and lever alcove that "opens" the next hall (room13/16). 

### 51. CQ stronghold stairs and entrance towers
- **Source:** Chocolate Quest, `stronghold/stairs/stairs0..3.schematic` (15x20x15: stone brick with iron bars and slabs), `stronghold/entrance/{tower,tower2,tower3,tower4,towerXiraxis,skull,suspicious_trees}.schematic` (15x20x15; towerXiraxis 15x27x15 with vines, torches and sandstone), `stronghold/entrance_stairs/entranceStairs.schematic`.
- **Layout:** the stairs are 15x20x15 spirals/switchbacks (20 high); the towers are stone-brick lookouts with planks, ladders 65, torches; "skull" is a giant skull mound (stone); "suspicious trees" is a grove with silverfish nests.
- **Blocks:** stone brick 98, stairs 109, slab 44, iron bars 101, planks 5, ladder 65, torch 50, vine 106. **Tex:** VAN only.
- **Mood:** a descent: "the way down".
- **Segment:** "switchback stair": a 15-wide, 20-step stair with iron-bar railings; each landing a short alcove row. The best transition piece between rooms at different depths.

### 52. CQ Cathedral and Redstone castle (snow castles)
- **Source:** Chocolate Quest, `snowCastles/Cathedral.schematic` (70x50x70: 16969 stone brick, 1702 stained clay, 1458 stairs, 91 torches), `Redstone_castle.schematic` (70x60x69: redstone 733, wool 449, cauldrons 13, enchantment table), `CubeCastle.schematic` (69x60x70: iron bars 3757, stained clay 5240, redstone lamps 158), `MountainCastle.schematic` (70x85x70, 148 torches, 21 chests, quartz).
- **Layout:** huge multi-storey castle interiors: the Cathedral has a nave of stone-brick vaults with coloured stained clay windows and rows of torches; the Redstone castle is a lit-circuit fortress (redstone wiring in walls); CubeCastle a cubic fortress with iron-bar grilles and lamp-lit halls.
- **Blocks:** stone brick 98, stained clay 159 (window colours), stairs 109, torches 50, redstone lamp 123, wool 35. **Tex:** VAN only.
- **Mobs:** Skeleton, Zombie, Witch (cauldron/brewing stand details).
- **Mood:** cathedral: ceremonial and bright; the best "grand hall" candidate.
- **Segment:** "nave": 9 wide, 9 high vaulted hall of stone brick with two rows of pillars, stained-clay "windows" (159 coloured panes) on both sides, ~91 torches' worth of candlelight: dozens of small lights, the brightest segment of the shallow bands. Grave alcoves in the side aisles behind pillars. 24-40 long.

### 53. CQ wizard, alchemist and lake castles
- **Source:** Chocolate Quest, `castles/wizCastle.kanokarob.schematic` (50x46x50: cobble 7416, mossy cobble 2871, 8 spawners, vines 399, 18 torches), `AlchemistCastle.schematic` (50x45x50: 12 cauldrons 118, 9 brewing stands 117, 45 glowstone, 863 water), `LakeCastle.schematic` (49x40x50: water 1812, 4 spawners, 12 torches), `Ravine_castle.schematic`, `castles/BigTree.schematic` (50x55x50: leaves, vines, water, enchantment tables).
- **Layout:** castles set on cliffs, in lakes or in giant trees; interiors with brewing rooms and mage studies.
- **Blocks:** cobble 4, mossy cobble 48, stone brick 98, cauldron 118, brewing stand 117, enchantment table 116, vine 106, water 8, glowstone 89, wool 35. **Tex:** VAN only.
- **Mood:** wizard-alchemist storybook.
- **Segment:** "alchemist hall": a stone-brick hall with cauldrons (118) in the alcoves (some filled with water meta 3: the grave "basin"), brewing stands on shelves, green glowstone lamps, drips. A shift from sepulchral to arcane.

### 54. CQ Castle End and Netherlike castle
- **Source:** Chocolate Quest, `castles/CastleEnd.schematic` (49x48x50: stone 20250, stone brick 13729, web 223, lava 30, 5 chests, skulls), `neaEkkleasia.xiraxis.schematic` (50x50x50: sandstone 6211, double slab 3157, end stone 1642, wool 1062, 75 torches, 24 glowstone).
- **Layout:** Castle End: a stone fortress with webbed ruins and lava; Ekklesia: a sandstone and end-stone cathedral complex.
- **Blocks:** stone 1, stone brick 98, web 30, lava 11, sandstone 24, end stone 121, double slab 43, wool 35, torch 50, glowstone 89. **Tex:** VAN only.
- **Mood:** apocalyptic keep; webs on everything.
- **Segment:** "ruined keep": a stone and web hall with partial collapsed ceiling (sky-dark), lava seams in the floor cracks, columns snapped half-way. 20-30 long.

### 55. CQ ships (skeleton ship, galleon, creeper ship, corrupted ship)
- **Source:** Chocolate Quest, `ships/{SkeleShip,Galleon,GalleonCannons,smallGalleon,smallPirateShip,RedFlagShip,creeperShip,corruptedShip,OceanWievShip,PirateIsland}.schematic` (small ones 15x20x15; Galleon 32x42x50, GalleonCannons 50x40x31 with 191 TNT; PirateIsland 54x55x60).
- **Layout:** wooden hulls: planks 5 and log 17 hulls, wool 35 sails, fence 85 rigging, stairs 53 decks, cauldron 118 galley; cannons are TNT behind obsidian 49 and glass panes 102; ghost/corrupted ship uses nether brick 112 and soul sand 88.
- **Blocks:** planks 5, log 17, wool 35 (sails), fence 85, ladder 65, ironbars, cauldron, TNT, obsidian. **Tex:** VAN only.
- **Mobs:** Pirates (CQ mob), Skeleton (SkeleShip).
- **Mood:** shipwreck and mutiny; a break from stone.
- **Segment:** "wreck hold": a below-decks corridor of planks and log ribs, wool-sail scraps hung, cannon ports (obsidian/TNT) along one side, lantern glows (torch 50 + fence posts). Floor of wet planks with a water seep (gap of water). 15-30 long.

### 56. CQ village, arena, market and inn
- **Source:** Chocolate Quest, `village/{Arena,Inn,Market,InquisitionVilla,OrcVillage,WitchVilla}.schematic` (32x20x32 plots), `snowCastles/WolfVillage.schematic`.
- **Layout:** 32x32 footprints: the arena is a sandstone ring with 468 glowstone lights 89 and fences; the market has wool 35 awnings, anvils 145, stone and cobble; the inn has planks and 56 torches.
- **Blocks:** sandstone 24, glowstone 89, stained glass 95, planks 5, cobble 4, wool 35, anvil 145, fence 85. **Tex:** VAN only.
- **Mood:** festival at the bottom of a grave: ironic, crowded, warm.
- **Segment:** "market gallery": a wide (7-9) hall with stall alcoves (wool awnings 35 over each grave nook), glowstone lamps hung on fences, anvils and barrels as dressing. The warmest, busiest kind in the catalogue; use to break up long dark runs.

---

## Stratum 9: Arcane halls and witch lairs

### 57. Roguelike Library and Lab
- **Source:** Roguelike Dungeons, `rooms/DungeonLibrary`, `rooms/DungeonLab`, `segment/part/SegmentBooks`, `SegmentShelf`.
- **Layout:** the library: shelves 47 up the walls, carpet 171 (green) aisle, oak stairs 53 as reading benches, redstone lamps 124 lit by hidden redstone blocks 152, podzol/ferns as potted decor, oak doors 64 and trapdoors 96; the lab: farmland 60 with carrots, melons, pumpkins and nether wart 115 beds, water, soul sand 88, cyan-stained clay, redstone lamps, an alchemist's study.
- **Blocks:** bookshelf 47, carpet 171[13], oak stairs 53, redstone lamp 123/124 (lit by a block of redstone 152 buried under the floor), trapdoor 96, farmland 60, nether wart 115, soul sand 88, stained clay 159[9]. **Tex:** VAN only.
- **Mood:** cosy scholarly (library), mad-scientist (lab).
- **Segment:** "reading room": 5 wide, a green carpet runner, shelf-lined walls with graves between shelves, lamps at each bay (the hidden-redstone trick makes lamps glow without visible wiring). A warm yellow-white interior; 12-20 long.

### 58. Roguelike Smithy and Mess hall
- **Source:** Roguelike Dungeons, `rooms/DungeonsSmithy`, `rooms/DungeonMess`.
- **Layout:** smithy: brick 45 forge walls with fire 51 over netherrack 87 behind iron bars 101, an anvil 145 (new and damaged), lava 11 and water 8 quenching pools, redstone lamps; mess: crafting table, fires, a glowstone chandelier, iron bars, a food chest.
- **Blocks:** brick 45, brick stairs 108, slab 44, anvil 145, fire 51, netherrack 87, lava 11, water 8, iron bars 101, redstone lamp 124, glowstone 89. **Tex:** VAN only.
- **Mood:** hearth, workman's heat, orange-lit.
- **Segment:** "forge nook": a hall with brick-and-iron-bar forge alcoves (fire inside: a flickering orange glow), an anvil on a fence pedestal, a quench trough (water with a stone lip), warm light. Contrasts with every cold stratum.

### 59. Roguelike Enchant, Music, Reward and Firework rooms
- **Source:** Roguelike Dungeons, `rooms/DungeonsEnchant` (enchantment tables 116 ringed with purple stained clay 159[10] and glowstone), `DungeonsMusic` (jukebox 84 on carpet with a record chest), `DungeonReward` (glowstone-ringed chest), `DungeonFirework`, `DungeonBTeam`, `DungeonAvidya`, `DungeonEniko`, `DungeonEtho`, `DungeonTreetho` (author-gift rooms).
- **Layout:** small themed chambers with a single centrepiece (tables, jukebox, chest, firework launchers).
- **Blocks:** enchantment table 116, glowstone 89, jukebox 84, carpet 171, note block 25, redstone lamp, stained clay. **Tex:** VAN only.
- **Mood:** reward, a pause.
- **Segment:** "shrine alcove": a single 5x5 room beside the path with a centrepiece on a 3x3 dais ringed in glowstone; a jukebox variant can play the stratum's ambience from a block. Used rarely (1 per ~40 graves).

### 60. Witchery coven, shack and goblin hut
- **Source:** Witchery, `worldgen/ComponentCoven`, `ComponentShack`, `ComponentGoblinHut`, `ComponentVillageWitchHut`, `WitcheryComponent`, `WorldHandlerCoven`.
- **Layout:** a swamp shack on stilts of logs 17 with planks 5 and spruce stairs 134, a cauldron 118 inside, a chest, bed 26, crafting table 58; the coven: a ring of sand and cobble, web 30 and water, with witches; the goblin hut: log-and-plank cottage with a cauldron and stone slab roof.
- **Blocks:** log 17, planks 5, cobble 4, sand 12, dirt 3, grass 2, cauldron 118, web 30, wooden door 64, fence 85, torch 50, bed 26. **Tex:** VAN only for the structure; Witchery props (altar, circle glyphs, wicker block) are WIT-only.
- **Mobs:** Witch, Goblin, Familiar.
- **Mood:** swamp witch folk-horror.
- **Segment:** "witch's stilt-hall": a plank walkway on log stilts over a swamp (water beneath), a lantern (torch 50) on a fence post every 5, a cauldron in the largest alcove; webs in corners.

### 61. Witchery Wicker Man and Altar circles
- **Source:** Witchery, `worldgen/ComponentWickerMan`, `WorldHandlerWickerMan`, `blocks/BlockCircle`, textures `wicker_block_plain_side.png`, `wicker_block_bloodied_side.png`, `circleglyph1.1..3.12.png`, `altar.png`, `coffin.png`.
- **Layout:** a giant wicker figure on a dirt-and-sand plot (zombies near it); circles are floor glyph rings (chalk/gold/infernal) used in rituals; the altar is a 3-block structure.
- **Blocks:** WIT wicker block, glyph circle (WIT), hay 170 (fallback for wicker), netherrack 87, fire 51 (burn the man). **Tex:** WIT (all glyph/wicker textures); VAN fallback: hay bale 170 + nether brick.
- **Mobs:** Zombie, Witch, Imp, Demon (the circles summon).
- **Mood:** pagan, ritual horror.
- **Segment:** "ritual circle": a 7x7 floor glyph ring (flat, drawn with 1px glyph textures; the VAN fallback is a ring of redstone-dust-like red marks) in the centre of a round chamber; a bone-white altar and 4 candle torches. The player walks the rim; a scare on the circle. WIT-only variant needs the owner's yes.

### 62. Witchery village keep, watchtower, apothecary
- **Source:** Witchery, `worldgen/ComponentVillageKeep`, `ComponentVillageWatchTower`, `ComponentVillageApothecary`, `ComponentVillageBookShop`, `WorldHandlerVillageDistrict`.
- **Layout:** a village walled district: a keep with stone and wood, guards and chest; watchtower; an apothecary shop with brewing stands 117 and cauldron 118; bookshop shelves 47.
- **Blocks:** planks 5, cobble 4, iron bars 101, ladder 65, torch 50, brewing stand 117, bookshelf 47, cauldron 118. **Tex:** VAN only.
- **Mobs:** Village Guard, villagers.
- **Mood:** civic order, lived-in.
- **Segment:** "apothecary row": a wooden-beamed corridor with shelves, bottles (brewing stands) and herb bundles (flowers hung from fences) in the grave alcoves, hanging lanterns; reads as "a shop beneath the graves".

### 63. Witchery Torment, Mirror and Dream worlds (maze dimension)
- **Source:** Witchery, `dimension/WorldProviderTorment`, `WorldProviderMirror`, `WorldProviderDreamWorld`, `GenerateMaze`.
- **Layout:** the Torment dimension is a dark maze of stone-like hostile corridors with a ceiling and heavy mist; the Mirror dimension duplicates a pocket; the Dream world floats islands in a void. All three are generated by code with a maze generator (`GenerateMaze`).
- **Blocks:** stone/grass in the Dream world; Torment uses a custom dark stone and "spirit" fog; flowspirit (a fluid) texture `flowspirit_still.png`. **Tex:** WIT (`flowspirit_*`, `dreamCatcher.png`, `mirror.png`); VAN fallback: obsidian 49 and soul sand 88.
- **Mobs:** spirit mobs; Dream mobs (nightmare, spectre).
- **Mood:** nightmare and spirit-world surreal.
- **Segment:** "spirit passage": a dark corridor of obsidian-black walls with a thin white mist at knee height, glowing spirit-water channels along the floor; alcoves look like dream-catchers (a hoop of fence blocks). Use for a one-off eerie interlude (a "dream" segment).

### 64. SecretRooms hidden doors and one-way glass
- **Source:** SecretRooms mod, `blocks/BlockCamoDoor`, `BlockCamoGate`, `BlockCamoStair`, `BlockCamoPlate`, `BlockCamoLever`, `BlockOneWay`, `BlockCamoGhost`, `BlockSolidAir`, `BlockTorchLever`, `BlockCamoChest`; textures `CamoBase.png`, `CamoGate.png`, `CamoPlateIron.png`, `clear.png`, `SolidAir.png`, `TorchLever.png`.
- **Layout:** blocks that copy the block they are embedded in: a hidden door set into a wall looks like stone brick until a (camouflaged) lever or plate opens it; ghost blocks let you walk through; one-way glass; torch levers that switch when clicked.
- **Blocks:** camo blocks mimic neighbours; for the Krypt, use stone brick 98 or the local wall for a "sealed alcove".
- **Tex:** SR (the camo base textures) but the visual result is the neighbour's texture, so none is needed in the Krypt: VAN only.
- **Mood:** a hidden room, secret grave.
- **Segment:** "false wall alcove": 1 in 8 alcoves is hidden behind a wall that looks continuous; clicking a torch-lever lights up the stone; revealed: a larger family vault with a grave of someone special (e.g. the 100th death). Good for milestone graves.

---

## Stratum 10: The Nether

### 65. Vanilla Nether fortress
- **Source:** vanilla 1.7.10, `StructureNetherBridgePieces` (Straight, Crossing, Corridor with nether wart room, Stairs, Throne room with blaze spawner, Entrance).
- **Layout:** a raised network of nether brick bridges 5 wide, 5 high with open sides and nether brick fence 113 railings, corridors enclosed 5x4, a wart staircase room (soul sand 88 + nether wart 115 in a lava-fronted well), a blaze throne room with a spawner on a dais, openings over lava seas.
- **Blocks:** nether brick 112, nether brick fence 113, nether brick stairs 114, soul sand 88, nether wart 115, spawner 52, chest 54, lava 10/11. **Tex:** VAN only (`nether_brick`, `soul_sand`, `netherrack`, `lava_still`).
- **Mobs:** Blaze, Wither Skeleton, Zombie Pigman, Magma Cube.
- **Mood:** hot, red, towering. The iconic one.
- **Segment:** "fortress bridge": the path is a 5-wide nether-brick bridge with fence rails, open to a lava sea below on both sides (no side walls, only the ceiling-less cavern dark red), pillars supporting; alcoves are impossible without walls, so put graves as niches in short wall stubs (every 8 blocks a gatehouse wall with alcoves). A crossing with a wart-room well is the climax. Provides the **lava gap** naturally (a missing bridge slab).

### 66. Doomlike nether halls
- **Source:** Doomlike Dungeons, `res/themes/nether.cfg`.
- **Layout:** Y 32-64; `buildFoundation true`, `outside` big (15-25% of the dungeon is open air), Blaze/Magma Cube/Zombie commons; boss mob WitherBoss in the largest room; no degeneracy.
- **Blocks:** nether brick 112 everywhere (walls, floor, ceiling), nether brick fence 113, pillars of nether brick, obsidian 49 and quartz 155; lava as liquid. **Tex:** VAN only.
- **Mobs:** Blaze, Magma Cube, Zombie Pigman, Skeleton (Wither), Wither (boss).
- **Mood:** a nether bunker.
- **Segment:** "brimstone hall": enclosed nether-brick hall 5-7 wide with pillars of obsidian every 5 blocks, a lava stream (1 wide) down the middle crossed by slab bridges, ember glow (fire 51 on netherrack 87 in brazier alcoves).

### 67. Roguelike Nether theme and fire/obsidian rooms
- **Source:** Roguelike Dungeons, `theme/ThemeNether`, `rooms/DungeonsNetherBrick`, `DungeonsNetherBrickFortress`, `DungeonObsidian`, `DungeonsFire`, `segment/part/SegmentNetherArch`, `SegmentNetherLava`, `SegmentNetherStripes`, `SegmentNetherWart`, `SegmentFireArch`, `SegmentFirePlace`.
- **Layout:** segments: an arch of nether-brick fence 113 over a lava channel; a stripe pattern of lava between slabs in the floor; a nether-wart bed in soul sand; a fireplace (fire 51 on netherrack 87 behind iron bars 101) in the wall; rooms: obsidian vault with lava moat and a spawner; fire room: a grid of netherrack brasiers.
- **Blocks:** nether brick 112, netherrack 87, soul sand 88, obsidian 49, quartz ore 153, redstone block 152, coal block (substitute coal ore 16 at 1.7.10), fire 51, lava 11, iron bars 101. **Tex:** VAN only.
- **Mobs:** Blaze, Magma Cube, Wither Skeleton.
- **Mood:** furnace-like.
- **Segment:** "brazier gallery": alcoves with iron-barred fireplaces (fire inside, glow outward), the floor striped with lava between slab bars so you step along a 1-wide path. High atmosphere for cheap blocks.

### 68. Chocolate Quest pigcity dungeon and lava temple
- **Source:** Chocolate Quest, `DungeonConfig/netherCity.prop` (`builder = lavaCity`, dimension -1, `floorBlock = nether_brick`, `lavaBlock = lava`, `posY = 31`, `rows = 4`), `pigcity/{dungeon,Temple,Temple1,Temple2,big_colisseum,fat_tower,Prison,mage_tower,portal_temple,ghast_nest,houses*,mansion1..5,Hotel,Pub,shop,plaza,track,gym,farm,Pig_farm,art_gallery,blacksmith,tree_plaza,colisseum}.schematic` (15x?x15 plots).
- **Layout:** a city of 15x15 plots on a nether-brick floor over a lava sea: dungeon (15x20x15: 2166 nether brick, 123 lava, redstone and repeaters 25, pistons 8 for a trap, 15 glowstone), Temple (15x13x15: 91 lava, 29 glowstone, 2 gold blocks), Prison (1227 nether brick, 84 fence, 28 glowstone, 8 web, 2 chests), fat tower, colosseum.
- **Blocks:** nether brick 112, nether brick stairs 114, fence 113, lava 11, glowstone 89, gold block 41, redstone 55, repeater 93, sticky piston 29, web 30. **Tex:** VAN only.
- **Mobs:** Zombie Pigman (`mob = pigzombie`).
- **Mood:** decadent infernal city; grand and absurd.
- **Segment:** "pigcity avenue": a 7-wide nether-brick street between façades of towered houses (stairs and fence trim), glowstone lampposts, lava canals either side; the prison variant has cells with fences and webs. 15 long (one plot).

### 69. Chocolate Quest portal temple, mage tower, ghast nest, water temple
- **Source:** Chocolate Quest, `pigcity/portal_temple.schematic` (15x11x15: 310 nether brick, 30 log 17, 24 glowstone, 12 obsidian, 2 gold, 2 lapis), `mage_tower.schematic` (15x15x15: 76 bookshelf, 39 glowstone, farmland 10 with wheat, 7 water, enchantment table), `ghast_nest.schematic` (15x19x15: 169 hay 170, 60 nether fence, 1 spawner), `temple_water.schematic` (15x13x15: 56 water, 4 lava, 4 glowstone, enchantment table).
- **Layout:** four small shrine-like buildings: a log-framed portal frame with obsidian, a tower of books and a farm, a hay-bale nest (ghast spawner), a watery temple in the middle of fire.
- **Blocks:** nether brick 112, log 17, obsidian 49, glowstone 89, bookshelf 47, hay bale 170, nether brick fence 113, water 9. **Tex:** VAN only.
- **Mood:** the weird shrine at the end of a hot street.
- **Segment:** "portal chapel": a 15-wide short chapel with an unlit obsidian frame (4x5, with a purple-black interior) on the end wall (graves flank it), a pair of lava braziers. Ties to the gap/jump (a portal at the end can be the lore link to the End).

### 70. Recurrent Complex blaze crystal, Unholy Monolith and Joker Tower
- **Source:** Recurrent Complex, `BlazeSpawnerCrystal.rcst` (7x8x7, Y 8-40: obsidian 49, nether brick, a Blaze spawner), `MonolythUnholy.rcst` (15x26x15: slabs, nether brick, obsidian, netherrack 87, fire 51, glowstone, stained glass, a spawner and droppers), `MonolythHoly.rcst` (quartz 155, glowstone), `JokerTower.rcst` (9x32x9 buried 18 deep: stone brick, nether brick, TNT 46, pressure plate, obsidian, a chest and bats).
- **Layout:** pillar-shrines: the unholy monolith is a 26-tall nether-brick spire topped with fire and a spawner, the holy one the quartz counterpart; the joker tower is a buried vertical shaft with a TNT trap.
- **Blocks:** obsidian 49, nether brick 112, netherrack 87, fire 51, glowstone 89, quartz 155, TNT 46, stained glass 95. **Tex:** VAN only.
- **Mobs:** Blaze, Zombie, Bat.
- **Mood:** monolith: sacred/profane duality.
- **Segment:** "dual spire": a hall crossing between a holy (white quartz, glowing) and an unholy (black nether brick, fiery) half; the left wall quartz, the right nether brick, with a seam down the middle. A direct fit for the Krypt's themes of death and judgment.

### 71. Doomlike volcanic halls
- **Source:** Doomlike Dungeons, `res/themes/volcanic.cfg` (type FIERY, MOUNTAIN, Y 10-25).
- **Layout:** the liquid ladder is 85% lava at the top end; floors include obsidian 49; walls stone, cobble, cracked brick.
- **Blocks:** cobble 4, stone 1, stone brick 98[2], obsidian 49, dirt, lava 10/11. **Tex:** VAN only.
- **Mobs:** Zombie, Skeleton, Spider (the default list).
- **Mood:** magma chambers: a cave on fire.
- **Segment:** "lava causeway": the path is an obsidian walkway, 3 wide, over a lava river whose banks have stone brick; the lava ceiling-glow lights everything orange; gaps occur at lava pools (the spec's lava gap). 14-24 long.

---

## Stratum 11: The End (Hardcore Ender Expansion)

All art here is in `HardcoreEnderExpansionMCv.jar` (`assets/hardcoreenderexpansion/textures/blocks/`), licence unverified; each entry has a VAN fallback (obsidian, end stone, quartz, purple stained clay).

### 72. HEE Obsidian tower
- **Source:** HEE, `world/structure/tower/ComponentTower`, `StructureTower`, `MapGenTower` (`obsidian_special`, `obsidian_special_glow`, `obsidian_stairs`, enderman heads, enhanced TNT, essence altar, enhanced brewing stand, custom spawner, death flower pots).
- **Layout:** a tall (~25) obsidian tower with chambers on several levels; Enderman spawners (`TowerEndermanSpawnerLogic`), a death-flower pot room, dispensers and furnaces, an altar.
- **Blocks:** HEE `obsidian_special`, `obsidian_special_glow`, `obsidian_smooth`, `obsidian_chiseled`, `obsidian_pillar`; end stone 121; skull 144. **Tex:** HEE (`obsidian_*.png`); VAN fallback: obsidian 49 + quartz 155 pillars.
- **Mobs:** Enderman, Endermite-like Louse.
- **Mood:** tall dark; the End's gothic.
- **Segment:** "obsidian stair": a 5-wide spiral up/down in a smooth obsidian shaft; glowing purple seams in the glow block; altars at landings.

### 73. HEE End temple and portal chamber
- **Source:** HEE, `world/feature/TempleGenerator`, `block/BlockTempleEndPortal`, `entity/block/EntityBlockTempleDragonEgg`, `item/ItemTempleCaller`, `mechanics/misc/TempleEvents`.
- **Layout:** a temple built around a special end portal with a dragon egg; temple events (waves).
- **Blocks:** HEE `temple_end_portal` (a portal with its own render), obsidian, end stone. **Tex:** HEE `obsidian_*`; VAN fallback: end portal frames 120 and black fog.
- **Mobs:** Enderman, Angry Enderman.
- **Mood:** sacred void.
- **Segment:** "portal sanctum": a round 15x15 chamber with a sunken portal ring (dark glow), egg on a pedestal, ring of obsidian pillars. The last chamber of the End stratum or a milestone grave room.

### 74. HEE Ravaged dungeon
- **Source:** HEE, `world/structure/island/biome/feature/forest/ravageddungeon/` (`DungeonLayer`, `DungeonElement`, `DungeonElementType`, `DungeonDir`, `RavagedDungeonGenerator`, `RavagedDungeonPlacer`, `RavagedDungeonLoot`), `StructureRavagedDungeon`.
- **Layout:** a multi-layer grid dungeon (a layer is a grid of elements: hallways, dead ends, embedded chests, encased cubicle chest, end room, louse spawners, ruin chests); walls of ravaged brick in five damage levels with glowing variants; ender goo pools, stardust ore.
- **Blocks:** HEE `ravaged_brick`, `_smooth`, `_cracked`, `_damaged_1..4`, `_glow`, ravaged brick fence/slab/stairs, `ender_goo`, `end_powder_ore`, death-flower pots. **Tex:** HEE (`ravaged_brick_*.png`); VAN fallback: stone brick 98[2] cracked + 98[1] mossy tinted purple, glowstone.
- **Mobs:** Louse (ravaged), Silverfish.
- **Mood:** ruined and sticky with purple goo.
- **Segment:** "ravaged corridor": 3-wide with damage progression (the first blocks smooth, later heavily cracked), glow seams, goo puddles (slime 165 or purple-tinted water), embedded chest alcoves = grave alcoves. Damage is a natural parameter: 0-4.

### 75. HEE Laboratory
- **Source:** HEE, `island/biome/feature/island/laboratory/` (`LaboratoryGenerator`, `LaboratoryPlan`, `LaboratoryElementType` NONE, HALL_X, HALL_Z, SMALL_ROOM, LARGE_ROOM; `LaboratoryContent` with `SmallRoom` and `LargeRoom`; `StructureLaboratory`).
- **Layout:** a plan-grid of halls (X and Z) and rooms of two sizes; laboratory floor, glass walls with outline, obsidian frames.
- **Blocks:** HEE `laboratory_floor`, `laboratory_glass`, `laboratory_glass_outline`, `laboratory_obsidian`, `laboratory_stairs`. **Tex:** HEE; VAN fallback: quartz 155 floor, glass 20, obsidian 49.
- **Mobs:** Infested Bat/Louse etc., scientists (Vampire bats).
- **Mood:** clinical sci-fi, sterile and wrong.
- **Segment:** "lab corridor": a white-quartz floor, glass-panelled walls with obsidian frame bars, cold white light strips (glowstone behind glass), alcoves as glass pods holding the graves. A strong stylistic break; 14-24 long.

### 76. HEE Silverfish dungeon, hidden cellar and burning-mountain puzzle
- **Source:** HEE, `island/biome/feature/forest/StructureSilverfishDungeon`, `island/biome/feature/island/StructureHiddenCellar` (persegrit blocks, normal/rare chests), `island/biome/feature/mountains/StructureDungeonPuzzle` (`BlockDungeonPuzzle`: chained, distributor spread/square, trigger, wall).
- **Layout:** the silverfish dungeon: spawner-cells in infested ground; the cellar: a small hidden vault under a hatch; the puzzle: a floor of coloured tiles you must light in the correct pattern (trigger, chained and distributor tiles) to open the way.
- **Blocks:** HEE `dungeon_puzzle_trigger_lit`, `_chained_lit`, `_distributor_spread_lit`, `_distributor_square_lit`, `_wall`, `_wall_rock`, `_disabled`, `persegrit`. **Tex:** HEE; VAN fallback: redstone lamps 123/124 as lit/unlit tiles.
- **Mood:** puzzle floor, a game.
- **Segment:** "light-tile floor": a 7x7 floor of redstone-lamp-like tiles (unlit/lit) that light as you walk (a function of the walker's step); the path is the lit tiles. Visually distinctive; a puzzle without a puzzle (scare hook: the tile you step on goes dark).

### 77. Vanilla stronghold portal room, Roguelike Ender room, RC corrupted Ender tree
- **Source:** vanilla 1.7.10 `StructureStrongholdPieces$PortalRoom` (11x8x16: end portal frames 120 in a ring of 12, lava pool 11, a silverfish spawner 52, stairs); Roguelike `rooms/DungeonsEnder`, `ThemeEnder`; RC `CorruptedEnderTree.rcst` (14x16x12: end stone, leaves, obsidian, log, an Enderman spawner).
- **Layout:** the portal room: a raised dais of 12 frames (eyes inserted randomly) over a lava pool, a spawner behind; the RL Ender room: obsidian + quartz + an Enderman spawner; the corrupted tree: a withered end-stone tree.
- **Blocks:** end portal frame 120, end stone 121, obsidian 49, lava 11, quartz 155, sandstone 24. **Tex:** VAN only.
- **Mobs:** Silverfish, Enderman.
- **Mood:** endgame threshold. The 12 frames and the portal glow are the iconic final image.
- **Segment:** "portal dais": a 11x16 room with a 12-frame ring (4x? dais) with lava on either side, steps up; the portal's black void at the centre (a flat quad). Use as the last segment before the End band, or as the ending of any milestone (every 1000th grave).

---

## Stratum 12: The Hollow Beyond (OreSpawn vaults, altars, Lucky traps)

OreSpawn's dungeons are single code-built rooms ("vaults") with a spawner and cage-style loot. Their gem and crystal textures are in `orespawn.zip` (`assets/orespawn/textures/blocks/`), already used on the site.

### 78. OreSpawn generic dungeon
- **Source:** OreSpawn, `danger/orespawn/GenericDungeon.class` (`makeDungeon`), `DungeonSpawnerBlock`, `ItemRandomDungeon`; mob table in the class (Alien, Alosaurus, Basilisk, Bee, Blaze, Boyfriend/Girlfriend, Brutalfly, Cloud, Crystal, Dungeon beast, Emperor, Ender, Frog, Ghost, Hercules, Kyuubi, Leonopteryx, Molenoid, Mantis and more).
- **Layout:** a closed chamber built from many mass-fill calls (the class uses room sizes around 15 wide, 6-10 high, with 35 and 25 as the larger spans), one monster spawner 52 behind bars with a "cage" of loot.
- **Blocks:** a vanilla block, picked per dungeon (class draws ~1400 setBlock calls); spawner 52; OreSpawn `dungeonspawner.png`. **Tex:** OS (`dungeonspawner.png`); VAN for the rest.
- **Mobs:** a random OreSpawn mob per room; this is the "boss-of-the-room" model.
- **Mood:** boss closet.
- **Segment:** "beast vault": a 15x7 chamber with a cage (iron bars) around a pedestal holding a creature silhouette (a model standing in a pen); the spawner glows. Parameter: creature silhouette picked from the pack's mob list.

### 79. OreSpawn Nightmare dungeon
- **Source:** OreSpawn, `danger/orespawn/NightmareDungeon.class` (`makeDungeon`, 25x? footprint); loot: amethyst armour/tools, experience gear, `CageEmpty` caged mobs; mob "Emperor Scorpion" and "Nightmare".
- **Layout:** a 25-block-wide room with a raised dais and a chest of amethyst (blocks `blockamethyst.png`, ore `oreamethyst.png`) and ultimate gear.
- **Blocks:** amethyst block, vanilla stone brick. **Tex:** OS (`blockamethyst.png`, `oreamethyst.png`).
- **Mobs:** Nightmare, Emperor Scorpion.
- **Mood:** the dreaded amethyst vault.
- **Segment:** "amethyst vault": a purple-lit chamber with violet crystal clusters in alcoves, a pedestal with a glowing amethyst block; 12-18 long.

### 80. OreSpawn Ruby bird dungeon
- **Source:** OreSpawn, `danger/orespawn/RubyBirdDungeon.class`; ruby blocks `blockruby.png`, ore `oreruby.png`.
- **Layout:** a 15x15 chamber with ruby block walls/loot; caged "Ruby Bird" in `CageEmpty`.
- **Blocks:** ruby block (OS), cobble, torches. **Tex:** OS (`blockruby.png`, `oreruby.png`).
- **Mood:** red jewel box.
- **Segment:** "ruby vault": a short 15-long room, red glints from ruby ore in the walls, a cage with a red bird silhouette. Pairs well with the Nether stratum as a gem break.

### 81. OreSpawn Basilisk maze
- **Source:** OreSpawn, `danger/orespawn/BasiliskMaze.class` (`buildBasiliskMaze`, `makeMaze`, `drawSide`, uses a random-walk maze on a 30-wide grid, 15 and 20 block spans), loot with ultimate gear, titanium and uranium ingots, caged girlfriend (`CagedGirlfriend`), Basilisk boss.
- **Layout:** a stone maze (30x30) built by depth-first search with a Basilisk in the centre.
- **Blocks:** stone, `extremetorch.png` (OS torch), `blocktitanium.png`, `blockuranium.png`. **Tex:** OS.
- **Mobs:** Basilisk.
- **Mood:** deadly serpent maze.
- **Segment:** "serpent maze": 3-wide stone passages with sharp turns (4 turns per 24 blocks), green torches, a stone "eyes" carving at each branch. 20-30 long.

### 82. OreSpawn Crystal maze
- **Source:** OreSpawn, `danger/orespawn/CrystalMaze.class` (`buildCrystalMaze`, `makeMaze`, `openCrystalMaze`; spans of 16/32/64/128), blocks `crystalstone.png`, `crystalplanks.png`, `crystalgrass_*`, `crystaltorch.png`, trees `crystaltreelog.png`.
- **Layout:** a maze carved in crystal stone (a luminous translucent stone), opening to a crystal garden with crystal trees.
- **Blocks:** OS `crystalstone`, `crystalplanks`, `crystaltorch`, `crystalgrass`, `crystaltreeleaves`. **Tex:** OS (all in `orespawn.zip`); VAN fallback: ice 79 + glowstone.
- **Mobs:** Crystal Cow, Crystal Rat, Crystal Termite.
- **Mood:** bright pastel crystal: a surprising oasis at the bottom of the dark.
- **Segment:** "crystal maze": translucent cyan-white walls, crystal torches (cool light), the floor of crystal grass. The only cold, bright segment at the deepest end; a palette surprise.

### 83. Lycanites altars (summoning chambers)
- **Source:** Lycanites Mobs, `api/info/AltarInfo`, `demonmobs/info/AltarInfoRahovart`, `AltarInfoEbonCacodemon`, `infernomobs/info/AltarInfoUmberLobber`, `mountainmobs/info/AltarInfoCelestialGeonach`, `shadowmobs/info/AltarInfoLunarGrue`.
- **Layout:** an altar is a small block arrangement (a few blocks, e.g. obsidian 49 and a metal block) on which a Soulkey is used to summon a mini-boss; the mod ships no schematic rooms, so the "spawner room" is the altar placed in a built chamber.
- **Blocks:** obsidian 49, diamond/gold/iron blocks 57/41/42, glowstone 89, lava 11, depending on the altar (the Rahovart altar uses obsidian and a diamond-block topping). **Tex:** VAN only.
- **Mobs:** Rahovart, Ebon Cacodemon, Umber Lobber, Celestial Geonach, Lunar Grue.
- **Mood:** summoning.
- **Segment:** "altar niche": a 3x3x3 niche off the corridor, 4 corner torches, an obsidian dais with a coloured block on top; the grave alcoves around it. Use altar block recipes as alcove "totems".

### 84. Lucky traps: anvil, lava, pit and cage
- **Source:** Lucky Blocks, `mod/lucky/util/CustomStructures` (`makePitTrap`, `makeCage`, `makeWaterCage`), `LuckyBlockProperties.txt` (IDs `anvil_trap`, `lava_trap`, `water_trap`, `pit_trap`, `bedrock_problem`, `explosion`).
- **Layout:** pit trap: a 3-wide shaft of cobweb 30 at the top and lava 11 at the bottom (the class fills a narrow shaft with web near the top and lava at the bottom); the cage: a box of iron bars 101 and cobble wall 139; the anvil trap: an anvil 145 falling from above; the lava trap: lava 10 pour; the bedrock problem: a chamber of bedrock 7.
- **Blocks:** web 30, lava 11, iron bars 101, cobble wall 139, anvil 145, bedrock 7. **Tex:** VAN only.
- **Mood:** gleeful cruelty: designed to kill you.
- **Segment:** "trap hall": a deliberate hazard: a pit in the floor (with web across, lava below, 2-3 wide: the **lava gap**), an anvil hanging on a chain over the path, a cage descending. Tie each to a scare in the scares module.

---

## Section A: Corners and gaps catalogue

Quick picks for the spec's bend gaps (2-3 blocks of lava or water):

| Gap | From | Look |
|---|---|---|
| Lava moat with a slab bridge | 12, 50, 71 | stone corridor cut by a 2-wide lava channel, bridge of stone slabs 44 (missing slab = gap) |
| Water gap | 17, 18, 55 | plank causeway with a 2-3 block missing span over water |
| Pit with web | 84 | cobweb across a 2-3 wide shaft, lava below |
| Vanishing tile | 48, 76 | floor tiles that blink out for a second |
| Portal gap | 69, 77 | a bend where the path crosses a black void |

## Section B: Variety parameters (for krypt-gen)

Every entry above accepts these without new geometry:
- **Length** 6-40 (multiples of the entry's rhythm: 4 for alcoves, 6 for pillars, 15 for CQ rooms).
- **Width/height** (3x3 up to 9x9; vaults up to 15x15, towers up to 5x60).
- **Dressing seed**: picks wall-set variants (98 plain/mossy/cracked/carved at ratios 60/20/15/5), 4 floor variants, torch pattern, cobweb density, vine density, loot-less chest props.
- **Damage**: 0-4 (cracked and gravel ratio; HEE ravaged levels 0-4; TF collapse; mossy for dank).
- **Light colour**: per stratum, brightening within it (cold white to amber).
- **Alcove style**: plain recess, barred cell, bone niche, quartz-capped tomb, cauldron basin, glass pod, curtain (carpet), wishing well.

## Section C: Licence summary for the owner

- **Ship with the VAN decision only:** entries 1-35, 50-60, 62, 64-71, 77, 83, 84 (CQ, Roguelike, Doomlike and Recurrent Complex contribute layout ideas, not art).
- **Need a TF art decision, with a VAN fallback ready:** 36-49.
- **Need a HEE art decision, with a VAN fallback:** 72-76 (73 and 75 are mostly VAN already).
- **Need a WIT art decision:** 61, 63 (wicker, glyph, spirit water).
- **Already in use:** OreSpawn textures (78-82 beyond the vanilla part).
- **Camo (SR) textures:** not needed visually (64).
- **No art at all:** Roguelike and Doomlike entries; their value is layout and block palettes.
