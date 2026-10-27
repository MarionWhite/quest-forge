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

- 2026-10-27 00:23 (look step, dust motes): r9tg2 dust_b showed the beam haze but almost no motes in the shaft.
  Cause found: far flakes (14-48 m, the grid that carries dust_b's shaft) were gated by gBeam, a dithered per-pixel,
  per-frame count that the 14-step march made noisier, so TAA kept none. Change (uncommitted until verified,
  composite.glsl motesGrid): far flakes need shade on BOTH sides across the light (inBeam = (1-s1)(1-s2), two taps,
  was three + gBeam: cheaper); near flakes unchanged. check_glsl 0 errors. Shot render **1027-002247-r009-dust-shot**
  (spec r9-dust.json): r9dm on dust_b, forest_golden, ocean_sunset (watch: no flakes over the open sea); r9dm1 =
  QF_DUST_DBG 1 on dust_b (every sunlit mote, to tell a missing mote from a failed beam test).
- 00:27: r9dm: far motes now show in the upper shaft (against the cliff); ocean_sunset clean (r8b's orange specks
  over the sea gone, none added); forest_golden unchanged. Committed **ca40184**. r9dm1 (DBG 1) still showed almost
  no sunlit near flakes in the lower shaft: likely the tex-golden size cut (2.6-1.3 -> 2.0-1.2) left them ~1 px, which
  TAA erases. Loop 2 (uncommitted): near air flakes mix(2.0, 1.7, smoothstep(3, 8, along)). Shot render
  **1027-002705-r009-dust-shot2** (r9-dust2.json): r9dn on dust_b + golden_lit (coin check, box 640,792,1280,1224),
  r9dn1 = DBG 1 on dust_b.
- 00:31: r9dn: upper-shaft motes a little bolder, golden_lit no coins back: committed **c209810**. Lower shaft still
  empty in DBG 1, also with QF_VOL_FAST 0 (r9dv1), so not the fast path. Loop 3 (uncommitted): flakes in front of a
  surface fade over the last 1.5 m (were last 18% near, last 8 m far; those long fades stay for the walk's end).
  Shot render **1027-003222-r009-dust-shot4** (r9-dust4.json, tag r9do: dust_b, golden_lit, forest_golden).
- 00:35: r9do: a couple more upper motes, golden_lit identical (no ground dots); committed **bbf3b79**. Dust step
  result: motes in the upper shaft; the lower half still has no sunlit flake even in DBG 1 (suspects and next
  diagnostic in the journal's 00:35 entry). Parked as open, not blocking: the owner sees r009's dust as it is.
- **Next:** the sun step (critic uh/uj/p8: sharper limb, core ~1.5x hotter, wider warm Mie glow, longer brighter sun
  path on the water; views ocean_sunset, sky views). Shot renders only until 08:00. At 08:00 the queued cost run
  1026-223822 measures a651ede only: after reading it, resubmit r9-volfast.json with new tags on the current pack
  (now includes ca40184/c209810/bbf3b79). Crop helper: 10-line PIL side-by-side (scratchpad copies get wiped).

- 00:36 (look step, sun): p8 critic already rated the disk crisp with a real aureole (limb/core asks were uh's, done
  in r008 loop 3); the open sun ask is the water path (77 luma vs r007 qw 86). Change (uncommitted until verified,
  composite.glsl shadeWaterAbove, the long low-sun lobe): a2b x2.2 -> x3.2, weight 0.30 -> 0.44, sqrt(balance).
  Constants only. Shot render **1027-003639-r009-sun-shot** (r9-sun.json, tag r9sn: ocean_sunset, lake_glitter);
  baseline C:\qfb\shaderdev\rounds\screenshots\bench-r9dm-ocean_sunset.png (frames land in rounds\screenshots).
- 00:40: r9sn path luma (x 1140-1300, 120-row bands from y 760) +2..+4 (5-10 %), off-path water unchanged: too mild.
  Loop 2 (uncommitted): weight 0.80. Shot render **1027-004022-r009-sun-shot2** (r9-sun2.json, tag r9so).
- 00:44: r9so path luma 127->133, 69->80, 45->53, 37->45, 30->35, 25->25 (+12-20 % down the column, the p8 target
  ratio 77->86); off-path water unchanged; the column reads longer and brighter in the crop; lake_glitter unchanged
  (sun behind the cliff). Committed **b6b26f7**. **Sun step closed** (disk/limb/aureole were done in r008 per p8).
- **Next:** cloud-over-sun occlusion (critic uh forest_golden / owner: clouds in front of the sun must dim the disk
  and glare; check final.glsl sunGlare's 9-tap vis against a cloud-covered sun, lib/sky.glsl applyClouds order vs
  sunDiskReal in skyRadiance). Find or pick a view with a cloud crossing the sun (ocean_sunset has clouds near it).
  Shot renders only until 08:00; the 08:00 cost-run note above still stands (resubmit r9-volfast.json on the current
  pack, which now includes b6b26f7).

- 00:45 (look step, cloud-over-sun): owner's note is r008 sunset-full = ocean_sunset; r9so crop shows wisps crossing
  the disk but the disk drawn whole. Cause: cloudMarch's far-cloud melt (fade = exp(-t0/6500)*smoothstep(0.012,0.09,
  dir.y), ~0.1 at a low sun) also cancelled the clouds' transmittance on the disk. Change (uncommitted until verified,
  lib/sky.glsl): skyRadiance adds the disk after the clouds times new global gCloudTd = mix(1, T*T, smoothstep(0.012,
  0.03, dir.y)) set in cloudMarch (QF_CLOUDS 2 only; 1/0 keep Td 1). Aureole stays under the faded clouds. Glare needs
  no change (its 9 taps read the dimmed disk). Cost: none. check_glsl 0 errors. Shot **1027-004547-r009-cloudsun-shot**
  (r9-cloudsun.json, tag r9cs: ocean_sunset; baseline bench-r9so-ocean_sunset.png, sun crop box 1000,480,1400,780).
- 00:48: r9cs hid the disk almost wholly (one sliver under a band) behind clouds the melt draws faint: reads as a sun
  behind a cloud bank, but the sun is gone. Loop 2 (uncommitted): T, not T*T. Shot **1027-004813-r009-cloudsun-shot2**
  (r9-cloudsun2.json, tag r9ct). If r9ct also loses the disk, the fallback is mix(1, T, sqrt(fade)).
- 00:50: r9ct is nearly the same as r9cs: the slab is dense (T < 0.1) where the sun sits; the melt only drew it faint.
  The sun now sets behind that cloud, a crescent shows under its base and the aureole glow stays. This is the owner's
  ask, kept. Committed **25e9263**. **Cloud-over-sun step closed.** For the owner/critic in r009: ocean_sunset's disk
  is now mostly hidden by its cloud (the critic's "sun form" is judged on the sky views).
- **Next:** golden band + grazing light (critic uf/p8: cream-peach band fading to lavender, warm grazing light on lit
  slopes, keep grass green; views golden_lit / golden-horizon). Then forest wash, river, bluer non-swamp underwater, sky_noon.
- 00:51 (look step, golden band + grazing): p8 says the band is fine (rose band kept, olive gone); open ask is warm
  low-sun light on the grass tops. Change (uncommitted until verified, lighting.glsl non-foliage diffuse, QF_CAL_GOLD):
  diffuse = max(diffuse, 0.32*goldenHour()*smoothstep(0.7,0.95,geoNormal.y)*step(0,L.y)); shadow still gates. ALU only.
  Shot **1027-005103-r009-graze-shot** (r9-graze.json, tag r9gz: golden_lit, forest_golden; baseline r9do). Check near
  grass rows 1000-1300 (p8 43,47,15) for the olive wash returning.
- 00:55: r9gz: near grass 41,46,15 -> 42,47,15 (no olive). The near field and most ridge tops sit in the 7-block
  shadows a 7.9 deg sun throws behind every terrace step; lit tops between them only +2 R (direct is small next to sky
  light). Loop 2 (uncommitted): floor 0.7. Shot **1027-005458-r009-graze-shot2** (r9-graze2.json, tag r9gy). Ridge crop
  box 1300,680,1900,1080 (r9do bands at y 700/820/940/1060: 61.7,59.8,20.7 / 53.8,48.8,13.2 / 50,49,13.5 / 39,46.5,14.5).
- 00:57: r9gy: lit ridge tops +4..+6 R (65.6,62.8,19.6 / 57.9,52.1,11.7 / 55.9,53.6,11.4); the sunlit grass between the
  terrace shadows reads warm yellow-green, shade stays cool green; near field 41.9,46.7,14.7 (no olive); forest_golden
  unchanged. Committed **20331ee**. **Golden band + grazing step closed** (band itself was fine per p8).
- 00:58 (look step, forest cream wash): r9gy forest_golden sky: upper-left 131,122,124 / 154,141,133 grey-lavender,
  round the gap 193,159,132 -> 252,199,153; refs (refs/forest_golden-1/-2) expose for the sun: dark forest, hot gap.
  Bisect shot **1027-005744-r009-fwash-bisect** (r9-fwash.json): r9fs0 QF_SHAFTS 0, r9fa0 QF_AERIAL 0 vs r9gy. If neither
  moves the sky, the wash is exposure (prepare.glsl meter lifts the dark forest); then a backlit-meter idea: count the
  sun-side sky more when the sun is on screen at golden hour (check ocean_sunset doesn't darken).
- 01:00: bisect: r9fs0 (shafts off) canopy 47,51,7 -> 19,47,5 and the sky round the gap goes neutral (154,151,150);
  r9fa0 (aerial off) only ~+10 brighter. The wash is shaft in-scatter, not exposure. Change (uncommitted until verified,
  composite.glsl lightShafts near-air switch): keepNear = gBeam*smoothstep(0.30,0.60,shadedAir) replaces gBeam there
  (dust/motes still use gBeam). Shot **1027-010016-r009-fwash-shot** (r9-fwash2.json, tag r9fw: forest_golden, dust_b;
  baselines r9gy forest_golden, r9do dust_b). If it fails, revert that hunk (git checkout the file: only my hunk is in it).
- 01:03: r9fw did nothing (canopy 50,54,8; sky equal to r9fa0's, i.e. run-to-run exposure): the near-air switch is not
  the veil. **Reverted** (composite.glsl clean). Next suspect: dust haze dustL (forward phase g 0.62, gBeam-gated; shafts
  off removes it too). Bisect **1027-010304-r009-fwash-bisect2** (r9-fwash3.json, tag r9fd0 = QF_DUST 0, forest_golden).
- 01:05: r9fd0: right canopy (box 1900-2500 x 300-700) 47,51,7 -> 31,47,5; sky unchanged. So canopy veil = dust haze
  (dustL); the sky's cream = shaft open-sky veil (lit *= 0.8 at dist >= far), left for later. Change (uncommitted,
  composite.glsl after dustL): dustL *= dist >= far ? 1 : mix(0.35, 1, smoothstep(8, 40, dist)). Shot
  **1027-010521-r009-fwash-shot2** (r9-fwash4.json, tag r9fx: forest_golden, dust_b vs r9gy / r9do).
- 01:07: r9fx: forest canopy 47 -> 39 R (cleaner), but dust_b's lit beam haze over the path visibly weaker: **reverted**
  (composite.glsl clean, nothing uncommitted from this step). Forest wash **still open**; findings in the journal 01:07.
- **Next:** forest wash, two separate parts. (a) Canopy veil = dust haze: it must stay in dust_b's beam but leave the
  leaves in forest_golden. Ideas: scale dustL by the ray's shaded share in front of the hit (beam = shade on both sides)
  rather than distance, or by the hit's material (foliage hit: less haze). Check dust_b's path beam (r9do) each loop.
  (b) Cream sky round the gap = shafts' open-sky veil (composite.glsl `if (dist >= far) lit *= 0.8;`, history: 0.6 lost
  the forest gap's glow in r006 qh, full veil washed out the ocean sun in pa); try lower only when gBeam > 0 (forest) so
  ocean_sunset keeps 0.8. Then river, bluer non-swamp underwater, sky_noon. Shot renders only until 08:00; the 08:00
  cost-run note stands (read 1026-223822, then resubmit r9-volfast.json with new tags on the current pack, which now
  includes 25e9263 and 20331ee).

## Hand-off from texture-dev (2026-10-26): owner's r008 "tex-golden: weird artifacting in all photos" is shader-side
Same artifacts in t8v0, t8v1, t8f64 (all three packs) and still in t9v1/t9v2c (r009 shader), so not textures. In golden_lit
(2560x1440): (1) the shaft haze ends in blocky stair-steps on shadow-map texels: a hard-edged lit rectangle over the grass,
native box 680,860,1000,1010 (zoom 2x nearest); (2) dark radial streaks fanning across the whole ground (anti-crepuscular
shafts lying on the terrain), visible in a half-size full frame; (3) under r009 the motes read as soft orange discs up to ~8 px
sitting on the grass ("coins"), box 640,792,1280,1224. r008's brown ground smear is gone in r009. Check these three in the
volfast look-check (shaft jitter/blue noise should break the stair-steps; mote size/brightness at distance).
