# Brief: ambient occlusion (short)

Grounding at block corners without rounding the voxels. Read with [`README.md`](README.md).

## 1. What the owner asked for

- r000 direction: blocks as "compelling, high quality, high resolution renditions", not
  photoreal surfaces.
- r006 overall: "I like the light to interact with the blocks realistically."
- Look bible 11: "Grounding ambient occlusion, subtle at block corners so the voxels still
  read." Anti-pattern: "Rounded-off voxel edges (heavy parallax, over-smooth normals)."

Nothing in six rounds was a direct AO question; the owner notices light on blocks (r001 "how
the light hits the blocks in the background"), which is where AO shows.

## 2. What we do now

Vanilla vertex AO only. `shaders.properties` sets `separateAo = true`, so the vertex AO
arrives in the colour alpha and `program/gbuffers.glsl` writes it to `colortex2.b`
(`ao = vColor.a`). `lib/lighting.glsl` `shadeSurface` applies `mix(1, ao, QF_AO_STRENGTH)` to
the sky, block-light, night-floor and bounce terms (0.6 on Potato and Low, 0.8 Medium and up).
With `QF_PBR 1` the LabPBR normal map's blue channel multiplies in at 0.8. There is no
screen-space AO, no half-resolution buffer, and the G-buffer normal is the face normal.

## 3. What the top packs do

- **Photon** [V, `shaders.properties`]: screen-space AO on Low and Medium, a "more precise
  ground-truth" method (GTAO) on High and Ultra; the AO buffer runs at half resolution; the
  README lists "Detailed ambient occlusion (GTAO)".
- **Jimenez et al. 2016, GTAO** [V, PDF
  https://www.iryoku.com/downloads/Practical-Realtime-Strategies-for-Accurate-Indirect-Occlusion.pdf]:
  horizon angles measured from the view vector so the inner integral is analytic; a binary
  visibility with an attenuation that blends to zero toward the maximum radius; half
  resolution, **one slice direction per pixel**, a 4x4 bilateral spatial gather and six
  temporal rotations with reprojection, for 96 effective directions at **0.5 ms on a PS4 at
  1080p**; a thickness heuristic (blend the horizon toward an exponential average when the
  new sample's cosine drops) so leaves and branches do not over-occlude; a multi-bounce fit
  G(A, albedo) = a A^3 - b A^2 + c A with a = 2.0404 rho - 0.3324, b = 4.7951 rho - 0.6417,
  c = 2.7552 rho + 0.6903 that returns the energy plain AO loses.
- **XeGTAO** (Intel) [V, https://github.com/GameTechDev/XeGTAO, MIT, archived 2024]: three
  compute passes (depth MIP prefilter, main, denoise); defaults 3 slices x 6 samples per pixel
  at full resolution (Low 2 x 4), a 5x5 depth-aware denoiser with TAA for temporal
  accumulation, thin-occluder compensation off by default; 0.56 ms at 1080p on an RTX 2060,
  2.39 ms on an i7-1195G7's integrated GPU, 1.4 ms at 4K on an RTX 3070 (High preset).
- **Complementary** (BSL-derived) has AO [U]; **Solas**, **Kappa**, **Sundial** do not
  describe theirs.

## 4. The technique

GTAO at half resolution, one slice per pixel, resolved by our TAA, multiplied with the vanilla
vertex AO so the crisp block-corner darkening stays:

```
pass gtao (deferred stage, before lighting: scale.deferred = 0.5, writes a half-res R8 buffer)
  reconstruct view position and normal (G-buffer normal, flat faces) at the half-res texel
  slice angle = IGN(texel, frameCounter) * pi            (one slice; TAA and the 5x5 filter average it)
  for each of the two sides: 4 steps (Low preset of XeGTAO), radius 2.5 blocks projected to pixels, clamped to 64 px
     sample depth, horizon cosine relative to the view vector, thickness heuristic blend, falloff over the last 30% of the radius
  visibility = analytic arc integral of the two horizons (Jimenez eq. 7), projected-normal weighted
  out = visibility
pass lighting (deferred1, full res): ao_ss = depth-and-normal-aware 4-tap upsample of the R8 buffer (5x5 denoise folded into the upsample weights)
  ao_ss = multibounce(ao_ss, albedo)        (the cubic fit)
  ao = ao_ss * mix(1, vertexAO, 0.5)        (vertex AO at 0.5 when GTAO is on, 0.8 when it is not)
```

Flat voxel faces are the easy case for a horizon method (no normal noise); the hard cases
are cutout leaves and fences (thickness heuristic) and the hand (exclude by `FLAG_HAND`).
Radius 2.5 blocks grounds a torch on a wall and a chest on the floor without darkening whole
rooms; the multi-bounce fit stops corners going black (look bible 1).

Programs: `deferred` becomes GTAO at half resolution, `deferred1` the lighting. High allows
four deferred programs. Render target: one half-resolution R8 (0.9 MB at 1440p).

## 5. Low and Potato

Vanilla AO only, at 0.6 (as today, and as `performance-rules.md` "What Low drops" says). GTAO
from Medium up, since it needs TAA to hide the single slice and Low's budget has no room.

## 6. Cost

- **[measured]** GTAO 0.5 ms on PS4 at 1080p (half res, one slice, 4x4 spatial, six temporal);
  XeGTAO High 0.56 ms at 1080p on an RTX 2060 (full res, 18 samples).
- **[estimate]** Ours at 1440p High on the dev PC: half resolution, one slice, 8 samples, 0.06
  to 0.12 ms including the upsample. On an RTX 3060 (the High target) about 0.3 ms.
- Measure: `--scenes plains_noon,golden_lit,texture_wall,torch,biome_roofed,gallery` toggling
  the new option; `check_frames.py --max-crushed` guards over-darkening.

## 7. Test scenes and reference photos

Views: `plains_noon` (block corners in flat light), `golden_lit`, `biome_roofed` (dark
canopy, the leaves test), `torch` (tunnel corners under block light), `texture_wall`,
`gallery`. Photos: none that help; the reference is restraint. If one is wanted, overcast
photographs of stone walls meeting pavements show the real scale of corner darkening.

## 8. Pitfalls

Angelica: at the deferred stage `depthtex0` holds only opaques, which is what GTAO wants
(water is shaded later from `depthtex1`); the half-res buffer is written once per frame, so do
not keep history in it (trap 4), TAA at full resolution does the accumulation; Potato and Low
have no GTAO, so the pass must be disabled with `program.deferred.enabled` under the preset,
not left running; particles have a fixed up normal (trap 6) and must not occlude (exclude by
material). Technique: haloing at depth edges without the depth-aware upsample; over-darkening
without the multi-bounce fit; flicker on foliage without the thickness heuristic; a radius in
world units must be clamped in pixels near the camera or the gather thrashes the cache (the
paper's note).

## 9. Licences

| Source | Terms | Use |
|---|---|---|
| Jimenez, Wu, Pesce, Jarabo 2016 (Activision) | paper | method and the multi-bounce coefficients |
| XeGTAO | MIT (Intel 2021) [V] | may be ported to GLSL with the notice in `LICENSES/README.md` |
| Bavoil, Sainz, Dimitrov 2008 (HBAO); Timonen 2013 | talk; paper | background |
| Photon | learn-only | tiering (SSAO low, GTAO high) |
