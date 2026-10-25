# r14 — The difficulty mechanism (tier grid + qf-content hook)

**Status:** built 2026-10-25 and tested on a server trial. It ships **inert**: every multiplier
defaults to 1.0, so a world with the grid plays exactly like one without it. The only rule that
acts by default is the author's decision to keep Lycanites event spawns out of the spawn pockets.
The numbers get tuned later, after the census and the tests in the
[proposal](difficulty-enforcement-proposal.md) §7. Balance changes need the author's yes.

The mechanism follows the approved hybrid (proposal §3, with the author's decisions of
2026-10-25). The biome still picks the mob family through JAS. The map position picks the tier,
and the tier decides how many mobs spawn and how strong they are.

## Pieces

| Piece | Where |
|---|---|
| Spec (tiers, hot zones, spawn pockets) | [`difficulty.yaml`](difficulty.yaml); design in [`difficulty.md`](difficulty.md) |
| Bake | `tools/world/difficulty.py --bake OUT` |
| Baked grid for the r13 plan | [`qf-tiers-r13.bin.gz`](qf-tiers-r13.bin.gz) (51 KB; 9.4 MB unpacked) |
| Hook | qf-content, package `com.questforge.content.difficulty` |
| Config | `config/qfcontent-difficulty.cfg` (written with defaults on first world load) |
| Test command | `/qfdifficulty` |

There is **no T1**. The tiers run from T2 to T6. The spawn pockets are T2 and small: T2 within
500 blocks of a spawn, then a ramp. T2 reads out to about 650 blocks, and T3 resumes there. That
is 1.3% of the land. Beyond the grid, the RWG outskirts start at T6 and keep rising with distance.

## Baking the grid

```
py -3.10 tools/world/plan.py render docs/design/world/r13/main.yaml PLAN --px 32
py -3.10 tools/world/difficulty.py PLAN docs/design/world/r14/difficulty.yaml --bake qf-tiers-r13.bin.gz
py -3.10 tools/world/difficulty.py --read-grid qf-tiers-r13.bin.gz --at 1400 5800 --at -8520 -150
```

The bake samples the continuous difficulty at every chunk centre with bilinear interpolation, so
one 32-block plan pixel does not show up as a 2×2 block of chunks. It rounds to a tier between 2
and 5 and marks the "beyond" sea as T6. A name ending in `.gz` gets gzipped deterministically
(mtime 0). `--read-grid` checks the CRC, prints the header and the chunk count per tier, and looks
up points.

The r13 grid: 3,072 × 3,072 chunks from chunk (−1536, −1536), so blocks ±24,576. By chunk count it
is T2 0.5%, T3 35.4%, T4 34.8%, T5 9.0% and T6 20.2% (sea included).

## File format (version 1)

Big-endian, so Java's `DataInputStream` reads it directly. The whole file may be gzipped, and the
mod checks the first two bytes to tell.

| Offset | Type | Field |
|---:|---|---|
| 0 | 4 bytes | magic `QFTG` |
| 4 | u16 | version (1) |
| 6 | u16 | header length in bytes (64); data starts here |
| 8 | i32 | origin chunk x (chunk of column 0) |
| 12 | i32 | origin chunk z (chunk of row 0) |
| 16 | i32 | width in chunks (along x) |
| 20 | i32 | height in chunks (along z) |
| 24 | u8 | min tier in the data (2) |
| 25 | u8 | max tier in the data (6) |
| 26 | u8 | tier just outside the grid (6) |
| 27 | u8 | reserved (0) |
| 28 | u32 | CRC-32 of the data |
| 32 | 32 bytes | SHA-256 of the `difficulty.yaml` it was baked from |
| 64 | width × height bytes | tier per chunk, row-major: chunk (cx, cz) is at `(cz − z0) × width + (cx − x0)` |

The mod refuses a file with a bad magic number, an unknown version, an implausible size or a CRC
mismatch, and logs why. A wrong grid is worse than none.

## Enabling it in a world

1. Copy the baked file into the world as **`<world>/data/qf-tiers.bin`**. The gzipped file can be
   copied as it is, just renamed.
2. Start the server. The log (`fml-server-latest.log`, logger `qfcontent`) shows
   `[difficulty] tier grid 3072x3072 chunks ... every tier at defaults (no change to play)`.
   With no file it shows `[difficulty] no tier grid at ...; difficulty tiers inactive`, and every
   hook returns on its first line.
3. Stand somewhere and run `/qfdifficulty`.

The grid belongs to the world, not the pack. Census nodes, trial worlds and today's test worlds
carry no grid, so nothing changes for them. Only the overworld uses it (`dimensions`). Nothing is
sent to clients. The server keeps the grid as a 9.4 MB `byte[]`, and a lookup is one array read.

## How a mob gets its tier

- **When:** the first time a hostile mob joins the world (`EntityJoinWorldEvent`, LOWEST, after
  InfernalMobs' roll). This covers every spawn path: JAS, vanilla, Lycanites' own spawners and
  events, dungeon spawners, eggs and `/summon`.
- **Stored as:** the tier goes into the mob's ForgeData as `qfTier`, and the source as `qfTierHow`
  (`grid`, `cave`, `outskirts`, `outskirts_cave` or `cage`). A T5 mob that chases someone into a
  pocket stays T5, and a reloaded chunk never rescales anything.
- **Which mobs:** "hostile" means `IMob`, or a mob that reports itself as `EnumCreatureType.monster`.
  That second test is how Lycanites marks its hostile mobs.
- **Never tiered:**
  - bosses: anything with a boss bar (`IBossDisplayData`), Lycanites `isBoss()`, or a name on the
    `bosses` list (by default the campaign's boss list);
  - owned or tamed mobs (`IEntityOwnable` with an owner);
  - names on the `exclude` list.
- **Lookup:** the grid tier of the chunk. Outside the grid, the tier is `6 + floor(distance from
  the grid edge / outskirtsStep)`, capped at `maxTier`.
- **Caves:** a spot with no sky access that lies at least `caveDepth` blocks under its column's top
  solid block counts `caveBonus` tiers harder, capped at `maxTier`. The depth margin keeps the shade
  of a tree or an overhang from counting as a cave.
- **Soul Shards cages:** cage mobs carry ForgeData `SSTOW = true`. `TileEntityCage` sets it before
  `spawnEntityInWorld`, as the bytecode of the pack's jar shows. They are always `cageTier` (T3),
  wherever the cage stands. Soul Shards is the pack's only player-made spawner.
- **Natural world spawners:** dungeon spawners and the like use the tier of the place they stand
  in, which is the default.

## Config keys (`config/qfcontent-difficulty.cfg`)

`general`:

| Key | Default | Meaning |
|---|---|---|
| `enabled` | true | Master switch. With false, nothing happens even with a grid. |
| `gridFile` | `data/qf-tiers.bin` | Grid path, relative to the world folder. |
| `dimensions` | 0 | Dimensions the grid applies to. |
| `maxTier` | 8 | Highest tier. Tiers above 6 occur only in the outskirts and in caves under T6 or higher. |
| `outskirtsStep` | 4000 | Blocks beyond the grid edge per extra tier. 0 means a flat T6. |
| `caveBonus` | 1 | Tiers added in caves. |
| `caveDepth` | 4 | Blocks under the column's top solid block before a spot counts as a cave. |
| `cageTier` | 3 | Tier of every Soul Shards cage mob. |
| `pocketMaxTier` | 2 | Grid tier at or below which a spot counts as a spawn pocket. |
| `suppressLycanitesEventsInPockets` | **true** | Refuse Lycanites event spawns in the pockets (the author's decision). |
| `bosses` | the campaign's boss list | Entity names never tiered (on top of boss-bar mobs and Lycanites bosses). |
| `exclude` | empty | More entity names never tiered. |
| `debugLog` | false | Log every decision: stamps, refused spawns and scaled hits. |

`tier2` … `tier8`. Each key's comment gives the proposal's starting number, but **none is
applied**:

| Key | Default | Meaning | Proposed (comment only) |
|---|---|---|---|
| `spawnKeep` | 1.0 | Share of natural spawn attempts kept (Forge `CheckSpawn` DENY on the rest) | T2 0.66; or 0.55 with the JAS MONSTER cap raised to 84, which puts T3 at 0.83 |
| `health` | 1.0 | Max-health multiplier: an attribute modifier, operator 2 (multiply total), fixed UUID | T2 0.7, T4 1.5, T5 2.2, T6 3.0 |
| `damage` | 1.0 | Multiplier on damage the mob deals: melee, projectiles and explosions (`LivingHurtEvent`, HIGH) | T2 0.8, T4 1.3, T5 1.7, T6 2.2 |
| `eliteOdds` | 1.0 | Multiplier on InfernalMobs' elite chance (1 in `eliteRarity`, 15 in the pack) | T2 0.45, T4 1.5, T5 2.25, T6 3.3 |
| `xp` | 1.0 | Multiplier on `experienceValue` | T2 0.8, T4 1.5, T5 2.0, T6 3.0 |
| `speed` | 1.0 | Movement-speed multiplier (operator 2). The author's rule: T6 only | T6: no number yet; try 1.15 |
| `armourIgnore` | 0 | Share of the mob's damage that goes straight to health, past armour (`LivingHurtEvent`, LOWEST) | T6 0.2; test it first |

### Tuning

- Edit the cfg, then run `/qfdifficulty reload` as an op. Both files are read again. **New** spawns
  use the new numbers at once.
- Health and speed are re-applied each time a mob joins. Tuning those also reaches mobs that are
  already saved, the next time their chunk loads.
- Elite odds and the spawn-keep share act only at spawn time.
- Health and speed compose **after** MobProperties' operator-1 boost. MobProperties sets health to
  `max − damage taken` once its queue runs, so a fresh mob ends at full scaled health.
- Under the balance rule, numbers move only with the author's yes, and gear and combat wait for
  the enchant census.

## The other mods

- **InfernalMobs:** clean, using its public API only.
  - To lower the odds, the hook demotes a fresh elite with probability `1 − eliteOdds`. It calls
    `removeEntFromElites` and removes the mob's IM NBT tag. The modifiers do nothing else until
    their first tick, so this is a clean undo.
  - To raise the odds, it makes further rolls through IM's own `processEntitySpawn`, which keeps
    IM's class lists. That is k full rolls plus one partial roll, chosen so the total chance comes
    out exactly `eliteOdds / eliteRarity`.
  - `eliteRarity` is read from IM's public `config`.
  - **Not done:** ultra and infernal shares by tier. A promoted elite gets IM's global 1/7 and 1/49,
    because those rolls are private to IM (`createMobModifiers`).
- **Lycanites 1.13.0.5 events:** clean, but they are refused at spawn time, not at event start.
  - Lycanites sets the public field `spawnedFromType` (whose `mobEvent` is non-null for event
    spawners) before Forge's `CheckSpawn`, and `spawnEventType` before `spawnEntityInWorld`.
  - The hook refuses an event spawn inside a pocket at `CheckSpawn` and again at the join event.
    The join check matters because event spawners can set `forceSpawning`, which ignores a DENY.
  - **Not done:** stopping the event itself. Lycanites events are world-wide (`MobEventServer`),
    so the event still runs and is announced, and players outside the pockets still meet it. There
    is no per-player or per-position API to stop the start cleanly.
- **Soul Shards:** clean, through the `SSTOW` tag (see above).

## Test results (server trial `qfdiff`, 2026-10-25)

**Trial setup:**
- `trial.py build qfdiff --server qfcontent lycanites infernalmobs soulshards --jar <built jar>
  --seed 1425`, plus the base set.
- Jar `QuestForgeContent-1.0.0.jar` from this commit.
- `guard` was OK before the work. No client was launched and nothing was installed live.
- Probes ran from a console commands file using `/qfdifficulty test …` (op-only). They spawn
  through `spawnEntityInWorld`, fire Forge's `CheckSpawn` the way JAS does, and hit through
  `attackEntityFrom`.
- Places used:
  - T2: the central-lowlands pocket, (1392, 5792);
  - T3: (912, 5312);
  - T4: (2112, 8784);
  - T5: (8768, 5792);
  - T6: (768, 22016);
  - outskirts: x = 26000 and 33000;
  - caves: y 12 under the T4 and T6 spots.
- Skeletons are the probe mob because, unlike zombies, they roll no random health bonus.

**Run A: no grid file.**
- The log says `no tier grid ... inactive`.
- `/qfdifficulty` reports inactive.
- 600 skeletons per place: no stamps, health and speed ratio 1.000, XP 5. Elites were 5.2–7.8%,
  which is IM's own 1 in 15.
- `CheckSpawn`: 4000 of 4000 allowed.
- Hits: 10 → 10.0 on an unarmoured villager and 2.0 on a villager in diamond armour.
- A Jabberwock carrying an event mark joined in the pocket.

**Run B: grid, default config.**
- The log says `every tier at defaults (no change to play)`.
- Stamps were right everywhere: T2 / T3 / T4 / T5 / T6 by grid, T4 → T5 in a cave, T6 → T7 in a
  cave, T6 at x 26000, T8 at x 33000 (cave capped at T8), and the SSTOW-tagged mobs at a T5 spot
  stamped **T3/cage**. WitherBoss and Rahovart got no stamp.
- Every ratio stayed 1.000 and XP stayed 5. Elites were 5.3–8.5% (unchanged), `CheckSpawn` allowed
  4000 of 4000, and the hits were unchanged (10.0 and 2.0).
- The only difference from run A is the default event rule. The Jabberwock with the
  `boulderdash` mark was refused in the pocket (`CheckSpawn` DENY, did not join) and joined at T3.

**Run C: grid, test config.** The test values were not proposals. Health ×0.5 / 1.5 / 2.0 / 2.5 /
3.0 / 3.5 / 4.0 for T2 to T8, with damage and XP equal to health. T2 had keep 0.5 and elites ×0.
Elites were ×2 / ×3 / ×4 for T4 / T5 / T6. Speed was ×1.2 / 1.3 / 1.4 and armourIgnore 0.5 for
T6 to T8.

| Place | Stamp | maxHealth / base | speed / base | XP (base 5) | Elites (expected) |
|---|---|---:|---:|---:|---:|
| T2 pocket | T2/grid | 0.500 | 1.000 | 2.50 | 0.0% (0%) |
| T3 | T3/grid | 1.500 | 1.000 | 7.51 | 7.2% (6.7%) |
| T4 | T4/grid | 2.000 | 1.000 | 10.00 | 15.5% (13.3%) |
| T5 | T5/grid | 2.500 | 1.000 | 12.49 | 18.2% (20.0%) |
| T6 | T6/grid | 3.000 | 1.200 | 15.00 | 24.0% (26.7%) |
| T4 spot, y 12 (cave) | T5/cave | 2.500 | 1.000 | 12.48 | — |
| T6 spot, y 12 (cave) | T7/cave | 3.500 | 1.300 | 17.38 | — |
| x 33000 (8,424 blocks out) | T8/outskirts | 4.000 | 1.400 | 20.00 | — |
| T5 spot, SSTOW tag (cage) | **T3/cage** | 1.500 | 1.000 | 7.38 | — |
| WitherBoss, Rahovart at T6 | none | 1.000 | 1.000 | 50 / 1000 | 0 |

The surface rows used 600 mobs each, so an elite share has a standard error of about 1.5 points.
Every elite share is within 1.6 standard errors of its target. The cave, outskirts and cage rows
used 50 mobs each.

More from run C:
- **`CheckSpawn` thinning:** T2 kept 2021 of 4000 (0.505, against 0.5). T3 kept 4000 of 4000.
- **Hits** (10 damage from a fresh, non-elite zombie):

  | Attacker | Unarmoured villager lost | Villager in diamond armour (20) lost |
  |---|---:|---:|
  | T3 | 15.0 | 3.0 |
  | T4 | 20.0 | — |
  | T6 | 30.0 | **18.0** |

  The T6 armoured hit is the 15 that ignores armour, plus 15 × 0.2 that gets through. The debug
  log shows `10.0 x3.0 = 30.0`, then `15.0 ignores armour, 15.0 left to armour`.
- **`/qfdifficulty`** reported every place correctly, for example
  `Tier T7 (cave, grid T6) at (769, 13, 22017)` and `Tier T8 (outskirts, outside the grid) at (33001, 121, 1)`.

**Not covered:**
- **A real Soul Shards cage.** The pack's Soul Shards config requires a player nearby at every
  tier, and a headless trial has none. A cage placed with `/setblock` and NBT also came up with
  metadata 0, which means "no shard", so it never ran. The detection rests on the `SSTOW` tag,
  which is confirmed in the jar's bytecode and exercised by the tagged probe above.
- **Natural spawning and a real Lycanites event.** Both run only around players. The probes fire
  the same `CheckSpawn` call and set the same field Lycanites sets.
- **MobProperties composition** (proposal §7.4). MobProperties was not in this trial.
- **JAS's own spawn cycle.** JAS calls `canEntitySpawn`, which is the path the probe used.

## Limits and notes

- **Spawn thinning** works only on spawners that fire `CheckSpawn` and honour a DENY: JAS, vanilla
  natural spawning, and the Lycanites custom spawners that do not set `forceSpawning`. Other spawns
  are tiered but not thinned.
- **XP** scales `EntityLiving.experienceValue`. A mod that overrides `getExperiencePoints` without
  using that field is not scaled. Vanilla drops XP only for player kills, but a FakePlayer kill
  counts as one.
- **Damage** scaling applies to whatever a tiered mob hits, including pets and other mobs.
- **Existing worlds:** a mob saved before the grid was added gets its tier the next time its chunk
  loads, from where it stands then.
- **Spawn ratings:** the picker's rating labels in [`difficulty.md`](difficulty.md) were
  calibrated for the old T1/T2 pockets, and they need new cut-offs.
- **Out of scope:** the JAS spawn-table rebuild for BoP biome names is a separate job.
- **Debugging:** the `/qfdifficulty test spawn|checkspawn|event|hurt` probes are op-only and remove
  what they spawn. They are left in for the tuning measurements.
