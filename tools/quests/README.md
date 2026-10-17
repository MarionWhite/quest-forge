# `quests/` — the quest book toolkit

`qb.py` loads, checks and edits the BetterQuesting book (`DefaultQuests.json`). It replaces the
scripts in `../pack-fixes/quests/`, which hard-code a macOS PrismLauncher path and cannot be
re-run. The plan it serves is [`../../docs/design/questline-audit.md`](../../docs/design/questline-audit.md).

```
py -3.10 -I tools/quests/qb.py check               # every check, both books; exit 1 on any error
py -3.10 -I tools/quests/qb.py tally               # reward totals per tab, and what is ungated
py -3.10 -I tools/quests/qb.py dump --out dump.txt # one readable line per task and reward
py -3.10 -I tools/quests/qb.py show 63             # one quest as JSON
py -3.10 -I tools/quests/qb.py diff                # where the pack and server books differ
py -3.10 -I tools/quests/qb.py registry --save "%APPDATA%\.crazycraft4\saves\Stress Test\level.dat"
```

Use `py -3.10 -I`. The default `python` on this PC is a different install.

## Two books

| Book | Path | What it is |
|---|---|---|
| `pack` | `pack/config/betterquesting/DefaultQuests.json` | The shipped book. Written with `§` escapes. |
| `server` | `server/config/betterquesting/DefaultQuests.json` | The survey server's book. It is **older**: it still has the HBM chapter (148, 149, 155, 410–415) and lacks the ChocolateQuest quests (440–444), because that server runs HBM (`../../server/README.md`). Written with raw UTF-8. |

Every quest edit goes into both. `qb.load()` refuses a file it cannot write back byte for byte,
and `save()` keeps each file's escaping, so a save that changes nothing changes no bytes.
The `ids` check skips the `hbm:` namespace in the server book only.

## The checks

| Check | Fails on |
|---|---|
| `lint` | duplicate quest ids, a prerequisite that does not exist, a cycle, a quest in zero or two lines, a line without a unique `order:3`, Secrets not last, an unknown `§` code. Warns on a tab name over 14 characters (GuiHome clips it). |
| `ids` | an item id that is not in `registry.json` (exact, case-sensitive), and anything on the blocklist below. |
| `cheese` | one claim of a quest's reward (all item rewards plus any single choice option) fully completes a quest it unlocks. Warns when it completes a quest that is not upstream of it. Quests that ask only for a Lucky Block, loot bag or tome are reward tutorials and are skipped. |
| `stack` | a retrieval task asking for more than one of an unstackable item (swords, armour, tools, by name). Warns on such rewards. |
| `text` | `a` before a vowel ("a Anvil"), "Beastiary" for the tab (the Lycanites GUI is spelled that way, so "Lycanites' Beastiary" is allowed), placeholder words, `..`. |

**Blocklist** (`BLOCKLIST` in `qb.py`): `TragicMC:swordOfJustice`, `TragicMC:bowOfJustice`
and `witchery:infinityegg` (creative-tab items), `betterquesting:placeholder`, and
`minecraft:command_block`; as tasks also `minecraft:mob_spawner`, `bedrock` and
`end_portal_frame`, which survival cannot produce. `levelup:*` is blocked automatically
while `pack/config/levelup.cfg` disables the Level Up items, because a disabled item is not
registered and BQ quietly turns it into a placeholder.

`check` reads names only. Damage values are not in the registry, so a wrong meta (the
Railcraft Smoker that should have been a Firebox) still needs the mod's own enum or lang.

## `tally`

Two numbers per cell: **guaranteed** (item rewards) / **best case** (plus the largest choice
option of that kind). Columns: Lucky Blocks, loot bags `bag0`–`bag4` (Common → Legendary),
sealed tomes `tome0`–`tome4`, diamonds, diamond blocks, golden apples, nether stars.

**Ungated** means no boss quest is upstream: neither the quest nor any prerequisite is in
`BOSS_QUESTS` (Twilight bosses, the three OreSpawn titans, Rahovart), and its task does not
ask for a boss quest's proof item. It is the faucet a fresh player can drink from.

## The registry

`registry.json` is the item and block list Forge saves in every world's `level.dat`
(`FML → ItemData`). The committed copy comes from `saves/Stress Test` (2026-10-16, 141 mod
ids). Rebuild it with `qb.py registry --save …` from a world last opened with the current mod
list; it only reads the save. Do not use `Tryhard Run`: it still has HBM and lacks 39 newer
mods.

## Editing

The audit recommends authoring new quests in BQ's own editor (`/bq_admin edit`, then
`/bq_admin default save`), so new task types get exactly the typed keys BQ writes. For edits
to existing stacks and text, a script is safer and repeatable:

```python
import qb
for book in qb.books_for('all'):
    log = qb.Log(book)
    qb.replace_reward(log, book.quest(24), 'OreSpawn:OreSpawn_QueenScale', None, count=4)
    book.save()
```

The helpers (`replace_reward`, `replace_task_item`, `set_icon`, `edit_text`,
`rewrite_text`) check the state they expect and report "already" when the edit is in, so a
patch can be re-run. `patches/` holds the applied work packages:

| Patch | Work package |
|---|---|
| `patches/wp1_hotfixes.py` | WP-1: broken quests, creative rewards, Twilight proofs, cheese pairs, text, `pack_version` |
| `patches/wp2_tier_leaks.py` | WP-2: rewards that skip tiers, and the Pets/Heroes faucet |

After any edit: `qb.py check`, bump `pack_version` in `questSettings`, then a slim boot
(`../trial/README.md`) with `--bundle quests --bundle inspect` plus the mods whose items the
edited quests use, and read `logs/latest.log` for BetterQuesting errors. A server only
re-imports the book after `/bq_admin default load`.
