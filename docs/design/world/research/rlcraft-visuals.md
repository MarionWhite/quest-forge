# What makes RLCraft's world look good, and what 1.7.10 can match

Research only; nothing in the repo was changed. Date: 2026-10-17. **[unverified]** marks claims without a primary source.
This complements `docs/design/world/research/biomes.md` and `ambience.md`, and does not repeat them.

## TL;DR

1. **RLCraft does not use Biomes O' Plenty at all.** The v2.9.3 manifest has 197 relations on CurseForge, and none of them is BoP. Its "unique trees" are **Dynamic Trees**, which turns vanilla, Traverse and Defiled Lands trees into growing, branching trees. Its biomes are vanilla plus **Traverse Reforged**, **Defiled Lands** and **BetterNether**. The terrain is vanilla or **RTG**. Better Foliage, Serene Seasons, Dynamic Surroundings, Fancy Block Particles, Snow! Real Magic!, Chunk Animator and five "Animated and Emissive" resource packs add the polish on top.
2. **The "masterfully crafted, 300–800 biomes" videos are very likely RLCraft *Dregora*** **[unverified that the author watched it]**. That is a separate 1.12.2 pack (v1.0.0 2024-10-18, v1.1.2b 2025-12-02) whose world is a hand-authored **OTG preset**. It has "800+ biomes" and "20000 biome objects including custom trees, rocks, caves…", and it **uses BoP blocks** to dress its biomes. In other words it is the same recipe as our WorldPainter plan: BoP blocks plus a large hand-made object library. It is not procedural BoP.
3. **BoP 2.1 for 1.7.10 is not content-poorer than BoP 7.x for 1.12. It has more biomes.** The 1.12 version is a cleaner rewrite with parametrised generators and fewer hand-coded tree shapes. The visual gap to RLCraft comes from Dynamic Trees, the foliage and particle mods, the resource packs, shaders and, in Dregora, the object library. It does not come from the BoP version.
4. **1.7.10 equivalents exist for most of the polish:**
   - Better Foliage Legacy (Angelica-aware).
   - An unofficial Serene Seasons 1.7.10 port on the official Modrinth project.
   - Dynamic Surroundings (mist475 fork).
   - Sound Physics (lwjgl3ify fork).
   - Dynamic Trees 1.7.10 0.7.2c, but vanilla species only, with no BoP add-on.

   These have no 1.7.10 build: Traverse, Defiled Lands, Ice and Fire, Fancy Block Particles, Chunk Animator, Snow! Real Magic!, Better Biome Blend and the YUNG mods.
5. **The biggest lever is WorldPainter Custom Object layers fed with a curated tree and rock library.** Pre-1.13 `.schematic` files that use only vanilla blocks drop straight into a 1.7.10 Anvil export. Modded blocks in objects need numeric IDs that match *this* world's FML ID map. Most modern tree packs on sale target 1.13+ and need checking before use.

---

## 1. RLCraft 2.9.3: what shapes its look

Source: the [v2.9.3 file relations](https://www.curseforge.com/minecraft/modpacks/rlcraft/files/4612979/dependencies), all 10 pages read. The file is RLCraft 1.12.2 Release v2.9.3, dated 2023-06-27 and still the latest per [cfwidget](https://api.cfwidget.com/minecraft/modpacks/rlcraft). Exact mod versions are not shown on the relations page **[unverified per-mod versions]**.

| Role | Mods in v2.9.3 |
|---|---|
| Biomes | **Traverse Reforged** (new overworld biomes: autumnal woods, canyons, cliffs, rolling hills and so on, roughly 20 **[unverified count]**), **Defiled Lands** (corrupted biomes), **BetterNether**. **No BoP.** |
| Terrain | **Realistic Terrain Generation** is shipped. The stock pack's default world type is vanilla, and the pack recommends Large Biomes. The semi-official ["HARDCORE Config v1" for 2.9.3](https://www.curseforge.com/minecraft/modpacks/rlcraft/files/4613113) switches the default type to RTG: "The default world type will now use Realistic Terrain Gen, so Large Biomes is no longer required." **Better Biome Blend** (added in 2.9.2) smooths colour seams between biomes. |
| Trees | **Dynamic Trees**, **Dynamic Trees – Traverse**, **Dynamic Trees – Defiled Lands**. DT was updated in 2.9.2. |
| Seasons and weather | **Serene Seasons** (seasonal foliage tint, snow), **Snow! Real Magic!** (snow layers on plants and slabs), **Tumbleweed**, **Bloodmoon**. |
| Foliage, particles, ambience | **Better Foliage**, **Fancy Block Particles** (3D break particles), **Dynamic Surroundings** with its HUDs, **Sound Filters**, **Chunk Animator** (chunks slide in), **ItemPhysic Full**, **Realistic Torches**, **EnhancedVisuals**, **CoralReef**, **Particle Culling**, **Entity Culling**. |
| Structures | **Battle Towers**, **Recurrent Complex** (RLCraft's custom structure set), **Roguelike Dungeons (Fnar's Edition)**, **Doomlike Dungeons**, **Ruins**, **Ice and Fire** (dragon roosts and caves), **Lycanites Mobs** (lairs), **The Lost Cities**, **YUNG's Better Caves**, **YUNG's Better Mineshafts**, **Waystones** (shrines). |
| Resource packs (shipped) | **AnimEmis RL** plus four "Animated and Emissive" packs (Ice and Fire/Spartan, Scape and Run weapons, Defiled Lands, Forgotten Items). These are OptiFine CTM/emissive item and mob textures, not landscape textures. |
| Shaders | **None shipped.** OptiFine HD U G5 is required, and the page recommends "some shaders if your system can handle them". The author built the pack using the **Chroma Hills** resource pack, and the author's own shader and texture combo is pinned in the Discord ([cfwidget description](https://api.cfwidget.com/minecraft/modpacks/rlcraft)). |

**Pack beauty versus shader beauty.** A stock RLCraft world is vanilla blocks and textures in vanilla, Traverse and Defiled Lands biomes, with DT trees, Better Foliage and seasonal tint. Anything with soft shadows, waving leaves, volumetric light, reflective water or a painterly texture look is OptiFine shaders plus a third-party resource pack such as Chroma Hills. RLCraft requires OptiFine and the author recommends shaders, so recorded footage with shaders is plausibly the norm. **I found no source that measures how common shader footage is [unverified]**, and the guides I found (e.g. [space-node](https://space-node.net/blog/rlcraft-shaders-performance-guide-2026)) are SEO-grade. Practical test: if a clip shows shadows that move with the sun, or waving grass while Better Foliage is off, it is a shader.

**RLCraft Dregora** ([cfwidget](https://api.cfwidget.com/minecraft/modpacks/rlcraft-dregora), [Dregora RL world mod](https://www.curseforge.com/minecraft/mc-mods/dregora-rlc)):
- 1.12.2 pack by NLBlackEagle; the world mod is DregoraRL-3.9.2 (2026-10-03).
- "Custom world generator… powered by OTG", 300+ biomes per the pack page and "800+" per the mod page, plus "20000 biome objects including custom trees, rocks, caves, huge dungeons, villages".
- "Integrates Biomes O' Plenty blocks to diversify the redesigned biomes".
- Lineage: it grew from a Terrain Control world for the Ancient Realms server, started in 2013.
- Whether Dregora keeps Dynamic Trees or replaces it with OTG object trees is **[unverified]**.

If the videos showed hand-placed-looking giant trees, rock spires and dense ground clutter, that is Dregora's object library.

## 2. BoP 7.x (1.12) versus BoP 2.1 (1.7.10)

Counts come from the source trees on GitHub, branches [`BOP-1.7.10-2.1.x`](https://github.com/Glitchfiend/BiomesOPlenty/tree/BOP-1.7.10-2.1.x) and [`BOP-1.12.x-7.0.x`](https://github.com/Glitchfiend/BiomesOPlenty/tree/BOP-1.12.x-7.0.x).

| | 1.7.10 (2.1.0) | 1.12.2 (7.0.x) |
|---|---|---|
| Biomes | About 84: 59 overworld, 16 sub-biomes, 2 rivers, 6 Nether, 1 End. This matches `biomes.md`. | 63 overworld classes and 5 Nether. No sub-biome system, no End biome. |
| Only in this version | Arctic, Canyon (and Canyon Ravine), Deciduous Forest, Dense Forest, Frost Forest, overworld Fungi Forest, Garden, Heathland, **Jade Cliffs**, Sludgepit, Thicket, Polar Chasm, **Silkglades**, Spruce Woods, Alps Forest, Meadow Forest, Scrubland, Seasonal Forest Clearing, Tropics, Volcano, Dry River, Lush River, Spectral Garden (End), Boneyard (Nether) | Cold Desert, Flower Island, Gravel Beach, **Overgrown Cliffs**, Pasture, Snowy Forest, Tropical Island, **Volcanic Island**, White Beach, Origin Beach and Island |
| Tree generation | About 32 hand-written `WorldGen*` classes. Examples: Redwood ×3, Bayou ×3, Bog ×2, Taiga ×3, Poplar ×2, Sacred Oak, Cypress, Bulb, Mangrove, Palm, Rainforest, Giant Flower. | 17 parametrised `Generator*` classes: Basic, Big, Huge, Bush, Taiga, Pine, Redwood and RedwoodThin, Mahogany, Mangrove, MegaJungle, Palm, Bayou, Bulb, Twiglet, Profile, Logs. |
| Customisation | Java only, plus ID and config files | Per-biome generator settings can be edited in JSON config **[unverified scope]** |
| Block textures | 413 files | 344 files |

**Verdict.** The 1.12 version is a rewrite, not a visual upgrade. The tree catalogue is similar in kind (redwoods, mahogany, cypress and bayou trees, palms, poplars, sacred oaks). Several 1.7.10-only biomes that look striking, such as Jade Cliffs, Silkglades, Canyon, Volcano and Sacred Springs, were dropped or changed later. Whether 1.12's trees have more natural silhouettes is **[unverified]**: I found no side-by-side screenshots. The rewrite mostly cleaned up generation code.

What 1.7.10 BoP really lacks against RLCraft:
- Dynamic Trees integration (there is no 1.7.10 DT-BoP add-on).
- Better Biome Blend.
- Fancy Block Particles.

## 3. 1.7.10 equivalents for RLCraft's ingredients

| RLCraft ingredient | 1.7.10 option | Status and notes |
|---|---|---|
| Dynamic Trees | [DynamicTrees-1.7.10-0.7.2c](https://api.cfwidget.com/minecraft/mc-mods/dynamictrees) (2017-12-28); source branch [`release/1.7.10`](https://github.com/DynamicTreesTeam/DynamicTrees/tree/release/1.7.10) | Vanilla species only (Oak, Birch, Spruce, Jungle, Acacia, Dark Oak). Its only compat code is for ComputerCraft. It hooks the vanilla decorate-tree event, so whether it replaces RWG or BoP trees is **[unverified]** and probably mixed (see `biomes.md`). **No BoP add-on for 1.7.10**: [DT-BoP](https://api.cfwidget.com/289529) starts at 1.12.2 alpha 1 (2018-03-05). Angelica and Java 25 behaviour **[unverified]**. Not recommended. |
| Serene Seasons | **[SereneSeasons-1.7.10-1.2.18](https://modrinth.com/mod/serene-seasons)**, published 2023-11-19 on the official Modrinth project: "1.7.10 port courtesy of DarkShadow44… not officially supported." | Seasonal grass and foliage tint. Interaction with BoP and RWG colour handlers, Angelica and shaders is **[unverified]**. Worth a slim trial. |
| Better Foliage | **[Better Foliage – Legacy Edition](https://modrinth.com/mod/better-foliage-legacy-edition)** | Already covered in `biomes.md` and `ambience.md`. Its changelog has Angelica fixes. A shader needs `separateAo=false`. |
| Dynamic Surroundings | [mist475 fork](https://modrinth.com/mod/dynamic-surroundings-unofficial-1.7.10) (2026-09-30) | Covered in `ambience.md`; it conflicts with shader rain (Angelica #1524). |
| Sound Filters | [Sound Physics 1.7.10 Mixin Edition](https://modrinth.com/mod/sound-physics-1.7.10-mixin-edition) | "Fixes compatibility with lwjgl3ify", but it is not maintained. It conflicts with MAtmos (per `ambience.md`). |
| Fancy Block Particles, Chunk Animator, Snow! Real Magic!, Better Biome Blend, Tumbleweed | None found on Modrinth's 1.7.10 facet | [An Extra Touch](https://modrinth.com/mod/an-extra-touch) backports some Dynamic Surroundings-style visual touches. |
| Traverse and Defiled Lands biomes | None (1.10+). BoP 2.1 plus RWG covers the same autumn, cliff and canyon themes. | Defiled-style corrupted land could be painted with WorldPainter. |
| Structures | Battle Towers and Ruins (archived 1.7.10 jars), Recurrent Complex (1.7.10 exists), Roguelike Dungeons (**GTNH-maintained**, pushed 2026-10), Doomlike Dungeons (1.7.10 build **[unverified]**), Lycanites (has 1.7.10) | Ice and Fire, Lost Cities and the YUNG mods have no 1.7.10 builds. |
| Terrain | GTNH [Realistic-World-Gen](https://github.com/GTNewHorizons/Realistic-World-Gen), plus a GTNH [Realistic-Terrain-Generation](https://github.com/GTNewHorizons/Realistic-Terrain-Generation) fork (pushed 2026-07) | The RTG fork is new information compared with `biomes.md`, which calls RTG dead. Its status and branch are **[unverified]**; check before ruling it out. |
| BoP rewrite | GTNH [BiomeBridge](https://github.com/GTNewHorizons/BiomeBridge) | Stalled: last commit 2024-02-04, only config scaffolding. |
| Water tint | [biome-water-backport](https://modrinth.com/resourcepack/biome-water-backport) resource pack | Needs MCPatcher or OptiFine custom colours. Angelica support **[unverified]**. |
| Painted biome layout | [Painted Biomes](https://modrinth.com/mod/painted-biomes) (has a 1.7.10 build) | An image sets the biome map. It is an alternative to stitching WorldPainter biomes if RWG's biome map gets in the way **[unverified with RWG]**. |
| Shaders and resource pack | Our own shader under Angelica, plus our own texture pack | This is the equivalent of RLCraft's recommended shader plus Chroma Hills. |

## 4. Beyond mods: what hand-built maps do, and how to do it in WorldPainter

Professional WorldPainter or Gaia-style maps get their look from three things:
- **Custom object layers.** Hundreds of tree, bush, rock and fallen-log variants are painted at mixed densities. Large "hero" trees go at edges and clearings.
- **Ground-cover layering.** Several materials are mixed per terrain type: coarse dirt, podzol, gravel, moss and grass by slope and height, using WorldPainter's Mixed Material and Custom Terrain.
- **Composition.** Sight lines, landmarks on ridgelines, and tree-line breaks at biome borders.

None of this needs a mod. Every placed object is plain blocks in the save.

**WorldPainter mechanics** ([Custom Objects wiki](https://www.worldpainter.net/trac/wiki/CustomObjects), [Custom Blocks wiki](https://www.worldpainter.net/trac/wiki/CustomBlocks)):
- Formats: `.schematic` (MCEdit, pre-1.13 numeric IDs, which is the native fit for 1.7.10), `.bo2`, `.bo3`, `.nbt` (structure block) and `.schem` (Sponge).
- Painting: one Custom Object layer holds many objects, each with a relative frequency. You paint intensity to set density. Objects are randomly rotated and mirrored by default.
- bo2/bo3 limits: only `spawnWater`, `spawnLava`, `needsFoundation` and `randomRotation` are honoured, and "WorldPainter does *not* support groups or branches". Dregora-style branching bo3 structures therefore will not reproduce; flat single-piece bo3 trees will.
- Modded blocks in 1.12-or-older maps are addressed as `legacy:block_<id>` with `data_value=<n>`, through a custom-materials `.csv`. The `.csv` does not travel with the `.world` file, and WorldPainter will not light these blocks correctly.
- For 1.7.10 this means modded IDs (e.g. BoP logs and leaves) must equal the numeric IDs in **this pack's FML registry**. Dump them from a server trial, much like WP-D0 in `quests.md`. Mods that pin IDs in config keep them stable **[unverified for BoP blocks; 1.7.10 Forge assigns block IDs per world and persists them in level.dat]**.
- Modern `.nbt` and `.schem` objects use 1.13+ block names. Whether WorldPainter down-converts them to legacy IDs on a 1.2–1.12 export, and what it does with blocks that do not exist yet (e.g. stripped logs), is **[unverified]**. Expect missing or replaced blocks, and prefer `.schematic` sources.

**Tree and object libraries:**

| Library | Format and version fit | Cost |
|---|---|---|
| Lentebriesje, "Custom Tree Repository" / [Native Trees of Europe template repository](http://www.planetminecraft.com/project/native-trees-of-europe-template-repository-1779952/), linked from the WorldPainter wiki | 2013-era MCEdit `.schematic`, vanilla blocks, so it fits 1.7.10 directly **[contents unverified; Planet Minecraft returned 403]** | Free |
| ["treepack" on Planet Minecraft](https://www.planetminecraft.com/project/treepack-3095300/) (2016) | Says it is for WorldPainter, MCEdit, or WorldEdit on 1.7 and lower | Free |
| [ULTIMATE Tree Repository, 300+ schems](https://builtbybit.com/resources/ultimate-tree-repository-over-300-schems.31286/history) | Targets 1.19–1.20, so it needs conversion and has block-palette loss | $19.99 |
| [Essential Trees (Conquest Reforged)](https://www.conquestreforged.com/showcase/essential-trees); [essentialschematics](https://essentialschematics.gumroad.com/l/mossyivydeciduoussmall) and [stellardweller](https://stellardweller.gumroad.com/l/rwdab) on Gumroad | Prepared for WorldPainter with rotations, but modern (1.13+, some 1.18+) and some use Conquest blocks | Paid |

Practical fit for Quest Forge:
- Prefer pre-1.13 `.schematic` vanilla-block libraries.
- Re-skin them with BoP woods and leaves through a batch block-replace at the numeric-ID level. Do this only after pinning IDs.
- Or build a small house library of signature trees and rocks per region in a 1.7.10 creative world, and export them with MCEdit 1.x or Schematica.
- A two-tier mix is cheap: dense object forests near quest hubs and landmarks, and RWG/BoP procedural decoration in the outskirts.
- On weaker PCs, object-heavy chunks cost the same as normal blocks. There is no tile-entity cost unless objects contain chests or signs.

## Sources
- RLCraft: [v2.9.3 file](https://www.curseforge.com/minecraft/modpacks/rlcraft/files/4612979), [relations](https://www.curseforge.com/minecraft/modpacks/rlcraft/files/4612979/dependencies), [cfwidget](https://api.cfwidget.com/minecraft/modpacks/rlcraft), [Hardcore config](https://www.curseforge.com/minecraft/modpacks/rlcraft/files/4613113)
- Dregora: [pack (cfwidget)](https://api.cfwidget.com/minecraft/modpacks/rlcraft-dregora), [Dregora RL](https://www.curseforge.com/minecraft/mc-mods/dregora-rlc), [Shockbyte](https://shockbyte.com/modpacks/rlcraft-dregora)
- BoP source: [GitHub branches](https://github.com/Glitchfiend/BiomesOPlenty)
- DT: [cfwidget](https://api.cfwidget.com/minecraft/mc-mods/dynamictrees), [GitHub](https://github.com/DynamicTreesTeam/DynamicTrees), [DT-BoP](https://api.cfwidget.com/289529)
- Modrinth API (searched with the 1.7.10 facet); GTNH org repo listing via the GitHub API
- WorldPainter: [Custom Objects](https://www.worldpainter.net/trac/wiki/CustomObjects), [Custom Blocks](https://www.worldpainter.net/trac/wiki/CustomBlocks)
