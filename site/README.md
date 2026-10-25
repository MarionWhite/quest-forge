# Site

The public site, [marionwhite.github.io/quest-forge](https://marionwhite.github.io/quest-forge/).
Static pages with no build step and no external dependencies beyond web fonts. Each
folder is served under its own name, except `home/`, which is the site root
(`.github/workflows/pages.yml` arranges them). Every page carries the same nav strip,
the same colour tokens (light and dark), and links back to `../`.

| Page | Served at | What it is |
|---|---|---|
| [`home/`](home/) | `/` | The homepage: the main-menu art, what makes the pack different, a card for every page, three of the pack's own shader renders, the quest book's chapters and what opens each, and the loading-screen plates. Also the root's `404.html`, `favicon.png` and `apple-touch-icon.png`, and `img/`, which every other page shares. The images are web-sized copies made by [`../tools/site/make_home_images.py`](../tools/site/make_home_images.py). |
| [`play/`](play/) | `/play/` | **Get the pack.** Written for a friend: Java 8, Prism Launcher, the client release, putting it in Prism, memory and Java arguments by installed RAM, the Normal / Lite / Potato profiles, keys, what each refusal from the server means, things not to do, and the Mac steps. Shows the latest client release from the GitHub API when it can reach it. Its facts come from `docs/setup/` and `tools/lite-client/`; change those first, then this. |
| [`mods/`](mods/) | `/mods/` | The player-facing mod list: all 111 mods sorted into ten content categories, with performance and background mods last, and a live filter. Generated; see below. |
| [`items/`](items/) | `/items/` | The item index: every item in the pack with its icon, recipes, uses, ore names and the quests that ask for it, give it or show it. Search like NEI (`@mod`, `$ore`, `%tab`, `#tooltip`). Its data is separate, in `items/data/`, because the icons alone are megabytes. Built by [`../tools/items/`](../tools/items/). |
| [`worlds/`](worlds/) | `/worlds/` | All twenty-seven dimensions with their loading plates, grouped by the mod that supplies them, with each one's dimension number and where it sits in the climb. Dimension numbers come from `docs/survey/dimension-names.tsv`; the order from the quest book's chapter descriptions. TragicMC's two dimensions have no plate and are listed as such. |
| [`enchantments/`](enchantments/) | `/enchantments/` | The 81 custom enchantments: how tomes, books and the roll work, the success and destroy range of every rarity (from `Rarity.java`), the four consumables, and the full roster with a filter. The roster is data inlined into the page, taken from the item index's dump of every book; see below. |
| [`ore-atlas/`](ore-atlas/) | `/ore-atlas/` | The interactive ore atlas: pick any of nineteen dimensions and get a cut through the ground, a depth profile, a rarity scale anchored to ores you already know, and a sortable table of every ore. **Its figures are stale** ([decision 0002](../docs/decisions/0002-discard-the-ore-survey.md)); it is redone after the survey that runs just before the server opens. |
| [`online/`](online/) | `/online/` | **Who's online.** Reads `online/config.json`; while `address` is empty it says the server hasn't opened. Once the address is set it polls `api.mcstatus.io` every minute and shows up/down, the player count, the names on, and the MOTD. Nothing is stored. |
| [`shaders/`](shaders/) | `/shaders/` | The Shader Lab: the owner reviews shader rounds here, from a phone or a laptop. Each scene shows two or three options of one setting (our renders, and for taste questions a credited Wikimedia Commons reference photo); the owner picks, rates and notes, and "Send feedback" opens a GitHub issue holding the answers as JSON. Rounds are data in `shaders/rounds/` (`index.json`, `rNNN.json`, `rNNN/*.jpg`), posted by [`../tools/shaders/review/publish_round.py`](../tools/shaders/review/publish_round.py) and read back by [`fetch_feedback.py`](../tools/shaders/review/fetch_feedback.py). Answers autosave as a draft in the browser. |

## Adding a page

1. Put it in its own folder here. Copy the `:root` tokens and the `nav.site` strip from
   any existing page, mark its own entry with `aria-current="page"`, and refer to the
   icon and images as `../favicon.png` and `../img/...`.
2. Add a `cp -R site/<folder> _site/<folder>` line to `.github/workflows/pages.yml`.
3. Give it a card in `home/index.html`'s directory, and a link in every page's nav strip
   (the mod list's lives in `tools/modlist/render-page.py`; regenerate it).

## Opening the server page

Put the server's host name or IP in `online/config.json` (`address`, and `port` if it is
not 25565) and push. The page then shows live status. Leave `address` empty while the
server is closed, and the page says so instead of showing "offline".

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

## Regenerating the enchantment roster

The roster inside `enchantments/index.html` (the `const ENCH = [...]` line) is built
from the item index's data, so it describes the books the game actually hands out.
After `tools/items/build_site.py` has refreshed `items/data/`, rebuild the line:

```bash
python3 -I tools/site/build_enchant_roster.py    # rewrites the ENCH line in place
```

Each entry is the book's name, highest level, rarity, what it applies to, the
description from `items/data/descriptions.json` (`enchant:<key>`), and the item key the
card links to in the item index. The script refuses to write if any book lacks a
description or the count is not 81.

The ore atlas carries its own data — 512 survey parameters and all 86 ore sprites
are inline, the sprites as base64 PNGs. It makes no network requests, so it works
from any host, or from a local file.

An earlier, static `vein-atlas` page was removed once this replaced it. It is in
git history if it is ever wanted back:

```bash
git log --oneline --diff-filter=D -- site/vein-atlas
git checkout <commit>^ -- site/vein-atlas
```
