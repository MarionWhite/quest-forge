# Leaf frills (r010, option D) and the Stay True port (r011)

## r011: Stay True's leaves and crops, copied (supersedes the r010 frills and crop sprites below)
The owner's call on 2026-10-27 after r010 ("they make the tree look spiky"; crops "the wrong execution"; "actually check
what Stay True does"): copy Stay True into the private pack (CLAUDE.md, Licences exception). Its files stay in
`C:\qf-world
eference-packs\Stay True 1\` and are read at build time; nothing of it is committed or shown on the site.

What Stay True does, read from its JSON (`tools/textures/staytrue.py --dump` prints the table):
- Leaves: every leaf block picks one of 2-3 models (equal weight, all distances). Each is the leaf cube plus two vertical
  planes 2 blocks wide (x or z -7..25) and 1.75 tall (y -6..22; cross2 2 tall), rotated -22.5 or +22.5 degrees about Y so
  they cross near the block centre, unshaded, textured with a 32x32 round "bushy" clump (~51% opaque). Tinted, except
  birch (its PNGs are pre-coloured; the build divides the birch cube by 1.7.10's fixed 0x80A755 tint). Spruce and dark
  oak also vary the cube texture per variant.
- Crops: wheat 5-7 and ripe carrots/potatoes pick weighted models. Some are the plain crop with one of several sprites,
  the rest are two blocks tall: the same four planes at 4 and 12, y -1..16 with a "bottom" sprite and 16..32 with a
  "top" one, unshaded, no AO, untinted. Ripe wheat: 6 plain / 3,3,4,4 tall.

How it is built:
- `build_qf_textures.py --stay-true PATH` (staytrue.py): Stay True's PNGs under 1.7.10 names (leaves_<kind>, crop
  stages) and `textures/blocks/staytrue/*`, nearest 4x (16 px/block -> 64); and `assets/minecraft/qf/staytrue_models.txt`:
  per 1.7.10 block + metadata the weighted variants and every face as four vertices, rotated by Minecraft's FaceBakery
  rules (right-handed about the axis through the origin, no rescale). Also Stay True's animated diamond/emerald.
- qf-tweaks (branch leaf-frills, `StayTrueModels`, `LeafFrills`, `CropVariants`): the spec is read and its sprites
  registered at every blocks-atlas stitch; the pick is weight-proportional from a position hash. Leaves: a before-hook
  sets the variant's cube sprite as overrideBlockTexture, the after-hook adds the planes (block brightness, colour
  multiplier where Stay True tints). Crops: a head hook in renderBlockCropsImpl draws tall variants and skips vanilla's
  planes; one-block variants swap the icon. Switches: leafFrills.enabled (-Dqf.frills), cropVariants.enabled
  (-Dqf.cropvariants). Fancy leaves only. Without the spec file in the resource packs nothing changes.
- Cost: see "r011 results" at the end.

The r010 sections below are history.


The owner's call on 2026-10-27: build real outward leaf frills, like Stay True's, on Faithful 64x leaves. The options are in
`direction.md`, "Leaf frills: options on 1.7.10". This note says how the build works and what it costs.

## Where the hook is

- **Angelica 2.2.33 meshes every block through vanilla code.** Its chunk builder (Celeritas,
  `AngelicaChunkBuilderMeshingTask`) calls `RenderBlocks.renderBlockByRenderType` into a tessellator. It then converts
  the tessellator's raw quads into chunk vertices (`AngelicaChunkBuildContext.copyRawBuffer`). So any quad drawn
  during that call ends up in the chunk mesh, with the block's shader id and light.
- **Leaves mesh off the main thread.** Render type 0 is on Celeritas' thread-safe list. GTNHLib rewrites every read of
  `Tessellator.instance` in every non-excluded class into `TessellatorManager.get()`, which returns the calling
  thread's own tessellator. So our helper class must stay out of the coremod's TransformerExclusions. The first frill
  drawn on a worker thread checks this. If the redirect is missing, frills switch off and the log says why.
- **The hook:** qf-tweaks `LeafFrillsTransformer` patches `renderBlockByRenderType` right after its one
  `renderStandardBlock` call (the type-0 branch). The patch passes that call's result through
  `LeafFrills.after(result, this, block, x, y, z)`.
  - It does not patch `renderStandardBlock` itself: fences, panes and many mods' renderers call that for parts of other
    blocks.
  - Angelica's mixins on the method still match: they wrap the same invoke, which stays where it was.
  - Vanilla's WorldRenderer (OptiFine E7) goes through the same method, but frills are only tested under Angelica.
- **Which blocks:** vanilla leaves only, `minecraft:leaves` and `leaves2` (oak, spruce, birch, jungle, acacia, dark oak).
- **Fancy only:** Fast leaves are opaque cubes, in vanilla and in NotFine alike, and get no frills. Neither does the
  block-breaking overlay.

## How the quads are placed

v2 (worktree commit d705c6a) replaced v1's single layout with three styles (`leafFrills.style`). It also replaced v1's leaf-icon texture with the frill sprite. The rest of this section describes v1, which survives as the `tufts` style.

- **`edges` (the v2 default):** one card per **open edge** of the block, or `leafFrills.tufts` cards fanned across it.
  - An edge is open when both faces beside it are open and the block diagonally beyond it is not leaves.
  - Each card leans out along the edge's diagonal, ±20 degrees.
  - The cube's outline is made of these edges, so this style breaks the silhouette from every side. A flat face seen
    head-on gets nothing.
- **`tufts`:** v1's crossed pairs out of open faces, with `leafFrills.tufts` pairs per face and `leafFrills.droop`
  degrees of droop on the sides.
- **`hang`:** cards hinged near the top of open side faces, hanging `leafFrills.droop` degrees off the face. The leaves
  spill down over the face and below the block. Tops get short tufts, and open bottoms get a downward tuft.
- **Sprite:** `textures/blocks/leaves_KIND_frill.png`, from the texture agent's `tools/textures/leaves_dense.py
  frill()`.
  - qf-tweaks `LeafFrillsIcons` registers it in the blocks atlas at `TextureStitchEvent.Pre`, but only when the
    resource pack has it, so a missing PNG never stitches as missingno.
  - The whole sprite is mapped 1:1 onto the card. Its solid base row sits 0.15 inside the block, and its ragged top
    reaches `length` out.
  - Spruce has no frill sprite, so it falls back to a window of the leaf icon.
- **Each card is one double-sided quad pair,** so a card costs 2 quads.

v1 layout (`tufts`):

- **Which faces:** every face whose neighbour is neither an opaque cube nor leaves.
  - Interior faces of a canopy get none. Neither do faces against a log or the ground.
  - `leafFrills.faces` can limit this to `up`, `down` or `sides`.
- **One tuft per face** that passes the density test. The test is `hash & 255 < density * 256`; the default density
  is 0.75.
  - A tuft is two cards crossed at 90 degrees, turned 45 ± 22 degrees about the face normal.
  - Its centre sits within ±0.15 of the face centre.
  - Each card starts 0.19 inside the face and reaches `length × (0.7…1)` out. The default length is 0.31 blocks, five
    pixels at 16x.
  - Side tufts droop 15 degrees.
  - Both sides of each card are drawn, because terrain is back-face culled. That makes 4 quads per tuft.
- **No shimmer:** all the randomness comes from a hash of (x, y, z, face). A block always grows the same frills, at
  every rebuild and on every client.
- **Texture:** the leaf's own icon for that face, through a window the card's size, at a hashed offset. A dedicated
  leaf-edge sprite (r010-textures item 3) can replace it later. The card's outer edge maps to the top of the window.
- **Light:**
  - Brightness comes from the air block the tuft grows into.
  - Colour is the block's foliage colour, which includes Angelica's smooth biome blend.
  - The light is flat, like tall grass, and no directional shade is baked in. With a shader pack, Celeritas cancels
    vanilla's per-face shade itself, so a baked shade would only darken the albedo.
- **Shader:** the cards carry the leaf's `mc_Entity` (`block.1010`, MAT_LEAVES), so they get the pack's leaf treatment.
  - Iris computes their normals from the geometry.
  - `windOffset` phases the wind by vertex position, so tips sway with the canopy. The shadow pass uses the same mesh,
    so frills cast shadows.

## Switches

`config/qftweaks.cfg`:

| Key | Default | System property |
|---|---|---|
| `leafFrills.enabled` | `false` | `-Dqf.frills` |
| `leafFrills.length` | `0.3125` | `-Dqf.frills.length` |
| `leafFrills.density` | `0.75` | `-Dqf.frills.density` |
| `leafFrills.faces` | `all` | `-Dqf.frills.faces` |
| `leafFrills.style` | `edges` | `-Dqf.frills.style` (`edges`, `tufts`, `hang`) |
| `leafFrills.tufts` | `1` | `-Dqf.frills.tufts` (cards per edge, or tufts per face, 1-4) |
| `leafFrills.droop` | `15` | `-Dqf.frills.droop` (degrees) |

- **Off by default** until the owner has seen the renders. When it is off and nothing is being measured, RenderBlocks is
  not patched at all.
- **Low and Potato** should keep it off.

## Measuring the cost

`-Dqf.meshstats=FILE` turns on qf-tweaks `MeshStats`. It patches only Angelica's classes:

- It times each section build: the wall time of `execute` on its thread.
- It counts each section's vertices (`copyRawBuffer`), leaf blocks and frill quads.
- Every 2 s it appends a line of running totals to FILE.
- "Leafy" sections are those with 32 or more leaf blocks.

The frame time comes from FrameBench, in the same renderq boots: `renderq` job fields `jars` (the test qf-tweaks jar)
and `props` (`qf.frills=…`, `qf.meshstats=…`).

## Modded leaves (listed, not built)

Each needs its own check, because its renderer may not be type 0 through `renderStandardBlock`:

- Biomes O' Plenty: `leaves1-4`, `colorizedLeaves1-2`, `appleLeaves`, `persimmonLeaves`.
- Twilight Forest: `TFLeaves`, `TFLeaves3`, `DarkLeaves`, `GiantLeaves`, `TFMagicLeaves`. NotFine patches the
  Twilight leaves' fast/fancy handling.
- Chisel `leaves`, Witchery `witchleaves`, FoodPlus fruit leaves, TragicMC leaves, HEE `spooky_leaves`, Psychedelicraft
  `psycheLeaves`. These are the leaf entries in the shader's `block.1010`.

For blocks that are type 0 and extend `BlockLeavesBase`, extending the hook's block check is enough. The others need a
hook in their own renderer.

## Results

### v1 (render `1027-165243-r010-frills-a`, jar b373480, Faithful 64x, preset 3, 2560x1440)

**Look:** it does not read as leaves sticking out.
- The cards stand straight out of the face centre. Seen face-on they are edge-on, so they show as streaks smeared across
  the hedge.
- The silhouette barely changes: the tips reach only 0.31 out, and half the leaf icon is holes.
- A window of the leaf icon gives every card a straight-cut tip, so the cards read as slabs, not leaves.
- No z-fighting or light seams were seen. The cards are a touch darker than the cube faces.

**Cost** (`py -3.10 tools/textures/frills_cost.py --off fr1a0 --on fr1a1`; this PC, so frame times are a floor):

| scene | frame p50 ms off / on | p99 ms off / on | leafy sections built off / on | ms per leafy section off / on | vertices per leafy section off / on | frill quads |
|---|---|---|---|---|---|---|
| leaves_close | 2.73 / 2.66 (-3%) | 3.47 / 3.34 (-4%) | 912 / 809 | 3.21 / 3.20 (-0%) | 8139 / 9985 (+23%) | 390632 |
| tree_close | 2.93 / 2.89 (-1%) | 3.60 / 3.63 (+1%) | 184 / 305 | 2.24 / 2.36 (+5%) | 7879 / 9763 (+24%) | 148320 |
| forest_lit | 2.36 / 2.38 (+1%) | 3.23 / 3.45 (+7%) | 228 / 236 | 3.78 / 4.19 (+11%) | 9581 / 13908 (+45%) | 261556 |
| forest_far | 3.00 / 3.11 (+4%) | 3.63 / 3.70 (+2%) | 52 / 78 | 2.60 / 2.80 (+8%) | 9456 / 11904 (+26%) | 68764 |
| biome_roofed | 2.75 / 2.80 (+2%) | 3.65 / 3.76 (+3%) | 671 / 788 | 3.41 / 3.77 (+10%) | 11466 / 15711 (+37%) | 773796 |

Whole boot (every section built, from world load to the last scene):

| | sections | ms per section | vertices per section | leafy sections | ms per leafy section | vertices per leafy section | leaf blocks | frill quads |
|---|---|---|---|---|---|---|---|---|
| off | 7738 | 3.841 | 7176 | 2058 | 3.239 | 9415 | 281710 | 0 |
| on | 8167 | 3.696 | 8048 | 2216 | 3.378 | 12476 | 329186 | 1643068 |
| change | | -4% | +12% | | +4% | +33% | | |

- **Frame time:** no measurable change on this GPU. p50 moved -3% to +4% per scene, which is inside the noise.
- **Vertices:** +33% in leafy sections (+23% to +45% per scene) and +12% over all sections. On a weak GPU the vertex
  count is the cost to watch.
- **Chunk rebuilds:** +4% per leafy section over the whole boot, and up to +11% in the dense forest scenes.

### v2 (render `1027-171917-r010-frills-b`, jar d705c6a, Faithful 64x + the frill sprites, preset 3, 2560x1440)

All four looks use the texture agent's `leaves_KIND_frill` sprites. The "off" reference is fr1a0. Sheets:
`C:\qfb\frills\look\fr1b-full.jpg` (five columns: off, b1-b4), `fr1b-hedge.jpg` and `fr1b-hedge-1to1.jpg`.

| tag | look | settings | verdict |
|---|---|---|---|
| fr1b1 | edges | length 0.4, density 0.85, 2 per edge | **Best.** Whole leaves break the hedge's top edge and the canopy outline, which is Stay True's effect. The side edges change less. |
| fr1b2 | short, dense tufts | length 0.25, density 1, 3 per face, droop 10 | Bushier, but busy. Edge-on cards show as slivers across the faces, and it costs the most. |
| fr1b3 | long, sparse tufts | length 0.6, density 0.45, 1 per face, droop 20 | Long stretched streaks. Reads as cards, not leaves. |
| fr1b4 | hanging | length 0.7, density 0.9, 2 per face, droop 25 | Large smeared diagonal planes. Messy from below (tree_close, leaves_close looking up). |

**Cost**, whole boot (`frills_cost.py --off fr1a0 --on fr1bN`; tables per scene in `C:\qfb\frills\cost-fr1bN.md`):

| tag | vertices per leafy section | ms per leafy section (chunk build) | vertices, all sections | frame p50 per scene |
|---|---|---|---|---|
| fr1b1 edges | +26% | +14% | +8% | -2% to +4% (noise) |
| fr1b2 short tufts | +139% | +50% | +46% | +2% to +11% |
| fr1b3 long tufts | +19% | +7% | +8% | 0% to +4% (noise) |
| fr1b4 hanging | +60% | +18% | +22% | -0% to +7% |

- **Edges is the look to keep.** It gives the most per vertex: +26% in leafy sections, with frame time inside the noise.
- **Short tufts are out on cost.** They more than double the vertices in leafy sections, and they are the only look whose
  frame time rises beyond the noise.

### v2 tuning (render `1027-185527-r010-frills-c`, same jar, edges only, density 1)

| tag | settings | vertices per leafy section | ms per leafy section | vertices, all sections | frame p50 per scene |
|---|---|---|---|---|---|
| fr1b1 | length 0.4, 2 per edge, density 0.85 | +26% | +14% | +8% | noise |
| fr1c1 | length 0.5, 2 per edge | +29% | +9% | +10% | -1% to +4% (noise) |
| fr1c2 | length 0.4, 3 per edge | +42% | +11% | +15% | -1% to +5% (noise) |

- **c2 is the fullest fringe:** the hedge top and the oak's crown read as a mass of leaves spilling over the edge, the
  closest to Stay True's hedges.
- **c1 is the cheaper alternative:** fewer, longer leaves, and a little streakier from below.
- **Both went to the owner** as r010 scenes B and C, against no frills (`C:\qfb\shaderdev\r010\frills_scenes.json`).
  Sheets: `C:\qfb\frills\look\fr1c-full.jpg` and `fr1c-hedge-1to1.jpg`.
- **Leaf build time is noisy.** The per-leafy-section build time (+9..+14%) moves between boots by about as much as
  the looks differ, so treat the vertex count as the solid number.

## Crop variants (same branch, owner's yes 2026-10-27)

- **Why a hook:** Stay True's fields never tile, because each ripe wheat block picks one of five sprites. Angelica's
  MCPatcher CTM never reaches `RenderBlocks.renderBlockCrops`, so the pack's `ctm/wheat` `method=random` rule does
  nothing on 1.7.10.
- **The hook:** `CropVariantsTransformer` patches `renderBlockCropsImpl` (SRG `func_147795_a`). It passes the icon from
  `getBlockIconFromSideAndMetadata` through `CropVariants.pick(icon, x, y, z)`.
- **The sprites:** a crop stage `NAME` (wheat 0-7, carrots 0-3, potatoes 0-3) with `textures/blocks/NAME_v0.png`,
  `NAME_v1.png`, and so on in the pack gets one of those per block, picked by a position hash. They are registered at
  `TextureStitchEvent.Pre` only when they exist. `build_qf_textures.py --wheat dense|bushy` writes
  `wheat_stage_7_v0-4`.
- **The cost:** one identity-map lookup per crop block while a chunk is meshed, and nothing per frame.
- **The switch:** `cropVariants.enabled` (`-Dqf.cropvariants`), default true. With it off, RenderBlocks is not
  patched for crops.
- **Render:** `1027-190035-r010-crops-a`, with cv1a0 off and cv1a1 on, `farm` and `farm_close`, plus MeshStats.
  Results follow.

### Crop variants, results

**crops-a** (`1027-190035-r010-crops-a`, jar adec733, QF-w-bushy plus the five wheat sprites):
- The hook loaded, and the stitch found `wheat_stage_7 x5`.
- **The look:** on matched off exactly. Every ripe wheat drew the base sprite, so `pick`'s identity lookup never
  matched. The sprites themselves are fine: the tops of v0-v4 sit at rows 24, 18, 12, 6 and 0 of 64.
- **What was ruled out:** no Angelica mixin touches `renderBlockCropsImpl` or the identity of the sprite
  `registerIcon` returns (CTM, ParallelLoad, Celeritas, NotFine), and Forge's stitch order (re-gather icons, then Pre)
  holds.
- **The cost of the hook running and missing:** frame p50 rose 0-1%, and whole-boot ms per section rose 7%, but over
  different section counts (2365 off, 2244 on), so it is noise-level.

**crops-b** (`1027-192003-r010-crops-b`, jar 9a3acba):
- **The fix:** `pick` falls back to a name key (`getIconName`).
- **Diagnostics:** it logs the first icon at the hook, whether the match was by identity or by name, and whether the
  stitched atlas is Minecraft's blocks atlas.
- **Sprites:** the texture agent's QF-cropvar.zip (wheat x5, carrots x4, potatoes x4).
- **The log:** the stitch found `[wheat_stage_7 x5, carrots_stage_3 x4, potatoes_stage_3 x4]` in Minecraft's blocks
  atlas. The first icon at the hook was `carrots_stage_3`, and it matched the stitched sprite by identity.
- **The look:** carrots and potatoes now vary: mixed leaf shapes, and white flowers on some potatoes. **Ripe wheat
  did not change**: off and on differ only by waving noise.
- **What was ruled out for wheat:** the hash (simulated over the field, the five buckets get 25-38 blocks each), the
  sprites, the world (the wheat is meta 7), and the trial mods (none touches wheat, and Angelica has no crop mixin).
  The v4 log covered only the first icon, so it could not say why wheat missed.
- **The cost:** frame p50 changed by -1% to +0% and p99 by +1%. Whole-boot ms per section fell 6% and vertices per
  section fell 2%. All of that is noise.

**crops-c** (`1027-193327-r010-crops-c`, jar 9444d77): one log line per distinct crop sprite at the hook (identity,
by name, or no variants; the variant drawn; the stitched names).
- **The cause:** carrots and potatoes matched by identity. Every ripe wheat reached the hook as
  `minecraft:mcpatcher/ctm/wheat/0.png`, so it found no variants. Angelica's MCPatcher CTM overwrites
  `RenderBlocks.getBlockIconFromSideAndMetadata` with `CTMUtils.getBlockIcon(icon, block, side, meta)`, a lookup with
  no block position. The pack's `ctm/wheat` `method=random` rule therefore gives **every** ripe wheat tile 0, the
  shortest sprite. That happens in-game too, with the hook off, whenever a pack ships that rule. So the rule is not
  harmless: QF Textures should stop writing it once the hook ships.
- **The cost:** frame p50 rose 0-1%. Whole-boot ms per section rose 40% this time, against -6% in crops-b and +7% in
  crops-a for nearly the same code. The whole-boot figure is dominated by the world-load burst and swings that much
  between boots, so it can't measure a per-crop map lookup.

**crops-d** (`1027-193920-r010-crops-d`, jar 081cd00): `pick` now also gets the block and meta. When the icon is not a
stitched base sprite, it looks up the block's own sprite, `block.getIcon(0, meta)`, which has no CTM. The hook's
variants then replace the CTM tile. The bytecode verifies offline. One job, cv1d1 (hook on); the off reference is
cv1c0 (same packs and scenes).
- **The log (boot b1027200457):** ripe wheat reached the hook as `minecraft:mcpatcher/ctm/wheat/0.png`, took "the
  block's own sprite (a CTM tile reached the hook)" and drew `wheat_stage_7_v1`; carrots and potatoes still match by
  identity; unripe stages log "no variants" as intended.
- **The look:** **it works.** Ripe wheat now mixes all five heights. Near (farm_close) the rows break into an uneven,
  hand-placed field; far (farm) the gold mass has a ragged top instead of a regular grid of identical tufts. No
  missingno, no seams. Sheets: `C:\qfb\frills\look\cv1d.jpg`, `cv1d-near.jpg`.
- **The cost (frills_cost.py --off cv1c0 --on cv1d1):** frame p50 +1% (farm) and +0% (farm_close); p99 -9% / -7%.
  Whole boot: ms per section -1%, vertices per section +2% (the taller variants), all within noise. **Answer: no
  measurable cost.**
- **Handed off:** crop scenes `crops-variants` and `crops-variants-far` (A cv1c0 / B cv1d1) are in
  `C:\qfb\shaderdev\r010\frills_scenes.json` (5 scenes, FRILLS-READY updated).
- **Follow-up:** QF Textures should drop `mcpatcher/ctm/wheat` once the hook ships (it is what made every wheat tile 0).

## r011 results
Render `1027-220844-r011-staytrue-a` (st1a0 hooks off / st1a1 on, QF Textures --stay-true, jar 718473f).
Both boots clean (st1a1: both transforms applied, 11 model kinds, 50 sprites, 280 quads, none dropped, first tall crop drawn).

**Look** (sheets `C:\qfbrills\look\st1a*.jpg`): the planes break the cube outline into a soft, rounded crown and
hedge; the canopy is denser and less see-through than Stay True's textures on plain cubes (the clumps fill the gaps);
faint edge-on plane streaks show on flat hedge faces. Ripe wheat is a tall, uneven field with dark stalks and gold heads,
no seam at y 16. No re-render needed. Gems (`1027-221021-r011-gems-a`, gm1b): emerald is Stay True's concentric glass
face, diamond glassy.

**Cost** (`frills_cost.py --off st1a0 --on st1a1`): frame p50 +0 to +5%, leafy sections +23% vertices, rebuild time
per section unchanged.

Frills off `st1a0` vs on `st1a1`.

| scene | frame p50 ms off / on | p99 ms off / on | leafy sections built off / on | ms per leafy section off / on | vertices per leafy section off / on | frill quads |
|---|---|---|---|---|---|---|
| leaves_close | 2.72 / 2.76 (+1%) | 3.63 / 3.69 (+2%) | 685 / 666 | 3.40 / 3.39 (-0%) | 8033 / 9468 (+18%) | 231388 |
| tree_close | 2.90 / 2.91 (+0%) | 3.84 / 3.76 (-2%) | 185 / 365 | 2.31 / 2.38 (+3%) | 8069 / 9534 (+18%) | 130336 |
| forest_lit | 2.45 / 2.47 (+1%) | 3.41 / 3.73 (+9%) | 213 / 197 | 4.18 / 4.81 (+15%) | 9627 / 13573 (+41%) | 184828 |
| forest_far | 3.09 / 3.25 (+5%) | 3.89 / 4.08 (+5%) | 59 / 102 | 2.36 / 2.77 (+18%) | 8357 / 12354 (+48%) | 65432 |
| biome_roofed | 2.83 / 2.88 (+2%) | 3.88 / 3.93 (+1%) | 712 / 620 | 3.70 / 3.59 (-3%) | 11385 / 14523 (+28%) | 478936 |
| farm | 2.92 / 2.97 (+2%) | 3.86 / 3.85 (-0%) | 97 / 92 | 2.35 / 2.38 (+1%) | 7420 / 10022 (+35%) | 60476 |
| farm_close | 2.76 / 2.78 (+1%) | 3.70 / 3.61 (-2%) | 23 / 12 | 1.65 / 1.69 (+3%) | 5485 / 8039 (+47%) | 6256 |

Whole boot (every section built, from world load to the last scene):

| | sections | ms per section | vertices per section | leafy sections | ms per leafy section | vertices per leafy section | leaf blocks | frill quads |
|---|---|---|---|---|---|---|---|---|
| off | 8580 | 3.699 | 7085 | 1980 | 3.384 | 9366 | 290536 | 0 |
| on | 8475 | 3.555 | 7762 | 2055 | 3.321 | 11556 | 289481 | 1157924 |
| change | | -4% | +10% | | -2% | +23% | | |

