# balance: re-test after the 2026-10-25 enchant changes (checkpoint 22:35)

Decision: docs/decisions/0005-enchant-census-proposals.md. The owner: everything is retested
before anything ships; no further fight-length changes without a check-in.

## Done (all on main)
- P1 00fba6b, P2 537dee3, P4 2950908, P7 53a6284, P8 823f683, P9 20eef31, P6 config ad7f9f4.
- Worktree for the build: C:\qfb\wt-enchant (detached at ad7f9f4; rebase/recreate at main's head).
- An untracked `tools/balance/retest-2026-10-25.json` exists in the tree (the planned re-test set?);
  check it, keep or replace it, commit it.

## Next
1. Build qf-content from a clean worktree at main (`.\gradlew.bat build -x test` from PowerShell);
   record version + SHA-1 here. Do NOT install.
2. Launch the targeted census (C:\qfs\campaign tooling, tick-warp, headless, one node, ≤6 GB total;
   check free RAM; `trial.py guard` before/after): capped T4 trio + Naga for P1/P2 (singles + the
   four evidence pairs), Naga + one T3 for P7, Baba Yaga or DeathReaper for P8, Rahovart for P6.
   Start it detached, write the run folder and expected finish time here, and EXIT (never wait).
3. A fresh agent (triage first: did it finish?) writes §9 "Re-test after the 2026-10-25 changes"
   in docs/reference/enchantment-combat-results.md (old vs new per change, same measures), then
   reports whether the jar is ready to install. The owner decides the install.

## Rules
Renders never; servers headless only; stage only own hunks; report in five lines; detail to
ops/journal/balance.md.
