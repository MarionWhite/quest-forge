# site-lucky-stage (checkpoint, started 2026-10-25 23:00, Mac)

Brief: ops/briefs/site-3d-page.md + the task prompt (design notes: /private/tmp/claude-503/-Users-suaz-Desktop-QuestForge/91769071-2ed0-4412-b25d-3c510232d8e5/scratchpad/shared/round4.md).
Owns: site/lucky/{app.js,stage.js,index.html,poster.jpg}, new site/lucky/steve.js, new textures
Done means: empty dais; block drops with whoosh+slam; Steve idle activities, '!' and sprint; sky (square sun, 3D clouds, no seam); upright grass; fragments fade; particles never freeze; smooth pan; torches flash mood colour; Close returns to idle; ticks always on (toggle removed); music.lucky; speaker toggle; coloured names on the sheet; dump JSON has errors/sfx/sceneReport; ?idle=; poster regenerated

## Done
- Read all of app.js/stage.js/index.html, qfaudio.js API, mobs.js API. No code written yet.
- Found: textures source /private/tmp/claude-503/-Users-suaz-Desktop-QuestForge/91769071-2ed0-4412-b25d-3c510232d8e5/scratchpad/assets/mc/assets/minecraft/textures (blocks/items/entity); copy into site/lucky/tex.
- Found freeze bug: app.js stepTimeline returns early in idle, and frame() skips stepTimeline in phase 'result', so st.fx (burst particles) never step. Fix: step st.fx every frame.
- Found grass bug: stage.js crossMesh uv is v-flipped (bottom=1,top=0). Sun is above frame top (DISC y 0.09); lower to ~0.05 and to the right of centre.

## Plan
- new camp.js (campsite meshes + layout, built from app.js after createStage), steve.js (coroutine activities, A* grid walk, '!' sprite, sprint), sky.js maybe (3D clouds from environment/clouds.png, pixel stars shader).
- app.js: sequence drop(0.6s)->slam->Steve alert/run/jump on dais/mine->shatter, then old reel timeline (T_SHATTER=2.3 post clock); camera spring pre-phase, quintic pan to reel; Close = dip to idle; Steve placed at (3.2,0,0.5) before scene.
- Steve must be at POS.player facing dais when the scene starts (scenes expect it).

## Next
- implement per plan, then dump_frames list + sheet, poster, node --check, commit own paths, journal line.
