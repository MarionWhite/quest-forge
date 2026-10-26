# Shaders journal (newest first)

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
