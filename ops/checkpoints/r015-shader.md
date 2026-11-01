# r015 shader (shader-dev, 2026-11-01)

Work order: ops/checkpoints/r015-plan.md "Shader" 1-5 (critic r014 notes C:\qfb\shaderdev\r014\critic.json p14/ocean_sunset,
p14/shore_sunset, p14cc + p14cch1/sun_clear, p14clipm/night_wide). Hand-off C:\qfb\shaderdev\r015\ (spec_scenes.py,
round.json, renders, SHADERS-READY). Night mode 22:15-08:00 = shots only.

## Progress log
- 09:59 started; queue idle. Dir C:\qfb\shaderdev\r015\{specs,sheets,tools,crops}, tools copied from r014.
- 10:04 HORIZON DIFF (item 3), tools r015\tools\hdiff.py, hzone.py; sheets r015\sheets\h_full.jpg (A|B|diff x6),
  h_crop.jpg, h_zoom.jpg (3x, pier + cliff by the sun). p14cch1 vs p14cc (same cost run 1031-204537): mean |d| 1.9;
  sky and land 1-2 levels darker in B everywhere (haze energy moved into the HG 0.9 lobe), the pier right under the sun
  +3.5 luma and yellower (235,180,88 vs 232,177,83). Land local contrast/edge step equal within run-to-run noise
  (control r14vcc = A setting other run). Silhouette: B's block edges sit a median 0.20 px off A's (162/505 columns
  >0.5 px), control A vs A' 0.07 (55), loop-6 pair hb1 vs vcc 0.09 (61): a sub-pixel camera difference between the two
  boots, not the setting. => No shape/"distortion" difference caused by the option; the wavy far blocks (haze veil +
  mirrored pier in the waves) are in both. B becomes default anyway (owner's pick); say so plainly, show crop A|B.
- 10:09 refs read: Photon stars.glsl (stable star field, blackbody 4500-8500 K, threshold drops in the galaxy),
  Complementary stars (read only), r010 photos (photo 1 bg luma 58, dense stars; ours bg ~8). Code (all new options
  default 0 for now; QF_SUN_HALO now 1): QF_SEA_FAR 1/2 (composite: gold hue pull eases over the last 6 deg below the
  horizon, 2 adds a 10 % darker far strip), QF_DUSK_SKY 1/2 (photon.glsl: Rayleigh sky keeps blue under 7 deg, dims;
  sky.glsl cloudLum: gold shift x exp(-0.6 od) = sunlit only, shadowed light cools/dims, c.under cool), QF_METEOR_SKY
  1/2 (sky.glsl: cloud threshold +0.08/+0.16 on shower nights, navy lift, Photon star field port phStars).
  Measured p14 ocean_sunset left horizon: sky y710 202,161,96 r/b 2.10 vs sea y760 188,142,61 r/b 3.08 (same luma);
  BSL sea 2.8. shore: gold share (b/g<0.55, right 2/3, y<600) p14 43.5 %, p13r 23.6 %, BSL 0.5 %; open-sky darkest 30 %
  123,101,89 (BSL 83,65,61; Photon 85,95,139 blue). Pale column (p14cc): blue bump ~+10 at 150-250 px right of the
  sun over the beach (sheets\col_hp.jpg, high-pass) -> testing shafts/crepuscular off.
  Submitted **1101-100900-r015-loop1** (specs\r15-loop1.json: r15b, r15x1, r15x2, r15cc, r15ccs0, r15ccr0).
- 10:15 GEMS REQUEST (coordinator, gems look D): added **QF_GEM_NFADE [0 1 2]**, default 0 (program/gbuffers.glsl PBR
  block): on polished gem pixels (_s R > 0.88 and G > 0.1, the gem path's own test) the normal map's tilt fades with
  distance before the TBN: 1 to 15 % by 28 blocks (fade starts at 6), 2 flat by 14 (from 3). Every gem consumer
  (diffuse, gemInnerLight, composite gemReflection) reads that normal. Cost: one length + branch per terrain pixel
  (unmeasurable). check_glsl clean for 0/1/2. Gems agent: render look D with opts {"QF_GEM_NFADE": 1} (or 2).
- 10:25 loop 1 read (sheets r015\sheets\l1_shore.jpg, l1_night.jpg, col_hp2.jpg):
  SEA: SEA_FAR (hue pull only) moved rows 735-760 (r/b 2.89 -> 2.61/2.52) but not the far band 760-840 (2.79 ->
  2.78; BSL 2.40): p14sg0 (graze off) has 1.8-2.0 there, so the far orange is the ELEVATION pull -> SEA_FAR now eases
  the elevation pull too (1: 55 %, 2: 70 % at the horizon).
  SHORE: DUSK 1/2 (gold only where exp(-0.6 od)) brought r013's CORAL back on every lit side and a MAUVE sky (gold
  share 43 % -> 6 %; zenith 134,103,104): od toward the sun is 7-25 a few blocks in. -> gold kept on all sunlight
  (r014), shadowed part (1-exp(-0.08 od)) x 0.70/0.85 drains to luma x (0.80,0.84,1.0) x 0.62; Rayleigh tint smaller
  change (1: blue cut 0.90 not 0.80; 2: none, dimmer); c.under back to r014.
  SUN COLUMN: blue bump is symmetric (ring at ~200 px, B 128-130 both sides). Shafts off (r15ccs0) removes the peach
  dome AND the pale wedge; crepuscular off barely changes it -> the wedge is the QF_SHAFTS lit air: sky rays right of
  the sun cross the cliff's shadow in the air, lose the amber in-scatter. New QF_SKY_SHAFT 1: over open sky at golden
  hour 60 % of the shadowed air counts lit.
  METEOR SKY: x1 (+0.08 clear): cloud-dark share 26 % -> 12 %, star px 23k -> 64k (x2 144k); stars were 3-4 px
  yellow-green blobs -> finer (coord x1000), 5200-11000 K, navy 0.016, clear +0.10.
  Submitted **1101-102616-r015-loop2** (specs\r15-loop2.json: r15c2, r15c3, r15c2cc, r15b2). Gems queue ahead.
- 10:35 loop 2 read (sheets l2_shore.jpg, l2_night.jpg, col_hp3.jpg): SEA: far band across the width (760-840):
  open sea left ours 3.04/luma 135 vs BSL 2.83/149 (same), under the sun ours 2.60-2.91 vs BSL 1.88-2.09 (white-hot,
  brighter): the critic's orange far band = the sun's path, recoloured by the hue pull -> SEA_FAR now exempts the
  mirrored glow within ~10-13 deg of the sun (0.8 / 1.0). SHORE: c2 (DUSK 1) gold share 38.5 %, c3 (DUSK 2) 17.7 %
  with amber rims kept (top 5 % 250,157,82), cloud tops greyer; zenith still mauve 133,105,104 -> DUSK 2 Rayleigh tint
  now (0.78,0.90,1.04). COLUMN: QF_SKY_SHAFT changed nothing (B@y530 within 1 level) -> removed. The pale band is
  symmetric (sky ring where the gold dome meets the blue; cliff frames it on the right); only shafts-off removes it,
  with the whole glow. Say so in the scene. NIGHT: c3 (METEOR_SKY 2) best: cloud-dark 11 %, star px 140k, fine stars
  -> navy 0.026. forest_golden c2 vs b2 mean 77->74 (check in cost frames).
  Submitted **1101-103449-r015-loop3** specs\r15-loop3.json: r15d1, r15d2.
- 10:45 loop 3 read (sheets l3.jpg, l3n.jpg): shore DUSK 2 (red cut sky): gold share 12.5 % (DUSK 1 38.5 %), rims
  amber (top 5 % 250,157,83), open sky lilac-blue 117,95,110; night METEOR_SKY 2: star px 130k, sky mean 10,11,16;
  forest_golden unchanged (77.3 vs 77.4). SEA: sun path still 2.74 -> the ELEVATION pull also recoloured the path ->
  sunK (within ~10-13 deg of the plain mirror direction) now lifts both pulls (not yet seen in a frame: check in cost).
  DEFAULTS committed fefac03: QF_SUN_HALO 1, QF_SEA_FAR 1, QF_DUSK_SKY 2, QF_METEOR_SKY 2 (QF_GEM_NFADE 0).
  Frozen r14 pack: C:\qfb\shaderdev\r015\pack-r14\QuestForge (git archive a9565b3).
  Submitted **1101-104149-r015-publish-cost** (FULL ID; specs\p15-cost.json, 16 jobs, 91 scenes; ETA ~11:40).
  Drafted C:\qfb\shaderdev\r015\spec_scenes.py (4 scenes: sea p15/p14r, shore p15/p14r, sun-glow p15cc/p14rcc crops
  + horizon 3x crops of r14's p14cc/p14cch1 in r015\crops, meteors clips p15clipm/p14rclipm), round.json, and
  tools\look.py (writes r015\look.json: SEANUMS/SHORENUMS/METNUMS put into the questions).

## Resume here (fresh agent)
1. `py -3.10 -I tools/renderq/renderq.py results 1101-104149-r015-publish-cost`; check
   C:\qfb\shaderdev\rounds\bench\p15*.userbusy.json noisy false (re-submit a noisy job alone, cost mode, outside 22:15-08:00).
2. SEA CHECK: `py -3.10 -I C:\qfb\shaderdev\r015\tools\look.py` (p15 vs p14r). Sun path (760-840, x960-1440) should
   drop from ~2.75 toward BSL 1.96; if it did not, or the path looks wrong (sheet with tools\grid.py p15,p14r,p15sf0
   ocean_sunset), fix and re-shoot as a shot, or drop SEA_FAR to 0 and rewrite the sea scene to say so.
3. Sheets (only changed frames): ocean_sunset, shore_sunset, sun_clear crop 912,436,600,360 (p15cc,p14rcc),
   night_wide (p15m,p14rm) + forest_golden (p15 vs p15ds0 vs p14r: DUSK side effect). Check no magenta.
4. Costs: High worst p15 (water views ~3.5 known), p15lo <= 0.9, p15po <= 0.4; meteors p15m vs p15ms0 vs p14rm must be
   no higher than r014 (2.98); if higher, say so plainly in the meteors text (or lower clear level to 1 and re-cost).
5. Dry run `py -3.10 -I tools/shaders/review/finish_round.py` --allow-missing-critic (see r014 checkpoint), fix any
   text a number contradicts, touch C:\qfb\shaderdev\r015\SHADERS-READY, update ops/tracks/shaders.md, one journal
   entry, commit own hunks, `git log origin/main..main` before any push.

## 2026-11-01 13:00 hand-off agent
- Costs (roundlib, vs p15off/p15looff/p15pooff): High worst 3.65 sun_clear (cloud cover default; p15cc 3.38, p14rcc 3.36);
  over 3.0: 11/24 (ocean_sunset 3.61, sun_clear 3.65, river_swamp 3.28, lake 3.23, beach 3.20, swamp 3.18, biome_ocean
  3.17, ocean_swamp 3.17, shore_noon 3.11, night_new 3.11, night_wide 3.02). p14r same run ocean_sunset 3.55.
  Meteors p15m 2.98 / p15ms0 3.02 / p14rm 3.05 (r012 2.94). Potato worst 0.31. Low p15lo DISTURBED (underwater/night_wide
  half frames, p99 7.8/9.5): p14rlo2 (1101-125524, r14 pack) clean 1.08/1.25 p50; p15lo2 was a cache hit of the bad
  run -> fresh p15lo3 submitted **1101-125848-r015-lo-recheck2**. Use p15lo3 for those scenes in spec_scenes.py.
- SEA: sun path r/b 2.76 = 2.76 (sf0 same; BSL 1.96): SEA_FAR does NOT whiten the path. It does make the strip just
  under the horizon on the open sea bluer (735-760 left: 2.96 -> 2.55, far band 3.05 -> 2.96). Keep default 1 (cost
  3.61 vs 3.62 sf0), rewrite the sea scene: path unchanged, it is the sun glint's own colour -> r016 idea.
  Sheets r015\sheets\c_sea.jpg, c_sea2.jpg (left horizon crop 0,640,900,300), c_shore, c_misc, c_fg, c_over. No magenta.
- 13:07 p15lo3 clean: Low lake 0.94, ocean 0.95, underwater 0.66, night 0.81 (r14 pack p14rlo2 0.95/0.93/0.65/0.83).
  spec_scenes.py final (sea scene rewritten "not fixed yet" + C/D left-horizon 2x crops; shore says lilac sky, BSL darker;
  meteors cost text plain), look.py SEANUMS with sf0, round.json renders + p15lo3. Dry run OK (only flag: sea 3.61 >
  3.0, stated). SHADERS-READY touched. Next: track, journal, commit, push. Draft kept specs\spec_scenes.draft.py.
