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
