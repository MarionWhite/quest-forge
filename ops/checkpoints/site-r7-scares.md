# site-r7-scares (checkpoint, started 2026-10-27, Mac)

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
- [ ] **Enderman and Creeper are approved** and in `approved.json`. Do not change how they look or play. If
  shared code changes (`fnaf.js`, `common.js`, `rig.js`), snapshot their current timing and effects first,
  then check frame by frame that they are unchanged.
- [ ] **Pigman:** keep everything, but loosen the FNAF effect: less static, screen tear, chromatic split and
  head jitter. The lunge becomes a physical step and strike in the world rather than a glitch.
- [ ] **The other 11 plus the 2 gap deaths:**
  - Rebalance toward the Story Mode cinematic: in-world staging, mob behaviour, timing, sound, blocky gore.
  - Use FNAF devices (static, tear, jitter, face-into-lens lunges) sparingly: at most one subtle device per
    scare, and only where it serves that mob.
  - Each scare should scare through situation and the mob's own nature, the way the Enderman (the stare
    and teleport) and the Creeper (the silent arrival and swell) do. Study why those two work, and apply it.
- [ ] **Screams:** the audio task is replacing `qf.scare.death_scream`, `scream`, `jumpscreech` and
  `underwater` with real recorded voices. Keep the names, and prefer `death_scream` over the screech.
  Re-check the mix when they land.
- [ ] Sheet, plus a live J run of all 16 with no exceptions. In your report, rank each scare's
  fear against the Enderman and Creeper.
