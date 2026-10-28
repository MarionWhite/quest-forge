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
