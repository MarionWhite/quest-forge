# server: rules applied, verified, three documents written; /tpa jar built (checkpoint 2026-10-25 22:50, project paused)

Decision: docs/decisions/0007-server-rules.md. Detail: ops/journal/server.md (2026-10-25 entries).

## Done (all on main)
1. Rules verified on disk in C:\qfs\friends, file:line per rule in the journal (ba3ec94 rebuild;
   backup `C:\qfs\_backup-friends-2026-10-25-rules\`).
2. Byte-identical copy booted twice on port 25690 (Done 48 s / 54 s; Morpheus and Opis answer;
   `world\betterquesting\QuestDatabase.json party_enable = 0`; exit 0); both copies deleted, no
   scratch server running, `trial.py guard` OK.
3. docs/setup/server-rules.md rewritten to the decisions (6f899de).
4. docs/design/server-loaders-explainer.md (1ff0b3a).
5. docs/design/hub-proposal.md (e938888).
6a. /tpa jar built from a clean detached worktree at df53b43: version `1.1.0+20261025.df53b436`,
   SHA-1 `b459091080a22670c392c3686a66dfec258e94bc`, copy at
   `C:\qfb\builds\QuestForgeCommands-1.0.0-tpa-df53b43.jar`. NOT installed. Worktree removed.

## Remaining (project paused by the owner 2026-10-25)
6b. Slim headless boot of that jar: `py -3.10 -I tools/trial/trial.py build tpa --server qfcommands
   --jar C:\qfb\builds\QuestForgeCommands-1.0.0-tpa-df53b43.jar`, then `launch tpa --wait
   --commands <file with: tpa Dev / stop>`. Expect `[QuestForgeCommands] registered 35 of 35
   commands across 33 tickets` (the live jar says 33 of 33 across 32) and the console refused as
   not a player ("You do not have permission" from CommandHandler; the before-unlock refusal is the
   shared UnlockedCommand path, needs a client to see). Record in the journal. Do not install.
7. ops/BOARD.md server row (rules verified; docs done; /tpa jar built, slim boot pending),
   ops/tracks/server.md (create, under 2 KB), one journal line. Commit.
8. Sheet 2 cards from the hub proposal §5 and the explainer (one revert card per item):
   `ops/DECISIONS.md` already lists the loaders bundle; add hub-where, hub-access, hub-respawn,
   hub-boards, hub-trade.
