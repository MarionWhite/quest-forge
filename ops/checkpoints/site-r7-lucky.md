# site-r7-lucky (checkpoint, started 2026-10-27, Mac)

Brief: `ops/briefs/site-3d-page.md`. Agent: sonnet. Owns: all of `site/lucky/*`, `tools/site/nav_check.py`.
Previous state: `site-r6-lucky.md`.

## Owner's words (2026-10-27)
- "When he digs with the shovel, he jumps in the hole, then phases through the ground as he walks around."
- "There is one where he places a cobblestone block and jumps on it and I think breaks it, which is broken."
- "Any of them where he breaks a block, he should not be replacing it. We can silently replace the blocks when
  they are off screen."
- "Any of the animations where he needs to interact with structures, like when he shoots a bow at the haybale,
  need to either have the structure always around or he needs to place it before interacting with it."
- "On the archery one, the camera is positioned so you can't see what he is doing, so there needs to be smarter
  camera positioning."
- "The enchantment table texture is broken and I never saw it used once."
- "The bottle of xp that splash on the player have bugged textures." (drop 165, Launched experience bottles)

## Done means
- [ ] **World state:** a block Steve breaks stays broken and one he places stays placed. Restore the camp
  silently, only when the changed cell is outside the camera frustum. Holes, huts, torches and crops all
  follow this rule.
- [ ] **No phasing:** Steve and the animals always stand on the real surface. They walk around holes or step
  down and back up, never through ground or into blocks.
  - The dig act: he digs and stands beside the hole, or climbs out with a jump, but never walks through
    the ground.
  - The cobblestone act: place, jump up, stand, hop down, then break it with the break animation and drop.
    Or replace it with an act that makes sense.
  - Extend `nav_check.py` to sample feet height against the surface (error ≤ 0.05) and to flag any act that
    alters a block in view without an animation. 0 violations over all 29 acts.
- [ ] **Props first:** every act that uses a prop has it built into the camp permanently, or Steve places
  it first. Examples: the archery target, the note block, the brewing stand, the enchanting table.
- [ ] **Smart activity camera:** frame both Steve and the act's target: the bow and the hay-bale target,
  the rod and the bobber, the dog, the sheep. Use a side-on 3/4 shot chosen from the two positions, with
  an occlusion check. Make one frame per act where both read.
- [ ] **Enchanting table:**
  - The 1.7.10 model: 12/16 height, `enchanting_table_top`/`side`/`bottom`, and the floating open book
    from `entity/enchanting_table_book.png` that bobs and turns to face Steve.
  - The enchanting glyph particles.
  - The enchant act shows up in normal idle. Prove the scheduler reaches all 29 acts within 15 minutes of
    simulated idle.
- [ ] **XP bottles (drop 165):**
  - The thrown bottle uses the `experience_bottle` item sprite.
  - The splash uses the 1.7.10 potion-splash particles in the XP colour.
  - XP orbs use the animated `experience_orb.png`, bob, and fly to Steve with the orb sound.
  - Check every other thrown-item outcome the same way: potions, eggs, snowballs, ender pearls.
- [ ] Re-run `vet_lucky.py` and `audit_lucky.py`.
- [ ] Verify motion in real time with the CDP driver (copy `scratchpad/orch/cdp.mjs`), not only stills.
- [ ] Sheet: each fixed act, 3 frames each (start, middle, end), plus drop 165.

## Progress (agent log)
- [x] 2026-10-27 world-state core in steve.js ("the world's memory": W.later/hand/settle, surfaceAt, auto floor + gravity + half-block steps, frustum from S.camera or, in fast-forward, the page's follow shot via deps.shot). Quarry/tree log/hole/crops/torches/hut/sapling/hay arrows put back only when out of frame. Restores of terrain voxels survive resetStage (app.js restoreVoxels skips brain.keeps(key)).
- [x] acts: parkour (place, run-up, jump, stand, step off, break+drop), hole (dig, fall, jump out, fill with dirt), sapling (instant tree, chop 4 logs, nav boxes), bow (permanent hay, real EntityArrow flight, crit trail, side-on frame), enchant (no diamond swap), creeper/chicken spawn out of frame, scheduler = shuffled bag of all 29 (every act within ~670 s sim).
- [x] camp.js: hay target, 3x2 bookshelves behind the enchanting table, table side UVs cropped (1.7.10 bounds), glyph particles (particles.png cells 225-250).
- [x] nav_check.py: --acts, --cover; feet/world/acts in data-nav-stats.
- NEXT: view enchant/harvest/sapling/hut/torches stills, camera per act (spec.mark), drop 165 + thrown items, vet/audit, CDP motion check, sheet.
- Scratch: /private/tmp/claude-503/-Users-suaz-Desktop-QuestForge/91769071-2ed0-4412-b25d-3c510232d8e5/scratchpad/r7/lucky/ (cdp.mjs, trace*.js, s1..s3 sheets)
