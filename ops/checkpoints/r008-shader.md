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
