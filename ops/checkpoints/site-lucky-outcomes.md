# site-lucky-outcomes checkpoint

## Done
- fx.js, beats.js (items ring, TNT, fireworks, dud), scenes.js rewritten, mobscenes.js (groups, towers, pets, grand boss engine, apocalypse), wells.js (wells + temples), structscenes.js sfx + watch, blocks.js generic block table (+ textures in site/lucky/tex/blocks), structures.js counts blocks.
- build_lucky.py: dud scene + 4 dud drops (3 skipped lines + line 384), text fixes, validate checks; lucky.json rebuilt (306 drops).
- tools/site/vet_lucky.py written and smoke-tested (10 drops, all load).
- Baseline frames before my changes: /private/tmp/claude-503/-Users-suaz-Desktop-QuestForge/91769071-2ed0-4412-b25d-3c510232d8e5/scratchpad/lk/t0/sheet.png (153, 162, 208).

## Next
1. Full vet run: python3 -I tools/site/vet_lucky.py /private/tmp/claude-503/-Users-suaz-Desktop-QuestForge/91769071-2ed0-4412-b25d-3c510232d8e5/scratchpad/lk/v1 ; read vet.txt, then ~35 sheets in /private/tmp/claude-503/-Users-suaz-Desktop-QuestForge/91769071-2ed0-4412-b25d-3c510232d8e5/scratchpad/lk/v1/sheets/<key>.png.
2. Fix every BAD/weak scene (camera, scale, timing), rerun vet on the failing indexes only.
3. README-lucky.md (dud, skipped now drops, vet tool), node --check .mjs copies, build_lucky --check, check_fresh, manifest sound check (site/lib/sfx/manifest.json), journal line ops/journal/site.md, commit paths.

## Paths
frames: /private/tmp/claude-503/-Users-suaz-Desktop-QuestForge/91769071-2ed0-4412-b25d-3c510232d8e5/scratchpad/lk/ ; vet table: /private/tmp/claude-503/-Users-suaz-Desktop-QuestForge/91769071-2ed0-4412-b25d-3c510232d8e5/scratchpad/lk/v1/vet.txt (after step 1)
Notes: wells/temples are one drop per inner outcome in the data, the drop rolled is the well roll. Needs from MOBS: mobSounds names, models for Blaze, Brown Ant etc., part names rightArm.
