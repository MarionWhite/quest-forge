# Procedural trees (`tools/world/trees`)

This generator fills the gaps that the downloaded tree packs leave (see `C:\qf-world\trees\SOURCES.md`
and `docs/design/world/research/custom-trees.md`). It writes MCEdit `.schematic` files that WorldPainter
places as custom objects. It runs in Python only, with no Minecraft or WorldPainter needed. A full run of
all 256 trees takes under a minute on one core.

## Usage

```
py -3.10 treegen.py                       # all species, default counts -> C:\qf-world\trees\generated
py -3.10 treegen.py redwood mangrove      # only these species
py -3.10 treegen.py cherry --sizes medium,large --count 6 --seed 7
py -3.10 treegen.py autumn --palette vanilla-wool   # dyed-wool canopies (opt-in, see below)
py -3.10 treegen.py --palette bop --out C:\qf-world\trees\generated-bop   # BoP re-skin, pinned IDs
py -3.10 -I clean_packs.py               # cleaned copies of the downloaded packs
py -3.10 treegen.py --list                # species and default counts
```

It needs `numpy`, `nbtlib` and `Pillow`. These are installed for `py -3.10`; the default `python` lacks numpy.

The generator writes these files:
- `<out>\<species>\<species>_<size>_<n>.schematic`, which is gzip NBT with Width/Height/Length/Blocks/Data,
  `Materials "Alpha"`, and `AddBlocks` only when a modded ID is above 255;
- `<out>\<species>-preview.png`, a contact sheet with a side elevation and a plan view of every tree,
  in rows by size class.

The same `--seed` always produces the same trees. Change it to get a fresh forest.

## Files

| File | Role |
|---|---|
| `treegen.py` | Command-line tool: seeds, export, previews |
| `voxel.py` | Voxel canvas that stores *roles* (trunk, branch, root, leaf, accent, …) rather than blocks; drawing primitives (tapered capsules, ragged ellipsoids, lobed trunk layers) |
| `growth.py` | Growth algorithms: space colonisation (Runions et al. 2007), pipe-model radii, recursive limbs, fluted trunks with buttress roots, irregular multi-lobe crown envelopes |
| `palettes.py` | Role → block palettes per species: `vanilla`, `vanilla-wool`, `bop` (+ BoP-only variants dead, dark, jacaranda) |
| `clean_packs.py` | Cleaned, trunk-centred copies of the downloaded packs (see *Cleaned downloaded packs*) |
| `../blockids.py` | The pinned FML block registry: extract to `docs/survey/block-ids.tsv`, inject into a world |
| `schematic.py` | Role grid → blocks (log axis bits, patchy block mixing) → `.schematic` |
| `render.py` | Preview renderer (depth, sky occlusion, translucent glass) and contact sheets |
| `species/*.py` | One style module per species. Each module exposes `COUNTS` and `grow(rng, size) -> (Grid, info)` |
| `worldtest/` | WorldPainter test world: build, export, check and render (see *Testing in a real world*) |

## Species

Every module draws its parameters per seed from ranges for each size class: small, medium, large and giant.
The giant class is for landmark trees.

Small trees are too small for space colonisation: at 6–10 blocks it fills the crown into one blob.
Small ice and autumn trees therefore use `growth.small_frame` instead: a one-block trunk (crooked,
leaning or, for ice, a corkscrew with a 2×2 foot), 3–6 single-log limbs spread round it by the golden
angle (upper limbs steeper and shorter), one fork on about half of them, and separate foliage clumps
on the limb ends plus a crown dome. The forms keep their character at that size: oak is a low flat
dome on spreading limbs, maple an oval, elm an open vase with no centre clump, aspen a narrow birch
column; ice frost trees carry glass clumps with crystal points, shard trees fans of tapering
crystals round a clear-ice heart, weeping trees short arching limbs with glass curtains.

| Species | Count (S/M/L/G) | Model | Heights | Randomised per seed |
|---|---|---|---|---|
| `redwood` | 8/10/10/8 = 36 | recursive branching | 20–30 / 34–46 / 52–66 / 72–94 | trunk radius (giants 3.6–4.7, so trunks are 8–10 blocks wide), clear-bole fraction, crown width, buttress count, lean; giants add candelabra leaders, snag tops, fire-scar hollows, epicormic sprouts and dead stubs |
| `mangrove` | 6/10/10/4 = 30 | colonised crown + Bézier prop roots | 8–26 | root-skirt height (2.5–8), number of prop roots (5–19), forked roots, aerial drop roots from limbs (large and giant), crown radius |
| `baobab` | 6/8/8/5 = 27 | lobed trunk + recursive limbs | 9–30 | form (bottle *digitata* / column *grandidieri* / squat), bulge, fluting, limb count, leafy or bare (dry season) |
| `ice` | 8/10/8/5 = 31 | colonised or recursive | 7–36 | style (frost / shard / weeping), colour scheme (frost / glacier / aurora), twisting trunk, icicles, hidden glowstone hearts |
| `eucalyptus` | 6/10/10/5 = 31 | colonised lumpy crown | 14–62 | clear bole (35–62 %), forks, crown lumps, bend and lean, rough-bark "stocking" (40 %) |
| `petrified` | 8/10/8/5 = 31 | recursive gnarled limbs | 6–34 | style (snag / spire / split), snapped limbs, gnarled trunk path, moss on upward faces, fallen fragments |
| `autumn` | 10/12/10/5 = 37 | colonised irregular crown | 6–28 | form (maple / oak / elm vase / aspen), colour scheme (red / orange / yellow / mixed / turning) |
| `cherry` | 8/12/10/3 = 33 | colonised flat dome | 5–18 | split height, crown spread (0.6–0.85 × height), weeping form (25 %), petal drapes |

## Blocks and palettes

Trees are grown in roles: `trunk branch root bark core leaf leaf2 leaf3 leaf4 accent accent2 glow snow`.
Each role is mapped to blocks only at export time. A palette entry is a list of `(block, meta, weight)`.
When an entry has several blocks, they are mixed in patches using low-frequency noise. Logs (17, 162 and
the BoP `logs1-4`) get their axis bits from the growth direction: +0 up, +4 east-west, +8 north-south.

The `vanilla` palette uses only 1.7.10 blocks with IDs 0–175:

| Species | Blocks |
|---|---|
| redwood | spruce logs, spruce leaves with some dark-oak leaves, oak-leaf sprouts |
| mangrove | oak and jungle logs, jungle, oak and dark-oak leaves |
| baobab | acacia logs and leaves |
| ice | packed ice 174 trunk; stained glass 95 canopy (light blue, white, cyan, magenta, purple); ice 79 icicles; snow block roots; glowstone 89 |
| eucalyptus | birch logs (oak on the rough stocking); birch and spruce leaves |
| petrified | stone, stone brick (plain, cracked, mossy), cobblestone, mossy cobblestone |
| autumn | oak logs (birch for aspen); dark-oak, acacia, birch and oak leaves (spruce for the dead-leaf accent) |
| cherry | dark-oak logs; birch and oak leaves |

Wool versus leaves: vanilla 1.7.10 has no orange, red or pink leaves, so the autumn and cherry
canopies were first built from dyed wool and stained clay. The 2026-10-25 world test (below) settled
it against wool, so the default `vanilla` palette now uses real leaves for both, and the wool version
is the opt-in `--palette vanilla-wool` (`vanilla-leaves` is kept as an old name for `vanilla`):
- wool and clay are opaque full cubes. Each autumn tree in the test plot had about 140 canopy-top
  wool blocks with two air blocks above, which is a mob spawn floor at night, and each cherry about 77.
  Leaves are not a spawn surface;
- the canopy blocks skylight completely and hides the branch structure the crowns are built around;
- punching wool drops it, so every autumn grove is a free dyed-wool farm;
- seen from a distance, in the offline renders, the ragged wool clumps do read as foliage. Up close it
  is cloth texture on solid cubes. Nobody has looked at it in a client.

Leaves take their colour from the biome. Oak, dark-oak and acacia leaves follow the foliage tint, and
birch and spruce leaves have fixed colours, so the "yellow" clumps use birch to stay lighter whatever
the biome. Real autumn and blossom colour comes from the BoP re-skin below, or a biome with an autumn
foliage tint (to check in game before relying on it).

## Loading into WorldPainter (1.2–1.12 map, Minecraft 1.7.10)

What follows was measured on WorldPainter 2.27.1: from its exporter (`Bo2LayerExporter`, read with
`javap`) and from the test world, where all 650 generated trees were found where they should be.

1. Add a **Custom Objects** layer in the Layers panel, then **Add…** the schematics. You can select a
   whole species folder at once.
2. **Offset.** WorldPainter reads `WEOffsetX/Y/Z` from each schematic as the object's offset, so the
   object editor already shows the trunk-centre offset, for example `(-11, -10, -2)`, and nothing needs
   setting by hand. The offset block goes at terrain height + 1, the first air block above the ground,
   in the middle of the trunk. The one or two root-flare layers below it replace the top ground
   blocks, so the trunk comes out of the ground with no gap and no plinth. Downloaded packs that have
   no `WEOffset` tags (H2CO3, for one) get a guessed offset instead. In the test it was 1–3 blocks off
   the trunk centre, and some of those objects carry their own bedrock or stone foot. Load the
   copies in `C:\qf-world\trees\cleaned\` instead: they are trunk-centred and stripped of that foot.
3. **Rotation and mirroring.** Leave the object's default *random rotation* on. In WorldPainter it
   means a random quarter turn **plus** a 50 % mirror, so each tree appears in 8 orientations. The
   test found all 8, and every rotated log kept a correct axis (east-west and north-south swap on
   quarter turns). The generated trees have no handed blocks, so mirroring is safe and doubles the
   variety. Use "rotation only" just for objects with stairs, doors or text.
4. **Frequency.** The layer's *density* `d` and the painted intensity `v` (0–15; a 100 % brush is 15,
   50 % is about 8) give every painted block a `(1 + v²) / (64·d)` chance of starting an object. On top
   of that, the default *solid* collision mode skips an object whose blocks would hit blocks already
   placed. At a 50 % brush this means **density ≈ (mean spacing between trunks)²**. The default density
   of 20 is a near-solid thicket. Starting points, worked out from the formula and the tree footprints
   (not yet judged by eye in a painted forest):

   | Stand | Spacing | Density at a 50 % brush |
   |---|---|---|
   | small and medium broadleaf (autumn, cherry, ice) | 7–10 | 50–100 |
   | large broadleaf, baobab, eucalyptus | 14–20 | 200–400 |
   | redwood large, open savanna baobab | 20–30 | 400–900 |
   | giants | landmarks | place by hand, or a 1–2 % brush at density 400 |

   Leave the grid at 1 and random displacement at 0. A grid lays trees out in rows, which reads as an
   orchard. Grid plus zero displacement is only for tests like the one below.
5. **Mixing sizes.** Put a species' small, medium and large trees in one layer and weight them with each
   object's *frequency* attribute (default 100). For example: small 100, medium 100, large 40, and
   giants in their own sparse layer. Within a layer, an object's share is its frequency over the
   frequency sum, and the per-class file counts differ, so set the weights per file.
6. Mangroves: `y = 0` is the end of the roots. Place them on the lagoon or sea bed, with the object's
   "spawn in water" attribute on, in water 2–4 deep. The trunk base is 2.5–8 blocks up, so the arches
   stand clear of the surface. On dry land they stand on their root tips, as in the test plot.
7. Leaves are written with the vanilla no-decay bit (meta | 4), and the object's leaf-decay setting
   defaults to "no change", so they never decay without a log nearby.

## Testing in a real world (`worldtest/`)

```
py -3.10 worldtest/build_test_world.py --wp <WorldPainter dir>     # plan + WorldPainter export
py -3.10 worldtest/check_test_world.py --json C:\qf-world\trees\test\report.json
```

`build_test_world.py` writes a flat 1024 × 1024 grass world at y = 64 to `C:\qf-world\trees\test`.
It has a 3 × 3 set of 320-block plots, one per species plus one plot of the first 40 H2CO3 1.7.10
trees, each on its own biome (mega taiga, swamp, savanna, ice plains, forest, desert, birch forest), with a
few forest and meadow patches between them. Every plot is one Custom Objects layer, built through the
scripting API (`Bo2ObjectTube.load` and `new Bo2Layer`, then `dim.setLayerValueAt`, then
`dim.setCustomLayers`). The layers use density 1 and a grid one footprint wide, so every grid point
gets exactly one tree. The script then exports in the 1.2–1.12 Anvil format. WorldPainter runs as
`java -Xmx2g … ScriptingTool`, because `wpscript.exe`'s vmoptions ask for an 8 GB heap.

`check_test_world.py` reads the region files back. At every grid point it finds which schematic was
placed, and in which of the 8 orientations, by matching the exported blocks against each schematic
hung from its offset at (x, ground + 1, z). If nothing fits exactly, it searches shifts of ±3 blocks,
so floating, buried and off-centre placements show up. It also checks log axis bits and lists every
block ID above the ground. It writes `<plot>-top.png`, `<plot>-oblique.png` and `sheet.png` to the
test dir.

Results on 2026-10-25:
- **Placement.** 650 of 650 generated trees were exact fits: every one stood on its trunk centre at
  ground + 1, with no floating or buried trees. All 8 orientations appeared, and log axes were 100 %
  correct after rotation.
- **Block IDs.** Every block above the ground was in the palettes, apart from WorldPainter's own grass,
  flowers and double plants (31, 37, 38, 175) and the chest it puts at spawn.
- **H2CO3 pack.** The trees landed on the ground, but 1–3 blocks off their guessed centre.
- **Server load.** A slim server trial (`trial.py build --server --world …`, base set only) loaded the
  export and saved it again with 0 changed blocks across all plots. Its only warning was
  `Skipping BlockEntity with id minecraft:chest`, which is WorldPainter's spawn chest written with a
  1.13-style ID. It is not a tree problem.

## BoP re-skin and the pinned registry

In 1.7.10 FML hands out modded block IDs per world and saves the map in `level.dat` (FML → `ItemData`);
BoP's `ids.cfg` pins only biomes. A schematic with BoP blocks is therefore only right in a world that
carries the same map. The map is now pinned instead of waiting for the final world:

1. **Source.** The full-pack test server `C:\qfs\v0` (the whole pack: BoP 2.1.0.2308, RWG alpha-1.5.2,
   Forge 10.13.4.1614). Its `world` and `world-rwg` hold identical registries: 2427 blocks (83 of them
   BoP) and 135 mods. It is only ever read.
2. **Table.** `py -3.10 tools/world/blockids.py extract` writes `docs/survey/block-ids.tsv` (name, id).
   `blockids.py check <level.dat>` compares any world with it. BoP's tree blocks are `logs1`–`logs4`
   1143–1146, `leaves1`–`leaves4` 1147–1150 and `colorizedLeaves1`/`2` 1186/1187.
3. **Final world.** `tools/world/stitch.py … --registry C:\qfs\v0\world\level.dat` copies the whole
   FML compound (`ItemData`, `ModList`, alias and substitution lists) and the Forge compound into the
   stitched world. FML then keeps these IDs on first load instead of handing out fresh ones.
   (`blockids.py inject SRC DST` does the same for any level.dat.)
4. **Generate.** `py -3.10 treegen.py --palette bop --out C:\qf-world\trees\generated-bop` resolves the
   `bop` palette's registry names through the TSV (`--idmap <level.dat>` resolves them against another
   world instead). IDs above 255 go into `AddBlocks`, which WorldPainter reads. The same seed gives the
   same shapes, so the BoP set matches the vanilla set in `generated\` tree for tree.

The metas were read from the 2308 jar, not from memory. `BOPBlocks` registers each block as a category
(CAT1–4). The type is `meta & 3`, and the names come from the static arrays in `BlockBOPLog`, `BlockBOPLeaves`
and `BlockBOPColorizedLeaves`, in the same order as `en_US.lang`. Leaf decay works as in vanilla: a leaf
decays only with bit 8 set and bit 4 clear, so the generator writes `type | 4`. The memory note that
BoP stores no-decay differently was wrong.

| Block (ID) | meta 0 | 1 | 2 | 3 |
|---|---|---|---|---|
| `logs1` (1143) | sacred oak | cherry | dark | fir |
| `logs2` (1144) | ethereal | magic | mangrove | palm |
| `logs3` (1145) | redwood | willow | dead | giant flower stem |
| `logs4` (1146) | pine | hellbark | jacaranda | mahogany |
| `leaves1` (1147) | yellow autumn | bamboo | magic | dark |
| `leaves2` (1148) | dying | fir | ethereal | orange autumn |
| `leaves3` (1149) | origin | pink cherry | maple (red) | white cherry |
| `leaves4` (1150) | hellbark | jacaranda | | |
| `colorizedLeaves1` (1186) | sacred oak | mangrove | palm | redwood |
| `colorizedLeaves2` (1187) | willow | pine | mahogany | flowering oak |

Logs take axis bits as vanilla does: +4 for east-west and +8 for north-south.

The `bop` palette uses these blocks per species:

| Species | Wood | Leaves |
|---|---|---|
| redwood | redwood `logs3:0` | redwood (5 parts) and pine (1 part); oak-leaf sprouts |
| mangrove | mangrove `logs2:2` | mangrove (with some vanilla jungle) |
| autumn | oak (birch for aspen) | maple (red), orange autumn and yellow autumn; dying leaves as the accent; a little oak green |
| cherry | cherry `logs1:1` | pink cherry and white cherry, a few oak leaves |
| eucalyptus | birch (BoP 1.7.10 has no eucalyptus) | willow mixed with birch and spruce |
| **dead** (petrified shapes) | dead `logs3:2` | none |
| **dark** (autumn shapes) | dark `logs1:2` | dark leaves, some vanilla dark oak, dying-leaf accent |
| **jacaranda** (cherry shapes) | jacaranda `logs4:2` | jacaranda (purple) |
| baobab, ice, petrified | as `vanilla` | BoP has no baobab or petrified wood |

`dead`, `dark` and `jacaranda` are BoP-only variants (`VARIANTS` in `palettes.py`): each reuses an existing
growth model under its own name and seed. The set on 2026-10-25 holds 357 trees in 11 species, with
previews at `C:\qf-world\trees\generated-bop\<species>-preview.png`. The previews colour BoP blocks with the
mean colour of their textures in the jar (`BOP_COLOURS`), so autumn reads red, orange and yellow and
cherry reads pink. Nobody has looked at them in a client yet.

## Cleaned downloaded packs (`clean_packs.py`)

```
py -3.10 -I clean_packs.py            # -> C:\qf-world\trees\cleaned\<pack>\..., plus cleaned\report.tsv
```

This writes cleaned copies of the downloaded packs, using the `-1.7.10` copies where a pack has them.
It only parses their NBT and never writes into the pack folders. For each schematic it:
- strips bedrock and the raw 1.8+ technical IDs (166 barrier, 217 structure void, 255 structure block);
- finds the trunk. This is the cluster of log columns, at least half as tall as the tallest column,
  that reaches lowest. Without logs, huge-mushroom stems stand in, and failing those, the lowest layer
  that is not ground;
- sets the base (the layer that goes at terrain + 1). Where the author placed grass, flowers or
  saplings in the lower 40 % of the object, their lowest layer is the base. This matters for H2CO3,
  whose logs are all six-sided bark, so roots and trunk look alike. Otherwise the base is the lowest
  trunk log, raised above any dirt or grass plate round the trunk foot;
- deletes ground blocks (grass, dirt, stone, cobble, sand, gravel, clay, mycelium, soul sand,
  farmland, sandstone) below the base. Logs below it stay: they are roots and go into the ground;
- crops empty borders, then writes `WEOffsetX/Y/Z` so the trunk centre lands on the base.

Results on 2026-10-25: 4915 files were written, and every one has a trunk-centred offset (4808 had
none; Mythix13's 107 WorldEdit offsets were replaced). Blocks were stripped from 487 files, among them
1252 bedrock (all in H2CO3). Rock folders were skipped (Jamziboy `Rockrepository`, sijmenvb `rocks`).
`report.tsv` lists each file's trunk method, the blocks stripped, and the old and new offsets. A
sample check found the bases right. Some H2CO3 trees stand on a stone outcrop at the trunk foot,
which was kept.

## Known weak spots

- Redwood bark in vanilla is spruce, which is dark brown rather than red. The BoP set uses `logs3:0`.
- Glass in the previews is drawn translucent over a dark background. In game the colours are brighter.
- With the vanilla leaves palette, autumn and cherry trees are green apart from the birch-lightened
  clumps. The BoP set (`generated-bop`) has their colour, but it needs the pinned registry in the world.
- BoP dark leaves are almost black, so the `dark` variant reads as a silhouette.
- Small trees of the other species still use the large-tree growth models. They have not been
  reworked onto `small_frame` or looked at closely at that size.
