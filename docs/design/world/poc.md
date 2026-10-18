# Decision 0003 proof of concept: a painted continent under RWG

**Date:** 2026-10-17
**Decision:** [0003 — hand-designed continent, procedural seas beyond](../../decisions/0003-designed-world.md)
**Method:** server trials only, built with `tools/trial/trial.py` on Forge 1614. No client was launched.

## Summary

| # | Question | Answer |
|---|---|---|
| 1 | Do mods still decorate painted chunks under `level-type=rwg`? | **Partly.** Ores, dungeons, structures and spawn tables follow the painted biome. **Trees and plants do not.** RWG decorates every chunk by its own noise biome, so the painted biomes get the wrong vegetation. |
| 2 | Can every biome ID be pinned with no collisions? | **Yes.** 83 BoP and 25 RWG biomes fill all 255 usable slots. One BoP biome (Canyon Ravine) is disabled. The boot was clean. |
| 3 | Does WorldPainter export a 1.7.10 world with modded biome IDs? | **Yes.** WorldPainter 2.27.1 has a "Minecraft 1.2 - 1.12" format that writes raw biome IDs from 0 to 254. It can also run headless through `wpscript`. |
| 4 | How long does pregeneration take, and how big is it, per million chunks? | Slim set: **about 2.1 h** to generate a million new RWG chunks and **about 1.5 h** to populate a million painted ones. On disk that is **about 7 GB**. |
| 5 | Can OptiFine E7 clients join with the GTNH RWG fork? | **Yes for RWG**, which needs nothing on the client. **BoP is the catch**: it needs Forge 1566 or later on both server and client, which means moving the pack from 1558 to 1614. |

**The decision holds, but it needs one piece of code.** A small qf-tweaks hook has to make RWG decorate painted chunks by their stored biome. Until that hook exists, painting biomes under RWG only changes ores, structures, spawns and colours.

## 1. Decoration of painted chunks under RWG

**Setup.** The test island was 2,000 blocks across, centred on 0,0, inside a 2,560 × 2,560 WorldPainter export (25,600 chunks).
- It had 10 painted regions: six BoP biomes (Redwood Forest, Tundra, Boreal Forest, Mystic Grove, Ominous Woods, Lavender Fields), three RWG biomes (Redwood, Snow Forest, Hot Desert) and vanilla Forest.
- Every chunk was exported with `TerrainPopulated=0`, and WorldPainter placed no ores.
- The same export ran on two servers. One had `generatorName=RWG`. The control had `BIOMESOP`, BoP's world type, which uses vanilla population.
- Both servers loaded BoP, RWG, Roguelike, Doomlike, Recurrent Complex, ChocolateQuest, Lycanites, JAS, OreSpawn and Chunk Pregenerator.
- Each world was inspected offline with `tools/world/scan_island.py`.

**Why RWG ignores the painted biome.** `ChunkGeneratorRealistic.populate` looks up its own noise map (`cmr.getBiomeDataAt`) and calls `rDecorate` on each RWG biome it finds there. It never reads the chunk's stored biome array. For a BoP biome that RWG supports, `rDecorate` calls BoP's `decorate()`, but only for the BoP biome the *noise* puts at that spot. Everything else in population reads the stored array: `IWorldGenerator` mods (ores and structures), world-gen animals (`getBiomeGenForCoords`), JAS and Lycanites. Vanilla population (`BIOMESOP`, `DEFAULT`) reads the stored array too.

**Measured, per chunk, RWG vs. the BIOMESOP control:**

| Painted region | Signature blocks under RWG | Signature blocks under BIOMESOP | Spawners (RWG / BOP) |
|---|---|---|---|
| BoP Redwood Forest (1,907 chunks) | redwood logs (`logs3`) 26, redwood leaves 48, plus a mix of other species | **logs3 254, leaves 470** | 333 / 444 |
| BoP Ominous Woods (1,754) | ominous leaves (`leaves1`) 30, mixed with others | **leaves1 400** | 293 / 180 |
| RWG Hot Desert (1,893) | about 130 leaves of forest trees | about 8 leaves | 600 / 577 |
| RWG Redwood (1,819) | about 420 leaves, mixed species | **about 6** (RWG base biomes have empty decorators) | 337 / 317 |
| BoP Tundra (518) | about 10 leaves | 72 leaves | 23 / 16 |
| BoP Lavender Fields (647) | about 600 leaves (a forest) | about 190 leaves | 1 / 1 |

- **Under RWG, painted regions are invisible in the vegetation.** The render shows RWG's own biome blobs across the island instead. RWG's snow-and-ice pass is also keyed to its noise, so it put **ice sheets over the painted sea** (the white patches in the render).
- **Ores are present everywhere**: vanilla ores, BoP gem ore (about 12 per chunk) and OreSpawn ores (about 40–60 per chunk). Under RWG, painted land holds **about 650–770 vanilla ore blocks per chunk, against about 350–400 under BIOMESOP**. RWG runs its own ore pass, and then BoP's `decorate()` runs another. The pack's ore balance would change, so this needs the ore survey and an approval decision.
- **Structures follow the painted biome, the same way under both generators.**
  - Recurrent Complex placed 576 structures inside |x|,|z| < 1000 under RWG and 577 under BIOMESOP. `structuredata.dat` was 55 KB.
  - Roguelike and Doomlike spawners and chests turned up in every forest region and almost none in Lavender Fields, Snow Forest or Tundra, again the same under both generators.
  - ChocolateQuest placed 18 `CQSpawner` tile entities and a spider boss in the painted Hot Desert under both.
- **Spawns:** JAS mapped every BoP and RWG biome by name (`BiomeGroups.cfg`). World-gen animals and Lycanites read the stored biome. Runtime Lycanites spawns were not observed, because they need a player.
- **Outskirts:** RWG generated past the sea with BoP biomes in its layout (Lavender Fields, Dead Forest, Snowy Coniferous and others), at about 247 BoP blocks per chunk.
  - At the edge of the export the seam is a **straight line**: RWG land starts right at ±1280.
  - The sea has to be painted wide enough to hide that seam, or the sea floor has to be painted down to match RWG's ocean depth.

**What broke, and how to fix it.**
- **Chunk Pregenerator skips chunks that already exist.** `pregen gen startradius ... 80` "finished" all 25,600 painted chunks in 1 s and populated none of them. Only the spawn area and the rim next to new outskirts got populated. **Use the `PostProcessingOnly` rule**, which `tools/world/pregen_island.py` does.
- **Recommended code fix:** a qf-tweaks transformer on `ChunkGeneratorRealistic.populate`, applied to chunks inside the painted bounds:
  - Decorate by the chunk's stored biome instead of the noise.
  - For a BoP or vanilla ID, call `biome.decorate()`.
  - For an RWG ID, call the `RealisticBiomeBase` whose base biome matches.
  - Skip RWG's noise-keyed snow pass.
  - Outside the painted bounds, run RWG unchanged.
- **Until that fix exists**, paint with BoP and vanilla IDs, not RWG IDs. RWG base biomes have empty decorators, so a painted RWG biome comes out bare under any generator but RWG's own.
- **Fallback with no code:** `BIOMESOP`. The painted core then decorates correctly (see the table), but the outskirts are BoP on vanilla-shaped terrain, not RWG.

## 2. Biome ID plan

The configs are `pack/config/biomesoplenty/ids.cfg` and `pack/config/RWG.cfg`. The generator script was kept in the session's scratchpad, not the repo. The resulting table is [`docs/survey/biome-ids.tsv`](../../survey/biome-ids.tsv).

- **RWG:** 204–228, all 25 in order. This moves RWG off Legends' 200–203.
- **BoP:** 83 biomes in alphabetical order across 59–66, 70–89, 138–139, 141–148, 150, 152–154, 159, 168–169, 183–199, 229 and 235–254.
- **Disabled: `Canyon Ravine ID=-1`.** It is a sub-biome that RWG never places. BoP's `registerOverworldSubBiome` and `registerBiomeToDictionary` both null-check, and no other BoP class refers to it.
- **Do not disable** Quagmire, Sludgepit, Silkglades, Wetland, Wasteland, Tropical Rainforest, Origin Valley, Ominous Woods, Mystic Grove, Dead Swamp, Crag or Bayou. BoP's `disableRivers()` dereferences each of them without a null check. RWG's `SupportBOP` also dereferences 42 BoP biomes without checks.

**Verified on a Forge 1614 server trial** with BoP, RWG, TwilightForest, TragicMC, 1Legends, OreSpawn, WelcomeToTheJungle and HEE.
- The boot had no ID errors.
- The `qf-biomedump` probe (`tools/world/biomedump/`) dumped **255 of 255 usable slots, with no overlaps**:
  - BoP 83, RWG 25, TragicMC 42, Twilight Forest 19, 1Legends 17, OreSpawn 5, Jungle 3, HEE 1.
  - Vanilla 31, plus 29 vanilla slots that BoP overrides.
- The only `SLOT_MISMATCH` is vanilla's own: Mega Spruce Taiga Hills M sits in slot 161 with biomeID 160.
- **There is no headroom left.** Any new biome mod needs a BoP biome disabled, or EndlessIDs.
- Slots 138–169 hold BoP IDs. That only matters under BIOMESOP, where `GenLayerHills` turns biome *k* into *k*+128. RWG has no GenLayers.

## 3. WorldPainter

WorldPainter 2.27.1 (2026-08-30) was downloaded to the scratchpad.
- **Format:** platform `org.pepsoft.anvil`, "Minecraft 1.2 - 1.12". It writes the 1.7.10 layout: `Blocks`/`Data`/`Add` sections and a 256-byte `Biomes` array.
- **Modded biome IDs:** the Biomes layer holds raw IDs 0–254, and the export kept every painted ID (196, 247, 225 and the rest, checked offline). In the GUI, the author declares the modded IDs under *Edit → Custom Biomes* with the numbers in `docs/survey/biome-ids.tsv`, then paints them.
- **Population:** with *Allow Minecraft to populate* on (`Dimension.setPopulate(true)`), every chunk is exported with `TerrainPopulated=0`.
- **`level.dat`:** WorldPainter writes `generatorName=largeBiomes`. It has to be set to `RWG` after export, with a fixed seed. The test did this with nbtlib.
- **Headless:** `wpscript.exe` runs on the installed JDK 25 (`INSTALL4J_JAVA_HOME`). `tools/world/wp_build_island.js` builds a world from a height PNG and a biome PNG, then saves and exports it: 25,600 chunks in 19 s.
  - **Trap:** a scripted `createWorld()` keeps default Resources settings made for modern versions, and the export dies with *"Cannot store modern material copper_ore ... in pre-1.13 Anvil chunk"*. The script clears the Resources layer. Leave it cleared anyway, so the game places the ores.
- **Viable for the author: yes.** Paint by hand in the GUI, with the same Custom Biomes, populate on, and the Minecraft 1.2–1.12 format. The `.world` file the script saves opens in the GUI as a starting point.

## 4. Pregeneration time and disk size

Slim server trial: 11 mods plus the base set, Java 8, 4 GB heap, Chunk Pregenerator `timepertick 250`, single node.

| Step | Chunks | Time | Rate | Per million chunks |
|---|---|---|---|---|
| WorldPainter export (unpopulated) | 25,600 | 19 s | 1,350/s | about 12 min |
| RWG outskirts, new chunks | 24,576 | 185 s | 133/s | **about 2.1 h** |
| Populate painted chunks, RWG (`PostProcessingOnly`) | 24,306 | 135 s | 181/s | **about 1.5 h** |
| Populate painted chunks, BIOMESOP control | 24,189 | 74 s | 326/s | about 0.85 h |

| On disk (region files incl. sector padding) | KB/chunk | Per million chunks |
|---|---|---|
| WorldPainter export, unpopulated | 4.0 | 4 GB |
| Painted land after RWG population | 5.7–9.1 (mean 7.1 over the whole world) | **about 7 GB** |
| RWG outskirts | 6.9 | about 7 GB |
| Painted land after BIOMESOP population | 5.5 | 5.5 GB |

- A million chunks is 16,000 × 16,000 blocks. The test island is about 15,600 chunks: two minutes of population and about 110 MB.
- The full pack will be slower. The ore survey measured 97–156 chunks/s per node for vanilla worldgen with every mod loaded.

## 5. Client requirements and OptiFine E7

- **RWG alpha-1.5.2** declares `acceptableRemoteVersions="*"`, has no dependencies and no mixins or coremod, and is Java 8 bytecode (class version 52). **It does not need GTNHLib or any other GTNH library**, and clients do not need RWG installed. If it is left off the clients, RWG biome IDs fall back to Plains colours there. It is harmless to ship it to clients, and it should go out with `RWG.cfg` because of the qf-content ID check.
- **BoP 2.1.0.2308** has to be on every client (it adds blocks), and its `@Mod` declares **`required-after:Forge@[10.13.4.1566,)`**. On the pack's Forge 1558 it fails at boot with a `MissingModsException`. This trial hit that, and `trial.py --forge 1614` was added because of it.
  - Moving to Forge 1614 means rebuilding the hand-patched qf splash. That patch lives in the 1558 Forge jar (see the memory note on the splash).
  - OptiFine E7 is commonly run on 1614, but **an E7 client on 1614 has not been booted on this PC**. That needs one client boot, which was not done here because another agent's client held the lock.
- **Verdict:** RWG does not affect whether OptiFine E7 clients can join. BoP turns the Forge upgrade to 1614, which Angelica needed anyway, into a requirement.

## Files

- `pack/config/biomesoplenty/ids.cfg`, `pack/config/RWG.cfg`: the pinned IDs.
- `docs/survey/biome-ids.tsv`: the live registry dump.
- `tools/trial/`: `stage` for candidate jars, catalog entries `biomesoplenty`, `rwg` and `biomedump` (staged), and `build --forge 1614`.
- `tools/world/make_test_island.py`: height and biome PNGs.
- `tools/world/wp_build_island.js`: the WorldPainter headless build and export.
- `tools/world/pregen_island.py`: populate and pregenerate with timing.
- `tools/world/scan_island.py`: offline per-biome inspection and a top-down render.
- `tools/world/biomedump/`: the biome-registry probe.

Downloads for this run, in the session scratchpad: `BiomesOPlenty-1.7.10-2.1.0.2308-universal.jar` (Modrinth, sha1 b0d13f22…), `RWG-alpha-1.5.2.jar` (GitHub GTNewHorizons/Realistic-World-Gen) and WorldPainter 2.27.1 (sha256 matches worldpainter.net). The trial worlds are still on disk at `%APPDATA%\.qf-trials\w-rwg` and `w-bop`.

## RWG decoration hook

**Date:** 2026-10-17. **Code:** `mods/qf-tweaks/src/com/questforge/RwgPaintTransformer.java` and `RwgPaintHook.java`. The jar is built by `build.bat --no-install` and is not installed in the live pack.

**What it patches** (`rwg.world.ChunkGeneratorRealistic` in RWG alpha-1.5.2; RWG's own methods gain no branches):
- **`populate`, the one `RealisticBiomeBase.rDecorate` call.** It now goes through a new static bridge, `qf$rDecorate`, which first asks `RwgPaintHook.decoratePainted(...)`.
  - Outside the painted area that returns false, and RWG's own `rDecorate` call runs unchanged.
  - Inside the area, the chunk is decorated once by its stored biomes, and every noise-biome call is skipped.
- **`populate`, the `snow < 0.59f` test.** For a painted chunk the test reads 1, so RWG's noise-keyed snow pass is skipped. Vanilla's ice step runs in its place (`isBlockFreezable` and `func_147478_e` per column), and it reads each column's stored biome temperature.
- **`provideChunk`.** It records the chunks RWG itself generates inside the rectangle, for the safety check below.

**How painted decoration works.**
1. It takes 8×8 stored-biome samples over the population window `[x+8, x+24)`. That window lies inside the four chunks population already has loaded, so nothing new is loaded.
2. It decorates each biome present, in biome-ID order. A biome's strength is its share of the samples, the way RWG blends.
3. **BoP biomes:** RWG's `RealisticBiomeSupport` wrapper decorates them. That is BoP's `decorate()` when the share is over 0.3, plus RWG's edits.
4. **RWG base biomes:** one RWG variant decorates each. Several variants share a base, so `rwgPreferred` in the config picks one (Hot Desert → `RealisticBiomeDesert`). RWG's placeholder `*Test*` biomes are never used.
5. **Vanilla biomes, and BoP biomes RWG does not support:** they get their own `decorate()` when their share is over 0.3.
6. The dominant biome always decorates.
- RWG's `baseRedwood` (225) has no RWG variant, so a painted RWG Redwood comes out bare, as it does under BIOMESOP. **Paint redwoods with BoP Redwood Forest (196).**

**How a chunk counts as painted.**
- **The config rectangle.** It lives in `config/qftweaks-rwgpaint.cfg`, written on first use. The default is blocks ±16384, the continent's piece-built, 512-aligned extent. A chunk must lie wholly inside it.
- **Safety check.** Any chunk that RWG's own `provideChunk` generated inside the rectangle during this session keeps stock decoration. That covers a hole in the export, or a rectangle larger than the export. Painted chunks come from disk with `TerrainPopulated=0` and never pass through `provideChunk`.
- **Limit of the check.** The check is held in memory. A chunk that RWG generated inside the rectangle in an *earlier* session and left unpopulated would be treated as painted. Only a hole in the export can produce one.
- `enabled=false` turns the hook off. Any reflection failure also disables it, with one log line, and RWG then runs stock.

**Test.**
- **World:** the PoC export, a 2,560 × 2,560 island with seed 20261017 and `generatorName=RWG`.
- **Servers:** slim Forge 1614 trials with the base set, BoP, RWG and Chunk Pregenerator, plus `--overlay pack`.
- **Runs:** two with the hook (rectangle ±1280, the export's bounds) and two stock, with the live qf-tweaks.
- **Steps:** `pregen_island.py ... 81:PostProcessingOnly 112`, then `scan_island.py`.
- **Log:** `Transform applied: RWG decorates painted chunks ...` and about 25,000 painted chunks decorated. Neither world had an exception.

Per chunk, by painted region:

| Painted region | Hook: signature | Stock RWG: signature | BIOMESOP control (§1): signature | Vanilla ores: hook / stock / BIOMESOP |
|---|---|---|---|---|
| BoP Redwood Forest | **redwood logs 265**, leaves 583 | logs 27, leaves 205 | logs 254, leaves 557 | 649 / 652 / 356 |
| BoP Ominous Woods | **ominous leaves 415** | 28 | 400 | 642 / 642 / 347 |
| BoP Boreal Forest | leaves 436 | 158 | 426 | 643 / 467 / 357 |
| BoP Mystic Grove | leaves 281 | 22 | 342 | 645 / 530 / 352 |
| BoP Tundra | leaves 91 | 11 | 80 | 654 / 642 / 360 |
| BoP Lavender Fields | leaves 48 | 525 (a forest) | 190 | 834 / 900 / 450 |
| Vanilla Forest | leaves 298 | 30 | 285 | 942 / 708 / 671 |
| RWG Hot Desert | **leaves 24** | 131 (forest) | 8 | 383 / 758 / 395 |
| RWG Snow Forest | leaves 59, **snow layers 216** | leaves 514, snow 0.2 | leaves 16 | 449 / 955 / 456 |
| RWG Redwood | leaves 7 (bare, see above) | 426 | 7 | 725 / 767 / 396 |
| Deep Ocean (sea) | **ice 0.9 per chunk, in 124 of 13,182 chunks** | **ice 44.5 per chunk, in 3,475 chunks** | n/a | 397 / 400 / 223 |

- **Painted biomes now decorate like the BIOMESOP control.**
- **Painted sea no longer freezes.** The little ice left is on the coast next to the painted Snow Forest.
- **Lavender Fields comes out below the control** (48 vs 190). The cause is the vanilla `WorldGenBigTree` bug described under the outskirts below.
- **Ores now follow the painted biome.**
  - RWG's own ore pass, about 380–450 vanilla ore blocks per chunk, runs in every chunk.
  - A painted BoP or vanilla biome adds its decorator's ore pass on top, for about 640–940. An RWG base biome adds none.
  - Under stock RWG, the noise biome decided this instead.
  - BoP gem ore also follows the painted biome: about 12 per chunk in BoP land, 0 in sea and desert.
  - **This is for the ore survey and an approval decision. Nothing was rebalanced.**
- **Structures:** the mineshaft, village, stronghold, dungeon and `IWorldGenerator` passes run before or outside the patched calls.
  - Tile entities per region match within ±5 between hook and stock. Redwood Forest, for example, has 45 spawners and 18 chests with the hook, and 46 and 20 stock.
  - §1's structure mods were not in this slim set. §1 showed they read the stored biome on their own.
- **Speed:** with each server running alone, painted population ran at 328 chunks/s with the hook and 198 chunks/s stock. Each painted chunk makes fewer decorate calls than RWG's 9×9 noise blend. Speed is not a concern.

**Outskirts stay stock.**
- **No hook work runs there.** Outside the rectangle the bridge makes RWG's original `rDecorate` call, and the snow test reads RWG's own value.
- **A block-for-block comparison does not work, because stock RWG is not reproducible run to run.**
  - Two stock runs of the same world and seed matched block-for-block in only 31% of outskirts chunks (median 20 blocks different).
  - Hook against stock gave the same picture: 32% matched, median 17 blocks different.
- **The aggregates agree:**

| Outskirts, per chunk | Hook | Stock run 1 | Stock run 2 |
|---|---|---|---|
| Vanilla ores | 586 | 587 | 585 |
| Gem ore | 10.2 | 10.2 | 10.2 |
| Ice | 4.2 | 4.2 | 4.2 |
| Coal | 349 | 350 | 348 |

  - The biome mix is identical in all three.
  - Spawners and chests: 699 and 759 with the hook, 694 and 753 in stock run 1, and 699 and 759 in stock run 2.
- **The one difference: trees in a few outskirts biomes.** Vanilla-leaf counts differ in BoP Lavender Fields, RWG Temperate River and Hot Plains. Lavender Fields has 23.5 per chunk in both hook runs, against 165 and 119 in the two stock runs.
  - **The cause is vanilla 1.7.10's `WorldGenBigTree`.** Each biome shares one instance, and it sets `heightLimit` only while that is still 0, so **the first big tree of the session fixes the size of every later big tree in that biome.**
  - Stock varies with whichever chunk populates first. With the hook, the first Lavender big tree is always the same painted one, so the outskirts are stable but different.
  - So the difference comes from that bug's session-order dependence. No hook code runs in the outskirts.
  - Resetting `heightLimit` per tree would fix it, as a separate patch.

**Installing, after review.**
- Rebuild with `mods/qf-tweaks/build.bat --no-install`.
- Install with `py -3.10 tools/trial/trial.py install mods/qf-tweaks/QuestForgeTweaks-1.0.jar --why "RWG paint hook"`.
- On the server, set the rectangle in `config/qftweaks-rwgpaint.cfg` to the continent's real export bounds.
- Only servers that run `level-type=rwg` need the hook. It does nothing on clients, but they share the same coremod jar.
