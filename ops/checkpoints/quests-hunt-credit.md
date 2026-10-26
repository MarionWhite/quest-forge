# quests: damage-based hunt credit in qf-content (checkpoint 22:35)

Decision: docs/decisions/0004-prologue-and-act-i.md. No parties. Everyone who damaged a boss gets
the hunt-task credit; "the person who dealt the killing blow should get highlighted in some way."

## Done
- Worktree C:\qfb\hunt-credit\wt on branch `hunt-credit` (at ad7f9f4). Nothing written yet.

## Design (from the brief)
- Server-side damage ledger per boss-class entity (hunt targets from the quest DB or max health >
  configurable 100), damage per player UUID (pets/minions → owner, projectiles → shooter), dropped
  on death/unload.
- On death: every contributor above a minimum share (default 5 % of max health) gets the hunt task
  progress exactly as a kill would (BetterQuesting API; respect required counts).
- Highlight: server-wide chat line (lang key) naming the killer, then the contributors; optional
  title to the killer via QFNetwork if cheap.
- Config: enabled, min share, health threshold.

## Next
1. Read BQ/Standard Expansion jars (READ ONLY, javap into C:\qfb\hunt-credit\) for TaskHunt's kill
   path and the API to progress a task for a UUID. Write the handler as new files + minimal
   registration (another agent edits qf-content's recipes; rebase before commit).
2. Build; test on a slim headless server with a `-Dqf.huntcredit.test=1` debug command (two
   FakePlayers damage then kill a boss): contributor credited, killer credited, chat line,
   below-threshold ignored, non-boss ignored. One server at a time; check RAM.
3. Docs: act-structure §6 rule + thresholds; tools/quests/README.md line. Commit; record jar
   version + SHA-1; do not install. Checkpoint after each step.
