# site-r5-krypt-more (checkpoint, started 2026-10-26, Mac)

Brief: `ops/briefs/site-3d-page.md`. Agent: sonnet.
Owns: `site/graves/{krypt,dress,fx,kaudio,app}.js` (except the marked scares block in app.js),
`site/graves/index.html`, `site/graves/tex/*` (except `tex/scare`).
Previous state: `ops/checkpoints/site-krypt-world.md`.

## Owner's words (2026-10-26)
- "The Krypt is actually really close to polished. Every improvement is fucking landing and this
  thing is sick. The only things that need immediate improvement are the jump scare animations
  and just more dungeon."

## Done means
- [x] (DONE, committed) **Contract for the scares task, first** (they code against it):
  - `__krypt.carve(min, max)` removes the blocks in that box and rebuilds only the affected
    chunk;
  - `__krypt.restore()` undoes every carve;
  - `__krypt.solidAt(x, y, z)`;
  - `__krypt.blockAt(x, y, z)` returns a block name.
  Document them in the contract comment at the top of `app.js`, and commit before anything else.
- [ ] **More dungeon:** about twice the walk, with at least five new segment kinds in the same
  quality and lighting rules. Ideas that fit:
  - catacomb niches with skulls and cobwebs;
  - a cave-spider mineshaft with web tunnels;
  - a jungle-temple trap hall with dispensers, tripwire and levers;
  - a nether fortress bridge corridor;
  - an iron-door vault;
  - a stronghold end-portal room as the finale at the bottom.
  Keep the existing nine segments. Graves still sit in alcoves along the whole path, and the
  depth lighting table extends to cover the new length.
- [ ] Six to ten more bends and side passages, with collision checks as before.
- [ ] Phone performance stays acceptable: chunk build stays lazy and the draw-call count stays
  in the same range.
- [ ] Sheet: one frame per new segment, plus the full-path overview, a phone-width frame, and a
  carve demo (`?carve=x,y,z,w,h,d`, a debug hook).

## Done
- Contract shipped and committed (132d554): chunked lazy meshing (krypt.js meshGrid, CH=32, pump), makeCarver; app.js exposes
  __krypt.carve/restore/solidAt/blockAt, documented at the top; ?carve=x,y,z,w,h,d hook in runDump.
- Six new segments in krypt.js (SPEC, step per leg, PROFILE, WALLS 10-15) + dress.js decor: catacomb, spidermine (cave spider
  spawner, web tunnel), temple (dispensers, tripwire, levers), vault (iron doors, hoard), fortress (nether brick arches, fences,
  lava pits), stronghold (end portal room finale, vc/pathEnd). 15 legs, 14 bends, 9 side passages. Walk length 460 blocks (was ~235).
- Textures copied from 1.7.10 into site/graves/tex (furnace_side/top, dispenser front, lever, trip_wire(_source), door_iron_*,
  endframe_*, gold/diamond/lapis/emerald block, stonebrick_carved).
- Dress batches are per 32x32 cell (culled). Draw calls in dump (incl. ~20 post passes): 62-111, old frames were 40-74.
- Next: final sheet check, journal line, commit. Sheet: scratchpad r5/krypt-more/final/sheet.png, phone/sheet.png.
