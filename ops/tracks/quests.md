# Quests: current state

Rewrite this file when the state changes; keep it under 2 KB. History: `ops/journal/quests.md`.

- **Books:** `pack/config/betterquesting/DefaultQuests.json` (shipped) and the server copy; `tools/quests/qb.py check` after every edit (`obtain` warns on nine unobtainable asks; `--strict` makes them errors).
- **Decisions:** 0004 (no parties; voice rejected, samples lead; damage-based boss credit with the killer highlighted). Act I structure as planned: one tab per act, /home ticket, jukebox reward + recipe, 17-quest Prologue, Act I from iron.
- **Drafts, not applied:** `tools/quests/drafts/DefaultQuests.wp5.json` (Prologue) and `.wp6.json` (four-act spine, 328 quests, 19 lines; `patches/wp6_acts.py --decisions docs/decisions/answers/s001.json`, `--no-parties` always on). Moved quests keep shipped text; new quests, Pack Master and act tabs are `[WRITE:]` placeholders. Tally: Act III 78/72 diamonds over (pre-existing).
- **Writers (Mac):** `docs/design/quests/wp6-writing-brief.md`: first three or four voice samples on quests 1, 473, 481 for the next Decisions sheet; then the placeholders. No party language; hunts credit everyone who damaged the boss (code in progress).
- **Code:** jukebox recipe (shapeless jukebox + blank record) in qf-content, jar 1.1.0+20261025.20eef315 not installed; hunt credit: `ops/checkpoints/quests-hunt-credit.md`.
- **Reference:** `docs/reference/dead-items.md` (what players cannot get; nine quests flagged), `docs/design/quests/act-structure.md`, `questline-audit.md`.
