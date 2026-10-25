# `quests/` — the quest book toolkit

`qb.py` loads, checks and edits the BetterQuesting book (`DefaultQuests.json`). It replaces the
scripts in `../pack-fixes/quests/`, which hard-code a macOS PrismLauncher path and cannot be
re-run. The plan it serves is [`../../docs/design/questline-audit.md`](../../docs/design/questline-audit.md).

```
py -3.10 -I tools/quests/qb.py check               # every check, both books; exit 1 on any error
py -3.10 -I tools/quests/qb.py path                # the chapter order: what opens each numbered chapter
py -3.10 -I tools/quests/qb.py tally               # reward totals per tab, and what is ungated
py -3.10 -I tools/quests/qb.py dump --out dump.txt # one readable line per task and reward
py -3.10 -I tools/quests/qb.py show 63             # one quest as JSON
py -3.10 -I tools/quests/qb.py diff                # where the pack and server books differ
py -3.10 -I tools/quests/qb.py check --book tools/quests/drafts/DefaultQuests.wp5.json   # any book file
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
| `hunt` | a `bq_standard:hunt` target that is not in `entities.json`, or a `bq_standard:location` dimension that is not. BQ never checks a hunt target when the book loads: a misspelt name is a quest nobody can finish, and no log line says so. |
| `path` | a quest that needs a HIDDEN quest, a prerequisite cycle, or a numbered chapter that can open before (or together with) the one before it. Prints, per chapter, the quest that opens it, what that quest needs, and how many quests come first. |

**The chapter order `path` enforces.** Each numbered chapter's cheapest entry quest must need
everything the previous chapter's entry needs, and more; no earlier chapter may need a later
chapter's quest. Two numbered tabs are exceptions, set in `SIDE_CHAPTERS` and
`LADDER_CHAPTERS`: Ch 2 Base is a side tab that opens with Ch 1, and Ch 9 ProjectE is a
ladder whose rungs open at the boss each recipe needs (the Philosopher's Stone at the Lich),
so only its last rung has to come after Ch 8 opens. Act tabs are numbered by their roman
numeral (`II: Old Powers` is act 2), so the exception keys are tab labels ('Ch 2', 'Ch 9'), not numbers. "Needs" is the cheapest set of quests
that must be complete, so an OR prerequisite counts its cheapest branch.

## Drafts

`drafts/` holds copies of the pack book with a proposed work package applied, for the author to
review before anything touches the real books. Every `qb.py` command takes one with
`--book PATH`. A draft is rebuilt from the current pack book each time its patch runs without
`--book`, so it never drifts; nothing installs it.

## `entities.json`

The entity names hunt tasks may use, each with the class it maps to and how the name was
checked: read from the mod's own registration call in the jar (`EntityRegistry.registerModEntity`
gives `ModId.name`; `registerGlobalEntityID` first gives the plain name, which then wins), then
confirmed in a server trial with `/qfcensus find <text>` (qf-content), which lists the keys of
`EntityList.stringToClassMapping`, the map BQ looks targets up in. Plain `/summon` cannot take
the names with spaces (`TwilightForest.Snow Queen`, `The King`). BQ's hunt task (Standard Expansion `TaskHunt`) credits a kill when the killer is a
player, to every member of that player's party; with `subtypes` on (the default) it also
credits subclasses, so never target a base class such as TF's `Tower Ghast` or `Minotaur`.
Kills by pets, minions or the environment do not count.

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
| `patches/wp3_chapter_order.py` | WP-3: cross-chapter prerequisites, later chapters hidden until they open, chapter-order texts |
| `patches/wp4_boss_hunts.py` | WP-4: boss proofs become hunt and location tasks; the Overlord and Mutant quests |
| `patches/wp5_prologue.py` | WP-5 **draft, not applied**: the Prologue tab "Arrival", plus the WP-10 voice sample on the old Ch 1. With no `--book` it writes `drafts/DefaultQuests.wp5.json`; `--book all` applies it once approved ([review](../../docs/design/quests/review-2026-10-19.md)) |
| `patches/wp6_act2.py` | WP-6 **draft, not applied**: Act II "II: Old Powers" (Twilight and Witchery in one tab), finale 484, three new quests, the Act II texts. With no `--book` it rebuilds `drafts/DefaultQuests.wp5.json` and writes `drafts/DefaultQuests.act2.json`; `--book all` applies both once approved ([review](../../docs/design/quests/review-act2-2026-10-25.md)) |

More helpers for those: `set_prereqs`, `set_visibility`, `set_tasks` (checks the task list it
expects), `add_quest` (copies every property key from an existing quest), `move_in_line`,
`set_pack_version`, `add_line` (a new tab; later tabs move right), `move_to_line`, and the task
builders `retrieval`, `hunt`, `location`, `checkbox`, `item_reward`, `choice_reward`, written with the keys and defaults Standard Expansion 3.0.181 reads.

**Booting a changed book.** BQ writes `world/betterquesting/QuestDatabase.json` only when the
database is dirty, so a trial that only starts and stops leaves no copy to inspect. End the
command file with `bq_admin default save` before `stop`: BQ then writes what it parsed back over
the trial's `config/betterquesting/DefaultQuests.json`, which can be compared with the repo book
(a hunt task whose keys BQ did not read comes back targeting `Zombie`). "Loaded N quests" is in
`logs/fml-server-latest.log`, not `latest.log`.

After any edit: `qb.py check`, bump `pack_version` in `questSettings`, then a slim boot
(`../trial/README.md`) with `--bundle quests --bundle inspect` plus the mods whose items the
edited quests use, and read `logs/latest.log` for BetterQuesting errors. A server only
re-imports the book after `/bq_admin default load`.
