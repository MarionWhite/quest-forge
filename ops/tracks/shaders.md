# Shaders: current state

Rewrite this file when the state changes; keep it under 2 KB. History is in `ops/journal/shaders.md`
and the long archive in `C:\qfb\shaderdev\NEXT.md` (PC only).

- **Pack:** `shaders/QuestForge`, Iris/Angelica only.
- **Budgets per frame:** High 1440p 3 ms · Low 1080p 0.9 ms · Potato 720p 0.4 ms.
- **Lab:** https://marionwhite.github.io/quest-forge/shaders/. Rounds are in `site/shaders/rounds/rNNN.json`; feedback is in
  `docs/design/shaders/feedback/rNNN.json` with images in `attachments/rNNN/`. Taste is in `docs/design/shaders/look-bible.md`.
- **Round state:** r016 pre-publish fixes done (critic.json `_r016_publish_summary`, shader items 1-5, 7): crops named
  per option key, dawn gate (QF_DUSK_SKY 3/QF_DUSK_RAY evening only; s16fd dawn = p15), shore text says plainly it did not
  pass by eye (6/10). Sea, sun, night critic-passed. Shore pass 4 (QF_DUSK_CLFLOOR 1, s16ff) broke two numbers: off.
  finish_round dry run clean; ready to publish. Round 17 opens on the shore's clouds (lit tan, never under the sky).
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
- 2026-11-01: r016 PUBLISHED (f15c766), awaiting owner feedback.
- 2026-11-01 22:20: r016 pre-publish fixes in; ready for finish_round.
