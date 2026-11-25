# Brief: light shafts

Sunlit air through gaps: volumetric light. Read with [`README.md`](README.md); the medium it
scatters in is defined in sky.md section 4A.

## 1. What the owner asked for

- r000 fog: "a tundra would be awesome with a much heavier affect where vision is limited, and
  a mob could seemingly come out of nowhere amidst the storm." references: "dust particles to
  caves that are not obstructive ... rain that isn't just a bunch of particles ... the clouded,
  misted environment."
- r004 leaves (neither, 4/5): "I agree with the critic. I just expect more cinematic light."
  (the critic had missed round f's warm shaft through the trees).
- r005 forest-light (A, 4/5): "If we could sharpen the rays that come through without
  significantly intensifying the light source and washing out the sky then I would be on
  board." leaves (B, 4/5): the stronger shafts.
- r006 forest-light (C, round 5's, 4/5): "The color is warmer, the rays are better formed, but
  it is still far from perfect." water-sunset: "I don't know if I can detect the little dust
  particle things anymore."

He wants well-formed, warm beams between trunks, no veil over the sky, no brighter sun, and
visible (tasteful) motes in them.

## 2. What we do now

`program/composite.glsl` `lightShafts(viewDir, dist, eyeSky)`, in the single full-screen
composite pass, per pixel at full resolution, Low and up (`QF_SHAFTS > 0 && QF_SHADOWS`):

- `SHAFT_STEPS` 20 High, 12 Medium, 8 Low along the view ray to `maxD = min(dist, 96)`
  blocks, quadratic spacing (`f*f*maxD`, denser near the camera), one IGN jitter per pixel and
  frame (`frameCounter % 64`) that TAA resolves.
- Each step calls `shadowRaw`: one `texelFetch` compare on the distorted `shadowtex0` with
  bias 0.0004 (the manual compare, trap 1); outside the map's 0.98 clip box it returns lit.
- `lit` = the lit fraction (weighted `2f`), times `maxD` metres; `QF_SHAFT_STYLE 1` (the owner's
  pick) keeps it linear, style 0 raised it to the 1.8 power for contrast.
- Phase: 0.85 HG(g 0.78) + 0.15 isotropic. Scattering coefficient `sigma` = 0.0008 per block
  by day to 0.0038 at golden hour (`goldenHour()`), x `SHAFT_GAIN 1.5`, x (1 + rain). Colour:
  `lightIrradiance()` warmed by (1.30, 0.93, 0.56) at golden hour. Gated by `outside`
  (sky light at the eye) and `smoothstep(0, 0.06, L.y)`.
- Open-sky pixels get 0.8 of it and nothing on the disk itself (so the sun is not washed out,
  the r005 complaint). No cloud shadow in the march; the medium is constant along the ray and
  unrelated to the haze; no transmittance is accumulated (pure additive).
- Dust motes are separate: `ambientMotes`, 22 / 16 / 10 steps over the first 20 blocks, only
  in front of land or under water (`QF_MOTES`). The owner can no longer see them (r006).
- Potato: none (no shadow map).

Cost: not isolated **[estimate]** 0.15 to 0.3 ms at 1440p High (20 fetches per pixel plus
the distortion maths; the whole round-6 frame was 2.3 ms).

## 3. What the top packs do

- **Photon** [V, published `shaders.properties`]: a volumetric lighting master toggle and a
  light-propagation-volume variant with a step count and per-dimension intensities;
  atmospheric fog with Rayleigh and Mie densities by time and weather and falloff; coloured
  light shafts on Ultra (through coloured shadow maps); cloudy fog noise; border and cave fog;
  crepuscular rays as a separate sky setting (a screen-space effect, by its placement [U]).
- **Kappa** [V, https://wiki.rre36.com/wiki/Kappa_Shader]: volumetric fog with density, mist
  altitude, Mie anisotropy, maximum distance, sea level, falloff and "mist lighting steps";
  "water volume" god-rays under water; cloud shadows on fog.
- **Complementary**: light shafts with four quality levels in its profiles [V, from its public
  `shaders.properties` as read in `../performance.md`]. **BSL**: "volumetric light" [V,
  Modrinth]. **Sildur's Enhanced Default**: "god rays" [V, https://sildurs-shaders.github.io/].
  **Solas**: crepuscular rays [V]. **Rethinking Voxels**: "more VL" through its voxels [V].
  **Sundial Lite**: volumetric light and volumetric fog [V].
- **Mitchell 2007, GPU Gems 3 ch. 13** [V,
  https://developer.nvidia.com/gpugems/gpugems3/part-ii-light-and-shadows/chapter-13-volumetric-light-scattering-post-process]:
  a screen-space radial sum toward the sun's projected position with exposure, weight, decay
  and density controls, an occlusion pre-pass (occluders rendered black), and the known
  limits: depth ordering, flicker when occluders leave the screen, the sun off-screen or
  perpendicular.
- **Engelhardt and Dachsbacher 2010** [V, PDF
  https://faculty.digipen.edu/~gherron/references/References/LightEffects/VolumetricLighting/espmss10.pdf]:
  ray-march only along epipolar lines from the sun's projection to points on the screen border
  (1024 lines, 8 to 32 initial samples each), add samples at depth discontinuities found with a
  threshold search, then interpolate along each line with a 3 to 5 tap bilateral filter and
  between the two nearest lines; 5.8% of pixels ray-marched for an image indistinguishable
  from per-pixel marching; a light behind the camera works unchanged (the vanishing point);
  on a 2008 GPU at 1080p: lines 1.2 ms, discontinuity search 6.0 ms, marching 16.7 ms at 500
  steps, interpolation 4.4 ms; fewer lines blur the result.
- **Frostbite 2016** [V]: the energy-conserving step integral and temporal jitter with
  reprojection, used for its fog as well as clouds.

## 4. The technique

Single scattering through the same medium as the haze, with the shadow map as visibility:

```
L_shaft(pixel) = E_sun * p(cos theta) * integral_0^D  T(0,t) * sigma_s(t) * V(t) dt
   V(t) = shadow-map visibility * cloud shadow map;  sigma_s(t) = rho(y(t)) * albedo
   per step (Frostbite): S_step = sigma_s V (1 - exp(-sigma_t dt)) / sigma_t;  acc += T * S_step;  T *= exp(-sigma_t dt)
```

Because `E_sun` and the phase are constants per pixel, the march accumulates **one scalar**
(the shadowed in-scatter integral) and one transmittance; colour and phase are applied at
full resolution afterwards. That is what makes the quarter-resolution version cheap.

**Option A (recommended): a quarter-resolution volumetric pass.**

```
pass volumetrics (composite stage, before the water pass; scale.composite = 0.25 or size.buffer.colortex7 = viewWidth/4 viewHeight/4, RG16F):
  d_end = min(linear depth of depthtex0 at the texel, far)      (depthtex0 includes water, so shafts stop at the surface)
  12 steps (High) exponentially spaced from 0.5 to min(d_end, 1.5 * shadowDistance), blue-noise or IGN offset per texel and frame
  per step: V = shadowRaw(p) inside the map, else cloud shadow only; rho from the height fog; accumulate acc, T
  out = (acc, T)
pass water + fog (the present composite): shafts = E_sun * phase * bilateralUpsample(colortex7.r) applied after the aerial LUT, before the water? no: after the water (the water surface is in d_end already)
   upsample: 4 taps, weights by |linearDepth_full - linearDepth_quarter| / linearDepth_full with a 0.1 tolerance, falling back to the nearest tap
```

Rename passes so the budget holds: `composite` volumetrics (quarter), `composite1` water and
fog and apply (full), `composite2` TAA. High allows 5 composite programs, Low 3, so Low fits
exactly. The medium is sky.md's height fog, so a beam is the lit part of the very fog that
blues the distance; beams and haze then agree in colour and density by construction, which is
what the owner's "warmer, better formed" picks were groping toward.

**Sharper rays without a brighter sun** (r005): sharpness is the resolution of shadow
boundaries along the ray. Twelve jittered steps at quarter resolution with TAA, plus the
exponential spacing, resolve a trunk's shadow edge as well as twenty full-resolution steps
did, and the energy-conserving integral stops the lit metres from growing with step count.
Narrow the phase lobe toward the sun (g 0.8 dual-lobe with a 15% back lobe) and keep `sigma`
by day at 0.001 per block so open sky gets a faint veil, not a wash; golden hour 3x through
the aerosol term, not a separate gain. Drop the `pow(lit, 1.8)` contrast hack.

**Motes** (owner: make them visible, tastefully): keep `ambientMotes` but light them with the
same `V(t)`, so dust only sparkles inside the beams, and raise density where `acc` is high.
That is what real dust in sunbeams looks like, and it makes the beams read.

**Option B (Ultra experiment): epipolar sampling** for the forest scenes where the sun is in
frame. 512 lines x 16 samples in a 512x16 texture built in one pass, a discontinuity-search
pass, a march pass over the sample texture, then a full-screen interpolation. Crisper rays at
lower cost than A when the sun is on screen; three extra programs and a special case when the
sun is off screen (fall back to A). Only if A's beams smear in `forest_golden`.

**Option C (Potato only, optional): Mitchell's radial blur** on a quarter-resolution sky mask
(16 samples, decay 0.96, weight 0.3, density 0.9): a cheap "sun rays" effect for a tier with
no shadow map. Off by default; it fails with the sun off screen, so fade it out as the sun
leaves the frame.

**Under water**: the same march with the water coefficients and `V` from the shadow map
(the surface is not in the map because `shadowTranslucent=false`; approximate the surface's
shadow with the caustic field). Kappa's "water volume" is the reference look.

## 5. Low and Potato

- **Low**: option A at 6 steps, or off (rule 7 says volumetric light is off on Low; today Low
  pays for 8 full-resolution steps, which is dearer than 6 quarter-resolution ones).
  Measure both; a 1080p quarter-res march of 6 steps should be about 0.005 ms **[estimate]**.
- **Potato**: no shadow map, so no shafts; option C if the owner wants rays there.

## 6. Cost

- **[estimate]** Today, High 1440p: 0.15 to 0.3 ms (20 full-res fetches). Option A: 12 steps
  over 1/16 of the pixels, 0.02 to 0.04 ms, plus a 4-tap bilateral upsample 0.03 ms.
- **[measured]** Engelhardt 2010: 28 ms total on a Radeon HD 4850 at 1080p with 500 steps
  (a 2008 GPU; only the ratios transfer: marching 5.8% of pixels).
- Measure: `--scenes forest_golden,forest_lit,leafview,golden_lit,shore_sunset,biome_roofed`
  with `--opt QF_SHAFTS=0`. Shafts are a variable cost by view, so check the 1% low on
  `forest_golden` against `--prev`.

## 7. Test scenes and reference photos

Views: `forest_golden` (sun 9 degrees up seen through the trees: the beam scene),
`forest_lit` (same clearing, sun behind-left), `leafview`, `golden_lit`, `shore_sunset`,
`biome_roofed` (dark forest, high canopy), `underwater`. Photos (Commons): Category:Crepuscular
rays [V] and its subcategories "Crepuscular rays in forests", "Crepuscular rays at sunrise",
"Crepuscular rays at sunset", and "Tyndall effect in buildings" for indoor shafts.

## 8. Pitfalls

Angelica: `shadowtex0HW` is wrong (trap 1; `shadowRaw` already compares manually); the shadow
map covers only `shadowDistance` (48 / 80 / 112), so beyond it `V` is the cloud shadow alone
(fade, never a hard edge); the water surface is not in the map (`shadowTranslucent=false`);
a quarter-resolution buffer written once per frame reads stale under ping-pong (trap 4: do
not keep history in it, let TAA accumulate at full resolution, or write it twice); Potato has
no TAA, so no jitter there; the two shadow biases (`shadowRaw` 0.0004, `sampleShadow` 0.00012)
should agree or beams start a few blocks away from the shadow that casts them. Technique:
banding without jitter; light leaking through thin walls at map resolution; the r003 "orange
cone" came from taking the in-scatter colour from the sky near the sun per pixel: take it from
`E_sun` times the phase, never from `skyScatter` toward the sun; a veil over open sky washes
out the sun (keep the disk exclusion); and anything with a data-dependent step count breaks
the 1% low.

## 9. Licences

| Source | Terms | Use |
|---|---|---|
| Mitchell 2007, GPU Gems 3 ch. 13 | text free online, code licence not stated [V] | idea only (option C) |
| Engelhardt and Dachsbacher 2010, I3D, DOI 10.1145/1730804.1730823 | paper | method (option B) |
| Hillaire 2016, Frostbite | talk | integration and jitter |
| Hillaire 2015, "Physically based and unified volumetric rendering in Frostbite" | talk [U] | froxel fog idea |
| Wronski 2014, "Volumetric fog" (Assassin's Creed 4) | talk [U] | idea |
| Photon, Kappa, Complementary, BSL, Sildur's, Solas, Sundial, Rethinking Voxels | learn-only | feature survey |
