# Brief: bloom (short)

The halo on genuinely bright pixels. Read with [`README.md`](README.md).

## 1. What the owner asked for

- r000 bloom (B subtle, 4/5): "a subtle natural halo affected by light intensity makes sense
  and lends itself to photorealistic light." dislikes: "I don't like too much bloom."
- r005 forest-light: sharper rays "without significantly intensifying the light source and
  washing out the sky."
- Look bible 15: "Restrained, energy-conserving bloom on genuinely emissive pixels only";
  anti-pattern "too much bloom"; the sun wants "glare that does not wash out" (r006 notes).

## 2. What we do now

No bloom in the main path. `program/final.glsl` `calBloom` exists only for the round-0
calibration options (`QF_CAL_BLOOM`, `QF_CAL_GRADE`). The only glow is `sunGlare` (r007): a
point-spread function of three exponentials (0.16 e^(-theta/0.0045) + 0.025 e^(-theta/0.018)
+ 0.004 e^(-theta/0.09)) scaled by nine visibility taps on the disk, drawn over everything in
front of the sun. Emissive blocks are brightened in `lib/lighting.glsl` (`MAT_EMISSIVE`,
`MAT_LAVA`) but do not glow beyond their pixels. Rule 11: one mip chain on one R11G11B10F
buffer; Low four mips; Potato none.

## 3. What the top packs do

- **Jimenez 2014, CoD: Advanced Warfare** [V,
  https://www.iryoku.com/next-generation-post-processing-in-call-of-duty-advanced-warfare/]:
  a pyramidal downsample with each sample weighted 1 / (1 + luma) per 2x2 block to kill
  fireflies (the "partial Karis average"), a 3x3 tent filter on each progressive upsample
  (E' = blur(E), D' = blur(D) + E', and so on), bloom mixed at a low value "say 0.04", no
  bright-pass threshold with physically based lighting, exposure applied after bloom.
- **Photon** [V, README and `shaders.properties`]: credits the CoD:AW downsampling method;
  intensity, spread and an upsampling-filter choice. **Kappa**, **Sundial Lite**, **BSL**,
  **Complementary** list bloom as a feature [V]; none describes the method.

## 4. The technique

Jimenez's chain, on exposed linear colour after TAA (stable input) and before the mapper:

```
pass bloom-down (composite stage, half-resolution atlas, R11G11B10F): levels 1/2 .. 1/32 side by side in one buffer
   level 1 from colortex4 (exposed, luma-weight undone): 13-tap downsample with the 1/(1+luma) block weights
   levels 2..5: 13-tap from the previous level (plain weights)
pass bloom-up: from level 5 to level 1, 3x3 tent (radius 1 texel of the coarser level), accumulate
apply (final): color = color * (1 - k) + k * bloom_level1(bilinear), k = 0.035 (High), the "natural halo" that scales with intensity because nothing is thresholded
```

Keep `sunGlare` for the disk: it is the owner's "real sun" glare and models a wider, sharper
PSF than five mips reach; subtract its energy from the bloom input around the disk so the two
do not stack. Emitters (torches, glowstone, lava) and glints get their halo from the chain;
the look bible's "only on genuinely emissive pixels" is met by the 1/(1+luma) weighting and
the low k, not by a threshold (thresholds give the cut-out look he dislikes).

Programs: two composite programs at half resolution (`scale.compositeN = 0.5`) writing one
half-resolution atlas, then `final`. Within rule 11 and rule 6 (High has five composite
slots: volumetrics, water, TAA, bloom-down, bloom-up). Render target: one half-resolution
R11G11B10F buffer (about 4 MB at 1440p; README's budget arithmetic).

## 5. Low and Potato

- **Low**: four levels (1/4 to 1/32) from a quarter-resolution first downsample; k 0.03. Low's
  composite budget is three programs (volumetrics, water, TAA), so merge bloom-down into the
  water pass's tail region of the atlas or fold bloom-up into `final` (five tent taps).
- **Potato**: none (rule 11); keep `sunGlare`, which is nine taps.

## 6. Cost

- **[estimate]** 1440p High: the down chain touches 1.33 half-resolution images (13 taps) and
  the up chain about the same (9 taps): 0.05 to 0.12 ms on the dev PC. Jimenez gives no
  timings on the page.
- Measure: `--scenes torch,night_full,shore_sunset,gallery,texture_wall` with the new option
  off and on; `check_frames.py --max-clipped` guards the wash.

## 7. Test scenes and reference photos

Views: `torch` and `gallery` (bench scenes: torches, glowstone, lava), `night_full` and
`night_new` (emitters against dark), `shore_sunset` and `ocean_sunset` (glints must not bloom
into a sheet), `texture_wall`. Photos: not needed; the reference is the absence of a visible
effect except around lights, judged on the owner's phone.

## 8. Pitfalls

Angelica: box mips flicker and are not rebuilt for `prepare` reads (trap 3), so build the
chain with explicit passes, not `MipmapEnabled`; a bloom buffer read the next frame is
single-writer (trap 4), so never keep history in it. Technique: fireflies from glints without
the Karis weights; a fixed-radius tent on wide levels smears into a wash (the r005 complaint);
bloom before TAA flickers; bloom after the mapper clips; any threshold reads as a cut-out.

## 9. Licences

| Source | Terms | Use |
|---|---|---|
| Jimenez 2014, SIGGRAPH Advances | talk, copyright Jorge Jimenez [V] | method |
| Karis 2013, "Tone mapping" blog (the luma weight) | blog | idea |
| Bjoerge 2015, dual Kawase (ARM, SIGGRAPH mobile course) | talk [U] | alternative, not used |
| Photon, Kappa, Sundial, BSL, Complementary | learn-only | feature survey |
