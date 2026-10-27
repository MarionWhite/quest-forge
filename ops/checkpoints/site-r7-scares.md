# site-r7-scares (checkpoint, started 2026-10-27, Mac) - DONE 2026-10-27

Brief: `ops/briefs/site-3d-page.md`. Agent: opus (horror direction and building).
Owns: `site/graves/scares.js`, `site/graves/scares/*`, `site/graves/tex/scare/*`.
Previous state: `site-r6-scares.md`. Spec: `docs/design/site/krypt-scares.md`.

## Owner's words (2026-10-27)
- "The FNAF inspiration was taken too strongly and now the only 2 animations that I am fully happy with are
  the enderman and the creeper."
- "The pigman one is almost perfect, but just loosen up on the FNAF effect for it."
- (Round 4, still the brief) Minecraft Story Mode quality, gruesome like Mortal Kombat, scary, on brand per
  mob, staged where the player is.

## Done means
- [x] **Enderman and Creeper are approved** and in `approved.json`. Do not change how they look or play. If
  shared code changes (`fnaf.js`, `common.js`, `rig.js`), snapshot their current timing and effects first,
  then check frame by frame that they are unchanged.
- [x] **Pigman:** keep everything, but loosen the FNAF effect: less static, screen tear, chromatic split and
  head jitter. The lunge becomes a physical step and strike in the world rather than a glitch.
- [x] **The other 11 plus the 2 gap deaths:**
  - Rebalance toward the Story Mode cinematic: in-world staging, mob behaviour, timing, sound, blocky gore.
  - Use FNAF devices (static, tear, jitter, face-into-lens lunges) sparingly: at most one subtle device per
    scare, and only where it serves that mob.
  - Each scare should scare through situation and the mob's own nature, the way the Enderman (the stare
    and teleport) and the Creeper (the silent arrival and swell) do. Study why those two work, and apply it.
- [x] **Screams:** the audio task is replacing `qf.scare.death_scream`, `scream`, `jumpscreech` and
  `underwater` with real recorded voices. Keep the names, and prefer `death_scream` over the screech.
  Re-check the mix when they land.
- [x] Sheet, plus a live J run of all 16 with no exceptions. In your report, rank each scare's
  fear against the Enderman and Creeper.

## Progress (opus, 2026-10-27)
Scratch: `scratchpad/r7/scares/` (serve.py on :8765, pid in serve.pid; tools mk.py, multi.py, sheet2.py, rt/cdp.mjs,
rt/scareflow16.js, rt/trace.js, cmp_trace.py).
- Baseline for Enderman and Creeper: `base_trace.json` (rt/trace.js at `graves/?demo&at=0.3&trace=Enderman,Creeper`,
  seeds 1-4: camera, frame fields, every visible object, sounds, loops on a 0.05 s grid). Deterministic run to run
  except the first 0.9 s camera settle (cmp_trace.py ignores it). Re-run and `cmp_trace.py base_trace.json new.json`
  after any shared change.
- Why those two work: the scare is the mob's own vanilla mechanic (the stare and the teleport; the silent walk-up,
  the hiss, the swell, the white flashes), every sound is the mob's, the one glitch is diegetic (teleport), the "lunge"
  is short and motivated (it teleported to arm's length; it was already behind you), and the kill leaves a mark in the
  world (the lava chasm, the crater, the hotbar scattered) with an aftershock (the fall, the second hiss).
- Kit: `scares/story.js` (roar, blow, kick, impactSplit, hop, faceOf). Shared fnaf/common/rig untouched so far.
- Dumps: dump_frames needs `--budget 60000` now (multi.py passes it); a page sometimes misses its hook on the
  busy machine, rerun it alone.
- [x] Pigman (66ce321): pick lands, head snaps round, a beat staring over his shoulder in the hurt tint, he turns
  square, arms drop, steps in to 0.6 m, sword wound back over his head and chopped down on yours (kick, blood up into
  view, stagger); then the horde as before. No lunge/screech/tear/static; impactSplit 0.25 on the blow; eyes 0.45.
  Frames `pig3/sheet.png` (shots `pig1.txt`, seeds 1-3 at at=0.3/0.55/0.8). Real-time check still to do (J run).
- [x] Zombie: the look-back to arm's length (a, 45%) or the walk out of the dark while you back into a second one
  with hands over your shoulders (b). Frames `z1/sheet.png` (all beats, seeds 1-4), `z4/sheet.png` (bite distance).
- [x] Skeleton: lights die (its one device), bones rattle, the miss into the wall, the creak, the standoff in the last
  light or beside you, the shot. Frames `sk1/sheet.png`, `sk2/sheet.png`.
- [x] Spider: crawls the ceiling to above you (or bare), the drop in front of you, the thump, the rear and hiss, the
  leap onto your face. Frames `sp1/sheet.png`, `sp2/sheet.png` (leap tracked).
- [x] Cave Spider: freeze kept as the one device; the click, the one on the pit wall rears and leaps onto your face.
  Frames `cs1/sheet.png`, `cs3/sheet.png`.
- [x] Witch: Slowness at your feet, she walks up, Poison on your chest (kneel), she bends over you, silence, Harming
  in your face. Frames `wi2/sheet.png`, `wi3/sheet.png`.
- [x] Slime: squeezes through the hole and drops on you, or sits in the pit and hops onto you. Frames
  `sl1/sheet.png` (hole branch), `sl3/sheet.png` (hop branch). Weakest of the set by nature (its size fills frames).
- [x] Silverfish: infested wall, cracks, the stall kept; the wall bursts into the swarm (no big one at the lens).
  Frames `sf1/sheet.png`.
- [x] Blaze: rises, floats out, flares (tell), three shots (wall, feet, you), burning, it follows, second volley.
  Frames `bl1/sheet.png`.
- [x] Ghast: the face rises (or is there on the look-back), the charge, the fireball across the drop. Frames
  `gh1/sheet.png`.
- [x] Magma Cube (4b7b2b2): power-out and the heart kept (its one device); hops in with its slices spreading in the air
  and the core lighting the corridor; sits pulsing; the pop, small ones hit you (70%); it squats and leaps, fanned
  wide, and comes down on you as you back away; the slices shut. Frames `mc2/sheet.png`, `mc4/sheet.png`, `mc3` (smalls).
- [x] Wither Skeleton: black fog kept (its one device); the drag, the stop, the tick; turning back it stands over you
  at 2 m, the look up its ribs to the skull, the rattle, the stride in and the thrust; the blade, decapitation, and
  at the end it looks at your head as the Wither black closes in. Frames `ws1/sheet.png`, `ws2/sheet.png` (strike).
- [x] Lava fall: already physical; stingers and the slip screech removed (sound only).
- [x] Drowned grab: the peek is a shape drifting far down (no frame-flash); it has your ankles, climbs your legs, bites
  your side, drags you down (no clear-sound screech, no lens lunge). Frames `dr1/sheet.png`, `dr2/sheet.png`.
- [x] Enderman/Creeper: `git diff 66ce321^ HEAD` is empty for enderman.js, creeper.js, fnaf.js, common.js, rig.js,
  hud.js, director.js; scares.js changed only in the sound player (below) and Magma Cube's label. The re-run trace
  differs from `base_trace.json` only because the world under `?demo&at=0.3` changed (krypt a84e267: segment
  classic -> carpet_crypt, new props), not the scares.
- [x] Screams: the new takes run 2 to 4.5 s (-12.5 to -18.4 LUFS, peaks -1 dBFS), and most scares call
  `deathScream` twice 1 to 2 s apart, which put two different men screaming at once. `scares.js` now drops a
  death_scream that would start while one still sounds (d96ccc9); probe: one start per scare. Creeper and Enderman
  keep their screech (approved); Pigman keeps its one stinger on the horde.
- [x] Sheet: `scratchpad/r7/scares/all/sheet.png` (16 rows: dread, fake, lunge, kill; every shot dumped).
- [x] J run (`rt/flow_r7final.out`, rerun `rt/flow_r7b.out`): 16/16 entered and came back, no exceptions, 59.4-60 fps,
  lunge gaps 28-48 ms. Creeper's ~125 ms hitch at the explosion is pre-existing (round-start flow1/flow2: 129 ms),
  the crater carve; left alone as the Creeper is approved. Wither Skeleton 206 ms and Lava fall 110 ms did not repeat
  (33, 34 ms on the rerun).
- [x] `node --check` on .mjs copies of all 18 touched/approved modules; `check_sounds.py` exit 0 (189 names, 0 missing).
- [x] Spec: `docs/design/site/krypt-scares.md` v4 section (efa6325). Journal line (58e1108).
- Fear vs Enderman/Creeper (agent's ranking, owner to judge): near them: Ghast, Pigman, Wither Skeleton, Blaze;
  a step below: Spider, Zombie, Magma Cube, Witch, Skeleton, Drowned grab; lower: Cave Spider, Silverfish, Lava fall,
  Slime (weakest by nature).
- Next round: the owner plays the 14 in the J picker and approves or names what is off.
