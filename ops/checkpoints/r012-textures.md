# r012 textures: Stay True carry-overs (texture-dev, 2026-10-28)

Brief: ops/checkpoints/r012-plan.md "Textures: Stay True carry-overs"; background ops/checkpoints/r011-stay-true.md.
1. Gems: find WHY r011's Stay True gems were not glassier in a still (numbers), then 2-3 genuinely different options in
   a still view that shows reflection.
2. Roofed forest: re-aim biome_roofed into the dark oak canopy; re-render hooks off/on (+ r010 frills?).
Hand-off: C:\qfb\shaderdev\r012\ + ready marker.

## Progress log
### session 1
- Started. Read plan + r011-stay-true.
- Gem cause, measured (scripts in session scratchpad, recreate from these numbers):
  - Textures: Stay True diamond albedo = Faithful's (lum 207 vs 210, sat 0.60 vs 0.64). Its glint: mcmeta holds frame 0
    for 200 ticks then 7 glint frames x 1 tick (emerald 230 + 9 x 1) -> a still shows the glint 3.4% (4%) of the time.
  - PBR maps: r010 diamond = Faithful 64x + VNR hybrid _n, a dome (mean tilt 23.8 deg, p90 42); r011 Stay True gems are
    "drawn" -> labpbr.py's own flat _n (2.3 / 3.6 deg). Smoothness 222 -> 232 (diamond), emerald 158/F0 14 -> 230/F0 44.
  - Shader (lighting.glsl dielectric path): sky reflection = skyScatter(R) * F(NdotV) * s^2, no SSR, and skyScatter clamps
    R.y to 0, so a flat face seen level or from above reflects the brightest, whitest horizon sky on every pixel: a
    uniform wash. GGX a2 floor 0.0015 at s 0.9: a sun highlight needs N.H within ~2 deg: never on a flat vertical face.
  - Frames (diag_column diamond face, x1140-1420 y580-712): r010 t10lb mean 145 std 21.7 sat 0.854 top->bottom bands
    170..116; r011 gm1b mean 166 (+15%) std 13.3 (-39%) sat 0.647 (-24%) bands 170..162 (flat). diag_emerald
    (x1135-1415 y615-745): r010 d6 mean 119 sat 0.986; gm1b 135 (+13%) sat 0.764 (-23%) (reflection term 6.6x r010's:
    s^2*F0 0.81*0.17 vs 0.38*0.055).
  - Verdict: paler + flatter = a bigger uniform horizon-sky wash on a face whose dome normal was lost; not the albedo.
    The glint only exists in motion. Emerald's nested squares are Stay True's art itself.
  - Other reference packs: only Stay True has diamond/emerald blocks (Faithless, Patrix, Conquest, Soartex: none).
- Plan: world copy C:\qfb\textures\world-gems (build_showcase.py --gems: gem floors + pillars), views gem_glint (low sun
  ahead, floor glint) and gem_lit (morning sun on the faces). Options: A Faithful facet gems + VNR dome on both + glass
  maps (texture only); B Stay True art, emerald re-toned from Stay True's diamond (no nested squares), dome maps, glint
  clip; C = A + shader: polished dielectrics take the metal SSR path (real scene + ground below the horizon), private pack
  copy (shader track ships it if picked). Roofed: new view roofed_canopy (biome_roofed stays: shader fog scene).
- Code (uncommitted yet): gems.py (+ramp_from, dome_normal, emerald_from_diamond by_value), build_qf_textures.py
  `--gems facet|staytrue` (smoothness 240, F0 44 both; facet: emerald reuses diamond's VNR dome _n; staytrue: dome _n
  tilt 0.52 = 23.8 deg mean like VNR's, emerald = Stay True diamond re-toned by value in Stay True's emerald colours).
  Built C:\qfb\textures\r012\QF-gems-facet.zip (A) and QF-gems-staytrue.zip (B), both with --stay-true. Texture sheet
  checked: B emerald reads as Stay True's diamond face in green, no squares; glint frames keep timing.
- World C:\qfb\textures\world-gems (build_showcase.py --src world-showcase --dst world-gems --gems): diamond floor x244-250
  z181-185, emerald floor z188-192 (y67, flush), 3x3 pillars at x243. Views appended to views-world-master.txt:
  gem_glint_d, gem_glint_e (11000, looking west into the sun), gem_lit (4000, sun behind), roofed_canopy, roofed_edge
  (over the lake at x -205.5 z -124.5, canopy edge x -210, top y 80-82; biome_roofed left as is: shader fog scene).
- Option C shader: private copies of HEAD's pack, C:\qfb\gems\base\shaders\QuestForge and ...\ssr\... (patched:
  composite gemReflection = metalReflection with untinted F(F0) for smoothness > 0.88 and F0 > 0.1; deferred skips the
  skyScatter wash there and scales the diffuse by 1-F). Diff: C:\qfb\gems\gem-ssr.patch (40 lines). check_glsl: 0 errors.
- 15:03 guard OK. SUBMITTED `1028-150300-r012-gems-a` (spec C:\qfb\gems\specs\r012-gems-a.json; tags g12r10, g12r11,
  g12a, g12b, g12c, g12cb on gem_glint_d/e + gem_lit, g12bclip = B gem_lit burst 84 x 133 ms crop 0,360,1280,720)
  and `1028-150300-r012-roofed-a` (C:\qfb\gems\specs\r012-roofed-a.json; st2r0 off / st2r1 on, cost, MeshStats
  C:\qfb\frills\stats\st2r{0,1}.txt). Behind shader-r012 loop1 (16 scenes).

## Resume here
1. `py -3.10 -I tools/renderq/renderq.py results 1028-150300-r012-gems-a` and `... 1028-150300-r012-roofed-a`.
2. Gems: sheet `py -3.10 -I C:\qfb\frills\scripts\grid.py OUT.jpg 900 g12r10,g12r11,g12a,g12b,g12c,g12cb gem_glint_d
   gem_glint_e gem_lit`; numbers per floor/pillar crop (reflection contrast: std, sat, highlight %>240) vs r010/r011.
   Glint clip: frames bench-g12bclip-gem_lit-f*.png; find the glint frames; make_clip.py -> webp.
3. Roofed: grid st2r0,st2r1 roofed_canopy roofed_edge; pick the better view; cost frills_cost.py --off st2r0 --on st2r1.
4. Hand-off: C:\qfb\shaderdev\r012\textures_make_scenes.py -> textures_scenes.json + TEXTURES-READY (pattern:
   C:\qfb\shaderdev\r011\staytrue_make_scenes.py). Track file, journal, commit, push.
