# Textures: current state

Rewrite this file when the state changes; keep it under 2 KB.

- **Builder:** `tools/textures/build_qf_textures.py`. Output goes to `C:\qfb\textures\QFTextures-vN.zip` and is NOT committed (it contains Mojang pixels).
- **Direction:** `docs/design/textures/direction.md` and `faithless-study.md`. The owner's round 7 pack notes are in
  `docs/design/shaders/feedback/r007.json` (scene `tex-packs`) plus the attachments.
- **v0** (shipped to r007) won every comparison but changed too little in the forest.
- **v1 in progress** (cc3230e):
  - Faithful 64x for stone, bricks, ores and metals, plus Faithful's dirt sides.
  - Our own plant and crop art in the direction of Stay True.
  - PBR improved toward Vanilla Normals Renewed (licence check pending).
  - Bookshelves.
  - Leaf gaps as small pockets.
  - CIT potion and enchanted-book prototypes (Faithless-inspired), with CIT on in TRIAL config only.
- **Owner likes:**
  - Faithful 64x stone bricks and metals.
  - Stay True's wheat and leaves on trees, but not the frills on single blocks or hedges.
  - Patrix mobs. Asked what's achievable: 1.7.10 has no CEM, so repaints only.
  - Vanilla Normals Renewed's light interaction.
  - Soartex's bookshelves.
  - From Faithless: item sprites, unique potion bottles and enchanted books, the GUI (not the main menu), creative tabs, TNT lettering, boss bars and animations.
- **Owner dislikes:** Conquest's textures, Faithful's grass, and Faithless's block textures.
- **Hand-off:** write `C:\qfb\shaderdev\r008\texture_scenes.json`, then `TEXTURES-READY`. The shader round merges them.
- **Showcase world:** `C:\qfb\textures\world-showcase`, with the texture wall, glass, and the modded-block wall (`--modded`, 36043c9).
