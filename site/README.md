# Site

Static pages with no build step and no external dependencies beyond web fonts. Each folder is
served under its own name, except `home/`, which is the site root
(`.github/workflows/pages.yml` arranges them).

| Page | Served at | What it is |
|---|---|---|
| [`home/`](home/) | `/` | The homepage and directory: the main-menu art, a card for every page, and the loading-screen plates. Its images are web-sized copies made by [`../tools/site/make_home_images.py`](../tools/site/make_home_images.py). |
| [`mods/`](mods/) | `/mods/` | The player-facing mod list: all 111 mods sorted into ten content categories, with performance and background mods last, and a live filter. |
| [`items/`](items/) | `/items/` | The item index: every item in the pack with its icon, recipes, uses, ore names and the quests that ask for it, give it or show it. Search like NEI (`@mod`, `$ore`, `%tab`, `#tooltip`). Its data is separate, in `items/data/`, because the icons alone are megabytes. Built by [`../tools/items/`](../tools/items/). |
| [`ore-atlas/`](ore-atlas/) | `/ore-atlas/` | The interactive ore atlas: pick any of nineteen dimensions and get a cut through the ground, a depth profile, a rarity scale anchored to ores you already know, and a sortable table of every ore. **Its figures are stale** ([decision 0002](../docs/decisions/0002-discard-the-ore-survey.md)); it is redone after the survey that runs just before the server opens. |
| [`shaders/`](shaders/) | `/shaders/` | The Shader Lab: the owner reviews shader rounds here, from a phone or a laptop. Each scene shows two or three options of one setting (our renders, and for taste questions a credited Wikimedia Commons reference photo); the owner picks, rates and notes, and "Send feedback" opens a GitHub issue holding the answers as JSON. Rounds are data in `shaders/rounds/` (`index.json`, `rNNN.json`, `rNNN/*.jpg`), posted by [`../tools/shaders/review/publish_round.py`](../tools/shaders/review/publish_round.py) and read back by [`fetch_feedback.py`](../tools/shaders/review/fetch_feedback.py). Answers autosave as a draft in the browser. |

## Adding a page

1. Put it in its own folder here, and link back to `../` (the homepage).
2. Add a `cp -R site/<folder> _site/<folder>` line to `.github/workflows/pages.yml`.
3. Give it a card in `home/index.html`'s directory. A planned page can sit there first as a
   `page soon` card (no link), as "Get the pack" and "Who's online" do now.

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
python3 render-page.py           # -> ../../site/mods/index.html
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
