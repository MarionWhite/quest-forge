# Shaders: current state

Rewrite this file when the state changes; keep it under 2 KB. History is in `ops/journal/shaders.md`
and the long archive in `C:\qfb\shaderdev\NEXT.md` (PC only).

- **Pack:** `shaders/QuestForge`, Iris/Angelica only.
- **Budgets per frame:** High 1440p 3 ms · Low 1080p 0.9 ms · Potato 720p 0.4 ms.
- **Lab:** https://marionwhite.github.io/quest-forge/shaders/. Rounds are in `site/shaders/rounds/rNNN.json`; feedback is in
  `docs/design/shaders/feedback/rNNN.json` with images in `attachments/rNNN/`. Taste is in `docs/design/shaders/look-bible.md`.
- **Round in progress:** r011 shader scenes handed off (`C:\qfb\shaderdev\r011\` spec_scenes.py, SHADERS-READY); critic and
  publisher next. Pack: Photon 1.4 atmosphere (QF_ATMOS 1), Photon rays + shadow wedges (QF_CREPUSCULAR 2, QF_CREP_SHADE),
  sectored meteors (QF_METEOR_STYLE 4/5). Photon LICENSE in `LICENSES/`. r010 picks kept.
- **Over budget:** High sea/swamp-water views 3.0-3.3 ms (as in r009/r010); r011's changes add at most 0.06.
- **Later:** Conquest's sky/fog/lightmaps can't show under our shader (we discard vanilla sky, never read fog colour
  or lightmap): port per-biome fog/sky tint from its colormaps, nether/end lightmap colours, aurora layer
  (r011-shader.md note). Photon's evening haze greys shaded near ground (golden_lit).
- **Debug views:** QF_DEBUG_VIEW 9 colortex5 raw; 11-14 water (sun/Fresnel/depth, bed, transmitted, reflected); 15 rays, cloud map, sky.
- **Standing rules:** render with the current QF textures zip; vanilla only as a control. Every Lab question states the
  cause and the trade-off with numbers.
- **References (internal only):** `C:\qfb\shaderdev\refs` (Complementary, BSL, Photon on our views).
- **Render queue night mode** 22:15-08:00: shot jobs only.
- **Tools:** `tools/renderq`, `tools/shaders/review/finish_round.py`, `check_glsl.py`, `make_clip.py --speedup`.
