# Custom trees for the WorldPainter map

Research of 2026-10-24. The packs themselves live outside the repo in `C:\qf-world\trees\` (Syncthing,
shared with the author's Mac). `SOURCES.md` there lists each pack's URL, licence and credit line, and each
`<pack>-preview.png` is a side-view contact sheet. Follows on from [rlcraft-visuals.md](rlcraft-visuals.md) §4.

## What was downloaded

All are free, and all allow use on a private server. None allow re-uploading the files, so the folder stays private.

| Folder | Objects | Size range (W×H×L) | Format, version | 1.7.10-clean? | Licence | Credit |
|---|---|---|---|---|---|---|
| `h2co3-1k-treepack` | 1,059 trees (split from one grid schematic) | 5–61 × 5–83 × 5–57, median 15×21×15 | .schematic, 1.12 | No: fences 188–191, concrete 251/252, glazed terracotta. `trees-1.7.10/` is a remapped copy | Free for any project | Not needed |
| `h2co3-1k-trees-3k-bushes` | 3,522 objects; 934 are 10+ blocks tall | up to 80×74×75 | .schematic, 1.12 | No (25 post-1.7 IDs); `objects-1.7.10/` remapped | Same as above | Not needed |
| `mythix13-tree-repository` | 107 objects (trees, giant mushrooms, dead pines, bones, rocks, plants), also as .bo2 | 7–33 × 11–49 × 7–32 | .schematic, roots pre-snapped for WP | **Yes** | Any use with credit | Yes |
| `plutouthere-god-tree-pack` | 46 "god trees": 9 oaks × 4 seasons (summer, blossom/autumn, leafless), willows, bonsai, dead, jungle | 86–287 × 57–182 × 52–231 | .schematic, 1.8+ | One ID (190 jungle fence); `schematic-1.7.10/` remapped | Free, credit | Yes |
| `jamziboy-conquered-trees-rocks` | 59 trees + 20 rocks, each also .bo2 | 5–37 × 9–44 × 5–40 | .schematic | **Yes** | Free with credit, no re-upload | Yes |
| `murokmakto-vol1-boreal` | 41 conifers, larches, bushes, trunks | 3–11 × 1–30 × 2–11 | .schematic | **Yes** (only logs, leaves, grass, fence) | Credit requested | Requested |
| `sijmenvb-worldpainter-trees` | 93 objects in 13 sets (jungle, palms, savanna, spruce, dead, mushrooms, roofed forest), plus WP `.layer` files | 1–36 × 1–55 × 1–39 | Sponge .schem (1.16+) | Converted to `schematic-1.7.10/`; stripped logs became normal logs | MIT | Keep notice |

"1.7.10-clean" means every block ID is 0–164 or 170–175. IDs 165–169 and 176+ are 1.8–1.12 blocks.
The remap (scratch tool `remap.py`) swaps fences to the oak fence, concrete to wool, glazed terracotta to
stained clay, and so on, and converts `.schem` names to numeric IDs, keeping log axis.

**[unverified]** Whether WorldPainter itself down-converts a modern `.schem` cleanly on a 1.2–1.12 export.
The converted `.schematic` copies avoid relying on it.

## Libraries surveyed

| Library | Content and quality | Format, MC version | Pre-1.13 OK? | Licence (private server?) | Price | Direct download |
|---|---|---|---|---|---|---|
| H2CO3 1k Treepack / 1k trees + 3k bushes / Treepack 3 (756 trees, 116 types) | Best value found: ~2,800 hand-built trees, ~70+116 species incl. palms, conifers, tropical, fantasy colours | One huge grid .schematic each (1.12) | After remap | Any use, no credit | Free | PMC files via the Internet Archive; Treepack 3 not fetched |
| Mythix13 Tree Repository V3.1 | 107 objects, strong on fantasy: 15 giant mushrooms, blossom, autumn, rotting/dead pines, bones | .schematic + .bo2 | Yes | Credit | Free | Dropbox |
| Plutouthere God Tree-Pack | 46 enormous landmark trees, 4 seasons each | .schematic | After 1 swap | Credit | Free | Mediafire |
| Conquered_ (Jamziboy) | 59 trees, 20 rocks; oak, willow, pine, olive, palm, jungle | .schematic + .bo2 | Yes | Credit, no re-upload | Free | Dropbox |
| Murokmakto Vol.1 Boreal, Vol.2 Tropical (48 plants) | Clean, natural conifers / tropical | .schematic | Yes | Credit requested | Free | Mediafire; Vol.2 not fetched |
| sijmenvb/worldpainter-trees | 93 survival-friendly objects + ready WP layers | .schem | Converted | MIT | Free | GitHub |
| EREMILION "Exotic and Desert Trees" (150) and "Realistic trees v2" (525) | Palms, desert and exotic trees | .schematic grid + files | Likely | Credit | Free | Not fetched (rate limit) |
| Psykovsky Tree Bundle | 10-per-species sets incl. cherry blossom, weeping mulberry, olive | .schematic | Likely | "anyone can use" | Free | Not fetched |
| WetSquarish "Tree/Rock/Bush 1400+", "1k Pine Trees" | Bulk variety | .schematic grid | Likely | "Use for anything" | Free | Not fetched |
| exsilit Tree Bundle (370) | Varied trees, mushrooms | world + schematics | Likely | Credit optional | Free | Not fetched |
| Grimace449 Epic Mushroom Pack; Giant Mushrooms (real species) | Giant mushrooms | .schematic | Likely | Credit / free | Free | Not fetched |
| Dead Tree Repository (The1Kwa1jsucsh) | 25 dead trees, upright and fallen | .schematic + OBJ | Likely | Own projects OK, no redistribution | Free | Not fetched |
| Lentebriesje Fantasy Tree Repository / Native Trees of Europe (WP wiki link) | Large 2013 repository | .schematic | Yes | **No licence stated** | Free | Skipped |
| Paleozoey, Trees of Europe & the Mediterranean (186, 39 species) | Survival-friendly, WP layers | 1.20 .schem | Conversion | No credit needed | Free | Not fetched |
| Consue's Baobabs Pack | Baobabs | 1.16+ .schem | Conversion | Credit | Free | Not fetched |
| ULTIMATE Tree Repository (BuiltByBit) | 300+ trees, rocks, shrubs, 10 biomes, sakura | 1.19–1.20 schem | Conversion with block loss | Standard licence, attribution | $19.99 | After purchase |
| Essential Trees (Haydn & Argent, Gumroad) | ~5 species × 50–60 per pack, very realistic | Modern; **needs Conquest Reforged blocks** | No | Server OK if files aren't handed out | £10/pack, £25 bundle | After purchase |
| CaliberMC Acacia; "50 Custom Trees Fantasy & Realist"; "Trees & Markets" | Small single-theme packs | Modern .schem (1.18+) | Conversion | No redistribution | $4, $4.98, ~$7–8 | After purchase |

Planet Minecraft blocks scripted access (403), so its pages and files were read through the Internet Archive.
The Archive rate-limited this research too; the "not fetched" packs above can be downloaded by hand in a browser.

## BoP IDs

BoP blocks have no pinned IDs (`config/biomesoplenty/ids.cfg` pins only biomes). In the POC world
`C:\qfs\v0\world` the IDs are: logs1–4 = 1143–1146, leaves1–4 = 1147–1150, petals = 1151,
colorizedLeaves1–2 = 1186–1187, planks = 1164, bamboo = 1134, willow = 1118, ivy = 1119, treeMoss = 1120.
These are above 255, so a schematic needs the AddBlocks nibble (WorldPainter reads it), and they hold only
for a world whose level.dat carries the same registry. Re-skinning vanilla-wood trees as BoP woods is a
numeric swap. Do it after the final pack's IDs are frozen.

## Procedural generation

A prototype (`gen.py`, about 200 lines) writes legacy .schematic trees from three models:
- space colonisation for broadleaf crowns, with pipe-model branch thickness;
- whorled conifers;
- curved palms.

It produced recognisable oak, maple, acacia, baobab, redwood, spruce, mega fir, palm, dead oak and
ice-crystal trees in one sitting (`procedural-prototype-preview.png`).

- **Realism:** good for geometric species: redwood, mega conifers, palms, baobab, mangrove prop roots, crystal and ice trees, petrified spires. Weaker than the best hand-built packs for broadleaf crowns, where H2CO3 and Plutouthere are clearly better.
- **Variety:** unlimited per species once tuned. A seed gives a new tree, and sizes scale freely.
- **Effort:** about 2–4 hours per species to tune to a good standard. Any block palette works, including BoP IDs.

## Recommendation per biome

| Biome | Use | Gap? |
|---|---|---|
| Redwood coast | **Generate** giant redwoods (5–9 wide trunks, 50–90 tall, crown in the top third, BoP redwood or spruce logs). Understorey from Murokmakto/H2CO3 conifers | No free redwood pack (Plutouthere's is DM-only) |
| Temperate rainforest | H2CO3 deciduous/conifer mix + Conquered_ big oaks + sijmenvb "old living forest"; add vines/moss by re-skin | — |
| Maple/autumn | Mythix autumn, Plutouthere autumn variants as landmarks, plus **leaf re-colour** of H2CO3 broadleaves to orange/red (BoP colourized leaves or stained clay) | Thin; re-colour fills it |
| Boreal, snowy conifer, mega taiga | Murokmakto Vol.1, Conquered_ pines, Mythix pines, H2CO3 conifers, sijmenvb large spruce (to 48 tall); **generate** mega spruces | — |
| Tropical rainforest, jungle | sijmenvb jungle (to 38 tall), H2CO3 tropical/banyan types, Conquered_ jungle | — |
| Mangrove | **Generate** (prop roots) | Gap |
| Savanna | H2CO3 acacias, sijmenvb savanna; **generate** baobabs | Baobab gap |
| Desert oasis | Palms from sijmenvb, Conquered_, H2CO3 | — |
| Enchanted quarter | Mythix giant mushrooms (15) and dead pines, H2CO3 fantasy-colour trees, God Tree dead/willow/bonsai as landmarks; re-skin with BoP magic/dark leaves | Mystic leaf colours need BoP re-skin |
| Frozen fairy forest | **Generate** ice-crystal trees (packed ice, stained glass); Conquered_ icy rocks | Gap |
| Dead forest, petrified spires | Mythix rotting pines, sijmenvb dead trees, God Tree leafless variants; **re-skin** dead trees in stone/andesite for petrified ones, or generate spires | Petrified gap |
| Cherry blossom | God Tree blossom variants (landmarks), Mythix pink blossom; generate or re-colour mid-size ones | Mid-size thin |
| Eucalyptus | **Generate** (tall pale birch-log trunks, sparse high crowns) | Gap |

**Bottom line:** packs cover most biomes. No paid pack is needed; the best paid candidate, the $19.99
ULTIMATE Tree Repository, is 1.19+ and would lose blocks in conversion. Build a small generator for the six
gaps (redwood, mangrove, baobab, crystal, eucalyptus, petrified), plus a re-skin/re-colour pass for autumn,
mystic and BoP woods.
