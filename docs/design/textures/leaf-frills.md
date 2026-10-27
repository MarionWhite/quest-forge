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

See "Results" below once the renders are in.
