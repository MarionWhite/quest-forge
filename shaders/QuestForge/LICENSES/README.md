# Sources and credits

All GLSL in this pack was written for Quest Forge from scratch. No code, ID tables, option
names or textures come from Complementary, BSL, Sildur's, SEUS, Photon, Bliss or any GPL pack
(docs/design/shaders/README.md, "Licence stance"). The pack's own licence is the owner's
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
