# Textures: current state

Rewrite this file when the state changes; keep it under 2 KB.

- **Builder:** `tools/textures/build_qf_textures.py` -> `C:\qfb\textures\QFTextures-vN.zip`, never committed (Mojang pixels).
- **Direction:** `docs/design/textures/direction.md` (v1: sections 5-7), `faithless-study.md`, `modded-blocks.md`.
- **v1 done for r008** (`QFTextures-v1.zip`, with CIT):
  - Faithful 64x stone, bricks, ores, metals, glass, dirt; clear glass keeps Faithful's own CTM rule (else Angelica's 16x rule wins).
  - Ours: leaves, bark, grass top, tall grass, fern, wheat, four bookshelves. PBR from VNR.
  - CIT potions and books, CIT on in trials only. Faithless-level sprites need a pixel artist.
  - Leaf frills A/B/C via `--leaf-edges none|all|sides`; D (outward frills) needs qf-tweaks code.
  - Weak: fern, birch bark, wheat middle stages, grass top a little flat.
- **Hand-off:** `C:\qfb\shaderdev\r008\texture_scenes.json` + `TEXTURES-READY` (11 scenes).
- **r009 v2 in progress** (`ops/checkpoints/r009-textures.md`): leaves closed at v2b; grass top closed at v2c (vanilla's
  pattern kept crisp at 32x, as r007). Next: crops, metals/emerald, tex-golden artifact, potions.
- **Owner likes:** Faithful 64x bricks/metals; Stay True wheat and tree leaves (no frills on lone blocks/hedges);
  Patrix mobs (repaints only on 1.7.10); VNR light; Soartex bookshelves; Faithless items, potions, books, GUI, tabs, TNT, boss bars.
- **Owner dislikes:** Conquest's textures, Faithful's grass, Faithless's blocks.
- **Showcase world:** `C:\qfb\textures\world-showcase` (texture walls, glass, farm, items board, `--modded` wall).
- **Modded blocks (decision 0006):** `build_modded_textures.py` + `build_ship.py` (one zip, `C:\qfb\textures\QFTextures.zip`,
  wired into release and client profiles). Panes connect (`glassPane=true`, live). Fold into v1.
