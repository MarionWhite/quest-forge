# Textures: current state

Rewrite this file when the state changes; keep it under 2 KB.

- **Builder:** `tools/textures/build_qf_textures.py` -> `C:\qfb\textures\*.zip`, never committed (Mojang pixels).
  `--stay-true PATH` copies Stay True from `C:\qf-world\reference-packs` at build time (private, never git-added).
- **Direction:** `docs/design/textures/` (direction, faithless-study, modded-blocks, leaf-frills).
- **r013 connected gems handed off** (`C:/qfb/shaderdev/r013/textures_scenes.json`, 4 scenes;
  `r013-textures.md`): `gems_ctm.py`, builder `--gems-ctm facet|flat` = 47-tile MCPatcher CTM (Angelica's,
  PBR verified) on diamond, emerald, gold, iron, lapis from Faithful 64x's own pixels; redstone stays per
  block. Facet recommended. Iron fix: render 1029-130343 pending. Conflict: shader-dev's QF_GEM_FACET (block-local facets) would re-grid connected gems.
- **r011 Stay True port** (`r011-stay-true.md`): leaf planes and weighted tall crops (qf-tweaks branch `leaf-frills`
  718473f, not merged). Open: leaves denser than the transparency the owner liked; keep or thin.
- **r014 packs** (`r014-packs.md`): one HUD (`qf_hud_r014.py`, own art: grace hotbar, tarnished boss bar,
  individual icons) x 3 XP bars; golem options Faithless/Soartex/Conquest. Render 1031-194643 reviewed;
  medallion fix re-render 1031-201118 pending, then `r014_packs_handoff.py --ready`. Owner: ship the
  XpBarStyle hook (client-only qf-content code) or the XP number stays lime. Settled: round 12's mob set.
- **Next:** owner's r013 gem pick (make --gems-ctm the default); then merge leaf-frills, set builder defaults, build QFTextures-v3; second item style.
- **Owner likes:** Faithful 64x bricks, metals and leaves; Stay True wheat and tree leaves; Patrix mobs; VNR light;
  Soartex bookshelves; Faithless items, potions, books, GUI, TNT and boss bars.
- **Owner dislikes:** Conquest textures, Faithful grass, Faithless blocks, r010 spiky frills.
- **Showcase world:** `C:\qfb\textures\world-showcase` (diag_column/diag_emerald = wall-lighting ladder).
- **Modded blocks (0006):** `build_modded_textures.py` + `build_ship.py` -> `C:\qfb\textures\QFTextures.zip`.
