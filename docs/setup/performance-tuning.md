# Quest Forge — performance on this Mac

Set up 2026-09-04. This covers both concerns: long load time, and low in-game FPS.

## The honest ceiling

This is a 139-mod Minecraft 1.7.10 pack (Lycanites, OreSpawn, TragicMC, HBM, the Legends superhero packs, McHeli) with Sildur shaders. Two facts cap what is possible on this machine:

1. **It runs under Rosetta 2.** Minecraft 1.7.10's Forge will not boot on any Java 8 build newer than about 8u242, and the only *native* Apple Silicon Java 8 that exists (Azul Zulu 8u442) is too new — it crashes in Forge's class patcher before the window opens. Verified on 2026-09-04: the same crash happens on a newer Intel Java 8 too, so it is the Java version, not the CPU. The pack therefore runs on Intel Java 8u162 translated by Rosetta. Native-ARM speed is not reachable without a differently patched Forge.
2. **Graphics go through OpenGL 2.1 emulated over Metal.** Old Minecraft uses a graphics API Apple no longer supports directly, so every frame is translated. Shaders make this the main bottleneck on a Mac far more than on a Windows PC with a real GPU.

So: expect smoother, cooler, and more consistent, not "modern game" framerates. Your friends on weaker *Windows* PCs may actually do better than this Mac at the same settings, because they avoid both translation layers — as long as they turn shaders off (see Low below).

## Load / compile time (~3.5 minutes to the title screen)

Where the time goes, measured from the load log:

| Phase | Time |
|---|---|
| Forge + coremod class scanning | ~25 s |
| Pre-init (all mods build their content) | ~80 s |
| Init + post-init | ~65 s |
| Texture atlas stitching + resource reload | ~45 s |

The slowest single mods are LittleMaid's model library (~40 s, much of it printing a harmless caught exception), the Legends superhero mod (~30 s, an 85 MB mod loading five hero packs and their dimensions), and McHeli (~16 s).

**This is essentially fixed cost.** 1.7.10 has no mod-load cache, so it re-does this every launch, and Rosetta roughly doubles it versus native. There is no safe setting that meaningfully cuts it while keeping the pack intact. The one real lever is content: in `config/LegendsMod.cfg` under `installed packs`, setting hero packs you do not play (`Battlebourn`, `Horror`, `Kaiju`, `Star Wars`, `Superheroes Unlimited`) to `false` cuts both load time and memory. That removes content, so it is left to you.

Do **not** try to "fix" load time by adding mixin/optimization mods (Hodgepodge, UniMixins, FoamFix, Neodymium). They fight OptiFine E7 and HBM in this pack and cause invisible blocks or crashes. This was already investigated in the Windows perf pass.

## In-game FPS: the preset switcher

The real FPS control is a three-level preset. Run it by double-clicking:

```
~/Library/Application Support/PrismLauncher/instances/Quest Forge/perf-preset.command
```

or from Terminal with `low`, `balanced`, `quality`, or `show`. It edits only performance and visual keys; your keybinds, resource pack, and quests are untouched, and it keeps a first-run backup beside itself.

| Preset | Shaders | Render dist. | FPS cap | Graphics | Use it for |
|---|---|---|---|---|---|
| **quality** | Vibrant High, full shadows | 8 | 120 | Fancy | The original look, when sitting still or taking screenshots |
| **balanced** (default now) | Enhanced Default, half-res shadows | 7 | 90 | Fancy | Everyday play on this Mac. Shaded and still pretty, roughly twice the FPS of quality here |
| **low** | Off (Fast Render on) | 6 | 60 | Fast | Weak PCs, laptops on battery, or if the Mac still stutters. The lowest spec floor |

The single biggest lever is shaders. `low` turns them off entirely and enables OptiFine's Fast Render, which is the largest jump. `balanced` keeps shaders but swaps Sildur's heavy Vibrant High for the much cheaper Enhanced Default and halves the shadow resolution.

### What changed from the Windows defaults

Applied as the new **balanced** default on this Mac:

- Shader pack Vibrant High → Enhanced Default, shadow resolution 1.0 → 0.5.
- FPS cap 260 → 90. The old cap let the GPU run flat-out and cook the laptop, which throttles it and *lowers* sustained FPS. Capping keeps it cool and steady.
- Particles All → Decreased. "All" was the heaviest setting.
- Render distance 8 → 7, mipmaps 4 → 2, clouds and rain to their fast variants.

`ofFastRender` stays **false** whenever shaders are on (quality and balanced) — it breaks Sildur. `low` is the only preset that turns it on, and it turns shaders off in the same step. The switcher keeps those two in sync automatically, so never toggle Fast Render by hand in the OptiFine menu.

## For your friends

Tell friends on weaker machines to run the pack at **low**. On a weak PC the shaders, not the mod count, are what kills FPS, and low removes them. If they have a mid-range PC they can try balanced. The load time will be long for everyone — that is the pack, not their hardware.

## Backups

- `minecraft/_perf-backup-<timestamp>/` — the settings exactly as they arrived from Windows (quality-level).
- `_perf-preset-firstrun-backup/` next to the switcher — the same, saved the first time you switched.

To get the original look back at any time, run the switcher and choose `quality`.
