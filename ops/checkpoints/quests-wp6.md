# quests: WP-6 drafts to decision 0004 (checkpoint 22:35)

Decision: docs/decisions/0004-prologue-and-act-i.md (no parties; voice rejected, samples lead;
damage-based boss credit with the killer highlighted, built separately: ops/checkpoints/quests-hunt-credit.md).

## Done (main)
- Drafts rebuilt with `--decisions` and no parties / no house voice (6acae6e).
- Jukebox recipe in qf-content (1e836c4); worktree C:\qfb\wt-jukebox at 1e836c4.

## Uncommitted in the tree (the agent's)
- docs/design/quests/act-structure.md, docs/design/quests/wp6-writing-brief.md.

## Next
1. Finish the brief: the samples lead (three registers as examples, invite a fourth); hunts use
   damage-based credit, killer highlighted; no party language. Finish act-structure §6 the same way.
   Commit both.
2. Build the jukebox jar (clean worktree at main head), one slim headless server boot to confirm the
   recipe registers; record version + SHA-1; do not install. Delete the trial.
3. `qb.py check` on both drafts; `qb.py path`; tally per act into the journal.
4. ops/BOARD.md quests row → "drafts and brief ready; writers' voice samples next (Mac)";
   ops/tracks/quests.md (create, under 2 KB); one line in ops/journal/quests.md.
