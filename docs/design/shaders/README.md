# Quest Forge shader pack

A shader pack written from scratch for this modpack, targeting **Angelica's Iris
backport** (Angelica 2.2.33, Iris feature level 1.8.3, `IRIS_VERSION 10803`).
The goal is a near-photoreal look that still reads as Minecraft, holds frame
rate on weaker PCs, and treats the pack's modded blocks, dimensions and custom
renderers as first-class.

The pack moved from OptiFine 1.7.10 HD U E7 to Angelica on 2026-10-17
([`../angelica-decision.md`](../angelica-decision.md),
[`../platform-decision.md`](../platform-decision.md)). This plan was re-targeted
the same day. The E7 plan survives as a [historical note](#historical-the-e7-plan-2026-10-16).

## Platform stance: Iris only

**Our pack runs only on Angelica. It doesn't try to run on E7, even in a
degraded form.** The E7 client stays supported for GPUs without OpenGL 3.3
(Intel HD 2000/3000 and older). On E7 our pack is not offered: those PCs play
with shaders off, or with Sildur's Enhanced Default, as the lite client already
recommends.

Why we don't build a degraded E7 path:

- **The hardware that needs E7 can't run a deferred pack anyway.** A GPU that
  stops at OpenGL 3.1–3.2 is far below the Potato tier in
  [`performance-rules.md`](performance-rules.md). The only people a degraded
  path would serve are people who should play with shaders off.
- **The two pipelines differ in almost every line that matters.** E7 runs GLSL
  on a compatibility context with no `shadowcomp`, no per-buffer scaling, no
  `program.X.enabled`, no entity removal from the shadow pass, and it reads
  `block.properties` from mod resource domains. Iris transforms GLSL for a core
  profile and reads `block.properties` only from the pack. A dual target
  doubles every test and keeps the worst limits of both.
- **The review loop can't afford two baselines.** Every scene would need to be
  judged twice.

How to enforce it: every program includes `/lib/platform.glsl`, which starts with
`#ifndef IS_ANGELICA` / `#error "Quest Forge shaders need the Angelica client"` /
`#endif`. *Verify once* on E7 that the error makes OptiFine fall back to no
shaders, not to a black screen.

## Why our own pack

Re-checked 2026-10-17 on Angelica:

- **Complementary now renders, and renders well**
  (`C:\qfb\client-ang\screenshots\bench-m-B2*.png`, 239–249 fps at 1440p on the
  dev PC, at the 240 Hz vsync cap). But:
  - its licence won't let us ship a modified copy under our own terms (see
    [Licence](#licence-stance));
  - its `block.properties` has no 1.7.10 section, so Angelica converts its modern
    names and the pack's roughly 5,200 modded block textures get no material IDs
    at all;
  - it isn't tuned to the look bible or to a 1060-class floor.
- **No PBR texture pack exists for the 1.7.10 layout.** `gen_surface_pack.py`
  generates normal maps for every block instead. Iris reads `_n` and `_s` atlases,
  so the generated maps finally have a consumer. (Vibrant read only `_n`.)
- **The CPU cost is now much lower.** Measured on Angelica with Vibrant High:
  252–274 fps at 1440p against E7's 71–158. Celeritas builds chunks on worker
  threads and keeps them in VBOs, so the shadow pass costs a fraction of what it
  did on E7. Entities can also be dropped from the shadow pass. Pixel cost now
  matters again, so budgets are GPU budgets first (see
  [`performance-rules.md`](performance-rules.md)).

## Licence stance

Our code is our own and we choose its licence. We learn techniques from any
pack, but copy code only from public-domain, MIT, BSD, Apache or CC0 sources,
keeping their notices. No code from Complementary, BSL, Sildur's, SEUS, Photon,
Bliss or any GPL pack. The per-pack licence table is in
[`research/techniques.md`](research/techniques.md).

### Complementary: what we may learn, and what we may not copy

Complementary is Angelica's primary compatibility target, so it is the pack we'll
study most. Its licence is **Complementary License Agreement 1.7** (`License.txt`
in `ComplementaryUnbound_r5.9.3.zip`). Its terms for us:

- **Using it unmodified is fine.** That covers playing with it and taking
  screenshots of it ("Normal Usage", §1.1). It can serve as a visual reference
  frame in the review loop.
- **Shipping it in our modpack** is allowed only unmodified, credited, and
  downloaded through CurseForge or Modrinth (§1.2). "Block property additions"
  count as modifications (§1.2c), so we can't add our modded block IDs to it.
- **A modified pack** (§1.3) has to keep CLA 1.7 as its *only* licence (§1.3e).
  It also has to drop "Complementary" from its name, look noticeably different,
  and credit the original. That rules out our own licence, so **we never start
  from its code.** "Everything else is All Rights Reserved" (§2.1).

**What we may learn** from reading it (ideas and architecture aren't covered by
copyright; code and text are):

- which program does what;
- how it splits work between deferred and composite;
- which effects it ties to which settings tier, and how its profiles are laid out;
- what Angelica does to it, read in `patched_shaders/` (see Platform facts below);
- how it handles weather, the Nether and the End;
- the *general idea* of an integrated-PBR scheme: block IDs classify materials,
  and normals come from the albedo.

**What we may not copy:**

- any GLSL, including "small" helpers, constants tables and noise functions;
- its `block.properties`, `item.properties` or `entity.properties`, or their ID
  numbering;
- its option names, screen layout or language files;
- its textures.

When we want one of its techniques, we implement it from the primary source
(the paper, or an MIT/BSD reference in `research/techniques.md`), without
Complementary open in another window. Euphoria Patches modifies Complementary,
so the same rules apply to it.

## Documents

| File | What it is |
|---|---|
| [`look-bible.md`](look-bible.md) | What "the look" means. The critic scores against this. |
| [`performance-rules.md`](performance-rules.md) | Hard rules, per-tier frame budgets, and the mandatory Low and Potato presets. |
| [`review-loop.md`](review-loop.md) | How every iteration is rendered on the Angelica client, critiqued, and sent to the owner's phone. |
| [`research/`](research/) | The three source reports from 2026-10-16: performance, desirability, and techniques and licences. They were written for E7; where they disagree with the platform facts below, this file wins. |
| [`../../../tools/shaders/`](../../../tools/shaders/) | `gen_surface_pack.py` (normal maps and `block.properties`); `review/` (Shader Lab page, `check_frames.py`). |

## Getting started

These steps get a dev shader folder iterating today in the existing Angelica
client.

**Before any launch:**

```
py -3.10 -I tools/trial/trial.py status
```

If it lists *any* client, don't launch. A second full-pack client makes the
NVIDIA driver reset the GPU and kills both games. Other sessions run their own
clients on this machine, so check every time, not once a day.

1. **Use `C:\qfb\client-ang`.** It is the Angelica stack the benchmarks used:
   Angelica 2.2.33, Forge 1614, with Hodgepodge 2.7.216 and ArchaicFix 0.8.0.
   The final Angelica client, built by `tools/angelica-client/build_angelica_client.py`
   (`C:\qfb\client-ang2` is one build of it), drops Hodgepodge and ArchaicFix.
   Move to it when it's done, and re-run the frame-time baselines when you do.
   Numbers from the two clients aren't comparable.
2. **Set up `C:\qfb\client-ang` once, with the game closed.**
   - Bind the Iris keys. Angelica ships them unbound. Add these lines to
     `C:\qfb\client-ang\options.txt`, replacing the `:0` lines:
     `key_iris.keybind.toggleShaders:62` (F4), `key_iris.keybind.shaderPackSelection:66`
     (F8), `key_iris.keybind.reload:67` (F9). The final client already has them.
   - Turn off the vsync cap. In `C:\qfb\client-ang\config\angelica-options.json`
     add `"vsync_mode": "OFF"`. Without it, frame times pin to 4.16 ms on the
     240 Hz monitor and every budget reads as "passes".
   - Turn on Iris's debug output. In `C:\qfb\client-ang\config\shaders.properties`
     set `enableDebugOptions=true` (compile errors show in game, with the line)
     and `saveCompiledShaders=true`. Angelica's rewritten GLSL then lands in
     `C:\qfb\client-ang\patched_shaders\`. Read that copy whenever a line number
     doesn't match.
3. **Create the dev pack** as a folder, not a zip, so edits apply on F9:
   ```
   C:\qfb\client-ang\shaderpacks\QuestForge-dev\shaders\
       shaders.properties   block.properties   dimension.properties
       lib\platform.glsl     (the IS_ANGELICA guard, see above)
       gbuffers_*.vsh/.fsh   deferred*.fsh   composite*.fsh   final.fsh   shadow.vsh/.fsh
   ```
   Start from shaderLABS **Base-330**: a minimal, correct program set in GLSL 330
   under the Unlicense, so no notice is required. Record where it came from in
   `LICENSES/README` anyway. Write `#version 330 core` and modern GLSL
   (`texture`, `in`/`out`), so Angelica's compatibility rewrite has little to do.

   To keep the source in git, put it at `shaders/QuestForge/` in the repo and
   junction it in:
   `cmd /c mklink /J C:\qfb\client-ang\shaderpacks\QuestForge-dev <repo>\shaders\QuestForge`.
   Remove the junction with `cmd /c rmdir`, never with a recursive delete,
   because a recursive delete follows the link into the repo.
4. **Generate the block mapping:**
   ```
   py -3.10 -I tools/shaders/gen_surface_pack.py --target questforge --instance C:\qfb\client-ang ^
       --world C:\qfb\world-master --shader-pack C:\qfb\client-ang\shaderpacks\QuestForge-dev ^
       --out C:\qfb\surface\QuestForge-Surface.zip
   ```
   This writes `shaders/block.properties` into the pack: vanilla and modded
   blocks, with the material IDs in the generator's `QF_IDS` table and the
   1.7.10 guard. It also writes a normal-map resource pack. Enable that pack
   above `QuestForge.zip`. Re-run the generator whenever mods change.
5. **Iterate.** Launch with `C:\qfb\run_bench.ps1 -Client C:\qfb\client-ang -ForgeJar
   C:\qfs\forge1614-install\forge-1.7.10-10.13.4.1614-1.7.10-universal.jar -Shader QuestForge-dev ...`
   for measured scenes ([`review-loop.md`](review-loop.md)). For hand iteration,
   launch the same client yourself. Press F8 and pick `QuestForge-dev`. Then
   edit, press F9 and look.

### Milestone 1: the lighting, water and sky baseline

Done when every item below holds in the scene set's plains-noon,
forest-golden-hour, ocean-shore and full-moon-night scenes:

1. **Sky.** Hillaire transmittance and multi-scatter lookup tables, a per-frame
   sky-view lookup table, a sun disk and a moon. The zenith stays blue at golden
   hour (look bible 4 and 8).
2. **Lighting.** Sun and sky light from `shadowtex0` with hardware PCF at a
   2048 map and distance 112 (High), and at 1024 and distance 48 (Low). Block
   light at about 2800 K. An ambient floor scaled by moon phase, so nights are
   dark but readable (look bible 1, 10 and 13).
3. **Exposure and colour.** Slow, bounded auto-exposure from a mip chain, and a
   neutral tone mapper (AgX or Tony McMapface, both permissive). Wood, sand and
   gold don't turn neon (look bible 2 and 3).
4. **Water.** Clear shallows, Beer–Lambert depth tint, Fresnel with a lookup-table
   sky fallback, normal-only waves, and an underwater fog volume (look bible 12).
5. **TAA.** Variance clipping and a disocclusion test. Without TAA nothing else can
   under-sample.
6. **Low preset.** It exists from day one and passes its proxy budget in
   [`performance-rules.md`](performance-rules.md). Shadows-off Potato renders.
7. **Modded blocks.** Modded leaves and plants wave from the generated
   `block.properties`. This proves the ID path end to end.

Clouds, AO, reflections beyond the sky fallback, wetness and per-dimension skies
come in later milestones.

### What's in the way

Status 2026-10-18: milestone 1's first baseline is in `shaders/QuestForge/`; see
[`milestone-1.md`](milestone-1.md) for what works, the numbers, and how to iterate.

- **Slim Angelica trials exist** (`trial.py build --renderer angelica`, 2026-10-18).
  `tools/shaders/review/bench_round.py` renders and measures a round on one in
  about 10 minutes for 11 scenes; the full pack is no longer needed for shader work.
- **FrameBench view scenes hide the GUI** (`-Dqf.bench.views`), so frames carry no HUD.
- **Two Angelica 2.2.33 problems change the rules above.** The hardware shadow
  sampler `shadowtex0HW` gave wrong results, so the pack compares `shadowtex0`
  itself. And a shader-cache miss at startup can crash the first world frame
  (the pipeline is built twice); relaunch once. Details in `milestone-1.md`.
- **The Low and Potato budgets are proxies.** No GTX 1060 or integrated-GPU PC
  has run the pack. A friend's PC has to confirm them before release (see
  [`performance-rules.md`](performance-rules.md)).

## Platform facts (verified in the Angelica jar, 2026-10-17)

Source: the Iris code in Angelica 2.2.33. I read the release's `-sources.jar`
and spot-checked six of the strings below in the binary jar at
`C:\qfb\client-ang\mods\angelica-2.2.33.jar`; all six are present. Paths are
under `net/coderbot/iris/`. **[V]** means read in the source. **[I]** means
inferred, not tested in game.

**Context.** Angelica runs a core profile at the highest version the driver
offers: "Created GL 4.6 core profile context" on the dev PC's RTX 5070 Ti. The
minimum is 3.3. Pack GLSL is rewritten for core (`pipeline/transform/`). [V]

**Programs** (`shaderpack/loading/ProgramId`, `ProgramArrayId`). [V]
- `setup`, `begin` and `prepare` (99 each, before the world);
- `shadow`, plus `shadow_solid`, `shadow_cutout` and `shadow_water`;
- `shadowcomp` (99 slots);
- the `gbuffers_*` set, with Iris's fallback chain: `basic`, `line`, `textured`,
  `textured_lit`, `skybasic`, `skytextured`, `clouds`, `terrain`,
  `terrain_solid`, `terrain_cutout`, `damagedblock`, `block`,
  `block_translucent`, `beaconbeam`, `item`, `entities`, `entities_translucent`,
  `entities_glowing`, `lightning`, `particles`, `particles_translucent`,
  `armor_glint`, `spidereyes`, `hand`, `weather`, `water` and `hand_water`;
- `deferred` and `composite` (99 slots each);
- `final`.

Every program can also have a compute stage (`.csh`). Geometry shaders (`.gsh`)
load. Tessellation (`.tcs`/`.tes`) is parsed but the feature flag is hard-off,
so it is effectively absent (`features/FeatureFlags`). [V]

**Buffers.** `colortex0`–`colortex31` (`IrisLimits.MAX_COLOR_BUFFERS = 32`),
`shadowcolor0`–`shadowcolor7`, and `shadowtex0`/`shadowtex1`. Hardware-filtered
shadow samplers have separate names (`shadowtex0HW`). [V]

**`shaders.properties` keys parsed** (`shaderpack/ShaderProperties`). [V]
- Programs and passes: `program.<name>.enabled` (conditional programs), `size.buffer.<buf>`
  (per-buffer resolution), `scale.<pass>`, `blend.<program>[.<buffer>]` (per-buffer
  blending), `alphaTest.<program>` and `flip.<pass>.<buf>`.
- Storage: `image.<name>` (custom images, which need image load/store),
  `bufferObject.<n>` (SSBOs), `customTexture.<name>`, `texture.<stage>.<sampler>`
  (PNG or raw) and `texture.noise`.
- Custom uniforms: `uniform.<type>.<name>` and `variable.<type>.<name>`. The
  expression language is `kroppeb/stareval`.
- Features: `iris.features.required` and `iris.features.optional`.
- Shadow pass: `shadow.enabled`, `shadowTerrain`, `shadowTranslucent`,
  `shadowEntities`, `shadowPlayer`, `shadowBlockEntities`,
  `shadowLightBlockEntities` and `shadow.culling`.
- Pass order: `separateAo`, `particles.before.deferred` and `prepareBeforeShadow`.
- Vanilla parts: `sun`, `moon`, `stars`, `sky`, `vignette`, `clouds`, `weather`,
  `underwaterOverlay`, `backFace.*`, `rain.depth` and `beacon.beam.depth`.
- Other: `voxelizeLightBlocks`, `allowConcurrentCompute`, `separateEntityDraws`.
- Settings UI: `profile.*`, `screen.*` and `sliders`.

`shaders.properties` itself goes through the preprocessor, so these keys can
switch with options (`#ifdef SHADOWS`).

Shader consts (`PackShadowDirectives`, `PackDirectives`): `shadowMapResolution`,
`shadowDistance`, `shadowDistanceRenderMul`, **`entityShadowDistanceMul`**,
`shadowIntervalSize`, `voxelDistance`, `sunPathRotation`,
`ambientOcclusionLevel`, the `*Halflife` set, `colortexNFormat`/`Clear`/`ClearColor`/`MipmapEnabled`,
and the `shadowtex`/`shadowcolor` mipmap and nearest flags. [V]

**Feature flags** (`IRIS_FEATURE_<NAME>` is defined when available):
`SEPARATE_HARDWARE_SAMPLERS`, `PER_BUFFER_BLENDING`, `ENTITY_TRANSLUCENT`,
`BLOCK_EMISSION_ATTRIBUTE`, `HIGHER_SHADOWCOLOR`, `REVERSED_CULLING` and
`CAN_DISABLE_WEATHER` are always available. Three depend on the driver:
`COMPUTE_SHADERS` (GL 4.3), `CUSTOM_IMAGES` (image load/store, GL 4.2) and
`SSBO` (GL 4.3). A GTX 1060 and Intel Gen9+ graphics on Windows report GL 4.6
[I]. A GL 3.3-only GPU gets none of the three, which is why Low and Potato never
use them. [V]

**Macros** (`gl/shader/StandardMacros`). [V]
- Platform: `IS_ANGELICA`, `ANGELICA_VERSION`, `IS_IRIS` and `IRIS_VERSION 10803`
  (both on by default via `defineIsIris`), `MC_VERSION 10710`, `MC_GL_VERSION`,
  `MC_GLSL_VERSION`, `MC_OS_WINDOWS` and the GPU vendor.
- One macro per GL extension.
- `BIOME_<NAME>` for every registered biome, modded included.
- `MC_HAND_DEPTH`.

**Uniforms worth knowing** (`uniforms/`). [V]
- Temporal reprojection: `frameCounter`, `frameTime`, the previous-frame
  matrices, and `cameraPositionInt`/`Fract` with `previousCameraPosition*`.
- Biome and world: `biome` (the current biome's ID, modded biomes included),
  `biome_category`, `temperature`, `rainfall`, `hasCeiling`, `hasSkylight`,
  `cloudHeight` and `seaLevel`.
- Player: `isEyeInWater`, `eyeBrightnessSmooth`, `heldBlockLightValue`/`Color`,
  `currentSelectedBlockId`, `lightningBoltPosition`, `playerMood` and
  `nightVision`.
- **There is no dimension-ID uniform.** Per-dimension looks come from
  `dimension.properties` folders, or from `biome`, `hasCeiling` and `hasSkylight`.

**Dimensions** (`shaderpack/ShaderPack`). [V] `dimension.properties` maps a folder
to names from `WorldProvider.getDimensionName()` (for example `dimension.world7=
"Twilight Forest"`), with `*` as the wildcard. Without a mapping it tries
`world<dimensionId>`, then the base folder.
- **A dimension folder replaces the base program set completely**; nothing merges.
- Each folder compiles on first entry.
- At most 12 program sets stay cached (`-Diris.dimensionCacheSize`); Overworld,
  Nether and End stay pinned.

**`block.properties`** (`shaderpack/IdMap`, `block_rendering/BlockMaterialMapping`). [V]
- **Read only from the pack's `shaders/` folder.** E7 also loaded
  `assets/<modid>/shaders/block.properties` from resource packs
  (`BlockAliases.loadModBlockAliases`); Iris does not. The old surface pack's
  per-mod files do nothing here.
- **Entry format.** Entries are `modid:name[:meta[,meta]]` with optional
  `[nbt]` conditions for tile entities. They resolve against
  `Block.blockRegistry` by exact registry name, with case kept (for example
  `TwilightForest:tile.TFLeaves`).
- **Duplicates.** If a block appears under two IDs, the first one inserted wins
  (`putIfAbsent`). The generator emits each block once.
- **The 1.7.10 section.** The file counts as having a 1.7.10 section only if a
  line matches `#if … MC_VERSION … 10710`. Otherwise vanilla entries are read as
  modern (1.13+) names and run through a flattening map, and the whole pack is
  compiled with a modern `MC_VERSION` (trap 9). Modded names resolve directly
  either way.
- `item.properties` and `entity.properties` are read too, for `heldItemId` and
  `entityId`. `layer.*` render-type overrides are parsed, but the code marks
  "properly override block render layers" as a TODO.

**Normal and specular maps.** Iris builds `_n` and `_s` atlases
(`texture/pbr`), with an optional LabPBR format declaration. [V]

**Shadow pass** (`pipeline/ShadowRenderer`, `DeferredWorldRenderingPipeline`). [V]
- Terrain comes from Celeritas's VBOs. Entities, the player and tile entities
  can each be switched off (`shadowEntities=false` and so on), or limited in
  range with `entityShadowDistanceMul`. Angelica also culls tile entities from
  the shadow pass by default.
- The pass runs if `shadow.enabled` is true. If that is unset, it runs when a
  program actually binds a `shadowtex`/`shadowcolor` sampler or image. Iris
  checks the compiled program, so a declaration that the preprocessor removed
  shouldn't count [I]. F3 shows the shadow entity count, or "disabled by pack".
- `config/shaders.properties maxShadowRenderDistance=32` caps shadow distance at
  32 chunks.

**No CPU readbacks in Iris.** The Iris sources contain no `glReadPixels` or
`glGetTexImage` call. `centerDepthSmooth` is a GPU pass (`postprocess/CenterDepthSampler`).
[V]

**Debugging.** `config/shaders.properties`: `enableDebugOptions=true` turns on the
in-game error reports, and `saveCompiledShaders=true` writes the transformed
GLSL to `<gameDir>/patched_shaders/`. On a core profile, RenderDoc can capture
frames [I: untested here; it couldn't attach to E7's compatibility context].

**Keys.** Reload, toggle and pack-select ship unbound (`Iris.java`: key code 0).
The final client binds them to F9, F4 and F8.

### Traps

1. **`block.properties` must live in the pack and must carry the 1.7.10 guard.**
   Wrap the whole file in `#if MC_VERSION == 10710` … `#endif`. Without the
   guard, `minecraft:grass` is read as a modern name and lands on the wrong
   block, silently.
2. **Dimension folders are whole copies.** Keep the folder count small: base,
   `world-1`, `world1`, plus at most three grouped modded folders. Each folder's
   programs should be two-line stubs (`#define DIM_TWILIGHT`, then
   `#include "/program/composite1.glsl"`), so that 30 dimensions don't become 30
   forks. Measure the first-entry compile hitch. It is a stutter, and stutter
   is a bug.
3. **A G-buffer still can't blend**, and custom mod renderers still hit the
   failure modes in the deferred-shader memory: untextured quads, opaque
   overlays, additive passes that replace, and mid-frame depth clears. Iris
   adds per-buffer blending (`blend.gbuffers_entities.colortex1=off` and so on),
   so albedo can blend while normals and material IDs stay unblended. Use it
   instead of working around the problem in mod code.
4. **Mod GL now runs through Angelica's fixed-function emulation.** A mod's
   matrix or VBO code (MCHeli's rotors, Transformers) can misplace geometry with
   shaders off as well. Rule out the shaders-off case before blaming the pack.
5. **Vsync caps every measurement** at 240 Hz unless `vsync_mode` is `OFF` in
   `angelica-options.json`.
6. **Angelica releases almost daily.** Pin 2.2.33. When it moves, re-run this
   section's checks and the scene set before trusting old numbers.
7. **Iris rewrites terrain programs for Celeritas.** Vertex attribute names and
   line numbers in errors refer to the patched source, so read `patched_shaders/`.
8. **`shaderParityFlip`** (Angelica config, on by default) ping-pongs buffers to
   skip a copy at the end of the frame. If a history buffer reads stale data,
   switch it off once to rule it out.
9. **The guard also sets `MC_VERSION` for the whole pack.** If `block.properties`
   is missing or has no `#if … MC_VERSION … 10710` line, Angelica defines
   `MC_VERSION` as `modernFallbackMcVersion` (default `260101`). It does that for
   every program, item and entity file, not only for `block.properties`
   (`ShaderPack.java`, `mcVersionOverride`). With the guard, the pack sees
   `10710`. Never branch the pack's GLSL on `MC_VERSION`; branch on `IS_ANGELICA`.

## Historical: the E7 plan (2026-10-16)

The first version of this plan targeted OptiFine 1.7.10 HD U E7 (ShadersMod
2.4.12). Its verified facts, kept for the fallback client:

- **Present:** gbuffers programs, `shadow`, `deferred`–`deferred7`,
  `composite`–`composite7` and `final`; colortex0–7; hardware shadow filtering;
  previous-frame matrices; `block.properties` (including per-mod resource-domain
  files); custom uniforms and textures; `shadowTranslucent` and
  `shadowDistanceRenderMul`.
- **Absent:** `shadowcomp`, `prepare`, compute, geometry shaders,
  `program.X.enabled`, per-buffer scaling, `separateAo`, and entity removal from
  the shadow pass.
- **Traps:**
  - Any declared shadow sampler, even inside `#ifdef`, enables the whole shadow
    pass.
  - `centerDepthSmooth` forces a `glReadPixels` every frame.
  - Mentioning `colortex7` allocates all eight buffers.
  - The block-mapping reload and the mod-domain lookup both needed the
    qf-tweaks patch.
- **Measurements:** Complementary didn't render. Vibrant High ran 140–170 fps at
  1440p with the GPU about 44% busy (CPU-bound); the shadow pass dominated.

**What the move to Iris gained:** `shadowcomp`, `setup`, `begin` and `prepare`;
compute and custom images (GL 4.3 hardware); geometry shaders; 32 colour and 8
shadow-colour buffers; conditional programs; real per-buffer resolution; per-buffer
blending; `separateAo`; entities, the player and tile entities out of the shadow
pass; per-dimension folders mapped by name; NBT-conditional block IDs; specular
atlases; GPU-side `centerDepthSmooth`; a core profile with RenderDoc.

**What it lost:** the E7 client (GL < 3.3 PCs) can't run our pack, and
`block.properties` can no longer come from a resource pack.

**What stayed the same:** the G-buffer blending rules, and the absence of
tessellation.

On E7 the pack stays as it is today: Sildur's Vibrant or Enhanced Default with
the qf-tweaks `GlErrorTransformer` and block-mapping fixes. We don't develop
shaders for it.
