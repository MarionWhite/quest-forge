# r011: port Photon's sky (shader-dev, 2026-10-27)

Read first: ops/checkpoints/r011-plan.md (owner's r010 verdict and picks; the licence facts), then the shader track
file and the r010 shader checkpoint for budgets, bench_round.py and renderq use.

## The owner's direction (r010)
"We need to start just copying from the packs that are doing things right, and then we can try to improve upon
them." Stop inventing techniques and micro-tuning: port working code, then tune to our budget.

Photon 1.4 (`C:\qfb\refpacks\photon-shader\dl\photon_v1.4.zip`, official Modrinth file) permits modifying and
redistributing portions, including in a modpack, except on paid platforms; keep its LICENSE with any substantial copy
(add it under shaders/QuestForge/ with a credit line naming the files ported). Complementary forbids edits in a
modpack: read it, never copy it. BSL: check its licence before copying anything.

## Work, in order
1. **Sunset/atmosphere** (owner, sunset-full 3/5: "The sun reads as a single hot spot rather than affecting the
   lighting of the whole atmosphere in a realistic way"). Port Photon's atmosphere: `include/sky/atmosphere.glsl`
   with its precomputed scattering LUT (`image/atmosphere/scattering.dat`), so a low sun colours the whole sky and
   the light reaching the ground. Angelica is an Iris port: check how the LUT gets loaded (custom texture in
   shaders.properties) and that Angelica supports it; if not, bake it to a PNG.
2. **Crepuscular rays** (sun-cloud: B, "the rays make a pretty big difference, but only if we can afford them").
   Port `include/sky/crepuscular_rays.glsl` if it is cheaper or better than ours; either way it must fit High's
   3.0 ms with the atmosphere.
3. **Meteors** (meteors: B storm, 3/5). Reference photos: docs/design/shaders/feedback/attachments/r010/ (a shower:
   many long, thin, straight streaks radiating from one point, faint, against the Milky Way). "It looks like we need
   to figure out how to improve performance again": night_wide was 3.47 ms (24 slots) and 3.98 (storm, 40 slots),
   because every sky pixel tests every slot. Find out how Photon/BSL/Complementary draw shooting stars (if any) and
   copy the cheapest that works; otherwise cut the per-pixel cost (cull slots per screen tile, or test only
   the few slots near the pixel). Must be under 3.0 ms on night_wide at High.
4. Measure everything on the standard scenes (bench_round.py, cost mode) with the cost per change as a number.
5. Hand the r011 scenes to `C:\qfb\shaderdev\r011\` (spec_scenes.py like r010). Small round: atmosphere/sunset,
   sunbeams, meteors, each against r010, with cost. Nothing else.

Keep, don't re-ask (owner's r010 picks): underwater A, river A (must stay distinct from ocean and coast), gold A,
checks C, forest-light B, QF_VOL_FAST on.

## Progress log
