# QuestForge Content — mod dev workspace

A Forge 1.7.10 mod development workspace for the Quest Forge modpack, set up to
work on this M1 Mac.

## The three Javas

This is the part that trips everyone up. Three different JVMs do three different
jobs, and mixing them up is where the confusing crashes come from:

| Role | JVM | Why this one |
|---|---|---|
| Runs Gradle | Homebrew `openjdk@25` (arm64) | RetroFuturaGradle 2.0.3 is compiled for Java 25; a JDK 17 fails with `UnsupportedClassVersionError: class file version 69.0` |
| Compiles the mod | Zulu 8u442 (arm64) | Mod must be Java 8 bytecode. Azul is the only vendor shipping a Java 8 JDK for macOS arm64 |
| Runs `./gradlew runClient` | Zulu 8u442 (arm64) — same one | RFG ships **arm64** LWJGL natives into `run/natives/lwjgl2`. Forcing an x86_64 JVM here dies with `UnsatisfiedLinkError: liblwjgl.dylib (have 'arm64', need 'x86_64')` |
| Runs the pack in Prism | Oracle 8u162 (x86_64, Rosetta) | The packed instance has x86_64 LWJGL natives, and Forge 1.7.10 NPEs in `ClassPatchManager` on Java 8 newer than ~8u242 |

The last two rows are the surprising part: **the dev client and the real pack run
on different JVMs and different architectures.** That is fine and expected. RFG
patches Minecraft at build time, so the runtime `ClassPatchManager` path that
breaks the packed instance on newer Java 8 is never exercised in `runClient`.
Verified working — a `runClient` on arm64 Zulu 8 reaches the main menu and logs
`Forge Mod Loader has successfully loaded 4 mods`.

The consequence for you: `runClient` succeeding is *not* proof the pack will
load it. Only `install-to-prism.command` plus a real Prism launch proves that.

Everything is pinned in the build — `org.gradle.java.home` and the toolchain
paths in `gradle.properties`, the toolchain block in `build.gradle.kts`. Nothing
needs setting by hand, and the system default `java` (17) is left alone.
`openjdk@25` is keg-only, so it is not on `PATH` and cannot confuse Prism's Java
detection.

Toolchain auto-detection is deliberately **off**, with exactly two JDKs declared
in `gradle.properties`. This machine has six Java 8 installs, three of them
Oracle 8, and auto-detection made "Java 8 from Oracle" ambiguous between 8u162
(works) and 8u291/8u301 (crash). If you add a JDK and Gradle cannot see it, that
setting is why.

## Status: verified working end to end

- `./gradlew build` produces a Java 8 reobfuscated jar.
- `./gradlew runClient` reaches the main menu with the mod loaded.
- **Installed into the real pack, it loads.** Prism launch on 2026-09-05 reported
  `Forge Mod Loader has successfully loaded 140 mods`, with
  `[qfcontent]: QuestForge Content loaded.` and no ID conflicts — block and item
  ID maps froze cleanly alongside the other 113 mods.

## Commands

```bash
./gradlew build          # compile + reobfuscate -> build/libs/
./gradlew runClient      # dev client: this mod + NEI, nothing else (~40s)
./gradlew --stop         # kill a stuck daemon
./install-to-prism.command   # build, then drop the jar into the Prism instance
```

### Where to test

**Default to `runClient`** — ~40 seconds, versus ~3.5 minutes for a full pack
launch. That is the iteration loop.

But it only has this mod and NEI, so it cannot catch:

- enchantment ID collisions with the pack's other 113 mods
- whether an enchantment applies correctly to *modded* weapons and armor
- conflicts with the pack's other coremods

Do a `./install-to-prism.command` plus a real launch at milestones, not never.
The coremod half in particular behaves differently in the two environments: the
dev client loads it from `-Dfml.coreMods.load`, the pack from the jar manifest.

See **[COOKBOOK.md](COOKBOOK.md)** for how to actually write 1.7.10 content —
items, blocks, recipes, events, config, tile entities, commands. Worth reading
before your first change: essentially every Forge tutorial online targets 1.12+,
where blocks use `BlockPos`/`IBlockState` and models are JSON. None of it
compiles here.

The first `build` downloads and decompiles Minecraft (several minutes, ~1 GB into
`~/.gradle/caches/retro_futura_gradle`). After that it is fast and offline.

`runClient` launches a bare Forge instance with only this mod — it is for fast
iteration, *not* a test of pack compatibility. For that, use
`install-to-prism.command` and launch Quest Forge normally.

## Layout

```
src/main/java/com/questforge/content/
  QuestForgeContent.java   @Mod entry point, lifecycle events
  CommonProxy.java         shared setup
  ClientProxy.java         client-only setup (renderers, models, keybinds)
  ModItems.java            item registration
  ModBlocks.java           block registration
  ModRecipes.java          crafting recipes
  ModCreativeTab.java      the creative tab everything appears under

src/main/resources/
  mcmod.info                              mod metadata shown in the mods list
  assets/qfcontent/lang/en_US.lang        display names
  assets/qfcontent/textures/items/        16x16 item textures
  assets/qfcontent/textures/blocks/       16x16 block textures

src/test/java/com/questforge/content/
  CookbookExamples.java    every COOKBOOK.md snippet as real code, so the
                           compiler checks the API signatures. Compiled by
                           `build`, never shipped in the jar. There are no
                           JUnit tests -- hence failOnNoDiscoveredTests=false.
```

`Tags.VERSION` is generated at build time from the `version` in
`build.gradle.kts` — it is not a file you edit.

## Adding content

The pattern for a new item: construct it in `ModItems.register()`, give it a
`setTextureName("qfcontent:your_item")`, call `GameRegistry.registerItem`, add a
16x16 PNG at `textures/items/your_item.png`, and add an
`item.your_item.name=Your Item` line to `en_US.lang`. Blocks are the same shape
via `ModBlocks`.

**Registry names are permanent.** Once a world has saved with
`qfcontent:forge_shard` in it, renaming that item orphans every copy in every
chest. Rename freely before you play with it, not after.

## Installing into the pack — read before the first time

The instance already has **113 mods** and **existing worlds** (`Here We Go`,
`Tryhard Run`, `Quest Test`). Two things follow:

1. **Test on a throwaway world first.** `Quest Test` looks like the right one.
   Adding blocks/items to a world is safe — Forge assigns free IDs and records
   them in `level.dat` — but *removing* the mod afterwards makes Forge prompt
   about missing registry entries, and confirming that deletes those blocks
   from the world.
2. **Back up before installing into a world you care about.** The pack's own
   backups live in `minecraft/_qf-backups/`; `install-to-prism.command` puts a
   copy of any jar it replaces there too.

The pack runs Forge **10.13.4.1558**. RetroFuturaGradle builds against its own
1.7.10 Forge version, which is normal practice and fine for ordinary block/item/
recipe APIs — but it is the first thing to suspect if something works in
`runClient` and not in the pack.

## Relationship to QuestForgeTweaks

`QuestForgeTweaks-1.0.jar` in the pack is a different kind of thing: a **coremod**
that rewrites other classes' bytecode with ASM (splash music, quest button). It
is built by plain `javac` against the instance jars, from
`QuestForge-Transfer/3-Unpacked-Instance/tools/questforge-coremod/`, and needs no
Gradle. Keep the two separate — this workspace is for *adding* content, that one
is for *changing* existing behaviour.
