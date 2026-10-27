# Shaders journal (newest first)

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

- 2026-10-26: r008 loop 4, bug fixes (205d13c; renders um bisect, up, uq, ur, us, ut; sheets C:\qfb\shaderdev008\look\l4).
  Boot fault: FrameBench settled on "0 chunk updates" with no chunks; it now waits for client chunks, retries, and renderq drops
  no-terrain scenes (f81dc5d, eca88fd; new jar). golden_lit olive = QF_DUST's beam test on ground shadow noise: 37,47,15 now.
  forest_golden oval = a TAA-smeared dust mote ~1-4 m out: gone. Metals reflect via SSR (stripe gone). Lake near Fresnel faded,
  sun path +5%, warm aureole. Open: motes inside beams still sparse in dust_b's clip; forest_golden cream wash; the queued
  publish-cost run 1026-004242 renders the pre-loop-4 shader and must be resubmitted.
- 2026-10-26: r008 prepared for publishing: spec_scenes.py (14 shader scenes with 4 motion clips, then the 11 texture scenes) and
  round.json in C:\qfb\shaderdev008; one cost submission 1026-004242-r008-publish-cost (p8*/c8* + baselines) waits for 08:00.
  Shader frames come from that run (critic notes still needed); texture frames stay t8*, costs from c8*. Lab footer credits Faithful/VNR.
- 2026-10-26: r008 loop 3 (ef42eec; renders uj/uk/ul). Fixed: crisp sun limb, no glare disk over leaves, sky colour in the calm lake,
  river grey cloud patch, forced meteor stills (QF_METEOR_SHOW). Partial: metals show a horizon line, beam dust a few flakes.
  Open: golden_lit olive ground (shafts/aerial/amber ruled out), river ledges faint, sky_noon streaks. One boot lost terrain after forest_golden.
- 2026-10-25: r007 answered (issue #11). r008 started on the new render queue. Before this date, the full history is in
  `C:\qfb\shaderdev\NEXT.md` (PC only) and the posted rounds `site/shaders/rounds/r000-r007.json`.
