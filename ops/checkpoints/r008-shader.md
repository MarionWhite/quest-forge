# r008 shader checkpoint (2026-10-25 ~21:50)

Brief: owner's r007 answers (docs/design/shaders/feedback/r007.json, committed dd2c734; look bible e3b7ea2).
Shader WIP da16ea8: compiles clean (check_glsl), NOT yet reviewed in frames.

## Asks
- Sun: done, unreviewed. QF_SUN_SIZE 3.0 (opts 1-5); sunPeak 16-22 with a hot white core; glare psf measured from the limb (final.glsl). The dark ring came from the shafts' `pow(mu,1500)` cut-out; removed.
- Dust: done, unreviewed. QF_DUST 0/1/2: a dustField in lightShafts (first 24 m); gBeam counts lit/shaded flips along the ray; motes are lit only when gBeam > 0, sized by depth.
- Golden horizon: done, unreviewed. QF_GOLD_HORIZON in skyScatter.
- Lake: done, unreviewed. QF_LAKE_CALM: style 3 raised the lake's chop 1.7x at sunset (the cause). The lake amp now falls to 0.26 at golden hour; flatter SSR normal.
- River ledges: done, unreviewed. Bed light is filtered by the sun path through the water (Tdown), and caustics redistribute light instead of only adding it.
- Meteors: done, unreviewed. QF_METEOR_RATE default 3, trains.
- Vibrance: 0.25 (settings + lang).
- PBR metals: done, unreviewed. metalShade(), QF_PBR default 1, MAT_METAL without maps too.
  - The r007 black blob was a NaN from fresnelSchlick pow(neg). Fixed with a clamp, plus NaN guards in composite out and TAA history.
- Under water: done, unreviewed. QF_UNDERWATER: caustics, shafts, ringed bubbles; UW_SURF 62.9. New view underwater_sun.
- Motion clips: built by a fork, commits 96303ff, 35c2de0, d95f67c.
  - Job `"burst":{"frames":90,"interval_ms":66,"crop":[x,y,w,h]}`; `ov()` in spec_scenes; tools/shaders/review/make_clip.py.
  - Use 66 ms or more; at night (30 fps cap) a shorter interval repeats frames.
- Untouched: spec_scenes.py and round.json for r008; the texture scenes merge; the Lab footer.

## Loop 1 done (ub, commit a1119da, 2026-10-25 ~22:50)
- ua reviewed (sheets C:/qfb/shaderdev/r008/look/ua): sun 30 px, brown horizon band + cyan zenith, lake choppy, river ledges
  yellow, dust specks over the lake sky, no meteors in stills.
- Fixed in a1119da (renders 1025-222049-r008-ub, QFTextures-v1, sheets look/ub): QF_SUN_SIZE 5; band lift + lavender zenith +
  lighter veil; lake calm also on river share; river bed sun path +1.2 blocks x4 + shallow tint (yellow gone, now green);
  motes need shade within 2.2 m across the light (sky specks gone); QF_METEOR_RATE 4, wider streaks.
- Clips (make_clip): C:/qfb/shaderdev/r008/clips/{met,wat,cld,dust}.webp from ub_clipmet/ub_clipwat/ub_clipcld/ub_clipdust.
  The met burst ran ~318 ms/frame (night cap?), so that clip is 28.6 s long.
- Still wrong (loop 2): the horizon band is khaki, not peach (the warm multiplier cuts blue too hard; haze desat in composite ~l.1001);
  the lake is still choppy next to the refs' mirror; the sun disk is still smaller than the refs' (try 6, brighter core vs the glare);
  no meteors in stills (TAA may eat them; see look/ub/met_max.jpg); PBR metals barely differ from QF_PBR 0.
- Grey blob in the clouds over the noon sun (river_noon): pre-dates r008. Not the sun (QF_SUN 0 keeps it), not the rim
  (QF_CLOUD_RIM 0 keeps it), and it moves between boots: suspect vanilla clouds (gbuffers_clouds). Not fixed.

## Renders
- 1025-211519-r008-ua: shot mode, iteration a. Tags ua (15 views), ua_met (NIGHT_SKY 4), ua_pbr, ua_pbr0 (showcase world). Finished; NOT looked at yet.
- 1025-211531-r008-uc-cost: early cost read (High / Low / Potato and off baselines). Queued.
- New FrameBench jar: the cache reset once.

## Findings
- refs (C:\qfb\shaderdev\refs, internal only): CU, CR and BSL all show a clear, large disk with a bright halo and a warm horizon band all round.
- The cyan hills grass is the biome colour: all four packs show it. Not a shader bug.

## Next
1. Contact sheets: C:\qfb\shaderdev\r008\tools\sheet.py OUT tag:scene[@x,y,w,h] ... Compare ua against refcu/refcr/refbsl and tune.
2. Re-iterate in shot mode (night 22:15-08:00).
3. After 08:00: final cost-mode submission (defaults, option tags, burst clip jobs, Low/Potato, off baselines).
4. Texture v1 when C:\qfb\shaderdev\r008\TEXTURES-READY exists; merge texture_scenes.json after ours.
5. Write r008 spec_scenes.py and round.json, critic.json, then `finish_round.py --publish --no-push`.
   - Then check that r008.json returns 200, take the Edge screenshot, check `git log origin/main..main`, push.

## Traps
- `#if` cannot compare floats.
- gBeam and UW_SURF must be declared before ambientMotes.
- Costs measured under the night cap are invalid.

## Loop 2 (uc..., 2026-10-25 ~23:30) - fixes in the tree, compiled clean, not yet rendered
- Sun: QF_SUN_SIZE 15 (3x; options 3-18); cutoff cos(R*1.3) instead of 0.999; white core over mu>0.55, gold rim; near glare 0.20->0.10; glare taps 0.45R, want 0.30 peak.
- Beach/shore mint: Tdown x4 + shallow tint only for river share (lib waterRiverShare); sea keeps 1.6 at 0.35 weight.
- Golden band cream-peach (blue kept), below-horizon veil 1.0/0.94/0.88, golden haze and aerial air desaturated to cream.
- Lake: waterCalmShare() = max(lake, glassy w); chop to 0.12 at golden hour; SSR flatS 0.92; SSR weight no longer falls linearly per step (shore mirror).
- Dust: beam motes gated per mote (inBeam), not by the dithered per-pixel gBeam; brighter.
- Meteors: tint white/warm; added after the clouds via gMeteor with smoothstep(0.85,0.99,cloudT).
- Metals: metalShade(..., diffuse): x1.6 env + horizon band, broad sun sheen, never below diffuse*1.05.
- Cloud blob: light samples use soft cloudDensL (smoothstep of signed field), far weight 130->90.
- Spec: C:/qfb/shaderdev/r008/specs/ud.json, submitted as 1025-225155-r008-ud (tags ud, ud_met, ud_pbr, ud_pbr0, ud_clip{met,wat,cld,dust}). Next: wait, sheets vs refs, commit.
- ud reviewed (sheets C:/qfb/shaderdev/r008/look/ud, clips C:/qfb/shaderdev/r008/clips/ud_*.webp): sun ~50 px white disk (fixed);
  beach/shore sand tan again (fixed); lake a clean mirror of cliff, tower and clouds (fixed); metals bright and reflective (fixed);
  meteors behind the dark core but trains green and over thin cloud; golden band still khaki (187,163,116 vs CR 222,179,155);
  cloud blob softer in biome_ocean, still in river_noon; dust still invisible in the clip.
- Post-ud tweaks: band rosier + lift 1.15; deep cloud diffusion octave; metal env 1.4+0.9; meteor train blue-white, cloud cut 0.93;
  dust: raw 3.5 m four-side beam test, maxD 30, QF_DUST_DBG diagnostic. Verify batch 1025-231105-r008-ue (tags ue, ue_pbr, ue_clipmet, ue_clipdust, ue_dustdbg).
- ue reviewed: cloud blob gone in biome_ocean, faint in river_noon; band a bit lighter (193,168,128); QF_DUST_DBG 1 also lit nothing
  in the beam: not the gate. Cause found: MOTE_STEPS 22 walks only ~16 m. Now 38 (Ultra) / 26 (High) with QF_DUST; band pushed rosier.
  Verify batch 1025-232208-r008-uf (uf, uf_clipdust, uf_dustdbg).
- uf/ug/uh reviewed: band 199,170,137 (CR 222,179,155; closer, still a little khaki); a bright ring at the limb behind leaves
  (glare skipped inside the disk on non-sky pixels) fixed in final.glsl; sunlit motes over sky and bright far land were white
  specks (owner's r007 complaint): motes now never over sky and fade over bright backgrounds (uh: specks gone).
- Loop 2 committed (see git log "r008 loop 2"). Renders this loop: ud, ud_met, ud_pbr, ud_pbr0, ud_clip{met,wat,cld,dust},
  ue, ue_pbr, ue_clipmet, ue_clipdust, ue_dustdbg, uf, uf_clipdust, uf_dustdbg, ug, uh. Clips: C:/qfb/shaderdev/r008/clips/ud_*.webp.

## Next (loop 3)
- Dust in the beam is still not visible (even QF_DUST_DBG 1): the forest_golden beam lies 20-40 m out where a 1.25 m-cell mote is
  ~1 px, and the near air is shaded. Try: larger mote cells past 15 m (2.5-4 m, 2-3 px flakes), or a dust view with a beam in front
  of dark trunks; also check sampleShadow's vis at the mote is not zeroed by eyeSky^2 under canopy. Cost of MOTE_STEPS 38 needs a cost run (morning).
- Golden band: still ~20 under CR in R and B; try a below-horizon veil lift and less haze yellow.
- river_noon cloud: faint grey patch left.
- Then the morning cost submission, spec_scenes.py, round.json, finish_round (see the earlier Next list).

## Loop 3 (uj, 2026-10-25 ~23:57) - fixes in the tree, check_glsl clean (also with METEOR_SHOW/DUST_DBG), rendering
- Dust: motesGrid() near grid (1.25 m, 0-18 m) + far grid (3 m cells, 14-48 m, 2-3 px flakes, 5 m beam taps);
  the old fadeD faded everything from 18 m (the real reason DBG lit nothing in the beam). Mote fade over bright bg 0.30->0.55.
  New views dust_beam/2/3 (forest_golden walked 10/16/22 blocks toward the gap) in tools/shaders/review/views-world-master.txt.
- Golden ground: shafts' lit air at golden hour in open sun counts only from 28-80 m (litFar; beams keep near air);
  aerial starts 48 m out at golden hour; haze start 0.35->0.46 far. Band warm B up, lift 1.22->1.32, below veil 1.04/0.96/0.95.
- Sun: thin bright rim (core smoothstep 0.22-0.50, rim 0.45-0.85), core 1.6->2.4; glare core 0.12 @ 0.0026; glare on land within 2.5 R cut to 0.12.
- Meteors: QF_METEOR_SHOW 1 (dev) pins two meteors in front of the camera for stills.
- Metals: bent-face reflection (sky top, crisp horizon, ground bottom per block), diffuse on top 0.55->0.32.
- Lake: calm golden water F >= 0.34 near, body x0.72. River: constant 2.2-block bed path, shallow tint removed.
- Clouds: 3D noise finer in height (4.6, 7.5), deep diffusion 0.26.
- Spec C:/qfb/shaderdev/r008/specs/uj.json, submitted 1025-235656-r008-uj (tags uj, uj_dustdbg, uj_met, uj_pbr, uj_pbr0,
  uj_clipmet, uj_clipwat, uj_clipcld, uj_clipdust, uj_clipdust2). Next: wait, sheets in C:/qfb/shaderdev/r008/look/uj, commit.
- uj reviewed (sheets C:/qfb/shaderdev/r008/look/uj): sun now a crisp white disk (good); forced meteor shows in night_sky
  (QF_METEOR_SHOW 1); metals show a horizon line across each block; golden_lit near ground still olive (77,60,17 vs BSL 43,46,22).
  BOOT FAULT: in b1026000221 every scene after forest_golden (lake, river, sky_noon, ocean, dust_beam*) rendered with no
  terrain (chunks stopped loading after the first teleports); not the shader (pbr boot fine, forest_golden fine every time).
- Post-uj: lighter amber + full sky fill on up-facing non-foliage faces at golden hour (lib/lighting.glsl upF); dust views y=64.0.
- Re-render 1026-001926-r008-uk (uk, uk_clipwat, uk_clipcld, uk_clipdust2, uk_clipdust), spec C:/qfb/shaderdev/r008/specs/uk.json.
- uk reviewed (sheets look/uj/k_*.jpg): lake near water now carries the blue sky and cloud reflections (fixed); river grey
  cloud patch gone; ledge stripes fainter but still there; pale glare disk over leaves gone; sky_noon streaks only a little
  less; golden_lit near ground unchanged (78,62,19 vs BSL 43,46,22): the upF amber change did nothing measurable, reverted.
- Dust: the dust_beam views (y 64) stand inside the canopy with the sun hidden: useless, removed from the views file.
  ul (far grid density 2.6x, gain 1.8x): a handful of drifting flakes in the forest_golden beam (look/uj/l_dust.jpg),
  more than uk, still sparse. Not the "dust in the beam" the owner wants yet.
- Clips: C:/qfb/shaderdev/r008/clips/l3_{met,wat,cld,dust}.webp (uj_clipmet, uk_clipwat, uk_clipcld, ul_clipdust).
- Loop 3 committed ("r008 loop 3"). Renders: 1025-235656-r008-uj, 1026-001926-r008-uk, 1026-002542-r008-ul.

## Next (after loop 3)
- Golden ground olive: not the shafts, aerial or amber paths (all changed, near pixel moved by <2). Bisect with
  QF_SHAFTS 0 / QF_CAL_GOLD 0 / QF_AERIAL 0 jobs on golden_lit; suspect the grade or skyIrradiance at golden hour.
- Dust: needs a real view where a beam crosses near air (find a gap with region files + sun azimuth), or brighter near motes.
- River ledges still faint; sky_noon streaks; meteor still forced only via QF_METEOR_SHOW (dev).
- Morning: cost submission, spec_scenes.py, round.json, finish_round (see the earlier Next list).

## Loop 4 (2026-10-26 00:45, bug-fix loop; critic notes in C:\qfb\shaderdev\r008\critic.json)
- Submitted golden_lit bisect 1026-004523-r008-um (um, um_gh0, um_du0, um_vb15, um_pbr0, um_all), spec specs/um.json.
- Next: boot fault (no terrain after first scenes in b1026000221), dust view, lake Fresnel/glint, ocean sun path, metals SSR.
- Boot fault: FrameBench SETTLE accepted "0 chunk updates" with no chunks loaded. Fixed (811df12, ce75ec7, eca88fd):
  place() loads 5x5 chunks + updatePlayerPertinentChunks; SETTLE waits for client chunks, re-teleports every 10 s,
  reports "incident no-terrain" which renderq drops (retry). New jar in C:\qfb\renderq\jars (old: .pre-terrain-20261026);
  built in worktree C:\qfb\wt-fb. Runner restarted to load batch.py.
- Shader edits (uncommitted until verified): gSsrOcc (r007 linear weight) for the water sun occlusion (ocean/lake path);
  lake F>=0.34 floor faded in over 10-40 m; metal env from composite SSR (metalReflection, QF_METAL_SSR), bent faces off
  with SSR; foliage PBR a2>=0.08 and sp cap 3 (the yellow oval = sun image on a smooth leaf top, absent in qh);
  cloud deep diffusion x0.30 at golden hour (cream wash); warm Mie aureole in skyRadiance.
- Dust candidate views dust_a..d appended to views-world-master.txt.
- Submitted 1026-005710-r008-un (un, un_dustdbg, un_met, un_night, un_clipmet, un_pbr), spec specs/un.json.
- golden_lit bisect um: QF_DUST 0 alone fixes it (78,61,18 -> 36,45,14; others no change). Cause: beam flips/dust counted samples in the last 2 blocks before the ground (shadow noise). Fix: freeAir gate in lightShafts. Verify job 1026-uo (uo: golden_lit, forest_golden, dust_a-d).
- un (b1026005719) rendered void after its first scene: the server-side updatePlayerPertinentChunks call broke chunk
  sending. Reverted (f81dc5d); kept the client terrain gate, no-terrain incident, and a bounce retry. Jar swapped again.
  Cancelled un/uo; resubmitted everything as 1026-010948-r008-up (up, up_dustdbg, up_met, up_night, up_clipmet, up_pbr),
  shader snapshot includes the freeAir golden_lit fix.
- up reviewed (sheets C:/qfb/shaderdev/r008/look/l4): terrain in every frame (gate works, no incidents). Night stills
  and meteor clip clean now. golden_lit still 72,58,17: freeAir was not enough (camera 20 m over the field), so gBeam
  now also needs >=12-30% shaded free air, and the dust haze phase is mostly forward. Ocean path unchanged by gSsrOcc
  (15-25% under qh down the column): added a second long lobe at low sun. Mie aureole 0.05 invisible: now 0.24/0.022.
  Oval is NOT the foliage spec (still there): bisect jobs in uq. Wash unchanged by cloud deep term. Metals: stripe gone.
  Dust: dust_a/dust_b are good views (beam across near air before trunks); near motes denser (x1.6) and 3.6x in beams.
- Submitted 1026-r008-uq (spec specs/uq.json): uq main + oval bisect (sun0,pbr0,du0,sh0,bo0) + night + clips + pbr.
- uq resubmitted as 1026-012403-r008-uq after cloud base tweak (golden base 0.16 exp(-od*0.6), under horizon 0.45).
- uq reviewed: golden_lit near ground 38,47,15 (FIXED, was 78,61,18). Oval bisect: only QF_DUST 0 removes it;
  ur_near/ur_far (QF_DUST_DBG 2/3, new dev modes): it is a NEAR-grid mote ~1 m from the eye, TAA-smeared into an oval
  (dust clip motion map shows such blobs drifting in arcs). Fix: air near motes fade in over 1.5-3.5 m.
  Far flakes now also need gBeam (specks over the sea/canopy in uq). Clips l4_{dust,met,wat}.webp in r008/clips.
  Meteor clip: 293 ms mean interval, write 789 ms/frame (night cap + full-res write): fine for a clip, noted.
- Submitted 1026-r008-us (final verify: us, us_dustdbg, us_met, us_clipdust, us_pbr, us_pbr0).
- us reviewed: oval gone on forest_golden, golden 37,47,15, terrain everywhere; dust_b still shows a near-mote oval ~4 m out -> fade 3-6.5 m. Verify 1026-r008-ut (ut, ut_clipdust).
- ut reviewed: dust_b near oval gone (3-6.5 m fade); the dust clip's motion map shows no stray blobs, but still few mote
  trails inside the beam (the beam haze shows). Committed 205d13c (shader + views). Clips: C:/qfb/shaderdev/r008/clips/l4_{dust,met,wat}.webp.
## Loop 4 result tags
- Clean-boot finals: us (golden_lit, lake_glitter, ocean_sunset, forest_golden, dust_a, dust_b), ut (forest_golden, dust_b,
  ocean_sunset; latest near-mote fade), us_met (night_sky, night_new), uq_clipmet, uq_clipwat, ut_clipdust, us_pbr/us_pbr0.
  No no-terrain incidents in up/uq/us/ut.
## Next
- The publish-cost run 1026-004242-r008-publish-cost uses the pre-loop-4 snapshot: cancel and resubmit with the current pack.
- Dust: denser/brighter motes inside beams (dust_b is the view); forest_golden cream wash (cloud deck) still there.
