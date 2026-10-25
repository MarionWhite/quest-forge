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
| `text` | `a` before a vowel ("a Anvil"), "Beastiary" for the tab (the Lycanites GUI is spelled that way, so "Lycanites' Beastiary" is allowed), placeholder words, `..`. A `[WRITE: ...]` placeholder (what a data patch leaves for the writers) is a warning in a draft and an error in the pack and server books. |
| `hunt` | a `bq_standard:hunt` target that is not in `entities.json`, or a `bq_standard:location` dimension that is not. BQ never checks a hunt target when the book loads: a misspelt name is a quest nobody can finish, and no log line says so. |
| `path` | a quest that needs a HIDDEN quest, a prerequisite cycle, or an act (numbered chapter) that can open before (or together with) the one before it. Prints, per tab, the quest that opens it, what that quest needs, and how many quests come first. |
| `obtain` | a retrieval task whose item the dead-item census ([`../../docs/reference/dead-items.md`](../../docs/reference/dead-items.md), `dead-items.json` beside it) does not call `ok`: creative-only, technical, hidden, no known source, or never listed by the item dump. `ids` proves an id is registered; `obtain` asks whether a player can get it. Warns on a reward whose item is creative, technical or hidden. `OBTAIN_ALLOW` in `qb.py` overrules the census per quest for cases a human has verified in game (empty today). Needs the census file; without it the check only warns. |

**What `obtain` flags today (census of 2026-10-25, dump of 2026-10-17).** The pack book fails
on nine tasks, the server book on the same minus quest 440 (it lacks the ChocolateQuest
quests); the WP-5 and WP-6 drafts fail on the same nine and add one warning. None has been
verified in game yet, so `OBTAIN_ALLOW` is empty and `qb.py check` exits 1 until each is fixed
or allowlisted:

| Quest | Asks for | Census says |
|---|---|---|
| 33 MC Helicopters: Take Flight | `mcheli:bell47g` | never listed by the item dump: MCHeli reads `assets/mcheli/*/*.txt` from the working directory, which the dump client lacked (and the play server lacks; see `docs/setup/hosting-a-server.md`) |
| 45 Spirit World | `witchery:spiritportal` | technical block, not obtainable; the quest should be a location task for the Spirit World |
| 53 Trophy Hunter | `statues:statues.statue` | hidden block item with no recipe; quest 208 is its only source |
| 120 HEE: The Biome Compass | `HardcoreEnderExpansion:biome_core` | hidden, untranslated, unresearched |
| 134, 135, 144 (TragicMC keys, Doombringer) | `TragicMC:dimensionalKeySynapse`, `dimensionalKeyNether` | research says creative only; the quest text claims a recipe the dump does not have |
| 432 A Spare You | `Sync:Sync_ItemPlaceholder` | no recipe in the dump; Sync registers its core recipe per world (`Sync.cfg hardcoreMode=2`), which a title-screen dump never sees |
| 440 The Ridge Has a Landlord | `chocolateQuest:banner` | creative only (no recipe, loot or drop in this pack) |
| 476 Bring Your Own Music (drafts only) | reward `qfcontent:qf_jukebox` | warning: creative only, so the quest is its only source (fine for a reward) |

Verify each in game before touching the book; a description that says "creative only" is
research, not a test.

**The order `path` enforces.** A tab is a link in the chain when its name is numbered: `Ch N:`
(the pre-WP-6 book) or an act tab from `act-structure.md` (`Arrival` is act 0, `I: Broken Sky`
to `IV: Titans` are 1-4, `Chronicle` is 5; `chapter_number()`). Several tabs may share an act
(`II: Twilight` beside `II: Witchery`) and are checked as one. Every entry quest of every tab
of an act must need everything the previous act's opening entry needs, and more; no earlier
act may need a later act's quest. Tabs named in `SIDE_CHAPTERS` and `LADDER_CHAPTERS` (keyed
by tab name) are exceptions: Base is a side tab that opens with the Prologue, and ProjectE is a
ladder whose rungs open at the boss each recipe needs (the Philosopher's Stone at the Lich), so
only its last rung has to come after the act the table names (Ch 8, or Act IV). "Needs" is the
cheapest set of quests that must be complete, so an OR prerequisite counts its cheapest branch.

## Drafts

`drafts/` holds copies of the pack book with a proposed work package applied, for the author to
review before anything touches the real books. Every `qb.py` command takes one with
`--book PATH`. A draft is rebuilt from its base (the pack book for WP-5, the WP-5 draft for
WP-6) each time its patch runs without `--book`, so it never drifts; nothing installs it. Running
a patch with `--book` on its own draft changes no bytes.

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

**By act.** After the per-line table, one row per act (the tabs `chapter_number()` places in
the chain, side tabs excluded) with the best case against the audit 4.5 budget (`ACT_BUDGET`):
the most valuable loot bag and sealed tome tier, Lucky Blocks, and diamonds counting 9 per
block. `OVER` marks a column past its budget. `Ch N` tabs have no act budget.

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
| `patches/wp6_acts.py` | WP-6 **draft, not applied**: the four-act spine ([act-structure](../../docs/design/quests/act-structure.md)): act tabs, the finales 481-486, the Nether and Wither quests, Pack Master as the convergence. Parameterised by the Decisions page answers (`--decisions docs/decisions/answers/s001.json`, or `--act1-02 B` per card; defaults are the recommendations). Builds `drafts/DefaultQuests.wp6.json` from the WP-5 draft; new text is left as `[WRITE: ...]` placeholders for the writers ([brief](../../docs/design/quests/wp6-writing-brief.md)). `--book all` applies it once approved, after WP-5 |

More helpers for those: `set_prereqs`, `set_visibility`, `set_tasks` (checks the task list it
expects), `set_task_field`, `add_quest` (copies every property key from an existing quest),
`remove_quest` (refuses while anything needs it), `add_reward_stack`, `move_in_line`,
`set_pack_version`, `add_line` (a new tab; later tabs move right), `rename_line`, `remove_line`
(an empty tab only), `set_tab_order`, `line_by_name`, `move_to_line` (position and size), and
the task builders `retrieval`, `hunt`, `location`, `checkbox`, `item_reward`, `choice_reward`,
written with the keys and defaults Standard Expansion 3.0.181 reads.

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
