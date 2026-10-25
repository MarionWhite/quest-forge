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
#   delete the trial's mods/QuestForgeContent-1.0.0.jar first: it is a HARD LINK to the live
#   jar, and copying over it would overwrite the live one. Then copy the debug jar in.
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

## 4. The dead-item census

```bash
py -3.10 -I tools/items/dead_items.py      # -> docs/reference/dead-items.{md,json}
```

Joins the dump, the descriptions, the quest book, the pack's loot configs (Lucky Block,
ChocolateQuest, Doomlike, Surprise Eggs, Loot Bags), the CraftTweaker scripts and the ore
survey, and gives every item a status: `ok`, `no-source`, `creative`, `technical`, `hidden`,
`disabled` or `quest-only`, with the flags that decided it. The Markdown is written for the
quest writers ([`../../docs/reference/dead-items.md`](../../docs/reference/dead-items.md)); the
JSON carries every flag per item for the texture ranking. Each "how to get it" line is
classified sentence by sentence, so a line that says "creative only" or "technical" is a
verdict and one that names a mob, chest, machine or biome is a source. What it cannot see (mob
drops and dungeon loot inside jars, machine recipes, recipes registered at world load) is
listed at the top of both outputs. Re-run after any change to the dump, the descriptions, the
book or the loot configs, and commit both outputs.
