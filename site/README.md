# Site

The public site, [marionwhite.github.io/quest-forge](https://marionwhite.github.io/quest-forge/).
Static pages with no build step and no external dependencies beyond web fonts. Each
folder is served under its own name, except `home/`, which is the site root
(`.github/workflows/pages.yml` arranges them). Every page carries the same nav strip,
the same colour tokens (light and dark, with a toggle), and links back to `../`.

| Page | Served at | What it is |
|---|---|---|
| [`home/`](home/) | `/` | The homepage: the main-menu art with a living sky (embers, ash and the odd meteor, drawn on a canvas; the Konami code cracks it open), the pack in numbers, what makes it different, the pack's own shader renders as a crossfading reel, a card for every page, the quest book's chapters with a rotating line from the book, and the loading-screen plates. Also the root's `404.html`, `favicon.png` and `apple-touch-icon.png`, and `img/`, which every other page shares. The images are web-sized copies made by [`../tools/site/make_home_images.py`](../tools/site/make_home_images.py). The footer shows the pack version from `play/pack.json` when the deploy has written it. |
| [`play/`](play/) | `/play/` | **Get the pack.** Written for a friend: Java 8, Prism Launcher, the client release, putting it in Prism, memory and Java arguments by installed RAM, the Normal / Lite / Potato profiles, keys, what each refusal from the server means, things not to do, and the Mac steps. Shows the latest client release from the GitHub API when it can reach it, and the pack version the server expects from `pack.json` (written at deploy time, see below). Its facts come from `docs/setup/` and `tools/lite-client/`; change those first, then this. |
| [`first-night/`](first-night/) | `/first-night/` | **Your first night.** The survival primer: what to do before dark, the keys that matter (voice chat on Tab and U since 2026-10-25; B and N belong to the Adventure Backpack), what comes out at night (Infernal names, Weeping Angels below Y 40, mutants and giants), what happens when you die, playing together (parties, voice chat ranges, EnderStorage locks), luck and loot, tickets, and what comes next. Every fact is from the shipped configs, the shipped quest book or the pack's own source; the draft Prologue is not described as in the book. A Weeping Angel haunts the page: it only moves while you are not looking. |
| [`lucky/`](lucky/) | `/lucky/` | **Break a Lucky Block.** A full-screen opening in the style of a CS:GO case: the block drops, cracks, a reel of outcomes spins down onto the one that was rolled, and the reveal gets its own animation per kind (items with their real icons, mob spawns, explosions, falling blocks, structures, potion effects, messages, time, difficulty). Every outcome and its odds come from `pack/config/lucky/LuckyBlockProperties.txt`, including the luck modifiers of the crafting ingredients and the mod's own weighting; `data/lucky.json` is built by [`../tools/site/build_lucky.py`](../tools/site/build_lucky.py) and the freshness check flags it when the table changes. |
| [`graves/`](graves/) | `/graves/` | **The Wall of Graves.** Every death on the server as a gravestone in a graveyard, scaffolded for the day the server opens: the stones are the pack's gravestone shapes rebuilt as CSS cuboids with our own stone surfaces (no mod texture shipped), each carrying the player's name and, on hover, the death line, when, where and the killer, with "what kills people here" and "who dies most" boards. Reads `graves/config.json`: while `feed` is empty it shows `data/graves.json` (empty until the server opens; `?demo` shows `data/demo.json`); set `feed` to a published JSON (a Gist, say) and it reads that. The producer is [`../tools/server/graves_from_log.py`](../tools/server/graves_from_log.py), which turns the server log's death lines into that JSON. |
| [`players/`](players/) | `/players/` | **Players.** A card for everyone on the server (skin, class and level, time played, deaths, kills, quests done) and the **First Kills** board: who killed each boss first, from the earliest completion of each hunt quest in BetterQuesting's progress file. Same `config.json` / `data/players.json` / `?demo` pattern as the graves. The producer is [`../tools/server/player_cards.py`](../tools/server/player_cards.py), which reads a server folder's `usercache.json`, `stats/` and `betterquesting/QuestProgress.json`. |
| [`mods/`](mods/) | `/mods/` | The player-facing mod list: all 111 mods sorted into ten content categories, with performance and background mods last, a live filter, and for every mod that has items a link into the item index with its item and quest counts. Generated; see below. |
| [`items/`](items/) | `/items/` | The item index: every item in the pack with its icon, recipes, uses, ore names and the quests that ask for it. Search like NEI (`@mod`, `$ore`, `%tab`, `#tooltip`). Installable and usable offline: `manifest.webmanifest`, `sw.js` and the two icons make it a web app; the worker keeps a copy of the page and its data and tells the page when a newer index has been published ("A newer item index is ready", with a Reload button). It shows a banner when `data/freshness.json` (written at deploy time) says the index lags the pack. Its data is separate, in `items/data/`, because the icons alone are megabytes. Built by [`../tools/items/`](../tools/items/). |
| [`worlds/`](worlds/) | `/worlds/` | All twenty-seven dimensions with their loading plates, grouped by the mod that supplies them, with each one's dimension number and where it sits in the climb. Every plate downloads at 1280 × 720 from the repo, and the masthead links the 4K masters zip on the `art-masters-2026-09-08` release. Dimension numbers come from `docs/survey/dimension-names.tsv`; the order from the quest book's chapter descriptions. TragicMC's two dimensions have no plate and are listed as such. |
| [`enchantments/`](enchantments/) | `/enchantments/` | The 81 custom enchantments: how tomes, books and the roll work, the success and destroy range of every rarity (from `Rarity.java`), the four consumables, and the full roster with a filter. The roster is data inlined into the page, taken from the item index's dump of every book; see below. |
| [`ore-atlas/`](ore-atlas/) | `/ore-atlas/` | The interactive ore atlas: pick any of nineteen dimensions and get a cut through the ground, a depth profile, a rarity scale anchored to ores you already know, and a sortable table of every ore. **Its figures are stale** ([decision 0002](../docs/decisions/0002-discard-the-ore-survey.md)); it is redone after the survey that runs just before the server opens. |
| [`online/`](online/) | `/online/` | **Who's online.** Reads `online/config.json`; while `address` is empty it says the server hasn't opened. Once the address is set it polls `api.mcstatus.io` every minute and shows up/down, the player count, the names on, and the MOTD. Nothing is stored. |
| [`shaders/`](shaders/) | `/shaders/` | The Shader Lab: the owner reviews shader rounds here, from a phone or a laptop. **Not linked from the homepage or the nav**: shader progress is the owner's business, so the Lab is reachable only by its URL. Each scene shows two or three options of one setting (our renders, and for taste questions a credited Wikimedia Commons reference photo); the owner picks, rates and notes, and "Send feedback" opens a GitHub issue holding the answers as JSON. Rounds are data in `shaders/rounds/` (`index.json`, `rNNN.json`, `rNNN/*.jpg`), posted by [`../tools/shaders/review/publish_round.py`](../tools/shaders/review/publish_round.py) and read back by [`fetch_feedback.py`](../tools/shaders/review/fetch_feedback.py). Answers autosave as a draft in the browser. |

## Theme

Every page follows the system theme and carries a toggle at the right end of the nav. It
cycles auto → the opposite of the system theme → auto, so each click flips the page, and the
choice is one `localStorage` key (`qf-theme`) shared by the whole site. A one-line script in
each page's head applies it before the stylesheet, so there is no flash. The Shader Lab and the
ore atlas are dark by design and have no toggle.

## Adding a page

1. Put it in its own folder here. Copy the `:root` tokens, the head theme script, the
   `nav.site` strip (with the toggle button and its script) from any existing page, mark its
   own entry with `aria-current="page"`, and refer to the icon and images as `../favicon.png`
   and `../img/...`.
2. Add a `cp -R site/<folder> _site/<folder>` line to `.github/workflows/pages.yml`.
3. Give it a card in `home/index.html`'s directory, and a link in every page's nav strip
   (the mod list's lives in `tools/modlist/render-page.py`; regenerate it).

## What the deploy generates

`pages.yml` copies the folders and then writes two files that are never committed:

- `play/pack.json`, from [`../tools/site/pack_json.py`](../tools/site/pack_json.py): the pack
  fingerprint and `packDate` of `pack/config` at that commit, as the title screen shows them
  (`pack 2026-10-17 - 3f7f089e6508`). The play page and the homepage footer show it.
- `items/data/freshness.json`, from [`../tools/site/check_fresh.py`](../tools/site/check_fresh.py):
  whether the item index, the mod list or the enchantment roster lags the pack, and why. The
  item index shows a banner from it. The deploy never fails on either; `site-fresh.yml` is the
  workflow that fails a push when the committed data is stale. How the pieces keep each other
  honest is in [`../tools/items/README.md`](../tools/items/README.md) ("Staying fresh"), and
  the one command that refreshes all of it on the PC is `tools/items/refresh.py`.

## Opening the server page

Put the server's host name or IP in `online/config.json` (`address`, and `port` if it is
not 25565) and push. The page then shows live status. Leave `address` empty while the
server is closed, and the page says so instead of showing "offline".

## Regenerating the mod list

The page is generated, not hand-written. Three steps, in
[`../tools/modlist/`](../tools/modlist/):

```bash
cd tools/modlist
python3 read-mod-metadata.py     # read every jar -> mods.json (--mods DIR or QF_MODS_DIR on another machine)
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

`render-page.py` also reads `site/items/data/items.json` for the per-mod item and quest
counts, so run it after the item index when both change.

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
