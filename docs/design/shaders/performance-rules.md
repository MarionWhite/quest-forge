# Performance rules

Hard rules for every pass, from [`research/performance.md`](research/performance.md)
and our own measurements. Budgets marked *target* are estimates until the
benchmark measures them; replace each with a measured number when one exists.

## What is expensive here

Measured 2026-10-16 on a Ryzen 9 7900X and RTX 5070 Ti at 2560×1440: the pack
is CPU-bound. The GPU sat at about 44% while Vibrant High ran 140–170 fps. The
CPU cost is geometry submission, and the shadow pass is the big one: it draws
every chunk and every entity a second time, every frame, and E7 cannot drop
entities from it. In a mob-heavy modpack that dominates. Pixel work is cheap by
comparison.

## Rules

1. **One extra geometry pass: the shadow pass.** Nothing else re-submits geometry.
   `shadowDistanceRenderMul = 1.0`.
2. **Shadow distance is the main quality lever.** Potato 0 (pass removed),
   Low 48, Medium 80, High 112, Ultra 144.
3. **All shadow-sampler declarations live in one resolve pass** (plus
   `gbuffers_water` if needed). OptiFine turns on the shadow pass if a sampler is
   declared anywhere, even inside a disabled `#ifdef`. The Potato profile
   disables `program.shadow` and that pass. *Verify* the pass disappears in the
   profiler.
4. **`shadowTranslucent=false`** unless it measures under 0.3 ms CPU. Tinted
   glass shadows come from `shadowcolor0` alpha.
5. **Shadow maps:** 1024 (Low), 1536 (Medium), 2048 (High and Ultra), distorted,
   hardware PCF plus 4–12 blue-noise taps by tier. Contact-hardening penumbra on
   Ultra only.
6. **Pass budget:** at most 4 deferred and 5 composite programs at full
   viewport, plus `final`. Merge any pass that does not need a neighbourhood read.
7. **Expensive effects at quarter resolution** in a corner of a full-size
   buffer (E7 has no per-buffer scaling), with depth-aware upsampling and
   temporal accumulation: volumetric light (8 steps), clouds (24 primary /
   5 light steps, 2×2 checkerboard, 4×4 on Low), reflections, AO.
8. **Every ray march has a fixed maximum** and an early-out on transmittance or
   hit, with blue-noise jitter resolved by TAA. No `while` loops; no
   data-dependent step count above 32.
9. **The sky is precomputed:** small lookup tables (Hillaire 2020) updated once
   per frame in the first deferred pass. Nothing ray-marches the atmosphere per
   pixel.
10. **Formats:** R11G11B10F for HDR colour and bloom, RGBA8 or RGB10_A2 for the
    G-buffer, RGBA16F only for TAA and cloud history. Never RGBA32F; never declare
    an RGBA format on `gdepth`. Six colour buffers or fewer.
11. **One bloom method:** a single mip chain on one R11G11B10F buffer.
12. **TAA is mandatory.** It is what lets everything else under-sample. Variance
    clipping, disocclusion test, a G-buffer flag for entities and hands.
13. **About 8 gbuffers programs**, using OptiFine's fallback chain, not 20:
    shorter compiles, fewer program switches.
14. **Never declare `centerDepthSmooth`** or anything else that reads back to the
    CPU. Never print from a hot path: that is what cost Vibrant 80% of its frame
    rate (fixed by qf-tweaks `GlErrorTransformer`).
15. **Stutter is a bug.** Shader recompiles, chunk-rebuild bursts and variable
    loops all show up as 1% lows. The benchmark reports 1% low and frames over
    33 ms for every scene; a change that worsens either is rejected even if the
    average improves.

## Budgets per tier at 1440p (total shader GPU time) — *targets*

| Tier | Hardware | GPU budget | Shadow distance |
|---|---|---|---|
| Ultra | RTX 5070 Ti | ≤ 3 ms | 144 |
| High | RTX 3060 | ≤ 6 ms | 112 |
| Medium | RTX 3060 | ≤ 4.5 ms | 80 |
| Low | GTX 1060, 1080p | ≤ 5 ms | 48 |
| Potato | integrated | shadows off | 0 |

CPU: the shadow pass takes at most 35% of main-thread render time on the 7900X
at High.

## How it is measured

`tools/` benchmark harness (`FrameBench`, in qf-content's debug package):
fixed scenes, every frame time recorded, mean / median / p99 / 1% low / frames
over 33 ms, GPU load sampled alongside. Slim trials (`tools/trial/`) for fast
iteration; full-pack runs for baselines and anything entity-heavy.

Also to test: OptiFine's "Smooth FPS" (`ofSmoothFps`, currently on in the live
instance) probably forces a CPU/GPU sync every frame.
