# r016 shader, sky pass 1 (shader-dev, 2026-11-01)

Plan: ops/checkpoints/r016-plan.md "Process change" + "Sky". Targets: critic r015 WORK ORDER
(C:\qfb\shaderdev\r015\critic.json `_r015_publish_summary`). Work dir C:\qfb\shaderdev\r016\{specs,sheets,tools,measure}.

## Tools
- `py -3.10 -I C:\qfb\shaderdev\r016\tools\measure.py TAG [--sea T --shore T --night T --sun T]`: pass/fail per target,
  regions calibrated so p15 reproduces the critic's r015 numbers (band 2.76, top tenth 251,204,128, darker half 2.70,
  upper-sky blue>green 50 %); writes r016\measure\TAG.json.
- `tools\grid.py`, `tools\zoomrows.py OUT scale x,y,w,h files...`, `tools\sand.py` (sand under the sun).

## Progress log
- 15:45 Sun-glow finding (item 4): on the sand block right under the sun (sun_clear, box 1150,668,300,50) the block's
  top edge sits at row 27, flat, with QF_SUN_HALO 0 (p14cc, p14rcc: two runs), and at rows 28-30, jagged, with HALO 1
  (p14cch1 = D, and p15cc = today's default): the tight HG 0.9 haze lobe brightens the far top faces by distance, so
  the glow eats 1-3 px into the block tops unevenly; frame-to-frame shimmer 0.86-0.98 vs 0.67-0.71. The default
  (HALO 1) already has D's effect: p15cc vs D differ 1.21, C vs D 2.58. Sheets r016\sheets\hz_CD_zoom.png, sand4.png.
- 15:52 Code (all check_glsl clean): QF_SUN_WHITE 1 (final.glsl per-channel shoulder past peak 5 at golden hour;
  composite.glsl hottest glint facets take the light's peak in every channel), QF_SEA_FAR 3 (no far easing, sunK
  0.95-0.99 full), QF_DUSK_SKY 3 + QF_DUSK_RAY 0.40 (photon.glsl Rayleigh tint under 7 deg), QF_METEOR_SKY 3 +
  QF_METEOR_NAVY 0.10 (sky.glsl: navy, phStars 700/7000-20000 K/x2, MW blue-white, clear 0.26, no amber meteors).
  Submitted **1101-155233-r016-loop1** (specs\r16-loop1.json: s16a, s16acc, s16am, s16w2, s16r30, s16r60, s16n14).

- 16:04 loop 1 sea frames in (s16a, s16w2; sheet r016\sheets\l1_sea.jpg): horizon step back to r014's (23 px, PASS);
  the sun's core now clips (204 px at 250+ all channels, top 200 px 255,253,251; p15 0 px) but BSL's disk is 2885 px;
  band 2.76 -> 2.57, darker half 2.70 -> 2.63, brightest tenth 251,213,152 (r/b 1.65), clip 0.5 %: FAIL. Cause seen
  in the crop: the path stops at the island's reflection, the far band under the sun has no core. The SSR hit
  (calm normal, mirrors 1-5 deg up, finds the island) hid the glint, which comes off facets mirroring the sun 9 deg
  up. Fix: under QF_SUN_WHITE the SSR occlusion applies only where the calm mirror ray is within ~3-6 deg of the
  sun. SUN_WHITE 2 now also whitens glint facets from exposed 0.5 (1 from 1.0). Submitted **1101-160434-r016-loop2**
  (s16b, s16bw2, s16bd14 = reflection x F, s16bd13 = body). Queue paused 16:05: owner playing a game.

- 16:20 queue still paused (owner in a game since 16:05; loop 1 at 2/8, loop 2 queued behind). Wait > 10 min, so
  checkpointed and exited per the rules. Note: texture-dev's 1101-155222-r016-gems-a snapshot carries these defaults
  too; they act only at golden hour (SUN_WHITE, DUSK 3) or on a shower night (METEOR 3).

## Current best per item (render IDs, frames)
Frames in C:\qfb\shaderdevounds\screenshotsench-TAG-SCENE.png.
- Sea: s16a (1101-155233-r016-loop1) bench-s16a-ocean_sunset.png; s16w2 same job. Loop 2 (1101-160434-r016-loop2,
  s16b / s16bw2 with the SSR occlusion fix) not rendered yet: likely the better one.
- Shore: s16a shore_sunset, s16r30, s16r60 (loop 1): not rendered yet. r015 baseline bench-p15-shore_sunset.png.
- Meteor night: s16am, s16n14 night_wide (loop 1): not rendered yet. Cost not measured (needs a cost job vs p15m 2.98).
- Sun glow: s16acc sun_clear (loop 1) not rendered yet; today's default p15cc already has D's effect (below).

## Targets (critic r015 work order) vs measured, measure.py
| Item | Target | r015 | Best now | Pass |
|---|---|---|---|---|
| Sea | band brightest tenth ~254,250,235, r/b <= 1.1 | 251,204,128 (1.96) | s16a 251,213,152 (1.65) | FAIL |
| Sea | >= 5 % of far band at 250+ all channels | 0.0 % | s16a 0.5 % | FAIL |
| Sea | sea beside the path (band's darker half) ~2.35 | 2.70 | s16a 2.63 | FAIL |
| Sea | far band r/b 2.0-2.1 | 2.76 | s16a 2.57 | FAIL |
| Sea | sun core clips to white | 0 px at 250+, top 200 px 255,247,239 | s16a 204 px, 255,253,251 | PASS (core); BSL's disk 2885 px |
| Sea | horizon strip reverted (step spread r014 24 px) | 54 px | s16a 23 px | PASS |
| Shore | top right ~75,65,72 | 115,106,118 | not rendered | - |
| Shore | between clouds ~120,90,65 (open sky darkest 30 %) | 117,96,111 | not rendered | - |
| Shore | upper sky blue>green <= 15 % | 50.4 % | not rendered | - |
| Shore | ~40 % darker (upper-sky luma vs r015; BSL 0.75) | 1.00 | not rendered | - |
| Shore | red <= blue above ~30 deg (BSL itself 1.71) | 1.48 | not rendered | - |
| Shore | keep rims 250,157,83 | 250,157,83 | not rendered | - |
| Night | sky median ~18,22,38 | 4,7,15 | not rendered | - |
| Night | brightest stars ~170,180,210 (300 px) | 191,168,133 | not rendered | - |
| Night | cost <= 2.98 ms | 2.98 | not measured | - |
| Sun | default has D's sand effect (block top row >= 28, jagged) | C 27.0 flat, D 28.9 | p15cc (default HALO 1) 28.8, jag 0.62 | PASS (on r015 frames) |

## Next
- Loop 1 rest (s16acc, s16am, s16r30, s16r60, s16n14): measure.py s16a --night s16am --sun s16acc; r30/r60 on shore.
- Loop 2: measure s16b/s16bw2; debug 14/13 band r/b tells whether the darker half's orange is the reflection or
  the broad glint lobes (lightIrradiance colour) -> next: whiten/narrow the broad lobe or widen sunK.
- Sea, if loop 2 still short: (a) the far band's core is too dim/sparse next to BSL's solid 80 px column (luma 240):
  raise the tight lobe at golden hour in the far band (balance -> 1.0, a2c core x1.5) under QF_SUN_WHITE; (b) darker
  half: if debug 14 shows the reflection is the orange, widen sunK (0.90-0.98) or ease hueK by 50 % within 25 deg; if
  the broad lobes, tint them halfway to the white of the core. (c) The disk: BSL's is ~14x larger; if the critic asks,
  QF_SUN_SIZE or the soft blob's k.
- Shore: pick DUSK_RAY from r30/r40/r60 against the table; if "between clouds" stays pink, cut the Mie blue (0.72 ->
  0.55) under DUSK 3 and re-check the rims and the left cloud's underside (124,99,66).
- Night: tune METEOR_NAVY to the 18,22,38 median; then a cost job (p16m vs p15m vs p16ms0, night_wide) for <= 2.98.
- Sun glow: s16acc must keep top row >= 28 (measure.py --sun s16acc); sheet tools\sheet.py row 5 (default vs D).
- Then hand the frames to the critic: sheet `py -3.10 -I C:\qfb\shaderdev\r016\tools\sheet.py OUT SEA SHORE NIGHT SUN`.
