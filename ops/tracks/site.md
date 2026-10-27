# site: current state (rewrite, don't append; under 2 KB)

Updated 2026-10-26 (Mac).

- Rounds 4 to 6 are done and critic-passed. Round 6: Lucky (slam ripple instead of the ring,
  Steve's pace, 29 activities, an animal pen, big mobs path around trees); Krypt endless
  (10,000+ graves, 12 strata, 61 kinds, 12 set pieces, gap jumps, find a grave); 16 scares
  rebuilt FNAF-style, including gap deaths and the owner's pigman-ore idea; a mood layer; recorded
  CC0 screams (`site/lib/sfx/sources.json`).
- Lives on the Mac's local `main`: 133 commits ahead of origin/main, ~150 behind. Not pushed.
  Publishing needs a merge (the PC's `/online/` page wins) and the owner's word.
- Owner to check live: scares (J, then approve; `scares/approved.json` is empty), mood events
  (Shift+M; peeks are unverified in stills), screams by ear, Safari, phone.
- Open for the owner: a recorded voice if the CC0 screams fall short; Witchery/Twilight/HEE art
  plus the game-asset licence and publish route (`DECISIONS.md`, Site).
- Round 7 running (owner 2026-10-27: Krypt regressed vs round 5, scares too FNAF, screams digitized,
  Lucky act logic): lucky, krypt (opus), scares (opus), audio. Checkpoints `checkpoints/site-r7-*.md`.
  Enderman and Creeper approved for the director.
- Known: Krypt heap ~62 MB at grave 1,000 (37 MB a pass earlier), not yet profiled; four Lucky
  activity shots (harvest, sapling, notes, brew) are framed tight.
- Checks: `dump_frames.py --sheet`, `vet_lucky.py`, `audit_lucky.py`, `nav_check.py`,
  `check_sounds.py`, `node tools/site/check_krypt_plan.mjs`; preview `tools/site/serve.py`.
