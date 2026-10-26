# The endless Krypt (design spec, 2026-10-26)

The owner wants the Krypt "long enough to hold 1000 graves if not 10x that", built out now and
then extended with each death. He wants the dungeon's quality driven up, repeats avoided as long
as possible, and the structure design of the pack's mods drawn on. He loves the scroll feel, the
stone focus and the lights brightening with depth, so none of those may regress.

## Capacity and order
- **At least 10,000 graves.** The layout is generated deterministically from a seed and the grave
  index, and streamed as you walk. Only the segments near the camera exist, and the ones behind
  are disposed. Memory and draw calls stay flat whether there are 25 graves or 10,000.
- **Chronological.** The first death sits at the entrance, and each new death extends the
  dungeon at the deep end. Adding a death never moves an existing grave. A grave's position is
  a pure function of its index and the seed.
- **Demo data:** `?demo` (25 graves, as now), `?demo=1000` and `?demo=10000` generate
  synthetic graves from a seeded name and cause list.

## Strata, so that depth means something
- The path descends through themed strata, each a band of a few hundred graves with its own
  palette, segment pool, light table, ambience bed and fog.
- The order runs from shallow crypts to the depths. Examples:
  - stone crypts and mines;
  - catacombs and ossuaries;
  - flooded and drowned halls;
  - jungle and temple ruins;
  - the Twilight Forest's labyrinth and its stronghold;
  - Chocolate Quest and Roguelike dungeon halls;
  - the nether;
  - Hardcore Ender Expansion's end, past the end portal.
- After the last stratum it cycles with new variation; it never stops.
- The owner's rule holds throughout: lights brighten and warm as you go deeper within a
  stratum, and each stratum has its own character.

## Segment library
- At least 40 segment kinds, drawn from the catalogue in `docs/design/site/krypt-structures.md`.
  That catalogue covers the pack's dungeon mods (Doomlike Dungeons, Roguelike Dungeons,
  Chocolate Quest, Recurrent Complex, Twilight Forest, OreSpawn, Lucky Blocks, Hardcore Ender
  Expansion, Witchery, SecretRooms) plus vanilla structures.
- Every kind takes parameters (length, width, height, dressing seed, damage, light colour) so
  two of the same kind still differ.
- A kind never repeats within its stratum's last 12 segments, or the last 6 overall when the
  pool is small. Repeats are allowed only when nothing else fits.
- Licences: block textures follow the open owner decision on game assets (`ops/DECISIONS.md`,
  Site). Vanilla and OreSpawn are already in use. Note any other mod's textures in the
  catalogue so they can be swapped or dropped.

## Corners and gaps
- Some bends have a 2 to 3 block gap of lava or water where the path breaks; the owner
  noticed these.
- Walking across a gap plays a jump: the camera crouches slightly, then arcs over with the step
  sounds, lands with a dip, and plays the landing sound.
- Before each jump, the Krypt fires `krypt-gap` (a CustomEvent on window). The detail is
  `{ gap, takeover() }`. If a listener calls `takeover()`, the jump is theirs to animate; the
  scares use this for the failed-jump deaths. If nobody takes over, the normal jump plays.

## Navigation at 10,000 graves
- A depth gauge shows the stratum name and the grave number.
- "Find a grave" takes a name and descends to that grave with a fast, smooth transition (a
  blur or fog rush down the path), never a hard cut.
- Page Down jumps to the next stratum and Page Up to the previous one.
- The click focus and passing focus on stones work as now.
- Hooks: `?grave=N`, `?at=0..1` (fraction of the whole path) and `?stratum=k`.

## The `window.__krypt` contract
Everything below is in addition to the existing fields; keep those.
- `getWalk()` also returns `stratum` (an index) and `stratumName`.
- `corners` holds the corners near the walker (within ±150 blocks), refreshed as segments
  stream. `cornersNear(s, range)` gives the same for any range.
- `gaps` holds the gaps near the walker: `[{ s, pos, dir, width, kind: 'lava' | 'water', side }]`.
- `light` controls the lights. The mood layer and the scares use it; every effect eases and
  ends restored.
  - `light.scale(k, seconds)` scales every light.
  - `light.flicker(pos, seconds)` flickers the nearest torch.
  - `light.off(pos, seconds)` snuffs that torch, which relights after `seconds`.
  - `light.pulse(seconds)` dims all lights once and brings them back.
- `carve`, `restore`, `solidAt` and `blockAt` stay. Fix the two follow-ups the scares filed:
  clamp dt at 0 in `frameInner`, and build chunks around the camera while a scare holds the
  player.
