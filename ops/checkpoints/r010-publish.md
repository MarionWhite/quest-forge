# r010 publish checkpoint (2026-10-27): DONE except push

Pattern: ops/checkpoints/r009-publish.md. Render 1027-193818-r010-publish-cost done 20:04:55, all 17 jobs done.

## Done
- Step 1 checks (scratchpad scripts, wiped with the session):
  - Mint wedge (p10-ocean_sunset box x900-1460 y560-900, G>R+5 & G>B+5): p9 1107 px, r10l2 686, **p10 0** (p10cr 0). Gone.
  - p10clipg2 (procession, radiant 45, PROC_P 9): one fireball dives steeply from the top edge with 2-3 fragments
    (f070-f107) and vanishes in one frame (f108: 6591 -> 38 bright px). Not a procession: **option dropped** from the
    meteors scene, said so in the question. Meteors now A grazers (p10clipg1), B storm (p10clipg3), C round 9.
  - Crepuscular (p10cr - p10): ocean_sunset +0.33 (3.31 -> 3.64), lake +0.22, forest/dust +0.15, golden/noon +0.04.
    In the Lab text via CRMAX and in ops/DECISIONS.md.
  - Night costs: night_sky 2.88 (r9 2.46), night_new 3.42, night_wide 3.47; clip p50s g1 3.43, g3 3.98 (storm +0.55,
    ~0.034 ms/slot). In the meteors question (cost + trade-off) and a DECISIONS entry.
  - Costs: High worst 3.47 (night_wide; r9 3.29), Low 0.89, Potato 0.31.
- Step 2 critic: C:/qfb/shaderdev/r010/critic.json, 56 frame notes + _r010_publish_summary (mean 6.6, shader frames 6.9;
  "not yet: the forest light needs a new view and technique"; leaps on meteors, sunset, gold). Texture/frills notes are
  keyed tag/scene (crop/<file> for item crops); spec_scenes.py attaches them to the texture/frills options.
- spec_scenes.py edits (backup spec_scenes.py.pre-publish): meteors scene rewritten (2 directions + r9, costs GA/GC/GD,
  per-slot trade-off), crepuscular rays are a visible fan, sunset says 0 px, underwater trade-off, intro budget line and
  two cost questions, stale tex-wall gold / tex-farm hook sentences and tex-wall notePrompt patched after the json load.
- Step 3: texture_make_scenes.py (8 scenes) + frills_make_scenes.py (5 scenes, crop variants included) rerun right before
  `finish_round.py C:/qfb/shaderdev/r010 --publish --no-push` -> commit **01b7fe4** (r010.json, index.json, r009 closed).
  Pre-post checks: terrain in every frame (sheets critic-todo-1..5 + texture/frills sheets); clips 1.08-1.75 MB; OVER
  BUDGET lines printed (sunset-full/A 3.31, checks C/D 3.09/3.05); no Stay True images (links only, tex-leaves/tex-farm/
  frills/crops); every shader question has cause + trade-off with numbers.
- Step 4: BOARD shaders + textures rows, ops/journal/shaders.md entry, DECISIONS (rays, meteor slots).

## Left for the orchestrator
- `git log origin/main..main`, push; check site/shaders/rounds/r010.json returns 200; Edge screenshot into r010\look\.

## Open for r011 (shader track)
Forest light (no canopy gap toward the sun in forest_golden; needs a new view/technique), dust motes, night skies over
budget (meteor slots), sunset disk glow and flat lilac sky, river bed showing in shallows, underwater square particles.
