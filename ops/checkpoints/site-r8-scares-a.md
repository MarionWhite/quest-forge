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
