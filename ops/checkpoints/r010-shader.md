# r010 shader checkpoint (orchestrator, 2026-10-27)

Input: docs/design/shaders/feedback/r009.json (owner, 2026-10-27). r009 is live (ab4ada7, critic 6.5). Open items
carried from r009: ops/checkpoints/r009-shader.md and ops/journal/shaders.md (forest gap cream sky, dust_b lower-shaft
motes, sea navy at sunset).

## Owner's answers (already in ops/DECISIONS.md)
QF_VOL_FAST stays on; daytime torchlight damping stays; the sun stays hidden behind its cloud; noon clouds keep the
cheaper version (no extra noise fetch).

## Owner's overall note
"We are kind of stalling on improvements ... you aren't asking the right questions ... I would like to be moving a lot
faster, and getting results that surprise me like the first big leap in quality for the water." So: bigger swings,
2-3 genuinely different directions for each weak scene, and every Lab question names the cause and the trade-off with
numbers. No question left general or vague.

## Order of work
1. **Meteors (owner rating 4, choice "neither"):** "It doesn't look like the meteors are coasting through the
   atmosphere overhead. These things look like they're plummeting to the ground. I want a beautiful cinematic meteor
   shower where it looks like a bunch of them passing by at high altitude." Make them Earth-grazers: radiant low or
   at the horizon, so streaks travel long and slow, nearly parallel to the horizon, across a large part of the sky,
   lasting about 1-4 s, with trains. Show 2-3 directions (e.g. grazers only; grazers plus a few overhead; a denser
   "storm" night). Re-read docs/design/shaders/research/meteor-showers.md on Earth-grazers.
2. **sunset-full (5/5) green tint:** "some weird green coloring right in the middle of the image". Find the cause with
   a crop and an option ladder before fixing.
3. **sun-cloud (4/5):** "make sure that the sun is interacting realistically with the clouds in front of it": bright
   silver lining on thin edges, the disk dimmed through thin cloud, hidden by thick cloud, and crepuscular rays.
4. **forest-light (3/5):** owner likes that B's rays "extend further, and they seem a bit broader". Bring A toward
   that, measured against cost.
5. **underwater (B, 3/5):** "really good", but visibility is a bit low in B. Raise it without losing B's look.
6. **river (3/5):** "very green": partly the reference's vegetation reflection. Cut the green cast; show the cause.
7. **dust (3/5) "seems close"**, golden (3/5) "fine", clouds and water-check fine: hold, only fix regressions.
8. Cost run on the final pack (cost mode, after 08:00), then critic, then publisher.

## Progress log
- 2026-10-27 16:43 (step 1 meteors, uncommitted until verified): Earth-grazers drawn in 3D in lib/sky.glsl
  (grazers(), gzClosest(); meteors() dispatches when QF_METEOR_STYLE > 0, the r009 body kept under #else). Each meteor is
  a straight track 88-118 km up, heading away from a radiant 1-5 deg above the horizon; per pixel, closest approach of the
  view ray to the track (a few dots per slot), so perspective gives long sweeps overhead and slow thin ones on the horizon.
  New options (settings.glsl): QF_METEOR_STYLE [0 1 2 3] default 1 (0 r009, 1 grazers 24 slots, 2 grazers + fireball
  procession every QF_METEOR_PROC_P s, 3 storm 40 slots), QF_METEOR_RAZ (pin radiant bearing, -1 per night).
  New view night_wide (views-world-master.txt, night_sky's bearing, pitch -22, treeline in frame). Offline numpy sim:
  scratchpad gzsim.py (gets wiped). check_glsl 0 errors (styles 0-3). Shot **1027-164245-r010-meteor1-shot**
  (C:/qfb/shaderdev/r010/specs/r10-meteor1.json): r10g1 stills night_sky+night_wide; clips r10g1c/r10g2c/r10g3c on
  night_wide, 120 frames x 100 ms, crop 320,180,1920,1080. Baseline r9mt / r9mclip.
  Next: review clips (make_clip.py, motion-max composite), tune, commit; then sunset-full green tint (step 2).

### Note from the texture agent (2026-10-27, r010 wall ladder 1027-164027, frames bench-t10d*-diag_column.png)
Gold reads darker than vanilla under the shader with ANY textures, so it is shader-side: relative to plain stone in the same
frame gold is 1.52x under every shader rung (Faithful 64x without maps, QF_PBR 0, our maps) vs 1.71x with shaders off. Under
the shader gold's blue channel is 0 in 81-98% of its pixels (vanilla B ~34) and red peaks at 154-161 (vanilla 179): the colour
grade / tonemap clips saturated yellow (box x 1134-1426, y 890-1022 of diag_column). Iron is fine (1.82x = vanilla).
The diamond "light only on the bottom half" was texture-side and is fixed (VNR normal Y + diamond no longer coded metal).
- 16:55 (step 2 sunset-full green, uncommitted until verified): cause from crops of bench-p9*-ocean_sunset (2560
  native, box 1020,660,1340,840; peak 95,173,121 at 1192,750): the mint patch survives waves/PBR/dust/shafts off and Low,
  and sits where reflected rays skim toward the island. waterSSR traces depthtex1 (no water), so the ray "hit" the sand a
  block under the surface and mirrored the mint shallows. Fix (composite.glsl waterSSR, new arg fromWater): a water
  reflection hit below the reflecting point's level (> 0.15 below) is a miss and the march goes on; metal SSR passes
  false. check_glsl 0 errors. Shot **1027-165502-r010-green-shot** (r10-green.json, tag r10sf: ocean_sunset +
  lake_glitter; baselines bench-p9-ocean_sunset / bench-p9-lake_glitter). Queue had the meteor shot first, ETA ~17:07.
- Sun-cloud notes (step 3, not started): in ocean_sunset the clouds round a 2-5 deg sun get the far-cloud melt
  (fade = exp(-t0/6500)*smoothstep(0.012,0.09,dir.y) ~0.2), while the disk uses the unfaded T: a hidden sun behind a
  cloud you barely see. Directions to try: (A) lift the melt near the sun + strong forward lobe on thin view-depth
  edges (silver lining), ALU only; (B) crepuscular rays as a screen-space radial blur of a cloud-T mask near the sun
  (12-16 taps, costs; ocean_sunset is already the worst High frame at 3.29 ms vs 3.0).
- 17:05 meteors loop 1 read (1027-164245, r10g1/r10g1c/g2c/g3c): parallel level streaks, right direction, but short
  dashes (wake 35-110 km) and trains 2 km wide drew 25 px comet bands with hard ends; night_wide at bearing 200 was a
  hillside; the burst writer takes ~1 s a frame (intervals 0.4 s, uneven). Loop 2 (uncommitted): wake = 40-65% of the
  burnt path (20-160 km), thinner/tapering; trains 0.12-0.7 km, dimmer (0.12), tapered by the burn; new dev option
  QF_METEOR_SLOW (clip slow motion) + make_clip.py --speedup; night_wide now bearing 135 pitch -18. Shot
  **1027-170451-r010-meteor2-shot** (r10-meteor2.json: r10h1 stills, r10h1c/h2c/h3c clips at SLOW 0.25, 150 frames,
  crop 640,360,1280,720; radiant 135). Clip: make_clip.py r10h1c night_wide --speedup 4. Review sheet script:
  scratchpad clipsheet.py (frames + max-over-time composite).
- 17:08 committed WIP **1028f79** (grazers, SSR fix, QF_SUN_CLOUD, views, make_clip --speedup). Then (uncommitted ->
  committed next line) three ALU-only ladders: QF_DUST_LEAF 2 (composite.glsl lightShafts: the 0.4 leaf cut only on rays
  < ~20 m: smoothstep(8, 30, dist)), QF_UW_VIS [1.0 1.4 2.0] (waterVolumeEye: non-swamp A and S / VIS, shafts
  untouched), QF_RIVER_TINT [0 1 2] (water.glsl WA/WS_RIVER: 1 teal-blue, 2 clear slate; composite bed hue pull
  teal-blue when > 0). QF_SUN_CLOUD [0 1 2] default 1: cloudMarch melt lifted within ~20 deg of sun/moon
  (smoothstep(0.93,0.995,mu)); 2 also silver lining 2.5x on the thinnest fringe (cloudLum).
- Renders queued (all shot mode, ETA ~17:25-17:30, other agents' jobs ahead):
  **1027-165502-r010-green-shot** r10sf ocean_sunset+lake_glitter (SSR fix; compare bench-p9-*; green peak was 95,173,121
  at 1192,750, box 1020,660,1340,840);
  **1027-170451-r010-meteor2-shot** r10h1 stills + r10h1c/h2c/h3c clips (make_clip.py TAG night_wide --speedup 4);
  **1027-170600-r010-suncloud-shot** r10sc0/1/2 ocean_sunset (crop round the sun ~x 1000-1500, y 500-800), r10sc1 forest_golden;
  **1027-170749-r010-ladders-shot** r10fl1/2/0 forest_golden, r10uv10/14/20 underwater_sun (+r10uv14 underwater),
  r10rt0/1/2 river_noon.
- **Next (fresh agent):** renderq.py results for each; sheets with tools/shaders/review/check_frames.py (or a PIL crop
  sheet) vs C:\qfb\shaderdev\refs and the r009 frames (bench-p9-*). Meteors: judge streak length/thinness, trains, the
  procession's chain (h2c) and the storm (h3c); if still dashes, lengthen wake fraction / raise speed. Pick defaults per
  ladder, then QF_UW_VIS / QF_RIVER_TINT / QF_DUST_LEAF defaults to what reads best (owner decides in the Lab: present
  each as A/B/C with the numbers). Crepuscular rays (sun-cloud) not started: needs a cost decision (screen-space radial
  blur ~12-16 taps near the sun; ocean_sunset is already the worst High frame, 3.29 ms vs 3.0). Then dust/golden
  regression check, cost run (cost mode, now allowed after 08:00), spec_scenes.py + round.json in C:\qfb\shaderdev\r010,
  critic, publisher. Every Lab question: cause + trade-off with numbers.
- At the end: ops/tracks/shaders.md still describes r008; rewrite it for r010, and add one journal entry (ops/journal/shaders.md).
### Note from the texture agent (2026-10-27 19:15): gold's lime sheen
With the map fixes, gold's metal pixels show a lime sheen in their top third (bench-t10lb-texture_wall.png, box ~1575,705,1700,800):
lighting.glsl uses the albedo as metal F0 (`f0v = metal ? s.albedo : ...`, metalShade tint), and gold's albedo after the grade has
B ~0 and G close to R, so a reflected green field and blue sky come out lime. Suggest: for LabPBR hard-coded metals (230-237) use
the spec's F0 table (gold 231 ~ (1.00, 0.78, 0.34)); textures cannot fix it without dropping gold's metal flag.

## Session 2 (2026-10-27 ~19:10)
Review of the four session-1 renders (crop sheets, scratchpad scripts csheet.py / clipmax.py, wiped with the session):
- **Green (r10sf):** SSR fix cut the mint from 1107 to 678 px (mask G>R+5 & G>B+5, box 900-1460 x 560-900); Low (no SSR)
  kept it, so the rest is the bed: QF_CAL_GOLD lights flat sand tops with 0.7 of the amber sun at golden hour and the
  composite bed filter faded to 0 as L.y -> 0, so orange sand through the sea's red absorption came out mint. New
  **QF_SHALLOW_SUN [0 1 2] default 2** (composite shadeWaterAbove): Fresnel transmission into the water (73 % reflected
  at 3 deg), filter held to the horizon; 2 also counts the bed's light as mostly the sun's at low sun (0.9 not 0.35).
- **Meteors (r10h1c/h2c/h3c):** level parallel streaks with tapering wakes look right, but each crossed ~15 deg (an
  eighth of the frame); procession barely caught; storm fireball glow read as a comet ball. Loop 3 (lib/sky.glsl
  grazers): dur 2-5 s, PB 7 (storm 6), side offset weighted overhead (sign * u^1.6 * 380 km), wake 55-85 % up to 300 km,
  fireball glow 0.12 at ~1 deg.
- **Sun-cloud (r10sc0/1/2):** sc1 vs sc0 0.7 luma in the sun box, sc2 == sc1 (the narrower fringe cancelled the 2.5x
  gain). Not a leap. Option 2 redone: rim lobe cap 80 -> 320 (cloudMarch c.rim), gain 0.045 -> 0.09. New High-only
  **QF_CREPUSCULAR [0 1] default 0**: deferred writes the sky's cloud T (gSkyT) to colortex1.g (RENDERTARGETS 3,1, only
  when on); composite crepuscularGain(): 16 taps along the screen line to the sun, sky gain 0.5 (wedge) .. 1.15 (lane).
- **Forest (r10fl*):** fl2 == fl0 because `#if QF_DUST_LEAF == 1` wrapped the `== 2` branch (fixed to >= 1). All
  three within 1.1 luma of each other. New ladder: fm2 (fixed DUST_LEAF 2), fm3 (+ QF_SHAFTS 2, gain 2.0).
- **Underwater (r10uv*):** far-terrain local contrast (|l - box15 mean|) 1.10 / 1.40 / 2.0: 1.55; hue unchanged.
  Default **QF_UW_VIS 2.0**.
- **River (r10rt*):** water mean rt0 51,79,63 (green); rt1 50,74,80 (teal-blue); rt2 48,65,68 (just darker; the bed veil
  in composite sets the look). Default **QF_RIVER_TINT 1**; option 2 reworked as "clear stream" (WA 0.11/0.06/0.06,
  veil 0.6 blocks x1.8, hue pull 0.25).
- **Gold (texture note):** cause found. diag_column box: gold 178,152,34 off -> 150,126,1 PBR 0 (iron 154 -> 128,
  stone level). (a) lighting.glsl PBR-0 metal path `color *= 0.65`, PBR-1 metalShade with SSR keeps 0.30 of diffuse;
  (b) vibrance pushed the weakest channel below 0 and clipped it. Fix: **QF_METAL_FLOOR 1** (0.65 -> 0.92, 0.30 ->
  0.62) and vibrance k held so the weakest channel keeps >= half its value (global, final.glsl).
- check_glsl: 0 errors, all presets and the option combos.
- **Renders queued (19:07), ETA ~19:35-19:45:** **1027-190711-r010-loop2-shot** (r10-loop2.json: r10l2 defaults on
  ocean_sunset, lake_glitter, beach_noon, river_noon, underwater, underwater_sun, forest_golden, diag_column; r10ss0,
  r10ss1 ocean_sunset; r10sd2 ocean_sunset+forest_golden; r10cr1 ocean_sunset+forest_golden+lake_glitter; r10fm2,
  r10fm3 forest_golden; r10rv2 river_noon; r10gd0 diag_column) and **1027-190711-r010-meteor3-shot** (r10i1 stills,
  r10i1c/i2c(240 fr)/i3c clips). DO NOT edit shaders/ until both have booted (the pack is read live).
- **Next:** review (ocean_sunset box 900-1460 x 560-900 mint count vs r10sf 678; sun box 1000-1500 x 400-620 for sd2/cr1;
  gold/stone in diag_column: gold box x1134-1426 y890-1022, stone x820-1100 y1000-1100, target ~1.8; beach_noon vs
  bench-p9-beach_noon for SHALLOW_SUN at noon; underwater at 2.0 vs bench-p9-underwater). Cost of cr1 needs a cost-mode
  run (ocean_sunset is already 3.29 ms on High). Then cost run on the final pack, spec_scenes.py + round.json in
  C:\qfb\shaderdev\r010 (texture scenes from texture_scenes.json / frills_scenes.json when READY files exist),
  track rewrite, journal entry.

## Session 3 (2026-10-27 ~19:30)
Review of 1027-190711-r010-loop2-shot and -meteor3-shot (scratchpad sheet.py / clipmax.py / measure.py, wiped with the session):
- **Meteors (r10i1c/i2c/i3c):** long thin level streaks, tapered wakes, bright heads, parallel; cinematic. Settled:
  QF_METEOR_STYLE 1 default; i2c (procession) and i3c (storm) as Lab options. Best frames: i1c f024, i2c f023, i3c f107.
- **Mint (ocean_sunset box 900-1460 x 560-900):** p9 1107, r10sf 678, l2 (SHALLOW_SUN 2) 686, ss0 692, ss1 661: the
  shallow-sun filter does NOT touch it; the mint shallows left of the island remain. Cause theory (bed lit by the golden
  boost) unproven: the filter is weighted by `sh`, and the patch may be in the island's shadow. Next: debug views.
- **Sun-cloud:** sd2 == l2 (sun box luma 181.8 vs 182.3): SUN_CLOUD 2 does nothing visible; keep 1. cr1 (crepuscular)
  -7 % luma in the sun box, soft wedges, subtle; needs the cost number.
- **Forest:** l2/fm2/fm3/cr1 all near-identical to p9; no visible longer rays. Honest "no leap" in the Lab.
- **Underwater 2.0:** canyon reads further and bluer; keep. **River tint 1:** teal-blue, good; rv2 brings back
  yellow/mint ledge stripes (keep as option C with that note). **Beach/lake:** unchanged by SHALLOW_SUN (good).
- **Gold:** loop2's diag_column ran in the default world (no column): the spec missed `world: C:/qfb/textures/world-showcase`.
  Gold must be re-measured there (texture pack C:/qfb/textures/diag/QF-l-dense.zip = t10lb, baseline bench-t10lb-*).
- 19:30 (uncommitted until verified): **QF_METAL_F0 1** (lib/lighting.glsl metalF0(): LabPBR F0 bytes 230-237 use the
  real metal F0 table x texture brightness; metalShade/metalReflection take the F0 byte). Water debug views 11-14 in
  shadeWaterAbove (11 sh/F/depth, 12 bed as lit, 13 transmitted, 14 reflected). check_glsl 0 errors.
  Shot **1027-193024-r010-diag3-shot** (specs/r10-diag3.json): r10m11-14 ocean_sunset; r10gf1/r10gf0 (METAL_F0 1/0)
  diag_column+texture_wall on world-showcase with QF-l-dense.zip; r10gfoff shaders off diag_column.
  Gold boxes: gold x1134-1426 y890-1022, stone x820-1100 y1000-1100 (diag_column); lime box texture_wall ~1575,705,1700,800.
- 19:40 diag3 read: **mint cause found** (debug 12): where depthtex1 has no terrain behind the sea (dR = 1), `behind`
  was the sunset sky itself, and 32 blocks of reef water took its red: the mint wedge (151,185,130) is the horizon glow
  seen through the sea. Fix in both water paths: no bed in view -> behind = 0 (in-scatter only). QF_SHALLOW_SUN back to
  0 (not the cause; ss0/1/2 692/661/686). **Gold:** METAL_FLOOR + vibrance floor: gold/stone 1.48 (t10lb) -> 1.77
  (gf0) / 1.74 (gf1), vanilla 1.82; blue clipped 61 % -> 0 %. METAL_F0 1: wall gold-top G/R 0.97 (t10lb) -> 0.941 (gf0)
  -> 0.934 (gf1); the lime read is gone in gf0/gf1 crops (mostly the vibrance floor). Defaults settled: METEOR_STYLE 1,
  SUN_CLOUD 1, DUST_LEAF 1 (fm2/fm3 no visible change), UW_VIS 2.0, RIVER_TINT 1, METAL_FLOOR 1, METAL_F0 1,
  CREPUSCULAR 0 (owner question), SHALLOW_SUN 0. Next: commit, cost spec, submit, spec_scenes.py, round.json.
