# site-r5-lucky-flow: DONE 2026-10-26 (checkpoint, Mac)
Sheet: /private/tmp/claude-503/-Users-suaz-Desktop-QuestForge/91769071-2ed0-4412-b25d-3c510232d8e5/scratchpad/r5/lucky-flow/sheet/sheet.png (4 results + phone width, real clicks, real time)
All sweeps: 35 scenes closed in real time, 306 drops seeked with no exception; Break-another then Close works.

Brief: `ops/briefs/site-3d-page.md`. Agent: sonnet.
Owns: `site/lucky/app.js`, `site/lucky/stage.js`, `site/lucky/particles.js`, `site/lucky/sky.js`,
`site/lucky/index.html`.
Previous state: `ops/checkpoints/site-lucky-stage.md`.

## Owner's words (2026-10-26)
- "When you press close after the results of a block the screen just goes black."
- "The ambient particles still freeze when a block is broken sometimes."

## Done means
- [ ] **Close:** pressing Close after any result dips and comes back to the idle camp, with Steve
  resuming his activities. Test the real click path, not only `?closetest`: drive `closeResult()`
  from a dump hook that runs the same code as the button, including the `dip`. Find why the
  screen stays black; likely suspects are the `#dip` opacity, a render loop paused while
  hidden, `st.hold`, a camera left inside geometry, or the composer.
- [ ] Close also works after Break-another, after a structure scene, after a boss scene (sky
  darkened), and at phone width.
- [ ] **Particles:** the ambient particles never freeze, including through break, shatter, reel,
  scene and close, and after a tab switch. Find the cause: the particle clock, a dt clamp, a
  stepped flag, a frustum or instance count, or the pool being reused by the shatter. Prove it
  with dumps at several times in each phase comparing particle positions (they must change), or
  with a small timing log in the dump JSON.
- [ ] Sheet: before Close, during the dip, and after Close at 0.5 s and 2 s, for 3 result types;
  plus the particle-motion evidence.

## Done
- 2026-10-26 Close black screen REPRODUCED in real time (CDP driver, scratchpad r5/lucky-flow/cdp.mjs + flow2.js, serves site on :8123):
  anvil_trap, bedrock_problem, lava_trap, lucky_choice leave `#dip` at opacity 1 forever. Root cause: `S.clearTemp()` threw
  `o.material.dispose is not a function` (meshes with a material ARRAY), inside the dip's setTimeout, so `lift` never ran.
  Fixed in stage.js (clearTemp handles arrays) and app.js (`dip` try/catch + always lifts, with a 400 ms fallback timer).
- Debug hooks in app.js: `?flowdbg=1` exposes window.__qf; `?flowclose=ms` / `?flowbreak=ms` dump hooks with a probe trace.
- Next: re-run the sweep, then find the particle freeze (real-time trace of emberY/ashY/solidN through break).

- Particle freeze ROOT CAUSE (proved with real-time probe, br/fxold.json vs br/fxnew.json in the scratchpad): `buildScene` was followed by
  `st.fx.length = 0`, wiping the live updaters (the 80-point reveal burst at T_WIN+0.7, 1.1 s life, plus scene-start puffs/lights) while
  their Points stayed in S.temp, so they hung frozen in mid-air for the whole scene. Removed. Old: burst y-sum stuck at 158.244, opacity 0.8 for 2.7 s;
  new: animates and is gone in 1.2 s.
- Break stalls (all motion pausing 100-300 ms): first draws compiled shaders/uploaded textures mid-break. Added `warmStage()` at boot and `prebuildReel()` while mining.
  Headless result: reel/mine/shatter gaps gone. Remaining ~170 ms gap right at the Break click is the page's first-gesture handler (audio unlock?), not mine: see Requests.
- Commits: 0599b29 (close), next commit (particles + warm-up).
- Still to do: final sheet (before close / dip / +0.5 s / +2 s for 3 results), phone width, Break-another, journal line, mark done.

## Requests
- audio agent / qfaudio.js: the first user gesture (Break click) stalls the main thread ~170 ms (measured as the synchronous cost of
  `breakBtn.click()` with all of breakWith ~0 ms). Likely AudioContext creation/unlock; create/resume it earlier (on pointerdown or page load) so it is not inside the click.
