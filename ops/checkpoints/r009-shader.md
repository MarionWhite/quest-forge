# r009 shader checkpoint (orchestrator, 2026-10-26)

Brief: ops/briefs/shader-round.md. Input: docs/design/shaders/feedback/r008.json, critic C:/qfb/shaderdev/r008/critic.json.
Start state: r008 live (loop 4, 205d13c). Nothing for r009 started; no renders submitted.
Owner overall: no drastic improvement; over budget on performance; wants optimisation or a helper so nothing kills anyone's game.

## Order of work
1. **Researcher first (parallel, no render):** meteor-shower note at docs/design/shaders/research/meteor-showers.md (brief item 10).
   Shader-dev does not touch meteors until it exists.
2. **Perf:** r008 publish costs: worst frame 4.6 ms High (budget 3.0), Low 1.32 (0.9), Potato 0.30 (0.4, OK). Find the top
   cost terms (cost run with per-option off tags), cut or gate them, and propose the "helper": an auto-tier or option-gating
   rule that drops to a cheaper preset by measured frame time. Default changes that alter the look go to ops/DECISIONS.md.
3. **Metals (HARD CONSTRAINT):** r008 measured metal shading 3.47 ms vs off 3.41 in that frame (+0.06), but the owner rates
   the look 2/5 and calls the cost very high. Rule: nothing that raises High or Low cost. Evaluate in a cost run first:
   reuse the SSR already computed for water/composite instead of a metal-only pass; early-out outside MAT_METAL pixels; a cheap
   fallback (sky gradient + horizon band, no extra taps). Iron needs a visible reflection; the emerald noise must go.
   Decide with numbers before writing shading code; if it cannot be free, ship the cheap version and say so.
4. Look fixes in the brief's order: dust motes (view dust_b), sun limb and core, cloud-over-sun occlusion, golden band + grazing
   light, forest cream wash, river clarity/ledges/glint, bluer underwater for non-swamp water, sky_noon smear.
5. Meteors from the research note.

## Critic fixes to carry ("listen to the critic")
- sun: uh/uj/p8: sharper limb, core ~1.5x hotter, wider warm Mie glow, longer brighter sun path on the water.
- golden-horizon: uf/p8: cream-peach band fading to lavender, warm grazing light on lit slopes, keep grass green.
- forest-light: p8: kill the cream wash, more canopy contrast against the gap.
- dust: p8clipdust: real motes, a few px each, drifting through the lit shaft. Note p8d0 shows "off" also removes the beam haze.
- river: p8: clearer water near the banks, lose the ledge stripes, add sun glint.

## Rules
- Cost-mode renders run after 08:00; night mode is shot jobs only. Use renderq; never launch a client.
- Verify every "already fixed" claim against frames. Resubmit publish-cost with the final pack.
- Write spec_scenes.py and round.json for r009 in C:\qfb\shaderdev\r009.

## Progress log
- 2026-10-26 17:48: meteor note not written yet (step 1 still open, researcher's job). Step 2 started: submitted
  renderq job **1026-174757-r009-cost-breakdown** (spec C:/qfb/shaderdev/r009/specs/r9-costbreak.json; 15 jobs, 80 scenes,
  ETA ~37 min). High tags: r8b base plus one tag per option off (r8xshaft, r8xdust (DUST+MOTES), r8xpbr, r8xbounce,
  r8xwaves (WAVES+FOAM+CAUSTICS), r8xrim, r8xaer (AERIAL+HAZE_HEIGHT), r8xgh, r8xflk (FLECKS+SUN_SPARKLE)) on
  ocean_sunset, golden_lit, forest_golden, dust_b, lake_glitter, river_noon. Low (preset 1, 1080p): r8lb, r8lxshaft,
  r8lxpbr, r8lxwaves, r8lxbounce on golden_lit, lake_glitter, biome_hills, ocean_sunset. Off baselines: r008 p8off/p8looff.
- 2026-10-26 (later): cost breakdown read and ranked; the table is in ops/journal/shaders.md. High: SHAFTS -1.84 ms mean
  (-2.50 max) and DUST+MOTES -1.48 (-2.30) dwarf the rest (WAVES -0.15, PBR -0.11, all others <=0.06). Low: SHAFTS -0.51,
  everything else <=0.06. Volumetrics are the whole budget problem. dust_b has no r8b base row.
- **Next:** find the shaft/dust march (grep VOLUMETRIC/SHAFT steps in shaders/QuestForge) and cut it: fewer steps plus
  dither/blue-noise jitter, half-resolution march, and dust computed inside the shaft loop (not its own pass). Submit a
  High/Low cost run against r8b/r8lb (after 08:00). Then draft the auto-tier helper: measured p50 above the tier budget
  (High 3.0, Low 0.9) drops to the next preset; first drop is shafts quality, then shafts off. Look-changing default
  edits go to ops/DECISIONS.md. Metal-path cost (QF_METAL_SSR, lighting.glsl:85) is not in this run; it goes in step 3's run.
- 2026-10-26 22:38: loops cut, commit **a651ede** (check_glsl: 0 errors, 48 stages x 5 presets). New option
  `QF_VOL_FAST` [0 1], default 1 (settings.glsl). Exact changes (always on): affine shadow-clip march (shadowClip/
  shadowClipDir/shadowRawClip in composite.glsl), the same for the mote inBeam taps, and the near mote walk starts 2.5 m
  out (flakes fade in from 3 m anyway). Lossy changes (QF_VOL_FAST 1 only): SHAFT_STEPS High 20->14, Med 12->10,
  Low 8->6; dust clumps on alternating steps by frame at 2x weight; Low (preset<=1) beam haze has no clumps (density 1);
  MOTE_STEPS -3 to match the later start; the whole mote walk is skipped when the shaft march found no shaded free air
  (gNoShade) and block light < 0.1. Submitted **1026-223822-r009-volfast-cost** (spec C:/qfb/shaderdev/r009/specs/
  r9-volfast.json; 4 jobs, 20 scenes; ETA ~22:49 if the owner is idle). Tags: r9vf / r9vf0 (High, QF_VOL_FAST 1/0) on the
  6 r8b scenes; r9lvf / r9lvf0 (Low 1080p) on the 4 r8lb scenes.
- **Next:** `renderq.py results 1026-223822-r009-volfast-cost`. Compare r9vf vs r9vf0 and r8b (High, budget 3.0) and
  r9lvf vs r9lvf0 and r8lb (Low, 0.9); log the table in ops/journal/shaders.md. Look-check forest_golden, dust_b and
  golden_lit crops (check_frames.py) for shaft banding/noise from 14 steps, and flakes lost to the gNoShade gate. If
  High is still over budget, try half-res shafts; Low will likely still be over 0.9 (shafts were 0.51 of 1.32), so the
  auto-tier helper draft (unchanged plan above) is next. QF_VOL_FAST 1 changes the look slightly: once the frames are
  checked, put "keep it as the default" in ops/DECISIONS.md.

- 2026-10-26 23:55 (look step, tex-golden artifacts): commit **4666aab** (composite.glsl; check_glsl 0 errors). Cost
  run 1026-223822 is still queued for 08:00 and snapshotted its pack at submit, so it measures a651ede, not this.
  Changes: (1) stair-steps: shaft march taps via shadowRawClipJ, jittered up to +-1 shadow texel per step (R2 sequence
  off the ign seed); (2) radial streaks: the golden-hour near-air switch (lit vs litFar by gBeam) now scales gBeam by
  smoothstep(-0.2,0.4,mu), so rays away from the sun all take litFar; (3) coins: root cause was the mote inBeam test,
  whose -p2 tap (near-vertical at low sun) sat under the grass, read as shade, and lit every flake near the ground.
  p2 now points up with one tap (3 taps, was 4: cheaper); near air flakes rw factor 2.6-1.3 -> 2.0-1.2.
  Shot render **1026-235508-r009-texgold-shot** (spec r9-texgold.json; tag r9tg: golden_lit, forest_golden, dust_b).
- 2026-10-27 00:20: r9tg left the rectangle in place. The bisect renders showed it was block light, not shadows (journal
  entry). Fix commit **cd1cfa7**: blockDayDamp() in lighting.glsl on surfaces and motes. Verify render
  **1027-001651-r009-texgold-shot2** (tag r9tg2): rectangle and warm patches gone, coins nearly gone (a few faint flakes),
  radial streaks much fainter, forest_golden/dust_b beams unchanged. **tex-golden step closed.** Still open from it:
  the faint diagonal streaks on golden_lit's shadowed field (not shafts: they persist with QF_SHAFTS 0; likely terrain
  sky/AO shading, low priority). Look change for the owner to see in r009: daytime torchlight outdoors is ~70% weaker.
- Cost: 4666aab + cd1cfa7 are neutral or cheaper (one mote tap fewer; mote-walk skip fires in daylight block light), but
  the queued 08:00 run **1026-223822** measures a651ede only. After reading it, resubmit r9-volfast.json (new tags,
  e.g. r9vf2/r9lvf2) with the current pack before publishing.
- **Next:** the brief's order from dust motes: dust_b ("real motes, a few px each, drifting through the lit shaft";
  bench-r9tg2-dust_b.png is the current state), then sun, cloud-over-sun, golden band, forest wash, river, bluer
  non-swamp underwater, sky_noon. Crop helper idea: scratchpad scripts are gone; rebuild with PIL (full frame 640x360 +
  native crops side by side).

## Hand-off from texture-dev (2026-10-26): owner's r008 "tex-golden: weird artifacting in all photos" is shader-side
Same artifacts in t8v0, t8v1, t8f64 (all three packs) and still in t9v1/t9v2c (r009 shader), so not textures. In golden_lit
(2560x1440): (1) the shaft haze ends in blocky stair-steps on shadow-map texels: a hard-edged lit rectangle over the grass,
native box 680,860,1000,1010 (zoom 2x nearest); (2) dark radial streaks fanning across the whole ground (anti-crepuscular
shafts lying on the terrain), visible in a half-size full frame; (3) under r009 the motes read as soft orange discs up to ~8 px
sitting on the grass ("coins"), box 640,792,1280,1224. r008's brown ground smear is gone in r009. Check these three in the
volfast look-check (shaft jitter/blue noise should break the stair-steps; mote size/brightness at distance).
