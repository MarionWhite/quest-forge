# Performance rules

Hard rules for every pass on Angelica's Iris pipeline. They come from
[`research/performance.md`](research/performance.md) (written for E7; its GPU
sections still hold), from our own measurements, and from the platform facts in
[`README.md`](README.md). Budgets marked *target* or *proxy* are estimates until
a benchmark measures them on the named hardware. Replace each one with a measured
number when it exists.

The owner's PC is not the floor. Friends on ordinary PCs must be able to play, so **the Low and Potato
presets are part of the pack, not an afterthought.** A feature that has no Low
answer doesn't ship.

## What is expensive here

**On E7 (2026-10-16)** the pack was CPU-bound. The GPU sat at about 44% while
Vibrant High ran 140–170 fps at 1440p. The shadow pass drew every chunk and
entity a second time, and E7 couldn't drop entities from it.

**On Angelica (2026-10-16/17, same PC, 1440p)**:

| | Static scene, mean fps (1% low) |
|---|---|
| Shaders off | 590 (101) |
| Vibrant High | 264 (88) |
| Complementary Unbound | 245 (85) |

The shader numbers are a lower bound: they sit at the monitor's 240 Hz vsync
cap. Celeritas builds chunks on worker threads and keeps them in VBOs, so the
shadow pass costs a fraction of E7's, and entities can leave the shadow pass
entirely. **Pixel work now matters again.** Budgets are GPU milliseconds first,
with CPU rules kept for the shadow pass and stutter.

On a weak PC both limits bite at once. A GTX 1060 is roughly 5–6× slower than
the dev PC's RTX 5070 Ti in raster throughput, and integrated graphics 15–55×
slower [I: 3DMark Time Spy class ratios, not measured here]. A 4-core CPU
also pays for every entity in the shadow pass.

## Rules

1. **One extra geometry pass: the shadow pass.** Nothing else re-submits
   geometry. Keep `shadowDistanceRenderMul = 1.0`. Voxelization
   (`voxelizeLightBlocks`) piggybacks on the shadow pass and is Ultra-only until
   measured.
2. **Shadow distance and shadow content are the main quality levers.**

   | Tier | Shadow distance | `shadowEntities` | `entityShadowDistanceMul` | `shadowBlockEntities` |
   |---|---|---|---|---|
   | Potato | none (pass off) | – | – | – |
   | Low | 48 | false | – | false |
   | Medium | 80 | true | 0.25 | false |
   | High | 112 | true | 0.5 | true |
   | Ultra | 144 | true | 1.0 | true |

   The player's own shadow (`shadowPlayer=true`) stays on from Low up, because
   it grounds the view.
3. **The shadow pass is switched explicitly.** Every profile sets `shadow.enabled`
   through the preprocessed `shaders.properties` (`#ifdef SHADOWS`). Don't rely
   on Iris detecting shadow samplers. Potato sets it false and must show
   "disabled by pack" in F3's shadow line. *Verify* that once per release.
4. **`shadowTranslucent=false`** unless it measures under 0.3 ms CPU. Tinted
   glass shadows come from `shadowcolor0` alpha.
5. **Shadow maps:** 1024 (Low), 1536 (Medium), 2048 (High and Ultra),
   distorted. Hardware PCF (`shadowtex0HW`) plus 0 (Low), 4 (Medium) or 8–12
   (High and Ultra) blue-noise taps. Contact-hardening penumbra on Ultra only.
6. **Pass budget at full viewport:** at most 4 `deferred` and 5 `composite`
   programs, plus `final`; Low at most 2 and 3; Potato at most 1 and 2. Merge any
   pass that doesn't need a neighbourhood read. `prepare` and `shadowcomp`
   passes count against the same totals.
7. **Expensive effects run in real sub-resolution buffers.** Use `size.buffer.colortexN`
   or `scale.<pass>`, not E7's corner-of-a-full-buffer trick. Each needs
   depth-aware upsampling and temporal accumulation:
   - volumetric light: 8 steps at quarter resolution; off on Low;
   - clouds: 24 primary and 5 light steps, 2×2 checkerboard; 2D clouds on Low
     and Potato;
   - screen-space reflections: half resolution; sky-fallback only on Low;
   - AO: half resolution, one GTAO slice; vanilla AO at 0.6 on Low.
8. **Every ray march has a fixed maximum** and an early-out on transmittance or
   hit, with blue-noise jitter resolved by TAA. No `while` loops, and no
   data-dependent step count above 32.
9. **The sky is precomputed:** small lookup tables (Hillaire 2020). Transmittance
   and multi-scatter tables are built once, in `setup` or on the first frame. The
   sky-view table is updated once per frame in a `prepare` pass. Nothing
   ray-marches the atmosphere per pixel.
10. **Formats:** R11G11B10F for HDR colour and bloom; RGBA8 or RGB10_A2 for the
    G-buffer; RGBA16F only for TAA and cloud history. Never RGBA32F; never an
    RGBA format on `gdepth`. Six colour buffers or fewer (five on Low, four on
    Potato), even though Iris offers 32: every target is a full-screen
    bandwidth cost.
11. **One bloom method:** a single mip chain on one R11G11B10F buffer. Low
    takes 4 mips; Potato takes none.
12. **TAA is mandatory from Low up.** It is what lets everything else
    under-sample. It needs variance clipping, a disocclusion test, and a
    G-buffer flag for entities and hands. Potato may use FXAA-class
    post-filtering instead.
13. **About 8 gbuffers programs**, using Iris's fallback chain
    (`terrain` → `textured_lit` → `textured` → `basic`, and so on), not 30.
    That means shorter compiles and fewer program switches.
14. **No CPU readbacks.** Iris itself has none (`centerDepthSmooth` is GPU-side,
    so it is allowed). Never add `glGetTexImage`-style debugging to the pack.
    Never log from a hot path.
15. **Stutter is a bug.** Shader recompiles, the compile when entering a new
    dimension folder, chunk-rebuild bursts and variable loops all show up as 1%
    lows. The benchmark reports the 1% low and frames over 33 ms for every
    scene. A change that worsens either is rejected even if the average improves.
16. **Low and Potato use only OpenGL 3.3 features.** That means no compute, no
    custom images and no SSBOs, so any GPU that can start Angelica can run them.
    Medium and up may use compute through `iris.features.optional`, inside
    `#ifdef IRIS_FEATURE_COMPUTE_SHADERS`, always with a fragment-shader path
    that produces the same image.
17. **At most six dimension program sets**: base, Nether, End, and three grouped
    modded folders. Their programs are stubs that `#define` the dimension and
    `#include` shared code. The first-entry compile is measured once per folder
    and must stay under 1 s on the dev PC.
18. **Profiles and options never change the material IDs**, so that one
    generated `block.properties` serves every tier.

## Budgets

"Shader cost" is the frame time with our pack minus the frame time with shaders
off, in the same scene, client and resolution. It is measured with
`vsync_mode` OFF, from `FrameBench` medians.

| Tier | Target hardware | Resolution | Shader cost | Whole frame | Shadow distance |
|---|---|---|---|---|---|
| Ultra | RTX 5070 Ti (dev PC) | 2560×1440 | ≤ 3 ms | – | 144 |
| High | RTX 3060 | 2560×1440 | ≤ 6 ms | ≥ 90 fps | 112 |
| Medium | RTX 3060 | 1920×1080 | ≤ 4.5 ms | ≥ 100 fps | 80 |
| **Low** | **GTX 1060 6 GB, 4-core CPU** | **1920×1080** | **≤ 5 ms** | **≥ 60 fps mean, 1% low ≥ 45, ≤ 0.5% of frames over 33 ms** | 48 |
| **Potato** | **Iris Xe (96 EU) / Radeon Vega 8** | **1280×720** | **≤ 6 ms** | **≥ 40 fps mean, 1% low ≥ 30** | off |

These are *targets* until measured on the named hardware.

**Below Potato** (Intel UHD 620 and older, about 55× slower than the dev PC):
play with shaders off, using the lite client
([`../../../tools/lite-client/README.md`](../../../tools/lite-client/README.md)).
GPUs without OpenGL 3.3 use the E7 client, also with shaders off.

### The Low and Potato presets are mandatory

- Both appear in `shaders.properties` as `profile.LOW` and `profile.POTATO`.
  They are selectable on the shader screen. Each profile sets one option,
  `QF_PRESET` (0 Potato, 1 Low, 2 Medium, 3 High, 4 Ultra), and every effect
  keys off it, so the bench selects a tier with `-PackOpts @{QF_PRESET='1'}`.
- The **pack default is Medium.** The lite client must switch it to Low or
  Potato. To do that, `tools/lite-client/apply-lite.ps1` has to learn to write
  `shaderpacks\<pack>.txt`; it doesn't yet. A friend
  who only installs the pack and presses F4 must never land on Ultra.
- Every milestone ships with Low and Potato passing their proxy budgets. Missing
  either is a failed milestone, not a follow-up task.
- **What Low keeps:** the physically based sky lookup tables, sun shadows at 48
  with no entities except the player, the water model, TAA, auto-exposure, the
  tone mapper, the 4-mip bloom, block-ID waving and emissives, and the readable
  night floor.
- **What Low drops:** volumetric clouds (a 2D layer instead), volumetric light,
  SSR (sky fallback only), GTAO (vanilla AO at 0.6), wetness puddles (wetness
  tint only) and contact-hardening shadows.
- **Potato** also drops the shadow pass, TAA (an FXAA-class filter instead) and
  bloom. It keeps the sky, water, exposure and colour. Readable darkness and
  neutral colour (look bible Tier A) apply to Potato too.

### Proxy budgets on the dev PC

There is no GTX 1060 or integrated-GPU PC on hand. Until a friend's PC runs the
scene set, each milestone checks Low and Potato on the dev PC against *proxy*
budgets: the target cost divided by the approximate speed ratio [I].

| Tier | Measure at | Proxy shader cost on the RTX 5070 Ti | Ratio used |
|---|---|---|---|
| Low | 1920×1080 | ≤ 0.9 ms | ÷ 5.5 (GTX 1060) |
| Potato | 1280×720 | ≤ 0.4 ms | ÷ 15 (Iris Xe) |

The CPU proxy is the bench's existing 4-core / 8-thread affinity run
(`run_bench_lo.ps1`). At Low it must keep the 1% low within 10% of the
shaders-off run.

These ratios are guesses with a wide error bar. **Before release**, one real
GTX 1060-class PC and one integrated-GPU laptop from the friend group run the
scene set on Low and Potato. Their numbers replace this table.

### CPU

The shadow pass takes at most 25% of main-thread render time at High on the
dev PC, and at most 15% at Low on the 4-core proxy. Entities are the cost to
watch: a mob crowd scene with `shadowEntities=true` versus `false` is part of
every High-tier round.

## How it is measured

- **Harness.** `FrameBench`, in qf-content's debug package, flies fixed scenes,
  records every frame time, and reports mean, median, p99, 1% low and frames
  over 33 ms. `nvidia-smi` samples GPU load alongside. It is launched by
  `C:\qfb\run_bench.ps1 -Client C:\qfb\client-ang -ForgeJar <1614 jar>`; see
  [`review-loop.md`](review-loop.md).
- **Vsync.** Frame pacing must be off (`"vsync_mode": "OFF"` in the client's
  `config/angelica-options.json`). Otherwise every result sits at 4.16 ms.
- **Per-pass cost.** Angelica's core profile lets RenderDoc or Nsight Graphics
  capture a frame and time each pass [I: untested here]. Use them when a tier
  misses its budget, not on every round.
- **Clients.** Use full-pack runs on `C:\qfb\client-ang` today.
  `tools/trial/trial.py` has no Angelica base set yet, so there are no slim
  trials. When the final client, built without Hodgepodge and ArchaicFix, takes
  over, re-baseline the shaders-off and Vibrant numbers first.
- **Gone with E7.** OptiFine's "Smooth FPS" question is moot: Angelica has no
  such setting.
