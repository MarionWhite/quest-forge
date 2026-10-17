@echo off
setlocal enabledelayedexpansion
title Quest Forge LITE

rem Quest Forge LITE launcher -- for an install laid out like the pack's own
rem instance (bin\minecraft.jar, bin\lib, bin\natives next to mods\).
rem Put this file in that folder, next to TEST-LAUNCH.bat, and double-click it.
rem
rem OFFLINE ONLY: like TEST-LAUNCH.bat it starts the game without signing in, so
rem it works for singleplayer and LAN tests but NOT on the friends' server, which
rem runs in online mode. To play on the server, use Prism Launcher with the
rem settings in jvm-args.txt. The heap choice below is the same table.
rem
rem Run apply-lite.ps1 once first; this script only sets Java memory.

cd /d "%~dp0" || (echo Could not change to "%~dp0" & pause & exit /b 1)
set "INST=%CD%"

set "JAVA="
if exist "C:\Program Files\Java\jre1.8.0_241\bin\java.exe" set "JAVA=C:\Program Files\Java\jre1.8.0_241\bin\java.exe"
if not defined JAVA for /d %%D in ("C:\Program Files\Java\jre1.8*") do if exist "%%~D\bin\java.exe" set "JAVA=%%~D\bin\java.exe"
if not defined JAVA for /d %%D in ("C:\Program Files\Java\jdk1.8*") do if exist "%%~D\jre\bin\java.exe" set "JAVA=%%~D\jre\bin\java.exe"
if not defined JAVA for /d %%D in ("C:\Program Files\Eclipse Adoptium\jre-8*" "C:\Program Files\Eclipse Adoptium\jdk-8*") do if exist "%%~D\bin\java.exe" set "JAVA=%%~D\bin\java.exe"
if not defined JAVA (
  echo Java 8 64-bit not found. Install Java 8 ^(e.g. Temurin 8 x64^) and try again.
  pause & exit /b 1
)
for %%F in (bin\minecraft.jar bin\natives bin\lib\forge-1.7.10-10.13.4.1558-1.7.10-universal.jar) do (
  if not exist "%%F" (echo Missing "%INST%\%%F" -- is this the Quest Forge folder? & pause & exit /b 1)
)

rem Heap from installed RAM: 8 GB -> 3 GB, 12 GB -> 4 GB, 16 GB -> 5 GB, more -> 6 GB.
set "RAMGB=8"
for /f %%m in ('powershell -NoProfile -Command "[math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory/1GB)"') do set "RAMGB=%%m"
set "XMX=3072M" & set "XMS=1024M"
if !RAMGB! GEQ 11 set "XMX=4096M"
if !RAMGB! GEQ 15 (set "XMX=5120M" & set "XMS=2048M")
if !RAMGB! GEQ 30 set "XMX=6144M"
if defined QF_XMX set "XMX=%QF_XMX%"

set "CP=bin\minecraft.jar"
for %%f in (bin\lib\*.jar) do set "CP=!CP!;bin\lib\%%~nxf"
set "LOG4J="
if exist "log4j2_17-111.xml" set "LOG4J=-Dlog4j.configurationFile=log4j2_17-111.xml"
if not defined QF_USER set "QF_USER=Player"

echo Instance: %INST%
echo Java:     %JAVA%
echo RAM:      %RAMGB% GB  -^>  heap %XMX%   (set QF_XMX=4096M to override)
echo.

"%JAVA%" ^
 -Djava.net.preferIPv4Stack=true ^
 -Dfml.ignoreInvalidMinecraftCertificates=true ^
 -Dfml.ignorePatchDiscrepancies=true ^
 -Dlog4j2.formatMsgNoLookups=true %LOG4J% ^
 -Djava.library.path="%INST%\bin\natives" ^
 -Xms%XMS% -Xmx%XMX% -XX:MaxPermSize=256M ^
 -XX:+UseG1GC -XX:MaxGCPauseMillis=50 -XX:G1HeapRegionSize=16M ^
 -XX:+ParallelRefProcEnabled -XX:+DisableExplicitGC -XX:+UseCompressedOops ^
 -XX:+UseSplitVerifier -XX:+FailOverToOldVerifier -XX:-HeapDumpOnOutOfMemoryError ^
 -cp "!CP!" ^
 net.minecraft.launchwrapper.Launch ^
 --username %QF_USER% --accessToken 0 ^
 --uuid 00000000-0000-0000-0000-000000000000 ^
 --version 1.7.10 --assetIndex 1.7.10 ^
 --tweakClass cpw.mods.fml.common.launcher.FMLTweaker ^
 --gameDir "%INST%" --assetsDir "%INST%\assets" ^
 --userProperties {}

echo.
echo ---- Minecraft exited with code %ERRORLEVEL% ----
pause
