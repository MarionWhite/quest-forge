# Brief: clouds

The raymarched deck: shape, light, resolution, history, shadows, and what Low gets instead.
Read with [`README.md`](README.md).

## 1. What the owner asked for

- r003 hills: "I'm not loving the color range, the environment, or the clouds that you have come
  up with. I think you should search for some inspiration for the clouds."
- r004 clouds (D dramatic broken clouds, 5/5): "I don't want it to look like a png of this
  pasted onto the sky. I would want something more dynamic that looks beautiful and natural.
  I want this pack to have a truly beautiful sky."
- r005 clouds (A, 4/5): "a very good start, but we have a lot of ground to cover to get to
  perfect." golden (A, 4/5): "if the clouds' lighting was also affected by the hour then it
  would take the scene to the next level." night-new (A, 3/5): "The clouds look kinda weird at
  night."
- r006 clouds (A, 4/5): "They definitely look better, but we have some room for improvement."
  golden (A, 4/5): "maybe more of a sharper highlight effect on the edges of the clouds for
  more of a cinematic effect." sunset-sky (A, 5/5): "The clouds have improved, but not as much
  as the water has." night-new (A, 5/5): "The night clouds look pretty good and have shape."

Shape and hour-light are accepted; he wants crisper rims, more beauty, and no regressions at
night. The look bible adds cloud shadows, day-to-day weather, and rain that darkens them.

## 2. What we do now

`lib/sky.glsl`, `QF_CLOUDS 2` (r005, rebuilt r006). A slab `CL_BASE 300` to `CL_TOP 470`
blocks, `CL_SCALE 1/520`, extinction `CL_SIGMA 0.16` per unit density.

- **Shape** (`cloudDens`): a 2D base from two `qfNoise.b` smooth fields at unrelated scales,
  bent by a 3D warp from `noise3t` (the one-fetch 3D value noise), plus a `noise3t` term; the
  threshold climbs with height (`cloudThreshold() + 0.55 h^1.3`, a small lip at the base) so
  sides lean and tops dome; three octaves of `noise3t` erosion scaled by height. Coverage per
  day from `hash12(worldDay)` (threshold 0.45 to 0.52), thinner at night (+0.07), rain 0.33,
  `QF_CLOUD_COVER` offset. All noise is `qfNoise` (one fetch per lookup).
- **March** (`cloudMarch`): `CL_STEPS` 24 High, 16 Medium, 9 Low, 4 Potato over at most 520
  blocks of slab; stride 1.5 dt in air, 0.6 dt in cloud; IGN jitter per pixel and frame
  (TAA resolves it); exit at transmittance 0.02; fade `exp(-t0/6500)` toward the horizon.
  Per cloud sample, three light taps at 16, 60 and 190 blocks toward the light (Potato two).
- **Light** (`cloudLight`, `cloudPhases`, `cloudLum`): sun or moon irradiance from the LUT
  constants (`sunIrradiance()`), kept lit to 0.07 below the horizon and tinted (1.18, 0.86,
  0.56) at golden hour; sky ambient from `C_AMB_UP` above, and below it the warm horizon sky 60
  degrees round from the sun (a `lookupSkyView` tap) scaled by `goldenHour()`. Wrenninge
  octaves: contributions 1, 0.52, 0.2704 against extinction scales 1, 0.42, 0.1764, phase g
  shrinking by 0.55 per octave (two-lobe HG 0.82 / -0.20 mixed 0.62). Powder
  `1 - 0.7 exp(-0.9 od - 2 dens)`. `QF_CLOUD_RIM`: a g 0.92 fringe lobe where the cloud is
  thin both ways. Night: bodies darkened by `exp(-0.8 od)` so only rims carry moonlight.
- **Shadows** (`cloudShadow`): one density tap at a quarter of the slab height, 0.6 strength,
  per lit terrain pixel. **Reflections**: `applyCloudsCheap`, two taps.
- It runs **per sky pixel at full resolution** inside `skyRadiance` in `deferred`. There is no
  cloud buffer and no history; TAA on `colortex4` is the only accumulation.
- `QF_CLOUDS 1` is the r003 flat deck (`applyClouds`, fBm, self-shadow by a tap toward the
  light), still compiled but unused; `performance-rules.md` rule 7 says Low and Potato get
  2D clouds, while `settings.glsl` gives them 9 and 4 raymarch steps. Resolve one way.

Cost **[measured]**: six Potato steps put `night_sky` at 0.42 ms (budget 0.4), hence four.
The High share is not isolated; round 6's worst frame was 2.3 ms with everything on.

## 3. What the top packs do

- **Horizon Zero Dawn, Schneider 2015** [V, slides,
  https://d3d3g8mu99pzk9.cloudfront.net/AndrewSchneider/The-Real-time-Volumetric-Cloudscapes-of-Horizon-Zero-Dawn.pdf]:
  128^3 base texture (Perlin-Worley plus three Worley octaves), 32^3 Worley detail, 128^2 curl
  noise; a weather map with coverage, precipitation and cloud type; three height-gradient
  presets; the volumetric layer between 1500 and 4000 m, 2D cirrus and alto above; 64 steps at
  the zenith to 128 at the horizon, cheap samples until a cloud is hit, one step back, full
  samples inside, exit at alpha 1, back to cheap after several empty samples; six light
  samples in a cone, five near and one far for distant cloud shadows, cheap light samples once
  alpha passes 0.3 ("2x faster"); Beer's law, the "powder" darkening, Henyey-Greenstein, extra
  absorption for rain clouds; colour = ambient rising with height + sun, attenuated to the
  atmosphere by depth. 20 ms brute force became about 2 ms by updating one pixel in each 4x4
  block per frame in a quarter-resolution buffer with reprojection.
- **Frostbite, Hillaire 2016** [V, PDF
  https://media.contentapi.ea.com/content/dam/eacom/frostbite/files/s2016-pbs-frostbite-sky-clouds-new.pdf]:
  a cloud-type texture (density over height, erosion amount); the energy-conserving step
  integral S (1 - exp(-sigma_t d)) / sigma_t; four shadow samples at a base distance times a
  growing factor; per-frame jitter blended by an exponential moving average and reprojected;
  a dual-lobe HG phase; Wrenninge's octaves with the rule **a <= b** (contribution scale must
  not exceed extinction scale) or energy is created; clouds affected by aerial perspective and
  aerial perspective attenuated by cloud cover. Xbox One: 0.91 ms at 720p, 1.60 ms at 1080p
  for the main view, worst case at the horizon.
- **Nubis Evolved 2022 / Nubis Cubed 2023** [V via search,
  https://advances.realtimerendering.com/s2022/SIGGRAPH2022-Advances-NubisEvolved-NoVideos.pdf,
  https://advances.realtimerendering.com/s2023/Nubis%20Cubed%20(Advances%202023).pdf]: 2D
  modelling fields decompressed vertically at render time; about 2 ms; 0.2 to 5 ms when flying
  through.
- **Photon** [V, published `shaders.properties`]: layers for cumulus, altocumulus, cumulus
  congestus, cirrus with a cirrocumulus sub-option, and noctilucent clouds; a blocky option;
  rendering at full, half, third or quarter resolution with temporal upscaling; a 512x512
  cloud shadow map; 3D Worley textures; "different skies each day" (README). **Kappa** [V,
  https://wiki.rre36.com/wiki/Kappa_Shader]: volumetric cumulus plus planar cirrus, cloud
  shadows on terrain and fog ("much more authentic"), clouds in reflections, temporal
  checkerboard upscaling with a target resolution; cumulus and cloud shadows are its biggest
  costs. **Complementary Unbound**: volumetric, with a blocky option [V, site]. **Sundial
  Lite** [V]: realistic or blocky, plus a 2D plane and shadows. **SEUS PTGI E12**: cirrus and
  cumulus with coverage varying over long periods, lit by the same functions as the sky [U,
  Patreon post via search snippet]. **RRe36** considered a third volumetric layer for
  high-altitude clouds [V, https://rre36.com/?p=3655].

## 4. The technique

Our shape and light are already HZD/Frostbite in outline. Four changes, in order of effect
per millisecond.

**A. Energy and phase (cheap, do first).** Replace `S += T * lum * (1 - Ts)` with Frostbite's
integral `S += T * lum * (1 - Ts) / max(sigma_t, eps)` written per step with `lum` as the
scattered radiance per unit length (so the result is independent of step count; today a
step-count change changes brightness). Fix the octaves: our a 0.52 > b 0.42 breaks a <= b;
use a 0.5, b 0.5 (or a 0.4, b 0.5) and re-tune `* 2.2`. Keep the two-lobe phase. For the
owner's "sharper highlight on the edges", the physically right lever is the forward lobe at
the fringe: thin cloud has optical depth under 1 toward the sun, so the first octave's
`exp(-od)` is large exactly there; draw it with g 0.85 to 0.9 and let `QF_CLOUD_RIM`'s hand
term shrink. Light taps: use Frostbite's progressive four (base 12 blocks, factor 2.2: 12, 26,
58, 128) jittered within each span, instead of three fixed.

**B. Resolution and history (the real win).** Render the clouds once per frame into a
quarter-resolution buffer and reproject, as HZD and every pack above do, instead of per sky
pixel at full resolution.

```
pass "clouds" (deferred stage, before lighting; scale 0.25 via size.buffer.colortex6 = viewWidth/4 viewHeight/4, RGBA16F):
  for each cloud texel: ray from the camera; if the full-res depth at the texel centre is not sky, skip
  march as today with CL_STEPS 24 (High), checkerboard: update 2 of 4 texels per frame (frameCounter parity on x+y)
  result (S.rgb, T) is blended with history:
     history uv = project(previous matrices, camera + dir * t_mid) where t_mid is the ray's hit with the slab's middle plane
     (no per-pixel depth needed: the deck is 300 blocks up, so camera translation is sub-texel)
     w = 0.1 when the history texel was sky last frame and inside the screen; 1.0 otherwise
     out = mix(history, current, w) for updated texels; history for skipped ones
apply (deferred lighting pass, sky pixels): bilinear fetch of colortex6, rejecting the 4 taps whose full-res depth is not sky,
     L_sky = L * T + S
```

The buffer written once per frame reads stale under ping-pong (trap 4); either write it in
two passes (compute then copy, as `prepare1` does) or read and write the same texel in one pass
and accept Angelica's flip (debug view 8 shows which happens). This is the 2x2 checkerboard
rule 7 asks for; HZD's 1/16 is more aggressive than TAA can hide at our frame rates.

**C. Shadows and reflections from one small map.** Build a 256x256 **cloud shadow map** in
`prepare` each frame: world XZ around the camera, 2 x shadowDistance across, one density
integral per texel along the light through the slab (four taps). Terrain lighting
(`shadeSurface`), light shafts and the water then take one bilinear fetch each, consistent
with what is overhead. Water reflections keep `applyCloudsCheap` (two taps) or read the
quarter-res buffer by reflected direction when the reflected ray points up.

**D. Modelling for beauty.** The owner's "truly beautiful sky" is a question of silhouettes.
HZD's base is a 128^3 Perlin-Worley volume; our 2D-slice `noise3t` gives about seven distinct
layers before it wraps, which is why tops read as sheets from some angles. If a raw
`TEXTURE_3D` custom texture loads under Angelica (README trap 11, test first), bake a 128^3 R8
Perlin-Worley base and a 32^3 RGB Worley erosion with `make_textures.py` (2 MB + 0.1 MB) and
use HZD's remap: base = remap(perlin, worleyFbm - 1, 1, 0, 1), then times the height profile,
times coverage, then erode the edges by the detail noise mixed by height (billows up, wisps
down), with 2D curl noise distorting the detail. Weather: coverage, type and precipitation as
a 512x512 function of world XZ drifting with the wind, re-seeded per `worldDay` (the
"different skies each day" the owner liked in principle; rain raises precipitation and
darkens by extra absorption as HZD does). Add a **2D cirrus plane** at a second altitude: one
fBm fetch stretched along the wind, lit by a strong forward lobe (ice is bright near the sun):
this is where cinematic silver linings come cheaply, and it fills empty skies.

Light by the hour (owner r005): take the sun's irradiance at the deck's altitude from the LUT
(`lightTransmittance(cameraRadius() + 0.3 km, sunDir)`) instead of the smoothstep and tint; a
deck 300 m up is lit, orange, for minutes after the ground sun sets, which is the real
"golden undersides". Night: the moon through the same path, bodies dark (kept).

Aerial perspective on clouds (Frostbite 5.9.1): attenuate S by the transmittance to the mean
cloud distance and add the aerial in-scatter; and the sky's in-scatter under a heavy deck
(5.9.2) should drop with mean coverage. See sky.md for the aerial LUT.

## 5. Low and Potato

Per rule 7: **Low** gets the 2D deck (`QF_CLOUDS 1` path: coverage fBm, a self-shadow tap, no
N.L, lit by the hour from the LUT) plus the cirrus plane; both are one or two fetches per sky
pixel at full resolution, no buffer. Cloud shadows from the same 2D field (one fetch).
**Potato**: the 2D deck only, three octaves, no shadow. If measurement shows the quarter-res
raymarch at 8 steps is cheaper than today's 9 full-res steps on Low, Low may keep it; it has
TAA. Potato has no TAA and must not jitter.

## 6. Cost

- **[measured]** Potato: 6 steps 0.42 ms on `night_sky`, 4 steps inside 0.4. Frostbite: 0.91
  ms at 720p on Xbox One (full-res, 14 to 21 samples); HZD: about 2 ms on PS4 with 1/16
  update; Nubis Evolved about 2 ms.
- **[estimate]** Today at 1440p High on `sky_noon` (sky about 60% of pixels, 24 steps, three
  light taps): 0.4 to 0.8 ms. Quarter-res with a 2x2 checkerboard: one eighth of the samples
  per frame, 0.06 to 0.12 ms plus 0.03 ms apply, plus 0.01 ms for the shadow map. 3D textures
  cost nothing extra per fetch versus `noise3t` and save one fetch each.
- Measure: `--scenes sky_noon,golden_lit,forest_golden,ocean_sunset,night_new,night_full,
  plains_noon` with `--opt QF_CLOUDS=0`. Watch the 1% low: the march is the pack's most
  variable loop (horizon views are the worst case).

## 7. Test scenes and reference photos

Views: `sky_noon` (overhead, the brush-streak test), `golden_lit` and `forest_golden`
(hour-light), `ocean_sunset` and `shore_sunset` (rims against a low sun), `dawn_wide`,
`night_new` and `night_full` (dark bodies, moonlit rims), `night_sky`, `biome_hills`
(clouds over terrain, shadows). Photos: Category:Cumulus clouds [V] with subcategories
"Cumulus humilis clouds", "Cumulus mediocris clouds", "Cumulus congestus clouds", "Cumulus
fractus" and "Cumulus clouds at sunset"; Category:Crepuscular rays at sunset [V] for rims and
rays together; Category:Belt of Venus [V] for twilight decks. Cirrus and mammatus categories
were not checked [U].

## 8. Pitfalls

Angelica: the quarter-res buffer is single-writer (trap 4); mips are not rebuilt in `prepare`
(irrelevant unless the shadow map is mipped); raw 3D textures are untested (trap 11); the sun
and moon disks must be drawn before clouds are applied so a cloud occludes them (today's
order is right); Potato has no TAA, so any jitter there is visible noise. Technique: sheets
and streaks from under-sampling along the ray (the r005 lesson: short steps inside cloud);
energy creation when a > b; grey mush when ambient is too strong; glowing night bodies (owner
r005) unless the night term stays; horizon aliasing without the fade; checkerboard history
ghosting when the deck moves fast (wind 3 blocks/s is fine, storms are not); the "pasted PNG"
look whenever erosion is 2D only.

## 9. Licences

| Source | Terms | Use |
|---|---|---|
| Schneider 2015 (Guerrilla, SIGGRAPH Advances); Nubis 2017, 2022, 2023 | talks | method |
| Hillaire 2016 (Frostbite, SIGGRAPH PBS course) | talk; it offers a noise generator whose licence I did not check [U] | method; our own generator |
| Wrenninge, Kulla, Lundqvist 2013, "Oz: the great and volumetric" | SIGGRAPH talk | the octave approximation |
| Worley 1996, Perlin 1985/2002, Bridson 2007 curl noise | papers | algorithms |
| Photon, Kappa, Complementary, Sundial, SEUS | learn-only | feature survey |
