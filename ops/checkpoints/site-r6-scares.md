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
- [ ] All 14 scares have a FNAF lunge and a randomised build-up with fake-outs, per the v3 spec.
- [ ] The Magma Cube is redone, and the Wither Skeleton has a new ending.
- [ ] **Gap deaths:** Lava fall and Drowned grab are built, in the J picker, and hooked to
  `krypt-gap` at 15%, gated by `approved.json` like the rest.
- [ ] The kills use the recorded death screams once audio lands.
- [ ] Sheet: 5 frames per scare (dread, fake-out or tell, lunge, kill, death), 80 frames in all.
  Review it as a horror director.
- [ ] A live real-time run of all 16 through the J flow with no exceptions. The CDP driver is
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

## Next
- The 80-frame sheet (dump_frames --list --sheet, beats dread,fake,lunge,kill,death x 16), review; the real-time J
  run of all 16 (copies of scratchpad/orch/cdp.mjs and scareflow.js); journal line; final report.
