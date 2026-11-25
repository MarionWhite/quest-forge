# Server journal (newest first)

- 2026-10-25 22:50: paused by the owner. Second boot of a byte-identical copy confirmed `worldetterquesting\QuestDatabase.json party_enable = 0` (Done 54 s, exit 0, deleted). Docs committed: rules post 6f899de, loaders explainer 1ff0b3a, hub proposal e938888. /tpa jar from a clean worktree at df53b43: `1.1.0+20261025.df53b436`, SHA-1 b459091080a22670c392c3686a66dfec258e94bc, kept at `C:\qfbuilds\QuestForgeCommands-1.0.0-tpa-df53b43.jar`, not installed, slim boot not run. Guard OK.

## 2026-10-25 — decision 0007 verified on disk and by boot (task server-rules-docs)

Rebuild: `build_play_server.py --java25 --instance %APPDATA%\.crazycraft4 --out C:\qfs\friends --force --opis --rules tools/server/rules.json` (ba3ec94; output in `C:\qfs\_backup-friends-2026-10-25-rules\rebuild-output.txt`, kept files + `mods-sha1.txt` backed up there first). The builder gained `srv-pvp: "as-is"` and `srv-loaders.op_loaders_offline` (the bundle's "op loaders stop when offline" had no key).

Rule → file:line in `C:\qfs\friends`:
- srv-pvp as-is → nothing written: `config/GraviGun.cfg:104 I:grabablePlayers=1` (the pack's value), `server.properties:24 pvp=true`, `supervisor.json "team": ""`.
- srv-quests personal → `config/betterquesting/DefaultQuests.json:28875 "party_enable:1": 0`.
- srv-sleep 43 → `mods/Morpheus-1.7.10-1.6.21.jar` (sha256 37014340…), `config/Morpheus.cfg:5 I:SleeperPerc=43`. Morpheus skips when floor(100·sleepers/counted) ≥ 43 (read from the jar's WorldSleepState): exact floor(n/2) for n = 2, 4, 6, 8–15; one more for 3, 5, 7. No single percentage does better.
- srv-afk 30 → `server.properties:23 player-idle-timeout=30`.
- srv-hub 16 → `server.properties:32 spawn-protection=16`.
- srv-loaders world_anchors off → `config/railcraft/railcraft.cfg:7 B:craftable=false` (passive :24, personal :38 stay true); no Railcraft block in `forgeChunkLoading.cfg`.
- srv-loaders sync_shells false → `config/Sync.cfg:34 I:allowChunkLoading=0`.
- srv-loaders op_loaders_offline false → `config/ChickenChunks.cfg:18 OP=false` (allowoffline; DEFAULT=false at :17).
- srv-graves → nothing on the server (rules post only).
- srv-tools chest_transporter_spawners false → `config/ChestTransporter.cfg:5 B:pickupSpawners=false`.
- srv-tools projecte_time_watch_pedestal 0 → `config/ProjectE/ProjectE.cfg:26 I:timePedBonus=0`.
- srv-tools lycanites_first_event_day 3 → `config/LycanitesMobs/lycanitesmobs-mobevents.cfg:357 I:"Random Mob Events Day Minimum Overworld (0)"=3`.
- Opis → `mods/Opis-1.2.5_1.7.10.jar` (sha256 76905f92…), `play-options.json "opis": true`. No `config/WorldBorder`, no border jar (mods: 112 files).
- `play-options.json` holds the rules and `rules_file = C:\dev\quest-forge\tools\server\rules.json`, so later rebuilds keep applying them.
- `ops.json`, `whitelist.json` byte-identical to the backup; `server.properties` differs only at :23 and :32 (the two rule lines).
- `MANIFEST.sha256` regenerated 21:14, 2182 files (2178 before: + the two addon jars, Morpheus.cfg, …); `BUILT-FROM.txt` lists the 12 applied lines.

Boot of a byte-identical copy (`C:\qfs\scratch-rules-20261025`, port 25690 the only edit, `-Xmx5G`; MANIFEST check 2182/2182 identical before the edit): `Done (11.755s)!` after 48 s wall; `[Morpheus]: Loading configuration`; `opis_help` answered with its 13 commands; `forge tps` overall 0.000 ms, Dim 0 0.365 ms; FML 148 mods; `[QuestForgeCommands] registered 33 of 33 commands across 32 tickets` (the live jar, not the /tpa build); BetterQuesting loaded 312 quests; `stop` → exit 0; copy deleted. The world's own BQ settings file is checked by a second boot (see below).

- 2026-10-25: decision 0007 applied (ba3ec94), /tpa (df53b43); earlier: Opis/border/rules/mirror (ab8a8c7), !jfr (1368096), Who's online feed + host check (586eb35, bafdea1, 078b205), MCHeli assets (a4054c3), two rebuilds. Docs and hub proposal checkpointed.
