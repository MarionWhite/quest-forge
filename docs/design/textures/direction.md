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
- `tools/shaders/gen_surface_pack.py` writes LabPBR too since 2026-10-25 (`_n` + `_s` for every
  modded texture, `--format legacy` for the OptiFine/Vibrant fallback), through the shared
  `tools/textures/labpbr.py`; `--only` builds the maps for a ranked list. See
  [modded-blocks.md](modded-blocks.md).

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
- **Modded blocks are untouched** (still 16x). Which ones matter, and in what order, is
  [modded-blocks.md](modded-blocks.md); their LabPBR maps are built by `gen_surface_pack.py`.
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

### Shipping (decision 0006, 2026-10-25)

The owner decided ([decisions/0006](../../decisions/0006-textures-ship-and-panes.md)) that QF
Textures ships with the pack as a built zip, and that glass panes connect
(`connected_textures { B:glassPane=true }` in `config/mcpatcherforge.cfg`: now in
`pack/config/`, installed into the live client with `trial.py install`, and in every trial and
release built from it; the showcase wall's top row holds panes for the next render round).

**One zip, one command:**

```
py -3.10 -I tools/textures/build_ship.py --out C:\qfb\textures\QFTextures.zip
```

`tools/textures/build_ship.py` runs `build_qf_textures.py` (QF v0) and `build_modded_textures.py`
(modded v1, [modded-blocks.md](modded-blocks.md) section 4b) and merges them: one `pack.mcmeta`,
one `CREDITS.txt` (v0's credits, then v1's generated per-file records, both Faithful zips with
their sha256), `LICENSE-Faithful.txt` once, and every other member of both (they share no path,
which the merge asserts).

- **`C:\qfb\textures\QFTextures.zip`**, built 2026-10-25: **5,204,668 bytes (5.2 MB)**, sha256
  `5044df51e593abe9553c651afe9ef9a0893d5e3992417d3bdb18980b7e897ef9`, 9,366 members plus the
  three shared files, 3.7 s. Rebuild it after any change to either builder or their lists; the
  hash changes with every build (PNG encoding is deterministic, but the dates in CREDITS are
  not), so the record above is of that build.
- Never committed: it carries vanilla's pixels (recoloured) and the mods' pixels (re-arranged).
- **Release:** `tools/release/build_client_release.py --textures` (the default path above) copies
  the zip into `resourcepacks\` and selects it in `options.txt` after the packs already selected
  (`resourcePacks:["QuestForge.zip","QFTextures.zip"]`; the branding pack has no block textures,
  so the order does not matter today); the Angelica edition inherits both. The client profiles
  (`tools/lite-client/profiles/*.json`, `resourcepacks` section) select it on apply and leave the
  selection alone when the zip is missing.

## 5. QF Textures v1 (Shader Lab round 8, 2026-10-25)

**The owner's round 7, in short:**
- **QF v0 won** the wall, glass, forest and golden comparisons.
- In the forest, v0 and vanilla looked identical: v0 changed too little there.
- Faithful's dirt has the better side profile.
- Faithful 64x is "just a better version of 32": the stone bricks and metals.
- Stay True's crops and leaves, but not its frills on lone blocks and hedges.
- Patrix's mobs: are they achievable, and at what cost?
- Vanilla Normals Renewed has the best light interaction.
- Conquest's water effects. They are shader-side; the shader agent has them.
- Soartex's bookshelves.
- Faithless's items, GUI, creative tabs, TNT lettering, boss bars, animations; not its blocks.

**Build:**
```
py -3.10 -I tools/textures/build_qf_textures.py --out C:\qfb\textures\QFTextures-v1.zip [--leaf-edges none|all|sides] [--no-cit]
```
- The output zip is not committed (it holds Mojang pixels).
- v0's builder is commit e4dd9f6; v0 itself is `C:\qfb\textures\QFTextures-v0.zip`.
- Sources:
  - `resourcepacks/QFTextures/`: pack.mcmeta, CREDITS.txt, faithful64.txt, ctm47.json;
  - `tools/textures/qf_art.py`: our drawn blocks;
  - `qf_items.py`: items;
  - `vnr.py`: PBR conversion.

**What v1 contains:**

| Part | Source | Notes |
|---|---|---|
| Stone, stone bricks (4 kinds), cobble, mossy cobble, all ores, gold/iron/diamond/emerald/lapis/redstone/coal blocks, glowstone, glass + stained + pane tops, dirt, grass_side (+ overlay), farmland | **Faithful 64x**, 1.7.10 branch (61 textures) | chroma x1.10 |
| Connected glass | Faithful 64x's 851 CTM files | Its stained rules use 1.13 names (`matchBlocks=black_stained_glass`), which 1.7.10 does not know. The build rewrites them to `95`/`160` + `metadata` and names each rule after its folder, as Angelica's defaults are named (`black_stained_glass`, `black_stained_glasspane`). Clear glass ships Faithful's own rule unchanged (`matchBlocks=glass` is a 1.7.10 name too): renamed, or moved to Angelica's path with `20`, it lost to Angelica's built-in 16x glass rule (r008 renders v1 and v1b). |
| Leaves (oak, birch, jungle, acacia, dark oak; spruce needles), their Fast `_opaque` forms | **ours**, 32x, `qf_art.leaves` | Lit clumps of single leaves: bright crown, dark underside, dark seams between leaves, gaps only between clumps. Grey, so biome tint still applies. Mean value kept at vanilla's. |
| Log sides and ends, six woods | **ours**, 32x | Bark ridges broken into plates, lit left, dark fissures; ring ends with a bark rim. |
| Tall grass, fern, wheat stages 0-7 | **ours**, 32x | Wheat: 13 stalks, kernel-pair ears that nod, awns, green to turning to gold. |
| Grass top | **ours**, 32x | Calm: clump-scale light and shade, sparse blade marks, narrow value range (no "carpet"). |
| Bookshelf | **ours**, 32x, four variants | Leather books of varied width, height and colour, gilt bands, title labels, gaps, the odd leaning book. Mixed by CTM `method=random`. This **replaces Angelica's built-in bookshelf CTM** (DarkBum's `method=horizontal`, which otherwise overrides any `bookshelf.png`). |
| Everything else | vanilla 1.7.10 | chroma x1.10 (v0 used 1.12; "keep vibrance modest") |
| LabPBR `_n`/`_s` | 142 VNR converted, 33 hybrid, the rest ours | Details below |
| Potion bottles, enchanted-book covers | **ours**, CIT | Section 7 |

**PBR, toward VNR's quality:**
- **Vanilla textures VNR covers** (142) get VNR's own maps, converted to LabPBR:
  - VNR's normals are OpenGL (green up the image): `G` correlates -0.83 to -0.98 with the height's downward slope on stonebrick, cobble, planks and brick. So G is flipped to DirectX.
  - AO is computed from VNR's height.
  - The metal flag (G 255) becomes LabPBR 230 (iron) or 231 (gold).
  - VNR's blue-channel emission moves to alpha.
- **Faithful 64x textures that keep vanilla's layout** (33; luminance correlation over 0.45 after box-filtering to 16x) get a hybrid:
  - VNR's height and normal, upscaled smoothly: the bevelled bricks and rounded cobbles;
  - plus our own relief from the 64x pixels (weight 0.7);
  - VNR's smoothness pattern;
  - our ore-fleck rule on the 64x art.
- **Everything else** (our drawn art, CTM tiles, the rest) uses `labpbr.py` as in v0.
- The QuestForge shader does not read `_n`/`_s` by default yet (QF_PBR is the shader agent's).
- The owner's r007 note, "the metallic blocks just look like they are in the shade", is the shader's side. LabPBR metals (230/231) have no diffuse term, so without a sky or environment reflection they render dark. Handed to the shader agent.

**Where generated art falls short (honest):**
- Leaves, bark and bookshelves read well at 1:1 and in game. They are a clear step from vanilla.
- They are not Stay True's hand-placed quality: the leaf clumps are blobby in places.
- The wheat is dense, and its ripe colour is now straw (the first render's gold went orange in the sun). The ears are chunky and the middle stages blotchy lime next to Faithful's; a pixel artist would draw each ear.
- The grass top is calm but a little flat.
- The fern is weak (a stiff, symmetrical frond) and the birch bark is blotchy. Both are candidates for hand drawing.
- I did not redraw flowers, saplings, double plants, carrots or potatoes. Code would not beat vanilla's own there, so they stay vanilla.

### Licences checked 2026-10-25

**Faithful 64x:**
- Downloaded from https://github.com/Faithful-Resource-Pack/Faithful-64x-Java, branch `1.7.10`, head `89f200c` (2026-10-25). sha256 `992d7c04...`; details in `C:\qfb\faithful64\meta.txt`.
- There is no 1.7.10 release, so we use the branch archive. It is repacked flat for trials as `C:\qfb\faithful64\Faithful-64x-1.7.10.zip`.
- It ships **Faithful License v4** (Jul 31, 2026), identical to the 32x copy we already credit: use, modify and distribute with credit and a link, never paywalled.
- 438 block textures are true 64x. Only `water_overlay` is an upscale.
- It lacks the six `leaves_*_opaque` and the beds. The leaves do not matter here: v1 draws its own.

**Vanilla Normals Renewed:**
- The 1.13+ repo uses `block/` names. The pre-1.13 pack is the separate archive repo https://github.com/Poudingue/Vanilla-Normals-Renewed-1.12 (v0.04, commit `c848329`, 2020-05-24), which already uses 1.7.10-style names (`blocks/`, `planks_oak`, `stonebrick_mossy`).
- It has no LICENSE file. The README's terms:
  > "You can do whatever you want with my texture pack, screenshots, videos, modifications for
  > personal use or redistribution, as long as you don't sell it and provide a link to this page
  > or my Patreon. Oh, and also, don't mix it with Realistico."
- **Verdict: allowed.** A free, never-sold pack may redistribute modified (converted, renamed) maps with a link. We do that, credit it in CREDITS.txt and pack.mcmeta, and never mix it with Realistico.
- We ship **only its `_n`/`_s` maps**, never its 321 albedo PNGs, which are modified Mojang textures.
- **Caveats:**
  - It is an informal README grant, not a formal licence, so the author could change it.
  - His later MIT pack, Vanilla-Normals-Reborn, was made "to make sure I don't get into legal trouble with Mojang". It is a cleaner-licensed fallback; not yet inventoried.

## 6. The owner's questions, answered

### Patrix: what is achievable on 1.7.10, and what it costs

**Patrix itself:** ARR and 1.20+. We can only take ideas from it, never files.

**Mobs, the part the owner liked:**
- **What Patrix does:** its mobs are mostly OptiFine **CEM**, custom entity models (`.jem`): new geometry (horns, manes, fur tufts, armour plates), new animations, plus emissive eyes.
- **What 1.7.10 has:** no CEM, and no OptiFine at all on our Angelica stack. Mob geometry is Java code (`ModelBase` subclasses).
- **So, in tiers:**
  1. **Skin repaints: yes, cheap.**
     - A resource pack can replace every vanilla mob texture, at 2x or 4x resolution, if the aspect ratio is kept (1.7.10 scales entity UVs).
     - Patrix-style shading and detail on the existing shapes: fur, scales, cloth, eyes.
     - Frame cost: none measurable; one bound texture per mob either way. VRAM: kilobytes per mob at 32x.
     - Work: an artist's work. Generated mob skins would be junk; I will not ship them.
  2. **Random variants: yes, one switch.**
     - Angelica's MCPatcherForge `random_mobs` module is off by default.
     - It gives several skins per mob, chosen per biome or height. Frame cost: none (a texture choice at render).
     - It needs a trial (`trial.py`) before it goes live, like CIT.
  3. **Glowing eyes and other emissive parts: probably, shader-side.**
     - Our deferred shader can make chosen pixels emissive.
     - Unverified: whether Angelica's Iris port loads `_s` maps for entity textures. Iris does on modern versions; I did not test Angelica.
     - The fallback is an entity-ID rule in the shader. Cost: one texture fetch in the entity pass, a few hundredths of a ms.
  4. **New shapes: only with code.**
     - A per-mob replacement model and renderer in our own mod (qf-content). It must keep the vanilla animation hooks, mob by mob.
     - Modded mobs (Twilight Forest, the mob mods) need their own renderers and would not follow.
     - Frame cost: small. Entities are a tiny share of our frame next to terrain. A few dozen extra cubes per mob, on 20-40 mobs, is well under 0.1 ms. That is an estimate; measure it if we go there.
     - The real cost is the work and compatibility, not the GPU.

**The rest of Patrix** (32x blocks, extensive CTM, LabPBR) is the route we are already on:
- **32x/64x blocks:** VRAM and atlas size.
  - We use 64x only on about 60 textures.
  - With thousands of modded 16x textures in the atlas, 64x everywhere would multiply atlas memory by 16. That would hurt the friends' weaker PCs.
- **CTM:** costs CPU at chunk rebuild, not per frame.
- **PBR:** two texture fetches and a TBN per terrain fragment, about 0.1-0.2 ms at 1440p High (estimate, section 2).

**Answer:** Patrix-quality mob skins and random variants are fully achievable at no performance cost, but they need a pixel artist. Patrix's 3D mob shapes need Java renderers, mob by mob.

### Leaf frills: options on 1.7.10

Stay True's frills are **block-model geometry**: 1.14+ JSON models with planes sticking out of the leaf cube. 1.7.10 has no JSON block models; a leaf block is always the cube `RenderBlocks` draws. Options:

| Option | How | Frills go | Lone block / hedge | Cost | Rendered |
|---|---|---|---|---|---|
| A. No frills (v1 default) | Our clumped leaf texture on the cube | none | Clean cube | none | `t8v1` |
| B. Ragged edges everywhere | CTM `method=ctm` (47 tiles per wood): every face edge with no leaf block beyond it is bitten in, with a wandering profile and a dark rim | **inward**: the silhouette breaks up | A lone block reads as a ragged bush; a hedge's top and ends are ragged, its flat sides clean | none per frame; 47 tiles per wood in the atlas | `t8e1` |
| C. Ragged top and bottom only | Same, but only side faces (`faces=sides`), and only their top/bottom edges | inward, only where no leaf is above or below | Hedge sides and ends stay straight; only the top line is ragged | as B | `t8e2` |
| D. Real outward frills | Code in qf-tweaks: extra crossed quads (like tall grass) on leaf faces that have air beyond, optionally only above and below | **outward**, like Stay True | Can be skipped for lone blocks: draw frills only on leaves with leaves beside them | More vertices in leafy chunks (estimate +30-60% there), slower chunk rebuilds. Must work inside Angelica's chunk renderer; modded leaves (BOP, Twilight) need their own hook. Days of work plus a trial | not built |
| E. Shader silhouette | A geometry shader growing leaf triangles, or alpha-dithering leaf edges in the fragment shader | GS: outward. Dither: inward only, like B | as B/C | GS on every terrain triangle is expensive, and whether Angelica's Iris supports `.gsh` is unverified. Not recommended | not built |

- **The owner's own idea,** "frills only with air above or below", is option C as a texture, or D as geometry.
- **CTM caveat:** CTM only sees neighbours in the face's own plane. So "air above" means "no leaf block above", which is the same thing in practice.

**Recommendation:** pick between A, B and C from the renders now; they are free. Build D only if B and C fall short, as a trial with a measured cost.

## 7. Items: potion bottles and enchanted books (CIT prototype)

**What it is:** `tools/textures/qf_items.py`, built into the pack under `assets/minecraft/mcpatcher/cit/`.

**CIT is on only in the trial:**
- It is off in the live `mcpatcherforge.cfg`.
- renderq's `"cit": true` job field switches it on in its trial's config only (`batch.enable_cit`, commit 691b16d).

**How it works:**
- A potion draws two layers:
  - `potion_overlay`, the liquid, tinted with the effect's colour;
  - `potion_bottle_drinkable` or `potion_bottle_splash`, the glass.
- Our rule replaces both. The liquid stays grey, so the game's own colour fills our bottle: the shape says which effect, the colour stays familiar.
- `damageMask=16399` (effect bits plus the splash bit) gives all levels and durations of an effect one bottle.
- Books match `enchantmentIDs`; CIT reads StoredEnchantments.

**The prototype:**
- **Seven bottle shapes for 12 effects, plus a splash grenade:**
  - round flask: regeneration;
  - slim vial: swiftness, weakness;
  - squat jar: fire resistance, slowness;
  - heart: healing;
  - cone flask: night vision, invisibility;
  - square bottle: strength, harming;
  - teardrop: water breathing, poison.
- **Nine book covers:** a coloured cover per family, each with a 7x7 emblem:
  - armour (blue): shield, flame;
  - weapon (red): sword, flame;
  - tool (green): pickaxe, thread, anvil, gem;
  - bow (brown): arrow.

**Quality, honestly:**
- The sprites are readable. The silhouettes differ at a glance, and the heart, cone and jar read best.
- They are flat next to Faithless:
  - no 3/4 tilt on the books;
  - two or three shading steps;
  - emblems are icons, not illustrations;
  - per-effect props (feathers, flames, bubbles) are missing.
- They are hand-placed pixel grids, not generated art: each shape is typed in the code as a 16x16 grid. A grid is as good as the person typing it.
- Faithless-level sprites need a pixel artist. A skilled one might do the 81 custom enchantments' emblems in two to three days (about 10-15 minutes each, plus review). The potion set takes a day.

**A sustainable path:**
1. **Style guide** (already the legend in qf_items.py):
   - 16x;
   - a one-pixel dark outline (34,30,44);
   - light from the upper left;
   - three steps of shading;
   - tell items apart by silhouette first, colour second;
   - potion liquids grey (the game tints them);
   - book covers coloured by family, the emblem in a fixed 7x7 slot at (5,4).
2. **Templates:** the book base and the bottle grids. An artist edits a grid, or drops in a PNG of the same size, and the build picks it up.
3. **Coverage first, polish second:**
   - Family covers for all 81 custom enchantments, so enchanting is readable at once. This needs the enchant census's ID list.
   - Then emblems, most-used first.
4. **Next and cheap:** the TNT side with enchanting-table (Standard Galactic) lettering; Faithless-style creative tabs; boss bars. Each is a plain texture or a small GUI repaint.
5. **Not cheap:** GUI layout outside a container's frame, and the redstone readouts. Both need code.
