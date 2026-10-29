# Shaders: current state

Rewrite this file when the state changes; keep it under 2 KB. History is in `ops/journal/shaders.md`
and the long archive in `C:\qfb\shaderdev\NEXT.md` (PC only).

- **Pack:** `shaders/QuestForge`, Iris/Angelica only.
- **Budgets per frame:** High 1440p 3 ms · Low 1080p 0.9 ms · Potato 720p 0.4 ms.
- **Lab:** https://marionwhite.github.io/quest-forge/shaders/. Rounds are in `site/shaders/rounds/rNNN.json`; feedback is in
  `docs/design/shaders/feedback/rNNN.json` with images in `attachments/rNNN/`. Taste is in `docs/design/shaders/look-bible.md`.
- **Round in progress:** r013 (`ops/checkpoints/r013-shader.md`): code and picks done, publish-cost renders
  1029-160736-r013-publish-cost queued; `C:\qfb\shaderdev013\spec_scenes.py` + round.json drafted, SHADERS-READY after
  review. New defaults: gold sea body at golden hour (QF_SEA_GOLD 1), gold shift under 7 deg (QF_SUN_GOLD_LOW 3), BSL
  soft sun (QF_SUN_SOFT 1), rays 8 taps one fetch (+0.12 ms, was +0.30), one-radiant meteors (no cost rise), gem SSR
  on with CTM facet packs (QF_GEM_FACET 0, +0.15 ms). New view sun_clear (no view fully clears the far strand).
- **Over budget:** High ocean_sunset 3.55 ms (3.43 with rays off: the water is the cost now), lake 3.19.
- **Later:** ocean/lake water cost; Conquest's per-biome fog/sky tint, nether/end lightmaps, aurora.
- **Debug views:** QF_DEBUG_VIEW 9 colortex5 raw; 11-14 water (sun/Fresnel/depth, bed, transmitted, reflected); 15 rays, cloud map, sky.
- **Standing rules:** render with the current QF textures zip; vanilla only as a control. Every Lab question states the
  cause and the trade-off with numbers.
- **References (internal only):** `C:\qfb\shaderdev\refs` (Complementary, BSL, Photon on our views).
- **Render queue night mode** 22:15-08:00: shot jobs only.
- **Tools:** `tools/renderq`, `tools/shaders/review/finish_round.py`, `check_glsl.py`, `make_clip.py --speedup`.
