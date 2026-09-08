# Quest Forge on an M1 MacBook Pro

This is the only guide you need. You do **not** need Homebrew, Cursor, a USB stick, iCloud, or any Windows username. You do **not** need to have used Terminal before — when a step uses it, the exact text to paste is written out.

**Do not use VoidLauncher** on this Mac (or on the Windows PC). It restores stock jars and **breaks the splash mural**. Launch from **Prism Launcher** only.

This pack is Minecraft **1.7.10** + Forge **10.13.4.1558**. It will **not** run on Java 17 or Java 21.

---

## What you should have in front of you

A folder named `QuestForge-Mac-Migrate` (this bundle). Inside it:

| Item | What it is |
|---|---|
| `START-HERE.txt` | Pointer to this file |
| `docs/README.md` | This guide |
| `docs/JVM-ARGS.txt` | Copy-paste Java settings |
| `minecraft/` | The playable pack + your worlds |
| `tools/` | Optional iterate/branding files (not needed to play) |
| `launch-questforge-mac.command` | Emergency fallback only — **prefer Prism** |
| `MANIFEST.txt` | What was copied / skipped |

If you received a file named `QuestForge-Mac-Migrate.zip`, double-click it in Finder to unzip, then open the folder it creates.

---

## Big picture (so the steps make sense)

This Mac is **Apple Silicon (M1)**. The Java this pack needs is **Intel-only Java 8**. Those two facts mean:

1. Install **Rosetta 2** (Apple’s Intel translator).
2. Install **Temurin Java 8 x64** (Intel), **not** the aarch64 / ARM build, **not** Java 17/21.
3. Install **Prism Launcher** (Apple Silicon / universal is fine).
4. Let Prism create a **1.7.10 + Forge 1558** instance and launch it **once** so it downloads **macOS** game natives.
5. Copy **this bundle’s `minecraft` folder contents** into that instance (merge — do not delete Prism’s natives).
6. Overlay the **patched Forge jar** (required for the splash mural).
7. Paste JVM args. Launch from Prism. Play.

---

# Step 1 — Enable Rosetta 2

Java 8 for this pack is Intel-only. On an M1 Mac it will not start until Rosetta is installed.

1. Open **Spotlight**: press **Command (⌘) + Space**.
2. Type `Terminal` and press **Return**. A window with a prompt appears.
3. Copy this **entire** line, paste it into Terminal, press Return:

```bash
softwareupdate --install-rosetta --agree-to-license
```

4. Wait. It may ask for your Mac password (the one you use to log in). Type it — characters will not show — and press Return.

**Success looks like:** Terminal prints that Rosetta was installed, or that it is already installed. Either is fine. You can close Terminal.

If you see a license prompt instead of finishing automatically, run this instead (no `--agree-to-license`) and click Agree:

```bash
softwareupdate --install-rosetta
```

---

# Step 2 — Install Temurin 8 (x64 / Intel) — not ARM, not Java 17/21

## 2a. Download the correct installer

Use **one** of these. The first is a ready-made filter. The second is a direct file.

**Option A — pick it on the website (harder to get wrong):**

1. Open Safari (or any browser).
2. Go to:  
   **https://adoptium.net/temurin/releases/?version=8&os=mac&arch=x64&package=jdk**
3. Confirm these filters before you download:
   - Version: **8**
   - Operating System: **macOS**
   - Architecture: **x64**  ← **not aarch64, not ARM**
   - Package: **JDK**
4. Download the **`.pkg`** (installer). The file name must look like:

   `OpenJDK8U-jdk_x64_mac_hotspot_8u504b01.pkg`

   The `8u504` part may be a newer 8u-number. That is fine.  
   **`x64` must be in the name. `aarch64` is the wrong file.**

**Option B — direct file (Eclipse Temurin 8u504, x64 macOS .pkg):**

https://github.com/adoptium/temurin8-binaries/releases/download/jdk8u504-b01/OpenJDK8U-jdk_x64_mac_hotspot_8u504b01.pkg

All Temurin 8 mac builds: https://github.com/adoptium/temurin8-binaries/releases

**Wrong downloads (do not use):**

| File name contains… | Why it is wrong |
|---|---|
| `aarch64` | ARM Java. You will get “wrong architecture”. |
| `x64_windows` | Windows. Will not install on a Mac. |
| Java **11 / 17 / 21 / 25** | Forge 1.7.10 will not run. |
| Homebrew `openjdk` / `java` with no `@8` | Almost always 17 or newer. |

You do **not** need Homebrew for this.

## 2b. Run the installer

1. In **Downloads**, double-click the `.pkg`.
2. Click through **Continue → Continue → Install**.
3. Enter your Mac password if asked.
4. Click **Close** when it says the installation was successful.

**Success looks like:** a standard macOS “Install Succeeded” dialog. Nothing Minecraft-related appears yet. That is normal.

## 2c. Verify in Terminal (required)

1. Open **Terminal** again (⌘ + Space, type `Terminal`, Return).
2. Paste this, press Return:

```bash
/usr/libexec/java_home -V
```

**Success looks like:** a list of installed Javas. One line must mention **1.8** or **8** (for example `1.8.0_504`). If the only lines are 11, 17, 21, or 25, you installed the wrong Java — go back to 2a.

3. Paste this, press Return:

```bash
/usr/libexec/java_home -v 1.8
```

**Success looks like:** one path, similar to:

`/Library/Java/JavaVirtualMachines/temurin-8.jdk/Contents/Home`

Copy that path. You will paste it into Prism later. If this command errors with “Unable to find any JVMs matching version 1.8”, Java 8 is not installed.

4. Paste this, press Return:

```bash
java -version
```

**Success looks like:** the first line contains **`1.8.0_`** something, for example:

```
openjdk version "1.8.0_504"
OpenJDK Runtime Environment (Temurin)(build 1.8.0_504-b01)
OpenJDK 64-Bit Server VM (Temurin)(build 25.504-b01, mixed mode)
```

- If you see `17.`, `21.`, or `25.`, the Mac’s default Java is too new. Prism can still work if you **point Prism at the 1.8 path from step 3**. Do not “fix” this by installing another modern Java.
- If you see `aarch64` or an error about **wrong architecture**, you installed the ARM `.pkg`. Uninstall it (below) and install the **x64** `.pkg`.

Optional extra check (the word **x86_64** must appear, not **arm64**):

```bash
file "$(/usr/libexec/java_home -v 1.8)/bin/java"
```

**Success looks like:** `Mach-O 64-bit executable x86_64`

To remove a wrong Temurin install: open **Finder → Go → Go to Folder…** (⇧⌘G) → paste `/Library/Java/JavaVirtualMachines` → move the wrong `.jdk` folder to Trash (password required). Then install the x64 `.pkg`.

---

# Step 3 — Install Prism Launcher

Prism is the launcher. A **universal / Apple Silicon** Prism is correct. Prism itself does not need to be Intel. Only **Java 8** must be Intel (x64).

1. Open: **https://prismlauncher.org/download/macos/**
2. Download **Universal (.zip)** (or the `.dmg` if that is what the page shows).
3. If you got a `.zip`, double-click it. Drag **Prism Launcher** into **Applications**.
4. If you got a `.dmg`, open it and drag **Prism Launcher** into **Applications**.
5. Open **Applications** and double-click **Prism Launcher**.
6. If macOS says it cannot be opened (Gatekeeper):
   - **System Settings → Privacy & Security** → scroll to the message → **Open Anyway**,  
   - or Right-click Prism Launcher → **Open** → **Open**.

Direct files (Prism 11.0.3; a newer 11.x on the site is also fine):

- https://github.com/PrismLauncher/PrismLauncher/releases/download/11.0.3/PrismLauncher-macOS-11.0.3.zip
- https://github.com/PrismLauncher/PrismLauncher/releases/download/11.0.3/PrismLauncher-macOS-11.0.3.dmg
- All versions: https://github.com/PrismLauncher/PrismLauncher/releases/latest

On first run, Prism may ask you to sign in to a Microsoft account. You can:

- Sign in if you have one (normal), or
- Use **offline** play if Prism offers it (this pack was played offline on Windows as user `Dev`).

**Success looks like:** Prism’s main window, with a list of instances (probably empty) and an **Add Instance** / plus button.

You do **not** need Homebrew (`brew install --cask prismlauncher` is optional and not required).

---

# Step 4 — Create a 1.7.10 + Forge 1558 instance, then launch ONCE

This first launch is **not** Quest Forge yet. It exists so Prism downloads **macOS LWJGL natives**. If you skip it and only copy folders, the game will crash with `UnsatisfiedLinkError`.

1. In Prism, click **Add Instance** (plus button).
2. Name it exactly: `Quest Forge`
3. Version / group: **Vanilla** is fine.
4. Minecraft version: **1.7.10**  
   (type `1.7.10` in the filter if the list is long.)
5. Install **Forge**:
   - In the same create dialog, if you see a **Loader** or **Forge** checkbox, enable Forge.
   - Forge version: **10.13.4.1558**  
     If the create dialog has no Forge picker: create the instance as 1.7.10 first, then **right-click `Quest Forge` → Edit → Version** (or **Loader**) → **Install Forge** → pick **10.13.4.1558**.
6. Create / OK. Do **not** add extra mods. Do **not** copy this bundle yet.
7. Select **Quest Forge** and click **Launch**.
8. Wait through the Mojang / Forge loading screen. When you reach the **Minecraft title screen** (Singleplayer / Multiplayer), **Quit** the game. Then you can close Prism or leave it open.

**Success looks like:** the vanilla/Forge title screen appeared and you quit without a crash. Prism now has macOS natives for 1.7.10. The splash will still be the **stock** Forge splash. That is expected — you have not copied the pack yet.

If launch fails here, stop. Fix Java (Step 2) or Forge version (must be **1558**) before copying files.

---

# Step 5 — Find the instance `minecraft` folder

Prism on a Mac typically stores instances here:

```
/Users/YOUR-MAC-USERNAME/Library/Application Support/PrismLauncher/instances/Quest Forge/minecraft/
```

`YOUR-MAC-USERNAME` is whatever account you log into this Mac with. You do **not** need to guess it. Use Prism to open the folder:

**Easiest (use this):**

1. In Prism’s instance list, **right-click** `Quest Forge`.
2. Click **Folder** (sometimes **Open Folder**, **Browse**, or **View Folder**).
3. Finder opens the **instance** folder. You should see a folder named **`minecraft`** (some older layouts use `.minecraft`).
4. Double-click **`minecraft`**. This is the destination you will copy into.

**If there is no Folder item:**

1. Right-click `Quest Forge` → **Edit**.
2. Look for a folder icon or **Open instance folder**.

**If you must type it:** Finder → **Go → Go to Folder…** (⇧⌘G) → paste:

```
~/Library/Application Support/PrismLauncher/instances
```

Then open `Quest Forge` → `minecraft`.

**Success looks like:** a Finder window showing folders such as `mods` (maybe empty or nearly empty), `config`, `saves`, and possibly `assets`. There may be a `natives` folder **next to** `minecraft` (in the instance folder) or inside it. **Do not delete any `natives` folder.** This bundle does **not** include Windows `.dll` natives.

---

# Step 6 — Copy this bundle’s `minecraft` contents into Prism

You are **merging**. You are **not** replacing the whole Prism instance. You must **not** delete Prism’s natives.

1. Open a **second** Finder window.
2. Go to this bundle: `QuestForge-Mac-Migrate` → open the folder named **`minecraft`**.
3. In that `minecraft` folder: **Edit → Select All** (⌘A).
4. **Edit → Copy** (⌘C).
5. Click the Prism `minecraft` folder from Step 5.
6. **Edit → Paste** (⌘V).
7. When macOS asks about existing items:
   - Choose **Replace** / **Overwrite** for files that already exist (`options.txt`, empty `mods`, etc.).
   - If it offers **Merge** for folders (`mods`, `config`, `assets`), choose **Merge**.
8. Wait until the copy finishes. This is more than 2 GB. The spinner may sit on `assets` and `saves` for a while.

**Do not** copy the outer `QuestForge-Mac-Migrate` folder into Prism.  
**Do not** copy `tools/` into the instance.  
**Do not** delete a folder named `natives` if you see one.

**Success looks like:** inside Prism’s `minecraft` you now have large folders `mods`, `saves`, `assets`, `legends`, plus `resourcepacks/QuestForge.zip`, and `bin/lib` with a Forge jar. Prism’s `natives` (if present) is still there.

---

# Step 7 — Overlay the patched Forge jar (required for splash)

The mural / pulse / emblem splash **only** works with the **patched** Forge 1558 jar in this bundle. Prism’s first launch downloaded a **stock** Forge. You must overlay ours.

## 7a. Our jar (source)

In this bundle:

```
minecraft/bin/lib/forge-1.7.10-10.13.4.1558-1.7.10-universal.jar
```

It is about **2.9 MB**. If it is tiny (a few KB), the copy is damaged — stop and recopy.

After Step 6, the same file should also already be here:

```
…/instances/Quest Forge/minecraft/bin/lib/forge-1.7.10-10.13.4.1558-1.7.10-universal.jar
```

Prism usually does **not** load Forge from `minecraft/bin/lib`. It loads it from its **libraries** cache. You must replace **that** file too.

## 7b. Find Prism’s Forge file

**Method 1 — Finder search**

1. Finder → **Go → Go to Folder…** (⇧⌘G).
2. Paste:

```
~/Library/Application Support/PrismLauncher
```

3. Press ⌘F (search). Set search scope to **PrismLauncher** (this folder).
4. Search for: `1558`
5. Look for a file named like one of these:

   - `forge-1.7.10-10.13.4.1558-1.7.10-universal.jar`
   - `forge-1.7.10-10.13.4.1558-universal.jar`

   Typical folder:

   `~/Library/Application Support/PrismLauncher/libraries/net/minecraftforge/forge/…/`

**Method 2 — walk the folders**

⇧⌘G → paste:

```
~/Library/Application Support/PrismLauncher/libraries/net/minecraftforge/forge
```

Open the folder whose name contains **1558**. The `.jar` inside is the one to replace.

## 7c. Replace it

1. Keep Prism **fully quit** (Prism Launcher → Quit).
2. Copy this bundle’s patched jar (7a).
3. Paste it into Prism’s Forge folder (7b).
4. **If the filenames are identical:** Replace.
5. **If the filenames differ** (ours has an extra `-1.7.10` in the middle, Prism’s might not):
   - Copy our jar into that folder.
   - Duplicate / rename **our** file so it also matches **Prism’s exact filename**.
   - Replace Prism’s original `.jar` with the renamed copy.
   - You want the **patched bytes** under **whichever name Prism already uses**.

**Success looks like:** the Forge `.jar` Prism will load is ~2.9 MB and was just replaced. Next launch should show the **Quest Forge mural splash** (not the default dirt / stock Forge bar). If you still get a black splash or a `BufferOverflow` crash, this step was skipped or the wrong file was replaced.

---

# Step 8 — Java, memory, and JVM args in Prism

1. Open Prism. Right-click **Quest Forge** → **Edit**.
2. Open the **Settings** tab (sometimes a Java subsection).
3. **Enable** “Override Java installation” / custom Java if the checkbox exists.
4. Set Java to the **1.8** path from Step 2c, plus `/bin/java`:

   `/Library/Java/JavaVirtualMachines/temurin-8.jdk/Contents/Home/bin/java`

   If your folder name differs, use:

   `$( /usr/libexec/java_home -v 1.8 )` + `/bin/java`

5. How much RAM does this Mac have?  
   ** → About This Mac → Memory**

   | This Mac has | Max memory in Prism | Min memory |
   |---|---|---|
   | **8 GB** | **4096 MiB** | 1024 MiB |
   | **16 GB** | **6144 MiB** | 2048 MiB |

   **Never set 16384 / 16G** on an 8 GB Mac. The machine will grind to a halt.

6. Open `docs/JVM-ARGS.txt` in this bundle. Copy the **EXTRA JVM ARGS** paragraph (the long single line starting with `-Djava.net.preferIPv4Stack`).
7. Paste it into Prism’s **JVM arguments** / **Java arguments** box.

Those args include `MaxPermSize=256M` (required on Java 8) and the two FML flags that let the patched Forge load.

**Success looks like:** Prism shows Java 8 (1.8.0_xxx), max memory 4096 or 6144, and the extra args box contains `MaxPermSize` and `ignorePatchDiscrepancies`.

A ready-to-copy copy of everything is in `docs/JVM-ARGS.txt`.

---

# Step 9 — Settings that must stay as they are

These files already travelled with the pack. Do not “optimize” them.

| Setting | Value | Why |
|---|---|---|
| OptiFine Fast Render | **off** (`ofFastRender:false`) | Required for Sildur. If someone turns it on, shaders break. |
| Resource pack | **QuestForge.zip** | Menu / branding. |
| Shader pack | Sildur’s Vibrant High | Looks best **if** it compiles. |
| Fallback shader | **Sildur's Enhanced Default v1.19 Fancy** | Already in `shaderpacks/`. |

**If Sildur Vibrant fails to compile on M1 / Rosetta** (pink/black world, shader error, instant kick back to menu):

1. From the title screen: **Options → Video Settings → Shaders** (or Options → Shaders).
2. Select **Sildur's Enhanced Default v1.19 Fancy**.
3. If that still fails, select **OFF**.

`ofFastRender` must stay **false** even with Enhanced Default.

---

# Step 10 — Launch from Prism only

1. Quit anything else heavy (browsers with many tabs are fine; close other games).
2. In Prism, select **Quest Forge** → **Launch**.
3. Wait. First launch after the copy can take several minutes (mod scan + Forge).

**Success looks like:**

- Splash shows the **Quest Forge mural** (painted loading scene) and corner emblem — not a plain dirt background.
- You reach the **CustomMenu** title (branded buttons, including a Mods button).
- **Options → Resource Packs** shows `QuestForge.zip` selected.
- You can click **Singleplayer** and see the copied worlds.

**Never** open VoidLauncher “to fix it.” It will put stock jars back and the splash will go black / crash.

---

# Step 11 — Worlds and the quest book

Copied worlds in `saves/`:

- **Here We Go**
- **Tryhard Run**
- **Test**
- plus a zip backup of Here We Go

## New world

Create a new world as usual. It **automatically** loads `config/betterquesting/DefaultQuests.json`. You do **not** run an admin command.

**Success looks like:** the quest book is the Quest Forge book (not an empty / old Crazy Craft book).

## Existing copied worlds

Open the world. Press the quest key (below). If the book already looks like Quest Forge, **do nothing**.

If the book looks **stale** (old quests, missing new chapters):

1. You must be **op**. In singleplayer you usually already are. If commands are rejected:
   - Escape → **Open to LAN** → **Allow Cheats: ON** → Start LAN World.
2. Press **T** to open chat. Type exactly:

```
/bq_admin default load
```

3. Press Return.

This **replaces that world’s quest progress** with the pack defaults. Only do it if the book is wrong.

---

# Step 12 — Keys you will actually use

These are already set in `options.txt`:

| Action | Key |
|---|---|
| Quest book (Better Questing) | **apostrophe** `'` |
| JourneyMap full map | **J** |

On a Mac keyboard the apostrophe is the key to the **left of Return**, same as on Windows (the `"` key, unshifted).

If a key does nothing: **Options → Controls** and search for Quests / JourneyMap.

---

# Step 13 — Morph (leave it off)

Morph is in **`mods_disabled`**, not in `mods`. **Leave it there.**

The pack was tuned this way. Only move a Morph jar into `mods` if you are deliberately testing the iterate jar in `tools/_morph-optifine-20260904/`. That is optional and not part of first launch.

---

# After you are in-game (first-session checklist)

- [ ] Mural splash appeared (not black, not stock Forge).
- [ ] Title screen is branded; Mods button works.
- [ ] Resource pack `QuestForge.zip` is on.
- [ ] Apostrophe opens the quest book.
- [ ] J opens the map.
- [ ] A copied world loads, **or** a new world has the Quest Forge book.
- [ ] Helicopters / McHeli content exist if you look in the McHeli inventory / spawn (assets travelled).
- [ ] If Vibrant shaders failed: switched to **Enhanced Default**.
- [ ] Fast Render still off.

---

# Troubleshooting

| What you see | What it actually means | What to do |
|---|---|---|
| **wrong architecture** / “incompatible architecture (have 'x86_64', need 'arm64')” or the reverse | You installed **ARM (aarch64)** Java, or Prism is pointed at the wrong Java. | Uninstall the aarch64 JDK. Install the **x64** Temurin 8 `.pkg` from Step 2. Point Prism at that 1.8 path. Confirm `file "$(/usr/libexec/java_home -v 1.8)/bin/java"` says **x86_64**. |
| **`UnsatisfiedLinkError`** / **lwjgl** / “no lwjgl in java.library.path” / mentions **`.dll`** | Windows natives are still in play, **or** you skipped the first Prism launch. | This bundle has **no** `bin/natives` on purpose. Do **not** copy any `.dll`. Create/launch the empty 1.7.10 Forge instance **once** (Step 4) so Prism downloads **macOS** natives. Never point Java at a folder of `.dll` files. |
| **Black splash** / crash mentioning **`BufferOverflow`** / stock dirt splash | Patched Forge was not the jar Prism loaded. | Repeat Step 7. Quit Prism first. Replace **Prism’s** `*1558*universal.jar` with the ~2.9 MB jar from `minecraft/bin/lib/`. |
| **Missing helicopters** / McHeli empty / crash on helicopter content | `assets/mcheli` was not copied. | Confirm `…/minecraft/assets/mcheli` exists and is large (~350 MB). Recopy `assets` from this bundle. Prism will **not** download mcheli for you. |
| Splash is stock, Mods button is vanilla | `CustomMenu.jar` missing, or VoidLauncher restored stock jars. | Confirm `minecraft/mods/CustomMenu.jar` is ~1.5 MB. Do not run VoidLauncher. Recopy `mods` from this bundle. |
| `UnsupportedClassVersion` / `MaxPermSize` unrecognized / instant exit on Java 17 | Prism is using Java 17/21. | Force the Temurin **8** path in instance settings. |
| Pink/black world after title screen, shader compile error | Sildur Vibrant + M1/Rosetta GPU. | Options → Shaders → **Sildur's Enhanced Default v1.19 Fancy**, or Off. Keep Fast Render **false**. |
| Game is a slideshow, Mac fans scream, then freeze | Heap too large for this machine (e.g. 16G Xmx on 8 GB RAM). | Set max memory to **4096** (8 GB Mac) or **6144** (16 GB Mac). |
| Quest book empty / old on a **copied** world | World still has an old BetterQuesting DB. | Only if stale: `/bq_admin default load` while op. Do not run this on a fresh world that already looks right. |
| Prism “Folder” missing | UI wording differs by version. | ⇧⌘G → `~/Library/Application Support/PrismLauncher/instances` |

---

# Optional fallback: `launch-questforge-mac.command`

**Prefer Prism.** Only use this if Prism cannot run and you understand you must supply **macOS** natives yourself.

1. Finish Steps 1–2 (Rosetta + Java 8 x64).
2. Copy this bundle’s `minecraft` folder to somewhere easy, for example `Games/QuestForge` inside your home folder.
3. Copy **macOS** LWJGL 2.9.x natives (from a Prism 1.7.10 instance’s `natives` folder) into `minecraft/bin/natives`. You need `liblwjgl.dylib` (or `.jnilib`). **`.dll` files are Windows and will be refused.**
4. Copy `launch-questforge-mac.command` **into that `minecraft` folder** (same level as `bin/`, `mods/`).
5. In Terminal:

```bash
chmod +x ~/Games/QuestForge/launch-questforge-mac.command
open ~/Games/QuestForge/launch-questforge-mac.command
```

The script uses a **colon** classpath, `java_home -v 1.8`, and **will not start** if it only sees Windows `.dll` natives.

Heap defaults to 4G. On a 16 GB Mac you can run:

```bash
QF_XMX=6144M ~/Games/QuestForge/launch-questforge-mac.command
```

---

# What you should never do

- Do not install **VoidLauncher** or let it “repair” the pack.
- Do not update **CodeChickenCore / NEI** “because they are old.”
- Do not install Java 17/21 “because Minecraft needs a new Java.” **This** Minecraft needs **8**.
- Do not download Temurin **aarch64**.
- Do not copy `bin/natives` from Windows.
- Do not set **16G** heap on an 8 GB Mac.
- Do not turn **Fast Render** on to “go faster.”

---

# `tools/` (optional — not required to play)

Branding sources, splash patch scripts, Morph OptiFine experiment, hero-quest scripts, perf overlay, coremod source. About 213 MB. Leave this folder next to `docs/` on disk if you want to keep iterating later. Do not dump it into Prism’s `mods`.
