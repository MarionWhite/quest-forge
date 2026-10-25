# `items/` — the item browser's data

[`site/items/`](../../site/items/) is a searchable index of every item in the pack, built for
writing quests: what each item is, how it's made, what it goes into, and which quests already
ask for it, give it or show it. It is served at `/items/` beside the mod list.

The page (`site/items/index.html`) is hand-written. Its data (`site/items/data/`) is generated
in two steps.

## 1. Dump the items from a running pack

qf-content's debug `ItemDump` (`mods/qf-content/src/main/java/com/questforge/content/debug/`)
runs at the title screen of a full-pack client. It writes items, icons and recipes, then closes
the game. It is debug tooling, so the release jar never contains it.

```bash
# a debug jar (the release build leaves the debug package out)
cd mods/qf-content && ./gradlew build -PqfDebugTools=true
#   copy build/libs/QuestForgeContent-1.0.0.jar somewhere safe, then rebuild without the flag
#   so build/libs never holds a debug jar someone could `trial.py install`

# a full-pack trial client with the debug jar swapped in
py -3.10 tools/trial/trial.py build itemdump <every catalog key> --overlay pack --shader off
#   trial.py copies every mod jar into the trial (it never links one into the live instance),
#   so the trial's mods/QuestForgeContent-1.0.0.jar is a plain copy. Delete it, then copy the
#   debug jar in. Never copy over it in place: refresh.py refuses a file with another hard link.
py -3.10 tools/trial/trial.py launch itemdump --xmx 5G --wait --timeout 600 \
    -D qf.itemdump=<out dir> -D qf.itemdump.quit=1
```

`--overlay pack` matters: CraftTweaker scripts in `pack/scripts` change recipes, and the
browser should show the recipes players get. To list every catalog key:
`py -3.10 -I -c "import json;print(' '.join(json.load(open('tools/trial/catalog.json'))['mods']))"`.

What it writes:

| File | Contents |
|---|---|
| `items.json` | One entry per stack that `getSubItems` hands out (what NEI and the creative menu list): name, mod, creative tab, kind, ore names, tooltip, attack, armour, durability, food |
| `icons-N.png` | 2048-pixel sheets of 32-pixel icons, drawn through `RenderItem`'s GUI path, so 3D blocks and mods' custom item renderers look as they do in an inventory |
| `recipes.json` | Every crafting recipe whose grid is readable (vanilla and `ore` shaped/shapeless), every furnace recipe, the ore dictionary, and a count of recipe classes it could not read |
| `mods.json`, `summary.json` | Mod names, versions and jar files; counts of failed renders and blank icons |

Limits worth knowing:

- Only **crafting and furnace** recipes. Machines, altars, Witchery's cauldron and other
  mod-specific crafting are not in the vanilla registries, so the browser can't show them.
  A mod's own `IRecipe` class still shows its output, labelled "Mod recipe".
- Tooltips are read with no player. A mod that needs one for `addInformation` contributes no
  tooltip lines. Not a crash: every item is read on its own.
- Icons are drawn at the title screen. A renderer that needs a world draws nothing, and the
  browser shows a lettered placeholder for it. `summary.json` counts these.

## 2. Build the site data

```bash
py -3.10 -I tools/items/build_site.py --dump <out dir>
```

It writes `items.json` (with `built`, the date, and `source`, the repo's short commit with
`-dirty` when the tree had changes; absent in dumps built before that change), `recipes.json`,
the icon sheets, and `stats.json`, which carries the same `built` and `source`.

This joins the dump with:

- [`../modlist/catalog.json`](../modlist/catalog.json): each mod's category and blurb, matched
  by jar file name. A mod missing there is filed under "Other" and listed when the script ends.
- The quest book, through [`../quests/qb.py`](../quests/): every task, reward and icon
  reference. A reference with a damage value the creative list doesn't have (a damaged tool, say)
  is attached to the item's first variant. One whose id is not in the dump at all is counted as
  unresolved. `qb.py ids` is the place to chase those down.

Rebuild after any change to the mod set, CraftTweaker scripts or the quest book, then commit
`site/items/data/`. Quest edits alone only need step 2 against the last dump.

## 3. Descriptions: what each item is, and how to get it

Every item page leads with a short wiki-style description and a "How to get it" line. Both
live in [`descriptions.json`](descriptions.json), keyed by `modid:name` (every variant) or
`modid:name@meta` (one variant). A value is either a string, the description alone, or
`{"d": description, "get": how to obtain}`. Edit it by hand freely.

They were researched per mod: from the mod's jar (its lang files and decompiled code), the
pack's own config (which changes what's true here; OreSpawn's disables its overworld
dungeons, for example), and the mod's wiki where it could be reached.
[`descriptions-sources.json`](descriptions-sources.json) records each entry's source, and
`inferred` marks the ones with no source beyond the name and recipe. To redo a mod:

```bash
py -3.10 -I tools/items/export_for_writing.py --out <dir> --mod <mod id>   # its research sheet
#   research and write <dir2>/<mod>.json as {key: {"d", "get", "src"}}
py -3.10 -I tools/items/merge_descriptions.py <dir2>                         # hand-written entries are kept
py -3.10 -I tools/items/build_site.py --dump <dump dir>
```

Chest loot is measured, not researched: the dump reads every `ChestGenHooks` table (dungeon,
mineshaft, stronghold, temple and blacksmith chests, plus any a mod adds), and the page shows
each item's chance per chest. Loot that mods roll in their own code (most mod dungeons) and
mob drops are only as good as the research.

## Refreshing everything in one go

On the Windows PC, from the repo root:

```bat
py -3.10 -I tools/items/refresh.py
```

It runs steps 1 and 2 above (debug build, trial, dump, item index), rebuilds the enchantment
roster, rebuilds the mod list from the live instance at `%APPDATA%\.crazycraft4\mods`
(`read-mod-metadata.py`, `build-catalog.py`, `render-page.py`), runs `check_fresh.py`, and prints
`git status --short` with a suggested commit message. It commits nothing.

- `--dry-run` prints every step and command and runs none of them.
- `--skip-dump --dump-dir <dir>` builds from a dump that already exists (after a failed mod-list
  step, say) and skips the game.
- `--xmx 5G` and `--timeout 600` go to the dump client.

Limits:

- Untested on the Mac. It was written against `trial.py` and this README as of 2026-10-25. Each
  `trial.py` call is one the steps above already document, so a changed option fails its step.
- `trial.py launch` waits until the owner has been idle for a few minutes before it starts a
  client (up to 600 minutes by default), so a dump can start late. That is deliberate.
- `pack/mods.tsv` is not regenerated. If `check_fresh.py` says it disagrees with the item index
  or the catalog, that file is the thing to correct by hand.

## Staying fresh

Three generated things can fall behind the pack: the item index (`site/items/data/`), the mod
list (`site/mods/index.html`, from `tools/modlist/catalog.json`) and the enchantment roster inside
`site/enchantments/index.html`. `tools/site/check_fresh.py` reports which, and why:

```bash
py -3.10 -I tools/site/check_fresh.py            # text report
py -3.10 -I tools/site/check_fresh.py --json     # the same as JSON
py -3.10 -I tools/site/check_fresh.py --strict   # also exit 1 when anything is stale
```

What it compares:

- **items:** the baseline is `source` from `items.json` when it is present and a commit here, else
  the last commit on or before `built`. From there it reports jars added, removed or re-versioned
  in `pack/mods.tsv`; versions the index recorded that disagree with `mods.tsv`; commits to
  `pack/scripts`, `pack/config/betterquesting/DefaultQuests.json`, `mods/qf-content/src/main` and
  `mods/qf-commands/src/main`; and uncommitted changes there. The pack's own jars (`QuestForge*`)
  are judged by their source commits, not by version: refresh builds them from the repo.
- **mods:** `catalog.json` against `mods.tsv` by jar name and version, and `site/mods/index.html`
  committed no earlier than `catalog.json` or `render-page.py`.
- **enchantments:** the keys in the page's `const ENCH` line against the `add(cfg, "key", ...)`
  calls in `QFEnchantments.java`.

A check that cannot run (no git history, a missing file) reports an `unknown:` reason, and that
area counts as stale. A check that cannot run is not a pass.

What the deploy writes (`.github/workflows/pages.yml`, both soft: a failure never fails the deploy):

- `_site/play/pack.json`, from `tools/site/pack_json.py`: the pack's fingerprint, packDate and commit.
- `_site/items/data/freshness.json`, from `check_fresh.py --json`: the report above. The item index
  page reads it for its banner.

What `.github/workflows/site-fresh.yml` fails on: a push to `main` or a pull request that touches
the inputs of these checks, when `check_fresh.py --strict` finds stale data. CI cannot rebuild the
index itself, because the dump needs the full 1.2 GB client with the debug jar, which is on the
owner's PC. The fix is `py -3.10 -I tools/items/refresh.py` there, then commit `site/` and push.
