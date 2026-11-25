# balance: re-test after the 2026-10-25 enchant changes (checkpoint 22:55, project paused)

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

## The census is running detached (owner paused the project at 22:50; it was left running)
- **Progress:** `type C:\qfs\campaign-v3\driver-v3.log` (one line per job start/done; ends with
  "campaign complete"); `dir C:\qfs\campaign-v3\R-*inished.json`; cells measured so far on the
  node: `findstr /c:"first swing" C:\qfs\c4\census-run.log | find /c /v ""`. At 22:55 the Naga job
  (120 cells) had finished in 125 s and Mobzilla was running; the queue should end about 23:10-23:30.
- **Results:** `C:\qfs\campaign-v3\R-<job>\` holds `qfcontent-census-combat.tsv` (the balance
  sheet), `-procs.tsv`, `-failed.tsv`, `census.log` and `finished.json` (or `failed.json`). The
  driver copies them there when each job's server exits; nothing is lost if it is left alone.
- **Pause:** create `C:\qfs\campaign-v3\PAUSE` (the running job finishes, no new one starts);
  delete it to carry on. **Stop:** `taskkill /PID 19888 /F` (the driver), then the server:
  PowerShell `Get-CimInstance Win32_Process -Filter "Name like '%java%'" | Where-Object { $_.CommandLine -like '*qf.census.combat*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }`.
  **Resume:** the launch command above, unchanged (jobs with finished.json are skipped).
- `C:\qfs\c4\census-err.log` carries NPE spam (152 by 22:52; first frame: cpw.mods.fml.common.network.FMLOutboundHandler$OutboundTarget$4.selectNetworks(FMLOutboundHandler.java:109)); the census
  log shows cells landing normally, so treat it as the known harmless kind unless a job fails.
- The build worktree C:\qfb\wt-enchant (detached at ad7f9f4) holds the jar; remove it with
  `git worktree remove C:\qfb\wt-enchant` once the jar has been installed or rebuilt.

## Update 2026-10-26: steps 1-2 DONE
- Census finished 22:53:21 ("campaign complete"); all 8 R-* have finished.json, no failed.json.
- c4 rahovart.json restored from .orig; `trial.py guard` OK (112 live jars match).
- **Next is step 3** (write §9 using qfcampaign.py on the R-* tsvs vs v2), then step 4.

## Next (a fresh agent, when the owner resumes)
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

## Update 2026-10-26 (later): step 3 DONE
- §9 written at the end of docs/reference/enchantment-combat-results.md (pooled reps, no per-rep sd yet).
  Findings: DoTs, P8 hits, P6 landed; P7 cost is 3-5 health not ~10; colossus+venomous Mobzilla synergy +24.5 remains.
- **Next is step 4 remainder:** journal entry in ops/journal/balance.md, then report; owner decides install of the jar.
  Optional: per-rep sd; remove worktree C:\qfb\wt-enchant after install.
