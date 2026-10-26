# site-r6-krypt-gen (checkpoint, started 2026-10-26, Mac)

Brief: `ops/briefs/site-3d-page.md`. Agent: sonnet.
Spec: `docs/design/site/krypt-endless.md`. Read it first.
Catalogue: `docs/design/site/krypt-structures.md`. The research task is writing it now. Start
on the architecture, and pull segment kinds from the catalogue as it lands.
Owns:
- all of `site/graves/*` except `scares.js`, `scares/*`, `tex/scare/*` and the new `mood.js` /
  `mood/*`;
- in `app.js`, everything except the marked scares and mood blocks.
Previous state: `site-r5-krypt-more.md`.

## Owner's words (2026-10-26)
- "I want this thing to be long enough to hold 1000 fucking graves, if not 10x that. We should
  build it all out now, and then we can set it up to extend with each death."
- "I want to drive the quality of dungeon up, and avoid repeats as much as we can. If we get to
  a point where it is the only option then that's fine to repeat, but draw on a lot of the
  structure design from the mod pack and keep staying creative."
- "At corners the path often breaks, like there is 3 blocks of lava or water. That's fine, but
  put something in the animation where the character jumps across the gap."
- He loves the scroll feel, the stone focus and the lighting. Don't regress them.

## Done means
- [ ] **First commit:** the contract additions from the spec (`gaps`, the `krypt-gap` event with
  `takeover`, `light.*`, `cornersNear`, stratum in `getWalk`), plus a marked mood block in
  `app.js`:
  `import("./mood.js").then((m) => m.initMood()).catch((e) => console.warn("mood", e));`
  guarded so a missing `mood.js` is harmless. Also the dt clamp and building chunks while a
  scare holds the player.
- [ ] **Streaming generator** for at least 10,000 graves: deterministic, chronological and
  append-only, with flat memory and draw calls. Measure the draw calls and the JS heap at
  graves 10, 1,000 and 9,000 of `?demo=10000`.
- [ ] **Strata:** 8 or more, with at least 40 segment kinds from the catalogue, parametric, and
  following the no-repeat rule. Script-check the no-repeat rule over the whole 10,000-grave
  layout.
- [ ] **Gap jump:** the jump animation plays, and a dump shows the mid-arc frame.
- [ ] **Navigation:** the depth gauge, "find a grave", Page Up and Down, and `?grave=N` all
  work at 10,000 graves.
- [ ] Phone performance is acceptable.
- [ ] Sheet: one frame per stratum, five more segment kinds, the gap jump at mid-arc, the find
  transition, and a phone frame.

## Progress log
- [x] Stage 0 (commit e2fd0ca): contract additions (gaps/cornersNear/light/krypt-gap plumbing/getWalk.stratum), mood import block,
  dt clamp, chunk build around camera while held. `light.*` = lightfx.js + dim spheres in patchBake/patchTorch (krypt.js).
  Gaps and strata are stubs ([] and index 0) until the generator lands.
- Architecture decision (stage 1): plan.js (deterministic plan: strata, legs, slots, gaps, path polyline, lookups) +
  chunk-window streaming in krypt.js (each 48x48 chunk generated from the legs that reach it, objects clipped to the chunk,
  passages decided at plan time) + kinds.js (dressers). Walk length = max(n, 60 slots) + runway; ?demo=1000|10000 synthetic graves.
- [x] Stage 1 (commit d826e67): streaming engine works. plan.js/geom.js/blocks.js/kinds.js/strata.js/demo.js new; krypt.js rewritten
  (makeWorld, chunk windows CH=48 MARGIN=16); dress.js = makeDresser; app.js on plan + world; gap pit + jump (position-based, camera
  offsets, krypt-gap event); rush transition (fog + blur) for far jumps; PageUp/Down strata; depth gauge #hudK; strata bands in the
  minimap above 300 graves. demo=10000 -> 81,303 blocks, 1369 legs, heap ~37 MB, 9-10 chunks, build ~25 ms/chunk (max 69).
  Only the 15 original kinds + frontier so far, one stratum. NEXT: strata + 30 new kinds, no-repeat script, nav checks, perf, sheets.
