# Textures: current state

Rewrite this file when the state changes; keep it under 2 KB.

- **Builder:** `tools/textures/build_qf_textures.py` -> `C:\qfb\textures\*.zip`, never committed (Mojang pixels).
  It warns on any normal map that runs OpenGL-style (`labpbr.y_sign`).
- **Direction:** `docs/design/textures/direction.md`, `faithless-study.md`, `modded-blocks.md`.
- **r010 method (owner, r009):** no more procedural leaf or wheat art. Start from Faithful 64x and reproduce
  Stay True's technique, never its pixels. Show 2-3 different directions per weak scene.
- **r010 in progress** (`ops/checkpoints/r010-textures.md`):
  - Wall fixed. VNR normals were already DirectX and got flipped (34 maps lit from below), and diamond was
    coded metal. Now: Y fix, `--diamond gem`, gold metal kept off steep bevels.
  - Gold's darkness is the shader's colour grade (blue clipped to 0); handed to r010-shader.
  - Wheat: `--wheat dense|bushy` (wheat_dense.py) is dense and gold, but crops get no random CTM under Angelica.
    The variants need a qf-tweaks hook (ops/DECISIONS.md).
  - Leaves: `--leaves faithful|dense|crowns` (leaves_dense.py), plus leaves_<kind>_frill.png for the frills track.
  - Emerald in the diamond's direction (gems.py, default). Books centred by bounding box. A motif on every splash potion.
  - Next: review the leaves, wall and items renders, then hand off r010 (texture_scenes.json, TEXTURES-READY).
- **Owner likes:** Faithful 64x bricks, metals and leaves; Stay True wheat and tree leaves; Patrix mobs; VNR light;
  Soartex bookshelves; Faithless items, potions, books, GUI, TNT and boss bars.
- **Owner dislikes:** Conquest's textures, Faithful's grass, Faithless's blocks.
- **Showcase world:** `C:\qfb\textures\world-showcase`. Views diag_column and diag_emerald are the wall-lighting ladder.
- **Modded blocks (decision 0006):** `build_modded_textures.py` + `build_ship.py` -> `C:\qfb\textures\QFTextures.zip`.
