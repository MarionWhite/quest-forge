# Texture direction (started 2026-10-24, for Shader Lab round 7)

The owner's round-6 verdict on the texture scenes: neither Faithful nor vanilla is the answer
yet, "we have a massive gap to hurdle with texture quality and direction". What he wants:

- **Minecraft's own block designs**, not a restyle: "we don't need to stray too far for most of them".
- **Added detail**, the way Faithful 32x adds it to stone, gold, iron, glowstone, glass and diamond.
  He likes those for their resolution and detail, not their style.
- **No noisy grass.** Faithful's grass is a "noisy green carpet". In the forest-light scene vanilla
  looked better: warmer, with better rays.
- **Connected textures where they apply**, glass above all.
- **Light that behaves**: normal and specular (PBR) maps that our deferred shader can use.
- **A little more vibrance.**

The licence rule from the look bible still holds. The base is **Faithful**, whose licence allows
derivatives. Other packs are **reference only**: we never copy them, never ship them, and never
show their images on our site.

## 1. Connected textures on our stack

**Our stack:** Angelica 2.2.x on Forge 10.13.4.1614, 1.7.10.

**Conclusion: we already have OptiFine-format CTM. We need no extra mod.**

- **Angelica bundles MCPatcherForge.** It is GTNH's port of MCPatcher, and its connected-textures
  module is on by default.
  - The README lists "MCPatcher - connected textures …" with status "Alpha":
    https://github.com/GTNewHorizons/Angelica
  - Checked locally in `C:\qfb\client-ang2`:
    - `angelica-2.2.33.jar` contains `jss/notfine/config/MCPatcherForgeConfig$ConnectedTextures`.
    - It ships default CTM for glass, the 16 stained glasses, bookshelf and sandstone
      (`assets/minecraft/mcpatcher/ctm/...`). Those defaults are by DarkBum, CC-BY-SA.
    - `config/mcpatcherforge.cfg` has `connected_textures { enabled=true, standard=true,
      nonStandard=true, glassPane=false, betterGrass=false }`.
- **What the loader supports.** It reads both `mcpatcher/ctm/` and `optifine/ctm/` `.properties`
  files (CTMUtils.java).
  - Methods: `ctm`/`glass`, `random`, `fixed`, `horizontal`, `vertical`, `h+v`, `v+h`, `top`,
    `repeat`, `compact`, `compact_expanded` (TileOverride.java).
  - **It has no OptiFine `overlay` method.** CTM that relies on overlays (grass edges, ore
    overlays on modern packs) will not work.
- **Vanilla glass connects out of the box**, from Angelica's own defaults. A resource pack can
  replace those rules.
  - Faithful 32x's 1.7.10 zip carries its own 32x connected glass:
    `assets/minecraft/mcpatcher/ctm/glass/`, 833 files, with numeric `matchBlocks=95` and `metadata=`.
  - QF v0 uses Faithful's set.
  - **Glass panes need `glassPane=true`** in `config/mcpatcherforge.cfg`. It is off by default.
    That is a one-line pack config change, still to be decided.
- **Rules must be written for 1.7.10.** That means block IDs or 1.7.10 names, plus metadata, under
  `textures/blocks/`. Packs written for 1.13+ (flattened names, `textures/block/`) need their rules
  rewritten. Packs from 1.8 to 1.12 map closely.
- **Alternatives, for the record:**
  - **Standalone MCPatcherForge** is archived and says to use Angelica:
    https://github.com/mist475/MCPatcherForge
  - **ConnectedTexturesMod** (Chisel-Team/tterrag) only exists for 1.10 and later:
    https://github.com/Chisel-Team/ConnectedTexturesMod
  - **Chisel** (the GTNH fork) has its own CTM for its own blocks, including chiselled
    connected-glass variants: https://github.com/GTNewHorizons/Chisel
    - Angelica compiles against Chisel and GTNH ships both together, so it should render.
    - Not tested here.
    - Chisel only covers blocks you chisel, not placed vanilla glass.
- **Risk:** the module is alpha.
  - I could not verify whether CTM tiles pick up their own `_n`/`_s` PBR maps.
  - QF v0 generates maps for the tiles anyway.
  - **Verified in the r007 renders** (2026-10-24, `glass_close`, High 1440p): the 4×4 glass panel
    and the stained glass draw as one pane in all three packs. With vanilla textures, Angelica's
    default glass covers the panel in white streaks; Faithful's connected glass is a thin frame,
    nearly clear.

## 2. PBR: what Angelica reads and what our shader would need

**Angelica carries Iris's PBR loader:**
- `net/coderbot/iris/texture/pbr/` (PBRAtlasTexture, AtlasPBRLoader) is in the 2.2.33 jar. It has
  44 classes and resources there.
- `PBRType` defines `_n` (default `0x7F7FFFFF`, a flat normal) and `_s` (default 0).
- The deferred pipeline binds the `normals` and `specular` samplers, and `at_tangent` is a vertex
  attribute.
- LabPBR packs were confirmed working in GTNewHorizons/Angelica#777 and #1039.

So any resource pack's `<texture>_n.png` / `_s.png` reach a shader that asks for them.

**The two formats:**

- **LabPBR 1.3**, the de-facto standard: https://shaderlabs.org/wiki/LabPBR_Material_Standard
  - `_n` normal map:
    - R, G: normal X and Y, DirectX convention.
    - B: ambient occlusion.
    - A: height (255 = flat, at least 1).
  - `_s` specular map:
    - R: perceptual smoothness; roughness = (1 − R)².
    - G 0–229: linear F0.
    - G 230–237: hard-coded metals (230 iron, 231 gold, then aluminium, chrome, copper, lead,
      platinum, silver).
    - G 255: albedo is used as F0.
    - B 0–64: porosity. B 65–255: subsurface scattering.
    - A 0–254: emission. A 255: none.
- **"Old PBR" / SEUS**, as read by Complementary:
  - `_n` is an RGB normal.
  - `_s` R is smoothness, G metalness, B emission.

**What we standardise on: LabPBR.**
- Most current PBR packs use it, so the owner can drop one in for comparison.
- Our generated maps (QF v0) use it.
- `tools/shaders/gen_surface_pack.py` still writes the older layout (RGB normal, A height) for
  every modded texture. It should switch to LabPBR, sharing `build_qf_textures.py`'s conversion,
  before modded maps matter.

**What the QuestForge shader does today:**
- It samples **only `gtexture`**. Normals are the vertex normals.
- Roughness and F0 come from the per-block material IDs (`lib/materials.glsl`, from
  `block.properties`).
- The generated `_n` maps are loaded by Angelica but **not read**.

Using them would take, in the shader agent's files, not mine:

1. **gbuffers.glsl (terrain, hand, entities, water for glass):**
   - Declare `in vec4 at_tangent`.
   - Build the tangent basis (TBN) in the vertex shader, with bitangent =
     `cross(normal, tangent) * at_tangent.w`.
   - In the fragment shader, sample `normals` and `specular`.
   - Decode the normal: xy·2−1, z = √(1−xy²); Iris's tangents match LabPBR's DirectX Y.
   - Write the mapped normal into colortex1.rg in place of the vertex normal.
   - Keep the vertex normal for the shadow bias. It is already used in the vertex shader.
2. **G-buffer room:**
   - colortex2.a is unused, so it can hold smoothness.
   - colortex0.a is written as 1.0, so it can hold the F0/metal byte.
   - Emission and subsurface can stay on the material IDs at first.
   - That fits the five-target budget (rule 10) without a new target. Potato could skip PBR
     entirely.
3. **deferred.glsl / lighting.glsl:**
   - Use the sampled smoothness and F0 where a map exists.
   - Fall back to the material table where `specular` reads as 0, the Iris default for "no map".
   - Treat 230–237 as metals with tinted F0.
   - Add a pack option `QF_PBR` (0 off, 1 normals, 2 normals + specular) so each step can be
     judged on its own in the Lab.
4. **Look-bible guardrails:**
   - No heavy parallax: "rounded-off voxel edges" is an anti-pattern, so ignore height at first.
   - Fade normal strength with distance or mip level, so 32x detail does not shimmer. TAA helps.
5. **Expected cost:** two extra texture fetches plus a TBN per terrain fragment, roughly
   0.1–0.2 ms at 1440p on High. This is an estimate, not measured.

## 3. Packs to look at (reference only)

Checked on 2026-10-24 on each pack's official page. Modrinth licence fields were read from its
API. ARR = All Rights Reserved; a pack with no licence stated is ARR by default. **Only
Faithful-licensed packs, and with conditions the CC-BY-NC-SA ones, could ever feed what we ship.**
The rest are for direction only.

| Pack | Official page | Res | CTM | PBR | 1.7.10? | Licence (derivatives / redistribution) | Why look |
|---|---|---|---|---|---|---|---|
| Faithful 32x | https://faithfulpack.net · https://modrinth.com/resourcepack/faithful-32x | 32x | Yes; the 1.7.10 zip has 864 MCPatcher CTM files | No | **Yes** (GitHub `1.7.10` branch, R17) | Faithful License v4: use, modify, distribute with credit + link; no paywall (https://faithfulpack.net/license) | Our licensed base: vanilla shapes with more detail, native 1.7.10 CTM |
| Faithful 64x | https://modrinth.com/resourcepack/faithful-64x | 64x | Yes (1.7.10 branch) | No | **Yes** (GitHub 1.7.10 branch) | Faithful License (same terms) | More detail, same licence; watch friends' VRAM |
| Stay True | https://www.curseforge.com/minecraft/texture-packs/stay-true | 16x | Yes | No | No (1.14+, last update 2025-05) | ARR; the author's FAQ allows use in modpacks with credit, not edits | Closest art direction to "vanilla, a bit nicer", with CTM |
| Patrix 32x | https://modrinth.com/resourcepack/patrix-32x | 32x free (64–256x paid) | Yes, extensive | Yes, LabPBR | No (1.20+) | ARR | Benchmark for vanilla-matched detail + CTM + PBR together |
| Vanilla Normals Renewed | https://github.com/Poudingue/Vanilla-Normals-Renewed | 16x | No | Yes, LabPBR (normals, AO, height, emission) | 1.12 archive (near-1.7 names) | README: do what you like, redistribution OK if not sold and linked | What good PBR on vanilla art looks like; licence even permits reuse |
| Dandelion X | https://modrinth.com/resourcepack/dandelion-x | 16x/32x | Yes | Not stated | No (1.21.4+) | ARR | A cohesive, slightly more vibrant vanilla palette |
| Unity | https://modrinth.com/resourcepack/unity | 16x | Add-on | Shader-map add-on | No (1.19 only, last update 2023-06) | CC-BY-NC-SA-4.0 | Natural tones, CTM + PBR add-ons; share-alike licence would bind our pack |
| Soartex Invictus (Shader Mapped) | https://www.curseforge.com/minecraft/texture-packs/soartex-invictus-shader-mapped | 64x | Yes | Yes (old format) | **Yes** (1.7.10, 2014) | ARR, "no public redistribution" | The only 1.7.10 pack found with CTM + normals + specular together; crisper, less vanilla |
| Conquest_ | https://modrinth.com/resourcepack/conquest_ | 32x | Yes | No | **Yes** | ARR (modpack listing allowed by its FAQ, no redistribution otherwise) | How far 1.7.10 CTM can go; medieval, so off-style |
| Soartex Grove | https://modrinth.com/resourcepack/soartex-grove | 64x | not verified | not verified | No (modern) | CC-BY-NC-SA-4.0 | Remixable high-detail art, if we ever want a 64x direction |
| Jicklus | https://modrinth.com/resourcepack/jicklus | 16x | not stated | No | No (1.16+) | ARR ("personal use only") | Warm, rustic recolour: a vibrance reference |
| **Faithless** (owner's pick, 2026-10-25) | https://modrinth.com/resourcepack/faithless · https://www.curseforge.com/minecraft/texture-packs/faithless | 16x | not stated | not stated | No (1.20–1.21) | ARR on Modrinth; no derivative permission stated | **Owner likes a lot of its elements.** Inspiration for direction only: we study what it does and draw our own; nothing is copied, traced or recoloured from it |
| Bare Bones | https://modrinth.com/resourcepack/bare-bones | 16x | No | No | Listed from 1.6.1 | ARR | The contrast: less detail, flat colour. Shows what "not that" means |

**Dropped from the list:**
- **Vanilla Tweaks** (https://vanillatweaks.net/terms/): a picker of small tweaks with no
  overall look, and 1.13+ as far as I could see.
- **Mizuno's 16 Craft:** I could not reach an official page. Its CTM add-on on Modrinth is MIT,
  but the base licence is unverified. Its cottagecore style is off the brief.
- **Clarity and Excalibur:** ARR and off-style.
- **Faithful PBR 32x:** ARR, 1.14–1.19 only.

**Recommendation:** the route our sources support is Faithful 32x for detail, our own art
direction for grass, foliage and colour, Angelica's CTM, and our own LabPBR maps. That route is
QF v0, below. The owner picks the 2–3 packs above that come closest to what they want, and later
versions aim at those.

**Owner, 2026-10-25:** has looked at packs and likes a lot of things from **Faithless**. It is
ARR and 1.20+, so it is inspiration only: name the elements they like (shapes, palette,
shading, detail level, specific blocks), then draw our own versions of those ideas over the
Faithful/vanilla base.

## 4. QF Textures v0 (prototype)

**Source:** `resourcepacks/QFTextures/` (pack.mcmeta, CREDITS.txt, faithful.txt).
**Build script:** `tools/textures/build_qf_textures.py`.
**Output:** `C:\qfb\textures\QFTextures-v0.zip`, 1.6 MB.

The zip is never committed: it contains Mojang's pixels, read from the player's own
`minecraft.jar` at build time.

```
py -3.10 -I tools/textures/build_qf_textures.py --out C:\qfb\textures\QFTextures-v0.zip
```

**What it contains:**
- **Vanilla 1.7.10** for every block texture except those listed below (300 textures).
- **Faithful 32x** for 47 textures: stone, all eight ores, gold/iron/diamond blocks, glowstone,
  glass, the stained glasses and the pane tops.
- **Faithful's connected glass**, 833 CTM files.
- **Grass:** vanilla's `grass_top` and `grass_side_overlay` doubled to 32x, keeping vanilla's
  pattern. Contrast is pulled toward a 3×3 blur, keeping 68%, so the carpet reads calmer. Faithful's
  grass is not used.
- **Vibrance:** chroma ×1.12 around each pixel's own luminance.
  - Grey, biome-tinted textures are unchanged; their colour comes from the shader's tint.
- **LabPBR `_n` + `_s` for 1,132 textures, CTM tiles included:**
  - Normals come from gen_surface_pack's luminance relief and per-material strengths, converted to
    DirectX Y, with cavity AO in B and height in A.
  - Specular is set per material:
    - glass 0.96 smooth;
    - gold block = 231 and iron block = 230 hard-coded metals;
    - diamond F0 0.17;
    - ore pixels, found by difference from stone, get their own smoothness and F0 (gold flecks
      are metal);
    - soils have porosity, leaves and plants subsurface;
    - glowstone, lamps, torches, lava and fire have emission from their bright pixels.
  - The shader does not read these yet (section 2).
- **Faithful licence:**
  - credit and a link in pack.mcmeta and CREDITS.txt;
  - LICENSE-Faithful.txt (v4) is included unmodified;
  - only the textures we use are taken.

**Open:**
- **Is shipping recoloured vanilla textures acceptable?** It is common practice for resource
  packs, but the owner should agree before the pack is distributed with the modpack.
- **Glass panes** need `glassPane=true`.
- **Modded blocks are untouched** (still 16x).
- **Foliage, logs, planks and dirt are vanilla 16x.** The owner liked vanilla's look in the
  forest, so they stay until he picks a direction.

**Test world:** the bench gallery puts its blocks two apart, so CTM never shows there.
- `tools/textures/build_showcase.py` copies `C:\qfb\world-master` to
  `C:\qfb\textures\world-showcase` and builds a wall of glass 4×4, stained glass, stone with ores,
  gold, iron, diamond and glowstone on the plain behind golden_lit's camera.
- Views `texture_wall` and `glass_close` are in `tools/shaders/review/views-world-master.txt`.
- Render with `bench_round.py --world C:\qfb\textures\world-showcase`.

**r007 renders** (bench tags in `C:\qfb\shaderdev
ounds`):
- `tx0v` vanilla, `tx0f` Faithful 32x, `tx0r` QF v0 (`tx0q` is an earlier QF v0 run), and
  `tx0o` with shaders off.
- Views: texture_wall, glass_close, forest_lit, golden_lit and gallery.
- Run script: `C:\qfb	extures	x0.sh`. Lab scenes: `C:\qfb\shaderdev
007	exture_scenes.json`.
- The pack makes no measurable difference to cost: frame times are within 0.02 ms of vanilla on
  every view.
- In forest_lit, QF v0 is almost identical to vanilla, by design. On the wall it has Faithful's
  detail with vanilla's grass.
