# Hosting the multiplayer server

How to run Quest Forge for a group of friends. This is a different server from
the survey servers in [`../../server/`](../../server/), which measure worldgen
and must never be reused for play — their config gives six qf-content
enchantments different IDs from every client.

## Build it

The server is never edited by hand. Rebuild it from the client instance after
any mod or config change:

```
py -3.10 tools/server/build_play_server.py ^
  --instance %APPDATA%\.crazycraft4 ^
  --forge-install C:\qfs\forge-install ^
  --out C:\qfs\friends --force
```

`--force` rebuilds an existing server. It keeps `world/`, `ops.json`,
`whitelist.json`, the ban lists, `usercache.json`, `server.properties`, `logs/`,
`crash-reports/`, `backups/`, `supervisor.json` and `play-options.json` (the
additions and decisions below). Everything else is
regenerated. A kept `server.properties` changes only where an option is given
on the command line (`--port`, `--max-players`, `--view-distance`,
`--online-mode`). The build refuses to run while the server is up. It checks
`supervisor.pid`, the port, Java command lines, and whether Windows will let it
rename the session lock, the open log and the folder itself.

What it does, and why:

- **Copies `config/` verbatim from the client.** 1.7.10 never syncs enchantment,
  potion or biome IDs. They agree only because both sides read the same files.
- **Drops nine client-only mods:** OptiFine, SoundFilters, CustomMenu,
  DamageIndicators, MobDismemberment, MobAmputation, InventoryTweaks, Controlling
  and JourneyMap. Clients keep all of them. QuestForgeTweaks stays: one of its
  patches fixes GraveStones on the server side. FML lets a client
  carry mods the server lacks, but refuses any client missing one of the
  server's.
- **Keeps `mods/saintspack/`, and `start.bat` always starts from the server
  folder.** Saintscore reads `mods\saintspack\Packs.txt` relative to the working
  directory and crashes the boot without it.
- **Takes the instance's CodeChickenCore as it is.** Since 2026-10-18 that is
  GTNH CodeChickenCore 1.4.22, with CodeChickenLib merged in (see
  "CodeChickenCore" below). It needs no patch for pregeneration. The build
  prints which CCC it found, and refuses `--ccl` or a leftover CodeChickenLib
  next to GTNH CCC (a duplicate mod).
- **Writes play settings:** survival, Normal difficulty, whitelist on,
  `allow-flight=true` (otherwise vanilla kicks Transformers jets, Legends heroes
  and OreSpawn gliders after four seconds airborne), 15 players, view distance 6,
  online mode on. See "Performance" for why 6.
- **Writes `start.bat` and `start.sh`** with a 10 GB heap (`--xmx`) and GC
  logging to `logs/gc.log`.
- **Removes `JndiLookup.class` from `minecraft_server.1.7.10.jar` (Log4Shell).**
  The server's log4j is 2.0-beta9, and the `-Dlog4j2.formatMsgNoLookups` flag
  only works from 2.10 on, so the flag alone does nothing.
- **Installs `supervisor.py`, `start-supervised.bat` and a default
  `supervisor.json`**, and hashes every jar and config file into
  `MANIFEST.sha256`.
- **Optionally adds server-only mods and applies the owner's decisions:**
  `--opis`, `--world-border RADIUS`, `--rules FILE`, `--backup-mirror DIR`.
  See "Server-only additions" and "The owner's decisions" below.

## The Java 25 server (`--java25`)

Approved 2026-10-17. The same server on Temurin 25 with lwjgl3ify and UniMixins
on Forge 1614, and nothing else from the GTNH stack. Today's OptiFine E7 clients
join it unchanged; they stay on Java 8 and Forge 1558. The point is garbage
collection. In a 10-minute idle run with 320 mobs on the same world, Java 8
stopped the server for 1,412 ms in all, and its worst stall was 311 ms, right
after boot. Java 25 stopped it for 281 ms, with a worst stall of 46 ms. Details
and the earlier benches are in
[`../design/angelica-decision.md`](../design/angelica-decision.md).

Build it with `--java25` added. `--forge-install` is not needed:

```
py -3.10 tools/server/build_play_server.py --java25 ^
  --instance %APPDATA%\.crazycraft4 ^
  --out C:\qfs\friends --force
```

What it adds to the normal build:

- **Pinned downloads, checked by sha256:** lwjgl3ify 3.0.39 (its
  `forgePatches` launcher and the mod jar), UniMixins 0.3.2, lwjgl3ify's
  `java9args.txt` from the same tag, and the Forge 1614 installer. They are
  fetched once into `%LOCALAPPDATA%\quest-forge\server-deps` (`--cache`).
  Forge 1614 is installed there with Java 8 (`--java8`). A file whose hash
  differs is thrown away and never used.
- **The layout lwjgl3ify's README asks for:** `lwjgl3ify-forgePatches.jar`
  next to `forge-1.7.10-10.13.4.1614-1.7.10-universal.jar` and
  `minecraft_server.1.7.10.jar` (its manifest names both, by exact file name),
  `java9args.txt` beside them, and `lwjgl3ify-3.0.39.jar` and
  `+unimixins-all-1.7.10-0.3.2.jar` in `mods/`.
- **A Java 25 command line in `start.bat`/`start.sh`:**
  `java <heap and G1 flags> -Xlog:gc,safepoint:file=logs/gc.log:... @java9args.txt -jar lwjgl3ify-forgePatches.jar nogui`.
  The Java 8 GC flags (`-Xloggc`, `-XX:+PrintGC*`, `-XX:+UseSplitVerifier`)
  stop Java 25 from starting, so they are replaced. The GC log is still
  `logs/gc.log`, rotated 5 × 20 MB. Java is the newest
  `C:\Program Files\Eclipse Adoptium\jdk-25*` (`--java` to override).
  `start-supervised.bat` and the supervisor work unchanged. They read the
  command from `start.bat`, and the hang dumps use the `jstack` of the JDK 25
  the server runs on.
- **Refuses to build** if the pack's mods contain Hodgepodge, ArchaicFix,
  GTNHLib or Angelica. On a server, each of those becomes required on every
  client, and GTNHLib crashes OptiFine. It also refuses if the pack's
  QuestForgeTweaks lacks the three Java 25 fixes below. Install the current
  qf-tweaks build first, or name a jar with `--tweaks`.
- **Adds `Forge` to qf-content's packcheck `ignoreMods`** in the server's
  `config/qfcontent.cfg`. The login check refuses any client whose version of
  a shared mod differs, and to it Forge counts as a mod: every Java 8 client
  (Forge 1558) was refused with "Your mods differ from the server's. Mods:
  Minecraft Forge 10.13.4.1558 (server 10.13.4.1614)". FML's own handshake
  accepts that pair. The setting is read only on the server and is not an ID
  entry, so the config fingerprint clients must match is unchanged.
- `logs/` is created by the build. Java 25 refuses to start when the GC log's
  folder is missing.

Three mods break on Java 25 alone. Each is fixed by a transformer in qf-tweaks
that does nothing on Java 8:

| Mod | Breakage on Java 25 | Fix |
|---|---|---|
| Lucky Block | Every drop expression fails (301 errors at boot): Java 25 has no JavaScript engine of its own. | `LuckyScriptTransformer` points it at lwjgl3ify's Nashorn. |
| Recurrent Complex | The loot tables Holy, Unholy, TribalChest and PeacefulCrypt fail to load. They hold enchanted books as wrapped NBT, which lwjgl3ify's Gson 2.10 rejects. Their structures then generate without loot. | `RecNbtTransformer` asks Gson for `NBTBase` for wrapped tags. |
| AsieLib | `nicknames.json` fails to load from the second boot on, because Gson 2.10 can't build a `HashBiMap`. `/nick` names are lost. | `AsieNickTransformer` falls back to reading the file as a plain map. |

Like every client, the server runs GTNH CodeChickenCore 1.4.22 since
2026-10-18 (next section), so Angelica clients can join it.

### Switching the friends' server to Java 25

Done for `C:\qfs\friends` in the 2026-10-17 batch ([`batch-2026-10-17.md`](batch-2026-10-17.md)). For another server, do this after the clients have the batch:

1. Stop the server (`stop` or Ctrl+C in the supervisor window) and wait for the
   supervisor to exit.
2. Back up `C:\qfs\friends\world` (copy the folder, or keep the newest zip from
   `backups\`).
3. Put the current qf-tweaks into the pack with the rest of the batch. Build it
   with `mods\qf-tweaks\build.bat --no-install`, then
   `py -3.10 tools/trial/trial.py install mods/qf-tweaks/QuestForgeTweaks-1.0.jar --why "Java 25 server fixes"`.
   It must be a build that includes `RecNbtTransformer` and
   `AsieNickTransformer`. The `--java25` build refuses an older one and says
   which fix is missing. **Friends need the same jar.** qf-tweaks carries a
   version (`qftweaks`, `1.1.0+<date>.<sha8>`), and qf-content's pack check
   refuses a client whose version differs from the server's. So the new jar
   goes out in the client release of the same batch. For the same reason, use
   `--tweaks` only for tests, unless the clients have that exact jar.
4. Run the `--java25` build above. It keeps `world/`, the player lists,
   `server.properties`, `logs/`, `backups/` and `supervisor.json`.
5. Start `start-supervised.bat`. The first boot logs these, and all of them are
   expected:
   - `Lucky Block: the JDK has no JavaScript engine; using the game class loader's`
   - `Recurrent Complex: Gson checks adapter results`
   - `FML appears to be missing any signature data`. This is an ERROR line,
     but harmless: FML can't read its own jar's signature through lwjgl3ify's
     launcher.
   - One VoltzEngine `Could not locate folder[ /content/<mod>/ ]` line for each
     of the 9 new mod IDs (lwjgl3ify and UniMixins' modules). VoltzEngine
     prints the same line for every mod in the pack.
6. Join once and check that `logs/gc.log` is growing.

### Switching back to Java 8

Stop the server and rebuild without `--java25`, with the usual Java 8 command:

```
py -3.10 tools/server/build_play_server.py ^
  --instance %APPDATA%\.crazycraft4 ^
  --forge-install C:\qfs\forge-install ^
  --out C:\qfs\friends --force
```

The world carries over. On the first Java 8 boot, FML logs `This world was saved
with mod lwjgl3ify which appears to be missing` (and the same for the UniMixins
modules). Those mods add no blocks or items, so nothing is lost. Tested
2026-10-17 by switching the test server back and forth.

## CodeChickenCore

Since 2026-10-18 the pack, the server and every client run **GTNH
CodeChickenCore 1.4.22** (`CodeChickenCore-1.4.22.jar`, sha1 `f4b6d5e12fdd`, the
same as on nexus.gtnewhorizons.com) instead of stock `CodeChickenCore.jar` +
`mods/1.7.10/CodeChickenLib-1.7.10-1.1.3.138-universal.jar`. CodeChickenLib is
merged into it. Why:

- **Angelica clients need it,** and NEI's packets differ between the two. With
  stock CCC on the server, a client running GTNH CCC is kicked about 5 seconds
  after login. So the server and **every** client, E7 or Angelica, must run the
  same one. A friend still on stock CCC is kicked from the friends' server.
- **The OptiFine E7 client runs on it unchanged.** NEI, ForgeMultipart,
  ChickenChunks, EnderStorage and WR-CBE ask only for CodeChickenCore 1.0.3 to
  1.0.7 or newer. ForgeMultipart's DepLoader finds CodeChickenLib's classes
  inside it, so it downloads nothing. The stock ForgeMultipart stays.
- **Pregeneration needs no patch any more.** Stock CodeChickenLib's
  `WorldExtension.unloadChunk` has no null check, and pregeneration crashes on it
  within seconds. GTNH CCC has the check. On 2026-10-18 a slim server
  (ForgeMultipart + Chunk Pregenerator) pregenerated 40,000 chunks on GTNH CCC
  with 0 failures. The same server with stock CCC + CCL crashed on that NPE in
  its first second. `--ccl` is still there for a pack on stock CCC, and is
  refused otherwise.

In the live pack the swap was `trial.py install CodeChickenCore-1.4.22.jar
--replace CodeChickenCore.jar` and `trial.py uninstall
"1.7.10/CodeChickenLib-*.jar"`. A friend's own install makes the same swap:
delete those two jars and add `CodeChickenCore-1.4.22.jar` (link in
`tools/angelica-client/manifest.json`, `source_must_have`).

## Running the server

Double-click **`start-supervised.bat`**. Its window is the server console: type
commands as usual. The supervisor (`tools/server/supervisor.py`) owns the Java
process and handles the following:

- **Crash restart.** It restarts after any exit nobody asked for, waiting 10,
  30, 60, then 120 s. After three crashes in 15 minutes it stops trying and
  says so. A crash loop needs a person.
- **Hang detection.** It sends `list` every 60 s. If there is no answer in 90 s,
  the tick is stuck: it writes a `jstack` thread dump to
  `logs/threaddump-*.txt`, kills Java and restarts. Thread dumps need a JDK of
  the server's Java version: on Java 8, a JDK 8 (the JRE has no jstack); the
  Java 25 build runs on Temurin's JDK, which has `jstack` and `jcmd` (either is
  used). Tested 2026-10-25 with `tools/server/simulate_hang.py <pid>`, which
  suspends only the `Server thread` of a scratch server: the probe timed out,
  the dump was written with the frozen thread in it, Java was killed and the
  server was back within the backoff plus a boot. Never run that script
  against the friends' server.
- **Hourly backups** to `backups/hourly/` (24 kept), and the first of each day
  to `backups/daily/` (7 kept). Each backup is skipped if nobody has been online
  since the last one. A backup runs `save-off` and `save-all`, waits for
  `Saved the world` and for the region files to go quiet, copies the world,
  then runs `save-on`. Saving is off for those waits and the copy (17 s on a
  fresh full-pack world in testing). The zip is written afterwards. Each zip also holds `server.properties`, the player lists
  and `MANIFEST.sha256`, the jar set the world needs.
- **A daily restart** at 05:00. If anyone is online, it warns them at 10, 5
  and 1 minutes. It takes a backup first.
- **A graceful stop.** Press Ctrl+C or type `stop`. Either one saves and waits
  for Java to exit. Closing the window also sends `stop`; Java runs in its own
  hidden console, so it finishes the save after the window is gone. Still,
  prefer Ctrl+C.

Supervisor commands, typed in the same window: `!backup`, `!restart`, `!dump`
(a thread dump), `!jfr [seconds]` (a Flight Recorder profile into `logs/`, see
"Opis"), `!status` and `!stop`. Without a console (a remote shell, a
synced folder), put the same lines into a file named `supervisor.inbox` in the
server folder, or create `stop.flag`. Write those files from bash or Python,
not PowerShell, which adds a BOM. The supervisor's own log is
`logs/supervisor.log`.

**Settings** are in `supervisor.json`. Rebuilds keep it.
`py -3 supervisor.py --print-defaults` lists every key. For **Discord alerts**
(crash, hang, restart, a crash loop, failed backups, Forge deleting an
erroring entity), set `discord_webhook` there, or set the environment variable
`QF_DISCORD_WEBHOOK`. Never put the URL in the repo. Without a webhook every
alert is only a line in `logs/supervisor.log`; with a wrong one the post fails
in its own thread and is logged as `webhook post failed: <error type>` with the
URL never printed (tested 2026-10-25 with an unreachable URL). The builder
writes two keys for you: `backup_mirror` (`--backup-mirror`) and `team`
(`--rules`, `srv-pvp`). `restart_min_uptime_s` (3600) is how close to
`restart_at` a boot may be before the restart waits a day.

**One team, friendly fire off** (`team` in `supervisor.json`, set by the
builder's `--rules` when `srv-pvp` is `"team"`): at every boot the supervisor
runs `scoreboard teams add qf` and `scoreboard teams option qf friendlyfire
false`, and puts every player who joins on the team. Vanilla then drops any
damage whose source is a teammate, which covers swords, arrows and the mod
weapons that name the attacker (Legends powers, MCHeli, ICBM blasts with an
owner). `pvp=true` stays, so a duel is two players an op takes off the team
(`scoreboard teams leave <name>`). Without the supervisor, type the two
commands once and `scoreboard teams join qf <name>` per player.

`start.bat` still works on its own, with no restarts and no backups.

## Backups: the restore drill and off-machine copies

The supervisor's zips hold `world/` plus `server.properties`, the player lists,
`BUILT-FROM.txt` and `MANIFEST.sha256`. The drill below was run on a scratch
server on 2026-10-25 (backup, change a gamerule, stop, restore, boot, read the
gamerule back). Two things it found are built into the steps: unzipping a
backup over the server folder also overwrites `server.properties`,
`MANIFEST.sha256` and the player lists with the copies from backup time, and
nothing checked that the jars still matched the world. `tools/server/restore_backup.py`
does the checks and extracts only `world/`.

### Restoring a backup

1. Pick the zip: `backups/hourly/` (24 kept) for the last few hours,
   `backups/daily/` (7 kept) or the mirror folder for older. Names are
   `world-<yyyymmdd>-<hhmmss>.zip`, local time.
2. Stop the server: `!stop` or Ctrl+C in the supervisor window, or create
   `stop.flag`. Wait for `supervisor exited` in `logs/supervisor.log`. The
   restore refuses to run while anything holds the folder.
3. Check before touching anything:
   ```
   py -3.10 -I tools/server/restore_backup.py --server C:\qfs\friends --backup <zip> --check-only
   ```
   It compares the zip's `MANIFEST.sha256` with the server's jars and configs
   now. Config differences are listed and allowed (the server rewrites about 45
   config files at boot; none is an ID entry). A **jar** difference stops it:
   the world is only valid with the jar set it was saved under. Either rebuild
   to that set first (`BUILT-FROM.txt` inside the zip says how it was built)
   or, if the change is a server-only addition (Opis, Morpheus, WorldBorder)
   pass `--accept-jar-changes`.
4. Restore:
   ```
   py -3.10 -I tools/server/restore_backup.py --server C:\qfs\friends --backup <zip>
   ```
   The current `world/` is renamed to `world.before-restore-<time>/`, nothing is
   deleted, and only `world/` comes out of the zip. Add `--with-player-lists` to
   also take `ops.json`, `whitelist.json` and the ban lists from the zip (after
   an op or whitelist mistake). `server.properties` is never restored from a
   backup.
5. Start `start-supervised.bat`, wait for `server is up`, and have someone log
   in. Check that what the backup was chosen for is back (a chest, a build, a
   quest). In the drill: `gamerule doDaylightCycle` printed `true` again on a
   world where it had been set to `false` after the backup.
6. Tell the players what was rolled back and to which time, then delete
   `world.before-restore-*` once nobody misses anything in it.

By hand, if Python is not available: stop the server, rename `world/`, extract
**only** the `world/` folder from the zip, start. Do not extract the whole zip
into the server folder.

### Off-machine copies (`--backup-mirror`)

`backups/` is on the same disk as the world, so a dead disk takes both. Build
with `--backup-mirror DIR` and the supervisor writes a second copy of every
daily backup into `DIR` (written as `.partial`, then renamed, so a sync client
never ships a half-written zip), keeps `keep_daily` of them there, and alerts
if the copy fails without ever touching the server. Tested 2026-10-25: the
mirror copy was byte-identical to the daily.

- The cheapest off-machine copy is a folder another machine already syncs.
  `C:\qf-world` is a Syncthing folder shared with the owner's Mac, so
  `--backup-mirror C:\qf-world\server-backups` puts every daily on the Mac
  with no new setup. Each daily is 70 MB for a fresh world and grows with it;
  7 of a played world may be several GB. If that is too much for the Mac,
  create a second Syncthing folder for the mirror instead of using
  `C:\qf-world` (Syncthing: Add Folder, pick the mirror directory, share it
  with the Mac), or point the mirror at an external disk or a OneDrive folder.
- Never sync the live `world/` folder itself: a sync client copying region
  files mid-write ships a torn world.
- The setting is `backup_mirror` in `supervisor.json`, kept across rebuilds;
  `--backup-mirror none` turns it off.

## "Who's online": the status feed for the site

The site's [`/online/`](../../site/online/) page shows who is on, when the
server was last seen, its uptime, the pack fingerprint and the tick time per
dimension. The data comes from the supervisor, in two steps:

1. **`status.json` next to `supervisor.py`**, rewritten (whole file, renamed
   into place) after every `list` probe, at boot, and on every stop, crash or
   hang. Keys: `state` (`online`, `starting`, `offline`), `reason`, `online`
   (names), `count`, `max`, `updated_at` (UTC, `Z`), `last_restart`,
   `uptime_s`, `minecraft`, `pack` (`date`, `fingerprint`, `mods`, from
   qf-content's boot line) and `tps` (`overall` and per-dimension `ms`/`tps`
   from `forge tps`, sent every `status_tps_interval_s` = 300 s; it prints
   about 35 lines each time, which is the whole cost). Names come from the
   line after `There are N/M players online:`, and joins and leaves update
   them between probes. Always on; `status_file: ""` turns it off.
2. **A publisher**, off until configured, so a server with nothing set does
   nothing. `status_publisher: "gist"` PATCHes a GitHub Gist through the API
   after every write, at most once per `status_publish_min_interval_s` (60)
   unless the state changed. `"dry-run"` logs what it would send. Failures
   are logged (with the HTTP code, never the token) at the 1st, 10th and
   100th in a row, and the page keeps showing the last good status, marked
   stale after 5 minutes.

**Why a Gist and not a push to the repo.** Every push that touches `site/**`
redeploys the whole site through Pages (`.github/workflows/pages.yml`), so a
status every minute would be 1,440 deploys a day and a token with write access
to the repo on the host PC. A Gist is one JSON file behind a raw URL that
browsers can read cross-origin, the token can only touch gists, and the site
never redeploys for it.

**Setting it up** (the owner, once):

1. Create a secret Gist at gist.github.com with one file named
   `status.json` (any content). Its id is the hex string in the URL.
2. Create a token that can only write gists: Settings > Developer settings >
   Personal access tokens. Fine-grained: account permission **Gists:
   Read and write**, nothing else; or classic with only the `gist` scope.
3. Put both in the server's `supervisor.json` (kept across rebuilds; never
   commit it): `"status_publisher": "gist"`, `"status_gist_id": "<id>"`,
   `"status_gist_token": "<token>"`. The token may instead go in the
   environment variable `QF_STATUS_GIST_TOKEN` of the account that runs
   `start-supervised.bat`. Restart the supervisor; its first lines say
   `status feed: status.json, publisher gist`.
4. Open the Gist, click Raw on `status.json`, and take the URL **without the
   commit hash**: `https://gist.githubusercontent.com/<user>/<id>/raw/status.json`
   (that form always serves the newest revision). Put it in
   `site/online/config.json` as `feed` and commit. Until then the page and the
   homepage card say "Not yet connected"; `/online/?demo` shows the layout with
   sample data, `?demo&stale` the stale warning.

Tested 2026-10-25 on a scratch server against a mock of the Gist API
(`status_api_url` points the publisher at it): `status.json` was written at
boot and after each probe with the fields above, every write was PATCHed with
the bearer token and the GitHub headers, and the page rendered the sample
feed, the stale warning and the not-connected state in headless Edge
(`tools/site/screenshot.py`). Not tested: a real Gist (no token was created).

## The host machine

The server runs on the owner's PC, so the PC's own settings are part of the
server. `tools/server/host_check.py` reads each of these and prints PASS, FAIL,
WARN or MANUAL with the fix; run it before a season and after any Windows
update:

```
py -3.10 -I tools/server/host_check.py --server C:\qfs\friends --play-hours 17-02
```

| Setting | Why | Check / fix |
|---|---|---|
| **Sleep and hibernation off on AC power** | A sleeping PC is a server that is down, and a world saved mid-write | `powercfg /change standby-timeout-ac 0` and `hibernate-timeout-ac 0` (the script reads the current scheme) |
| **Windows Update active hours cover the play hours** | Outside them Windows may reboot for an update, mid-save; with the daily restart at 05:00, a reboot should land after it | Settings > Windows Update > Advanced options > Active hours, manual, at most 18 h. Or pause updates for the season. Was 11:00-05:00 on 2026-10-25 |
| **Firewall: inbound TCP on the server port** | Without a rule, nobody outside the LAN reaches the server even with the router forwarding the port | admin PowerShell: `New-NetFirewallRule -DisplayName 'Quest Forge server' -Direction Inbound -Protocol TCP -LocalPort 25565 -Action Allow -Profile Any`. **Missing on 2026-10-25** |
| **Router forwards TCP 25565 to this PC** | The only way friends get in | The script prints the LAN and public addresses; forward in the router, then have a friend connect while the server is up. Cannot be checked from inside (MANUAL) |
| **Syncthing running, `C:\qf-world` connected to the Mac** | The backup mirror leaves the machine only through it | The script reads Syncthing's REST API (key from `%LOCALAPPDATA%\Syncthing\config.xml`): share present, a peer connected, state idle. Connected on 2026-10-25 |
| **Backup mirror inside the share** | Otherwise the mirror is a second copy on the same disk | `--backup-mirror C:\qf-world\server-backups` at build time |
| **Census `PAUSE` file during sessions** | `run_campaign.py` nodes compete for the clocks the tick needs | The script fails if a campaign runs without `C:\qfs\campaign\PAUSE` |
| **A JDK for the server's Java** | Hang dumps need `jstack`; `!jfr` needs `jcmd` | The `--java25` build runs on Temurin's JDK: pass |
| **Free disk** | Hourly zips plus seven dailies | At least 20 GB or ten dailies' worth |
| **A Discord webhook** | Otherwise a crash loop at 3 a.m. is a line in a log | `discord_webhook` in `supervisor.json` (WARN if missing) |

The 2026-10-25 run on this PC: sleep and hibernate never, active hours
11:00-05:00 (play 17:00-02:00 covered), Syncthing connected, no campaign
running, JDK 25, 2 TB free; **FAIL on the firewall rule**, WARN on the
webhook and the mirror, MANUAL on the port forward. The firewall rule and the
port forward need the owner (admin rights and the router).

## Server-only additions

Three mods the builder can add that no client needs. Each declares
`acceptableRemoteVersions="*"`, which FML 1614 answers with its
`IgnoredChecker` (read from the jar and from the Forge jar, 2026-10-25), so a
client without the mod joins. None adds a block or item, so they can be added to
a running world. They are pinned downloads checked by sha256, like the Java 25
deps, and remembered in `play-options.json`, so a rebuild keeps them.

### Opis, the profiler (`--opis`)

Opis 1.2.5 for 1.7.10, which needs exactly MobiusCore 1.2.5; the pack ships
it (`mods/MobiusCore.jar`). Booted on the scratch server with no errors.
Console commands (`opis_help` lists them): `opis_start`, `opis_stop`,
`opis_ticks <n>` (data points per run; `config/Opis.cfg` `profiler.maxpts`,
default 250), `opis_ent` and `opis_te` (the 20 slowest entities and tile
entities), `opis_chunk` (the 20 slowest chunks), `opis_nent` (entity counts by
type), `opis_kill`, `opis_killall`.

**What worked and what did not (2026-10-25, scratch servers).** Opis boots on
both builds and `opis_nent` lists every entity type with counts on both. The
timing tables differ:

- **Java 25 (`--java25`, the friends' server):** `opis_ent` and `opis_te`
  print only their header, even with 40 summoned creepers ticking in the spawn
  chunks for 600 ticks of a 2,000-tick run. Opis's entity profiler recorded
  nothing (a row needs 40 samples; its data map stayed empty). MobiusCore
  logs the same "Successful injection in h ()V" lines as on Java 8, so the
  hooks are injected but never deliver under the lwjgl3ify launcher. Not
  understood yet; a follow-up.
- **Java 8 (the stock build):** the same test lists 20 entities and 20 tile
  entities, so the profiler works there. But the console prints each row as
  `DataEntity@35d0ac7f`: the rows are objects for the `/opis` GUI, and the
  console path is deprecated (the command says so). The tables are readable
  only in the GUI, which needs Opis on the client.

So on the live server Opis is, today, an entity census (`opis_nent`) and
nothing more. The measurement that does work on Java 25 is the JDK's own
**Flight Recorder**: `!jfr [seconds]` in the supervisor window (default 120)
runs `jcmd <pid> JFR.start settings=profile` and writes
`logs/profile-<time>.jfr`, about 1% overhead while it records. Read it with
`"C:\Program Files\Eclipse Adoptium\jdk-25*\bin\jfr" print --events jdk.ExecutionSample logs\profile-*.jfr`
(hot stacks: the mod whose tick methods appear most is the cost) or open it
in JDK Mission Control. It samples Java methods, not entities, so it answers
"which mod" rather than "which machine"; for "which chunk" use `forge tps`
per dimension plus `opis_nent`. Tested 2026-10-25 on the Java 25 scratch
server: a 20 s recording was written and `jfr summary` read it.

**Profile the first real session** (the audit's section 4b asks for 5 players
spread out):

1. Before the session, `!status` in the supervisor window, and `forge tps`
   for a baseline with nobody on (idle was 1.3 ms overall on the scratch
   server).
2. Twenty minutes in, with everyone spread out: `forge tps`. Note the
   `Overall` mean tick time and the slowest `Dim`. Over 40 ms means the
   evening is in trouble; 20-40 ms means the next steps matter.
3. `!jfr 120` while it is at its worst. Afterwards, `jfr print --events
   jdk.ExecutionSample` on the file and count the top frames by mod package
   (`lycanitesmobs`, `danger.orespawn`, `tragicneko`, `mods.railcraft`,
   `fi.dy.masa`...). Paste the top ten into the session notes.
4. `opis_nent` for the entity census. Compare with the JAS caps in
   `hosting-a-server.md` (46 monsters per player at distance 6). If the host
   carries Opis on his client (safe: the server has it too), `/opis` in game
   gives the per-entity and per-tile tables on a Java 8 server only.
5. Decide from numbers, not guesses, in this order: event mobs piling up
   (Lycanites `forced no despawning`), a chunk-loaded base with a spawner
   tower, JAS caps, then view distance.

### World border (`--world-border RADIUS`)

WorldBorder-Forge 1.0.2 (RoyCurtis's port of Brettflan's WorldBorder). The
builder writes `config/WorldBorder/borders.cfg` with one square border of
`RADIUS` blocks around 0,0 in the overworld, in the layout the mod itself
writes, so it is in force from the first boot; `--world-border 0` removes it.
Tested 2026-10-25: boots with the full pack on Java 25, `wb list` shows the
border, and the border survived a stop, a restore and three restarts. To the
mod the overworld is named after `level-name` (`world`), other dimensions
`DIM<id>`. Console commands: `wb list`, `wb world set <radius> <x> <z>`,
`wb wshape world square|round`, `wb DIM7 set ...` for the Twilight Forest,
`wb world fill` to pregenerate up to the border (a slower alternative to
ChunkPregenerator), `wb world trim` to delete chunks outside it,
`wb world clear`. Knockback is 3 blocks, checked every 20 ticks; ender pearls
past the border are cancelled; blocks cannot be placed and mobs do not spawn
outside it (`main.cfg`). Pick the radius to match the pregenerated area
(3,000 for the 188-chunk plan).

## The owner's decisions (`--rules`)

Sections 4 and 6 of the audit are choices only the owner makes. Each one is a
line in a small JSON file keyed by decision id, and
`build_play_server.py --rules FILE --force` turns the whole file into the
server's settings in one rebuild. `tools/server/rules.example.json` lists every
key with its choices; its values are the audit's recommendations, so edit it to
the owner's answers, then:

```
py -3.10 tools/server/build_play_server.py --java25 ^
  --instance %APPDATA%\.crazycraft4 --out C:\qfs\friends ^
  --rules docs\decisions\server-rules.json --force
```

The file is remembered in the server's `play-options.json`, so later rebuilds
keep applying it (`--rules none` forgets it). Every edit is to the **server's
copy** of a config: none of these keys is an ID entry, so the pack fingerprint
clients must match is unchanged, and clients need no new release. A client with
the old value still shows the old recipe or option locally (NEI lists the World
Anchor recipe, say), but the server decides. `BUILT-FROM.txt` records what was
applied. Tested 2026-10-25 on the scratch server with the example file: every
edit landed, the server booted, and the team was created at boot.

| Decision | Values | What the builder changes |
|---|---|---|
| `srv-pvp` | `"team"`, `"off"`, `"on"` | `team`: supervisor.json `team=qf` (one team, friendly fire off, see "Running the server"), `GraviGun.cfg grabablePlayers=0`, `pvp=true`. `off`: `pvp=false`, `grabablePlayers=0`. `on`: vanilla. |
| `srv-quests` | `"personal"`, `"parties"` | `party_enable` in `config/betterquesting/DefaultQuests.json`. BetterQuesting copies that file into the world at creation; an existing world takes it with `/bq_admin default load` (back up first). |
| `srv-sleep` | percent `0`-`100` | Above 0: Morpheus 1.6.21 installed and `config/Morpheus.cfg` `SleeperPerc` set; that share of the players in the dimension asleep skips the night. `0`: no mod, vanilla rule. |
| `srv-afk` | minutes, `0` = never | `server.properties player-idle-timeout`. |
| `srv-hub` | blocks, `0` = off | `server.properties spawn-protection`: non-ops cannot place or break inside that radius of spawn (vanilla interactions only). |
| `srv-loaders` | `{"world_anchors": "off"\|"capped"\|"on", "sync_shells": bool}` | `off`: Railcraft `anchors.craftable=false` (World Anchors; Personal and Passive stay). `capped`: a `Railcraft { 20 tickets x 9 chunks }` block in `forgeChunkLoading.cfg`. `sync_shells`: Sync `allowChunkLoading`. Note: the audit said World Anchors burn no fuel; the live config has `world.fuel=minecraft:ender_pearl=12`, so they do. |
| `srv-graves` | `"shared"`, `"owner-only"` | Nothing: GraveStones has no owner-only option. The value is for the rules post. |
| `srv-tools` | `{"chest_transporter_spawners": bool, "projecte_time_watch_pedestal": ticks, "lycanites_first_event_day": day}` | ChestTransporter `pickupSpawners`; ProjectE `timePedBonus` (mod default 18, `0` = the Watch of Flowing Time gives machines nothing from a pedestal); Lycanites `Random Mob Events Day Minimum Overworld (0)`. |

Sleepy Head 1.0 was the other sleep-vote candidate. Its `@Mod` has no
`acceptableRemoteVersions`, so every client would need it; it is not used.

## Run it without the supervisor

`start.bat` (Windows) or `./start.sh` (Linux) runs Java once. It boots in
about a minute; the first boot also generates the world. Type `stop` in its
window to shut down. It saves. 1.7.10 has no watchdog, so a hung tick hangs
forever; if the console stops responding, check `logs/fml-server-latest.log`
before killing it.

On a rented host with a control panel (Pterodactyl and the like), the panel
starts the server itself. For a Java 8 build choose **Java 8**, since Forge
1.7.10 does not start on anything newer by itself; for a `--java25` build
choose **Java 25** (see below). Paste the JVM flags from `start.sh` into its
startup field, and upload the whole server folder over SFTP.

## Online mode

**The friends' server runs in online mode** (`online-mode=true`): the user's
decision of 2026-10-18, and the builder's default. The server asks Mojang's
session servers to confirm every login, so a name on the server is that
player's real account and nobody can join under someone else's name. A rebuild
keeps the setting in `server.properties`; `--online-mode true` or `false`
changes it.

**What each friend needs:**

- **A real Minecraft: Java Edition account** (a Microsoft account that owns the
  game).
- **A launcher that logs in with it.** Prism Launcher is the recommended one: add
  the account under Accounts, and run the pack as a Forge 1.7.10 instance. The
  pack's own `TEST-LAUNCH.bat`, `LAUNCH-ANGELICA.bat` and the 10-17 release's
  `PLAY*.bat` start the game **offline** (`--accessToken 0`). The server refuses
  them at login. They are for singleplayer and LAN only.
- The same mods and config as the server ("What every friend needs" below).

**The whitelist holds real account names.** In online mode a player is
identified by their account's UUID. With the server running, `whitelist add
<name>` in the console looks the name up at Mojang and stores that UUID. So add
each friend by their exact Minecraft name, and op yourself the same way:

```
whitelist add TheirRealName
op YourRealName
```

`--player` is refused in online mode, because it writes the offline UUID. The
`Dev` entry in `whitelist.json` and `ops.json` is the offline test account from
2026-10-16. Its UUID (`380df991-...`) is the offline one, which no real account
has, so it does nothing in online mode. Remove it with `whitelist remove Dev`
and `deop Dev`, or leave it.

**Testing without an account.** Build a scratch copy with `--online-mode false
--player Dev --port <N> --out C:\qfs\<scratch>` and join it from an offline
launcher (`trial.py launch NAME --join 127.0.0.1:<N>`). Never switch the friends'
server itself to offline mode. An offline server lets anyone join under any
name, so the whitelist filters names but does not prove identity.

**In offline mode, do not use `whitelist add`.** It stores the UUID of the paid
account that has that name, but an offline player is identified by a UUID
derived from the name, so they are refused with "You are not white-listed". Pass
each name to the build with `--player <name>` (repeatable; existing entries are
kept), then run `whitelist reload` if the server is up. `op <name>` has the same
problem in offline mode.

## Performance

A 1.7.10 server runs every dimension's world tick on one thread. Mobs, worldgen
and every player's chunks share it, so single-core speed decides how many players
it holds, and more cores do not help. When a host lists its CPU, pick a recent,
high-clock one, and ask before buying if it does not say.

**Measured on 2026-10-16** (Ryzen 9 7900X, 6 GB heap, no players, view distance 6):

| | |
|---|---|
| Boot | 49 s wall; Forge reports 19 s |
| Idle tick, all loaded dimensions | 0.9 ms; 1.5 ms after pregen (the budget is 50 ms) |
| Pregeneration | 185 chunks/s at `timepertick 250` |
| GC pauses | p50 0.08 ms, p99 29 ms, worst 152 ms (during pregen); no full GC |
| Live heap | about 2.6 GB |

That is the cost of the server itself, not of players. Fifteen players spread
across dimensions have not been measured. Use `forge tps` in the console to see
which dimension is slow.

**Settings that matter, and why they are set as they are:**

- **View distance 6.** Each player keeps (2r+1)² chunks loaded and ticking:
  169 at 6, 289 at 8. Clients cannot see further than the server sends.
- **JustAnotherSpawner** (`config/JustAnotherSpawner/GlobalProperties.cfg`):
  - Spawning and counting distance is 6, to match the view distance. JAS
    scales every mob cap by the chunks it counts ÷ 256, the same formula as
    vanilla. That gives 46 monsters per player instead of 79, at the same
    density per chunk.
  - If you change the view distance, change these two values with it. Counting
    8 on a server that loads 6 packs 79 monsters into 169 chunks. The build
    prints a warning if they disagree.
  - `Spawner Tick Spacing` 2: the spawner pass runs every third tick instead of
    every tick. Caps are unchanged; mobs refill a few seconds more slowly after
    a fight.
  - Per-spawn logging is off.
- **Already in config:**
  - ChickenChunks: `DEFAULT=49`, `allowoffline=false`.
  - TARDIS: `Dimension always loaded=false`.
  - CompactMachines: `chunkLoadingMode=2`.

**Pregenerate before anyone joins.** Generating new terrain is the most
expensive thing this pack does: dungeons, structures and dozens of dimensions.
Done live, it makes everyone lag when one person explores. ChunkPregenerator
radius is in chunks (blocks ÷ 16). For example, 3,000 blocks is 188 chunks,
about 142,000 chunks, about 13 minutes on the PC above:

```
pregen timepertick 250
pregen gen startradius square 0 0 188 0
```

Do this on your own PC before uploading the `world/` folder. It is faster than
most rented CPUs, and nobody is online to feel it. On a live server, leave
`timepertick` at its default and run `pregen setPlayerLimit 1`, which pauses
generation while anyone is online. There is no world border in 1.7.10, so
anyone who walks past the pregenerated area generates chunks live.

## What every friend needs

The exact client instance: the same mods folder, the same `config/`, and the
hand-patched Forge jar. Install from the client-instance release
(see [`../../pack/README.md`](../../pack/README.md)), not by assembling mods
yourself:

- A single differing jar version gets the client refused at login.
- A differing ID-bearing config gets it refused by the pack check, below.
  Before the check existed, such a client got in and then played with the
  wrong enchantments, potions or biomes.
- An install from before 2026-10-18 still has stock `CodeChickenCore.jar` and
  CodeChickenLib, and is kicked about 5 seconds after login. Swap them for GTNH
  CodeChickenCore 1.4.22 ("CodeChickenCore" above).
- A real account and a launcher that logs in ("Online mode" above).

Friends who are refused should read
[`why-was-i-refused.md`](why-was-i-refused.md).

## The pack check

Two checks keep a stale client out.

1. **Mod versions, at FML's handshake.** qf-content, qf-commands and
   qf-tweaks carry a version derived from git:
   `1.1.0+<date>.<sha8>` of the last commit that touched the mod's folder
   (`.dirty` if it was built with uncommitted changes). FML compares a shared
   mod's versions as exact strings, so a client with an older qf-content is
   refused with `Mod rejections [FMLMod:qfcontent{<server version>}]`. The jar file names stay
   `QuestForgeContent-1.0.0.jar` and so on, so an update overwrites the old jar.
2. **The pack fingerprint, right after login (qf-content).** The server asks
   each joining client for a hash of its ID-bearing configs and its mod list.
   It disconnects the client when the hash differs, or when a mod both sides
   have is at a different version. The message says which side is out of date
   (by `packDate`), names the files or mods that differ, and gives the
   `updateFrom` link. Each check is logged as `[packcheck] <name> OK` or
   `[packcheck] refusing <name>: ...`.

**What the fingerprint covers.** The configs listed in
`mods/qf-content/src/main/resources/qfcontent-packcheck.txt`. The list ships
inside the jar, so both sides use the same one. Today it has 22 files:
witchery, OreSpawn, TragicMC, qfcontent, thejungleMod, TwilightForest,
LegendsMod, InventoryPets, OpenBlocks, BiblioCraft, battlegear2, SSTOW,
railcraft, VoltzEngine, Lycanites general, chocolateQuest, TrailMix,
psychedelicraft, CompactMachines, CustomNpcs, HardcoreEnderExpansion and
TardisMod. Within those files, only the ID entries count: integer values whose
key has an ID token (`ID`, `Id`, `_id`) or names a potion, biome, enchantment,
dimension, villager, profession or provider, or that sit in a section that
does. Sections with "client" in their name are skipped. Comments, layout, line
endings (CRLF or LF), key order and every other setting are ignored, so a
config that differs only in a HUD option or in line endings still passes.

**Reading it.** `/qfpack` (anyone, any console) prints this side's fingerprint
and pack date, the qf-content version, the mod count and a digest of the mod
list. `/qfpack files` adds each config's digest. Without booting the game:

```
py -3.10 -I tools/pack_fingerprint.py                      # pack/config
py -3.10 -I tools/pack_fingerprint.py --config C:\qfs\friends\config --files
py -3.10 -I tools/pack_fingerprint.py --diff <a friend's config folder>
```

The script and the game compute the same value. If they ever disagree, the
two implementations have drifted (`PackFingerprint.java` and the script must
change together).

**When you change an ID-bearing config.** Run
`py -3.10 -I tools/pack_fingerprint.py --stamp` to set `packDate` in
`pack/config/qfcontent.cfg` to today. The date is not part of the hash; it is
how the message tells "your client is out of date" from "the server is". Then
rebuild the server and cut a client release from the same config. When a mod
that assigns IDs joins the pack, `--scan` lists every config with ID entries
that is neither fingerprinted nor reviewed, and exits 1 if there is one. Add
the file to the list.

**Emergency overrides** (`packcheck` in the server's `config/qfcontent.cfg`,
restart to apply):

| Key | Use |
|---|---|
| `alsoAccept` | Further client fingerprints to let in, e.g. last release's while friends update. Prefer this. |
| `expectedFingerprint` | Require this value instead of the one computed from the server's own configs. For a server whose files were rewritten in a way clients do not share. |
| `ignoreMods` | Mod IDs whose versions may differ. |
| `checkModVersions` | `false` compares configs only. |
| `enabled` | `false` turns the check off. |
| `updateFrom` | The link shown to refused players. |
| `answerTimeoutSeconds` | A client that has not answered by then is disconnected (default 60). |

Only a dedicated server checks. In singleplayer and on LAN, the client is the
server.

## Rules for the life of the world

- **Start a fresh world on the final mod set.** Removing or changing a mod
  mid-world deletes its items and entities. An old test world lost 63,000 item
  entities that way.
- **Never update the Transformers jar mid-world.** Its crafting-material IDs are
  assigned at first load and saved per world. A different jar silently turns
  one material into another.
- **Back the world up daily.** ProjectE, Archimedes Ships, Chest Transporter and
  Sync all have dupe or loss reputations in 1.7.10 that nobody has verified for
  these versions.
- **EnderStorage frequencies are shared.** Anyone who sets the same three
  colours opens the same inventory. Only diamond-locked ones are private.

## Found by playing on it, not by reading it

A scripted client joined this server on 2026-10-16 and exercised joining,
commands, a Sealed Tome, a soulbound item thrown into lava, death, respawn and
reopening the grave. Four problems never show up in singleplayer:

- **Every death disconnected every player.** GraveStones resyncs Baubles slots
  0–6 when there are only four, and each client crashes on "slot 4". Fixed by
  `GraveBaublesTransformer` in qf-tweaks. That is why qf-tweaks now runs on the
  server too.
- **Deaths were being cancelled.** Welcome to the Jungle's
  `Keep Special Items On Death` cancels every player death and re-implements it
  by hand, skipping Forge's drop handling. It is now `false` in
  `config/thejungleMod.cfg`. Ceremonial obsidian armour now goes to the grave
  like everything else.
- **Soulbound items burned to death on lava.** An item resting on a lava pool
  never counted as "in lava". Fixed in qf-content.
- **Offline-mode whitelisting** (see "Online mode").
- **ChickenChunks' chunk cleanup is hardened, defensively.** It walks the live
  loaded-chunk list while removing players from chunks they have left, so any
  mod that loads a chunk in response would end the session with a
  `ConcurrentModificationException`. The one crash seen came from a benchmark
  writing to the server from the wrong thread, so a real server may never hit
  it. `ChunkCleanTransformer` in qf-tweaks makes the loop walk a copy anyway.

Not covered by that test, because they need two people: voice chat, and
packets sent to bystanders.

## Known and accepted

- **Griefing is left on by choice:** ICBM antimatter breaks bedrock, OreSpawn
  bosses and MCHeli break blocks, Lucky Block and Pandora's Box do what they
  do, and Excavate, Timber and Tunneler ignore protection.
- **Two Legends crashes have no fix short of patching Legends:**
  `EntityLightningTrail` (speedster trails) and `EntityLightning` when damaged.
  If the server crashes in either, the crash report names them.
- **The `/dream_world` ticket is retired.** Leaving Witchery's Dream World twice
  crashed the server inside Railcraft. Entering it the normal way is still
  possible and has not been tested.
