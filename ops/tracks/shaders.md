# Shaders: current state

Rewrite this file when the state changes; keep it under 2 KB. History is in `ops/journal/shaders.md`
and the long archive in `C:\qfb\shaderdev\NEXT.md` (PC only).

- **Pack:** `shaders/QuestForge`, Iris/Angelica only.
- **Budgets per frame:** High 1440p 3 ms · Low 1080p 0.9 ms · Potato 720p 0.4 ms.
- **Lab:** https://marionwhite.github.io/quest-forge/shaders/. Rounds are in `site/shaders/rounds/rNNN.json`; feedback is in
  `docs/design/shaders/feedback/rNNN.json` with images in `attachments/rNNN/`. Taste is in `docs/design/shaders/look-bible.md`.
- **Round in progress:** r012 shader scenes handed off (`C:\qfb\shaderdev\r012\` spec_scenes.py, SHADERS-READY, 4 scenes);
  critic and publisher next. Pack: Photon atmosphere with gold sun tint (QF_SUN_GOLD 1), sun glow (QF_SUN_BLOOM 2), near
  air clear to 32 blocks (QF_PH_NEAR 32), round 10's rays (QF_CREPUSCULAR 1), lean storm meteors (QF_METEOR_STYLE 5,
  QF_METEOR_LEAN 1), gem SSR merged off (QF_GEM_SSR 0, +0.17 ms on gem walls).
- **Over budget:** High ocean_sunset 3.65 ms (round 10's rays +0.30), lake 3.23, sea/swamp water 3.08-3.18.
- **Later:** cheaper round-10 rays (fewer taps or Photon's march with r010's lanes); shore_sunset still salmon (sun on
  the horizon); Conquest's per-biome fog/sky tint, nether/end lightmaps, aurora (r011-shader.md note).
- **Debug views:** QF_DEBUG_VIEW 9 colortex5 raw; 11-14 water (sun/Fresnel/depth, bed, transmitted, reflected); 15 rays, cloud map, sky.
- **Standing rules:** render with the current QF textures zip; vanilla only as a control. Every Lab question states the
  cause and the trade-off with numbers.
- **References (internal only):** `C:\qfb\shaderdev\refs` (Complementary, BSL, Photon on our views).
- **Render queue night mode** 22:15-08:00: shot jobs only.
- **Tools:** `tools/renderq`, `tools/shaders/review/finish_round.py`, `check_glsl.py`, `make_clip.py --speedup`.
