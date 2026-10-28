# site: current state (rewrite, don't append; under 2 KB)

Updated 2026-10-27 (Mac).

- Rounds 4 to 8 are done and critic-passed. Round 8 (owner's notes on scares, screams, floating props, scary mobs):
  - redone: Spider and Magma Cube (owner's scripts), Zombie (door break), Wither Skeleton (shadow on the wall),
    Blaze (from the grave), Ghast (one fireball);
  - `tools/site/scare_flow.mjs` fails on any sound left after a scare or Enter (Silverfish's chitter leaked);
  - nothing floats: `check_krypt_support.mjs` over 10,000 graves, run by `check_krypt_plan.mjs`;
  - screams: CC0/CC BY, ranked by Freesound downloads and ratings, own 'voice' bus; credits page;
  - Patrix mob skins load from `site/graves/tex/mobs-local/` (gitignored, never commit). Re-import with
    `tools/textures/mobs/import_patrix.py <zip>`. Our own painted skins are paused and gated (`?ownskins`).
- Approved for the director: Enderman and Creeper (`site/graves/scares/approved.json`).
- Lives on the Mac's local `main`: 202 commits ahead of origin/main, ~150 behind. Not pushed.
  Publishing needs a merge (the PC's `/online/` page wins) and the owner's word.
- Owner to do: pick screams on the audition page (scratchpad `r8/audio/audition/index.html`); test the 14 scares
  (J); say if the End islands should stay floating.
- Open: Witchery/Twilight/HEE art, the game-asset licence and the publish route (`DECISIONS.md`, Site).
- Known: prison block props cost 95 draw calls; Creeper explosion hitch of about 125 ms (approved, left as is).
- Checks: `dump_frames.py --sheet`, `vet_lucky.py`, `audit_lucky.py`, `nav_check.py`, `check_sounds.py`,
  `node tools/site/check_krypt_plan.mjs`, `node tools/site/scare_flow.mjs`; preview `tools/site/serve.py`.
