# Ambience research: RLCraft-style ambience on the Quest Forge stack

Research only, 2026-10-17. Nothing was installed or launched, and nothing in the repo was edited.
Claims marked **[unverified]** come from inference or from a single anecdote. They have not been tested in this pack.

## 0. Repo facts that change the answer

- **The lite and potato profiles run with shaders off** (docs/design/performance-plan.md, around line 147). Friends on weak PCs will never see anything that lives only in the shader pack. Their fog and sky have to come from somewhere else, such as a resource pack.
- **The lite profile already drops SoundFilters** (the "Mods out" row in performance-plan.md).
- **The Angelica client ships without Hodgepodge or ArchaicFix** (tools/angelica-client/manifest.json, docs/design/angelica-decision.md). It has GTNHLib, but only on the client. Java 25 with lwjgl3ify is planned for the server; the client manifest does not include lwjgl3ify.
- **GTNHLib crashes OptiFine E7** (angelica-decision.md). Any mod that needs GTNHLib therefore works only on Angelica clients.
- **Parity rule:** client-only mods must never go on the server, or every client is forced to have them. This is the same lesson as GTNHLib.
- **The shader research already lists the known breakers:** Better Foliage dark shadows and Dynamic Surroundings breaking rain detection (docs/design/shaders/research/desirability.md, around lines 141–145).

## 1. Mods

| Mod | Latest 1.7.10 build | What it does | Angelica and shaders | lwjgl3ify / Java 25 | Cost (all **[unverified]**, not measured) |
|---|---|---|---|---|---|
| **Dynamic Surroundings** (mist475 fork of OreCruncher; needs UniMixins) | 1.0.9.0, 2026-09-30 ([Modrinth](https://modrinth.com/mod/dynamic-surroundings-unofficial-1.7.10), [GitHub](https://github.com/mist475/DynamicSurroundings)). The last official build is 1.0.6.4 from 2018 ([CurseForge via cfwidget](https://api.cfwidget.com/minecraft/mc-mods/dynamic-surroundings)). The maintainer says they are not continuing it. | Biome sounds, footsteps (the Presence Footsteps engine is built in), auroras, biome/morning/weather/elevation fog, desert dust, rain/snow overhaul with splash particles, block "jets" (steam, fire, bubbles, dust, fountains), damage pop-offs, potion HUD | **Overwrites** `EntityRenderer.renderRainSnow` and `addRainParticles`, and `World.updateWeatherBody` (mixins/early/MixinEntityRenderer.java and MixinWorld.java). These overwrites are unconditional. Open issue [Angelica #1524](https://github.com/GTNewHorizons/Angelica/issues/1524) "DS breaks shaders rain detection" reproduces on Complementary and Sildur's and is still there in 2.1.22. One user does not reproduce it on 2.1.16 with lwjgl3ify 3.0.16. Fog changes GL fog colour and density, which shaders read as `fogColor`. Auroras are drawn in the world pass with blending, so they will probably break under a deferred pack **[unverified]**. | Its sound mixins target paulscode. A commenter on #1524 runs it with lwjgl3ify 3.0.16. DS 1.0.7.4 fixed a clash with MAtmos. | Medium CPU: block-effect scanning, biome survey, sound engine. Rain splash default is 100 particles per tick. Open crash issues [#11 (flushSound)](https://github.com/mist475/DynamicSurroundings/issues/11) and [#12 (biome fog)](https://github.com/mist475/DynamicSurroundings/issues/12). |
| **An Extra Touch** (needs UniMixins, GTNHLib, AngelLib) | 0.0.12, 2026-05-14 ([Modrinth](https://modrinth.com/mod/an-extra-touch), [CurseForge](https://www.curseforge.com/minecraft/mc-mods/an-extra-touch)). GitHub snapshots up to 2026-09-25 ([releases](https://github.com/AngelicIndustries/AnExtraTouch/releases)). | Footprints, cold breath, dripping-wet entities, wet footsteps, armour sounds, enhanced thunder, water and lava splashes, **waterfall foam and ambience**, rain ripples, wakes, coastal waves, camera tilt and shake, smooth GUI. Can mute DS animal sounds. | **Built for Angelica.** It has a mixin into Angelica's `DeferredWorldRenderingPipeline` (captures depth before translucents), and 0.0.12 fixed culling "with renderer replacements like Angelica". | Unknown. GTNHLib is required, so it runs on Angelica clients only. | Low to medium **[unverified]**. It ships a network channel (armour step, explosion shake), so it must be installed on clients only. |
| **MAtmos** (makamys) | 1.7.10-36.0.1, 2024-02-14 ([Modrinth](https://modrinth.com/mod/matmos), [GitHub](https://github.com/makamys/MAtmos)). Pair it with the [MAtmos 2020 "Zen"](https://github.com/makamys/MAtmos-2020-Zen) soundpack. | Data-driven biome, indoor/outdoor and deep-indoor soundscapes. This is the closest match to RLCraft's ambience. | Audio only, so no rendering conflict. | Unknown. Open issues: [#16](https://github.com/makamys/MAtmos/issues/16) and [#31](https://github.com/makamys/MAtmos/issues/31) (conflicts with Sound Physics), and [#21](https://github.com/makamys/MAtmos/issues/21) (sounds cut out with DynamicSounds). | Low to medium: periodic block scans around the player **[unverified]**. Overlaps DS biome sounds, so pick one of the two. |
| **Better Foliage – Legacy Edition** (Kynake; needs UniMixins and Forgelin) | 1.2.4, 2026-01-31 ([Modrinth](https://modrinth.com/mod/better-foliage-legacy-edition), [GitHub](https://github.com/Kynake/BetterFoliage)). The original stopped at 2.0.17 in 2017. | Falling leaf particles, short grass, round logs, reeds, algae, coral, cactus, rising soul particles | States that it aims at Angelica compatibility. Grass goes black or dark when a shader sets `separateAo=true` ([#1351](https://github.com/GTNewHorizons/Angelica/issues/1351), [#2022](https://github.com/GTNewHorizons/Angelica/issues/2022), both open). The workaround is `separateAo=false` in shaders.properties, which the pack's own shader controls. | Unknown. | GPU and chunk-mesh cost from the extra geometry. Round logs and short grass are the heavy options **[unverified]**. Chunk building is threaded under Celeritas. |
| **Sound Physics 1.7.10 Mixin Edition** (mist475) | 1.1.1, 2026-06-27 ([Modrinth](https://modrinth.com/mod/sound-physics-1.7.10-mixin-edition), [GitHub](https://github.com/mist475/Sound-Physics)). Unmaintained. | Ray-traced reverb, occlusion and absorption | Audio only. | Fixed explicitly for lwjgl3ify: [lwjgl3ify #60](https://github.com/GTNewHorizons/lwjgl3ify/issues/60) and [#75](https://github.com/GTNewHorizons/lwjgl3ify/issues/75). | CPU raycasts for every sound **[unverified]**. Overlaps SoundFilters, so run one, not both (an inference; no conflict report found). |
| **SoundFilters 0.8** (installed) | 2015 ([CurseForge](https://www.curseforge.com/minecraft/mc-mods/sound-filters)) | Cave reverb, muffling underwater and behind walls | Audio only. | Unknown. | The pack already drops it in the lite profile. |
| **Presence Footsteps** | No Forge 1.7.10 build. Only an unofficial **LiteLoader** r5c ([Modrinth](https://modrinth.com/mod/presence-footsteps)). | — | Angelica needs LiteloaderLoader to run LiteLoader mods (Angelica README). | — | Skip it. DS already contains its engine. |
| **AmbientSounds** (CreativeMD) | None for 1.7.10 ([cfwidget](https://api.cfwidget.com/minecraft/mc-mods/ambientsounds)). | — | — | — | — |
| **Fancy Block Particles** | 1.7.x-2.4.1, 2018 | 3D particles | Broken by Angelica particle batching ([#2237](https://github.com/GTNewHorizons/Angelica/issues/2237), open). | — | Avoid. |
| **Fireflies, falling-leaf or aurora-only mods** | None found for 1.7.10. Particular and fireflies mods are 1.20+ only (web search). | — | — | — | Build these in qf-content. |

**GTNH:** the GTNewHorizons GitHub org has 333 public repos and **none of them is an ambience fork**. Only Climate-Control, BiomeBridge and similar match the keywords, and those are worldgen. The GTNH 2.9.0-RC-2 manifest ([DreamAssemblerXXL](https://github.com/GTNewHorizons/DreamAssemblerXXL)) ships no DS, MAtmos or BF; its only sound-related mod is Extreme Sound Muffler.

**What Angelica itself provides** ([README](https://github.com/GTNewHorizons/Angelica)):
- dynamic lights;
- batching and instancing of particles and weather;
- MCPatcher features (alpha): **custom colors** (resource-pack biome, fog and sky colours), **better skies** (skyboxes) and connected textures;
- no ambient particles and no sounds.

MCPatcher custom colours are the cheapest way to give no-shader (lite) players per-biome fog and sky tint. That is a resource-pack job with no extra mod **[unverified on Angelica's alpha implementation]**.

## 2. Shader vs mod vs qf-content

**Things that conflict with a custom shader pack:**
- **DS fog:** it changes the GL fog colour and density that shaders read, and the look bible (Tier A #6, Tier C #17) makes the shader the owner of fog. Turn it off (Biome, Morning, Weather and Desert Fog, and Elevation Haze).
- **DS weather overwrite:** it causes the rain-detection bug in #1524. Whether DS's `Disable Weather Effects` setting restores the vanilla path and the vanilla rain strength is **[unverified]**, because the mixin `@Overwrite` itself is unconditional.
- **DS aurora:** it blends, and a deferred G-buffer cannot blend. Disable it and draw auroras in the shader instead.
- **Better Foliage:** it needs `separateAo=false` in the pack.
- **MCPatcher better skies or custom colours** would double up with a shader sky. Use them only for shaders-off players **[unverified whether Angelica suppresses them under a shaderpack]**.

**Shader owns:**
- fog: biome, weather, height and per-dimension;
- sky and auroras: auroras gated by the biome or temperature uniforms, if Angelica's Iris backport exposes them **[unverified]**;
- rain darkening and wetness;
- waving leaves and grass;
- heat shimmer over lava and desert;
- god rays;
- underwater fog.

**Resource pack (MCPatcher custom colours) owns** the shaders-off fallback for biome fog and sky colours.

**Mods own:**
- **Biome soundscape:** MAtmos with Zen (lightest and purely audio). Use DS only if you also want its footsteps and are willing to configure away its fog, aurora and weather.
- **Footsteps:** the DS engine, or An Extra Touch's wet and armour steps.
- **Reverb and occlusion:** exactly one of SoundFilters or Sound Physics.
- **Falling leaves and foliage geometry:** BF Legacy.
- **Water, waterfall, breath and footprints:** An Extra Touch, on Angelica clients only because it needs GTNHLib.

**qf-content owns** the pack-specific effects: minecart sparks, lava embers, waterfall mist (if An Extra Touch is not used), desert dust (if DS is not used) and swamp fireflies, plus ambient sound beds for the pack's roughly 30 modded dimensions, which no mod covers.

**A coherent minimal set:** MAtmos + Zen, BF Legacy (falling leaves only, with short grass and round logs off in lite), and the qf-content ambience module. Add An Extra Touch on Angelica clients. Skip DS unless its footsteps are wanted, and only after a bisect of #1524 against the pack's own shader.

## 3. Sketch: a qf-content ambience module

This is a sketch only; no code was written.

**Where it hooks in.**
- qf-content's client code is a single event hub: `client/QFClientEvents` (client tick END, `RenderWorldLastEvent`, overlay events), registered on both buses by `ClientProxy.init`.
- Its convention is that nothing else in the client package touches Forge events. So the hub calls `Ambience.tick()` from `onClientTick` and `Ambience.clear()` from `onDisconnect`.
- The new code lives in a `client/ambience/` package.
- `client/Shaders.active()` already tells whether a shader pack is running, under either OptiFine or Iris.
- The module is client-only, with no packets and no server parity concerns.

**Classes.**
- **`Ambience`:** the director.
  - Each tick: return if paused, if there is no world, or if `gameSettings.particleSetting == 2` (Minimal).
  - Otherwise compute the budget and run each emitter.
- **`Budget`:**
  - Spawns per tick: `base × {All: 1.0, Decreased: 0.35, Minimal: 0}`.
  - A hard cap on live ambience particles, for example 300 at All and 100 at Decreased. Each `QFAmbientFX` increments a counter in its constructor and decrements it in `setDead`.
  - Optionally halve the budget when the smoothed frame time exceeds about 16 ms.
  - It reads the vanilla setting, so the lite profile, which sets Decreased and never touches config/, scales it down automatically.
- **`QFAmbientFX extends EntityFX`:** the shared particle class.
  - It uses the standard particle sheet and `fxLayer`, and renders only through the passed-in Tessellator: no `draw()`, no texture binds and no GL state changes inside `renderParticle`. That keeps it safe with Angelica particle batching and culling, which broke custom FX that do their own tessellating ([#1975](https://github.com/GTNewHorizons/Angelica/issues/1975), [#2237](https://github.com/GTNewHorizons/Angelica/issues/2237)).
  - Glowing effects override `getBrightnessForRender` to return `0xF000F0` rather than using additive blending, because deferred packs cannot blend.
  - Sprites are alpha-tested, not translucent.
- **`BlockSampler`:** works like vanilla `WorldClient.doVoidFogParticles`. It picks N random positions within 16–24 blocks of the player, with N taken from the budget, and asks each `BlockEmitter` whether that block matches.
  - **Lava embers:** lava with air above. A small, rising, full-bright orange mote, life 20–40 ticks, at about a 1/8 chance.
  - **Waterfall mist:** flowing water with metadata ≥ 8 (falling) and still water or a solid block below. Spawn a puff with drift where the column lands, plus a quiet looped hiss with a per-position cooldown.
  - **Desert dust:** `BiomeDictionary` types SANDY and HOT, the sky visible at the sampled y, daytime. Low, sideways-drifting tan motes. Off when rain flags are set.
  - **Swamp fireflies:** biome type SWAMP, night, not raining, light level ≤ 7, near tall grass or water. Slow-wander full-bright yellow-green dots that pulse, with their own sub-cap (for example 24).
- **`MinecartSparks`:** scans `mc.theWorld.loadedEntityList` every 2 ticks for `EntityMinecart` within 24 blocks.
  - It triggers when horizontal speed exceeds 0.3, the block at the cart is a `BlockRailBase` (Railcraft 9 `BlockTrack` is believed to extend `BlockRailBase` **[verify]**), and either the rail metadata is a curve (6–9) or speed dropped by more than 30% since the last sample (braking).
  - It emits 1–3 short-lived (6–10 ticks), gravity-affected, bouncing, full-bright sparks at the wheel positions, plus an optional brake-squeal sound with a cooldown.
- **Config:** one qf-content config category with a master toggle and a per-emitter multiplier. The vanilla particle setting stays the primary knob.
- **Debug:** a client command, `/qfambience`, prints live counts per emitter. It registers through `ClientCommandHandler`, the same way `CommandJukebox` does.

## Sources

- https://api.modrinth.com/v2/project/{dynamic-surroundings-unofficial-1.7.10, an-extra-touch, matmos, better-foliage-legacy-edition, sound-physics-1.7.10-mixin-edition, presence-footsteps}
- https://api.cfwidget.com/minecraft/mc-mods/{dynamic-surroundings, matmos, better-foliage, an-extra-touch, ambientsounds, fancy-block-particles, sound-filters, presence-footsteps}
- https://github.com/GTNewHorizons/Angelica (README); issues #1351, #1524, #1975, #2022, #2237
- https://github.com/GTNewHorizons/lwjgl3ify issues #60 and #75
- https://github.com/mist475/DynamicSurroundings (source, CHANGELOG, issues)
- https://github.com/makamys/MAtmos/issues
- https://github.com/GTNewHorizons/DreamAssemblerXXL releases/manifests/2.9.0-RC-2.json
- GitHub API listing of the GTNewHorizons org (333 repos)
