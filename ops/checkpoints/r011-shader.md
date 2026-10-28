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
- 2026-10-27 22:05 (step 1 atmosphere, uncommitted): Photon 1.4 extracted to C:\qfb\refpacks\photon-shader\src.
  Angelica 2.2.33 parses raw TEXTURE_3D customTexture (RawData3D, RGB16F, HALF_FLOAT in its enums), so the LUT ships
  as is: shaders/textures/qf_scattering.dat (+ .mcmeta), customTexture.qfScatter in shaders.properties. Offline
  check (C:\qfb\shaderdev\r011\tools\atmo_sim.py, sim/cmp.png): Photon's LUT is in our sky-view units (zenith 0.8-1.2x
  ours, sun 60..0 deg), so it drops into prepare's sky-view tables (no per-pixel cost). New lib/photon.glsl (ported:
  LUT lookup + horizon stretch + nvidia Mie phase + saturation boost, sun tint/exposure by the hour incl. blue-hour
  boost, analytic air fog with Photon's per-hour Mie densities). QF_ATMOS [0 1] default 1: prepare sky-view + C_SUN
  from Photon; sky.glsl gold-sky / golden-band hacks off; composite applies Photon's air fog to land AND sky (night
  keeps r010's fog, blended by phNight). LICENSES/photon-LICENSE.txt + README credit. check_glsl 0 errors.
  Shot **1027-220513-r011-atm1-shot** (r011/specs/r11-atm1.json): r11a1 ocean_sunset, golden_lit, forest_golden,
  shore_sunset, shore_dusk, dawn_wide, lake_glitter, sky_noon, beach_noon, biome_hills; r11a0 (ATMOS 0) shore_sunset,
  shore_dusk, dawn_wide. Baselines: bench-p10-* and refs/screenshots/bench-refcr|refbsl-*.
  Tools: C:\qfb\shaderdev\r011\tools\sheet.py (contact sheets: OUT W "label=path[@x,y,w,h]" ..., COLS env).
- 22:20 (steps 2-3, uncommitted): **meteors** QF_METEOR_STYLE 4 (new default) / 5 storm in lib/sky.glsl meteorsSector():
  radiant 18-45 deg up (RAZ pins bearing), sky cut into 96 (storm 240) wedges round the radiant by position angle,
  one slot per wedge with its own clock; a pixel tests its wedge + 2 neighbours (3 slots, r010: 24/40). r009 physics
  (great circles, len ~ sin(dist), power-law brightness, trains). Shot **1027-220703-r011-met1-shot** (r11m4c, r11m5c
  clips night_wide RAZ 135 SLOW 0.25, crop 640,360,1280,720; r11m4d RAZ 45 full frame 100 fr).
  **Rays** QF_CREPUSCULAR 2 (default, Medium+): Photon's crepuscular_rays.glsl ported: cloud shadow map 64x64 in
  colortex5 x192-255 y96-159 (lib/lut.glsl, sqrt-spaced light-normal plane, +-4096 blocks, built in prepare from
  cloudDens at 2 slab heights), composite crepuscularRays(): march eye -> cloud base (<= 4096), QF_CREP_STEPS
  (High 20 / Medium 12) at horizon -> 4 zenith, sh^3 * T * b(d), Photon two-lobe phase, x lightIrradiance x QF_CREP_I
  (0.05). Shot **1027-221114-r011-crep1-shot** (r11c05 / r11c20 at CREP_I 0.2). check_glsl 0 errors (defaults,
  ATMOS0+CREP1, CREP0+STYLE5, STYLE1+CLOUDS1).
  NOTE: renderq night mode runs 22:15-08:00 (shot only): every COST number must wait for 08:00.
- 22:18 atm1 read (sheet C:\qfb\shaderdev\r011\sheets\a1_sunset.jpg; 4x4 box means via r011/tools/boxes.py): r11a1 is
  pinker (Photon's evening tint) and twilight is far better (shore_dusk: blue hour with a pink horizon vs a0 near
  black), but ocean_sunset still reads "hot spot": the far haze band 139,109,97 vs CR 212,160,120, sea navy. Cause:
  bench renderDistance 8 (far 128), Photon's densities assume 16-32 chunks. Loop 2: density x max(1, 256/far) x
  QF_PH_FOG (new option, 1.0), and water sky reflections fogged (phFogSky in lib/photon.glsl, both water paths).
  Shot **1027-221723-r011-atm2-shot** (r11b1 defaults; r11b2 QF_PH_FOG 2.0). Cost spec drafted:
  C:\qfb\shaderdev\r011\specs\p11-cost.json (submit once the pack is final; runs after 08:00).
- 22:21 met1 read (C:\qfb\shaderdev\r011\sheets\met1.jpg max-over-time, met1f.jpg frames; r011/tools/clipmax.py):
  geometry right (straight streaks radiating from one point, like both photos; RAZ 45 puts the radiant overhead like
  photo 2); storm 47.7k streak px over the clip vs r010 storm 12.9k. Wrong: streaks 5-8 px wide with bloomed comet
  heads, short, plain starry night. Loop 2: brightness cap 7 -> 3.5, width 1.2-1.8 -> 0.85-1.15 px, len +50 %, trail
  lit along ~all its length, smaller head; shower nights (style >= 4) now show the Milky Way. Shot
  **1027-222132-r011-met2-shot** (r11n4c, r11n5c, same views as m4c/m5c).
- 22:40 reads: **atm2** (sheet r011/sheets/atm2.jpg): the low sun now lights the haze across the view (lake_glitter,
  forest_golden glow; ocean_sunset far band 146,112,98 -> sea purple-navy, reflects pink sky), but golden_lit's near
  field went grey-veiled at x2 density. Loop 3 (uncommitted): land density x sqrt(256/far) (1.41 at 8 chunks), sky
  pixels, chunk-edge fade and water reflections look through phSkyLen() = max(far, 256) blocks.
  **met2** (r011/sheets/met2.jpg): thin long streaks out of one radiant over the Milky Way; close to the photos.
  Shower style 4 default, storm 5 the Lab option. Best still frames: r11n4c f020, r11n5c f061.
  **Rays (crep1) BUG**: r11c05/r11c20 identical to r11a1 to 0.2 luma. Debug view 9 (r11d9) shows the cloud shadow map
  region is written (mostly open). New QF_DEBUG_VIEW 15 (composite: r rays x4, g map at 500 blocks, b sky) shot
  **1027-223210-r011-dbg15-shot** (r11d15 ocean_sunset), queued behind the texture agent's 58-step job (~23:05).

### Note from texture-dev #2 (r011 packs, 2026-10-27 22:40): Conquest's environment is shader-side
The owner wants Conquest_'s "environmental lighting and effects ... the visual effects of being in specific other
environments" (not underwater: done). Checked what reaches the screen under our shader:
- **Not as files.** Live mcpatcherforge.cfg has `custom_colors` and `better_skies` OFF, and our shader discards vanilla
  sky geometry (GB_SKY) and never reads fogColor / skyColor / the lightmap texture. So Conquest's 26 MCPatcher sky
  layers (C:\qf-world\reference-packs\Conquest_\Conquest_1.8.zip, assets/minecraft/mcpatcher/sky/world0: aurora
  `northlight*.png`, `sky_shootingstar.png`, `sky_sunflare*.png`, `sky_starfield.png`, sunrise/sunset boxes),
  its per-biome fog and sky colours (mcpatcher/colormap/fogcolor0.png, skycolor0.png; color.properties) and its
  lightmaps (mcpatcher/lightmap/world0.png, world-1.png nether, world1.png end) would do nothing.
- **What would carry it into our pack (your call, shader track):** (1) per-biome fog/sky tint: sample Conquest's
  fogcolor0/skycolor0 colormaps by biome temperature x rainfall (they are 256x256 vanilla-style colormaps) as a
  uniform-driven tint on our fog; (2) the nether/end lightmaps as the torch/ambient colour for those dimensions;
  (3) the aurora layer (northlight, ~night, cold biomes) as a sky texture in deferred. Files may be copied into the
  private pack (owner's call, CLAUDE.md "Licences"), never committed.
- **Shipping as files now (texture side, QF-r011-packs.zip):** particles.png (its bubbles, splashes, smoke),
  footprint.png, rain.png, snow.png, and its ambient cave and rain sounds.
