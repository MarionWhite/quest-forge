# Harness journal (newest first)

- 2026-10-25: API-credit lanes built ($200/month: continuity 90, batch 50, automation 20, reserve 40). tools/ops/ledger.py (ops/api-ledger.jsonl, status/check), api_run.py (headless `claude -p`, dontAsk + allowlist, overflow via --when-subscription-limited), batch.py (Message Batches, cost logged at fetch). Key file ~/.qf/anthropic.key not yet created by the owner, so the live Haiku call is untested; the `claude -p` JSON field names (total_cost_usd, usage) are assumed and fall back to an estimate. Never set ANTHROPIC_API_KEY globally. The claude CLI is not on PATH on the PC; api_run finds the Cursor-extension binary (or CLAUDE_BIN).
- 2026-10-25 22:55: project paused by the owner. Pick-up list at the top of BOARD.md; four checkpoints open (balance-retest, balance-effects-table, server-rules-docs, quests-hunt-credit); census re-test still running on node c4.
- 2026-10-25: ops/ harness, CLAUDE.md, .claude/agents tiers. Render loop rebuilt (renderq: about 30 min per round instead of 4-5 h;
  focus guard 5acf541; idle gate f6c875a; lock-screen fix c6ee679). Night mode test from 22:15.
