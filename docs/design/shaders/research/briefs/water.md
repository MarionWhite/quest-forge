# Brief: water

Waves, optics, reflection, the sun's glitter, biome colour and biome borders. Read with
[`README.md`](README.md) (tags, measurement recipe, buffer budget).

## 1. What the owner asked for

- r000 water (C, 5/5): "balancing the surface reflection with the water is a huge component of
  how it looks in game."
- r001 sunset (B, 4/5): "the water doesn't look amazing here."
- r002 water-sunset (C lively, 3/5): "the light source doesn't look as cinematic as I would hope.
  I would like a bit of glittery interaction with the water's surface texture, but only if we
  can get it right." water-noon (B calm, 4/5): "the distant surface texture does not dominate
  ... I also really like the 'bubble' particle effect." water-colour (5/5): "more teal and
  murky for a swamp or marsh, something deep blue for most oceans, a more transparent, glassy
  look for most rivers and lakes, and something like the Maldives color for coastal regions and
  coral reefs. We are going to pregenerate a map, so this concept will work well."
- r003 water-sunset (A, 4/5): the other options had "an ugly orange cone artifact right down the
  middle of the screen"; wanted "spots right below the sun that have the light intensity
  depth"; "look for other water designs from other shaders ... decide together."
  water-looks (3/5): "the little white particles are becoming a bit much."
- r004 water-direction (A, 5/5): "a combination of complementary's unbound (realistic) style,
  and photons strict realism." water-sunset (4/5): "a really good starting platform ... I am
  hoping to get more beauty out of a scene like this."
- r005 sunset-water (C, 4/5): "I like how the glint looks right below the sun ... but it doesn't
  extend as far as lively does, and for it to do that it will have to fade and balance as it
  draws closer to the camera." lake-sunset (5/5): "I still expect a LOT more out of the water
  and the light effects."
- r006 water-sunset (A, 5/5): "very fucking nice. Well done on the water and the light
  interaction. I don't know if I can detect the little dust particle things anymore."
  lake-sunset (A, 5/5): "The water texture gets splotchy in some areas when not enough light
  sources are present." water-noon (A, 5/5): "if there are other improvements ... I am open."
  water-biomes (C, 5/5): "The coast and the ocean look fucking unbelievable ... boundary
  conditions. When an ocean meets a swamp ... a pleasant gradient ... instead of stark cutoffs."

The direction is settled: physically grounded water (Photon-like optics) with a long, lively,
balanced sun path (the Unbound look he likes in screenshots), biome colour from the
pregenerated map, and smooth borders. Open faults: splotchy low-light lakes, the glitter's
near-camera balance, flecks too faint now, and borders.

## 2. What we do now

**Surface** (`program/gbuffers.glsl`, `GB_WATER`; `lib/water.glsl`): `waterNormalRough` builds
the normal from `spectralSlope`: one baked ocean-spectrum slope field (`qfWaves`, from
`tools/shaders/make_textures.py`, an inverse FFT of a power-law spectrum) laid down `WAVE_N = 8`
times at `WAVE_L` = 41, 23, 12.7, 7.3, 4.1, 2.3, 1.3, 0.74 blocks, slopes `WAVE_S` 0.046 to
0.068, golden-angle rotations, each layer drifting at the deep-water phase speed of its
dominant wave. A layer fades once its finest crests near two pixels (`waveFootprint` from
`dFdx`), and the slope variance it would have added is kept as roughness (`lost`, Toksvig
style), written to `colortex2.a` as `sqrt(var) * 8`. Gusts come from a slow noise. Potato uses
layers 2 to 5 only. Lakes get 0.72 of the ocean's amplitude (r007, the splotch fix).
`colortex2.b` carries the swamp share read from the vanilla water tint (`swampFromTint`).

**Optics** (`lib/water.glsl`): Beer-Lambert absorption and in-scattering per block, per biome:
`WA_GLASSY` (0.050, 0.024, 0.026) / `WS_GLASSY` (0.0013, 0.0031, 0.0030); `WA_OCEAN` (0.16,
0.060, 0.030) / `WS_OCEAN` (0.0006, 0.0034, 0.0105); `WA_REEF` (0.20, 0.022, 0.026) / `WS_REEF`
(0.0010, 0.0125, 0.0125); `WA_SWAMP` (1.10, 0.80, 1.25) / `WS_SWAMP` (0.050, 0.050, 0.021);
`WA_RIVER` (0.15, 0.080, 0.115) / `WS_RIVER` (0.0030, 0.0060, 0.0040). Weights come from the
camera's biome through `shaders.properties` uniforms smoothed over 12 s (`qfWaterOcean`,
`qfWaterReef`, `qfWaterSwamp`, `qfWaterRiver`) and, with `QF_WATER_BLEND`, from position
(`waterWeightsAt`: the swamp tint share and depth pulling toward ocean).

**Shading** (`program/composite.glsl` `shadeWaterAbove`, one full-screen pass): refraction by
the view-space slope (`uvR`, falls back when the offset lands in front); `waterVolume` for the
refracted light; caustics from two drifting cellular-edge layers of `qfNoise` projected along
the light (`QF_CAUSTICS`); exact unpolarised Fresnel `fresnelWater` (n 1.333); reflection =
`skyScatter` + `applyCloudsCheap` + `waterSSR` (12 steps Medium, 20 High, 4 bisection steps,
edge fade, hit weight masks the glitter where land is mirrored); sun glint = tight GGX
(alpha squared 0.0016) + a broad lobe (`GLITTER_A2` 0.03 to 0.05) + hashed sparkles
(`SPARK_CUT` 0.93) + `QF_SUN_SPARKLE` world-anchored facets whose cell size follows the pixel
footprint; flecks (`QF_FLECKS`), shore foam (`QF_FOAM`); underwater: `waterVolume` to 96 blocks
and the Snell window. `QF_WATER_STYLE 3` is calm by day and lively at low sun.

Measured **[measured]**: round 6's dearest High frame 2.3 ms (all effects); on Potato
`lake_glitter` cost 0.46 ms with five wave layers, so Potato runs four (`settings.glsl` note).

## 3. What the top packs do

- **Photon** [V, its published `shaders.properties`,
  https://raw.githubusercontent.com/sixthsurge/photon/main/shaders/shaders.properties]: waves
  from an iterated procedural generator with persistence and lacunarity (an fBm), separate
  speeds for still and flowing water, height variation and displacement, parallax on the
  surface, edge highlights; water fog as per-channel absorption and scattering coefficients with
  a separate set when the eye is under water; caustics, a Snell's-window effect, refraction and
  a biome tint. No foam. README: "revamped ... water", "screen-space reflections"
  [V, https://github.com/sixthsurge/photon]. Licence: learn-only.
- **Complementary Unbound**: no public method description anywhere I could find [V: the site
  https://www.complementary.dev/shaders/ and the Modrinth page describe styles and options
  only]. Third-party pages say SSR plus a wave simulation [U]. We have its frames
  (`bench-comp-*`) as a visual reference only.
- **Kappa** [V, https://wiki.rre36.com/wiki/Kappa_Shader]: a "Water Volume" mode that models
  light through the water body, "similar to god-rays", at a noise cost; off, water is "simpler,
  clearer, faster and less realistic."
- **Sundial Lite** [V, https://github.com/GeForceLegend/Sundial-Lite]: refraction, caustics and
  water fog, realistic or vanilla style. **Solas** [V,
  https://github.com/Septonious/Solas-Shader]: procedural waves, caustics, absorption,
  refraction. **BSL** [V, https://modrinth.com/shader/bsl-shaders]: "customizable ... water".
  **MakeUp Ultra Fast** [V, https://github.com/javiergcim/MakeUpUltraFast]: reflection and
  refraction. None publishes the method.

What we take from this: everybody's realistic water is normal-only waves, SSR with a sky
fallback, per-channel absorption and scattering, caustics and refraction. We already have all
of it. The gap to "Photon's strict realism" is in the BRDF for sub-pixel waves and in the
optics coefficients, and the gap to the Unbound screenshots is in the glitter's balance.

## 4. The technique

Two primary sources carry the rest of the way.

**Tessendorf's spectrum** [V, Lantz's walkthrough of the course notes,
https://www.keithlantz.net/2011/10/ocean-simulation-part-one-using-the-discrete-fourier-transform/;
the notes themselves at
https://people.computing.clemson.edu/~jtessen/reports/papers_files/coursenotes2004.pdf]: the
Phillips spectrum P(k) = A exp(-1/(kL)^2) / k^4 * |k_hat . w_hat|^2, with L = V^2/g for wind
speed V, a small-wave damping exp(-k^2 l^2) with l about L/1000, the deep-water dispersion
omega^2 = g k, Gaussian random amplitudes h0 = (xi_r + i xi_i)/sqrt(2) * sqrt(P), horizontal
choppiness lambda * D with D = sum of -i k/|k| h, slopes as the gradient and the normal
(-eps_x, 1, -eps_z). `make_textures.py` already bakes a power-law field; **re-bake with a
Phillips shape and a wind direction** so the long waves are aligned (a real glitter path is
elongated along the wind) and the short waves are damped. Keep `qfWaves` as slope + height;
add the choppy displacement later only if near-field parallax is wanted.

**Bruneton, Neyret and Holzschuch 2010** [V, the authors' slides,
https://cgg.mff.cuni.cz/~jaroslav/teaching/2012-npgr031/prezentace/Realtime%20Realistic%20Ocean%20Lighting.pdf;
paper record https://evasion.inrialpes.fr/Publications/2010/BNH10]: a hierarchy. Waves longer
than the grid cell become geometry, waves longer than a pixel become normals, and everything
shorter becomes a BRDF whose slope distribution is Gaussian (central limit theorem over the
dropped trochoids) with variance equal to the dropped waves' slope variance; each level is
attenuated by the smoothstep w(a, b, x). Sun light: a microfacet BRDF in the tangent plane
aligned with the mean normal and the wind, with anisotropic slope variances. Sky light: an
average Fresnel reflectance (a fitted function of the variance) times the sky radiance
filtered over an ellipse set by the slope distribution. Refracted light: treated as diffuse
and proportional to sun and sky irradiance, with transmittance = 1 - reflectance.

Our `spectralSlope` is already this hierarchy minus geometry: resolved layers make the normal
and `lost` is the BRDF variance. What is missing is to **use that variance as a real
anisotropic Gaussian-slope BRDF**, not as a GGX alpha fudge:

```
per water pixel (composite):
  n        = decoded normal from colortex1          (resolved waves)
  var      = (colortex2.a / 8)^2                    (dropped waves, isotropic today)
  var     += cox_munk(wind)                         (baseline for waves below the finest layer)
  split var into along-wind s_u^2 and cross-wind s_c^2 (ratio about 1.5 : 1)
  for the sun:
     h = normalize(L + V); slope of h in the tangent frame of n -> (su, sc)
     D = exp(-0.5 * (su^2/s_u^2 + sc^2/s_c^2)) / (2 pi s_u s_c)
     glitter = E_sun * F(h.V) * D / (4 * n.V * n.L)  (times shadow, times (1 - SSR hit))
  for the sky:
     F_avg = fit(var)                                (grows with variance, Bruneton's fit [U: coefficients not in the slides; fit our own from numeric integration offline])
     sky   = lookupSkyView(reflect) blurred by the slope ellipse (sample the LUT at 3 to 5 elevations spread by sqrt(var))
  refracted light as today, with the body term scaled by (1 - F_avg)
```

Why this answers the owner: the glitter path's length and its near-camera fade fall out of
the variance. Far from the camera the dropped-wave variance is large, so D is wide and dim (a
long soft path); near the camera the waves are resolved, the variance is small, and the
energy returns to the resolved facets as sparkles (the "spots right below the sun" with
"light intensity depth"). The r005 complaint ("fade and balance as it draws closer") is a
request for exactly this continuity; the hand-tuned `GLITTER_A2`, `BROAD_W`, `noonTame0` and
the sparkle hash can then go. Cox-Munk 1954 slope variances for a wind of U m/s are roughly
0.003 + 1.92e-3 U along and 0.00316 U across the wind [U, from memory; verify in the paper
before use]; with U = 3 to 5 m/s for lakes and 8 to 10 for the ocean.

**Optics.** Pure-water absorption (Pope and Fry 1997) is about (0.34, 0.056, 0.0092) per metre at
650, 550 and 450 nm [U, from memory]: red goes first, blue almost never. Our `WA_GLASSY` red of
0.050 is seven times too low and blue four times too high, deliberately, because true values
turn pale sand mint within two blocks (the r005 lesson). Keep that compromise, but structure
the coefficients as pure water times a clarity factor plus a particulate term per biome, so
the biomes differ by *what is in the water* (silt: scattering, warm; plankton: absorption of
blue and red, green-teal; clear: nothing) rather than by five unrelated triples. Starting
values: clarity 0.25; silt scattering (0.006, 0.006, 0.005) per unit of silt; plankton
absorption (0.02, 0.0, 0.04) per unit; swamp silt 8, river silt 0.5 and plankton 0.5, reef 0,
ocean plankton 0.3.

**Biome borders** (owner r006). The vanilla tint only marks swamps in 1.7.10, so position
blending has nothing to read for ocean against river or beach. Because the world is
pregenerated, bake a **biome class map** of the core: one texel per 4 blocks, `customTexture`
PNG, R = water class (0 glassy, 1 ocean, 2 reef, 3 swamp, 4 river) as a palette index, G = an
8-bit distance to the nearest different class. Sample it bilinearly in world XZ (the
`cameraPosition` plus scene position), blend classes over 16 to 24 blocks using G, and fall
back to the camera-biome uniforms outside the map. This also fixes the critic's "milky river"
since a river's class is exact. `tools/world/` already reads the region files' biome arrays
(`views-world-master.txt` was built from them).

**Splotchy lakes at low light** (owner r006): at grazing angles a steep facet flips between
dark water and bright sky. Bruneton attenuates waves shorter than a pixel for this reason; add
a slope clamp that scales the resolved slope by smoothstep(0.05, 0.25, n.V) and send the
removed slope into the variance, so the surface turns into a smooth sheen at the horizon
instead of flickering patches. Keep the r007 lake amplitude as a second knob.

**Caustics**: keep the cheap cellular pattern but derive it from the same `qfWaves` slopes
(refract the light through the slope field at the bed's projection and take 1/|det J| of the
finite differences) so caustics move with the waves. Shadow-pass caustics (Wallace's method)
are better but need `shadowcolor0` writes for water, which `shadowTranslucent=false` forbids.

Programs: `gbuffers_water` (normal, variance), `composite` (shading). No new render targets;
the biome map is a custom texture.

## 5. Low and Potato

- **Low**: the full model minus SSR (sky fallback only, `QF_SSR_STEPS 0` as today), 8 layers,
  the Gaussian BRDF (ALU only), caustics on, flecks on. The biome map is one fetch.
- **Potato**: 4 layers (as today), no caustics, foam or motes, Gaussian BRDF on (it replaces
  three lobes with one), exact Fresnel kept. Potato's `lake_glitter` sits at 0.4 ms today, so
  anything added must be paid for by removing a lobe.

## 6. Cost

- **[measured]** Round 6 High whole-frame 2.3 ms; Potato `lake_glitter` 0.46 ms with five
  layers, 0.4 budget.
- **[estimate]** Gaussian-slope BRDF replacing the GGX trio and the sparkle hash: neutral to
  -0.02 ms at 1440p High. Biome map fetch: +0.01 ms. Slope-smeared sky lookup (3 to 5 LUT
  taps): +0.02 ms on water-heavy views. SSR at half resolution in a `scale.composite` pass
  would save 0.1 to 0.2 ms on `ocean_sunset`, but needs a pass split (see light-shafts.md for
  the composite renumbering).
- Measure with the shared recipe on `ocean_sunset,lake_glitter,lake_glow,shore_noon,
  river_noon,beach_noon,biome_swamp,biome_ocean,ocean_swamp,river_swamp,underwater`, toggling
  `--opt QF_WAVES=0` for the whole wave model and the new option for the BRDF.

## 7. Test scenes and reference photos

Views: `ocean_sunset` (sun 9 degrees up, open water: the glitter path), `lake_glitter` and
`lake_glow` (sheltered water, cliff reflections, the splotch test), `shore_noon` (clear
shallows, caustics, foam), `river_noon`, `beach_noon`, `biome_swamp`, `biome_ocean`,
`ocean_swamp` and `river_swamp` (borders), `underwater`. Photos (Wikimedia Commons, check each
file's licence): Category:Sun glitter [V exists], Category:Water reflections [V] with
subcategories "Reflections in still water" and "Water reflections from grazing angles",
Category:Water reflections of sunsets [V, under Category:Sunsets], Category:Caustics (optics)
[V, e.g. "Caustics Shallow Water Pic1.png"]. Round 6 already used Dietmar Rabich's
"Kühlungsborn, Blick von der Seebrücke, Sonnenuntergang -- 2024 -- 4955.jpg" (CC BY-SA 4.0).
For the Maldives turquoise search Commons for lagoon photographs of the Maldives [U: category
name not checked].

## 8. Pitfalls

Angelica: `y auto` over water puts the camera under the surface (give `y`); a G-buffer cannot
blend, so water writes its normal with `blend.gbuffers_water.colortex1 = off` (already set);
`shadowtex0HW` is wrong, keep the manual compare in the glint's shadow; a quarter-resolution
SSR buffer written once per frame reads stale under ping-pong (write it twice or do not keep
history). Technique: a Gaussian-slope BRDF over-brightens the horizon without a
shadowing-masking term (clamp n.V from below and fade D as n.V goes to 0); a Phillips spectrum
without damping aliases at high k; FFT tiles repeat (our eight scales hide it); refraction
offsets can fetch foreground geometry (the fallback exists); world-anchored sparkles that move
leave TAA trails (the facets must hold for a second or more, as r005 found); the biome map
must be re-baked when the pregenerated core changes.

## 9. Licences

| Source | Terms | Use |
|---|---|---|
| Tessendorf, "Simulating Ocean Water", SIGGRAPH course notes | paper | method; our generator |
| Lantz, ocean simulation articles | explanatory blog, code is his | read for the equations only |
| Bruneton, Neyret, Holzschuch 2010, CGF 29(2), DOI 10.1111/j.1467-8659.2009.01618.x | paper; its code lives in Proland (BSD-3 [U]) | method only |
| Cox and Munk 1954; Pope and Fry 1997 | measured data | constants [U until checked] |
| Wallace, "Rendering realtime caustics in WebGL" | blog | idea |
| Photon, Complementary, Kappa, Sundial, Solas, BSL, MakeUp | learn-only (see README) | feature survey only |
