# Continent v0: first in-game test

**Date:** 2026-10-17
**Plan:** [`continent-v0.yaml`](continent-v0.yaml), described in [continent-v0.md](continent-v0.md)
**Decision:** [0003](../../decisions/0003-designed-world.md); method follows the [proof of concept](poc.md)
**Setup:** one full-pack dedicated server: 136 mods, Forge 10.13.4.1614, BoP 2.1.0.2308, RWG alpha-1.5.2, Java 8, `-Xmx8G`. Server trials only; no client was launched.

## Summary

**The pipeline works end to end, and the full pack loads and populates the 32,768-block continent with no worldgen crash.**
- The plan expands into four 16,384-block pieces, WorldPainter builds and exports them, and the stitched world boots.
- The painted world populates at 80 to 150 chunks/s on the full pack.
- Biomes, terrain and sea come through exactly as painted.
- The piece seams at x=0 and z=0 cannot be seen in height or in decoration.

Three things need work before the author paints for real:

1. **Surface blocks follow WorldPainter's height theme, not the biome.**
   - The painted Wasteland (Ash Reach) reads as a green meadow with ponds.
   - The Volcano (the Wound) has a grass rim and a snow cap.
   - Fix: `wp_piece.js` should lay per-biome terrain.
2. **Vegetation borders between biomes step in 16-block chunk squares.** This comes from 1.7.10 population, which decorates each chunk by a single biome.
3. **The world edge is a straight line**, where generated land meets the painted sea.

The BIOMESOP control decorates the painted biomes correctly. Stock RWG again ignores them: on the Redwood Coast it places 0 redwood logs, against 272 per chunk under BIOMESOP. The qf-tweaks hook that fixes this (f7fab36) landed while this test ran and was **not** used here.

## 1. Pipeline: time, RAM and disk

| Step | Time | Peak RAM | Output on disk |
|---|---|---|---|
| `plan.py expand`, 4 pieces in parallel | 20.3 min wall | 1.6 GB working set (3.1 GB commit) per process | 117–133 MB of PNGs per piece |
| `wp_piece.js` build + export, piece 0,0 | 8.5 min | 7.1 GB (heap capped at `-Xmx8g`) | `.world` 259 MB; export 4.30 GB |
| piece 0,1 | 11.0 min | 7.9 GB | 224 MB; 4.30 GB |
| piece 1,0 | 8.4 min | 8.3 GB | 244 MB; 4.30 GB |
| piece 1,1 | 9.8 min | 8.3 GB | 227 MB; 4.30 GB |
| `stitch.py` (4,096 region files) | 34 s | small | 17.2 GB world |
| **Whole pipeline** | **about 58 min** | | |

- Each piece is 1,024 region files and 1,048,576 chunks; the continent is 4.19 M chunks.
- The export comes to about 4.1 KB per chunk unpopulated.
- WorldPainter uses all the heap it is given. With 8 GB it finished every piece, but sat at the cap the whole time. Opening one 16,384 piece in the GUI probably needs a heap of at least 8 GB. The author's Mac has not tried it yet.
- The four piece `.world` files are in `C:\qf-world\pieces\qf-v0-piece_{0,1}_{0,1}.world`, a Syncthing folder.
- **Fixed during the test:**
  - `plan.py expand` used 1,024-row strips, which took about 5 GB per process and paged heavily. It now uses 256-row strips (about 1.6 GB) and gives identical output.
  - `stitch.py` gained `--generator` (RWG or BIOMESOP).

**Machine note.** At the start of the run OneDrive.exe held **26.7 GB of private commit**, and the system was at 59.5 of 66 GB committed, with only 3–4 GB of physical RAM free. That forced the expansion runs to be serialised. It is the same leak the census memory note records (7 GB then). Restarting OneDrive would free most of it.

## 2. Server and boot

- The server is built at `C:\qfs\v0` with `tools/survey/build_server.py`, on the live instance with Forge 1614. On top of that build it adds:
  - BoP and RWG from the trial staging folder;
  - the pinned `pack/config/biomesoplenty/ids.cfg` and `pack/config/RWG.cfg`;
  - the null-guarded CodeChickenLib.
- Hodgepodge is not in the pack, so its two settings did not apply.
- `level.dat` uses `generatorName=BIOMESOP`, seed 20261017, with spawn at Driftwood Landing (-12300, -1500).
- **Boot:** 48 s to `Done`, all 136 mods loaded, 1.8 GB working set.

**Log lines that touch worldgen, biomes or chunks.** Nothing crashed, and every pregen task finished.

| When | Message | Assessment |
|---|---|---|
| Boot | No biome ID conflict or "already occupied" messages. `Redundant call to BiomeDictionary.registerAllBiomes ignored` | Clean. The pinned IDs hold in the full pack. |
| Boot | JAS: `Duplicate mapping Ocean and was renamed to biomesoplenty.Ocean`, and the same for Plains, Desert, Extreme Hills, Forest, Taiga, Swampland, River and Hell | BoP overrides those vanilla biomes. The JAS table rebuild in decision 0003 has to use the renamed keys. |
| Boot | JAS: 12 `Error processing com.entity_* ... does not exist` (HBM/NTM names) | Already present in the pack's JAS config; not worldgen. |
| Boot | VoltzEngine JsonContentLoader: `Could not locate folder /content/BiomesOPlenty/` | Harmless; BoP ships no VE content. |
| Populate, the Wound | Doomlike Dungeons printed 16 stack traces `java.lang.Exception: Place block at x, y` from `DBlock.placeChest` | One dungeon logging a debug trace. The dungeon was still placed. |
| Populate, Sunfields | 25 × `Skipping Entity with id ` (empty id), near block 368, 9456 | Some worldgen saved an entity with no id, and it was dropped on load. Cosmetic; the mod was not identified. |
| RWG copy only | ChocolateQuest `ClassCastException: TileEntityChest cannot be cast to TileEntityFurnace` in `RoomBase.placeFoodFurnace`, from a castle kitchen | A CQ bug. Chunk Pregenerator skipped the chunk ("1 Failed"), so it stays unpopulated. |
| RWG copy only | Lycanites `SpawnTypeTree.onBlockHarvest`: `ReportedException: Exception getting block type in world` during a `HarvestDropsEvent` | A Lycanites tree-spawn hook reading a block during population. Caught; it did not cause a failed chunk. |

- Recurrent Complex saved its structure data correctly (1,378 entries).
- On Windows that data sits in an NTFS alternate data stream: `data\reccomplex:structuredata.dat`. A directory listing shows it as a 0-byte file named `reccomplex`. `inspect_area.py` reads the stream.

## 3. Population: time and throughput

Chunk Pregenerator ran with `timepertick 250` and the `PostProcessingOnly` rule, centred in block units (`b` prefix). Each task was a square of the given half-width.

| Area | Centre, half-width (blocks) | Chunks | Time | Chunks/s | Server working set (max) | Mean tick (`forge tps`) |
|---|---|---|---|---|---|---|
| a. Sunfields / Lavender Sea, on the x=0 seam | 0,10000, 1200 | 22,500 | 4 min 41 s | **80** | 5.9 GB | 3.7 ms, 20 TPS |
| b. The Wound, where all four pieces meet | 0,0, 1000 | 15,376 | 1 min 42 s | **150** | 3.3 GB | 11.5 ms, 20 TPS |
| c. Driftwood Landing, Redwood Coast | -12300,-1500, 500 | 3,844 | 34 s | 113 | 5.3 GB | 8.6 ms, 20 TPS |
| d. Ash Crater, Ashen Reach | 7500,6000, 800 | 10,000 | 1 min 12 s | 138 | 4.6 GB | 17 ms, 20 TPS |
| e. Shade Pass, Crown Range | -3110,-3110, 600 | 5,476 | 36 s | 152 | 3.4 GB | 15 ms, 20 TPS |
| f. West rim, generate new chunks (bonus) | -16384,-1500, 400 | 2,500 | 10 s | 250 | — | — |
| f. West rim, populate | same | 2,500 | 6 s | 416 | — | — |
| RWG copy: a | as a | 22,500 | 2 min 26 s | 154 | 6.1 GB | 13.9 ms |
| RWG copy: c | as c | 3,844 | 26 s | 148 | — | — |

- `forge tps` reads 20 TPS throughout, because Chunk Pregenerator works inside its own time budget per tick.
- The first task ran slower (80 chunks/s) while the JVM and the class caches warmed up. Every later task ran at 110–150 chunks/s.
- **Estimate for the whole painted continent:** 4.19 M chunks at about 120 chunks/s is **about 10 h on one node.** Most of it is sea, which populates faster.
- Each task leaves its outer row of chunks unpopulated, because population needs the +x/+z neighbours. A full-continent run covers that.
- On disk, painted chunks went from about 4 KB to 8–11 KB per chunk after population. The world was 17.6 GB after about 60 k chunks had been populated.
- Results: `C:\qfs\v0\pregen-result-*.json`. Logs: `C:\qfs\v0\pregen-biomesop.log` and `pregen-rwg.log`.

## 4. What populated chunks contain

Measured offline with `tools/world/inspect_area.py`. Figures are per chunk, by each chunk's majority biome.

| Area | Biomes stored = plan | Ground − plan height | Painted biome: logs / leaves per chunk | Ores per chunk (all mods) | Spawners | CQ spawners | Recurrent Complex structures |
|---|---|---|---|---|---|---|---|
| a. Sunfields | 100% (Prairie 84.5%, Lavender Fields 15.4%) | mean +0.5, mean abs 0.6, p99 2 | Prairie 2.4 / 10; Lavender Fields 5.1 / 69 (BoP `leaves4` 23) | 1,361 | 3,887 | 137 | 461 |
| b. The Wound | 100% (Volcano) | +0.5 / 0.6 / 3 | 0.8 / 7.5 | 1,457 | 672 | 31, plus a CQ spider boss and a lich | 289 |
| c. Redwood Coast | 100% (Redwood Forest) | +0.5 / 0.6 / 2 | **272 BoP redwood logs (`logs3`)**, 495 BoP leaves | 1,389 | 245 | 0 | 197 |
| d. Ash Crater | 100% (Wasteland) | +0.2 / 0.7 / 3 | 2.7 / 0.5 (BoP dead `logs3` 2.2) | 1,216 | 1,562 | 7 | 276 |
| e. Shade Pass | 100% (Alps 78.5%, Ominous Woods 21.5%) | +0.5 / 0.6 / 2 | Alps 0.4 / 2.2; Ominous Woods 39 / 386 (BoP `leaves1` 382) | 1,417 | 465 | 0 | 52 |

- **Decoration follows the painted biome under BIOMESOP.**
  - Redwood Coast: 272 redwood logs per chunk (the PoC island had 254).
  - Ominous Woods: 382 ominous leaves per chunk.
  - Lavender Fields carries BoP's own trees; Prairie stays open grassland.
- **Ores:** 1,216–1,457 per chunk. That is in line with the ore survey's 1,141 for vanilla worldgen in the full pack, plus more stone volume under high terrain. The top ores are coal, iron, VoltzEngine stone and gem ores, and Legends black and red iron, silicon and cassiterite.
- **Dungeons and structures** appear in every area:
  - Mob spawners from Roguelike, Doomlike and vanilla dungeons;
  - Recurrent Complex's stone mazes, crypts, cottages, shrines and meteor sites;
  - ChocolateQuest, mostly on the open Prairie.
  - Mineshaft, stronghold, temple and village data were written as well.
- **Water:**
  - 99.9% of the columns planned as sea are water.
  - No ice formed on the sea under BIOMESOP; RWG put ice on 0.13% of it.
  - On land, vanilla and BoP lakes add surface pools: 1.7–3.5% of columns in most areas, but **12.8% in the Wasteland.**
- **Seams:** none.
  - The average ground step across x=0 is 0.04 (Sunfields) and 0.06 (Wound), against 0.08–0.13 for any other column boundary. Across z=0 it is 0.05.
  - Logs per chunk on either side of the seam match within noise: 2.2 / 2.8 at Sunfields, 0.2 / 0.3 and 0.4 / 0.6 at the Wound.
  - The renders show no line.
- **Observations for the danger and spawn design:**
  - **Villages generate in the T4 Wound**: 212 villagers, plus Witchery village guards.
  - A ChocolateQuest spider boss and a lich also spawned in the Wound.
  - Structure placement knows nothing about tiers.
  - Almost no world-gen animals were saved: 1 cow in about 60 k chunks. That is probably JAS owning the spawn lists, but it was not verified. It belongs with the JAS rebuild.

### BIOMESOP vs stock RWG, same painted chunks

| Area | BIOMESOP | Stock RWG |
|---|---|---|
| Redwood Coast | 272 redwood logs per chunk, 495 BoP leaves | **0 redwood logs**; 21 oak logs, 185 oak leaves (generic forest) |
| Prairie | 2.4 logs, 10 leaves (open grassland) | 50 logs, 313 leaves (a forest) |
| Ores per chunk | 1,361 / 1,389 | 1,537 / 1,690 (**+13% / +22%**: RWG's ore pass plus BoP's `decorate`) |
| ChocolateQuest spawners (Sunfields) | 137 | 10 |
| Recurrent Complex, spawners | 461, 3,887 | 460, 3,884 (the same) |

This repeats the PoC finding on the real continent. Stock RWG paints the wrong forests and inflates ore. The hook in f7fab36 is meant to fix both and has to be measured on this world next.

## 5. Renders

All in `C:\qf-world\renders\`. Each area render is 1 px per block, block colours with hillshade. Red dashes mark x=0 / z=0, and there is a 500-block scale bar.

| File | What it shows |
|---|---|
| `v0-overview-continent.png` | The whole continent from the exported piece heights, 1 px = 8 blocks. Biome colours, region labels, spawns and landmarks, the test areas boxed, piece seams dashed. |
| `v0-a-sunfields-seam.png` | Prairie and Lavender Fields across x=0; no seam. Shows the scattered ponds and Prairie's open look. |
| `v0-b-wound.png` | The Volcano caldera where all four pieces meet. The surface is WorldPainter's height theme: grass rim, dirt, stone, snow cap. |
| `v0-c-driftwood-redwood-coast.png` | Dense BoP redwood forest around the spawn. |
| `v0-d-ash-crater.png` | The painted Wasteland. It looks like a pond-dotted meadow (issue 1 below). |
| `v0-e-shade-pass.png` | The Alps / Ominous Woods border. The forest edge steps in 16-block chunks (issue 2). |
| `v0-f-west-rim.png` | The world edge at x=-16384. BoP-generated land (desert, steppe, canyon) meets the painted deep sea in a straight line (issue 3). |
| `v0-rwg-a-sunfields-seam.png`, `v0-rwg-c-driftwood-redwood-coast.png` | The same chunks under stock RWG, for comparison. |

## 6. What broke, and recommendations

1. **Surface blocks ignore the painted biome.**
   - Population never reruns a biome's `topBlock` or `fillerBlock`, so every painted chunk keeps the surface WorldPainter's default theme gave it: grass, then dirt, stone and snow as height rises.
   - The Wasteland, Volcano, Alps, deserts and mesas all come out as grassland or generic mountain.
   - **Recommendation:** in `wp_piece.js`, apply a per-biome terrain from a table of biome to top and filler material. Vanilla materials are safe. BoP's own blocks (dried dirt, ash, hard sand) need their numeric IDs, which this world's `level.dat` FML registry now fixes for the current mod set. The author can repaint by hand on top of that.
2. **Vegetation borders are chunk-quantised.** 1.7.10 decorates each chunk by one biome, so forest edges step in 16-block squares where two decorated biomes meet. There is no cheap fix. One mitigation is to use painted transition biomes, such as a sparse woodland, between dense forest and open land.
3. **The world edge is a straight seam.**
   - Past ±16,384, BoP (or RWG) generates whatever it likes, including land right at the edge.
   - **The author has to decide** between:
     - (a) making the sea ring wider, which only moves the line;
     - (b) a qf-tweaks rule that forces ocean in a band outside the painted rectangle;
     - (c) accepting it as the "frontier" edge.
4. **Run the f7fab36 RWG hook on this world** (areas a and c are ready in `C:\qfs\v0\world-rwg`, as unpopulated copies rebuilt from the exports). Check redwood logs, Prairie openness and ore per chunk against the BIOMESOP column above. The ore increase under RWG still needs the balance approval the PoC flagged.
5. **Danger and structure placement.** Villages and ChocolateQuest bosses ignore tiers, so the T4 Wound got villages. If the design wants tiered danger, structure spawns need per-region config, for example Recurrent Complex and ChocolateQuest biome filters.
6. **Wasteland ponds.** 12.8% of the painted Wasteland is surface water. Check BoP's Wasteland lake settings, or paint the area drier, before it becomes a hero region.
7. **Pregeneration budget:** about 10 h on one node for the whole painted continent at full-pack speed, and about 17 GB unpopulated growing to about 35–45 GB populated (from the 8–11 KB per chunk measured here).

## Files

- `tools/world/pregen_island.py`: tasks can now be centred anywhere (`NAME=RADIUS[:RULE][@X,Z]`, with `b` for blocks), and it records `forge tps` and the JVM working set.
- `tools/world/stitch.py`: `--generator RWG|BIOMESOP`.
- `tools/world/inspect_area.py` (new): per-area check against the plan (biomes, heights, water, seams, decoration, ores, structures, including Recurrent Complex's NTFS stream) plus a hillshaded render.
- `tools/world/render_overview.py` (new): the whole-continent overview from the piece heights.
- `tools/world/plan.py`: 256-row strips in `expand`, committed in 3418334.
- The test server and worlds stay on disk: `C:\qfs\v0` (`world` is BIOMESOP, the main test; `world-rwg` is the RWG comparison). The piece inputs and exports are in the session scratchpad.
