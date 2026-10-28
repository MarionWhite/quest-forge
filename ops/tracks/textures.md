# Textures: current state

Rewrite this file when the state changes; keep it under 2 KB.

- **Builder:** `tools/textures/build_qf_textures.py` -> `C:\qfb\textures\*.zip`, never committed (Mojang pixels).
  `--stay-true PATH` copies Stay True from `C:\qf-world\reference-packs` at build time (private; never git-added).
- **Direction:** `docs/design/textures/direction.md`, `faithless-study.md`, `modded-blocks.md`, `leaf-frills.md`.
- **r011 Stay True port handed off** (`C:\qfb\shaderdev\r011\staytrue_scenes.json` + STAYTRUE-READY, 7 scenes;
  checkpoint `r011-stay-true.md`): Stay True's leaf planes and weighted tall crops (qf-tweaks branch `leaf-frills`
  718473f, not merged) and its glassy animated gems. Cost: frame p50 +0-5%, leafy sections +23% vertices.
  Open for the owner: leaves are denser than the transparency he liked; keep or thin.
- **r011 packs handed off** (`r011-packs.md`; `packs_scenes.json` + PACKS-READY, 21 scenes): `r007packs.py` ->
  QF-r011-packs.zip / QF-r011-gui.zip (Faithless items/GUI/TNT, Soartex shelves, Patrix skins for 12 mobs). No measurable
  cost. Open: owner's Soartex/smoke/boss-bar answers; GUI fixes (plaque contrast, enchanting book) unless he objects.
- **Next:** owner's r011 picks; then merge leaf-frills, set builder defaults, build QFTextures-v3; second item style.
- **Owner likes:** Faithful 64x bricks, metals and leaves; Stay True wheat and tree leaves; Patrix mobs; VNR light;
  Soartex bookshelves; Faithless items, potions, books, GUI, TNT and boss bars.
- **Owner dislikes:** Conquest's textures, Faithful's grass, Faithless's blocks, r010's spiky frills.
- **Showcase world:** `C:\qfb\textures\world-showcase`. Views diag_column and diag_emerald are the wall-lighting ladder.
- **Modded blocks (decision 0006):** `build_modded_textures.py` + `build_ship.py` -> `C:\qfb\textures\QFTextures.zip`.
