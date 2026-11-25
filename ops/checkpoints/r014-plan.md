# r014 plan from the owner's r013 feedback (2026-10-31)

Source: docs/design/shaders/feedback/r013.json (issue 17). Critic notes: C:\qfb\shaderdev\r013\critic.json.
Method unchanged (r011-plan.md, r013-plan.md): copy first, small rounds, only answers to this feedback, settled picks
never re-asked. The owner again said "listen to the critic" / "Please closely follow the critic here. This is all good
feedback" on the sky: the critic's r013 notes are the work order, item by item.

## Settled by r013 (do not ask again)
- Sea sunset A (warmer sea), sun glow A (soft sun), rays A (8 points: "I can't tell the difference", so keep the cheap
  one), meteors A (one radiant, varied) as defaults.
- Metals connected (B, 4): gold, diamond, emerald, lapis, iron join. Connected is the way.
- Mobs: round 12's set (A, 5 in six views). Round 13's swaps (Faithless slime/magma/squid/snow golem) are NOT picked.
- HUD pieces: Tarnished's boss bar, Grace's hotbar.

## Shader (ops/checkpoints/r014-shader.md, shader-dev)
1. Sea (3, "listen to critic", p13/ocean_sunset): the sea is pewter grey (middle sea red/blue 1.05 vs BSL 1.99). "Let
   the reflected gold horizon lead at grazing angles": read BSL's water Fresnel and reflection weighting and copy it.
2. Shore (neither, "closely follow the critic", p13/shore_sunset): the sunlit cloud RIMS are still salmon (brightest 5 %
   250,152,108): give the lit edges the same gold shift as the mid-tones, so rims go amber, not coral. The near water
   reads as mud (36,26,10): it must read as a reflection of a gold sky.
3. Sun glow (3, "critic", p13/sun_clear): the edge is answered, the glow is round 12's. Get a view with the WHOLE disk
   clear at sunset (14 views failed on terrain: use a clear-weather / cloud-free setting for that one view, or a scene
   set-up that removes the far strand, and say so), then judge and tune the glow's size and falloff against Photon/BSL.
4. Meteors (3, "kinda, but let's improve"): the critic wants the cost back to 2.94 (cull the faint streaks a frame cannot
   show). Then improve toward the r010 photos (docs/design/shaders/feedback/attachments/r010/): look at what the photos
   have that ours lack (head brightness, colour, persistent trains) and copy the strongest one. Cost no higher than r012.
5. Gems (3, "Right idea, but I don't like this. It looks like plastic"): see Textures; shader-dev owns the GLSL side.

## Textures (ops/checkpoints/r014-textures.md, texture-dev)
- Gems: the owner rated all three connected-gem scenes "neither" (5) and the shader gem scene 3, "looks like plastic";
  metals connected B is picked. So: keep connected, change the MATERIAL. Find out with numbers why ours reads as plastic
  (uniform smoothness? sky reflection over the whole face? no internal depth or colour variation?) and copy how a pack
  that makes gems look like gems does it (Stay True's diamond art, any labPBR/specular pack among the references,
  BSL's handling of high-F0 dielectrics). 2-3 genuinely different materials, connected, against r013's.

## Packs (ops/checkpoints/r014-packs.md, texture-dev)
- HUD: "The hearts and food should stay individual icons. I like the boss hp bar from tarnished and the hotbar from
  grace. We need a better xp bar." Build ONE HUD: Grace's hotbar + Tarnished's boss bar + individual heart and food
  icons in the same style (Elden Ring-inspired, our own art) + 2-3 XP bar options (the critic also flagged the vanilla
  lime XP number). Fix the food-bar test bug in the shot (GuiShots fix needs the qf-content build, or set food another
  way) so the icons show full.
- Mobs: round 12's set is the default. Snow golem "is still default": give it 2-3 non-default options from the
  reference packs (Faithless's from r013 B is one) in one view, the rest unchanged.

## Still open with the owner
- Live install of the settled picks (trial.py install, guard before and after).
- Public site: pk-mob/GUI/leaf scenes show copied pack art in in-game renders (since r011). Keep, blur after voting,
  or owner-only from r014.
- The water is over the High budget (sea sunset 3.52 ms vs 3.0): cheaper water is a later question.
