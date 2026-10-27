# Textures: current state

Rewrite this file when the state changes; keep it under 2 KB.

- **Builder:** `tools/textures/build_qf_textures.py` -> `C:\qfb\textures\*.zip`, never committed (Mojang pixels).
  It warns on any normal map that runs OpenGL-style (`labpbr.y_sign`).
- **Direction:** `docs/design/textures/direction.md`, `faithless-study.md`, `modded-blocks.md`.
- **r010 method (owner, r009):** no more procedural leaf or wheat art. Start from Faithful 64x and reproduce
  Stay True's technique, never its pixels. Show 2-3 different directions per weak scene.
- **r010 handed off** (`C:\qfb\shaderdev010	exture_scenes.json` + TEXTURES-READY; checkpoint `r010-textures.md`):
  - Wall fixed (direction.md, "r010: why the wall was lit from below"). Gold's darkness and lime sheen are the shader's.
  - Leaves: three directions, `--leaves faithful|rim|fine` (fine = Faithful 32x at half size). Texture alone can't
    break the cube outline; the frills do.
  - Wheat `--wheat bushy|dense`; crop variants (wheat x5, carrots x4, potatoes x4, `<stage>_v<i>`) for the qf-tweaks hook.
  - Emerald in diamond's direction; books centred; a motif on every splash potion.
  - Next: owner's picks, then set the builder defaults and build QFTextures-v3.
- **Owner likes:** Faithful 64x bricks, metals and leaves; Stay True wheat and tree leaves; Patrix mobs; VNR light;
  Soartex bookshelves; Faithless items, potions, books, GUI, TNT and boss bars.
- **Owner dislikes:** Conquest's textures, Faithful's grass, Faithless's blocks.
- **Showcase world:** `C:\qfb\textures\world-showcase`. Views diag_column and diag_emerald are the wall-lighting ladder.
- **Modded blocks (decision 0006):** `build_modded_textures.py` + `build_ship.py` -> `C:\qfb\textures\QFTextures.zip`.
