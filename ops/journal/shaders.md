# Shaders journal (newest first)

- 2026-10-28 16:40: **r012 shader scenes handed off** (C:\qfb\shaderdev012\spec_scenes.py, SHADERS-READY; 4 scenes:
  sunset-full, sun-glow 2x crops, sun-cloud, meteors; pack 4f9e553). Loop 2 (1028-151425): the glow shows once measured
  in display units with its own visibility (thin sunlit cloud over the disk counts): sun box 194.0 none / 196.0 default /
  197.4 strong, BSL 224 (clear disk); noon unchanged. Gold: ocean_sunset upper sky 154,133,116 (r011 154,121,122 lilac);
  shore_sunset barely moves (sun on the horizon). golden_lit near grass 40,56,19 (r011 69,67,40, r010 38,45,15). Lean
  meteors read as tapered hairlines, none at dusk. Costs (1028-151500, High 1440p): worst ocean_sunset 3.65 (r011 3.30):
  round 10's rays +0.30 there (Photon's +0.02), glow +0.06-0.09, gold +0.04, near air 0; Low 0.89, Potato 0.31; meteors
  2.94 both shapes. Gem SSR (QF_GEM_SSR) +0.18/+0.17/+0.05 ms, written into the texture track's gems scene.

- 2026-10-28: **r011 posted** (1553b04, 29 scenes via finish_round --publish). Rays scene moved to golden_lit (lake_glitter A looked like off; no p11r75 frame there, option dropped); pack scenes marked noCost. Checkpoint ops/checkpoints/r011-publish.md.

- 2026-10-28 09:20: **r011 shader scenes handed off** (be6b241; C:\qfb\shaderdev
011\spec_scenes.py, SHADERS-READY;
  3 scenes). Loop 3 read: rays invisible (+1-3 luma; Photon's term only adds light to a sky that already holds the lit
  air's glow); loop 4 QF_CREP_SHADE 0.5 dims that glow by the shadowed share of the air below the cloud base: wedges
  round the sun p5 -6 luma (0.75: -10, r010 -16). golden_lit near grass still lifted, 66,64,39 vs r010 40,45,15; at x1
  density (r11a1) already 62,63,35, so it is Photon's own evening Mie haze: stated on the Lab, a later item. Costs (High
  1440p, 1027-224601 + 1028-085424): atmosphere -0.12..+0.03, rays +0.00..+0.07 (r010 +0.14..+0.31); worst ocean_sunset
  3.28-3.30 (r010 3.31; sea/swamp-water views 3.01-3.16 over, as before); night_wide 2.99 for shower and storm (r010
  3.47 / 3.98). Low 0.86, Potato 0.30. Later: Conquest's sky/fog/lightmaps need shader-side ports (texture-dev note).

- 2026-10-27 22:47: **r011 Photon port, loops 1-3** (ada996a). Owner r010: "copy from the packs that are doing things
  right". Atmosphere: Angelica 2.2.33 parses raw TEXTURE_3D custom textures, so Photon's scattering LUT ships unmodified;
  offline check (r011/tools/atmo_sim.py) shows it is in our sky-view units (zenith 0.8-1.2x ours), so it fills prepare's
  sky-view tables at no per-pixel cost. With Photon's sun tint, horizon stretch and air fog: twilight is a lit blue hour
  (shore_dusk was near black); at 8 chunks Photon's fog was a third as thick as CR's horizon band (139,109,97 vs
  212,160,120) because its densities assume a 16-32 chunk view: land x sqrt(256/far), sky and reflections through 256
  blocks. Rays: Photon's march through a 64x64 cloud shadow map; loop 1 drew nothing (debug 15: ~1 % of the sky, the
  gain was 6x too low for our light units), now QF_CREP_I 0.3. Meteors: the sky cut into 96 (storm 240) wedges round the
  radiant, 3 slots per pixel instead of 24/40; loop 2 hairlines, longer, fainter, Milky Way on shower nights; matches
  the owner's photos in max-over-time sheets. Costs pending 1027-224601-r011-publish-cost (08:00).

- 2026-10-27 20:30: **r010 posted** (01b7fe4, --no-push; 21 scenes: 8 shader, 8 texture, 5 frills/crops). Costs from
  1027-193818-r010-publish-cost (done 20:04, 17/17 jobs). High p10 worst night_wide 3.47 (grazers), night_new 3.42,
  night_sky 2.88 (r9 2.46); sunset/water views 3.04-3.31, within 0.03 of r9. Clip p50s: grazers 3.43, storm 3.98
  (~0.034 ms per meteor slot). Low 0.89, Potato 0.31. Crepuscular rays (p10cr - p10): ocean_sunset +0.33 (3.64), lake
  +0.22, forest/dust +0.15, golden/noon +0.04; in the full frame they draw a clear fan above the sun, more than the
  "-7 % luma" suggested. Mint box (900-1460 x 560-900): p9 1107, **p10 0 px**. Procession (p10clipg2, radiant 45,
  PROC_P 9): one fireball dives steeply from the top edge with 2-3 fragments and vanishes in one frame (f107 -> f108),
  so not a procession: dropped from the Lab (meteors now A grazers, B storm, C r9). Critic (me, r010/critic.json):
  56 frames, mean 6.6 (shader 6.9); 8s for grazers, sunset, rays, gold, underwater_sun, beach, frills B, crop variants;
  "not yet: forest light needs a new view and technique". Two owner cost calls in DECISIONS (rays, meteor slots).

- 2026-10-27 19:45: **r010 shader work done, publish-cost run submitted** (1027-193818, specs/p10-cost.json; pack c542939).
  Meteors: Earth-grazers (3D tracks 88-118 km up, radiant 1-5 deg above the horizon) read as long thin level streaks with
  tapering wakes (r10i1c); style 1 default, 2 procession (unproven in loop 3's clip: it ran overhead, out of the crop;
  p10clipg2 tries radiant 45), 3 storm. Sunset mint: SSR fix 1107 -> 678 px; QF_SHALLOW_SUN (bed lit by the golden boost)
  was a wrong cause (ss0/1/2 692/661/686, now off); debug view 12 showed the wedge's "bed" was the sky: dR = 1, so
  colortex3 there is the horizon glow, and 32 blocks of reef water left mint (151,185,130). No bed in view -> behind = 0.
  Gold: METAL_FLOOR + vibrance floor took gold/stone 1.48 -> 1.74 (vanilla 1.82), blue clipped 61 % -> 0 %;
  QF_METAL_F0 (LabPBR 230-237 F0 table) G/R 0.941 -> 0.934, lime gone in crops. UW_VIS 2.0 (+41 % far contrast),
  RIVER_TINT 1 (water 51,79,63 -> 50,74,80). No visible change: SUN_CLOUD 2 (0.5 luma), DUST_LEAF 2 / SHAFTS 2 (1 luma).
  Crepuscular rays (16 taps, High-only) -7 % luma in the sun crop; cost from p10cr goes on the Lab. spec_scenes.py and
  round.json written (8 shader scenes + texture + frills). Next: critic, then publisher.

- 2026-10-27 08:55: **r009 posted** (ab4ada7, --no-push; 20 scenes: 11 shader + 9 texture). Costs from
  1027-020424-r009-publish-cost (done 08:41, 24/24 jobs), ms vs shaders-off of the same size:
  High p9 worst ocean_sunset 3.29 (r8 4.58); over 3.0: river_swamp 3.14, beach 3.08, swamp/ocean_swamp 3.04, biome_ocean
  3.03; the rest 1.88-3.00. Low p9lo worst 0.86 (r8 1.32, budget 0.9). Potato 0.29 (0.4).
  Budget lines on the 6 r8b views (High, ms saved when off): SHAFTS 0.62-0.85 (r8 1.84 mean), DUST+MOTES 0.30-1.03,
  WAVES 0-0.23, PBR 0.03-0.10. QF_VOL_FAST 0 adds +0.42 (forest_golden) to +1.46 (golden_lit) High and +0.41-0.50 Low;
  its look at sheet scale is the same (golden_lit, dust_b). Water views now carry the High overage.
  Critic (me, r009/critic.json): mean 6.5 over 22 frames, "not yet: motes in the beam". Dust clip motion map: leaf sway
  and beam shimmer only, no separable mote tracks (same as p8); the p9 shaft by the cliff is fainter than p8's, and with
  QF_DUST 0 the few motes show more (haze hides them). River: yellow stripes gone, but pale mint dashes on the ledge edges.
  Meteor clip: about 7 near-parallel streaks with heads at the lower ends, one radiant above the top right of the frame.
  Pre-post checks: terrain in all 22 frames, clips 1.1-2.9 MB, intro numbers filled. Texture options carry the new
  "noCost" flag (shot-mode t9* frames; finish_round.py skips them in the no-cost stop).

- 2026-10-27 02:04: r009 last night tries, then the freeze. Shot 1027-015510 (pinned exposure) put two ideas behind
  temporary toggles: an open-sky shaft veil cut to 0.5 on golden-hour rays through shaded air (forest_golden's cream sky
  round the gap 150.3 -> 147.9 R: noise; shaded share on sky rays is too small to key on), and raw shadow taps for mote
  visibility (dust_b lower shaft, DBG 1: 43.0 -> 40.7 R, no new flakes: the filtered vis is not why that half is empty).
  Both reverted; both stay open for r010. Pack frozen at 76fb7ef. The stale volfast cost run 1026-223822 (a651ede) was
  cancelled, and **1027-020424-r009-publish-cost** (p9-cost.json, 112 scenes, High/Low/Potato + off baselines + per-option
  budget lines + QF_VOL_FAST 0) was submitted for 08:00. Next: results table, critic, publisher.

- 2026-10-27 01:52: r009 forest wash, canopy veil (0c72440). New dev pin QF_EXPO_PIN (log2 QF_EXPO_PIN_LOG) so A/B frames
  share one exposure. With it pinned at 1.0, the 01:28 pending-dust idea (keep dust only where the ray goes on into shade)
  did nothing (canopy R 36.5 -> 35.6; rays onto leaves cross shaded air too), so it was reverted. What worked is cutting
  the haze by what the ray hits: dustL x0.4 when the pixel is foliage (g1 is already fetched, so no cost). Canopy 36.5 -> 28.4 R
  (dust off 20.9), green kept, no outline at the leaf/sky edge, dust_b path beam -4 %. Part (b), the cream sky veil round the
  gap, is still open.

- 2026-10-27 01:45: r009 meteors (513fa7d, lib/sky.glsl), built from docs/design/shaders/research/meteor-showers.md
  for the owner's r008 note ("isn't just shit flying in every direction"). r008 had a radiant already, but it sat mid-view in
  night_sky, so the clip was a starburst of equal-length streaks at every heading. Now: random bearing, 25-60 deg up per
  night, slot use ~ sin(altitude); starts 10-100 deg out (cos-uniform, so most far out), length (0.22-0.50 rad)*sin(d), so
  meteors near the radiant are short; brightness min(0.6/u, 8) (P(>b) ~ 1/b, r ~ 2.5), colour saturates with brightness, white
  head; trains only above 2.5; fireball (u<0.012) head glow. Same 12-slot loop on night sky pixels: no added cost. r9mclip:
  ~5 streaks in 90 frames, all moving left/down-left (head tracked frame by frame), so the view reads as one direction.
  The pinned QF_METEOR_SHOW pair runs the same way. Caught a fireball in r9mt night_new: soft ~90 px halo, streak fat
  under bloom; for the critic to judge. Skipped: sporadics, persistent trains of 20-60 s (the ~4 s slot cycle can't hold
  them), sky flash.

- 2026-10-27 01:31: r009 river, underwater, sky_noon, forest wash retry (shot renders only, all ALU-only or reverted).
  River (critic p8): the "ledge stripes" were yellow-green grass tops seen through teal water. 85dab7a pulls the bed's
  hue to the water's teal at its own luma (mix 0.6*river) and eases the down-path filter 4.0 -> 3.0: in r9rv the near
  stripes read as teal bed texture, the far yellow dashes are gone, the bed is a little clearer. No glint: river_noon's
  sun is overhead/behind, so none is physically in frame. Underwater (owner r008 "more blue for the other water
  types"): first try (volume only) barely moved, because the shafts carried the green; 85dab7a gives the volume and the
  shafts shared eye coefficients (non-swamp: g/b absorption swapped at 0.8, scatter x(0.75,0.8,1.8)). r9uw is blue-teal
  with blue shafts; swamp keeps its green by construction (river_swamp above water unchanged).
  sky_noon radial smear: a 380-block march segment plus 0.5 dt in-cloud steps (r9sf) matched the same-pack baseline (r9sb)
  exactly, so it is not along-ray undersampling. Cause is the shape: the base field is 2D and runs through the 170-block
  slab, and columns seen from below fan out from the zenith. A fix needs height-varying base shape, likely one more noise
  fetch per sample (not cost-neutral), so it was reverted and left for a cost decision.
  Forest wash retry: (b) open-sky veil mix(0.8, 0.5, gBeam*gh) did nothing beyond run noise (gBeam is low on sky rays
  round the gap); (a) dust counted only ahead of shaded free air (else 0.35) brightened the whole frame instead (canopy
  46->50, sky 175->190, likely exposure), and dust_b was unchanged. Both reverted. Next idea for (a): the exposure meter
  compensates whatever the haze loses, so pair any haze cut with a fixed-exposure A/B (or read prepare.glsl's meter) first.

- 2026-10-27 01:07: r009 cloud-over-sun, grazing light, forest wash (shot renders only, all cost-neutral).
  Cloud-over-sun (owner r008 sunset-full): cloudMarch's far-cloud melt (fade ~0.1 at a low sun) also cancelled the slab's
  transmittance on the disk, so a low sun shone whole through the wisps over it. 25e9263: skyRadiance adds the disk after
  the clouds, times gCloudTd = mix(1, T, smoothstep(0.012, 0.03, dir.y)) from cloudMarch (QF_CLOUDS 2). r9cs (T^2) and
  r9ct (T) look alike: the slab is dense where ocean_sunset's sun sits, so the sun now sets behind that cloud with a
  crescent under its base and the aureole kept. The critic's "sun form" is judged on the sky views from now on.
  Grazing light (critic p8 golden_lit): 20331ee, at golden hour up-facing lit faces take diffuse >= 0.7*goldenHour;
  the shadow map still gates. A 7.9 deg sun throws ~7-block shadows behind every terrace step, so only the strips
  between turn gold: ridge bands +4..+6 R (r9gy vs r9do), near field 41.9,46.7,14.7 (no olive). 0.32 (r9gz) was unseen.
  Forest cream wash (critic p8 forest_golden), not fixed; bisects: QF_SHAFTS 0 takes the right canopy (box x 1900-2500,
  y 300-700) 47,51,7 -> 19,47,5 and turns the sky round the gap neutral; QF_AERIAL 0 ~+10 only; QF_DUST 0 canopy -> 31,47,5
  with the sky unchanged. So the canopy veil is mostly dust haze (dustL) and the cream sky is the shafts' open-sky veil
  (lit *= 0.8 at dist >= far). Tried and reverted: (1) keepNear = gBeam*smoothstep(0.30,0.60,shadedAir) on the near-air
  switch, no effect (r9fw); (2) dustL *= mix(0.35,1,smoothstep(8,40,dist)) on hits, canopy 47 -> 39 but dust_b's
  lit beam over the path visibly weaker (r9fx), a regression on the owner's lowest-rated ask.

- 2026-10-27 00:44: r009 sun step. The p8 critic already rated the disk crisp with a real warm aureole (the limb/core
  asks were uh's, done in r008 loop 3); the open ask was the water path (77 luma vs r007 qw 86). b6b26f7: the long
  low-sun lobe in shadeWaterAbove is wider (a2b x3.2, was 2.2) and brighter (0.80, was 0.30), and keeps sqrt(balance)
  near the camera. Constants only, no cost. Shot renders 1027-003639 (r9sn, weight 0.44: only +5-10 %) and 004022 (r9so):
  ocean_sunset path luma (x 1140-1300, 120-row bands from y 760) 127->133, 69->80, 45->53, 37->45, 30->35, 25->25 against
  r9dm; off-path water unchanged; lake_glitter unchanged (sun behind the cliff). Not done: the dark navy open water at
  sunset (critic p8). It stays open.

- 2026-10-27 00:35: r009 dust motes (dust_b, critic p8clipdust), shot renders 1027-002247 (r9dm, r9dm1 = QF_DUST_DBG 1),
  002705 (r9dn, r9dn1), 002955 (r9dv1 = DBG 1 + QF_VOL_FAST 0), 003222 (r9do). Three commits, all cost-neutral or cheaper:
  ca40184 far flakes gated per mote (shade on BOTH sides across the light, 2 taps, was 3 + gBeam; gBeam is dithered per
  pixel/frame and with 14 shaft steps flickered under every flake, so TAA kept none); c209810 near air flakes keep a 1.7
  size factor past 8 m (~4 px; tex-golden's 1.2 left ~1 px dots); bbf3b79 flakes fade over the last 1.5 m in front of a
  surface (were last 18% near / 8 m far). Result: motes now drift in dust_b's upper shaft (against the cliff); ocean_sunset
  clean (r8b's orange specks over the sea gone, none added); golden_lit no coins back; forest_golden unchanged.
  Open: the shaft's lower half (box 1460,560,1900,1160, over the corridor grass) has no sunlit flake even in DBG 1, with or
  without QF_VOL_FAST; not size, not the end fade, not the fast-path skip. Remaining suspects: the mote vis
  (sampleShadow, filtered + normal offset) disagreeing with the march's raw shadowtex0 taps, or that haze's lit air sits
  past the near grid's reach (25 cells from 2.5 m). Next diagnostic: a debug view of the first lit free-air distance on
  those pixels, and DBG 1 with vis from shadowRaw instead of sampleShadow.

- 2026-10-27: r009 tex-golden artifacts (texture-dev handover), shot renders 1026-235508 (r9tg), bisects 1027-000345
  (debug view 7), 000618 (shafts/dust/bounce off), 000950 (view 5, clouds off), 001317 (views 2, 3), verify 001651 (r9tg2).
  The stepped "lit rectangle" was none of shafts, dust, bounce, clouds or the sun shadow (view 5: the whole field is in the
  hill's shadow). View 3 showed block light (colortex2.r) up to ~1 in soft patches over the field: light sources in the
  grass, the stair-steps being vanilla's per-block falloff, and the motes took that block light (Eblock) and glowed as the
  orange "coins". Fix cd1cfa7: blockDayDamp(skyLight) = 1 - 0.7*smoothstep(-0.05,0.10,sunY)*sky^2 on surfaces and motes
  (the mote-walk skip uses it too, so that field now skips the walk). r9tg2: rectangle and warm patches gone, coins nearly
  gone, radial streaks much fainter. forest_golden and dust_b beams unchanged. Also in 4666aab (did not cure the rectangle
  alone, kept): shaft taps jittered +-1 shadow texel, the golden-hour near-air switch only towards the sun, the mote beam
  test's downward tap removed (it sat under the grass at low sun; 3 taps, was 4), near flakes 2.6-1.3 -> 2.0-1.2.

- 2026-10-26: r009 cost breakdown (renderq 1026-174757, p50 ms, delta = base minus option-off; base r8b/r8lb were cached).
  High (2560x1440, base 2.8-5.0 ms, off 0.35-0.51): SHAFTS -1.84 mean / -2.50 max; DUST+MOTES -1.48 / -2.30;
  WAVES+FOAM+CAUSTICS -0.15 / -0.30; PBR -0.11 / -0.19; AERIAL+HAZE -0.06; GOLDEN_HOUR -0.06; BOUNCE -0.04; RIM -0.03;
  FLECKS+SPARKLE ~0. Low (preset 1, 1080p, base 1.51-1.74, off 0.42-0.52): SHAFTS -0.51 / -0.69; WAVES -0.06; PBR -0.04;
  BOUNCE -0.01. The volumetric pair (shafts + dust) is about 3.3 of High's ~4.7 ms; everything else together is under 0.5.
  They probably share the march (critic: dust off also kills beam haze), so the two deltas overlap and don't add up.
  dust_b has no base row in r8b, so it is missing from the table. Next: cut march steps or resolution, gate dust on shafts,
  then the auto-tier helper.

- 2026-10-26: r008 posted (006fe9b, --no-push) from cost run 1026-015851 (39/39 done, terrain in every frame); critic 6.3,
  not yet a leap (motes in beams; iron reflection; ocean sun path; forest_golden wash; sky_noon deck); 10 p8 frames 3.5-4.6 ms > 3.0.

- 2026-10-26: r008 loop 4, bug fixes (205d13c; renders um bisect, up, uq, ur, us, ut; sheets C:\qfb\shaderdev
008\look\l4).
  Boot fault: FrameBench settled on "0 chunk updates" with no chunks; it now waits for client chunks, retries, and renderq drops
  no-terrain scenes (f81dc5d, eca88fd; new jar). golden_lit olive = QF_DUST's beam test on ground shadow noise: 37,47,15 now.
  forest_golden oval = a TAA-smeared dust mote ~1-4 m out: gone. Metals reflect via SSR (stripe gone). Lake near Fresnel faded,
  sun path +5%, warm aureole. Open: motes inside beams still sparse in dust_b's clip; forest_golden cream wash; the queued
  publish-cost run 1026-004242 renders the pre-loop-4 shader and must be resubmitted.
- 2026-10-26: r008 prepared for publishing: spec_scenes.py (14 shader scenes with 4 motion clips, then the 11 texture scenes) and
  round.json in C:\qfb\shaderdev
008; one cost submission 1026-004242-r008-publish-cost (p8*/c8* + baselines) waits for 08:00.
  Shader frames come from that run (critic notes still needed); texture frames stay t8*, costs from c8*. Lab footer credits Faithful/VNR.
- 2026-10-26: r008 loop 3 (ef42eec; renders uj/uk/ul). Fixed: crisp sun limb, no glare disk over leaves, sky colour in the calm lake,
  river grey cloud patch, forced meteor stills (QF_METEOR_SHOW). Partial: metals show a horizon line, beam dust a few flakes.
  Open: golden_lit olive ground (shafts/aerial/amber ruled out), river ledges faint, sky_noon streaks. One boot lost terrain after forest_golden.
- 2026-10-25: r007 answered (issue #11). r008 started on the new render queue. Before this date, the full history is in
  `C:\qfb\shaderdev\NEXT.md` (PC only) and the posted rounds `site/shaders/rounds/r000-r007.json`.
