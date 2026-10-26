# Brief: shader round NNN (agent: shader-dev)

Fill in ROUND, FEEDBACK and FOCUS; the rest stays as written.

- ROUND: rNNN. Work dir C:\qfb\shaderdev\rNNN.
- FEEDBACK: docs/design/shaders/feedback/r(NNN-1).json, plus attachments/. Look at the images.
- FOCUS: <the owner's top asks, one line each>

Done when:
- [ ] Every ask is addressed, or explicitly deferred with a reason in the checkpoint.
- [ ] Renders submitted through renderq with the current QF textures zip in "defaults"; option labels are clear.
- [ ] `check_glsl.py` passes on all presets; budgets hold (ops/tracks/shaders.md).
- [ ] Self-review against refs shows a visible leap on the owner's top asks.
- [ ] `spec_scenes.py` written in the round dir (scene text: what changed and why).
- [ ] Commits pushed-ready, ops/tracks/shaders.md updated, one journal line.
Then stop. The critic and publisher take it from there.
