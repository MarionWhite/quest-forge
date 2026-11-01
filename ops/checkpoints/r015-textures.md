# r015 textures: gems, a big swing (texture-dev, 2026-11-01)

Brief: ops/checkpoints/r015-plan.md "Textures". Owner r014: every gem scene "neither": "These either look plastic or
very noisy ... we are not even close." 4-5 complete, different, connected directions, each at three distances (close
block, pillar, floor) in the same light; measure noise and plastic for each. Hand-off C:\qfb\shaderdev\r015\.
Scratch: C:\qfb\gems\r015 (ref/, tools/). Reference gems extracted to C:\qfb\gems\r015\ref (private).

## Progress log
### session 1
- 10:05 read plan, r014-textures, critic r014 gem notes. Queue idle.
- Ref study (sheet C:/qfb/gems/r015/ref/sheet.png): Patrix diamond _n = ~10 big planes over the block (median tilt
  22 deg), its _s 255/228 (F0 0.89: a mirror, not used). Stay True diamond = 16x bevel + diagonal streaks + glint
  sweep animation; emerald = step-cut concentric rings (6 tones). Soartex 64x = frosted pale ice, emerald rhombus
  bands. Shader reads no emission/SSS (gem path: smoothness>0.88 & F0>0.1; QF_GEM_LOOK 2 default).
- Plan: directions A facets (Patrix planes, planarised, Faithful tones per facet, gem path), B Stay True plain
  (connected, no maps -> no gem path, QF_GEM_SSR 0), C deep jewel (dark saturated body, painted inner glow, few
  sparkle pixels, low reflection), D r014 Faithful calm (low-passed _n, uniform _s), E Soartex frost.
  New gallery world C:/qfb/textures/world-gems15 (big floors so distance noise shows); 3 views, light 11000 yaw 90.
- 10:13 BUILT: tools/textures/gems_look.py (5 looks: facets = rhombus cut 8 planes + table, Patrix tilts 21 deg, gem
  path; staytrue = Stay True 16x at 4x, diamond quilted, emerald rings per block, _s 90/10; jewel = brilliant/step
  cut painted deep + 3 sparkles, _s 205/12 (sparkles 255/44); calm = r014 faithful, contrast x0.75, crystal _n
  blurred 1.2 px x0.5, _s 240/34 even; frost = Soartex 64x quilted inside 6-px bands, block-scale swell removed,
  _s 140/10). Builder: --gem-look (build_qf_textures.py). Previews C:/qfb/gems/r015/an/look_*.png, all_looks.png.
  Packs C:/qfb/textures/r015/QF-gems-{facets,staytrue,jewel,calm,frost}.zip (+ QF-gems-mask.zip, flat magenta
  diamond / orange emerald for shaders-off masks).
  World C:/qfb/textures/world-gems15 (build_showcase.py --v1 --gems15, from world-gems). Views
  C:/qfb/gems/r015/views-r015-gems.txt: gem15_close / gem15_pillar / gem15_floor, all 11000 yaw 90.
  Shader frozen at HEAD: C:/qfb/gems/r015/shader-r014. Guard OK.
- 10:13 SUBMITTED `1101-101323-r015-gems-a` (spec C:/qfb/gems/r015/specs/r015-gems-a.json; tags g15fac g15st
  (QF_GEM_SSR 0) g15jew g15calm g15fro g15mask(off)). Next: wait, review crops, measures, then hand-off.
- 10:16 queue: owner active (idle 2.1 of 5 min), my job behind shader-r015 loop1; ETA > 10 min -> exit per CLAUDE.md.
  Written while waiting: C:/qfb/gems/r015/tools/review_r015.py (masks from g15mask, auto crop boxes from the mask
  bbox, sheets review/<scene>.jpg, numbers.json: hf_sd glitter, sparkles/10k px, low_share sky sheet, white_frac,
  sat_top3; floor also *_far = far half) and C:/qfb/shaderdev/r015/textures_make_scenes.py (3 scenes gems15-close/
  pillar/floor x options A facets, B Stay True, C jewel, D calm, E frost; numbers auto from numbers.json; optional
  review/crops_manual.json overrides boxes; --ready touches TEXTURES-READY). Code committed.

## Next (resume here)
Render: `1101-101323-r015-gems-a` (18 scenes). Check: `py -3.10 -I tools/renderq/renderq.py results 1101-101323-r015-gems-a`
(or one blocking `renderq.py wait 1101-101323-r015-gems-a` if the status ETA is under 10 min).
1. `py -3.10 -I C:/qfb/gems/r015/tools/review_r015.py` -> check review/mask-*.png are the gems only (orange emerald
   vs wheat!), look at review/gem15_*.jpg. If a view misses (blocks off-frame, pillar too far), fix
   views-r015-gems.txt and resubmit only that scene (-b spec).
2. Judge each look: is it good art? (facets: rhombus pattern too regular? jewel: buttons? frost: grid?) Fix in
   tools/textures/gems_look.py, rebuild that pack (build cmd below), resubmit -b. Note numbers vs r014 (g14fai2
   floor glitter/sky sheet: see C:/qfb/gems/r014/review/numbers.json).
3. `py -3.10 -I -X utf8 C:/qfb/shaderdev/r015/textures_make_scenes.py`, view every crop in C:/qfb/shaderdev/r015/crops
   (aimed at the gems?), then rerun with --ready.
4. ops/tracks/textures.md, one journal entry (ops/journal/textures.md), commit own files, report <= 5 lines.
Build: `py -3.10 -I tools/textures/build_qf_textures.py --out C:/qfb/textures/r015/QF-gems-<look>.zip --stay-true
"C:\qf-world\reference-packs\Stay True 1" --gems facet --gems-ctm facet --gem-look <look>`
Shader question for shader-dev (ask in r015-shader or here): D "noise out at distance" is texture-only (blurred,
halved _n, even _s); a true distance fade needs a normal fade by LOD/distance in the gem path (not an existing option).
