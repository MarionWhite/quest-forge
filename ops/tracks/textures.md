# Textures: current state

Rewrite this file when the state changes; keep it under 2 KB.

- **Builder:** `tools/textures/build_qf_textures.py`. Output goes to `C:\qfb\textures\QFTextures-vN.zip` and is NOT committed (it contains Mojang pixels).
- **Direction:** `docs/design/textures/direction.md` and `faithless-study.md`. The owner's round 7 pack notes are in
  `docs/design/shaders/feedback/r007.json` (scene `tex-packs`) plus the attachments.
- **v0** (shipped to r007) won every comparison but changed too little in the forest.
- **v1 done for r008** (`C:\qfb	extures\QFTextures-v1.zip`, not committed):
  - Faithful 64x for stone, bricks, ores, metals, glass and dirt; its connected glass (clear glass keeps Faithful's own rule, or Angelica's 16x rule wins).
  - Our own leaves, bark, grass top, tall grass, fern, wheat (straw when ripe) and four bookshelf variants.
  - PBR from Vanilla Normals Renewed (converted / hybrid), ours elsewhere.
  - CIT potion and enchanted-book prototypes, CIT on in TRIAL config only. Faithless-level sprites need a pixel artist.
  - Leaf frills A/B/C rendered (`--leaf-edges none|all|sides`); D (real outward frills) needs qf-tweaks code.
  - Weak spots: fern, birch bark, wheat middle stages, grass top a little flat.
- **r008 hand-off written:** `C:\qfb\shaderdev008	exture_scenes.json` + `TEXTURES-READY` (11 scenes). Next: the owner's r008 answers.
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
- **Modded blocks (decision 0006):** ranking and style notes in `docs/design/textures/modded-blocks.md`; `build_modded_textures.py` (ores on Faithful stone, backports, modded CTM, emissive) and `build_ship.py` (one zip, `C:\qfb	extures\QFTextures.zip`, wired into the release builder and the client profiles). Panes connect (`glassPane=true`, installed live). Fold into v1.
