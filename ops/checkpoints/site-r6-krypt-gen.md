# site-r6-krypt-gen (checkpoint, started 2026-10-26, Mac)

STATUS: done (2026-10-26, final pass: chasm lava sea 8 below the bridge with strong glow, void_bridge open to a dome of stars (end_sky tile + drawn stars, app.js K.endSky), library balcony lamps). 46 kinds, 12 strata, 10,000 graves in 79 ms of plan; `node tools/site/check_krypt_plan.mjs` passes (no-repeat, determinism, append-only). Sheets: scratchpad r6/krypt-gen/f1, f2, fin, fin2.
Open items for the owner/next round: water gaps look almost black; cycle name reads "Lower The Crypt"; stronghold portal side-room kind not re-implemented; draw-call/heap numbers at grave 9,000 and real phone timing not measured; gap-jump mid-arc and find-rush only checked by dump, not by CDP motion.
Requests: none.

Critic pass 1 (2026-10-26): kinds_c.js gives every kind its own alcove pillar/lintel tiles and a hall shape (vault, cavern, colonnade, catwalk, collapse, maze; widths 3-7, heights 4-9), adds maze_hall, collapsed_hall, void_bridge and portal_room (the End stratum's entry); the 11 round-5 kinds are all registered and in pools (sheet r5). Water gaps now carry a blue light. Cycle names read "The Crypt, second descent". `?free=1` + `?cam=` frames each kind down its hall (scratchpad gencam.mjs). Sheets (scratchpad r6/krypt-gen): k1, k2 (+ sheet_grey.png), r5, ph (phone).
Critic pass 2: kinds_d.js adds 12 open set pieces, one per stratum, forced by plan.js (def.set at stratum legs 4, 22, 46, 70): mine_crossing, labyrinth_junction, flooded_cistern, library_balcony, sand_chamber (blue clay, TNT pit), ice_cavern, mushroom_cavern, fortress_bridge, arena, chasm_open, void_bridge, hollow_hill; portal_room is now a room with tiers, a lava pool and side cells. Ordinary kinds get an asymmetry pass (ceiling dips, broken pillars, glimpsed side rooms, floor props) and plan.js jitters alcove spacing. Sheets: s2, s3 (set pieces, 3/4 view), o1 (ordinary kinds). Check script also asserts each stratum holds its set piece.
Metrics (demo=10000, desktop): grave 10: 52 calls, 5.8k tris, heap 33 MB; grave 1,000: 60 calls, 16.9k tris, 37 MB; grave 9,000: 85 calls, 17.2k tris, 28 MB. Phone 390x844 at graves 300/2,900/5,300/7,700/9,000: 23-93 calls, 4-16k tris, heap 28-33 MB. CDP real time: 60 fps (16.7 ms p95), gap jump lifts the camera 0.95 block and fires krypt-gap, the End rush crosses 99% of the Krypt in about 3 s with one 283 ms hitch while chunks build under fog.


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

Final re-measure (demo=10000): grave 10: 50 calls, 5.0k tris, heap 28 MB; grave 1,000: 83 calls, 16.4k tris, 62 MB; grave 9,000: 37 calls, 7.4k tris, 38 MB. Phone set pieces: sheet ph2 (chasm_open, library_balcony, void_bridge). Desktop set pieces: t1 (chasm_open), t2 (void_bridge), t3 (library_balcony). check_krypt_plan.mjs: OK.
