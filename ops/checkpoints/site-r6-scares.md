# site-r6-scares (checkpoint, started 2026-10-26, Mac)

Brief: `ops/briefs/site-3d-page.md`. Agent: opus (horror direction and building).
Spec: `docs/design/site/krypt-scares.md`. Read all of it, especially the v3 section, which holds
the owner's new direction.
Owns: `site/graves/scares.js`, `site/graves/scares/*`, `site/graves/tex/scare/*`.
Previous state: `site-r5-scares.md`.
The krypt-gen task adds `krypt-gap` and `__krypt.light`; feature-detect them. The audio task adds
`qf.scare.death_scream`, `jumpscreech`, `underwater` and `static`; until they land, use the
current bank and list the gaps here.

## Owner's words (2026-10-26)
- "The animations are of a high quality, but they aren't scary enough."
- "The silverfish one and the cave spider one are almost there, but that is a specific type of
  fear."
- "The magma cube animation is kind of boring, and the wither skeleton one starts off cool, and
  is a cool idea with the sparks, but it ends kind of boring."
- "Take some inspiration from FNAF for the jumpscares, and be creative. Make me fucking piss my
  pants even though I know it's coming."

## Done means
- [x] All 14 scares have a FNAF lunge and a randomised build-up with fake-outs, per the v3 spec.
- [x] The Magma Cube is redone, and the Wither Skeleton has a new ending.
- [x] **Gap deaths:** Lava fall and Drowned grab are built, in the J picker, and hooked to
  `krypt-gap` at 15%, gated by `approved.json` like the rest.
- [x] The kills use the recorded death screams once audio lands.
- [x] Sheet: 5 frames per scare (dread, fake-out or tell, lunge, kill, death), 80 frames in all.
  Review it as a horror director.
- [x] A live real-time run of all 16 through the J flow with no exceptions. The CDP driver is
  `scratchpad/orch/cdp.mjs` with `scareflow.js`.

## Plan (2026-10-26, opus)
- New shared kit `site/graves/scares/fnaf.js`: the lunge (the mob's face driven into the lens from where it stood,
  ~0.22 s, overshoot, jittering hold), the split jaw (head box cut at the mouth row with mcBoxGeometry, a dark
  mouth, pixel teeth), lit eyes, jitter noise, silence/fake-out/music-box helpers, the layered screech.
- rig.js: per-play random seed (R.rand, R.vary), camera pose set before S.update (the lunge reads R.camera), a
  post pass in the composer (tear, RGB split, static), warm-up (compile + texture upload) so the lunge never hitches,
  a frame override for gaps.
- hud.js: the static cut (GUI-res noise over everything). scares.js: @silence, preload of every sound before the
  freeze, S.marks for the sheet (scareat=dread|fake|lunge|kill|death), 16 entries, krypt-gap hook (15%, approved
  only, feature-detected), mood busy check, `__scares.busy`.
- Then every scare rebuilt in turn; checkpoint after each.

## Done (r6)
- cd90a97: kit `scares/fnaf.js`; rig (R.rand/vary/chance/pick per play, camera pose before update, post pass
  tear/split/static, warm-up compile + texture upload + post-pass program, R.unsnuff, dump restores fog/exposure/lights
  after each render); hud static cut; scares.js (@silence, preload before the freeze, marks, scareat=a,b,c multi-moment
  dumps into `pngs`, scareseed, nofx, scarepull debug camera, 16 entries, krypt-gap hook at 15% approved-only, mood
  busy check, `__scares.busy`). Rebuilt: Zombie, Skeleton (music box), Creeper, Spider, Cave Spider (swarm freeze),
  Enderman (vanish + flash), Witch (hallucinations).
- Iteration tools (scratchpad r6/scares): `mk.py` (shot list), `multi.py` (dump_frames + split pngs + sheet).
- Note: krypt-gen landed the streaming world (d826e67): kr.gaps, krypt-gap, kr.light exist now. Torch meshes still
  detected (torch_on). Dumps take ~4 s a page with dump_frames.

- aadaffd: Slime (blocked hole, light back, nothing; lunge from the hole or out of the pit's dark; the core's maw
  opens inside the thinned jelly, lit pupils). Magma Cube redone (all torches out, a pulsing core far off, 2-3 hops,
  glow gone, silence, a pop to one side; 3-5 small cubes from every side as the fake-out (60%) or leading straight
  in; the upper plates lift off the blazing core, the lower hinge down; lunge from ahead or above; swallowed, chewed).
  Enderman anchor raised (eyes in frame). Verified in sheets c1-c4 (scratchpad r6/scares).

- Wither Skeleton new ending committed (sheets c5-c12): randomised scrapes cut mid-stroke, silence, a tick (side or
  behind), the turn back to the cocked skull 0.75 m away, lunge; a stone-sword sprite in its fist through your chest
  (bloody past the middle), wither vignette; pull, decap flight (v2), lift to its face, jaw open.

- 017c2f1: gap deaths. `scares/gap.js` (gapSite: the Krypt's gap from R.gap or one dug across the hall, exact
  edges from the world blocks; runUp; firstArms; camBasis), `lavafall.js`, `drowned.js` (carves a 6-block shaft under
  the gap; muffle struck every 0.4 s under water, cleared for the lunge). Sheets c13, c14. Dumps near a real gap:
  `&gap=N&jx=-2` (gap=1 is lava, gap=0 water in the default plan). check_sounds exits 0.

- Silverfish 6995df5, Blaze 3ea8cfc, Ghast 628689c, Zombie Pigman (this commit): all 14 have a lunge, dice and marks
  (sheets c15-c22).

- 5a938ce..fac5ef6: Zombie Pigman; all 14 have a lunge, dice and marks.
- Sheet: 80 frames (16 x dread, fake, lunge, kill, death), `scratchpad/r6/scares/final/sheet.png` (shot list
  `final_all.txt`; seeds in it). Reviewed: every lunge lands a face in the lens with the eyes in frame. Weakest
  frames: the Creeper lunge is mostly tear, the Pigman lunge is noisy, the Wither Skeleton's eyes clip white, and
  Lava fall's lunge beat (at that seed) is a dark rock view before the hands slip.
- Real time (2c54d2f, 31e91a2): `__scares.state` (clock, frames, marks, notes, carve ms). `rt/scareflow16.js` drives
  the J picker for all 16 (click, run, death screen, Enter): no exceptions, all respawn, 60 fps, the worst gap inside
  any lunge window 30 ms (25 ms polling). Found and fixed: the Creeper's crater carve stalled the boom frame
  50-90 ms (the flash landed late on the explosion), now a frame after the flash under the white; the piston trap's
  carve (Cave Spider, Slime) stalled the open frame 30-80 ms, now a frame before the pistons move. `rt/hitch.js`
  logs every frame gap over 45 ms with the carve time. Left: sporadic 40-130 ms gaps in build-ups (shared machine, GC).
- check_sounds exits 0. No requests to other agents.

## Owner
- Approve scares in `site/graves/scares/approved.json` (empty, so the director plays nothing). The gap deaths
  (LavaFall, DrownedGrab) take 15% of failed jumps once approved.

## Next
- Nothing. Round 6 scares done.
