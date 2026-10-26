# site: current state (rewrite, don't append; under 2 KB)

Updated 2026-10-26 (Mac).

- Round 4 is done and critic-passed: Lucky Block (stage, Steve, drop-in, all 306 outcomes),
  Krypt (9 segments, stone focus, torches, gate, ambience, 14 scares), First night, audio bank
  + music, shared mob library. Detail in `journal/site.md`; per-task state in
  `checkpoints/site-*.md` (all done).
- Lives on the Mac's local `main` in `~/Desktop/QuestForge`: 42 commits ahead of origin/main,
  ~150 behind. Not pushed. Publishing needs a merge (conflicts incl. the PC's `/online/` page,
  which wins) and the owner's choice of route.
- Owner to check by hand: audio, Safari, scroll feel, phone (headless Chrome can't go under
  500 px wide).
- Checks: `tools/site/dump_frames.py --sheet` (WebGL frames), `tools/site/vet_lucky.py`
  (every Lucky outcome; `--jobs 2`, rerun timeouts alone), `tools/site/check_sounds.py`.
- Open for the owner (`DECISIONS.md`, Site): publish route; Mojang/OreSpawn textures and
  sounds on the public site vs the repo licence rule (`build_sfx.py --own-only` drops them).
- Round 5 (owner review 2026-10-26: "really good"): seven tasks, checkpoints
  `checkpoints/site-r5-*.md`: lucky-life, lucky-accuracy (deep audit), lucky-flow, mobs-gear,
  scares (v2 spec `docs/design/site/krypt-scares.md`, opus), krypt-more, audio (scare sounds).
- Next: critic pass on r5 sheets, then owner review; publish only on their word.
