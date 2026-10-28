# Shaders: current state

Rewrite this file when the state changes; keep it under 2 KB. History is in `ops/journal/shaders.md`
and the long archive in `C:\qfb\shaderdev\NEXT.md` (PC only).

- **Pack:** `shaders/QuestForge`, Iris/Angelica only.
- **Budgets per frame:** High 1440p 3 ms · Low 1080p 0.9 ms · Potato 720p 0.4 ms.
- **Lab:** https://marionwhite.github.io/quest-forge/shaders/. Rounds are in `site/shaders/rounds/rNNN.json`; feedback is in
  `docs/design/shaders/feedback/rNNN.json` with images in `attachments/rNNN/`. Taste is in `docs/design/shaders/look-bible.md`.
- **Round in progress:** r011 (owner r010: copy what works), work dir `C:\qfb\shaderdev
011` (spec_scenes.py, round.json;
  checkpoint `ops/checkpoints/r011-shader.md`). Pack ada996a: Photon 1.4 atmosphere ported (QF_ATMOS 1: scattering LUT
  `textures/qf_scattering.dat` as a raw 3D customTexture, sun tint by the hour, analytic air fog), Photon-style rays
  (QF_CREPUSCULAR 2), sectored meteor shower (QF_METEOR_STYLE 4/5, 3 slots per pixel).
  Publish-cost run **1027-224601-r011-publish-cost** (after 08:00), then critic, then publisher. Photon LICENSE in `LICENSES/`. r010 picks kept.
- **Debug views:** QF_DEBUG_VIEW 9 colortex5 raw; 11-14 water (sun/Fresnel/depth, bed, transmitted, reflected); 15 rays, cloud map, sky.
- **Standing rules:** render with the current QF textures zip; vanilla only as a control. Label options clearly.
  Every Lab question states the cause and the trade-off with numbers.
- **References (internal only, never on the site):** `C:\qfb\shaderdev\refs` holds Complementary Reimagined/Unbound and BSL on our 16 views.
- **Render queue night mode** 22:15-08:00: shot jobs only; cost numbers wait for the morning.
- **Known:** the cyan-grey grass in biome_hills is that biome's own colour, not a shader fault.
- **Tools:** `tools/renderq` (render, cost, cache), `tools/shaders/review/finish_round.py` (spec and publish), `check_glsl.py`,
  `make_clip.py --speedup` for slow-motion meteor clips (roundlib `ov(..., speedup=4)`).
