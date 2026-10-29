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

## Resume here (fresh agent)
1. `renderq.py results` on the three IDs above. Sheets with `py -3.10 -I C:\qfb\shaderdev\r013\tools\grid.py OUT 640 tags scene[:crop]`
   (tag@scene picks a scene per column; ref* tags read C:\qfb\shaderdev\refs\screenshots).
   - Sea: r12s vs r13a vs r13s2 vs r13b45/r13b10 on ocean_sunset; shore: r12s, r13gl0 (gold-low off), r13a. Measure near-sea
     crop (800,1000,1760,1300) against r12 28,43,68; target warm dark (photos/BSL). Pick SEA_GOLD 1|2 and SEA_BODY.
   - Sun: pick the clearest sunclr_* (r12s vs r13a); rename it sun_clear in views-world-master.txt (drop the others), and
     shoot BSL/Photon refs there (spec "reference": C:\qfb\refpacks\bsl-shaders\dl\BSL_v10.1.8.zip, tag refbsl) if wanted.
     If no candidate is clear, try more points/times (clouds are the same every day; move the camera).
   - Rays: r13a vs r13t16 (and r12s/p12) look the same? Gems: r13gf0/1/2 (r012 non-CTM pack) and r13gc/r13gcf (CTM).
     Meteors: make_clip r13clipm / r12clipm (--speedup 4), check radiating, length spread, no dashes.
2. Cost run (mode cost, day only): r13 defaults vs pack-r12 ("pack": C:/qfb/shaderdev/r013/pack-r12/QuestForge) on
   ocean_sunset, golden_lit, lake_glitter, shore_sunset, sun_clear, night_wide + shaders-off baselines; per item:
   QF_CREP_TAPS 16 vs 8 vs QF_CREPUSCULAR 0 (rays before/after on ocean_sunset vs High 3.0), SEA_GOLD 0, SUN_SOFT 0,
   METEOR_SPREAD 0 (night_wide), GEM_SSR 0 on world-gems with the CTM pack; Low/Potato spot checks as p12-cost.json.
3. Hand-off as r012: C:\qfb\shaderdev\r013\spec_scenes.py (copy r012's), round.json, SHADERS-READY; track, journal, commit.
