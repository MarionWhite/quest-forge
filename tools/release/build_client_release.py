#!/usr/bin/env python3
"""Build the friends' client release (OptiFine E7 and Angelica editions) from the live instance.

    py -3.10 -I tools/release/build_client_release.py --out C:\\qfs\\release-2026-10-17 \\
        --jars C:\\qfb\\dl [--add-shaderpack C:\\qfb\\dl\\complementary\\ComplementaryUnbound_r5.9.3.zip]

Writes, under --out:
  QuestForge-OptiFine\\    a raw game folder (TEST-LAUNCH.bat layout): bin\\ with the hand-patched
                           Forge 1558 jar, mods\\, config\\, assets\\ (vanilla + assets\\mcheli), resources\\ ...
  QuestForge-Angelica\\    the same folder rebuilt by tools/angelica-client/build_angelica_client.py
  each edition's SHA1SUMS.txt, and player-name.txt (the name used to join)

WHY A RAW FOLDER AND NOT A PRISM INSTANCE. The pack has always run on Windows from
%APPDATA%\\.crazycraft4 through TEST-LAUNCH.bat, and that is the layout every boot test uses.
A raw folder is what this script can boot and join-test before anyone downloads it. The
launchers start the game offline, which suits an offline-mode server. An online-mode server
needs a launcher that signs in (Prism), and that path is not tested here.

WHAT IS LEFT OUT: saves, logs, crash reports, screenshots, every _backup-*/_work-* folder,
*.pre-*/*.broken-* jar snapshots, the JourneyMap map cache (its config is kept), personal
caches (usercache, usernamecache, nicknames.json) and the decompiled debug/ classes.

The live instance is only read. Everything is a real copy (never a hard link into it); see
memory note "hardlink hazard". The Angelica builder hard-links between the two release
folders, which is harmless: both are this script's own output.
"""
import argparse, hashlib, os, re, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
LIVE = os.path.join(os.environ.get("APPDATA", ""), ".crazycraft4")

DIRS = ["bin", "mods", "config", "scripts", "resources", "resourcepacks", "shaderpacks", "assets",
        "fonts", "customnpcs", "hats", "structures", "CustomDISkins", "legends"]
FILES = ["options.txt", "optionsof.txt", "optionsshaders.txt", "log4j2_17-111.xml", "betterfps.txt",
         "pack.png", "questforge.ico", "tf-tutorials.txt"]
SKIP_FILE = re.compile(r"\.(pre-|broken-|bak-)|\.jar\.pre|\.batch-tmp$", re.I)
JOURNEYMAP_KEEP = ["config"]          # the map cache (data/) is per player

LAUNCH_E7 = r"""@echo off
setlocal enabledelayedexpansion
title Quest Forge
rem Quest Forge (OptiFine edition) launcher. Starts the game OFFLINE with the name in
rem player-name.txt: fine for singleplayer and for an offline-mode server.
rem Optional: set QF_XMX=6144M (heap), QF_JVM_ARGS / QF_GAME_ARGS (extra arguments, e.g.
rem QF_GAME_ARGS=--server 1.2.3.4 --port 25565 to connect straight away).
cd /d "%~dp0" || (echo Could not change to "%~dp0" & pause & exit /b 1)
set "INST=%CD%"
set "QF_USER="
if exist player-name.txt set /p QF_USER=<player-name.txt
if not defined QF_USER set /p QF_USER=Your Minecraft name:
if not defined QF_USER (echo No name given. & pause & exit /b 1)
>player-name.txt echo !QF_USER!

set "JAVA="
if exist "C:\Program Files\Java\jre1.8.0_241\bin\java.exe" set "JAVA=C:\Program Files\Java\jre1.8.0_241\bin\java.exe"
if not defined JAVA for /d %%D in ("C:\Program Files\Java\jre1.8*") do if exist "%%~D\bin\java.exe" set "JAVA=%%~D\bin\java.exe"
if not defined JAVA for /d %%D in ("C:\Program Files\Java\jdk1.8*") do if exist "%%~D\jre\bin\java.exe" set "JAVA=%%~D\jre\bin\java.exe"
if not defined JAVA for /d %%D in ("C:\Program Files\Eclipse Adoptium\jre-8*" "C:\Program Files\Eclipse Adoptium\jdk-8*") do if exist "%%~D\bin\java.exe" set "JAVA=%%~D\bin\java.exe"
if not defined JAVA (echo Java 8 64-bit not found. Install Temurin 8 JRE x64 and try again. & pause & exit /b 1)
for %%F in (bin\minecraft.jar bin\natives bin\lib\forge-1.7.10-10.13.4.1558-1.7.10-universal.jar) do (
  if not exist "%%F" (echo Missing "%INST%\%%F" -- is this the Quest Forge folder? & pause & exit /b 1)
)

set "RAMGB=16"
for /f %%m in ('powershell -NoProfile -Command "[math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory/1GB)"') do set "RAMGB=%%m"
set "XMX=3072M" & set "XMS=1024M"
if !RAMGB! GEQ 11 set "XMX=4096M"
if !RAMGB! GEQ 15 (set "XMX=5120M" & set "XMS=2048M")
if !RAMGB! GEQ 30 set "XMX=7168M"
if defined QF_XMX set "XMX=%QF_XMX%"

set "CP=bin\minecraft.jar"
for %%f in (bin\lib\*.jar) do set "CP=!CP!;bin\lib\%%~nxf"
echo Player:   !QF_USER!   (edit player-name.txt to change)
echo Java:     %JAVA%
echo Heap:     %XMX%  (RAM %RAMGB% GB; set QF_XMX to override)
echo.
"%JAVA%" ^
 -Djava.net.preferIPv4Stack=true ^
 -Dfml.ignoreInvalidMinecraftCertificates=true ^
 -Dfml.ignorePatchDiscrepancies=true ^
 -Dlog4j2.formatMsgNoLookups=true ^
 -Dlog4j.configurationFile=log4j2_17-111.xml ^
 -Djava.library.path="%INST%\bin\natives" ^
 -Xms%XMS% -Xmx%XMX% -XX:MaxPermSize=256M ^
 -XX:+UseG1GC -XX:MaxGCPauseMillis=50 -XX:G1HeapRegionSize=16M ^
 -XX:+ParallelRefProcEnabled -XX:+DisableExplicitGC -XX:+UseCompressedOops ^
 -XX:+UseSplitVerifier -XX:+FailOverToOldVerifier -XX:-HeapDumpOnOutOfMemoryError %QF_JVM_ARGS% ^
 -cp "!CP!" ^
 net.minecraft.launchwrapper.Launch ^
 --username !QF_USER! --accessToken 0 ^
 --uuid 00000000-0000-0000-0000-000000000000 ^
 --version 1.7.10 --assetIndex 1.7.10 ^
 --tweakClass cpw.mods.fml.common.launcher.FMLTweaker ^
 --gameDir "%INST%" --assetsDir "%INST%\assets" ^
 --userProperties {} %QF_GAME_ARGS%
echo.
echo ---- Minecraft exited with code %ERRORLEVEL% ----
pause
"""

PLAY_ANGELICA = r"""@echo off
setlocal enabledelayedexpansion
rem Asks for (once) and remembers the player name, then runs LAUNCH-ANGELICA.bat with it.
cd /d "%~dp0" || (echo Could not change to "%~dp0" & pause & exit /b 1)
set "QF_USER="
if exist player-name.txt set /p QF_USER=<player-name.txt
if not defined QF_USER set /p QF_USER=Your Minecraft name:
if not defined QF_USER (echo No name given. & pause & exit /b 1)
>player-name.txt echo !QF_USER!
call LAUNCH-ANGELICA.bat
"""


def copy_tree(src, dst, skip_dirs=()):
    n = 0
    for root, dirs, files in os.walk(src):
        rel = os.path.relpath(root, src)
        dirs[:] = [d for d in dirs if not (rel == "." and d in skip_dirs)]
        for f in files:
            if SKIP_FILE.search(f):
                continue
            s = os.path.join(root, f)
            d = os.path.join(dst, rel, f)
            os.makedirs(os.path.dirname(d), exist_ok=True)
            shutil.copy2(s, d)      # a real copy: never link into the live instance
            n += 1
    return n


def sha1sums(folder):
    out = []
    for root, dirs, files in os.walk(folder):
        for f in files:
            p = os.path.join(root, f)
            rel = os.path.relpath(p, folder).replace("\\", "/")
            if rel in ("SHA1SUMS.txt", "player-name.txt") or rel.startswith(("logs/", "saves/", "falsepattern/")):
                continue
            with open(p, "rb") as fh:
                out.append("%s  %s" % (hashlib.sha1(fh.read()).hexdigest(), rel))
    out.sort(key=lambda l: l[42:])
    with open(os.path.join(folder, "SHA1SUMS.txt"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(out) + "\n")
    return len(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--from", dest="src", default=LIVE, help="E7 game folder to package (read only)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--jars", action="append", default=[], help="folder(s) with the Angelica manifest jars")
    ap.add_argument("--add-shaderpack", help="shader pack zip for the Angelica edition")
    ap.add_argument("--no-angelica", action="store_true")
    a = ap.parse_args()
    src, out = os.path.abspath(a.src), os.path.abspath(a.out)
    if os.path.normcase(out).startswith(os.path.normcase(src)):
        sys.exit("--out must not be inside the source instance")
    e7 = os.path.join(out, "QuestForge-OptiFine")
    if os.path.exists(e7):
        sys.exit("%s exists; remove it first (this script never overwrites a folder)" % e7)
    for d in DIRS:
        s = os.path.join(src, d)
        if os.path.isdir(s):
            print("copy %-14s %6d files" % (d, copy_tree(s, os.path.join(e7, d))))
    jm = os.path.join(src, "journeymap")
    for d in JOURNEYMAP_KEEP:
        if os.path.isdir(os.path.join(jm, d)):
            copy_tree(os.path.join(jm, d), os.path.join(e7, "journeymap", d))
    for f in FILES:
        if os.path.isfile(os.path.join(src, f)):
            shutil.copy2(os.path.join(src, f), os.path.join(e7, f))
    with open(os.path.join(e7, "PLAY.bat"), "w", newline="\r\n") as fh:
        fh.write(LAUNCH_E7)
    mcheli = os.path.join(e7, "assets", "mcheli", "helicopters")
    if not os.path.isdir(mcheli):
        sys.exit("assets\\mcheli\\helicopters is missing: MCHeli would have no aircraft")
    print("E7 edition: %d files hashed" % sha1sums(e7))

    if not a.no_angelica:
        ang = os.path.join(out, "QuestForge-Angelica")
        cmd = [sys.executable, "-I", os.path.join(REPO, "tools", "angelica-client", "build_angelica_client.py"),
               "--from", e7, "--to", ang]
        for j in a.jars:
            cmd += ["--jars", j]
        if a.add_shaderpack:
            cmd += ["--add-shaderpack", a.add_shaderpack]
        print(" ".join(cmd))
        subprocess.check_call(cmd)
        for f in ("PLAY.bat",):
            p = os.path.join(ang, f)
            if os.path.exists(p):
                os.remove(p)   # the E7 launcher would refuse (wrong Forge); unlink before writing
        with open(os.path.join(ang, "PLAY-ANGELICA.bat"), "w", newline="\r\n") as fh:
            fh.write(PLAY_ANGELICA)
        print("Angelica edition: %d files hashed" % sha1sums(ang))


if __name__ == "__main__":
    main()
