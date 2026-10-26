# r008 textures: QF Textures v1 (checkpoint 2026-10-25 22:20)

Details: direction.md sections 5-7.

## v1 so far
- Build: `py -3.10 -I tools/textures/build_qf_textures.py --out C:/qfb/textures/QFTextures-v1.zip [--leaf-edges none|all|sides] [--no-cit]`.
- Faithful 64x: stone, bricks, cobble, ores, metal blocks, glowstone, glass, dirt, grass side, farmland (resourcepacks/QFTextures/faithful64.txt).
- Glass CTM rules rewritten to 1.7.10 ids, each named after its folder.
- Our art (tools/textures/qf_art.py): leaves, bark, log ends, tall grass, fern, wheat 0-7, grass top, 4 bookshelf variants (CTM random, replaces Angelica's).
- PBR from VNR (vnr.py): converted on vanilla textures, hybrid on Faithful ones.
- Vibrance 1.10.

## Licences
- Faithful 64x: 1.7.10 branch 89f200c, Faithful License v4.
- VNR 1.12 (c848329): README allows redistribution, unsold, with a link; no Realistico. Ship only its _n/_s maps.

## Owner's answers
Written in direction.md section 6:
- Patrix mobs: skins and random variants are cheap but need an artist; new shapes need Java.
- Leaf frills: options A-E. B/C are CTM `--leaf-edges all|sides`; D is qf-tweaks code.

## Items
- qf_items.py: 7 bottles plus splash, 9 book covers.
- renderq `"cit": true` turns CIT on in the trial only.
- t8i1 vs t8i0 works in item frames: distinct shapes, game colours.
- Quality: readable but flat; an artist is needed for Faithless level.

## renderq
- 1025-210601-textures-v1: done. Showed black glass (fixed), black sky-light patches (fixed), cameras too far (fixed), zigzag leaf gaps (fixed).
- 1025-210753-textures-v1-items: done. Frames are bench-t8i0/t8i1-items_frames.png in C:\qfb\shaderdev\rounds\screenshots.
- **1025-211536-textures-v1: queued, ETA ~21:52.** Shot mode, relit world, all fixes. Tags:
  - t8v1, t8v0, t8f64, t8van;
  - t8e1 / t8e2 (leaf edges all / sides);
  - t8p1 / t8p0 (QF_PBR 1).
- Night mode from 22:15: only `mode: shot` jobs run.

## Review of 1025-211536 (22:20)
- Good: walls, Faithful ores/metals, leaves, bookshelves, forest. Leaf-edge variants e1/e2 visible.
- BAD: v1 clear glass draws Angelica's built-in 16x CTM (key = rule file basename; ours was clear_glass). Fix: name rules glass.properties / glasspane.properties / <col>_stained_glass[pane] like Angelica.
- Wheat stage 7 too orange: paler WHEAT_GOLD. Grass top/fern left as is (owner question).

## Iteration b (committed)
- Clear glass now at ctm/glass/glass.properties + tiles (Angelica's path); panes *glasspane. Wheat gold paler.
- **1025-221933-textures-v1b submitted 22:20** (spec textures-v1b.json): re-renders t8v1 (7 scenes), t8e1/t8e2 leaves, t8p1 glass. Wait on it, review glass + wheat, then step 4.

## Iteration c
- v1b: wheat now straw (good). Glass still wrong: border on every block (jar's compact rule won).
- v1c: clear glass ships Faithful's raw rule (glass/glass/glass.properties, matchBlocks=glass). **1025-222922-textures-v1c submitted 22:29** (t8v1 wall/wall2/glass, t8p1). If still wrong: drop our clear-glass CTM and say so.

## Next
1. `renderq.py results 1025-211536-textures-v1`. Review crops with C:\qfb\textures\v1work\cmp.py (scene, tags, crop, scale).
2. If needed:
   - tune art: grass top a little flat, wheat orange, fern weak;
   - rebuild the items zip with the fixes (`specs/textures-v1-items.json`);
   - resubmit, in shot mode.
3. Fix direction.md's quality claims to match the frames.
4. Write C:\qfb\shaderdev\r008\texture_scenes.json in the r007 format (template: C:\qfb\textures\make_scenes.py). Scenes:
   - tex-wall (texture_wall + texture_wall2): A v0, B v1, C Faithful 64x;
   - tex-glass, tex-forest (forest_lit), tex-golden;
   - tex-farm (farm, farm_close);
   - tex-leaves (leaves_close, tree_close): A no frills t8v1, B edges all t8e1, C top/bottom only t8e2;
   - tex-pbr: t8p0 vs t8p1;
   - tex-items: t8i0 vanilla vs t8i1 ours, cropped to the board.
   - Credits: Faithful License v4 + link, VNR link.
5. Final build: `build_qf_textures.py --out C:/qfb/textures/QFTextures-v1.zip` (with CIT). Write C:\qfb\shaderdev\r008\TEXTURES-READY.
6. `trial.py guard`; check `git log origin/main..main`; push.
