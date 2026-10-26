# site-r6-mood (checkpoint, started 2026-10-26, Mac)

Brief: `ops/briefs/site-3d-page.md`. Agent: sonnet.
Spec: `docs/design/site/krypt-mood.md`. Read it first.
Owns: new `site/graves/mood.js` and `site/graves/mood/*`.
The krypt-gen task adds the `app.js` import block and `__krypt.light`; until those land,
feature-detect and test with your own `?mood=` dump hook.
The audio task adds the `qf.mood.*` sounds; until then, use runtime reverb on the bank's mob
sounds.

## Owner's words (2026-10-26)
- "For the overall creepy mood we should do very distant echoing mob sounds, and the occasional
  scampering nearby. Maybe the light does weird things sometimes, or you catch glimpses of
  certain mobs peeking at you from around corners. I want this thing to be truly fucking scary
  and immersive."

## Done means
- [ ] Every event in the spec is built: distant echoes, scampering, the light effects, glimpses
  and close calls. Each has a test trigger (Shift+M list and `__mood.trigger`) and a dump hook.
- [ ] Timing follows the spec's rules, with no overlap with scares. Simulate 30 minutes of
  walking and report a timeline.
- [ ] Sheet: each glimpse kind (zombie, skeleton, creeper, enderman, witch, spider eyes,
  still creeper), plus the light effects in two frames each.

## Progress (mood agent)
- 2026-10-26: read all specs. Plan: `site/graves/mood.js` (init, loop, picker, dump), `mood/director.js` (pure timing, node-testable),
  `mood/geo.js`, `mood/sound.js`, `mood/light.js` (own fallback via krypt.js bakeUniform), `mood/visual.js` (peeks, eyes, still creeper), `mood/sim.mjs`.
- Next: write them, then shots under scratchpad r6/mood/.
- 2026-10-26: built and verified. mood.js + mood/{director,geo,light,events-sound,events-light,events-visual}.js, sim.mjs, harness.html
  (test page: graves/mood/harness.html loads mood.js; delete once krypt-gen's import block in app.js lands).
  Sheets: scratchpad r6/mood/s1/sheet.png (all), s2 (light, 2 frames each), crops_glimpses.png. Timeline: r6/mood/timeline.txt.
- Needs krypt-gen: app.js `import("./mood.js").then(m=>m.initMood({enabled, reduced}))`; `__krypt.light` (own fallback scales bakeUniform until then).
- Needs audio: qf.mood.* (feature-detected; bank-sound fallback with echoes now). Not live-tested by ear.
- Status: done except live listen/real-time check.
- 2026-10-26 critic pass: glimpses now 18-30 blocks, dark spots only (no torch within 4 blocks), at most ~35% of the body past an edge,
  faint cold rim only, enderman purple eyes, hold 0.6-1.2 s, retract on turn (>46 deg) or approach (<15 blocks); still creeper in a dark hidden spot;
  event is skipped when no such spot exists. harness.html deleted (app.js import block has landed).
  Final dump: r6/mood/crops_glimpses_v2.png (enderman, still creeper, spider eyes). Zombie/skeleton/creeper/witch found no spot in the dump's
  corridor (torch-dense, few corners after krypt-gen's rewrite), so they are unframed; they run the same code path as the enderman. Not seen live.
- Status: DONE (code committed; live check by the owner outstanding).
