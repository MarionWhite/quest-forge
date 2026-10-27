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
- Step 3 input already exists: the texture agent (477eecc) writes `assets/minecraft/textures/blocks/leaves_<kind>_frill.png`
  (kinds = leaves_dense.KINDS: oak, spruce, birch, jungle, acacia, big_oak) into QFTextures when built with
  `--leaves faithful|dense|crowns`: whole Faithful leaves in a blob, BASE AT THE BOTTOM ROW, ragged top at 35-75% of the
  height, transparent above. To use it: register `leaves_<kind>_frill` in the blocks atlas (TextureStitchEvent.Pre, map
  type 0) only if the resource exists (else keep the leaf icon: a missing PNG would stitch as missingno), map the whole
  sprite onto the card at 1:1 scale (card ~1 block tall: base just inside the face, tip ~0.55-0.75 out), meta&3 -> kind
  (leaves: oak, spruce, birch, jungle; leaves2: acacia, big_oak). Needs stubs for TextureMap (func_94245_a registerIcon,
  func_130086_a getTextureType) and the Forge event (forge universal jar is on build.bat's classpath).

### 2026-10-27 session 2 (leaf-frills agent)
- 17:15 step 1 DONE: both boots (b1027170341 fr1a0, b1027170725 fr1a1) show the hook, both meshstats patches, "leaf frills
  off"/"ON", "meshing on 'Chunk Render Task Executor #9' with its own tessellator", no frills error. The SplashProgress
  "crash report" is the usual specs printout (in every boot). guard OK 17:11.
- Step 2 DONE: sheets `C:\qfb\frills\look\fr1a.jpg`, crops `C:\qfb\frills\look\fr1a-crops.jpg`. Verdict: v1 does NOT read
  as leaves sticking out. Cards stand perpendicular at face centres, so face-on they are edge-on streaks smeared across the
  hedge; the silhouette barely changes (0.31 out, leaf icon half holes); the window of the leaf icon gives straight-cut
  card tips. No z-fighting or light seams seen; cards a touch darker than faces.
- Step 3 DONE: `C:\qfb\frills\cost-fr1a.md` (frame p50 within noise -3..+4%; leafy-section vertices +33% (+23..+45% per
  scene); leafy-section build time +4% (+0..+11%)).
- Step 4/5 code DONE (17:18): v2 on branch leaf-frills **d705c6a**, jar `C:\qfb\frills\jars\v2\QuestForgeTweaks-1.0.jar`
  (1.1.0+20261027.d705c6a2). New: `LeafFrillsIcons` registers `leaves_<kind>_frill` at TextureStitchEvent.Pre when the
  pack has it (registered from QuestForgeTweaksContainer.registerBus, client + frills on); styles `qf.frills.style=
  edges|tufts|hang`, `qf.frills.tufts=1-4`, `qf.frills.droop=deg`. Sprite pack for trials:
  `C:\qfb\frills\QF-frill-sprites.zip` (the 5 kinds' frill PNGs + _n/_s, extracted from QF-l-faithful.zip), stacked on
  Faithful 64x. Design note updated (styles, switches).
- 17:19 SUBMITTED `1027-171917-r010-frills-b` (spec `C:\qfb\frills\spec-r010-frills-b.json`, queue ETA ~17:40-17:45):
  fr1b1 edges len 0.4 dens 0.85 x2 | fr1b2 tufts short/dense len 0.25 dens 1 x3 | fr1b3 tufts long/sparse len 0.6 dens
  0.45 x1 droop 20 | fr1b4 hang len 0.7 dens 0.9 x2 droop 25. Off reference = fr1a0. MeshStats `C:\qfb\frills\stats\fr1b*.txt`.
- guard OK 17:20. Session 2 exits here (wait > 10 min).

## Resume here (session 3)
1. `renderq.py results 1027-171917-r010-frills-b`. In each boot log (`C:\qfb\shaderdev\rounds\logs\b*.log` after 17:20)
   check "frill sprites for [oak, birch, jungle, acacia, big_oak]" (if [] the sprite pack did not load: check the job's
   resourcepacks), "leaf frills ON (style ...)", "own tessellator", no exception from LeafFrills/LeafFrillsIcons.
2. Sheets: `py -3.10 C:\qfb\frills\scripts\sheet.py OUT fr1a0 fr1bN leaves_close tree_close forest_lit forest_far
   biome_roofed` for N=1..4 plus hedge crops (`leaves_close:780,680,980,440`, `tree_close:650,850,1250,450`,
   `leaves_close:500,150,700,450`). Better: one 5-column sheet (off, b1..b4) per crop, so the owner sees the looks side by side.
3. Cost: `py -3.10 tools/textures/frills_cost.py --off fr1a0 --on fr1bN` for each; table in leaf-frills.md Results "v2".
4. Pick/tune 1-2 more if a look has seams (edges cards poking through neighbours, hang cards in the ground), then hand
   off: write `C:\qfb\shaderdev\r010\frills_scenes.json` in texture_scenes.json's format (r009's: id, name, question,
   notePrompt, options[key,label,img,ms,desc]); options = off (fr1a0), the looks, and a Stay True reference crop. Don't
   overwrite the texture agent's texture_scenes.json.
5. Commit main-repo docs/ops hunks only; journal ops/journal/textures.md.

## Added by the orchestrator (2026-10-27): crop-variant hook, owner said yes
Build the hook described in ops/DECISIONS.md ("crop variants via a small qf-tweaks hook"): a transformer in
`RenderBlocks.renderBlockCrops` that picks one of the five ripe-wheat icons (and carrot/potato variants if the texture
agent supplies them) by a block-position hash, registered like the frill sprites. Same branch/worktree as the frills,
its own config switch. Sprites: `build_qf_textures.py --wheat bushy` (ops/checkpoints/r010-textures.md, step 2).
Render a field near and far, hook off vs on, through renderq; measure chunk-rebuild cost with MeshStats.

### 2026-10-27 session 3 (leaf-frills agent)
- 18:50 step 1 DONE: frills-b boots all show "frill sprites for [oak, birch, jungle, acacia, big_oak]", "leaf frills ON
  (style ...)", own tessellator. "Unable to determine registrant mod for LeafFrillsIcons" is FML's harmless warning for a
  coremod-container handler (it still registers). guard OK 18:48.
- Sheets: `C:\qfb\frills\look\fr1b-full.jpg` (5 cols off,b1..b4), `fr1b-hedge.jpg`, `fr1b-hedge-1to1.jpg`; grid script
  `C:\qfb\frills\scripts\grid.py OUT CELLW tag,tag scene[:box]...`. Costs `C:\qfb\frills\cost-fr1b{1..4}.md`.
- Verdict: b1 edges best (whole leaves break the top silhouette, +26% leafy vertices, +14% leafy build, frame in noise);
  b2 short tufts busier + streaky slivers, +139% vertices/+50% build/+8% frame; b3 long sparse = stretched streaks;
  b4 hang = big smeared diagonal planes, messy from below.
- 18:55 SUBMITTED `1027-185527-r010-frills-c` (spec `C:\qfb\frills\spec-r010-frills-c.json`): fr1c1 edges len 0.5 dens 1 x2,
  fr1c2 edges len 0.4 dens 1 x3. Meanwhile: crop-variant hook code in the worktree.
- 19:00 crop variants BUILT: branch leaf-frills **adec733** (CropVariants + CropVariantsTransformer, cropVariants.enabled /
  -Dqf.cropvariants, default true; sprites textures/blocks/NAME_vN.png registered at stitch when present). Offline verify OK
  (`C:\qfb\frills\verify\src2\VerifyCrops.java` vs srg_merged_minecraft.jar). Jar `C:\qfb\frills\jars\v3\QuestForgeTweaks-1.0.jar`
  (1.1.0+20261027.adec733c; also has frills). Builder on main (c97c5a0) writes wheat_stage_7_v0-4. Trial sprite zip
  `C:\qfb\frills\crops\QF-crop-variants.zip` (from QF-w-bushy ctm/wheat).
- 19:00 SUBMITTED `1027-190035-r010-crops-a` (spec `C:\qfb\frills\crops\spec-r010-crops-a.json`): cv1a0 off / cv1a1 on, farm +
  farm_close, cost mode, MeshStats `C:\qfb\frills\stats\cv1a{0,1}.txt`. Boot logs: look for "crop variants: [wheat_stage_7 x5]".
- v2 results in leaf-frills.md (4680b96).
- NEXT: wait frills-c + crops-a; review c1/c2 vs b1 (grid.py, 1:1 hedge crops), cost; pick final; write
  `C:\qfb\shaderdev\r010\frills_scenes.json` + FRILLS-READY (options off fr1a0 / best edges / runner-up / Stay True crop);
  crops: sheet cv1a0|cv1a1 farm/farm_close + cost (frills_cost.py --off cv1a0 --on cv1a1, whole-boot "all" columns); docs; journal.

### Note from the texture agent (2026-10-27 19:10): crop-variant sprites for the hook
`build_qf_textures.py --wheat dense|bushy` now writes, in CropVariants.java's naming (`textures/blocks/<stage>_v<i>.png`,
with _n/_s maps): `wheat_stage_7_v0..v4` (five heights, wheat_dense.py), `carrots_stage_3_v0..v3` and
`potatoes_stage_3_v0..v3` (crops_dense.py: Faithful 64x's ripe plant with darker mirrored back copies, four heights; two
potato variants carry small white flowers). Test zip: C:\qfb\textures\diag\QF-cropvar.zip (--wheat bushy --leaves faithful).
Other stages have no variants (the hook draws them as before). The old ctm/wheat random rule is still in the zip (harmless).
- 19:15 frills-c DONE and reviewed: c2 (edges len 0.4 x3 dens 1) fullest fringe, +42% leafy verts / +11% build; c1 (len 0.5
  x2) +29% / +9%; frame within noise. HANDED OFF: `C:\qfb\shaderdev\r010\frills_scenes.json` (frills-hedge/-tree/-forest,
  A off fr1a0, B c2, C c1, Stay True as link only: all-rights-reserved, never shown) + `FRILLS-READY`; generator
  `C:\qfb\shaderdev\r010\frills_make_scenes.py`. Docs db7d35c, journal entry. guard OK 19:12. Session 3 exits (crops ETA ~19:25).

## Resume here (session 4)
1. `renderq.py results 1027-190035-r010-crops-a`. In both boot logs (`C:\qfb\shaderdev\rounds\logs\b*.log` after 19:10, jobs
   cv1a0/cv1a1): cv1a0 "crop variants off ... left untouched"; cv1a1 "Transform applied: crop variants hook" and
   "crop variants: [wheat_stage_7 x5]". If cv1a1's list is [] the sprite zip did not load (check resourcepacks).
2. Sheet: `py -3.10 C:\qfb\frills\scripts\grid.py C:\qfb\frills\look\cv1a.jpg 960 cv1a0,cv1a1 farm farm_close` plus a 1:1 crop
   of the near field. Judge: do five heights show, no tiling, no missingno.
   If every block is still identical: the base-sprite identity key failed (Angelica's atlas?). Fallback: key by icon name
   (IIcon.func_94215_i getIconName; add to the stub) in pick.
3. Cost: `py -3.10 tools/textures/frills_cost.py --off cv1a0 --on cv1a1` (use the whole-boot "all sections" ms and vertices;
   the leafy columns don't apply). Expect noise-level change. Add to leaf-frills.md "Crop variants" Results.
4. Add a scene "crops-variants" (A cv1a0 off, B cv1a1 on; farm_close, maybe farm) to `frills_make_scenes.py`, rerun, touch
   FRILLS-READY. Commit docs/ops; journal.

### 2026-10-27 session 4 (leaf-frills agent)
- 19:30 guard OK. crops-a boots: cv1a0 b1027191111 "crop variants off ... untouched"; cv1a1 b1027191250 "Transform applied:
  crop variants hook", "crop variants: [wheat_stage_7 x5]" (logged twice, 19:13:11/12). The IllegalArgumentException
  "Unable to read a class file" is FML mod discovery (in every boot since 17:03), harmless.
- Look: `C:\qfb\frills\look\cv1a.jpg`, `cv1a-near.jpg`: on == off, every ripe wheat the same height -> pick() returns the
  base icon. Sprites are fine (v0..v4 tops at rows 24/18/12/6/0). No Angelica mixin touches renderBlockCropsImpl or
  registerIcon identity (decompiled into C:\qfb\frills\ang\src3). Cause unknown -> v4: name-keyed fallback + one-shot
  diagnostic log in pick ("crop variants: first lookup ..."), rebuild jar v4, re-render crops-b with QF-cropvar.zip
  (wheat + carrots + potatoes variants).
- 19:20 v4 BUILT: leaf-frills **9a3acba** (CropVariants: name-keyed fallback `byName` via IIcon.func_94215_i; logs "first crop
  icon at the hook: NAME (class@id), N stitched stage(s)", then "NAME matched the stitched sprite" or "...reached the hook as
  ..., matching by name"; the stitch line now names the atlas and says whether it is Minecraft's blocks atlas). Jar
  `C:\qfb\frills\jars\v4\QuestForgeTweaks-1.0.jar`. Docs 4c2032e (leaf-frills.md "Crop variants, results").
- 19:20 SUBMITTED `1027-192003-r010-crops-b` (spec `C:\qfb\frills\crops\spec-r010-crops-b.json`): cv1b0 off / cv1b1 on,
  packs QF-w-bushy + `C:\qfb\textures\diag\QF-cropvar.zip` (wheat x5, carrots x4, potatoes x4), farm + farm_close, cost mode,
  MeshStats `C:\qfb\frills\stats\cv1b{0,1}.txt`. Queue ETA ~19:35-19:40.
- crops-a cost (hook on, all misses): frame p50 +0..1%, whole-boot ms/section +7% over different section counts = noise.
- `frills_make_scenes.py` (backup `.bak-s4`) now appends scenes `crops-variants` (farm_close) and `crops-variants-far` (farm),
  A cv1b0 / B cv1b1, ONLY when all four cv1b frames exist; rerun now = unchanged 3 scenes (checked with cmp). Fill
  `CROP_COST` there with the cost line.
- guard OK 19:22. Session 4 exits (wait > 10 min).

## Resume here (session 5)
1. `renderq.py results 1027-192003-r010-crops-b`. Boot logs (`C:\qfb\shaderdev\rounds\logs\b*.log` after 19:25, jobs
   cv1b0/cv1b1): `grep -a "crop variants"`. cv1b1 needs "[wheat_stage_7 x5, carrots_stage_3 x4, potatoes_stage_3 x4]
   (... the blocks atlas)", "first crop icon at the hook", and a "matched"/"matching by name" line.
   - No "first crop icon" line at all: the hook never runs (renderBlockCropsImpl not reached) -> check Angelica's
     ThreadedAngelicaChunkBuilderMeshingTask / any ISBRH for crops.
   - "first crop icon ... 0 stitched stage(s)": classloader split (two CropVariants classes) -> put the map in a class both see.
   - "NOT Minecraft's blocks atlas": another type-0 TextureMap stitched last; only accept the stitch when map == func_147117_R().
   - First icon named e.g. "minecraft:wheat_stage_7": strip the domain in the byName key.
2. Look: `py -3.10 C:\qfb\frills\scripts\grid.py C:\qfb\frills\look\cv1b.jpg 960 cv1b0,cv1b1 farm farm_close` and 1:1
   `... cv1b-near.jpg 900 cv1b0,cv1b1 farm_close:1100,640,900,380` (wheat); carrots/potatoes are the green rows to the
   right/front. Judge: five heights mix, no grid, no missingno; compare with docs/design/shaders/feedback/attachments/r009/.
3. Cost: `py -3.10 tools/textures/frills_cost.py --off cv1b0 --on cv1b1` (whole-boot "all sections" ms and vertices).
   Write into leaf-frills.md "Crop variants, results" (crops-b) and into CROP_COST in frills_make_scenes.py.
4. `py -3.10 -I -X utf8 C:\qfb\shaderdev\r010\frills_make_scenes.py` -> 5 scenes; touch FRILLS-READY. Commit docs/ops; journal.
   If the hook works, drop the diagnostics? No: they are one-shot and cheap; keep.

### 2026-10-27 session 5 (leaf-frills agent)
- 19:31 guard OK. crops-b boots: cv1b0 b1027192552 "crop variants off"; cv1b1 b1027192729 hook applied, stitch "[wheat_stage_7 x5,
  carrots_stage_3 x4, potatoes_stage_3 x4] (... the blocks atlas)", first icon carrots_stage_3 "matched the stitched sprite".
- Look (`C:\qfb\frills\look\cv1b.jpg`, `cv1b-near.jpg`, `cv1b-wheat-1to1.jpg` = off/on/diff): carrots and potatoes VARY (mixed
  leaf shapes, potato flowers); ripe wheat is IDENTICAL off vs on (diff = waving noise only). Not the hash (simulated: 5 buckets
  25-38 each over the field), not the sprites (v0..v4 tops 24/18/12/6/0), world wheat is meta 7 (build_showcase.py), trial mods
  have nothing touching wheat, Angelica has no crop mixin. The v4 log only covered the first icon, so the wheat miss is unexplained.
- Cost crops-b: frame p50 -1%/+0%, p99 +1%; whole boot ms/section -6%, vertices/section -2% = noise.
- 19:33 v5 BUILT: leaf-frills **9444d77** (one log line per distinct crop sprite: identity / by name / no variants, variant drawn,
  stitched names). Jar `C:\qfb\frills\jars\v5\QuestForgeTweaks-1.0.jar`. SUBMITTED `1027-193327-r010-crops-c` (spec
  `C:\qfb\frills\crops\spec-r010-crops-c.json`, cv1c0 off / cv1c1 on, same packs/scenes).

- 19:37 crops-c DONE. cv1c1 boot b1027193558: carrots_stage_3 / potatoes_stage_3 "identity, drew ..._vN"; ripe wheat arrives
  as `minecraft:mcpatcher/ctm/wheat/0.png`: "no variants". CAUSE: Angelica's MCPatcher CTM overwrites
  getBlockIconFromSideAndMetadata (CTMUtils.getBlockIcon(icon, block, side, meta), no position), so the pack's ctm/wheat
  method=random rule gives every ripe wheat tile 0 (also in-game with the hook off). crops-c cost: frame p50 +0..1%; whole-boot
  ms/section +40% (vs -6% crops-b, +7% crops-a) = boot noise.
- 19:39 v6 BUILT: leaf-frills **081cd00**: pick(icon, block, meta, x, y, z); on a miss it looks up block.getIcon(0, meta) (no CTM)
  and its variants win. Stub Block.func_149691_a. Offline verify OK (`C:\qfbrillserify\out3`, CheckClassAdapter vs
  srg_merged_minecraft.jar). Jar `C:\qfbrills\jars6\QuestForgeTweaks-1.0.jar`.
- 19:39 SUBMITTED `1027-193920-r010-crops-d` (spec `C:\qfbrills\crops\spec-r010-crops-d.json`): ONE job cv1d1 (hook on);
  off reference = cv1c0. Queue ETA ~20:01 (behind r010-publish-cost) -> session 5 exits.
- `frills_make_scenes.py` (backup `.bak-s5`) now uses CROP_TAGS = (cv1c0, cv1d1); crop scenes appear when cv1d1's frames exist.
  Rerun now = the 3 frills scenes.
- Docs: leaf-frills.md crops-b, crops-c, crops-d entries. guard OK 19:39.
- For the texture agent / owner: QF Textures' `mcpatcher/ctm/wheat` random rule is harmful under Angelica (every wheat = tile 0,
  the shortest); drop it once the hook ships (build_qf_textures.py --wheat; not my file, noted in the journal).

## Resume here (session 6)
1. `renderq.py results 1027-193920-r010-crops-d`; `grep -a "crop variants"` in the cv1d1 boot log: want
   `minecraft:mcpatcher/ctm/wheat/0.png ... the block's own sprite (a CTM tile reached the hook), drew wheat_stage_7_vN`.
2. Look: `py -3.10 C:\qfbrills\scripts\grid.py C:\qfbrills\look\cv1d.jpg 960 cv1c0,cv1d1 farm farm_close` and
   `... cv1d-near.jpg 900 cv1c0,cv1d1 farm_close:1100,640,900,380`. Five wheat heights mixed, no grid, no missingno; compare
   with docs/design/shaders/feedback/attachments/r009/ (Stay True fields).
3. Cost: `py -3.10 tools/textures/frills_cost.py --off cv1c0 --on cv1d1` -> leaf-frills.md crops-d + CROP_COST in
   `C:\qfb\shaderdev010rills_make_scenes.py` (use the frame p50 line; whole-boot ms is boot noise, see crops-c).
4. If it works: `py -3.10 -I -X utf8 C:\qfb\shaderdev010rills_make_scenes.py` -> 5 scenes; touch FRILLS-READY (keep it).
   Commit docs/ops; journal ops/journal/textures.md. If wheat still misses: fix from the log line, rebuild v7, re-render.
