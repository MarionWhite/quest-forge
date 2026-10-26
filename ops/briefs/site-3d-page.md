# Brief: a site 3D page task (agent: general-purpose on sonnet; critic on opus)

Fill in: task name, owned files, the owner's words for this task, "done" checklist.

## Rules (on top of CLAUDE.md)
- Read: CLAUDE.md, `ops/tracks/site.md`, your checkpoint `ops/checkpoints/site-<task>.md` if it
  exists, then only the files your task names. Shared design rules: the scratchpad briefs
  `round3.md`/`round4.md` until they are folded into `docs/design/site/`.
- Own only your files. Others run in the same tree at the same time.
- Checkpoint after every step to `ops/checkpoints/site-<task>.md`: done, next, file paths,
  frame dirs. Running out of context must lose nothing.
- Never wait. No polling loops or sleeps for other agents. If blocked on someone else's file,
  do the independent work, then checkpoint "blocked on X" and exit.
- Verify WebGL only with `python3 -I tools/site/dump_frames.py OUTDIR --list shots.txt --sheet`
  (pages implement `?dump=1`). Look at the sheet, then crops. One verify-fix loop, not ten.
- Read big files in slices (lucky.json, items.json). Don't re-read unchanged files.
- Commit your own paths at each milestone: `git commit -m "<msg>" -- <your paths>`
  (end the message with the Co-Authored-By line). Never `git add -A`. Never push.
- Finish: delete nothing of others', update your checkpoint to "done", add one dated line to
  `ops/journal/site.md`, report in five lines or fewer with the sheet path.

## Done means (script-checkable where possible)
- `node --check` passes on .mjs copies of every module touched.
- Every frame in the task's shot list dumps (no "NO DUMP", no `errors` in its JSON).
- Every sound name used exists in `site/lib/sfx/manifest.json`.
- The task's own checklist below is ticked in the checkpoint.
