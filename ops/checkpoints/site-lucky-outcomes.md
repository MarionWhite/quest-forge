# site-lucky-outcomes checkpoint

## Done
- All modules written and committed once (1d9bcd6): fx, beats, scenes, mobscenes, wells, structscenes, blocks, structures, vet_lucky.py, build_lucky.py (dud drops, text fixes).
- Vet v1 (306 drops): broken 14, weak 4. Fix pass applied (report counting, towers, grand camera and fog, wells ring, falling columns now use dy as spawn height, lucky eggs, mobSay fallbacks, m.hover for flyers, blurbs for stacks).
- Vet v2 (70 sampled drops): broken 4 (towers 180/207 timing, anvil, pit), all since fixed in code.
- Full vet v3 running: /private/tmp/claude-503/-Users-suaz-Desktop-QuestForge/91769071-2ed0-4412-b25d-3c510232d8e5/scratchpad/lk/v3 (log /private/tmp/claude-503/-Users-suaz-Desktop-QuestForge/91769071-2ed0-4412-b25d-3c510232d8e5/scratchpad/lk/v3.log, table /private/tmp/claude-503/-Users-suaz-Desktop-QuestForge/91769071-2ed0-4412-b25d-3c510232d8e5/scratchpad/lk/v3/vet.txt, sheets /private/tmp/claude-503/-Users-suaz-Desktop-QuestForge/91769071-2ed0-4412-b25d-3c510232d8e5/scratchpad/lk/v3/sheets/<key>.png).

## Next
1. Read v3 vet.txt, fix any BAD left, rerun those with --only.
2. node --check on .mjs copies, build_lucky --check, check_fresh, manifest sound check, journal line in ops/journal/site.md, commit paths (git add my new files by explicit path first).

## Open for other agents
- MOBS: Mothra model renders invisible in scene 163 (tags show, no body); Rotator renders as flat red slabs; unknown ids fall back to Zombie (Apple Cow etc.).
- STAGE: nothing required; I write <script id=qf-scene-report> in ?dump mode myself. Fog near/far are reset by buildScene; a resetFog in resetStage would be cleaner.
