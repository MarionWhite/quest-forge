# Textures: current state

Rewrite this file when the state changes; keep it under 2 KB.

- **Builder:** `tools/textures/build_qf_textures.py` -> `C:\qfb\textures\*.zip`, never committed (Mojang pixels).
  `--stay-true PATH` copies Stay True from `C:\qf-world\reference-packs` at build time (private, never git-added).
- **Direction:** `docs/design/textures/` (direction, faithless-study, modded-blocks, leaf-frills).
- **r014 gem materials handed off** (`C:/qfb/shaderdev/r014/textures_scenes.json`, 4 scenes; `r014-textures.md`):
  `--gem-mat crystal|faithful` (`gems_mat.py`) on r013's connected tiles. r013 plastic = one even gloss on flat
  colour (sky 76-89 % of floor variation); B/C 18-36 %. Polished dropped. Flaw: 1-block repeat.
- **r011 Stay True port** (`r011-stay-true.md`): leaf planes and weighted tall crops (qf-tweaks branch `leaf-frills`
  718473f, not merged). Open: leaves denser than the transparency the owner liked; keep or thin.
- **r014 packs** (`r014-packs.md`): one HUD (`qf_hud_r014.py`, own art: grace hotbar, tarnished boss bar,
  individual icons) x 3 XP bars; golem options Faithless/Soartex/Conquest. Render 1031-194643 reviewed;
  medallion fix re-render 1031-201118 pending, then `r014_packs_handoff.py --ready`. Owner: ship the
  XpBarStyle hook (client-only qf-content code) or the XP number stays lime. Settled: round 12's mob set.
- **Next:** owner's r014 gem pick (default it; break the repeat); then merge leaf-frills, set builder defaults, build QFTextures-v3; second item style.
- **Owner likes:** Faithful 64x bricks, metals and leaves; Stay True wheat and tree leaves; Patrix mobs; VNR light;
  Soartex bookshelves; Faithless items, potions, books, GUI, TNT and boss bars.
- **Owner dislikes:** Conquest textures, Faithful grass, Faithless blocks, r010 spiky frills.
- **Showcase world:** `C:\qfb\textures\world-showcase` (diag_column/diag_emerald = wall-lighting ladder).
- **Modded blocks (0006):** `build_modded_textures.py` + `build_ship.py` -> `C:\qfb\textures\QFTextures.zip`.
