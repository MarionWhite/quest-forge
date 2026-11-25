# r008 publish checkpoint (2026-10-26 ~00:45; requeue step 2026-10-26 night)

## Requeue for loop 4 (done 2026-10-26 ~02:00)
- Cancelled 1026-004242-r008-publish-cost (0/139 had run; it held the pre-loop-4 ef42eec snapshot).
- **Current cost submission: 1026-015851-r008-publish-cost** (39 jobs, 141 scenes, mode cost: runs after 08:00).
  Shader snapshot = loop 4, commit 205d13c (+ ops 152785a). Spec `C:/qfb/shaderdev/r008/specs/p8-cost.json`: the dust scene
  moved to view dust_b (p8, p8off, p8d0, p8d2 gain dust_b; p8clipdust is dust_b with crop 1280,480,1280,720).
- `C:/qfb/shaderdev/r008/spec_scenes.py` updated for loop 4: MOTEBOX = dust_b crop; text now says golden_lit olive, yellow
  oval, metal stripe and lake painted mirror are fixed; still weak: few motes inside beams, forest_golden cream wash,
  ocean sun path dimmer than r007, no lake glint column. Dust option C relabelled "Dust off" (QF_DUST 0).
- Critic verdict for the loop-4 fix loop: none (critic: null, no critic pass ran). The critic notes on the p8 frames are
  still step 2 of the publisher below; read every "already fixed" claim in the scene text against the p8 frames.
- worktree C:/qfb/wt-fb: pruned (git worktree prune), gone from the list.
- Wherever this file says 1026-004242 below, read 1026-015851.

Shader state being published: commit ef42eec (r008 loop 3), pack snapshotted by renderq at submit.
If `shaders/QuestForge` changes before publishing, the cost frames no longer show it: re-submit
`C:/qfb/shaderdev/r008/specs/p8-cost.json` (`--replace`) and update `round.json` "renders".

## Done
- Step 1 (v1 re-renders): not needed. Every shader render from ub onward (incl. the final uj/uk/ul) already used
  `C:/qfb/textures/QFTextures-v1.zip`, and the final CIT build of that zip (22:40) predates ud. Only ua/uc used v0.
- `C:/qfb/shaderdev/r008/spec_scenes.py`: TITLE, INTRO (what changed since r007, known weak spots, cost line, Faithful/VNR
  credits), 14 shader scenes (sun crop A-D, sunset, golden-horizon band A-D, forest, dust clip, lake clip, river, water biomes,
  biome borders, clouds clip, meteors clip + pinned still, underwater, metals, vibrance), then the 11 texture scenes from
  `texture_scenes.json` (TEXTURES-READY exists). Shader options are cost-mode tags p8*; "Round 7" options are r007's qw/qz
  (baseline off8h). Texture options keep their reviewed t8* frames and take ms from cost tags c8* (map in spec_scenes.py).
- `C:/qfb/shaderdev/r008/round.json`: n 8, critic r007 + r008, refs r003/r004, base qw/qz -> off8h, renders, budgets p8/p8lo/p8po.
- Dry test: spec_scenes exec'd clean (25 scenes); only the p8*/c8* frames and costs are missing, as expected.
- Cost submission: **1026-004242-r008-publish-cost** (spec `C:/qfb/shaderdev/r008/specs/p8-cost.json`, 39 jobs, 139 scenes,
  mode cost, so it runs after 08:00). Baselines: p8off (1440p master+v1), p8looff, p8pooff, c8off1/c8off0/c8offf/c8offe1/c8offe2
  (showcase world per pack; c8off1 is also p8pbr's baseline), c8offi0/c8offi1 (cit). p8pbr0w (QF_PBR 0 golden_lit) and p8d0/p8v15
  on golden_lit are extra: free bisect data for the golden_lit olive regression (critic fix 1).
- Lab footer (site/shaders/index.html) now credits Faithful 32x/64x (License v4) and Vanilla Normals Renewed.

## Publisher run 2026-10-26 (after 09:03)
- Step 1 done: 1026-015851 finished 09:02:58, all 39 jobs done, no failures.
- Step 2 done: critic notes for every p8* todo frame were already in critic.json (09:14, incl. `_r008_publish_summary`,
  6.3, "not yet: motes in the beams"); dry run exits 0. round.json "renders" now 1026-015851 (it still named 004242).
- Step 3: critic recorded terrain in every frame; clips p8clip*.webp 1.1-2.8 MB; intro WORST 4.6 ms, Low 0.32, Potato 0.30,
  no "?"; dust/metal texts edited by the critic (spec_scenes.py.pre-critic). OVER BUDGET: 10 p8 frames 3.5-4.6 ms > 3.0.
  Sheets 1/4/5/6 re-checked by eye: ground in night_sky, night_new, lake, river, biome_ocean, clips.
- Step 4 done: `finish_round.py ... --publish --no-push` committed **006fe9b** (r008.json, index.json, r007 closed).
  BOARD shaders row + journal updated. Footer was already in 1c916d5.
- **Left for after the push (orchestrator):** rounds/r008.json returns 200, then the Edge screenshot into r008\look\.
  `git log origin/main..main` holds 12 commits, incl. other sessions' balance commits 94a5e12, f4bbd0d.

## Next: the publisher (after 1026-004242-r008-publish-cost is done)
1. `py -3.10 -I tools/renderq/renderq.py results 1026-004242-r008-publish-cost` : every job done? A failed job = a missing frame/cost.
2. `cd C:\dev\quest-forge` then dry run: `py -3.10 -I -X utf8 tools/shaders/review/finish_round.py C:/qfb/shaderdev/r008`
   - It will stop with exit 3: the p8* frames have no critic notes. The critic looks at `C:/qfb/shaderdev/r008/critic-todo-N.jpg`
     and adds `"p8.../scene": {"score", "note"}` to `C:/qfb/shaderdev/r008/critic.json`, then re-run.
3. Check before posting:
   - **Terrain in every frame.** A boot on 10-26 (b1026000221) lost all terrain after the first scenes (uj). If any p8 frame
     has no ground (night_sky/night_new, lake, river, sky_noon, biome_ocean, clips), re-render those tags in a new submission;
     do not publish void frames.
   - The clips: `C:/qfb/shaderdev/r008/clips/p8clip*.webp` exist, each under 4 MB; the meteor clip actually shows streaks.
   - The sun crop (SUNBOX 970,505,480,270 in spec_scenes.py) is centred on the disk in p8, p8sun10, p8sun18 and qz.
   - The dust and metal question texts say the critic's honest notes; edit them if the p8 frames say otherwise.
   - OVER BUDGET lines (p8 3.0 ms, p8lo 0.9, p8po 0.4) and the intro's WORST/LOWP numbers (no "?").
4. Post: `py -3.10 -I -X utf8 tools/shaders/review/finish_round.py C:/qfb/shaderdev/r008 --publish`
   (add `--no-push` if pushing is left to the orchestrator). Then check site/shaders/rounds/r008.json is served (200),
   take the Edge screenshot, `git log origin/main..main` before any push. Commit the footer change with it if not yet pushed.

## Open for the shader track (not blocking the post)
Critic top fixes in `C:/qfb/shaderdev/r008/critic.json` (_loop3_summary): golden_lit olive (bisect), dust needs a near-beam view,
lake near Fresnel + glint column, metals need a real reflection, sky_noon deck.
