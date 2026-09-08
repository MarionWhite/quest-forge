# Site

Static pages. Each is a single self-contained HTML file with no build step and no
external dependencies beyond web fonts — open one in a browser, or drop it on any
static host.

| Page | What it is |
|---|---|
| [`modlist/`](modlist/) | The player-facing mod list: all 111 mods sorted into ten content categories, with performance and background mods last, and a live filter. Served at the site root. |
| [`ore-atlas/`](ore-atlas/) | The interactive ore atlas: pick any of nineteen dimensions and get a cut through the ground, a depth profile, a rarity scale anchored to ores you already know, and a sortable table of every ore. Served at `/ore-atlas/`. |

The ore atlas carries its own data — 512 survey parameters and all 86 ore sprites
are inline, the sprites as base64 PNGs. It makes no network requests, so it works
from any host, or from a local file.

An earlier, static `vein-atlas` page was removed once this replaced it. It is in
git history if it is ever wanted back:

```bash
git log --oneline --diff-filter=D -- site/vein-atlas
git checkout <commit>^ -- site/vein-atlas
```

## Regenerating the mod list

The page is generated, not hand-written. Three steps, in
[`../tools/modlist/`](../tools/modlist/):

```bash
cd tools/modlist
python3 read-mod-metadata.py     # read every jar -> mods.json
python3 build-catalog.py         # join with categories + blurbs -> catalog.json
python3 render-page.py           # -> questforge-modlist.html
```

`read-mod-metadata.py` pulls each mod's name and version from its own `mcmod.info`,
so those fields track the jars rather than anyone's memory of them. Roughly a dozen
mods ship no metadata at all — OptiFine, NEI, ICBM and others — and are identified
from their package and asset structure instead.

`build-catalog.py` holds the category assignment and the one-line description for
every mod, and **fails loudly** if a jar in the instance has no catalog entry or a
catalog entry names a jar that is not there. That check is the point: it is what
stops the page from drifting away from the pack it claims to describe.

When the pack's mod set changes, re-run all three rather than editing the HTML.
