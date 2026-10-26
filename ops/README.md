# ops/: the working harness

The state of all work lives here, not in anyone's context. Any agent on any machine (the
owner's PC or Mac) starts from these files, does one bounded task, and leaves them current.

| File | What it holds | Who writes it |
|---|---|---|
| `BOARD.md` | one row per track: status, next step, blocker, owner | whoever changes a track's state |
| `DECISIONS.md` | every open question for the owner, with options and a recommendation | anyone; the owner answers through the Decisions page |
| `tracks/<track>.md` | that track's **current state**, under 2 KB: what is true now | the agent that changed it (rewrite, don't append) |
| `journal/<track>.md` | dated history, newest first, one short entry per task | append-only |
| `briefs/<name>.md` | reusable task templates; the orchestrator fills in a few lines | edit when the process changes |
| `checkpoints/<task>.md` | an in-flight task's progress, so a fresh agent can resume | the running agent; deleted when the task is done |

## Who does what (`.claude/agents/`)
| Agent | Model | Job |
|---|---|---|
| `shader-dev` | opus | shader design and code: the quality-critical work |
| `texture-dev` | opus | texture art direction and pack building |
| `critic` | opus | judges frames against the look bible, the owner's feedback and the reference packs |
| `writer` | opus | quest and lore writing |
| `publisher` | sonnet | runs `finish_round.py`, verifies the page, pushes |
| `researcher` | sonnet | licence checks, pack and technique research, summaries with sources |
| `triage` | haiku | status checks, log reading, "did X finish, what failed" |

Scripts take every deterministic step: `renderq` (renders, costs, cache), `finish_round.py`
(spec and publish), `fetch_feedback.py`, and the watchers in `tools/ops/`.

## A shader round, end to end
1. Feedback arrives (issue "Shader Lab feedback: round N"). The watcher runs
   `fetch_feedback.py` and appends an event to `ops/inbox.log`.
2. The orchestrator reads the feedback and fills in `briefs/shader-round.md` and `briefs/texture-iteration.md`.
3. `shader-dev` and `texture-dev` run in parallel. Each submits renders to renderq, checkpoints, and
   resumes when the results land.
4. `critic` reviews contact sheets of the changed frames against the references, and writes `critic.json`.
5. `shader-dev` gets one more loop if the critic says the leap isn't there yet.
6. `publisher` runs `finish_round.py --publish`, checks for a 200 and a screenshot, then pushes.
7. The watcher waits for the owner's answers. Waiting costs zero tokens.

The orchestrator session stays short. It reads BOARD.md, starts the next step and exits. A new
session per round costs nothing, because the state lives here.
