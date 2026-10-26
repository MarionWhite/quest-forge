# site-krypt-scares (checkpoint, started 2026-10-25 23:00, Mac)

Brief: ops/briefs/site-3d-page.md + the task prompt (design notes: /private/tmp/claude-503/-Users-suaz-Desktop-QuestForge/91769071-2ed0-4412-b25d-3c510232d8e5/scratchpad/shared/round4.md).
Owns: site/graves/scares.js, site/graves/scares/*, site/graves/tex/scare/*, the marked block in site/graves/app.js
Done means: director (eligible ~25 s active walking, first by ~60 s, guaranteed by ~75 s or 60% depth, cooldown 120 s, no repeats, max 4, reduced-motion off); one cutscene per 1.7.10 hostile mob ending on a 'You died!' parody with Respawn; ?scare=&at= with ?dump=1; sound design per scare; sheet reviewed

## Done
- site/graves/scares/director.js (pure timing; node sim: first scare 25..59 s, guarantee at 10 s when depth>=0.6, min gap 120, max 4). Sim: scratchpad/sim.mjs.

## Next
Plan (own overlay canvas + own THREE scene, independent of the Krypt scene; deterministic f(t) so ?at= seeks):
1. scares/stage.js (corridor scene, camera rig, instanced gore particles, mob wrapper w/ fallbacks for Blaze/MagmaCube/PigZombie/WitherSkeleton)
2. scares/fx.js (240x270-ish pixel overlay: hurt flash, cracks, splats, hearts+hotbar, fire, death screen)
3. scares/cuts1.js, cuts2.js (14 cutscenes), scares.js (runner, input walking detection, dump hook, audio)
4. app.js marker block (dynamic import of ./scares.js, initScares()), verify sheet, sfx names vs manifest.
