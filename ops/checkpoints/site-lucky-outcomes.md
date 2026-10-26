# site-lucky-outcomes checkpoint

## Done
- Read briefs, scenes.js, structscenes.js, structures.js, app.js ctx and timeline, build_lucky.py layout.
- Baseline seen (frames in /private/tmp/claude-503/-Users-suaz-Desktop-QuestForge/91769071-2ed0-4412-b25d-3c510232d8e5/scratchpad/lk/t0/sheet.png): 153 silverfish shows Steve's back, 162 Mobzilla shows empty sky, 208 shows the giant "?" plaque.
- Wrote site/lucky/fx.js: math, burst/puff, strikeBolt, sky/fog, spawnMob/mobTick with mob voice, item sprites at 0.5 block, roll() for choices, newReport/finishReport/sfx/watch for the scene report.
- Findings: each of the 14 wells and 20 temples is already one drop per inner outcome, so the drop rolled is the well's roll; play its "then" actions after the coin. skipped[] lines (529, 539, 541) and drop 208 (line 384) become scene "dud" drops.

## Next (in order)
1. site/lucky/scenes.js rewrite: itemsBeat (ring on dais, low camera), dud, simple scenes with sfx, buildScene wrapper that adds scene.report() and writes <script id="qf-scene-report"> in ?dump mode.
2. site/lucky/mobscenes.js: horde/spawn/tower/pet/villager (side camera, mobs between camera and Steve) plus grand boss treatments (night, bolts, fog, shake, roar).
3. site/lucky/wells.js: wishing_well, sky_temple, ground_temple (coin, hidden block breaks, inner outcome).
4. structscenes.js: sfx, bedrock sign, message plus items.
5. tools/site/build_lucky.py: text fixes, dud drops, "dud" in SCENES; README-lucky.md.
6. tools/site/vet_lucky.py, run before and after; sheets per scene key.
7. node --check, build_lucky --check, check_fresh, manifest sound-name check, journal line.

## Paths
frames: /private/tmp/claude-503/-Users-suaz-Desktop-QuestForge/91769071-2ed0-4412-b25d-3c510232d8e5/scratchpad/lk/ ; vet table: not written yet (will be /private/tmp/claude-503/-Users-suaz-Desktop-QuestForge/91769071-2ed0-4412-b25d-3c510232d8e5/scratchpad/lk/vet.txt)
Blocked on: nothing. Needs from STAGE: sceneReport in dump JSON (I also write qf-scene-report in the DOM myself).
