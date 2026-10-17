# Shader pack research: licenses and techniques for an OptiFine 1.7.10 HD U E7 pack

> **Platform note (2026-10-17):** the pack now targets Angelica's Iris backport, not E7. Wherever this report describes E7 features, limits or traps, [`../README.md`](../README.md) "Platform facts" wins. The technique, cost and licence findings still apply.

Date: 2026-10-16. Tags: **[V]** = I checked it myself (I read the LICENSE file or ran a probe). **[U]** = unverified (from memory or a secondary source).

## 0. What E7 actually supports

I extracted `shadersmod/` from `%APPDATA%\.crazycraft4\mods\OptiFine_1.7.10_HD_U_E7.jar` (it reports ShadersMod 2.4.12) and searched its class strings. Seeing a string in the classes shows a feature is present, but not the exact `shaders.properties` syntax. Check the syntax against a test pack.

- **Programs:** `deferred`, `deferred1-7`, `composite`, `composite1-7`, `final`, the `gbuffers_*` set (including `beaconbeam`, `hand_water`, `weather`, `clouds`, `skytextured`) and `shadow`. **No geometry shaders.** No `.gsh` handling was found. [V]
- **Buffers:** `colortex0-7` and `shadowcolor0/1`, with formats up to `RGBA16F`, `RGBA32F` and `R11F_G11F_B10F`. Per-buffer `Clear` and `MipmapEnabled` exist, so persistent history buffers and mip chains are possible. `flip` (ping-pong) exists. `shadowHardwareFiltering` (sampler2DShadow), shadow mipmaps and `Nearest` toggles exist. [V]
- **Uniforms present:** `frameCounter`, `frameTimeCounter`, `gbufferPreviousProjection/ModelView`, `previousCameraPosition`, `shadowModelView(Inverse)`, `sunPosition`, `moonPosition`, `shadowLightPosition`, `sunAngle`, `moonPhase`, `eyeBrightnessSmooth`, `wetness`, `rainStrength`, `heldItemId(2)`, `heldBlockLightValue(2)`, `centerDepthSmooth`, `eyeAltitude`, `fogColor`, `skyColor`, `nightVision`, `blindness`, `entityId`, `blockEntityId`. `block.properties` (BlockAliases), `ambientOcclusionLevel`, `noisetex` and the attributes `mc_Entity`, `mc_midTexCoord` and `at_tangent` are also present. [V]
- **Custom uniforms and custom PNG textures:** the classes `shadersmod/uniform/CustomUniforms` and `shadersmod/client/CustomTexture` exist, with stage names gbuffers, deferred and composite. Their exact syntax is not confirmed. [V for presence, U for syntax]
- **Not found:** `separateAo`. Vanilla AO stays baked into `gl_Color`, but `ambientOcclusionLevel` can scale it down. [V]
- **What this means:** TAA, LUTs, temporal clouds and mip-based exposure and bloom are all feasible. Compute shaders, image load/store, sub-resolution render targets (`size.buffer`) and floodfill are not.
- **GLSL version:** OptiFine passes `#version` through unchanged (it matches on `^\s*#version`). On a compatibility context, NVIDIA and AMD drivers usually accept `#version 130`, and often `150 compatibility` or higher, which adds `textureGather` and `texelFetch`. Treat anything above 130 as an optional, driver-dependent path. [U]

## 1. Open-source packs and their licenses

| Pack | License (file) | Can we reuse the code? | Known for |
|---|---|---|---|
| **shaderLABS Base-120 / Base-150 / Base-330** | Unlicense (public domain) [V] — [120](https://github.com/shaderLABS/Base-120), [150](https://github.com/shaderLABS/Base-150), [330](https://github.com/shaderLABS/Base-330) | **Yes, freely, no notice needed.** Base-120 is the right skeleton for GLSL 120. | Minimal correct program set and buffer plumbing. |
| **Miniature Shader** (mateuskreuch) | MIT [V] [LICENSE](https://github.com/mateuskreuch/minecraft-miniature-shader/blob/master/LICENSE) | Yes, keep the notice. Supports MC 1.7.2+ (Modrinth metadata) [V], so its code is legacy-compatible. | Lightweight shadows, reflections and water. |
| **Arc** (Null-MC) | MIT [V] [LICENSE](https://github.com/Null-MC/Arc-Shader/blob/main/LICENSE) | Yes, keep the notice. Targets 1.16–1.19 (Iris and OptiFine) and probably needs newer GLSL [U]. | Realistic-leaning look: volumetrics, PBR. |
| **Glimmer** (jbritain) | MIT [V] [LICENSE](https://github.com/jbritain/glimmer-shaders/blob/main/LICENSE) | Yes. Iris only, modern GL, so read it for ideas. | Clean, modern, performant. |
| **Renderpearl** (Luracasmus) | MIT [V] [LICENSE](https://github.com/Luracasmus/renderpearl/blob/main/LICENSE) | Yes. Iris only and compute-heavy, so the ideas are what transfer. | High-performance modern pipeline. |
| **Spectrum** (zombye) | MIT [V] [LICENSE](https://github.com/zombye/spectrum/blob/master/LICENSE) | Yes. From 2017–18, the OptiFine 1.12 era. | Physically based sky and water, "natural" look. |
| **Mellow** (TheCMK) | MIT (Modrinth) [V] [source](https://codeberg.org/TheCMK/mellow-shader) | Yes. Supports 1.8+. | Painterly and cheap. |
| **Musk Rose** (Rinloid) | CC0 [V] [LICENSE](https://github.com/Rinloid/musk_rose_je/blob/main/LICENSE) | Yes, freely. | Pretty, simple sky and water. |
| **MakeUp-UltraFast** (javiergcim) | **LGPL-3.0** (Modrinth says "or later") [V] [LICENSE](https://github.com/javiergcim/MakeUpUltraFast/blob/master/LICENSE) | Yes, under LGPL terms (see below). Very good quality-per-millisecond reference. Supports OptiFine 1.12.2+. | Fast TAA, clouds, AO, cheap volumetrics. |
| **Sundial Lite** (GeForceLegend) | **GPL-3.0-or-later** [V] [LICENSE](https://github.com/GeForceLegend/Sundial-Lite/blob/main/LICENSE) | Copyleft. Supports MC 1.8.9+ on OptiFine, the closest to our legacy pipeline. | Balance of quality, performance and compatibility. |
| **Noble** (BelmuTM) | **GPL-3.0-only** [V] [LICENSE.txt](https://github.com/BelmuTM/NobleRT/blob/master/LICENSE.txt) | Copyleft. | Physically based atmosphere and screen-space ray tracing [U]. |
| **Alpha Piscium** (Luna5ama) | **GPL-3.0** [V] [LICENSE](https://github.com/Luna5ama/Alpha-Piscium/blob/main/LICENSE) | Copyleft. Iris only. | High-end realistic look. |
| Steadfast (coderbot) | GPL-3.0-only (Modrinth) [V] [repo](https://github.com/coderbot16/Steadfast) | Copyleft. | Fast and careful. |
| VanillAA | MPL-2.0 [V] [repo](https://github.com/leo60228/VanillAA-Shaders) | File-level copyleft. | TAA only. |

**Do not copy code from these:**
- **Photon:** custom license [V] ([LICENSE](https://github.com/sixthsurge/photon/blob/main/LICENSE)). It lets you examine and learn from the code. It also lets you redistribute portions, but the license text must ship with them, they cannot go on platforms that pay creators (CurseForge, Modrinth) without permission, and they cannot be sold. That conflicts with "our own license", so treat Photon as **learn-only**. It is the best-documented modern reference for the Hillaire sky, clouds and AgX.
- **Bliss:** "© 2020 Chocapic13. All rights reserved." [V] ([LICENSE.md](https://github.com/X0nk/Bliss-Shader/blob/main/LICENSE.md)). Treat Chocapic13 derivatives the same way.
- **Super Duper Vanilla:** FlameRender License 1.6 [V]. Modified versions must keep that same license, so it is share-alike to a proprietary license.
- **Rethinking Voxels:** Complementary Agreement 1.3 [V].
- **Lux:** "the agreement… is the same as BSL's" [V] ([AGREEMENT.txt](https://github.com/Aurealis-Graphics/Lux-Shader/blob/main/AGREEMENT.txt)).
- **Kappa and Nostalgia** (RRe36): all rights reserved, no public repo [V via Modrinth API].
- **Ebin** (BruceKnowsHow): "Do not redistribute… without permission" [V].
- **Shrimple** (Null): all rights reserved [V].
- **KUDA:** DeDelner's original has no public repo or license. A Modrinth "kuda-shaders" by Titan1um is BSD-3 ([repo](https://github.com/T1taniumF0rge-Industries-Inc/kuda-shaders)) [V], but its README only says it is "inspired by DeDelner". **Its provenance is unclear, so avoid it.**

**Non-pack reference code with permissive licenses (very useful):**
- Hillaire's [UnrealEngineSkyAtmosphere](https://github.com/sebh/UnrealEngineSkyAtmosphere): MIT [V].
- [Bruneton precomputed scattering](https://github.com/ebruneton/precomputed_atmospheric_scattering): BSD-3 [V].
- [Playdead TAA](https://github.com/playdeadgames/temporal): MIT [V].
- [Tony McMapface](https://github.com/h3r2tic/tony-mc-mapface): MIT/Apache [V].
- [XeGTAO](https://github.com/GameTechDev/XeGTAO): MIT [U].
- [Bend screen-space shadows](https://www.bendstudio.com/blog/inside-bend-screen-space-shadows/) (the code zip): Apache-2.0 [V; I read the header].

**What each license obliges us to do** (my reading, not legal advice):
- **MIT, BSD, Zlib:** keep the copyright notice in the copied files or in a `LICENSES/` folder.
- **Apache-2.0:** keep the notice, add a NOTICE file if upstream has one, and mark modified files.
- **GPL-3.0:** a shader pack ships as source, so any copied GPL code makes the **whole pack** a combined work that must be GPL-3. That gives up "our own license" and binds downstream forks too. "GPL-3.0-only" and "-or-later" can be combined, but the result is 3.0-only. Our own PNGs and properties files can carry separate licenses only if they are clearly separable. Code from the Quest Forge mods is not affected.
- **LGPL-3.0:** GLSL has no linking boundary, because `#include`d files are compiled into one program. The safe reading is to keep LGPL-derived code in separate include files under LGPL-3, with modifications published (automatic for a shader pack), and to license the rest of the pack as we like. This interpretation is debatable [U].
- **MPL-2.0:** copyleft per file; the same pattern of isolated files works.

**Recommendation:** take the skeleton from Base-120 (Unlicense). Copy code only from MIT, BSD, Apache or CC0 sources. Read Photon, Sundial and Noble for ideas but write our own code. Note that clean-room reimplementation from papers is always safe.

## 2. Techniques: primary sources, feasibility and recommendations

Costs below are my estimates for a mid-high GPU at 1440p, not measurements: **cheap** is under 0.3 ms, **medium** is 0.3–1.5 ms, **expensive** is over 1.5 ms.

### Atmosphere, sky and night
- **Hillaire 2020** ([paper](https://sebh.github.io/publications/egsr2020.pdf), [code, MIT](https://github.com/sebh/UnrealEngineSkyAtmosphere)): a transmittance LUT (256×64), a multiple-scattering LUT (32×32), a per-frame sky-view LUT (about 192×108) and an aerial-perspective froxel volume (32³).
  - **GLSL 120 feasibility:** draw the LUTs into a reserved corner of a non-cleared RGBA16F `colortex` in `deferred`, with a `discard` outside the rectangle. The two static LUTs can also be baked offline into PNG custom textures, using our `tools/` Python scripts. The 32³ volume can be packed as a 32-slice 2D strip (1024×32).
- **Bruneton 2008/2017** ([site](https://ebruneton.github.io/precomputed_atmospheric_scattering/), BSD-3): higher fidelity, but needs 4D/3D LUTs and a heavy precompute. That is overkill here.
- **Cheap alternatives:** a single-scattering raymarch of 8–16 steps with an analytic Chapman optical depth, or Preetham/Hosek fits. These are fine for low settings.
- **Sun and moon:** draw the sun as an analytic disk with limb darkening, multiplied by transmittance. Draw the moon as a textured quad from `gbuffers_skytextured` with `moonPhase`, lit by a dim "sun" whose color comes from the same atmosphere model at a lower intensity. Do not use a different sky color hack.
- **Stars:** a hashed cell grid on the sky direction, rotated by `sunAngle`, attenuated by transmittance.
- **Night:** add a scotopic or Purkinje blue shift and desaturation before tonemapping (Kirk & O'Brien, "Perceptually Based Tone Mapping for Low-Light Conditions", 2011) [U, no link checked].
- **Recommend:** Hillaire, with static LUTs baked to PNG and the sky-view LUT computed per frame. **Cheap.**

### Clouds
- **Primary sources:**
  - Schneider 2015, [HZD volumetric cloudscapes](https://www.guerrilla-games.com/read/the-real-time-volumetric-cloudscapes-of-horizon-zero-dawn), and the 2017 [Nubis](https://www.guerrilla-games.com/read/nubis-authoring-real-time-volumetric-cloudscapes-with-the-decima-engine) talk: a weather map, a height gradient, Perlin-Worley shape plus erosion, Beer-Powder lighting and quarter-resolution rendering with reprojection.
  - Hillaire 2016, [Frostbite sky and clouds](https://media.contentapi.ea.com/content/dam/eacom/frostbite/files/s2016-pbs-frostbite-sky-clouds-new.pdf): energy-conserving integration and a multi-scattering octave approximation.
- **GLSL 120 constraints:** there are no 3D textures. Emulate 3D noise with two offset slices of a 2D `noisetex` (the classic iq trick), or with a packed 2D atlas loaded as a custom PNG.
- **Low resolution:** E7 has no sub-resolution render targets. Emulate a quarter-res trace by tracing only one pixel in each 4×4 block per frame, chosen by a Bayer index from `frameCounter`, then reproject into a non-cleared history buffer. A cheaper alternative is to trace every pixel with 1/4 of the steps plus blue-noise jitter and TAA.
- **Recommend:** a cumulus volume layer with 12–24 primary steps and 4 light steps, a Beer-Powder term, dual-lobe Henyey-Greenstein phase and 3 multi-scatter octaves. Trace it with the 4×4 interleave plus temporal reprojection, and add a fBm 2D cirrus plane above it. **Medium.** Discard vanilla `gbuffers_clouds`.

### Shadows
- **Distortion:** use the standard radial warp `p.xy /= mix(1.0, length(p.xy), k)` with k ≈ 0.85, plus a z-squash for the depth range. Use a distortion-aware normal-offset bias. Reference: the [shaderLABS wiki](https://shaderlabs.org/wiki/Main_Page) [U, page content not checked]. Use `shadowMapResolution` 2048–4096 and `shadowDistance` 128–160.
- **Filtering:** PCSS ([Fernando 2005](https://developer.download.nvidia.com/shaderlibrary/docs/shadow_PCSS.pdf)) with an 8-tap blocker search and 12–16 PCF taps on a Vogel disk. Rotate the disk with interleaved gradient noise ([Jimenez 2014](https://www.iryoku.com/next-generation-post-processing-in-call-of-duty-advanced-warfare/)) and let TAA resolve the noise. Use `shadowHardwareFiltering` so each tap is bilinear-filtered.
- **Colored translucent shadows:** compare `shadowtex0` (with translucents) to `shadowtex1` (opaque only). Where they differ, multiply by `shadowcolor0`, which holds glass or water tint and alpha written in `shadow.fsh`.
- **Contact shadows:** a 12–16 step screen-space march toward the light in the depth buffer, as in Bend's Days Gone technique ([blog](https://www.bendstudio.com/blog/inside-bend-screen-space-shadows/), Apache-2.0). Their implementation is a compute shader, so port the idea, not the code.
- **Leaves and grass subsurface:** thickness = receiver depth minus shadow-map depth, transmission = exp(−σ·thickness) × forward-lobe Henyey-Greenstein, applied by block-ID class.
- **Recommend:** distorted 3072² shadow map, PCSS-lite with hardware PCF, colored translucency, contact shadows, and thickness-based foliage subsurface. **Medium.**

### Ambient occlusion
- **GTAO:** Jimenez et al. 2016 ([PDF](https://www.iryoku.com/downloads/Practical-Realtime-Strategies-for-Accurate-Indirect-Occlusion.pdf); revised version with multi-bounce and specular occlusion at [Activision Research](https://research.activision.com/publications/archives/practical-real-time-strategies-for-accurate-indirect-occlusion)). XeGTAO (MIT) is a clean HLSL reference. It ports to GLSL 120 as pure fragment math.
- **Vanilla AO:** it is baked into `gl_Color` in 1.7.10 and cannot be separated from the biome tint. Set `ambientOcclusionLevel` to about 0.3–0.5 so vanilla AO keeps its crisp block-corner darkening. Multiply by GTAO for medium-scale occlusion, and use the multi-bounce fit to avoid over-darkening.
- **Recommend:** GTAO with 1 slice per pixel per frame (rotated by `frameCounter`) and 6–8 steps per side over a 2–3 m radius, accumulated by TAA plus a small depth-aware 4-tap blur. **Medium-cheap.**

### Reflections and water
- **SSR:** a linear view-space march of 16–24 steps with jitter, then 4–6 binary-refine steps. Hi-Z is not practical, because mipmaps average and do not take the minimum. Sample the previous frame's lit color, reprojected, so reflections include lighting.
- **Sky fallback:** use the sky-view LUT multiplied by the skylight lightmap (`lmcoord.y`) so caves do not reflect sky. Blend at the screen edge.
- **Roughness:** sample a GGX VNDF ray per pixel per frame (Heitz 2018, JCGT "Sampling the GGX Distribution of Visible Normals") [U, no link checked]. Combine with TAA, plus the mip level of the previous-frame color (`MipmapEnabled`) chosen by cone angle. Use the Schlick Fresnel term with an energy-split approximation.
- **Waves:** FFT ([Tessendorf](https://people.computing.clemson.edu/~jtessen/reports/papers_files/coursenotes2004.pdf)) needs multi-pass butterflies over persistent buffers. It is possible with fragment ping-pong but not worth it for block water. Gerstner displacement in `gbuffers_water` is limited by quad tessellation (one quad per block top). Use small-amplitude vertex bob, and get detail from **fragment normals** made of 8–12 directional exponential-sine or fBm octaves with domain warping, plus optional parallax.
- **Water optics:**
  - Beer-Lambert absorption with σa ≈ (0.30, 0.06, 0.02) per meter [U, a rough pure-water value per Pope & Fry 1997], plus a small σs in-scatter.
  - Underwater fog uses the same coefficients, with a shadowed sun in-scatter term.
  - Snell's window and total internal reflection at the surface when `isEyeInWater`.
- **Caustics:** in `shadow.fsh` for water, compute the refracted-ray area change via `dFdx`/`dFdy` of the refracted ground hit, as in Evan Wallace's WebGL water ([write-up](https://medium.com/@evanwallace/rendering-realtime-caustics-in-webgl-2a99a29a0b2c) [U, link not checked]). Write the intensity to `shadowcolor0` so the shadow lookup projects caustics for free.
- **Recommend:** SSR with VNDF sampling, TAA and sky fallback (**medium**); fragment-normal waves with Beer-Lambert and shadow-pass caustics (**cheap-medium**).

### Lighting and colored block light
- **Falloff:** convert `lmcoord.x` back to a level L (0–15), then a pseudo-distance d = 15 − L, then `I = k / (d² + 1)` windowed by `smoothstep(0,1,L/15)`. This gives a bright core and a long, soft tail. Use a separate exposure-friendly scale so torches light at about 3–6 EV below the sun.
- **Colored light without voxels or floodfill:**
  1. **Recommended:** in `gbuffers`, write emissive color from block-ID classes in `block.properties` (torch orange, glowstone gold, redstone red, sea lantern cyan) to an emissive buffer with `MipmapEnabled`. In `deferred`, sample mips 5–7 at the pixel. Normalize that color to a tint and multiply the lightmap block light by it. Fall back to warm white when the emissive mip is weak (off-screen sources). Stabilize with temporal smoothing. **Cheap.** Off-screen sources lose their color, which is acceptable.
  2. **Experimental:** shadow-pass voxelization by remapping each block's vertices into a 2D voxel atlas in `shadowcolor1` from the vertex shader. Without geometry shaders this is fragile (per-vertex, not per-face). Only consider it later.
- **Emissives:** the albedo luminance mask decides which pixels emit, per block-ID class; boost before bloom.
- **Hand light:** `heldBlockLightValue` and `heldItemId` (numeric IDs in 1.7.10) give a point light at the camera with the same falloff, and the item's color comes from a small `#define` table.

### Materials without texture maps
- **Normals:** a generated normal from the albedo luminance Sobel operator, at the texel scale of each atlas tile. Clamp at tile edges using `mc_midTexCoord` and `atlasSize`, and weight by material class.
- **Material classes:** come from `block.properties` → `mc_Entity.x` (stone, metal, wood, foliage, water, glass, ice, emissive, sand/dirt). Each class gets roughness, F0, porosity and subsurface values.
- **Wetness:** `wetness` × skylight × up-facing factor. Darken albedo by porosity and lower roughness, following [Lagarde's wet surfaces](https://seblagarde.wordpress.com/2013/04/14/water-drop-3b-physically-based-wet-surfaces/). Puddles come from a world-space noise mask on flat up-faces, with mirror roughness and ripples driven by `rainStrength` and `frameTimeCounter`.
- **Cost:** cheap.

### Post-processing
- **Tonemap:** AgX via Wrensch's [minimal AgX](https://iolite-engine.com/blog_posts/minimal_agx_implementation) polynomial (cheap, ALU only), with a "punchy" look option. Tony McMapface needs a 48³ LUT, which as an 8-bit PNG custom texture loses precision [U, quality untested]. The [ACES fit (Narkowicz)](https://knarkowicz.wordpress.com/2016/01/06/aces-filmic-tone-mapping-curve/) oversaturates highlights. [Lottes 2016](https://gpuopen.com/wp-content/uploads/2016/03/GdcVdrLottes.pdf) is a good tunable alternative. **Recommend AgX.**
- **Auto-exposure:** a true histogram needs compute or scatter. Instead, enable mipmaps on a log-luminance buffer, read the 1×1 top mip in `final` (center-weighted by sampling a slightly lower mip at several points), and adapt it temporally into a persistent pixel. **Cheap.**
- **Bloom:** E7 cannot render to lower resolutions. Either sample the HDR buffer's hardware mip chain (blurred mips 1–6 with a 13-tap filter as in [Jimenez 2014](https://www.iryoku.com/next-generation-post-processing-in-call-of-duty-advanced-warfare/), the CoD:AW talk), or do dual-Kawase-style taps ([Bjørge 2015](https://community.arm.com/cfs-file/__key/communityserver-blogs-components-weblogfiles/00-00-00-20-66/siggraph2015_2D00_mmg_2D00_marius_2D00_notes.pdf)) at full resolution on mip inputs. **Recommend mip-chain bloom, mixed energy-conservingly at about 4%.** **Cheap-medium.**
- **TAA:**
  - Jitter `gl_Position` in all gbuffers and shadow-independent programs by a Halton(2,3) sequence with `frameCounter`.
  - Reproject with `gbufferPrevious*` and `previousCameraPosition`.
  - Clip in YCoCg against variance bounds ([Karis 2014](https://de45xmedrsdbp.cloudfront.net/Resources/files/TemporalAA_small-59732822.pdf), Salvi variance clipping [U, no link checked]; [Playdead TAA, MIT](https://github.com/playdeadgames/temporal)).
  - Resolve history with Catmull-Rom (5-tap), then sharpen with CAS or unsharp.
  - Entities and hand do not get motion vectors: tag them via `entityId` and lower history weight there.
  - **Medium-cheap.**
- **Grain and vignette:** luminance-dependent blue-noise grain at 1–2% ([Wronski](https://bartwronski.com/2016/10/30/dithering-part-two-golden-ratio-sequence-blue-noise-and-highpass-and-remap/)), plus a natural cos⁴-style vignette at about 10%. Dither the 8-bit output. **Cheap.**

### Fog and aerial perspective
- **Aerial perspective:** use the Hillaire froxel volume (packed 2D) for distant terrain, which keeps it consistent with the sky.
- **Height fog:** analytic exponential height fog ([Wenzel 2006](https://developer.amd.com/wordpress/media/2012/10/Wenzel-Real-time_Atmospheric_Effects_in_Games.pdf) [U, link not checked]) for valleys and rain. Its in-scatter color is taken from the sky-view LUT in the view direction and the sun transmittance, so it never mismatches the sky.
- **Optional extra:** volumetric god-rays as a 12-step shadow-map march with interleaved-gradient-noise jitter plus TAA (**medium**).
- **Underwater and caves:** underwater uses the water coefficients. Cave fog is gated by `eyeBrightnessSmooth`.
- **Recommend:** froxel aerial perspective plus analytic height fog (**cheap**); god-rays optional (**medium**).

## 3. Recommended stack and frame budget

| Feature | Choice | Cost |
|---|---|---|
| Sky | Hillaire LUTs (baked transmittance and multi-scatter, per-frame sky-view) | cheap |
| Clouds | Volumetric cumulus, 4×4 interleaved + reprojection, plus a 2D cirrus layer | medium |
| Shadows | Distorted 3072², PCSS-lite, colored translucency, contact shadows, foliage subsurface | medium |
| AO | GTAO 1 slice + TAA + vanilla AO at 0.4 | medium-cheap |
| Reflections | SSR with VNDF sampling, previous-frame color, LUT sky fallback | medium |
| Water | Normal-only wave octaves, Beer-Lambert, shadow-pass caustics | cheap-medium |
| Block light | Inverse-square remap plus emissive-mip color tint | cheap |
| Materials | Block-ID classes, Sobel normals, porosity-based wetness and puddles | cheap |
| Post | AgX, mip-based exposure, mip bloom, TAA + CAS, grain and vignette | cheap-medium |
| Fog | Froxel aerial perspective + height fog (optional god-rays) | cheap |

Estimated total is roughly 4–7 ms on a mid-range card at 1440p with medium settings [U, not measured]. Our memory notes on the deferred G-buffer still apply: translucents cannot blend into G-buffer targets. Resolve water and glass in `composite` against the opaque lighting.
