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

## API credits
Anthropic API credits, kept apart from the subscription. The owner's two caps (2026-10-26), shared by
every lane: **$200 per calendar month and $50 per day**. Within them, spend freely on whatever the work
needs. Lanes only label what a spend was for. Every spend is one line in `ops/api-ledger.jsonl`
(committed, so the Mac sees it too); check before spending, never guess.

| Lane | For |
|---|---|
| continuity | carrying a checkpointed task on, e.g. while the subscription is at 90 % or more |
| batch | bulk independent items through the Batches API (50% off) |
| automation | scheduled and watcher jobs |
| reserve | anything else |

Commands (all `py -3.10 -I tools/ops/...`):
- `ledger.py status` shows month-to-date, today and projected month-end per lane, and what is left under the two caps;
  `ledger.py check LANE EST_USD` exits non-zero if the spend would break the day or month cap.
- `api_run.py --lane L --model opus|sonnet|haiku --task NAME [--checkpoint NAME | --brief F | PROMPT]`
  runs headless `claude -p` in the repo, checks the ledger first, caps the run with `--max-budget-usd`
  and logs the cost Claude Code reports. `--dry-run` shows the plan without spending.
  Permission mode is `dontAsk` with an explicit allowlist (read/edit, `py -3.10 -I tools/*`, git status/diff/log/add/commit;
  `trial.py install` and `git push` denied). Not `bypassPermissions`: the harness rules depend on tool limits.
- Overflow: when a subscription session hits its limit it (or a workflow/scheduled task) runs
  `api_run.py --mark-limited`, then `api_run.py --lane continuity --model sonnet --task X --checkpoint X --when-subscription-limited`.
  It runs when the 5-hour session or the weekly limit is at **90 % or more** (`--limit-pct`, env `QF_LIMIT_PCT`; read from
  the same usage Claude Code's /usage shows, via the owner's local login, so 10 % stays in reserve), or when the marker
  (`~/.qf/subscription-limited`, 5 h expiry) is live, and only within the daily cap. `--probe` tests the subscription with a trivial call instead. `--clear-limited` removes the marker. `api_run.py --usage` prints the current percentages.
- `batch.py submit JOBS.json [--dry-run]`, `status ID`, `fetch ID OUT_DIR`: one result file per `custom_id`,
  cost logged under lane `batch` at fetch (usage priced at the batch rate). Shared `system` text is prompt-cached.
  Job format is in the script's docstring. Tests: `py -3.10 -I tools/ops/test_ledger.py`.

**The key** lives only in `C:\Users\a2dsu\.qf\anthropic.key` (PC) or `~/.qf/anthropic.key` (Mac): one line, never in the repo,
logs or errors. The scripts hand it to the child process / SDK client only. **Never set `ANTHROPIC_API_KEY` system-wide**:
the owner's interactive Claude Code sessions would move onto API billing.
