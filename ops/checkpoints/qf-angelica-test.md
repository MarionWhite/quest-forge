# Owner's test copy: Angelica + every settled Lab pick (texture-dev, 2026-11-01)

Owner: "please put the solidified choices into my game so that I can test these things in tandem".
Target %APPDATA%\.qf-angelica (did not exist at start). Source %APPDATA%\.crazycraft4, READ ONLY.

## Decisions
- Real copies, no hard links: build_angelica_client.py gains `--copy` (2.1 TB free; copy ~3.7 GB).
- Angelica jars from C:\qfb\client-ang2 (mods + bin\lib), SHA-1s match manifest.json (checked).
- Shader: `git archive 1017eb5:shaders/QuestForge` -> shaderpacks\QuestForge (r015 picks).zip (LICENSES kept).
- Textures: one merged zip "QF Textures (settled picks).zip" (tools/textures/build_test_stack.py), bottom -> top:
  C:\qfb\textures\r016\QF-gems-frost-chiselcalm.zip (full QF Textures: Stay True, connected metals B, frost gems,
  chisel calm), r013\QF-r012-packs-final.zip, r013\QF-r012-gui-final.zip MINUS gui/icons.png + gui/widgets.png (HUD
  stays as live), r014\QF-r014-golem-conquest.zip. Above QuestForge.zip (only overlap was widgets.png).
- CIT on in the copy's mcpatcherforge.cfg (renders the owner judged had cit on).
- Stay True leaf planes/tall wheat need qf-tweaks leaf-frills build C:\qfb\frills\jars\v7\QuestForgeTweaks-1.0.jar
  (718473f = main's qf-tweaks + StayTrueModels; MeshStats off unless -Dqf.meshstats). config\qftweaks.cfg leafFrills.enabled=true.
- No XpBarStyle / debug / bench qf-content jar.

## Progress
- guard before: OK (112 jars, no hard links).
- Built: shader zip + C:\qfb\textures\test\QF Textures (settled picks).zip (5335 files); copy built with --copy
  --with-saves --pack-jars C:\qfb\frills\jars\v7; resourcePacks ["QuestForge.zip","QF Textures (settled picks).zip"]
  (1.7.10 lists bottom -> top); CIT on; config\qftweaks.cfg written; README-QF-TEST.txt written.
- Check: 10,363 files, 0 hard links; guard after: OK. Not boot-tested (owner starts it).
- DONE apart from commit/push (track, journal written).
