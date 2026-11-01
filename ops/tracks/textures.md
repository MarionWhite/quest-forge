# Textures: current state

Rewrite this file when the state changes; keep it under 2 KB.

- **Builder:** `tools/textures/build_qf_textures.py` -> `C:\qfb\textures\*.zip`, never committed (Mojang pixels).
  `--stay-true PATH` copies Stay True from `C:\qf-world\reference-packs` at build time (private, never git-added).
- **Direction:** `docs/design/textures/` (direction, faithless-study, modded-blocks, leaf-frills).
- **Gems:** owner picked r015 E frost (`--gem-look frost`); r016 slider frost -> calm + Chisel calm option
  (`--chisel-gems calm`), render 1101-155222 pending review (`r016-textures.md`).
- **r011 Stay True port** (`r011-stay-true.md`): leaf planes and weighted tall crops (qf-tweaks branch `leaf-frills`
  718473f, not merged). Open: leaves denser than the transparency the owner liked; keep or thin.
- **HUD:** every design through r016 rejected; XpBarStyle hook still needs the owner's yes. Settled: round 12 mobs, Conquest snow golem.
- **Owner's test copy** (2026-11-01, `qf-angelica-test.md`): `%APPDATA%\.qf-angelica` (Angelica, real copies,
  saves) + shader 1017eb5 (r015) + `build_test_stack.py` picks + leaf-frills tweaks v7; HUD as live.
- **Next:** owner's r015 gem direction (then break any per-block repeat); then merge leaf-frills, set builder defaults, build QFTextures-v3; second item style.
- **Owner likes:** Faithful 64x bricks, metals and leaves; Stay True wheat and tree leaves; Patrix mobs; VNR light;
  Soartex bookshelves; Faithless items, potions, books, GUI, TNT and boss bars.
- **Owner dislikes:** Conquest textures, Faithful grass, Faithless blocks, r010 spiky frills.
- **Showcase world:** `C:\qfb\textures\world-showcase` (diag_column/diag_emerald = wall-lighting ladder).
- **Modded blocks (0006):** `build_modded_textures.py` + `build_ship.py` -> `C:\qfb\textures\QFTextures.zip`.
