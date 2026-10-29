# r013 shader (shader-dev, 2026-10-29)

Work order: ops/checkpoints/r013-plan.md "Shader" 1-5 (critic r012 notes = the brief). Hand-off to C:\qfb\shaderdev\r013\
(spec_scenes.py, renders, SHADERS-READY; critic notes left to the critic agent).
Refs extracted for reading (scratchpad, read only): BSL v10.1.8, Complementary r5.9.3; Photon src C:\qfb\refpacks\photon-shader\src.

## Progress log
- started; queue idle. Gem SSR patch already merged behind QF_GEM_SSR 0 (r012 4f9e553): item 5 = default on + wobble.
- 12:03 frozen r12 pack copy C:\qfb\shaderdev\r013\pack-r12\QuestForge (git archive HEAD 8bddace) for same-run
  baselines (spec "pack"). views-world-master.txt += sunclr_a..f (sun-clear candidates). Tools: r013\tools\grid.py.
  Submitted **1029-120321-r013-loop0-shot** (specs\r13-loop0.json): r12s (r12 pack) ocean/shore_sunset + sunclr_a-f;
  r12d14 / r12d13 water debug (reflected x F / transmitted) on ocean/shore_sunset.
- Study (read, not guessed): BSL water = albedo waterColor lit by the light colour + Schlick^5 Fresnel x GetSkyColor
  (gold) reflection; BSL sun = pow(smoothstep(1-0.007,1,VoL),3) soft blob (~3.7 deg half) + miniGlare pow(VoL,192)*0.05
  + bloom; Photon sun = real-luminance disk + 6-level gaussian bloom mixed 0.12 (no analytic glow).
  Plans: rays (composite crepuscularGain) 16 taps x 2 fetches -> 8 jittered taps, 1 fetch (sky sentinel material in
  colortex1.b from deferred); meteors: clip radiant is 90 deg off view (RAZ 135 vs view az 225) -> parallel; length /
  brightness correlated and wider spread; cloud cut smoothstep(0.93,0.995,T) -> gentle ramp (dashes). Gems: facet
  normal from block-local position (table + 8 crown facets) for gem reflection + deferred highlight; option flat.
- 12:15 loop 0 read (sheets r013\sheets\l0_water.jpg, l0_sunclr.jpg): near sea transmitted 3,38,70 (navy) vs
  reflected x F 19,19,20: the water body's blue in-scatter (overhead-sky irradiance x ocean scatter albedo) leads.
  shore_sunset: sky itself salmon (Photon tint pulse gives a 2-deg sun ~half the gold). Sun candidates a-d identical
  clouds every day, sun behind cloud; e/f (lake) sun behind the hill -> new candidates (lower/higher sun, other points).
- 12:19 code (uncommitted -> committed below), all behind options, check_glsl 0 errors on 5 combos:
  QF_SEA_GOLD 1 (+QF_SEA_BODY 0.7) composite shadeWaterAbove; QF_SUN_GOLD_LOW 1 photon.glsl phSunTintX;
  QF_SUN_SOFT 1 sun.glsl BSL-shaped soft sun + final.glsl corona dropped; QF_CREP_TAPS 8 + sky sentinel colortex1.b=1
  (deferred) one fetch per tap; QF_METEOR_SPREAD 1 (length tied to brightness, cloud ramp smoothstep(0.45,1,T));
  QF_GEM_SSR 1 default, QF_GEM_FACET 2 (lighting.glsl gemFacetNormal, used in deferred glint + composite reflection).
  pack-r12 settings: RAZ list += 210 225 (no look change).
  Submitted **1029-121912-r013-loop1a-shot** (r13a sunsets + sunclr_a-f, r13gl0, r13s2, r13b45, r13b10, r12s sunclr)
  and **1029-121917-r013-loop1b-shot** (r13gf2/gf1/gf0 gems, r13t16, r13r regressions, r13clipm / r12clipm RAZ 210).
- Committed **b4d0135** (loop 1 code). 12:30 coordinator: the textures track's connected (CTM) gem/metal packs carry
  rim bevel + facets in their _n (ops/checkpoints/r013-textures.md; packs C:\qfb\textures\r013\QF-gems-ctm-facet.zip /
  -flat.zip); a per-block cut (FACET 2) brings the block grid back. -> **QF_GEM_FACET default 0** (map normals; 1/2
  kept for packs without CTM; a CTM-following cut is not possible in the shader, it cannot see the tile layout).
  check_glsl 0 errors. Submitted **1029-123012-r013-loop1c-shot** (r13gc = ctm-facet, r13gcf = ctm-flat, FACET 0
  default pack, gem_glint_d/e, gem_lit, diag_column on world-gems). Note for texture-dev: nothing needed from the
  normal maps; the wobble was the r012 dome _n, which the CTM maps replace.
- 12:31 queue waiting for the owner to be idle (ETA ~22+ min): exiting per CLAUDE.md. Waits: 1029-121912-r013-loop1a-shot,
  1029-121917-r013-loop1b-shot, 1029-123012-r013-loop1c-shot.

- 13:00 loop 1 reviewed (sheets r013\sheets\l1_*.jpg; scratchpad metrics m.py/prof.py/stack.py, simple numpy):
  SEA pass: near sea (800,1000,1760,300) r12 34,47,70 r/b 0.48 -> r13a 48,44,44 r/b 1.09 (BSL 41,33,27 r/b 1.52);
  mid sea r/b 1.08 -> 1.47 (BSL 2.28). SEA_GOLD 2 = 1 (keep 1); BODY 0.45 greyer (r/b 1.00), 1.0 warmer (1.18) but
  brighter than BSL: keep 0.7. SHORE fail: still salmon, clouds (1700,0,860,350) 148,111,105 -> 153,113,106, horizon
  r/b 1.57 -> 1.61; GOLD_LOW 1 barely moves it (r13gl0 = r12). SUN: no candidate fully clear; f (300 W) best (sun in a
  gap, one strand below). Soft sun works: saturated px 478 -> 236 (f), 418 -> 249 (d), limb step r20-30 251->225 vs
  248->232. RAYS pass: 8 vs 16 taps mean|d| 1.75 / 0.62 / 0.97 (ocean/golden/lake), no grain at 1:1.
  METEORS pass: max-stack l1_meteor_stack.jpg both radiate from RAZ 210; r13 varied length/brightness, tapered, no
  dashes across the cloud band (l1_meteor_cloud.jpg). GEMS pass: CTM facet pack + FACET 0 (r13gc) sharp mirror SSR, no
  wobble; flat CTM (r13gcf) reads as water: facet pack is the one to show.
- 13:02 code: QF_SUN_GOLD_LOW 2/3 (photon.glsl phSunTintX: under 7 deg, gold shift on light/glow/sky; 3 stronger),
  default still 1 pending loop 2. check_glsl 0 errors (1/2/3). views += sunclr_g..n. Committed (see git log).
  Drafted specs\p13-cost.json (publish cost, uses scene "sun_clear" = the picked candidate).
  Submitted **1029-130228-r013-loop2** (specs13-loop2.json, ETA ~13:25): r13lo2/r13lo3 shore/ocean/sunclr_f/golden,
  r13a sunclr_g..n, cost c13/c12 (r12 pack) 6 views, c13t16, c13cr0, c13m/c13m0/c12m (night_wide storm RAZ 210),
  c13g/c13g0 (CTM gems SSR on/off), c13off.

## Resume here (fresh agent)
1. `renderq.py results 1029-130228-r013-loop2`. Shore: grid r12s,r13a,r13lo2,r13lo3 shore_sunset (+ ocean_sunset,
   golden_lit regressions: must not change at 9 deg); measure clouds 1700,0,860,350 and horizon 1200,350,800,150
   (target G/R ~0.75+, B well under G). Set QF_SUN_GOLD_LOW default to the pick in settings.glsl.
   Sun: grid r13a sunclr_f..n with 1:1 crops round the sun (prof.py-style: find the hot spot, saturated px). Rename the
   best to sun_clear in views-world-master.txt (drop the other sunclr_* lines).
   Cost: High ms = cost(tag) - cost(c13off). Rays: c13 vs c13t16 vs c13cr0 on ocean_sunset (r012 3.65 vs budget 3.0);
   meteors c13m vs c12m (<= r012 2.94-2.99); gems c13g - c13g0. If ocean_sunset still > 3.0 say so with the number.
2. Submit specs\p13-cost.json (publish cost) and checkpoint; when done write r013\spec_scenes.py (copy r012's: sea
   p13 vs p12r vs ref BSL; shore p13 vs p12r; sun_clear p13 vs p12r (vs p13so0); rays p13 golden/ocean vs p13t16 with
   cost; meteors ov p13clipm / p12clipm; gems g13c vs g12c (r012 C) with SSR cost), round.json (n 13, renders, budgets
   p13 3.0 / p13lo 0.9 / p13po 0.4), touch SHADERS-READY; track, journal, commit, push.

## Loop 2 read (16:10, agent 3)
- Noise: c13/c13t16/c13cr0/c13m/c13m0 lost 6 steps to the owner gaming (Deadlock) at 13:16:30; the runner kept the 23
  steps measured before it (last one c13 lake_glitter 13:14:57, before the last idle sample) and re-ran the 6 at 15:52
  (owner gate idle 5 min). Cross-boot check: lake 3.70 (boot 1) vs 3.67 t16 (retry) vs 3.75 c12 (boot 3). Clean.
  c13 golden_lit had 136 chunk updates / 14 frames > 33 ms (chunk loading, not the owner); p50 is unaffected.
- Shore (sheets l2_shore.jpg, l2_shore_crop.jpg): clouds B/G 0.94 (r13a) -> 0.85 (lo2) -> 0.77 (lo3), horizon G/R
  0.70 -> 0.74, B/G 0.88 -> 0.71; ocean_sunset/golden_lit identical. **QF_SUN_GOLD_LOW default 3** (settings.glsl).
- Sun (l2_sunclr.jpg, l2_sun_crop*.jpg, l2_sun_disc.jpg): g, n spawn inside terrain; i behind leaves; k behind a hill.
  No view fully clears the far strand at the sun's altitude. **sun_clear = sunclr_l** (f at 12250): roundest core,
  smooth fade (ring 252 223 208 201 196). Other sunclr_* lines dropped from views-world-master.txt.
- Cost, High = p50 - shaders-off p50 (c13off cached): ocean_sunset r13 3.55 / r12 3.66 / r13 16 taps 3.58 / rays off
  3.43 -> rays now +0.12 ms (r12 +0.30 by r012's count; 16 taps one fetch +0.15). **ocean_sunset still 0.55 over 3.0,
  and 0.43 over with the rays off: the rest is the water, not the rays.** golden 2.95 / 2.86, lake 3.19 / 3.24 (rays
  +0.15), shore 2.92 / 2.92, night_wide 2.95 / 3.00, sky_noon 2.35 / 2.38. Meteors storm RAZ 210: c13m 2.96, spread
  off 2.97, r12 3.02 (r012 band 2.94-2.99): no rise. Gem SSR on the CTM facet pack: +0.16 / +0.14 ms (d / e).
- check_glsl 0 errors. Next: commit, submit specs\p13-cost.json.
