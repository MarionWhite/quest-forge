# site-r8-krypt (checkpoint, started 2026-10-27, Mac)

Brief: `ops/briefs/site-3d-page.md`. Agent: sonnet. Owns: `site/graves/kinds*.js`, `site/graves/blocks.js`,
`site/graves/app.js` (outside the scares and mood blocks), `site/graves/*.css`, `tools/site/check_krypt_plan.mjs`.
Previous state: `site-r7-krypt.md`. Spec: `docs/design/site/krypt-endless.md`, `krypt-structures.md`.

## Owner's words (2026-10-27, round 8)
- "I attached an image of dispensers that are just floating in the fucking air." The screenshot is at grave 68 of
  `graves/?demo=1000`: two dispensers side by side in mid-air at a dead end, a lit pillar behind, a pale slab strip
  on the floor. Probably the trap hall in `kinds.js` (around line 239: dispensers on both walls), placed where the
  wall was carved away.

## Done means
- [ ] The floating dispensers fixed at their cause.
- [ ] **Nothing floats, anywhere:** add a support check to `check_krypt_plan.mjs` over the whole plan (10,000 graves).
  A wall-mounted block (dispenser, lever, button, tripwire hook, ladder, wall sign, wall torch, item frame,
  painting) needs the solid block it hangs on. A floor block or prop needs something solid under it. Webs, vines,
  chains and hanging lanterns may hang from a ceiling. Fix every failure it finds, then it must pass.
- [ ] Close crops at each fixed spot, before and after, plus a walk filmstrip through the trap hall.
- [ ] The HUD at a 1149 x 834 window and at phone width: in the owner's screenshot, the "Find a name" box and the
  walk bar run off the right edge. If they overflow, fix it; if not, say so.
- [ ] `node tools/site/check_krypt_plan.mjs` OK. Commit your own paths, journal line, report in five lines.
  Chrome: one at a time (two other agents render too).

## Progress
(write after every step)
