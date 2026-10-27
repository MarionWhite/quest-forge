# Leaf frills (r010, option D)

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
