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
