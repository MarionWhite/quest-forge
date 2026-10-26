# site-r5-lucky-flow (checkpoint, started 2026-10-26, Mac)

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
