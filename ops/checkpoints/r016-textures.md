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

## Next (resume here)
Render `1101-155222-r016-gems-a`. Check `py -3.10 -I tools/renderq/renderq.py results 1101-155222-r016-gems-a`
(or one blocking `renderq.py wait 1101-155222-r016-gems-a` if status ETA < 10 min).
1. If g16chis/g16chmask failed to boot (Chisel deps?), read the boot log, fix mods list, resubmit -b with only those.
2. `py -3.10 -I C:/qfb/gems/r016/tools/review_r016.py`; check mask-g16chmask-*.png are the gems only; view
   review/gem15_*.jpg and 1:1 crops. Is each step good art (mud? grid? the 40->60 jump at the gem switch)? If a step
   is bad, fix gems_look.slide / SLIDE_S, rebuild that pack, resubmit -b.
3. Chisel: chisel_vs_calm numbers + diff-chisel-calm-*.png. Close view (lone blocks) should be ~0; pillar/floor near 0
   if the CTM rule took; a frame on every block = CTM did not take on Chisel's renderer (RendererCTM) -> fallback:
   ship the periodic face with no frame for the variant (seamless, no rim), or Chisel's own -ctm files (only seen at
   registration; needs the pack active at startup). State plainly which.
4. Fill VERDICT in C:/qfb/shaderdev/r016/textures_make_scenes.py (every (tag, view) for g16fro..g16calm + g16chis),
   run it, view every crop in C:/qfb/shaderdev/r016/crops, rerun with --ready.
5. ops/tracks/textures.md, one journal entry (ops/journal/textures.md), commit own files, git log origin/main..main,
   push, report <= 5 lines.
