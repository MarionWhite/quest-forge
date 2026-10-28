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
- 22:45 rays cause found (r11d15, debug 15): the map works (g shows the cloud shapes, shadow round the hidden sun) but
  the rays were ~0.003 radiance: QF_CREP_I 0.05 was ~1 % of the sky (Photon's light_color is ~7x ours and its
  coverage-driven "amount" isn't modelled). QF_CREP_I default 0.3 [0.15 0.3 0.6 1.0]. Committed **ada996a** (WIP,
  all r011 shader work so far). Shot **1027-224435-r011-loop3-shot**: r11e defaults (ocean_sunset, golden_lit,
  forest_golden, lake_glitter, shore_sunset, shore_dusk, dawn_wide, dust_b, beach_noon), r11e6 (CREP_I 0.6), r11e0
  (rays off) on ocean_sunset, forest_golden, lake_glitter, shore_sunset.
- 22:46 handoff files written: C:\qfb\shaderdev\r011\spec_scenes.py (3 scenes: sunset-full A p11 ocean_sunset / B p10 /
  C p11 shore_dusk / D p11a0 shore_dusk; sun-cloud A p11 / B p11cr0 / C p11cr1 on RAYVIEW (set after loop 3);
  meteors ov clips p11clipm4 / p11clipm5 / p10clipg3, cost MG from p11clipg3) and round.json (replace
  PUBLISH-COST-ID with the p11 cost submission id). Cost spec C:\qfb\shaderdev\r011\specs\p11-cost.json.
- 22:47 **Publish-cost run submitted: 1027-224601-r011-publish-cost** (specs/p11-cost.json, pack = ada996a + QF_CREP_I
  0.3 + debug view 15; runs after 08:00, night mode). round.json points at it. Exiting here: loop3 (1027-224435) is
  ~20 min behind the texture agent's jobs.
  **Next (fresh agent):**
  1. `renderq.py results 1027-224435-r011-loop3-shot`; sheet r11e vs r11e0 vs r11e6 (rays: lanes near the sun in
     ocean_sunset box 970,505,480,270, lake_glitter, shore_sunset, forest_golden) and r11e golden_lit vs r11b1/p10 (is
     the near field still veiled at land x1.41?). Tools: C:\qfb\shaderdev\r011\tools\sheet.py, boxes.py, clipmax.py.
  2. If a default changes (QF_CREP_I, QF_PH_FOG, the fog scaling): edit, check_glsl, commit, then resubmit the cost
     run with `renderq.py submit --replace C:/qfb/shaderdev/r011/specs/p11-cost.json` and update round.json's id.
     Set RAYVIEW in spec_scenes.py to the view where the rays read best.
  3. After 08:00 the cost lands: atmosphere cost = p11 - p11a0, rays = p11 - p11cr0 (r010 rays p11cr1), meteors
     p11clipm4/m5 vs p11clipg3 (target night_wide < 3.0 High). If over budget, cut QF_CREP_STEPS or the wedge count.
  4. critic (r011/critic.json), then publisher: `finish_round.py C:/qfb/shaderdev/r011 --publish`.
  5. Track file + journal entry + the five-line report (scenes handed off in C:\qfb\shaderdev\r011\).
- 2026-10-28 (finisher) loop 3 read (sheets r011/sheets/loop3_rays.jpg, loop3_raysbox.jpg, loop3_raydiff.png x6 diff,
  loop3_golden.jpg, loop3_golden_refs.jpg): **rays invisible** (r11e - r11e0 +1-3 luma near the sun, faint radial lanes
  only in the x6 diff; e6 barely more). Cause: Photon's term only adds light on a sky that already holds the lit air's
  glow. **golden_lit near field still veiled**: bottom-row means r11e 66,64,39 vs p10 40,45,15; r11a1 (x1 density) is
  already 62,63,35, so it is Photon's own evening Mie haze (0.005/block, half every 7 blocks) over grazing-lit grass,
  not our x1.41. Left as is (later item; CR's near field is also lifted, 91,57,25, but warm).
  **Costs** (1027-224601, High 1440p): worst p11 ocean_sunset 3.30 (p10 3.31; water scenes 3.01-3.16 were over in r010
  too); atmosphere p11-p11a0 -0.12..+0.03; rays p11-p11cr0 +0.01..+0.06 (r010 rays +0.14..+0.31); night_wide 2.99
  (shower m4 and storm m5 both 2.99) vs r010 3.47/3.98 (p11clipg3 3.99); Low worst 0.86, Potato 0.30.
  Loop 4: QF_CREP_SHADE 0.5 (new): sky dimmed by (1-lit share) x (1-T to cloud base) x 0.5. check_glsl 0 errors.
  Cost spec r011/specs/p11r-rays.json (p11r on 8 ray views, p11r75 SHADE 0.75 on 4); spec_scenes then uses p11r for
  ocean_sunset / shore_dusk / RAYVIEW (p11cr0, p11cr1, p11a0 unaffected by the change).
