# Shaders: current state

Rewrite this file when the state changes; keep it under 2 KB. History is in `ops/journal/shaders.md`
and the long archive in `C:\qfb\shaderdev\NEXT.md` (PC only).

- **Pack:** `shaders/QuestForge`, Iris/Angelica only.
- **Budgets per frame:** High 1440p 3 ms · Low 1080p 0.9 ms · Potato 720p 0.4 ms.
- **Lab:** https://marionwhite.github.io/quest-forge/shaders/. Rounds are in `site/shaders/rounds/rNNN.json`; feedback is in
  `docs/design/shaders/feedback/rNNN.json` with images in `attachments/rNNN/`. Taste is in `docs/design/shaders/look-bible.md`.
- **Round in progress:** r008. Work dir `C:\qfb\shaderdev\r008`. Input is the r007 feedback and its 9 images. Owner's asks:
  - a bigger sun with a visible, formed disk, more than 1.8x;
  - dust only inside sunbeams, with no screen-wide white specks;
  - a stronger golden-hour horizon;
  - the lake fixed (rated 2/5, follow the critic);
  - the river's orange, flat near-surface dirt fixed;
  - metals that look polished under PBR;
  - vibrance around 0.25;
  - busier meteors;
  - **animated clips** in the Lab (meteors, water, clouds, dust);
  - Conquest-style underwater ambience.
  The owner expects a "massive leap".
- **r008 loop 4 (2026-10-26):** bug fixes committed (205d13c). The publish-cost run 1026-004242 predates them: resubmit it.
- **Standing rules:** render with the current QF textures zip; vanilla only as a control. Label options clearly (the owner was confused by C/D labels).
- **References (internal only, never on the site):** `C:\qfb\shaderdev\refs` holds Complementary Reimagined/Unbound and BSL on our 16 views.
  Photon doesn't render under Angelica.
- **Known:** the cyan-grey grass in biome_hills is that biome's own colour, not a shader fault.
- **Tools:** `tools/renderq` (render, cost, cache), `tools/shaders/review/finish_round.py` (spec and publish), `check_glsl.py`.
