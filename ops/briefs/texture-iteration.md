# Brief: texture iteration v2 (agent: texture-dev)

- VERSION: v2. Output C:\qfb\textures\QFTextures-v2.zip (not committed).
- FEEDBACK: the tex-* scenes in docs/design/shaders/feedback/r008.json, plus attachments/. State: `ops/checkpoints/r009-textures.md`.
- FOCUS (owner: "Fix the leaves, fix the grass, fix the crops"; he expected a drastic improvement and did not see it):
  1. **Leaves**: bad in every option (3/5); B (edges) was "complete shit". Rework heavily.
  2. **Grass**: flat felt at close range (critic; r007's was crisp). Fix top and side.
  3. **Crops**: get as close as possible to the pack whose crops he liked, without copying it (study only; licence rules in CLAUDE.md).
  4. Metals: he liked B's metallic metals and diamond; iron and gold look unlit in A (texture-side albedo/spec, not light).
  5. Emerald block looks weird close up; keep B's stone brick.
  6. tex-golden: weird artifacting in all photos. Find it (CTM seams, mip bleed, leaf-edge overlay?).
  7. Items: books good; potions boring, give them personality.
  Metals cost constraint (see r009-shader): PBR map changes add no per-frame cost.

Done when:
- [ ] The build script and sources are committed; the licence ledger is updated in direction.md.
- [ ] Comparison renders are through renderq (specs/textures.json pattern).
- [ ] `C:\qfb\shaderdev\r009\texture_scenes.json` and `TEXTURES-READY` are written.
- [ ] ops/tracks/textures.md updated, one journal line.
