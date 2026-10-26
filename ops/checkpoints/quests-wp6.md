# quests: WP-6 drafts to decision 0004 (checkpoint 2026-10-25 22:45, project paused by the owner)

Decision: docs/decisions/0004-prologue-and-act-i.md (no parties; voice rejected, samples lead;
damage-based boss credit with the killer highlighted, built separately: ops/checkpoints/quests-hunt-credit.md).

## Done (all on main, nothing uncommitted from this task)
- 6acae6e: WP-5 and WP-6 drafts rebuilt with `--decisions docs/decisions/answers/s001.json`: no 478,
  no party text, `party_enable` 0, no house voice (moved quests keep the shipped text; new quests and
  act tabs carry neutral `[WRITE: ...]` placeholders). `wp6_acts.py --no-parties` documented, always on.
- 1e836c4: qf-content jukebox recipe (vanilla jukebox + any blank Record, shapeless) and a `[recipes]`
  log line at init.
- 8b29c67: wp6-writing-brief.md (voice samples lead: 1, 473, 481 in three registers given as examples,
  a fourth invited, no tone dictated; per-quest rows; damage-based credit line) and act-structure.md
  (status + §6 rewritten without parties; damage credit as the planned rule).
- Checks: `qb.py check` passes on both drafts; `qb.py path` shows every act opening strictly after
  the one before; each patch re-run on its own draft changes no bytes.
- Jar from clean worktree C:\qfb\wt-jukebox at main head e0a1ca4 (mod head 20eef31):
  version 1.1.0+20261025.20eef315, SHA-1 79A67860B4B6BD49D28C3695F909B7D7C79115E4, 23679185 bytes,
  C:\qfb\wt-jukebox\mods\qf-content\build\libs\QuestForgeContent-1.0.0.jar. NOT installed.
- Slim headless server boot (qfcontent + base) logged
  `[qfcontent/qfcontent]: [recipes] 11 recipes make qfcontent items; the jukebox is a vanilla jukebox
  plus a blank record, shapeless`; 8 mods loaded; trial removed; guard OK before and after.
- Tally per act (best case, `qb.py tally --book ...wp6.json`): Prologue Common bag/tome, 0/5 lucky,
  0/0 diamonds; Act I Uncommon, 0/20, 12/16; Act II Rare, 0/30, 12/36; Act III Epic, 0/30, 78/72 OVER;
  Act IV Legendary, 8/40, 144/free; Epilogue Legendary bag, no tome. Quests per act: 16/7/18/32/18/3.

## Remaining (not started; the owner paused the project)
1. ops/BOARD.md quests row → "drafts and brief ready; writers' voice samples next (Mac)".
2. Create ops/tracks/quests.md (under 2 KB) from the Done list above; then delete this checkpoint.
3. `git worktree remove C:\qfb\wt-jukebox` once the jar is no longer wanted (the hunt-credit task
   may rebuild qf-content anyway).
4. When the dump is rebuilt, the dead-item census stops calling `qfcontent:qf_jukebox` creative-only
   (tools/quests/README.md notes it).
5. The Mac side: voice samples per wp6-writing-brief.md §1, then Decisions sheet 2.
