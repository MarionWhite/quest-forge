# site-r5-lucky-life (checkpoint, started 2026-10-26, Mac)

Brief: `ops/briefs/site-3d-page.md`. Agent: sonnet.
Owns: `site/lucky/steve.js`, `site/lucky/camp.js`, new `site/lucky/nav.js`, `site/lucky/mobscenes.js`.
Previous state of these files: `ops/checkpoints/site-lucky-stage.md`.

## Owner's words (2026-10-26)
- "Steve will walk and phase through blocks when he is walking around."
- "When he chases the chicken he just repeatedly teleports inside of its body and bugs out."
- "Whenever he interacts with the crafting table, furnace, or chest he always goes to the back side of it."
- "The furnace > crafting table pipeline doesn't make sense because he takes iron from the
  furnace and crafts a wooden pickaxe."
- "The pickaxe doesn't sit how it should in his hand."
- "The textures on the fence posts aren't all connected in the world."
- "The chest is having rendering issues where it looks ghosted out."
- "Most of the mob spawning animations seem to be on point, but the mobs will often walk through
  and phase through blocks."

## Done means
- [ ] **Navigation:** `nav.js` holds an occupancy grid built from every camp prop: dais, campfire
  and benches, trees, furnace, table, chest, fences and wheat, pond, rocks, signs and lamps.
  - It provides A* paths with smooth steering and a check for blocked cells.
  - Steve never intersects a prop. Ground mobs in `mobscenes.js` path around props and keep
    apart from each other; flyers are exempt.
  - A script or dump check proves it: sample Steve's and the mobs' positions over 60 s of idle
    and over each mob scene, and report zero samples inside a blocked cell.
- [ ] **Chicken chase:** the chicken flees in hops with its wings flapping, and Steve follows at
  about 1 block and swings. He never overlaps it and never teleports. It ends with the chicken
  escaping or a feather puff.
- [ ] **Front-side use:** the chest, furnace and table each have a facing. Steve stands in front of
  the facing side and looks at the block. The chest lid opens and closes with
  `random.chestopen` and `random.chestclosed`, and the furnace front glows while it smelts.
- [ ] **Coherent chain:**
  - Iron: mine iron ore at the rocks, then smelt it at the furnace while it crackles, take the
    ingots, and craft an iron pickaxe.
  - Wood: punch the tree for logs, craft planks, sticks and a wooden pickaxe.
  - Either chain is fine, or alternate them. The item in his hand always matches the step (ore,
    ingots, logs, the new pickaxe).
- [ ] **Held items:** use 1.7.10's third-person transform from `RenderPlayer.renderEquippedItems`
  (javap the client jar if needed). Tools are gripped at the handle and point forward and up;
  blocks are small cubes. Items are drawn from the item sprites.
- [ ] **Fences:** the 1.7.10 fence model, with connecting rails where neighbours exist and
  continuous `planks_oak` UVs.
- [ ] **Chest:** the 1.7.10 chest model (lid, base and latch from `entity/chest.png`), opaque, with
  no ghosting. Check the material's transparency, depthWrite and side settings.
- [ ] Sheet: idle activities (each step of the chain), the chicken chase in 4 frames, a close-up
  of each use, the held pickaxe, the fences, the chest, and 3 mob scenes showing mobs avoiding
  props.

## Done
(nothing yet)

## Next
Start with `nav.js` and Steve's paths, then the chest and fences, the chain and held items, the
chicken, and the mob scenes.
