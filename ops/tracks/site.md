# site: current state (rewrite, don't append; under 2 KB)

Updated 2026-10-27 (Mac).

- Rounds 4 to 7 are done and critic-passed. Round 7 (owner: Krypt regressed vs round 5, scares too
  FNAF, screams digitized, Lucky act logic) fixed:
  - the Krypt focus swing (0 to 0.65 reversals per 10 s);
  - props with common sense, and 15 story rooms (repeats in 6% of 600-block windows, was 87%);
  - round 5's cold-to-warm depth light, restored;
  - texture arrays (phone draw calls about -30%);
  - scares rebuilt in the Story Mode style, with Enderman and Creeper untouched;
  - one real CC0 voice per scream, at 48 kHz;
  - Lucky world-state persistence, no phasing, enchanting table, XP bottles;
  - a mood.js boot crash, fixed (no mood event had ever played live).
- Approved for the director: Enderman and Creeper (`site/graves/scares/approved.json`).
- Lives on the Mac's local `main`: 181 commits ahead of origin/main, ~150 behind. Not pushed.
  Publishing needs a merge (the PC's `/online/` page wins) and the owner's word.
- Owner to check live: the 14 other scares (J), mood (Shift+M), the screams (preview in the scratchpad
  `r7/audio/preview/`), Safari, phone.
- Open: Witchery/Twilight/HEE art, the game-asset licence and the publish route (`DECISIONS.md`, Site).
- Known: prison block props cost 95 draw calls (props not yet in the texture array); Creeper
  explosion hitch of about 125 ms (approved scare, left as is).
- Checks: `dump_frames.py --sheet`, `vet_lucky.py`, `audit_lucky.py`, `nav_check.py`,
  `check_sounds.py`, `node tools/site/check_krypt_plan.mjs`; preview `tools/site/serve.py`.
