# r009 publish checkpoint (2026-10-27): DONE except push

Pattern: ops/checkpoints/r008-publish.md. Render 1027-020424-r009-publish-cost done 08:41:53, all 24 jobs done.

## Done
- Costs: High p9 worst ocean_sunset 3.29 (r8 4.58), water views 3.03-3.14 over 3.0; Low 0.86; Potato 0.29. Table in
  ops/journal/shaders.md (2026-10-27 08:55).
- C:/qfb/shaderdev/r009/spec_scenes.py (11 shader + 9 texture scenes) and round.json written. Owner questions:
  QF_VOL_FAST default ("performance"), sun behind cloud ("sun-cloud"), daytime torchlight ("golden"), sky_noon cost
  ("clouds"); also in ops/DECISIONS.md "Shaders".
- Critic: C:/qfb/shaderdev/r009/critic.json, 22 notes + _r009_publish_summary (6.5, "not yet: motes in the beam").
  Texts edited to match frames (dust motes, river mint dashes, pinned meteor shows only one).
- Pre-post checks passed: terrain in all 22 frames; clips 1.1-2.9 MB; meteor max-minus-median map = ~7 near-parallel
  streaks from one radiant above the top right; OVER BUDGET lines printed (sunset-full/A 3.29, water-check A-D 3.04-3.14).
- `finish_round.py C:/qfb/shaderdev/r009 --publish --no-push` -> commit **ab4ada7** (r009.json, index.json, r008 closed).
- finish_round.py: "noCost" option flag (texture t9* shot frames have no cost); committed with the ops files.

## Left for the orchestrator
- `git log origin/main..main`, push; check site/shaders/rounds/r009.json returns 200; Edge screenshot into r009\look\.

## Open for r010 (shader track)
Motes in the beam (none separable; haze hides the few there are), forest cream sky round the gap, river ledge-edge
dashes, High still 0.3 ms over on water views, noon-cloud shape (+1 fetch), metals (cheap reflection, step 3 not done).
