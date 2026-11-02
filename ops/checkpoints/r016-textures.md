# r016 textures: gems slider (frost -> r015 D) and a Chisel option (texture-dev, 2026-11-01)

Brief: ops/checkpoints/r016-plan.md "Gems"; owner notes docs/design/shaders/feedback/r015.json gems15-*.
1. Slider: frost (r015 E) + 4 steps toward r015 D (round 14 calmed), each complete and connected, at gem15_close /
   gem15_pillar / gem15_floor, same light (11000), same frozen shader (C:/qfb/gems/r015/shader-r014) so r015's
   g15fro / g15calm / g15mask frames stay valid as the two ends and the masks.
2. Chisel option: D's look on Chisel variants (texture + CTM only), shown in game.
Scratch: C:/qfb/gems/r016. Hand-off C:/qfb/shaderdev/r016/textures_scenes.json + TEXTURES-READY.

## Findings
- Chisel.jar = Chisel 2 2.3.10.37. Blocks chisel:diamond_block / chisel:emerald_block (Features$24/$27, javap).
  Diamond metas: 1 embossed, 2 gem, 3 cells (v4), 4 space, 5 spaceblack, 6 simple (-top/-side/-bottom), 7 bismuth,
  8 crushed, 9 four, 10 fourornate, 11 zelda, 12 ornatelayer. Emerald: 1 panel, 2 panelclassic, 3 smooth, 4 chunk,
  5 goldborder, 6 zelda, 7 cell, 8 cellbismuth, 9 four, 10 fourornate, 11 ornate. Sheet C:/qfb/gems/r016/chisel/variants.png.
  Picked: diamond meta 6 "Simple Diamond Block" (assets/chisel/textures/blocks/diamond/terrain-diamond-simple-{top,side,
  bottom}.png), emerald meta 3 "Smooth Emerald" (emerald/smooth.png): the plain ones, least lost.
  CarvableHelper.exists() checks suffixes through the resource manager at registration, so override existing names only
  (adding -ctm files would change the variant kind only if present at startup: fragile). Render type = Chisel.renderCTMId.
  CTM: MCPatcher rule matchBlocks=chisel:diamond_block metadata=6 (as build_modded_textures does); untested on Chisel's
  renderer. Fallback: the face is 64-periodic, so even without CTM a floor is seamless (no rim).
- Shader gem path is a switch (smoothness > 224 and F0 > 25.5): below it a plain sky sheen. Slider steps 1-2 below,
  3-4 above.

## Progress log
- 10:xx read plan/feedback/r015 crops; queue idle; Chisel variants found. Next: gems_look.py slider looks + chisel
  export, build packs, world with Chisel blocks, submit.
- 15:52 BUILT: gems_look.py slide20/40/60/80 (`slide()`: colour mean by t, pattern detail crossfade by t rescaled to
  interpolated contrast, calm's normals x t, gloss SLIDE_S 170/14, 205/18 | 228/27, 234/30; frost's 6-px bands);
  _frost_parts/_calm_parts refactor (frost/calm output unchanged). Builder: --gem-look slide*, --chisel-gems LOOK
  (CHISEL_GEMS: overrides + ctm/qf_chisel/<name>_<meta>/ rule matchBlocks+metadata, connect=tile). build_showcase.py
  --chisel16 (gallery in chisel ids 1239:6 / 1242:3). Previews C:/qfb/gems/r016/an/slider_sheet.png.
  Packs C:/qfb/textures/r016/QF-gems-slide{20,40,60,80}.zip, QF-gems-frost-chiselcalm.zip, QF-chisel-mask.zip
  (tools/make_chisel_mask.py). World C:/qfb/textures/world-chisel16 (read back: 1239:6, 1242:3 at the gallery).
  Build: `py -3.10 -I tools/textures/build_qf_textures.py --out C:/qfb/textures/r016/QF-gems-<L>.zip --stay-true
  "C:\qf-world\reference-packs\Stay True 1" --gems facet --gems-ctm facet --gem-look <L> [--chisel-gems calm]`
- 15:52 SUBMITTED `1101-155222-r016-gems-a` (spec C:/qfb/gems/r016/specs/r016-gems-a.json): g16fro g16s20 g16s40
  g16s60 g16s80 g16calm (world-gems15) + g16chis g16chmask (world-chisel16, mods +chisel). Guard OK.
  Next: wait; review (crops/sheets; r015 masks g15mask for gems15 world); check chisel CTM took (g16chis vs g16calm
  pixel diff on the gems); numbers; textures_scenes.json; TEXTURES-READY.
- 15:58 committed f43dcf9 (gems_look slide, builder --chisel-gems, build_showcase --chisel16; frost/calm previews
  pixel-identical to r015's after the refactor). Cache: g16fro/g16calm hit (r015's frames). Written, not run yet:
  C:/qfb/gems/r016/tools/review_r016.py (sheets, numbers incl. chisel_vs_calm diff + diff-chisel-calm-<view>.png) and
  C:/qfb/shaderdev/r016/textures_make_scenes.py (4 scenes gems16-close/pillar/floor A-F + gems16-chisel A-C; --ready
  refuses until VERDICT has every (tag, view)). Queue: owner active, ETA ~16 min behind shader-r016 loop1 -> exit.

- 2026-11-01 evening (resumed): render landed (all 8 jobs, Chisel booted). review_r016.py run; sheets + 1:1 crops
  read. Slider is bimodal: A-C (fro/s20/s40) frost getting richer (colour 0.39/0.50/0.59 close diamond, sparkles
  ~6), D-F (s60/s80/calm) all read as calmed (sparkles 74-76, brightness 0.51 -> 0.38 at the C->D step). Cause: the
  shader's gem path is a hard switch (smoothness > 224 and F0 > 25.5); no texture step can sit between. Path: a
  gradual gem switch in the shader (shader-dev), only if the owner wants a look between C and D. No re-render.
  Chisel: CTM took on Chisel's renderer: chisel_vs_calm mean |diff| 0.003-0.015, share > 0.1 0.1-3.5 % (floor
  emerald, sparkle positions), no grid in diff-chisel-calm-*.png. Fallback not needed.
  Sky options: not in this render (frozen r014 shader, opts {}); in the dev shader they are gated by golden hour
  (sun under ~18 deg) / meteor nights, and gem15 views have the sun ~24 deg up: no effect on the gem light. At
  sunset QF_SUN_WHITE's final shoulder could whiten a gem's sun glint (screen-wide, peak > 5).
  VERDICT filled (21), textures_scenes.json written, TEXTURES-READY touched.

## Done
Hand-off C:/qfb/shaderdev/r016/textures_scenes.json + crops/ + TEXTURES-READY. Track and journal updated.

## Shader-dev note (2026-11-01 20:15): gem ramp done
QF_GEM_RAMP 1 (default) in shaders/QuestForge: the gem path now blends in by gloss (lighting.glsl gemWeight): frost 140/10 -> 0,
slide20 170/14 -> 0.2, slide40 205/18 -> 0.4, slide60 228/27 -> 0.6, slide80 234/30 -> 0.8, calm 240/34 -> 1 (needs F0 >= ~13
to start, so glass/polished stone at F0 10 stay plain). Frost (E) and calmed (D) render exactly as before. Composite's
gemReflection is scaled by the same weight. Ready for texture-dev to re-render the slider with the current pack.

## Gem ramp re-render (texture-dev, 2026-11-01 20:13)
- Shader 80da4db snapshotted to C:/qfb/gems/r016/shader-80da4db (git archive; tree was clean). QF_GEM_RAMP is already 1 in
  settings.glsl.
- SUBMITTED `1101-201308-r016-gems-ramp` (spec C:/qfb/gems/r016/specs/r016-gems-ramp.json): g16rfro g16r20 g16r40 g16r60
  g16r80 g16rcalm, same packs/world/views as r016-gems-a, opts QF_GEM_RAMP 1. Guard OK.
  Next: wait; review_r016.py-style numbers (colour, sparkles, brightness per step, per view); ends vs r015 g15fro/g15calm
  (mean |diff|); textures_scenes.json + intro text; textures_make_scenes.py --ready; track, journal, commit, push.
- 20:22 DONE. Render landed (18/18, none cached; guard OK after). C:/qfb/gems/r016/tools/review_ramp.py -> review-ramp/
  (sheets, numbers.json, ends.json, evenness.json, diff-*.png).
  Ends: g16rfro vs g15fro and g16rcalm vs g15calm differ only by a uniform whole-frame light drift (r014 -> 80da4db; grass
  too): frame mean |diff| 0.002-0.015, frost gem pixels > 0.1 none, calm 0.02-0.5 %. Gem numbers the same (close diamond
  frost sat 0.39/0.39, sparkles 6.1/5.9; calm sat 0.72/0.73, sparkles 78/74).
  Evenness (pos 0 frost .. 1 calm; switch -> ramp): brightness close diamond 0/.03/.06/.95/.97/1 -> 0/.23/.40/.56/.76/1
  (max step .89 -> .24; every view/gem now monotonic, max .24-.35); colour unchanged (front-loaded by the texture,
  max step .28-.57, as before); glitter hf_sd even; sparkles no longer jump (C->D 1.03 -> .09) but grow geometrically,
  ~x2 per step from C (close diamond 6/4.5/11/18/47/78), so half the count lands in E->F.
  Verdict: smooth slide, no jump between neighbours; D is a real middle. **QF_GEM_RAMP 1 should stay the default**
  (it already is in settings.glsl at 80da4db). Optional, shader-dev.s call: if the owner wants sparkle linear in steps, ease
  the sparkle growth along gemWeight (not checked in the shader; not needed for the hand-off).
  Hand-off: textures_make_scenes.py slider tags g16r*, verdicts rewritten, intro says the slide is even (no jump), notes
  name the ramp render + ends check; Chisel scene unchanged (round 15 shader, at 100 % the ramp draws the same).
  Backups of the pre-ramp maker/json in C:/qfb/gems/r016/*.pre-ramp.*. --ready: TEXTURES-READY touched.
