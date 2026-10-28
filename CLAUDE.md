# Quest Forge: instructions for every agent

A 1.7.10 modpack for a small friends' server: an AAA questline, CrazyCraft-style power leaps,
runs on weaker PCs, and its own shader and texture pack. This repo is public, so secrets,
tokens and friends' personal details never go in it.

## Start here
1. Read `ops/BOARD.md`, the state of every track.
2. If you were given a brief, read `ops/briefs/<name>.md` and your track's `ops/tracks/<track>.md`.
   Read nothing else up front; open other files only when the task needs them.
3. If a checkpoint exists for your task, `ops/checkpoints/<task>.md`, resume from it.

## Hard rules
- **The live game** is `%APPDATA%\.crazycraft4`. It is never written to except by
  `py -3.10 -I tools/trial/trial.py install`. Run `trial.py guard` before and after any work on a game dir.
- **Renders go through the queue:** `tools/renderq/renderq.py submit|status|wait|results`.
  Never launch a Minecraft client yourself. One client at a time; the queue enforces it.
- **Clients are background-only:** never focused, never audible, never over the owner's game. Never pass `--busy-ok`.
- **Gameplay and balance changes need the owner's yes.** Put the question in `ops/DECISIONS.md`.
- **Commit every fix, staging only your own hunks.** Other sessions share the tree.
  Before pushing, check `git log origin/main..main`.
- Licences: only Faithful-licensed or redistribution-permitting art ships. All-rights-reserved packs are
  studied, never copied, traced or recoloured. **Exception (owner, 2026-10-27): Stay True, Faithless, Patrix 32x,
  Conquest_ and Soartex** (the packs named in r007 feedback) may be copied and edited into the private pack. Their
  files live only in `C:\qf-world\reference-packs` and are read at build time: never commit them, and never show
  them on the public site.
- Use `py -3.10` for the tools/ scripts.

## How to work cheaply without losing quality
- **Never wait inside an agent.** For a short wait (under 10 min), make one blocking call:
  `renderq.py wait ID` as a single foreground command, with no polling loops and no background tasks.
  For anything longer, write your checkpoint and exit. A fresh agent resumes when the work lands.
- **Checkpoint after every step** to `ops/checkpoints/<task>.md`: what's done, what's next, file
  paths and render IDs. Running out of context must never lose work.
- **Report in five lines or fewer:** outcome, links, anything that needs the owner. Put detail in the
  track journal (`ops/journal/<track>.md`, dated entries, newest first), not in the report.
- **Review images as contact sheets and crops** (`tools/shaders/review/check_frames.py`), not as
  full frames. Only review frames whose image changed; the render cache knows which.
- **Bulk independent items go through the batch lane** (`tools/ops/batch.py`, 50% off, API credits): critic first passes, quest voice variants, item descriptions. Check `tools/ops/ledger.py status` first; see ops/README.md "API credits".
- **Deterministic steps belong to scripts, not to agents:** rendering, costs, publishing
  (`finish_round.py`), feedback fetch (`fetch_feedback.py`).
