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
