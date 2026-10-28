# r012 shader (shader-dev, 2026-10-28)

Work order: ops/checkpoints/r012-plan.md "Shader". Owner r011: sunset A 4 "listen to the critic" (gold not
pink-lilac, sun glow: copy Photon/BSL sun disk + glow); rays C 4 (round 10's rays on Photon's sky; cut the near-field
evening haze on golden_lit, 66,64,39 vs r010 40,45,15); meteors storm B 4 "leaner like the references" (thinner,
longer, fainter). Every change with measured cost (High 1440p vs 3.0, Low, Potato). Hand off to C:\qfb\shaderdev\r012\.

## Progress log
- 14:53 started; queue idle (day mode, cost jobs allowed until 22:15).
- 15:00 (loop 1, uncommitted): BSL v10.1.8 zip ships no licence; techniques.md files its agreement as no
  modified redistribution -> BSL read only (like Complementary). Causes found: (1) pink = Photon's evening tint
  vec3(1.05,0.84,0.93), multiplied into sunlight AND the whole sky; (2) no glow = final.glsl sunGlare scales by
  `vis` (share of the disk clear at 0.3 x peak), so a sun under cloud gets nothing, and its PSF holds ~3e-4 of
  the sun's energy vs Photon's bloom ~12 %; (3) r011 meteor clips were 1:1 crops at 1440p (streaks look 2x).
  Code: lib/photon.glsl QF_SUN_GOLD [0 1 2] (Photon's user sun tint split: gold on sunlight + Mie, near-neutral
  on Rayleigh; phScatteringT), phAirFogNear + QF_PH_NEAR 32 (land haze starts 32 blocks out); final.glsl
  QF_SUN_BLOOM [0 1 2 3] (two analytic lobes 2/7 deg, gold at low sun, own visibility visG counting sunlit thin
  cloud); QF_CREPUSCULAR default 1 (owner C), QF_METEOR_STYLE default 5 (owner B), sky.glsl QF_METEOR_LEAN 1.
  check_glsl 0 errors (defaults + 3 option combos). Shot **1028-150047-r012-loop1-shot**
  (specs/r12-loop1.json: r12a defaults x8 views, r12g2 GOLD2+BLOOM3, r12b1 BLOOM1, r12n0/r12n64 golden_lit,
  r12m5c storm clip crop 320,0,1920,1080).
- 15:15 orchestrator ask: texture track's gem SSR patch (C:\qfb\gems\gem-ssr.patch) merged behind **QF_GEM_SSR 0**
  [0 1] (needs QF_METAL_SSR, i.e. Medium+): lib/lighting.glsl (diffuse x (1-F) for smoothness > 0.88 and F0 > 0.1),
  composite.glsl gemReflection() + call after metalReflection. No conflict with r012 shader work. check_glsl 0 errors
  (defaults, GEM_SSR=1). Cost: to measure in the r012 cost run (world C:/qfb/textures/world-gems, pack
  QF-gems-facet.zip, gem_glint_d/gem_glint_e/gem_lit, GEM_SSR 0 vs 1 vs preset off).
- loop 1 wait moved to background (queue was waiting for the owner to be idle).
- 15:20 loop 1 read (sheets C:\qfb\shaderdev\r012\sheets\l1_sunset.jpg, l1_sunbox.jpg, l1_golden.jpg, l1_views.jpg,
  l1_met.jpg, m5c_zoom.jpg):
  **gold** works: ocean_sunset clouds amber not salmon, upper sky 139,123,115 (r011 138,112,121 lilac); noon unchanged.
  GOLD 2 (deeper) barely differs from 1; keep 1. **glow** did NOT show: r12a = r12b1 = r12g2 to 1 luma (sun box
  249,186,113; BSL 248,223,151). Cause: visG measured against the disk peak (cloud ~0.06 of it) and the sliver lies
  outside the 0.45 R taps. Loop 2 fix (final.glsl): visG = smoothstep(0.30, 1.0, exposed) over 9 inner taps + an 8-tap
  ring at 0.9 R; glow in exposed units (core 0.9 @ 1.7 deg whitish-gold, wide 0.25 @ 5.7 deg gold) x BA (0.5/1/1.8)
  x mix(0.25, 1, low sun) x visG. **near haze**: diagnosis confirmed it was Photon's near haze, not ambient:
  golden_lit bottom NEAR 0 62,66,32 / NEAR 32 40,56,20 / NEAR 64 40,57,20 (r010 38,45,15, r011 69,67,41); keep 32
  (mid-field keeps some gold depth: 75,72,30 vs 64's 63,65,23). **rays** (round 10's) read on lake_glitter and
  ocean_sunset as a clean fan, no streak artifacts. **meteors** lean: hairlines ~2 px at 1440p, tapered both ends,
  no beading at 3x (m5c_zoom.jpg); lab-size still close to the photos. Critic's dusk contrail: meteors now fade in
  from sun -3 deg, full at -8 (sky.glsl).
- 15:15 **loop 2 shot submitted: 1028-151425-r012-loop2-shot** (specs/r12-loop2.json: r12c defaults x7 views, r12c1
  BLOOM 1, r12c3 BLOOM 3). **Cost run submitted: 1028-151500-r012-publish-cost** (specs/p12-cost.json: p12 x23,
  p12g0, p12b0, p12n0, p12cr0, p12cr2, p12clipm5 / p12clipl0 bursts crop 320,0,1920,1080, off baselines, me/lo/po,
  gm0/gm1/gmoff gem SSR on world-gems). Queue had ~65 texture renders ahead: loop 2 ETA ~15:50, cost ~16:50.
- Committed **4f9e553** (all r012 shader code + gem merge; CRLF from python writes fixed back to LF).
- Drafted C:\qfb\shaderdev\r012\spec_scenes.py (sunset-full A p12 / B p11r ocean_sunset; sun-cloud A p12 / B p11r /
  C p10cr golden_lit; meteors ov p12clipm5 / p12clipl0 scale 0.6667) and round.json (renders r012 cost + r011 + r010).

## Resume here (fresh agent)
1. `py -3.10 tools/renderq/renderq.py results 1028-151425-r012-loop2-shot`; sheet r12c/r12c1/r12c3 ocean_sunset +
   lake_glitter vs p11r and refbsl (tools in C:\qfb\shaderdev\r012\tools: sheet.py, crops 810,405,800,450); sun box
   means (1110,545,200,100). Also check sky_noon r12c3 (no wash) and shore_dusk (no meteor). Pick QF_SUN_BLOOM default.
   If the glow still doesn't show, debug visG (QF_DEBUG_VIEW in final) before tuning amplitudes.
2. If the default changes: edit settings.glsl, check_glsl, commit; the cost run's p12 frames then need a re-run of
   the affected tags only (p12 sunset views, p12b0 unaffected). Note glow cost ~0 (17 cached taps + 2 exps).
3. When 1028-151500-r012-publish-cost lands: costs per change (spec_scenes computes them), gem SSR = gm1 - gm0 per
   view (log here; tell the texture track), meteors p12clipm5 vs p12clipl0 vs budget 3.0.
4. Re-measure golden_lit bottom (1080:1440 rows) on bench-p12-golden_lit.png and update "(now 40,56,20)".
5. Dry-check spec_scenes with roundlib if allowed; write C:\qfb\shaderdev\r012\SHADERS-READY.
6. ops/tracks/shaders.md, one journal entry (ops/journal/shaders.md), commit, `git log origin/main..main`, push.
