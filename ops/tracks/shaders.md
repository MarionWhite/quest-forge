# Shaders: current state

Rewrite this file when the state changes; keep it under 2 KB. History is in `ops/journal/shaders.md`
and the long archive in `C:\qfb\shaderdev\NEXT.md` (PC only).

- **Pack:** `shaders/QuestForge`, Iris/Angelica only.
- **Budgets per frame:** High 1440p 3 ms · Low 1080p 0.9 ms · Potato 720p 0.4 ms.
- **Lab:** https://marionwhite.github.io/quest-forge/shaders/. Rounds are in `site/shaders/rounds/rNNN.json`; feedback is in
  `docs/design/shaders/feedback/rNNN.json` with images in `attachments/rNNN/`. Taste is in `docs/design/shaders/look-bible.md`.
- **Round state:** r014 shader scenes handed off (C:\qfb\shaderdev014\SHADERS-READY, 6 scenes; cost 1031-204537,
  gems 1031-214418). Next: critic r014, then publisher. Defaults: QF_SEA_GRAZE 2, QF_RIM_GOLD 2, QF_METEOR_CULL 0.25 +
  HUE 1, QF_GEM_LOOK 2. QF_CLOUD_COVER 0.6 = cloud-free sky. QF_SUN_HALO (off) did not move the glow: it is the sky
  haze's forward lobe; a hotter halo means re-tuning the haze (owner question in the sun-glow scene).
- **Over budget (owner question, later round):** High sea sunset 3.56 ms (r013 3.52): the water is the cost; 11 of 24
  High views 3.04-3.60, all with water. Low ocean_sunset 0.95 (r013 0.92). Meteors 2.98 vs r012 2.94.
- **Later:** ocean/lake water cost; Conquest's per-biome fog/sky tint, nether/end lightmaps, aurora.
- **Debug views:** QF_DEBUG_VIEW 9 colortex5 raw; 11-14 water (sun/Fresnel/depth, bed, transmitted, reflected); 15 rays, cloud map, sky; 16 the final-pass sun glare alone.
- **Standing rules:** render with the current QF textures zip; vanilla only as a control. Every Lab question states the
  cause and the trade-off with numbers.
- **References (internal only):** `C:\qfb\shaderdev\refs` (Complementary, BSL, Photon on our views).
- **Render queue night mode** 22:15-08:00: shot jobs only.
- **Tools:** `tools/renderq`, `tools/shaders/review/finish_round.py`, `check_glsl.py`, `make_clip.py --speedup`.
