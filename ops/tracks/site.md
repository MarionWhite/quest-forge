# site: current state (rewrite, don't append; under 2 KB)

Updated 2026-10-25 (Mac, late).

- Work lives on the Mac's local `main` in `~/Desktop/QuestForge`: 24 commits ahead of
  origin/main, 150 behind. Not pushed. Publishing needs a merge (conflicts incl. the PC's
  `/online/` page, which wins) and the owner's choice of route (`ops/DECISIONS.md`, Site).
- Round 4 (owner's feedback on Lucky Block, the Krypt, First night), one checkpoint per agent
  in `ops/checkpoints/site-*.md`, brief `ops/briefs/site-3d-page.md`.
  - Done: first-night (e2bb765), audio bank + music (dbe8973), mob library + reel tiles
    (861286a), Krypt scares first pass (cb24bb5).
  - Critic fixes sent: scares (spider face, zombie camera inside mob, ghast framing, wall
    clipping, re-dump against new mob lib); mobs (OreSpawn ants scattered, robots 2-4 black,
    robot5, wings edge-on); outcomes (horde framing).
  - Running: lucky-stage (Steve, sky, drop-in, pan), lucky-outcomes (full vet, then fixes),
    krypt-world (camera focus, torches, lighting, ambience). Graves page fails to load until
    krypt-world finishes (`alcoveFor` export); scares hook line in graves/app.js waits on it.
- After all report: sound-name check vs `site/lib/sfx/manifest.json`, one Opus critic pass
  on fresh sheets, then report to owner.
- Verification: WebGL pages only via `?dump=1` + `tools/site/dump_frames.py --sheet`.
- Open for the owner: publish route; Mojang/OreSpawn assets on the public site vs the repo
  licence rule (both in `ops/DECISIONS.md`).
