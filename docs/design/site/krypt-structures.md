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
- **Layout:** the Vault is a 15x15 chamber with sand, TNT 46, pressure plate 52, chests 54: a treasure room with a TNT trap and the lure of a chest on a platform; the Fountain room has a water or lava basin; Spawner Chests has a spawner flanked by chests with iron bars and planks frames; Collapse is a rubble-filled square with gravel 13, dirt 3, grass 2 and ferns.
- **Blocks:** mazestone, sand 12, TNT 46, spawner 52, chests 54, iron bars 101, planks 5, gravel 13. **Tex:** TF (`mazestone_*`); VAN fallback as above.
- **Mobs:** Minotaur, Maze Slime.
- **Mood:** the "treasure room" and "collapsed ceiling" are great surprises.
- **Segment:** "vault crossing": a 15x15 room the path crosses diagonally, a chest dais in the middle (sand beneath and a visible TNT block under glass-like bars) and a collapsed corner of rubble. 15 long.

### 38. Labyrinth dead ends: torches, painting, trapped chest, lava fountain, roots
- **Source:** Twilight Forest, `ComponentTFMazeDeadEnd*` (Chest, TrappedChest, Fountain, FountainLava, Painting, Roots, Shrooms, Torches), `ComponentTFMazeEntranceShaft`, `ComponentTFMazeUpperEntrance`.
- **Layout:** each dead end is a cell terminating in a small dressing: a chest, a trapped chest 146 (explodes?), a water or lava fountain 8/10, a painting 321 item frame, a ring of torches.
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
