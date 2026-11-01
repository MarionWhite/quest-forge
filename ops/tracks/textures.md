# Textures: current state

Rewrite this file when the state changes; keep it under 2 KB.

- **Builder:** `tools/textures/build_qf_textures.py` -> `C:\qfb\textures\*.zip`, never committed (Mojang pixels).
  `--stay-true PATH` copies Stay True from `C:\qf-world\reference-packs` at build time (private, never git-added).
- **Direction:** `docs/design/textures/` (direction, faithless-study, modded-blocks, leaf-frills).
- **r015 gems handed off** (`C:/qfb/shaderdev/r015/textures_scenes.json`, 3 scenes x 6 looks; `r015-textures.md`):
  `--gem-look facets|staytrue|jewel|calm|frost` (`gems_look.py`), F = calm + shader QF_GEM_NFADE 2. Our read: A cut
  stone close but per-block grid; B diamond cleanest, B emerald nested-square grid; C buttons/tiles (drop); D noisy;
  E calm but pale ice; F calms only the far floor. None is the answer yet.
- **r011 Stay True port** (`r011-stay-true.md`): leaf planes and weighted tall crops (qf-tweaks branch `leaf-frills`
  718473f, not merged). Open: leaves denser than the transparency the owner liked; keep or thin.
- **r015 packs** (`r015-packs.md`): five complete HUDs (`qf_hud_r015.py`, own art: gilded, cloisonne, ironbound,
  moonsilver, obsidian; banded rows, medallion, boss frame, outlined boss name). XpBarStyle gained text.boss,
  qf.boss.outline, qf.boss.frame (bench jar jars-r015). Render 1101-101607 pending, then `r015_packs_handoff.py
  --ready`. Owner: ship XpBarStyle or the number stays lime and no medallion/boss frame/outline. Settled: round 12 mobs,
  Conquest snow golem.
- **Next:** owner's r015 gem direction (then break any per-block repeat); then merge leaf-frills, set builder defaults, build QFTextures-v3; second item style.
- **Owner likes:** Faithful 64x bricks, metals and leaves; Stay True wheat and tree leaves; Patrix mobs; VNR light;
  Soartex bookshelves; Faithless items, potions, books, GUI, TNT and boss bars.
- **Owner dislikes:** Conquest textures, Faithful grass, Faithless blocks, r010 spiky frills.
- **Showcase world:** `C:\qfb\textures\world-showcase` (diag_column/diag_emerald = wall-lighting ladder).
- **Modded blocks (0006):** `build_modded_textures.py` + `build_ship.py` -> `C:\qfb\textures\QFTextures.zip`.
