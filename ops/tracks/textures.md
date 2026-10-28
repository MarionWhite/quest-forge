# Textures: current state

Rewrite this file when the state changes; keep it under 2 KB.

- **Builder:** `tools/textures/build_qf_textures.py` -> `C:\qfb\textures\*.zip`, never committed (Mojang pixels).
  `--stay-true PATH` copies Stay True from `C:\qf-world\reference-packs` at build time (private; never git-added).
- **Direction:** `docs/design/textures/direction.md`, `faithless-study.md`, `modded-blocks.md`, `leaf-frills.md`.
- **r012 gems + roofed handed off** (`C:\qfb\shaderdev\r012\textures_scenes.json` + TEXTURES-READY, 4 scenes;
  checkpoint `r012-textures.md`): gems A Faithful polished / B Stay True, emerald without squares / C shader QF_GEM_SSR
  (cost pending, publisher fills GEM_COST). Builder `--gems facet|staytrue`. Roofed canopy: planes +8% p50.
- **r011 Stay True port** (`r011-stay-true.md`): leaf planes and weighted tall crops (qf-tweaks branch `leaf-frills`
  718473f, not merged). Open: leaves denser than the transparency the owner liked; keep or thin.
- **r011 packs handed off** (`r011-packs.md`; `packs_scenes.json` + PACKS-READY, 21 scenes): `r007packs.py` ->
  QF-r011-packs.zip / QF-r011-gui.zip (Faithless items/GUI/TNT, Soartex shelves, Patrix skins for 12 mobs). No measurable
  cost. Open: owner's Soartex/smoke/boss-bar answers; GUI fixes (plaque contrast, enchanting book) unless he objects.
- **Next:** owner's r011/r012 picks (gem A/B/C); then merge leaf-frills, set builder defaults, build QFTextures-v3; second item style.
- **Owner likes:** Faithful 64x bricks, metals and leaves; Stay True wheat and tree leaves; Patrix mobs; VNR light;
  Soartex bookshelves; Faithless items, potions, books, GUI, TNT and boss bars.
- **Owner dislikes:** Conquest's textures, Faithful's grass, Faithless's blocks, r010's spiky frills.
- **Showcase world:** `C:\qfb\textures\world-showcase`. Views diag_column and diag_emerald are the wall-lighting ladder.
- **Modded blocks (decision 0006):** `build_modded_textures.py` + `build_ship.py` -> `C:\qfb\textures\QFTextures.zip`.
