# Brief: tone mapping

Exposure, the display transform, vibrance, and the night. Read with [`README.md`](README.md).

## 1. What the owner asked for

- r000 direction: "some sort of combination between photorealistic and cinematic ... I don't
  want blocks themselves to look photorealistic ... but I want a cinematic look to them."
  night (B, 3/5): "Somewhere between truly dark and moonlit."
- r001 torch (5/5): "It's not warm at all. It looks like there is a florescent light bulb in
  the tunnel somewhere." (colour, not exposure, but the test surface for hue skew.)
- r002 night-new (D, 4/5): "I think we regressed" (the brown-black sky of the darker options).
- r003 night-new (B, 5/5): "The sky looks fuller in this one and has a deep rich darkness."
- r006 overall: "I like the light to interact with the blocks realistically, and I like a
  little more vibrance."
- Look bible Tier A: calm exposure, no pumping; neutral colour, "a neutral tone mapper with no
  hue skew on bright orange and red. Wood, chests, sand and gold are the test surfaces: they
  turn neon first"; golden hour without the wash.

History that matters: milestone round 3 removed the PBR Neutral toe because at our levels it
deleted the weakest channel and the frame went neon (mean saturation 0.82 against vanilla's
0.53); round 5 fixed exposure by reading level 0 (trap 3); rounds 6 and 7 collapsed exposure
on Low and Potato and were reverted; the hi/lo split in `C_EXPOSURE` fixed a half-float
freeze at 1000 fps.

## 2. What we do now

- **Operator** (`lib/tonemap.glsl` `tonemapNeutral`): Khronos PBR Neutral without the offset
  term: `startCompression 0.76`, `desaturation 0.15`; below the knee the colour passes
  through, above it the peak is compressed by `1 - d^2 / (peak + d - start)` and the colour
  mixed toward the compressed white by `g = 1 - 1 / (0.15 (peak - newPeak) + 1)`. Then
  `linearToSrgb` (exact curve).
- **Chain** (`program/final.glsl` `display`): `linearToSrgb(tonemapNeutral(vibrance(calGrade(
  exposed))))`. `vibrance` (`QF_VIBRANCE 0.15`, r007): a saturation lift in perceptual
  (square-root) terms that scales as `1 + 0.15 (1 - sat) 2.2`, so muted colours gain and
  vivid ones hardly move. `calGrade` is the round-0 calibration (off). The Potato path blends a
  4-neighbour edge filter after `display`. Exposed colour comes from the TAA history with the
  Karis luma weight undone, or from `colortex3 * exposure()` without TAA.
- **Exposure** (`program/prepare.glsl`, `lib/lut.glsl`): a 32x18 centre-weighted meter of
  `colortex3` level 0 (log-average blended 75% toward the arithmetic mean, `EXPOSURE_MEAN_WEIGHT`),
  summed in `prepare1`; the target curve `exposureTargetLog`: full adaptation above a sunny
  day's metered -3.64 (`EXPO_DAY_E 1.24`), partial between day and a full-moon night (-10.7,
  `EXPO_NIGHT_E 2.26`), 0.6 stop per stop below (`QF_DEEP_SLOPE`), plus a sky lift (0.3) and a
  dusk lift (0.6) gated by `eyeBrightnessSmooth`; bounds 0.12 to 48; time constants 1.2 s up
  and 3 s down; `QF_EXPOSURE_BIAS` slider. Night darkness itself is lighting (`nightFloor`,
  `QF_NEW_MOON`), not the mapper.
- No bloom in the path; no Purkinje shift; the output is dithered (milestone pipeline).

## 3. What the top packs do

- **Photon** [V, published `shaders.properties`]: one tone-map selector with a split-screen
  compare mode (operators not named in the file); colour grading (brightness, contrast,
  saturation, white balance, per-hue saturation, a green hue shift, a night Purkinje shift);
  **histogram-based** auto-exposure with bin count and target, separate brightening and
  dimming speeds, min and max limits; bloom intensity and spread.
- **Kappa** [V, wiki]: exposure decay, bias, dark and bright limits, manual override; no
  operator named. **Sundial Lite** [V]: "tonemapping, final color adjustments, average
  exposure". **Bliss**: tone-map presets as its only profiles [V, `../performance.md`].
  **Complementary**: nothing public; judge from the `bench-comp-*` frames.
- **Filament** (Google, Apache-2.0) [V, https://github.com/google/filament]: "Multiple tone
  mappers: GT7, PBR Neutral, AgX, generic (customizable), ACES, filmic". Blender, Godot and
  Substance adopted AgX [V, https://github.com/sobotka/AgX-S2O3].
- **Khronos PBR Neutral** [V, spec https://github.com/KhronosGroup/ToneMapping/blob/main/PBR_Neutral/README.md,
  Apache-2.0]: F90 = 0.04, Ks = 0.76, Kd = 0.15; offset f = x - x^2 / (4 F90) for the minimum
  channel x below 0.08, else 0.04; p = max(c - f); p_n = 1 - (1 - Ks)^2 / (p + 1 - 2 Ks);
  g = 1 / (Kd (p - p_n) + 1); out = (c - f) p_n / p g + p_n (1 - g) above Ks. Goals: a base
  colour between 0.08 and 0.8 under unit white light reproduces as c - 0.04, no hue shift (all
  changes in the plane of the colour and the white axis), continuous derivatives, invertible,
  no gamut mapping, sRGB only; made for product shots with small highlights.
- **AgX** (Sobotka): constants verified in Filament via three.js [V,
  https://github.com/mrdoob/three.js/blob/dev/src/renderers/shaders/ShaderChunk/tonemapping_pars_fragment.glsl.js,
  MIT; Filament Apache-2.0]: work in linear Rec. 2020, an "inset" 3x3 that pulls the primaries
  toward the centre, log2 encoding from -12.47393 to +4.026069 EV (16.5 stops, mid grey 0.18
  at the centre), a sigmoid approximated by a 6th-order polynomial (Wrensch's fit, mean square
  error 3.7e-6), an "outset" 3x3, a 2.2 power to linear, back to sRGB and clamp. Sobotka's own
  pages were unreachable (certificate error) and his AgX repo shows no licence on its page [V];
  the S2O3 README calls the sigmoid replaceable and any implementation should expose
  "rotation and inset parameters" [V].
- **Tony McMapface** (h3r2tic) [V, https://github.com/h3r2tic/tony-mc-mapface, MIT or
  Apache-2.0]: a 48^3 LUT sampled at `x / (x + 1)` with a `(N - 1) / N + 0.5 / N` texel-centre
  remap, linear output then the sRGB OETF; "intentionally boring": no contrast or saturation
  boost, no parameters, Helmholtz-Kohlrausch and a deliberate Bezold-Bruecke shift, selective
  desaturation that avoids the Abney effect; the author calls it "phenomenological" against
  AgX's "mathematically pure".
- **ACES fit, Narkowicz** [V, https://knarkowicz.wordpress.com/2016/01/06/aces-filmic-tone-mapping-curve/,
  CC0 or MIT]: x (2.51 x + 0.03) / (x (2.43 x + 0.59) + 0.14), input times 0.6 to match ACES;
  "a very simple luminance only fit, which over saturates brights".
- **Hable (Uncharted 2)** [V, http://filmicworlds.com/blog/filmic-tonemapping-operators/]:
  ((x (A x + C B) + D E) / (x (A x + B) + D F)) - E / F with A 0.15, B 0.50, C 0.10, D 0.20,
  E 0.02, F 0.30, white 11.2, exposure bias 2; no licence statement. **Reinhard**: x / (1 + x).
  **Uchimura GT** (CEDEC 2017): a toe, linear and shoulder curve with P 1, a 1, m 0.22, l 0.4,
  c 1.33, b 0 [U, defaults from memory; the MIT glsl-tone-map repo https://github.com/dmnsgn/glsl-tone-map
  lists it but its file path could not be fetched]. **Lottes 2016**: a tunable curve
  (GPUOpen talk) [U].

## 4. The technique

**Keep PBR Neutral as the default, and add AgX as the Cinematic look.** Neutral is the look
bible's Tier A by construction (no hue shift, invertible, vanilla-faithful mid-tones), and the
owner's accepted frames are on it. Its limit is that it adds no contrast and desaturates
highlights abruptly above 0.76: fine for product shots, flat for a sunset. AgX gives filmic
contrast and a graceful roll-off to white while keeping hue through the inset, and it costs
two 3x3 multiplies and a polynomial. Offer both on the shader screen; render every Shader Lab
sunset and the texture wall in both for one round, then set the default by his pick.

```
AgX (from the Filament constants, Apache-2.0 notice kept):
  c = exposed linear sRGB -> Rec. 2020 (3x3) -> inset (3x3)
  v = clamp((log2(max(c, 1e-10)) - (-12.47393)) / (4.026069 - -12.47393), 0, 1)
  v = sigmoid6(v)              (the 6th-order fit; or fit our own to the S2O3 curve)
  c = outset (3x3) applied to v, then pow 2.2, Rec. 2020 -> sRGB, clamp
  look (punchy-lite, between AgX base and Blender's punchy): offset 0, slope 1.0, power 1.2, saturation 1.2   [starting values]
  then the exact sRGB OETF (ours), not a 2.2 approximation
```

Mid grey: AgX puts 0.18 at the centre of its 16.5-stop range, so the exposure curve's day key
(`EXPO_DAY_E 1.24`, chosen for Neutral) needs re-fitting so sunlit grass lands near 0.18
before the mapper; measure with debug view 8's meter readout. Do not stack `vibrance` on AgX:
the inset already does what the vibrance slider was for; keep the slider only for Neutral.

**Exposure: keep the meter, add outlier rejection.** Photon's histogram needs compute or a
scatter pass (Low and Potato are GL 3.3 only). Our 576-sample meter is enough; its weakness
is that the sun's glitter or a lava lake drives the mean. Cheap fix in `prepare`: the columns
already carry sums; add a sum of squares, compute mean and sigma in `prepare1`, and re-weight
the metered value toward the log-average when the arithmetic mean exceeds the log-average by
more than 1.5 stops (a proxy for "a few very bright pixels"). Keep 1.2 s up and 3 s down, the
bounds, the sky and dusk lifts. Never let white balance follow time of day (look bible 4).

**Night: a Purkinje shift** (see sky.md 4D) between exposure and the mapper, gated by the
metered log2 luminance, off under `nightVision`; it is what makes a navy night read as night
and not as a dim day, and it is the physically honest replacement for a "moonlit blue" grade.

**Tony McMapface** stays the fallback if AgX's hue rotation shows on gold or torch orange: it
needs a 48^3 texture, so raw `TEXTURE_3D` under Angelica must load first (README trap 11); an
8-bit PNG atlas loses precision in the toe, a 16-bit raw does not.

Programs: `final` (mapper, Purkinje), `prepare` / `prepare1` (meter). No new render targets; a
LUT would be a custom texture.

## 5. Low and Potato

Identical on every tier: AgX is arithmetic, Neutral is arithmetic, the meter already runs on
Potato (its `prepare` is fixed-size). The Potato edge filter stays after `display`.

## 6. Cost

- **[estimate]** Any of these operators is under 0.02 ms at 1440p (a few dozen ALU per pixel in
  a pass we already run). Tony McMapface is one trilinear 3D fetch. Meter changes are in a
  256x320 pass: negligible.
- Measure with the shared recipe on `plains_noon,texture_wall,shore_sunset,night_full,torch`
  toggling the new operator option; the cost is in the noise, so the real check is
  `check_frames.py`'s crushed and clipped percentages (`--max-crushed`, `--max-clipped`) and
  the mean-saturation line the critic reads.

## 7. Test scenes and reference photos

Views: `texture_wall` (wood, chests, sand, gold, glowstone, the neon test; needs
`--world C:/qfb/textures/world-showcase`), `plains_noon` (grass must not go lime),
`golden_lit` (amber faces against blue shade), `shore_sunset` and `ocean_sunset` (sun and
glints into the shoulder), `night_full` and `night_new` (toe, the "deep rich darkness"),
`torch` (bench scene, torch warmth through the mapper), `underwater`. Photos: none; a display
transform has no photographic reference. The owner judges on a phone: it maps sRGB
correctly, applies auto-brightness, and a wide-gamut screen can make our sRGB look muted, so
never chase saturation beyond sRGB.

## 8. Pitfalls

Angelica: the exposure texel is single-writer unless `prepare1` copies it (trap 4) and must
stay split hi/lo in RGBA16F; mips are not rebuilt for `prepare` reads (trap 3, why the meter
reads level 0); TAA works on luma-weighted exposed colour, so the mapper must run after the
weight is undone (`sceneExposed`). Technique: the Neutral toe deletes the weakest channel at
our low levels (keep it off, or scale the scene up so levels sit where Khronos expects);
vibrance before the mapper pushes mid-tones into the shoulder; ACES's fit skews orange toward
yellow (rejected by the look bible); Reinhard greys mid-tones; Hable needs a white point per
scene; AgX slightly desaturates pure primaries by design, so check gold and torchlight; any
mapper applied before bloom makes bloom clip (bloom.md: bloom on exposed linear, before the
mapper).

## 9. Licences

| Source | Terms | Use |
|---|---|---|
| Khronos PBR Neutral specification | Apache-2.0 [V] | implemented from the formula (already credited) |
| AgX constants via Filament | Apache-2.0 [V]; three.js copy MIT [V] | constants with the Apache notice; sigmoid re-fit or taken with notice |
| Sobotka AgX, AgX-S2O3 | no licence shown on the repo pages [V] | concept only |
| Wrensch, "Minimal AgX implementation" (iolite) | licence not shown [V] | do not copy; the fit is reproduced in Filament under Apache-2.0 |
| Tony McMapface | MIT or Apache-2.0 [V] | LUT and sampling code may be used with notice |
| Narkowicz ACES fit | CC0 or MIT [V] | not recommended |
| Hable, filmic operators | no statement [V]; maths | formula only |
| Uchimura 2017, Lottes 2016 | talks | formulas; glsl-tone-map (MIT [V]) implements them |
| Photon, Kappa, Sundial, Bliss | learn-only | feature survey |
