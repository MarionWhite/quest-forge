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
py -3.10 treegen.py autumn --palette vanilla-leaves
py -3.10 treegen.py redwood --palette bop --idmap C:\qfs\friends\world\level.dat
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
| `palettes.py` | Role → block palettes per species: `vanilla`, `vanilla-leaves`, `bop` |
| `schematic.py` | Role grid → blocks (log axis bits, patchy block mixing) → `.schematic` |
| `render.py` | Preview renderer (depth, sky occlusion, translucent glass) and contact sheets |
| `species/*.py` | One style module per species. Each module exposes `COUNTS` and `grow(rng, size) -> (Grid, info)` |

## Species

Every module draws its parameters per seed from ranges for each size class: small, medium, large and giant.
The giant class is for landmark trees.

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
| autumn | oak logs (birch for aspen); wool 35 for bright colour with stained clay 159 for depth, plus some oak and dark-oak leaves inside the crown |
| cherry | dark-oak logs; pink wool, white wool, white clay and magenta wool, with a few oak leaves |

Wool versus leaves: the autumn and cherry canopies use wool and clay because vanilla 1.7.10 has no orange,
red or pink leaves. To make them read as foliage rather than solid blocks, the canopies are kept ragged
and gappy, built from many small clumps, and mixed with real leaves. Whether this works can only be
judged in game. If it doesn't, run `--palette vanilla-leaves`, which maps every coloured role to real
leaves. The colour then has to come from the biome tint. The proper fix is the BoP re-skin below.

## Loading into WorldPainter (1.2–1.12 map, Minecraft 1.7.10)

1. Add a **Custom Objects** layer in the Layers panel, then **Add…** the schematics. You can select a
   whole species folder at once.
2. Each schematic stores WorldEdit `WEOffsetX/Y/Z`, which put the placement point at the trunk base. Big
   trees have one or two layers of root flare below that point, which WorldPainter sinks into the ground.
   Check that the **Offset** in the object editor reads `(-x, -z, -depth)` before mass-painting. If your
   WorldPainter version ignores the tags, set the offset by hand to the trunk centre.
3. Allow random rotation. Turn mirroring off: the trees are asymmetric, and mirroring is the Essential
   Trees advice for packs like these.
4. Mangroves: `y = 0` is the end of the roots. Place them on the lagoon or sea bed, with the object's
   "spawn in water" attribute on, in water 2–4 deep. The trunk base is 2.5–8 blocks up, so the arches
   stand clear of the surface.
5. Use the size classes as separate layers or with different frequencies. Giants are landmarks: paint them
   sparsely or place them by hand.
6. Leaves are written with the vanilla no-decay bit (meta | 4), so they never decay without a log nearby.

## BoP re-skin plan

Biomes O' Plenty block IDs are not pinned. Its `ids.cfg` pins only biomes, so the numeric IDs change from
world to world (`custom-trees.md` → "BoP IDs"). The generator therefore keeps blocks abstract until export:

1. Freeze the final mod list and create the real world once.
2. Run `treegen.py <species> --palette bop --idmap <world>\level.dat`. The `bop` palette names blocks by
   registry name (`BiomesOPlenty:logs3`, `BiomesOPlenty:leaves3`, …). `--idmap` resolves each name to that
   world's numeric ID from the FML `ItemData` in `level.dat`. IDs above 255 go into `AddBlocks`, which
   WorldPainter reads.
3. Before trusting the result, check every BoP `meta` in game with F3 or NEI. The meta values in
   `palettes.py` are BoP 2.1 for 1.7.10 from memory:
   - redwood: `logs3:0` with `colorizedLeaves1:3`;
   - mangrove: `logs2:2` with `colorizedLeaves1:1`;
   - cherry: `logs1:1` with `leaves3:1` (pink) and `leaves3:3` (white);
   - autumn: `leaves3:2` (maple), `leaves2:3` (orange) and `leaves1:0` (yellow).

   BoP leaves also store no-decay differently from vanilla.
4. The same seed gives the same shapes, so a re-skinned set matches the vanilla set tree for tree. Only
   the blocks change. To re-skin another species, add or override its entry in `BOP` in `palettes.py`.
   No growth code changes.

## Known weak spots

- Small ice and small autumn trees are only a few blocks wide and look crude next to the large ones.
- Redwood bark in vanilla is spruce, which is dark brown rather than red. BoP `logs3:0` fixes this.
- Glass in the previews is drawn translucent over a dark background. In game the colours are brighter.
