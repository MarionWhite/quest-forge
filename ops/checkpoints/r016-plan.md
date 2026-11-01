# r016 plan from the owner's r015 feedback (2026-11-01)

Source: docs/design/shaders/feedback/r015.json. Critic notes and sky work order: C:\qfb\shaderdev\r015\critic.json
(`_r015_publish_summary`, "WORK ORDER"). Overall: "We really need to start moving the needle on all of this because we
still have a shit ton of ground to cover."

## Process change (owner, r015 sea note)
"We keep having to go back and forth for the simplest things... the critic layer needs to be more actively integrated
in the actual process of making the changes... passing this back and forth between an agent changing it and the critic
judging it until it is fixed." So, for the sky, nothing reaches the owner until the critic has passed it:
1. shader-dev changes, renders, measures against the targets below, checkpoints, exits;
2. a fresh critic judges those frames against the same targets (pass/fail per target, numbers, what to change);
3. the notes go back to shader-dev; repeat. At most 4 passes per item, then it ships with the critic's honest verdict.
On art taste (gems, HUD) the owner's picks override the critic's: r015 critic preferred gem A and HUD A, the owner
picked gem E and rejected every HUD. The critic still checks claims, crops and readability there.

## Settled (do not ask again)
- Shore A (gold rims, cool shadows), sun A (haze-core default), meteors A (clear starry night) stay as the base.
- Gems: frost (E, Soartex) is the base direction. Gem looks A, B, C, F are dropped.
- HUD: every r015 design is rejected; no Elden Ring inspiration.

## Sky (shader-dev <-> critic loop; ops/checkpoints/r016-shader.md)
Targets are the critic's r015 work order (critic.json summary), verbatim numbers:
1. Sea: the sun disk core and glint core clip to white (band's brightest tenth ~254,250,235, r/b <= 1.1; >= 5 % of the
   far band under the sun at 250+ on all channels); gold only in the path's edges and falloff; within ~10 degrees of
   the sun ease the gold-sea pull (sea beside the path 2.70 -> ~2.35); revert r015's horizon strip (the line spread
   12 -> 50 px); far band 2.0-2.1.
2. Shore ("listen to the critic"): cut red from the open sky, don't add blue. Top right 129,108,112 -> ~75,65,72;
   between clouds 137,100,103 -> ~120,90,65; red <= blue above ~30 degrees; <= 15 % of upper sky blue>green; sky ~40 %
   darker overall; keep rims (brightest 5 % 250,157,83) and the underside.
3. Meteor night (owner rated 3): sky median 4,7,15 -> ~18,22,38; brightest stars 135,125,107 -> ~170,180,210, big enough
   to survive the half-size clip; Milky Way blue-white, not sepia; clear the cloud over it; white heads, green trains.
   Cost <= 2.98 ms.
4. Sun glow (owner): "In D, the sand blocks right under the sun have like a heat distortion effect when compared to C."
   r015 measured the two as equal; the owner sees a difference on the sand under the sun. Find it (3x crops, local
   warping/shimmer, frame-to-frame), and make sure the default has D's effect. Show default vs D on that sand.

## Gems (texture-dev; ops/checkpoints/r016-textures.md)
- Owner: "a slider between the frost and the round 14 calmed, and begin sliding from the frost towards that one."
  Show frost (r015 E) and 3-4 steps from it toward r015 D (round 14 calmed), each a complete look, same three distances.
- Owner: "add the round 14 calmed as a chisel option because it is still pretty cool." Chisel is in the pack: give
  r015 D's look to a Chisel diamond/emerald block variant (texture only; no new blocks or recipes). Show it.

## HUD (texture-dev; ops/checkpoints/r016-packs.md)
- Owner: "These are all worse. WAY worse. Back to a minimal design, but don't get stuck in the Elden ring inspiration."
  Earlier (r014): round 14's minimal set was "too far minimalist... I want it to look more sleek and pleasing on the
  eyes". So the target is minimal and sleek: clean shapes, little framing, good finish. Show a few genuinely different
  minimal designs (hotbar, hearts, food, armour, XP), starting from round 14's.
- Boss bar: "Try for something closer to the terraria infernum mod with the custom health bars and UI." Open real
  Infernum Mode boss-bar images/source first (study only, never copy its art), state what makes it work, then draw our
  own. The r015 obsidian boss bar (E) was "the only one that's kinda close".
- The XP colour/medallion/boss frame still need the qf-content XpBarStyle hook: still the owner's yes.

## Still open with the owner
- Live install of the settled picks; cheaper water (High 3.61 ms on the sea sunset); XpBarStyle hook.
