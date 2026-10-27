# site-r7-krypt (checkpoint, started 2026-10-27, Mac)

Brief: `ops/briefs/site-3d-page.md`. Agent: opus, a level designer with taste, not a feature builder.
Owns: all of `site/graves/*` except `scares.js`, `scares/*`, `tex/scare/*`, `mood.js` and `mood/*`; and
`tools/site/check_krypt_plan.mjs`.
Previous state: `site-r6-krypt-gen.md`. Specs: `docs/design/site/krypt-endless.md`, `krypt-structures.md`.

## Owner's words (2026-10-27)
- "The krypt has regressed significantly."
- "When the graves are super close together in the krypt the camera constantly swings back and forth and it
  feels like shit."
- "The dungeon is very repetitive, and I would appreciate more creativity and new structures."
- "There are just a bunch of chests with fucked up textures scattered throughout the dungeon. I don't know why
  they are even there for 1, and for 2 they look like shit. There are also black things that kind of look like
  cauldrons on the floor that are out of place. The decorations could benefit from some common sense."
- In round 5 he said the Krypt was "really close to polished" and "every improvement is landing". That
  version is commit 275579a. Use `git worktree add` into the scratchpad to run it next to the current one
  and compare, and keep every quality that version had.

## Done means
1. [ ] **Camera:**
   - The passing focus never ping-pongs. With dense stones, hold a gentle side bias toward the wall the
     stones are on, and turn fully only toward a stone you are slowing near.
   - Add hysteresis, a minimum hold, and a cap on yaw rate and acceleration.
   - Prove it with a real-time CDP metric: steady scrolling past the densest stretch at slow, medium and
     fast speeds. Report yaw direction reversals per 10 s (target ≤ 1) and peak yaw rate.
   - Click focus works as before.
2. [ ] **Props with common sense:**
   - Remove the generic random-prop scatter (chests, cauldrons, carts).
   - Props appear only where a builder would put them: chests in a treasury or vault, cauldrons in an
     alchemy room or witch hut, carts on rails in a mine, bones in an ossuary.
   - Every prop uses its real 1.7.10 model and texture, close-up correct: the chest model with lid and
     latch, the cauldron model with its hollow inside.
   - Make a close-crop sheet of every prop type.
3. [ ] **Less repetition, more creativity:**
   - Judge it as the visitor walks it. Write a walk filmstrip tool that samples a frame every 12 blocks
     along 600 blocks of path at 3 depths. A viewer must not feel "I've seen this" within a strip.
   - Fewer plain corridors. More rooms, landmarks, height changes and memorable set pieces.
   - At least 15 new structures with a story, for example:
     - a spider nest cavern with egg sacs;
     - a sunken chapel;
     - a prison block with iron doors and a skeleton in a cell;
     - a ravine crossing on mine rails;
     - an underground lake with a dock and a boat;
     - a forge with anvils and lava channels;
     - a desert tomb with sarcophagi;
     - a frozen hall with mobs in ice;
     - a redstone trap room with pistons;
     - a ruined Nether portal;
     - a giant's bones;
     - a witch's hut in a swamp cave;
     - a cartographer's room with maps;
     - a flooded ossuary;
     - a crypt of iron doors.
     Study the catalogue and the mods; don't copy.
4. [ ] Keep round 5's lighting rules, the graves in alcoves, the stone focus feel and performance. Measure
   heap and draw calls; the heap rose to 62 MB, so find out why.
5. [ ] Sheets:
   - the yaw metric table;
   - the prop crops;
   - 3 walk filmstrips, before and after;
   - one frame per new structure;
   - a side-by-side against 275579a at 3 matching spots.
