# r009 textures checkpoint (orchestrator, 2026-10-26)

Brief: ops/briefs/texture-iteration.md (v2). Input: tex-* answers in docs/design/shaders/feedback/r008.json.
Start state: QF Textures v1 (cc3230e). Build: `py -3.10 -I tools/textures/build_qf_textures.py --out C:/qfb/textures/QFTextures-v2.zip`.
Nothing for v2 started; no renders submitted.

## Owner's r008 texture answers
- tex-wall A 3/5: likes B's metallic metals and diamond and B's stone brick; iron and gold too dark in A, as if unlit.
- tex-wall-close B 4/5: emerald and grass look weird; the rest is good.
- tex-glass: all the same. tex-forest A 4/5: leaves in B (edges) are "complete shit".
- tex-golden: weird artifacting in all photos.
- tex-farm C 4/5, farm-close B 3/5: wants crops as close as possible to the pack whose crops he liked, without copying it.
- tex-leaves B 3/5, tex-leaves-tree B 3/5: leaves need heavy rework; B gives the tree more shape but he dislikes the look.
- tex-pbr B 3/5 "fine". tex-items B 4/5: books good; potions boring.
- Overall: "Fix the leaves, fix the grass, fix the crops."

## Plan
1. Leaves (qf_art.py): redesign; study, never copy, the packs he liked; drop or redo the ragged-edge CTM (--leaf-edges).
2. Grass top/side: restore the crisp r007 read, no flat felt.
3. Crops: own art in the liked pack's approach; check that pack's licence first (all-rights-reserved is study only).
4. Metals: raise iron/gold albedo in the PBR set; fix emerald. No per-frame cost (hard constraint, see r009-shader).
5. Find the tex-golden artifact.
6. Potions: stronger silhouette and colour personality.
7. Render via renderq (shot mode at night); write texture_scenes.json in C:\qfb\shaderdev\r009, TEXTURES-READY; `trial.py guard`; no push.

## Progress log
- 2026-10-26 (texture-dev, capped run): step 1 split into 1a/1b/1c. 1a done (read-only diagnosis, no code changed, no renders).
  - Leaf code: `tools/textures/qf_art.py` `leaves()` (l.115) + `LEAF_KINDS` (l.77); ragged-edge CTM is
    `build_qf_textures.py` `leaf_ctm()` (l.125), already off by default (`--leaf-edges none`). Keep it off; don't redo it in v2.
  - Diagnosis: per 32px tile, 8 metaball clumps + 30-60 lens leaves, each its own value step, with a dark seam
    (-0.16) at every leaf boundary. At 32px that is pixel-level noise over a busy clump pattern, so the canopy reads
    as speckle, not as foliage masses, and the per-tile clump lighting repeats block to block.
  - 1b spec (next): fewer, bigger value groups (3 values per clump: lit crown / mid / shadow underside);
    single leaves drawn only on clump crowns and silhouettes, not everywhere; seam strength 0.16 -> ~0.06;
    stronger macro contrast between clumps; alpha stays >= 0.61. Verify offline first: a 3x3 tiled preview per kind,
    biome-tinted, as one contact sheet in the scratchpad, before any render.
  - 1c: render tex-leaves, tex-leaves-tree, tex-forest via renderq (shot mode, night per item 7).

- 2026-10-26 (texture-dev, capped run): 1b done, offline only, no renders.
  - `leaves()` now has 3 macro value groups per clump (crown +0.16 / mid / shadow -0.16) plus a per-clump
    offset (±0.08) so the masses separate; single leaves only on crown or silhouette (f < 0.75);
    seam 0.16 -> 0.06; leafless clump interior -0.12 -> -0.04.
  - Preview: scratchpad `leaf_preview.py` (3x3 tiled, vanilla biome tints over sky blue, 4x zoom). It ran;
    I looked at the sheet. Clumps read as masses now, not speckle. Alpha: oak .89, big_oak .93, birch .91,
    jungle .79, acacia .98 (all >= .61). Scratchpad is per-session, so recreate the preview when needed.
  - Seen but not fixed: oak's gap pockets still form a visible zigzag column per tile; acacia gaps are
    thin tick marks; jungle gaps are large Y-shapes. Only 5 grey values survive quantisation. Possible 1b+ touch-ups,
    otherwise judge them in the 1c render.

- 2026-10-26 (texture-dev, capped run): 1c gap fix + render submitted.
  - `leaves()` see-through pockets: the valley-following pockets (oak zigzag columns, jungle Y-shapes,
    acacia ticks) are replaced by round pockets centred on each field minimum (7x7 window, f below 0.24-0.30),
    varied in size (0.6-1.4x) and made of two overlapping discs so they don't read as a dot grid.
    Alpha now: oak .92, big_oak .95, birch .96, jungle .95, acacia .97. Preview looked right; oak has
    one keyhole-shaped pocket per tile, so judge that in the render.
  - Built v2 (checkpoint command). Without --no-cit the build warns of duplicate zip entries for
    `mcpatcher/cit/potions/bottle_cone.png` and `liquid_cone.png`. Not fixed; fix it with the potions step (6).
  - Spec `tools/renderq/specs/textures-v2-leaves.json` (prebuild with --no-cit): t9v2 vs t9v1 on
    leaves_close, tree_close, forest_lit. Submission **1026-223656-textures-v2-leaves**: DONE 22:44,
    6/6 frames, nothing cached (result.json in C:\qfb\renderq\results\1026-223656-textures-v2-leaves\). Not reviewed yet.

- 2026-10-26 (texture-dev, capped run): 1d review of 1026-223656 + fix, render submitted.
  - check_frames.py has no contact-sheet mode; built sheets/crops with a scratchpad PIL script instead.
  - Verdict t9v2 vs t9v1: v2 calmer, clumpier, fewer harsh holes, so better. But a native-res crop of the hedge
    (leaves_close) showed a diagonal hatch repeating block to block: every clump's crown was a straight
    half-plane cut toward one LIGHT, and the cuts lined up. Distant canopies (tree_close) slightly flatter than v1.
  - Fix in `leaves()`: per-clump light angle (±0.8 rad) and the crown is now a round highlight pushed toward it
    (push 0.25-0.45, radius 0.45-0.65), drawn from its own stream rng(seed+100). Preview: hatch gone, clumps
    read as rounded masses; acacia slightly coin-like. Committed with spec `tools/renderq/specs/textures-v2b-leaves.json`.
  - Submission **1026-224756-textures-v2b-leaves** (tag t9v2b; compare with t9v2/t9v1 frames from 1026-223656).

  - 1026-224756 DONE 22:51, 3/3 frames. Reviewed as a 3-way contact sheet t9v1 | t9v2 | t9v2b plus native-res crops
    (2560px frame boxes: hedge 800,740,1440,1100; lower canopy 900,860,1540,1220; forest 1600,360,2240,720).
    v2b: the hedge reads as rounded clump masses, and the hatch is down to a faint diagonal from the leaf
    lenses (normal(pi/2, 1.0) angles). Canopy/forest same as v2 or better. **Step 1 (leaves) closed at v2b.**
    Caveat for the owner: this refines v1's procedural clump approach rather than a ground-up redesign;
    if r009 feedback still says the leaves are bad, the next path is hand-painted leaf masters instead of more generator tuning.

- 2026-10-26 (texture-dev, capped run): step 2 (grass) code + render submitted.
  - Diagnosis from r008 crops (t8v0 vs t8v1 texture_wall2, ground box 1000,1100,1500,1350; step box 1600,700,1950,950):
    v1's drawn `grass_top()` has 6 grey values (sd 8.8) and a diagonal swoosh clump that repeats every tile: the felt.
    r007/v0 was vanilla's grass_top doubled + 3x3 blur at 68% (`calm_grass`, git e4dd9f6), sd 14.4, crisp pattern.
    Grass SIDE is Faithful 64x (faithful64.txt, owner liked its dirt); its fringe's top rows mean 150.8 vs top 147.7. Left as is.
  - Fix: `qf_art.grass_top_from(vanilla, keep=0.75)`: vanilla pattern, pixel contrast lowered around a 16x 3x3 blur, doubled with
    hard edges (no blur after doubling), blade-tip sub-pixel (lit UL, shaded LR). sd 14.1. Build passes vanilla's grass_top in
    (`drawn_art(planks, grass)`). Old `grass_top()` kept for previews. Preview (scratchpad grass_preview.py, per-session): v2 ~ v0, crisper.
  - Committed (spec `tools/renderq/specs/textures-v2c-grass.json`: t9v2c vs t9v1 on texture_wall, texture_wall2, golden_lit).
  - Submission **1026-225431-textures-v2c-grass**: DONE 22:57, 6/6 frames (bench tags t9v2c, t9v1).
  - Review (sheet t9v1 | t9v2c of 3 views + crops): the near ground in v2c has r007's crisp vanilla pattern; v1's is soft felt.
    The step top at grazing angle is mip-smoothed in t8v0, t9v1 and t9v2c alike (crop sd 16.3 / 11.9 / 12.2), so that's not the felt.
    The 64x side fringe joins the top cleanly. golden_lit: no visible difference at distance. **Step 2 (grass) closed at v2c.**
    For the owner in r009 scenes: if "grass looks weird" meant the 64x side fringe, not the top, the fallback is vanilla's side overlay doubled.

- 2026-10-26 (texture-dev, capped run): step 3 (crops) code + render submitted.
  - Liked pack = Stay True (track file; direction.md l.153: ARR, study only). No local copy; CurseForge blocks scripted
    download (Cloudflare), cfwidget gave a wrong project. So no pixel study: designed from the r008 frames instead.
  - r008 farm_close sheet (t8v0 | t8v1 | t8f64): v1 wheat = a solid chunky straw wall (13 stalks, 3 px checker ears);
    owner picked C = Faithful 64x (airy separate plants, leafy carrots/potatoes) at distance.
  - `qf_art.wheat()` redrawn (old kept as `wheat_v1()` for previews): 5 front + 3 back plants (back in the gaps, darker,
    shorter), 1 px stalks, arching blade leaves, tufts for 0-2, 2 px braided ears from stage 4, awns on the upper ear at 6-7,
    ripe ear nods; new WHEAT_RIPE palette a step brighter/yellower. Leans clamped inside the tile, ears fit under the top.
    Preview: scratchpad `wheat_preview.py` (rows v2 / v1 / Faithful64 / F64 carrots+potatoes + a ripe field strip). Reads as
    wheat plants now; stage 7 tile has one sparse gap on the right (judge in-world, crossed planes overlap).
  - Carrots/potatoes: `faithful64.txt` += carrots_stage_*, potatoes_stage_* (Faithful licence; owner rated that farm best).
  - Committed c899ffd with spec `tools/renderq/specs/textures-v2d-crops.json` (t9v2d vs t9v1 on farm, farm_close;
    third column = r008's `C:\qfb\shaderdev\rounds\screenshots\bench-t8f64-farm*.png`).
  - Submission **1026-230307-textures-v2d-crops**.

  - 1026-230307 DONE 23:10. Review (sheet t9v1 | t9v2d | t8f64 of farm, farm_close; native crop of farm_close box
    900,800,1560,1150): v2d clearly airier than v1's wall, carrots/potatoes now Faithful's leafy darker green (no neon).
    But ripe ears read as short blobs on rigid posts next to Faithful's curving plants.
  - Fix pass v2e (commit 390b0fd): EAR lengths 5/7/9/10 (stages 4-7), stalk bow, tip nods from stage 6, jitter ±0.7, lean sd 1.5.
    Ripe tile still bunches a little (reads as tufts). Spec `textures-v2e-crops.json`; submission **1026-231132-textures-v2e-crops**.

  - 1026-231132 DONE 23:14. Review (crops t9v2d | t9v2e | t8f64; farm_close box 900,800,1560,1150, farm box 900,500,1560,860):
    v2e ears are longer and slimmer and read as wheat heads, better than v2d. Behind Faithful: stalks fairly straight, and stages 1-2
    read as flat lime "+" shapes from above (Faithful's are upright shoots). **Step 3 (crops) closed at v2e.**
    For the owner: code wheat isn't Stay True's hand-placed look; if r009 says so, hand-drawn wheat masters are the next path.

- 2026-10-26 (texture-dev, capped run): step 4 (metals, emerald) diagnosis + code + render submitted.
  - Crops (texture_wall box 0.52,0.36,0.68,0.58; texture_wall2 box 0.70,0.36,0.86,0.66; t8v0 | t8v1 | t8f64): A's iron/gold dull
    and flat; B's (= v2 before this step) gold dark on top with a bright liquid-like horizon band; B emerald a murky green mirror.
  - Cause: iron/gold `_s` are 100% metal (230/231) in v0, v1 and v2. The shader (lighting.glsl metalShade, SSR path at preset 3)
    keeps 0.30 of a metal's diffuse and shows reflection otherwise. Iron's F0 = albedo x 1.15 already clips at 1, so the plan's
    "raise albedo" can't work. A's were flatter than B's only because v0's normals are near flat (nsd 1.2 vs 10.8/20.2).
  - Emerald: VNR's vanilla rhombus maps over Faithful 64x's square bevels (layout_match let it through), and VNR flags it as
    metal (code 230, so f0 = green albedo). Diamond: also VNR metal (owner liked it, kept), but its `_s` alpha was 254 = full
    LabPBR emission (VNR B=255 everywhere). QuestForge ignores spec emission, but other shaders would make it glow.
  - Fix (commit fa0c7e1): `build_qf_textures.py` VNR_SKIP={emerald_block} (falls to labpbr: dielectric 0.62/F0 14, normals from
    the 64x art); METAL_BLOCKS + `metal_spec()` + `--metals lit|split|vnr` (default lit): lit = every pixel a dielectric F0 190
    (iron) / 140 (gold), full diffuse + untinted reflection; split = metal only where lum > its 70th pct (iron 9%: plate
    highlight lines; gold 16%: diagonal shine streaks). `vnr.py`: B>=250 everywhere is not emission (beacon excepted).
  - Spec `tools/renderq/specs/textures-v2f-metals.json`: t9v2f (lit, QFTextures-v2.zip) and t9v2fs (split, QFTextures-v2-split.zip)
    on texture_wall, texture_wall2. Baseline t9v1 frames from 1026-225431. Submission **1026-231924-textures-v2f-metals**.

  - 1026-231924 DONE 23:27. Review (t9v1 | t9v2f | t9v2fs, both boxes + native crop px 1450,600,1700,850):
    emerald fixed in both (clean square bevels, no murk). Iron: lit = split, both better than v1 (plates read, lit like the
    neighbours). Gold: both washed pale and plastic-orange (crop B 44 -> 66: untinted sky over yellow); v1's all-metal gold richer.
    Note: under the r009 shader v1's metals are already much brighter than in r008 (iron crop mean 134 vs t8v1 91).
  - Pass 2 (commit 70b04a2): METAL_BLOCKS is per block (code, dielectric F0, metal percentile); `--metals qf|vnr` (default qf):
    iron F0 190 everywhere; gold metal above its 55th pct (40%, the diagonal shine bands) over F0 60.
    Spec `textures-v2g-metals.json` (t9v2g). Submission **1026-232836-textures-v2g-metals**.

  - 1026-232836 DONE 23:30. Review (t9v1 | t9v2f | t9v2g, wide box + native crop): gold saturated again, its diagonal shine
    bands read as polished glints, lit over the whole face (no dark top half); a touch more lemon than v1's deeper gold.
    Iron as v2f. **Step 4 (metals, emerald) closed at v2g.** QFTextures-v2.zip is the default build (--metals qf).
    For the owner: if gold reads too lemon, raise its metal share (lower pct in METAL_BLOCKS); if metals still look unlit in
    r009, the lever is the shader's metal diffuse (0.30, lighting.glsl metalShade), not the textures.
    C:/qfb/textures/QFTextures-v2-split.zip is a leftover of 1026-231924 (scratch, deletable).

## Next
Step 5: find the tex-golden artifact (owner r008: "weird artifacting in all photos"). Read-only diagnosis first:
r008 tex-golden frames (site/shaders/rounds/r008/tex-golden-*.jpg, bench golden_lit pngs), native-res crops, check whether it
is texture-side (mips, alpha, CTM, PBR maps) or shader-side (then hand it to r009-shader in ops/DECISIONS or the board).
Steps still open: 5 (tex-golden artifact), 6 (potions; also fix the duplicate CIT zip entries), 7 (scene hand-off).
