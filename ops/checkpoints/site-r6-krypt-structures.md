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
