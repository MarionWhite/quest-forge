# Server: current state

Rewrite this file when the state changes; keep it under 2 KB. History: `ops/journal/server.md`.

- **Where:** `C:\qfs\friends`, built only by `tools/server/build_play_server.py --java25 --force` (+ `--opis --rules tools/server/rules.json`; no `--world-border`). Online mode, stopped, no world yet. Agents may not boot it: verify on a byte-identical copy.
- **Decision 0007 applied:** PvP as is, personal quests (party_enable 0), Morpheus sleep vote 43 % (about half rounded down), idle kick 30 min, spawn-protection 16, loaders bundle, honour-system graves, Opis, /tpa (jar built, not installed), no border.
- **Also on it:** MCHeli aircraft definitions (the builder copies assets/mcheli), qf-tweaks with Decocraft lazy models, ChestConfig loot fix, supervisor with crash/hang/daily restart, hourly/daily zip backups, `!jfr`, status.json feed (Gist publisher unconfigured).
- **Docs:** `docs/setup/hosting-a-server.md` (rules mapping, restore checklist, host machine), `docs/setup/server-rules.md` (the post), `docs/design/server-loaders-explainer.md`, `docs/design/hub-proposal.md` (lobby dimension + in-house Trading Post recommended), `docs/design/server-readiness.md` (audit, status table).
- **Owner actions:** op his real account before day one; gist-scoped token for Who's online; firewall rule for TCP 25565; router port forward (`tools/server/host_check.py`); optional `--backup-mirror C:\qf-world\server-backups`.
- **Open:** sheet-2 cards (hub, loaders reverts, RCON over Tailscale); two-person session before inviting friends.
