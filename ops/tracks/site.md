# site: current state (rewrite, don't append; under 2 KB)

Updated 2026-11-24 (Mac).

- Rounds 4 to 8b are done and critic-passed. Round 8b (owner's notes of 10-27):
  - redone: Wither Skeleton "Too tall to follow", Skeleton "Bone pile" (`scares/ossuary.js`); Zombie: you back off
    and run (`scares/chase.js`);
  - no mob flash at the J press; `scare_flow.mjs` checks every frame from J;
  - one hotbar (`scares/loadout.js`): the selected slot is what the hand holds; items drop at death;
  - held items read in the dark; Steve's bow on the Lucky page uses the 1.7.10 bow transform;
  - a scare that finds no room plays another, never silence.
- Round 8: Spider, Magma Cube, Zombie door, Blaze grave, Ghast; sound-leak check; nothing floats
  (`check_krypt_support.mjs`); screams CC0/CC BY with credits; Patrix skins local only
  (`site/graves/tex/mobs-local/`, gitignored, never commit; `import_patrix.py <zip>`).
- Approved for the director: Enderman and Creeper (`site/graves/scares/approved.json`).
- Published 2026-11-24: merged with origin/main and pushed (decision 0008: vanilla and OreSpawn assets, credited).
  The Shader Lab card stays off the homepage (owner, 10-25: /shaders/ by URL only).
- Owner to do: test the scares (J); pick screams (the audition page needs a rebuild); say which scares go
  into random play and if the End islands stay floating.
- Open: Witchery/Twilight/HEE art.
- Known: prison props 95 draw calls; Creeper blast hitch ~125 ms; empty hands draw no bare arm.
- Checks: `dump_frames.py --sheet`, `vet_lucky.py`, `audit_lucky.py`, `nav_check.py`, `check_sounds.py`,
  `node tools/site/check_krypt_plan.mjs`, `node tools/site/scare_flow.mjs`; preview `tools/site/serve.py`.
