# Shaders: current state

Rewrite this file when the state changes; keep it under 2 KB. History is in `ops/journal/shaders.md`
and the long archive in `C:\qfb\shaderdev\NEXT.md` (PC only).

- **Pack:** `shaders/QuestForge`, Iris/Angelica only.
- **Budgets per frame:** High 1440p 3 ms · Low 1080p 0.9 ms · Potato 720p 0.4 ms.
- **Lab:** https://marionwhite.github.io/quest-forge/shaders/. Rounds are in `site/shaders/rounds/rNNN.json`; feedback is in
  `docs/design/shaders/feedback/rNNN.json` with images in `attachments/rNNN/`. Taste is in `docs/design/shaders/look-bible.md`.
- **Round in progress:** r014 (`ops/checkpoints/r014-shader.md`): publish cost 1031-204537-r014-publish-cost queued;
  then spec_scenes check, SHADERS-READY. New defaults: QF_SEA_GRAZE 2 (gold horizon in the sea), QF_RIM_GOLD 2 (amber
  clouds, warm highlight shoulder), QF_METEOR_CULL 0.25 + QF_METEOR_HUE 1, QF_GEM_LOOK 2 (inner-facet gem light).
  QF_CLOUD_COVER 0.6 = cloud-free sky (whole-disk sun view). QF_SUN_HALO option (glow is the sky/haze Mie).
- **Over budget (owner question, later round):** High sea sunset 3.55 ms, 3.40 with rays off: the water is the cost.
  11 of 24 High views 3.01-3.55, all with water (as r012). Low lake 0.94, ocean_sunset 0.92 (r012 0.88/0.89).
- **Later:** ocean/lake water cost; Conquest's per-biome fog/sky tint, nether/end lightmaps, aurora.
- **Debug views:** QF_DEBUG_VIEW 9 colortex5 raw; 11-14 water (sun/Fresnel/depth, bed, transmitted, reflected); 15 rays, cloud map, sky; 16 the final-pass sun glare alone.
- **Standing rules:** render with the current QF textures zip; vanilla only as a control. Every Lab question states the
  cause and the trade-off with numbers.
- **References (internal only):** `C:\qfb\shaderdev\refs` (Complementary, BSL, Photon on our views).
- **Render queue night mode** 22:15-08:00: shot jobs only.
- **Tools:** `tools/renderq`, `tools/shaders/review/finish_round.py`, `check_glsl.py`, `make_clip.py --speedup`.
