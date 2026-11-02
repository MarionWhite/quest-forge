# Shaders: current state

Rewrite this file when the state changes; keep it under 2 KB. History is in `ops/journal/shaders.md`
and the long archive in `C:\qfb\shaderdev\NEXT.md` (PC only).

- **Pack:** `shaders/QuestForge`, Iris/Angelica only.
- **Budgets per frame:** High 1440p 3 ms · Low 1080p 0.9 ms · Potato 720p 0.4 ms.
- **Lab:** https://marionwhite.github.io/quest-forge/shaders/. Rounds are in `site/shaders/rounds/rNNN.json`; feedback is in
  `docs/design/shaders/feedback/rNNN.json` with images in `attachments/rNNN/`. Taste is in `docs/design/shaders/look-bible.md`.
- **Round state:** r016 sky loop (ops/checkpoints/r016-shader.md), awaiting a critic pass. Night passes on defaults (NAVY 0.30,
  STAR_GAIN 0.070; 2.92 ms). Sea passes all 7 with QF_SUN_WHITE 3 (s16f1) but that blows sun_clear's sand edge;
  shore passes 5/6 with QF_DUSK_ZEN 6 (cold grey). Sea/shore defaults unchanged until the critic picks.
- **Over budget (owner question, later round):** High 11 of 24 views over 3.0: 9 water views 3.11-3.65 (sea sunset 3.61,
  sun_clear 3.65) and the nights 3.02/3.11. Low ocean_sunset 0.95, lake 0.94. Meteors 2.98 vs r012 2.94.
- **Later:** ocean/lake water cost; Conquest's per-biome fog/sky tint, nether/end lightmaps, aurora.
- **Debug views:** QF_DEBUG_VIEW 9 colortex5 raw; 11-14 water (sun/Fresnel/depth, bed, transmitted, reflected); 15 rays, cloud map, sky; 16 the final-pass sun glare alone.
- **Standing rules:** render with the current QF textures zip; vanilla only as a control. Every Lab question states the
  cause and the trade-off with numbers.
- **References (internal only):** `C:\qfb\shaderdev\refs` (Complementary, BSL, Photon on our views).
- **Render queue night mode** 22:15-08:00: shot jobs only.
- **Tools:** `tools/renderq`, `tools/shaders/review/finish_round.py`, `check_glsl.py`, `make_clip.py --speedup`.

- 2026-11-01: r016 sky loops 1-11 done; next: critic on the frames in the r016 checkpoint.
