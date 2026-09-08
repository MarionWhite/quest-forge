# Quest Forge on this Mac — what was set up on 2026-09-04

This machine already had Rosetta and several Intel Java 8 installs, so README Steps 1–2 were skipped. Everything else from `1-Read-Me-First/README.md` was done, with one deliberate deviation noted below.

## Where the live pack now lives

```
~/Library/Application Support/PrismLauncher/instances/Quest Forge/minecraft/
```

This is the **single** working copy (8,520 files, ~2.1 GB, identical file count to `MANIFEST.txt`). Edit mods / config / quests **here**. The bundle under `3-Unpacked-Instance/` on the Desktop is now the pristine reference copy from Windows; leave it alone as a fallback.

Iteration tools stay where they are: `3-Unpacked-Instance/tools/` (splash patch scripts, hero-quest scripts, coremod source, backups).

## Verified

A scripted launch through the fallback `.command` path (same classpath and JVM args, JDK 8u162, 6144 MiB heap) was run on 2026-09-04 and reached the title screen in about 3 minutes and 20 seconds:

- Forge Mod Loader loaded 139 mods, no crash report written.
- OpenGL: Apple M1 Pro, LWJGL 2.9.4.
- Sildur's Vibrant Shaders v2.01 High loaded; `QuestForge.zip` resource pack active.
- QuestForgeTweaks coremod transform applied; OpenAL sound engine started; JourneyMap palette generated.

The Prism launch path itself has not been exercised because Prism needs an account added interactively first (see below). It uses the same Java, jar, and arguments.

## What was done

| Step | Result |
|---|---|
| Prism Launcher 11.1.0 | Installed to `/Applications` via Homebrew cask |
| Instance `Quest Forge` | Created by hand: `instance.cfg` + `mmc-pack.json` (1.7.10, Forge 10.13.4.1558, LWJGL 2.9.4-nightly) |
| Pack contents | rsync'd from the bundle into the instance `minecraft/` folder |
| Patched Forge jar (2,948,988 bytes) | Locked in as a **local library**: the jar sits in the instance's own `libraries/` folder and `patches/net.minecraftforge.json` marks the Forge library `MMC-hint: local`, so Prism never downloads it. (First attempt, pre-seeding Prism's shared `libraries/` cache, did not survive: Prism re-downloaded the stock 3,014,625-byte jar on the first launch, which produced the black splash + `BufferOverflowException` in the splash thread. The game still loaded underneath, just without the mural.) |
| Java | Instance override: `/Library/Java/JavaVirtualMachines/jdk1.8.0_162.jdk/Contents/Home/bin/java` (Oracle 8u162, x86_64). See the Java section below for why this exact build. |
| Memory | 6144 MiB max / 2048 MiB min / PermGen 256 (16 GB Mac preset) |
| JVM args | The EXTRA JVM ARGS line from `JVM-ARGS.txt`, minus `-Xmx`/`MaxPermSize` which Prism adds itself |
| Instance icon | `pack.png` copied to Prism's `icons/questforge.png` |
| Fallback launcher | `launch-questforge-mac.command` placed in the instance `minecraft/` folder and made executable. Edited to prefer the 8u162 JDK and to default to the 6144/2048 MiB heap. |
| macOS natives | `bin/natives/` now holds `liblwjgl.dylib`, `openal.dylib`, `libjinput-osx.jnilib` (x86_64) for the fallback launcher |

### Deviation from the README: LWJGL 2.9.1 → 2.9.4-nightly-20150209

The bundle shipped `lwjgl-2.9.1.jar` / `lwjgl_util-2.9.1.jar` in `bin/lib/`. LWJGL 2.9.1 misbehaves on modern macOS, which is why every launcher (Prism included) substitutes the 2.9.4 nightly for 1.7.10. The instance's `bin/lib/` now carries the 2.9.4 jars and matching natives. The original 2.9.1 jars are kept in `bin/_lwjgl-2.9.1-original-jars/` (outside the classpath). This only affects the fallback `.command` path; Prism supplies its own LWJGL regardless.

### Java: the README's "any x64 Java 8" advice is not enough on this macOS

The first test launch (Oracle 8u301) got through Forge, the coremods, and OpenGL init, then the process was killed by macOS with:

```
*** Terminating app due to uncaught exception 'NSInternalInconsistencyException',
reason: 'NSWindow geometry should only be modified on the main thread!'
  ... liblwjgl.dylib  Java_org_lwjgl_opengl_MacOSXDisplay_nSetResizable
```

This is a known LWJGL 2 problem: Minecraft 1.7.10 calls `Display.setResizable` off the main thread, and AppKit only enforces the main-thread rule for binaries linked against newer SDKs. Java 8 builds compiled with newer Xcode trigger it (Oracle/OpenJDK 8u261+, AdoptOpenJDK 8u252+, current Temurin 8). Builds compiled with older toolchains do not (Oracle 8u242 and earlier, Amazon Corretto 8). References: MinecraftForge issue 7546, AdoptOpenJDK support issue 101.

So on this Mac:

- **Use** `jdk1.8.0_162` (already installed, x86_64). The Prism instance and the fallback launcher both point at it.
- **Do not use** `jdk1.8.0_291`, `jdk1.8.0_301`, the Internet Plug-Ins JRE (8u471, which is what `java_home -v 1.8` returns), or a fresh Temurin 8 download.
- If 8u162 is ever removed, install Amazon Corretto 8 instead (`brew install --cask corretto@8`) and point Prism at it.

This is also why the README's Temurin 8 download instructions should **not** be followed on this machine.

## First launch from Prism (one thing only you can do)

1. Open **Prism Launcher** from Applications. Walk through the first-run wizard (language / theme / Java page — the Java page does not matter because the instance overrides it).
2. Prism needs an account before it will launch anything: **Accounts → Add Microsoft** and sign in. Offline play is only offered once a Microsoft account exists.
3. Select **Quest Forge** → **Launch**. The first launch downloads vanilla libraries and the Forge dependency jars (Scala, Akka, etc.). The Forge universal jar itself is already the patched one.
4. Expect: mural splash with corner emblem, branded CustomMenu title screen, `QuestForge.zip` selected, apostrophe opens the quest book, J opens the map.

If Sildur's Vibrant fails to compile on the Apple GPU: Options → Shaders → **Sildur's Enhanced Default v1.19 Fancy**. Keep Fast Render off.

## Desktop icon

`~/Desktop/Quest Forge.app` is a small app bundle (emblem icon, ad-hoc signed). Double-clicking it runs Prism's command line with `--launch "Quest Forge"`: if Prism is already open the request is forwarded to it, otherwise Prism starts and launches the instance. It replaces the Windows `Quest Forge.lnk` shortcut. It needs Prism at `/Applications/Prism Launcher.app`; if that is missing it shows an alert instead of failing silently. You can drag it to the Dock as well.

## Fallback launch without Prism

```bash
open "$HOME/Library/Application Support/PrismLauncher/instances/Quest Forge/minecraft/launch-questforge-mac.command"
```

Defaults to a 4 GB heap. For this 16 GB machine:

```bash
QF_XMX=6144M QF_XMS=2048M "$HOME/Library/Application Support/PrismLauncher/instances/Quest Forge/minecraft/launch-questforge-mac.command"
```

## If the splash is ever black again

1. Check the Forge jar Prism loaded: `PrismLauncher/instances/Quest Forge/libraries/forge-1.7.10-10.13.4.1558-1.7.10-universal.jar` must be 2,948,988 bytes and `patches/net.minecraftforge.json` must still mark it `MMC-hint: local`. If you ever click "Revert to default" on the Forge component in Prism's Version tab, that override is gone and Prism will fetch the stock jar again.
2. Check `config/splash.properties`. When the stock jar overflows on the mural, Forge silently writes `enabled=false` there. Set it back to `enabled=true`, otherwise even the patched jar shows no mural.

## Standing rules (unchanged from the README)

- Never run VoidLauncher.
- Do not update CodeChickenCore / NEI.
- `ofFastRender` stays `false`.
- Morph stays in `mods_disabled` unless testing `tools/_morph-optifine-20260904/`.
- Java 8 x64 only. The default `java` on this Mac is Homebrew OpenJDK 17 (arm64) and a Zulu 8 arm64 also exists; do not point Prism at either.
