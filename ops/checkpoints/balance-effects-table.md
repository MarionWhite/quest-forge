# balance: enchant effects table, rarity plan, fight-duration study (checkpoint 22:35)

Decision: docs/decisions/0005-enchant-census-proposals.md (the owner's P10 note is the spec).

## Done
- `tools/balance/effects_table.py` written, untracked, never run to completion (the agent stopped
  while validating it against the census doc's figures).

## Next
1. Run it into the scratchpad, check a few rows against enchantment-combat-results.md (trusted
   means, TTKs), fix, then write docs/reference/enchant-effects.md + .json; commit script + docs.
   Make it rerunnable so the re-test results (ops/checkpoints/balance-retest.md) slot in.
2. docs/design/enchant-rarity-plan.md: distribution today vs target, mispriced ones, no-effect ones
   and what they could become, 8–15 new-enchant ideas. No drop rates or sources.
3. docs/design/fight-duration-study.md: our TTKs by tier; what RLCraft, Prominence II, DawnCraft,
   Better MC, GTNH-style packs and good boss mods aim for ([V]/[U] with URLs); a target band per
   tier; Bastion-like summon enchants elsewhere. Proposals only.
4. Each doc gets a line in ops/DECISIONS.md if it needs the owner. Checkpoint after each doc.

## Rules
No game launches; web via WebSearch/WebFetch; stage only own files; five-line report; journal
ops/journal/balance.md.
