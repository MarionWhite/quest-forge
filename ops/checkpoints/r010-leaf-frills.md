# r010 leaf frills checkpoint (orchestrator, 2026-10-27)

Owner's choice 2026-10-27 (ops/DECISIONS.md): **build real outward leaf frills**, like Stay True's, on Faithful
64x leaf art. Design notes and the cost estimate: docs/design/textures/direction.md, "Leaf frills: options on
1.7.10", option D. Stay True screenshots: docs/design/shaders/feedback/attachments/r009/.

## Goal
Leaf blocks that look full and bushy at their edges: extra crossed quads (like tall grass) sticking *outward* from
leaf faces that have air beyond them, so hedges and canopies stop reading as cubes.

## Constraints
- 1.7.10 has no JSON block models: this is code in mods/qf-tweaks (a transformer or a render hook), and it must work
  inside Angelica's chunk renderer. Read memory notes on the Angelica client and qf-tweaks before designing.
- Weaker PCs: measure the cost. Estimate was +30-60% vertices in leafy chunks and slower chunk rebuilds. Frills must
  have a config switch; Low/Potato presets may turn them off. The answer to "what does it cost" is a number.
- Vanilla leaves first (oak, birch, spruce, jungle, acacia, dark oak). Modded leaves (BoP, Twilight) need their own
  hook: list them, don't build them yet.
- Fancy vs Fast leaves: frills only in Fancy.
- Build and test in a worktree and a test game dir via `tools/trial/trial.py`; never write the live game.
  Renders only through renderq. `trial.py guard` before and after.

## Order of work
1. Design note (short): where to hook (RenderBlocks leaf path vs Angelica's), how quads are placed (which faces, how
   many, how far out, deterministic per block position so they don't shimmer), how the shader's leaf waving and
   subsurface light treat them.
2. Prototype on oak only. Render one lone tree, a hedge and a forest near and far, frills on vs off, plus the measured
   chunk-rebuild time and frame time.
3. Leaf-edge texture for the quads: coordinate with r010-textures.md item 3.
4. Hand the r010 scene (on/off/reference) to C:\qfb\shaderdev\r010 like texture_scenes.json.

## Progress log
