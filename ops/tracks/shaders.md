# Shaders: current state

Rewrite this file when the state changes; keep it under 2 KB. History is in `ops/journal/shaders.md`
and the long archive in `C:\qfb\shaderdev\NEXT.md` (PC only).

- **Pack:** `shaders/QuestForge`, Iris/Angelica only.
- **Budgets per frame:** High 1440p 3 ms · Low 1080p 0.9 ms · Potato 720p 0.4 ms.
- **Lab:** https://marionwhite.github.io/quest-forge/shaders/. Rounds are in `site/shaders/rounds/rNNN.json`; feedback is in
  `docs/design/shaders/feedback/rNNN.json` with images in `attachments/rNNN/`. Taste is in `docs/design/shaders/look-bible.md`.
- **Round state:** r016 sky done in the loop (ops/checkpoints/r016-shader.md): sea s16r3, sun s16r3cc, night s16t1
  critic-passed (7.75); shore s16y29 passes loop 3 on the critic's targets by hundredths (not re-judged). All
  defaults now (QF_SUN_WHITE 3 set, QF_DUSK_ZEN 7 + HICLOUD 3). SHADERS-READY;
  hand-off files in C:\qfb\shaderdev
016 (spec_scenes.py, round.json, shore.json).
- **Over budget (owner question):** r016 High 14 of 24 over 3.0 (12 water views 3.01-3.77, sun_clear worst; nights
  3.09/3.02); sunset water +0.11 ms vs r015 same run (white path +0.07). Low ocean_sunset 0.99, lake 0.96.
- **Later:** water cost; sea body olive vs BSL amber-rose; per-biome fog, nether/end lightmaps, aurora.
- **Debug views:** QF_DEBUG_VIEW 9 colortex5 raw; 11-14 water (sun/Fresnel/depth, bed, transmitted, reflected); 15 rays, cloud map, sky; 16 the final-pass sun glare alone.
- **Standing rules:** render with the current QF textures zip; vanilla only as a control. Every Lab question states the
  cause and the trade-off with numbers.
- **References (internal only):** `C:\qfb\shaderdev\refs` (Complementary, BSL, Photon on our views).
- **Render queue night mode** 22:15-08:00: shot jobs only.
- **Tools:** `tools/renderq`, `tools/shaders/review/finish_round.py`, `check_glsl.py`, `make_clip.py --speedup`.

- 2026-11-01: r016 SHADERS-READY; next: critic notes on the p16 frames, then publish.
