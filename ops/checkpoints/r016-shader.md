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

- 18:35 loops 1-2 measured (numbers in the table). Findings: (1) loop 2's SSR fix changed nothing (s16b = s16a): the
  glint is cut by the island's SHADOW on the water (hard diagonal edge, sheets\l2_band3x.png; BSL's column has the same
  edge, its sun sits ~33 px further left); the lit part left of it is too dim to clip (exposed ~2-3, the curve keeps
  orange). (2) debug 14 vs 13: the band's darker half is the mirror (2.65), the body is 0.83. (3) shore: DUSK_RAY moves
  g/b only, top right red stays ~130 (the sunlit air, not Rayleigh). (4) night: the "brightest stars" were the green
  meteor trains; measure.py now masks streaks: stars 121,144,163 (cyan, dim); s16n14 was NAVY 0.20 -> 13,18,31.
  (5) sun: s16acc rows 28.9 jag 0.38 shimmer 0.70: D-like, PASS (sheets\l1_sand.png).
  Code (check_glsl clean, variants too): QF_SUN_WHITE 3 + QF_GLINT_GAIN (hot core x(1+gain)), QF_SEA_NEAR 0-3 (mirror
  near the sun's bearing -> warm white), QF_DUSK_ZEN 0-3 (sky above 8-26 deg loses red/green, sun < 7 deg only; sky
  pixels and the water's mirrored sky), QF_STAR_GAIN, QF_STAR_TMAX. Submitted **1101-183455-r016-loop3**
  (specs\r16-loop3.json: s16c1/c2/c3 sea+shore, s16ccc sun, s16cm1/cm2 night).

- 18:43 loop 3 measured. Sea best s16c2 (GAIN 8, NEAR 3): 250+ 3.6 %, top tenth 253,229,191 (1.32), darker half 2.44
  PASS, mean 2.27; the column's lit part is white now (sheets\l3_band3x.jpg), the island's shadow still cuts its right
  half. Shore: ZEN 3 (s16c3) passes top right 68,62,68, r/b 1.03, darker 0.64, rims 240,147,60, but blue>green 52 %
  (its g cut > b cut). Night s16cm1 (NAVY 0.30, STAR_GAIN 0.070, TMAX 15000): median 17,23,37, stars 161,189,207, half
  153,181,200: all PASS -> made the defaults. Sun: SUN_WHITE 3 made a white blob over the sand (s16ccc, rows 27.4 FAIL,
  sheets\l3_sand.png) -> loop 4 fades the white-hot core in from 2 to 6 deg sun (SUN_WHITE 1 below) and adds
  QF_GLINT_LO; ZEN 1/2 now cut g and b alike (grey, g>=b), ramp from 10 deg. Submitted **1101-184251-r016-loop4**
  (s16d1/d2 sea+shore, s16d3 sea, s16dcc sun) and **1101-184251-r016-night-cost** (cost mode p16m, p16ms0, p16moff;
  priority 0, runs when the owner is idle).

- 18:48 loop 4 measured. Sea: s16d2 (GAIN 12, LO 0.3, NEAR 3) 250+ 4.5 %, top 253,241,222 (1.14), darker half 2.45,
  mean 2.14 PASS; s16d3 (GAIN 8, LO 0.2) top r/b 1.11, mean 2.09, 3.9 %. Shore d1/d2 pass most numbers but the sky
  and the orange clouds went OLIVE-TEAL (sheets\l4_shore.jpg): rejected on the look; c3's mauve is the nearest to BSL.
  Sun: s16dcc still a white blob (fade 2-6 deg too low; sun_clear's sun is ~4-5 deg up). Loop 5 code: hiSun 5-8.6
  deg; ZEN 1 = 0.20/0.40/0.56, 2 = 0.22/0.42/0.60 (mauve grey); bright sky pixels (exposed > 0.6-2) keep their colour
  (rims). Submitted **1101-184815-r016-loop5** (s16e1 GAIN 16 LO 0.2 ZEN 1; s16e2 GAIN 24 ZEN 2; s16ecc sun).

- 18:55 loop 5: SEA s16e1 (SUN_WHITE 3, GAIN 16, LO 0.2, NEAR 3) passes all but the darker half (2.46 vs <=2.45):
  top tenth 254,246,235 (1.08), 250+ 5.4 %, mean 2.07, sun 571 px; e2 (GAIN 24) 6.0 %, 2.47. Column white to the
  horizon left of the island's shadow (sheets\l5_band.jpg). Shore e1/e2 (ZEN 1/2): slate sky, olive upper-left cloud,
  share 45 %: rejected. Sun s16ecc: blob worse (clip 3121 px; acc 710): both suns stand ~as high, so the gate is now on
  the view (1.1-2.6 deg under the horizon). Night cost (1101-184251-r016-night-cost): p16m 3.37 - off 0.45 = 2.92 ms
  PASS (p15m 2.98). Loop 6 code: ZEN 4/5 = darken (0.50/0.40) + drain to warm grey, no per-channel cut; SEA_NEAR 4.
  Submitted **1101-185509-r016-loop6** (s16f1 NEAR 4 ZEN 4; s16f2 NEAR 3 ZEN 5; s16fcc sun).

- 19:01 loop 6: SEA s16f1 (SUN_WHITE 3, GAIN 16, LO 0.2, NEAR 4) PASSES ALL 7 (254,246,235 r/b 1.08; 5.4 %; darker
  half 2.40; mean 2.03; sun 536 px; horizon 25 px). Shore f1/f2 (ZEN 4/5): dusky grey sky, no olive (sheets\l6_shore.jpg),
  share 0 %, darker 0.74/0.70, open sky PASS; top right 89,78,72 / 82,71,65 and r/b 1.25 FAIL (the salmon cloud up
  there is kept as "bright"); rims 239,166,119 FAIL. Sun s16fcc still a blob: horizon y 703, the blob runs 0-5 deg
  down (ocean band 3-7 deg) and its bloom lifts the sand edge; it is +-5 deg wide. Loop 7: QF_GLINT_AZ 1/2 (core only
  within 1.5-3.5 deg of the sun's bearing; 2 also 2-3.5 deg down), ZEN 6 (neutral drain, rims only past exposed 1-3).
  Submitted **1101-190108-r016-loop7** (s16g1 sea+shore, s16g2 sea, s16g1cc/s16g2cc sun).

- 19:05 loop 7: SHORE s16g1 (ZEN 6) passes 5 of 6: top right 82,78,77, r/b 1.04, share 0 %, darker 0.74, open sky
  62,61,60; rims 221,171,138 FAIL (the drained white top-right cloud now ranks in the brightest 5 %). The look is a cold
  storm-grey (sheets\l7_shore.jpg); f1 (ZEN 4) is warmer, nearer BSL's beige-mauve, fails top right/r-b/rims. SUN:
  GLINT_AZ 1/2 pass the sand (s16g1cc 28.8, s16g2cc 29.2 jag 0.62; sheets\l7_sand.png) but the sea drops to 4.2 %
  at 250+, r/b 1.24. Loop 8: AZ 3/4 (2.5-4.5 / 3.5-6 deg, with the horizon gate). Submitted
  **1101-190521-r016-loop8** (s16h3, s16h4 sea; s16h3cc, s16h4cc sun).

- 19:09 loop 8: AZ 3 sea 5.0 % / r/b 1.17, sun FAIL 27.0; AZ 4 sea 5.2 % / 1.11, sun FAIL (sheets\l8_sand.png). The
  azimuth width trades the sea's core against sun_clear's sand. Loop 9: QF_GLINT_CAP (the gain lifts the core to at
  most exposed 3/5: white without the huge bloom). Submitted **1101-190838-r016-loop9** (s16i5, s16i3 sea; s16i5cc,
  s16i3cc, s16i5a3cc sun).

- 19:12 loop 9: CAP 5/3 pass the sand (s16i5cc 28.1, s16i3cc 28.4) but the sea falls to 0.5 % at 250+ (the white
  needs an exposed well past 5 through the warm shoulder and TAA). Submitted **1101-191146-r016-loop10** (CAP 12/20:
  s16j12, s16j20 sea; s16j12cc, s16j20cc sun).

- 19:15 loop 10: CAP 12 sea 0.6 % (all else PASS), CAP 20 sea ALL PASS (5.4 %) but sun 26.9 FAIL: white needs an
  exposed ~20 on the current curve. Loop 11: final.glsl SUN_WHITE 3, near-white pixels (min/max > 0.62-0.80) take the
  per-channel shoulder from exposed 2-4, so a capped core (5/8) can clip. Submitted **1101-191439-r016-loop11**
  (s16k5 sea+golden_lit, s16k8 sea, s16k5cc, s16k8cc sun).

- 19:20 loop 11: the near-white shoulder moved the band (mean diff 2.2; top 1 % 255,252,249) but the 250+ share stayed
  0.5 % (cap 5) / 0.5 % (cap 8): the core sits a hair under 250 in blue. Sun k5cc/k8cc 27.6 (FAIL, close). golden_lit under it unchanged vs p15 (sheets\l11_golden.jpg).
  Stopped here (session long; nothing pending in the queue).

## Critic loop 2 (work order C:\qfb\shaderdev
016\critic-loop1.json; critic tools r016\critic1oth.py, prof.py)
- 19:38 code (check_glsl clean): QF_METER_CAP 4 (prepare.glsl meterColumn: each sample adds at most exposed 4 to the
  arithmetic mean; default ON); QF_DUSK_ZEN 7 (+QF_DUSK_WARM/DARK/CLOUD: composite splits the sky pixel by the cloud
  deck's T from colortex1.g: open sky darkened + drained warm, cloud gets ZEN 3's filter); QF_METEOR_WHITE 1 (emerald
  body/train, white 2.2x head in the leading few %, meteors take only 1/5 of the air's tint); QF_STAR_POINT 1 +
  QF_STAR_PT_GAIN 1.6 (phStars as ~0.6 px points, 4 cells as before); QF_GEM_RAMP 1 (lighting.glsl gemWeight:
  piecewise ramp frost 140/10 -> 0, slider 170/205/228/234 -> .2/.4/.6/.8, calm 240/34 -> 1, F0 gate 11.5-13.5;
  both paths blended; composite gemReflection x gw). Gem: texture-dev re-renders the slider.
- Submitted 1101-193011-r016-l2a (meter cap: s16l1 = f1 opts AZ 0 ocean_sunset+golden_lit, s16l1cc sun_clear, s16l0/
  s16l0cc SUN_WHITE 1 controls + beach_noon/torch, s16lm night; s16lx/s16lxm cap 0 controls), 1101-193115-r016-l2b
  (wedge debug views 5/11/14/13 on ocean_sunset), 1101-193821-r016-l2c (shore s16z7a/b/c, night s16n2/s16n2g).
- 19:53 measured with r016	ools\l2m.py (critic's revised targets, both.py's method). l2a: meter cap 4 + f1 opts (s16l1):
  sea lit 44.8 %, horizon 633, luma 98.9 (-1.3 % vs s16l0 100.2), streak var 0.127 (BSL 0.141) + all 7 old sea numbers;
  sun s16l1cc rows 28.9 luma 92.3 disk 3064 PASS (cap fixes the sand). Torch: cap bites (31.3 -> 39.5, repeated in
  l2d s16t0/s16t4) -> cap now gated to open sky (eyeBrightnessSmooth.y 0.35-0.75). Cap 2 (s16p5k2): ocean luma 100.4,
  beach_noon unchanged. Wedge = island's shadow on the water (debug 11: r=0 in the triangle); QF_WATER_PENUMBRA 5/8
  cut the step 35 -> 17/12 (target <6) -> 12/16 in l2f. Night l2c s16n2: meteors white heads/emerald trains (heads in
  frame 243, 228 at the land edge; long one's head is off-frame); stars: blobs = phStars (STAR_GAIN ~0 removes them,
  s16sg0) but the pxA-sized Gaussian came out ~6 px -> QF_STAR_SIGMA (share of a cell) in l2g. Shore: ZEN 7 z7a passes
  5/6 (top right 96,75,61 fails); DUSK_TOP z8a went blue -> red-mauve top (1.30,1,1.10) x0.80 in l2g.
  Pending: 1101-194923-r016-l2f (penumbra 12/16, cap 2 + gate, torch/sky_noon/plains_noon regression), 1101-195329-r016-l2g.
- 20:01 l2f: torch is bimodal run to run (31.3 or 40.2-40.9 whatever the cap: s16qx cap0 40.9, s16q4 cap4 40.2, s16q0
  cap2 31.3), so the cap does not bite there. plains_noon: cap 2 112.1 vs cap 0 115.5 (-2.9 %) -> cap 2 bites outdoors;
  testing 3/4. Sea s16q2 (f1 opts + PENUMBRA 12 + cap 2): ALL PASS (lit 41.4 %, horizon 682, luma -0.5 %, streak var
  0.139 vs BSL 0.141, old 7 pass); the straight diagonal is gone at 5x (sheets r016\l2\wedge3.png; row steps are now
  ripples 5-33). Sun s16q2cc rows 31.2 luma 95.4 disk 3068 PASS. l2g stars: sigma as cell share gives pinpoints
  (0 blobs >3 px) but far too faint (brightest 108-114 luma) -> sigma 0.15, gain 8 default. Shore z9a: open sky 70,56,58
  PASS, top right 89,70,66 + b>g 43 % FAIL -> top tint (1.30,1,1.0), clouds drained 0.8*hz. Submitted 1101-200055-r016-l2h.
- 20:15 l2h/l2i: cap 0/3/4 identical on plains_noon (115.3-115.4; l2f's cap-2 dip was the cap or noise) -> QF_METER_CAP 3
  default. SEA s16r3 (SUN_WHITE 3, GLINT_GAIN 16, GLINT_LO 0.2, SEA_NEAR 4, WATER_PENUMBRA 12, cap 3): ALL PASS (lit 41.1 %,
  horizon 649, luma 99.6 = -0.9 % vs s16c3x, streak var 0.140 vs BSL 0.141, old 7 pass); SUN s16r3cc rows 29.6, luma 93.4,
  disk 3065 PASS (the white below-horizon glint is wide, 6152 px vs BSL 4075: a flat white bar, critic to judge).
  golden_lit unchanged (108.8 all). NIGHT s16t1 (defaults: METEOR_WHITE 1, STAR_POINT 1 sigma 0.15 gain 8): sky 17,23,37,
  stars 185,217,238, half 138,162,181, bright-star FWHM 2.1 px (1 of 31 at 4 px, adjacent pair), heads in frame 243 /
  229 (land edge); cost p16m2 3.42 - off 0.45 = 2.97 ms <= 2.98. SHORE s16z11b (ZEN 7, WARM 0.30, DARK 0.50, TOPB 1.03;
  now the dev defaults, ZEN default still 0): 5/6, top right 86,68,62 FAIL (luma 85, r<=b+12: the pale top-right cloud).
  Sheet r016\sheets\l2_final.jpg (tools\sheet.py, sun crop box fixed).

## Critic loop 2: best frame per item (measured with r016	ools\l2m.py = critic's revised targets)
| Item | Frame (render) | Opts | Result |
|---|---|---|---|
| Sea | s16r3 ocean_sunset (1101-200055-r016-l2h) | QF_SUN_WHITE 3, QF_GLINT_GAIN 16, QF_GLINT_LO 0.2, QF_SEA_NEAR 4, QF_WATER_PENUMBRA 12 (cap 3 default) | PASS all (lit 41.1 %, horizon 649, luma -0.9 %, streak 0.140/0.141, old 7); wedge's straight edge gone at 5x (row steps now ripple-sized, 5-36: the critic's "<6" not met literally) |
| Sun | s16r3cc sun_clear (same) | as sea + QF_CLOUD_COVER 0.6 | PASS (rows 29.6, luma 93.4, disk 3065) |
| Shore | s16z11b shore_sunset (1101-200709-r016-l2i) | QF_DUSK_ZEN 7 | 5/6: open 67,54,53, b>g 8 %, darker 0.69, rims 242,149,69 (3.52), clouds sat 0.53 / 0 % grey PASS; top right 86,68,62 FAIL |
| Night | s16t1 night_wide (1101-200055-r016-l2h) | defaults + QF_NIGHT_SKY 4, QF_METEOR_RAZ 210 | PASS: green trains, white heads (in-frame heads 243/229), pinpoint stars, 2.97 ms |
| Gems | not rendered (texture-dev re-renders the slider) | QF_GEM_RAMP 1 default | frost 140/10 and calm 240/34 unchanged by construction |
Defaults now: QF_METER_CAP 3, QF_METEOR_WHITE 1, QF_STAR_POINT 1, QF_GEM_RAMP 1. Sea/shore stay opt-in (SUN_WHITE 1,
ZEN 0) until the critic picks. Nothing pending in the queue.

## Current best per item (loop 1, superseded) (render IDs, frames)
Frames: C:\qfb\shaderdev\rounds\screenshots\bench-TAG-SCENE.png. Sheets: C:\qfb\shaderdev\r016\sheets\.
- Sea (all 7 pass): s16f1 ocean_sunset (1101-185509-r016-loop6; opts QF_SUN_WHITE 3, GLINT_GAIN 16, GLINT_LO 0.2,
  SEA_NEAR 4), also s16j20 (1101-191146-r016-loop10, + GLINT_CAP 20). BUT these settings blow sun_clear's glint into a
  white blob and lose the owner's D sand edge (s16fcc 27.0, s16j20cc 26.9). Compromise that passes the sun:
  s16g2 (1101-190108-r016-loop7, + GLINT_AZ 2): sea 4/7 (250+ 4.2 %, top tenth r/b 1.24), sun s16g2cc 29.2 PASS.
- Shore: s16g1 (1101-190108-r016-loop7, QF_DUSK_ZEN 6): 5/6 pass, rims fail; look is a cold storm-grey. s16f1
  (loop 6, ZEN 4): warmer dusk, nearer BSL's beige-mauve, 3/6. Let the critic choose the look (sheets\l7_shore.jpg).
- Meteor night (all pass): s16cm1 night_wide (1101-183455-r016-loop3); its values are now the defaults
  (METEOR_NAVY 0.30, STAR_GAIN 0.070, STAR_TMAX 15000). Cost p16m (1101-184251-r016-night-cost) 3.37 - off 0.45 =
  2.92 ms <= 2.98.
- Sun glow (pass): default (SUN_WHITE 1) s16acc sun_clear (1101-155233-r016-loop1) rows 28.9, jag 0.38
  (sheets\l1_sand.png, vs D p14cch1 and C p14cc); s16g2cc under SUN_WHITE 3 + AZ 2 also 29.2.
Defaults unchanged for sea and shore (SUN_WHITE 1, SEA_NEAR 0, DUSK_ZEN 0) until the critic picks.

## Targets (critic r015 work order) vs measured, measure.py (meteors masked in the star numbers since 16:40)
| Item | Target | r015 | Best now | Pass |
|---|---|---|---|---|
| Sea | band brightest tenth ~254,250,235, r/b <= 1.1 | 251,204,128 (1.96) | s16f1 254,246,235 (1.08) | PASS |
| Sea | >= 5 % of far band at 250+ all channels | 0.0 % | s16f1 5.4 % | PASS |
| Sea | sea beside the path (darker half) ~2.35 (<= 2.45) | 2.70 | s16f1 2.40 | PASS |
| Sea | far band r/b 2.0-2.1 | 2.76 | s16f1 2.03 | PASS |
| Sea | sun core clips white | 0 px | s16f1 536 px, 255,254,253 | PASS (BSL disk 2885 px) |
| Sea | horizon strip reverted (r014 24 px) | 54 px | s16f1 25 px | PASS |
| Shore | top right ~75,65,72 (luma <= 85, r <= b+8) | 129,108,112 | s16g1 82,78,77 | PASS |
| Shore | open sky (darkest 30 %) warm-dark, b <= g | 117,96,111 | s16g1 62,61,60 | PASS |
| Shore | upper sky blue>green <= 15 % | 50.4 % | s16g1 0.0 % | PASS |
| Shore | ~40 % darker (luma ratio 0.5-0.75) | 1.00 | s16g1 0.74 | PASS |
| Shore | red <= blue above ~30 deg (BSL itself 1.71) | 1.48 | s16g1 1.04 | PASS |
| Shore | keep rims 250,157,83 | 250,157,83 | s16g1 221,171,138 | FAIL |
| Night | sky median ~18,22,38 | 4,7,15 | s16cm1 17,23,37 | PASS |
| Night | brightest stars ~170,180,210 (meteors masked) | 115,115,102 | s16cm1 161,189,207 (half size 153,181,200) | PASS |
| Night | cost <= 2.98 ms | 2.98 | p16m 2.92 | PASS |
| Sun | sand block top row >= 28, jagged (D 28.9) | C 27.0, D 28.9 | default s16acc 28.9 | PASS; FAIL with s16f1's sea settings |

## Next
- Sea vs sun conflict: white needs an exposed ~20 on the current curve, and a core that bright blooms over sun_clear's
  sand. Loop 11 got the core to 255,252,249: try the near-white shoulder from exposed 1.5-3 (final.glsl SUN_WHITE 3,
  wk smoothstep 2,4 -> 1.5,3) or curve 1.15 -> 1.4, with GLINT_CAP 5-8, on ocean_sunset + sun_clear + golden_lit.
  Or GLINT_AZ 2 with a stronger gain inside it. Also an artifact in every sea frame: a lighter wedge at the island's
  left base (x 1175-1190, y 740-760), present since r015 (shadow/haze edge).
- Shore: rims with ZEN 6: protect from exposed 0.6-2 again (as 4) but drain the top-right salmon cloud anyway (it is
  what fails "top right"); the critic should say whether the storm-grey (g1) or warm dusk (f1) is wanted.
- Then a fresh critic on: sea s16f1 + s16g2, shore s16g1 + s16f1, night s16cm1, sun s16acc + s16g2cc (vs D p14cch1).
  Sheet: `py -3.10 -I C:\qfb\shaderdev\r016\tools\sheet.py OUT SEA SHORE NIGHT SUN`.
