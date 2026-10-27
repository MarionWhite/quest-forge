# site-r6-krypt-structures (checkpoint, started 2026-10-26, Mac)

Brief: research (agent: sonnet). Output: `docs/design/site/krypt-structures.md` only. No site code.
The jars are in `~/Library/Application Support/PrismLauncher/instances/Quest Forge/minecraft/mods/`.
Treat that game dir as read-only: copy jars into a new scratch dir before you unzip or javap them.

## Why
The owner wants the Krypt to hold up to 10,000 graves without repeating, drawing "on a lot of
the structure design from the mod pack". The krypt-gen task builds segments from your catalogue
(spec: `docs/design/site/krypt-endless.md`).

## Done means
- [ ] **At least 40 entries** across the pack's structure mods:
  - Doomlike Dungeons, Roguelike Dungeons, Chocolate Quest (its dungeon schematics and
    themes), Recurrent Complex (its structure files), The Twilight Forest (labyrinth,
    stronghold, hollow hills, lich tower, dark tower);
  - OreSpawn's dungeons, Lucky Blocks' structures, Hardcore Ender Expansion, Witchery,
    SecretRooms, Lycanites spawner rooms;
  - vanilla strongholds, mineshafts, fortresses, temples and dungeons.
- [ ] **Each entry:**
  - name, mod and source (class or file);
  - a layout sketch in words: size, rooms, corridors, levels;
  - signature blocks with their ids, the texture files they need (and in which jar) and the
    licence status;
  - signature features: traps, spawners, loot, light sources, liquids;
  - which mobs belong there;
  - mood, and the stratum it fits;
  - how to adapt it as a walk-through corridor segment, about 6 to 40 blocks long, with
    alcoves for graves.
- [ ] Grouped into 8 to 12 proposed strata in descending order, each with at least 5 entries.
- [ ] Where a mod ships schematic or structure files, list the paths, since krypt-gen may parse
  them directly.
- [ ] Report in five lines.

## Progress (agent log)
- Step 1 done: jars unzipped under scratchpad r6/structures/*/x; tools in r6/tools (schem.py = schematic histogram, rc2.py = .rcst reader).
  Harvested: Doomlike themes (res/themes/*.cfg), CQ schematics (stronghold rooms 15x10x15, castles, ships, pigcity, villages),
  Recurrent Complex 60+ .rcst (zip: structure.json + worldData.nbt), Roguelike themes/rooms/segments (javap), TF structure class list.
- Next: HEE, Witchery, OreSpawn, Lycanites, SecretRooms, Lucky, vanilla; then write docs/design/site/krypt-structures.md (commit partial at 10+ entries).
- Step 2 done: harvested HEE, Witchery, OreSpawn, Lycanites, Lucky, SecretRooms, TF class lists. Wrote partial doc (outline, texture-source table, strata 1-2 first 12 entries) and committed.
- Next: finish strata 2-12 (strata table entry ranges must be fixed to the final numbering at the end), then final commit.
- Step 3 done: entries 1-35 written and committed. Next: strata 6-12 (36+), fix strata table ranges, final commit.
- Step 4 done: entries 36-56 (Twilight, CQ) committed. Next: S9 arcane (57-64), S10 nether (65-71), S11 end (72-77), S12 beyond (78-84); fix strata table, final commit.
- DONE: all 84 entries, 12 strata, gaps/params/licence sections written; final commit made.
