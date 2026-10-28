# site: current state (rewrite, don't append; under 2 KB)

Updated 2026-10-28 (Mac).

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
- Lives on the Mac's local `main`, far ahead of origin/main and ~150 behind. Not pushed.
  Publishing needs a merge (the PC's `/online/` page wins) and the owner's word.
- Owner to do: test the scares (J); pick screams (scratchpad `r8/audio/audition/index.html`); say which scares go
  into random play and if the End islands stay floating.
- Open: Witchery/Twilight/HEE art, the game-asset licence and the publish route (`DECISIONS.md`, Site).
- Known: prison props 95 draw calls; Creeper blast hitch ~125 ms; empty hands draw no bare arm.
- Checks: `dump_frames.py --sheet`, `vet_lucky.py`, `audit_lucky.py`, `nav_check.py`, `check_sounds.py`,
  `node tools/site/check_krypt_plan.mjs`, `node tools/site/scare_flow.mjs`; preview `tools/site/serve.py`.
