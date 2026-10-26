# site-r5-scares (checkpoint, started 2026-10-26, Mac) - DONE

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
- [x] All 14 scares are rebuilt to the spec. They run in the real Krypt scene at the player's
  position, with no separate canvas and no teleport cut.
- [x] The J picker and `site/graves/scares/approved.json` (empty) exist. The director uses only
  approved scares.
- [x] Sounds use the `qf.scare.*` names in the spec (the audio task makes them) and the existing
  bank. `python3 -I tools/site/check_sounds.py` exits 0 once audio lands. Until then, list the
  missing names in this checkpoint.
- [x] `site/graves/scares/test.html` is removed. All dumps run on the real page, in at least three
  segments.
- [x] Sheet: 4 frames per scare (dread, hit, kill, death screen), 56 in all. Review it as a
  horror director: is this scary, does it make sense where the player stands, and is it
  accurate Minecraft?

## Done
- 09:30 Read spec and code. Contract landed (132d554: carve/restore/solidAt/blockAt); audio landed
  all 15 qf.scare.* events (ed420a4). Copied 1.7.10 textures (Mojang, like graves/tex) into
  site/graves/tex/scare/ (pistons, fire_layer_1, destroy stages, icons, widgets, ascii font, items,
  explosion, vignette, arrow, particles). approved.json created.

## Plan (architecture)
- scares.js: entry, J picker, approved.json, director loop, dump hook (?scare=&scareat=&dump=1).
- scares/rig.js: runs in __krypt.scene via scene.onBeforeRender (krypt keeps rendering while held);
  local frame at the player's feet (heading = last bend's dir), probe via solidAt/blockAt, head camera
  (1.62 eye, MC hurt roll sin(x^4 pi)*14deg, death drop+roll), env overrides (bakeUniform, exposure,
  point lights, fog, nausea projection warp), camera-attached group for fire/hands/web, gore, mobs.
- scares/hud.js: overlay canvas inside #stage: real icons.png hearts, widgets.png hotbar, ascii.png font,
  1.7.10 death screen (gradient, You died!, Score, Respawn/Title screen), chat death line.
- scares/s_*.js: one module per scare. Old stage.js/cuts1/cuts2/fx.js/test.html to be removed.

- 10:40 scares.js rewritten (J picker, approved.json, director only plays approved, dump hook on the real
  page); scares/rig.js (in-scene runner via scene.onBeforeRender), scares/hud.js (1.7.10 HUD + death
  screen from icons/widgets/ascii), scares/common.js; old stage/cuts1/cuts2/fx/test.html removed.
  Zombie built and dumped: frames r5/scares/z3 (dread, back, hit, bite, kill, hands) look right.
- Dump workaround: the Krypt's runDump leaves K.last in the future, so the next live frame has dt<0 and
  throws the camera to y=-2000. dumpMode puts the camera back from the dumpshot pos/look first.

- 11:40 Skeleton (lights-out; torches snuffed via the merged torch mesh, smoke from particles.png, arrows
  from entity/arrow.png), Creeper (look-back; real crater via carve, explosion.png puffs, dropped items,
  ringing, second hiss) and Spider (ceiling eyes, drop, lens legs, hauled up and dangling) built.
  Frames: r5/scares/sk3, cr2, sp1, sp2. rig: R.ready() awaits mob textures after build (they were black
  otherwise), mob {own:true} ambient outside the bake gain, ?scarecam=x,y,z,yaw,pitch for checks.
  Sheets: dump_frames' own --sheet times out on this busy machine; r5/scares/sheet.py (anaconda PIL) instead.

- 13:10 Witch (nausea warp, splash particles, Harming), Blaze (fireballs, fire blocks, burning overlay,
  char) and Magma Cube (thumps behind, jumps over you, fullbright, squash crush) built: 5abf9ae, c2f4035.
  Frames r5/scares/wi1, bl1, bl2, mc1, mc2.
- 14:20 Zombie Pigman (your fault) built: 6d7d62e. Frames r5/scares/pz1-3. Shared: common.heldItem (the
  1.7.10 first-person sword and swing at the hand's own 70 deg projection), zombieArms (ModelZombie swing),
  mcRot, halo/glowTex, swingAt. Fixed: R.flash never applied (NormalBlending is truthy); zombie.js and
  skeleton.js arms pointed backwards (three's rotation.x = -MC's; use mcRot).

- 15:00 Silverfish (the wall) built: e84e0de. Frames r5/scares/sf1-3. Infestable 3x2 face (or a 1-wide
  pillar) found by rays; the jolting block uses R.bakeAt (the chunk's 'bake' attribute) so it matches the wall;
  crack overlay = destroy_stage with MC's DST_COLOR/SRC_COLOR blend; swarm = 8 baked wiggle poses of
  makeMob('Silverfish') as InstancedMesh (110 + climbers), lens silverfish in R.view. The 1.7.10 texture's
  sparse bristle pixels make them look fuzzy: that is accurate.

- 15:50 Wither Skeleton built: 0a93c78. Frames r5/scares/ws1-2 (deep segments: at=0.7 chasm, 0.85 fortress,
  0.95 stronghold). Decapitation: the head flies, rolls, rests on its side; headless Steve (makeMob('Steve'),
  iron sword) goes over with MC's rotateCorpse; the black fog lifts a little at death so the tableau reads.

- 16:40 Enderman built: 7c58be1. Frames r5/scares/en1-2. The chasm it drops you into is built by the scare
  (instanced blocks at local y -140, lava_still frames, lava-lit instance colours); falls at MC gravity 32 m/s^2.
  Workaround: ModelEnderman lifts only the head when screaming; the library lifts the jaw (hat) too, so the scare
  puts the hat back down 5 px (request for mobs-gear below).

- 17:30 Piston trap (scares/piston.js) and Cave Spider built: 97525ab. Frames r5/scares/cs1. The room is
  carved under the patch (sized to the solid rock found; fits=false in flood, which has open water below);
  the pistons are our meshes in the carved floor slots, retracting in 0.1 s. common.bakePoses/swarm/webs.

- 18:20 Slime (c6d3860, frames r5/scares/sl1-2) and Ghast (112be8f, frames gh1-3) built: all 14 scares exist.
  Slime: the pit has slime water; it squeezes through the hole, lands face to face, hops on you; inside it the
  air meter drains. Ghast: pistonTrap({room:false}) carves only the floor; the shaft and a netherrack cavern are
  the scare's own instanced blocks, seen through the Krypt rock by a depth punch (gl_FragDepth = 1 quad at
  renderOrder 5); the camera tilts from the eyes to the mouth as it opens.

- 18:50 Final: check_sounds.py exits 0 (0 missing); node --check passes on scares.js and every scares/*.js; test.html
  gone. Sheet r5/scares/final/sheet.png: 56 frames (dread, hit, kill, death x 14) over mine, flood, library,
  fortress and stronghold, no dump errors or missing sounds. Review fixes: the Ghast's camera tilts from the
  eyes to the mouth; pistonTrap({room:false}) no longer shrinks the depth (5e93b4e: the ledge floated in the
  stronghold); kill frames retimed to read (Enderman over the lava, Wither tableau). DONE.

## Requests (krypt-more, app.js)
- frameInner: clamp dt at 0 (`Math.max(0, ...)`): runDump's frameInner(now+16+q*30) leaves K.last ahead
  of the clock and the next frame's damped lerp diverges (K.pos.y ~ -2000 in every ?dump page).
- While K.held, pump chunks around K.camera.position (not K.pos): the Enderman teleport needs the
  chasm's chunks built even if the visitor never walked there. (Worked around: the scare builds its own chasm.)

## Requests (mobs-gear, site/lib/mc/mobs.js)
- ANIMS.enderman with `screaming`: ModelEnderman (1.7.10) copies the head's pivot to bipedHeadwear and only
  then lifts bipedHead by 5, so the jaw (hat layer) stays and the mouth opens. The library lifts both.

## Next
Nothing: done. The owner approves scares with the J picker (approved.json is empty, so none play yet).
