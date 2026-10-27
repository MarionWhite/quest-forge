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

### 2026-10-27 session 1 (leaf-frills agent)
- Worktree `C:\qfb\frills\wt`, branch `leaf-frills` (mod code lives there; docs, ops and renderq changes go on main).
- Angelica 2.2.33 internals read (decompiled with CFR 0.152 into `C:\qfb\frills\ang\src`): Celeritas meshes every
  block with vanilla `RenderBlocks.renderBlockByRenderType` into `Tessellator.instance` (GTNHLib redirects that GETSTATIC
  to a per-thread tessellator in every non-excluded class), then `AngelicaChunkBuildContext.copyRawBuffer` turns the raw
  quads into Celeritas vertices. Leaves (render type 0) mesh off-thread. So frills = extra quads added right after
  `renderStandardBlock` returns inside `renderBlockByRenderType`; the helper class must NOT be in the coremod's
  TransformerExclusions (else it writes to the main thread's tessellator).
- Next: design note `docs/design/textures/leaf-frills.md`, then code (LeafFrillsTransformer + LeafFrills + MeshStats).
- Code committed on branch `leaf-frills` (b373480): LeafFrills, LeafFrillsTransformer, MeshStats(+Transformer), TweaksConfig
  keys leafFrills.enabled/length/density/faces (sysprops qf.frills, qf.frills.length, ...), SRG stubs in stubs/net/.
  Jar builds (`build.bat --no-install` from PowerShell) -> `C:\qfb\frills\wt\mods\qf-tweaks\QuestForgeTweaks-1.0.jar`.
- renderq got job fields `jars` and `props` (main, 1979f42). The RUNNER must be restarted to load them: at 16:47 I set
  `renderq.py pause --after-boot` (boot b1027164553 = texture agent's wall ladder). Next: after that boot,
  `renderq.py stop`, `renderq.py start`, `renderq.py resume`. IF THE RUNNER IS STILL PAUSED BY ME, RESUME IT FIRST.
- 16:53 runner restarted on the new code (pid 27096) and RESUMED (no PAUSE left). Views: `forest_far` added (bec6cd0);
  design note `docs/design/textures/leaf-frills.md` (bec6cd0). Offline check: the RenderBlocks patch verifies with ASM's
  CheckClassAdapter against the SRG RenderBlocks (`C:\qfb\frills\verify`).
- Submitted `1027-165243-r010-frills-a` (spec `C:\qfb\frills\spec-r010-frills-a.json`): tags fr1a0 (off) / fr1a1 (on),
  Faithful 64x, preset 3, 2560x1440, cost mode, scenes leaves_close,tree_close,forest_lit,forest_far,biome_roofed; jar
  `C:\qfb\frills\jars\v1\QuestForgeTweaks-1.0.jar` (=b373480); MeshStats to `C:\qfb\frills\stats\fr1a{0,1}.txt`.
  Client log of each boot: `C:\qfb\shaderdev\rounds\logs\<boot>.log` (check "[QuestForgeTweaks] Transform applied: leaf
  frills" and "meshing on '...' with its own tessellator").
- Next: when it lands, look at frames (contact sheet), compute cost (script), tune, then step 3 (edge texture) and 4.
- frills_cost.py committed: `py -3.10 tools/textures/frills_cost.py --off fr1a0 --on fr1a1`; sheet script `C:\qfb\frills\scripts\sheet.py OUT off on scene[:x,y,w,h]...`

### Note from the texture agent (2026-10-27): the frill texture exists
`build_qf_textures.py --leaves dense|crowns|faithful` writes `assets/minecraft/textures/blocks/leaves_<kind>_frill.png`
(+ `_n`/`_s`) for oak, big_oak, birch, jungle, acacia (spruce keeps needles): 64x, grey like vanilla leaves (tint it with the
block's colour multiplier), whole Faithful leaves on transparency, solid at the BOTTOM edge (sit that edge on the leaf face),
ragged leafy top reaching 55-90% of the height. Register it as an icon named `leaves_<kind>_frill` (registerIcon in the
blocks atlas). Generator: `tools/textures/leaves_dense.py frill()`. Test zips: C:\qfb\textures\diag\QF-l-dense.zip (and -crowns, -faithful).
- 17:05 `trial.py guard`: OK. Boot b1027170341 (fr1a0) started 17:03; fr1a1 boots after it (ETA ~17:15). Session 1 exits
  here (second wait). Journal entry in ops/journal/textures.md.

## Resume here (session 2)
1. `renderq.py results 1027-165243-r010-frills-a`. In both boot logs (`C:\qfb\shaderdev\rounds\logs\b*.log`, the two
   boots with jobs fr1a0 / fr1a1) check: "Transform applied: leaf frills hook", "meshstats ... (1 method(s))" twice,
   "leaf frills ON" (fr1a1) / "off" (fr1a0), "meshing on '...' with its own tessellator", no "leaf frills OFF" error,
   no crash. If the hook says "found 0", Angelica's mixin moved the invoke: hook renderStandardBlock's RETURN instead.
2. Sheet: `py -3.10 C:\qfb\frills\scripts\sheet.py C:\qfb\frills\look\fr1a.jpg fr1a0 fr1a1 leaves_close tree_close
   forest_lit forest_far biome_roofed`, plus crops of the hedge (leaves_close) at full scale. Judge: do tufts read as
   leaves sticking out, any seams/z-fighting, light too bright/dark vs the cube faces, density.
3. Numbers: `py -3.10 tools/textures/frills_cost.py --off fr1a0 --on fr1a1 --md C:\qfb\frills\cost-fr1a.md`; paste into
   leaf-frills.md "Results" (frame p50/p99, ms and vertices per leafy section) and commit.
4. Tune (length/density/faces/droop, light) with new tags (fr1b0/fr1b1 ...) via `props` (qf.frills.length=...,
   qf.frills.density=..., qf.frills.faces=...), same jar; code changes = rebuild jar into `C:\qfb\frills\jars\v2\`.
5. Step 3 (edge sprite, with r010-textures item 3) and step 4 (scene hand-off to C:\qfb\shaderdev\r010, like
   texture_scenes.json: on/off/reference).
- 17:06 fr1a0 boot log (trial `%APPDATA%\.qf-trials\renderq\logs\latest.log`): leaf-frills hook and both meshstats
  patches applied under Angelica; MeshStats writing (2434 sections by 17:05). fr1a1 (frills ON) is the real test.
