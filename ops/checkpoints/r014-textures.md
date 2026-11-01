# r014 textures: gem MATERIAL (texture-dev, 2026-10-31)

Brief: ops/checkpoints/r014-plan.md "Textures". Owner r013: metals connected B (4) picked; gems-ctm-diamond/emerald/lit
all "neither" (5); shader gems scene 3, "Right idea, but I don't like this. It looks like plastic." Keep the connected
layout (gems_ctm.py), change the material. Hand-off: C:\qfb\shaderdev\r014\ (textures_scenes.json, crops, TEXTURES-READY).

## Progress log
### session 1
- Read plan, r013-textures.md, critic r013 gem notes. r014-shader.md does not exist yet (shader-dev starting).
- Material today (build_qf_textures.py --gems facet --gems-ctm facet): _s smoothness 240 and F0 44 on EVERY gem pixel;
  shader (lighting.glsl/composite gemReflection): diffuse *= 1-Fe, + untinted scene reflection * Fe.
- Reference gem PBR found: Patrix 32x has diamond/emerald/amethyst/lapis/gold _n and _s (+ ctm random/repeat folders).
  Extracted (private, never committed) to C:\qfb\gems\r014\ref\{patrix,soartex,staytrue}.
- r013 frames: C:\qfb\shaderdev\rounds\screenshots\bench-{g13c,g13facet,g13flat,g13c12,g13coff,g13c0}-gem_*.png
  (g13coff = shaders off, for masks; g13c0 = QF_GEM_SSR 0).

### session 1: why it reads as plastic (numbers; C:\qfb\gems/r014/tools\plastic_numbers.py, lowfreq.py; masks from g13coff)
- Material: _s smoothness 240 + F0 44 on 100 % of gem pixels (std 0): the plastic BRDF, an even white coat on even paint.
- Flat colour, no depth: Faithful 64x diamond face = 9 tones, luma CV 0.09, 0 % of pixels < 0.6x mean (Patrix and
  Soartex amethyst: CV 0.38, 12-19 % dark, 17-19 % bright). Rendered with the sun behind (gem_lit, g13c) the face's
  high-frequency sd is 0.04 against 0.14 for round 12's C: a nearly flat-coloured slab.
- Reflection over the whole face: on gem_glint_d/e 74-89 % of the face's brightness variance is low-frequency (one
  smooth sky/pillar gradient across the slab; sigma 12 px), r12 C 22-63 %. Connected + flat face made it a glossy sheet.
- Glints: top-3 % pixels are white (saturation 0.16-0.32 vs body 0.62-0.74); 19-21 elongated glint blobs per floor,
  52-53 % in one 30-degree bin, ~85 % within 0-60 deg: same-angle dashes (the critic's "rain on ice").
- Shader side (for shader-dev, not changed by me): gemReflection is untinted, one Fresnel for the whole face, no
  roughness blur unless smoothness < ~0.6; the gem path needs smoothness > 0.88 and F0 > 0.1 (else ordinary sky-only
  path); no SSS or emission is read (_s B and A ignored), so internal brilliance can only be painted in albedo.
- BSL 10.1.8 (C:\qfb\gems/r014/bsl): no gem special case. Dielectric reflection = mix(F0, 1, fresnel) * remapped
  smoothness (s^2/(2-s)), albedo darkened by fresnel*smoothness^2, rough reflections blurred by LOD. Its gems look
  like gems only through the pack's maps: per-pixel smoothness/F0 and faceted normals.
- Reference maps: Patrix 32x diamond _n = large planar facets (median tilt 22 deg), _s 255/228, SSS 255; amethyst _n
  crystal facets (median 28 deg, ~30 crystals/128 px), _s smoothness 126-250 (crystals smooth, gaps rough), F0 115,
  SSS 179-220; normals DirectX like ours (crystal y~G corr +0.40). Stay True diamond = Faithful-like streaks + glint
  animation (no maps). Soartex = frosted low-saturation.
- Constraint found: ctm interior tiles are 1-block periodic, so any low-frequency shape (big facets, depth gradient)
  repeats per block as a pattern. Big Voronoi facets (9 or 18 cells) looked like camo / crazy paving: dropped.

### session 1: materials (tools/textures/gems_mat.py, builder --gem-mat; sheets C:\qfb\gems/r014/an\mat_*.png)
- crystal: Patrix amethyst 4x4 repeat texture (128 px) read at native size, 64-periodic by the r013 quilting,
  re-toned by value onto a deeper ramp (Faithful's tones + 2 deeper), Patrix _n kept, _s crystals -> 230-255/F0 44
  (gem path), gaps -> rough/F0 10. polished: same colour, flat _n, _s 250/F0 30. faithful: Faithful face by rank on
  the deeper ramp + crystal _n/_s. Frame = Faithful rim + r013 bevel; tile 0 = the block.
- Packs: C:\qfb/textures/r014\QF-gems-{crystal,polished,faithful}.zip (only the 288 gem entries differ from r013
  facet). Shader frozen at HEAD cecae3e: C:\qfb\gems/r014\shader-r013. Views + close-ups:
  C:\qfb\gems/r014/views-r014-gems.txt (gem_close_d/e/lit added).
- 19:48 guard OK, SUBMITTED `1031-194802-r014-gems-mat-a` (g14r13 control, g14cry, g14pol, g14fai; 6 scenes each;
  spec C:\qfb\gems/r014\specs/r014-gems-mat-a.json). Queue ETA past 20:06 (shader-dev loop0/1 + packs ahead).

## Next (resume here)
Render: `1031-194802-r014-gems-mat-a` (24 scene renders; at 19:50 the queue ETA was ~20:16, behind shader-dev's
r014-loop0/loop1 and textures-r014-packs). Check: `py -3.10 -I tools/renderq/renderq.py results 1031-194802-r014-gems-mat-a`.
1. When it lands: `py -3.10 -I C:/qfb/gems/r014/tools/review_r014.py` -> sheets C:/qfb/gems/r014/review/<scene>.jpg
   (crops of g14r13/g14cry/g14pol/g14fai side by side) and review/numbers.json (L_cv, hf_sd, low_share, dark_frac,
   sat_top3, white_frac, glint dashes / top_bin_share vs the r013 numbers above). Set the gem_close_* crop boxes in
   CROP after looking at one full frame (views are guesses: 4-5 blocks from the pillar, pitch 28 / 14).
2. Judge: does each read as gem, not plastic? Watch for a per-block repeat pattern (1-block period), the frame
   against the new face, crystal gaps too rough/dark, polished = "pool of glass" again (critic r013 flat).
   If one fails, fix gems_mat.py, rebuild that pack (command below), resubmit a -b spec.
3. Hand-off: write C:/qfb/shaderdev/r014/textures_make_scenes.py (model: C:/qfb/shaderdev/r013/textures_make_scenes.py)
   -> textures_scenes.json: scenes gems-mat-diamond (gem_glint_d), gems-mat-emerald (gem_glint_e), gems-mat-lit
   (gem_lit), gems-mat-close (gem_close_d or _e); options A = round 13 connected (g14r13), B crystal, C polished,
   D faithful; crops in C:/qfb/shaderdev/r014/crops aimed at the floors/pillars (check every crop); touch TEXTURES-READY.
4. Track ops/tracks/textures.md, one journal entry, commit (stage own hunks only), report <= 5 lines.

Build (one per material):
  py -3.10 -I tools/textures/build_qf_textures.py --out C:/qfb/textures/r014/QF-gems-<mat>.zip
     --stay-true "C:\qf-worldeference-packs\Stay True 1" --gems facet --gems-ctm facet --gem-mat <mat>
Tile check (done for the a-build): ctm tile 26 gem-path share crystal/faithful 0.65, polished 1.00; albedo luma CV
crystal 0.29/0.35 (diamond/emerald), faithful 0.21/0.25, vs r013 0.09.

### session 2
- 20:16 render 1031-194802-r014-gems-mat-a done; review_r014.py run -> C:/qfb/gems/r014/review/*.jpg + numbers.json.
  Next: look at sheets, set close-up CROP boxes, judge, hand-off.
- 20:22 judged (numbers C:/qfb/gems/r014/review/numbers.json): crystal + faithful beat r13 on every plastic measure;
  polished DROPPED (coat measures = r13: low_share 0.67-0.70, sat_top3 0.15/0.21, white 0.072). Close crop boxes set
  in review_r014.py (close_d/e 760,300,1440,810; close_lit 200,470,2160,970). Next: textures_make_scenes.py hand-off.
- 20:30 HAND-OFF DONE: C:/qfb/shaderdev/r014/textures_make_scenes.py -> textures_scenes.json (gems-mat-diamond/emerald/
  lit/close; A g14r13, B g14cry, C g14fai), crops C:/qfb/shaderdev/r014/crops/g14*.png (all checked: sheet
  C:/qfb/gems/r014/review/handoff_crops.jpg), TEXTURES-READY touched. Next: track, journal, commit, push.
- 20:35 track + journal updated. Next: commit (own files: ops/checkpoints/r014-textures.md, ops/tracks/textures.md,
  ops/journal/textures.md), git log origin/main..main, push.
- 20:38 DONE: committed c3c50fa, pushed. Task complete; next is the owner's r014 pick.
