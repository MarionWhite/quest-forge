# site-r8-scares-c (checkpoint, started 2026-10-27, Mac)

Brief: `ops/briefs/site-3d-page.md`. Agent: opus (horror direction and building).
Owns: `site/graves/scares/skeleton.js` and any new helper file you add. Do not touch `scares.js`'s start path or
`hud.js`: the scares-b agent is fixing a mob flash at the J press and making the hotbar match the held item (use its
loadout API once it lands). The scares-a agent is redoing `witherskeleton.js`. Commit only your own hunks.
Previous state: `site-r7-scares.md` and `site-r8-scares-a.md` (tools: trace.js, scareflow, filmstrip and beat log,
the proof that mobs are off frame or dark before they first show). Spec: `docs/design/site/krypt-scares.md`.

## Owner's words (2026-10-27, round 8b)
- "the normal skeleton is quite boring and low quality" (full redo).
- He chose "Bone pile": an ossuary room heaped with bones and skulls. As you cross it, the bones rattle and a
  skeleton stands up out of the pile. Then another, and another, all around you, bows drawn.
- On the Wither redo, same day: "Make it scary". That is the bar here too.

## Rules (from the owner's notes this round)
- No mob pops into view: every skeleton is inside its heap (occluded) until it rises out of it.
- The camera only turns for a reason the viewer can perceive (a rattle behind you, a skull rolling).
- Nothing waits for the player to look back. Every sound and loop stops at the end and on Enter.
- Minecraft 1.7.10 look: bone items, skeleton skulls (a 1.7.10 block) and the skeleton model with its bow. There is
  no bone block in 1.7.10. Mobs wear the local Patrix skin when present (`?vanillaskins` for A/B).

## Done means
- [ ] The room: the walk enters an ossuary, either a real one nearby in the plan or a side room carved with the
  carve contract before the first frame, out of view, and restored after. Heaps of bones and skulls on the floor
  and in wall niches, with a builder's logic, lit by little.
- [ ] The beats, scary first: crossing in near silence, bones clattering underfoot; a skull rolls off a heap by
  itself; the player stops; the rattle; one heap shifts, a hand, then a skeleton stands up out of it with bones
  sliding off; you back away; a rattle behind turns you to a second one rising; then more all round, too many; the
  bows come up together, a silence; the volley (arrows thud in, arrows stuck in view, knocked down); one walks up
  and the last shot comes point blank. Death.
- [ ] Review: filmstrip at 5 frames per second and a beat log beside his words; full-size crops of the first rise
  and of the ring of bows; 3 seeds and 2 depths; proof that each skeleton is occluded the frame before it shows.
  Live J run of all 16 with no exceptions and no leaks (`tools/site/scare_flow.mjs`). One Chrome at a time.
- [ ] Rank its fear against the Enderman and Creeper. Commit your own paths, journal line, report in five lines.

## Progress
(write after every step)
Scratch: `scratchpad/r8/scares-c/` (film.js, film.py, crop.py, probe.js, cdp.mjs copied from r8/scares-a and orch).
- [2026-10-27] Read brief, track, scares-a checkpoint, rig/common/story/fnaf/door/old skeleton, krypt carve+bake.
  Design: new helper `scares/ossuary.js` finds a spot beside the corridor (doorway 1x2 in the side wall behind-beside,
  out of frame at the start pose and through the settle; a rock-cut room ~7x7x3 behind a 1-2 block wall, its shell
  checked solid; graves and torches avoided), carves it in build (restore on dispose), heaps of bone items + skull
  blocks over a dark core (the core is the occluder: S.solid), wall niches with skulls, one copied Krypt torch on the
  far wall. Beats: a faint clatter from the doorway turns you; you cross to it, look in, walk in slowly (bones
  underfoot, one kicked); a skull rolls off the far heap; you stop; the rattle; the heap shifts, a hand, it sits up
  and stands, bones sliding off; you back toward the door; a rattle behind: the second rises by the doorway; more
  all round; bows up together; silence; the volley (misses stuck in walls/heaps, hits knock you down); one walks up;
  point blank. No bowstring creak (not 1.7.10).
- [x] `scares/ossuary.js` (new): findRoom (doorway 1x2 in a side wall behind-beside, out of frame through the settle;
  room up to 7x7x3 behind 1-2 blocks of wall; shell all rock; graves/torches avoided; solidity cached) fits at 10 of 11
  depths probed (0.05..0.9; misses: 0.65 'worn' jagged walls, now relaxed). buildRoom: carve (doorway, room, niches),
  copied-geometry Krypt torch + PointLight on the far wall, up to 6 heaps (bone items as 1.7.10 2D-extruded sprites,
  skull blocks, a dark core = the occluder), floor scatter, niche skulls, rollSkull, kicks, riser(i, mob, sch): lying
  on its back in the heap -> hand -> sit up (hip fixed) -> stand (feet planted), pieces released where the body passes.
- [x] `skeleton.js` rewritten on it (first film runs: f1.json at=0.42 seed 1; dur 24 s: too long, tighten to ~18-19).
  Python with PIL: `/opt/anaconda3/bin/python -I film.py RAW OUT cols`.
- [x] Iterated on films f2..f4 and full frames g1..g3 (scratch). Fixed: heaps were black blobs -> paraboloid cores with
  a 64px bone-pile texture (planar UVs), lumps outward only, more pieces, skulls facing the room; near heaps long
  enough to hide a skeleton (L>=1.3); skeleton lies lower; the room's stop deeper (closer to the first riser); H2 steps
  into the doorway's way; bows-up framing picks the yaw that shows most of them; misses stick in view; the head looks
  back up at the heap after the skull stops; look targets are pure functions of t (dump-safe); findRoom has a relaxed
  second pass (zq -7.5..2.5, T up to 3, rooms down to 4x4). Proof (film3.js samples each part's box, LOS step 4 cm):
  every riser first on screen after it starts to rise, occluded/off frame the step before (f4).
- Tools: `film3.js` (proof on part boxes), `film2.py` (chunked JPEG sheets), `grab.py` (full frames), `crops.py`
  (1:1 crops), `dbgvis.js` (which part is in sight), `probe_many.sh` -> probe_many.txt (room fit over 17 depths).
- Next: read probe_many.txt (fallback if misses); review films 3 seeds x 2 depths + crops; scare_flow live run; commit.
- [x] Room fit: `probe_walk.js` (one page, 21 spots +-30 m along the corridor): 0.5 21/21, 0.66 ('worn') 19/21, 0.86
  14/14 after a third pass (zq -16..2.5, no flat test, 0.22 m path margin) and a summed-area shell check (<400 ms).
  Misses (~4%, riddled 'worn' rock): build throws "no room for the ossuary here" -> the picker plays nothing. Report it.
- Next: review films at 0.3 and 0.8 (seeds 1-3) + 1:1 crops (marks hand,sit,stand,behind,bows,volley); live run.
- [x] Review at=0.3 seeds 1-3 (scratch review/film_at0.3, proof_at0.3.txt): proof clean on all 12 risers (occluded or
  off frame the step before; Skeleton#0 = R1, #2 = R2 behind). Sheets read: skull roll, hand/sit/stand, R2 close
  behind, bows (2-3 in view against the torch), volley, fall, point blank, death screen. at=0.8 rendering (00:36).
- Next: proof_at0.8; crops_run.sh; README beats; scare_flow --only Skeleton then all 16; commit; journal; report.
- [x] Fixes after the first review set (01:35): the hand didn't read (straight up it stayed under the crest, and the bow
  in it was a big dark sprite): the clawing arm is now the one on the room's side, reaching up and out of the heap's
  flank; the bow lies in the bones (hidden) until the hand is back down inside the core (found at build, notes.bowIn),
  then comes up with it. Hand beat 0.6 s (was 0.45). One FNAF scream only (dropped the one at the volley).
- Running: scratch `final_run.sh` -> review/film_at{0.3,0.8}, proof_at*.txt (.films_done), crops_at*_s*.png
  (.crops_done). Old set in review_old/. Then: README beats (times shift ~+0.2 s), scare_flow, commit, journal, report.
- [x] Committed 571122b (skeleton.js, ossuary.js, this checkpoint). Proof at=0.3 (new code) clean on all seeds.
- Next: proof_at0.8 + sheets (review/film_at0.8), crops (.crops_done), README beats, scare_flow (--only Skeleton, then
  all 16), journal line + commit, report.
- [x] Review set done (scratch review/): film_at{0.3,0.8}/Skeleton_s{1,2,3}_part0N.jpg + _log.txt, proof_at*.txt (clean:
  every riser occluded/off frame the step before it shows), crops_at{0.3,0.8}_s{1,2,3}.png, README.txt (beats table).
- Next: scare_flow all 16 (--out scratch flow_all.json), journal line + commit, report.
- [x] scare_flow all 16 (02:21): ok, no flashes, no leaks, no exceptions (Skeleton 20.95 s, fps 9.1 on a machine shared
  with two other renderers). Journal line added. DONE.
