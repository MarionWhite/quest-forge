Quest Forge — M1 Mac migration bundle
=====================================
Built: 2026-09-04
Source instance (NOT deleted, NOT gutted):
  C:\Users\a2dsu\AppData\Roaming\.crazycraft4
Work (lean iterate only; OneDrive placeholders hydrated before copy):
  C:\Users\a2dsu\OneDrive\Desktop\QuestForge-Work
This folder:
  C:\Temp\QuestForge-Mac-Migrate
Zip:
  C:\Temp\QuestForge-Mac-Migrate.zip
  1,910,396,090 bytes  (1,821.90 MB / 1.779 GB)  created 2026-09-04 with tar.exe -a

Read docs/README.md first. Launch from Prism only. Never VoidLauncher.
Do not update CCC/NEI.

Bundle layout
-------------
START-HERE.txt
docs/README.md                  primary M1 Mac guide
docs/JVM-ARGS.txt               copy-paste Java / heap presets
launch-questforge-mac.command   optional raw fallback (also copied into minecraft/)
MANIFEST.txt                    this file
minecraft/                      overlay into Prism's instance minecraft folder
tools/                          lean iterate set (~213 MB)

COPIED — minecraft/  (~2,114.6 MB, 8,520 files)
----------------------------------------------
mods/                           680.2 MB   175 files  (includes patched CustomMenu.jar)
mods_disabled/                   62.4 MB     8 files  (Morph stays HERE)
config/                          11.7 MB   876 files  (includes betterquesting/DefaultQuests.json)
scripts/                          8 KB       3 files
resources/                       11.4 MB     5 files  (loading_mural.png, emblem, pulse)
resourcepacks/                    1.5 MB     1 file   (QuestForge.zip)
shaderpacks/                      0.3 MB     6 files  (Sildur Vibrant High + Enhanced Default)
bin/minecraft.jar                 5.0 MB
bin/lib/                         43.0 MB    43 jars   (patched Forge 1558 ~2,948,988 bytes)
assets/                         462.8 MB  3914 files  (MUST include mcheli ~349.4 MB)
legends/                        131.6 MB   455 files
saves/                          695.6 MB  1971 files
  Here We Go                    204.0 MB
  Tryhard Run                   255.3 MB
  Test                          156.0 MB
  Here We Go-20251216-222518.zip 80.2 MB
  NEI                             0 MB
hats/                             1.2 MB   405 files  (seamless extras)
journeymap/                       7.7 MB   635 files  (waypoints / explored map)
fonts/                            0.1 MB
customnpcs/                       ~4 KB
options.txt, optionsof.txt, optionsshaders.txt
betterfps.txt, additionalCmdLine.txt
log4j2_17-111.xml
questforge.ico, pack.png
launch-questforge-mac.command     (copy; run from this folder if using fallback)

Verified key files
------------------
bin/lib/forge-1.7.10-10.13.4.1558-1.7.10-universal.jar   2,948,988 bytes  (patched, required for splash)
mods/CustomMenu.jar                                      1,495,611 bytes
resourcepacks/QuestForge.zip                             1,528,617 bytes
resources/assets/minecraft/textures/gui/title/loading_mural.png  11,116,157 bytes
config/betterquesting/DefaultQuests.json                   831,573 bytes
assets/mcheli/                                           349.4 MB
questforge.ico                                           101,687 bytes
optionsof.txt  ofFastRender:false
options.txt    resourcePacks=["QuestForge.zip"]
               quest book = apostrophe (key 40)
               JourneyMap = J (key 36)
Morph-Beta-0.9.3.jar is in mods_disabled only (not in mods)
shaderpacks include Enhanced Default fallback
NO bin/natives
NO .dll files anywhere in this bundle

EXCLUDED from the live instance
-------------------------------
bin/natives/                    Windows LWJGL .dlls (would crash on Mac)
logs/                           skip
crash-reports/                  skip
hs_err*                         none copied
minetweaker.log                 skip
TEST-LAUNCH.bat                 Windows-only
asm/, debug/                    regenerated
_backup-*                       Windows iteration clutter (~393 MB)
_work-*                         Windows iteration clutter
_backup-forge-splashbuf-*.jar   leftover at instance root
CustomDISkins/, data/, structures/  empty / unused
modlist.html, nicknames.json, usercache.json, usernamecache.json

COPIED — tools/  (~213.4 MB, 427 files)
---------------------------------------
cc4-branding/
cc4-branding-v2/
cc4-quest55-fix/
questforge-coremod/
crazycraft4-originals-_backup-20260903-195022/
_morph-optifine-20260904/          includes Morph-Beta-0.9.3-QF-OPTIFINE.jar (hydrated, PK header OK)
_heroes-20260904/
_perf-20260904/
_emblem-pulse/
_splash-4k-buffer/
_splash-knight-glow/
_splash-fix-20260904/
_splash-boot-fix/
_work-hires-splash/
_fix-settings-20260904/
README.txt
TRANSFER-TO-MAC.md
launch-questforge-mac.command      (older draft; use bundle-root script)

EXCLUDED from QuestForge-Work
-----------------------------
crazycraft4-sealed-*.zip           ~5 GB older Windows snapshots
jdk8/                              Windows Temurin 8 tree
OpenJDK8U-jdk_x64_windows_*.zip    Windows JDK zip
_tools/                            Windows Real-ESRGAN etc.

Source instance after this build
--------------------------------
Untouched. CustomMenu.jar, bin/natives/*.dll, saves, and assets/mcheli
are still in C:\Users\a2dsu\AppData\Roaming\.crazycraft4.
