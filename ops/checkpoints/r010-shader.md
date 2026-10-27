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
