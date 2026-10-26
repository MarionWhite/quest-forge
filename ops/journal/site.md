# Site journal (newest first)

- 2026-10-26 (Mac) site-r5-mobs-gear: makeMob(id,{equipment}) dresses Zombie/Giant/PigZombie/Skeleton/Steve: 1.7.10 armour layers (ModelBiped 1.0/0.5), enchant glint (2 additive passes), RenderBiped hand transform, extruded sprite items, OreSpawn Queen armour + battle axe (scale 1.0 bytecode: ~7 blocks long). MOB_FEATURES.equipment. Silverfish model/texture were already exact; anim speed fixed. Vanilla Giants draw no armour in 1.7.10 (done anyway).
- 2026-10-26 (Mac) site-r5-lucky-flow: Close black screen = S.clearTemp threw on array materials (anvil_trap, bedrock_problem, lava_trap, lucky_choice) inside the dip's timer, so #dip never lifted; fixed, dip now always lifts. Particle freeze = buildScene was followed by st.fx.length = 0, orphaning the reveal burst Points mid-air; removed. Added warmStage() and a mined-time reel prebuild against break stalls. Not verified: Safari timing (Chrome headless only).
- 2026-10-26 (Mac) site-r5-audio: 15 qf.scare.* events (scream x3, scream_far x2, shriek x3, stinger x3, hit, heartbeat x3, breath, drone, ringing, chitter, whisper x3, fall, crunch x3, gore x3, cackle x2) synthesized in tools/music/scare_sounds.py, peaks about -1 dBFS, loops exactly periodic; checked by spectrogram and peak only, not by ear.

- 2026-10-26 (Mac) orchestrator: round 4 done, all seven tasks critic-passed on contact sheets.
  Critic rounds caught: OreSpawn rotations missing (ants scattered), OreSpawn fit offset (mobs
  below their roots, Mothras on the ground), unknown ids silently drawn as Zombies (vet now flags
  them), scare camera inside mobs, scare set not matching the Krypt segment (getWalk().segment),
  Steve silhouetted, phone framing, well item camera. Checks: vet_lucky 306/306 ok (OreSpawn drops
  re-vetted after the fit fix), check_sounds 0 missing. Not verified: audio by ear, Safari, real
  scroll, true portrait phone. Approximations: Mothra (no jar model), horse gait, dragon static.

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
