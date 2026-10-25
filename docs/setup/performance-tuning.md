# Performance tuning: which profile for which PC

Updated 2026-10-25 for the Angelica client. The owner's PC (7900X / RTX 5070 Ti)
is not the floor: friends on ordinary PCs play the same content with lighter
visuals. The levers are three **client profiles** (full, lite, potato), the
QuestForge shader pack's five **presets**, and the **Java heap**. None of them
changes content: every setting is client-side video, HUD or audio, and every
mod a profile sets aside is one the server never had.

The profiles live in [`tools/lite-client/profiles/`](../../tools/lite-client/profiles/)
as JSON (one `why` line per setting) and are applied by
[`tools/lite-client/apply-profile.ps1`](../../tools/lite-client/apply-profile.ps1)
([README](../../tools/lite-client/README.md)).

## The short version

| Your PC | Profile | Shader preset | Resolution | Java max heap |
|---|---|---|---|---|
| Gaming PC from the last ~5 years (RTX 3060 / RX 6600 or better, 16 GB+) | **full** | QuestForge **Medium** (High at 1440p on an RTX 3060+; Ultra is the dev PC) | 1080p–1440p | 5 GB (16 GB RAM), 6 GB (32 GB) |
| GTX 1060 6 GB / RX 580, 4–6 cores, 8–16 GB | **lite** | QuestForge **Low** | 1080p | 3 GB (8 GB RAM), 4 GB (12–16 GB) |
| Integrated graphics of the Iris Xe / Vega 8 class, 8 GB | **potato** | QuestForge **Potato** | 720p | 3 GB |
| Older integrated graphics (Intel UHD 620 and down) | **potato**, `-Shaders off` | none | 720p | 3 GB |
| No OpenGL 3.3 (Intel HD 2000/3000) | OptiFine E7 client, lite or potato | none | 720p–1080p | 3 GB |

Presets are selectable in game too: F8 → QuestForge → Profile. A friend who
only installs the pack lands on Medium (the pack default), never on Ultra.

## How to apply

Windows, with the game closed, from the repo's `tools\lite-client` folder:

```
powershell -ExecutionPolicy Bypass -File apply-profile.ps1 -Instance "<game folder>" -Profile lite
powershell -ExecutionPolicy Bypass -File apply-profile.ps1 -Instance "<game folder>" -Profile potato -Shaders off
powershell -ExecutionPolicy Bypass -File apply-profile.ps1 -Instance "<game folder>" -Status
powershell -ExecutionPolicy Bypass -File apply-profile.ps1 -Instance "<game folder>" -Revert
```

`<game folder>` is the folder with `mods\` and `options.txt` (Prism: right-click
the instance → Folder → `.minecraft`). Add `-WhatIf` to see the changes first.
The script is idempotent, backs up every file it touches
(`_qf-profile\original\` once, `_qf-profile\backup-<time>\` per run) and moves
jars to `mods-aside\`, never deletes. It ends by printing the Java memory and
arguments for the PC it runs on; set them in Prism (Edit instance → Settings →
Java). On the Mac the JSON files are the spec for the Prism tooling; the README
maps each section to its file.

## What each profile gives up

| | Full | Lite | Potato |
|---|---|---|---|
| Shader | QuestForge Medium: shadows to 80 blocks with entities, TAA, SSR, GTAO, soft shadows, bloom | QuestForge Low: sky, own shadow to 48 blocks, water, TAA, bloom; no volumetric clouds or light, no SSR, no GTAO, no puddles, hard shadows | QuestForge Potato: sky, water, exposure and colour only; no shadow pass, no TAA (FXAA-class), no bloom |
| Render distance | 8 | 6 (= the server's view-distance; free there) | 5 |
| Graphics | Fancy | Fast: opaque leaves, no blob shadows | Fast |
| Smooth lighting | on | on | off (flat light indoors: the one change you notice) |
| Particles / mipmaps | All / 4 | Decreased / 2 | Minimal / 1 |
| Biome blend, grass sides, texture filter | 3 fancy, overlay, RGSS+AF | 1 fast, plain, AF | none, plain, none |
| Dynamic lights (held torch) | on | off | off |
| Max FPS, FPS reducer | 120, off | 90, 10 unfocused / 30 idle | 60, 10 / 20 |
| Mods aside | none | SoundFilters, MobDismemberment, MobAmputation, CustomMenu | + JourneyMap, DamageIndicators |
| Java heap (8 / 12 / 16 / 32 GB RAM) | 3 / 4 / 5 / 6 GB | 3 / 4 / 4 / 4 | 3 / 3.5 / 4 / 4 |

The why of every row is in the JSON. Two things that are *not* settings any
more: OptiFine's Smooth FPS, Fast Render and Fast Math do not exist under
Angelica (its renderer is faster with shaders off than E7 with Fast Render on),
and `optionsof.txt` is ignored there.

## Measured

Pending: one FrameBench cycle on the dev PC (RTX 5070 Ti), a slim Angelica
trial (base set + qf-content debug build + Twilight Forest), the static, fly and
torch scenes, each profile at its target resolution, shaders on at the profile's
preset. From the repo, as a background task, only when `trial.py status` shows
no client:

```
py -3.10 -I tools/trial/trial.py build liteprof --renderer angelica qfcontent twilightforest --jar C:\qfb\shaderdev\jars\QuestForgeContent-1.0.0.jar --shaderpack shaders/QuestForge --shader QuestForge --world C:\qfb\world-master --force
rem per profile p in full (2560x1440), lite (1920x1080), potato (1280x720):
powershell -ExecutionPolicy Bypass -File tools\lite-client\apply-profile.ps1 -Instance %APPDATA%\.qf-trials\liteprof -Profile p
rem then set maxFps:260 in the trial's options.txt (measurement only) and
py -3.10 -I tools/trial/trial.py launch liteprof --size WxH --xmx 3G -D qf.bench=1 -D qf.bench.tag=prof_p -D qf.bench.scenes=static,fly,torch -D fml.queryResult=confirm
rem result: %APPDATA%\.qf-trials\liteprof\bench\prof_p.txt
```

## What the numbers mean for a friend's PC

The dev PC's GPU is 5–6× a GTX 1060 and 15× an Iris Xe in raster throughput
(ratios from 3DMark-class numbers, not measured here), and its CPU drives the
frame at these resolutions. So read the table above as: the *shader cost* (the
profile's frame time minus shaders off at the same resolution) scales roughly
by those ratios on the friend's GPU, while the chunk and entity work scales
with their CPU's single-thread speed. Nobody has run friend-class hardware yet;
the budgets in [`../design/shaders/performance-rules.md`](../design/shaders/performance-rules.md)
(Low: ≥ 60 fps mean on a GTX 1060 at 1080p; Potato: ≥ 40 fps on Iris Xe at
720p) are the targets a real run has to confirm or refute. When a friend can,
the F3 frame rate in the same spot at full and at lite is the single most useful
number to send back.

## The honest ceiling: load time

This is a 110-odd-mod 1.7.10 pack (Lycanites, OreSpawn, TragicMC, HBM, the
Legends packs, MCHeli). Loading takes 84 s on the dev PC and 2–4 minutes on a
4-core CPU, every launch, in every profile: 1.7.10 has no mod-load cache, and
the three heavy mods (Decocraft, MCHeli, Legends) build every model at
start-up. No profile setting cuts it. The only lever that would is content
(fewer Legends hero packs), so it is left to the player.

Do not add mixin or optimisation mods (Hodgepodge, ArchaicFix, FoamFix,
Neodymium) to a client: Hodgepodge and ArchaicFix change the login packets so
the client can only join a server that runs them too
([`angelica-client.md`](angelica-client.md)), and FoamFix breaks HBM-style
renderers on E7.

## The Mac (E7-era notes, 2026-09-04)

The pack on an Apple Silicon Mac runs the OptiFine E7 client under Rosetta 2
(Forge 1.7.10 boots only on Java 8 ≤ 8u242, and no native-ARM build that old
exists) with OpenGL 2.1 emulated over Metal, so every frame is translated and
shaders cost far more than on a Windows PC with a real GPU. Expect smoother and
cooler, not "modern game" frame rates; a friend on a weak Windows PC may do
better than the Mac at the same settings. The Mac's `perf-preset.command`
(quality / balanced / low) predates Angelica and the QuestForge pack; its `low`
is this doc's lite with shaders off on E7. Angelica on the Mac is untested.
Java memory for the Mac: [`jvm-args.md`](jvm-args.md).

## Troubleshooting

- **Stutter every few seconds with the disk light on:** swapping. Lower the Java
  maximum; on 8 GB never above 3 GB. Close the browser and Discord's overlay.
- **Out of memory:** raise the maximum by 512 MB, but on 8 GB stay at or under 3.5 GB.
- **Every frame is exactly 4.16 ms / 240 fps, or 16.7 ms / 60 fps:** vsync is
  on. `vsync_mode` in `config\angelica-options.json` must be `OFF` (every profile
  sets it); the `maxFps` cap does the pacing.
- **The shader looks like the full pack on lite:** F8 → QuestForge → Profile
  should say LOW (POTATO). `apply-profile.ps1 -Status` prints the `QF_PRESET` it wrote.
- **Shaders off although lite was applied:** the QuestForge pack is not in
  `shaderpacks\`; lite and potato then turn shaders off on purpose. Install the
  pack and re-apply.
