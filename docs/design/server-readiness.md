# Server readiness: what the friends' server is still missing

An audit of what stands between the pack and a server that 5-15 friends can play
on for months. Written 2026-10-16 from the repo, `C:\qfs\friends`, the live
instance and the git log. Nothing was launched to write it, so every performance
figure here is either quoted from
[`../setup/hosting-a-server.md`](../setup/hosting-a-server.md) or marked
**unmeasured**.

The gaps are in order of how badly each one would hurt this group. The top three
must be settled **before the world is created**: once friends have played, the
cost of changing them is lost inventories or a reset.

| # | Gap | Fix before day one? | Effort |
|---|---|---|---|
| 1 | ~~Nothing backs up the world, restarts after a crash, or detects a hang~~ **Done 2026-10-17:** `tools/server/supervisor.py` and the builder guards. **Restore drill, off-machine mirror, restart/hang/crash tests done 2026-10-25** | yes | done |
| 2 | A friend can join with a stale client and play with the wrong IDs. **Versions and the login check done 2026-10-17**; a new release is still needed | yes | a new release |
| 3 | Identity and mod set are not yet frozen (`online-mode=false` right now) | yes | decisions plus a builder change |
| 4 | Load at 15 players is unmeasured; ~~chunk loaders are only partly capped; no profiler; no border~~ **Prepared 2026-10-25:** `--world-border`, `--opis`, loader caps behind `--rules` (the owner's call); load still unmeasured, and Opis's console tables came back empty (4d) | partly | one flag each |
| 5 | No block logging or rollback; no remote admin; Log4Shell mitigation does not apply to this log4j | yes, for log4j | config; FE is optional |
| 6 | Social rules nobody has decided: PvP, graves, quests, sleep, AFK, a hub. **Prepared 2026-10-25:** every choice is one line in a `--rules` JSON (`tools/server/rules.example.json`), rules post drafted (`../setup/server-rules.md`); the decisions themselves are the owner's | yes | one rebuild once decided |
| 7 | Multiplayer paths no test has covered (two-person paths) | before inviting | one session, two people |
| 8 | Content worth adding: selective, cheap. **Opis, WorldBorder-Forge and Morpheus are builder options since 2026-10-25** (server-only, verified); `/tpa` and the hub remain | must land before day one | small |

What the recent commits already fixed is listed in an appendix at the end, so
nobody redoes it.

---

## 1. Data safety: no backups, no restart, no hang detection

**Done 2026-10-17.** Everything under "The supervisor, specifically" and "Changes
to `build_play_server.py`" below is built. It was tested on a throwaway full-pack
server: `tools/server/supervisor.py`, installed by the builder with
`start-supervised.bat`, and how to use it is in
[`../setup/hosting-a-server.md`](../setup/hosting-a-server.md#running-the-server).
Where it differs from the plan:

- It takes a plain zip copy into `backups/hourly` and `backups/daily` (24 and 7
  kept), not restic. There is no weekly tier. ~~Nothing copies backups off the
  machine; that stays a manual step for the host.~~ **Done 2026-10-25:**
  `--backup-mirror DIR` copies every daily into a second folder (a Syncthing
  folder reaches the owner's Mac); see the hosting guide, "Off-machine copies".
- The builder checks for a running server through `supervisor.pid`, the port,
  Java command lines, and rename probes on the session lock, the open log and
  the folder. In 1.7.10 `session.lock` is written once and not held, so it
  is not enough on its own.
- The jar and config manifest is `MANIFEST.sha256`, next to `BUILT-FROM.txt`,
  and every backup carries a copy.
- ~~Still open: the **restore drill** with a real login~~ **Done 2026-10-25**
  on a scratch server (backup, change a gamerule, stop, restore, boot, read it
  back). The guide's one-line restore also overwrote `server.properties`,
  `MANIFEST.sha256` and the player lists and checked no jars, so the drill is
  now `tools/server/restore_backup.py` and a six-step checklist in the hosting
  guide. The same day: crash restart (Java killed; back in 40 s), hang
  detection (`tools/server/simulate_hang.py` froze the server thread; dump,
  kill, back in 2.5 min plus boot), the daily restart cycle, `stop.flag`, and a
  webhook failing safely were all exercised on the scratch server. Still open:
  the host-machine settings (Windows Update, sleep), the census `PAUSE` file,
  and a restore with a real login (the drill read a gamerule back from the
  console, not a player's chest).
  `removeErroring*` stays on; the supervisor now alerts when Forge removes
  something.

The rest of this section is the audit as written.

**Status at the audit (2026-10-16).**

- **No backups.** Nothing in the repo, in `C:\qfs\friends` or in its
  `start.bat` copies the world anywhere. The hosting guide says "Back the world up
  daily" but supplies nothing to do it. `C:\qfs\friends` has no `world/` yet
  (directory listing, 2026-10-16), so nothing has been lost so far.
- **No restart after a crash.** `start.bat` runs Java once and then `pause`s. Two
  Legends crashes are accepted as unfixable (`EntityLightningTrail`,
  `EntityLightning`), so a crash will happen sooner or later. Each one leaves the
  server down until the host notices.
- **No hang detection.** 1.7.10 has no tick watchdog (`max-tick-time` arrived in
  1.8), and the hosting guide notes that a hung tick hangs forever.
- **No scheduled restart.** The GC log shows about 2.6 GB live heap idle, but
  nobody has measured how it grows over a multi-day session with players.
- **Unsafe shutdown paths.** Only typing `stop` saves reliably. Closing the
  console window gives the JVM a few seconds before Windows kills it, which is not
  enough to save a world with about 30 dimensions. If the server runs on the
  user's PC, a Windows Update reboot or sleep has the same effect.
- **Silent deletion is switched on.** `config/forge.cfg` sets
  `removeErroringEntities=true` and `removeErroringTileEntities=true`. That keeps
  the server up when one entity throws, but it deletes the entity or machine (a
  player's Transformers vehicle, a Witchery altar) with only a log line. The only
  way back is a backup taken before it happened.
- **The rebuild script destroys evidence and can corrupt a live world.**
  `build_play_server.py --force` keeps only `world/`, `ops.json`,
  `whitelist.json` and the two ban lists. It then runs `shutil.rmtree` on the
  rest, which takes `logs/`, `crash-reports/`, `usercache.json` and
  `server.properties` with it. Nothing checks that the server is stopped first.
  Run during play, it moves `world/` out from under a running JVM and then fails
  partway on locked jars.
- **A restore cannot recreate the jar set.** `BUILT-FROM.txt` records how many
  mods were kept and which were dropped, but no names or hashes for the kept
  ones. The world is only valid with exactly those jars: Transformers assigns
  crafting-material IDs at first load, and removing a mod deletes its items.

**Why it matters here.** Friends lose interest in a modpack server for two
reasons: it is down when they want to play, or a week of work disappears. Both are
likely in this pack. It has accepted crash bugs, griefing switched on by choice,
dupe-prone mods that nobody has verified (ProjectE, Archimedes, Chest
Transporter, Sync; see section 7), and silent entity deletion.

**Options.**

| Option | What it gives | Cost |
|---|---|---|
| **A supervisor script** (proposed `tools/server/run_play_server.py`, Python, owns the server's stdin) | restart loop, hang detection, scheduled restart, backups, alerts | No in-JVM cost. A backup's `save-all` stalls the tick while every dimension is written (**unmeasured**; probably 1-5 s); the copy itself runs off-thread. |
| A `start.bat` `goto` loop | crash restart only | none, but no hang detection and no backups |
| ForgeEssentials 1.4.6 Backup module | in-game `/backup` and an automatic interval | a large server mod (16 MB) for one feature; see section 5 |
| FTB Utilities 1.7.10 (1.0.18.x) | backups, claims, homes | needs FTBLib on **clients** as well; adds blocks and GUI. Too heavy for backups alone. |
| A Windows Task Scheduler job plus robocopy | backups only | unsafe without `save-off` (the copy would be torn), and the task cannot send console commands |

The supervisor, specifically:

- **Console.** Start Java as a child process with a stdin pipe. Commands typed
  at the console are queued and run on the main thread, which is safe; RCON
  commands in 1.7.10 run on the RCON thread (see section 5). Send commands as
  plain bytes: PowerShell adds a BOM and the server answers "Unknown command".
- **Hang detection.** Every 60 s, send `list` and wait for `There are N/15
  players online`. No answer within 90 s (skipped while a backup runs) means the
  main thread is stuck. Take `jstack <pid>` into `logs/` (it needs a JDK 8; the
  server runs on a JRE), then kill and restart. The `list` answer also gives the
  player count, which later steps use.
- **Crash restart.** Restart on any exit that was not requested. If it crashes
  three times in 15 minutes, stop and alert: a crash loop on a bad chunk needs a
  person.
- **Scheduled restart.** Every day at a fixed hour (05:00), and only when
  nobody is online or after 10/5/1-minute `say` warnings: `save-all`, then
  `stop`, wait for the exit, start again.
- **Backups.** Hourly while anyone has been online in the past hour, plus one
  before every scheduled restart:
  1. `save-off`, then `save-all`.
  2. Wait for `Saved the world`, then until region-file mtimes have not changed
     for 10 s. In 1.7.10 chunk writes drain on a background IO thread after the
     message.
  3. Copy `world/`.
  4. `save-on`, in a `finally`.
- **Backup storage.** Use restic (deduplicating, encrypted, one Windows binary)
  or robocopy into dated folders. Keep 24 hourly, 14 daily and 8 weekly copies.
  Each backup also takes `server.properties`, the player lists and a sha256
  manifest of `mods/` and `config/`. Copy the daily one off the machine (an
  external disk, or the user's OneDrive), never the live world folder.
- **Alerts.** Post to a Discord webhook on crash, hang or restart, on any
  `Removing` / `has been removed` line from Forge's errored-entity handling, and,
  optionally, on joins. The webhook is an HTTP POST from Python, with no mod
  needed.
- **Stopping.** A `stop.flag` file (or Ctrl-C to the supervisor) sends `stop`
  and waits for the exit. The server window is never closed by hand.

**Changes to `build_play_server.py` that go with it:**

- refuse to run while `world/session.lock` is held, or while a `java.exe`
  command line names the server directory;
- carry `logs/`, `crash-reports/`, `usercache.json` and `server.properties`
  across `--force` (see 3);
- write a full sha256 jar and config manifest into `BUILT-FROM.txt`.

**Host machine, if it is the user's PC.**

- Set Windows Update active hours, or pause updates during the season, and turn
  off sleep.
- RAM is 31 GB. The server takes 10 GB at start (`-Xms10G`) and the user's own
  client takes 8 GB. `trial.py`'s 22 GB budget counts every `java.exe`, so it
  still holds. Even so, during play sessions create the `PAUSE` file that
  `run_campaign.py` honours (commit 605b9a2): the census nodes compete for the
  same boost clocks the server tick needs.

**Restore drill.** Do one before inviting anyone: restore last night's backup
into a scratch directory, boot it on a spare port, and log in. A backup nobody
has restored is a hope.

**Recommendation.** Build the supervisor and the builder changes before day one.
Nothing else in this document is worth as much.

---

## 2. Version mismatch: a stale client joins and plays with the wrong IDs

**Done 2026-10-17: options 2 and 3.** A stale client is now refused at login
with a message that says what to do. How it works and how to override it is in
[`../setup/hosting-a-server.md`](../setup/hosting-a-server.md#the-pack-check);
players get [`../setup/why-was-i-refused.md`](../setup/why-was-i-refused.md).

- ~~Give the in-house mods real versions.~~ qf-content, qf-commands and
  qf-tweaks are `1.1.0+<date>.<sha8>` of the last commit that touched each
  mod's folder. qf-tweaks gained a mod container (`qftweaks`) to carry its
  version. The jar file names are unchanged. FML refuses a client with a
  different qf-content.
- ~~Add a login config check.~~ qf-content's pack check hashes the ID entries
  of 22 configs (the list was built by scanning `pack/config`; `--scan` keeps it
  complete). It also compares the versions of every mod both sides have. The
  fingerprint ignores line endings, layout and client-only sections. `/qfpack`
  and `tools/pack_fingerprint.py` print it, and the main menu and F3 screen show
  it with the pack date.
- Still open: **option 1** (cut a new client release, which also brings the
  check to clients), **4** (`verify_pack.py` could call
  `pack_fingerprint.py --diff`), **5** (the Windows player guide), and the
  builder recording the fingerprint (`build_play_server.py` copies `config/`
  verbatim, so the server's fingerprint is the instance's).

**Status at the audit (2026-10-16).**

- **The only published client is out of date.** It is release
  `client-instance-2026-09-09` (`questforge-client-instance.tar`, 1.14 GB, on
  github.com/MarionWhite/quest-forge). Every server fix since then is newer:
  - Witchery potions moved to 150-193, OreSpawn biomes to 230-234, and the
    Jungle death setting changed (699e27e, 2026-10);
  - qf-tweaks gained `GraveBaublesTransformer`; Morph ships enabled;
  - qf-content gained `PacketClickIntent` (f1d5343) and `PacketDiscTier`
    (still uncommitted);
  - Transformers was hardened (8630df8).
- **FML will not catch a stale client.** Every in-house jar reports version
  `1.0.0` (`mcmod.info` expands `${modVersion}`; the jar names are
  `QuestForgeContent-1.0.0.jar` and `QuestForgeCommands-1.0.0.jar`). The
  handshake compares mod IDs and versions, so a September client passes. Config
  IDs are never compared. The hosting guide already says the result: the client
  "gets in, then plays with the wrong enchantments, potions or biomes".
- **The install path is a dead end.** `hosting-a-server.md` sends friends to
  "the client-instance release (see `pack/README.md`)", but `pack/README.md`
  never mentions a release. The repo alone cannot produce a runnable client:
  jars are gitignored, and the splash classes live only in the hand-patched Forge
  jar.
- **There is no Windows player guide.** `install-on-mac.md` is a migration
  guide for one Mac. Friends on Windows have nothing.
- **Online mode rules out the host's own launcher.** `TEST-LAUNCH.bat` is
  offline ("Offline credentials: singleplayer works; online servers do not").
  Every player, the host included, needs a launcher that signs in, such as Prism.
- **The manifest is incomplete.** `pack/mods.tsv` is missing
  `Morph-Beta-0.9.3.jar`, `QuestForgeCommands-1.0.0.jar` and
  `PortalGunSounds.pak` compared with the live instance.
- **The installed-pack check does not cover configs.** `tools/verify_pack.py`
  checks jars, the Forge jar, resources and the splash. It checks no
  ID-bearing config.

**Why it matters here.** It is the most likely first-week failure. Someone
installs from the link they were given in September, joins, and every TragicMC
potion they drink is a Witchery one. Nobody notices for days.

**Options.**

1. **Cut a new client release.** Name it `client-instance-<date>` and have the
   server record its name. Run `verify_pack.py` on it before uploading.
2. **Give the in-house mods real versions.** `1.0.<build>`, or the release date,
   so FML refuses a stale jar at the handshake with a readable message. Cost:
   none.
3. **Add a login config check (qf-content, about 100 lines).** On
   `PlayerLoggedInEvent` the server sends a hash of its ID-bearing config files:
   `witchery.cfg`, `OreSpawn.cfg`, `TragicMC.cfg`, `qfcontent.cfg`,
   `thejungleMod.cfg`, the biome and potion sections, and the release name. The
   client compares them with its own and disconnects itself with "Your pack is
   out of date; install release X". Cost: one packet per login. It also catches
   a friend who edited a config.
4. **Extend `verify_pack.py`.** Diff the instance's ID-bearing configs against
   `pack/config` (CRLF-insensitive; 12 files differ in real content today,
   mostly runtime rewrites such as InfernalMobs' new mob keys), and check
   `mods.tsv` completeness.
5. **Write a one-page player guide** (`docs/setup/joining-the-server.md`):
   - install Prism and sign in with a Microsoft account;
   - import the release tar and give the instance memory, linking
     `jvm-args.md`;
   - pick a preset from `performance-tuning.md` ("low" on weak PCs);
   - add the server address, and expect the first launch to take 3-4 minutes;
   - when the game quits without a crash report, send `logs/latest.log`, not a
     screenshot. Psychedelicraft's render hook catches exceptions and closes the
     game cleanly (8630df8), so a client crash often leaves no report.
   - never use VoidLauncher or CurseForge to "repair" the instance.

**Recommendation.** Do 1, 2 and 5 before inviting anyone. Do 3 before the first
mid-season config change, since that is when drift starts.

---

## 3. Freeze identity and the mod set before the world exists

**Status today.**

- **The server is in offline mode right now.** `C:\qfs\friends\server.properties`
  says `online-mode=false`, and its only whitelist and op entry is `Dev` with an
  offline UUID (`380df991-...`), left over from the scripted join test. The
  builder's default is `true`.
- **Everything a player owns is keyed by UUID:** the player `.dat`
  (inventory, Baubles), BetterQuesting progress and parties, ProjectE knowledge,
  the qf-commands unlocks and homes (stored in the player's persisted NBT,
  `Unlocks.java`), ChickenChunks loader ownership, Lycanites pet owners and
  EnderStorage personal locks. Offline and online UUIDs for the same name differ.
  A switch after day one orphans all of it, and each item needs a hand
  migration.
- **Console changes do not survive a rebuild.** `server.properties` is not in
  the builder's keep list. `/setidletimeout`, a changed MOTD, a different view
  distance or RCON settings all vanish on the next `--force`.
- **The mod set must be final at world creation.** The hosting guide says so:
  removing a mod mid-world deleted 63,000 item entities once, and Transformers
  IDs are fixed per world. Every addition this document recommends therefore
  has to land before day one, or be confined to mods that add no blocks or items.

**Recommendation.**

- Rebuild with `--online-mode true` before the world is created, and add the
  friends with `whitelist add`.
- Move every property the builder writes, plus `player-idle-timeout`,
  `op-permission-level` and the RCON keys, into builder arguments, so the
  template is the record of what the server runs with.
- Pick a "day one" and freeze the jar list then. Mods added after it must be
  server-only and content-free (a profiler, a border).

---

## 4. Performance at 5-15 players

**What is measured.** The figures below are from `hosting-a-server.md`, with no
players connected:

- idle tick 0.9 ms, or 1.5 ms after pregeneration, against a 50 ms budget;
- pregeneration at 185 chunks/s;
- GC p99 29 ms;
- boot in 49 s.

Fifteen players have not been measured. Neither has one player. Everything below
is an estimate of where the 48 ms of headroom will go.

### 4a. The play world is not pregenerated

There is no `world/` in `C:\qfs\friends`. The guide's plan is sound: overworld
radius 188 chunks (3,000 blocks), about 13 minutes on the 7900X. Two gaps remain.

- **Pregenerate only the overworld, and players leave it on day one.** Live
  generation in Twilight Forest (hollow hills, Twilight structures), the Nether
  and Witchery's dimensions hits everyone the first time a group goes there.
  Pregenerate the dimensions the questbook sends people to: the Nether at about
  64 chunks, Twilight Forest (dim 7) at about 94 chunks. Their generation speed
  is **unmeasured**.
- **"There is no world border in 1.7.10" is true only of vanilla.**
  [WorldBorder-Forge](https://github.com/RoyCurtis/WorldBorder-Forge) is a
  server-only port of the Bukkit WorldBorder plugin for Forge 1.7.10. It sets
  per-dimension radius borders, can fill (pregenerate) and trim, and checks
  player positions on a timer, so its runtime cost is negligible. The README
  says it is buggier than the original, so set it up on a scratch copy first. A
  border at the pregenerated radius turns "please don't explore past 3,000" into
  a wall. **Done 2026-10-25:** `build_play_server.py --world-border 3000`
  installs WorldBorder-Forge 1.0.2 (pinned, sha256) and writes its
  `borders.cfg`; it booted with the full pack on Java 25, `wb list` showed the
  border and it survived restarts and a restore. Off by default: the radius is
  the owner's (it should equal the pregenerated radius).

### 4b. Mob load scales with how spread out players are

- **JAS mobs.** JAS counts chunks around every player, like vanilla. The guide
  works out 46 monsters per player at distance 6. Players who spread out each get
  their own cap: 15 players apart is about 690 hostile mobs plus animals. Players
  who stay together share one. At a guessed 0.03-0.08 ms per modded mob AI tick
  (**unmeasured**; Lycanites, OreSpawn and TragicMC AI is far heavier than
  vanilla), 690 mobs is 20-55 ms. That is enough on its own to put a spread-out
  evening over budget.
- **Lycanites' special spawners bypass JAS.** Fire, lava, storm, sky, lunar,
  portal, underground, water and so on are enabled in
  `lycanitesmobs-spawning.cfg`, ticking every 400-1,200 ticks within 32-48
  blocks of each player. They add to the JAS cap, and cost scales linearly with
  players.
- **Lycanites mob events.** Random events are on in every listed dimension, one
  every 72,000-144,000 ticks (1-2 hours of server uptime), many from day 0. Every
  event has `forced no despawning=true`, so event mobs accumulate wherever they
  are left. That includes chunk-loaded bases.
- **Recommendation.** Keep the design, but measure it: Opis (4d) with 5 players
  spread out in the first session.
  - If entity ticking dominates, lower JAS caps 20-30% before cutting view
    distance.
  - Set `Random Mob Events Day Minimum Overworld (0)` to 2-3, so the first
    session is not an event.
  - Consider `event forced no despawning=false` if Opis shows event mobs piling
    up in bases.

### 4c. Chunk loaders: capped in one mod, open in three others

The ChickenChunks cap (49 per player, off when the owner is offline) is the only
loader limit set.

| Loader | Setting today | Effect |
|---|---|---|
| ChickenChunks | `DEFAULT=49`, `allowoffline DEFAULT=false`, but `OP=500`, `allowoffline OP=true` | Fine for players. The host's own loaders (Dev is op) run 500 chunks while he is offline. |
| **Railcraft World Anchor** | `railcraft/railcraft.cfg`: `craftable=true`, no fuel key; module `chunk.loading=true` | A 3x3 always-on loader, with no fuel, whether the owner is online or not. Only Forge's per-mod default limits it: 200 tickets × 25 chunks per world (`forgeChunkLoading.cfg`). Personal anchors burn ender pearls and (per Railcraft) work only while the owner is online. |
| **Sync shells** | `Sync.cfg`: `allowChunkLoading=1`, with Sync's own comment "Added by request ... Untested, unsupported." | Every shell storage keeps its chunk loaded. |
| CompactMachines | `chunkLoadingMode=2` | Already fixed. |
| TARDIS | `Dimension always loaded=false` | Already fixed. |

**Recommendation.**

- Set Railcraft `anchors.craftable=false` (world anchors) and keep personal and
  passive ones. Or, more gently, give Railcraft its own category in
  `forgeChunkLoading.cfg`: `Railcraft { I:maximumTicketCount=20
  I:maximumChunksPerTicket=9 }`, which allows 20 anchors per world.
- Set Sync `allowChunkLoading=0`.
- Decide whether the host's op loaders should really run while he is offline.

**Prepared 2026-10-25 (`srv-loaders` in `--rules`):** `world_anchors`
`"off"` / `"capped"` / `"on"` and `sync_shells` apply the two changes above to
the server's config copies; nothing is applied until the owner's answer is in
the rules file. Correction to the table: the live `railcraft.cfg` has
`world.fuel=minecraft:ender_pearl=12`, so World Anchors do burn ender pearls
(12 hours each); "no fuel key" was wrong.

### 4d. No profiler

Only `forge tps` (per-dimension mean tick time) is available. When the server
lags, nobody will be able to say which machine or mob caused it.

| Tool | 1.7.10 status | Cost |
|---|---|---|
| `forge tps` | built in | none |
| **Opis** (ProfMobius) | 1.7.10 builds exist and need **MobiusCore**, which the pack already ships (`MobiusCore.jar`, 1.2.5) | Collects only during a `/opis start` ... `/opis stop` window; idle overhead is meant to be negligible (**unmeasured**). The GUI needs Opis on clients, but its chat summaries work from the server alone. Check whether it declares itself acceptable server-only; if not, ship it in the client release (it is small). |
| TickProfiler (nallar) | 1.7 builds are reported but not confirmed here | per-profiling window only |
| jstack, jcmd, VisualVM | need a JDK 8 on the host (the server runs a JRE) | jstack costs a pause of a few ms; VisualVM sampling costs a few % while attached |
| GC log | already on, rotated at 5 × 20 MB | none measurable (per the builder) |

**Recommendation.** Add Opis before day one (it adds no blocks, so it could even
come later), and put the jstack-on-hang step into the supervisor. Profile once in
the first real session with 5 players spread out. That turns this whole section
from estimates into numbers.

**Done 2026-10-25, with a catch.** `--opis` installs Opis 1.2.5 (pinned; it
depends on exactly MobiusCore 1.2.5, which the pack ships, and its `@Mod` says
`acceptableRemoteVersions="*"`, which FML 1614's `IgnoredChecker` accepts, so
no client needs it). It boots clean and `opis_nent` counts entities. But
`opis_ent` and `opis_te` returned empty tables on the Java 25 scratch server
even with 40 summoned creepers ticking for 600 ticks: the server-side entity
profiler recorded nothing, and the console commands call themselves deprecated
in favour of the `/opis` GUI (Opis on the client). The same test on a Java 8
scratch build recorded 20 entities and 20 tile entities, so Opis works there
but not under lwjgl3ify, and even there the console prints the rows as
`DataEntity@...` objects: only the GUI can read them. In its place the
supervisor gained `!jfr [seconds]`, a JDK Flight Recorder profile of the Java
25 server (tested), which names the hot mod code rather than the hot entity.
jstack-on-hang was already in the supervisor; it was exercised today (section
1), and `jcmd` is a fallback. The "profile the first real session" steps are
in the hosting guide.

### 4e. Specific hazards in this mod list

- **Chest Transporter can move mob spawners.** Every tier can
  (`spawnerWithWood=true` and up). Doomlike, Roguelike and Chocolate Quest
  dungeons are full of spawners. One player can build a 10-spawner mob tower in
  a chunk-loaded base, and that is the classic modded-server TPS sink. Set wood
  and iron to `false`, or all of them.
- **ProjectE Watch of Flowing Time.** `enableTimeWatch=true` with
  `timePedBonus=18`. In a DM Pedestal it gives every tile entity in range extra
  ticks permanently, so its cost is a multiple of whatever machines are nearby.
  Lower the bonus or disable the pedestal use.
- **Archimedes ships.** `max_chunk_blocks=2048`. A compiled ship is one entity
  carrying up to 2,048 blocks and their tile entities, synced every
  `sync_rate=20` ticks. Ships parked as entities are also where community
  reports of lost ships come from. Tell players to decompile ships when parking:
  blocks in the world are safer than an entity. Consider lowering the cap to
  1,024.
- **MCHeli.** `Explosion_DestroyBlock=true` and `Collision_DestroyBlock=true`
  are griefing, which is accepted. Bullets and rockets are entities, so a
  dogfight spikes entity count briefly; that is fine. No config limits vehicles
  per player.
- **TARDIS.** Each TARDIS is its own dimension. With `always loaded=false`, each
  one loads and unloads as players enter and leave. That churns the disk but is
  otherwise cheap.
- **RecurrentComplex** (`structureSpawnChance=1.0`, all dimensions) is a
  generation cost only, so pregeneration absorbs it.
- **The overworld spawn chunks are always loaded** (vanilla). A shared base built
  there ticks 24/7, even with nobody online. That is fine for a hub of
  decoration; avoid putting machines or farms there.

### 4f. Bandwidth, if the server is at home

**Unmeasured; arithmetic only.**

- **Voice** is 12 KB/s per speaker per listener in range (`voice-chat.md`).
  Ten players in one base with three talking is 3 × 9 × 12 KB/s ≈ 2.6 Mbit/s of
  upload.
- **Chunks.** A join or teleport sends about 169 chunks per player. A group
  teleport is a burst of several MB per person.

A 10-20 Mbit/s home uplink holds this, but voice in a crowd is the largest steady
flow. If friends report voice breakup in big groups, look at the host's upload
before blaming the codec.

---

## 5. Admin tooling, block logging, remote management, Log4Shell

**Status today.**

- **Permissions** are vanilla op levels only. `ops.json` holds one offline-mode
  `Dev`. CustomNPCs editing is op-only (699e27e).
- **Block-change logging and rollback: none.** Griefing is left on by choice
  (ICBM antimatter breaks bedrock, OreSpawn bosses, Lucky Blocks, Pandora's Box,
  qf-content's Excavate, Timber and Tunneler). The only rollback is a whole-world
  backup, which takes everyone's work back with the grief.
- **Remote management: none.** `enable-rcon` is not set. Any change means
  sitting at the host machine.
- **Log4Shell: the mitigation in `start.bat` does nothing for this log4j.** The
  server's log4j is 2.0-beta9: `JndiLookup.class`, dated 2013, sits inside
  `minecraft_server.1.7.10.jar`. `-Dlog4j2.formatMsgNoLookups=true` is honoured
  only from log4j 2.10 on. For 1.7-1.11.2, Mojang's published fix is a log4j
  config file (the client already has `log4j2_17-111.xml`). The other standard
  fix is deleting `org/apache/logging/log4j/core/lookup/JndiLookup.class` from
  the server jar. With `online-mode=true` and a whitelist, only whitelisted
  players can put text in the log, so the exposure is small, but the fix is one
  line in the builder.

**Options.**

| Option | Gives | Cost and risk |
|---|---|---|
| **Delete `JndiLookup.class` in the builder** | closes Log4Shell | none; leaves Forge's own `log4j2.xml` logging unchanged |
| **RCON, bound to a private network** (Tailscale or ZeroTier between the host and the admins) | remote console from a phone or laptop | Free, but the RCON password is plaintext, so never port-forward it. In 1.7.10, RCON commands execute on the RCON thread, not the main thread. Use it for `list`, `say`, `whitelist`, `kick`, `ban`, and never for `save-*` or `stop`, which belong to the supervisor's stdin. |
| **ForgeEssentials 1.4.6.1373** (`forgeessentials-1.7.10-1.4.6.1373-server.jar`, 16 MB, Jan 2023; client mod optional) | permissions and groups, protected zones, a PlayerLogger module that records player block and container actions (rollback is advertised; confirm in a trial), backups, `/spawn`, warps, mail | A coremod-style server mod. Protection checks run on every block event (microseconds each), and PlayerLogger writes every block event to a database, so disk use grows. It is large and old in a pack full of ASM patches. Run it on a `trial.py` server first. Its protection covers only Forge events: mod explosives and Excavate bypass it, as they bypass everything. |
| A hybrid server (Crucible, the maintained Thermos fork) for CoreProtect, GriefPrevention and Essentials | the Bukkit admin stack, including true rollback | Hybrids remap classes and break coremods. This pack depends on qf-tweaks' ASM patches, a patched CodeChickenLib, Transformers and Morph fixes. **Not recommended.** |
| MyTown2 + MyEssentials-Core | towns and claims with mod-aware protection | heavy and flaky; known boot crashes in big packs |
| VoltzEngine regions (`/region`, `/ve`; `com.builtbroken.mc.modflag`, already in the pack) | regions that Voltz and ICBM blasts respect | ICBM-only. Useful for a no-missile zone around the hub, nothing more. |

**Recommendation.**

- ~~Fix log4j in the builder now.~~ **Done 2026-10-17, but not by deleting the
  class.** Deleting `JndiLookup.class` kills the server at launch: beta9's
  `Interpolator` constructs `JndiLookup` directly, so the first logger throws
  `NoClassDefFoundError`. The builder now swaps in an inert `JndiLookup` that
  resolves nothing, and the stripped jar boots.
- Add RCON over Tailscale for the host and one co-admin, and make that co-admin
  an op, so the server is never one person's hostage.
- Use ForgeEssentials only if the group wants grief rollback. If they do, trial
  it first and use only PlayerLogger and Backup. For 5-15 trusted friends, hourly
  backups plus the logs are probably enough, and they cost nothing.

---

## 6. Social systems: decisions nobody has written down

Each of these is a config value or a sentence in a rules post. None costs
performance. Today each one is a default that nobody chose.

**Prepared 2026-10-25.** The decisions are the owner's and are being recorded
on the Decisions page (`srv-pvp`, `srv-quests`, `srv-sleep`, `srv-afk`,
`srv-hub`, `srv-loaders`, `srv-graves`, `srv-tools`). Each id is a key in a
JSON file that `build_play_server.py --rules FILE --force` applies in one
rebuild; `tools/server/rules.example.json` holds the suggested choices below
and the hosting guide ("The owner's decisions") maps every key to the config
it changes. The team-with-friendly-fire-off setup is automated by the
supervisor (`team` key) rather than a first-boot script, so late joiners are
covered too. The rules post for the friends is drafted in
[`../setup/server-rules.md`](../setup/server-rules.md) with each open choice
marked `[pending: srv-xxx]`. Nothing has been applied to `C:\qfs\friends`.

| Topic | Today (evidence) | Problem | Suggested choice |
|---|---|---|---|
| **PvP** | `pvp=true`, no teams | Mod AoE (Legends powers, MCHeli, ICBM) and the Gravity Gun (`grabablePlayers=1`) make "accidental" PvP routine | Put everyone on a vanilla team with friendly fire off: `/scoreboard teams add qf`, `/scoreboard teams option qf friendlyfire false`. That blocks player-sourced damage at no cost. Turn off Gravity Gun player grabs. Leave server PvP on for opt-in duels. |
| **Land and grief** | Griefing allowed by choice; SecurityCraft `Is codebreaker allowed?=true` | In-pack locks are breakable by design | State the rule ("ask before you touch it; griefing is for consenting targets"). Back it with backups and, if wanted, ForgeEssentials PlayerLogger. Do not add claims unless the group asks. |
| **Graves** | GraveStones (OpenBlocks graves off); its config has no owner-only option; Witchery `AllowDeathItemRecoveryRite=true`; LevelUp `Skill points lost on death=5`; Sync shells override death | Assume anyone can loot anyone's grave (verify in section 7). The death penalty is lost skill points plus a walk back. | Accept the defaults, but write them down, including "don't loot other people's graves". |
| **Shared storage** | EnderStorage frequencies are shared unless diamond-locked (`personalItemID=diamond`) | Someone's "private" chest is anyone's | Put it in the rules post; it doubles as a legitimate mailbox system. |
| **Quest progression** | BetterQuesting `party_enable=1`; 305 of 308 tasks are retrieval with `consume=0` | With nothing consumed, one item set handed around completes the quest for every friend in turn and pays out every reward again. Parties may multiply rewards further (BQ 3.0.x shares completion; check whether each member can claim). | Decide: personal progression (no parties, and accept hand-me-down completions), or parties as the norm. For loot quests, consider `consume=1` on the few with the biggest rewards. |
| **Trading and economy** | No economy mod. ProjectE EMC is a de facto currency, and qf-commands lottery tickets are tradeable items that unlock commands. | Not a gap: a 5-15 group trades by hand | None needed. Optionally an op-built CustomNPCs trader at the hub. |
| **Getting together** | qf-commands has `/home`, vault and dimension tickets; non-ops otherwise only have `tell`, `help` and `me` (f6bc91a) | No way to join a friend, so groups drift apart in a 3,000-block world | Add a `/tpa` unlockable to qf-commands, earned like the rest (in house; negligible cost). |
| **Sleep** | Vanilla 1.7.10: every player in the dimension must sleep | With 5+ people, nights never skip | Morpheus (Quetzi; the 1.7.10 build is listed by mirrors) or Sleepy Head (adds a sleeping-percentage gamerule on 1.7.10). Server-side and cheap. |
| **AFK** | No `player-idle-timeout` | An AFK player holds 169 chunks and a JAS mob cap all night | `player-idle-timeout=30`, set via the builder (section 3). |
| **Hub and spawn** | `spawn-protection=0`; `spawnHasFuzz=true`, fuzz 20 | No shared place, and new players land somewhere random | Build a small hub at spawn before day one: rules on BiblioCraft boards, a community EnderStorage chest, a CustomNPCs greeter, the Twilight portal nearby. Set `spawn-protection=16`, which covers vanilla interactions by non-ops only. No machines (4e). |
| **Chat and names** | Vanilla chat, Microsoft names (with online mode), proximity voice | Fine for friends | Nothing. The supervisor's Discord webhook can mirror joins and deaths. |

---

## 7. Mods that misbehave in multiplayer

**Already found and fixed, by playing on a server.** These are listed in the
appendix. The scripted join test of 2026-10-16 found four bugs that singleplayer
hides. That is the strongest evidence in this document that the untested paths
below will also hide some.

**Known and accepted (hosting guide).**

- Legends `EntityLightningTrail` and `EntityLightning` crashes. The supervisor
  turns these into a one-minute outage.
- Witchery's Dream World via its normal entry. Only the `/dream_world` ticket was
  retired; returning twice crashed in Railcraft's TrailTicker. Natural entry
  remains untested on a server.

**Reputation only: nothing verified for these versions.** Web searches found no
version-specific reports, so treat these as unknowns, not knowns:

- ProjectE PE1.10.1;
- Archimedes Ships Plus 1.8.1 with MovingWorld 1.8.1 (lost ships across chunk
  unload or restart);
- Chest Transporter 2.0.4 (a 1.12.2 pack dropped it for picking up locked
  chests without the lock);
- Sync 4.0.1 (cross-dimension shell sync; its own config warns about End
  transitions).

**Multiplayer paths the scripted test did not cover.** It used one client, so
anything that depends on a second player was never exercised.

- Voice chat between two real clients, including the server-side 40-block cut.
- Bystander sync: a third player watching someone morph (Morph 0.9.3),
  transform (Transformers), use a Legends power, fire MCHeli weapons, or ride an
  Archimedes ship.
- Shared spaces: two players in one TARDIS interior, one Compact Machine, or one
  ship.
- Item handoff: two players on one EnderStorage frequency at once, and a second
  player looting the first's grave.
- Gravity Gun grabbing a player; Portal Gun portals placed by one player and
  used by another.
- BetterQuesting party completion and reward claims, with two members.
- Chest Transporter on a SecurityCraft keypad chest and on an
  EnderStorage-locked chest.

**Recommendation.** Before inviting the group, hold one two-person session
(host plus one friend) on a scratch copy of the world. Walk the list above and
record each result as a line in `hosting-a-server.md`'s "Found by playing on it"
section. Take a backup immediately before it, so the dupe tests can be thrown
away.

---

## 8. Content worth adding, and what is not

The bar: it makes a small-friends server better, costs no measurable TPS, and is
in the jar list before day one (section 3).

| Addition | Why for this group | Cost | Verdict |
|---|---|---|---|
| **Sleep vote** (Morpheus or Sleepy Head) | Nights otherwise never skip with 5+ players | server-side event handler | **add**. Morpheus 1.6.21 is behind `--rules srv-sleep` (2026-10-25); Sleepy Head would need every client |
| **`/tpa` unlockable** in qf-commands | Friends can actually play together; fits the lottery design | in-house, negligible | **add** |
| **Opis** | Answers "why is it lagging" | only while profiling | **add** (it adds no content, so it is safe to add later). `--opis` since 2026-10-25; console tables empty, see 4d |
| **WorldBorder-Forge** | Keeps play inside the pregenerated area | negligible | **add**, after a scratch trial. `--world-border RADIUS` since 2026-10-25, trialled |
| **Hub at spawn** (a build, not a mod) | Shared place, rules and portals; a first-session anchor | spawn chunks are loaded anyway | **do** |
| A first-session plan | Everyone joins at once: hub, rules, starter quests, a group trip to the Twilight portal; no Lycanites event on day 0 (4b) | none | **do** |
| ForgeEssentials | Rollback and permissions | see section 5 | only if the group wants grief rollback |
| Claims mods (FTBU 1.7.10, GTNH ServerUtilities, MyTown2) | Grief protection | Client installs plus libraries. GTNH ServerUtilities needs GTNHLib, and the pack has a standing rule against the GTNH mixin stack under OptiFine E7 (`performance-tuning.md`). | **skip**; griefing is on by choice |
| A Discord chat bridge mod | Talk to the server from outside | no 1.7.10 Forge bridge was confirmed here | **skip**; use the supervisor's webhook for status |
| More dimensions, mobs or worldgen | (none) | every one adds generation, entities and IDs | **skip**: the pack has plenty |

---

## Appendix A: already handled (from the git log, so nobody redoes it)

| Commit | What it fixed for multiplayer |
|---|---|
| fdf5fbc | Play-server builder: client-only drops, config copied verbatim, patched CCL, start scripts, offline-UUID whitelist |
| 95ff12a | GraveStones resyncing 7 Baubles slots: every death disconnected every player |
| 699e27e | Witchery and TragicMC potion IDs, OreSpawn and TragicMC biome IDs, Jungle cancelling every death; ChickenChunks 49 per player and offline off; TARDIS not always loaded; CompactMachines; CustomNPCs op-only |
| c1d4850 | Sealed Tome server crash, Soulbound CME and lava, voice frames sent from the netty thread, packet size caps, threading of speaker edits |
| f6bc91a | `/commands` refusing non-ops on a dedicated server; ghost player leaving the End; Dream World ticket retired |
| 8630df8 | Transformers: untrusted client packets, per-tick casts, login loading every dimension, idle Ground Bridge lag |
| f1d5343 | InventoryTweaks sorting applied enchant books server-side |
| 89856c3 | FakePlayer teleport NPEs in enchantments; `QFNetwork.toPlayer` NPE on a player with no connection |
| 31da143 | Morph kill kick and morph freeze (client); `/morph` works on a dedicated server |
| 8d934c7 | Railcraft Tracking Aura NPE (aura turned off) |
| (2026-10-17, see git log) | Supervisor (crash restart, hang dumps, hourly backups, daily restart, graceful stop, Discord alerts); builder refuses `--force` on a running server, keeps `server.properties`, `logs/`, `crash-reports/`, `backups/`; Log4Shell stub; `MANIFEST.sha256` |
| uncommitted (`git status`) | JAS distance 6 and tick spacing 2; JAS logging off; `ChunkCleanTransformer` in qf-tweaks |

## Appendix B: claims in this document that need checking before relying on them

- Railcraft personal anchors stop when the owner is offline (from Railcraft's
  documented behaviour, not tested here).
- RCON commands run on the RCON thread in 1.7.10 (from the decompiled
  `DedicatedServer.handleRConCommand`; check against the jar before scripting
  anything risky over RCON).
- ~~Opis, Morpheus and WorldBorder-Forge being accepted server-only by FML's
  handshake (`acceptableRemoteVersions="*"`). If any is not, it must ship in the
  client release.~~ **Checked 2026-10-25** from the jars' `@Mod` annotations
  (javap): Opis 1.2.5 (and its bundled MapWriter 2.1.2), Morpheus 1.6.21 and
  WorldBorder-Forge 1.0.2 all say `"*"`, and FML 1614's `NetworkModHolder`
  builds an `IgnoredChecker` for `"*"`, whose `check()` returns true for every
  client. Sleepy Head 1.0 has no `acceptableRemoteVersions`, so a client
  without it would be refused; it is not used. Still untested with a real
  client login (no client may be launched on this PC while the owner plays).
- Railcraft World Anchors having "no fuel key" (4c): wrong, the live config
  fuels them with ender pearls (`world.fuel=minecraft:ender_pearl=12`).
- ForgeEssentials 1.4.6's PlayerLogger rollback commands.
- Every per-mob and per-player cost figure marked unmeasured in section 4.

## Sources

- [WorldBorder-Forge (RoyCurtis)](https://github.com/RoyCurtis/WorldBorder-Forge)
- [ForgeEssentials 1.7.10 1.4.6.1373 server jar](https://www.curseforge.com/minecraft/mc-mods/forge-essentials/files/4353563)
- [ForgeEssentials forum thread (client mod not required)](https://www.minecraftforum.net/forums/mapping-and-modding-java-edition/minecraft-mods/1287664-forge-forgeessentials-bukkit-functionality-for)
- [ForgeEssentials PlayerLogger issue #1939](https://github.com/ForgeEssentials/ForgeEssentials/issues/1939)
- [Crucible (Thermos fork)](https://github.com/CrucibleMC/Crucible)
- [GTNH ServerUtilities](https://github.com/GTNewHorizons/ServerUtilities)
- [MobiusCore (Opis dependency)](https://moddex.gg/mod/mobiuscore)
- [Opis](https://craftane-main.onrender.com/mods/Opis)
- [Morpheus](https://www.curseforge.com/minecraft/mc-mods/morpheus)
- [Sleepy Head](https://www.curseforge.com/minecraft/mc-mods/sleepy-head)
- [MyTown2 on the FTB admin-mods list](https://forum.feed-the-beast.com/threads/comprehensive-list-of-mods-useful-for-server-admins.58524)
- [Chest Transporter lock-bypass removal (1.12.2 pack)](https://www.curseforge.com/minecraft/modpacks/clockwerk-pixelmon/files/2664827/dependencies)
