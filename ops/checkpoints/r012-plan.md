# r012 plan from the owner's r011 feedback (2026-10-28)

Source: docs/design/shaders/feedback/r011.json. Overall: "This is really good progress, and I want to keep riding
this momentum." The copy-first method (ops/checkpoints/r011-plan.md) works: keep it. Small rounds, only answers to
this feedback, settled picks never re-asked.

## Settled by r011 (do not ask again)
- Stay True leaves with planes (hedge 5, tree 5, forest 3) and Stay True's two-block crops (5, 5). Keep the density.
- Faithless items, items close, inventory, crafting, brewing, chest, anvil, enchanting: copy (B).
- Patrix mob skins: copy (B, mostly 5).
- Bookshelves: keep ours (A); Soartex's goes in as a Chisel variant (see packs).
- Meteors: storm (B) is the default.
- Sunset: Photon's sky (A), "listen to the critic".

## Shader (ops/checkpoints/r012-shader.md)
1. Sunset (A, 4): do what the critic said in r011 critic.json `_r011_publish_summary`: gold, not pink-lilac, and the
   sun gets a glow. Copy how Photon/BSL draw the sun disk and its glow.
2. Rays (C, 4): "A and B just don't look good. A looks like it's artifacting, and B is very hazy." The owner picked
   round 10's rays. Restore them on top of Photon's sky, and cut the near-field evening haze that greys golden_lit's
   grass (66,64,39 vs r010 40,45,15). Cost stated.
3. Meteors storm (B, 4): "I was also hoping that they would have the leaner design like the references I gave. These
   ones kinda look a little bulky." Thinner, longer, fainter streaks like the photos in attachments/r010/.

## Textures: Stay True carry-overs (ops/checkpoints/r012-textures.md)
- Gems: dropped in r011 (not glassier in a still; emerald back to nested squares). Next try, with the cause fixed.
- Roofed forest view: re-aim so the dark oak canopy is visible (forest scored 3).

## Packs (ops/checkpoints/r012-packs.md)
- Creative tabs: combat tab "something broke here and it looks all fucked up" (2); brewing "the tabs don't look
  richer here, this needs to be fixed" (3). Fix both.
- Furnace: "doesn't look exactly right, but yes, copy it" (3). Find what differs from Faithless and fix.
- All copied GUI: "Make the text on screen pop out more. It gets muddled by the noisy background."
- HUD (neither, 4): "I think we can do better on these. Something custom to Quest Forge." Design 2-3 QF HUD and boss
  bar directions, built on Faithless's craft level.
- TNT (B, 4): "I don't know why some of them have the normal lettering": every TNT gets the lettering (drop the 4:1 mix).
- Mobs: "We need to fix the ones that still have vanilla skins" and "find something for the passive mobs": every
  mob gets a non-vanilla skin (Patrix remapped to 1.7.10 UVs, or Faithless/Stay True/Conquest entity art where Patrix
  can't map).
- Shelves (A, 3): "Maybe we add the copied one as a [chisel] variation in the modpack, using the chisel mod": find
  out how to add a Chisel variant on 1.7.10 (config, CTM, or code), report the route; don't ship it yet.
