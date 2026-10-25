# Technique briefs for the shader agent

Written 2026-10-25, after Shader Lab round 6. Each brief takes one effect the owner keeps
rating, says what he asked for (his words, by round), what the pack does today (file and
function names), what the well-known packs do (from their public pages, each claim tagged),
and then the technique we should implement, from its primary source, with starting values,
the Iris program it belongs in, Low and Potato versions, a cost estimate, test scenes, and
the Angelica traps that bite it.

| Brief | Effect | Where it lives today |
|---|---|---|
| [`water.md`](water.md) | waves, optics, reflection, glitter, biome colour, borders | `lib/water.glsl`, `program/composite.glsl` `shadeWaterAbove` |
| [`clouds.md`](clouds.md) | the raymarched deck, its light, resolution and history | `lib/sky.glsl` `cloudMarch`, `cloudLum` |
| [`sky.md`](sky.md) | atmosphere tables, sun, moon, stars, fog and aerial perspective | `lib/atmosphere.glsl`, `program/prepare.glsl`, `lib/sky.glsl`, `lib/sun.glsl` |
| [`light-shafts.md`](light-shafts.md) | sunlit air through gaps | `program/composite.glsl` `lightShafts` |
| [`tone-mapping.md`](tone-mapping.md) | exposure, the display transform, vibrance | `lib/tonemap.glsl`, `program/final.glsl`, `lib/lut.glsl` |
| [`bloom.md`](bloom.md) (short) | the halo on emitters and glints | none yet; `final.glsl` `sunGlare` is the only glow |
| [`ambient-occlusion.md`](ambient-occlusion.md) (short) | grounding at block corners | vanilla vertex AO only, `lib/lighting.glsl` |

## How to use a brief

1. Read section 1 (what the owner asked for) and section 2 (what we do now) before touching
   code. Section 2 names the functions to change; the constants quoted there are the
   starting point, not a target.
2. Section 4 is the technique. Its pseudo-code is prose and maths in our own words: write
   the GLSL yourself. Where a brief gives a starting value, treat it as the first guess for
   a Shader Lab A/B, never as settled.
3. Section 5 is not optional. A feature without a Low and a Potato answer does not ship
   ([`../../performance-rules.md`](../../performance-rules.md)).
4. Section 6 says how to measure. Costs are marked **[measured]** (a number from a bench run,
   a paper's table, or a vendor page) or **[estimate]** (reasoning from pixel counts). Replace
   an estimate with a measurement in the brief when you have one.
5. Section 7 names the Shader Lab views (`tools/shaders/review/views-world-master.txt`) and
   the Wikimedia Commons categories for reference photos. Pick the photo per round; check its
   licence on the file page (Commons licences vary per file; CC BY and CC BY-SA need the
   credit line the round-6 publisher already writes).
6. Section 8 lists the Angelica traps that apply. They are a subset of the shared list
   below; a brief only repeats the ones that matter for its effect.

## The licence rule, restated

We learn techniques from any pack and copy code only from public-domain, MIT, BSD, Apache or
CC0 sources, with their notices kept in `shaders/QuestForge/LICENSES/README.md`. No GLSL,
constants tables, noise functions, option names, screen layouts or property files from
Complementary, Euphoria Patches, BSL, Sildur's, SEUS, Photon, Bliss, Kappa, Nostalgia,
Rethinking Voxels, Solas, Noble, Sundial or any GPL pack. Ideas and architecture are fine.
Where a brief says "Photon does X", that is an observation from its public README or its
published `shaders.properties`, read for *what* it does, never for *how* its code does it.
When a technique is wanted, implement it from the paper or from the MIT/BSD/Apache reference
the brief names, without any pack open in another window. Photon's licence lets us read and
learn but not redistribute on CurseForge or Modrinth, so it is learn-only too
([`../techniques.md`](../techniques.md), licence table).

## Tags

- **[V]** I read the cited page or PDF myself on 2026-10-25.
- **[U]** Unverified: from a secondary source, a search snippet or memory. Check before
  relying on a number.
- **[I]** Inferred about Angelica, not yet tested in game.

## Shared measurement recipe

Every brief measures the same way, so the numbers compare across rounds:

```
py -3.10 -I tools/shaders/review/bench_round.py --tag <tag>-on  --preset 3 --size 2560x1440 --scenes <views>
py -3.10 -I tools/shaders/review/bench_round.py --tag <tag>-off --preset 3 --size 2560x1440 --scenes <views> --opt QF_<EFFECT>=0
py -3.10 -I tools/shaders/review/bench_round.py --tag off-1440  --preset off --size 2560x1440 --scenes <views>
py -3.10 -I tools/shaders/review/check_frames.py --client C:\qfb\shaderdev\rounds --tag <tag>-on --off off-1440 --tier ultra --no-hud
```

The effect's cost is the p50 difference between the `-on` and `-off` runs per scene. The
whole pack's cost is `-on` minus the shaders-off run; it must stay inside the tier's budget
(High 3 ms at 1440p on the dev PC; Low 0.9 ms at 1080p with `--preset 1 --size 1920x1080`;
Potato 0.4 ms at 720p with `--preset 0 --size 1280x720`). Rounds run in the background and
wait for the one client slot; never launch a client by hand for a measurement. The 1% low and
the count of frames over 33 ms must not regress against the last accepted round (`--prev`):
every ray march in these briefs has a fixed step count for that reason.

Round 6's measured baseline, for scale **[measured]**: the dearest High frame cost 2.3 ms at
1440p (budget 3), Low at most 0.68 ms at 1080p (budget 0.9), Potato at most 0.28 ms at 720p
(budget 0.4), with everything in `shaders/QuestForge` on (`site/shaders/rounds/r006.json`,
intro). Milestone 1's bare baseline was 0.95 / 0.47 / 0.34 ms
([`../../milestone-1.md`](../../milestone-1.md)). So about 0.7 ms of High headroom exists
today, and Potato has almost none.

## Render targets: the budget these briefs share

`lib/common.glsl` lists the buffers: `colortex0` albedo RGBA8, `colortex1` normal and
material RGB10_A2, `colortex2` light and AO RGBA8, `colortex3` HDR R11G11B10F, `colortex4`
TAA history RGBA16F, `colortex5` the 256x320 sky tables. Rule 10 says six colour buffers or
fewer (five on Low, four on Potato), because every full-screen target is bandwidth. Three
briefs (clouds, light shafts, ambient occlusion) want a sub-resolution buffer each, and bloom
wants a half-resolution pyramid. Counted as buffers that is nine; counted as bandwidth it is
small. At 2560x1440 a full-screen RGBA16F target is 29.5 MB; a quarter-resolution RGBA16F is
1.8 MB, a half-resolution R8 is 0.9 MB, a half-resolution R11G11B10F atlas about 4 MB, and
`colortex5` is 0.65 MB. **Proposal for the shader agent, to be put to the owner of
`performance-rules.md`:** keep the rule but count it in full-screen equivalents, six at most,
where a buffer counts as its byte size divided by a full-screen RGBA16F target. Today's six
buffers are 4.1 equivalents; the four additions in these briefs add about 0.3. If the rule
stays as a count, pack the quarter-resolution volumetrics (clouds for sky pixels, shafts for
land pixels) into one `colortex6`; the briefs say how.

## Shared Angelica traps (2026-10-25 list)

From the memory notes and `milestone-1.md`; each brief repeats the ones that apply.

1. `shadowtex0HW` (the hardware-compare sampler) gives wrong results. Compare `shadowtex0`
   manually (`lib/shadows.glsl` `shadowPcf`).
2. A shader-cache miss at startup builds the pipeline twice; the rebuilt one can crash at
   the first world frame. Relaunch once before blaming a change.
3. `colortex` mips are not rebuilt for reads in `prepare`. Sample level 0 there.
4. A buffer written by only one pass per frame reads back stale under Angelica's ping-pong.
   Write it twice (`prepare1` exists for this) or make the flip count even.
5. A trial config without Angelica's first-boot files crashes; `bench_round.py` handles it.
6. Particle quads (`gbuffers_textured`, `_lit`) have no usable vertex normal; give them a
   fixed up normal (done in `gbuffers.glsl`).
7. Biome uniforms exist (`biome`, `biome_category`, `biome_precipitation`, `temperature`,
   `rainfall`) with `CAT_*`, `PPT_*` and `BIOME_*` macros, and custom uniforms with `smooth()`
   work; `shaders.properties` already uses both for fog and water.
8. A view with `y auto` over water puts the camera under the surface. Water views give `y`.
9. Angelica's own MCPatcher connected textures replace glass.
10. Iris's PBR loader reads `_n` and `_s` atlases but the pack samples only `gtexture`
    unless `QF_PBR` is 1; the integration steps are in
    [`../../../textures/direction.md`](../../../textures/direction.md) section 2.
11. Raw `TEXTURE_3D` custom textures are parsed by Iris's `customTexture` loader **[I]**;
    nobody has loaded one under Angelica yet. The cloud and tone-mapping briefs depend on it,
    so test it first with a 4x4x4 gradient.

## Sources read for these briefs

Primary: Hillaire 2020 (sky), Hillaire 2016 (Frostbite sky and clouds), Schneider 2015 (HZD
clouds), Tessendorf (ocean), Bruneton 2010 (ocean lighting), Mitchell 2007 (light shafts),
Engelhardt 2010 (epipolar sampling), Karis 2014 and Playdead 2016 (TAA), Jimenez 2014
(bloom), Jimenez 2016 and XeGTAO (AO), Khronos PBR Neutral, AgX via Filament and three.js,
Tony McMapface, Narkowicz, Hable. Packs: Photon's README, wiki page and published
`shaders.properties`; Complementary's site, repo and Modrinth page; Euphoria Patches' site;
BSL's Modrinth page; Sildur's site; SEUS's site; Bliss, Rethinking Voxels, Solas, Noble,
Spectrum, MakeUp Ultra Fast and Sundial Lite READMEs; RRe36's Kappa wiki and blog. Each
brief cites the URL next to the claim.

What could not be read: Complementary has no public technical documentation (its site,
repo README and Modrinth page describe styles and options, not methods), BSL's site renders
its text client-side, SEUS's Patreon posts return 403, Sobotka's own AgX pages were
unreachable (certificate error) so AgX's constants come from Filament and three.js, and
Photon has no technique write-ups beyond its README (its `shaders.properties` is the richest
public description). Claims about those packs are tagged accordingly.
