# Lucky Block page data

The Lucky Block page (`site/lucky/`) reads two generated files:

- `site/lucky/data/lucky.json`: every drop of the pack's table, with a title, blurb, mood, scene,
  reel tile and an ordered list of actions. Contract version 2 (see below).
- `site/lucky/data/structures.json`: the hard-coded structures the mod places (anvil trap, fort,
  temple, chests, wishing well, and so on), as voxel lists recovered from the mod's bytecode.

Both come from `tools/site/build_lucky.py`, which reads
`pack/config/lucky/LuckyBlockProperties.txt` and `site/items/data/items.json` (names and icons).

## Running it

    python3 -I tools/site/build_lucky.py           # write lucky.json and structures.json
    python3 -I tools/site/build_lucky.py --check   # rebuild in memory and assert the contract
    python3 -I tools/site/build_lucky.py --dump    # print lucky.json to stdout, write nothing
    python3 -I tools/site/check_fresh.py           # the lucky area must report fresh afterwards

`tools/items/refresh.py` runs the plain form. `check_fresh.py` calls the lucky area stale when the
config or this script is committed or edited after `lucky.json`, so rebuild after any change.

## How the parser follows the mod

The parser copies the mod's own steps (LuckyBlocks 5.1.0, `mod.lucky.util.MakeLuckyDrops`,
`LuckyFunction.splitBracketString`, `ChooseLuckyDrop`):

- A line is split on `;` and `,` only at bracket depth 0 and outside double quotes. A quote
  preceded by a backslash does not toggle the quote state.
- `group(...)` takes the text between the first `(` and the **last** `)` of the line. Anything
  after that `)` (a trailing `;`, `>`) is ignored, as in the mod.
- `group:N(...)` and `group:#random-a-b(...)` pick N members (or a random count in a-b) uniformly,
  without weights. These become `choice` actions. A bare `group(...)` runs every member in order.
  A nested group counts as one member when a pick is applied, and expands in place otherwise.
- `type=difficulty` is a precondition the mod runs before spawning mobs. It never becomes an
  action.
- A line with no `group` prefix is one drop. `type=quartz_block` is a type the mod does not know,
  so that member spawns nothing.
- Lines the mod cannot read become `skipped` entries. The mod throws
  `StringIndexOutOfBoundsException` at harvest when a `group(` has no `)`; the block then reports
  an error and drops nothing. Three such lines exist (config lines 529, 539, 541). Their weight
  still counts in the odds, as it does in the game.
- Line 531 has one `)`, which closes its nested group, so the outer `group:1(...)` is read. The
  nested group is unclosed, so that option is broken: it errors when chosen. It is kept as a drop
  with `"broken": true` and an empty option.
- Nested lucky blocks (`NBTTag=(Drops=["..."])`) become a `then` action after the block, with the
  inner table parsed by the same grammar.
- Colour codes `#x` become `§x`. `#playerName` becomes `{player}`. Messages are broadcast with
  `sendChatMsg` in the mod, so they carry `"to":"all"`.

Numeric ids are resolved through a small 1.7.10 table (97, 147, 349, 382, 383, 384, 2256–2267).
Random item ranges (`#random-1-500`, `#random-4249-4362`, `#random-349-350`,
`#random-2256-2267`) become `{"id":"random"}` with a name and no icon.

## The weight formula

Verified against `ChooseLuckyDrop.chooseDrop` in the jar. For block luck K (clamped to ±100),
with `Lmin = min(0, lowest @luck)` and `Lmax = max(0, highest @luck)` over the whole table:

    b      = 1 / (1 - 0.0077 * |K|)
    e      = L - Lmin + 1      when K >= 0
           = Lmax - L + 1      when K < 0
    weight = chance * 100 * b^e
    P      = weight / sum of weights

At K = 0 every drop's weight is `chance * 100`. `odds` on each drop gives P at K = 0, 100 and
-100; the skipped lines are included in the sums, since the game picks them too.

## Contract version 2

Top level: `version`, `contract` (2), `source`, `built`, `spawnrate`, `structureChance`, `recipe`,
`luck`, `craftingItems`, `scenes`, `moods`, `counts`, `drops`, `skipped`, `structures`.

Each drop has `index` (for `?force=`), `line` (the config line, the key for the hand-written text),
`luck`, `chance`, `raw`, `group` (the `/` comment above it), `title`, `blurb`, `mood`, `scene`,
`icon`, `tile`, `actions`, `odds`, and `broken` when an option cannot run in game.

Scene keys and mood keys are listed in the `scenes` and `moods` arrays. Action types are the
contract's list plus `time` and `particle`.

Fields added to the version 1 vocabulary (all optional, the engine falls back when absent):

- `drop.line`, `drop.group`, `drop.broken`, `drop.odds`
- `skipped[]`: `line`, `group`, `luck`, `chance`, `reason`, `raw`, `odds`
- `item`: `damage`, `offset`, `enchSet` (an enchantment set name, not resolved)
- `entity`: `offset`, `equipment` (item ids), `spreadRange` (the scatter range when `spread` is its
  maximum), `lift` (adjustHeight), `reinit`
- `falling` and `block` blocks: `rand` = `{"dx":[lo,hi],...}` when the config uses `#random` in
  posX/posY/posZ; the plain `dx,dy,dz` is then the midpoint. `origin` is `player` or `block`.
- `effect`: `level` and `duration` may be `[lo,hi]` for random effects.
- `message`: `to` = `"all"`.
- `command`: `gives` is parsed from `/give`.
- `then`: `label` is always "Break the hidden lucky block" in this table.

## Structures

`structures.json` is written from `build_structures()` in this file, which holds the voxel data
recovered from `mod.lucky.util.CustomStructures` and `StructureUtil` (javap of
`LuckyBlocks.jar`). See the notes on each structure for what the bytecode did not show.
