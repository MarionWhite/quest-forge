# Sources and credits

All GLSL in this pack was written for Quest Forge from scratch, except the Photon port below. No
code, ID tables, option names or textures come from Complementary, BSL, Sildur's, SEUS, Bliss or
any GPL pack (docs/design/shaders/README.md, "Licence stance").

## Ported from Photon Shaders (r011)

`lib/photon.glsl` and `textures/qf_scattering.dat` are modified portions of **Photon Shaders 1.4,
Copyright (c) 2021-2025 Benjamin Stott ("SixthSurge")**, redistributed under the Photon Shaders
License, included as `photon-LICENSE.txt` (modified portions may be redistributed, including in a
modpack; not on platforms that pay creators, e.g. Modrinth or CurseForge, and never for money).
Ported: `include/sky/atmosphere.glsl` (scattering-LUT lookup, horizon stretch, Mie phase, saturation
boost), `include/utility/phase_functions.glsl`, `include/lighting/colors/light_color.glsl` (sun tint
and exposure by the hour), `include/fog/overworld/analytic.glsl` and `include/weather/fog.glsl`
(analytic air fog), and `image/atmosphere/scattering.dat` (unmodified). The LUT's mapping functions
are E. Bruneton's (2017, BSD-3; notice in `lib/photon.glsl`). The pack's own licence is the owner's
choice and is not set yet.

The shaderLABS Base-330 template suggested in the plan was not used; the program set was
written directly.

Techniques, implemented from their published descriptions:

| Where | Technique | Source | Terms |
|---|---|---|---|
| `lib/atmosphere.glsl`, `program/prepare.glsl` | Sky and atmosphere lookup tables (transmittance, multiple scattering, sky-view), Earth medium constants | S. Hillaire, "A Scalable and Production Ready Sky and Atmosphere Rendering Technique", EGSR 2020 | paper; constants are physical data |
| `lib/atmosphere.glsl` | Transmittance table parameterisation | E. Bruneton, "Precomputed Atmospheric Scattering: a New Implementation", 2017 | paper (the reference code is BSD-3; none of it is copied) |
| `lib/tonemap.glsl` | PBR Neutral tone mapper | Khronos Group, "Khronos PBR Neutral Tone Mapper", 2024 | specification and sample code Apache-2.0; implemented from the formula |
| `program/taa.glsl` | Temporal AA with luma-weighted resolve | B. Karis, "High Quality Temporal Supersampling", SIGGRAPH 2014 | talk |
| `program/taa.glsl` | Variance clipping in YCoCg | M. Salvi, "An Excursion in Temporal Supersampling", GDC 2016 | talk |
| `lib/common.glsl` | Interleaved gradient noise | J. Jimenez, "Next Generation Post Processing in Call of Duty: Advanced Warfare", SIGGRAPH 2014 | talk |
| `lib/common.glsl` | `hash12`, `hash13` ("Hash without Sine") | D. Hoskins, Shadertoy 4djSRW | MIT; this notice serves as the credit |
| `lib/shadows.glsl` | Vogel (golden-angle) disk sampling | H. Vogel, 1979 | maths |

## Data textures (`shaders/textures/`)

Made by `tools/shaders/make_textures.py`.

| File | What | Source | Terms |
|---|---|---|---|
| `qf_waves.png` | Tileable ocean height field (slope and height) | Generated: inverse FFT of a power-law wave spectrum, after J. Tessendorf, "Simulating Ocean Water", SIGGRAPH course notes 2001 | ours; the method is from the paper |
| `qf_noise.png` | White noise, smooth fbm, cellular edges | Generated; one-fetch 3D noise after I. Quilez's "noise with a 2D texture" article | ours |
| `qf_milkyway.png` | The Milky Way for the QF_NIGHT_SKY 3 night | **ESO/S. Brunier**, "The Milky Way panorama" (eso0932a), https://www.eso.org/public/images/eso0932a/ | **CC BY 4.0** (https://creativecommons.org/licenses/by/4.0/). Modified: cropped to galactic latitude -45 to +45 degrees, point stars removed (grey opening, median, light blur), sky background subtracted, levels normalised, resized to 4096 x 1024. No AI was used. |

Credit line, as ESO asks for it: **ESO/S. Brunier**.
