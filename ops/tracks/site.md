# site: current state (rewrite, don't append; under 2 KB)

Updated 2026-10-26 (Mac).

- Rounds 4 and 5 are done and critic-passed. Round 5 (owner's review of round 4) fixed Steve's
  movement and work chain, the camera on his activities, props, the Close black screen,
  particles, a deep accuracy audit of all 306 Lucky outcomes (`tools/site/audit_lucky.py`),
  mob armour, a longer Krypt (15 segments), and 14 rebuilt scares (spec
  `docs/design/site/krypt-scares.md`), plus synthesized `qf.scare.*` sounds.
- Scares: J opens the test picker. `site/graves/scares/approved.json` is empty, so no random
  scares until the owner approves them one by one. All 14 were played live in headless Chrome:
  death screen, then Respawn back to the same spot, no errors.
- Lives on the Mac's local `main`: 81 commits ahead of origin/main, ~150 behind. Not pushed.
  Publishing needs a merge (the PC's `/online/` page wins) and the owner's word.
- Owner to check by hand: the scares (approve via J), audio by ear (screams are synthesized),
  Safari, phone.
- Open for the owner: the creepy-mood ideas (list in the session, not yet picked); publish
  route and game-asset licence (`DECISIONS.md`, Site).
- Round 6 running (owner review 2026-10-26): lucky (ring as slam effect, Steve's pace and 20+
  activities, big mobs vs tree), krypt-structures (mod catalogue), krypt-gen (10,000 graves,
  strata, gaps, find), scares (FNAF v3, gap deaths, opus), mood, audio (recorded CC0 screams).
  Checkpoints `checkpoints/site-r6-*.md`; specs `docs/design/site/krypt-{endless,mood,scares}.md`.
- Small follow-ups filed in checkpoints: Krypt `frameInner` dt clamp and chunk build while a
  scare holds the player (scares work around both); Enderman scream jaw in the mob library.
- Checks: `dump_frames.py --sheet`, `vet_lucky.py`, `audit_lucky.py`, `nav_check.py`,
  `check_sounds.py`; preview with `tools/site/serve.py`.
