# r011: port Stay True's leaves and wheat (texture-dev, 2026-10-27)

Read first: ops/checkpoints/r011-plan.md (owner's r010 verdict and picks), then the "Progress log" of
ops/checkpoints/r010-leaf-frills.md for the hook, worktree, jars, renderq job fields and cost scripts.

## The owner's call (2026-10-27, CLAUDE.md "Licences")
Copy Stay True's textures and models into the private pack and edit them from there. No more inventing shapes or
generating art toward screenshots. Stay True lives at `C:\qf-world\reference-packs\Stay True 1\` (1.21, 16x,
`assets/minecraft/textures/block/`). Its files are NEVER committed to the repo (public) and never shown on the
public site: the build script reads them from that folder at build time; renders and Lab images of our own game
are fine. Owner: "Please actually check to see what stay true does because I'm sick of the guess work."

## What Stay True actually does (read from its files, 2026-10-27)
- **Leaves** (`blockstates/oak_leaves.json`, `models/block/leaves_cross{,1,2}.json`): the normal full leaf cube
  (`oak_leaves.png`, 16x, 67% opaque) PLUS two vertical planes, unshaded (`"shade": false`), tinted, no cullface,
  textured with `oak_leaves_bushy*.png` (32x32, a ROUND soft-edged clump, about 51% opaque):
  - leaves_cross: plane A x=14, from y -6 to 22, z -7 to 25, rotated -22.5 deg about Y around (14.125,-8,-6.8125);
    plane B z=2, x -7 to 25, y -6 to 22, rotated -22.5 deg around (-6.8125,-8,1.875). Units are 1/16 block.
  - leaves_cross1: same planes, +22.5 deg, origins (6.125,-8,20.125) and (20.125,-8,6.125).
  - leaves_cross2: planes 2 blocks wide x 2 tall (y -8 to 24 / -7 to 24), -22.5 deg, origins (13.3375,-10,-6.2875)
    and (-7,-10,2).
  - Every leaf block gets one of the three variants at random (blockstate list, equal weight), on every leaf block,
    not only exposed edges. Per-species models exist (leaves_cross_birch*, _dark_oak*, ...): read each.
  - This is why our r010 frills read as spiky: we drew small strips on exposed edges; Stay True draws two big round
    clumps crossing each block, so the canopy reads as soft volume.
- **Wheat** (`blockstates/wheat.json`): ages 5, 6 and 7 each pick from 5 models with weights 6/3/3/4/4.
  - Weight 6: the plain one-block crop (`wheat_stage_7.png`, the standard `#` of 4 planes at 4 and 12).
  - Weights 3/3/4/4 (70% of ripe blocks): **two blocks tall**: the same 4 planes from y -1 to 16 with
    `wheat_stage_7_bottom{,1,2,3}.png` (dense dark stalks) and 16 to 32 with `wheat_stage_7_top{,1,2,3}.png` (a band
    of gold heads). Unshaded, ambient occlusion off. Ages 5 and 6 have their own bottom/top sets.
  - So our r010 hook (one-block sprite swap) was "the wrong execution": Stay True's field is tall and dark-based.

## Work
1. Copy, map and build: a build step (extend `build_qf_textures.py`, e.g. `--stay-true PATH`) that copies the needed
   Stay True PNGs into QF Textures under 1.7.10 names (leaves_oak etc., wheat stages, the bushy and top/bottom
   sprites the hook registers). Its output must stay out of git: check `.gitignore` covers the built pack, and never
   `git add` a Stay True PNG. Resolution: Stay True is 16x and the rest is Faithful 64x; nearest-upscale to 64 so
   mip and atlas behave the same.
2. Hook (worktree `C:\qfb\frills\wt`, branch `leaf-frills`): replace the edge frills with Stay True's geometry
   exactly: the two rotated planes per leaf block, three variants by position hash, unshaded, tinted with the
   block's colour multiplier, Fancy leaves only, config switch kept. Replace the crop variant hook with Stay True's
   wheat: weighted 6/3/3/4/4 by position hash, two-block-tall `#` planes for the tall variants. Carrots and
   potatoes: copy whatever Stay True does for them (read their blockstates); if it does nothing special, leave them.
3. Measure: frame time and vertices with `frills_cost.py`, on vs off, on the same scenes as r010 (forest_lit,
   tree_close, leaves_close, forest_far, biome_roofed, farm, farm_close). The answer to "what does it cost" is a number.
4. Diamond and emerald "glassier and more reflective" (owner, r010 gold scene): check whether Stay True's diamond
   and emerald blocks look like that; copy them if so, otherwise adjust our PBR maps (smoothness up, F0 stays
   non-metal: "keep metallic textures for the actual metals").
5. Hand the r011 scenes (Stay True port vs r010, each with the cost) to `C:\qfb\shaderdev\r011\` the way
   texture_scenes.json / frills_scenes.json were handed in r010. Small round: only these items.

Not in this round: the items' second art style (the owner wants one more full style set before committing; next round).
Owner's r010 picks to keep: tex-wall B (metal look on real metals only), dense wheat colour, leaf transparency
("I like the transparency... they should give a realistic looking tree volume and structure").

## Progress log

### 2026-10-27 session 1 (texture-dev)
- Read Stay True's files (not guesses). Corrections to the summary above:
  - Spruce uses `spruce_leaves{,1}.json` -> leaves_cross (tinted, 2 variants); `leaves_spruce1/2` + leaves_cross_spruce* are unused.
  - Birch: `leaves_cross_birch` for BOTH variants (cross geometry, NO tintindex: Stay True's birch PNGs are pre-coloured).
    1.7.10 tints birch cubes with 0x80A755, so the build divides the birch cube texture by it (max px 108,137,80 -> no clip).
  - Dark oak: parents leaves_cross / leaves_cross1 / leaves_cross (leaves_cross_dark_oak* unused), cube PNGs differ per variant.
  - Oak cube PNG is the same in all 3 variants; jungle/acacia 2 variants (cross, cross1).
  - Wheat age 5: weights 6 stage_5 / 3,3 tall (bottom{,1}/top{,1}) / 4,4 single `wheat_stage_5_1`. Ages 6, 7: 6 single / 3,3,4,4 tall.
  - Carrots age 7: 4 equal: stage3, stage3_1, stage3_2 (single), stage3_3 tall. Potatoes age 7: 2 stage3, 5 stage3_1, 5 stage3_2,
    3 tall(bottom/top), 3 single stage3_3, 3 tall(bottom2/top2), 3 tall(bottom1/top1). Tall = 8 planes, y -1..16 and 16..32.
  - Stay True also ships an OptiFine custom leaves colormap for oak + dark oak (optifine/colormap/custom/leaves.png) and animated
    diamond/emerald blocks (8 / 10 frame sparkle, .mcmeta).
- Design: the builder parses Stay True's blockstates + models and writes the leaf/crop variants (weights, sprites, every face
  as 4 rotated vertices) into the pack as `assets/minecraft/qf/staytrue_models.txt`; the hook reads that file at stitch time
  (no Stay True names in Java). Leaves: cube sprite via overrideBlockTexture in a before-hook, planes after renderStandardBlock.
  Crops: head hook in renderBlockCropsImpl draws tall variants; single variants swap the icon.
- Step 1 DONE (main a19d179): `tools/textures/staytrue.py` (parser; `--dump` prints the variant table) +
  `build_qf_textures.py --stay-true PATH`. Built `C:\qfb\textures\r011\QF-staytrue.zip` (private; *.zip is git-ignored):
  1.7.10 names (leaves_<kind>, _opaque, wheat_stage_0-7, carrots/potatoes_stage_0-3) + `textures/blocks/staytrue/*` (75 sprites,
  4x nearest: cube 64, bushy 128) + `assets/minecraft/qf/staytrue_models.txt` + CREDITS-StayTrue.txt. Own _n/_s from labpbr.
- Step 2 DONE (leaf-frills **718473f**): `StayTrueModels` (spec reader, stitch registration, weighted pick by position hash,
  drawQuads), `LeafFrills` before/after hooks (cube sprite via overrideBlockTexture, planes after renderStandardBlock),
  `CropVariants` head hook `tall()` + icon hook `pick()`. LeafFrillsIcons and the r010 frill tuning keys are gone; switches
  kept: leafFrills.enabled (-Dqf.frills), cropVariants.enabled (-Dqf.cropvariants). Offline verify OK
  (`C:\qfb\frills\verify\src4\VerifyST.java`, CheckClassAdapter vs srg_merged_minecraft.jar). Jar `C:\qfb\frills\jars\v7\`.
- 22:08 guard OK. SUBMITTED `1027-220844-r011-staytrue-a` (spec `C:\qfb\frills\spec-r011-staytrue-a.json`): st1a0 hooks off,
  st1a1 on, QF-staytrue.zip, 7 scenes, cost mode, MeshStats `C:\qfb\frills\stats\st1a{0,1}.txt`. Behind 2 shader boots (ETA ~22:25).
- Next: results; boot log of st1a1 needs "Stay True models: [leaves:0 x3, ...]", "Transform applied: Stay True leaves hooks",
  "Stay True crops hooks", "own tessellator", "first tall crop drawn"; sheets off/on; cost (frills_cost.py --off st1a0 --on st1a1).
