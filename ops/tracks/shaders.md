# Shaders: current state

Rewrite this file when the state changes; keep it under 2 KB. History is in `ops/journal/shaders.md`
and the long archive in `C:\qfb\shaderdev\NEXT.md` (PC only).

- **Pack:** `shaders/QuestForge`, Iris/Angelica only.
- **Budgets per frame:** High 1440p 3 ms · Low 1080p 0.9 ms · Potato 720p 0.4 ms.
- **Lab:** https://marionwhite.github.io/quest-forge/shaders/. Rounds are in `site/shaders/rounds/rNNN.json`; feedback is in
  `docs/design/shaders/feedback/rNNN.json` with images in `attachments/rNNN/`. Taste is in `docs/design/shaders/look-bible.md`.
- **Round in progress:** r010, work dir `C:\qfb\shaderdev\r010` (spec_scenes.py, round.json written; checkpoint
  `ops/checkpoints/r010-shader.md`). Pack at c542939. Publish-cost run **1027-193818-r010-publish-cost**; then critic,
  then publisher (`finish_round.py C:/qfb/shaderdev/r010`). Built: Earth-grazer meteors (QF_METEOR_STYLE 1-3), the sunset
  mint fixed (sky seen through deep water), UW_VIS 2.0, teal river (RIVER_TINT 1), gold fixed (METAL_FLOOR, vibrance
  floor, METAL_F0). Open: crepuscular rays (QF_CREPUSCULAR, High-only, owner cost question); forest rays no leap;
  dust and golden held.
- **Debug views:** QF_DEBUG_VIEW 11-14 split water into sun visibility/Fresnel/depth, bed, transmitted, reflected.
- **Standing rules:** render with the current QF textures zip; vanilla only as a control. Label options clearly.
  Every Lab question states the cause and the trade-off with numbers.
- **References (internal only, never on the site):** `C:\qfb\shaderdev\refs` holds Complementary Reimagined/Unbound and BSL on our 16 views.
- **Known:** the cyan-grey grass in biome_hills is that biome's own colour, not a shader fault.
- **Tools:** `tools/renderq` (render, cost, cache), `tools/shaders/review/finish_round.py` (spec and publish), `check_glsl.py`,
  `make_clip.py --speedup` for slow-motion meteor clips (roundlib `ov(..., speedup=4)`).
