# Modded blocks: which ones players see, and how to texture them (2026-10-25)

QF Textures v0 ([direction.md](direction.md) section 4) covers vanilla only. The pack registers
**2,427 blocks, 2,256 of them modded**, drawn from **5,551 modded block textures** with pixels across 65 resource
domains in 117 jars (the generator's full run also covers vanilla's 349 and 47 blank ones, 5,947
in all). This note ranks
those blocks by how often a player sees them, pairs each with the texture files it draws, sets the
style rules per family, and records the first generated LabPBR build for them. The ranking is
`docs/design/textures/modded-blocks.tsv` (every modded block, one row), written by
`tools/textures/rank_modded_blocks.py`.

Tags: **[verified]** = checked in a jar, config, file or measurement named here; **[guess]** = a
judgement or a reading of names; **[estimate]** = a number this note made up from a stated rule.

## 1. Method

Four signals per block, each scaled 0–10, summed with fixed weights:

```
score = 0.45 W (worldgen) + 0.20 C (crafts) + 0.25 B (base) + 0.10 Q (quests)
```

**W, worldgen presence.** Measured, not inferred. The ore survey kept its region files
(`C:\qfs\scan-n1..4.json`: 4 seeds, 30 dimensions, 4.78 M populated chunks, the live mod set of
2026-09-10, `docs/survey/README.md`), and the scans count **every** block in them, not only ores:
biome terrain, trees, Chisel's marble and limestone veins, dungeon walls, Twilight's deadrock, the
Collision's dark stone. Decision 0002 discarded the survey's *absolute* ore numbers for the old
instrument's faults; these scans are the replacement instrument, and relative frequencies are all
the ranking needs [verified: `pack/reports/README.md`]. The per-block, per-dimension rates and mean
heights are committed as `data/worldgen-modded.tsv` (2,154 rows), so the ranking reruns without
`C:\qfs`.

Per block: variants (metadata) are summed first (Railcraft's eleven ores are one block to the
eye), then for each dimension `v_d × log10(1 + blocks/chunk) × exposure`, where exposure is 1.5
when the block's mean Y is within 12 of the dimension's ground level (it is seen from the surface)
and 1.0 otherwise. The dimension weights are a judgement from the quest book [guess]:

| dim | weight | why |
|---|---|---|
| 0 Overworld | 1.0 | everything starts here |
| 7 Twilight Forest | 0.8 | chapter 3, 93 quest mentions, the only `location` task |
| -1 Nether, 1 End | 0.5 | vanilla progression; HEE's End is chapter 6 |
| 2 Collision, 3 Synapse | 0.35, 0.3 | TragicMC chapter 8, 34 mentions |
| 84 OreSpawn Crystal | 0.25 | a quest sends players there |
| -37 Dream (Witchery), 58 DIM 54 | 0.15 | Spirit World quests; Legends' richest dimension |
| 80–85 OreSpawn dims, -42 Lost World | 0.1 | reachable, no quests |
| 30–36, 51, 53, 66 Legends dims | 0.08 | reachable, no quests |
| 50, 55, -38, -39 | 0.03–0.05 | near-empty or instanced |
| 4 Compact Machines | 0 | its walls are scored as base blocks instead |

W saturates at a reference of "100 blocks per chunk at the Overworld surface" (W_REF = 3.0).

**Biomes O' Plenty** is not in the scans (it is on the world-design server, not the live client:
`C:\qfs\v0\mods`, `level-type=BIOMESOP` [verified]). Its terrain blocks get an **[estimate]**: the
script reads which `BOPCBlocks` fields each of the 100 biome classes references from the jar's
constant pools [verified], weights each biome by its share of the continent plan
(`docs/design/world/continent-v4.yaml`, 63 BoP/RWG biomes), and assigns per-field rates
(`BOP_FIELD_RATE`: a terrain block 2,500/chunk in its biome, leaves 300, logs 60, foliage 40,
gem ore 2.5). Crag (plan weight 24, `cragRock`), Alps (16, vanilla stone and snow), Volcano (15,
`ashStone`), Glacier (11, `hardIce`), Wasteland (6, `driedDirt`), Canyon (3, `hardDirt`) and
Outback (2, `hardSand`) are the BoP terrains that matter. RWG adds no blocks of its own
[verified: no `rwg` texture domain in its jar].

**C, craft frequency.** From the item dump (`site/items/data/recipes.json`: 6,386 crafting and
217 furnace recipes, ore dictionary expanded): `log2(1 + min(out, 16)) + 0.5·log2(1 + min(in,
64))`, out = recipes producing the block, in = recipes using it. Recipes whose output block is also
an input (lamp + dye → lamp) are skipped: BiblioCraft registers 258 such recolours per lamp.
Reference C_REF = 7.1 (16 recipes out, 64 in).

**B, base and machine blocks.** A hand table by mod and name (`BASE` in the script) [guess]: tier
3 for what nearly every base has and looks at daily (ender chest, iron chests, drawers, Compact
Machines, ProjectE's table/condenser/collectors/relays), tier 2 for machine rooms and common
decoration (Railcraft machines, bricks, posts and tracks; Witchery's altar, cauldron, oven,
distillery, planks; BiblioCraft; Chisel's building stones; Legends' workstations; qf-content),
tier 1 for the rest of the decorative mods.

**Q, quest mentions.** `site/items/data/items.json` `qrefs`: a task counts 3, an icon 1, a reward
0.5, capped at 10. The book barely asks for modded *blocks*: 529 task references in total, and
the modded block tasks are Witchery's altar, cauldron, oven, distillery, poppet shelf and kettle,
an iron chest, a drawer, the transmutation table, a Railcraft tank, SecurityCraft's keypad and
laser, SSTOW's soul cage, HEE's death flower and OreSpawn's Mobzilla scale block [verified].

**Textures.** Each creative stack (`block@meta`, 5,726 of them) is paired with a file under
`assets/<domain>/textures/blocks/` two ways, combined: by name (registry name, display name and
unlocalised name against the file name) and by colour: the item dump's 32 px inventory icon is
the block as an isometric cube, and its mean colour is **0.665 ×** the texture's mean (measured
on vanilla stone, 83.7 vs 125.4, and gold ore, 95.2 vs 143.5 [verified]). Confidence per stack:
high 1,881, mid 295, low 279 (a cube icon), name-high 697, name-mid 914, none 1,352 (no cube
icon: a model, a flat item, a fluid), no block textures in the domain at all 308 (BiblioCraft's
models, Decocraft, MrCrayfish, EnderStorage). Blocks the matcher cannot see or gets wrong are in
`OVERRIDES`, hand-checked against the jar listings: Twilight's logs, leaves and dungeon blocks,
Railcraft's slabs, stairs, walls and tracks, the BoP group blocks (no creative stacks), Legends'
"dynamic" blocks, TragicMC's ore and dark-stone variants, HEE's End blocks. Which metadata uses
which file is from the mods' names and the known block orders [guess] unless the TSV says
"verified"; the file names themselves are [verified].

**Not determined.** (1) Structure palettes: ChocolateQuest's `.schematic`s and Roguelike's code
place vanilla blocks; Doomlike's themes (`pack/config/DLDungeonsJBG/themes`) are vanilla except
`minecraft:stained_hardened_clay`; Recurrent Complex's 106 shipped structures use vanilla blocks
and its own `negativeSpace`/`naturalFloor` markers [verified by scanning the configs and jar].
Their blocks are therefore vanilla and outside this ranking; the modded dungeon blocks that do
appear (Twilight's mazestone, towerwood, castle brick, knight brick; HEE's ravaged brick) are in
the scans. (2) Legends' six prebuilt-map dimensions (Korriban, Tatooine, Tython, Outer Space,
Kingpin, DIM 54) are measured as shipped. (3) Mob-spawn blocks (`OreSpawn:*SpawnBlock`,
`legends:dynamic*` with no name) are ranked but are not worth art. (4) Dimension weights, base
tiers and BoP rates are judgements, stated above; change them in the script and rerun.

### Rerun

```
py -3.10 -I tools/textures/rank_modded_blocks.py --only C:\qfb\textures\top-modded.txt --top 150 \
    --sheet C:\qfb\textures\sheet-modded-top.png
```

24 s with the scans present (they refresh `data/worldgen-modded.tsv`); it writes the TSV, the
`--only` list for `gen_surface_pack.py` (434 texture paths for the top 150) and a contact sheet.

## 2. The ranking: top 150, grouped by mod

Global rank and score; W/C/B/Q as above; **icon** = yes when the inventory icon is the block's
own cube, so a texture change shows in the inventory and on the item index (after an item-dump
rebuild; 93 of the 150 are such cubes); textures in the order of the strongest worldgen variant first, tagged [v] verified or
high-confidence, [m] mid, [g] guess, [?] no pairing, [vanilla] draws a vanilla texture,
[missing] no such file. The full list of 2,256 is the TSV.

### Railcraft (22 of its 36 blocks in the top 150; best rank 1)

| # | score | block | names (first 3) | W | C | B | Q | icon | textures (inside `assets/<mod>/textures/blocks/`) |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 7.30 | `Railcraft:cube` | Abyssal Stone / Block of Coal Coke / Block of Concrete | 8.36 | 9.34 | 6.67 | 0.00 | yes | cube.stone.abyssal [v]; cube.stone.quarried [v]; cube.coke [v]; cube.copper [v]; cube.tin [v] … |
| 7 | 5.70 | `Railcraft:ore` | Dark Diamond Ore / Dark Emerald Ore / Dark Lapis Lazuli Ore | 10.00 | 1.82 | 3.33 | 0.00 | yes | ore.poor.iron [v]; ore.poor.lead [v]; ore.poor.copper [v]; ore.poor.tin [v]; ore.poor.gold [v] … |
| 31 | 3.61 | `Railcraft:slab` | Abyssal Block Slab / Abyssal Brick Slab / Abyssal Cobble Slab | 0.00 | 9.73 | 6.67 | 0.00 | no | brick.abyssal [v]; brick.bleachedbone [v]; brick.bloodstained [v]; brick.frostbound [v]; brick.infernal [v] … |
| 32 | 3.58 | `Railcraft:machine.beta` | Anchor Sentinel / Commercial Steam Engine / High Pressure Boiler Tank | 0.00 | 7.58 | 6.67 | 4.00 | yes | engine.steam.hobby [v]; tank.iron.wall [v]; tank.iron.gauge [v]; tank.iron.valve [v]; tank.steel.wall [v] … |
| 50 | 3.21 | `Railcraft:detector` | Detector - Advanced / Detector - Age / Detector - Animal | 0.00 | 7.73 | 6.67 | 0.00 | yes | detector.item [v]; detector.any [v]; detector.empty [v]; detector.mob [v]; detector.powered [v] … |
| 59 | 3.04 | `Railcraft:machine.alpha` | Admin Anchor / Automated Steam Trap / Blast Furnace Brick | 0.00 | 6.87 | 6.67 | 0.00 | yes | rolling.machine [v]; coke.oven [v]; blast.furnace [v]; steam.oven [v]; tank.water [v] … |
| 61 | 3.03 | `Railcraft:post` | Metal Platform / Metal Post / Stone Platform | 0.00 | 6.82 | 6.67 | 0.00 | no | post.wood [v]; post.metal [v] |
| 62 | 3.00 | `Railcraft:brick.abyssal` | Abyssal Block / Abyssal Brick / Abyssal Cobblestone | 0.00 | 6.66 | 6.67 | 0.00 | yes | brick.abyssal [v] |
| 63 | 3.00 | `Railcraft:brick.bleachedbone` | Bleached Bone Block / Bleached Bone Brick / Bleached Bone Cobblestone | 0.00 | 6.66 | 6.67 | 0.00 | yes | brick.bleachedbone [v] |
| 64 | 3.00 | `Railcraft:brick.bloodstained` | Blood Stained Block / Blood Stained Brick / Blood Stained Cobblestone | 0.00 | 6.66 | 6.67 | 0.00 | yes | brick.bloodstained [v] |
| 65 | 3.00 | `Railcraft:brick.quarried` | Etched Quarried Stone / Fitted Quarried Stone / Ornate Quarried Stone | 0.00 | 6.66 | 6.67 | 0.00 | yes | brick.quarried [v] |
| 66 | 2.98 | `Railcraft:brick.infernal` | Etched Infernal Stone / Fitted Infernal Stone / Infernal Block | 0.00 | 6.56 | 6.67 | 0.00 | yes | brick.infernal [v] |
| 67 | 2.96 | `Railcraft:brick.sandy` | Etched Sandy Stone / Fitted Sandy Stone / Ornate Sandy Stone | 0.00 | 6.48 | 6.67 | 0.00 | yes | brick.sandy [v] |
| 68 | 2.94 | `Railcraft:brick.frostbound` | Etched Frost Bound Stone / Fitted Frost Bound Stone / Frost Bound Block | 0.00 | 6.39 | 6.67 | 0.00 | yes | brick.frostbound [v] |
| 78 | 2.90 | `Railcraft:brick.nether` | Etched Nether Stone / Fitted Nether Stone / Nether Block | 0.00 | 6.19 | 6.67 | 0.00 | yes | brick.nether [v] |
| 80 | 2.82 | `Railcraft:track` | Buffer Stop Track / Control Track / Coupler Track | 0.00 | 5.76 | 6.67 | 0.00 | yes | tracks/track.switch [v]; tracks/track.junction [v]; tracks/track.wye [v]; tracks/track.boarding [v]; tracks/track.holding [v] … |
| 83 | 2.82 | `Railcraft:stair` | Abyssal Block Stairs / Abyssal Brick Stairs / Abyssal Cobble Stairs | 0.00 | 5.76 | 6.67 | 0.00 | yes | brick.abyssal [v]; brick.bleachedbone [v]; brick.bloodstained [v]; brick.frostbound [v]; brick.infernal [v] … |
| 84 | 2.82 | `Railcraft:post.metal` | Black Metal Post / Blue Metal Post / Brown Metal Post | 0.00 | 5.76 | 6.67 | 0.00 | no | post.metal [v] |
| 85 | 2.82 | `Railcraft:post.metal.platform` | Black Metal Platform / Blue Metal Platform / Brown Metal Platform | 0.00 | 5.76 | 6.67 | 0.00 | no | post.metal [g] |
| 86 | 2.82 | `Railcraft:wall.alpha` | Brick Wall / Chiseled Sandstone Wall / Chiseled Stone Brick Wall | 0.00 | 5.76 | 6.67 | 0.00 | no | brick.infernal [v]; brick.sandy [v]; concrete [v]; cube.stone.abyssal [v]; cube.stone.quarried [v] … |
| 89 | 2.79 | `Railcraft:signal` | Analog Signal Controller Box / Block Signal / Distant Signal | 0.00 | 5.63 | 6.67 | 0.00 | no | signal.switch.lever [v]; signal.switch.motor [v]; signal.switch.routing [v]; signal.switch.target [?]; signal.dual [v] … |
| 105 | 2.60 | `Railcraft:wall.beta` | Abyssal Brick Wall / Bleached Bone Brick Wall / Blood Stained Brick Wall | 0.00 | 4.68 | 6.67 | 0.00 | no | brick.abyssal [v]; brick.bleachedbone [v]; brick.nether [v] |

### chisel (8 of its 182 blocks in the top 150; best rank 2)

| # | score | block | names (first 3) | W | C | B | Q | icon | textures (inside `assets/<mod>/textures/blocks/`) |
|---|---|---|---|---|---|---|---|---|---|
| 2 | 7.05 | `chisel:marble` | Marble | 10.00 | 4.40 | 6.67 | 0.00 | yes | marble [v]; marble/32/marble [v] |
| 3 | 6.75 | `chisel:limestone` | Limestone | 10.00 | 2.94 | 6.67 | 0.00 | yes | limestone [v] |
| 4 | 6.67 | `chisel:diorite` | Diorite | 10.00 | 2.52 | 6.67 | 0.00 | yes | diorite/diorite [v] |
| 5 | 6.45 | `chisel:andesite` | Andesite | 10.00 | 1.41 | 6.67 | 0.00 | yes | andesite/andesite [v] |
| 6 | 6.45 | `chisel:granite` | Granite | 10.00 | 1.41 | 6.67 | 0.00 | yes | granite/granite [v] |
| 39 | 3.39 | `chisel:carpet_block` | Carpet | 0.00 | 8.64 | 6.67 | 0.00 | yes | marble/block [v]; sandstone/block [v]; concrete/block [v]; carpet/yellow [v]; fantasy/block [v] … |
| 87 | 2.82 | `chisel:carpet` | Floor Carpet | 0.00 | 5.76 | 6.67 | 0.00 | no | carpet/black [g] |
| 149 | 2.17 | `chisel:marble_pillar` | Marble Pillar | 0.00 | 2.52 | 6.67 | 0.00 | yes | fantasy/pillar+ [v]; fantasy2/pillar+ [v] |

### legends (21 of its 728 blocks in the top 150; best rank 8)

| # | score | block | names (first 3) | W | C | B | Q | icon | textures (inside `assets/<mod>/textures/blocks/`) |
|---|---|---|---|---|---|---|---|---|---|
| 8 | 5.14 | `legends:andesite` | Andesite | 8.64 | 2.11 | 3.33 | 0.00 | yes | stone_andesite [v] |
| 9 | 5.01 | `legends:diorite` | Diorite | 8.03 | 2.82 | 3.33 | 0.00 | yes | stone_diorite [v] |
| 11 | 4.88 | `legends:granite` | Granite | 8.05 | 2.11 | 3.33 | 0.00 | yes | stone_granite [v] |
| 38 | 3.40 | `legends:redIronOre` | Red Iron Ore | 7.24 | 0.70 | 0.00 | 0.00 | yes | redironore [v] |
| 40 | 3.39 | `legends:blackIronOre` | Black-Iron Ore | 7.21 | 0.70 | 0.00 | 0.00 | yes | blackironore [v] |
| 43 | 3.35 | `legends:siliconOre` | Silicon Ore | 7.13 | 0.70 | 0.00 | 0.00 | yes | siliconore [v] |
| 45 | 3.32 | `legends:copperOre` | Copper Ore | 7.06 | 0.70 | 0.00 | 0.00 | yes | copperore [v] |
| 46 | 3.31 | `legends:cassiteriteOre` | Cassiterite Ore | 7.04 | 0.70 | 0.00 | 0.00 | yes | cassiteriteore [v] |
| 53 | 3.10 | `legends:magnesiteOre` | Magnesite Ore | 6.58 | 0.70 | 0.00 | 0.00 | yes | magnesiteore [v] |
| 55 | 3.08 | `legends:sphaleriteOre` | Sphalerite Ore | 6.54 | 0.70 | 0.00 | 0.00 | yes | sphaleriteore [v] |
| 58 | 3.05 | `legends:concrete` | Black Concrete / Blue Concrete / Brown Concrete | 0.60 | 9.71 | 3.33 | 0.00 | yes | concrete_black [v]; concrete_gray [v]; concrete_light_gray [v]; concrete_brown [v]; concrete_white [v] … |
| 60 | 3.04 | `legends:titaniumOre` | Titanium Ore | 6.44 | 0.70 | 0.00 | 0.00 | yes | titaniumore [v] |
| 69 | 2.93 | `legends:bauxiteOre` | Bauxite Ore | 6.20 | 0.70 | 0.00 | 0.00 | yes | bauxiteore [v] |
| 99 | 2.75 | `legends:dynamicLegendsBlock14` | Silver Ore | 5.80 | 0.70 | 0.00 | 0.00 | yes | silverore [v] |
| 109 | 2.56 | `legends:concretePowder` | Black Concrete Powder / Blue Concrete Powder / Brown Concrete Powder | 0.01 | 8.64 | 3.33 | 0.00 | yes | concrete_powder_gray [v]; concrete_powder_light_gray [v]; concrete_powder_white [v]; concrete_powder_orange [v]; concrete_powder_magenta [v] … |
| 111 | 2.54 | `legends:platinumOre` | Platinum Ore | 5.33 | 0.70 | 0.00 | 0.00 | yes | platinumore [v] |
| 129 | 2.49 | `legends:dynamicLegendsBlock46` | Nether Gold Ore | 5.21 | 0.70 | 0.00 | 0.00 | yes | nether_gold_ore [v] |
| 131 | 2.42 | `legends:tungstenOre` | Tungsten Ore | 5.07 | 0.70 | 0.00 | 0.00 | yes | tungstenore [v] |
| 136 | 2.31 | `legends:monitor` | Monitor | 0.00 | 3.23 | 6.67 | 0.00 | no | ancient_debris_side [?] |
| 139 | 2.31 | `legends:dynamicLegendsBlock1` | Red Sandstone | 3.88 | 2.82 | 0.00 | 0.00 | yes | red_sandstone [v]; red_sandstone_top [v]; red_sandstone_bottom [v] |
| 144 | 2.23 | `legends:dynamicSuperHeroesBlock6` | Chunk of Krypton | 4.65 | 0.70 | 0.00 | 0.00 | yes | smoker_bottom [m] |

### voltzengine (2 of its 3 blocks in the top 150; best rank 10)

| # | score | block | names (first 3) | W | C | B | Q | icon | textures (inside `assets/<mod>/textures/blocks/`) |
|---|---|---|---|---|---|---|---|---|---|
| 10 | 4.92 | `voltzengine:veStoneOre` | Bauxite Ore / Copper Ore / Lead Ore | 10.00 | 2.11 | 0.00 | 0.00 | yes | stone/ore_lead [v]; stone/ore_zinc [v]; stone/ore_magnesite [v]; stone/ore_copper [v]; stone/ore_tin [v] … |
| 17 | 4.50 | `voltzengine:veGemOre` | Amazonite Ore / Black Banded Onyx Ore / Green Garnet Ore | 10.00 | 0.00 | 0.00 | 0.00 | yes | stone/ore_amazonite [v]; stone/ore_smokeyquartz [m]; stone/ore_garnetyellow [v]; stone/ore_garnetred [v]; stone/ore_garnetorange [v] … |

### BiomesOPlenty (14 of its 83 blocks in the top 150; best rank 12)

| # | score | block | names (first 3) | W | C | B | Q | icon | textures (inside `assets/<mod>/textures/blocks/`) |
|---|---|---|---|---|---|---|---|---|---|
| 12 | 4.50 | `BiomesOPlenty:ashStone` |  | 10.00 | 0.00 | 0.00 | 0.00 | no | ashstone [v] |
| 13 | 4.50 | `BiomesOPlenty:hardIce` |  | 10.00 | 0.00 | 0.00 | 0.00 | no | hardice [v] |
| 14 | 4.50 | `BiomesOPlenty:cragRock` |  | 10.00 | 0.00 | 0.00 | 0.00 | no | cragrock [v] |
| 24 | 3.91 | `BiomesOPlenty:driedDirt` |  | 8.68 | 0.00 | 0.00 | 0.00 | no | drieddirt [v] |
| 42 | 3.36 | `BiomesOPlenty:newBopDirt` |  | 7.46 | 0.00 | 0.00 | 0.00 | no | dirt_loamy [v]; dirt_sandy [v]; dirt_silty [v]; coarse_dirt_loamy [v]; coarse_dirt_sandy [v] … |
| 47 | 3.25 | `BiomesOPlenty:hardDirt` |  | 7.22 | 0.00 | 0.00 | 0.00 | no | harddirt [v] |
| 54 | 3.08 | `BiomesOPlenty:colorizedLeaves2` |  | 6.86 | 0.00 | 0.00 | 0.00 | no | leaves_willow_fancy [v]; leaves_pine_fancy [v]; leaves_mahogany_fancy [v]; leaves_flowering_fancy [v]; leaves_flowering_overlay [v] |
| 75 | 2.91 | `BiomesOPlenty:foliage` |  | 6.47 | 0.00 | 0.00 | 0.00 | no | shortgrass [v]; mediumgrass [v]; bush [v]; sprout [v]; poisonivy [v] … |
| 79 | 2.87 | `BiomesOPlenty:hardSand` |  | 6.38 | 0.00 | 0.00 | 0.00 | no | hardsand [v] |
| 130 | 2.43 | `BiomesOPlenty:newBopGrass` |  | 5.39 | 0.00 | 0.00 | 0.00 | no | grass_top [missing]; grass_loamy_side [v]; grass_sandy_side [v]; grass_silty_side [v]; grass_loamy_side_snowed [v] … |
| 132 | 2.40 | `BiomesOPlenty:leaves3` |  | 5.34 | 0.00 | 0.00 | 0.00 | no | leaves_origin_fancy [v]; leaves_pinkcherry_fancy [v]; leaves_maple_fancy [v]; leaves_whitecherry_fancy [v] |
| 137 | 2.31 | `BiomesOPlenty:leaves2` |  | 5.14 | 0.00 | 0.00 | 0.00 | no | leaves_dead_fancy [v]; leaves_fir_fancy [v]; leaves_ethereal_fancy [v]; leaves_orangeautumn_fancy [v] |
| 138 | 2.31 | `BiomesOPlenty:colorizedLeaves1` |  | 5.14 | 0.00 | 0.00 | 0.00 | no | leaves_sacredoak_fancy [v]; leaves_mangrove_fancy [v]; leaves_palm_fancy [v]; leaves_redwood_fancy [v] |
| 147 | 2.21 | `BiomesOPlenty:leaves1` |  | 4.90 | 0.00 | 0.00 | 0.00 | no | leaves_yellowautumn_fancy [v]; leaves_bamboo_fancy [v]; leaves_magic_fancy [v]; leaves_dark_fancy [v] |

### TwilightForest (12 of its 62 blocks in the top 150; best rank 15)

| # | score | block | names (first 3) | W | C | B | Q | icon | textures (inside `assets/<mod>/textures/blocks/`) |
|---|---|---|---|---|---|---|---|---|---|
| 15 | 4.50 | `TwilightForest:tile.TFLeaves` | Canopy Tree Leaves / Mangrove Leaves / Rainbow Oak Leaves | 10.00 | 0.00 | 0.00 | 0.00 | no | minecraft:leaves_oak [vanilla]; minecraft:leaves_spruce [vanilla]; minecraft:leaves_birch [vanilla] |
| 16 | 4.50 | `TwilightForest:tile.TFDeadrock` | Cracked Deadrock / Deadrock / Weathered Deadrock | 10.00 | 0.00 | 0.00 | 0.00 | yes | deadrock_solid [v]; deadrock_cracked [v]; deadrock_surface [v] |
| 19 | 4.20 | `TwilightForest:tile.DarkLeaves` | Darkwood Leaves | 9.34 | 0.00 | 0.00 | 0.00 | yes | darkwood_leaves [v] |
| 20 | 4.15 | `TwilightForest:tile.TFLog` | Canopy Tree Wood / Darkwood Wood / Mangrove Wood | 7.84 | 2.61 | 0.00 | 1.00 | yes | oak_side [v]; oak_top [v]; canopy_side [v]; canopy_top [v]; mangrove_side [v] … |
| 36 | 3.43 | `TwilightForest:tile.TFTowerStone` | Cracked Towerwood / Encased Towerwood / Infested Towerwood | 3.27 | 5.65 | 3.33 | 0.00 | yes | towerwood_planks [v]; towerwood_encased [v]; towerwood_cracked [v]; towerwood_mossy [v]; towerwood_infested [v] |
| 41 | 3.39 | `TwilightForest:tile.TFRoots` | Liveroots / Roots | 7.52 | 0.00 | 0.00 | 0.00 | yes | rootblock [v]; oreroots [v] |
| 49 | 3.22 | `TwilightForest:tile.CastleBrick` | Castle Brick / Castle Roof Tile / Cracked Castle Brick | 5.29 | 0.00 | 3.33 | 0.00 | yes | castleblock_brick [v]; castleblock_cracked [v]; castleblock_mossy [v]; castleblock_faded [v]; castleblock_roof [v] |
| 102 | 2.66 | `TwilightForest:tile.TFAuroraBrick` | Aurora Block | 3.57 | 1.12 | 3.33 | 0.00 | yes | forcefield_purple [g] |
| 108 | 2.57 | `TwilightForest:tile.TFPlank` | Canopy Planks / Darkwood Planks / Mangrove Planks | 0.00 | 8.71 | 3.33 | 0.00 | yes | twilight_oak_planks [v]; canopy_planks [v]; mangrove_planks [v]; darkwood_planks [v]; timewood_planks [v] … |
| 135 | 2.33 | `TwilightForest:tile.TFPlant` | Dried Bush / Fiddlehead / Forest Grass | 4.87 | 0.70 | 0.00 | 0.00 | yes | mosspatch [g]; towerdev_ghasttraplid_off [g]; mayapple [v]; torchberry [g]; mushgloom [v] … |
| 140 | 2.30 | `TwilightForest:tile.TFMazestone` | Chiseled Mazestone / Cracked Mazestone Brick / Decorative Mazestone Brick | 3.27 | 0.00 | 3.33 | 0.00 | yes | mazestone_plain [v]; mazestone_brick [v]; mazestone_decorative [v]; mazestone_mosaic [v]; mazestone_cracked [v] … |
| 148 | 2.20 | `TwilightForest:tile.TFUnderBrick` | Cracked Underbrick / Mossy Underbrick / Underbrick | 3.04 | 0.00 | 3.33 | 0.00 | yes | knightbrick [v]; knightbrick_mossy [v]; knightbrick_cracked [v]; knightbrick_floor [v] |

### transformers (2 of its 34 blocks in the top 150; best rank 18)

| # | score | block | names (first 3) | W | C | B | Q | icon | textures (inside `assets/<mod>/textures/blocks/`) |
|---|---|---|---|---|---|---|---|---|---|
| 18 | 4.38 | `transformers:energon_ore` | Energon Ore | 9.74 | 0.00 | 0.00 | 0.00 | yes | energon_ore [v] |
| 35 | 3.47 | `transformers:transformium_ore` | Transformium Ore | 7.71 | 0.00 | 0.00 | 0.00 | yes | transformium_ore [v] |

### TragicMC (7 of its 100 blocks in the top 150; best rank 21)

| # | score | block | names (first 3) | W | C | B | Q | icon | textures (inside `assets/<mod>/textures/blocks/`) |
|---|---|---|---|---|---|---|---|---|---|
| 21 | 4.13 | `TragicMC:darkStone` | Beveled Dark Stone / Brown Beveled Dark Stone / Brown Corroded Dark Stone | 4.91 | 5.42 | 3.33 | 0.00 | yes | SmoothDarkStone [v]; RedDarkStone [v]; GreenDarkStone [v]; TealDarkStone [v]; BrownDarkStone [v] … |
| 77 | 2.91 | `TragicMC:darkCobblestone` | Ashen Dark Cobblestone / Dark Cobblestone / Hot Dark Cobblestone | 3.09 | 3.42 | 3.33 | 0.00 | yes | NormalDarkCobble [v]; ToxicDarkCobble [v]; AshenDarkCobble [v]; HotDarkCobble [v] |
| 98 | 2.78 | `TragicMC:quicksand` | Drudge / Mud / Quicksand | 4.92 | 2.82 | 0.00 | 0.00 | yes | NetherDrudge [v]; ToxicSludge [v]; Quicksand [v]; Mud [v] |
| 100 | 2.70 | `TragicMC:starCrystal` | Black Star Crystal / Blue Star Crystal / Brown Star Crystal | 0.39 | 6.46 | 3.33 | 4.00 | yes | LightBlueStarCrystal [v]; LightGrayStarCrystal [v]; GreenStarCrystal [m]; BlueStarCrystal [v]; YellowStarCrystal [v] … |
| 101 | 2.67 | `TragicMC:circuit` | Aged Circuit / Damaged Circuit / Dead Circuit | 5.93 | 0.00 | 0.00 | 0.00 | yes | LiveCircuit [v]; DamagedCircuit [v]; VeryDamagedCircuit [v]; DeadCircuit [v]; AgedCircuit [v] |
| 107 | 2.58 | `TragicMC:erodedStone` | Carved Eroded Stone / Eroded Stone / Scattered Eroded Stone | 2.44 | 3.23 | 3.33 | 0.00 | yes | SmoothErodedStone [v]; ScatteredErodedStone [v]; CarvedErodedStone [v] |
| 128 | 2.50 | `TragicMC:mercuryOre` | Red Mercury Ore | 5.24 | 0.70 | 0.00 | 0.00 | yes | MercuryOre [v] |

### EnderStorage (1 of its 1 blocks in the top 150; best rank 22)

| # | score | block | names (first 3) | W | C | B | Q | icon | textures (inside `assets/<mod>/textures/blocks/`) |
|---|---|---|---|---|---|---|---|---|---|
| 22 | 4.05 | `EnderStorage:enderChest` | Ender Chest / Ender Tank | 0.00 | 5.76 | 10.00 | 4.00 | no | — |

### StorageDrawers (10 of its 16 blocks in the top 150; best rank 23)

| # | score | block | names (first 3) | W | C | B | Q | icon | textures (inside `assets/<mod>/textures/blocks/`) |
|---|---|---|---|---|---|---|---|---|---|
| 23 | 4.03 | `StorageDrawers:fullDrawers1` | Acacia Drawer / Birch Drawer / Dark Oak Drawer | 0.00 | 5.63 | 10.00 | 4.00 | yes | drawers_oak_side [m]; drawers_spruce_side [m]; drawers_birch_side [m]; drawers_jungle_side [m]; drawers_acacia_side [m] … |
| 26 | 3.63 | `StorageDrawers:fullDrawers2` | Acacia Drawers 1x2 / Birch Drawers 1x2 / Dark Oak Drawers 1x2 | 0.00 | 5.63 | 10.00 | 0.00 | yes | drawers_oak_front_1 [v]; drawers_spruce_front_1 [v]; drawers_birch_side_h [v]; drawers_jungle_front_1 [v]; drawers_acacia_side_h [v] … |
| 27 | 3.63 | `StorageDrawers:fullDrawers4` | Acacia Drawers 2x2 / Birch Drawers 2x2 / Dark Oak Drawers 2x2 | 0.00 | 5.63 | 10.00 | 0.00 | yes | drawers_oak_side_v [v]; drawers_spruce_side_v [v]; drawers_birch_sort [v]; drawers_jungle_side_h [v]; drawers_acacia_sort [v] … |
| 28 | 3.63 | `StorageDrawers:halfDrawers2` | Compact Acacia Drawers 1x2 / Compact Birch Drawers 1x2 / Compact Dark Oak Drawers 1x2 | 0.00 | 5.63 | 10.00 | 0.00 | no | drawers_oak_front_1 [g]; drawers_spruce_front_1 [g]; drawers_birch_front_1 [g]; drawers_jungle_front_1 [g]; drawers_acacia_front_1 [g] … |
| 29 | 3.63 | `StorageDrawers:halfDrawers4` | Compact Acacia Drawers 2x2 / Compact Birch Drawers 2x2 / Compact Dark Oak Drawers 2x2 | 0.00 | 5.63 | 10.00 | 0.00 | no | drawers_oak_front_1 [g]; drawers_spruce_front_1 [g]; drawers_birch_front_1 [g]; drawers_jungle_front_1 [g]; drawers_acacia_front_1 [g] … |
| 34 | 3.49 | `StorageDrawers:trim` | Acacia Trim / Birch Trim / Dark Oak Trim | 0.00 | 4.93 | 10.00 | 0.00 | yes | base/trim_oak [v]; drawers_spruce_side [m]; drawers_birch_side [m]; drawers_jungle_side [m]; drawers_acacia_trim [m] … |
| 52 | 3.18 | `StorageDrawers:controller` | Drawer Controller | 0.00 | 1.41 | 10.00 | 4.00 | yes | drawers_controller_front [g] |
| 95 | 2.78 | `StorageDrawers:compDrawers` | Compacting Drawer | 0.00 | 1.41 | 10.00 | 0.00 | yes | drawers_comp_front_2 [v] |
| 96 | 2.78 | `StorageDrawers:controllerSlave` | Controller Slave | 0.00 | 1.41 | 10.00 | 0.00 | yes | drawers_controller_front [g] |
| 97 | 2.78 | `StorageDrawers:trimCustom` | Framed Trim | 0.00 | 1.41 | 10.00 | 0.00 | yes | drawers_spruce_trim [g] |

### CompactMachines (7 of its 8 blocks in the top 150; best rank 25)

| # | score | block | names (first 3) | W | C | B | Q | icon | textures (inside `assets/<mod>/textures/blocks/`) |
|---|---|---|---|---|---|---|---|---|---|
| 25 | 3.69 | `CompactMachines:machine` | Compact Machine | 0.00 | 3.95 | 10.00 | 4.00 | yes | machine_0 [v]; machine_1 [v]; machine_2 [v]; machine_3 [v]; machine_4 [v] … |
| 90 | 2.78 | `CompactMachines:innerwalldecor` | Compact Machine Wall (Decorative) | 0.00 | 1.41 | 10.00 | 0.00 | yes | machine_0 [m] |
| 91 | 2.78 | `CompactMachines:interfacedecor` | Compact Machine Interface (Decorative) | 0.00 | 1.41 | 10.00 | 0.00 | yes | interface [v] |
| 110 | 2.55 | `CompactMachines:innerwall` | Compact Machine Wall | 0.00 | 0.00 | 10.00 | 0.50 | yes | innerwall [v] |
| 125 | 2.50 | `CompactMachines:interface` | Compact Machine Interface | 0.00 | 0.00 | 10.00 | 0.00 | yes | interface [v] |
| 126 | 2.50 | `CompactMachines:interfacecreative` | Compact Machine Interface | 0.00 | 0.00 | 10.00 | 0.00 | yes | interface [v] |
| 127 | 2.50 | `CompactMachines:innerwallcreative` | Compact Machine Wall | 0.00 | 0.00 | 10.00 | 0.00 | yes | machine_0 [m] |

### arcticmobs (1 of its 5 blocks in the top 150; best rank 30)

| # | score | block | names (first 3) | W | C | B | Q | icon | textures (inside `assets/<mod>/textures/blocks/`) |
|---|---|---|---|---|---|---|---|---|---|
| 30 | 3.62 | `arcticmobs:ooze` | Ooze | 8.05 | 0.00 | 0.00 | 0.00 | no | ooze_flow [g] |

### IronChest (1 of its 1 blocks in the top 150; best rank 33)

| # | score | block | names (first 3) | W | C | B | Q | icon | textures (inside `assets/<mod>/textures/blocks/`) |
|---|---|---|---|---|---|---|---|---|---|
| 33 | 3.55 | `IronChest:BlockIronChest` | Copper Chest / Crystal Chest / Diamond Chest | 0.00 | 3.27 | 10.00 | 4.00 | no | iron_front [g]; gold_front [g]; diamond_front [g]; copper_front [g]; dirtchest9000_front [g] |

### ProjectE (10 of its 20 blocks in the top 150; best rank 37)

| # | score | block | names (first 3) | W | C | B | Q | icon | textures (inside `assets/<mod>/textures/blocks/`) |
|---|---|---|---|---|---|---|---|---|---|
| 37 | 3.41 | `ProjectE:alchemical_chest` | Alchemical Chest | 0.00 | 4.29 | 10.00 | 0.50 | no | alchemy_chest [v] |
| 44 | 3.32 | `ProjectE:transmutation_table` | Transmutation Table | 0.00 | 2.11 | 10.00 | 4.00 | no | transmutation_stone/bottom [g] |
| 70 | 2.92 | `ProjectE:condenser_mk1` | Energy Condenser | 0.00 | 2.11 | 10.00 | 0.00 | no | condenser [v] |
| 71 | 2.92 | `ProjectE:collector_mk1` | Energy Collector MK1 | 0.00 | 2.11 | 10.00 | 0.00 | yes | collectors/other [g] |
| 72 | 2.92 | `ProjectE:collector_mk2` | Energy Collector MK2 | 0.00 | 2.11 | 10.00 | 0.00 | yes | collectors/front [m] |
| 73 | 2.92 | `ProjectE:relay_mk1` | Anti-Matter Relay MK1 | 0.00 | 2.11 | 10.00 | 0.00 | yes | matter_furnace/dm_on [g] |
| 74 | 2.92 | `ProjectE:relay_mk2` | Anti-Matter Relay MK2 | 0.00 | 2.11 | 10.00 | 0.00 | yes | matter_furnace/dm_on [m] |
| 92 | 2.78 | `ProjectE:condenser_mk2` | Energy Condenser MK2 | 0.00 | 1.41 | 10.00 | 0.00 | no | condenser_mk2 [v] |
| 93 | 2.78 | `ProjectE:collector_mk3` | Energy Collector MK3 | 0.00 | 1.41 | 10.00 | 0.00 | yes | explosives/nova1_side [g] |
| 94 | 2.78 | `ProjectE:relay_mk3` | Anti-Matter Relay MK3 | 0.00 | 1.41 | 10.00 | 0.00 | yes | matter_furnace/dm_on [m] |

### OreSpawn (1 of its 211 blocks in the top 150; best rank 48)

| # | score | block | names (first 3) | W | C | B | Q | icon | textures (inside `assets/<mod>/textures/blocks/`) |
|---|---|---|---|---|---|---|---|---|---|
| 48 | 3.24 | `OreSpawn:OreSpawn_OreSaltBlock` | Salt Ore | 6.89 | 0.70 | 0.00 | 0.00 | yes | oresalt [v] |

### BiblioCraft (19 of its 33 blocks in the top 150; best rank 51)

| # | score | block | names (first 3) | W | C | B | Q | icon | textures (inside `assets/<mod>/textures/blocks/`) |
|---|---|---|---|---|---|---|---|---|---|
| 51 | 3.20 | `BiblioCraft:BiblioBorderlessPainting` | Acacia Painting Frame / Birch Painting Frame / Dark Oak Painting Frame | 0.00 | 7.65 | 6.67 | 0.00 | no | frame [v] |
| 57 | 3.05 | `BiblioCraft:BiblioLabel` | Acacia Label / Birch Wood Label / Dark Oak Label | 0.00 | 6.91 | 6.67 | 0.00 | no | frame [?] |
| 76 | 2.91 | `BiblioCraft:BiblioShelf` | Acacia Shelf / Birch Shelf / Dark Oak Shelf | 0.00 | 4.23 | 6.67 | 4.00 | no | frame [?] |
| 81 | 2.82 | `BiblioCraft:BiblioTypewriter` | Black Typewriter / Blue Typewriter / Brown Typewriter | 0.00 | 5.76 | 6.67 | 0.00 | no | frame [?] |
| 82 | 2.82 | `BiblioCraft:BiblioSwordPedestal` | Sword Pedestal | 0.00 | 5.76 | 6.67 | 0.00 | no | — |
| 112 | 2.51 | `BiblioCraft:BiblioClock` | Acacia Clock / Birch Clock / Dark Oak Clock | 0.00 | 4.23 | 6.67 | 0.00 | no | frame [?] |
| 113 | 2.51 | `BiblioCraft:BiblioFlatPainting` | Acacia Painting Frame / Birch Painting Frame / Dark Oak Painting Frame | 0.00 | 4.23 | 6.67 | 0.00 | no | frame [v] |
| 114 | 2.51 | `BiblioCraft:BiblioSimplePainting` | Acacia Painting Frame / Birch Painting Frame / Dark Oak Painting Frame | 0.00 | 4.23 | 6.67 | 0.00 | no | frame [v] |
| 115 | 2.51 | `BiblioCraft:BiblioMiddlePainting` | Acacia Painting Frame / Birch Painting Frame / Dark Oak Painting Frame | 0.00 | 4.23 | 6.67 | 0.00 | no | frame [v] |
| 116 | 2.51 | `BiblioCraft:BiblioFancyPainting` | Acacia Painting Frame / Birch Painting Frame / Dark Oak Painting Frame | 0.00 | 4.23 | 6.67 | 0.00 | no | frame [v] |
| 117 | 2.51 | `BiblioCraft:BiblioFancySign` | Acacia Fancy Sign / Birch Fancy Sign / Dark Oak Fancy Sign | 0.00 | 4.23 | 6.67 | 0.00 | no | frame [?] |
| 118 | 2.51 | `BiblioCraft:BiblioPotionShelf` | Acacia Potion Shelf / Birch Potion Shelf / Dark Oak Potion Shelf | 0.00 | 4.23 | 6.67 | 0.00 | no | frame [?] |
| 119 | 2.51 | `BiblioCraft:BiblioRack` | Acacia Tool Rack / Birch Tool Rack / Dark Oak Tool Rack | 0.00 | 4.23 | 6.67 | 0.00 | no | frame [?] |
| 120 | 2.51 | `BiblioCraft:BiblioCase` | Acacia Case / Birch Case / Dark Oak Case | 0.00 | 4.23 | 6.67 | 0.00 | no | frame [?] |
| 121 | 2.51 | `BiblioCraft:BiblioDesk` | Acacia Desk / Birch Desk / Dark Oak Desk | 0.00 | 4.23 | 6.67 | 0.00 | no | frame [?] |
| 122 | 2.51 | `BiblioCraft:BiblioTable` | Acacia Table / Birch Table / Dark Oak Table | 0.00 | 4.23 | 6.67 | 0.00 | no | frame [?] |
| 123 | 2.51 | `BiblioCraft:BiblioMapFrames` | Acacia Map Frame / Birch Map Frame / Dark Oak Map Frame | 0.00 | 4.23 | 6.67 | 0.00 | no | frame [v] |
| 124 | 2.51 | `BiblioCraft:BiblioSeats` | Acacia Seat / Birch Seat / Dark Oak Seat | 0.00 | 4.23 | 6.67 | 0.00 | no | frame [?] |
| 145 | 2.23 | `BiblioCraft:Bibliotheca` | Acacia Bookcase / Birch Bookcase / Dark Oak Bookcase | 0.00 | 6.98 | 3.33 | 0.00 | no | frame [?] |

### witchery (11 of its 121 blocks in the top 150; best rank 56)

| # | score | block | names (first 3) | W | C | B | Q | icon | textures (inside `assets/<mod>/textures/blocks/`) |
|---|---|---|---|---|---|---|---|---|---|
| 56 | 3.08 | `witchery:witchwood` | Alder Planks / Hawthorn Planks / Rowan Planks | 0.00 | 7.06 | 6.67 | 0.00 | yes | planks_rowan [v]; planks_alder [v]; planks_hawthorn [v] |
| 88 | 2.82 | `witchery:shadedglass` | Black Shaded Glass / Blue Shaded Glass / Brown Shaded Glass | 0.00 | 5.76 | 6.67 | 0.00 | yes | shadedglass [v]; shadedglass_orange [v]; shadedglass_magenta [v]; shadedglass_light_blue [v]; shadedglass_yellow [v] … |
| 103 | 2.65 | `witchery:poppetshelf` | Poppet Shelf | 0.00 | 1.41 | 6.67 | 7.00 | no | poppetShelf [v] |
| 104 | 2.65 | `witchery:distilleryidle` | Distillery | 0.00 | 1.41 | 6.67 | 7.00 | no | distillery [v] |
| 133 | 2.35 | `witchery:altar` | Altar | 0.00 | 1.41 | 6.67 | 4.00 | yes | altar [v] |
| 134 | 2.35 | `witchery:kettle` | Kettle | 0.00 | 1.41 | 6.67 | 4.00 | no | kettle [v] |
| 141 | 2.30 | `witchery:brazier` | Brazier | 0.00 | 1.41 | 6.67 | 3.50 | no | brazier [v] |
| 142 | 2.25 | `witchery:witchlog` | Alder Wood / Hawthorn Wood / Rowan Wood | 0.00 | 2.94 | 6.67 | 0.00 | yes | log_rowan [v]; log_alder [v]; log_hawthorn [v] |
| 143 | 2.25 | `witchery:witchesovenidle` | Witches Oven | 0.00 | 1.41 | 6.67 | 3.00 | no | witchesOven [v] |
| 146 | 2.22 | `witchery:snowstairs` | Snow Stairs | 0.59 | 1.41 | 6.67 | 0.00 | yes | circleglyph1.8 [g] |
| 150 | 2.17 | `witchery:stairswoodrowan` | Rowan Stairs | 0.00 | 2.52 | 6.67 | 0.00 | yes | planks_rowan [v] |

### securitycraft (1 of its 106 blocks in the top 150; best rank 106)

| # | score | block | names (first 3) | W | C | B | Q | icon | textures (inside `assets/<mod>/textures/blocks/`) |
|---|---|---|---|---|---|---|---|---|---|
| 106 | 2.58 | `securitycraft:reinforcedStainedGlass` | Reinforced Black Stained Glass / Reinforced Blue Stained Glass / Reinforced Brown Stained Glass | 0.00 | 8.75 | 3.33 | 0.00 | yes | reinforcedDoorUpper [g]; glass_reinforced_orange [m]; glass_reinforced_magenta [v]; glass_reinforced_light_blue [m]; glass_reinforced_yellow [m] … |

**Mods with no block in the top 150, and why:** OpenBlocks (tanks, elevators: tier 1, few
recipes), SecurityCraft (one: reinforced stained glass; the rest are vanilla-derived reinforced
copies), malisisdoors, CarpentersBlocks (draws other blocks' textures), cfm and Decocraft (models),
HEE beyond `end_stone_terrain`, `obsidian_special` and `ravaged_brick` (the End is mostly void in a
100-chunk sample, so its per-chunk rates are small; its blocks sit at ranks 150–300), customnpcs,
TardisMod, icbmclassic, FoodPlus, psychedelicraft, Lycanites' fluids (`arcticmobs:ooze` is in).

## 3. Style notes per family

The rule from [direction.md](direction.md) and the look bible: Minecraft's own designs with
Faithful-style detail, no noisy carpets, connected textures where they apply, a little more
vibrance, and PBR maps the deferred shader can use. Per family, what that means and what the
mods' art does today (from the contact sheet, `C:\qfb\textures\sheet-modded-top.png`):

**Ores on stone** (Legends' 14, Railcraft's 11, VoltzEngine's 19, TragicMC's mercury and
`tragicOres`, OreSpawn's salt/uranium/titanium/amethyst/ruby, Transformers' energon and
transformium, BoP's 8 gems, HEE's end ores; about 70 textures, the largest group). All are 16x
vanilla stone with flecks pasted on [verified on the sheet]. The host must become *our* stone:
QF v0's Faithful 32x stone, so an ore tile and the stone around it match. Draw the flecks at 32x
with Faithless's rule (faithless-study.md, element 5): metals as rounded nuggets, gems faceted,
fuels chunky, dusts dotted, crystals (energon, transformium, star crystal, kyber) as needle
clusters. Keep each mod's fleck hue, because that is how players tell 14 Legends ores apart:
red iron dark red, black iron near-black, copper orange, cassiterite pale, silicon blue-grey,
magnesite white, sphalerite yellow-brown, titanium silver, bauxite red-brown, platinum pale
silver, tungsten dark grey, palladium light grey, lightning yellow, ruby/sapphire/red diamond
red/blue/deep red. Railcraft's "poor" ores are the same minerals with fewer flecks; keep that
reading. `_s`: the fleck mask already carries LabPBR's metal codes (iron 230, gold 231,
copper 234, lead 235, platinum 236, silver 237) and gem F0s; the flecks glint, the stone does not.
Nether ores (TragicMC ruby/sapphire nether ore, Legends nether gold) and End ores (HEE) follow
their host: netherrack and end stone from QF v0.

**Stone families.** Chisel's marble and limestone are the most common modded blocks in the
Overworld (137 and 156 per chunk, veins at Y 50–60 [verified]): keep Chisel's designs (pale marble
with grey veining, beige limestone) and give them Faithful stone's grain at 32x; Chisel ships its
own CTM variant folders, which inherit any change to the base tile. Chisel's and Legends' granite,
diorite and andesite are 1.8's designs backported [verified by the textures]; Faithful 32x's
modern Java releases carry those three under the same licence (section 5). TragicMC's dark stone
is the whole Collision (16,170 per chunk): very dark blue-grey, nearly flat. Keep it dark (the
dimension is meant to be), add Faithful's stone grain at 32x with low contrast, and give the
corroded variants their colour as grain, not as noise. Twilight's deadrock (684 per chunk, the
Highlands' surface): grey with cracks; keep the crack design, sharpen it. Railcraft's abyssal
and quarried stone (geodes under the sea floor, 88 per chunk) and its eight brick sets (abyssal,
bleached bone, bloodstained, frostbound, infernal, nether, quarried, sandy): bold, clean joints
like Faithless's element 6, each set keeping its hue. BoP's crag rock, ash stone, hardened dirt,
sand and ice, dried dirt: calm, broad clusters (element 3) because they are terrain.

**Metals and machine casings** (Railcraft tanks, boilers, engines, coke oven and blast furnace
bricks, rolling machine, detectors, anchors, posts; IronChest fronts; ProjectE's condensers,
collectors, relays; Compact Machines' cube and inner wall; SecurityCraft's keypad and laser).
Railcraft already ships 32x–96x art for 118 of its 190 textures [verified: 73 at 16x, the rest
32/48/64/80/96/256], so it sits nearly right beside Faithful; the rest are 16x. Treat casings the
way Faithful treats the iron block: brushed metal, rivets as small bevels, dark rims, no speckle.
Machine faces with lamps (firebox doors, engines, collectors, the Compact Machine's lit frame) get
their bright pixels marked emissive in `_s` alpha; the generator does that for names the
classifier calls emissive (`_on`, `lit`, lamp, lantern, glow) and should get a list for the rest.
Specular: casings F0 40 (0.16), smoothness 0.5; the pure metal blocks use the metal codes.

**Storage** (StorageDrawers' 10 blocks, iron chests, ender chest, alchemical chest). Drawers are
vanilla planks with a drawer face [verified]; they must follow whatever planks become, so they
stay 16x until planks are decided (direction.md: foliage, logs, planks and dirt stay vanilla for
now). The chests are tile-entity models: IronChest's `*_front/side/top` are block textures and
can be done, EnderStorage's are not under `textures/blocks` at all and need their own pass.

**Twilight woods and dungeons.** Twilight oak, canopy, mangrove and darkwood logs and planks, the
four magic woods, towerwood (five variants), mazestone (eight), castle brick, knight brick,
aurora, nagastone. Twilight's palette sits next to vanilla's (twilight oak a shade darker than
oak, canopy spruce-like, mangrove pale, darkwood grey-brown) [verified on the sheet]: keep it,
and add bark furrows and board seams in Faithful's manner (element 9). TF's own leaves are only
`darkwood_leaves`; the four `TFLeaves` draw vanilla's oak, spruce and birch leaf textures
[verified: no such files in the jar], so the vanilla leaf decision covers them. Dungeon stone sets
get Faithless's bold joints; the Dark Tower's towerwood is wood, not stone, and should read as
dark planks.

**Organic and Witchery.** Rowan, alder and hawthorn planks and logs, the altar, cauldron, oven,
distillery, kettle, brazier, poppet shelf, shaded glass (17 colours, a glass family that wants
CTM). Witchery's art is dark and desaturated on purpose; keep that, do not lift its vibrance with
the global +12 %. BoP's leaves, foliage, flowers and grasses are biome-tinted cut-outs: calm
clusters, never speckle, and the same subsurface setting as vanilla leaves.

**Bone, flesh and crystal (OreSpawn, Lycanites, TragicMC, HEE).** OreSpawn's crystal dimension
(pink crystal stone, 15,817 per chunk there), its scale, uranium and titanium blocks, duct tape and
pizza are comic 16x art with chroma well above vanilla's; the spawn-ore blocks (`ore<mob>`) are
vanilla stone with a mob icon. Keep the shapes, pull chroma down to vanilla's range for the
stone-based ones, and leave the crystal dimension vivid: it is meant to glow. Lycanites' blocks
are fluids (ooze, poison, pure lava) and a few plants: the shader does the work; textures stay as
animated strips. TragicMC's 16 star crystals and the Synapse's circuits are emissive by design:
bright pixels in `_s` alpha, and the dark circuit board matte. HEE's ravaged brick and the three
End terrains follow the End stone decision.

**Vibrance.** QF v0's chroma × 1.12 applies to vanilla only. For modded art apply it per family:
yes for stone, ores and woods (they are drawn in vanilla's muted range), no for OreSpawn, TragicMC
star crystals, Witchery and anything already saturated.

### 16x beside 32x: the options

| option | what | cost | verdict |
|---|---|---|---|
| A. keep 16x | the status quo | none | wrong for ores and stone: a 16x stone host inside a 32x Faithful wall is the first thing anyone sees |
| B. 2x nearest + relief | no new pixels; the generated `_n`/`_s` carry the artist's shading as relief and material | automatic, done (section 4) | the floor for everything; under the deferred shader it reads as detail at a distance, blocky up close |
| C. re-composite on our host | for ores: Faithful 32x stone (licensed) under the mod's flecks at 2x nearest, using the same fleck mask as `_s` | one script, automatic | **done in v1** (section 4b): 70 textures, the top of the ranking, with no drawing |
| D. procedural upscale (hqx, xBR, grain) | smears pixel art | low | off-brief: the owner wants Minecraft's designs, not smoothed ones |
| E. hand-drawn 32x | Faithful's method, per block | high per block | for the families B and C cannot carry: machines, Twilight and TragicMC terrain, Chisel's two stones |
| F. F32 Modded Edition | the 2014–2024 "Faithful 32 Modded Edition" for 1.7.10 (section 5) | a licence decision | covers Railcraft, Twilight, Witchery, Chisel, drawers, iron chests, ProjectE, OpenBlocks, BoP, Carpenter's, Malisis if the owner accepts its terms |
| G. Faithful 32x modern Java | Legends' and Chisel's backported 1.8–1.16 blocks | fetch one zip | **done in v1**: 90 textures verified by colour; | granite/diorite/andesite, 16 concretes and powders, prismarine, red sandstone, sea lantern, magma, bone block, basalt, blackstone, soul soil, nether gold ore, ancient debris, netherite, quartz bricks, smooth stone, red nether brick: 60+ Legends textures under the licence we already use |

Recommended order: B now (done), then C and G (automatic, licensed), then F if the owner says
yes, then E for the top of what is left.

## 4. The generated LabPBR build

`tools/shaders/gen_surface_pack.py` now writes LabPBR (`_n`: RG normal with DirectX Y, B ambient
occlusion, A height; `_s`: smoothness, F0 or metal code, porosity/subsurface, emission) through
`tools/textures/labpbr.py`, which `build_qf_textures.py` (QF v0) imports too, so vanilla and
modded maps come from one conversion. `--format legacy` keeps the old RGB-normal + height layout,
the default for `--target vibrant` (OptiFine E7). `--only FILE` builds maps for a list of textures;
`--mods DIR` adds jar folders (BoP is on the world-design server). The `block.properties` output is
unchanged: the build below wrote it to a scratch folder and it is byte-identical to
`shaders/QuestForge/shaders/block.properties` apart from the header [verified by diff].

```
py -3.10 -I tools/textures/rank_modded_blocks.py --only C:\qfb\textures\top-modded.txt --top 150
py -3.10 -I tools/shaders/gen_surface_pack.py --target questforge --instance %APPDATA%\.crazycraft4 \
    --mods C:\qfs\v0\mods --world C:\qfb\world-master --shader-pack C:\qfb\textures\shaderpack-scratch \
    --only C:\qfb\textures\top-modded.txt --out C:\qfb\textures\QFTextures-modded-v0.zip
```

- **`C:\qfb\textures\QFTextures-modded-v0.zip`**: 434 textures of the top 150 blocks, 868 maps,
  **665,081 bytes**, 0.8 s. Never committed: it is derived from the mods' pixels.
- The whole set (same command without `--only`, `QFTextures-modded-v0-full.zip`): 5,947 textures,
  **12.3 MB, 6.9 s**. Cheap enough to rebuild on every change.
- Enable it above `QuestForge.zip` like `QuestForge-Surface.zip` was; the shader does not read
  the maps yet (direction.md section 2).

**Checks run.** `labpbr.check_layout` over all 434 pairs: 0 problems (height never 0, AO never
below 0.4, no F0 in the reserved 238–254 range). PIL read-back of nine maps (Legends red iron
and copper ore, Chisel marble, Twilight deadrock and darkwood leaves, TragicMC dark stone,
Railcraft poor gold, BoP crag rock, Legends granite): `_n` R and G average 127–128 (a flat
normal), AO minimum 140–240, height 221–255; `_s` smoothness 48–159 by family, F0 10 on stone
with the fleck codes 230/234/231 on the three ores, B 18 (stone porosity) or 170 (leaves
subsurface), emission 255 (none) on all nine [verified]. QF v0 rebuilt through the shared module:
the same 3,464 files; of 2,264 maps, 752 stained-glass CTM `_s` tiles changed (they now get
glass smoothness, a v0 miss), and bed (cloth), cocoa and nether wart stages (plant subsurface),
lava (emission base), sandstone (stone, not soil), iron ore flecks (iron metal code) and the lit
repeater/comparator (emission) moved on purpose; every other vanilla map is identical.


## 4b. QF Textures modded v1: ores on our stone, backports, connected glass, emission (2026-10-25)

`tools/textures/build_modded_textures.py` builds **`C:\qfb\textures\QFTextures-modded-v1.zip`**:
**3,616,173 bytes (3.6 MB), 2.1 s**, never committed. Pack source: `resourcepacks/QFTextures-modded/`
(pack.mcmeta, `backports.txt`, `ores-extra.txt`); the emissive list is `tools/textures/emissive-modded.txt`.

```
py -3.10 -I tools/textures/build_modded_textures.py --out C:\qfb\textures\QFTextures-modded-v1.zip \
    --sheets C:\qfb\textures --tables C:\qfb\textures\v1-tables.md
```

What is in it, in the order the owner asked for:

1. **Ores on our stone: 70 textures.** Every 16x ore texture is tested against vanilla's
   `stone.png`: if fewer than 60 % of its pixels differ, the host is vanilla stone and the
   difference is the fleck mask (48 textures: Legends 11, VoltzEngine 21, BoP 7, TragicMC 5,
   Transformers 2, SUM 1, ICBM 1). Eleven more whose host is the mod's own stone drawing or whose
   flecks cover more than 60 % are listed in `ores-extra.txt` and masked by `labpbr.ore_mask`'s
   median fallback [guess that stone is their host: Legends red/black iron, sphalerite,
   lightning; OreSpawn salt, uranium, titanium, amethyst, ruby; the Jungle's sapphire; the
   surprise ore]. Each is re-composited as **Faithful 32x stone (QF v0's, with its chroma × 1.12)
   under the mod's flecks at 2x nearest**; no pixel is drawn. Railcraft's eleven ores are
   **transparent overlays** (alpha 0 on 76–93 % of the tile) that its `RenderBlockOre` draws over
   the stone block in a second pass [verified in the jar], so they are kept as overlays at 2x and
   land on whatever stone the pack ships. Ores on dark stone (TragicMC's `Ore*`), netherrack and
   end stone are left at 16x: QF v0 keeps those hosts at vanilla 16x, so a 32x host would not match
   its neighbours. Review sheet: `C:\qfb\textures\sheet-ores-v1.png` (before | after).
2. **Backports: 90 textures.** Legends' and Chisel's 1.8–1.16 vanilla blocks draw **Faithful 32x
   Java 1.21.1**'s texture for the same block (`backports.txt`, 94 pairs). A pair is taken only
   when the mod's 16x and Faithful's 32x agree: mean-colour distance ≤ 60 and mean per-pixel
   distance at 16x ≤ 48 (the 90 taken sit at 0–45 and 0.4–17). Four are **[guess] and left
   out**: `soul_fire_0/1` (Faithful's soul fire is a different drawing, distance 311/348),
   `concrete_silver` (Legends' "silver" concrete is not light-gray concrete, 369) and
   `blast_furnace_bottom` (paired with the top as a guess, 241). Animated ones (`magma`,
   `sea_lantern`, `prismarine_rough`, the lit furnaces) carry Faithful's `.mcmeta`. Sheet:
   `sheet-backports-v1.png`.
3. **Connected textures: 35 rules, 1,594 files**, under `assets/minecraft/mcpatcher/ctm/qf/`, the
   1.7.10 MCPatcher format Angelica reads. For Witchery's shaded glass (16 colours), SecurityCraft's
   reinforced stained glass (16) and reinforced glass (1): `method=ctm`, `matchBlocks=<modid:name>`,
   `metadata=<dye>`, `tiles=0-46`, `connect=tile`, with **47 tiles generated from the mod's own
   texture**: which edges each tile index keeps was measured from Faithful 32x's glass tiles
   (`CTM47` in the script), the standard layout every pack uses, so these connect exactly as
   Faithful's glass does; an open edge takes the interior row beside it. For Chisel's marble and
   limestone (metadata 0, the worldgen variant): `method=repeat width=2 height=2 tiles=0-3`, the
   tile's four rotations, so no two neighbours repeat. Keys and methods are the ones in Angelica's
   `TileOverride` (`ctm`, `repeat`, `matchBlocks`, `metadata`, `tiles`, `connect`, `width`,
   `height`) and `matchBlocks` resolves `modid:name` through `GameData.getBlockRegistry`
   [verified by `javap` on `BlockAPI.createMatchers`]. Block names are from the registry, metadata
   from the item dump, textures from the icon pairing [verified]. **Railcraft's strengthened glass
   gets no rule**: its `glass.png` is a 16×80 five-icon sheet that `TextureAtlasSheet.unstitchIcons`
   splits and the mod connects by itself [verified in the jar]. Not yet seen in a client: the first
   `modded_wall` render says whether the rules take. Sheet: `sheet-ctm-v1.png` (the 47 tiles and
   a 3×3 join of the blue shaded glass).
4. **Emission.** `gen_surface_pack.py --emissive FILE` (default `tools/textures/emissive-modded.txt`,
   `none` to disable) and the v1 builder mark the listed textures' bright pixels (luminance above
   0.45) as emitting in `_s` alpha: Railcraft fireboxes, engines, coke oven and blast furnace,
   ProjectE collectors/relays/condensers, Compact Machines, Legends' lanterns, sea lantern, magma
   and soul fire, TragicMC's 16 star crystals, lights and circuits, HEE's glow blocks and ores,
   Transformers' energon, Twilight's firefly jar, fire jet, gloom and aurora, and the rest of the
   list (~200 names, each checked against the jars). 45 of them are in v1's map set; the whole
   list applies on a full `gen_surface_pack` run. The item dump must be rerun after any texture
   change so the site's icons follow (`tools/items/README.md`; not run here).
5. **LabPBR maps** for the 434 top-ranked textures plus every replaced one (509) and every CTM tile
   (1,559), from what ships (the 32x composites for the ores).

**Checks run.** `labpbr.check_layout` over all 2,067 map pairs: 0 problems. PIL read-back:
`redironore` albedo 32×32 opaque, `_s` F0 {10, 230} (iron flecks); `ore.poor.gold` 32×32 with
alpha 0 on 93 % (overlay kept), F0 {0, 10, 231}; `ore.dark.lapis` overlay, F0 14; `stone_granite`
32×32, `_s` F0 10, smoothness 48–83; `sea_lantern` 160×32 animated strip, emission on 4,940 px
(minimum 13); `machine_0` 14 emitting px; `BlueStarCrystal` all 256 px emit; ProjectE
`collectors/front` 87 px. CTM properties read back as written (`matchBlocks=witchery:shadedglass`,
`metadata=11`, `method=ctm`, `tiles=0-46`, `connect=tile`; `chisel:marble` `method=repeat`
`width=2 height=2 tiles=0-3`). CREDITS.txt carries 211 lines: both Faithful zips with sha256, then
one record per generated file (source texture, jar, host, mask).

**Faithful 32x Java 1.21.1** (the backports' source), fetched 2026-10-25 into `C:\qfb\faithful\dl\`
and never into the repo: `Faithful.32x.-.1.21.1.zip`, **11,030,261 bytes**, sha256
`15e093da38af37e11531c6cfeb9787f5617c20009c68b789eb62cfafe53c2762`, from the official repository
`Faithful-Resource-Pack/Faithful-32x-Java`, release `june-2026-release` (2026-06-18),
https://github.com/Faithful-Resource-Pack/Faithful-32x-Java/releases/download/june-2026-release/Faithful.32x.-.1.21.1.zip,
pack_format 34, 1,009 block textures, `LICENSE.txt` = Faithful License v4 inside [verified]. Same
licence and the same credit as the 1.7.10 zip (look-bible, "Faithful 32x: source and licence").

#### Ores re-composited (70)

| texture | mask |
|---|---|
| `biomesoplenty/textures/blocks/amberore.png` | diff vs vanilla stone (55% flecks) |
| `biomesoplenty/textures/blocks/malachiteore.png` | diff vs vanilla stone (50% flecks) |
| `biomesoplenty/textures/blocks/peridotore.png` | diff vs vanilla stone (46% flecks) |
| `biomesoplenty/textures/blocks/rubyore.png` | diff vs vanilla stone (47% flecks) |
| `biomesoplenty/textures/blocks/sapphireore.png` | diff vs vanilla stone (41% flecks) |
| `biomesoplenty/textures/blocks/tanzaniteore.png` | diff vs vanilla stone (44% flecks) |
| `biomesoplenty/textures/blocks/topazore.png` | diff vs vanilla stone (56% flecks) |
| `icbmclassic/textures/blocks/redstone_ore.png` | diff vs vanilla stone (16% flecks) |
| `legends/textures/blocks/bauxiteore.png` | diff vs vanilla stone (16% flecks) |
| `legends/textures/blocks/blackironore.png` | ores-extra.txt, median fallback mask |
| `legends/textures/blocks/cassiteriteore.png` | diff vs vanilla stone (47% flecks) |
| `legends/textures/blocks/copperore.png` | diff vs vanilla stone (16% flecks) |
| `legends/textures/blocks/lightningore.png` | ores-extra.txt, median fallback mask |
| `legends/textures/blocks/limoniteore.png` | diff vs vanilla stone (33% flecks) |
| `legends/textures/blocks/magnesiteore.png` | diff vs vanilla stone (44% flecks) |
| `legends/textures/blocks/reddiamondore.png` | diff vs vanilla stone (20% flecks) |
| `legends/textures/blocks/redironore.png` | ores-extra.txt, median fallback mask |
| `legends/textures/blocks/rubyore.png` | diff vs vanilla stone (45% flecks) |
| `legends/textures/blocks/sapphireore.png` | diff vs vanilla stone (58% flecks) |
| `legends/textures/blocks/siliconore.png` | diff vs vanilla stone (23% flecks) |
| `legends/textures/blocks/silverore.png` | diff vs vanilla stone (23% flecks) |
| `legends/textures/blocks/sphaleriteore.png` | ores-extra.txt, median fallback mask |
| `legends/textures/blocks/tungstenore.png` | diff vs vanilla stone (41% flecks) |
| `orespawn/textures/blocks/oreamethyst.png` | ores-extra.txt, median fallback mask |
| `orespawn/textures/blocks/oreruby.png` | ores-extra.txt, median fallback mask |
| `orespawn/textures/blocks/oresalt.png` | ores-extra.txt, median fallback mask |
| `orespawn/textures/blocks/oretitanium.png` | ores-extra.txt, median fallback mask |
| `orespawn/textures/blocks/oreuranium.png` | ores-extra.txt, median fallback mask |
| `railcraft/textures/blocks/ore.dark.diamond.png` | transparent overlay kept, 2x nearest (the mod draws it over the stone block) |
| `railcraft/textures/blocks/ore.dark.emerald.png` | transparent overlay kept, 2x nearest (the mod draws it over the stone block) |
| `railcraft/textures/blocks/ore.dark.lapis.png` | transparent overlay kept, 2x nearest (the mod draws it over the stone block) |
| `railcraft/textures/blocks/ore.firestone.png` | transparent overlay kept, 2x nearest (the mod draws it over the stone block) |
| `railcraft/textures/blocks/ore.poor.copper.png` | transparent overlay kept, 2x nearest (the mod draws it over the stone block) |
| `railcraft/textures/blocks/ore.poor.gold.png` | transparent overlay kept, 2x nearest (the mod draws it over the stone block) |
| `railcraft/textures/blocks/ore.poor.iron.png` | transparent overlay kept, 2x nearest (the mod draws it over the stone block) |
| `railcraft/textures/blocks/ore.poor.lead.png` | transparent overlay kept, 2x nearest (the mod draws it over the stone block) |
| `railcraft/textures/blocks/ore.poor.tin.png` | transparent overlay kept, 2x nearest (the mod draws it over the stone block) |
| `railcraft/textures/blocks/ore.saltpeter.png` | transparent overlay kept, 2x nearest (the mod draws it over the stone block) |
| `railcraft/textures/blocks/ore.sulfur.png` | transparent overlay kept, 2x nearest (the mod draws it over the stone block) |
| `sum/textures/blocks/kryptoniteore.png` | diff vs vanilla stone (34% flecks) |
| `surpriseeggs/textures/blocks/surprise_ore.png` | ores-extra.txt, median fallback mask |
| `thejungle/textures/blocks/oreSapphire.png` | ores-extra.txt, median fallback mask |
| `tragicmc/textures/blocks/MercuryOre.png` | diff vs vanilla stone (24% flecks) |
| `tragicmc/textures/blocks/RubyOre.png` | diff vs vanilla stone (45% flecks) |
| `tragicmc/textures/blocks/SapphireOre.png` | diff vs vanilla stone (45% flecks) |
| `tragicmc/textures/blocks/SapphireOre2.png` | diff vs vanilla stone (24% flecks) |
| `tragicmc/textures/blocks/TungstenOre.png` | diff vs vanilla stone (24% flecks) |
| `transformers/textures/blocks/energon_ore.png` | diff vs vanilla stone (16% flecks) |
| `transformers/textures/blocks/transformium_ore.png` | diff vs vanilla stone (29% flecks) |
| `voltzengine/textures/blocks/stone/ore_amazonite.png` | diff vs vanilla stone (54% flecks) |
| `voltzengine/textures/blocks/stone/ore_bauxite.png` | diff vs vanilla stone (44% flecks) |
| `voltzengine/textures/blocks/stone/ore_copper.png` | diff vs vanilla stone (44% flecks) |
| `voltzengine/textures/blocks/stone/ore_garnetgreen.png` | diff vs vanilla stone (45% flecks) |
| `voltzengine/textures/blocks/stone/ore_garnetorange.png` | diff vs vanilla stone (45% flecks) |
| `voltzengine/textures/blocks/stone/ore_garnetred.png` | diff vs vanilla stone (45% flecks) |
| `voltzengine/textures/blocks/stone/ore_garnetyellow.png` | diff vs vanilla stone (45% flecks) |
| `voltzengine/textures/blocks/stone/ore_lead.png` | diff vs vanilla stone (23% flecks) |
| `voltzengine/textures/blocks/stone/ore_magnesite.png` | diff vs vanilla stone (44% flecks) |
| `voltzengine/textures/blocks/stone/ore_nickel.png` | diff vs vanilla stone (23% flecks) |
| `voltzengine/textures/blocks/stone/ore_onyxblack.png` | diff vs vanilla stone (45% flecks) |
| `voltzengine/textures/blocks/stone/ore_onyxred.png` | diff vs vanilla stone (45% flecks) |
| `voltzengine/textures/blocks/stone/ore_platinum.png` | diff vs vanilla stone (23% flecks) |
| `voltzengine/textures/blocks/stone/ore_ruby.png` | diff vs vanilla stone (45% flecks) |
| `voltzengine/textures/blocks/stone/ore_sapphire.png` | diff vs vanilla stone (45% flecks) |
| `voltzengine/textures/blocks/stone/ore_silver.png` | diff vs vanilla stone (23% flecks) |
| `voltzengine/textures/blocks/stone/ore_smokeyquartz.png` | diff vs vanilla stone (54% flecks) |
| `voltzengine/textures/blocks/stone/ore_tin.png` | diff vs vanilla stone (22% flecks) |
| `voltzengine/textures/blocks/stone/ore_titanium.png` | diff vs vanilla stone (23% flecks) |
| `voltzengine/textures/blocks/stone/ore_uranium.png` | diff vs vanilla stone (23% flecks) |
| `voltzengine/textures/blocks/stone/ore_zinc.png` | diff vs vanilla stone (23% flecks) |

#### Backports (94 listed, 90 verified)

| mod texture | Faithful 32x 1.21.1 `block/` | mean colour d | pixel d (16x) | result |
|---|---|---|---|---|
| `legends/stone_granite` | `granite` | 2.8 | 10.2 | verified |
| `legends/stone_granite_smooth` | `polished_granite` | 2.4 | 9.3 | verified |
| `legends/stone_diorite` | `diorite` | 0.2 | 22.2 | verified |
| `legends/stone_diorite_smooth` | `polished_diorite` | 15.9 | 11.9 | verified |
| `legends/stone_andesite` | `andesite` | 1.0 | 8.6 | verified |
| `legends/stone_andesite_smooth` | `polished_andesite` | 0.7 | 7.4 | verified |
| `chisel/granite/granite` | `granite` | 29.6 | 30.9 | verified |
| `chisel/diorite/diorite` | `diorite` | 24.0 | 37.6 | verified |
| `chisel/andesite/andesite` | `andesite` | 15.2 | 20.5 | verified |
| `legends/smooth_stone` | `smooth_stone` | 10.5 | 7.0 | verified |
| `legends/prismarine_rough` | `prismarine` | 8.8 | 15.1 | verified |
| `legends/prismarine_bricks` | `prismarine_bricks` | 5.2 | 9.3 | verified |
| `legends/prismarine_dark` | `dark_prismarine` | 12.5 | 8.9 | verified |
| `legends/sea_lantern` | `sea_lantern` | 30.0 | 11.4 | verified |
| `legends/magma` | `magma` | 10.4 | 20.0 | verified |
| `legends/bone_block_side` | `bone_block_side` | 1.0 | 0.9 | verified |
| `legends/bone_block_top` | `bone_block_top` | 2.1 | 2.7 | verified |
| `legends/red_sandstone` | `red_sandstone` | 40.8 | 15.8 | verified |
| `legends/red_sandstone_top` | `red_sandstone_top` | 30.3 | 10.6 | verified |
| `legends/red_sandstone_bottom` | `red_sandstone_bottom` | 45.3 | 16.6 | verified |
| `legends/red_sandstone_carved` | `chiseled_red_sandstone` | 38.8 | 14.5 | verified |
| `legends/red_sandstone_smooth` | `cut_red_sandstone` | 43.0 | 14.7 | verified |
| `legends/basalt_side` | `basalt_side` | 2.5 | 6.4 | verified |
| `legends/basalt_top` | `basalt_top` | 5.1 | 9.3 | verified |
| `legends/polished_basalt_side` | `polished_basalt_side` | 0.8 | 5.6 | verified |
| `legends/polished_basalt_top` | `polished_basalt_top` | 4.1 | 10.8 | verified |
| `legends/blackstone` | `blackstone` | 3.4 | 9.1 | verified |
| `legends/blackstone_top` | `blackstone_top` | 0.4 | 6.2 | verified |
| `legends/stone_blackstone` | `blackstone` | 3.4 | 9.1 | verified |
| `legends/polished_blackstone` | `polished_blackstone` | 3.2 | 6.2 | verified |
| `legends/polished_blackstone_bricks` | `polished_blackstone_bricks` | 7.2 | 8.7 | verified |
| `legends/cracked_polished_blackstone_bricks` | `cracked_polished_blackstone_bricks` | 8.9 | 10.5 | verified |
| `legends/chiseled_polished_blackstone` | `chiseled_polished_blackstone` | 9.3 | 8.7 | verified |
| `legends/gilded_blackstone` | `gilded_blackstone` | 4.6 | 12.7 | verified |
| `legends/soul_soil` | `soul_soil` | 1.1 | 3.5 | verified |
| `legends/nether_gold_ore` | `nether_gold_ore` | 2.1 | 9.6 | verified |
| `legends/ancient_debris_side` | `ancient_debris_side` | 5.4 | 8.9 | verified |
| `legends/ancient_debris_top` | `ancient_debris_top` | 20.9 | 18.2 | verified |
| `legends/netherite_block` | `netherite_block` | 8.5 | 10.1 | verified |
| `legends/quartz_bricks` | `quartz_bricks` | 2.6 | 4.0 | verified |
| `legends/chiseled_nether_bricks` | `chiseled_nether_bricks` | 2.1 | 6.7 | verified |
| `legends/cracked_nether_bricks` | `cracked_nether_bricks` | 5.1 | 10.8 | verified |
| `legends/red_nether_brick` | `red_nether_bricks` | 7.6 | 12.3 | verified |
| `legends/nether_wart_block` | `nether_wart_block` | 1.3 | 4.4 | verified |
| `legends/soul_torch` | `soul_torch` | 0.5 | 1.2 | verified |
| `legends/soul_fire_0` | `soul_fire_0` | 311.0 | 123.1 | guess: colours differ, left out |
| `legends/soul_fire_1` | `soul_fire_1` | 347.8 | 127.1 | guess: colours differ, left out |
| `legends/concrete_white` | `white_concrete` | 0.0 | 0.7 | verified |
| `legends/concrete_orange` | `orange_concrete` | 0.1 | 0.8 | verified |
| `legends/concrete_magenta` | `magenta_concrete` | 0.1 | 0.8 | verified |
| `legends/concrete_light_blue` | `light_blue_concrete` | 0.2 | 0.8 | verified |
| `legends/concrete_yellow` | `yellow_concrete` | 0.1 | 0.8 | verified |
| `legends/concrete_lime` | `lime_concrete` | 0.0 | 0.8 | verified |
| `legends/concrete_pink` | `pink_concrete` | 0.1 | 0.7 | verified |
| `legends/concrete_gray` | `gray_concrete` | 0.1 | 0.4 | verified |
| `legends/concrete_silver` | `light_gray_concrete` | 369.2 | 123.1 | guess: colours differ, left out |
| `legends/concrete_light_gray` | `light_gray_concrete` | 0.0 | 0.7 | verified |
| `legends/concrete_cyan` | `cyan_concrete` | 0.0 | 0.6 | verified |
| `legends/concrete_purple` | `purple_concrete` | 0.1 | 0.5 | verified |
| `legends/concrete_blue` | `blue_concrete` | 0.0 | 0.5 | verified |
| `legends/concrete_brown` | `brown_concrete` | 0.0 | 0.5 | verified |
| `legends/concrete_green` | `green_concrete` | 0.1 | 0.5 | verified |
| `legends/concrete_red` | `red_concrete` | 0.0 | 0.8 | verified |
| `legends/concrete_black` | `black_concrete` | 0.0 | 0.9 | verified |
| `legends/concrete_powder_white` | `white_concrete_powder` | 0.9 | 7.9 | verified |
| `legends/concrete_powder_orange` | `orange_concrete_powder` | 2.7 | 8.6 | verified |
| `legends/concrete_powder_magenta` | `magenta_concrete_powder` | 3.7 | 9.3 | verified |
| `legends/concrete_powder_light_blue` | `light_blue_concrete_powder` | 1.2 | 9.2 | verified |
| `legends/concrete_powder_yellow` | `yellow_concrete_powder` | 2.1 | 8.3 | verified |
| `legends/concrete_powder_lime` | `lime_concrete_powder` | 1.2 | 6.5 | verified |
| `legends/concrete_powder_pink` | `pink_concrete_powder` | 4.0 | 10.9 | verified |
| `legends/concrete_powder_gray` | `gray_concrete_powder` | 2.0 | 5.3 | verified |
| `legends/concrete_powder_light_gray` | `light_gray_concrete_powder` | 1.5 | 8.9 | verified |
| `legends/concrete_powder_cyan` | `cyan_concrete_powder` | 0.7 | 6.1 | verified |
| `legends/concrete_powder_purple` | `purple_concrete_powder` | 1.9 | 6.4 | verified |
| `legends/concrete_powder_blue` | `blue_concrete_powder` | 1.8 | 6.0 | verified |
| `legends/concrete_powder_brown` | `brown_concrete_powder` | 0.3 | 7.0 | verified |
| `legends/concrete_powder_green` | `green_concrete_powder` | 1.1 | 6.2 | verified |
| `legends/concrete_powder_red` | `red_concrete_powder` | 1.5 | 5.0 | verified |
| `legends/concrete_powder_black` | `black_concrete_powder` | 1.6 | 6.5 | verified |
| `legends/smithing_table_top` | `smithing_table_top` | 8.0 | 3.8 | verified |
| `legends/smithing_table_side` | `smithing_table_side` | 5.3 | 6.8 | verified |
| `legends/smithing_table_front` | `smithing_table_front` | 4.0 | 7.5 | verified |
| `legends/smithing_table_bottom` | `smithing_table_bottom` | 1.4 | 3.2 | verified |
| `legends/blast_furnace_front` | `blast_furnace_front` | 6.9 | 22.2 | verified |
| `legends/blast_furnace_front_on` | `blast_furnace_front_on` | 7.5 | 18.2 | verified |
| `legends/blast_furnace_side` | `blast_furnace_side` | 9.0 | 8.2 | verified |
| `legends/blast_furnace_top` | `blast_furnace_top` | 7.4 | 5.7 | verified |
| `legends/blast_furnace_bottom` | `blast_furnace_top` | 241.2 | 80.4 | guess: colours differ, left out |
| `legends/smoker_front` | `smoker_front` | 1.2 | 8.7 | verified |
| `legends/smoker_front_on` | `smoker_front_on` | 12.2 | 14.5 | verified |
| `legends/smoker_side` | `smoker_side` | 5.6 | 8.8 | verified |
| `legends/smoker_top` | `smoker_top` | 11.1 | 8.6 | verified |
| `legends/smoker_bottom` | `smoker_bottom` | 15.2 | 8.8 | verified |

#### CTM rules (35)

| block | meta | texture | method | sources |
|---|---|---|---|---|
| `witchery:shadedglass` | 0 | `shadedglass_white` | ctm, 47 tiles, connect=tile | verified: block name (registry), metadata (item dump), texture (icon pairing) |
| `witchery:shadedglass` | 1 | `shadedglass_orange` | ctm, 47 tiles, connect=tile | verified: block name (registry), metadata (item dump), texture (icon pairing) |
| `witchery:shadedglass` | 2 | `shadedglass_magenta` | ctm, 47 tiles, connect=tile | verified: block name (registry), metadata (item dump), texture (icon pairing) |
| `witchery:shadedglass` | 3 | `shadedglass_light_blue` | ctm, 47 tiles, connect=tile | verified: block name (registry), metadata (item dump), texture (icon pairing) |
| `witchery:shadedglass` | 4 | `shadedglass_yellow` | ctm, 47 tiles, connect=tile | verified: block name (registry), metadata (item dump), texture (icon pairing) |
| `witchery:shadedglass` | 5 | `shadedglass_lime` | ctm, 47 tiles, connect=tile | verified: block name (registry), metadata (item dump), texture (icon pairing) |
| `witchery:shadedglass` | 6 | `shadedglass_pink` | ctm, 47 tiles, connect=tile | verified: block name (registry), metadata (item dump), texture (icon pairing) |
| `witchery:shadedglass` | 7 | `shadedglass_gray` | ctm, 47 tiles, connect=tile | verified: block name (registry), metadata (item dump), texture (icon pairing) |
| `witchery:shadedglass` | 8 | `shadedglass_silver` | ctm, 47 tiles, connect=tile | verified: block name (registry), metadata (item dump), texture (icon pairing) |
| `witchery:shadedglass` | 9 | `shadedglass_cyan` | ctm, 47 tiles, connect=tile | verified: block name (registry), metadata (item dump), texture (icon pairing) |
| `witchery:shadedglass` | 10 | `shadedglass_purple` | ctm, 47 tiles, connect=tile | verified: block name (registry), metadata (item dump), texture (icon pairing) |
| `witchery:shadedglass` | 11 | `shadedglass_blue` | ctm, 47 tiles, connect=tile | verified: block name (registry), metadata (item dump), texture (icon pairing) |
| `witchery:shadedglass` | 12 | `shadedglass_brown` | ctm, 47 tiles, connect=tile | verified: block name (registry), metadata (item dump), texture (icon pairing) |
| `witchery:shadedglass` | 13 | `shadedglass_green` | ctm, 47 tiles, connect=tile | verified: block name (registry), metadata (item dump), texture (icon pairing) |
| `witchery:shadedglass` | 14 | `shadedglass_red` | ctm, 47 tiles, connect=tile | verified: block name (registry), metadata (item dump), texture (icon pairing) |
| `witchery:shadedglass` | 15 | `shadedglass_black` | ctm, 47 tiles, connect=tile | verified: block name (registry), metadata (item dump), texture (icon pairing) |
| `securitycraft:reinforcedStainedGlass` | 0 | `glass_reinforced_white` | ctm, 47 tiles, connect=tile | verified: block name (registry), metadata (item dump), texture (icon pairing) |
| `securitycraft:reinforcedStainedGlass` | 1 | `glass_reinforced_orange` | ctm, 47 tiles, connect=tile | verified: block name (registry), metadata (item dump), texture (icon pairing) |
| `securitycraft:reinforcedStainedGlass` | 2 | `glass_reinforced_magenta` | ctm, 47 tiles, connect=tile | verified: block name (registry), metadata (item dump), texture (icon pairing) |
| `securitycraft:reinforcedStainedGlass` | 3 | `glass_reinforced_light_blue` | ctm, 47 tiles, connect=tile | verified: block name (registry), metadata (item dump), texture (icon pairing) |
| `securitycraft:reinforcedStainedGlass` | 4 | `glass_reinforced_yellow` | ctm, 47 tiles, connect=tile | verified: block name (registry), metadata (item dump), texture (icon pairing) |
| `securitycraft:reinforcedStainedGlass` | 5 | `glass_reinforced_lime` | ctm, 47 tiles, connect=tile | verified: block name (registry), metadata (item dump), texture (icon pairing) |
| `securitycraft:reinforcedStainedGlass` | 6 | `glass_reinforced_pink` | ctm, 47 tiles, connect=tile | verified: block name (registry), metadata (item dump), texture (icon pairing) |
| `securitycraft:reinforcedStainedGlass` | 7 | `glass_reinforced_gray` | ctm, 47 tiles, connect=tile | verified: block name (registry), metadata (item dump), texture (icon pairing) |
| `securitycraft:reinforcedStainedGlass` | 8 | `glass_reinforced_silver` | ctm, 47 tiles, connect=tile | verified: block name (registry), metadata (item dump), texture (icon pairing) |
| `securitycraft:reinforcedStainedGlass` | 9 | `glass_reinforced_cyan` | ctm, 47 tiles, connect=tile | verified: block name (registry), metadata (item dump), texture (icon pairing) |
| `securitycraft:reinforcedStainedGlass` | 10 | `glass_reinforced_purple` | ctm, 47 tiles, connect=tile | verified: block name (registry), metadata (item dump), texture (icon pairing) |
| `securitycraft:reinforcedStainedGlass` | 11 | `glass_reinforced_blue` | ctm, 47 tiles, connect=tile | verified: block name (registry), metadata (item dump), texture (icon pairing) |
| `securitycraft:reinforcedStainedGlass` | 12 | `glass_reinforced_brown` | ctm, 47 tiles, connect=tile | verified: block name (registry), metadata (item dump), texture (icon pairing) |
| `securitycraft:reinforcedStainedGlass` | 13 | `glass_reinforced_green` | ctm, 47 tiles, connect=tile | verified: block name (registry), metadata (item dump), texture (icon pairing) |
| `securitycraft:reinforcedStainedGlass` | 14 | `glass_reinforced_red` | ctm, 47 tiles, connect=tile | verified: block name (registry), metadata (item dump), texture (icon pairing) |
| `securitycraft:reinforcedStainedGlass` | 15 | `glass_reinforced_black` | ctm, 47 tiles, connect=tile | verified: block name (registry), metadata (item dump), texture (icon pairing) |
| `securitycraft:reinforcedGlassBlock` | 0 | `glass_reinforced` | ctm, 47 tiles, connect=tile | verified: block name (registry), metadata (item dump), texture (icon pairing) |
| `chisel:marble` | 0 | `marble` | repeat 2x2, four rotations | verified: block name (registry), metadata 0 = the worldgen variant (scans) |
| `chisel:limestone` | 0 | `limestone` | repeat 2x2, four rotations | verified: block name (registry), metadata 0 = the worldgen variant (scans) |

## 5. Sources and licence

Only vanilla pixels read at build time and Faithful-licensed sources may feed what ships
(direction.md). Checked 2026-10-25:

- **Faithful 32x Mods** (the official mod-support repo, `Faithful-Resource-Pack/Faithful-32x-Mods`,
  Faithful License v4): branches `1.20.x` and `main` only; nothing for 1.7.10 [verified via the
  GitHub API].
- **Faithful 32 Modded Edition, 1.7.10** (`F32Organization/Faithful32-1.7.10`, last push
  2024-08-12): a complete pack with `assets/` for 190 mod domains, including, with the number of
  files in `textures/blocks`: railcraft 99, twilightforest 84, witchery 20, chisel 48, ironchest 24,
  storagedrawers 100, projecte 14, openblocks 51, biomesoplenty 333, carpentersblocks 11,
  malisisdoors 23; bibliocraft, enderstorage and cfm have no `textures/blocks` (models) [verified
  via the API]. Its licence is one sentence in the README, "You may use/modify this pack in any
  way you see fit. You may not profit from its distribution or the distribution of derivatives",
  with no LICENSE file and no GitHub licence field. That is permissive and non-commercial but it is
  **not the Faithful License v4**, and Faithful's own FAQ only points to it as where "the old
  Faithful mod textures" live. **Owner's call** before anything from it is used; until then it is
  reference only, like the other packs.
- **GTNH-Faithful**: no such pack was found. GTNH's own texture work is not Faithful-based, and the
  search only turned up GregTech Revival 32x (CC-BY-NC-SA, GregTech CEu, not our mods) and a
  Faithful 32x Thaumcraft add-on (1.7.10, a mod we do not ship).
- **Faithful 32x modern Java releases** (same licence as the 1.7.10 zip we use): the source for
  option G above. Not yet fetched; the block names are 1.8–1.16 vanilla's [verified in Legends'
  texture list], the files' presence in those zips is [guess] until one is downloaded.

Nothing in the build above copies any of these: the maps are generated from the textures the
game already loads.

## 6. Render requests

For the render-loop agent (never run from here). `tools/textures/build_showcase.py --modded`
adds a second wall east of the vanilla one in the showcase copy of world-master: x 263–281 at
z 178, four rows of 19 from `tools/textures/showcase-modded.txt` (row 1 ores on stone, row 2
stone families, row 3 Twilight/organic/crystal, row 4 base and machine blocks; the file names
the blocks and metadata). IDs come from the copied world's own registry, so BoP (absent from
world-master) is skipped and reported. Two views are in `views-world-master.txt`:

1. **modded_wall** (272.0, 69.6, 186.5, yaw 180, pitch 6, 7000): the whole wall, same light as
   `texture_wall`. Render three variants: vanilla textures, QF v0 + `QFTextures-modded-v0.zip`
   (maps only, so identical until the shader reads them), and the same with `QF_PBR` once it
   exists. The question for the owner: which families clash most beside Faithful stone.
   **v1 (2026-10-25):** render `modded_wall` and `modded_close` as **vanilla vs QF v0 + modded-v0
   vs QF v0 + `QFTextures-modded-v1.zip`** (v1 above v0 in the pack order, both above
   `QuestForge.zip`). v1 changes the albedo: the top row's ores sit on Faithful stone at 32x, row 2's
   granite/diorite/andesite and red sandstone and row 3's concrete are Faithful's, and the
   SecurityCraft/Witchery glass should connect if the rules take (add a 3×3 of
   `witchery:shadedglass@11` and of `securitycraft:reinforcedStainedGlass@3` to the wall list to
   see it; they are not in the current 76). Judge: (a) do the ore tiles now read as one stone with
   the wall, (b) do Railcraft's overlay ores still show over the stone, (c) do the backports match
   the owner's "vanilla design, Faithful detail" rule.
2. **modded_close** (267.5, 70.2, 181.8, yaw 180, pitch 4, 7000): the ores and stones from 3.5
   blocks, the 16x-host problem at full size.
3. **Twilight clearing** and **Collision surface**: a daytime view in dim 7 (a forest edge with
   deadrock in sight, Highlands preferred) and in dim 2 (dark stone, dead dirt, a painted tree).
   World-master's region files for those dimensions can give the points the way forest_golden's
   were found; these judge terrain families in their own light, which the wall cannot.
4. **A mine**: a 1×2 tunnel at Y 28 through the plains_noon area would show the Legends and
   Railcraft ores as players meet them; the showcase builder can carve it if the agent wants it
   (not built here).

## 7. Follow-ups

Status 2026-10-25 (evening): 1, 2, 5 and 6 are done in v1 (section 4b); 3 goes to the owner's
Decisions sheet as a licence call; 4 waits for the owner's direction.

1. ~~Ore re-composite (option C)~~ done: `build_modded_textures.py`, 70 textures.
2. ~~Fetch Faithful 32x modern Java and map the backported blocks (option G)~~ done: 90 textures.
3. **Owner decision on F32 Modded Edition** (section 5); if yes, take Railcraft, Twilight,
   Witchery, Chisel, drawers, iron chests and BoP from it and record each file's source.
4. **Hand-drawn 32x** for the uncovered top families: Compact Machines, ProjectE, TragicMC dark
   stone and eroded stone, Twilight deadrock/towerwood/mazestone, Chisel marble and limestone.
5. ~~CTM rules for the modded glass and stone families~~ done: 35 rules; Railcraft's glass connects
   natively. Open: confirm in a render that Angelica applies them to modded blocks, and
   `glassPane=true` for the pane variants.
6. ~~Emissive faces list~~ done: `tools/textures/emissive-modded.txt`, `--emissive`. Open: rerun the
   item dump after texture changes (not run here).
7. **Next:** the ore re-composite's hosts beyond stone once QF v0 decides netherrack and end stone
   (then TragicMC's nether ores, HEE's end ores and Legends' nether gold follow the same path), and
   the four [guess] backports if the owner wants them anyway.
