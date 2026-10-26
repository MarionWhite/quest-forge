# server: rules applied; docs, explainer, hub proposal (checkpoint 22:35)

Decision: docs/decisions/0007-server-rules.md.

## Done (main)
- tools/server/rules.json + the friends' server rebuilt with `--opis --rules` (ba3ec94). The
  agent's last words: "The rebuild applied all 12 rule lines."
- /tpa + /tpaccept as a lottery-ticket unlockable in qf-commands (df53b43); jar not built/booted?

## Next
1. Verify each rule's effect on disk in C:\qfs\friends (file:line per rule), Opis in mods,
   play-options.json, ops/whitelist/server.properties unchanged, manifest regenerated. Write the
   list to ops/journal/server.md.
2. Boot a byte-identical copy (C:\qfs\scratch-*, other port) to Done; confirm Morpheus, Opis and
   BQ party_enable=0; stop; delete. Never boot C:\qfs\friends itself. One server at a time; check RAM.
3. docs/setup/server-rules.md: drop every [pending], PvP "friendly fire is part of the game", no
   grave-looting line, personal quests, sleep (half rounded down), AFK note.
4. docs/design/server-loaders-explainer.md (per item: what it is, gameplay effect, benefit with
   [measured]/[estimate]/[guess], one-line revert). Owner asked for it.
5. docs/design/hub-proposal.md (lobby = spawn picker home, info boards, protection options, trade
   station survey + recommendation). Proposal only.
6. /tpa: build from a clean worktree, boot on a slim headless trial to see the command register and
   refuse before unlock; record version + SHA-1; do not install.
7. Update ops/BOARD.md server row, ops/tracks/server.md (create, under 2 KB), one journal line.
