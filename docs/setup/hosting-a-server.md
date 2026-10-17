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
  --ccl C:\qfs\tools\CodeChickenLib-patched.jar ^
  --out C:\qfs\friends --force
```

`--force` rebuilds an existing server and keeps its `world/`, `ops.json`,
`whitelist.json` and ban lists. Everything else is regenerated.

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
- **Swaps in the patched CodeChickenLib.** The stock one NPEs when a chunk
  unloads mid-generation. CCL has no `@Mod`, so the server may differ from
  clients here.
- **Writes play settings:** survival, Normal difficulty, whitelist on,
  `allow-flight=true` (otherwise vanilla kicks Transformers jets, Legends heroes
  and OreSpawn gliders after four seconds airborne), 15 players, view distance 6,
  online mode on. See "Performance" for why 6.
- **Writes `start.bat` and `start.sh`** with a 10 GB heap (`--xmx`) and GC
  logging to `logs/gc.log`.

## Run it

Double-click `start.bat` (Windows) or run `./start.sh` (Linux). It boots in
about a minute; the first boot also generates the world. Type `stop` in its
window to shut down. It saves. 1.7.10 has no watchdog, so a hung tick hangs
forever; if the console stops responding, check `logs/fml-server-latest.log`
before killing it.

On a rented host with a control panel (Pterodactyl and the like), the panel
starts the server itself. Choose **Java 8**, since Forge 1.7.10 does not start
on anything newer. Paste the JVM flags from `start.sh` into its startup field,
and upload the whole server folder over SFTP.

`online-mode` is `true` by default. Every player signs in with their own
Microsoft account, so names are proven. That rules out the offline
`TEST-LAUNCH.bat`: friends need a launcher that signs in, such as Prism.
Rebuild with `--online-mode false` only for a local test with offline-launched
clients. An offline server lets anyone join under any name, so the whitelist
filters names but does not prove identity.

**Adding players depends on that setting:**

- **Online mode (the default):** `whitelist add <name>` in the console.
- **Offline mode: do not use `whitelist add`.** It stores the UUID of whatever
  paid Mojang account has that name. An offline player is identified by a UUID
  derived from the name instead, so they are refused with "You are not
  white-listed". Pass each name to the build with `--player <name>`
  (repeatable; existing entries are kept), then run `whitelist reload` if the
  server is up.

Either way, `op <name>` makes someone an operator.

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
- A differing config value gets it in, then plays with the wrong enchantments,
  potions or biomes.

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
- **Offline-mode whitelisting** (see "Run it").
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
