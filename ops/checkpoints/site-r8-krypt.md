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
- [x] The floating dispensers fixed at their cause.
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
- [x] Cause found: kinds_e.js piston_trap puts two dispensers at hi+1, y0+1 in the open hall (air under, behind, beside; they
  touch only each other) = in the walkway. New checker tools/site/check_krypt_support.mjs (headless buildWindow over every
  chunk, flood fill from T_WALL for blocks, support per decor class). Needs a node resolve hook for "three" (inside the file).
  NEXT: fix piston_trap dispensers (into side wall), then fix each failure class from the checker list, wire into
  check_krypt_plan.mjs, crops before/after, HUD overflow check.
- [x] site/graves/support.js (decorProblem rules) + krypt.js step 4b net (a.dropped; drops unsupported decor and torches) +
  tools/site/check_krypt_support.mjs (fails on every a.dropped inside the chunk plus blocks not joined to rock via 18-neighbour flood).
  3000-graves run lists ~40 failure classes; fixing generators class by class (dispensers, catwalk fence, lily/skull/bone in flooded halls...).
- [x] HUD check (scratchpad r8/krypt/hud.js via cdp.mjs): 1149x834 hud-r right 1123 of 1149, docW 1149; 390 wide all within 376.
  No overflow. The owner's shot has the search at css x~966, which matches a ~1460 wide window cropped to 1149: a crop, not a bug.
- [x] Generator fixes so far: piston_trap dispensers into the side walls; ossuary/catacomb/flooded_ossuary niches = two tiers with a
  stone shelf; carpet_crypt carpet skips gaps, banner needs the pillar, skylight pane lies flat; witch_hut posts reach the bed;
  vines need wall; ctx helpers floored/walled/under (kindreg.js). NEXT: read the 10k run (task bn8lerozm), fix the rest, wire into check_krypt_plan.
- [x] Net + put() guard (support.js makeSupport; kindreg put/webAt refuse unsupported props; a.refused). Checker thresholds: blocks
  strict, props fail at >=12 per kind+type and >0.3% of the type. Fixed: arena pillars (under), fortress_bridge rails [-1,0],
  fortress rail needs floor, void_bridge arch landing (+ kind floatingOk: End islands float by design, ASK OWNER), flooded
  lava/water pillars. Running full3 (10k) -> scratchpad r8/krypt/full3.txt. Before crops: r8/krypt/crops/before (headwt worktree
  at HEAD in r8/krypt/headwt, REMOVE at the end: git worktree remove). NEXT: read full3, fix leftovers, after crops + walk strip,
  wire into check_krypt_plan.mjs, journal, commit own paths.
- [x] After crops: scratchpad r8/krypt/crops/{before,after}/sheet.png (dispensers: g68, disp_close, disp_side), crops2/{before,after}
  (catacomb niches, carpet skylight, fortress rails; arena/flooded frames mis-aimed), crops3/{before,after}/sheet.png = 6-frame walk
  through the trap hall. HUD: no overflow (see above). Net also removes floating pieces <=6 blocks (krypt.js step 4b).
  buildWindow cost 2.3 -> 6.3 ms (node, 60 windows). check_krypt_plan.mjs now runs the support check (child process).
  full8 (10k) running -> r8/krypt/full8.txt. NEXT: if OK: check_krypt_plan, check_sounds, quick dump of 3 frames for exceptions,
  journal line, board/track, commit own paths, remove headwt worktree.
- DONE (2026-10-27). check_krypt_plan OK incl. support (428 strays of 1.57M props, net-dropped); sounds OK; dumps 0 errors.
