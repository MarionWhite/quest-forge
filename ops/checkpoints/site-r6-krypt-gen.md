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
