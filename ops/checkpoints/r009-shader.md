# r009 shader checkpoint (orchestrator, 2026-10-26)

Brief: ops/briefs/shader-round.md. Input: docs/design/shaders/feedback/r008.json, critic C:/qfb/shaderdev/r008/critic.json.
Start state: r008 live (loop 4, 205d13c). Nothing for r009 started; no renders submitted.
Owner overall: no drastic improvement; over budget on performance; wants optimisation or a helper so nothing kills anyone's game.

## Order of work
1. **Researcher first (parallel, no render):** meteor-shower note at docs/design/shaders/research/meteor-showers.md (brief item 10).
   Shader-dev does not touch meteors until it exists.
2. **Perf:** r008 publish costs: worst frame 4.6 ms High (budget 3.0), Low 1.32 (0.9), Potato 0.30 (0.4, OK). Find the top
   cost terms (cost run with per-option off tags), cut or gate them, and propose the "helper": an auto-tier or option-gating
   rule that drops to a cheaper preset by measured frame time. Default changes that alter the look go to ops/DECISIONS.md.
3. **Metals (HARD CONSTRAINT):** r008 measured metal shading 3.47 ms vs off 3.41 in that frame (+0.06), but the owner rates
   the look 2/5 and calls the cost very high. Rule: nothing that raises High or Low cost. Evaluate in a cost run first:
   reuse the SSR already computed for water/composite instead of a metal-only pass; early-out outside MAT_METAL pixels; a cheap
   fallback (sky gradient + horizon band, no extra taps). Iron needs a visible reflection; the emerald noise must go.
   Decide with numbers before writing shading code; if it cannot be free, ship the cheap version and say so.
4. Look fixes in the brief's order: dust motes (view dust_b), sun limb and core, cloud-over-sun occlusion, golden band + grazing
   light, forest cream wash, river clarity/ledges/glint, bluer underwater for non-swamp water, sky_noon smear.
5. Meteors from the research note.

## Critic fixes to carry ("listen to the critic")
- sun: uh/uj/p8: sharper limb, core ~1.5x hotter, wider warm Mie glow, longer brighter sun path on the water.
- golden-horizon: uf/p8: cream-peach band fading to lavender, warm grazing light on lit slopes, keep grass green.
- forest-light: p8: kill the cream wash, more canopy contrast against the gap.
- dust: p8clipdust: real motes, a few px each, drifting through the lit shaft. Note p8d0 shows "off" also removes the beam haze.
- river: p8: clearer water near the banks, lose the ledge stripes, add sun glint.

## Rules
- Cost-mode renders run after 08:00; night mode is shot jobs only. Use renderq; never launch a client.
- Verify every "already fixed" claim against frames. Resubmit publish-cost with the final pack.
- Write spec_scenes.py and round.json for r009 in C:\qfb\shaderdev\r009.

## Progress log
(none yet)
