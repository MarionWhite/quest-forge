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
