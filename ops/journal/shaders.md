# Shaders journal (newest first)

- 2026-10-26: r008 prepared for publishing: spec_scenes.py (14 shader scenes with 4 motion clips, then the 11 texture scenes) and
  round.json in C:\qfb\shaderdev008; one cost submission 1026-004242-r008-publish-cost (p8*/c8* + baselines) waits for 08:00.
  Shader frames come from that run (critic notes still needed); texture frames stay t8*, costs from c8*. Lab footer credits Faithful/VNR.
- 2026-10-26: r008 loop 3 (ef42eec; renders uj/uk/ul). Fixed: crisp sun limb, no glare disk over leaves, sky colour in the calm lake,
  river grey cloud patch, forced meteor stills (QF_METEOR_SHOW). Partial: metals show a horizon line, beam dust a few flakes.
  Open: golden_lit olive ground (shafts/aerial/amber ruled out), river ledges faint, sky_noon streaks. One boot lost terrain after forest_golden.
- 2026-10-25: r007 answered (issue #11). r008 started on the new render queue. Before this date, the full history is in
  `C:\qfb\shaderdev\NEXT.md` (PC only) and the posted rounds `site/shaders/rounds/r000-r007.json`.
