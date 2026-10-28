# Site journal (newest first)

- 2026-10-27 (Mac) audio r8 (screams): the playback path coloured every scream. Manifest pitch [.97,1.03] meant a
  random playbackRate; volumes 1.1-1.7 drove a -10 dB 4:1 master compressor with automatic makeup gain, then a hard
  clip at the destination; ghast's @muffle low-passed the scream; muffle() swapped in a default (-24 dB 12:1)
  compressor for the rest of the visit; the game's "oof" landed 20 ms into each death scream; drowned.js stacked three
  underwater takes and a death scream. Now a qfaudio 'voice' bus (as recorded: no panner, rate 1, no reverb, gain <= 1,
  past the compressor and muffle, one -1 dBFS safety limiter for the whole mix), the oof 0.1 s before, one voice at a
  time for death_scream + underwater (6a1cd83 and this commit). r7's scream_pack2 pitch-shifted with rubberband and
  added a synthetic noise room: both gone. Pool: 70 Freesound searches sorted by downloads (911 results, 427 sound
  pages), CC0/CC BY 3.0/4.0 only, male only, clipped-at-source left out; rank = Bayesian rating + 0.15 log10(downloads).
  `tools/music/scream_pack3.py` (fetch|build|audition): trim, fade, level (-12 dBFS loudest 400 ms, -1 dBTP), 48 kHz
  192 kbps AAC (AudioToolbox), from the HQ Ogg previews (not r7's 128k mp3). Defaults wired (8/3/2/3/2); 34-take
  audition page in the scratchpad `r8/audio/audition/index.html`; credits at `site/lib/sfx/credits.html` (footer
  link on the Graves page). OGA and Commons checked: only Wilhelm-style or BY-SA, skipped. Owner picks by number.

- 2026-10-27 (Mac) orchestrator: round 7 done. The owner judged round 6's Krypt a regression; my
  stills-only reviews had missed motion and props. This round added a real-time yaw metric, prop
  close crops, walk filmstrips and a side-by-side against 275579a (round 5). The side-by-side caught
  the lost cold-to-warm descent. I fixed mood.js's TDZ crash myself (initMood threw whenever the
  Krypt was up first). Approved Enderman and Creeper on the owner's word.

- 2026-10-27 (Mac) krypt r7 follow-up: round 5's depth lighting restored over the endless path (r5 crypt values at the entrance, cold-to-warm per stratum and over the descent, torches thinned at stratum tops, cold opening kinds; nether/End keep their glow); terrain on one texture array per chunk (draw calls desktop 144->95 max, phone 88->62 max, typical 18-24); wall lean holds through corners (0-0.65 focus reversals/10 s).
- 2026-10-27 (Mac) krypt r7: passing focus rebuilt (lock with hysteresis, wall lean read per stone, 2.5 s wall hold, glance gate, 57 deg/s and 115 deg/s^2 caps; densest stretch 0-0.65 focus reversals/10 s, was 2.6-12.9), random prop scatter removed, props on real 1.7.10 models (props.js: chest, minecart, cauldron, anvil, brewing stand, enchanting table, piston, boat, pot, map, fence...), 15 story rooms (kinds_e.js) and a room rhythm (36% rooms, 600-block repeats 1176/1347 -> 95/1477 windows); heap after GC flat at ~15.5 MB (the 62 MB was a pre-GC dump sample); static mobs baked. Draw calls up to ~147 at busy spots (terrain per texture per chunk), left for an atlas.
- 2026-10-27 (Mac) scares r7: FNAF pulled back to Story Mode. 13 scares reworked so the mob's own mechanic is the scare and the blow
  lands in the world (no lens lunges, jitter, tear, static or screech; at most one device each); Enderman and Creeper code
  untouched; death screams play one take per scare. Sheet `scratchpad/r7/scares/all/sheet.png`; J run 16/16, no exceptions.
- 2026-10-27 (Mac) lucky r7: the world remembers (broken blocks stay broken, restored silently only off frame), no phasing (floor under his feet, gravity, steps; nav_check feet/world checks), parkour/hole/sapling/bow redone with permanent props (hay, bookshelves), enchanting table 1.7.10 crop + glyphs, XP bottles with real sprite/splash/orbs, bag scheduler reaches all 29 acts in ~670 s. Enchant book open state only verified in real time.
- 2026-10-27 (Mac) audio r7: screams rebuilt as ONE real recorded man per file (13 Freesound CC0 recordings, licence
  checked per page), trim/EQ/room only, 48 kHz 160 kbps; death_scream 8, scream 3, scream_far 2, underwater 3,
  jumpscreech 2. `tools/music/scream_pack2.py`. Unheard by the agent: owner picks by ear from the preview.

- 2026-10-26 (Mac) orchestrator: round 6 done. Critic rounds caught: every Krypt kind was one
  reskinned corridor (palettes, then shapes, then 12 open set pieces), the round-5 segments lost
  in the rewrite (restored), animals blocking the Lucky camera, a glowing sheep, four lunges that
  did not read, glimpses first too clean, then invisible and spotless in the endless halls (spot
  search widened to wall edges, coverage about 90%). 32 sound files were left uncommitted by the
  audio task (committed 1736790). Six orphaned headless Chromes from finished runs were stopped.

- 2026-10-26 (Mac) site-r6-scares: FNAF pass on all 14 Krypt scares (fnaf.js kit: lunge into the lens, split jaws, lit eyes, silence, fake-outs, a new roll of the dice every play), Magma Cube redone, Wither Skeleton's new ending (sword through the chest, decap, lifted to its face), gap deaths Lava fall and Drowned grab on `krypt-gap` (15%, approved only), recorded death screams. 80-frame sheet reviewed; all 16 run in real time through the J picker with no exceptions and no hitch in any lunge (two carve stalls found and moved). approved.json still empty.

- 2026-10-26 (Mac) site-r6-krypt-gen final: 61 kinds, 12 open set pieces forced one per stratum cycle (chasm with a lava sea, void bridge under a star dome, two-level library, cistern, mushroom and ice caverns, fortress bridge, arena, hollow hill, mine crossing, labyrinth junction, sand chamber), per-kind alcove palettes and hall shapes, asymmetry pass; metrics flat (37 to 83 draw calls, heap 28 to 62 MB at graves 10 / 1,000 / 9,000); `node tools/site/check_krypt_plan.mjs` passes.

- 2026-10-26 (Mac) site-r6-krypt-gen: the Krypt is endless. plan.js lays 10,000 graves as a deterministic append-only chain of legs (79 ms), krypt.js streams 48-block chunk windows (flat memory), 46 kinds in 12 strata (kinds.js, kinds_a.js, kinds_b.js on kindlib.js/kindreg.js), gaps with a jump arc and `krypt-gen` contract (`window.__krypt`), depth gauge, find rush, `?grave/at/stratum/kinds/leg`. Check: `tools/site/check_krypt_plan.mjs`. Not measured: phone timing, draw calls at grave 9,000.

- 2026-10-26 (Mac) site-r6-audio: screams are now real voices. `tools/music/scream_pack.py` layers CC0 OpenGameArt recordings (male death/pain screams, deaths, screeches, retching, wet foley, bubbles) with octave-down doubles, crunch, boom and cave/room reverb: qf.scare.death_scream x6 (three end in a gurgle), jumpscreech x4, underwater x3, static loop, and recorded scream/scream_far/shriek; qf.mood.far_* (x5, bank-derived, flagged "mojang"), scamper, scrape, breath_near. Sources, authors and licences: `site/lib/sfx/sources.json` and README.md. Checked by spectrogram and levels only, not by ear.

- 2026-10-26 (Mac) orchestrator: round 5 done. Critic rounds caught Steve hidden behind his own
  back at the stations (3/4 activity camera), the lamp post occluding, Giants dressed although
  1.7.10 never draws their armour (reverted), the lucky-choice camera, webs as cubes, a filled
  end-portal frame, a cluttered vault and muddy-dark segments. Live check: all 14 scares played
  in real time via CDP (picker, death screen, Enter respawns to the same spot, no exceptions).
  Audio context now warms in idle time (first Break click stalled ~170 ms).

- 2026-10-26 (Mac) site-r5-scares: all 14 Krypt scares rebuilt in the real scene (scares/rig.js runner, 1.7.10 HUD and death screen, J picker, approved.json empty so the director plays nothing until the owner approves); piston traps carve real rooms (Cave Spider, Slime) or drop you into a scare-built cavern seen through the rock (Ghast); 56-frame sheet over 5 segments, check_sounds 0 missing.
- 2026-10-26 lucky-life r5: nav.js occupancy map + A* (Steve and ground mobs never inside a prop, nav_check.py 0 violations), front-side table/furnace/chest, iron/wood chains, 1.7.10 held items, fence model, opaque chest, chicken chase, sign moved off the dais view.

- 2026-10-26 (Mac) site-r5-krypt-more: Krypt now 15 segments (+catacomb, cave-spider mineshaft, temple trap hall, iron-door vault, nether fortress bridge, stronghold end-portal finale), 14 bends, 9 side passages, walk 460 blocks (was ~235). Meshing is chunked and lazy (32 blocks); __krypt.carve/restore/solidAt/blockAt for the scares; ?carve=x,y,z,w,h,d demo. Dress batches culled per 32-block cell; draw calls in dumps 62-111 incl. post passes (old 40-74). Not verified: phone speed, Safari, walk feel.
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
2026-10-26 lucky-accuracy: audit (tools/site/audit_lucky.py), 1.7.10 block table + models, real reel tiles, sign/bars/chest/cake fixes; vet 306 ok.
2026-10-26 lucky r6: ring removed, leisurely pace + fidgets, 17 new activities with wolf/sheep/cow, big mobs path by real footprint (nav bucket bug). See ops/checkpoints/site-r6-lucky.md
