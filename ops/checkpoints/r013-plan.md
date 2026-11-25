# r013 plan from the owner's r012 feedback (2026-10-29)

Source: docs/design/shaders/feedback/r012.json (issue 16). Critic notes: C:\qfb\shaderdev\r012\critic.json.
Method unchanged (ops/checkpoints/r011-plan.md): copy first from the packs that do it right, small rounds, only answers
to this feedback, settled picks never re-asked. Twice the owner wrote "listen to the critic": the critic's r012 notes ARE
the work order for the sky.

## Settled by r012 (do not ask again; ship as the default)
- Sunset: round 12's gold Photon sky (A). Rays: round 10's (from r011), kept.
- Meteors: round 12's lean hairlines (A).
- Gems: option C (A's Faithful facet gems + glass maps + polished dielectrics on the SSR path). "I like this glassy effect."
- Roofed forest: Stay True canopy (A).
- Creative tabs combat + brewing: B (Faithless creative). Furnace, enchanting, crafting, brewing, anvil: B (5 each).
- TNT: B, every block lettered (5).
- Mobs: B, the Patrix remap, in all seven views. Conquest's passive mobs are out.

## Shader (ops/checkpoints/r013-shader.md, shader-dev)
1. Sea sunset (critic p12/ocean_sunset): the sea stays navy (25,44,69) under the gold sky. Make the water reflect the
   gold sky the way Photon/BSL do (read their water reflection code, copy the approach). shore_sunset is still salmon:
   same fix, check it.
2. Sun glow (critic r12c3, owner 3 "listen to critic"): a hot spot that fades into the sky, no visible disc edge. Judge it
   on a NEW view where the sun is clear of cloud at sunset (sun-cloud scene could not answer it in r012). Copy how
   Photon/BSL draw the sun's glow.
3. Rays cost: round 10's rays cost up to +0.30 ms and make ocean_sunset 3.65 ms against High's 3.0. Same look, cheaper
   (fewer steps, half-res, or dither + temporal). State the cost before and after.
4. Meteors (owner: "push the quality without increasing performance costs"; critic p12clipm5): radiate the streaks from
   one radiant point, vary length and brightness from short and faint to long and bright, and stop a streak breaking into
   dashes when it crosses thin cloud. The cost must not rise above round 12's lean meteors (2.94-2.99 ms).
5. Gems C becomes the default: merge the C patch (private copy C:\qfb\gems\ssr, see r012-textures.md) into
   shaders/QuestForge so QF_GEM_SSR is on by default. Critic g12c/gem_glint_d: "the reflection wobbles, reads as wet plastic":
   flatten the normals so the reflection is sharp and faceted. Coordinate the normal maps with the textures agent (the
   textures agent owns the gem PNGs and normal maps; shader-dev owns the GLSL).

## Textures (ops/checkpoints/r013-textures.md, texture-dev)
- Gems connected textures (owner, gems-lit: "I think they should have connected textures though"): diamond and emerald
  blocks (and gold, iron, lapis and redstone blocks if the same approach applies) join across neighbours, with no seam
  grid on a floor or pillar. Find out which CTM path works in this pack's client (OptiFine CTM properties, or the CTM
  that already works for TNT, `tiles=0` in r007packs.py) and copy the CTM layout from a pack that does connected gem
  blocks well. Show it on gem_glint and gem_lit with option C on.

## Packs (ops/checkpoints/r013-packs.md, texture-dev)
- HUD (neither, but 5; "Try going for something Elden Ring inspired"): 2-3 directions in that spirit: minimal, thin
  long bars, a muted dark frame with fine gold lines, quiet hotbar, a boss bar as a thin bar with the name above it. Our
  own art, inspired by the style and never copied from the game's assets. It must show IN GAME this time: replace
  QuestForge.zip's widgets.png in the stack (or order the packs) so the hotbar draws. Keep mock M only as a fallback.
  The framed boss bar's Java hook (qf-tweaks GuiIngame): report what it needs; build nothing on the server side.
- Mobs (B): the wither skeleton is not visible in view 1 ("it looked best in matrix" = Patrix): get it in frame. Snow
  golem still looks default in B: give it Patrix (remap) or another reference pack's art. Get the slime, magma cube and
  squid into the views (critic: missing in views 4 and 7). The wither and one horse marking still vanilla: say so if no
  source has them.
- Creative book page a few px short (carried from r012): fix if option C's book is still anywhere; B is picked, so it
  only matters if B shares it.

## Still open with the owner (not in the round)
- Install the picked parts into the live game now (via trial.py install, guard before and after): Stay True leaves and
  crops (branch leaf-frills), Faithless items and screens, now also Patrix mobs, TNT, creative tabs.
- Chisel route for the Soartex shelf: A texture override or B new block via IMC (r012-packs.md step 3).
