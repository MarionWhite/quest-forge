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

## Done (2026-10-26)
- nav.js: occupancy map from stage voxels + camp props, A*, resolve, tracker. tools/site/nav_check.py proves it:
  60 s idle, all 12 acts at 40 s, and 12 mob scenes (forces 143,195,146,174,150,169,144,156,176,185,178,190,286,287,167,168) -> 0 violations.
- Front-side use, furnace lit state, iron + wood chains, 1.7.10 held transform with extruded sprites, fence model, opaque chest, chicken chase, mobscenes routes + separation + equipment pass-through, sign moved to (6.6,-1.6).
- Sheet: scratchpad/r5/lucky-life/final/sheet.png (frames in same dir). Commits on local main.
## Requests
- none
## Status: done (held-pickaxe close-up not framed: idle camera sees Steve from behind during mining; rod and chest views verified)
