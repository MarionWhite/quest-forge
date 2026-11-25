# r011 publish checkpoint (2026-10-28): STOPPED at finish_round step 1 (exit 3)

## Done
- C:/qfb/shaderdev/r011/spec_scenes.py edited (backup spec_scenes.py.pre-publish): merges staytrue_scenes.json (5) and
  packs_scenes.json (21) after the 3 shader scenes, attaches critic.json notes (tag/scene or crop/<file>); intro now has the
  two method sentences; rays scene moved to golden_lit (A p11r, B p11cr0 off, C p10cr round 10's rays). The stronger
  p11r75 option was dropped: it has no golden_lit frame (only ocean_sunset, lake_glitter, shore_sunset, forest_golden).
- Dry run `finish_round.py C:/qfb/shaderdev/r011` loads and merges fine.

## Blocked
Exit 3: critic notes missing for the two new rays frames:
- p11cr0/golden_lit  (bench-p11cr0-golden_lit.png)
- p10cr/golden_lit   (bench-p10cr-golden_lit.png)
Contact sheet: C:/qfb/shaderdev/r011/critic-todo-1.jpg. Add both to r011/critic.json, then re-run, then --publish.

## Left
publish, verify r011.json 200, Edge screenshot, BOARD + journal, git log origin/main..main, push.
