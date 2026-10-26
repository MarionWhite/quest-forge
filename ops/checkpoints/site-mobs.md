# site-mobs checkpoint
Done: all of the brief. site/lib/mc/{mobs,textures,vanilla-models,orespawn-models}.js, tex/, lineup.html; tools/site/gen_vanilla_models.py + gen_orespawn_models.py; site/lucky/reel.js rewritten; shim site/lucky/mobs.js.
Frames: /private/tmp/claude-503/-Users-suaz-Desktop-QuestForge/91769071-2ed0-4412-b25d-3c510232d8e5/scratchpad/mobs/l8/sheet.png (lineups), l7/sheet.png (reel + scene).
Next: nothing required. Known approximate: EnderDragon (vanilla static), Horse gait, OreSpawn animations (generic), Mothra (Butterfly model), Rotator.
Critic pass done: generator ignored same-class setRotation calls (all OreSpawn rotations were missing); fixed, regenerated. Robot2-4 and Rotator get a mild emissive lift (their textures really are black); Brutalfly/Mothra wings lifted into a V. Sheet: l13/.
Moth pass: Brutalfly/Mothra pitched toward the camera (tilt 0.9, lift 0.3); Mothra uses lunamoth.png because mothscale_1 is almost fully transparent. Frame: l15/.
