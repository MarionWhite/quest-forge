# r13: in-game test of five landmarks

**Date:** 2026-10-24
**Plan:** [`r13/main.yaml`](r13/main.yaml); method follows the [v0 test](v0-ingame-test.md) and the [proof of concept](poc.md)
**Setup:** one slim dedicated server trial on Forge 10.13.4.1614 (`r13t`): the base set, BoP 2.1.0.2308, RWG alpha-1.5.2 and Chunk Pregenerator, plus `--overlay pack` for the pinned biome IDs. It ran the qf-tweaks jar with the RWG paint hook (f7fab36) through `build --jar`, so that jar was never staged or installed live. Java 8 with `-Xmx4G`. No client was launched.

## Summary

| Landmark | Verdict |
|---|---|
| Meteor crater (-9400, 8900) | **Shape right, surface wrong.** The bowl, the rim ring and the outer plain all come out at the planned heights. Everything is grass, though, and Wasteland pools pockmark the bowl and the ejecta ring. |
| Jungle tepui (15500, 13000) and its falls (14650, 12250) | **Reads as a mesa, but the wall is a slope.** The top is flat at 146–154 and drops to 68 below. The drop is spread over about 100 blocks (roughly 45°), not a cliff. Its three rivers step off the edge at the planned levels, but no water pours. |
| Calving front (13150, -20450) | **Wrong.** The bay freezes solid, and the icebergs are grass-rimmed, snow-dusted islands. Only one open-water patch remains, with 16-block stair-step edges. |
| Hot-spring terraces (-6454, 1448) | **The geometry is exact, but it doesn't read as terraces.** Six 7-block treads, each 190–270 blocks wide, with 15 pools on them. The pools cover 3–4% of each tread and half the slope is forest, so it looks like a stepped hillside with ponds. |
| Great falls (3383, -4811) | **The setting works, the falls don't.** It is a plunge pool at 90 in a box canyon about 65 blocks deep. The river reaches it in two steps (119 → 97 → 90), each lip a **dry grass sill**. No water falls. |

**The raised water levels come through exactly.** Wherever the plan raises water, 99% of those columns hold water in the game, and the surface sits on the planned level (98–100% within one block). The remaining columns are lily pads, BoP foliage or leaves over the water. This covers river steps, the tepui-top rivers (137–150), the falls pool and all nine hot-spring pool levels (67–121).

**The hook works.** Every painted biome decorated like itself, stored biomes match the plan 100%, the ground is within 1 block of the plan (p99), and there were 0 failed chunks.

Every problem below lies in the plan or the WorldPainter step, not in the game.

## 1. Pipeline

| Step | Time | Notes |
|---|---|---|
| `plan.py render` at full resolution (49,152 blocks at 16 per pixel) | **31.6 min** | Not the 5 min estimated. One process. |
| 16 × `plan.py expand --piece-size 2048` | 9–11 s each | |
| 16 × `wp_piece.js` build and export, `-Xmx6g` | 12–20 s each | 1.1 GB for all 16 exports. |
| `stitch.py --generator RWG`, spawn at (3000, -3500) | seconds | 256 region files, seed 20261017. |
| Server boot | 8 s | 1.04 GB working set. |
| Populate 5 areas (`PostProcessingOnly`) | 5.0 min in all | **95,188 chunks at 284–404 chunks/s, 0 failed.** Peak working set 1.15 GB, 20 TPS. |

**Pieces.** Index = (coord + 24576) // 2048.

| Landmark | Pieces | Why that many |
|---|---|---|
| Great falls | (13,9), (13,10) | |
| Calving front | (18,1), (18,2) | |
| Crater | (6..7, 15..16) | 2×2: the crater straddles a piece corner, and 2 pieces would have cut its rim. |
| Hot springs | (8..9, 12..13) | 2×2, for the same reason. |
| Tepui | (19..20, 17..18) | 2×2, for the same reason. |

**Population tasks**, each a square centred on the given block with the given half-width:

| Area | Centre | Half-width |
|---|---|---|
| falls | 3072, -4096 | 1000 |
| calving | 13312, -21000 | 1000 |
| crater | -9400, 8900 | 1330 |
| hot | -5800, 1950 | 900 |
| tepui | 15600, 12800 | 1250 |

**Hook.**
- `config/qftweaks-rwgpaint.cfg` held the bounding box of all 16 pieces: x [-12288, 18432), z [-22528, 14336).
- The log shows `Transform applied ...`, then 90,000+ `painted chunk(s) decorated by stored biome`.
- There were no exceptions besides the usual missing `ops.json` / `whitelist.json`.
- Gaps between pieces inside the box were never generated, so the hook's in-session safety check was never needed.

## 2. Water

Measured with `tools/world/check_water.py` (new). It compares the expanded pieces' `water.png` with the saved top block of every column.

| Area | Raised columns planned | Water on top | Surface = planned level (±1) | Levels | Unplanned water on land |
|---|---|---|---|---|---|
| Great falls | 618,209 | 93.5% (99% counting lilies and foliage) | 97.2% | 64 to 99, plus 119 | 0% |
| Tepui | 445,447 | 96.4% | 98.3% | 63 to 75 below; 115, 137 and 140–150 on and off the top | 0% |
| Hot springs | 118,358 | 93.9% | 98.7% | 67, 71, 86, 87, 93, 100, 107, 114, 121 (one per tread) | 0% |
| Crater | 65,183 (a lake NE of the crater, level 64) | 100% | 100% | 64 | **1.97%** (Wasteland pools) |
| Calving front | none | n/a | n/a | n/a | 0% |

- **Every step in the river levels is real.**
  - **Tepui NW**: 137 on top until radius 1110, then 72 within 10 blocks, a 65-block drop.
  - **Tepui E**: 146 → 115 → 67.
  - **Tepui N**: 140 → 75 → 66, through a gorge the river cut into the wall.
  - **Great falls**: 119 → 97 → 90.
- **But no water pours down any step.**
  - Each upper level ends at a strip of dry ground, 2–4 blocks wide (a grass sill), and the lower level starts beyond it.
  - Across the tepui NW step (x 14560–14620, z 12330–12395), **0 of 4,026 columns hold any water between y 73 and 136**.
  - The exported water is still water (id 9). Only 0.1–0.3% of surface water became flowing water.
  - So the falls are terraced pools with a cliff between them.
- **No crater pond exists in the spec.**
  - The crater floor is planned at y 62 with relief 255, and the ground there runs 53–66.
  - WorldPainter's sea-level water (62) fills whatever lies below it. The result is a lake over the north half of the bowl and puddles across the rest.
- **Wasteland pools again** (v0 issue 6):
  - 3,987 small pools, median 14 columns and at most 217.
  - 80% of them are in the painted Wasteland (the crater floor and the outer ejecta ring), the rest in Oasis and Outback.
  - In the render they are the blue speckle rings around the crater.

## 3. Decoration follows the painted biomes (hook)

Per chunk, by majority biome:

| Biome | Logs / leaves | Signature |
|---|---|---|
| BoP Temperate Rainforest (falls) | 166 / 1,396 | dense oak, BoP `colorizedLeaves2` 97 |
| BoP Rainforest (tepui) | 40 / 512 | |
| BoP Tropics | 33 / 119 | palms: BoP `logs2` 27, `colorizedLeaves1` 56 |
| BoP Cherry Blossom Grove | 29 / 472 | BoP `leaves3` 463 (cherry) |
| BoP Seasonal Forest | 53 / 577 | BoP `leaves2` 313–329 |
| BoP Oasis | 21 / 46 | palms |
| BoP Wasteland | 2 / 0.6 | BoP dead `logs3` |
| BoP Crag | 0.1–1.5 / 0.2–12 | bare |
| BoP Glacier | 0.4 / 4.7 | treeless |
| RWG Ice Ocean | | 98% of its surface is ice |
| RWG Cold Ocean | | 98% open water |

- Every biome matches its BoP signature, and no RWG noise forest showed up anywhere.
- Ores ran 530–1,180 per chunk. As in the PoC, this is RWG's own ore pass plus the painted biome's decorator. **It was not rebalanced** and still needs the ore-survey approval.
- Recurrent Complex and ChocolateQuest structures were not in this slim set.

## 4. Shapes

- **Crater**, median ground by distance from the centre:

  | Distance (blocks) | Median ground (y) |
  |---|---|
  | 0–300 | 62 (the floor) |
  | 400–500 | 92 |
  | 600–700 | 126 (rim crest) |
  | 800–900 | 107 |
  | 900–1300 | 99 (the outer plain) |

  - A 64-block rim around a 600-block bowl reads clearly in the hillshade.
  - The steep inner rim shows as a broken ring of dirt. That is WorldPainter's slope theme, not something planned.
- **Tepui.**
  - The top is flat (p10–p90 146–154 out to radius 900).
  - The wall has its 10th percentile at 139 at radius 925, 100 at 1000 and 66 at 1050, and its median at 148 at 1000 and 72 at 1100. So the drop takes 80–100 blocks of run: **a steep slope, not a cliff.** The spec's `wall: 60` is what widens it.
  - The same Rainforest covers the top and the lowland, so the plateau reads only through the shading.
- **Icebergs.**
  - They stand 10–30 blocks above the sea, with planned tops of 72–78. Their sides are grass under a 1-block `snow_layer`, and 11% of their tops are tallgrass or flowers.
  - `plan.py` gives every island a Beach (16) ring. Here that ring is grass (72%) with a little sand, which makes the bergs read as islands.
  - The glacier tongue ends in a snow-covered slope, not an ice face.
  - The frozen Ice Ocean around the bergs hides the coastline almost completely.
- **Hot-spring terraces.** Measured, they match the plan exactly. Each tread's median ground equals its planned top (88, 95, 102, 109, 116 and 123), and the treads are 190–270 blocks wide. The pools sit on them at the matching levels.

## 5. What looked wrong, and the fix for each

1. **The surface ignores the biome. This is still v0 issue 1.**
   - `wp_piece.js` neither applies per-biome terrain nor reads the `surface.png` that `plan.py` writes.
   - The results here:
     - The crater's Wasteland, Outback and Desert, and its black-sand floor, are all grass.
     - The Glacier is grass under snow, with tallgrass.
     - The hot-spring terraces have no travertine.
   - **Fix:**
     - In `wp_piece.js`, set terrain per biome from a table of biome to top and filler blocks: Glacier to packed ice over ice, Wasteland and Outback to hard dirt or sand, Desert to sand, Crag to stone.
     - Apply `surface.png`, starting with `black_sand`.
     - Add a `travertine` surface material to the spec (white hardened clay or quartz) for the terrace treads and the pool rims.
2. **Falls have dry lips.**
   - **Fix:** a post-export pass, in `stitch.py` or a new `tools/world/falls.py`. It would find every edge where the planned water drops by 3 or more blocks between neighbouring columns, then:
     - cut the sill down to the upper level;
     - write a column of falling water (block 8, meta 8) down the face to the lower surface;
     - add `TileTicks` for the top source blocks, so the game settles the flow when the chunk loads.
   - **Alternative inside `plan.py expand`:** where a river steps, extend the upper level by 1–2 blocks over the edge, so the export has water next to air at the lip. That still needs a block update to flow, so the post-pass is the reliable fix.
   - **Needs a client view to confirm.** A top-down render cannot show falling water.
3. **The calving bay freezes into pack ice.**
   - With the hook, the painted RWG Ice Ocean (210) gets vanilla's freeze step by its stored temperature, and 98% of it turns to ice. That is correct behaviour, but probably not the look the author wants.
   - **Fix:** paint the bay inside the bergs as RWG Cold Ocean (211), which stays open, and keep Ice Ocean for the outer sea.
   - The open patch that exists now has 16-block stair edges, because the biome edge follows the plan's pixels at sea (see 6).
4. **The icebergs read as islands.**
   - **Fix, in the spec:** `wall: 8` → `2` and the berg tops lower, so the sides are sheer.
   - **Fix, in `plan.py`:** skip the automatic Beach ring for islands inside a polar region, or flag them `iceberg: true`, so Glacier meets the sea directly.
   - Fix 1 then gives them packed ice and snow blocks.
5. **The tepui wall is a slope.**
   - **Fix:** in the spec, `wall: 60` → about `8`, for a sheer cliff of 70–80 blocks. Optionally paint the top with a different biome from the lowland, for example BoP Tropics or Rainforest with a lighter tree mix, so the top reads from above.
   - The NW, N and E falls then become real cliff falls once fix 2 exists.
6. **River banks step in 16-block squares.**
   - `expand` takes raised water from the plan's `water.png` (16 blocks per pixel) by nearest neighbour, so the shores of raised rivers and lakes show 16-block stair steps. They are visible all over the great-falls render and on the tepui's east river.
   - **Fix:** in `plan.py expand`, decide a column's raised level from a bilinear sample of the river mask, thresholded at 0.5, using the plan-pixel level only for the value. Better still, use the distance to the meandered river polyline at block resolution, as lakes already do with `pond_distance`.
7. **The crater has no pond, and Wasteland pools pockmark it.**
   - **Fix, in the spec:** add a `ponds` entry at (-9400, 8900), r about 300, level about 66, and lower the floor's `relief` from 255 to about 40. Then the bowl holds one clear lake instead of a half-lake and puddles.
   - For the pools there are three options, and the author decides:
     - (a) paint the crater floor and ejecta with a biome that makes no pools (BoP Outback or Crag);
     - (b) a hook option that skips lake features in painted chunks of chosen biomes;
     - (c) accept them as "meltwater pits".
8. **The hot-spring terraces don't read as terraces.**
   - **Fix, in the spec:**
     - make the treads 40–80 blocks wide instead of 190–270;
     - run pools along the lip of each tread (more pools, longer, nearly touching), so each step is mostly water;
     - paint the terraces Sacred Springs or another open biome instead of Cherry Blossom Grove, Seasonal Forest and Dead Forest;
     - add the travertine surface (fix 1).

## 6. Renders

All are in `C:\qf-world\renders\`, at 1 px per block, in block colours with hillshade and a 500-block scale bar:

| File | Area |
|---|---|
| `r13-test-crater.png` | 2,620 px, centre (-9400, 8900). The black strip on the right is east of the exported pieces. |
| `r13-test-tepui.png` | 2,460 px, centre (15600, 12800). |
| `r13-test-calving.png` | 1,960 px, centre (13312, -21000). |
| `r13-test-hot-springs.png` | 1,760 px, centre (-5800, 1950). |
| `r13-test-falls.png` | 1,960 px, centre (3072, -4096). |
| `r13-test-sheet.png` | All five scaled onto one sheet, with each landmark point marked. |

## Files and state

- `tools/world/check_water.py` (new): the raised-water check behind §2.
  - It compares planned water levels with the saved world, and finds unplanned water on land.
  - It saves each area's surface arrays as `.npz` for profiles.
- **The server trial stays on disk** at `%APPDATA%\.qf-trials\r13t`. Its world is 1.5 GB, with the five areas populated.
  - Results are in `pregen-result-*.json`, the log in `pregen.log`.
  - Before reusing it for another session: chunks RWG generates inside the hook rectangle in a *later* session would count as painted (poc.md), so add pieces only to a fresh stitch.
- The plan render, the pieces and the WorldPainter exports are in the session scratchpad (`r13t/`). They are not in the repo.

## Fixes and re-test

**Date:** 2026-10-24, same day. The author approved six fixes. They were made in the tools and in `r13/merge.py`'s fixups, the plan was re-rendered at full resolution (32 min), and the same 16 pieces were rebuilt. The pieces were stitched into a **fresh** world in the same trial (`r13t`; the first test's world is kept beside it as `world-test1`), and the same five areas were populated. Again 0 failed chunks, about 1.05 GB working set, 20 TPS. No client was launched.

| # | Fix | Where | Result |
|---|---|---|---|
| 1 | Calving bay: dark open water | merge fixup: an exact Deep Ocean (24) sea region over the bay, a basin to deepen it, `surface: packed_ice` on the bergs and the snout, `beach_skip: [89]` | **Works.** 2.79 M columns of the bay are Deep Ocean: **100% open water, 0.00% ice** (was 98% ice). Glacier tops are packed ice (934k columns) under a snow layer (232k). Bergs stand sheer from the sea. |
| 2 | Ground blocks per biome | `plan.py expand` writes `terrain.png` + `grounds.json`; `wp_piece.js` applies it in one WorldPainter mapping op | **Works.** The exports carry the right blocks per code, e.g. black sand 81% black stained clay + 19% gravel, stone_gravel 66/34, dirt_gravel 69/31, snow 83% snow block, packed ice 100%. The crater is scorched rubble, its eye black, the Outback terracotta, the Desert sand. |
| 3 | Sheer cliffs | `expand` recuts every plateau at block resolution (`recut_plateaus`); plateaus are in `plan.json` | **Works.** Tepui: the drop from 135 to 85 takes a **median of 7 blocks** of run, against 30 in the first test. Bergs, the snout, the great-falls bench and the hot-spring risers are cut the same way. |
| 4 | Waterfalls | new `tools/world/waterfalls.py`, run on the stitched world before populating | **Works.** 24 falls, 18,330 blocks of falling water. After population: tepui NW **148 → 72 (80-block sheet)**, N 145 → 81 (64), E 146 → 127 → 62 (21, then 66); great falls 119 → 97 (18) and **97 → 90 at the Great falls point (24)**. |
| 5 | Meteor crater as Crag | merge fixup: the Wasteland stamps and the bowl floor become BoP Crag (77) on `scorched` ground | **Works.** Unplanned water on land fell from 1.97% to **0.45%**, and what is left is the Oasis outside the crater. The bowl still holds its sea-level half-lake (§2; not part of this round). |
| 6 | Hot springs | merge fixup: Sacred Springs (197) on all six terraces; 146 pools placed in the treads, level pinned to `top - 1`, 1.6 radii clear of the lip | **Works.** Water covers **44%, 43%, 47%, 42% and 36%** of the five lower treads (the crown holds the vent: 11%), against 3–4%. Pool surfaces are on their tread levels (97.7% within one block). |

### How each fix works

1. **Calving bay** (`r13/merge.py`). Sea regions paint in list order, so the Deep Ocean circle (r 2300 round 13150, -21300) goes last and wins over RWG Ice Ocean. A basin (floor 34, wall 700) deepens the bay, so it reads dark between the bergs. Bergs and the snout get `surface: packed_ice`, a new plateau key. `beach_skip: [89]` is a new spec key: Glacier coasts get no automatic Beach ring.
   - `expand` also stops a plateau's biome at its wall. Before this, the plan's 16-block Glacier pixels round each berg froze into stepped skirts of sea ice. Now columns outside the wall take the nearest non-plateau pixel's biome, and the nearest sea's biome where they end below sea level.
2. **Ground blocks** (`plan.py` `GROUNDS`, `GROUND_RULES`; `wp_common.js` `qfGroundTerrains`).
   - Code 0 keeps WorldPainter's default. Mapping:
     - sand: Desert, Oasis, Xeric;
     - Mesa terrain: Mesa, Canyon;
     - terracotta: Outback;
     - stone + gravel: Crag, Alps;
     - snow blocks: Glacier, Tundra, Ice Plains and Mountains, frost and snowy biomes;
     - podzol: taiga, boreal, coniferous, spruce;
     - mycelium: Mushroom Island;
     - coarse dirt + gravel: Wasteland;
     - scorched: Volcano.
   - Water and shore biomes keep the default.
   - `surface.png` overrides the biome: `black_sand` (black stained clay + gravel), `scorched` (gravel, cobble, stone, black clay), `packed_ice`.
   - Built-in terrains are used only where they fit 1.7.10 (no granite and the like). The mixes are custom terrains made from legacy block IDs.
   - Cost: about 1 s per piece. WorldPainter's `applyHeightMap(...).applyToTerrain()` takes one `fromLevel(code).toTerrain(index)` per ground, and the index is the one in `Terrain.VALUES`, which is not the declaration order.
3. **Sheer cliffs** (`plan.py recut_plateaus`).
   - `expand` now builds the piece on a canvas 128 blocks wider on each side, so a wall near a piece edge sees the ground beyond it.
   - For each plateau, it tests the outline per block, with plan.py's coast warp on top of expand's own warp.
   - It takes the lowland from just outside the plan's smear band (64 blocks) and rebuilds the wall over `wall` blocks with the plan's profile.
   - Near the edge, it sets the top to the interior's level, which removes both the smear and the cubic overshoot. The first try left an 11-block parapet round the tepui.
   - River channels on the top keep their bed right to the outline. A top river pixel that already carries the lowland's level takes the top's level instead. Without that, the NW river stopped a pixel short, on a dry sill.
   - Water levels follow the wall: the top's level inside the outline, the lowland's outside it.
   - The tepui's `wall` went from 60 to 12 in the fixups, since `wall` is now real wall width.
4. **Waterfalls** (`tools/world/waterfalls.py`).
   - The pass finds raised water whose 4-neighbour is 3 or more blocks lower, and fills that column with block 8, metadata 8, from the upper surface down to the ground or water below.
   - To keep to real drops, a fall must:
     - land in water: in that column, or within 6 columns beyond it;
     - form a run of at least 3 columns;
     - drop at least 5 blocks somewhere;
     - come from a body of at least 64 columns.
   - Without the landing rule, the falls area got 223 "falls", nearly all raised river water spilling over its dry banks. With it, 7 remain there, all real.
   - Changed chunks get `LightPopulated=0`. The falls survive population as written.
5. **Crater** (merge fixup). BoP Wasteland decorates 10 poison lakes and 2 water lakes per chunk; Crag decorates none. BoP Volcano was the other option, but it decorates 20 lava lakes per chunk (javap of the BoP 2.1.0 jar), so it was not used.
6. **Hot springs** (merge fixup).
   - Tread masks are computed with plan.py's own warp, and pools are placed greedily in each tread: r 32–95, aspect 1–1.5, 1.6 r from the downhill lip and 1.05 r from the riser above, until about 42% of the tread is planned water.
   - `ponds` take an optional `level` (a new `plan.py` key), so a pool keeps its tread's level instead of the 10th percentile of the ground round it.
   - Three small overflow falls (9–12 blocks) formed where pools reach a riser.

### Still wrong or open

- **Sacred Springs is a forest.** It decorates 30 trees per chunk, its large sacred oaks among them, so between the pools the terraces are dense jungle canopy. The risers read only in the oblique view. Treads in plain ground or travertine (white stained clay, not added) would read as hot springs better. That is the author's call.
- **River banks still step in 16-block squares** (first test, item 6). Not part of this round. It shows at the great-falls pool and along the tepui rivers.
- **The great falls' upper step lands on a sill.** Two to four columns of ground at y 98–101 lie between the 119 water and the 97 pool, so the 18-block sheet lands on the sill, not in the pool. In the game it spills on into the pool at the first block update.
- **The crater bowl still floods at sea level** (first test, §2). The pond and relief fix (item 7) was not part of this round.
- **The tepui's foot is pocked.** Small gullies with puddles run along the foot, left from the plan's stepped outline beyond the 64-block band.
- **Ice and terrain on cliff faces.** WorldPainter lays a terrain only 3–7 blocks deep, so a berg's face is packed ice near the top and stone below.
- **Render palette.** Cobblestone shows red in `inspect_area.py`'s colours, so the scorched crater looks red-brown in the top-down render. The blocks are grey gravel, cobble, stone and black clay.

### Renders

All are in `C:\qf-world\renders\`. The top-down views are 1 px per block and use the same areas as the first test.

| File | What |
|---|---|
| `r13-test2-crater.png`, `-crater-oblique.png` | Crater top-down, and a view from the south |
| `r13-test2-tepui.png`, `-tepui-oblique.png`, `-tepui-oblique2.png` | Tepui top-down; the NW fall seen from the west; the E falls seen from the east |
| `r13-test2-calving.png`, `-calving-oblique.png` | Calving bay top-down, and a view from the south |
| `r13-test2-hot-springs.png`, `-hot-springs-oblique.png` | Hot-spring terraces top-down, and a view from the south |
| `r13-test2-falls.png`, `-falls-oblique.png` | Great falls top-down, and a view from the south |
| `r13-test2-sheet.png` | All of the above on one sheet, landmark points marked |

The oblique views are drawn from `check_water.py`'s `.npz` arrays (top block and height per column) by a scratch script. They show the shape, not a game render.

**Files.** The plan, pieces, exports, stitched world and scripts (`pieces.sh`, `all.sh`, `oblique.py`, `sheet.py`) are in the session scratchpad under `r13t2/`. The trial world in `%APPDATA%\.qf-trials\r13t\world` is this re-test.
