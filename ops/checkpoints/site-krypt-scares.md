# site-krypt-scares (checkpoint, started 2026-10-25 23:00, Mac)

Brief: ops/briefs/site-3d-page.md + the task prompt (design notes: /private/tmp/claude-503/-Users-suaz-Desktop-QuestForge/91769071-2ed0-4412-b25d-3c510232d8e5/scratchpad/shared/round4.md).
Owns: site/graves/scares.js, site/graves/scares/*, site/graves/tex/scare/*, the marked block in site/graves/app.js
Done means: director (eligible ~25 s active walking, first by ~60 s, guaranteed by ~75 s or 60% depth, cooldown 120 s, no repeats, max 4, reduced-motion off); one cutscene per 1.7.10 hostile mob ending on a 'You died!' parody with Respawn; ?scare=&at= with ?dump=1; sound design per scare; sheet reviewed

## Done
- director.js (sim ok), stage.js, fx.js, cuts1.js (Zombie Skeleton Creeper Spider CaveSpider Enderman Witch), cuts2.js (Slime Silverfish Blaze Ghast MagmaCube PigZombie WitherSkeleton), scares.js (runner, dump hook, director loop), app.js marker block (dynamic import).
- First sheet: scratchpad/scares/f1/sheet.png (mobs were invisible: textures not loaded at render; fixed by awaiting whenMobTexturesLoaded after makeMob). Second run: scratchpad/scares/f2 (shots.txt there).

## Next
- DONE. Final sheets: scratchpad/scares/f5 (7 mobs), f4 (3), f7/f6 (fixes), f2 (first 5 mobs). Verify via graves/scares/test.html?scare=X&at=ms (app.js was mid-edit by KRYPT-WORLD: krypt.js export alcoveFor missing broke graves/ itself). app.js marker block is uncommitted (shared file with KRYPT-WORLD).

Critic pass (861286a lib) done: spider legs/anim, zombie face framing, ghast placement via bbox, slime/witch/creeper fixes. Final reveal sheet scratchpad/scares/f11/sheet.png (+ f12 creeper, silverfish). Still dump with graves/scares/test.html while graves/app.js is mid-edit.

Final critic pass: creeper green, grey boxed silverfish, whole slime; stage dressed per krypt segment (SETS in stage.js, segment from __krypt.getWalk()), ?scareat=ms overrides ?at on the real page, ?seg= forces a set. Frames: scratchpad/scares/f18 (mine, flood), f19 (deep, library), f20/f24 (reveals).
