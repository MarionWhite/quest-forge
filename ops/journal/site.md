# Site journal (newest first)

- 2026-10-26 (Mac) site-lucky-outcomes: every drop has its own scene (generic is only a crash guard); wells and temples play the rolled hidden-block result; big mobs get night, lightning, fog, shake and their own roar; 4 dud drops; tools/site/vet_lucky.py vets all 306 drops with a per-scene report.
- 2026-10-25 (Mac) site-audio: sound bank site/lib/sfx (Minecraft 1.7.10 + OreSpawn as m4a, plus our own qf.* and music.lucky/music.krypt synthesized in tools/music/site_cues.py); game sounds ship only if the owner decides so (build_sfx.py --own-only).
- 2026-10-25 (Mac) first-night: Infernal modifiers (all 27) and Level Up classes and skills from the jars; difficulty noted as shipped inert; friends' server rules from decision 0007; parties, sleep and Farmer claims corrected. Voice keys stay Tab/U (local commit 5e9a96f; origin still B/N).
- 2026-10-25 23:30 (Mac): site work moved under the ops harness (track, checkpoints, brief).
  Round 4 running: lucky-stage, lucky-outcomes, mobs, audio, krypt-world, krypt-scares,
  first-night. New shared tools: `site/lib/qfaudio.js`, `tools/site/dump_frames.py`.
- 2026-10-25 21:00 (Mac): c0aa4c8 Lucky Block in 3D, the Krypt, first night as a reference.
  Owner feedback: "well done on a first pass, now we swing for the fences" (round 4).
- 2026-10-25 (Mac): earlier commits 5e3bae0..e872e30: theme toggle, first night, offline item
  index + freshness guard, homepage redesign, voice keys Tab/U, Lucky Block v1, graves,
  players. All local.
- 2026-10-25 (Mac): Krypt jump scares: director + 14 mob death cutscenes in site/graves/scares*, test page graves/scares/test.html; app.js has the marked block.
- 2026-10-25 (Mac, site-mobs): mob library rebuilt from the 1.7.10 model classes and OreSpawn's own jar models (site/lib/mc, generators in tools/site), lineup page lib/mc/lineup.html, reel tiles repainted (icons pixel-exact, mob busts, block cubes). Local only.
- 2026-10-25 (Mac, site-krypt-world): Krypt rebuilt as nine segments with bends and side passages, baked light plus 4 live lights, real wall torches, passing-focus camera, entry gate, spatial ambience, window.__krypt contract (site/graves/krypt.js dress.js fx.js kaudio.js app.js). Local only.
2026-10-25: Lucky stage round 4: block drops and slams, Steve's behaviour system and campsite, new sky, mood torch flash, always-on ticks, speaker toggle (site-lucky-stage).
