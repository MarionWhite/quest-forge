# r014 shader (shader-dev, 2026-10-31)

Work order: ops/checkpoints/r014-plan.md "Shader" 1-5 (critic r013 notes = the brief: C:\qfb\shaderdev\r013\critic.json
p13/ocean_sunset, p13/shore_sunset, p13/sun_clear, p13clipm/night_wide, g13c/gem_glint_d). Hand-off to
C:\qfb\shaderdev\r014\ (spec_scenes.py, round.json, renders, SHADERS-READY). Night mode 22:15-08:00 = shots only.

## Progress log
- 19:35 started; queue idle. Read plan, r013-shader checkpoint, critic notes.
- 19:40 settings QF_CLOUD_COVER list += 0.30 0.60 (cloud-free sky for the whole-disk sun view). Tools copied to
  C:\qfb\shaderdev\r014\tools (grid.py, m.py band metrics). Measured r013 frames: ocean_sunset sky 6 deg up r/b 1.94
  (gold), band y900-1020 sea 72,65,57 r/b 1.26 vs BSL 73,52,36 r/b 2.03. Gem _s maps are uniform (smooth 240, F0 44):
  uniform clear coat over a lambert pastel body = plastic. Submitted **1031-194049-r014-loop0** (shots: water debug
  13/14, sun_clear cloud cover 0.6/0.3, BSL+Photon refs shore_sunset/sun_clear).
- 19:46 code committed cecae3e, all default off: QF_SEA_GRAZE 1/2 (composite shadeWaterAbove: BSL normal fade
  pow(1-cos,8) x goldenHour for reflection dir + Fresnel; 2 also body x (1-0.65k)), QF_RIM_GOLD 1/2 (sky.glsl cloudLum
  gold toward the sun + fringe; 2 also tonemapNeutralW warm shoulder in final.glsl), QF_METEOR_CULL (skip slots with
  bright < cull), QF_METEOR_HUE 1 (green/amber body, white head, green train), QF_GEM_LOOK 1/2 (lighting.glsl
  gemInnerLight: body x0.5/0.25 + inner facet env tinted + sun flash with fire). Submitted **1031-194540-r014-loop1**
  (specs\r14-loop1.json; baselines = r013 frames p13, p13clipm, g13c).
- 19:55 loop 0 read (sheets r014\sheets\l0_shore.jpg, l0_sun.jpg; tools m.py, sunprof.py): ocean_sunset mid band
  (y900-1020) = transmitted 29,31,39 (r/b 0.75, a third of the light) + reflected x F 60,55,46 (r/b 1.29) -> both grey.
  Photon refs (ref14ph) on shore_sunset/sun_clear render broken (flat yellow): ignore; Photon ocean_sunset = refs\refph.
  Whole disk: QF_CLOUD_COVER 0.6 on sun_clear gives a fully clear disk (r14cc6; 0.3 leaves a wisp across it).
  Glow profile (luma at 50/100/200/300 px): r13 cc6 213/201/190/167 peach 253,203,157 @60px; BSL ocean_sunset
  235/211/171/148, 255,249,200 @60px; Photon 178/154/146/144. -> QF_SUN_HALO 1/2 (final.glsl bloom lobes).
  Coordinator: textures packs C:\qfb\textures\r014\QF-gems-{crystal,polished,faithful}.zip; gem option must be shown on
  them -> loop 2a. Committed c1b7bb9. Submitted **1031-195537-r014-loop2a** (halo on cc6 + clouded; GEM_LOOK 1 on the
  three r014 materials). Queue ETA ~20:17 for loop1+textures; 2a after.
- 20:10 loop 1 read (sheets l1_gems*.jpg, l1_shore.jpg, l1_meteor_*.jpg; tools mstack.py):
  SEA: GRAZE 1/2 (BSL normal fade) = no change (mid band r/b 1.23): the middle sea mirrors our sky 10-15 deg up, which
  is pale (181,159,129 r/b 1.4) where BSL's is amber (161,112,69 r/b 2.3); only <6 deg is gold. -> GRAZE reworked:
  mirrored elevation x mix(1,0.35,grazeK) (Fresnel-weighted facets lean to the horizon), 2 adds body x0.4 at golden hour
  (shore near-water mud = body scatter 31,26,7 in debug 13).
  RIM: RIM_GOLD 1 (mu-weighted) = no change: the coral clouds are far round from the sun. 2 (warm shoulder) top5%
  248,149,99 -> 248,146,79. -> RIM_GOLD now tints all sunlit cloud light under 7 deg (0.92,1.10,0.50).
  METEORS: clips are real-time, not repeatable frame by frame (stack-diff of cull meaningless). HUE 1 works: green-white
  and amber streaks like the r010 photo (stack streak g/b 1.38 -> 1.59). Cull 0.25 = the faintest 28% of slots (peak
  under 1/11 of the brightest): cost decides.
  GEMS: LOOK 1/2 (6 cells) not plastic any more (deep body, facet contrast), but a square mosaic; white dashes remain.
  -> 4 cells, LOOK 2 = map facets only, surface sun off the flat face (no bevel dashes), body 0.4.
  Committed c53c3f0. Submitted **1031-200934-r014-loop2b**. Frozen r13 pack: C:\qfb\shaderdev\r014\pack-r13\QuestForge
  (git archive 0b235e6, CLOUD_COVER list += 0.30 0.60).
- 20:25 loop 2a read: QF_SUN_HALO 1/2 change NOTHING on the cloud-free sun (profiles equal to 1 luma) -> the
  final.glsl sunGlare bloom seems not drawn at all on a clear sky (visG 0?), which is also why the critic found "the
  glow is round 12's" in A/B/C. Added QF_DEBUG_VIEW 16 (glare alone); submitted **1031-202034-r014-loop2c**
  (debug 16 clear+clouded, bloom 0/3 on cc6). Gems on textures' r014 packs (sheet l2a_gems_mat.jpg): crystal/faithful
  already varied; GEM_LOOK 1 deepens them, no harm. Waiting: loop2b (1031-200934-r014-loop2b), loop2c.
- 20:35 loop 2b/2c read: GRAZE (elevation pull) mid sea r/b 1.26 -> 1.35 only; RIM_GOLD 1 (sunlit light) top5% G
  149 -> 153 only (the bright bases are lit by c.under = the rose horizon 60 deg round). Debug 16: the final-pass
  bloom adds ~0.03 on the clear sky (bloom 0 vs 3: 1-2 luma); the visible glow is the sky aureole (skyRadiance).
  -> loop 3 code 60bd70f: HALO now reshapes the sky aureole; RIM_GOLD also tints c.under; GRAZE adds a horizon-hue
  pull on the reflection (0.75 x grazeK). Submitted **1031-203418-r014-loop3**.
- 20:41 loop 3 read (sheets l3_sea.jpg, l3_shore.jpg, l3_halo*.jpg): sea mid band r/b 1.26 -> 1.51, upper 1.49 -> 1.97
  (BSL 2.03/2.33); shore clouds coral -> golden (mean b/g 0.61 -> 0.54, top5% B 99 -> 74; G stuck ~151); near shore water
  39,28,12 -> 31,22,11 (darker reflection). HALO via the sky aureole ALSO changed nothing (<1 luma): the clear-sky glow
  is Photon's haze forward lobe (phAirFogO, HG 0.5). -> HALO now mixes HG 0.9 into the first bounce (15/25 %) + aureole.
  Gems (l2b_gems.jpg, l2b_cry.jpg): LOOK 1 cells read as a blocky camo on the r013 pack; LOOK 2 (map facets) on the
  textures track's crystal pack = rich, gem-like; on the r013 pack it keeps faint bevel dashes. Default LOOK 2.
  Tweaks: grazeK range 0.5 -> 0.8, hue pull 0.75 -> 0.95; rim tint (0.84,1.18,0.48).
  DEFAULTS now: QF_SEA_GRAZE 2, QF_RIM_GOLD 2, QF_METEOR_CULL 0.25, QF_METEOR_HUE 1, QF_GEM_LOOK 2, QF_SUN_HALO 0
  (option 1 shown via p14cch1/p14h1). Committed c16551c.
  Submitted **1031-204102-r014-loop4** (shots verify, priority 1) and **1031-204111-r014-publish-cost**
  (specs\p14-cost.json, 25 jobs, 118 scenes). If loop 4 shows a problem: cancel the cost, fix, resubmit before 22:15.
- 20:45 loop 4 read (sheets l4.jpg, l4_sun.jpg): sea mid r/b 1.82 (BSL 2.03), upper 2.30 (BSL 2.33), near 1.22 (1.48)
  but khaki (104,86,45); RIM_GOLD 2's warm shoulder burnt the sun core cream (0 px white) -> shoulder back to white
  past peak 6-20 (tonemap.glsl), sea hue sampled 2 deg up (orange-gold). HALO 1/2 via HG 0.9 still ~no shape change.
  Cancelled 1031-204111 (41/118 done, cached). Committed (see git log). Submitted **1031-204532-r014-loop5** (verify,
  priority 1) and **1031-204537-r014-publish-cost** (FULL ID; specs\p14-cost.json; ETA ~21:35).
- 21:06 drafted C:\qfb\shaderdev\r014\spec_scenes.py (5 scenes: sea-sunset p14/p13r, shore-sunset p14/p13r, sun-glow
  crops p14cc/p14cch1/p13rcc, meteors clips p14clipm/p13rclipm, gems crops gem_glint_e g14c/g14c0/g14cry2/g14cry0) and
  round.json (renders 1031-204537-r014-publish-cost + loop5; budgets p14/p14lo/p14po). Halo core scaled x2/x4 in the sky
  aureole (committed; cost-neutral constants) -> **1031-204608-r014-loop6** (shots after the cost). NOTE: p14cch1 in the
  cost run has the OLD halo constants (0.30): if loop 6's x2.0 looks right, re-shoot p14cch1 sun_clear as a shot
  (night-safe) or use r14hb1 in the scene (cost the same: constants only).
- 21:20 loop 5 read (sheet l5.jpg): sea middle band r/b 1.99 (BSL 2.03), far 2.59 (BSL 2.33), near 1.26 (BSL 1.48),
  reads warm gold; shore clouds amber (mean b/g 0.61 -> 0.53, top5% 248,149,99 -> 247,156,71), near water dark mirror;
  sun core white again on the cloud-free view (1621 px full white). spec_scenes.py sea text updated with these numbers.
  Track + journal updated. Cost ETA ~21:40 (>10 min): exiting per CLAUDE.md.

## For texture-dev (gem GLSL, r014)
Shader side of "looks like plastic" (lib/lighting.glsl gemInnerLight, QF_GEM_LOOK, default 2): gem pixels are still
detected as smoothness > 0.88 && F0 > 0.1 (_s R > 224, G > 25). For those: lambert body x0.4 x (1 - Fresnel); added
inner light = sky along reflect(view, inner facet normal) x stone tint (albedo normalised, squared) x (1 - F) x 1.6,
plus a ~3 deg sun flash per inner facet with a little dispersion colour. Inner facet normal: LOOK 2 = the _n map's tilt
x4 (so the material's own facets drive it: draw facets in _n, keep crystals smooth / gaps rough in _s); LOOK 1 = map
tilt x3 + random cells 4 per block (for flat-_n packs). The surface sun glint now uses the flat face, not the _n bevels.
The surface (composite gemReflection, SSR) stays untinted with one Schlick Fresnel per pixel from F0. _s SSS/emission
channels still not read. Shown on QF-gems-crystal/polished/faithful in loop 2a (g14cryl1/g14poll1/g14fail1) and 2b
(g14crym1/g14crym2); publish cost g14cry2 / g14cry0 (LOOK 2 / 0 on crystal).

## Resume here (fresh agent)
1. `py -3.10 -I tools/renderq/renderq.py results 1031-204537-r014-publish-cost` (FULL ID; 25 jobs). Check
   C:\qfb\shaderdev\rounds\bench\p14*.userbusy.json / g14*.userbusy.json noisy false (re-submit a noisy job alone, cost
   mode, before 22:15 or after 08:00; shots any time). The cancelled 1031-204111 run wrote the same tags earlier with
   older defaults: confirm frames are newer than 21:00 (the new run finishes last).
2. Loop 6 `1031-204608-r014-loop6` (shots): halo core x2/x4 (r14hb1/r14hb2 cloud-free, r14hc1 clouded). Run
   `py -3.10 -I C:\qfb\shaderdev\r014\tools\sunprof.py sun_clear r14vcc,r14hb1,r14hb2,ref14bsl`: target BSL-ish
   235+/211/171/148 at 50/100/200/300 px. If one is good, the sun-glow scene's B should show it: p14cch1 was costed with
   the old halo constants (cost-identical: constants only), so re-shoot `p14cch1` sun_clear with the current pack as a
   shot (tag p14cch1, --replace) or point option B at r14hb1/r14hb2 and say so. If none is good, B's text must say the
   glow is the sky/haze Mie glow and the halo tries did not change its shape (numbers in the log above).
3. Sheets with tools\grid.py (p14 vs p13r): ocean_sunset, shore_sunset, sun_clear crops 912,436,600,360 (p14cc,
   p14cch1, p13rcc), gem crops gem_glint_e 1100,620,800,420 (g14c, g14c0, g14cry2, g14cry0), meteor stack
   tools\mstack.py p14clipm,p13rclipm. Only changed frames. Check no magenta.
4. Costs: worst High p14 (expect water views ~3.5 > 3.0, as r013: the intro says so), p14lo <= 0.9, p14po <= 0.4;
   meteors p14m vs p14mc0 vs p13rm (critic target 2.94: if the cull does not get there, say so in the meteors text);
   sea p14 vs p14sg0, rim p14 vs p14rg0, gems g14c vs g14c0.
5. Dry run: `py -3.10 -I tools/shaders/review/finish_round.py` with --allow-missing-critic per r013 (see r013 checkpoint),
   fix any text a number contradicts, then touch C:\qfb\shaderdev\r014\SHADERS-READY, update ops/tracks/shaders.md
   (round state line), one journal entry, commit own hunks, check `git log origin/main..main` before any push.
