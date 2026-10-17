# Shader pack performance research (OptiFine 1.7.10 HD U E7)

> **Platform note (2026-10-17):** the pack now targets Angelica's Iris backport, not E7. Wherever this report describes E7 features, limits or traps, [`../README.md`](../README.md) "Platform facts" wins. The technique, cost and licence findings still apply.

Target: high average FPS and stable 1% lows on Ryzen 9 7900X + RTX 5070 Ti at 1440p (CPU/driver bound, GPU at ~44%), with quality tiers for weaker friend PCs.

Confidence tags:
- **[V-jar]**: verified by disassembling `%APPDATA%\.crazycraft4\mods\OptiFine_1.7.10_HD_U_E7.jar` (javap), including the `doc/shaders.txt` and `doc/shaders.properties` bundled inside the jar.
- **[V-src]**: verified from the cited source.
- **[U]**: unverified. This covers engineering estimates and recollections. Measure these before relying on them.

**The current online docs do not describe E7.** E7 was released on 04.04.2018 ([downloads](https://optifine.net/downloads)). Its shader code matches the 1.12.2 C7-era feature set. The online [shaders.properties doc](https://github.com/sp614x/optifine/blob/master/OptiFineDoc/doc/shaders.properties) describes features that arrived years later, as its [commit history](https://github.com/sp614x/optifine/commits/master/OptiFineDoc/doc/shaders.properties) shows. Use the docs bundled in the jar as the spec.

---

## 1. CPU-side / OptiFine-side levers (what E7 actually has)

### Not available in E7 [V-jar]

None of the following strings appear in the E7 classes or in its bundled doc:

| Feature | When it arrived | Source |
|---|---|---|
| `shadowTerrain`, `shadowEntities`, `shadowBlockEntities` | Mar 2021 | commit d5ef351 |
| `shadow.culling` | Dec 2021 | commit 1403369 |
| `size.buffer.*` | Feb–Mar 2021 | — |
| `scale.<program>` and `flip.<program>.<buf>` | 1.12.2 C9 | [1.12.2 changelog](https://optifine.net/changelog?f=OptiFine_1.12.2_HD_U_G5.jar) |
| `frustum.culling`, `separateAo` | 1.12.2 D1 | [1.12.2 changelog](https://optifine.net/changelog?f=OptiFine_1.12.2_HD_U_G5.jar) |
| `rain.depth`, `particles.before.deferred` | later | — |
| `shadowcomp`, `prepare`, compute shaders | later | — |
| vec custom uniforms | later | — |

Other E7 limits:
- **Custom uniforms are float, int and bool only.** The bundled doc lists `uniform.<float|int|bool>`. You can read vector components with `.x`, `.y`, `.z`.
- **Program conditions don't exist yet.** `program.X.enabled=<expr>` came in C9 and is not in the E7 changelog, which matches your "unreliable" observation.
- **Profiles can still disable programs.** Use `profile.LOW=... !program.composite3`. This has worked since D7 188_H2, per the [E7 changelog](https://optifine.net/changelog?f=OptiFine_1.7.10_HD_U_E7.jar).

### Available in E7 [V-jar]

- `shadowTranslucent=true|false` in `shaders.properties`. This is the only shadow-pass geometry toggle.
- `backFace.solid|cutout|cutoutMipped|translucent` for back-face culling per layer.
- `const float shadowDistance` and `const float shadowDistanceRenderMul`. When `shadowDistanceRenderMul` > 0, `shadowRenderDistance = shadowDistance * mul`, which limits which chunks the shadow pass submits.
- `shadowIntervalSize` and `shadowMapResolution`.
- `shadowHardwareFiltering`, `shadowtexNearest` and the `*Mipmap` consts.
- `<buf>Format`, `<buf>Clear=false` and `<buf>MipmapEnabled` (composite, deferred and final only).
- `texture.noise`, `texture.<stage>.<name>`, `profile.*`, `screen.*`, `sliders`, `uniform.*` and `variable.*`.
- Programs: `deferred`..`deferred7`, `composite`..`composite7`, `final`, plus the internal `deferred_last` and `composite_last` ping-pong restore passes.
- In-game Shaders menu options: Render Resolution multiplier (`RENDER_RES_MUL`), Shadow Quality (`SHADOW_RES_MUL`), `SHADOW_CLIP_FRUSTRUM`, FXAA, Hand Depth, Old Lighting and Cloud Shadow.

### How the E7 shadow pass works [V-jar, from `ShadersRender.renderShadowMap`]

- **It runs every frame.** `shadowPassInterval` is hard-coded to 1 whenever any shadow depth buffer is used.
- **It submits terrain, entities and translucent geometry.** The pass sets up a shadow camera, builds a shadow frustum (`ClippingHelperShadow`, which is always on), and runs its own setup-terrain/update-chunks step. It then draws:
  1. all sorted terrain renderers;
  2. entities and block entities;
  3. "copy shadow depth" (a full shadow-map copy, done only when `shadowtex1` is used);
  4. translucent geometry (only if `shadowTranslucent`);
  5. a second entity pass;
  6. shadow mipmaps (only if requested).
- **Face culling is off in the shadow pass.** `disableCull` is called, so both faces are rasterized.
- **Entities cannot be removed from the shadow pass in E7.** In a mob-heavy modpack this is the single biggest CPU cost of shadows. The 1.7.10 entity, TESR and Tessellator path is immediate-mode, so every entity and tile entity is submitted twice. A vertex shader can collapse entity vertices (`gl_Position = vec4(2.0, 2.0, 2.0, 1.0)`) to save GPU raster, but **the CPU submission still happens** [U]. Modern packs ship "entity shadows off" in their low profiles for this reason: see Photon's low and medium profiles and Complementary's POTATO to MEDIUM profiles ([Photon](https://raw.githubusercontent.com/sixthsurge/photon/main/shaders/shaders.properties), [Complementary](https://raw.githubusercontent.com/ComplementaryDevelopment/ComplementaryReimagined/main/shaders/shaders.properties)). That option needs newer OptiFine or Iris.

### Gotchas: OptiFine detects resources by scanning source lines, not the preprocessed shader [V-jar]

When loading each program, `Shaders` reads every line, applies option rewrites, and checks each `uniform` line by name with `ShaderParser.parseLine`. It does no `#ifdef` evaluation, because no preprocessor exists in E7.

1. **A shadow sampler declaration turns on the whole shadow pass.** If any loaded program declares `uniform sampler2D shadow`, `shadowtex0`, `shadowtex1` or `shadowcolor*`, the shadow pass runs every frame. This is true even inside an `#ifdef` that is switched off. A real "shadows OFF" tier therefore needs a profile that does `!program.shadow` and also disables every program declaring a shadow sampler.
   - Design for this: put all shadow-map sampling in one dedicated **shadow-resolve composite or deferred pass**. It writes a screen-space shadow mask into a colortex. The low profile disables that one program.
   - Encode the mask so that the cleared value (0) means "lit".
   - `gbuffers_water` is the exception. It must either stay unshadowed in that tier or come from a separate program file. **[U: whether the shadow pass is fully skipped when `program.shadow` is disabled but a sampler is still declared. Test it with the profiler string "shadow pass".]**
2. **`centerDepthSmooth` causes a GPU→CPU sync point every frame.** Declaring `uniform float centerDepthSmooth` anywhere sets `centerDepthSmoothEnabled`. `readCenterDepth()` then calls `glReadPixels` on the depth buffer every frame, outside the shadow pass. That stalls the pipeline, which is exactly the wrong thing in a CPU/driver-bound game. **Never declare it.** If you need autofocus for depth of field, sample depth at the screen centre into a 1-pixel region of a buffer with `Clear=false` and smooth it on the GPU.
3. **Buffer allocation follows the highest index you mention.**
   - Mentioning `colortex7` or `gaux4` allocates all 8 colour buffers.
   - Mentioning `depthtex2` allocates three depth buffers plus extra copies.
   - Declaring `gdepth` with an RGBA format silently upgrades buffer 1 to **RGBA32F** (bundled shaders.txt). Use `colortex1` or set an explicit format.
4. **OptiFine adds fixed CPU overhead you cannot remove.**
   - `checkGLError` (that is, `glGetError`) is ungated and called from about 74 sites.
   - Model-view matrices are read back with `glGetFloat`.
   - Test the NVIDIA "Threaded optimization" setting both on and off, because `glGet*` calls can serialize the driver thread. [U]

### Levers ranked by CPU impact for us

1. **`shadowDistanceRenderMul`.** Set it to 1.0 so the shadow pass only submits chunks inside `shadowDistance` (Sildur's and older packs do this) [V-jar mechanics; U magnitude]. Shadow distance is the strongest CPU knob: chunk draw calls in the shadow pass scale roughly with the area of the shadow volume. Starting points:
   - Low tier: 48–64 blocks.
   - High tier: 96–128 blocks.
   - Do not go above 160 even on the 5070 Ti, because the CPU pays for it.
2. **`shadowTranslucent=false` on low and medium.** This removes a whole terrain layer from the shadow pass and fakes water and glass shadows. This setting is per pack, not per profile [U: whether the macro can switch it]. If it cannot, decide one value for every tier.
3. **Keep frustum clipping on.** Leave the in-game Shadow Clip Frustum at its default (on) and document it for friends [U: exact semantics].
4. **Draw each geometry type once.**
   - Don't add gbuffers programs that need separate passes. In E7, each gbuffers program is just a shader switch, not an extra geometry pass; only shadow adds a pass.
   - Use the fallback chain instead of 15 distinct programs, because program switches cost driver time on every chunk batch [U magnitude].
   - Keep `gbuffers_entities`, `gbuffers_block` and `gbuffers_hand` lightweight. Entities are the CPU-bound part.
5. **Use as few buffers as you can.** Use `colortex0`–`5` unless you need more, avoid `depthtex2`, and only sample `shadowtex1` if you really need translucent shadow depth. Each extra one adds a full copy.
6. **Use the 1.7.10 renderer settings (outside the pack).**
   - Lower render distance and lower OptiFine "Chunk Updates" values.
   - Turn off "Smooth FPS". `glFinish` and the `smoothFps` field both appear in OptiFine's RenderGlobal patch [V-jar strings; U behaviour], and a `glFinish` forces a CPU stall.

---

## 2. GPU-side best practices and rough costs at 1440p (3.7 MP)

These are bandwidth floors for a trivial full-screen pass that reads and writes one RGBA16F target (about 59 MB): roughly **0.16 ms on an RTX 3060** (360 GB/s) and **0.07 ms on a 5070 Ti** (896 GB/s) [U, derived]. Real passes cost 2–10 times that floor.

**E7 limit on resolution:** E7 cannot render a composite pass at reduced resolution (no `scale.`, no `size.buffer`). There are two ways to fake it:
- Render low-res effects into the top-left quarter of a full-size buffer. Fragments outside that region `discard` or return immediately (about 0.03–0.08 ms of wasted invocations on a 3060 [U]). A later pass samples the quarter with UV×0.5.
- Use checkerboard or interleaved pixel updates.

| Feature | Recommended approach | Budget, 3060 @1440p | Budget, 5070 Ti |
|---|---|---|---|
| Shadow map | 2048² (high), 1024–1536² (low) with a distorted projection (bias toward the player, like Sildur's/BSL) instead of cascades, which E7 can't render as multiple shadow passes. Use `shadowHardwareFiltering` (free 2×2 PCF via `shadow2D`) plus 4–8 Poisson or Vogel taps rotated by blue noise, then let TAA resolve. Avoid PCSS's blocker search (16+ taps) except on Ultra. Variance shadow maps need a float `shadowcolor` plus a blur pass and leak light; skip them. | 0.3–0.6 ms raster (geometry-bound) + 0.2–0.4 ms filtering | ~0.1 + 0.1 |
| AO | GTAO at half res: 1 slice and 4–8 steps per frame, rotated temporally and accumulated. That is 0.5 ms at 1080p on PS4 ([Jimenez 2016](https://research.activision.com/publications/archives/practical-real-time-strategies-for-accurate-indirect-occlusion), [XeGTAO](https://github.com/GameTechDev/XeGTAO)). Plain SSAO (8–12 taps) is cheaper but worse; HBAO sits in between. Photon uses SSAO on low and medium and GTAO on high ([Photon](https://raw.githubusercontent.com/sixthsurge/photon/main/shaders/shaders.properties)). | 0.4–0.8 ms | 0.15–0.3 ms |
| SSR | Linear march with a coarse step, then a binary refine (4–6 steps), at half res. Only march where specular roughness < τ. Hi-Z tracing ([McGuire & Mara 2014](https://jcgt.org/published/0003/04/04/)) needs a depth min-mip chain that E7 can only build with several composite passes, so it's not worth it here. Fall back to the sky or a cubemap colour. | 0.5–1.0 ms (water-heavy views) | 0.2–0.4 ms |
| Volumetric light | Ray-march 6–12 steps at quarter res, offset per pixel with blue noise, accumulate temporally, then bilateral upsample. Skip it when the sun is occluded or the sky light level is 0. | 0.4–0.8 ms | 0.15–0.3 ms |
| Volumetric clouds | Quarter res plus 1/4 (2×2) or 1/16 (4×4) checkerboard updates with reprojection. Use 16–32 primary steps and 4–6 light steps, exit early at transmittance < 0.05, and stop at the cloud-layer bounds. Nubis ran in under 2 ms on PS4 ([Guerrilla](https://www.guerrilla-games.com/read/nubis-evolved)), updating about 1/16 of the rays per frame (community summary [U]). 2D/planar clouds are a cheap low-tier option. | 0.8–1.5 ms | 0.3–0.6 ms |
| Sky / atmosphere | Precomputed LUTs in the style of [Hillaire 2020](https://diglib.eg.org/handle/10.1111/cgf14050): transmittance (~256×64), multi-scatter (~32×32) and sky-view (~192×108). Keep them in a corner region of a `Clear=false` buffer and update them in one deferred pass, or only when the sun moves. Per-pixel sky ray-marching costs 10–50× more. Sizes are recalled; the paper's timings are about 0.1–0.3 ms total on a high-end PC [U]. Store aerial perspective as a tiled 2D texture, as one implementation did ([fgdata](https://git.nayala.duckdns.org/fly/fgdata/src/commit/37f43bd671d192753b2f4527a2b66ab8e696786d/Shaders/HDR/atmos-aerial-perspective.frag)). | 0.05–0.15 ms | <0.05 ms |
| Bloom | A downsample/upsample mip pyramid: 13-tap down and tent up (COD:AW style), or dual-Kawase ([Unity URP notes](https://docs.unity.com/en-us/engine/6000.7/manual/post-processing-and-full-screen-effects/urp/effect-list/bloom.md)). E7 has no separate per-mip targets. Either generate mips with `colortexNMipmapEnabled` (box filter, so it flickers unless you tent-filter on read), or tile all levels into one buffer from two composite passes. | 0.2–0.4 ms | <0.15 ms |
| TAA | Reproject with `gbufferPreviousModelView`, `gbufferPreviousProjection` and `previousCameraPosition` [V-jar]. Keep history in a `Clear=false` buffer, clamp to the 3×3 neighbourhood in YCoCg (variance clip), and blend 0.9–0.95 ([Karis 2014](https://advances.realtimerendering.com/s2014/)). Reject history on depth disocclusion. Give hands, entities and particles a flag in the G-buffer, because E7 has no velocity buffer and moving entities ghost under pure camera reprojection. | 0.15–0.3 ms | <0.1 ms |
| Formats | Use **R11G11B10F** (4 B/px) for HDR scene colour and bloom, **RGBA8** or **RGB10_A2** for packed normals and material data, and **RGBA16F** (8 B/px) only for history and accumulation buffers that need alpha or precision. Never use RGBA32F (watch the `gdepth` trap). Each RGBA16F to R11G11B10F switch halves that buffer's bandwidth. All of these formats are listed in the bundled E7 shaders.txt [V-jar]. | — | — |

General rules:
- Every full-res composite pass costs at least about 0.15 ms on a 3060, so **merge passes**.
- **Keep branches coherent.** Branch on sky versus terrain, or on large regions, rather than per-pixel noise.
- **Exit early** on sky pixels, `depth == 1`, underwater, and night.
- **Trade samples for frames:** use blue-noise dither plus temporal accumulation (e.g. [Peters' free blue noise textures](https://momentsingraphics.de/BlueNoise.html)), animated per frame with `frameCounter` plus an R2 or golden-ratio offset. Load it via `texture.noise=` (E6+ [V-src changelog]).

---

## 3. Frame-time stability (1% lows)

| Spike source | Mitigation |
|---|---|
| **Shader compile / recompile.** Every option or profile change, F3+R and dimension change recompiles all programs synchronously. The driver may also compile state-dependent variants on first use [U]. | Never touch options in play. Keep the program count low, because compile time scales with programs × source size. Rely on the NVIDIA GL disk shader cache and don't let users disable it. Precompute LUTs rather than using huge unrolled loops. Per-dimension folders (`world-1`) compile when you enter the dimension, so avoid them unless you need them. |
| **CPU sync points.** `glReadPixels` from `centerDepthSmooth` (above), any `glFinish` or Smooth FPS, and `glGetError`/`glGet*` with threaded drivers. | Don't use `centerDepthSmooth`. Turn Smooth FPS off. A/B test Threaded optimization. |
| **Chunk rebuild bursts** while flying or teleporting. 1.7.10 builds chunks on the main thread, and `ShadersTess` makes each vertex fatter (`mc_Entity`, `mc_midTexCoord`, `at_tangent`), so each rebuild is slower than vanilla [U magnitude]. The shadow pass doesn't rebuild chunks, but a newly visible chunk lands in both passes. | Keep OptiFine Chunk Updates at 1–2 with Dynamic Updates on. Keep `shadowDistanceRenderMul` at ≤1.0 so the shadow pass doesn't widen the visible set. |
| **Variable-length loops.** A ray march that sometimes runs 64 steps and sometimes 4 produces frame-time variance that depends on the view: looking at the sky versus the ground, or clouds filling the screen. | Use fixed step counts with early-out, and set the *upper bound* low. Spread work across frames (checkerboard) rather than doing more per pixel. Budget for the worst case, such as looking straight at the horizon in rain. |
| **Per-frame mipmap generation** (`*MipmapEnabled`, `generateShadowMipmap`). Constant cost rather than spikes, but it doubles memory traffic on the 3060. | Only generate mips for one small or medium buffer. Never mip the shadow map. |
| **Java GC pauses and modpack ticks** (outside the pack). These often dominate the 1% lows in a 140-mod pack. | Use a sensible `-Xmx` and Java 8 G1 flags. Check whether a spike is the GPU or the JVM before blaming the shader (F3 or `-Dshaders.debug` profiler). |
| **Lighting transitions** (`eyeBrightnessSmooth`, `wetness`) | GPU-cheap, but avoid recomputing LUTs on transitions. Update them incrementally. |

---

## 4. How respected packs structure tiers

- **Complementary Reimagined** ([shaders.properties](https://raw.githubusercontent.com/ComplementaryDevelopment/ComplementaryReimagined/main/shaders/shaders.properties)) [V-src]. Profiles run POTATO, VERYLOW, LOW, MEDIUM, HIGH, VERYHIGH, ULTRA, COMPLEMENTARY.
  - Shadows: off in POTATO, then quality 0 to 3.
  - **Shadow distance: 64, 96, 128, 192, 224, 256.**
  - Light shafts: 0 to 3.
  - Entity shadows: on only from HIGH up.
  - Also scaled: reflection quality, clouds, colored lighting, and anisotropic filtering.
  - Reflections render at reduced size via `size.buffer`.
- **Photon** ([shaders.properties](https://raw.githubusercontent.com/sixthsurge/photon/main/shaders/shaders.properties)) [V-src]. Profiles: low, medium, high, ultra.
  - Shadow map 1024 to 2048.
  - Colored shadows on from high.
  - Volumetrics on from medium.
  - Entity shadows on from high; block-entity shadows only on ultra.
  - AO goes SSAO to GTAO.
  - Screen-space ray-traced shadows on from high.
  - Clouds use temporal upscaling factors 1.0 to 0.25 (separate setting).
  - The sky map is a fixed 192×108 buffer.
  - Passes are toggled via `program.*.enabled`, which isn't available in E7.
- **Bliss** [V-src]. No quality profiles, only tonemap presets. Settings are manual sliders, and entity shadows are toggled with `shadowEntities`.
- **BSL, SEUS, Rethinking Voxels** [U, from memory]. BSL scales shadow resolution and distance, AO, light shafts, clouds and reflections per profile. SEUS PTGI scales GI ray counts and resolution. Rethinking Voxels voxelizes the world through the shadow pass, so its cost is dominated by shadow-pass geometry; that's the opposite of what we want.
- **Common pattern.** Tiers mainly change four things:
  1. shadow distance and resolution (the CPU and GPU levers);
  2. entity shadows;
  3. ray-march sample counts (volumetric light, clouds);
  4. resolution of expensive buffers.

  Low tiers delete whole passes rather than lowering per-pixel quality.

---

## 5. Prioritized performance rules for our pack

1. **Never declare `centerDepthSmooth`,** and never call anything that reads back to the CPU.
2. **Use exactly one geometry re-submission: the shadow pass.** Always set `shadowDistanceRenderMul = 1.0`. Shadow distance per tier: Potato 0 (pass removed), Low 48, Med 80, High 112, Ultra 144.
3. **All shadow-sampler declarations live in one shadow-resolve program** plus `gbuffers_water`. The Potato profile disables `program.shadow` and that resolve pass, which removes the shadow pass entirely. Verify in the profiler that "shadow pass" disappears.
4. **Use `shadowTranslucent=false`** unless the measured cost on the 5070 Ti is under 0.3 ms CPU. Don't sample `shadowtex1`; use `shadowcolor0` alpha for tinted glass if you need it.
5. **Shadow maps:** 1024 (Low), 1536 (Med), 2048 (High/Ultra), distorted, with hardware PCF plus 4 (Low) to 12 (Ultra) blue-noise taps. PCSS only on Ultra.
6. **Pass budget:** at most 4 deferred and 5 composite programs at full viewport, plus final. Merge anything that doesn't need a neighbourhood read. Target **≤ 1.5 ms of total post-processing on a 3060.**
7. **Expensive effects run in the quarter-res corner region,** reconstructed with a depth-aware bilateral upsample and temporal accumulation: volumetric light 8 steps, clouds 24/5 steps with a 2×2 checkerboard (4×4 on Low), SSR, and AO.
8. **Every ray march** has a fixed maximum, transmittance or hit early-out, and blue-noise jitter with TAA resolve. No `while` loops and no data-dependent step counts above 32.
9. **Sky LUTs** are computed once per frame into a 256×128 corner of a `Clear=false` buffer, in the first deferred pass. Nothing ray-marches the atmosphere per pixel.
10. **Formats:** R11G11B10F for HDR colour and bloom, RGBA8 or RGB10_A2 for the G-buffer, RGBA16F only for TAA and cloud history. Never use RGBA32F. Use 6 colortex or fewer.
11. **Pick one bloom method:** either a single mip chain via `MipmapEnabled` on one R11G11B10F buffer, or a two-pass tiled pyramid. Don't do both.
12. **TAA is mandatory** (it lets everything else under-sample). Use variance clipping, a depth-disocclusion test, and a G-buffer flag for entities and hands.
13. **Program count:** use the fallback chain so you have about 8 gbuffers programs total, not 20. That keeps compile time down and means fewer program switches.
14. **Budgets per tier at 1440p** (total shader GPU cost, excluding vanilla raster) [U targets]:
   - Ultra: 5070 Ti ≤ 3 ms, which leaves headroom because we are CPU bound.
   - High: 3060 ≤ 6 ms.
   - Medium: 3060 ≤ 4.5 ms.
   - Low: GTX 1060-class at 1080p ≤ 5 ms.
   - CPU: shadow pass ≤ 35% of main-thread render time on the 7900X at High.
15. **Measure, don't guess.**
   - Use F3 plus the profiler pie chart (shadow-pass share).
   - Use Nsight or RenderDoc for GPU timings per pass.
   - Use PresentMon or CapFrameX for 1% and 0.1% lows on a fixed flight path, comparing a mob farm against open terrain.
   - Test every tier on the 5070 Ti with the GPU clock-limited to approximate a 3060 [U method].

---

### Sources

- [OptiFine 1.7.10 E7 changelog](https://optifine.net/changelog?f=OptiFine_1.7.10_HD_U_E7.jar)
- [OptiFine 1.12.2 changelog](https://optifine.net/changelog?f=OptiFine_1.12.2_HD_U_G5.jar)
- [OptiFine downloads (release dates)](https://optifine.net/downloads)
- [shaders.txt (current)](https://github.com/sp614x/optifine/blob/master/OptiFineDoc/doc/shaders.txt)
- [shaders.properties (current)](https://github.com/sp614x/optifine/blob/master/OptiFineDoc/doc/shaders.properties) and [its history](https://github.com/sp614x/optifine/commits/master/OptiFineDoc/doc/shaders.properties)
- [Photon](https://raw.githubusercontent.com/sixthsurge/photon/main/shaders/shaders.properties)
- [Complementary Reimagined](https://raw.githubusercontent.com/ComplementaryDevelopment/ComplementaryReimagined/main/shaders/shaders.properties)
- [Bliss](https://raw.githubusercontent.com/X0nk/Bliss-Shader/main/shaders/shaders.properties)
- [Hillaire 2020](https://diglib.eg.org/handle/10.1111/cgf14050)
- [GTAO (Jimenez 2016)](https://research.activision.com/publications/archives/practical-real-time-strategies-for-accurate-indirect-occlusion)
- [XeGTAO](https://github.com/GameTechDev/XeGTAO)
- [Nubis Evolved](https://www.guerrilla-games.com/read/nubis-evolved)
- [McGuire & Mara SSR](https://jcgt.org/published/0003/04/04/)
- [Karis TAA (SIGGRAPH 2014 Advances)](https://advances.realtimerendering.com/s2014/)
- [Blue noise (Peters)](https://momentsingraphics.de/BlueNoise.html)
- [Unity URP bloom notes](https://docs.unity.com/en-us/engine/6000.7/manual/post-processing-and-full-screen-effects/urp/effect-list/bloom.md)
- Local: the docs bundled in the E7 jar (`doc/shaders.txt`, `doc/shaders.properties`) and javap output of `shadersmod.client.Shaders` and `ShadersRender`.
