# Joining the Quest Forge server

This is the guide for players. The short version: install Java 8, install Prism
Launcher, run the Quest Forge installer, sign in, launch, add the server. The
installer does the fiddly part (finding Java, setting the memory, putting the
pack where Prism looks). The manual steps are at the end, if the installer
cannot run on your PC.

Quest Forge runs on **Windows** (the tested path) and on a **Mac** (with
Rosetta, and smoother than fast). You need a **Minecraft: Java Edition** account
on a Microsoft account. The server checks every login with Mojang, so nobody can
join under your name.

## What you need

- A PC with 8 GB of RAM (16 GB is comfortable) and about 3 GB free on disk.
- Java 8, 64-bit (Windows) or Intel x86_64 (Mac). Not Java 11, 17, 21 or 25, and
  not a 32-bit Java. The installer checks for it.
- Prism Launcher, from [prismlauncher.org](https://prismlauncher.org).
- Your Microsoft account, signed in once in Prism.
- Thirty minutes. The first launch takes two to four minutes to reach the title
  screen: that is the pack loading 140 mods, not a slow PC.

## 1. Java 8

**Windows.** Open [adoptium.net](https://adoptium.net), choose version 8, Windows,
x64. Download the `.msi` and run it with the defaults. Either the JRE or the JDK
is fine.

**Mac.** Install Rosetta 2 first, in Terminal:

```
softwareupdate --install-rosetta --agree-to-license
```

Then download Temurin 8 for macOS **x64** (the `.pkg` whose name contains `x64`)
from adoptium.net, and install it. An `aarch64` Java 8 will not run the pack.

Keep any newer Java you already have. Prism picks a Java for each instance. The
installer checks for Java 8 and tells you what is missing; it does not install Java.

## 2. Prism Launcher

Install Prism from [prismlauncher.org](https://prismlauncher.org) and open it
once. Under **Accounts** (top right), add your Microsoft account and sign in.

## 3. Run the installer

The installer is attached to the newest **client instance** release on the
[releases page](https://github.com/MarionWhite/quest-forge/releases). Download
the one for your system:

- **Windows:** `Install-QuestForge.ps1`. Right-click it and choose
  **Run with PowerShell**. If Windows warns about it, run this in PowerShell
  instead, from the folder you saved it in:

  ```
  powershell -ExecutionPolicy Bypass -File .\Install-QuestForge.ps1
  ```

- **Mac:** `install-questforge.command`. Double-click it. The first time, macOS
  may refuse it because it came from the internet: right-click it, choose
  **Open**, then **Open** again. Or, in Terminal, from the Downloads folder:

  ```
  bash install-questforge.command
  ```

The installer:

1. finds Prism's folder and a Java 8,
2. reads your RAM and picks the memory for it,
3. on a first install, asks which kind of PC this is (normal, lite or potato; see step 6),
4. downloads the newest release and checks every file against its checksum,
5. puts the pack in Prism as **Quest Forge**.

It stops, before it changes anything, if Java is missing, if the download does
not match its checksum, or if Prism or the game is open. The message says what to
do. Close Prism and the game, and run it again.

Want to see what it would do first? Add `-WhatIf` (Windows) or `--dry-run` (Mac).
It changes nothing.

Want the OptiFine edition with the Angelica renderer instead? Add
`-Edition angelica` (Windows) or `--edition angelica` (Mac). Angelica needs an
OpenGL 3.3 graphics card (nearly anything since 2012) and runs shaders faster.
Your friends on the same server can use either edition.

## 4. Launch and join

1. In Prism, click **Quest Forge**, then **Launch**. Wait two to four minutes for
   the title screen. The loading screen shows the Quest Forge mural with textured
   bars; the top-right of the title screen shows the pack version and a
   fingerprint. The server compares both.
2. **Multiplayer**, **Add Server**. Paste the address the host gave you.
3. Ask the host to whitelist your exact Minecraft name. The whitelist is by
   account, so a typo means "You are not white-listed".

The first join takes a while as the world arrives. The website's "Your first
night" page says what to do once you are in.

## 5. Updating

When the host announces a new release, run the installer again. It keeps your
saves, screenshots, options, server list, JourneyMap data and your own resource
and shader packs. It replaces the mods and the config, and keeps the old copies
in `_qf-backups\` inside the instance, in a folder named by date and time.

Do not update a single mod by hand. The server refuses one differing jar.

## 6. Pick a profile

The installer asks which PC this is. The profile changes how much work your PC
does per frame. It does not change the world, the mobs, the items or the quests,
and it never gets you refused.

| Your PC | Profile | What it does |
|---|---|---|
| A gaming PC from the last five years, 16 GB+ | **normal** | Plays as released. Shaders are optional. |
| GTX 1060 / RX 580 class, 4 to 6 cores, 8 to 16 GB | **lite** | Shaders off, a smaller view, a few cosmetic mods set aside (gore, cave reverb, the branded menu). |
| A laptop or integrated graphics, 8 GB | **potato** | Lite, plus the minimap and the mob health bar set aside. |

On a Windows PC, lite and potato use `apply-lite.ps1` and set the mods aside
(they are kept in `mods-lite-removed\`, not deleted). On a Mac they use the
`perf-preset.command low` preset, which edits the video settings only.

To go back to normal later, on Windows run `apply-lite.ps1 -Undo` from the
`questforge-tools\lite-client` folder in the instance (its README,
[`tools/lite-client/README.md`](../../tools/lite-client/README.md), has the exact
command). It puts your settings and mods back. Running the installer again does
not undo a profile: the installer keeps the profile the instance is on.

## Things to know

- **Shaders.** With any shader on, **Fast Render must stay off**, or the screen
  goes black. On the Angelica edition, F8 picks a shader pack and F4 turns it on
  or off.
- **Memory.** The installer sets the memory from your RAM. More is not better:
  the whole pack lives in about 1.3 GB of heap, and a bigger heap only makes the
  pauses longer. On an 8 GB PC, anything over 3 GB makes Windows swap.
- **Don't** install Java 17 or 21 to fix a Java error; this Minecraft needs Java 8.
- **Don't** let another launcher "repair" the instance. It puts stock jars back,
  and the loading screen goes black.
- **Don't** delete `minecraft\assets\mcheli`. The helicopters and planes live there.
- **If the server refuses you**, the screen says why. The
  [refusal list](why-was-i-refused.md) says what to do for each message.
- **When you ask the host for help,** send `minecraft\logs\latest.log`, not a
  screenshot. The refusal text is in it.

## If the installer cannot run

The manual steps do the same thing by hand. Use them only if the installer will
not run. The release zip (`QuestForge-client-instance-optifine.zip` or
`...-angelica.zip`) is the same either way; download it and its `.sha1` from the
releases page.

1. **Get the zip.** It is a complete Prism instance.
2. **Put it in Prism.** In Prism, click **Folders** on the toolbar, then **View
   Instance Folder**. Extract the zip there, so a `Quest Forge` folder sits next
   to the others. Restart Prism. Don't launch it yet. Prism downloads Minecraft's
   own files and the native libraries on the first launch; the zip leaves them
   out on purpose.
3. **Java.** Right-click **Quest Forge**, **Edit**, **Settings**, **Java**. Tick
   **Java installation**, click **Auto-detect**, and pick the one whose version
   starts with `1.8` (on a Mac, the one that says `x86_64`).
4. **Memory.** Tick **Memory**. Set the maximum from your installed RAM:

   | Installed RAM | Minimum | Maximum (Windows) | Maximum (Mac) |
   |---|---|---|---|
   | 8 GB | 1024 MiB | 3072 MiB | 4096 MiB |
   | 12 GB | 1024 MiB | 4096 MiB | 6144 MiB |
   | 16 GB | 2048 MiB | 5120 MiB | 6144 MiB |
   | 32 GB or more | 2048 MiB | 6144 MiB | 6144 MiB |

5. **Java arguments.** Tick **Java arguments** and paste this as one line:

   ```
   -XX:+UseG1GC -XX:MaxGCPauseMillis=50 -XX:G1HeapRegionSize=16M -XX:+ParallelRefProcEnabled -XX:+DisableExplicitGC -XX:+UseCompressedOops -XX:MaxPermSize=256M -XX:+UseSplitVerifier -XX:+FailOverToOldVerifier -XX:-HeapDumpOnOutOfMemoryError -Djava.net.preferIPv4Stack=true -Dfml.ignoreInvalidMinecraftCertificates=true -Dfml.ignorePatchDiscrepancies=true -Dlog4j2.formatMsgNoLookups=true
   ```

   The two `-Dfml.ignore` flags are required: the pack's Forge jar is patched.
6. **Profile (optional).** For a weaker PC, see the Windows lite instructions in
   [`tools/lite-client/README.md`](../../tools/lite-client/README.md). On a Mac,
   run `perf-preset.command low` in the instance folder from Terminal.
7. Launch, and join as in step 4.

The installer does steps 2 to 6 for you, and checks the files against their
checksums on the way. Doing it by hand skips that check.
