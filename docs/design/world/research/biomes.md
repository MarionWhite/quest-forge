# Biome / worldgen research for Quest Forge (1.7.10, GTNH stack)

Research only; nothing was installed, launched or changed in the repo. Date: 2026-10-17.
"UNVERIFIED" marks claims I could not confirm from a primary source.

## TL;DR

- **The best-supported choice is Biomes O' Plenty 2.1.0.2308 with GTNH's Realistic World Gen fork (alpha-1.5.2), using `level-type=rwg`.** GTNH ships exactly this pair. Hodgepodge, Angelica and EndlessIDs all have code written specifically for BoP and RWG, and GTNH 2.9.0-RC-2 still lists both. No other 1.7.10 worldgen mod has that level of support on the GTNH stack.
- **Foliage:** use **Better Foliage – Legacy Edition 1.2.4** (2026-01-31). It is a maintained fork, says it is Angelica-compatible, is client-only, and needs UniMixins and Forgelin: Legacy.
- **Biome IDs:** the pack has **108 free IDs**. BoP needs 84 and RWG needs 25, a total of 109, so it is one short. **RWG's default IDs (200–224) also collide with Legends (200–203)**. The fix is to pin every ID by hand and disable a few BoP biomes. EndlessIDs is technically possible (GTNH 2.9 ships it), but too many of the pack's mods are unpatched for it to be safe here.
- **The biggest catch is that RWG's own land biomes report RWG "base" biomes, not vanilla ones.** Under RWG, vanilla Plains, Desert, Taiga and so on almost never appear. RWG's generator also does not run vanilla scattered features (desert temples, jungle temples, witch huts). Anything in the pack keyed to vanilla biome names stops working: JAS per-biome tables and any mod that checks `== BiomeGenBase.desert`.
- **Skip** Highlands, ExtraBiomesXL, RTG, Climate Control, Streams and Dynamic Trees. Each is dead since 2015–2018, has no GTNH patches, and is either redundant with RWG or conflicts with it.

## 1. Candidates

| Mod | Latest 1.7.10 | Maintained fork / GTNH status | GTNH-stack compatibility | Contributes | Notes |
|---|---|---|---|---|---|
| **Biomes O' Plenty** | 2.1.0.2308 (2017-11-13; also on Modrinth) | Licence is CC-BY-NC-ND, so it can't be forked. **GTNH ships the stock jar** (2.8.4 and 2.9.0-RC-2 manifests). GTNH is rewriting it as Viridium (MIT, no releases yet, aimed at Cubic Chunks) and earlier as BiomeBridge (stale since 2024). | **Hodgepodge** carries about 20 BoP mixins. They include `java12BopCompat` (Java 9+ reflection, needed on Java 25), a cascading-kelp worldgen fix, decoration allocation caching, faster leaf decay, a fog speedup, an EndlessIDs compat fix and an optional quicksand removal. **Angelica** has BoP fog blending and BoP particle compat, and classifies BoP biomes for shader biome uniforms (`compat/bop`, `ModdedBiomeDetector`). | Biome content: 59 overworld, 16 sub-biomes, 2 rivers, 6 Nether, 1 End = **84 biomes**. Redwood Forest, Tundra, Alps, Wasteland, Dead Forest, Ominous Woods, Bog, Crag and others. It also overrides vanilla biome classes and the Nether. | BoP biomes only generate in its own `BIOMESOP` world type, or through RWG. It auto-assigns IDs from 40 upward at its own init, so all IDs must be pinned in `config/biomesoplenty/ids.cfg`. [CF](https://www.curseforge.com/minecraft/mc-mods/biomes-o-plenty), [src 1.7.10](https://github.com/Glitchfiend/BiomesOPlenty/tree/BOP-1.7.10-2.1.x) |
| **Realistic World Gen (RWG)** | GTNH fork **alpha-1.5.2** (in 2.9.0-RC-2; 2.8.4 had alpha-1.5.0) | **GTNH fork**, GPL-3, of the original Ted80 alpha 1.3 from 2015. Fixes since then: far-coordinate terrain breaks (−20480, −28675), configs for caves, mineshafts, villages and lakes, a 2.2-compat command, and an optimisation pass on 2026-02-23 (PerlinNoise, CellNoise, tree decoration, ChunkGenerator). | GTNH's own pack runs it on Java 17–25 with Angelica and Hodgepodge. Angelica has RWG-specific shader biome categories. | **Terrain shape plus layout**, through its own noise-based biome map with no vanilla GenLayers. Supports BoP (**42 BoP biomes** in the code; Alps, Arctic, Wasteland, Crag, Moor, Steppe, Ominous Woods and others are commented out), EBXL (28), Thaumcraft and ChromatiCraft. Has 25 base biomes of its own, including **Redwood**, Redwood Snow, Hot Redwood, Tundra and Polar. | GTNH ships `config/RWG.cfg` with IDs moved to 200–237. [repo](https://github.com/GTNewHorizons/Realistic-World-Gen), [GTNH RWG.cfg](https://github.com/GTNewHorizons/GT-New-Horizons-Modpack/blob/master/config/RWG.cfg) |
| Realistic Terrain Generation (RTG) | RTG-1.7.10-1.1.1.7 (2018-01-18) | None. Development moved to 1.10/1.12. | Not in GTNH; no Hodgepodge or Angelica compat. Java 25 behaviour UNVERIFIED. | Terrain only; adds 0 biomes. Supports BoP, EBXL, Highlands and others. | Superseded on this stack by GTNH's RWG. [CF](https://www.curseforge.com/minecraft/mc-mods/realistic-terrain-generation) |
| Highlands | 2.2.3 (a 1.7.2 build that runs on 1.7.10; 2015-02-20) | None | No patches anywhere. Java 25 UNVERIFIED. | 44 biomes, 14 trees, 256-high mountains; its own world type. | Not supported by RWG. [CF](https://www.curseforge.com/minecraft/mc-mods/highlands) |
| ExtraBiomesXL | 3.16.4 (2016-01-01) | None at GTNH | No patches. Java 25 UNVERIFIED. | About 28–30 biomes, including Redwood Forest, Tundra, Glacier and Ice Wasteland. | RWG supports 28 EBXL biomes. It would duplicate BoP and cost about 30 IDs the pack doesn't have. [CF](https://www.curseforge.com/minecraft/mc-mods/extrabiomesxl) |
| Climate Control / GeographiCraft | 0.8.2 (2016-12-23) | None | EndlessIDs lists it as patched. Nothing else. | **Layout only**: climate zones, continent and ocean sizes, biome frequencies. | Works through vanilla GenLayers, so it does nothing under RWG, which has its own map and a "Climate Distance" setting. It only makes sense with plain `BIOMESOP` and no RWG. [CF](https://www.curseforge.com/minecraft/mc-mods/climate-control-geographicraft) |
| Streams | 0.3.4 (2018-05-26) | None | Needs Farseek API, which is Scala-based (UNVERIFIED on Java 25 + lwjgl3ify). Hooks chunk generation. | Real flowing rivers | High risk; worldgen cost UNVERIFIED. [CF](https://www.curseforge.com/minecraft/mc-mods/streams) |
| Dynamic Trees | **Yes**, 0.7.2c (2017-12-28) | None | Not in GTNH; Angelica behaviour UNVERIFIED. | Growing, choppable vanilla trees only. The BoP add-on exists only for 1.12+ (UNVERIFIED for 1.7.10). | Under RWG and BoP most trees come from RWG and BoP decorators, so the world would look mixed. Adds tile and branch blocks. Skip. [CF](https://www.curseforge.com/minecraft/mc-mods/dynamictrees) |
| Better Foliage (original) | 2.0.17 (2017-11-17) | — | Superseded | Client visuals | Use the Legacy Edition instead. |
| **Better Foliage – Legacy Edition** | **1.2.4 (2026-01-31)** | Maintained fork | States Angelica, SwanSong and OptiFine compat. Changelog fixes Angelica/NotFine seams and invisible leaf sides. Needs UniMixins plus Forgelin: Legacy or GTNH Forgelin. | Client visuals: round logs, bushy leaves, tall grass, algae and so on | Client-only; every feature can be toggled with F8, which suits weak PCs. FPS cost UNVERIFIED. [Modrinth](https://modrinth.com/mod/better-foliage-legacy-edition) |
| Others seen | Natura (GTNH-maintained 2.8.24), Ancient Trees 1.6.4 (2015), ATG 0.12 (2015), Ruins (2017) | | | | Natura is GTNH-maintained and adds trees and nether content, not biomes. Optional. |

GTNH org probe: no GTNH repos exist for BiomesOPlenty, ExtraBiomesXL, Highlands, Streams, BetterFoliage, DynamicTrees or ClimateControl (github.com returned 404). GTNH repos that do exist: Realistic-World-Gen, Viridium, BiomeBridge, TerrainHorizons (pre-alpha "terrain and biome API"), Natura and twilightforest.
Manifests checked: [2.8.4 / 2.9.0-RC-2](https://github.com/GTNewHorizons/DreamAssemblerXXL/tree/master/releases/manifests).

## 2. Biome ID budget

Sources: live configs in `%APPDATA%\.crazycraft4\config`, `javap` of WelcomeToTheJungle's `JungleBiomeRegistry` (hard-coded IDs), the JAS biome-group log in `logs/latest.log`, and commit 699e27e. That commit dumped the live biome table on a dedicated server and moved OreSpawn's IDs.

| IDs | Owner |
|---|---|
| 0–39 | Vanilla. HEE replaces 9, "Sky", with BiomeGenHardcoreEnd. |
| 40–58 | Twilight Forest (19) |
| 67–69 | Welcome to the Jungle: Jungle Mountain, Mangled Swamp, Lost World. **Hard-coded, not configurable.** Used only by its own `WorldTypeJungle`. |
| 90–128, 135–137 | TragicMC (42, Collision/Synapse dimensions) |
| 129–134, 140, 149, 151, 155–158, 160–167 | Vanilla mutated "M" biomes (21) |
| 170–182, 200–203 | 1Legends (17; the config only allows 170–255) |
| 230–234 | OreSpawn (5, BaseBiomeID=230) |
| 255 | Avoid: the chunk biome array uses 0xFF as its "unset" value |

Witchery, Psychedelicraft, Lycanites, TARDIS, Transformers, ChocolateQuest and the others register no biomes; I checked their jars and JAS mappings.

**Free: 108 IDs** — 59–66, 70–89, 138–139, 141–148, 150, 152–154, 159, 168–169, 183–199, 204–229, 235–254.

**Demand**

| Option | IDs needed | Fits? |
|---|---|---|
| BoP (84) + RWG (25) | 109 | 1 short |
| BoP alone | 84 | Yes |
| RWG alone | 25 | Yes |
| + EBXL | about 30 more | No |
| + Highlands | 44 more | No |

How to make BoP + RWG fit:
- Set unused BoP biomes to `-1` in `ids.cfg`; BoP's `createBiome` skips any ID of -1. Under RWG, about 42 of BoP's 84 biomes can never generate: the sub-biomes, the commented-out ones, and the End's Spectral Garden, since HEE owns the End. Disabling a handful gives headroom. Disabling the ones RWG references would throw an NPE, because `SupportBOP` has no null checks. Whether BoP's own code tolerates disabled biomes is UNVERIFIED; boot-test it.
- **Move RWG off 200–203.** RWG's defaults are 200–224, which collide with Legends.
- Under plain `BIOMESOP`, which uses vanilla GenLayers, don't put overworld biomes in the 15 free slots between 129 and 167. GenLayerHills turns biome *k* into *k+128* when that ID exists. RWG doesn't use GenLayers, so this doesn't matter under RWG.
- The qf-content login check refuses clients whose ID configs differ, so the BoP and RWG configs must ship in the pack.

**EndlessIDs** (FalsePattern/GTMEGA, 1.7.4 on 2026-05-30): raises the biome limit to 65,536. It needs FalsePatternLib, ChunkAPI and UniMixins. **GTNH 2.9.0-RC-2 ships it**, and Hodgepodge and Angelica both have EID compat code. Its patch list covers BoP, RWG, Highlands, Climate Control, JAS, Twilight Forest, Witchery and Compact Machines. **It does not cover TragicMC, OreSpawn, 1Legends, Welcome to the Jungle, HEE, Lycanites, TARDIS or MCHeli.** Its README warns that custom world generators calling the old vanilla biome-array method hit "an instant crash", and the pack has many custom dimensions. It also changes the world format and recommends AntiIDConflict. **Verdict: not viable now**, and not needed if the IDs are trimmed. Reconsider it only after a trial shows every dimension generates. [EndlessIDs](https://github.com/GTMEGA/EndlessIDs), [Modrinth](https://modrinth.com/mod/endlessids)

## 3. Interactions with the current pack

**JustAnotherSpawner** is the biggest job. Its config has "Empty vanilla spawnlists" and "Disable Vanilla Chunk Spawning" on, with tables sorted by biome *name*.
- Every new biome needs spawn entries: about 42 BoP plus 25 RWG.
- Under RWG, vanilla-named groups such as Plains, Desert and Taiga barely occur. Today's vanilla-keyed tables, and the danger tuning in them, would effectively stop applying.
- JAS attribute groups (BiomeDictionary types) can cover most of this: RWG and BoP both register dictionary types.
- Name clashes: BoP "Arctic" vs Legends "Arctic", and RWG "Oasis" vs BoP "Oasis". JAS gives the duplicate a package prefix, as it already does for `tragicneko.Dark Forest`.
- Best path: let JAS regenerate the biome mappings in a trial world, then re-apply the pack's edits. How JAS imports entries for biomes added to an existing config is UNVERIFIED.

**Lycanites:** spawns by BiomeDictionary tags (for example `COLD, SNOWY, CONIFEROUS, -END`), so it picks up typed BoP and RWG biomes automatically. Its spawns still pass through JAS for the MONSTER and CREATURE types.

**Structure mods:** these mostly use BiomeDictionary types, so they are fine with BoP and RWG.
- Roguelike uses types.
- Doomlike uses `NeverInBiomeTypes`.
- Recurrent Complex uses `universalBiomeMatcher` and per-structure expressions.
- ChocolateQuest uses `biomes = PLAINS, FOREST, …` types.
- They generate through IWorldGenerator, which still runs under RWG.
- **Under RWG, vanilla scattered features (desert and jungle temples, witch huts) don't generate.** Its generator only creates caves, stronghold, mineshaft and village.
- OreSpawn's overworld mob and structure hooks may check vanilla biome identities. UNVERIFIED; check in a trial.

**Chunk Pregenerator:** works with any world type. Hodgepodge's `unboxMapGen` must stay false (already documented). Measure worldgen cost: RWG plus BoP decoration is heavier than vanilla, and there are no published 1.7.10 numbers (UNVERIFIED). Use the existing pregen harness and compare chunks/s for vanilla, BIOMESOP and RWG.

**World type:** RWG, BIOMESOP and Welcome to the Jungle's world type are mutually exclusive. With `level-type=rwg`, the Jungle mod's three biomes only exist in its dimension or world type. `tools/server/build_play_server.py` and the client's default world type must set it.

**Ore survey:** changing the overworld generator invalidates the overworld ore survey, as with the OreSpawn ID move.

**Client memory:** BoP adds many block and item textures. The block atlas is already 2048², so it may grow to 4096×2048 (UNVERIFIED), which costs VRAM on friends' GPUs. The heap increase is unmeasured; the current live heap is 1.3 GB at 3 GB.

## 4. Recommendation

**Combination**

| Role | Choice |
|---|---|
| Terrain + layout | **GTNH Realistic World Gen alpha-1.5.2**, `level-type=rwg` |
| Biomes | **Biomes O' Plenty 2.1.0.2308**, all IDs pinned, unused BoP biomes set to −1 |
| Foliage | **Better Foliage – Legacy Edition 1.2.4** (client) + Forgelin: Legacy |
| Already planned | Hodgepodge with its BoP fixes on (defaults), Angelica |

Do not add EndlessIDs, EBXL, Highlands, RTG, Climate Control, Streams or Dynamic Trees.

This covers the brief:
- **Redwood forests:** RWG's Redwood, Redwood Snow, Hot Redwood and Redwood Jungle, plus BoP's Redwood Forest.
- **Desolate cold:** RWG Polar, Tundra Plains and Tundra Hills, plus BoP Tundra and Frost Forest.
- **Variety and danger:** many distinct biomes, with danger set per biome through JAS weights and Lycanites tags.

Under RWG, BoP Alps, Wasteland and Arctic don't generate. If those matter more than RWG's terrain, the fallback is BoP's own `BIOMESOP` world type, optionally with Climate Control for layout. That gives vanilla-style terrain but all 84 BoP biomes.

**Risks, highest first**
1. **Vanilla biome identities disappear under RWG.** JAS tables, vanilla temples and huts, and any vanilla-biome checks (OreSpawn and others) break or vanish. Mitigation: retable JAS by type and audit in a trial world.
2. **ID budget is one short, and RWG's defaults collide with Legends 200–203.** If a disabled BoP biome is still referenced, the game crashes with an NPE. Mitigation: pin every ID, boot-test, and use the live biome-table dump as done in 699e27e.
3. **Worldgen speed and server load on weak hosts are unmeasured.** Mitigation: benchmark pregen chunks/s in a trial (RWG got a 2026 optimisation pass).
4. **Client VRAM and heap growth from BoP textures and Better Foliage on weak PCs.** Mitigation: measure the atlas size and live heap with the existing harness; ship Better Foliage with conservative defaults.
5. **Combined trial needed.** Neither BoP nor RWG has been tested with TF 2.4.3 (non-GTNH), TragicMC, OreSpawn or Legends dimensions on Java 25. They probably don't interact, since those mods own separate dimensions, but this needs one combined trial through `tools/trial/trial.py`.
6. **Ore survey and JAS re-tuning work** must be redone after the switch.
