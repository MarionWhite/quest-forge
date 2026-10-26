# site-r5-scares (checkpoint, started 2026-10-26, Mac)

Brief: `ops/briefs/site-3d-page.md`. Agent: opus (creative horror direction and building).
Spec: `docs/design/site/krypt-scares.md`. Read it first; it is the owner's direction.
Owns:
- `site/graves/scares.js`, `site/graves/scares/*`, `site/graves/tex/scare/*`
- the marked scares block in `site/graves/app.js`
Previous state: `ops/checkpoints/site-krypt-scares.md`.

## Contract with the Krypt (krypt-more task)
`window.__krypt` will gain these:
- `carve(min, max)` rebuilds the affected chunk without those blocks;
- `restore()` undoes every carve;
- `solidAt(x, y, z)`;
- `blockAt(x, y, z)` returns a block name, for dressing pits like the segment.

Feature-detect them. Build the scares that don't need them first; the piston-trap scares come
last.

## Done means
- [ ] All 14 scares are rebuilt to the spec. They run in the real Krypt scene at the player's
  position, with no separate canvas and no teleport cut.
- [ ] The J picker and `site/graves/scares/approved.json` (empty) exist. The director uses only
  approved scares.
- [ ] Sounds use the `qf.scare.*` names in the spec (the audio task makes them) and the existing
  bank. `python3 -I tools/site/check_sounds.py` exits 0 once audio lands. Until then, list the
  missing names in this checkpoint.
- [ ] `site/graves/scares/test.html` is removed. All dumps run on the real page, in at least three
  segments.
- [ ] Sheet: 4 frames per scare (dread, hit, kill, death screen), 56 in all. Review it as a
  horror director: is this scary, does it make sense where the player stands, and is it
  accurate Minecraft?

## Done
(nothing yet)
