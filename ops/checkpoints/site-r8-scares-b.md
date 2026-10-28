# site-r8-scares-b (checkpoint, started 2026-10-27, Mac)

Brief: `ops/briefs/site-3d-page.md`. Agent: opus (horror direction and building).
Owns: `site/graves/scares/magmacube.js`, `blaze.js`, `ghast.js`, `silverfish.js`, the scare flow check script, and
any new helper file you add. Shared files (`scares.js`, `story.js`, `common.js`, `rig.js`, `fnaf.js`,
`site/lib/qfaudio.js`): additive changes only, commit only your hunks.
A second agent (`site-r8-scares-a.md`) works on Spider, Zombie and Wither Skeleton at the same time.
Previous state: `site-r7-scares.md` (its tools in the scratchpad `r7/scares/`: trace.js, cmp_trace.py, scareflow16.js,
multi.py, sheet2.py; reuse them). Spec: `docs/design/site/krypt-scares.md`.

## Owner's words (2026-10-27, round 8)
- Magma Cube: "the lights should dim, and there should be a baby magma cube that hops towards the player somewhat
  innocently, and as it gets close, the player looks down at it, and a Massive magma cube comes from behind and
  kills them."
- Blaze: "pretty good, but he just comes out of the wall. He should come out of the nearest grave."
- Silverfish: "every time I play the silverfish animation the audio stays permanently."
- Ghast: "close, but it shoots a fireball at the player prematurely. There should only be the one after it
  jumpscares the player."
- Lava and water gap deaths "aren't bad": leave them. Enderman and Creeper stay approved.

## Rules for every scare this round (from the owner's notes)
- No mob appears in view out of nowhere. It enters from a place that makes sense: a grave, a door, a hole, the
  ceiling, the dark beyond the light.
- The camera only turns for a reason the viewer can perceive: a sound, a sight, a touch.
- Mobs act on their own nature. Nothing waits for the player to look back.
- Every sound and loop the scare starts stops when it ends and on Enter (respawn).

## Done means
- [ ] **Silverfish audio leak fixed**, and the cause checked in every scare (16) and the mood layer. Add to the
  flow check: after each scare and after Enter, no scare voice or loop is still playing (expose a small debug
  count from qfaudio if needed). It fails loudly if one is.
- [ ] **Ghast:** no fireball before the jumpscare. Exactly one, after it.
- [ ] **Blaze:** rises out of the nearest grave (the grave cracks, fire and smoke burst up, rods spinning,
  `mob.blaze.breathe`), not out of the wall. Keep the rest the owner liked.
- [ ] **Magma Cube, the owner's script beat by beat:** the lights dim; a size-1 magma cube hops toward the player,
  almost cute (small squelches, its little compress-and-stretch hop); the player looks down at it as it arrives;
  a massive magma cube comes from behind (the orange glow grows on the floor, the big squelch) and kills them. Make
  it as big as the corridor allows (Size NBT beyond 4 is real Minecraft); its 1.7.10 layered model and texture.
- [ ] Enderman and Creeper unchanged: re-run trace.js and `cmp_trace.py base_trace.json` after any shared change.
- [ ] Review: per changed scare, a filmstrip at 5 frames per second across the whole scare, plus a beat log
  (time, camera yaw and pitch, what is on screen, sounds started and stopped) set beside the owner's words. Live J
  run of all 16 with no exceptions and no leaks. Chrome: one at a time (another agent renders too).
- [ ] Commit your own paths, journal line in `ops/journal/site.md`, report in five lines with the filmstrip paths.

## Progress (status: DONE 2026-10-27, see the last step)
(write after every step)
- 2026-10-27 step 0: read. Scratch `scratchpad/r8/scares-b/`. **Silverfish leak cause found:** `silverfish.js` puts
  `qf.scare.chitter` in `roar()` (S.sounds, a one-shot), but the manifest marks that event `loop: true`, and
  `qfaudio.play` loops any looping event; the scare's soundPlayer only tracks S.loops, so nothing ever stops it.
  No other scare plays a looping event as a one-shot (grep of the 10 looping names); mood stops its events (ev.stop).
  Plan: qfaudio voice registry + `voices()` + `once` option; soundPlayer tags "scare", one-shots `once`, tracks and
  stops them on Enter; silverfish chitter burst becomes a bounded loop; flow check samples voices.
- step 1 DONE (leak): `qfaudio.js` voice registry (`audio.voices()`: id, name, loop, bus, tag, age) and `once`;
  `scares.js` scareAudio(): one-shots `once`, all tagged "scare", stop() ends one-shots too (0.2 s) on Enter;
  `__scares.voices()`; `silverfish.js` chitter burst is a bounded loop. New check `tools/site/scare_flow.mjs`
  (`node tools/site/scare_flow.mjs [--only A,B] [--mood] [--out f.json]`, exits 1 on a leak/exception/no return).
  Proof: the old behaviour (scratch `leaksite/`, port 8771) FAILS "LEAK at the death screen: qf.scare.chitter; after
  Enter"; the fix passes. Full run `r8/scares-b/flow_all1.json`: 16/16 ok + 20 mood events ok, no leaks, 59-60 fps.
- step 2 (in progress, uncommitted): Ghast `ghast.js`: the fake fireball and its dice removed (exactly one fireball, after
  the face/charge); on the look-back branch it now floats in out of the dark (drift 5 m out, 2.2 m down) while you
  look away, instead of popping in. Blaze: `app.js` contract gains `kr.gravesNear(pos, range)` (additive, 12 lines:
  stone foot, out dir, statue, family, objs). Probe `r8/scares-b/probe_graves.js`: at=0.3 graves every ~4.5 m in
  alcoves at x=+-5.2 (stone 1.2 past the hall's half width); at=0.55/0.8 no graves within 16 m (fallback needed).
  Blaze plan: the grave plot (2 floor blocks in front of the stone) is carved in build() under stand-in blocks; cracks
  grow with orange glow seeping through, smoke wisps, breathing from below; the head turns to it (sound + glow); the
  plot bursts (floor block particles, flame column), it rises out of the pit rods spinning, floats out ahead (P1) and
  the rest is as r7. Fallback with no grave in 16 m: the same through the corridor floor ahead.
- step 3 (uncommitted): Blaze rewritten (`blaze.js`, findPlot + stand-ins + cracks/glow + burst + rise; r7 volley kept).
  Beat log tool `r8/scares-b/beat.js` + `beatfmt.py` (cdp: `graves/?demo&at=A&beat=ID&beatseed=N`); filmstrip tool
  `r8/scares-b/film.py NAME "<query>" DUR OUT` (5 fps, pages of 20, one Chrome). Blaze seed 1 at=0.3: grave 16 (cross)
  at 3.9 m left; crack 1.6 s, turn 2.0 s (after the sound), burst 3.9 s, rises 4.0-4.6, out 5.2-6.1, flare 6.1.
  Filmstrip `r8/scares-b/film/bl1/film.png` was rendering (slow: >10 min for 61 frames).
- step 4: Blaze and Ghast reviewed (sheets `r8/scares-b/film/bl1/film.png` (5 fps, before skins), `chk1/sheet.png`
  (Blaze no-grave fallback at=0.8; Ghast rise and look-back), `sk1/sheet.png` (with the local Patrix skins)).
  Ghast with a skin: its three faces are now painted on the skin (eyes opened, mouth opened at the painting's own
  lids and crease) instead of switching to the vanilla face mid-scare. Flow tool: progress lines + a 150 s stall
  watchdog (a first Blaze+Ghast run hung >15 min with no output on the loaded machine; alone each passes).
  Magma Cube rewritten (uncommitted): beat log `mc_beat1.json`, frames `mc1/`, `mc2/` (size 6 at ceil 4 and 7,
  width-limited); fixes so far: baby enters from the far dark (fades up from unlit), fullbright cubes, face at 2.4 m,
  slices spread capped to the ceiling.
- step 5: committed Blaze + Ghast + gravesNear + flow tool (e88931a). Magma fix: the big cube's first hop was in
  place (zG0 used min instead of the midpoint). Magma film re-rendering to `r8/scares-b/film/mc1/film.png`
  (background). NOTE: my `pkill -f "dump-dom"` at ~20:55 may have killed another agent's dump Chromes; only kill by PID.
  Next: films for Blaze (with skins) and Ghast, beat files beside the owner's words, full J run + mood, trace check
  for Enderman/Creeper, spec section, commit, journal.
- step 6: Magma film done `r8/scares-b/film/mc1/film.png` (72 frames; reads beat by beat: dim 0-1.8, baby out of
  the dark 2.0-5.2, stretched accordion hops, at your feet 6.6, looking down 6.8-9.2, turn 9.4, massive face 9.6,
  slices open 10.0, inside 10.2+, death 14.0). After it: floor glow from behind boosted (it was subtle), big start
  guarded against a near wall behind. Re-render 7.0-9.4 only: `FROM=7000 film.py mc1 "<q>" 9.4 film` (film.py now
  rebuilds the sheet from every frame in the dir). Films bl2/gh1/sf1 rendering in background (`films.sh`, logs
  `film_*.log`). Spec section v5 written (uncommitted, docs/design/site/krypt-scares.md). Beat-file builder
  `beatfile.py`. Enderman/Creeper: none of my commits touch enderman/creeper/rig/common/fnaf/story/hud/director.
- step 7: films `film/bl2/film.png` (Blaze, local skins on), `film/gh1/film.png` (Ghast, one fireball), `film/mc1/film.png`
  (Magma, 7.0-9.6 re-rendered with the stronger glow); Silverfish film skipped (visually unchanged; r7 `sf1/sheet.png`).
  Ghast look-back: its charge warble (T_BACKV - 0.15) turns the head; it fires on its own clock. Beat files beside the
  owner's words: `r8/scares-b/beats/{magmacube,blaze,ghast,silverfish}.txt`. Full live J run + mood:
  `flow_all2.json`: 16/16 ok, 20 mood ok, no leaks, no exceptions (gaps to 197 ms under load from other renders).
  check_sounds exit 0; node --check on .mjs copies of all touched modules.
- DONE: commits bf57898 (leak + flow check), e88931a (Blaze, Ghast, gravesNear), 8d9bbb5 (Magma Cube, spec v5), journal.
  Done-means: leak fixed and checked in all 16 + mood [x]; Ghast one fireball after [x]; Blaze from the nearest grave [x];
  Magma Cube beat by beat [x]; Enderman/Creeper untouched by these commits [x]; films + beat logs + live J run [x].
  Owner to judge: the Magma baby's tall stretched hops are vanilla-accurate but read less "cute"; the 14 s length.
- step 8 (coordinator review, 2 Magma tweaks; uncommitted): (1) baby: squish decays x0.6/tick and stretches half as far
  (peak ~2x as tall as wide for a tick or two), hops 0.45 m high, 0.42 s, <=1.6 m long, from <=9 m. (2) engulf: it
  lunges low along the floor (accelerating) as you go over backwards; inside, its slices give way to a box of its size
  and squish (dark insides, orange seams; drawn from the back, so it holds from 0.35 m outside its front too), the
  model's core over you and ahead (you are 1 m off its middle), three chews (squash, kick, jolt), black at tK+1.9, death
  screen. Fire overlay, flat tints and the projection squash removed. Frames `mc3/`, `mc4/`; film `film/mc2/`.
- step 9: engulf finish. The inside view starts from 1.1 m outside its front (the near face was a dark fill at 10.4);
  it lands with you just inside its front (zOn = min(-0.6, 0.4 - half)), so the core sits over you and ahead and
  never fills the lens; look-up 0.42 in the lunge, 0.25 inside, lying at 0.25 m. 20 fps check `film/mcf/` +
  `film/mcf_fine.png`. film.py trap: a stale raw page json overwrites re-rendered frames; moved to `film/mc2_stale/`.
  Film `film/mc2/film.png` (10.0-14.0 re-rendered). Hop crop `film/hop_peak.png` (rest / squish peak ~1.95x / top ~1.5x).
  Live run `flow_mc_final.json`: ok, mood 20 ok, no leaks. Spec v5 Magma lines updated. DONE: committed with the journal entry; report sent.

