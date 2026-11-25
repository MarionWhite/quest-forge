# Brief: shader round 009 (agent: shader-dev)

- ROUND: r009. Work dir C:\qfb\shaderdev\r009.
- FEEDBACK: docs/design/shaders/feedback/r008.json, plus attachments/. Look at the images.
  Critic notes: C:/qfb/shaderdev/r008/critic.json. State to resume from: `ops/checkpoints/r009-shader.md`.
- FOCUS (owner, in order; he said "listen to the critic" on sun, golden-horizon, forest-light, dust and river: carry the critic's fix for each):
  1. **Performance is over budget** (worst 4.6 ms on High against 3.0; Low 1.32 against 0.9). The owner wants optimisation or a
     helper that stops the shaders and texture pack from hurting anyone's game. Do this first; see the checkpoint.
  2. **Metals: hard constraint.** Owner rated 2/5: "far from where we need to be, and our cost is very high here. We need to
     figure something out before getting too deep." Metals work must not raise High or Low cost, or it does not ship.
  3. **Dust in the beams** (3/5, his lowest): real drifting motes, a few px each, inside the lit shaft (critic: view dust_b).
  4. **Sun** (4/5, size is good): sharpen the limb, core ~1.5x hotter, wider warm glow (critic uh/uj/p8).
  5. **Sunset clouds must cover the sun** when they are in front of it (cloud density occludes the disk).
  6. **Golden horizon**: critic's fix, bright cream-peach to pink band, warm grazing light on lit slopes, no olive cast.
  7. **Forest light** (5/5): keep; kill the cream sky wash round the gap, more canopy contrast.
  8. **River** (3/5, "overcorrected a little"): critic's fix, clearer water near the banks, no ledge stripes, a sun glint.
  9. **Underwater**: green suits the swamp only; coast, ocean and river water need bluer light. Bubbles as rings, not squares.
  10. **Meteors: RESEARCHER TASK.** The owner: "research what an actual meteor shower looks like; it isn't just stuff flying in
      every direction". A `researcher` agent first writes `docs/design/shaders/research/meteor-showers.md` (real radiant
      geometry: streaks diverge from one radiant point and trace back to it; rate, speed, length, trains, colour, foreshortening
      near the horizon; sources). Shader-dev implements from that note only. Also fix beaded streaks and get a meteor into the stills.
  11. Lake (3/5), clouds, water biomes, biome borders, vibrance: keep; do not regress.
- Carry-overs from the critic: sky_noon radial smear and heavy deck; swamp far water too pale and flat.

Done when:
- [ ] Every ask is addressed, or explicitly deferred with a reason in the checkpoint.
- [ ] Renders submitted through renderq with the current QF textures zip in "defaults"; option labels are clear.
- [ ] `check_glsl.py` passes on all presets; budgets hold (ops/tracks/shaders.md): High 3 ms, Low 0.9 ms, Potato 0.4 ms. If they cannot, say so in the checkpoint with the measured numbers.
- [ ] Self-review against refs shows a visible leap on the owner's top asks.
- [ ] `spec_scenes.py` written in the round dir (scene text: what changed and why).
- [ ] Commits pushed-ready, ops/tracks/shaders.md updated, one journal line.
Then stop. The critic and publisher take it from there.
