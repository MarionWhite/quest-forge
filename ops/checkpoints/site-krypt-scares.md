# site-krypt-scares (checkpoint, started 2026-10-25 23:00, Mac)

Brief: ops/briefs/site-3d-page.md + the task prompt (design notes: /private/tmp/claude-503/-Users-suaz-Desktop-QuestForge/91769071-2ed0-4412-b25d-3c510232d8e5/scratchpad/shared/round4.md).
Owns: site/graves/scares.js, site/graves/scares/*, site/graves/tex/scare/*, the marked block in site/graves/app.js
Done means: director (eligible ~25 s active walking, first by ~60 s, guaranteed by ~75 s or 60% depth, cooldown 120 s, no repeats, max 4, reduced-motion off); one cutscene per 1.7.10 hostile mob ending on a 'You died!' parody with Respawn; ?scare=&at= with ?dump=1; sound design per scare; sheet reviewed

## Done
- director.js (sim ok), stage.js, fx.js, cuts1.js (Zombie Skeleton Creeper Spider CaveSpider Enderman Witch), cuts2.js (Slime Silverfish Blaze Ghast MagmaCube PigZombie WitherSkeleton), scares.js (runner, dump hook, director loop), app.js marker block (dynamic import).
- First sheet: scratchpad/scares/f1/sheet.png (mobs were invisible: textures not loaded at render; fixed by awaiting whenMobTexturesLoaded after makeMob). Second run: scratchpad/scares/f2 (shots.txt there).

## Next
- review f2 sheet, fix once; check sfx names vs site/lib/sfx/manifest.json (mob.villager.idle for the witch cackle is NOT in the bank, pick another); node --check .mjs copies; test live run (?scare=Zombie without dump); journal line; commit.
