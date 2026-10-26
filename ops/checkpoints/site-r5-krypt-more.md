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
- [ ] **Contract for the scares task, first** (they code against it):
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
(nothing yet)
