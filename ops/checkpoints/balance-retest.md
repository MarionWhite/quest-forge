# balance: re-test after the 2026-10-25 enchant changes (checkpoint 22:45)

Decision: docs/decisions/0005-enchant-census-proposals.md. The owner: everything is retested
before anything ships; no further fight-length changes without a check-in.

## Done (all on main)
- Code: P1 00fba6b, P2 537dee3, P4 2950908, P7 53a6284, P8 823f683, P9 20eef31; config P6 ad7f9f4.
- Docs dated per change: d018367 (tuning rows + "Census pass, 2026-10-25", enchantments.md
  architecture notes, list rarities, ground-truth status note).
- Driver: 2487b12 adds `run_campaign.py --jobs FILE` (replicates via reps, `pin=false` re-samples a
  boss) and `--heap`; the queue is `tools/balance/retest-2026-10-25.json` (committed).
- **Jar built** from the clean worktree C:\qfb\wt-enchant (detached at ad7f9f4; main's head is
  e0a1ca4+ but no later commit touches mods/qf-content, so the version is the same):
  `C:\qfb\wt-enchant\mods\qf-content\build\libs\QuestForgeContent-1.0.0.jar`
  version **1.1.0+20261025.20eef315**, SHA-1 **79a67860b4b6bd49d28c3695f909b7d7c79115e4**,
  23,679,185 bytes, release variant (no AutoShot). Copy at C:\qfs\campaign-v3\QuestForgeContent-1.0.0.jar.
  **Not installed.** `trial.py guard` was OK before the run.
- **Census launched detached 22:37:21** (driver pid 19888, node C:\qfs\c4 only, -Xmx4G, tick-warp):
  ```
  py -3.10 C:\qfs\campaign\run_campaign.py --nodes C:\qfs\c4 --jar C:\qfs\campaign-v3\QuestForgeContent-1.0.0.jar ^
      --out C:\qfs\campaign-v3 --jobs C:\qfs\campaign-v3\retest-2026-10-25.json --tickwarp --timeout-hours 1.5
  ```
  (C:\qfs\campaign\run_campaign.py is a copy of the repo's 2487b12 version.) Log:
  `C:\qfs\campaign-v3\driver-v3.log`. Results land in `C:\qfs\campaign-v3\R-*\` (finished.json per job).
  8 jobs: Naga x5 reps (6 DoT/P2 enchants, singles + all 15 pairs), Mobzilla x3 (same), The King x3
  and The Queen x3 (3 DoTs + pairs), Mantis x5 (cultist + 3 DoTs + pairs), Baba Yaga x5 and
  DeathReaper x5 (bastion), Rahovart x1 unpinned (re-sampled under the P6 config; controls=5).
  **Expected finish about 23:30** (estimate 35-55 min; v2 pairs jobs took 130-380 s each plus ~50 s boot).
- `C:\qfs\campaign-v3\refs.json` = the v2 references minus demonmobs.rahovart (so every other boss is
  the same opponent as v2; Rahovart re-samples).
- Node c4 carries the P6 config overlay: `C:\qfs\c4\config\MobProperties\demonmobs\rahovart.json` is
  the repo file; the original is saved as `C:\qfs\campaign-v3\c4-rahovart.json.orig`.

## Next (a fresh agent)
1. Triage: `type C:\qfs\campaign-v3\driver-v3.log` ends with "campaign complete"? Every R-* has
   finished.json? A failed.json: read the node's `C:\qfs\c4\logs\fml-server-latest.log` and
   crash-reports; re-run with the same command (finished jobs are skipped).
2. Restore the node: `copy C:\qfs\campaign-v3\c4-rahovart.json.orig C:\qfs\c4\config\MobProperties\demonmobs\rahovart.json`.
   Run `py -3.10 -I tools/trial/trial.py guard`.
3. Write §9 "Re-test after the 2026-10-25 changes" at the end of
   docs/reference/enchantment-combat-results.md: per change, old (v2: `C:\qfs\campaign\<job>\`) vs
   new (`C:\qfs\campaign-v3\R-*\qfcontent-census-combat.tsv`), speed-up % and TTK, mean +- sd over
   the reps, and whether it landed where §6 predicted. Measures:
   - P1/P2: rupture/venomous/poisonous speed-up on Mobzilla, The King, The Queen (v2 +40..50%,
     predicted +10..15%) and Naga (v2 +25/+20/+16, predicted little change); the four pairs'
     synergy beyond independence (v2: colossus+rupture Naga +41 / Mobzilla +33, colossus+venomous
     Naga +46, roulette+rupture Mobzilla +57, cultist+poisonous Mobzilla +29; predicted about 0).
     `tools/balance/qfcampaign.py <tsv...> --markdown out.md` computes speed-ups and synergies.
   - P7: cultist `probe_hp_min` on Naga (v2 1.0-1.76) and Mantis (v2 20.0); predicted about 10
     health lost at both tiers (floor 1.0 if driven there); cultist speed-up unchanged (+17%).
   - P8: bastion on Baba Yaga (v2 TTK 114.8 s vs control 52-54 s, hits 56/80) and DeathReaper
     (v2 28.6 s vs 14.8 s, 70/80); predicted about 0% and 80/80 hits.
   - P6: Rahovart reference health in `R-T3-demonmobs.rahovart-p6\census.log` ("reference
     target ... maxHealth") vs 42,249; control TTK vs 845 s (predicted about 13,500 and ~270 s).
   - Anything that moved that should not have: Colossus, Roulette, Cultist singles on Naga and
     Mobzilla (same opponent, same jar apart from the changes).
4. Commit §9 (stage only that file), update this checkpoint and ops/journal/balance.md, report in
   five lines: is the jar ready to install (the owner decides the install).

## Not re-measured (documented command)
Levels I/II/III of the DoTs, Cultist on T2/T4, Bastion on Huntsman/Monking/Mantis, Rahovart at
T4, and the rest of the 14-enchant pair set. Add jobs to tools/balance/retest-2026-10-25.json
(or a new file) and run the same command with a new --out; `levels=all` for the level sweep.

## Rules
Renders never; servers headless only; stage only own hunks; report in five lines; detail to
ops/journal/balance.md.
