# Quest Forge → MacBook transfer (tonight)

Measured 2026-09-04 on this Windows machine. **Nothing was deleted. No zip was created** (see sizes below — a zip is practical, but do not drop another GB+ archive onto OneDrive Desktop).

**Do not use VoidLauncher on either machine.** It MD5-resyncs and restores stock Forge / CustomMenu / mods.

Live game (copy FROM here):

`C:\Users\a2dsu\AppData\Roaming\.crazycraft4`

Work / backups (iterate FROM here):

`C:\Users\a2dsu\OneDrive\Desktop\QuestForge-Work`

Windows launch today: `TEST-LAUNCH.bat` via Desktop `Quest Forge.lnk`  
Java on Windows: `C:\Program Files\Java\jre1.8.0_241`  
Forge: **patched** `bin\lib\forge-1.7.10-10.13.4.1558-1.7.10-universal.jar` (splash buffer, pulse, signatures stripped)  
`mods\CustomMenu.jar` is **patched** (Mods button). Morph is **only** in `mods_disabled`.

Cursor project `Desktop\New folder` (chats / canvases, ~28 MB) is **not** required to run the game.

A Mac launch-script draft is in this folder: `launch-questforge-mac.command` (raw-folder alternative only). Prefer Prism.

---

## 0. What the folders actually weigh

| Location | Size | Notes |
|---|---|---|
| Whole `.crazycraft4` | **2.49 GB** | Under 20 GB — a zip is practical. Includes ~393 MB of `_backup-*` / `_work-*` clutter (74 items). |
| `saves` | **696 MB** | Worlds: `Here We Go` 204, `Tryhard Run` 255, `Test` 156, plus `Here We Go-20251216-222518.zip` 80. **Ask before copying.** |
| `mods` | **680 MB** | 104 jars. Includes patched `CustomMenu.jar`, OptiFine E7, FastCraft 1.25, `1Legends-1.7.10-8.6.2.jar`, `QuestForgeTweaks-1.0.jar`. |
| `assets` | **463 MB** | Vanilla `objects` 113 + **`mcheli` 349** (helicopter pack — must travel) + indexes. |
| `mods_disabled` | **62 MB** | Morph 0.9.3 (already display-list NOP’d), old `Legends.jar`, old `fastcraft.jar`, BattleTowers, InventoryPets, PortalGun beta, RecipeScramble, FastLeafDecay. |
| `bin` | **87 MB** | `minecraft.jar` 5 + `lib` 43 (patched Forge + LWJGL **jars**) + **`natives` 39 MB, 15× `.dll` only — Windows.** |
| `legends` | **132 MB** | Maps for the live Legends jar. Copy with the pack. |
| `resources` | **11.4 MB** | Splash mural / emblem / pulse GIF. |
| `config` | **11.7 MB** | Includes `betterquesting\DefaultQuests.json` (~812 KB) and `splash.properties`. |
| `resourcepacks` | **1.5 MB** | `QuestForge.zip` only. |
| `shaderpacks` | **0.3 MB** | Sildur Vibrant High + Enhanced Default. |
| `scripts` | **8 KB** | `crazycraft_gating.zs`, `questforge_tips.zs`, `projecte_default.zs`. |
| `logs` / `crash-reports` | 3.4 / 0.2 MB | Skip. |
| `journeymap` | **7.7 MB** | Optional (waypoints / explored map). |
| QuestForge-Work **entire** | **5.46 GB** | Mostly old `crazycraft4-sealed-*.zip` (~5 GB). **Do not re-copy those.** |
| QuestForge-Work **lean** (iterate) | **~213 MB** | Branding, splash tools, Morph patch, heroes, perf, coremod source. |

`ofFastRender` is **false** in live `optionsof.txt` (required for Sildur). Keep it false on Mac.

---

## 1. Recommended zip (do this — do not zip the whole AppData dump)

**Create the archive on a USB stick or `C:\Temp`, not on OneDrive Desktop.** OneDrive already holds five sealed snapshots (~5 GB). Another zip there will sync for hours and can leave cloud placeholders (ReparsePoints) that look like files but are empty on the Mac.

Open **PowerShell**. Change `$Dest` to your USB or local folder.

```powershell
$Inst = "$env:APPDATA\.crazycraft4"
$Dest = "D:\QuestForge-Transfer"          # USB or C:\Temp — NOT OneDrive Desktop
$Stage = "C:\Temp\qf-mac-stage"
New-Item -ItemType Directory -Force -Path $Dest, $Stage | Out-Null

# --- REQUIRED (Prism path) ---
$Must = @(
  'mods','mods_disabled','config','scripts','resources',
  'resourcepacks','shaderpacks','legends','hats'
)
foreach ($n in $Must) {
  if (Test-Path "$Inst\$n") {
    robocopy "$Inst\$n" "$Stage\$n" /E /R:1 /W:1 /NFL /NDL /NJH /NJS
  }
}

# Patched Forge + libs, but NOT Windows natives
New-Item -ItemType Directory -Force -Path "$Stage\bin\lib" | Out-Null
Copy-Item "$Inst\bin\minecraft.jar" "$Stage\bin\minecraft.jar"
Copy-Item "$Inst\bin\lib\*" "$Stage\bin\lib\" -Force
# Intentionally skipped: $Inst\bin\natives  (all .dll)

# Vanilla + mcheli assets (mcheli is 349 MB and is not re-downloaded by Prism)
robocopy "$Inst\assets" "$Stage\assets" /E /R:1 /W:1 /NFL /NDL /NJH /NJS

# Options / branding crumbs
foreach ($f in @(
  'options.txt','optionsof.txt','optionsshaders.txt','betterfps.txt',
  'log4j2_17-111.xml','questforge.ico','pack.png','additionalCmdLine.txt'
)) {
  if (Test-Path "$Inst\$f") { Copy-Item "$Inst\$f" "$Stage\$f" }
}

# --- WORLDS: uncomment ONE of these after you decide ---
# robocopy "$Inst\saves" "$Stage\saves" /E /R:1 /W:1
# robocopy "$Inst\saves\Here We Go" "$Stage\saves\Here We Go" /E /R:1 /W:1
# robocopy "$Inst\saves\Tryhard Run" "$Stage\saves\Tryhard Run" /E /R:1 /W:1
# robocopy "$Inst\saves\Test" "$Stage\saves\Test" /E /R:1 /W:1

# --- OPTIONAL ---
# robocopy "$Inst\journeymap" "$Stage\journeymap" /E /R:1 /W:1

# Work folder (iterate) — lean only, skip sealed zips + Windows JDK
$Work = "$env:USERPROFILE\OneDrive\Desktop\QuestForge-Work"
$WorkLean = @(
  'README.txt','TRANSFER-TO-MAC.md','launch-questforge-mac.command',
  'cc4-branding','cc4-branding-v2','cc4-quest55-fix','questforge-coremod',
  'crazycraft4-originals-_backup-20260903-195022',
  '_morph-optifine-20260904','_heroes-20260904','_perf-20260904',
  '_emblem-pulse','_splash-4k-buffer','_splash-knight-glow',
  '_splash-fix-20260904','_splash-boot-fix','_work-hires-splash',
  '_fix-settings-20260904'
)
New-Item -ItemType Directory -Force -Path "$Stage\QuestForge-Work" | Out-Null
foreach ($n in $WorkLean) {
  $src = Join-Path $Work $n
  if (Test-Path $src) {
    if ((Get-Item $src).PSIsContainer) {
      robocopy $src "$Stage\QuestForge-Work\$n" /E /R:1 /W:1 /NFL /NDL /NJH /NJS
    } else {
      Copy-Item $src "$Stage\QuestForge-Work\$n" -Force
    }
  }
}

# Zip (Windows tar.exe). Expect ~1.0–1.4 GB depending on worlds.
tar.exe -a -cf "$Dest\QuestForge-Mac-Play.zip" -C $Stage *
Write-Output "Wrote $Dest\QuestForge-Mac-Play.zip"
```

### Approximate zip sizes

| What you include | Uncompressed | Zip (estimate) |
|---|---|---|
| Required pack, no worlds | **~1.4 GB** | **~1.0–1.2 GB** |
| + all three worlds | **~2.1 GB** | **~1.5–1.7 GB** |
| Whole instance as-is (not recommended) | 2.49 GB | ~1.8–2.1 GB — wastes ~393 MB of `_backup-*` |
| Work lean | 213 MB | ~150 MB |
| Entire QuestForge-Work | 5.46 GB | **Don’t.** 5 GB is old sealed Windows zips + a Windows JDK. |

`Compress-Archive` is fine under ~2 GB but is slower and fussier with long paths. Prefer `tar.exe` / 7-Zip / robocopy-to-USB.

---

## 2. Copy vs skip

### Required (game will be wrong without these)

| Path | Why |
|---|---|
| `mods\` | Entire pack, patched CustomMenu, OptiFine E7, FastCraft **1.25**, Tweaks. |
| `mods_disabled\` | Documents what is off. Includes Morph (leave disabled unless you test the work-folder jar). |
| `config\` | All tuning + **`config\betterquesting\DefaultQuests.json`**. |
| `scripts\` | MineTweaker gating / tips. |
| `resources\` | `loading_mural.png`, `emblem_corner.png`, `mojang_pulse.gif`, logos. |
| `resourcepacks\QuestForge.zip` | Menu / branding pack (`options.txt` already selects it). |
| `shaderpacks\` | Sildur Vibrant High (selected) + Enhanced Default fallback. |
| `bin\minecraft.jar` + `bin\lib\*` | Vanilla + **patched Forge** + LWJGL **jars** (jars are cross-platform). |
| `options.txt` `optionsof.txt` `optionsshaders.txt` | Video / shader / resource-pack selection. Keep `ofFastRender:false`. |
| `assets\mcheli\` | 349 MB extracted helicopter content. **Prism will not regenerate this.** |
| `assets\indexes\` + `assets\objects\` | Needed for a raw `TEST-LAUNCH` clone. Prism can re-download vanilla objects; copying is faster and safer. |
| `legends\` | 132 MB maps used by live `1Legends-*.jar`. |
| `log4j2_17-111.xml` | Only if you use the raw `.command` launcher. |

### Optional

| Path | Why |
|---|---|
| `saves\` | **Your worlds.** Copy if you want to keep playing them. See §7. |
| `journeymap\` | Explored map / waypoints. |
| `hats\` | Hats mod cache (~1 MB). |
| `questforge.ico` `pack.png` | Icon / pack image. |
| `betterfps.txt` | `algorithm=rivens-half`. Harmless to copy. |
| `fonts\` | Tiny. |

### Skip (or copy only if you want archaeology)

| Path | Why |
|---|---|
| `bin\natives\` | **15 Windows `.dll`s** (`lwjgl.dll`, `lwjgl64.dll`, `OpenAL*.dll`, `jinput-dx8*.dll`, Twitch, etc.). A raw copy **will fail on Mac.** |
| `logs\` `crash-reports\` `hs_err_pid*` `minetweaker.log` | Noise. |
| `_backup-*` `_work-*` (74 items, ~393 MB) | Local Windows iteration clutter. |
| `asm\` `debug\` | Regenerated. |
| QuestForge-Work `crazycraft4-sealed-*.zip` | ~5 GB of older Windows snapshots. |
| QuestForge-Work `jdk8\` + `OpenJDK8U-*windows*.zip` | Windows x64 JDK. Mac needs its own Java 8 x64. |
| QuestForge-Work `_tools\` | Windows Real-ESRGAN, etc. |
| Cursor `New folder` | Chats / canvases. Not the game. |

### Work folder that **should** travel (keep iterating)

Bring the lean set (~213 MB):

- `cc4-branding`, `cc4-branding-v2` — button / splash / QuestForge.zip masters
- `_emblem-pulse`, `_splash-*`, `_work-hires-splash`, `_fix-settings-20260904`
- `_morph-optifine-20260904` — includes `Morph-Beta-0.9.3-QF-OPTIFINE.jar` (OneDrive cloud file; open it once on Windows so it hydrates before copy)
- `_heroes-20260904` — quest retarget scripts / notes
- `_perf-20260904` — G1 / OptiFine overlay + `REAPPLY-AFTER-QUIT.bat`
- `questforge-coremod` — Tweaks source
- `cc4-quest55-fix`, `crazycraft4-originals-_backup-20260903-195022`
- this checklist + `launch-questforge-mac.command`

---

## 3. Natives / LWJGL (why a folder clone dies on Mac)

`TEST-LAUNCH.bat` sets:

`-Djava.library.path="%INST%\bin\natives"`

That folder is **Windows-only** (every file is `.dll`). The Java jars `bin\lib\lwjgl-2.9.1.jar` + `lwjgl_util-2.9.1.jar` are fine on Mac; the **native** half is not.

1.7.10 needs LWJGL **2.9.x macOS** dylibs (`liblwjgl.dylib`, `openal.dylib` / `libopenal.dylib`, jinput `.jnilib`). Prism / MultiMC download `lwjgl-platform-2.9.x-natives-osx` and point Java at them.

**If you only copy `.crazycraft4` to a Mac and run a translated `.bat`:** crash on startup (`no lwjgl in java.library.path`, `UnsatisfiedLinkError`, or it tries to load `lwjgl.dll`).

---

## 4. Windows launch (what the Mac script must replace)

`TEST-LAUNCH.bat` today:

- Java: hardcoded `C:\Program Files\Java\jre1.8.0_241\bin\java.exe` (then `jre1.8*` / `jdk1.8*`)
- Classpath: `bin\minecraft.jar` + every `bin\lib\*.jar`, joined with **`;`** (Windows)
- Entry: `net.minecraft.launchwrapper.Launch` + `FMLTweaker`
- Offline: `--username Dev --accessToken 0`
- Assets: `--assetsDir "%INST%\assets"` `--assetIndex 1.7.10`
- JVM: `-Xms2048M -Xmx7168M -XX:MaxPermSize=256M` + **G1** (`MaxGCPauseMillis=50`, `G1HeapRegionSize=16M`, 6/2 GC threads)
- Forge patches: `-Dfml.ignoreInvalidMinecraftCertificates=true` `-Dfml.ignorePatchDiscrepancies=true`
- Verifier (Morph / Tweaks): `-XX:+UseSplitVerifier -XX:+FailOverToOldVerifier`
- Desktop shortcut: target = that bat, icon = `questforge.ico`

On Mac: **colon** classpath, `$(/usr/libexec/java_home -v 1.8)`, **Mac natives**, and a smaller heap on 8 GB machines (`-Xmx4096M` is the draft default; raise toward 6–7G only if the Mac has ≥16 GB).

**Game will not run on Java 17+.** Do not install “just Homebrew java” (that is 17/21).

---

## 5. Mac install order (do this)

### A. Recommended — Prism Launcher (or MultiMC)

1. On the Mac, install **Rosetta** if the machine is Apple Silicon:  
   `softwareupdate --install-rosetta`
2. Install **Java 8 (1.8) x64** — Temurin 8 / Adoptium **x64**, not ARM, not 17+:
   - Adoptium: macOS / x64 / JDK 8  
   - or Homebrew (names change): `brew install --cask temurin@8`  
   Confirm: `/usr/libexec/java_home -v 1.8` and `java -version` → `1.8.0_xxx`
3. Install [Prism Launcher](https://prismlauncher.org/). On Apple Silicon, running Prism **under Rosetta** is the least surprising path while Java 8 is x64.
4. In Prism: create an instance → **Minecraft 1.7.10** → install **Forge 10.13.4.1558** (same as `bin\lib\forge-1.7.10-10.13.4.1558-1.7.10-universal.jar`).
5. Launch **once** so Prism downloads LWJGL **macosx** natives and vanilla assets. Quit.
6. Open the instance folder (`…/minecraft` or `.minecraft` inside the instance).
7. Copy **into that folder** (merge / replace):

   `mods`, `mods_disabled`, `config`, `scripts`, `resources`,  
   `resourcepacks`, `shaderpacks`, `legends`, `hats`,  
   `options.txt`, `optionsof.txt`, `optionsshaders.txt`, `betterfps.txt`,  
   `assets\mcheli` (and `assets\indexes` / `assets\objects` if you brought them),  
   `saves` only if you chose to.

8. **Splash branding:** replace Prism’s Forge universal with the **patched**  
   `bin\lib\forge-1.7.10-10.13.4.1558-1.7.10-universal.jar`  
   (Prism libraries path looks like `libraries/net/minecraftforge/forge/1.7.10-10.13.4.1558-1.7.10/`).
9. Instance settings → Java:
   - Java 8 x64 only
   - Memory: 4096–6144 MB on 8–16 GB Macs; 7168 MB only on ≥24 GB
   - Extra JVM args (paste):

```
-Djava.net.preferIPv4Stack=true
-Dfml.ignoreInvalidMinecraftCertificates=true
-Dfml.ignorePatchDiscrepancies=true
-Dlog4j2.formatMsgNoLookups=true
-XX:MaxPermSize=256M
-XX:+UseG1GC -XX:MaxGCPauseMillis=50 -XX:G1HeapRegionSize=16M
-XX:ParallelGCThreads=4 -XX:ConcGCThreads=1
-XX:+UseSplitVerifier -XX:+FailOverToOldVerifier
-XX:+UseCompressedOops -XX:+DisableExplicitGC
-XX:-HeapDumpOnOutOfMemoryError
```

10. Launch from **Prism**, not VoidLauncher, not a random `.bat`.
11. Confirm: splash mural + corner emblem, CustomMenu Mods button, resource pack `QuestForge.zip`, `ofFastRender` still false, Sildur selected. If Vibrant High is a black screen / compile fail on Apple GPU, switch to **Sildur's Enhanced Default**.

### B. Alternative — copy the whole instance + swap natives + `.command`

1. Same Java 8 x64 + Rosetta as above.
2. Copy the staged folder (no `bin/natives`) to e.g. `~/Games/QuestForge/`.
3. Let Prism (or a 1.7.10 MultiMC instance) download natives, then **copy only the macosx dylibs** into `bin/natives/`. Or extract `lwjgl-platform-2.9.1-natives-osx.jar`.
4. Copy `launch-questforge-mac.command` next to `bin/`, then:

```bash
chmod +x ~/Games/QuestForge/launch-questforge-mac.command
open ~/Games/QuestForge/launch-questforge-mac.command
```

The script **refuses to start** if it still sees `lwjgl.dll` and no `liblwjgl.dylib`.

---

## 6. What breaks if you only copy the folder

| You do this | What happens |
|---|---|
| Copy `.crazycraft4` as-is, run a translated bat | **UnsatisfiedLinkError** — Windows natives. |
| Use Java 17/21 (even “it launches”) | 1.7.10 / Forge 1558 / `MaxPermSize` / split verifier **die**. |
| Use ARM Java 8 (if you find one) or ARM Java 17 | LWJGL2 + this pack expect **x64 Java 8 under Rosetta**. |
| Skip `resources` / patched Forge | Stock splash, no mural / pulse / emblem. |
| Skip `CustomMenu.jar` or let VoidLauncher restore it | Mods button / menu branding revert. |
| Skip `assets/mcheli` | Helicopters missing / crash on content. |
| Skip `config` | Default quests, splash, Lycanites, HBM, etc. reset. |
| Skip `mods_disabled` | Fine to play, but you lose the Morph / old-jar parking lot. |
| Open VoidLauncher “to fix it” | Stock jars come back. Start over from the zip. |
| Copy only OneDrive `QuestForge-Work` | That is tools + old zips, **not** the live 104-mod instance. |
| Copy OneDrive cloud placeholders without hydrating | Empty Morph jar / splash PNGs on the Mac. |

Shaders: Sildur **can** work on Mac if the GPU/driver compiles them. On Apple Silicon, expect more shader compile failures or weird hands/shadows (Rosetta + Java 8 x64 + old GLSL). Keep `ofFastRender` false. Fallback is Enhanced Default, then shaders off.

---

## 7. Worlds and BetterQuesting

- **`DefaultQuests.json` travels with `config\`.** New worlds get the pack quests automatically.
- **`/bq_admin default load` — only if you copied `saves`.** Use it when an old world still shows the pre-Quest-Forge book and you want that world to reload the pack defaults (this **replaces** that world’s quest progress with the file in config). Do **not** run it on a fresh Mac world that already looks correct.
- If you skip `saves`, just create a new world on the Mac. No admin command needed.

---

## 8. Path length / OneDrive

| Path | OneDrive? | Use for transfer? |
|---|---|---|
| `C:\Users\a2dsu\AppData\Roaming\.crazycraft4` | **No** | **Yes — this is the live instance.** |
| `C:\Users\a2dsu\OneDrive\Desktop\QuestForge-Work` | **Yes** | Lean tools only. Many files are OneDrive **ReparsePoints**. Open / “Always keep on this device” before copying. |
| `C:\Users\a2dsu\OneDrive\Desktop\New folder` | Yes | Skip (Cursor). |
| Desktop `Quest Forge.lnk` | Yes (shortcut only) | Windows-only. Recreate on Mac (Prism or `.command`). |

Prefer **robocopy from AppData → USB**. Explorer copies from OneDrive Desktop can miss cloud-only files or hit `MAX_PATH` on deep `_splash-*` trees.

---

## 9. Tonight checklist

- [ ] Quit Minecraft on Windows (so options / JM flush).
- [ ] Decide worlds: none / `Here We Go` / `Tryhard Run` / `Test` / all.
- [ ] Hydrate work files you care about (especially `_morph-optifine-20260904\Morph-Beta-0.9.3-QF-OPTIFINE.jar`).
- [ ] Stage + zip to **USB or C:\Temp** using §1 (required pack ± saves ± lean work).
- [ ] On Mac: Rosetta (if needed) → **Java 8 x64** → Prism → 1.7.10 Forge **1558** → first launch → copy folders → overlay patched Forge → paste JVM args.
- [ ] Launch from Prism. Confirm splash, Mods button, QuestForge pack, shaders or Enhanced Default.
- [ ] If worlds were copied and the quest book is stale: `/bq_admin default load` once.
- [ ] Never open VoidLauncher.

**Drafted Mac launch script:** yes — `QuestForge-Work\launch-questforge-mac.command` (raw-folder path; Prism is still the right default).
