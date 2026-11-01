# r015 plan from the owner's r014 feedback (2026-11-01)

Source: docs/design/shaders/feedback/r014.json (submitted 2026-11-01). Critic notes: C:\qfb\shaderdev\r014\critic.json.
Method unchanged (r011/r013 plans): copy first, only answers to this feedback, settled picks never re-asked. On the sky
the owner again wrote "critic": the critic's r014 notes are the work order.

## Settled by r014 (do not ask again)
- Sea sunset A (gold sea) 4, shore A (amber rims) 3, meteors A (green trains) 3: defaults stay.
- Sun glow: B, the haze-core try, becomes the default (owner 3: "I kind of like the little bit of distortion that the
  blocks on the horizon get. It adds a layer of realism.").
- Snow golem: D, Conquest's ("the only one that really changes"). Rest of the mob set: round 12's.
- Copied-pack renders on the public Lab: fine (owner 2026-11-01, CLAUDE.md).

## Shader (ops/checkpoints/r015-shader.md, shader-dev)
1. Sea (critic p14/ocean_sunset): ease the far band back from red/blue 2.93 toward BSL's ~2.4 so the horizon line holds.
2. Shore (critic p14/shore_sunset): keep the gold on the sunlit rims only; cloud shadow sides and the open sky go darker
   and cooler, as BSL's do (strongly-gold sky share 56 % -> back near round 13's 32 %; zenith blue, not grey-mauve).
3. Sun: make the haze-core try (QF_SUN_HALO / p14cch1's setting) the default. The owner likes "distortion" on the
   horizon blocks in B: find what B does to the far terrain at the horizon (diff B against A at the horizon line, with
   numbers) and make sure the default keeps it. Fix the faint pale column over the far beach (critic p14cc).
4. Meteors (critic p14clipm): the photos' bigger gap is the sky: a dense blue star field where ours has heavy dark
   cloud hiding most of the shower. Show a clearer, starrier meteor-night sky (from the photos and Photon/BSL stars) on
   the meteor view. Cost no higher than round 14.
5. Gems: see Textures. If a big-facet normal map needs the shader to keep facets flat and sharp, that is yours.

## Textures (ops/checkpoints/r015-textures.md, texture-dev): gems, a big swing
The owner, rated 5 on every gem scene, "neither": "These either look plastic or very noisy. I'm not 100% sure what I'm
looking for here, but I know that we are not even close." So: stop tuning, show genuinely different directions, and
help the owner find the target. Connected stays (metals B, r013).
- 4-5 directions, each a complete look, each copied from something that works:
  (a) the critic's: big facets, about 6 planes per block, copied from Patrix's diamond_block normal map structure, so
      whole facets flash;
  (b) Stay True's diamond/emerald art as is, no gem reflection (QF_GEM_SSR off): the plain, clean baseline;
  (c) a clear, deep "jewel" look: darker saturated body, bright inner glow and few sharp highlights (emission/SSS
      channels the shader already reads or can read);
  (d) the best of r014 (Faithful + facets) with the noise taken out at distance (mip/normal fade);
  (e) optional: any other look a reference pack gets right.
- Show each at three distances (close block, pillar, floor) in the same light, so "noisy" and "plastic" can be judged.
  Name in each scene what the owner should look for (facet flashes, depth, cleanliness at distance).

## Packs (ops/checkpoints/r015-packs.md, texture-dev): HUD, five designs
The owner, "neither" (4): "I like the idea of a medallion, but we are going too far minimalist here with these designs.
I want it to look more sleek and pleasing on the eyes." Icons: "I want to see at least 5 unique designs before we commit."
- 5 complete, genuinely different HUD designs (hotbar, hearts, food, armour, XP with a medallion, boss bar), less
  minimalist: richer framing, depth and finish, still readable at 1x. Elden Ring-inspired was the r013 brief; the owner
  liked the medallion, Grace's hotbar and Tarnished's boss bar: use them as a starting point, not a limit. Our own art.
- Every design: the boss name gets a dark outline (critic: unreadable over bright sky, r013 and r014).
- Show each in game (no screen open, hearts clear of chat, food full) plus a close-up of the icons and the XP medallion.
- The XP number colour still needs the qf-content XpBarStyle hook: still the owner's yes (keep it stated).

## Still open with the owner
- Live install of the settled picks (trial.py install, guard before and after).
- Cheaper water (High 3.56 ms, Low 0.95 on the sea sunset).
