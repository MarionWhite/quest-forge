# site: current state (rewrite, don't append; under 2 KB)

Updated 2026-10-25 23:30 (Mac).

- Work lives on the Mac's local `main` in `~/Desktop/QuestForge`: 9 commits ahead of
  origin/main, ~107 behind. Not pushed. Publishing needs a merge (6 conflicts, incl. the PC's
  `/online/` page, which wins) and the owner's choice of route (`ops/DECISIONS.md`, Site).
- Live round: owner's round-4 feedback on Lucky Block, the Krypt and First night. Seven agents
  run in parallel, one checkpoint each in `ops/checkpoints/site-*.md`; brief template
  `ops/briefs/site-3d-page.md`. Builders are Sonnet against Opus-written specs; the critic pass
  (contact sheets, `tools/site/dump_frames.py --sheet`) is Opus. First-night fact review is Haiku.
- Shared pieces: `site/lib/three` (three.js 0.160), `site/lib/qfaudio.js` (sound engine, done),
  `site/lib/sfx/` (bank, in progress), `site/lib/mc/` (mob library, in progress).
- Verification: WebGL pages only via `?dump=1` + `tools/site/dump_frames.py` (headless
  screenshots return stale frames).
- Open for the owner: publish route; Mojang/OreSpawn textures and sounds on the public site
  vs the repo licence rule (both in `ops/DECISIONS.md`).
