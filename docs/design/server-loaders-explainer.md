# The loaders bundle, item by item

For the owner. Decision 0007 applied the whole bundle on 2026-10-25
(`tools/server/rules.json`, rebuilt into `C:\qfs\friends`). This says, for each
of the six items, what the setting is, what a player notices, what the server
gains, how sure we are, and the one line that reverts that item on its own.

How sure: **[measured]** a number read from this server or from the pack's own
config; **[estimate]** arithmetic from measured parts; **[guess]** mod
knowledge nobody has checked here.

**What we know about the cost of a loaded chunk.** With nobody online the
server ticks in 0.9 ms (1.5 ms after pregeneration) of its 50 ms budget
[measured, `hosting-a-server.md`]. A player at view distance 6 keeps 169
chunks loaded [measured: (2·6+1)²]. The cost of a chunk is not the chunk, it
is what is in it: mobs, machines, farms, dropped items. An empty loaded chunk
costs next to nothing [guess: never measured on this server]; a chunk with a
mob farm or twenty machines is where tick time goes. So every item below is
about chunks that would keep ticking with their owner gone, or about things
that multiply what a chunk costs.

**Reverting one item.** Change the line in `tools/server/rules.json`, rebuild
with the command at the top of that file, restart the server. Clients need
nothing. `forge tps` in the console and `!jfr` in the supervisor window
measure the difference afterwards (`hosting-a-server.md`, "Profile the first
real session").

## 1. Railcraft World Anchors cannot be crafted

- **The setting.** `railcraft.cfg` `anchors.craftable=false`. Personal and
  Passive Anchors stay craftable. Rule line: `"world_anchors": "off"`.
- **What a player loses.** The one loader that runs 24 hours a day with nobody
  online. A World Anchor keeps a 3x3 of chunks (9) loaded for 12 hours per
  ender pearl [measured: `world.fuel=minecraft:ender_pearl=12`]. Anchors
  already in the world keep working, and an op can still give one for a
  shared build.
- **What a player keeps.** ChickenChunks loaders: up to 49 chunks each, running
  only while you are online [measured: `ChickenChunks.cfg`]. Personal Anchors:
  a 3x3 on ender pearls, while you are online [measured fuel line; the
  online-only rule is Railcraft's, [guess] on its exact behaviour]. Passive
  Anchors: extend loading next to something already loaded [guess].
- **Benefit.** Nothing ticks while its owner is offline unless an op decided it
  should. With ten players and a few anchors each, ninety chunks of farms and
  machines running all night would be the first thing `opis_nent` and `!jfr`
  found [estimate]. Memory is not the question: a chunk is on the order of
  100 KB [guess]; anchors cost tick time.
- **Revert this item alone:** `"world_anchors": "off"` → `"capped"` (20
  anchors per world, enforced by Forge) or `"on"`.

## 2. Sync shells do not keep their chunk loaded

- **The setting.** `Sync.cfg` `allowChunkLoading=0`. Rule line:
  `"sync_shells": false`.
- **What a player loses.** A shell storage no longer holds its own chunk
  loaded while nobody is near. Syncing into a shell far away should still
  work: the server loads a chunk when something needs a block in it [guess:
  Sync's sync path was not read end to end].
- **The caution.** Sync's own comment on this option reads "Added by request,
  mod is made to chunkload shells. Untested, unsupported. Could crash your
  world fatally. Disable at own risk." [measured: the config]. Read from the
  jar: with the option off, Sync still takes a Forge chunk ticket and then
  empties it through reflection [measured: `ChunkLoadHandler` bytecode], so
  whatever risk there is sits in that code path. This is the least certain of
  the six. A two-player test before day one (die with a shell 2,000 blocks
  away, see whether you arrive) is the way to be sure; the revert is one line.
- **Benefit.** One chunk per shell, forever, for every shell anyone ever
  placed [estimate].
- **Revert this item alone:** `"sync_shells": false` → `true`.

## 3. The host's chunk loaders stop when he is offline

- **The setting.** `ChickenChunks.cfg` `allowoffline { OP=false }`. Players
  were already `DEFAULT=false`. Rule line: `"op_loaders_offline": false`.
- **What a player loses.** Nobody but you: this is about the op. You can still
  place loaders for up to 500 chunks (`players { OP=500 }`), but they stop
  when you log out, like everyone else's [measured: the config].
- **Benefit.** Before this, an op's loaders were the only unlimited, always-on
  loading in the pack: 500 chunks, all night [measured]. Same cost per chunk
  as item 1.
- **Revert this item alone:** `"op_loaders_offline": false` → `true`.

## 4. Chest Transporters cannot carry mob spawners

- **The setting.** `ChestTransporter.cfg` `pickupSpawners=false`, the master
  switch; the per-tier `spawnerWith*` lines stay `true` and do nothing without
  it [measured: the config's own comments]. Rule line:
  `"chest_transporter_spawners": false`.
- **What a player loses.** Building a mob farm out of dungeon spawners carried
  home. Spawners stay where the dungeons (Roguelike, Doomlike, Chocolate
  Quest) put them, and can be farmed there. Spawner XP farms at base are out.
- **Benefit.** A spawner tower under a chunk loader is the classic modded
  server's TPS sink: each spawner makes up to four mobs every 10-40 seconds
  while a player is within 16 blocks [guess: the vanilla rule], so ten of them
  produce entities faster than anything else in the pack, and entities are the
  biggest tick cost after chunks [estimate].
- **Revert this item alone:** `"chest_transporter_spawners": false` → `true`.

## 5. The Watch of Flowing Time gives no bonus from a pedestal

- **The setting.** `ProjectE.cfg` `timePedBonus=0` (mod default 18).
  `enableTimeWatch=true` stays; the pedestal still slows mobs around it
  (`timePedMobSlowness=0.1`) [measured: the config]. Rule line:
  `"projecte_time_watch_pedestal": 0`.
- **What a player loses.** Putting the watch in a Dark Matter Pedestal no
  longer makes the machines around it run faster. Held in hand, the watch's own
  effect is unchanged [guess: only the pedestal bonus is a setting].
- **Benefit.** 18 bonus ticks means every machine in the pedestal's range was
  updated 19 times per tick, permanently, for as long as its chunk was loaded:
  whatever those machines cost, times 19 [estimate from the config comment
  "Bonus ticks given by the Watch of Flowing Time while in the pedestal"].
- **Revert this item alone:** `"projecte_time_watch_pedestal": 0` → `18`, or
  any smaller number for a milder bonus.

## 6. Lycanites' random mob events start on day 3

- **The setting.** `lycanitesmobs-mobevents.cfg` `Random Mob Events Day
  Minimum Overworld (0)=3` (was 0). Events still run; between two random events
  the gap is 72,000 to 144,000 ticks, one to two in-game hours, which is 60 to
  120 real minutes [measured: the config]. Total world time is used, so
  `/time set` does not dodge it. Rule line: `"lycanites_first_event_day": 3`.
- **What a player loses.** No random event (Arachnophobia, Raptor Rampage,
  Boulder Dash and the rest) during the first three in-game days, one real
  hour. Scheduled events and the bosses are not touched. What is lost is an
  event landing on the first evening while everyone is at the hub with wooden
  tools.
- **Benefit.** An event spawns waves of extra mobs for its duration: dozens of
  entities on top of the normal cap [guess: never measured here]. On day 0 that
  is a TPS spike and a welcome nobody asked for; from day 3 it costs what it
  always did.
- **Revert this item alone:** `"lycanites_first_event_day": 3` → `0`.

## Not in the bundle, unchanged

- The ChickenChunks per-player cap (49 chunks, off when offline) was already
  set before the bundle.
- CompactMachines and TARDIS loading were fixed earlier (`server-readiness.md`
  4c).
- CustomNPCs' chunk-loading NPCs: untouched; NPC editing is ops-only anyway.
- Archimedes ships: a line in the rules post (decompile when parking), no
  setting.
