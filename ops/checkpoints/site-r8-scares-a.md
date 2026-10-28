# site-r8-scares-a (checkpoint, started 2026-10-27, Mac)

Brief: `ops/briefs/site-3d-page.md`. Agent: opus (horror direction and building).
Owns: `site/graves/scares/spider.js`, `zombie.js`, `witherskeleton.js`, and any new helper file you add.
Shared files (`scares.js`, `story.js`, `common.js`, `rig.js`, `fnaf.js`): additive changes only, commit only your hunks.
A second agent (`site-r8-scares-b.md`) works on Magma Cube, Blaze, Ghast and Silverfish at the same time.
Previous state: `site-r7-scares.md` (its tools in the scratchpad `r7/scares/`: trace.js, cmp_trace.py, scareflow16.js,
multi.py, sheet2.py; reuse them). Spec: `docs/design/site/krypt-scares.md`.

## Owner's words (2026-10-27, round 8)
- Zombie: "it starts with the zombie teleporting right in front of the camera. This doesn't make any fucking sense.
  It's there, the character turns for some reason, and the zombie waits until they look back to do anything?"
- Spider: "there should be a spider sound, the player looks left and right over their shoulders, and then after
  they look back forward they should slowly look up, and as soon as they see the spider for a second it jumps on
  their face and brutally starts ripping them apart."
- Wither Skeleton: "looks like shit and doesn't make sense, so please just scrap it and rethink it."
- Enderman and Creeper stay approved. The owner wants Story Mode quality, MK-level brutality, Minecraft-accurate.

## Rules for every scare this round (from the owner's notes)
- No mob appears in view out of nowhere. It enters from a place that makes sense: a grave, a door, a hole, the
  ceiling, the dark beyond the light. Prove it: the frame before a mob first shows on screen, it is off screen,
  occluded or in darkness, and it has moved there, not popped.
- The camera only turns for a reason the viewer can perceive: a sound, a sight, a touch.
- Mobs act on their own nature. Nothing waits for the player to look back.
- Every sound and loop the scare starts stops when it ends and on Enter (respawn).

## Done means
- [ ] **Spider, the owner's script beat by beat:** the spider's sound (1.7.10 `mob.spider.say`); the player looks
  over the left shoulder, then the right; back forward; then slowly looks up; the spider on the ceiling is seen for
  about a second; it leaps onto the face and rips them apart: legs and fangs over the lens, the camera thrashed and
  knocked to the floor, hurt flashes, bites, the scream, hearts emptying. Brutal in Minecraft's own vocabulary.
- [ ] **Zombie, rethought so it makes sense.** Suggested: 1.7.10 zombies break wooden doors. A wooden door is set in
  the crypt wall beside or behind the player (placed out of view before the scare starts). Banging
  (`mob.zombie.wood`) makes the player turn to it; the door shakes, dust falls, the block-crack overlay grows; the
  player backs away; groans; the door bursts (`mob.zombie.woodbreak`, door particles); the zombie lurches through,
  arms out, grabs and bites. A better idea that keeps the logic is fine; say why in the journal.
- [ ] **Wither Skeleton, scrapped and rethought.** Suggested: a torch behind the player throws their shadow on the
  wall ahead (a shadow-only body, invisible to the camera). A second, taller shadow rises behind theirs, a sword in
  its hand. The player freezes, then turns slowly: the 1.2-scale wither skeleton towers over them, looks down, and
  swings its stone sword. Hearts turn black (Wither), the view drains to black. Again, better ideas are welcome.
- [ ] Enderman and Creeper unchanged: re-run trace.js and `cmp_trace.py base_trace.json` after any shared change.
- [ ] Review: per scare, a filmstrip at 5 frames per second across the whole scare, plus a beat log (time, camera
  yaw and pitch, what is on screen, sounds started and stopped) set beside the owner's script. Live J run of all
  16 with no exceptions and no sound left playing after Enter. Chrome: one at a time (another agent renders too).
- [ ] Commit your own paths, journal line in `ops/journal/site.md`, report in five lines with the filmstrip paths.

## Progress
(write after every step)
Scratch: `scratchpad/r8/scares-a/` (tools copied from `../r7/scares/`). Preview server :8000.
- [2026-10-27] Read brief, track, r7 checkpoint, the three scares, rig/common/fnaf/story/scares.js. Plan:
  - Spider: the say (from overhead), left shoulder, right shoulder, forward, slow look up; it is on the ceiling over
    you (it was there when the walk stopped, out of frame; its steps overhead while you look round); ~1 s seen, it
    leaps (vanilla leap), the face, thrashed, floored, bites, scream, hearts out.
  - Zombie: a wooden door carved into the nearer side wall behind-beside you (out of frame at the freeze), a short
    dark passage behind it; bangs (mob.zombie.wood), crack overlay (destroy_stage), dust, backing away; woodbreak,
    the zombie lurches through, grab, bite, floored, two more through the doorway.
  - Wither Skeleton: planar/projected shadows (new helper `scares/shadow.js`): a torch behind throws your shadow
    ahead; a taller one with a sword comes up behind it; you turn, the first blow lands mid-turn (vanilla: it hits
    as soon as it is in range), Wither hearts, the second blow, floored, drain to black.
- Tools (scratch `r8/scares-a/`): `film.js` (CDP: `node cdp.mjs "<graves url>&film=Spider&seeds=1,2[&w=900&ats=6.2,kill+0.4]" film.js > X.json`),
  `film.py X.json OUTDIR` (filmstrip at 5 fps, beat log `<id>_s<seed>_log.txt`, appearance proof printed), `crop.py X.json SEED T0 T1 out.png`.
  `S.solid(worldVec)` (optional, in a scare) tells film.js about occluders that are not blocks (the door).
- [x] Spider built and committed (4d1de85). Films: `sp3_0.8/`, `sp3_0.42/`, `sp2/` (at=0.3: perch in a 6 m vault). Proof: off frame
  until the look up reaches it (first on screen ~0.7-1 s before tSee). Next: Zombie (door), then Wither Skeleton (shadows).
- [x] Zombie + `scares/door.js` committed. Films `z6/` (at=0.42 s2), `z3/` (0.8 s1). Proof: all three zombies occluded by the door
  until the break. Open: fallback (no wall spot) not yet seen in a film. Next: Wither Skeleton (shadows, new `scares/shadow.js`).
- [x] Wither Skeleton + `scares/shadow.js` (projected shadows: casters drawn from the light into a mask, the Krypt's
  chunk meshes re-drawn with a multiply). Torch pick: a Krypt torch behind whose shadows of you and of it climb the wall
  ahead; else a copy of a Krypt wall torch moved whole blocks to a wall behind you; else (a hall) floor shadows from the
  torch lifted 1.1 m. A spot from the flame lights the stone where they fall. Films `ws4_0.42/`, `ws4_0.8/` (own torch,
  wall shadows), `ws4_0.3/` (hall, floor). Proof: the skeleton is first on screen mid-turn (5.1-5.35 s), off frame before.
  Next: zombie teeth lit (coordinator note), trace/cmp, live J run of 16, journal, report.
- [x] Zombie jaw lit (db815c8): teeth/tongue/mouth colours scaled by its head's light each frame. Close frames (z7/, seeds 1-3):
  the bite is ~0.33 m from the face (both eyes in most frames), not centimetres.
- [x] Enderman/Creeper: r7 base_trace is stale (world under at=0.3 changed again: carpet_crypt -> classic). Traced the
  pre-round shared files (4d1de85^: scares.js, rig/common/fnaf/story, enderman, creeper) on a clone of today's site vs
  HEAD: all 8 traces identical (`tr_old.json` vs `tr_now.json`).
- Next: live J run (`node tools/site/scare_flow.mjs --only Spider,Zombie,WitherSkeleton`, then all 16) once no other
  headless Chrome is running; journal; report.
- [x] Live J run, all 16 (scare_flow.mjs, flow16.json): no leaks, no exceptions, 60 fps. Review set: scratchpad
  `r8/scares-a/review/` (README.txt = the owner's script beside the beats, proof.txt, filmstrips + beat logs per scare).
  Journal entry written. DONE apart from the report.
- [x] Coordinator review fixes (Wither Skeleton shadow): the walk stops square on to a flat, open face 3 m off (the
  nearest along the walk; else further, up to 12 m); floor fallback dropped; the torch is a copy of a Krypt wall torch at
  eye level on the wall behind (faded in if it is in sight at the first frame); its spot dominates while the Krypt's
  bake/lights go down (0.32/0.25) during the beat. shadow.js: 2048 mask, frustum fitted to the face, flat (no fall-off),
  bias 5 cm, and the receivers now take gl_Position from modelViewMatrix exactly as three.js does (world*view in the shader
  lost precision far from the origin and z-failed against the wall in about half the frames: the old "faint smudge").
  Skeleton: in front of the torch at rP*0.5 (spill), then a pace behind you to the roomier side (0.35 m), raise swung wide.
  Review: scratchpad review/wither/ (crops_at0.8|0.3_s1-3, film_at*_s*, logs, proof_wither.txt). Live run ok.

## Round 8b (2026-10-27): Wither Skeleton, full redo
Owner: "things are much much better. The wither skeleton one is stupid and doesn't make sense, so full redo."
Then: "Make it scary". That is the bar.
His chosen concept, **Too tall to follow:** "one chases you out of the dark, and you dive into a 2-high side passage. It
can't fit, since it's 2.4 blocks tall, so its skull scrapes the ceiling and it gives up. Silence, then relief. You go
deeper, and the passage opens into a tall room, where it was waiting after coming around the other way."
Coordinator build notes:
- **1.7.10 facts:**
  - A wither skeleton is 0.72 x 2.34 and can't path through a 2-high gap.
  - It moves at skeleton speed, carries a stone sword and uses skeleton sounds.
  - A hit gives Wither II (black hearts).
  - A sprinting player is faster than it.
- **Beats, in order, each making sense:**
  - A sound behind you turns you: the rattle, its steps, the sword scraping stone. It comes out of the dark.
  - You sprint (FOV kick, bobbing). A 2-high side opening is in view before you take it.
  - It can't get in: its body fills the opening, its head is hidden above the lintel, the skull grinds the stone. It
    tries again and again, goes still in a long silent hold, then turns away toward the way around.
  - Silence: breathing and heartbeat settle. Make the calm real.
  - You go deeper. A tall room (ceiling 4 or more) has a second entrance that visibly connects back to the corridor.
  - It is standing in the dark in the path of that entrance: a tall shape, perfectly still, closer than you thought.
    Then it is fast and brutal: Wither hearts, beaten down, the sword over you.
- **Build constraints:**
  - Carve with the krypt carve contract (as the Zombie door does), out of view before the first frame.
  - Scrap the shadow version (delete shadow.js if unused, remove the walk-stop logic).
  - Do not touch scares.js's start path or hud.js (another agent). Held item: use their loadout API if it has landed,
    else ask.
  - At most one FNAF device.
- **Review:**
  - Filmstrip and beat log against his words.
  - Full-size crops of "body in the opening, head above the lintel" and of the reveal, at 3 seeds and 2 depths.
  - Off-frame/dark proof for each first sighting.
  - Live J run of 16, no leaks.
  - Rank its fear against the Enderman and Creeper.
Also for the Zombie (owner): "Also the player should try to back up and run from the zombies instead of just standing
still." When the door breaks: stumble back a step or two, turn and run (FOV kick, bobbing, ragged breath, a glance
back). The catch must make sense (a sprinting player outruns a 1.7.10 zombie): e.g. the others come from ahead (out of
the dark or round the corner; zombies come in groups), or a dead end / closed door, back to the wall. Never simply catch
up. Same review (filmstrip, beat log, occlusion proof, live J run).
### 8b progress
- [~] Wither rewritten (`witherskeleton.js`, uncommitted; new helper `scares/chase.js`: poly/bez/runProfile/bob/bakeMany).
  Layout: flee direction d (usually back the way you came, the mouths behind the start view so the carve never shows),
  A (1x2, LA 4) at kA 4-10 rows, B (1x3) dB 3-4 rows further, room 5x(dB+3)x5; fallback LA3/RW4/RH4. Solid shell checked
  (mouth block may sit at a wall step). Carve verified after (windowless chunks), else restore + next.
  Probes (scratch `ws8b/probe_*.json`, `wsprobe.js`, `wsmap.js` ASCII map): 0.42 ok, 0.8 ok, 0.1 ok, 0.6 ok; 0.3 (classic hall,
  alcoves every 4 rows) failing, being relaxed. Carve cost 0.5-1.2 s uncontended (3 remeshes): score penalises chunks.
  Timeline ~21-24 s: rattle 0.6, run ~3, dive ~5.5, shoves, still 1.6 s (silence), peek, away, calm 2.2, room, cue, reveal.
- [x] Wither tuned: it waits hidden in an alcove/side way off the corridor (bodyHidden from the start eye) and steps out
  after the rattle; the look back aims at it; K (where it waits) is in the room beside B's mouth in B's torchlight
  (lightB), out of sight of A and of the walk; PR drifts away from B. Crops `ws8b/cr/cr08_s1-3.png`, `cr042_s1-3.png`,
  `cr03_s1-2.png` read well (body in the opening headless, peek under the lintel, reveal by the lit doorway).
  Machine heavily loaded by other agents (load 30+): carveMs 0.6-8 s measured; door-sized carve 130-390 ms same page.
- [x] Wither films `ws8b/film_{0.42,0.8,0.3}` (seed 2): every sighting off frame/occluded before (`appear.py`); a sword
  sliver showed during the walk into the room (17.2 s) -> K now chosen by a walk-visibility test (`showsAt`), re-film due.
  Wither refactored onto chase.js (`blocks`, `startView`, `hidden`, `sideSpots`).
- [~] Zombie rewritten for the flight (uncommitted): stumble back, turn, sprint (bob, FOV, ragged breath), one look back,
  modes: `ahead` (two step out of a side way/alcove/bend ahead, hidden from the first frame; you skid to a stop),
  `dark` (they come up the long corridor out of the dark, drawn only once the head is on the door), `end` (corridor ends,
  back to the wall, the others out of the door passage). z1 never catches a running man: tGrab >= your turn back.
  Probe (`probe2.js ...&scare=zombie&id=Zombie`): 0.3/0.42/0.8/0.6 `ahead`, 0.1 `dark`. Film `ws8b/zf042.json` running.
- [x] Zombie films `ws8b/zf_{0.42,0.1,0.8}.json/.png` (seed 1): all sightings off frame/occluded before. Fixes since:
  the others close in only after the grab (v2), shallow hiding spots first (`sideSpots`), an `ahead` spot must also be
  out of sight from the run until they move (`seenRunning`) else `dark`; `dark` = a stride or two, they are there.
  Wither: `held: null` (no hand drawn; loadout.js HELD.WitherSkeleton "sword" is the other agent's, tell coordinator).
  check_sounds: 0 missing. Re-film zombie 0.42/0.8 after the seenRunning filter; Wither crops `ws8b/cr/wcr_*` running.
- [x] Wither crops `ws8b/cr/wcr_0.42b_s1-3.png`: the look back now shows it running after you down the corridor.
- [~] Zombie: `ahead` spots seen during the whip turn at 0.42 (zf2) -> `seenRunning` now also tests backing (eyes on
  the door from 0 and P1) and the whip sweep from run0 (door yaw to 0); ahead ones move only as you come level
  (t0 = tSee-0.35). Probe `ws8b/zp3_*.json`, films `ws8b/zf3_{0.42,0.8}` running (bg).
- [x] Full-size push/reveal crops `ws8b/full/wfc_{0.42,0.8}_s1-3.png` (centre 706 px of w=1366): the body fills the
  opening with the skull above the lintel; the reveal stands by the lit doorway, eyes lit, ~2 m. Read well.
- [~] Zombie: the early sightings were the ahead ones walking OUT too soon (t0 led by their walk), not the spots. Now
  t0 = tSee-0.2 minus `hidLen` (how far along their way out they stay unseen from start settle, backing, whip and the
  early run) / V_O; spots also rejected if seen in the opening settle (0.3 had a 6% sliver at 0.4 s). zf3 stale.
  Films `ws8b/zf4_{0.3,0.42,0.8,0.6}` running (bg).
- [x] Pixel proof (`pix.js`: render with/without the mobs, diff): film.js's "visible" at t=0 (0.6, 2%) and 0.4 s (0.3, 6%)
  were empty corners of the box, 0 px. 0.42 had a real 16x21 px dark patch (a head edge) at 6.7 s in the whip ->
  `sees` now tests the outline as seen (both edges at three heights, the arms reaching at you), finer LOS, and a 0.3 m
  margin on the walk out: first pixels now at 7.2 = tSee (`ws8b/pix2_0.42.json`, `ws8b/pix/q042_s1_7.2.png`).
- [x] Films `ws8b/zf6_{0.42,0.6,0.3,0.8,0.1}.json/.png`: ahead at 0.3/0.42/0.6/0.8, dark at 0.1; beats read (door,
  break, whip, run, look back at it, two step out ahead, skid, turn back, it is on you). Every box-grid sighting before
  tSee is off frame/occluded before; the early ones checked by pixels are 0 px (0.42 s2 first pixels 7.4 = tSee 7.44,
  `ws8b/pix3_0.42.json`).
- [x] Live J run of all 16 (`node tools/site/scare_flow.mjs`, `ws8b/flow_all.json`): no flashes, no leaks, no
  exceptions (machine at load ~30: fps 2-12, Wither worst gap 3.7 s, Creeper 9.2 s).
- [x] Journal entry; commit of own paths (witherskeleton.js, zombie.js, chase.js, shadow.js removed, this file, journal).
- [ ] Report (five lines): Wither fear rank vs Enderman/Creeper; loadout.js HELD.WitherSkeleton "sword" is stale.
### 8b fix: the Wither opening (coordinator, after review)
Owner/coordinator: the player stood frozen ~3 s while it walked from 9 m to 3.9 m. Wanted: a 0.4-0.6 s freeze once it
squares up and walks at you, then back off (unsteady steps, breath up, view on it), turn and run at ~6-7 m; the chase
still fair (it never gains on a sprint), in just in time; sooner welcome. loadout.js is done by the coordinator (null).
- [x] witherskeleton.js: it steps out at V_OUT 2.4 right after the rattle (tM0 = tSay+0.2), walks at you at V_ON 1.9;
  tF0 = max(head on it, squared up); freeze vary(0.5, 0.2); back steps (vary 0.4 m / 0.5 s each, head dip and rock,
  breath loop from tB0) along the first of the run path, at most straight-3.2 m; run when it is gapR ~6.5 m off (at
  least two steps, or one if it is already 5.2 m); then it runs (V_CH 2.8-4.4, a 0.4 s pick-up) so you are in and
  round 1.3 s before it reaches the opening. Probes `ws8b/wbp_*.json`: gap at run 6.0-6.4 at 0.42/0.8, 5.2 at 0.6
  (closest spot, 7.1 m at square-up); tRun 3.3-4.4 (was ~4.05 after 3 s of standing); dur 24.0-25.9.
  (A probe once threw "no rock" at 0.42 s2: the demo page's start point drifts between builds in one page; a fresh page
  passes. Pre-existing, the live path returns false and cleans up.)
- [x] Films `ws8b/wf9_{0.42,0.8}` + back-off crops `ws8b/cr/wbk_*`: reads (out sideways, squares up ~9 m, frozen,
  closer, the whip at ~6.5 m). Live J run x2 clean (`ws8b/flow_wither.json`). BUT pixels (`pix.js`) showed its stone
  sword poking out of the alcove at t=0 at 0.42 (900 px; the box check of the spot never covered the sword) -> it now
  waits turned away into its dark and turns at the rattle (tM0..tMw 0.35 s): 0 px until 1.0-1.1 s (`ws8b/wpix2_0.42.json`).
- [x] Step-out at 3 m/s (less standing while it comes out sideways). Final films `ws8b/wf11_{0.42,0.8}` (2 seeds):
  first sightings 0.95-1.5 s occluded/off frame; tF0 1.7-2.6, run 3.3-4.4 s at 6.4-6.7 m, lead 1.3 s, V_CH 3.7-4.0,
  dur 24.0-24.9. Pixels 0 px to 0.9-1.0 s (`ws8b/wpix3_0.42.json`). Back-off crops `ws8b/cr/wbk3_0.42_s2.png`,
  `wbk2_0.8_s2.png`. J runs of the Wither x2 three times clean (one 10.5 s frame stall at load ~40).
- [x] Journal, commit of witherskeleton.js + this file + journal with `git commit -- <paths>`.
- [ ] Report.
