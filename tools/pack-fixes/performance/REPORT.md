# Quest Forge performance pass — 2026-09-04

Hardware read from this PC: Ryzen 9 7900X (12C/24T), RTX 5070 Ti (OptiFine is already using it), 31.1 GB RAM. Java 8 u241.

Honest ceiling: 139-mod 1.7.10 + Lycanites/OreSpawn/TragicMC/HBM + Sildur Vibrant High will not feel like modern vanilla. Expect smoother chunk updates and fewer GC/minimap hitches, not 200 FPS.

## Applied now

| File / key | Before | After |
|---|---|---|
| `TEST-LAUNCH.bat` heap | `-Xms1024M -Xmx7168M` | `-Xms2048M -Xmx7168M` (Xmx unchanged; 31 GB RAM, stay under ~8G on Java 8 / 1.7.10) |
| `TEST-LAUNCH.bat` GC | `-XX:+UseParallelGC -XX:ParallelGCThreads=12 -XX:+ScavengeBeforeFullGC` | `-XX:+UseG1GC -XX:MaxGCPauseMillis=50 -XX:G1HeapRegionSize=16M -XX:ParallelGCThreads=6 -XX:ConcGCThreads=2 -XX:+DisableExplicitGC` |
| `TEST-LAUNCH.bat` kept | `UseCompressedOops`, `MaxPermSize=256M`, verifier flags | unchanged |
| `optionsof.txt` `ofSmoothFps` | false | true |
| `optionsof.txt` `ofAnimatedWater` / `ofAnimatedLava` | 0 (always on) | 1 (Dynamic — E7 has no Smart Animations key) |
| `optionsof.txt` `ofChunkUpdatesDynamic` | false | true |
| `optionsof.txt` `ofConnectedTextures` | 2 (Fancy) | 1 (Fast) |
| `optionsof.txt` already good | `ofLazyChunkLoading=true`, `ofChunkLoading=1` (Smooth), `ofSmoothWorld=true`, `ofFastMath=true`, `ofDynamicLights=1` (Fast), render distance 8 | left |
| `optionsof.txt` `ofFastRender` | false | **false** (required for Sildur) |
| `journeymap.core.config` `tileHighDisplayQuality` | true | false |
| `journeymap.core.config` `mapAntialiasing` | true | false |
| JourneyMap minimap / radar | enabled, J / minimap on | left on; `alwaysMapCaves` was already false; webmap already off |
| `lycanitesmobs-spawning.cfg` FIRE/FROSTFIRE/LAVA/LUNAR/OOZE/STORM/WATER `Spawn Mob Limit` | 32 | 8 (default dump size; config itself says lower this for lag) |
| `betterfps.txt` `algorithm` | `rivens-half` | left (1.0.1 recommended default; fine on 7900X) |

Left alone on purpose: particles All, Fancy fog, default clouds/rain, mipmap 4, Sildur High, bloom 0.25, godrays 0.575, `sunFlareIntensity=0.05`, Morph off, CCC/NEI, splash cosmetics, `DefaultQuests.json`.

JAS: monster cap 70 / creature 10 is vanilla-normal. No spawn overhaul.

## Recommended but not applied

| Item | Why / risk |
|---|---|
| **Sildur Enhanced Default** (already installed) | Biggest FPS lever if Vibrant High is the bottleneck. Same OptiFine, much cheaper. Try this first if open-world FPS is still low. |
| FastCraft 1.25 | **Already installed.** 1.25 is the version Player shipped for OptiFine shaders. Keep it. Known leftover: player-shadow flicker while falling with OF E7 + shaders. Do not add another FastCraft. |
| `shadowResMul` 1.0 → 0.5 | Large shader FPS win, softer shadows. Not applied so High still looks High. |
| JourneyMap radar off / cave overlay off | Extra FPS in mob-dense areas. Minimap stays useful with radar on; turn radar off in JM options if Lycanites crowds tank FPS. |
| FoamFix 1.7.10 | Exists, but author does **not** support OptiFine. Reported HBM render bugs with OF E7. This pack has HBM. |
| Hodgepodge + UniMixins | GTNH-shaped mixin stack. Too invasive next to OptiFine E7 + FastCraft + this Forge. |
| Entity Culling 1.7.10 | Needs UniMixins; FastCraft already culls. |
| Newer AI Improvements | Tiny `AIImprovements-1.7.10-0.0.1b19-dev` is already in. Replacing it is not worth the risk. |
| ChunkPregenerator | Already installed. Use `/pregen` on a copy/new world if exploring hitch is the pain; do not leave a huge pregen running while playing. |
| G1 `UnlockExperimentalVMOptions` / NewSizePercent | Common in modern launchers; you asked to skip experimental. |
| Xmx 8G | Machine can spare it; 1.7.10 often gets worse GC past ~8G. 7G is the right band. |

## Do not do

| Action | Why |
|---|---|
| Fast Render on | Breaks Sildur / OptiFine shaders. |
| Angelica | Replaces OptiFine/shaders. Future-only, not this pack. |
| Remove FastCraft to “fix shaders” without measuring | You lose a real 1.7.10 boost; 1.25 is the coexist build. Only remove if shadow flicker is worse than the FPS gain. |
| FoamFix + this OptiFine/HBM stack | Unsupported; can make HBM structures invisible. |
| Hodgepodge / UniMixins / ArchaicFix / Neodymium | Mixin/renderer rewrites vs OptiFine E7. |
| Update CodeChickenCore or NEI | Another agent / pack pin. |
| VoidLauncher | Re-syncs and overwrites mods/config. |
| Xmx 16G on Java 8 | Old MC pause times get worse, not better. |
| Potato particles / RD 4 / clouds off | Looks worse than the FPS you would gain on a 5070 Ti. |
| Enable Morph | Leave off. |

## latest.log (this session)

- FastCraft 1.25 + OptiFine E7 + BetterFps loaded; Sildur Vibrant High selected; GPU is the 5070 Ti.
- Shader warnings are 1.8+ block IDs (beetroots, lanterns, etc.) — harmless on 1.7.10.
- No `Can't keep up`, no shader compile failure, no GC OOM. Session was boot / menu / JM palette, not a long open-world playtest.
- Pre-existing: Morph/Psychedelicraft `renderHand` patch errors (Morph stays disabled).

## Expected feel

Smoother frame pacing (G1 + Smooth FPS), less water/lava animation cost off-screen, faster connected-texture pass, lighter JourneyMap tiles, fewer Lycanites special-spawner dumps in fire/lava/water. Shaders stay Vibrant High. Not a miracle.

## How to test

1. Fully quit Minecraft (a session was open while these files were written — if video/JM settings revert, run `QuestForge-Work\_perf-20260904\REAPPLY-AFTER-QUIT.bat` after quit).
2. Launch with the Quest Forge shortcut (`TEST-LAUNCH.bat`). Do not use VoidLauncher.
3. F3 in an open Overworld biome. Note FPS / 1% lows, then look around at Lycanites density (especially near water, lava, storms).
4. Compare to your memory of before: chunk updates should hitch less; minimap should cost less; mob piles near fire/water should be smaller.
5. If Vibrant High is still the floor, switch shader pack to **Sildur's Enhanced Default** (already in `shaderpacks\`) and compare the same spot.

Backups: `QuestForge-Work\_perf-20260904\backups\`
