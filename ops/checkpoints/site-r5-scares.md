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

## Requests (krypt-more, app.js)
- frameInner: clamp dt at 0 (`Math.max(0, ...)`): runDump's frameInner(now+16+q*30) leaves K.last ahead
  of the clock and the next frame's damped lerp diverges (K.pos.y ~ -2000 in every ?dump page).
- While K.held, pump chunks around K.camera.position (not K.pos): the Enderman teleport needs the
  chasm's chunks built even if the visitor never walked there.

## Next
Remaining scares in order: Skeleton, Creeper, Spider, Witch, Blaze, MagmaCube, PigZombie, Silverfish
(use makeMob('Silverfish'), instanced), WitherSkeleton (equipment stone sword), Enderman; then the piston
traps CaveSpider, Slime, Ghast (carve is in). Sheet shots in r5/scares/<scare>/shots.txt.

