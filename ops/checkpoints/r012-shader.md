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

- 16:40 (resume agent) loop 2 read (sheets r012\sheets\l2_sun.jpg, l2_sunbox.jpg, l2_suntight.jpg, l2_glowopts.jpg,
  l2_views.jpg, l2_met.jpg, l2_metf.jpg): **glow shows** now, soft white-gold round the sun behind the cloud base
  (sun box 1110,545,200,100: none 194.0, BLOOM 1 195.1, 2 196.0, 3 197.4; BSL 224 with a clear disk); noon unchanged
  (upper sky 135.6 vs 135.7 without). lake_glitter: the glow lies over the cliff where the sun's top limb pokes over the
  ridge (as BSL's does there). Kept QF_SUN_BLOOM 2; offered 3 on the Lab (sun-glow crops). **Gold** ocean_sunset upper
  sky 154,133,116 (gold off 163,128,131); shore_sunset barely moves (144,100,84 vs 146,96,86): sun on the horizon,
  salmon there is extinction, not the tint (later item). **Near grass** golden_lit bottom 40,56,19 (r010 38,45,15).
  **Rays** round 10's: clean fan on lake_glitter / ocean_sunset. **Meteors** lean: thinner, longer, tapered; none at
  shore_dusk (r011 had the contrail).
- Costs (1028-151500, High 1440p vs shaders off): worst **ocean_sunset 3.65** (r011 3.30), lake_glitter 3.23,
  swamp/sea 3.08-3.18; Low 0.89, Potato 0.31, Medium 1.55. Per change: gold +0.00..+0.04, glow +0.00..+0.09, near air
  +0.00, round 10's rays +0.01..+0.30 (Photon's +0.00..+0.02), meteors lean = r011 shape 2.94. **Gem SSR gm1-gm0
  +0.18 / +0.17 / +0.05** (gem_glint_d/e, gem_lit) -> GEM_COST in r012	extures_make_scenes.py, rerun, no "pending".
- spec_scenes.py finished (4 scenes, sun-glow added: oc crops 890,440,640,360 of p12 / r12c3 noCost / p12b0), round.json
  + loop-2 render; dry-checked with roundlib (scratchpad dry.py): no missing frames or costs, 7 critic notes to write.
  SHADERS-READY written.

## Resume here (fresh agent)
Done. Next is the critic (r012/critic.json) and the publisher (finish_round.py). Follow-up for r013: a cheaper round-10
rays pass (16 random-access taps per sky pixel near the sun = +0.30 ms on ocean_sunset) if the owner keeps them.

## Pre-publish fix (2026-10-28 16:45, shader-dev)
Critic: hard-edged oval through cloud in the gem glint frames; sun-glow scene unjudgeable; gem_lit B clip misaimed.
- Cause (numbers, g12a-gem_glint_d): the oval is the **sun disk**, not the glow. The g12 gem frames were shot on
  C:/qfb/gems/base (r011 export, no QF_SUN_BLOOM at all) and gm0 (r012 pack) shows the same oval. Profile row 300:
  cloud 185-189 -> inside 223-228, +7 luma/px rim; oval 78 x 112 px = the 4-deg disk (SUN_REAL_R 0.0705) projected
  off-axis. Disk core ~50 exposed x cloud T (march stops at T < 0.02) -> 1-2 % still beats the cloud. Only the glint
  views (sun in frame); gem_lit has the sun behind the camera (glare returns early): no oval there.
- Fix: lib/sky.glsl gCloudTd = T * smoothstep(0.03, 0.25, T) (disk fades out with the cloud). check_glsl 0 errors
  (defaults, GEM_SSR=1).
- Shot **1028-164341-r012-gemfix-shot** (r012/specs/r12-gemfix.json): g12af / g12bf / g12cf (GEM_SSR 1) glint_d/e on
  the current pack; g12bclip2 gem_lit burst crop 800,400,960,540 on the base pack (matches g12b's still).
- Next: wait, check oval gone, make_clip g12bclip2, textures_make_scenes.py new tags, drop sun-glow from
  spec_scenes.py (r013: clear-sun view), critic notes for new tags, commit, push.
- 16:53 gemfix done: oval fill gone (row 300 inside 224 -> 196-204, smooth glow), but a thin outline stayed (+4-5 luma,
  2-3 px): the glare's tight corona hugging the hidden limb. final.glsl: corona x limbVis (one tap at 0.85 R toward the
  pixel, only th < 2.5 R). check_glsl 0 errors (defaults, GEM_SSR 1, BLOOM 0 + LENS 1).
  Shot **1028-165517-r012-gemfix2-shot** (specs/r12-gemfix2.json): g12a2 / g12b2 / g12c2 glint_d/e. Use these tags
  (not g12af/bf/cf). g12bclip2 (from gemfix) is the B clip. spec_scenes.py: sun-glow dropped (done).
- 17:05 **done.** gemfix2 read: no oval, no outline (row 300 monotonic, peak 206). textures_make_scenes.py: glint views
  -> g12a2/b2/c2, gem_lit B -> clips\g12bclip2-gem_lit.webp (make_clip done); rerun OK. spec_scenes.py: sun-glow dropped.
  critic.json: notes for g12a2/b2/c2 x glint_d/e, g12bclip2/gem_lit, crop/g12bclip2-gem_lit.webp; summary appended.
  round.json renders += both gemfix submissions. Dry check: 0 missing frames, 0 missing critic notes. Publisher next.
  r013: clear-sun glow view; sunset frames (p12) predate the disk fix.
