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
    leaves_close, tree_close, forest_lit. Submission **1026-223656-textures-v2-leaves**.

## Next
Step 1d: `renderq.py results 1026-223656-textures-v2-leaves`; review t9v2 against t9v1 as a contact sheet
(check_frames.py). If the leaves read as foliage masses with no tiling tell, move on to step 2 (grass).
