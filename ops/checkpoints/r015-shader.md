# r015 shader (shader-dev, 2026-11-01)

Work order: ops/checkpoints/r015-plan.md "Shader" 1-5 (critic r014 notes C:\qfb\shaderdev\r014\critic.json p14/ocean_sunset,
p14/shore_sunset, p14cc + p14cch1/sun_clear, p14clipm/night_wide). Hand-off C:\qfb\shaderdev\r015\ (spec_scenes.py,
round.json, renders, SHADERS-READY). Night mode 22:15-08:00 = shots only.

## Progress log
- 09:59 started; queue idle. Dir C:\qfb\shaderdev\r015\{specs,sheets,tools,crops}, tools copied from r014.
- 10:15 HORIZON DIFF (item 3), tools r015\tools\hdiff.py, hzone.py; sheets r015\sheets\h_full.jpg (A|B|diff x6),
  h_crop.jpg, h_zoom.jpg (3x, pier + cliff by the sun). p14cch1 vs p14cc (same cost run 1031-204537): mean |d| 1.9;
  sky and land 1-2 levels darker in B everywhere (haze energy moved into the HG 0.9 lobe), the pier right under the sun
  +3.5 luma and yellower (235,180,88 vs 232,177,83). Land local contrast/edge step equal within run-to-run noise
  (control r14vcc = A setting other run). Silhouette: B's block edges sit a median 0.20 px off A's (162/505 columns
  >0.5 px), control A vs A' 0.07 (55), loop-6 pair hb1 vs vcc 0.09 (61): a sub-pixel camera difference between the two
  boots, not the setting. => No shape/"distortion" difference caused by the option; the wavy far blocks (haze veil +
  mirrored pier in the waves) are in both. B becomes default anyway (owner's pick); say so plainly, show crop A|B.
- 10:40 refs read: Photon stars.glsl (stable star field, blackbody 4500-8500 K, threshold drops in the galaxy),
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
- 10:55 GEMS REQUEST (coordinator, gems look D): added **QF_GEM_NFADE [0 1 2]**, default 0 (program/gbuffers.glsl PBR
  block): on polished gem pixels (_s R > 0.88 and G > 0.1, the gem path's own test) the normal map's tilt fades with
  distance before the TBN: 1 to 15 % by 28 blocks (fade starts at 6), 2 flat by 14 (from 3). Every gem consumer
  (diffuse, gemInnerLight, composite gemReflection) reads that normal. Cost: one length + branch per terrain pixel
  (unmeasurable). check_glsl clean for 0/1/2. Gems agent: render look D with opts {"QF_GEM_NFADE": 1} (or 2).
