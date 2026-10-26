# site: current state (rewrite, don't append; under 2 KB)

Updated 2026-10-26 (Mac).

- Work lives on the Mac's local `main` in `~/Desktop/QuestForge`, well ahead of origin/main
  and ~150 behind. Not pushed. Publishing needs a merge (conflicts incl. the PC's `/online/`
  page, which wins) and the owner's choice of route (`ops/DECISIONS.md`, Site).
- Round 4 (owner's feedback on Lucky Block, the Krypt, First night). Checkpoints in
  `ops/checkpoints/site-*.md`, brief `ops/briefs/site-3d-page.md`.
  - Done and critic-passed: first-night, audio bank + music, mob library + reel tiles,
    Krypt world (9 segments, alcove torches, stone focus, gate + ambience), Krypt scares
    (14 mobs, set matches the segment via `getWalk().segment`), Lucky stage (sky, drop-in,
    Steve's activities, "!", pan, rarity torches, phone fit).
  - Running: lucky-outcomes, v3 vet of every drop, then final fixes.
- Known approximations: Mothra (no jar model, luna-moth texture), horse gait, ender dragon
  static, slime has no face in scares. Phone checked only near-square (headless Chrome
  clamps width to 500).
- Not verified by anyone: audio by ear, Safari, real scroll feel. Owner to check.
- Checks: `tools/site/dump_frames.py --sheet` (WebGL frames), `tools/site/check_sounds.py`
  (sound names vs bank).
- Open for the owner: publish route; Mojang/OreSpawn assets on the public site vs the repo
  licence rule (both in `ops/DECISIONS.md`).
